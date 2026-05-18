"""
LLM Client Abstraction Layer

Supports: Anthropic API, OpenAI API, OpenAI-compatible local endpoints (Ollama/vLLM)
This is THE single point where cloud ↔ local model swap happens.

Extracted from handler_claude.py:
- Anthropic SDK client initialization and API calls
- Streaming response handling
- Token counting
- Model selection / routing logic

New code (not in handler_claude.py):
- OpenAICompatibleClient for Ollama/vLLM/OpenAI endpoints
- LLMRouter for prefix-based model routing
"""

import json
import logging
import os
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, AsyncIterator, Dict, Iterator, List, Optional, Union

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Response dataclass — unified across backends
# ---------------------------------------------------------------------------

@dataclass
class LLMResponse:
    """Unified response object returned by all LLM clients."""
    content: str = ""
    model: str = ""
    input_tokens: int = 0
    output_tokens: int = 0
    stop_reason: Optional[str] = None
    tool_calls: List[Dict[str, Any]] = field(default_factory=list)
    thinking: str = ""
    raw: Any = None  # backend-specific raw response

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens


# ---------------------------------------------------------------------------
# Abstract base
# ---------------------------------------------------------------------------

class LLMClient(ABC):
    """Abstract base for all LLM backends."""

    @abstractmethod
    def create_message(
        self,
        messages: List[Dict],
        tools: Optional[List[Dict]] = None,
        model: str = "",
        max_tokens: int = 4096,
        system_prompt: str = "",
        temperature: float = 0.7,
        **kwargs: Any,
    ) -> LLMResponse:
        """Send a message and return a unified LLMResponse."""
        ...

    @abstractmethod
    def create_message_stream(
        self,
        messages: List[Dict],
        tools: Optional[List[Dict]] = None,
        model: str = "",
        max_tokens: int = 4096,
        system_prompt: str = "",
        temperature: float = 0.7,
        **kwargs: Any,
    ) -> Iterator[str]:
        """Stream text chunks. Yields str pieces."""
        ...

    @abstractmethod
    def count_tokens(self, text: str) -> int:
        """Count tokens for the given text."""
        ...

    @abstractmethod
    def get_available_models(self) -> List[str]:
        """Return list of models available through this backend."""
        ...

    @abstractmethod
    def health_check(self) -> bool:
        """Return True if the backend is reachable."""
        ...


# ---------------------------------------------------------------------------
# AnthropicClient — extracted from handler_claude.py
# ---------------------------------------------------------------------------

