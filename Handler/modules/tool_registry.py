"""
Tool Registry — Unified tool definitions that work with ANY LLM backend.

Tools are plain Python functions. The AgentLoop (see agent_loop.py) handles:
- Converting them to the right schema format (Anthropic or OpenAI-compatible)
- Running the agentic loop (call LLM → execute tools → feed results → repeat)
- Routing to the right backend via LLMRouter

This eliminates ~1,500 lines of manual schema generation, dispatch, and loop code
that was duplicated in handler_claude.py.

Architecture:
    @tool decorator → ToolKit collects tools → AgentLoop runs them
    
    Anthropic path:  ToolKit.to_anthropic_tools() → client.beta.messages.tool_runner()
    OpenAI path:     ToolKit.to_openai_tools() → manual loop with function_call handling
    Local model:     Same as OpenAI path (Ollama/vLLM use OpenAI-compatible API)
"""

import asyncio
import inspect
import json
import logging
import os
import subprocess
import glob as glob_module
import re
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Union

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Tool decorator + metadata
# ---------------------------------------------------------------------------

@dataclass
class ToolMeta:
    """Metadata for a registered tool function."""
    name: str
    description: str
    func: Callable
    input_schema: Dict[str, Any]
    permission: str = "auto"  # auto | prompt | deny


def tool(
    name: str = None,
    description: str = None,
    permission: str = "auto",
):
    """Decorator to register a function as a tool.
    
    Usage:
        @tool(name="Read", description="Read a file")
        def read_file(file_path: str, limit: int = 100) -> str:
            ...
    
    The function's type hints are used to auto-generate the JSON schema.
    Works with Anthropic's @beta_tool, OpenAI function calling, and local models.
    """
    def wrapper(func):
        func._tool_meta = ToolMeta(
            name=name or func.__name__,
            description=description or func.__doc__ or f"Tool: {name or func.__name__}",
            func=func,
            input_schema=_schema_from_function(func),
            permission=permission,
        )
        return func
    return wrapper


def _schema_from_function(func: Callable) -> Dict[str, Any]:
    """Generate JSON schema from function type hints."""
    sig = inspect.signature(func)
    hints = func.__annotations__
    
    properties = {}
    required = []
    
    TYPE_MAP = {
        str: "string",
        int: "integer", 
        float: "number",
        bool: "boolean",
        list: "array",
        dict: "object",
    }
    
    for param_name, param in sig.parameters.items():
        if param_name in ("self", "cls", "kwargs"):
            continue
        
        hint = hints.get(param_name, str)
        # Handle Optional[X]
        origin = getattr(hint, "__origin__", None)
        if origin is Union:
            args = [a for a in hint.__args__ if a is not type(None)]
            hint = args[0] if args else str
        
        json_type = TYPE_MAP.get(hint, "string")
        properties[param_name] = {"type": json_type, "description": param_name}
        
        if param.default is inspect.Parameter.empty:
            required.append(param_name)
    
    return {
        "type": "object",
        "properties": properties,
        "required": required,
    }


# ---------------------------------------------------------------------------
# ToolKit — collects tools, converts to any format
# ---------------------------------------------------------------------------