class AnthropicClient(LLMClient):
    """Wraps the anthropic Python SDK.

    Extracted from handler_claude.py:
    - __init__: API key loading, Anthropic() / AsyncAnthropic() creation, beta headers
    - create_message: client.messages.create with full param building
    - create_message_stream: client.messages.stream with event iteration
    - count_tokens: approximation (Anthropic doesn't expose a public tokenizer)
    """

    DEFAULT_MODEL = "claude-sonnet-4-5-20250929"

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        beta_features: Optional[str] = None,
    ) -> None:
        try:
            from anthropic import Anthropic, AsyncAnthropic
        except ImportError:
            raise ImportError("anthropic SDK required. Install with: pip install anthropic")

        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        if not self.api_key:
            # Try loading from config helper used by handler_claude.py
            try:
                from Core.config import load_api_key
                self.api_key = load_api_key("CLAUDE")
            except Exception:
                pass
        if not self.api_key:
            raise ValueError("Anthropic API key required (set ANTHROPIC_API_KEY or pass api_key)")

        # Beta headers — mirrors handler_claude.py __init__
        default_beta = "computer-use-2025-01-24,code-execution-2025-08-25,files-api-2025-04-14,web-fetch-2025-09-10"
        beta_str = beta_features or default_beta
        headers = {"anthropic-beta": beta_str}

        kwargs: Dict[str, Any] = {"api_key": self.api_key, "default_headers": headers}
        if base_url:
            kwargs["base_url"] = base_url

        # Explicit timeout — Anthropic SDK default is read=600s which means a stuck
        # server-side connection can hang for up to 10 minutes before surfacing as an
        # error. Vision calls with many images need ~90s; use 120s read as a safe margin.
        try:
            import httpx as _httpx
            _timeout = _httpx.Timeout(connect=10.0, read=120.0, write=60.0, pool=10.0)
        except ImportError:
            _timeout = 120.0  # scalar fallback
        kwargs["timeout"] = _timeout

        self.client = Anthropic(**kwargs)
        self.async_client = AsyncAnthropic(**kwargs)
        logger.info("✅ AnthropicClient initialized (sync + async, read_timeout=120s)")

    # -- helpers extracted from _build_advanced_api_params -----------------

    @staticmethod
    def _supports_thinking(model: str) -> bool:
        """Check if a model supports the thinking capability (from ClaudeModel.supports_thinking)."""
        if not model:
            return False
        return "claude-opus-4" in model or "claude-sonnet-4-5" in model

    def _build_api_params(
        self,
        model: str,
        messages: List[Dict],
        max_tokens: int,
        temperature: float,
        system_prompt: str = "",
        tools: Optional[List[Dict]] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Build params dict for client.messages.create (extracted from handler_claude._build_advanced_api_params)."""
        params: Dict[str, Any] = {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        if system_prompt:
            params["system"] = system_prompt
        if tools:
            params["tools"] = tools

        # Thinking support — requires anthropic-beta header for extended thinking models
        if self._supports_thinking(model):
            thinking_budget = kwargs.get("thinking_budget", 10000)
            params["thinking"] = {"type": "enabled", "budget_tokens": thinking_budget}
            params["temperature"] = 1     # Required when thinking is enabled
            params["max_tokens"] = max(params["max_tokens"], thinking_budget + 1000)
            params["extra_headers"] = {"anthropic-beta": "interleaved-thinking-2025-05-14"}

        # Optional advanced params
        for key in ("top_p", "top_k", "stop_sequences", "tool_choice"):
            if key in kwargs and kwargs[key] is not None:
                params[key] = kwargs[key]

        return params

    # -- core interface ----------------------------------------------------

    def create_message(
        self,
        messages: List[Dict],
        tools: Optional[List[Dict]] = None,
        model: str = "",
        max_tokens: int = 4096,
        system_prompt: str = "",
        temperature: float = 0.7,
        **kwargs: Any,
    ) -> LLMResponse:
        """Synchronous message creation — wraps client.messages.create."""
        model = model or self.DEFAULT_MODEL
        params = self._build_api_params(
            model, messages, max_tokens, temperature, system_prompt, tools, **kwargs
        )
        response = self.client.messages.create(**params)
        return self._parse_response(response)

    async def create_message_async(
        self,
        messages: List[Dict],
        tools: Optional[List[Dict]] = None,
        model: str = "",
        max_tokens: int = 4096,
        system_prompt: str = "",
        temperature: float = 0.7,
        **kwargs: Any,
    ) -> LLMResponse:
        """Async message creation — wraps async_client.messages.create."""
        model = model or self.DEFAULT_MODEL
        params = self._build_api_params(
            model, messages, max_tokens, temperature, system_prompt, tools, **kwargs
        )
        response = await self.async_client.messages.create(**params)
        return self._parse_response(response)

    def create_message_stream(
        self,
        messages: List[Dict],
        tools: Optional[List[Dict]] = None,
        model: str = "",
        max_tokens: int = 4096,
        system_prompt: str = "",
        temperature: float = 0.7,
        **kwargs: Any,
    ) -> Iterator[str]:
        """Streaming — wraps client.messages.stream (extracted from handler_claude streaming code)."""
        model = model or self.DEFAULT_MODEL
        params = self._build_api_params(
            model, messages, max_tokens, temperature, system_prompt, tools, **kwargs
        )

        # Determine if beta API is needed
        needs_beta = False
        if tools:
            needs_beta = any(
                t.get("type") in ("computer_20250124", "code_execution_20250825")
                for t in tools
            )

        if needs_beta:
            stream = self.client.beta.messages.stream(**params)
        else:
            stream = self.client.messages.stream(**params)

        with stream as event_stream:
            for event in event_stream:
                if hasattr(event, "type") and event.type == "content_block_delta":
                    delta = event.delta
                    if hasattr(delta, "type") and delta.type == "text_delta" and hasattr(delta, "text"):
                        yield delta.text

    def count_tokens(self, text: str) -> int:
        """Approximate token count (~4 chars per token for Claude)."""
        return max(1, len(text) // 4)

    def get_available_models(self) -> List[str]:
        return [
            "claude-sonnet-4-5-20250929",
            "claude-sonnet-4-20250514",
            "claude-opus-4-20250514",
            "claude-opus-4.1-20250808",
        ]

    def health_check(self) -> bool:
        try:
            resp = self.client.messages.create(
                model="claude-sonnet-4-5-20250929",
                max_tokens=10,
                messages=[{"role": "user", "content": "ping"}],
            )
            return bool(resp.content)
        except Exception as e:
            logger.warning(f"AnthropicClient health check failed: {e}")
            return False

    # -- response parsing --------------------------------------------------

    @staticmethod
    def _parse_response(response: Any) -> LLMResponse:
        """Parse an Anthropic Message into LLMResponse."""
        content = ""
        thinking = ""
        tool_calls: List[Dict[str, Any]] = []

        for block in response.content:
            if hasattr(block, "text") and block.text is not None:
                # Could be TextBlock
                content += block.text
            elif hasattr(block, "type") and block.type == "tool_use":
                tool_calls.append({
                    "id": getattr(block, "id", ""),
                    "name": getattr(block, "name", ""),
                    "input": getattr(block, "input", {}),
                })
            elif hasattr(block, "type") and block.type == "thinking":
                thinking += getattr(block, "thinking", "")

        return LLMResponse(
            content=content,
            model=response.model,
            input_tokens=response.usage.input_tokens if response.usage else 0,
            output_tokens=response.usage.output_tokens if response.usage else 0,
            stop_reason=getattr(response, "stop_reason", None),
            tool_calls=tool_calls,
            thinking=thinking,
            raw=response,
        )


# ---------------------------------------------------------------------------
# OpenAICompatibleClient — NEW (not in handler_claude.py)
# ---------------------------------------------------------------------------

class OpenAICompatibleClient(LLMClient):
    """Works with any OpenAI-compatible endpoint: Ollama, vLLM, LM Studio, OpenAI itself.

    Built fresh — handler_claude.py has no OpenAI-compatible code.
    Uses requests for HTTP calls to avoid adding openai SDK as hard dependency.
    """

    DEFAULT_MODEL = "llama3"

    def __init__(
        self,
        base_url: str = "http://localhost:11434/v1",
        api_key: str = "none",
        default_model: Optional[str] = None,
    ) -> None:
        import requests as _requests  # noqa: F811
        self._requests = _requests
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        if default_model:
            self.DEFAULT_MODEL = default_model
        logger.info(f"✅ OpenAICompatibleClient initialized → {self.base_url}")

    def _headers(self) -> Dict[str, str]:
        h = {"Content-Type": "application/json"}
        if self.api_key and self.api_key != "none":
            h["Authorization"] = f"Bearer {self.api_key}"
        return h

    @staticmethod
    def _convert_tools_to_openai(tools: Optional[List[Dict]]) -> Optional[List[Dict]]:
        """Convert Anthropic tool format → OpenAI function_calling format."""
        if not tools:
            return None
        openai_tools = []
        for t in tools:
            # Anthropic format: {name, description, input_schema}
            # OpenAI format: {type: "function", function: {name, description, parameters}}
            if t.get("type") in ("computer_20250124", "code_execution_20250825"):
                continue  # Skip Anthropic-specific tool types
            openai_tools.append({
                "type": "function",
                "function": {
                    "name": t.get("name", ""),
                    "description": t.get("description", ""),
                    "parameters": t.get("input_schema", {}),
                },
            })
        return openai_tools or None

    @staticmethod
    def _convert_messages_to_openai(
        messages: List[Dict], system_prompt: str = ""
    ) -> List[Dict]:
        """Prepend system message if needed (Anthropic uses separate system param)."""
        result = []
        if system_prompt:
            result.append({"role": "system", "content": system_prompt})
        for m in messages:
            # Flatten Anthropic-style content blocks to string
            content = m.get("content", "")
            if isinstance(content, list):
                text_parts = []
                for block in content:
                    if isinstance(block, dict) and block.get("type") == "text":
                        text_parts.append(block.get("text", ""))
                    elif isinstance(block, str):
                        text_parts.append(block)
                content = "\n".join(text_parts)
            result.append({"role": m.get("role", "user"), "content": content})
        return result

    def create_message(
        self,
        messages: List[Dict],
        tools: Optional[List[Dict]] = None,
        model: str = "",
        max_tokens: int = 4096,
        system_prompt: str = "",
        temperature: float = 0.7,
        **kwargs: Any,
    ) -> LLMResponse:
        model = model or self.DEFAULT_MODEL
        payload: Dict[str, Any] = {
            "model": model,
            "messages": self._convert_messages_to_openai(messages, system_prompt),
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stream": False,
        }
        oai_tools = self._convert_tools_to_openai(tools)
        if oai_tools:
            payload["tools"] = oai_tools

        resp = self._requests.post(
            f"{self.base_url}/chat/completions",
            headers=self._headers(),
            json=payload,
            timeout=120,
        )
        resp.raise_for_status()
        data = resp.json()
        return self._parse_openai_response(data, model)

    def create_message_stream(
        self,
        messages: List[Dict],
        tools: Optional[List[Dict]] = None,
        model: str = "",
        max_tokens: int = 4096,
        system_prompt: str = "",
        temperature: float = 0.7,
        **kwargs: Any,
    ) -> Iterator[str]:
        """SSE streaming from OpenAI-compatible endpoint."""
        model = model or self.DEFAULT_MODEL
        payload: Dict[str, Any] = {
            "model": model,
            "messages": self._convert_messages_to_openai(messages, system_prompt),
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stream": True,
        }
        oai_tools = self._convert_tools_to_openai(tools)
        if oai_tools:
            payload["tools"] = oai_tools

        resp = self._requests.post(
            f"{self.base_url}/chat/completions",
            headers=self._headers(),
            json=payload,
            timeout=120,
            stream=True,
        )
        resp.raise_for_status()

        for line in resp.iter_lines(decode_unicode=True):
            if not line or not line.startswith("data: "):
                continue
            data_str = line[6:]
            if data_str.strip() == "[DONE]":
                break
            try:
                chunk = json.loads(data_str)
                delta = chunk.get("choices", [{}])[0].get("delta", {})
                text = delta.get("content")
                if text:
                    yield text
            except (json.JSONDecodeError, IndexError):
                continue

    def count_tokens(self, text: str) -> int:
        """Approximate token count. Try tiktoken if available, else ~4 chars/token."""
        try:
            import tiktoken
            enc = tiktoken.get_encoding("cl100k_base")
            return len(enc.encode(text))
        except ImportError:
            return max(1, len(text) // 4)

    def get_available_models(self) -> List[str]:
        try:
            resp = self._requests.get(
                f"{self.base_url}/models", headers=self._headers(), timeout=5
            )
            resp.raise_for_status()
            data = resp.json()
            return [m["id"] for m in data.get("data", [])]
        except Exception:
            return []

    def health_check(self) -> bool:
        try:
            resp = self._requests.get(
                f"{self.base_url}/models", headers=self._headers(), timeout=5
            )
            return resp.status_code == 200
        except Exception:
            return False

    @staticmethod
    def _parse_openai_response(data: Dict, model: str) -> LLMResponse:
        choice = data.get("choices", [{}])[0]
        message = choice.get("message", {})
        content = message.get("content", "") or ""

        tool_calls = []
        for tc in message.get("tool_calls", []):
            func = tc.get("function", {})
            args = func.get("arguments", "{}")
            try:
                parsed_args = json.loads(args) if isinstance(args, str) else args
            except json.JSONDecodeError:
                parsed_args = {"raw": args}
            tool_calls.append({
                "id": tc.get("id", ""),
                "name": func.get("name", ""),
                "input": parsed_args,
            })

        usage = data.get("usage", {})
        return LLMResponse(
            content=content,
            model=data.get("model", model),
            input_tokens=usage.get("prompt_tokens", 0),
            output_tokens=usage.get("completion_tokens", 0),
            stop_reason=choice.get("finish_reason"),
            tool_calls=tool_calls,
            raw=data,
        )


# ---------------------------------------------------------------------------
# LLMRouter — routes model names to the correct client
# ---------------------------------------------------------------------------

class LLMRouter:
    """Routes requests to the correct LLMClient based on model name prefix.

    Routing:
    - "anthropic/claude-*" or bare "claude-*" → AnthropicClient
    - "ollama/*" → OpenAICompatibleClient(localhost:11434)
    - "openai/*" → OpenAICompatibleClient(api.openai.com)
    - No prefix → default client
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        self.clients: Dict[str, LLMClient] = {}
        self.default_client: Optional[LLMClient] = None
        self._prefix_map: Dict[str, str] = {}  # prefix → client key

        if config:
            self._init_from_config(config)

    def _init_from_config(self, config: Dict[str, Any]) -> None:
        """Initialize clients from a config dict.

        Expected format:
        {
            "default": "anthropic",
            "clients": {
                "anthropic": {"type": "anthropic", "api_key": "..."},
                "ollama": {"type": "openai_compatible", "base_url": "http://localhost:11434/v1"},
                "openai": {"type": "openai_compatible", "base_url": "https://api.openai.com/v1", "api_key": "..."},
            },
            "routing": {
                "anthropic/": "anthropic",
                "claude-": "anthropic",
                "ollama/": "ollama",
                "openai/": "openai",
            }
        }
        """
        for name, client_cfg in config.get("clients", {}).items():
            ctype = client_cfg.get("type", "")
            if ctype == "anthropic":
                client = AnthropicClient(
                    api_key=client_cfg.get("api_key"),
                    base_url=client_cfg.get("base_url"),
                )
            elif ctype == "openai_compatible":
                client = OpenAICompatibleClient(
                    base_url=client_cfg.get("base_url", "http://localhost:11434/v1"),
                    api_key=client_cfg.get("api_key", "none"),
                    default_model=client_cfg.get("default_model"),
                )
            else:
                logger.warning(f"Unknown client type '{ctype}' for '{name}', skipping")
                continue
            self.clients[name] = client

        for prefix, client_name in config.get("routing", {}).items():
            self._prefix_map[prefix] = client_name

        default_name = config.get("default", "")
        if default_name in self.clients:
            self.default_client = self.clients[default_name]

    def register_client(self, prefix: str, client: LLMClient, *, is_default: bool = False) -> None:
        """Register a client for a model prefix."""
        key = prefix.rstrip("/").rstrip("-")
        self.clients[key] = client
        self._prefix_map[prefix] = key
        if is_default:
            self.default_client = client

    def route(self, model: str) -> LLMClient:
        """Return the appropriate client for the given model string."""
        # Check prefix map
        for prefix, client_key in self._prefix_map.items():
            if model.startswith(prefix):
                client = self.clients.get(client_key)
                if client:
                    return client

        # Bare claude- names → look for anthropic client
        if model.startswith("claude-"):
            for key, client in self.clients.items():
                if isinstance(client, AnthropicClient):
                    return client

        if self.default_client:
            return self.default_client

        raise ValueError(f"No LLM client registered for model '{model}' and no default set")

    def strip_prefix(self, model: str) -> str:
        """Remove the routing prefix from a model name (e.g. 'ollama/llama3' → 'llama3')."""
        for prefix in self._prefix_map:
            if model.startswith(prefix):
                return model[len(prefix):]
        return model

    def create_message(self, model: str, **kwargs: Any) -> LLMResponse:
        """Route and forward a create_message call."""
        client = self.route(model)
        bare_model = self.strip_prefix(model)
        return client.create_message(model=bare_model, **kwargs)

    def create_message_stream(self, model: str, **kwargs: Any) -> Iterator[str]:
        """Route and forward a streaming call."""
        client = self.route(model)
        bare_model = self.strip_prefix(model)
        return client.create_message_stream(model=bare_model, **kwargs)


# ---------------------------------------------------------------------------
# Convenience factory
# ---------------------------------------------------------------------------

def create_default_router() -> LLMRouter:
    """Create a router with sensible defaults (Anthropic as default, Ollama local)."""
    router = LLMRouter()

    # Anthropic (will use env var ANTHROPIC_API_KEY)
    try:
        anthropic_client = AnthropicClient()
        router.register_client("anthropic/", anthropic_client, is_default=True)
        router.register_client("claude-", anthropic_client)
    except (ValueError, ImportError) as e:
        logger.warning(f"Could not initialize AnthropicClient: {e}")

    # Ollama (local, no API key needed)
    ollama_client = OpenAICompatibleClient(
        base_url="http://localhost:11434/v1",
        api_key="none",
        default_model="llama3",
    )
    router.register_client("ollama/", ollama_client)

    # OpenAI (needs OPENAI_API_KEY)
    openai_key = os.environ.get("OPENAI_API_KEY", "")
    if openai_key:
        openai_client = OpenAICompatibleClient(
            base_url="https://api.openai.com/v1",
            api_key=openai_key,
            default_model="gpt-4o",
        )
        router.register_client("openai/", openai_client)

    return router