class ToolKit:
    """Collection of tools that can be exported to any LLM format.
    
    Usage:
        kit = ToolKit()
        kit.add(read_file)           # Function decorated with @tool
        kit.add_raw("CustomTool", schema, handler)  # Manual registration
        
        # For Anthropic SDK tool_runner:
        anthropic_tools = kit.to_anthropic_tools()
        
        # For OpenAI-compatible (Ollama, vLLM, local models):
        openai_tools = kit.to_openai_tools()
        
        # Execute a tool by name:
        result = await kit.execute("Read", {"file_path": "config.py"})
    """
    
    def __init__(self):
        self._tools: Dict[str, ToolMeta] = {}
    
    def add(self, func: Callable) -> "ToolKit":
        """Add a @tool-decorated function."""
        meta = getattr(func, "_tool_meta", None)
        if meta is None:
            raise ValueError(f"{func.__name__} is not decorated with @tool")
        self._tools[meta.name] = meta
        return self
    
    def add_raw(self, name: str, description: str, input_schema: Dict,
                handler: Callable, permission: str = "auto") -> "ToolKit":
        """Add a tool from raw schema (for MCP tools, dynamic tools, etc.)."""
        self._tools[name] = ToolMeta(
            name=name,
            description=description,
            func=handler,
            input_schema=input_schema,
            permission=permission,
        )
        return self
    
    def add_mcp_tools(self, tools: List[Dict], invoke_fn: Callable) -> "ToolKit":
        """Bulk-add MCP tools discovered from a server.
        
        tools: list of {"name": ..., "description": ..., "inputSchema": ...}
        invoke_fn: async fn(tool_name, arguments) -> result
        """
        for t in tools:
            name = t["name"]
            async def _handler(_name=name, **kwargs):
                return await invoke_fn(_name, kwargs)
            
            self._tools[name] = ToolMeta(
                name=name,
                description=t.get("description", ""),
                func=_handler,
                input_schema=t.get("inputSchema", t.get("input_schema", {})),
            )
        return self
    
    def get(self, name: str) -> Optional[ToolMeta]:
        return self._tools.get(name)
    
    def names(self) -> List[str]:
        return list(self._tools.keys())
    
    def __len__(self) -> int:
        return len(self._tools)
    
    # --- Format converters ---
    
    def to_anthropic_tools(self) -> list:
        """Convert to Anthropic beta_tool format for tool_runner.
        
        Returns list of BetaFunctionTool objects if the SDK is available,
        otherwise returns raw dicts (for messages.create 'tools' param).
        """
        try:
            from anthropic import beta_tool as _beta_tool
            result = []
            for meta in self._tools.values():
                # Create a BetaFunctionTool from the function
                # We need to attach the right metadata
                bt = _beta_tool(name=meta.name, description=meta.description)(meta.func)
                result.append(bt)
            return result
        except ImportError:
            # Fallback: return raw dicts
            return self.to_anthropic_schemas()
    
    def to_anthropic_schemas(self) -> List[Dict]:
        """Convert to raw Anthropic API tool schemas (for messages.create)."""
        return [
            {
                "name": meta.name,
                "description": meta.description,
                "input_schema": meta.input_schema,
            }
            for meta in self._tools.values()
        ]
    
    def to_openai_tools(self) -> List[Dict]:
        """Convert to OpenAI function calling format.
        
        Works with: OpenAI API, Ollama, vLLM, LM Studio, any OpenAI-compatible endpoint.
        """
        return [
            {
                "type": "function",
                "function": {
                    "name": meta.name,
                    "description": meta.description,
                    "parameters": meta.input_schema,
                },
            }
            for meta in self._tools.values()
        ]
    
    # --- Execution ---
    
    async def execute(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """Execute a tool by name. Returns the result string/dict."""
        meta = self._tools.get(tool_name)
        if meta is None:
            return f"Error: Unknown tool '{tool_name}'"
        
        try:
            func = meta.func
            if asyncio.iscoroutinefunction(func):
                return await func(**arguments)
            else:
                return func(**arguments)
        except Exception as e:
            logger.error(f"Tool '{tool_name}' execution error: {e}")
            return f"Error executing {tool_name}: {str(e)}"


# ---------------------------------------------------------------------------
# AgentLoop — unified agentic loop for any backend
# ---------------------------------------------------------------------------

class AgentLoop:
    """Unified agentic loop that works with any LLM backend.
    
    For Anthropic: uses SDK tool_runner when available (zero custom loop code).
    For OpenAI-compatible (Ollama, vLLM, local models): manual loop with same tools.
    For trained local models: same as OpenAI path.
    
    Usage:
        loop = AgentLoop(llm_router, toolkit)
        result = await loop.run(
            model="claude-sonnet-4-5-20250929",  # or "ollama/qwen3.5:latest"
            messages=[{"role": "user", "content": "Read config.py and summarize it"}],
            system_prompt="You are a helpful assistant.",
            max_iterations=10,
        )
    """
    
    def __init__(self, llm_router, toolkit: ToolKit):
        """
        llm_router: LLMRouter instance from claude_client.py
        toolkit: ToolKit with registered tools
        """
        self.router = llm_router
        self.toolkit = toolkit
    
    async def run(
        self,
        model: str,
        messages: List[Dict],
        system_prompt: str = None,
        max_iterations: int = 25,
        max_tokens: int = 4096,
        temperature: float = 0.0,
        container: str = None,
        mcp_servers: List[Dict] = None,
        on_tool_start: Callable = None,
        on_tool_end: Callable = None,
    ) -> Dict[str, Any]:
        """Run the agentic loop until completion or max_iterations.
        
        Returns:
            {"content": str, "tool_calls": list, "iterations": int, "model": str}
        """
        # Route to appropriate backend
        if self._is_anthropic_model(model):
            return await self._run_anthropic(
                model, messages, system_prompt, max_iterations, max_tokens,
                temperature, container, mcp_servers, on_tool_start, on_tool_end,
            )
        else:
            return await self._run_openai_compatible(
                model, messages, system_prompt, max_iterations, max_tokens,
                temperature, on_tool_start, on_tool_end,
            )
    
    def _is_anthropic_model(self, model: str) -> bool:
        return model.startswith("claude") or model.startswith("anthropic/")
    
    # --- Anthropic path: use SDK tool_runner ---
    
    async def _run_anthropic(
        self, model, messages, system_prompt, max_iterations, max_tokens,
        temperature, container, mcp_servers, on_tool_start, on_tool_end,
    ) -> Dict[str, Any]:
        """Anthropic path — uses SDK tool_runner. ~10 lines vs ~400 in handler_claude."""
        try:
            client = self.router.get_client_for_model(model)
            if client is None:
                raise RuntimeError(f"No client registered for model: {model}")
            
            # Get the raw Anthropic client
            anthropic_client = getattr(client, "client", None)
            if anthropic_client is None:
                raise RuntimeError("AnthropicClient doesn't have .client attribute")
            
            # Build tool_runner params
            params = {
                "model": model.replace("anthropic/", ""),
                "max_tokens": max_tokens,
                "messages": list(messages),
                "tools": self.toolkit.to_anthropic_tools(),
                "max_iterations": max_iterations,
            }
            if system_prompt:
                params["system"] = system_prompt
            if temperature is not None:
                params["temperature"] = temperature
            if container:
                params["container"] = container
            if mcp_servers:
                params["mcp_servers"] = mcp_servers
            
            # SDK does the entire loop: call → tool_use → execute → tool_result → repeat
            runner = anthropic_client.beta.messages.tool_runner(**params)
            final_message = runner.until_done()
            
            # Extract text content
            content = ""
            for block in final_message.content:
                if hasattr(block, "text") and block.text:
                    content += block.text
            
            return {
                "content": content,
                "model": model,
                "stop_reason": final_message.stop_reason,
                "usage": {
                    "input_tokens": final_message.usage.input_tokens,
                    "output_tokens": final_message.usage.output_tokens,
                },
            }
        
        except Exception as e:
            logger.warning(f"Anthropic tool_runner failed ({e}), falling back to manual loop")
            return await self._run_openai_compatible(
                model, messages, system_prompt, max_iterations, max_tokens,
                temperature, on_tool_start, on_tool_end,
            )
    
    # --- OpenAI-compatible path: manual loop (Ollama, vLLM, local models) ---
    
    async def _run_openai_compatible(
        self, model, messages, system_prompt, max_iterations, max_tokens,
        temperature, on_tool_start, on_tool_end,
    ) -> Dict[str, Any]:
        """OpenAI-compatible path — works with Ollama, vLLM, LM Studio, trained models."""
        
        client = self.router.get_client_for_model(model)
        if client is None:
            raise RuntimeError(f"No client registered for model: {model}")
        
        # Build messages with system prompt
        loop_messages = list(messages)
        
        tools = self.toolkit.to_openai_tools()
        total_usage = {"input_tokens": 0, "output_tokens": 0}
        
        for iteration in range(max_iterations):
            # Call the LLM
            response = await client.create_message(
                model=model,
                messages=loop_messages,
                system=system_prompt,
                max_tokens=max_tokens,
                temperature=temperature,
                tools=tools if tools else None,
            )
            
            # Track usage
            if hasattr(response, "usage"):
                total_usage["input_tokens"] += getattr(response.usage, "input_tokens", 0)
                total_usage["output_tokens"] += getattr(response.usage, "output_tokens", 0)
            
            # Check if there are tool calls
            tool_calls = self._extract_tool_calls(response)
            
            if not tool_calls:
                # No tool calls — task complete
                content = self._extract_text(response)
                return {
                    "content": content,
                    "model": model,
                    "iterations": iteration + 1,
                    "stop_reason": getattr(response, "stop_reason", "end_turn"),
                    "usage": total_usage,
                }
            
            # Append assistant message with tool calls
            loop_messages.append(self._format_assistant_with_tools(response))
            
            # Execute each tool and add results
            for tc in tool_calls:
                tool_name = tc["name"]
                tool_args = tc["arguments"]
                tool_id = tc.get("id", f"call_{tool_name}")
                
                if on_tool_start:
                    on_tool_start(tool_name, tool_args)
                
                result = await self.toolkit.execute(tool_name, tool_args)
                
                if on_tool_end:
                    on_tool_end(tool_name, result)
                
                # Format result for the API
                result_str = json.dumps(result) if not isinstance(result, str) else result
                loop_messages.append(self._format_tool_result(tool_id, tool_name, result_str))
        
        # Max iterations reached
        return {
            "content": "[Max iterations reached]",
            "model": model,
            "iterations": max_iterations,
            "stop_reason": "max_iterations",
            "usage": total_usage,
        }
    
    # --- Response parsing helpers (handle both Anthropic and OpenAI formats) ---
    
    def _extract_tool_calls(self, response) -> List[Dict]:
        """Extract tool calls from either Anthropic or OpenAI response format."""
        calls = []
        
        # Anthropic format: response.content contains ToolUseBlock objects
        if hasattr(response, "content"):
            for block in response.content:
                if hasattr(block, "type") and block.type == "tool_use":
                    calls.append({
                        "id": block.id,
                        "name": block.name,
                        "arguments": block.input if hasattr(block, "input") else {},
                    })
        
        # OpenAI format: response.choices[0].message.tool_calls
        if hasattr(response, "choices"):
            for choice in response.choices:
                msg = choice.message if hasattr(choice, "message") else choice
                if hasattr(msg, "tool_calls") and msg.tool_calls:
                    for tc in msg.tool_calls:
                        func = tc.function if hasattr(tc, "function") else tc
                        args = func.arguments if isinstance(func.arguments, dict) else json.loads(func.arguments or "{}")
                        calls.append({
                            "id": tc.id if hasattr(tc, "id") else f"call_{func.name}",
                            "name": func.name,
                            "arguments": args,
                        })
        
        return calls
    
    def _extract_text(self, response) -> str:
        """Extract text content from either Anthropic or OpenAI response."""
        # Anthropic
        if hasattr(response, "content"):
            parts = []
            for block in response.content:
                if hasattr(block, "text") and block.text:
                    parts.append(block.text)
            if parts:
                return "\n".join(parts)
        
        # OpenAI
        if hasattr(response, "choices"):
            for choice in response.choices:
                msg = choice.message if hasattr(choice, "message") else choice
                if hasattr(msg, "content") and msg.content:
                    return msg.content
        
        return ""
    
    def _format_assistant_with_tools(self, response) -> Dict:
        """Format assistant response with tool calls for conversation history."""
        # Anthropic format
        if hasattr(response, "content"):
            return {"role": "assistant", "content": response.content}
        
        # OpenAI format
        if hasattr(response, "choices"):
            msg = response.choices[0].message
            return {"role": "assistant", "content": msg.content, "tool_calls": msg.tool_calls}
        
        return {"role": "assistant", "content": str(response)}
    
    def _format_tool_result(self, tool_id: str, tool_name: str, result: str) -> Dict:
        """Format tool result for the next API call.
        
        Returns Anthropic format. The LLMRouter's OpenAI client translates if needed.
        """
        return {
            "role": "user",
            "content": [
                {
                    "type": "tool_result",
                    "tool_use_id": tool_id,
                    "content": result,
                }
            ],
        }


# ---------------------------------------------------------------------------
# Built-in tool implementations
# These are plain Python functions. They work with ANY backend.
# ---------------------------------------------------------------------------

@tool(name="Read", description="Read file contents. Supports text files, images, PDFs.")
def tool_read(file_path: str, limit: int = 200, offset: int = 0) -> str:
    """Read file contents with optional line limit and offset."""
    try:
        file_path = os.path.expanduser(file_path)
        if not os.path.exists(file_path):
            return f"Error: File not found: {file_path}"
        
        # Binary files
        ext = os.path.splitext(file_path)[1].lower()
        if ext in (".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp"):
            size = os.path.getsize(file_path)
            return f"[Image file: {file_path}, {size} bytes, {ext}]"
        if ext == ".pdf":
            try:
                import fitz  # PyMuPDF
                doc = fitz.open(file_path)
                text = "\n".join(page.get_text() for page in doc)
                doc.close()
                return text[:50000]
            except ImportError:
                return f"[PDF file: {file_path}, install PyMuPDF to read]"
        
        # Text files
        with open(file_path, "r", errors="replace") as f:
            lines = f.readlines()
        
        total = len(lines)
        selected = lines[offset:offset + limit]
        text = "".join(selected)
        
        if total > offset + limit:
            text += f"\n[... {total - offset - limit} more lines. Use offset={offset + limit} to continue.]"
        
        return text
    except Exception as e:
        return f"Error reading {file_path}: {e}"


@tool(name="Write", description="Write content to a file. Creates directories if needed.")
def tool_write(file_path: str, content: str) -> str:
    """Write content to a file."""
    try:
        file_path = os.path.expanduser(file_path)
        os.makedirs(os.path.dirname(file_path) or ".", exist_ok=True)
        with open(file_path, "w") as f:
            f.write(content)
        return f"Successfully wrote {len(content)} bytes to {file_path}"
    except Exception as e:
        return f"Error writing {file_path}: {e}"


@tool(name="Edit", description="Edit a file by replacing exact text matches.")
def tool_edit(file_path: str, old_string: str, new_string: str) -> str:
    """Replace exact text in a file."""
    try:
        file_path = os.path.expanduser(file_path)
        with open(file_path, "r") as f:
            content = f.read()
        
        if old_string not in content:
            return f"Error: old_string not found in {file_path}"
        
        count = content.count(old_string)
        if count > 1:
            return f"Error: old_string found {count} times in {file_path}. Must be unique."
        
        new_content = content.replace(old_string, new_string, 1)
        with open(file_path, "w") as f:
            f.write(new_content)
        
        return f"Successfully edited {file_path}"
    except Exception as e:
        return f"Error editing {file_path}: {e}"


@tool(name="LS", description="List directory contents.")
def tool_ls(path: str = ".") -> str:
    """List directory contents."""
    try:
        path = os.path.expanduser(path)
        entries = sorted(os.listdir(path))
        result = []
        for e in entries[:200]:
            full = os.path.join(path, e)
            if os.path.isdir(full):
                result.append(f"  {e}/")
            else:
                size = os.path.getsize(full)
                result.append(f"  {e} ({size} bytes)")
        if len(entries) > 200:
            result.append(f"  ... and {len(entries) - 200} more")
        return "\n".join(result)
    except Exception as e:
        return f"Error listing {path}: {e}"


@tool(name="Grep", description="Search file contents using regex patterns.")
def tool_grep(pattern: str, path: str = ".", include: str = "") -> str:
    """Search for pattern in files."""
    try:
        cmd = ["grep", "-rn", pattern, os.path.expanduser(path)]
        if include:
            cmd.insert(2, f"--include={include}")
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        output = result.stdout[:20000]
        if not output:
            return "No matches found."
        return output
    except Exception as e:
        return f"Error searching: {e}"


@tool(name="Glob", description="Find files matching a glob pattern.")
def tool_glob(pattern: str, path: str = ".") -> str:
    """Find files matching a glob pattern."""
    try:
        full = os.path.join(os.path.expanduser(path), pattern)
        matches = sorted(glob_module.glob(full, recursive=True))[:200]
        if not matches:
            return "No files matched."
        return "\n".join(matches)
    except Exception as e:
        return f"Error globbing: {e}"


@tool(name="Bash", description="Execute a shell command.")
def tool_bash(command: str, timeout: int = 60) -> str:
    """Execute a shell command and return output."""
    try:
        result = subprocess.run(
            command, shell=True, capture_output=True, text=True,
            timeout=timeout, cwd=os.path.expanduser("~"),
        )
        output = ""
        if result.stdout:
            output += result.stdout[:30000]
        if result.stderr:
            output += f"\nSTDERR:\n{result.stderr[:10000]}"
        if result.returncode != 0:
            output += f"\n[Exit code: {result.returncode}]"
        return output or "[No output]"
    except subprocess.TimeoutExpired:
        return f"Error: Command timed out after {timeout}s"
    except Exception as e:
        return f"Error executing command: {e}"


# ---------------------------------------------------------------------------
# Default toolkit factory
# ---------------------------------------------------------------------------

def create_default_toolkit() -> ToolKit:
    """Create a ToolKit with all built-in tools registered.
    
    Usage:
        kit = create_default_toolkit()
        # Add any MCP tools:
        kit.add_mcp_tools(discovered_tools, invoke_fn)
        # Use with AgentLoop:
        loop = AgentLoop(llm_router, kit)
    """
    kit = ToolKit()
    kit.add(tool_read)
    kit.add(tool_write)
    kit.add(tool_edit)
    kit.add(tool_ls)
    kit.add(tool_grep)
    kit.add(tool_glob)
    kit.add(tool_bash)
    return kit


# ---------------------------------------------------------------------------
# MCP requirement detection (kept from original for backward compat)
# ---------------------------------------------------------------------------

MCP_KEYWORDS = [
    'email', 'send email', 'mail', 'gohighlevel', 'ghl', 'crm', 'contact',
    'lead', 'campaign', '<healthcare>', 'patient', 'appointment', 'calendar',
    'schedule', 'meeting', 'event', 'meta', 'facebook', 'instagram',
    'social media', 'google', 'drive', 'sheets', 'docs', 'gmail', 'swarm',
    'multi-agent', 'agent_builder', 'agent_registry', 'data_validator',
    'prompt_registry', 'github', 'git', 'pull request', 'railway', 'deploy',
    'wolfram', 'weather', 'news', 'webhook',
]


def request_requires_mcp(prompt: str) -> bool:
    """Quick check if a prompt likely needs MCP tools."""
    prompt_lower = prompt.lower()
    return any(kw in prompt_lower for kw in MCP_KEYWORDS)
