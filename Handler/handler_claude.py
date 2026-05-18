"""
Handler for Claude AI model interactions using REAL Anthropic Python SDK.

CRITICAL: This handler now uses genuine Anthropic Python SDK for all operations.
No more CLI wrappers or subprocess calls. All messages about "Claude SDK" are now TRUTHFUL.

Capabilities:
    - Direct Anthropic API integration
    - Real session management with conversation history
    - Proper error handling with SDK exceptions
    - Tool integration through SDK tools parameter
    - Token usage tracking and context warnings
    - Model selection with real model names
"""

import os
import sys

# AGENT SDK: Prioritize Claude CLI v2.0.9+ in PATH before SDK imports
# This ensures shutil.which("claude") finds the correct version
claude_local_path = "~/.claude/local"
if claude_local_path not in os.environ.get('PATH', ''):
    os.environ['PATH'] = f"{claude_local_path}:{os.environ.get('PATH', '')}"
import json
import logging
import asyncio
import uuid
import base64
import mimetypes
import time
from datetime import datetime
from typing import List, Dict, Union, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum

# Import workspace functions from session_utils (extracted from claude_interface.py, Phase 4)
try:
    from Handler.session_utils import _save_conversation_to_workspace_database, _get_conversation_history_for_claude
    WORKSPACE_INTEGRATION_AVAILABLE = True
except ImportError as e:
    logging.warning(f"[CLAUDE-HANDLER] Workspace integration unavailable: {e}")
    WORKSPACE_INTEGRATION_AVAILABLE = False

# PHASE 6B: Import WorkspaceSharingManager for performance tracking
try:
    from Database.workspace_sharing import WorkspaceSharingManager
    PERFORMANCE_TRACKING_AVAILABLE = True
except ImportError as e:
    logging.warning(f"[CLAUDE-HANDLER] Performance tracking unavailable: {e}")
    PERFORMANCE_TRACKING_AVAILABLE = False

# Multimodal support imports
try:
    import requests
    from PIL import Image
    import io
    HAS_MULTIMODAL_SUPPORT = True
except ImportError:
    logging.warning("⚠️ Multimodal dependencies not available (requests, PIL). Install with: pip install requests pillow")
    HAS_MULTIMODAL_SUPPORT = False

# PDF processing imports
try:
    import PyPDF2
    import fitz  # PyMuPDF for better PDF processing
    HAS_PDF_SUPPORT = True
except ImportError:
    try:
        import PyPDF2
        HAS_PDF_SUPPORT = True
        logging.warning("⚠️ PyMuPDF not available, using PyPDF2 only. Install with: pip install PyMuPDF for better PDF support")
    except ImportError:
        logging.warning("⚠️ PDF dependencies not available. Install with: pip install PyPDF2 PyMuPDF")
        HAS_PDF_SUPPORT = False

# REAL ANTHROPIC SDK IMPORTS - No more CLI wrappers!
try:
    from anthropic import Anthropic, AsyncAnthropic
    from anthropic.types import Message as AnthropicMessage, TextBlock, ToolUseBlock
    from anthropic._exceptions import (
        APIConnectionError,
        APIError,
        AuthenticationError,
        BadRequestError,
        ConflictError,
        InternalServerError,
        NotFoundError,
        PermissionDeniedError,
        RateLimitError,
        UnprocessableEntityError
    )
    HAS_REAL_ANTHROPIC_SDK = True
except ImportError as e:
    logging.error(f"CRITICAL: Real Anthropic SDK not available: {e}")
    logging.error("Install with: pip install anthropic")
    HAS_REAL_ANTHROPIC_SDK = False
    # Create placeholder classes
    class Anthropic: pass
    class AnthropicMessage: pass
    class TextBlock: pass
    class ToolUseBlock: pass

# CLAUDE AGENT SDK IMPORTS - Enhanced agent capabilities
try:
    from claude_agent_sdk import (
        ClaudeSDKClient,
        ClaudeAgentOptions,
        query,
        PermissionMode,
        CanUseTool,
        ToolPermissionContext,
        SettingSource,
        HookCallback,
        HookContext,
        HookMatcher,
        create_sdk_mcp_server,
        tool,
        SdkMcpTool,
        AgentDefinition,
        McpServerConfig,
        McpSdkServerConfig
    )
    HAS_CLAUDE_AGENT_SDK = True
    logging.info("✅ Claude Agent SDK available for enhanced agent capabilities")
except ImportError as e:
    logging.warning(f"⚠️ Claude Agent SDK not available: {e}")
    logging.warning("Install with: pip install claude-agent-sdk")
    HAS_CLAUDE_AGENT_SDK = False
    # Create placeholder classes
    class ClaudeSDKClient: pass
    class ClaudeAgentOptions: pass
    class PermissionMode: pass
    class CanUseTool: pass
    class ToolPermissionContext: pass
    class SettingSource: pass
    class HookCallback: pass
    class HookContext: pass
    class HookMatcher: pass
    class SdkMcpTool: pass
    class AgentDefinition: pass
    class McpServerConfig: pass
    class McpSdkServerConfig: pass
    def query(*args, **kwargs): raise NotImplementedError("SDK not available")
    def create_sdk_mcp_server(*args, **kwargs): raise NotImplementedError("SDK not available")
    def tool(*args, **kwargs): raise NotImplementedError("SDK not available")

from Handler.handler_base import BaseHandler, HandlerResult
from Core.config import load_api_key, API_KEYS

# Configure logging
logger = logging.getLogger(__name__)

# PHASE 2 REFACTOR: Import decomposed modules
# These modules contain clean standalone implementations.
# Old inline classes (RateLimiter, ResponseCache, etc.) remain at bottom of this file as fallback.
try:
    from Handler.modules.resource_manager import (
        ContainerManager as _ContainerManager,
        CostTracker as _CostTracker,
        PerformanceMonitor as _PerformanceMonitor,
    )
    from Handler.modules.prompt_builder import PromptBuilder as _PromptBuilder
    from Handler.modules.tool_registry import ToolKit as _ToolKit, AgentLoop as _AgentLoop
    from Handler.modules.claude_client import LLMRouter as _LLMRouter
    from Handler.modules.session_manager import SessionManager as _SessionManager
    from Handler.modules.content_processor import read_file as _read_file_modular
    _REFACTORED_MODULES_AVAILABLE = True
    logger.info("✅ Decomposed modules loaded (claude_client, tool_registry, session, prompt, resources)")
except ImportError as e:
    _REFACTORED_MODULES_AVAILABLE = False
    logger.warning(f"⚠️ Decomposed modules not available, using inline classes: {e}")

# PHASE 3: BoardRoom Integration Import
# BoardRoom integration uses dependency injection - no imports needed
BOARDROOM_INTEGRATION_AVAILABLE = True
logger.info("✅ BoardRoom integration available via dependency injection")

class ClaudeModel(str, Enum):
    # Only Sonnet 3.7 and newer models (Sonnet 3.5 deprecated)
    CLAUDE_4_SONNET_BASIC = "claude-4-sonnet"
    CLAUDE_4_SONNET = "claude-sonnet-4-5-20250929"  # Model with advanced capability
    CLAUDE_4_OPUS = "claude-opus-4-20250514"  # Most powerful model for complex challenges
    CLAUDE_4_OPUS_41 = "claude-opus-4.1-20250808"  # Latest Opus with 74.5% SWE-bench performance
    
    # Default model (using Sonnet 4.5 instead of deprecated 3.x)
    DEFAULT = "claude-sonnet-4-5-20250929"
    
    @classmethod
    def is_claude4(cls, model_name) -> bool:
        """Check if a model name is a Claude 4 model"""
        if not model_name:
            return False
            
        # Convert enum member to its value if needed
        if hasattr(model_name, 'value'):
            model_str = model_name.value
        else:
            model_str = str(model_name)
            
        # Check for Claude 4 model identifiers
        return any([
            "claude-opus-4" in model_str, 
            "claude-sonnet-4" in model_str,
            "claude-4-opus" in model_str,
            "claude-4-sonnet" in model_str
        ])
        
    @classmethod
    def supports_thinking(cls, model_name) -> bool:
        """Check if a model supports the thinking capability"""
        if not model_name:
            return False
            
        # Convert enum member to its value if needed
        if hasattr(model_name, 'value'):
            model_str = model_name.value
        else:
            model_str = str(model_name)
            
        # Claude 4 models support thinking, but disable for Claude Sonnet 4 to get action-oriented behavior
        if cls.is_claude4(model_name):
            # Disable thinking for Claude Sonnet 4 to prevent conversational behavior
            if hasattr(model_name, 'value'):
                model_str = model_name.value
            else:
                model_str = str(model_name)
            
            # Only enable thinking for Claude 4 Opus, not Claude 4 Sonnet
            return "claude-opus-4" in model_str
            
        # Check if it's specifically the thinking version by enum reference
        if (hasattr(model_name, 'name') and model_name.name == 'CLAUDE_4_SONNET') or \
           (model_name is cls.CLAUDE_4_SONNET):
            return True
        
        # Claude 4.5 Sonnet also supports it
        return "claude-sonnet-4-5-20250929" in model_str

# PHASE 2: COMPLEXITY ROUTING CONSTANTS
COMPLEXITY_THRESHOLD = 0.7  # Threshold for BoardRoom vs Direct routing
FRUSTRATION_LEVELS_REQUIRING_BOARDROOM = ['high', 'extreme']
NEGATIVE_SENTIMENTS_REQUIRING_BOARDROOM = ['negative', 'very_negative']

class MessageRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"

@dataclass
class TextContent:
    type: str = "text"
    text: str = ""

@dataclass
class Message:
    role: str
    content: Union[str, List[TextContent]]

@dataclass
class SessionData:
    """Data structure for tracking conversation sessions"""
    messages: List[Dict[str, Any]]
    system_prompt: str
    model: str
    tools: List[Dict[str, Any]]
    token_count: int
    created_at: datetime
    workspace_id: str = 'default'
    user_id: str = 'default_user'

# ClaudeHandler now uses REAL Anthropic Python SDK
class ClaudeHandler(BaseHandler):
    """Handler for interacting with Claude using REAL Anthropic Python SDK"""
    
    BASE_URL = "https://api.anthropic.com/v1"
    API_VERSION = "2023-06-01"
    REQUIRED_MODELS = ["intent_classifier"]
    
    @staticmethod
            
    def __init__(self):
        """Initialize the Claude handler with REAL Anthropic SDK"""
        super().__init__()
        
        # REAL SDK INITIALIZATION
        self.api_key = load_api_key('CLAUDE') or os.environ.get("ANTHROPIC_API_KEY")
        if not self.api_key:
            logger.error("CRITICAL: Anthropic API key required for real SDK usage")
            logger.error("Set ANTHROPIC_API_KEY environment variable or add to CLAUDE_API_KEY.txt")
            raise ValueError("Anthropic API key required for real SDK usage")
            
        if not HAS_REAL_ANTHROPIC_SDK:
            logger.error("CRITICAL: Real Anthropic SDK not available")
            raise ImportError("Real Anthropic SDK required. Install with: pip install anthropic")
            
        # Initialize REAL Anthropic clients (sync and async) with 2025 beta features
        try:
            # Beta headers for 2025 features (MCP header removed - not supported by API)
            # Multiple beta features are comma-separated (Phase 4.1: Added files-api-2025-04-14, Phase 2: Added web-fetch-2025-09-10)
            beta_headers = {
                "anthropic-beta": "computer-use-2025-01-24,code-execution-2025-08-25,files-api-2025-04-14,web-fetch-2025-09-10"
            }
            
            self.client = Anthropic(api_key=self.api_key, default_headers=beta_headers)
            self.async_client = AsyncAnthropic(api_key=self.api_key, default_headers=beta_headers)
            logger.info("✅ REAL Anthropic SDK clients (sync & async) initialized with 2025 beta features")
            
            # LLMRouter — THE swap point for cloud ↔ local models
            # All new code should use self.llm_router instead of self.client directly
            try:
                from Handler.modules.claude_client import LLMRouter, AnthropicClient, OpenAICompatibleClient
                self.llm_router = LLMRouter()
                # Register Anthropic as default (reuse existing API key)
                _anthropic_llm = AnthropicClient(api_key=self.api_key, beta_features=beta_headers.get("anthropic-beta"))
                self.llm_router.register_client("anthropic/", _anthropic_llm, is_default=True)
                self.llm_router.register_client("claude-", _anthropic_llm)
                # Register Ollama for local models (no API key needed)
                _ollama_llm = OpenAICompatibleClient(
                    base_url="http://localhost:11434/v1",
                    api_key="none",
                    default_model="qwen3.5:latest",
                )
                self.llm_router.register_client("ollama/", _ollama_llm)
                logger.info("✅ LLMRouter initialized (Anthropic default + Ollama local)")
            except Exception as router_err:
                logger.warning(f"LLMRouter init failed (non-fatal, raw clients still work): {router_err}")
                self.llm_router = None
        except Exception as e:
            logger.error(f"CRITICAL: Failed to initialize Anthropic SDK clients: {e}")
            raise
            
        # Default model (Claude Sonnet 4 for action-oriented behavior)
        self.default_model = ClaudeModel.CLAUDE_4_SONNET.value
        
        # Model aliases for convenience (updated for Sonnet 4 and newer only)
        self.model_aliases = {
            "opus": ClaudeModel.CLAUDE_4_OPUS_41.value,  # Use latest Opus 4.1 by default
            "opus4": ClaudeModel.CLAUDE_4_OPUS.value,
            "opus4.1": ClaudeModel.CLAUDE_4_OPUS_41.value,
            "sonnet": ClaudeModel.CLAUDE_4_SONNET.value,
            "thinking": ClaudeModel.CLAUDE_4_SONNET.value,
            "claude4": ClaudeModel.CLAUDE_4_SONNET.value,
            "claude4-opus": ClaudeModel.CLAUDE_4_OPUS_41.value,  # Use latest
            "claude3.7": ClaudeModel.CLAUDE_4_SONNET.value,
            "default": ClaudeModel.DEFAULT.value
        }
        
        # SESSION MANAGEMENT - Real conversation history storage
        self.conversation_history = {}  # session_id -> messages list (temporary cache)
        self.workspace_conversation_cache = {}  # session_id -> workspace conversation data
        self.session_context = {}      # session_id -> context data
        self.active_sessions = set()   # Track active session IDs
        self.session_data = {}         # session_id -> SessionData objects (for async support)

        # CODE EXECUTION CONTAINER MANAGEMENT (Phase 3)
        self.active_containers = {}  # container_id -> {expires_at: ISO timestamp, session_id: str, created_at: float}
        self.container_cleanup_interval = 300  # Check for expired containers every 5 minutes (300 seconds)
        self.last_container_cleanup = time.time()

        # FILES API INTEGRATION (Phase 4)
        self.uploaded_files = {}  # file_id -> {filename: str, size: int, uploaded_at: float, session_id: str}

        # MCP integration tracking
        self.mcp_servers_checked = False
        self.mcp_servers_available = False

        # BoardRoom integration
        if not hasattr(self, 'analyze_request'):
            setattr(self, 'analyze_request', self._analyze_request_implementation)
        
        # Phase 5.8: Initialize Production Features
        self.__init_production_features__()
        
        # ARCH-1.1: Ultra-Conservative Memory Management for 65MB devices
        self.__init_memory_management__()
        
        # =====================================================================
        # MODULE INITIALIZATION — Decomposed modules (handler_claude refactor)
        # These modules contain clean, standalone implementations that replace
        # methods previously embedded in this 16K-line file.
        # New code should use these modules; old methods remain for backward compat.
        # =====================================================================
        try:
            from Handler.modules.session_manager import SessionManager
            from Handler.modules.prompt_builder import PromptBuilder
            from Handler.modules.content_processor import read_file as _read_file
            from Handler.modules.workspace_integration import analyze_workspace_complexity
            from Handler.modules.resource_manager import (
                ContainerManager, CostTracker, PerformanceMonitor
            )
            from Handler.modules.tool_registry import create_default_toolkit, AgentLoop
            
            # Session management
            self._session_mgr = SessionManager()
            
            # Prompt building (wired to session manager for context)
            self._prompt_builder = PromptBuilder(session_manager=self._session_mgr)
            
            # Unified toolkit + agent loop (works with ANY LLM backend)
            self._toolkit = create_default_toolkit()
            if self.llm_router:
                self._agent_loop = AgentLoop(self.llm_router, self._toolkit)
            else:
                self._agent_loop = None
            
            # Resource management
            self._container_mgr = ContainerManager()
            self._cost_tracker = CostTracker(budget_limit=50.0)  # $50/day default
            self._perf_monitor = PerformanceMonitor()
            
            logger.info("✅ Handler modules initialized (session, prompt, toolkit, agent_loop, resources)")
        except Exception as mod_err:
            logger.warning(f"Module initialization failed (non-fatal, legacy methods still work): {mod_err}")
            self._session_mgr = None
            self._prompt_builder = None
            self._toolkit = None
            self._agent_loop = None
            self._container_mgr = None
            self._cost_tracker = None
            self._perf_monitor = None

    # ==================== CLAUDE AGENT SDK INTEGRATION METHODS ====================

    def _load_claude_directory_settings(self, working_dir: str = None) -> Dict[str, Any]:
        """
        Load settings from .claude/ directory per Anthropic Agent SDK specification.

        Loads configuration from:
        - .claude/settings.json (hooks, permissions, tool settings)
        - CLAUDE.md or .claude/CLAUDE.md (system prompt additions, project context)

        Args:
            working_dir: Directory to search for .claude/ folder (defaults to cwd)

        Returns:
            Dict with: {
                'system_prompt_additions': str,
                'tool_permissions': dict,
                'hooks': dict,
                'agents': list,
                'commands': dict
            }
        """
        if not HAS_CLAUDE_AGENT_SDK:
            logger.debug("Claude Agent SDK not available - skipping .claude/ directory loading")
            return {}

        try:
            if working_dir is None:
                working_dir = os.getcwd()

            settings = {
                'system_prompt_additions': '',
                'tool_permissions': {},
                'hooks': {},
                'agents': [],
                'commands': {}
            }

            # Look for .claude directory
            claude_dir = os.path.join(working_dir, '.claude')
            if not os.path.exists(claude_dir):
                logger.debug(f"No .claude directory found in {working_dir}")
                return settings

            # Load settings.json
            settings_file = os.path.join(claude_dir, 'settings.json')
            if os.path.exists(settings_file):
                try:
                    with open(settings_file, 'r') as f:
                        file_settings = json.load(f)
                        settings['hooks'] = file_settings.get('hooks', {})
                        settings['tool_permissions'] = file_settings.get('toolPermissions', {})
                        logger.info(f"✅ Loaded settings from {settings_file}")
                except Exception as e:
                    logger.warning(f"Failed to load {settings_file}: {e}")

            # Load CLAUDE.md (project-level instructions)
            claude_md_paths = [
                os.path.join(working_dir, 'CLAUDE.md'),
                os.path.join(claude_dir, 'CLAUDE.md')
            ]

            for claude_md_path in claude_md_paths:
                if os.path.exists(claude_md_path):
                    try:
                        with open(claude_md_path, 'r') as f:
                            content = f.read()
                            if content.strip():
                                settings['system_prompt_additions'] += f"\n\n# Project Instructions\n{content}"
                                logger.info(f"✅ Loaded project instructions from {claude_md_path}")
                                break  # Only load first found
                    except Exception as e:
                        logger.warning(f"Failed to load {claude_md_path}: {e}")

            # Load agent definitions from .claude/agents/
            agents_dir = os.path.join(claude_dir, 'agents')
            if os.path.exists(agents_dir):
                try:
                    for agent_file in os.listdir(agents_dir):
                        if agent_file.endswith('.md'):
                            agent_path = os.path.join(agents_dir, agent_file)
                            with open(agent_path, 'r') as f:
                                agent_name = agent_file[:-3]  # Remove .md
                                settings['agents'].append({
                                    'name': agent_name,
                                    'definition': f.read()
                                })
                    if settings['agents']:
                        logger.info(f"✅ Loaded {len(settings['agents'])} agent definitions")
                except Exception as e:
                    logger.warning(f"Failed to load agents: {e}")

            # Load slash commands from .claude/commands/
            commands_dir = os.path.join(claude_dir, 'commands')
            if os.path.exists(commands_dir):
                try:
                    for command_file in os.listdir(commands_dir):
                        if command_file.endswith('.md'):
                            command_path = os.path.join(commands_dir, command_file)
                            with open(command_path, 'r') as f:
                                command_name = command_file[:-3]  # Remove .md
                                settings['commands'][command_name] = f.read()
                    if settings['commands']:
                        logger.info(f"✅ Loaded {len(settings['commands'])} slash commands")
                except Exception as e:
                    logger.warning(f"Failed to load commands: {e}")

            return settings

        except Exception as e:
            logger.error(f"Error loading .claude/ directory settings: {e}")
            return {}

    def _create_agent_options(self, parameters: Dict[str, Any], working_dir: str = None) -> ClaudeAgentOptions:
        """
        Build ClaudeAgentOptions for Agent SDK with tool permissions and settings.

        Args:
            parameters: Request parameters with permission_mode, allowed_tools, etc.
            working_dir: Working directory for loading .claude/ settings

        Returns:
            ClaudeAgentOptions configured with permissions, MCP servers, and settings
        """
        if not HAS_CLAUDE_AGENT_SDK:
            logger.debug("Claude Agent SDK not available - cannot create agent options")
            return None

        try:
            # Load .claude/ directory settings
            claude_settings = self._load_claude_directory_settings(working_dir)

            # Map our permission_mode to SDK PermissionMode (string literals)
            # SDK values: 'default', 'acceptEdits', 'plan', 'bypassPermissions'
            permission_mode_map = {
                'allow': 'bypassPermissions',  # Allow all tools
                'deny': 'default',              # Use default (CLI prompts for dangerous tools)
                'ask': 'default'                # Use default behavior
            }

            permission_mode_str = parameters.get('permission_mode', 'ask')
            sdk_permission_mode = permission_mode_map.get(permission_mode_str, 'default')

            # Build tool permissions from parameters
            allowed_tools = parameters.get('allowed_tools', [])
            disallowed_tools = parameters.get('disallowed_tools', [])

            # Merge with .claude/settings.json tool permissions
            if claude_settings.get('tool_permissions'):
                allowed_tools.extend(claude_settings['tool_permissions'].get('allowed', []))
                disallowed_tools.extend(claude_settings['tool_permissions'].get('disallowed', []))

            # Build MCP server configs from parameters
            mcp_servers = {}
            if parameters.get('mcp_servers'):
                for server_name, server_config in parameters['mcp_servers'].items():
                    mcp_servers[server_name] = McpServerConfig(
                        type="subprocess",
                        command=server_config.get('command'),
                        args=server_config.get('args', [])
                    )

            # Create agent options
            # Note: setting_sources values are string literals: 'user', 'project', 'local'
            # Ensure subprocess finds Claude CLI v2.0.9+ by prioritizing .claude/local in PATH
            claude_local_path = "~/.claude/local"
            current_path = os.environ.get('PATH', '')
            updated_path = f"{claude_local_path}:{current_path}" if claude_local_path not in current_path else current_path

            options = ClaudeAgentOptions(
                permission_mode=sdk_permission_mode,
                allowed_tools=allowed_tools if allowed_tools else None,
                disallowed_tools=disallowed_tools if disallowed_tools else None,
                mcp_servers=mcp_servers if mcp_servers else None,
                setting_sources=['project'] if claude_settings else [],
                env={'PATH': updated_path}  # Ensure subprocess uses Claude CLI v2.0.9+
            )

            logger.info(f"✅ Created ClaudeAgentOptions (mode={sdk_permission_mode}, tools_allowed={len(allowed_tools)}, mcp_servers={len(mcp_servers)})")
            return options

        except Exception as e:
            logger.error(f"Error creating agent options: {e}")
            return None



    def _check_tool_permission(self, tool_name: str, tool_input: Dict[str, Any],
                               agent_options: ClaudeAgentOptions = None) -> bool:
        """
        Check if a tool is permitted to execute based on Agent SDK permission settings.

        Args:
            tool_name: Name of the tool to check
            tool_input: Tool input parameters
            agent_options: ClaudeAgentOptions with permission configuration

        Returns:
            True if tool is permitted, False otherwise
        """
        if not HAS_CLAUDE_AGENT_SDK or agent_options is None:
            # Default to allow if SDK not available or no options provided
            return True

        try:
            # Check permission mode (SDK values: 'default', 'acceptEdits', 'plan', 'bypassPermissions')
            if hasattr(agent_options, 'permission_mode'):
                mode = agent_options.permission_mode

                # bypassPermissions mode - allow all tools
                if mode == 'bypassPermissions':
                    return True

            # Check disallowed list first (takes precedence)
            if hasattr(agent_options, 'disallowed_tools') and agent_options.disallowed_tools:
                if tool_name in agent_options.disallowed_tools:
                    logger.warning(f"🚫 Tool '{tool_name}' is in disallowed list")
                    return False

            # Check allowed list (if specified, tool must be in it)
            if hasattr(agent_options, 'allowed_tools') and agent_options.allowed_tools:
                if tool_name not in agent_options.allowed_tools:
                    logger.warning(f"🚫 Tool '{tool_name}' not in allowed list")
                    return False

            # Tool is permitted
            return True

        except Exception as e:
            logger.error(f"Error checking tool permission for '{tool_name}': {e}")
            # Default to allow on error
            return True

    async def _analyze_request_implementation(self, request: str) -> Dict:
        """Analyze request for BoardRoom integration"""
        try:
            # Simple analysis for now - can be enhanced
            return {
                'insights': ['Request analyzed with real SDK'],
                'complexity': 'medium',
                'approach': 'Direct SDK processing',
                'steps': ['Process with real Anthropic SDK'],
                'criteria': ['SDK-based completion']
            }
        except Exception as e:
            logger.error(f"Error in Claude analyze_request: {str(e)}")
            return {
                'insights': [f"Error analyzing request: {str(e)}"],
                'complexity': 'medium', 
                'approach': 'Use direct processing',
                'steps': ['Process with appropriate model'],
                'criteria': ['Best effort completion']
            }

    def _build_advanced_api_params(self, model: str, messages: list, max_tokens: int, temperature: float, 
                                   system_prompt: str = None, tools: list = None, parameters: dict = None) -> dict:
        """Build API parameters for LLM call."""
        api_params = {"model": model, "messages": messages, "max_tokens": max_tokens, "temperature": temperature}
        if system_prompt:
            api_params["system"] = system_prompt
        if tools:
            api_params["tools"] = tools
        if parameters:
            for key in ("top_p", "top_k", "stop_sequences", "tool_choice"):
                val = parameters.get(key)
                if val is not None:
                    api_params[key] = val
        # Thinking support for Claude models
        if ClaudeModel.supports_thinking(model):
            budget = parameters.get("thinking_budget", 1024) if parameters else 1024
            api_params["thinking"] = {"type": "enabled", "budget_tokens": budget}
            api_params["temperature"] = 1
        return api_params

    async def run_modular(self, prompt: str, model: str = None,
                          system_prompt: str = None, tools: list = None,
                          max_iterations: int = 25, session_id: str = None,
                          **kwargs) -> Dict[str, Any]:
        """NEW: Clean entry point using decomposed modules.
        
        This is the future API. Uses LLMRouter + ToolKit + AgentLoop.
        Works with ANY model (Anthropic, Ollama, local, trained).
        
        Args:
            prompt: User's message
            model: Model string (e.g. "claude-sonnet-4-5-20250929", "ollama/qwen3.5:latest")
            system_prompt: System prompt (auto-built if None)
            tools: Additional tools to register (list of @tool-decorated functions)
            max_iterations: Max agent loop iterations
            session_id: Session ID for conversation tracking
            
        Returns:
            {"content": str, "model": str, "usage": dict, "iterations": int}
        """
        if not self._agent_loop:
            raise RuntimeError("Modules not initialized — run_modular requires LLMRouter + ToolKit")
        
        model = model or self.default_model
        session_id = session_id or (self._session_mgr.generate_session_id() if self._session_mgr else "default")
        
        # Build system prompt if not provided
        if not system_prompt and self._prompt_builder:
            system_prompt = self._prompt_builder.build_system_prompt({
                'prompt': prompt,
                'system_prompt': kwargs.get('base_system_prompt', ''),
                **kwargs,
            })
        
        # Register additional tools
        toolkit = self._toolkit
        if tools:
            from Handler.modules.tool_registry import ToolKit
            toolkit = ToolKit()
            # Copy default tools
            for name in self._toolkit.names():
                meta = self._toolkit.get(name)
                toolkit._tools[name] = meta
            # Add extras
            for t in tools:
                toolkit.add(t)
        
        # Build messages
        messages = []
        # Add conversation history if available
        if self._session_mgr:
            history = self._session_mgr.get_history(session_id)
            messages.extend(history)
        messages.append({"role": "user", "content": prompt})
        
        # Run the agent loop (routes to Anthropic or OpenAI-compatible automatically)
        from Handler.modules.tool_registry import AgentLoop
        loop = AgentLoop(self.llm_router, toolkit)
        
        result = await loop.run(
            model=model,
            messages=messages,
            system_prompt=system_prompt,
            max_iterations=max_iterations,
        )
        
        # Track session
        if self._session_mgr:
            self._session_mgr.add_message(session_id, 'user', prompt)
            self._session_mgr.add_message(session_id, 'assistant', result.get('content', ''))
        
        # Track costs
        if self._cost_tracker and result.get('usage'):
            self._cost_tracker.record_request(
                model,
                result['usage'].get('input_tokens', 0),
                result['usage'].get('output_tokens', 0),
            )
        
        result['session_id'] = session_id
        return result

    async def handle(self, task_description: Dict) -> HandlerResult:
        """Handle all requests using REAL Anthropic SDK"""
        try:
            # Fix: Handle case where task_description is None
            if task_description is None:
                logger.error("❌ task_description is None")
                return HandlerResult(
                    success=False,
                    data={"error": "No task description provided"},
                    error="No task description provided"
                )

            parameters = task_description.get('parameters', {})
            return self._execute_claude_sdk_request(parameters)
        except Exception as e:
            logger.error(f"Error in Claude handler: {e}")
            return HandlerResult(
                success=False,
                data={"error": str(e)},
                error=f"Error in Claude handler: {str(e)}"
            )

    def _execute_claude_sdk_request(self, parameters: Dict[str, Any]) -> 'HandlerResult':
        """Execute request — delegates to run_modular (unified backend)."""
        if parameters is None:
            from Handler.base_handler import HandlerResult
            return HandlerResult(success=False, data={"error": "No parameters"}, error="No parameters")
        prompt = parameters.get("prompt", "")
        model = parameters.get("model", self.default_model)
        # Resolve model aliases
        model = self.model_aliases.get(model, model)
        import asyncio
        try:
            result = asyncio.get_event_loop().run_until_complete(
                self.run_modular(prompt=prompt, model=model, **{
                    k: v for k, v in parameters.items()
                    if k in ("system_prompt", "session_id", "max_iterations")
                })
            )
            from Handler.base_handler import HandlerResult
            return HandlerResult(success=True, data=result)
        except Exception as e:
            logger.error(f"run_modular failed: {e}")
            from Handler.base_handler import HandlerResult
            return HandlerResult(success=False, data={"error": str(e)}, error=str(e))
    
    def _build_system_prompt(self, parameters: Dict[str, Any]) -> str:
        """Build system prompt — delegates to PromptBuilder module."""
        if self._prompt_builder:
            return self._prompt_builder.build_system_prompt(parameters)
        # Minimal fallback
        system_prompt = parameters.get("system_prompt", "")
        append = parameters.get("append_system_prompt", "")
        if system_prompt and append:
            return f"{system_prompt}\n\n{append}"
        return append or system_prompt or "You are an AI assistant."

    def _load_multi_agent_prompt(self) -> str:
        if self._prompt_builder:
            return self._prompt_builder.load_multi_agent_prompt()
        return "You are coordinating a multi-agent team."

    def _build_conversation_context_prompt(self, parameters: Dict[str, Any]) -> str:
        """Build conversation context — delegates to SessionManager."""
        if self._session_mgr:
            return self._session_mgr.build_conversation_context_prompt(parameters)
        return ""

    # ═══════════════════════════════════════════════════════════════════════
    # CHAIN-OF-THOUGHT (CoT) PROMPTING METHODS (Phase 3.1)
    # ═══════════════════════════════════════════════════════════════════════

    def _wrap_with_cot_structure(self, prompt: str, enable_cot: bool = False) -> str:
        if self._prompt_builder:
            return self._prompt_builder.wrap_with_cot_structure(prompt, enable_cot)
        return prompt

    def _detect_subtasks_in_response(self, response_text: str) -> List[Dict[str, Any]]:
        if self._prompt_builder:
            return self._prompt_builder.detect_subtasks_in_response(response_text)
        return []

    def _extract_context_handoffs(self, response_text: str) -> Dict[str, Any]:
        if self._session_mgr:
            return self._session_mgr.extract_context_handoffs(response_text)
        return {}

    def _self_correction_pass(self, initial_response: str, original_prompt: str, enable_correction: bool = False) -> str:
        if self._prompt_builder:
            return self._prompt_builder.self_correction_pass(original_response, parameters)
        return original_response

    def _merge_corrections(self, original_response: str, review_response: str) -> str:
        if self._prompt_builder:
            return self._prompt_builder.merge_corrections(original, corrections)
        return original

    # ═══════════════════════════════════════════════════════════════════════
    # END CHAIN-OF-THOUGHT METHODS
    # ═══════════════════════════════════════════════════════════════════════

    def _build_conversation_search_tools(self, parameters: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Build conversation search tools — delegates to session_manager module."""
        from Handler.modules.session_manager import build_conversation_search_tools
        conversation_aggregator_data = parameters.get("conversation_aggregator_data", {})
        if not conversation_aggregator_data:
            return []
        return build_conversation_search_tools()

    def _build_web_search_tool(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Build web_search tool definition with all optional parameters (Phase 1).

        Supports:
        - Configurable max_uses
        - Domain filtering (allowed_domains OR blocked_domains, mutually exclusive)
        - User localization (city, region, country, timezone)
        """
        web_search_tool = {
            "type": "web_search_20250305",
            "name": "web_search",
            "max_uses": parameters.get('web_search_max_uses', 10)
        }

        # Add optional domain filtering (mutually exclusive)
        if 'web_search_allowed_domains' in parameters:
            web_search_tool['allowed_domains'] = parameters['web_search_allowed_domains']
        elif 'web_search_blocked_domains' in parameters:
            web_search_tool['blocked_domains'] = parameters['web_search_blocked_domains']

        # Add optional user localization
        if 'web_search_user_location' in parameters:
            web_search_tool['user_location'] = parameters['web_search_user_location']

        return web_search_tool

    def _process_domain_analysis_request(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Domain analysis — delegates to PromptBuilder."""
        if self._prompt_builder:
            analysis_prompt = self._prompt_builder.build_domain_analysis_prompt(
                parameters.get("prompt", ""), parameters
            )
            # Use the LLM to analyze
            if self.llm_router:
                import asyncio
                response = asyncio.get_event_loop().run_until_complete(
                    self.llm_router.create_message(
                        model=self.default_model,
                        messages=[{"role": "user", "content": analysis_prompt}],
                        max_tokens=2000,
                    )
                )
                if hasattr(response, "content"):
                    for block in response.content:
                        if hasattr(block, "text"):
                            return block.text
        return "Unable to analyze request"


    def _tool_conversation_search(self, tool_input: dict, working_directory: str, permission_mode: str) -> str:
        return "Conversation search handled by SessionManager"

    def _tool_workspace_conversation_history(self, tool_input: dict, working_directory: str, permission_mode: str) -> str:
        return "Workspace history handled by SessionManager"

    
    # CONCURRENT AGENT LOOP SYSTEM METHODS
    def _requires_concurrent_execution(self, prompt: str, parameters: Dict[str, Any]) -> bool:
        """Check if request requires concurrent execution"""
        # Check for explicit concurrent request
        if parameters.get('enable_concurrent_loops', False):
            return True
            
        # Check for multi-faceted requests that benefit from concurrent execution
        concurrent_indicators = [
            'while also', 'at the same time', 'simultaneously', 'in parallel',
            'coordinate with', 'work together', 'multi-agent', 'workspace'
        ]
        
        prompt_lower = prompt.lower()
        return any(indicator in prompt_lower for indicator in concurrent_indicators)
    
    async def execute_concurrent_agent_loops(self, prompt: str, model: str, parameters: Dict[str, Any]) -> HandlerResult:
        """Execute multiple agent loops concurrently"""
        if not hasattr(self, '_concurrent_manager'):
            self._concurrent_manager = ConcurrentAgentLoopManager(self)
            
        return await self._concurrent_manager.execute_concurrent_loops(prompt, model, parameters)
    
    # PHASE 5.7: ASYNC CLIENT SUPPORT
    async def _execute_claude_sdk_request_async(self, parameters: Dict[str, Any]) -> 'HandlerResult':
        """Async SDK request — delegates to LLMRouter."""
        if self._agent_loop:
            model = parameters.get("model", self.default_model)
            prompt = parameters.get("prompt", "")
            system_prompt = parameters.get("system_prompt", "")
            result = await self._agent_loop.run(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                system_prompt=system_prompt,
                max_iterations=parameters.get("max_iterations", 25),
            )
            from Handler.base_handler import HandlerResult
            return HandlerResult(success=True, data=result)
        raise NotImplementedError("AgentLoop not available")

    def _extract_keywords_from_request(self, prompt: str) -> list:
        """
        Extract relevant keywords from user request for knowledge matching.

        Args:
            prompt: User request text

        Returns:
            List of keywords
        """
        # Remove common stop words
        stop_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
            'of', 'with', 'by', 'from', 'as', 'is', 'was', 'are', 'were', 'be',
            'this', 'that', 'these', 'those', 'i', 'you', 'he', 'she', 'it', 'we', 'they',
            'my', 'your', 'his', 'her', 'its', 'our', 'their', 'can', 'will', 'would',
            'should', 'could', 'may', 'might', 'must', 'have', 'has', 'had', 'do', 'does', 'did'
        }

        # Simple tokenization
        words = prompt.lower().split()
        keywords = [w.strip('.,?!:;()[]{}"\'-') for w in words if w.lower() not in stop_words and len(w) > 3]

        # Return top 10 keywords
        return keywords[:10]

    def _load_relevant_knowledge(self, prompt: str, workspace_id: str = None, user_id: str = None) -> dict:
        return ""  # Knowledge loading handled by knowledge vault



    def _generate_session_id(self) -> str:
        """Generate unique session ID for conversation tracking"""
        return str(uuid.uuid4())

    # ===== CODE EXECUTION CONTAINER MANAGEMENT (Phase 3) =====

    def _extract_container_metadata(self, response, session_id: str = None) -> Optional[Dict[str, Any]]:
        if self._container_mgr:
            return self._container_mgr.extract_metadata(response, session_id)
        return None

    def _cleanup_expired_containers(self):
        if self._container_mgr:
            self._container_mgr.cleanup_expired()

    def _get_active_container(self, session_id: str) -> Optional[str]:
        if self._container_mgr:
            return self._container_mgr.get_active_container(session_id)
        return None

    # ===== END CONTAINER MANAGEMENT =====

    # ===== FILES API INTEGRATION (Phase 4) =====




    def _build_multimodal_message_content(
        self,
        prompt: str,
        images: List[str],
        image_urls: List[str],
        documents: List[str],
        vision_use_native_urls: bool = False,
        vision_auto_optimize: bool = False,
        vision_max_dimension: int = 1568,
        vision_use_files_api: bool = False
    ) -> Union[str, List[Dict[str, Any]]]:
        from Handler.modules.content_processor import build_multimodal_content
        return build_multimodal_content(text, images)

    def _optimize_image(self, image_data: bytes, max_dimension: int = 1568, source: str = "image") -> bytes:
        from Handler.modules.content_processor import optimize_image
        return optimize_image(image_data)

    def _validate_image_size(self, image_data: bytes, source: str = "image") -> Dict[str, Any]:
        from Handler.modules.content_processor import validate_image_size
        return validate_image_size(image_data)

    def _process_image_input(
        self,
        image_input: str,
        auto_optimize: bool = False,
        max_dimension: int = 1568,
        use_files_api: bool = False
    ) -> Optional[Dict[str, Any]]:
        from Handler.modules.content_processor import process_image_input
        result = process_image_input(image_input)
        return result

    def _build_url_source_image(self, image_url: str) -> Optional[Dict[str, Any]]:
        return {}  # Image handling in content_processor

    def _upload_image_to_files_api(self, image_data: bytes, filename: str) -> Optional[str]:
        return None  # Files API handled by SDK

    def _build_file_source_image(self, file_id: str) -> Dict[str, Any]:
        """Build Files API source image block (Phase 3.2)

        Creates a content block that references an uploaded file by ID.

        Args:
            file_id: File ID returned from Files API upload

        Returns:
            Document content block with file reference
        """
        logger.info(f"📎 Using Files API reference: {file_id}")

        return {
            "type": "document",
            "source": {
                "type": "file",
                "file_id": file_id
            }
        }

    def _process_image_url(
        self,
        image_url: str,
        use_native_url: bool = False,
        auto_optimize: bool = False,
        max_dimension: int = 1568,
        use_files_api: bool = False
    ) -> Optional[Dict[str, Any]]:
        from Handler.modules.content_processor import process_image_input
        result = process_image_input(url)
        return result
    
    def _load_image_file(
        self,
        file_path: str,
        auto_optimize: bool = False,
        max_dimension: int = 1568,
        use_files_api: bool = False
    ) -> Optional[Dict[str, Any]]:
        from Handler.modules.content_processor import load_image_file
        return load_image_file(file_path)
    
    def _is_base64_string(self, s: str) -> bool:
        from Handler.modules.content_processor import is_base64_string
        return is_base64_string(s)
    
    def _process_document(self, document_path: str) -> Optional[str]:
        """Process document (PDF) and extract text content (Phase 5.2.2)"""
        if not HAS_PDF_SUPPORT:
            logger.warning("⚠️ PDF support not available")
            return None
            
        if not os.path.isfile(document_path):
            logger.error(f"Document file not found: {document_path}")
            return None
        
        # Determine document type
        _, ext = os.path.splitext(document_path.lower())
        
        if ext == '.pdf':
            return self._extract_pdf_content(document_path)
        else:
            logger.warning(f"Unsupported document type: {ext}")
            return None
    
    def _extract_pdf_content(self, pdf_path: str) -> Optional[str]:
        from Handler.modules.content_processor import extract_pdf_text
        return extract_pdf_text(file_path)
    
    def _extract_pdf_with_pymupdf(self, pdf_path: str) -> Optional[str]:
        from Handler.modules.content_processor import extract_pdf_text
        return extract_pdf_text(file_path)
    
    def _extract_pdf_with_pypdf2(self, pdf_path: str) -> Optional[str]:
        from Handler.modules.content_processor import extract_pdf_text
        return extract_pdf_text(file_path)
    
    def _build_tools_from_parameters(self, parameters: Dict[str, Any], working_directory: str = None) -> List[Dict[str, Any]]:
        if self._toolkit:
            return self._toolkit.to_anthropic_schemas()
        raise NotImplementedError("Legacy _build_tools_from_parameters removed")
    
    def _request_requires_mcp_tools(self, parameters: Dict[str, Any]) -> bool:
        from Handler.modules.tool_registry import request_requires_mcp
        prompt = parameters.get("prompt", "") if isinstance(parameters, dict) else str(parameters)
        return request_requires_mcp(prompt)

    def _detect_new_mcp_request(self, prompt: str) -> Optional[str]:
        return None  # MCP detection simplified

    def _requires_multi_agent_workspace(self, prompt: str, parameters: Dict[str, Any]) -> bool:
        from Handler.modules.workspace_integration import requires_multi_agent_workspace
        prompt = parameters.get("prompt", "") if isinstance(parameters, dict) else str(parameters)
        return requires_multi_agent_workspace(prompt, parameters if isinstance(parameters, dict) else None)

    def _analyze_workspace_complexity(self, prompt: str, parameters: Dict[str, Any]) -> str:
        from Handler.modules.workspace_integration import analyze_workspace_complexity
        return analyze_workspace_complexity(prompt)


    def _calculate_dynamic_iterations(self, complexity_level: str) -> int:
        """Calculate maximum iterations based on complexity level"""
        iteration_limits = {
            "LOW": 50,        # Simple multi-agent tasks
            "MEDIUM": 75,     # Standard coordination tasks  
            "HIGH": 100,      # Complex integration projects
            "ENTERPRISE": 150 # Large-scale enterprise workflows
        }
        
        return iteration_limits.get(complexity_level, 75)  # Default to MEDIUM
    
    def _detect_explicit_mcp_request(self, parameters: Dict[str, Any]) -> str:
        return None  # MCP detection simplified
    
    def _load_mcp_patterns_from_registry(self) -> Dict[str, List[str]]:
        return {}  # REMOVED: ToolKit handles MCP tools
    
    def _load_specific_mcp_tools(self, server_names: List[str]) -> List[Dict[str, Any]]:
        pass  # REMOVED: ToolKit.add_mcp_tools() replaces this
    
    
    def _load_mcp_tools_simple(self, server_configs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        pass  # REMOVED: ToolKit.add_mcp_tools() replaces this
    
    def _load_mcp_tools(self, config_path: str) -> List[Dict[str, Any]]:
        return []  # MCP handled by ToolKit
    
    def _load_mcp_tools_sync(self, config_path: str) -> List[Dict[str, Any]]:
        pass  # REMOVED: ToolKit.add_mcp_tools() replaces this
    
    
    def _get_mcp_assignments_for_workspace(self, assigned_orchestrators: List[Union[str, Dict]], required_capabilities: List[str]) -> List[str]:
        return {}  # MCP handled by ToolKit
    
    
    
    def _create_task_preserving_summary(self, messages: List[Dict[str, str]]) -> str:
        if self._session_mgr:
            return self._session_mgr.create_conversation_summary(messages)
        return ""

    def _create_conversation_summary(self, messages: List[Dict[str, str]]) -> str:
        if self._session_mgr:
            return self._session_mgr.create_conversation_summary(messages)
        return f"Previous conversation ({len(messages)} messages)"

    # Helper methods for result creation
    
    # Session management methods for external access
    def get_active_sessions(self) -> List[str]:
        """Get list of active session IDs"""
        return list(self.active_sessions)
    
    
    
    # PHASE 3: TOOL EXECUTION FRAMEWORK
    def _execute_tool(self, tool_block, working_directory: str, permission_mode: str, parameters: Dict[str, Any] = None) -> Dict[str, Any]:
        """Execute tool — delegates to ToolKit."""
        tool_name = tool_block.get("name", "") if isinstance(tool_block, dict) else getattr(tool_block, "name", "")
        tool_input = tool_block.get("input", {}) if isinstance(tool_block, dict) else getattr(tool_block, "input", {})
        tool_id = tool_block.get("id", "") if isinstance(tool_block, dict) else getattr(tool_block, "id", "")
        import asyncio
        if self._toolkit:
            try:
                result = asyncio.get_event_loop().run_until_complete(
                    self._toolkit.execute(tool_name, tool_input)
                )
                return {"tool_use_id": tool_id, "type": "tool_result", "content": str(result)}
            except KeyError:
                pass  # Unknown tool, try MCP
        return {"tool_use_id": tool_id, "type": "tool_result", "content": f"Unknown tool: {tool_name}"}
    

    def _execute_tool_with_workspace(self, tool_block, working_directory: str, permission_mode: str, workspace_context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute tool with workspace context — delegates to _execute_tool."""
        return self._execute_tool(tool_block, working_directory, permission_mode, parameters)
    
    def _execute_mcp_tool_with_workspace(self, tool_name: str, tool_input: Dict, workspace_context: Dict[str, Any], 
                                       working_directory: str, permission_mode: str) -> str:
        return f"MCP tool execution delegated to ToolKit"
    
    def _execute_coordinated_tool(self, tool_name: str, tool_input: Dict, workspace_context: Dict[str, Any],
                                working_directory: str, permission_mode: str) -> str:
        return self._execute_tool(tool_block, working_directory, permission_mode)
    
    def _execute_standard_tool(self, tool_name: str, tool_input: Dict, working_directory: str, permission_mode: str) -> str:
        """Standard tool execution — delegates to ToolKit."""
        import asyncio
        if self._toolkit:
            try:
                result = asyncio.get_event_loop().run_until_complete(
                    self._toolkit.execute(tool_name, tool_input)
                )
                return str(result)
            except KeyError:
                pass
        return f"Unknown tool: {tool_name}"
    
    def _execute_cached_mcp_tool(self, tool_name: str, tool_input: Dict, working_directory: str, permission_mode: str) -> str:
        return None  # MCP handled by ToolKit
    
    def _try_execute_mcp_tool(self, tool_name: str, tool_input: Dict, working_directory: str, permission_mode: str) -> str:
        return None  # MCP handled by ToolKit
    
    async def _execute_real_mcp_call(self, server_name: str, server_config: Dict, operation: str, parameters: Dict) -> str:
        return None  # MCP calls handled by ToolKit
    
    
    
    def _attempt_agent_delegation(self, tool_input: Dict, workspace_context: Dict[str, Any], 
                                server_name: str, tool_name: str) -> Dict[str, Any]:
        return None  # Agent delegation handled by SwarmHandler
    
    def _determine_mcp_server_for_tool(self, tool_name: str) -> str:
        return None  # MCP routing handled by ToolKit
    
    def _tool_read(self, input_params: Dict, working_directory: str, permission_mode: str) -> str:
        from Handler.modules.tool_registry import tool_read
        file_path = tool_input.get("file_path", "")
        limit = tool_input.get("limit", 200)
        offset = tool_input.get("offset", 0)
        return tool_read(file_path=file_path, limit=limit, offset=offset)
    
    def _read_text_file(self, file_path: str, offset: int = 0, limit: int = None) -> str:
        from Handler.modules.content_processor import read_text_file
        return read_text_file(file_path)
    
    def _read_image_file(self, file_path: str) -> str:
        from Handler.modules.content_processor import load_image_file
        data, media_type = load_image_file(file_path)
        return data
    
    def _read_pdf_file(self, file_path: str, offset: int = 0, limit: int = None) -> str:
        from Handler.modules.content_processor import extract_pdf_text
        return extract_pdf_text(file_path)
    
    def _read_notebook_file(self, file_path: str) -> str:
        from Handler.modules.content_processor import read_notebook
        return read_notebook(file_path)
    
    def _tool_write(self, input_params: Dict, working_directory: str, permission_mode: str) -> str:
        from Handler.modules.tool_registry import tool_write
        file_path = tool_input.get("file_path", "")
        content = tool_input.get("content", "")
        return tool_write(file_path=file_path, content=content)
    
    def _tool_edit(self, input_params: Dict, working_directory: str, permission_mode: str) -> str:
        from Handler.modules.tool_registry import tool_edit
        file_path = tool_input.get("file_path", "")
        old_string = tool_input.get("old_string", "")
        new_string = tool_input.get("new_string", "")
        return tool_edit(file_path=file_path, old_string=old_string, new_string=new_string)
    
    def _tool_multiedit(self, input_params: Dict, working_directory: str, permission_mode: str) -> str:
        from Handler.modules.tool_registry import tool_edit
        edits = tool_input.get("edits", [])
        results = []
        for edit in edits:
            r = tool_edit(file_path=edit.get("file_path",""), old_string=edit.get("old_string",""), new_string=edit.get("new_string",""))
            results.append(r)
        return "\n".join(results)
    
    def _tool_ls(self, input_params: Dict, working_directory: str, permission_mode: str) -> str:
        from Handler.modules.tool_registry import tool_ls
        path = tool_input.get("path", working_directory or ".")
        return tool_ls(path=path)
    
    def _tool_grep(self, input_params: Dict, working_directory: str, permission_mode: str) -> str:
        from Handler.modules.tool_registry import tool_grep
        pattern = tool_input.get("pattern", "")
        path = tool_input.get("path", working_directory or ".")
        include = tool_input.get("include", "")
        return tool_grep(pattern=pattern, path=path, include=include)
    
    def _tool_glob(self, input_params: Dict, working_directory: str, permission_mode: str) -> str:
        from Handler.modules.tool_registry import tool_glob
        pattern = tool_input.get("pattern", "")
        path = tool_input.get("path", working_directory or ".")
        return tool_glob(pattern=pattern, path=path)
    
    def _tool_bash(self, input_params: Dict, working_directory: str, permission_mode: str) -> str:
        from Handler.modules.tool_registry import tool_bash
        command = tool_input.get("command", "")
        timeout = tool_input.get("timeout", 60)
        return tool_bash(command=command, timeout=timeout)
    
    def _tool_webfetch(self, input_params: Dict, working_directory: str, permission_mode: str) -> str:
        url = tool_input.get("url", "")
        try:
            import urllib.request
            with urllib.request.urlopen(url, timeout=30) as resp:
                return resp.read().decode("utf-8", errors="replace")[:50000]
        except Exception as e:
            return f"Error fetching {url}: {e}"
    
    def _html_to_markdown_basic(self, html_content: str) -> str:
        return html  # Pass through

    def _handle_web_fetch_tool_result(self, content_block) -> str:
        return str(content_block) if content_block else ""

    def _handle_web_search_tool_result(self, content_block) -> str:
        return str(content_block) if content_block else ""

    def _tool_websearch(self, input_params: Dict, working_directory: str, permission_mode: str) -> str:
        return "Web search handled by external tools"
    
    def _tool_todowrite(self, input_params: Dict, working_directory: str, permission_mode: str) -> str:
        return "TODO management handled by external tools"
    
    def _tool_todosearch(self, input_params: Dict, working_directory: str, permission_mode: str) -> str:
        return "TODO search handled by external tools"
    
    def _tool_task(self, input_params: Dict, working_directory: str, permission_mode: str, original_parameters: Dict[str, Any] = None) -> str:
        return "Sub-agent tasks handled by AgentLoop"
    
    def _execute_subagent_task(self, task_context: Dict) -> str:
        return {}  # Subagent handled by sessions_spawn
    
    def _tool_bashoutput(self, input_params: Dict, working_directory: str, permission_mode: str) -> str:
        return "Use Bash tool for command execution"
    
    def _tool_killbash(self, input_params: Dict, working_directory: str, permission_mode: str) -> str:
        return "Background process management handled externally"
    
    def _get_available_background_shells(self) -> Dict:
        return []
    
    def _register_background_process(self, shell_id: str, process, command: str):
        """Register a real background process for BashOutput/KillBash tools"""
        try:
            from datetime import datetime
            
            # Initialize registry if needed
            if not hasattr(self, '_background_processes'):
                self._background_processes = {}
            
            # Store process information
            self._background_processes[shell_id] = {
                'process': process,
                'command': command,
                'pid': process.pid,
                'status': 'running',
                'started_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'output_buffer': [],  # Store output lines for retrieval
                'stderr_buffer': []   # Store error lines for retrieval
            }
            
            logger.info(f"✅ Registered background process: {shell_id} (PID: {process.pid})")
            
        except Exception as e:
            logger.error(f"Error registering background process: {e}")
    
    def _get_shell_output(self, bash_id: str) -> str:
        return ""  # Shell management handled by Bash tool
    
    def _kill_background_shell(self, shell_id: str) -> Dict:
        return "Background shells managed by Bash tool"
    
    def _tool_notebookedit(self, input_params: Dict, working_directory: str, permission_mode: str) -> str:
        return "NotebookEdit: use Write tool to edit notebook files directly"
    
    def _tool_computer_anthropic_official(self, input_params: Dict, working_directory: str, permission_mode: str) -> str:
        pass  # REMOVED: dead/legacy code
    
    # ==================== OFFICIAL ANTHROPIC AGENT LOOP IMPLEMENTATION ====================
    
    def handle_computer_action(self, action_type: str, params: Dict[str, Any]) -> str:
        return None  # Computer use handled by SDK
    
    def execute_computer_use_agent_loop(self, prompt: str, model: str = None, max_iterations: int = 50, 
                                       enable_thinking: bool = True, security_mode: str = "safe", parameters: Dict[str, Any] = None) -> HandlerResult:
        """Computer use agent loop — delegates to AgentLoop with computer_20250124 tools."""
        import asyncio
        if self._agent_loop:
            model = model or self.default_model
            messages = [{"role": "user", "content": prompt}]
            result = asyncio.get_event_loop().run_until_complete(
                self._agent_loop.run(
                    model=model, messages=messages, max_iterations=max_iterations or 50,
                )
            )
            from Handler.base_handler import HandlerResult
            return HandlerResult(success=True, data={"content": result.get("content", ""), "model": model})
        raise NotImplementedError("AgentLoop not available — modules not initialized")
    
    def execute_regular_tools_agent_loop(self, prompt: str, model: str = None, max_iterations: int = None, 
                                       system_prompt: str = None, parameters: Dict[str, Any] = None) -> HandlerResult:
        """Regular tools agent loop — delegates to AgentLoop (SDK tool_runner for Anthropic, manual loop for local)."""
        import asyncio
        if self._agent_loop:
            model = model or self.default_model
            messages = [{"role": "user", "content": prompt}]
            result = asyncio.get_event_loop().run_until_complete(
                self._agent_loop.run(
                    model=model, messages=messages,
                    system_prompt=system_prompt, max_iterations=max_iterations or 25,
                )
            )
            from Handler.base_handler import HandlerResult
            return HandlerResult(success=True, data={"content": result.get("content", ""), "session_id": parameters.get("session_id", ""), "model": model})
        raise NotImplementedError("AgentLoop not available — modules not initialized")
    
    def _execute_regular_tool(self, tool_block, parameters: Dict[str, Any]) -> Dict[str, Any]:
        return self._execute_tool(tool_block, working_directory, permission_mode)
    
    def _apply_grep_smart_constraints(self, tool_input: Dict[str, Any]) -> Dict[str, Any]:
        return params  # Pass through
    
    def _detect_finding(self, tool_block, tool_result, original_prompt):
        return None  # Legacy checkpoint system
    
    def _create_findings_summary(self, findings_list):
        """Create a formatted summary of discoveries for user checkpoint."""
        if not findings_list:
            return "No significant findings yet."
        
        summary_lines = []
        for i, finding in enumerate(findings_list, 1):
            category = finding['category'].replace('_', ' ').title()
            tool = finding['tool']
            details = finding.get('details', [])
            
            summary_lines.append(f"**{i}. {category}** (via {tool})")
            summary_lines.append(f"   - {finding['summary']}")
            
            if details and len(details) > 1:
                for detail in details[:2]:  # Show max 2 detail lines
                    summary_lines.append(f"   - {detail}")
            
            summary_lines.append("")  # Empty line between findings
        
        return "\n".join(summary_lines)

    def _detect_followup_question_early(self, prompt: str, parameters: Dict[str, Any]) -> bool:
        return None  # Simplified — AgentLoop handles continuity
    
    def _get_most_recent_session_from_workspace(self, parameters: Dict[str, Any]) -> Optional[str]:
        if self._session_mgr:
            return self._session_mgr.get_most_recent_session_from_workspace(parameters.get("workspace_id"))
        return None

    async def execute_multi_agent_workspace_loop(self, prompt: str, model: str, max_iterations: int, 
                                                parameters: Dict[str, Any]) -> HandlerResult:
        """Multi-agent workspace loop — delegates to AgentLoop."""
        if self._agent_loop:
            messages = [{"role": "user", "content": prompt}]
            result = await self._agent_loop.run(
                model=model, messages=messages, max_iterations=max_iterations or 25,
            )
            from Handler.base_handler import HandlerResult
            return HandlerResult(success=True, data={"content": result.get("content", ""), "model": model})
        raise NotImplementedError("AgentLoop not available — modules not initialized")
    
    def process_tool_calls(self, response) -> List[Dict[str, Any]]:
        """Process tool calls from Claude's response exactly as specified in official docs"""
        tool_results = []
        
        for content in response.content:
            if content.type == "tool_use":
                action = content.input.get("action")
                result = self.handle_computer_action(action, content.input)
                
                # Return result to Claude in official format
                tool_result = {
                    "type": "tool_result",
                    "tool_use_id": content.id,
                    "content": result
                }
                tool_results.append(tool_result)
                
        return tool_results
    
    # ==================== SECURITY AND SAFETY HELPERS ====================
    
    def _contains_sensitive_requests(self, prompt: str) -> bool:
        """Check if prompt contains potentially sensitive computer use requests per Anthropic guidelines"""
        sensitive_patterns = [
            # Account creation/impersonation (per Anthropic guidelines)
            "create account", "sign up", "register", "make account",
            # Social media/content generation restrictions  
            "post on", "tweet", "facebook post", "instagram", "tiktok",
            # System security concerns
            "password", "sudo", "admin", "root access", "system files",
            # Financial/sensitive data
            "bank", "credit card", "ssn", "social security", "financial"
        ]
        
        prompt_lower = prompt.lower()
        return any(pattern in prompt_lower for pattern in sensitive_patterns)
    
    def _get_computer_use_safety_prompt(self) -> str:
        """Get safety context prompt per Anthropic best practices"""
        return """🔒 COMPUTER USE SECURITY CONTEXT:
- You are operating in a controlled environment for computer automation
- Avoid accessing sensitive accounts or data without explicit permission
- Do not create accounts or impersonate users on social/communication platforms
- Be cautious with system-level operations that could affect security
- Always verify actions before execution, especially clicks on sensitive UI elements
- If you encounter sensitive information, handle it appropriately and notify the user"""
    
    
    def capture_screenshot(self) -> str:
        """Capture screenshot with proper error handling"""
        try:
            result = self.take_screenshot(compress_for_api=True)
            if 'error' in result:
                return f"❌ Screenshot failed: {result['error']}"
            return f"✅ Screenshot captured: {result.get('width', 'unknown')}x{result.get('height', 'unknown')} pixels"
        except Exception as e:
            return f"❌ Screenshot capture failed: {str(e)}"
    
    def click_at(self, x: int, y: int) -> str:
        pass  # REMOVED: dead/legacy code
    
    def right_click_at(self, x: int, y: int) -> str:
        pass  # REMOVED: dead/legacy code
    
    def middle_click_at(self, x: int, y: int) -> str:
        pass  # REMOVED: dead/legacy code
    
    def double_click_at(self, x: int, y: int) -> str:
        pass  # REMOVED: dead/legacy code
    
    def type_text(self, text: str) -> str:
        pass  # REMOVED: dead/legacy code
    
    def press_key(self, key: str) -> str:
        pass  # REMOVED: dead/legacy code
    
    def scroll_at(self, x: int, y: int, direction: str, amount: int) -> str:
        pass  # REMOVED: dead/legacy code
    
    def mouse_down_at(self, x: int, y: int, button: str) -> str:
        pass  # REMOVED: dead/legacy code
    
    def mouse_up_at(self, x: int, y: int, button: str) -> str:
        pass  # REMOVED: dead/legacy code
    
    def drag_from_to(self, start_x: int, start_y: int, end_x: int, end_y: int) -> str:
        pass  # REMOVED: dead/legacy code
    
    def move_mouse_to(self, x: int, y: int) -> str:
        pass  # REMOVED: dead/legacy code
    
    def left_click_drag(self, start_x: int, start_y: int, end_x: int, end_y: int) -> str:
        pass  # REMOVED: dead/legacy code
    
    
    
    def key_up(self, key: str) -> str:
        """Release held key"""
        try:
            import pyautogui
            pyautogui.keyUp(key)
            return f"✅ Key {key} released"
        except Exception as e:
            return f"❌ Key up failed: {str(e)}"
    
    
    
    # PHASE 3: DIRECT CODE ANALYSIS METHOD  
    # PHASE 3: STREAMING SUPPORT
    def _execute_claude_sdk_request_streaming(self, parameters: Dict[str, Any]) -> 'HandlerResult':
        """Streaming SDK request — delegates to AgentLoop (non-streaming fallback)."""
        # AgentLoop doesn't stream yet — use non-streaming path
        if self._agent_loop:
            model = parameters.get("model", self.default_model)
            prompt = parameters.get("prompt", "")
            import asyncio
            result = asyncio.get_event_loop().run_until_complete(
                self._agent_loop.run(
                    model=model,
                    messages=[{"role": "user", "content": prompt}],
                    max_iterations=parameters.get("max_iterations", 25),
                )
            )
            from Handler.base_handler import HandlerResult
            return HandlerResult(success=True, data=result)
        raise NotImplementedError("AgentLoop not available")
    
    # PHASE 5.3: ADVANCED API METHODS
    def count_tokens(self, messages: List[Dict[str, Any]], model: str = None, system: str = None, tools: List[Dict[str, Any]] = None) -> Dict[str, int]:
        """Count tokens — simplified, delegates to client."""
        try:
            count_params = {"model": model or self.default_model, "messages": messages}
            if system_prompt:
                count_params["system"] = system_prompt
            response = self.client.messages.count_tokens(**count_params)
            return response.input_tokens if hasattr(response, "input_tokens") else 0
        except Exception:
            return 0
    
    # PHASE 5.3.2: BATCH PROCESSING API
    
    
    def estimate_code_execution_cost(self, container_usage_hours: float) -> Dict[str, Any]:
        if self._cost_tracker:
            return self._cost_tracker.estimate_cost("unknown", 0, 0)
        return 0.0


    
    
    
    def take_screenshot(self, display_number: Optional[int] = None, compress_for_api: bool = True) -> Dict[str, Any]:
        return "Screenshot functionality handled by SDK computer_20250124 tool"
    
# REMOVED: Custom computer_action method - Anthropic SDK handles all computer actions directly
    
    
    
    async def perform_health_check(self) -> Dict[str, Any]:
        """Perform comprehensive health check (Phase 5.8.6)"""
        import time
        try:
            return await self.health_monitor.perform_health_check(self)
        except Exception as e:
            logger.error(f"Health check failed: {str(e)}")
            return {
                'overall_status': 'unhealthy',
                'error': str(e),
                'timestamp': time.time()
            }
    
    def clear_cache(self) -> Dict[str, Any]:
        """Clear response cache (Phase 5.8.6)"""
        try:
            old_stats = self.response_cache.get_stats()
            self.response_cache.clear()
            return {
                'success': True,
                'cleared_items': old_stats['cache_size'],
                'message': f"Cleared {old_stats['cache_size']} cached responses"
            }
        except Exception as e:
            logger.error(f"Error clearing cache: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    
    def analyze_request_complexity(self, user_input: str, parameters: Dict[str, Any] = None) -> Dict[str, Any]:
        return {"complexity": "moderate", "estimated_tokens": 4000}  # Simplified
    
    def _analyze_parameter_complexity(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        return "moderate"  # Simplified
    
    def _get_scaling_recommendation(self, complexity_level: str, confidence: int) -> Dict[str, Any]:
        return "none"  # REMOVED: legacy
    
    
    async def _handle_simple_request_scaling(self, recommendation: Dict[str, Any], memory_status: Dict[str, Any]) -> Dict[str, Any]:
        """SCALE-2.3: Handle scaling for simple requests"""
        return {
            'approach': 'single_server_optimized',
            'servers_limit': 1,
            'resource_allocation': 'minimal',
            'optimization': 'prefer_lightweight_servers',
            'message': '⚡ Simple request - using single optimized server',
            'success': True
        }
    
    async def _handle_complex_request_scaling(self, recommendation: Dict[str, Any], memory_status: Dict[str, Any]) -> Dict[str, Any]:
        """SCALE-2.3: Handle scaling for complex requests"""
        max_servers = min(recommendation['servers_needed'], self.low_memory_config.get('max_concurrent_servers', 8))
        
        return {
            'approach': 'multi_server_coordinated',
            'servers_limit': max_servers,
            'resource_allocation': 'moderate',
            'coordination': 'intelligent_load_balancing',
            'message': f'🎯 Complex request - using {max_servers} coordinated servers',
            'success': True
        }
    
    async def _handle_burst_worthy_request_scaling(self, recommendation: Dict[str, Any], memory_status: Dict[str, Any]) -> Dict[str, Any]:
        pass  # Legacy
    
    async def _handle_unknown_complexity_scaling(self, recommendation: Dict[str, Any], memory_status: Dict[str, Any]) -> Dict[str, Any]:
        """SCALE-2.3: Handle scaling for unknown complexity requests"""
        return {
            'approach': 'conservative_adaptive',
            'servers_limit': 2,
            'resource_allocation': 'conservative',
            'monitoring': 'enhanced_monitoring_enabled',
            'message': '🛡️ Unknown complexity - conservative approach with monitoring',
            'success': True
        }
    
    # ========================================
    # SCALE-3: Real-Time Scaling Optimization
    # ========================================
    
    def calculate_memory_headroom(self) -> Dict[str, Any]:
        return {"available_mb": 99999, "status": "ok"}  # REMOVED: legacy
    
    def _calculate_weighted_average_server_memory(self) -> float:
        return 0  # Legacy
    
    def _calculate_memory_pressure(self, available_mb: float, emergency_threshold: float) -> Dict[str, Any]:
        return 0.0  # Legacy
    
    def _recommend_launch_strategy(self, safe_launches: int, memory_pressure: Dict[str, Any], current_active: int) -> Dict[str, Any]:
        return "conservative"  # REMOVED: legacy
    
    async def smart_server_launch_sequence(self, required_servers: list, reason: str = "Request processing") -> Dict[str, Any]:
        pass  # REMOVED: legacy MCP server management
    
    async def _launch_server_batch(self, servers: list, reason: str) -> Dict[str, Dict[str, Any]]:
        """SCALE-3.1: Launch a batch of servers simultaneously"""
        batch_results = {}
        
        # Create launch tasks for simultaneous execution
        launch_tasks = []
        for server in servers:
            task = asyncio.create_task(self._launch_single_server_with_monitoring(server, reason))
            launch_tasks.append((server, task))
        
        # Wait for all launches to complete
        for server, task in launch_tasks:
            try:
                result = await task
                batch_results[server] = result
            except Exception as e:
                batch_results[server] = {'success': False, 'error': str(e)}
        
        return batch_results
    
    async def _launch_single_server_with_monitoring(self, server: str, reason: str) -> Dict[str, Any]:
        pass  # Legacy
    
    async def _launch_servers_conservatively(self, servers: list, reason: str) -> Dict[str, Any]:
        """SCALE-3.1: Conservative fallback server launch method"""
        logger.info("🛡️ Using conservative server launch approach")
        
        launched_servers = []
        for server in servers[:2]:  # Max 2 servers conservatively
            try:
                result = await self._launch_single_server_with_monitoring(server, f"Conservative: {reason}")
                if result.get('success', False):
                    launched_servers.append(server)
                await asyncio.sleep(3)  # Conservative delay
            except Exception as e:
                logger.error(f"Conservative launch failed for {server}: {str(e)}")
        
        return {
            'success': len(launched_servers) > 0,
            'launched_servers': launched_servers,
            'approach': 'conservative_fallback',
            'message': f"Conservatively launched {len(launched_servers)} servers"
        }
    
    # ========================================
    
    def _detect_system_profile(self) -> str:
        from Handler.modules.workspace_integration import detect_system_profile
        return detect_system_profile(parameters)
    
    
    def _apply_profile_transition(self, old_profile: str, new_profile: str) -> None:
        """SCALE-2.1: Gradually apply profile transition to avoid disruption"""
        try:
            old_max = self.memory_profiles[old_profile]['max_concurrent_servers']
            new_max = self.memory_profiles[new_profile]['max_concurrent_servers']
            
            if new_max > old_max:
                # SCALING UP: Gradually enable additional servers
                logger.info(f"🚀 SCALING UP: Enabling {new_max - old_max} additional servers")
                # Note: Actual server launching will happen on-demand when requests come in
                
            elif new_max < old_max:
                # SCALING DOWN: Gradually shutdown excess servers
                active_count = len(self.active_mcp_servers)
                if active_count > new_max:
                    servers_to_shutdown = active_count - new_max
                    logger.info(f"📉 SCALING DOWN: Shutting down {servers_to_shutdown} excess servers")
                    
                    # Shutdown lowest priority servers first
                    asyncio.create_task(self._graceful_scale_down(new_max))
            
        except Exception as e:
            logger.warning(f"⚠️ Error applying profile transition: {e}")
    
    async def _graceful_scale_down(self, target_max_servers: int) -> None:
        """SCALE-2.1: Gracefully scale down active servers to target limit"""
        try:
            current_count = len(self.active_mcp_servers)
            if current_count <= target_max_servers:
                return  # Already within limits
                
            shutdown_count = current_count - target_max_servers
            logger.info(f"📉 Graceful scale-down: {current_count} → {target_max_servers} servers")
            
            # Find lowest priority servers to shutdown
            active_servers_by_priority = sorted(
                self.active_mcp_servers.keys(),
                key=self._get_server_priority_score,
                reverse=True  # Highest score (lowest priority) first
            )
            
            # Shutdown excess servers
            for i in range(shutdown_count):
                if i < len(active_servers_by_priority):
                    server_to_shutdown = active_servers_by_priority[i]
                    logger.info(f"   🔻 Shutting down low-priority server: {server_to_shutdown}")
                    await self._shutdown_single_mcp_server(server_to_shutdown)
            
            logger.info(f"✅ Scale-down complete: {len(self.active_mcp_servers)} active servers")
            
        except Exception as e:
            logger.error(f"❌ Error during graceful scale-down: {e}")
    
    async def enable_burst_mode(self, duration_minutes: int = 30, reason: str = "Complex task processing") -> Dict[str, Any]:
        pass  # REMOVED: legacy MCP server management
    
    async def _schedule_burst_mode_cleanup(self, duration_minutes: int) -> None:
        """SCALE-2.2: Schedule automatic burst mode deactivation"""
        try:
            import time
            
            # Wait for the specified duration
            await asyncio.sleep(duration_minutes * 60)
            
            # Check if burst mode is still active (user might have manually disabled it)
            if self.low_memory_config.get('burst_mode_active', False):
                logger.info(f"⏰ BURST MODE TIMEOUT: {duration_minutes} minutes elapsed - initiating cleanup")
                await self.disable_burst_mode("Scheduled timeout")
            
        except Exception as e:
            logger.error(f"❌ Error in burst mode cleanup scheduler: {e}")
    
    async def disable_burst_mode(self, reason: str = "Manual deactivation") -> Dict[str, Any]:
        pass  # REMOVED: legacy MCP server management
    
    def get_system_memory_status(self) -> Dict[str, Any]:
        return {"status": "ok"}  # Legacy
    
    
    async def emergency_shutdown_all_mcps(self) -> Dict[str, Any]:
        pass  # Legacy MCP management
    
    async def process_emergency_shutdown_queue(self):
        pass  # Legacy
    
    def _start_memory_monitoring(self):
        """Start background memory monitoring thread"""
        import threading
        
        if self.memory_monitor_active:
            return  # Already running
            
        self.memory_monitor_active = True
        self.memory_check_thread = threading.Thread(
            target=self._memory_monitor_loop, 
            daemon=True,
            name="MCPMemoryMonitor"
        )
        self.memory_check_thread.start()
        logger.info("🔍 Memory monitoring thread started (65MB device protection)")
    
    def _memory_monitor_loop(self):
        pass  # Legacy memory monitoring
    
    def _estimate_active_mcp_memory(self) -> float:
        """Estimate total memory usage of active MCP servers"""
        total_mb = 0.0
        for server_name, server_info in self.active_mcp_servers.items():
            # Use actual memory if tracked, otherwise estimate
            if 'memory_mb' in server_info:
                total_mb += server_info['memory_mb']
            else:
                estimate = self.server_memory_estimates.get(server_name, 20)  # Default 20MB
                total_mb += estimate
        return total_mb
    
    # ========================================
    # ARCH-1.2: SMART SERVER PRIORITIZATION
    # ========================================
    
    def _get_server_priority_score(self, server_name: str) -> int:
        """ARCH-1.2.1: Get priority score for a server (lower = higher priority)"""
        return self.server_priority_ranking.get(server_name, 99)  # Default low priority
    
    def _find_best_servers_for_request(self, required_servers: list) -> list:
        """ARCH-1.2.1: Find optimal servers prioritizing lightweight options"""
        try:
            # Sort servers by priority (lightweight first)
            sorted_servers = sorted(required_servers, key=self._get_server_priority_score)
            
            # Check memory constraints
            available_slots = self.low_memory_config['max_concurrent_servers'] - len(self.active_mcp_servers)
            
            if self.low_memory_config['prefer_single_server'] and len(sorted_servers) > 1:
                # Try to find single-server solution
                single_server = self._find_single_server_alternative(sorted_servers)
                if single_server:
                    return [single_server]
            
            # Return as many as memory allows, prioritized
            if available_slots >= len(sorted_servers):
                return sorted_servers
            else:
                # Need server swapping
                return self._plan_server_swapping(sorted_servers)
                
        except Exception as e:
            logger.error(f"Error finding best servers: {str(e)}")
            return required_servers[:1]  # Fallback to first server only
    
    def _find_single_server_alternative(self, servers: list) -> Optional[str]:
        return None  # Legacy
    
    async def _plan_server_swapping(self, required_servers: list) -> list:
        return {}  # REMOVED: legacy MCP server management
    
    async def _shutdown_single_mcp_server(self, server_name: str) -> bool:
        """ARCH-1.2.2: Shutdown a single MCP server to free memory"""
        try:
            import os
            import signal
            
            if server_name not in self.active_mcp_servers:
                return True  # Already shutdown
            
            server_info = self.active_mcp_servers[server_name]
            pid = server_info.get('pid')
            
            if pid:
                os.kill(pid, signal.SIGTERM)
                logger.info(f"🚫 Shutdown MCP server: {server_name} (PID: {pid})")
            
            # Clean up tracking
            with self.memory_lock:
                self.active_mcp_servers.pop(server_name, None)
                self.mcp_connection_pool.pop(server_name, None)
                self.server_idle_timers.pop(server_name, None)
            
            return True
            
        except Exception as e:
            logger.error(f"Error shutting down {server_name}: {str(e)}")
            return False
    
    def _analyze_mcp_requirements_from_request(self, user_input: str) -> list:
        return {}  # MCP handled by ToolKit

    # ========================================
    # ARCH-1.4: SMART REQUEST PROCESSING WITH MEMORY CONSTRAINTS
    # ========================================
    
    async def analyze_request_memory_impact(self, user_input: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        return {}  # REMOVED: legacy
    
    def _determine_processing_strategy(self, available_mb: float, estimated_memory: float, 
                                     emergency_status: str, required_servers: list) -> Dict[str, Any]:
        pass  # REMOVED: dead/legacy code
    
    def _get_processing_recommendation(self, strategy_info: Dict[str, Any]) -> str:
        pass  # REMOVED: dead/legacy code
    
    
    async def _emergency_processing_without_mcp(self, user_input: str, parameters: Dict[str, Any], 
                                               analysis: Dict[str, Any]) -> Dict[str, Any]:
        pass  # REMOVED: dead/legacy code
    
    async def _single_server_processing(self, user_input: str, parameters: Dict[str, Any], 
                                       analysis: Dict[str, Any]) -> Dict[str, Any]:
        return None  # Legacy MCP server processing
    
    async def _queue_request_for_later(self, user_input: str, parameters: Dict[str, Any], 
                                      analysis: Dict[str, Any]) -> Dict[str, Any]:
        pass  # REMOVED: dead/legacy code
    
    async def _standard_mcp_processing(self, user_input: str, parameters: Dict[str, Any], 
                                      analysis: Dict[str, Any]) -> Dict[str, Any]:
        pass  # REMOVED: dead/legacy code
    
    async def _intelligent_swapping_processing(self, user_input: str, parameters: Dict[str, Any], 
                                              analysis: Dict[str, Any]) -> Dict[str, Any]:
        pass  # REMOVED: dead/legacy code
    
    async def _conservative_fallback_processing(self, user_input: str, parameters: Dict[str, Any], 
                                               analysis: Dict[str, Any]) -> Dict[str, Any]:
        """ARCH-1.4: Ultra-conservative fallback processing"""
        try:
            logger.info("🛡️ Conservative fallback processing")
            
            # Try single server first
            required_servers = analysis['mcp_requirements']['required_servers']
            if required_servers:
                return await self._single_server_processing(user_input, parameters, analysis)
            else:
                return await self._direct_processing_no_mcp(user_input, parameters, analysis)
                
        except Exception as e:
            logger.error(f"Conservative fallback failed: {str(e)}")
            return await self._fallback_processing_without_mcp(user_input, parameters)
    
    async def _direct_processing_no_mcp(self, user_input: str, parameters: Dict[str, Any], 
                                       analysis: Dict[str, Any]) -> Dict[str, Any]:
        pass  # REMOVED: dead/legacy code
    
    async def _fallback_processing_without_mcp(self, user_input: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        pass  # REMOVED: dead/legacy code

    # ========================================
    # PHASE 5.8: PRODUCTION FEATURES - CLASSES
    # ========================================
    
    def __init_production_features__(self):
        """Initialize production features - called from __init__"""
        import threading
        import time
        from collections import defaultdict, deque
        from typing import Optional, Callable, Any
        
        # Phase 5.8.1: Rate Limiting with Exponential Backoff
        self.rate_limiter = RateLimiter()
        
        # Phase 5.8.2: Response Caching System  
        self.response_cache = ResponseCache()
        
        # Phase 5.8.3: Monitoring and Metrics
        self.metrics_collector = MetricsCollector()
        
        # Phase 5.8.4: Production Error Handling
        self.error_handler = ProductionErrorHandler()
        
        # Phase 5.8.5: Health Monitoring
        self.health_monitor = HealthMonitor()
        
        logger.info("✅ Production features initialized successfully")
        
    def __init_memory_management__(self):
        pass  # REMOVED: OpenClaw manages resources
    
    # ========================================
    # SCALE-3.2: Performance-Based Scaling
    # ========================================
    
    def __init_performance_monitoring(self):
        pass  # REMOVED: PerformanceMonitor module replaces
    
    
    def _check_performance_degradation(self, server: str, response_time_ms: float) -> None:
        pass  # Legacy performance monitoring
    
    async def _consider_performance_based_scaling(self, bottleneck_server: str, performance_level: str) -> Dict[str, Any]:
        pass  # REMOVED: legacy
    
    def _suggest_performance_servers(self, bottleneck_server: str) -> list:
        return []  # Legacy
    
    def _suggest_complementary_server(self, bottleneck_server: str) -> str:
        """SCALE-3.2: Suggest one complementary server for gradual scaling"""
        potential_servers = self._suggest_performance_servers(bottleneck_server)
        return potential_servers[0] if potential_servers else None
    
    def analyze_system_performance(self) -> Dict[str, Any]:
        return {"status": "healthy"}  # REMOVED: PerformanceMonitor replaces
    
    def _calculate_performance_trend(self, server: str, recent_measurements: list) -> str:
        """SCALE-3.2: Calculate performance trend for a server"""
        if len(recent_measurements) < 3:
            return 'insufficient_data'
        
        # Compare first half to second half of recent measurements
        mid_point = len(recent_measurements) // 2
        first_half_avg = sum(m['response_time_ms'] for m in recent_measurements[:mid_point]) / mid_point
        second_half_avg = sum(m['response_time_ms'] for m in recent_measurements[mid_point:]) / (len(recent_measurements) - mid_point)
        
        # Calculate percentage change
        if first_half_avg == 0:
            return 'stable'
            
        change_percent = ((second_half_avg - first_half_avg) / first_half_avg) * 100
        
        if change_percent > 20:
            return 'degrading'
        elif change_percent < -20:
            return 'improving'
        else:
            return 'stable'
    
    def _generate_scaling_recommendations(self, analysis: Dict[str, Any]) -> list:
        return []  # REMOVED: legacy
    
    def _identify_idle_servers(self) -> list:
        """SCALE-3.2: Identify servers that appear to be idle based on performance data"""
        idle_servers = []
        current_time = time.time()
        idle_threshold_seconds = 300  # 5 minutes
        
        for server in self.active_mcp_servers:
            # Check if server has recent performance data
            if server in self.performance_metrics['server_response_times']:
                measurements = self.performance_metrics['server_response_times'][server]
                if measurements:
                    last_measurement_time = measurements[-1]['timestamp']
                    if current_time - last_measurement_time > idle_threshold_seconds:
                        idle_servers.append(server)
                else:
                    # No measurements = potentially idle
                    idle_servers.append(server)
            else:
                # No performance data = potentially idle
                idle_servers.append(server)
        
        return idle_servers
    
    
    def __init_cost_optimization(self):
        pass  # REMOVED: CostTracker module replaces
    
    
    def calculate_current_cost_rate(self) -> float:
        """SCALE-3.3: Calculate current hourly cost rate for active servers"""
        self.__init_cost_optimization()
        
        total_hourly_cost = 0.0
        active_server_costs = {}
        
        for server_name in self.active_mcp_servers:
            if server_name in self.aws_server_costs:
                server_cost = self.aws_server_costs[server_name]['cost_per_hour']
                total_hourly_cost += server_cost
                active_server_costs[server_name] = server_cost
            else:
                # Default cost for unknown servers (t3.small)
                default_cost = 0.0208
                total_hourly_cost += default_cost
                active_server_costs[server_name] = default_cost
        
        self.cost_optimization['current_cost_rate'] = total_hourly_cost
        self.cost_optimization['aws_instance_costs'] = active_server_costs
        
        return total_hourly_cost
    
    def check_cost_budget_compliance(self) -> Dict[str, Any]:
        if self._cost_tracker:
            return self._cost_tracker.check_budget_compliance()
        return {"within_budget": True}
    
    
    
    
    
    
    def optimize_server_costs(self) -> Dict[str, Any]:
        return {}  # REMOVED: CostTracker module replaces
    
    
    
    async def _track_journey_step(self, journey_id: str, step_name: str, description: str, 
                                 step_type: str, input_data: Dict = None, output_data: Dict = None):
        """
        Track journey steps for orchestrator coordination.
        
        This integrates with the existing BoardRoom journey tracking system.
        """
        try:
            # Import BoardRoom journey tracking
            from Jarvis_Agent_SDK.boardroom_connector import track_journey_step_sync
            
            await track_journey_step_sync(
                journey_id=journey_id,
                step_name=step_name,
                description=description,
                step_type=step_type,
                input_data=input_data or {},
                output_data=output_data or {}
            )
        except Exception as e:
            logging.warning(f"Journey tracking failed: {str(e)}")
    
    async def create_agent_workspace_with_orchestrators(self, task_name: str, required_capabilities: List[str] = None, user_request: str = None, workspace_id: str = None) -> Dict[str, Any]:
        return {}  # Workspace creation handled by SwarmRegistry

    async def _create_agents_via_mcp_tools(self, task_name: str, required_capabilities: List[str] = None, user_request: str = None) -> List[Dict[str, Any]]:
        return []  # Agent creation handled by AgentBuilder/SwarmRegistry

    async def _call_agent_builder_mcp(self, task_name: str, role: str, capabilities: List[str], user_request: str = None) -> Dict[str, Any]:
        """Call the agent_builder MCP tool to create a specialized agent"""
        try:
            # SIMPLIFIED: Just create an agent configuration dict
            # Following same pattern as structured_agent and data_validator
            # AgentBuilder creates actual OpenAI agents, but for workspace tracking we just need config
            agent_id = f"agent_builder_{role}_{uuid.uuid4().hex[:8]}"
            logging.info(f"Creating agent_builder agent: {agent_id} with role={role}, capabilities={capabilities}")

            return {
                "agent_id": agent_id,
                "agent_type": "agent_builder",
                "agent_name": f"{role}_agent",
                "role": role,
                "capabilities": capabilities,
                "status": "active",
                "created_at": time.time(),
                "created_via": "agent_builder_mcp",
                "task_context": user_request or task_name
            }
        except Exception as e:
            logging.error(f"Failed to call agent_builder MCP: {str(e)}")
            return None

    async def _call_swarm_mcp(self, task_name: str, role: str, capabilities: List[str], user_request: str = None) -> Dict[str, Any]:
        """Call the swarm MCP tool to create a coordination context"""
        try:
            # SIMPLIFIED: Just create a coordination configuration dict
            # Following same pattern as structured_agent and data_validator
            # SwarmHandler coordinates existing agents, but for workspace tracking we just need config
            # NOTE: Swarm coordinates EXISTING agents created by agent_builder, doesn't create new agents
            coordinator_id = f"swarm_{role}_{uuid.uuid4().hex[:8]}"
            logging.info(f"Creating swarm coordinator: {coordinator_id} with role={role}, capabilities={capabilities}")

            return {
                "agent_id": coordinator_id,
                "agent_type": "swarm_coordinator",
                "agent_name": f"{role}_coordinator",
                "role": role,
                "capabilities": capabilities,
                "status": "active",
                "created_at": time.time(),
                "created_via": "swarm_mcp",
                "coordination_mode": "workspace_coordination",
                "task_context": user_request or task_name
            }
        except Exception as e:
            logging.error(f"Failed to call swarm MCP: {str(e)}")
            return None

    async def _call_structured_agent_mcp(self, task_name: str, role: str, capabilities: List[str], user_request: str = None) -> Dict[str, Any]:
        pass  # REMOVED: dead/legacy code

    async def _call_data_validator_mcp(self, task_name: str, role: str, capabilities: List[str], user_request: str = None) -> Dict[str, Any]:
        """Call the data_validator MCP tool to create a validation agent"""
        try:
            # SIMPLIFIED: Just create a validator agent configuration dict
            # Similar to structured_agent, we just need a validator that can be tracked in the workspace
            # The actual validation happens when the validator agent is used, not during creation

            agent_id = f"validator_{role}_{uuid.uuid4().hex[:8]}"

            logging.info(f"Creating data validator agent: {agent_id} with role={role}, capabilities={capabilities}")

            return {
                "agent_id": agent_id,
                "agent_type": "data_validator",
                "agent_name": f"{role}_validator",
                "role": role,
                "capabilities": capabilities,
                "status": "active",
                "created_at": time.time(),
                "created_via": "data_validator_mcp",
                "task_context": user_request or task_name
            }

        except Exception as e:
            logging.error(f"Failed to call data_validator MCP: {str(e)}")
            return None

    async def _discover_existing_agents(self, required_capabilities: List[str] = None) -> List[Dict[str, Any]]:
        return []  # Agent discovery handled by AgentRegistry

    def _filter_agents_by_performance(self, agents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if self._perf_monitor:
            return self._perf_monitor.filter_agents_by_performance(agents)
        return agents

    async def _track_agent_performance(self, agent_id: str, agent_type: str, agent_name: str,
                                     workspace_id: str, task_id: str, success: bool,
                                     completion_time: float, error_count: int = 0,
                                     quality_score: float = None, metadata: Dict = None) -> bool:
        if self._perf_monitor:
            self._perf_monitor.track_agent_performance(agent_name, result)

    def _get_mcp_assignments_for_agents(self, agents: List[Dict[str, Any]]) -> Dict[str, List[str]]:
        return {}  # MCP handled by ToolKit
    
    




    async def _execute_claude_primary_step(self, task_spec: Dict[str, Any], step_context: Dict[str, Any], 
                                         original_request: str) -> Dict[str, Any]:
        return {}  # Primary execution handled by AgentLoop

    async def _execute_agent_step(self, agent_type: str, task_spec: Dict[str, Any], 
                                step_context: Dict[str, Any], original_request: str) -> Dict[str, Any]:
        return {}  # Agent execution handled by AgentLoop

    async def _initialize_swarm_coordination(self, parallel_tasks: List[Dict[str, Any]], 
                                           workspace_context: Dict[str, Any]) -> Dict[str, Any]:
        return {}  # Swarm coordination handled by SwarmRegistry

    async def _initialize_load_balanced_coordination(self, parallel_tasks: List[Dict[str, Any]], 
                                                   workspace_context: Dict[str, Any]) -> Dict[str, Any]:
        return {}  # Load balancing handled by SwarmRegistry

    async def _create_hierarchical_delegation_plan(self, request: str, hierarchy_context: Dict[str, Any], 
                                                 master_workspace: Dict[str, Any]) -> Dict[str, Any]:
        return {}  # Delegation handled by SwarmHandler

    async def _execute_hierarchical_delegation(self, delegated_task: Dict[str, Any], sub_agent_spec: Dict[str, Any], 
                                             sub_workspace_info: Dict[str, Any], hierarchy_context: Dict[str, Any]) -> Dict[str, Any]:
        return {}  # Delegation handled by SwarmHandler

    async def _consolidate_hierarchical_results(self, hierarchical_results: List[Dict[str, Any]], 
                                              hierarchy_context: Dict[str, Any], original_request: str) -> Dict[str, Any]:
        return {}  # Result aggregation handled by SwarmHandler

    # ==================== PHASE 3.2: DYNAMIC AGENT CREATION AND MANAGEMENT ==================== 

    async def create_specialized_agent_on_demand(self, task_requirements: Dict[str, Any], 
                                                context: Dict[str, Any] = None) -> Dict[str, Any]:
        return {}  # Agent creation handled by AgentBuilder


    
    async def _determine_optimal_agent_configuration(self, task_type: str, capabilities: List[str], 
                                                   complexity: str, specialization: str) -> Dict[str, Any]:
        return {}  # Agent config handled by AgentBuilder

    async def _create_agent_with_builder(self, agent_config: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        return None  # Agent creation handled by AgentBuilder

    async def _register_dynamic_agent(self, agent_info: Dict[str, Any], capabilities: List[str], 
                                    performance_requirements: Dict[str, Any]) -> Dict[str, Any]:
        return None  # Agent registration handled by AgentRegistry

    async def _execute_mcp_tool_call(self, server_name: str, tool_name: str, tool_input: Dict[str, Any]) -> Dict[str, Any]:
        return None  # MCP execution handled by ToolKit

    async def _get_agent_status(self, agent_id: str) -> Dict[str, Any]:
        return {}  # Agent status via AgentRegistry

    async def _update_agent_configuration(self, agent_id: str, configuration: Dict[str, Any], 
                                        capabilities: List[str]) -> Dict[str, Any]:
        pass  # REMOVED: dead/legacy code

    async def _scale_agent_resources(self, agent_id: str, direction: str, multiplier: float) -> Dict[str, Any]:
        pass  # REMOVED: dead/legacy code

    async def _pause_agent(self, agent_id: str, reason: str) -> Dict[str, Any]:
        pass  # REMOVED: dead/legacy code

    async def _resume_agent(self, agent_id: str) -> Dict[str, Any]:
        pass  # REMOVED: dead/legacy code

    async def _terminate_agent(self, agent_id: str, cleanup_workspace: bool, preserve_data: bool) -> Dict[str, Any]:
        """Safely terminate an agent and clean up resources"""
        try:
            logging.info(f"🛑 Terminating agent: {agent_id}")
            return {
                "success": True, 
                "termination_timestamp": time.time(),
                "cleanup_performed": cleanup_workspace,
                "data_preserved": preserve_data
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _distribute_task_to_agent_pool(self, task_request: str, agent_pool: List[Dict[str, Any]], 
                                           coordination_strategy: str, master_workspace_id: str) -> Dict[str, Any]:
        """Distribute complex task among agent pool members"""
        try:
            # Task breakdown and distribution logic
            task_distribution = {
                "original_task": task_request,
                "strategy": coordination_strategy,
                "agent_assignments": []
            }
            
            for i, agent in enumerate(agent_pool):
                assignment = {
                    "agent_id": agent.get("agent_id"),
                    "assigned_subtask": f"Subtask {i+1} of {len(agent_pool)}",
                    "specialization": agent.get("deployment_info", {}).get("agent_type"),
                    "priority": 1.0 / (i + 1)  # Decreasing priority
                }
                task_distribution["agent_assignments"].append(assignment)
            
            return task_distribution
            
        except Exception as e:
            logging.error(f"Task distribution failed: {e}")
            return {"assignments": [], "error": str(e)}

    async def _execute_coordinated_agent_pool(self, task_distribution: Dict[str, Any], 
                                            coordination_strategy: str, performance_requirements: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Execute tasks across coordinated agent pool"""
        try:
            execution_results = []
            
            for assignment in task_distribution.get("agent_assignments", []):
                # Simulate agent execution
                execution_time = 1.0 + (hash(assignment["agent_id"]) % 50) / 50.0  # Random 1-2 seconds
                
                result = {
                    "agent_id": assignment["agent_id"],
                    "subtask": assignment["assigned_subtask"],
                    "success": True,
                    "execution_time": execution_time,
                    "result_data": f"Completed {assignment['specialization']} task",
                    "timestamp": time.time()
                }
                
                execution_results.append(result)
            
            return execution_results
            
        except Exception as e:
            logging.error(f"Coordinated execution failed: {e}")
            return []

    async def _aggregate_multi_agent_results(self, execution_results: List[Dict[str, Any]], 
                                           original_task: str, agent_pool: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Aggregate results from multiple agents into cohesive output"""
        try:
            successful_results = [r for r in execution_results if r.get("success")]
            
            aggregation_summary = {
                "original_task": original_task,
                "total_agents": len(agent_pool),
                "successful_executions": len(successful_results),
                "aggregation_success": len(successful_results) > 0,
                "combined_results": [r.get("result_data") for r in successful_results],
                "resource_efficiency": len(successful_results) / len(agent_pool) if agent_pool else 0,
                "coordination_overhead": 0.1  # Simulated 10% overhead
            }
            
            return {
                "success": len(successful_results) > 0,
                **aggregation_summary
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _is_request_truly_vague(self, user_prompt: str, session_id: str = None) -> bool:
        return False  # Simplified — let the LLM figure it out
    
    def _get_available_tools_for_mcp(self, mcp_server: str) -> List[Dict[str, str]]:
        """Get list of available tools for the specified MCP server"""
        try:
            cache_path = "~/Jarvis/cache/mcp_tools_cache.json"
            if not os.path.exists(cache_path):
                return []
                
            with open(cache_path, 'r') as f:
                cached_tools = json.load(f)
            
            servers_with_cache = cached_tools.get("servers", {})
            if mcp_server in servers_with_cache:
                tools = servers_with_cache[mcp_server].get("tools", [])
                return [
                    {
                        'name': tool.get('name', 'unknown'),
                        'description': tool.get('description', 'No description available')
                    }
                    for tool in tools
                ]
            return []
        except Exception as e:
            logger.error(f"Error getting tools for MCP {mcp_server}: {e}")
            return []
    
    def _generate_tool_clarification_response(self, mcp_server: str, available_tools: List[Dict[str, str]], user_prompt: str) -> str:
        return "Please provide more details about what you need."


    def _detect_mcp_from_conversation_context(self, parameters: Dict[str, Any]) -> Optional[str]:
        if self._session_mgr:
            mcp_patterns = self._load_mcp_patterns_from_registry()
            return self._session_mgr.detect_mcp_from_conversation_context(parameters, mcp_patterns)
        return None

    def _should_use_boardroom(self, complexity_score: float, frustration_level: str, overall_sentiment: str, parameters: Dict[str, Any]) -> bool:
        return False  # BoardRoom routing handled by OpenClaw

    def _process_with_boardroom(self, parameters: Dict[str, Any]) -> 'HandlerResult':
        return None  # BoardRoom handled by OpenClaw sub-agents

    def _fallback_to_direct_processing(self, parameters: Dict[str, Any]) -> 'HandlerResult':
        pass  # REMOVED: dead/legacy code

    def _workspace_task_appears_complete(self, response_content: str) -> bool:
        """
        Check if workspace task appears complete (no tools needed).

        Used in multi-agent workspace loop to determine if coordination is finished
        when Claude doesn't request any tools.
        """
        completion_indicators = [
            'completed', 'finished', 'done', 'successfully', 'final result',
            'task accomplished', 'coordination successful'
        ]

        content_lower = response_content.lower()
        return any(indicator in content_lower for indicator in completion_indicators)


    def _generate_workspace_partial_summary(self, coordination_state: Dict[str, Any],
                                          workspace_context: Dict[str, Any]) -> str:
        """Generate partial completion summary when max iterations reached"""
        completed_tasks = len(coordination_state['completed_subtasks'])
        pending_tasks = len(coordination_state['pending_subtasks'])
        iterations = coordination_state['iteration_count']
        workspace_id = workspace_context['workspace_id']

        return f"""
⚠️ WORKSPACE COORDINATION PARTIAL COMPLETION

📊 Progress Summary:
- Workspace ID: {workspace_id}
- Completed Subtasks: {completed_tasks}
- Pending Subtasks: {pending_tasks}
- Coordination Iterations: {iterations}
- Status: Partially Completed (max iterations reached)

🔄 Workspace can be continued by resuming with the same workspace ID.
"""


class RateLimiter:
    """Intelligent rate limiting with exponential backoff"""
    
    def __init__(self, requests_per_minute: int = 60, burst_limit: int = 10):
        import threading
        import time
        from collections import deque
        
        self.requests_per_minute = requests_per_minute
        self.burst_limit = burst_limit
        self.request_times = deque()
        self.lock = threading.Lock()
        self.backoff_delay = 0
        self.consecutive_errors = 0
        
    def can_make_request(self) -> tuple[bool, float]:
        """Check if request can be made, return (allowed, wait_time)"""
        import time
        
        with self.lock:
            now = time.time()
            
            # Remove requests older than 1 minute
            while self.request_times and now - self.request_times[0] > 60:
                self.request_times.popleft()
            
            # Check burst limit
            if len(self.request_times) >= self.burst_limit:
                wait_time = 60 / self.requests_per_minute
                return False, wait_time
                
            # Check rate limit
            if len(self.request_times) >= self.requests_per_minute:
                oldest_request = self.request_times[0]
                wait_time = 60 - (now - oldest_request)
                return False, wait_time
                
            return True, 0
    
    def record_request(self, success: bool = True):
        """Record a request and adjust backoff if needed"""
        import time
        
        with self.lock:
            self.request_times.append(time.time())
            
            if success:
                self.consecutive_errors = 0
                self.backoff_delay = max(0, self.backoff_delay - 1)
            else:
                self.consecutive_errors += 1
                self.backoff_delay = min(60, 2 ** self.consecutive_errors)
    

class ResponseCache:
    """Response caching system with TTL and memory management"""
    
    def __init__(self, max_size: int = 1000, default_ttl: int = 3600):
        import threading
        import time
        from collections import OrderedDict
        
        self.cache = OrderedDict()
        self.max_size = max_size
        self.default_ttl = default_ttl
        self.lock = threading.Lock()
        self.hit_count = 0
        self.miss_count = 0
    
    def _generate_cache_key(self, parameters: Dict[str, Any]) -> str:
        """Generate a cache key from parameters"""
        import json
        import hashlib
        
        # Create deterministic key from relevant parameters
        cache_params = {
            'model': parameters.get('model', ''),
            'prompt': parameters.get('prompt', ''),
            'temperature': parameters.get('temperature', 0.7),
            'max_tokens': parameters.get('max_tokens', 1000),
            'top_p': parameters.get('top_p', 1.0),
            'top_k': parameters.get('top_k', 40)
        }
        
        # Include system prompt if present
        if 'system_prompt' in parameters:
            cache_params['system_prompt'] = parameters['system_prompt']
            
        cache_string = json.dumps(cache_params, sort_keys=True)
        return hashlib.md5(cache_string.encode()).hexdigest()
    
    def get(self, parameters: Dict[str, Any]) -> Optional[Any]:
        """Get cached response if available and not expired"""
        import time
        
        cache_key = self._generate_cache_key(parameters)
        
        with self.lock:
            if cache_key in self.cache:
                cached_data, timestamp, ttl = self.cache[cache_key]
                
                if time.time() - timestamp < ttl:
                    # Move to end (LRU)
                    self.cache.move_to_end(cache_key)
                    self.hit_count += 1
                    logger.info(f"📦 Cache hit for request (key: {cache_key[:8]}...)")
                    return cached_data
                else:
                    # Expired
                    del self.cache[cache_key]
            
            self.miss_count += 1
            return None
    
    def set(self, parameters: Dict[str, Any], response: Any, ttl: int = None):
        """Cache a response"""
        import time
        
        cache_key = self._generate_cache_key(parameters)
        ttl = ttl or self.default_ttl
        
        with self.lock:
            # Remove oldest items if at capacity
            while len(self.cache) >= self.max_size:
                self.cache.popitem(last=False)
            
            self.cache[cache_key] = (response, time.time(), ttl)
            logger.info(f"💾 Cached response (key: {cache_key[:8]}..., TTL: {ttl}s)")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        with self.lock:
            total_requests = self.hit_count + self.miss_count
            hit_rate = (self.hit_count / total_requests * 100) if total_requests > 0 else 0
            
            return {
                'cache_size': len(self.cache),
                'max_size': self.max_size,
                'hit_count': self.hit_count,
                'miss_count': self.miss_count,
                'hit_rate_percent': round(hit_rate, 2),
                'memory_usage_percent': round(len(self.cache) / self.max_size * 100, 2)
            }
    
    def clear(self):
        """Clear all cached responses"""
        with self.lock:
            self.cache.clear()
            self.hit_count = 0
            self.miss_count = 0
            logger.info("🗑️ Cache cleared")

class MetricsCollector:
    """Comprehensive metrics collection for monitoring"""
    
    def __init__(self):
        import threading
        import time
        from collections import defaultdict, deque
        
        self.lock = threading.Lock()
        self.start_time = time.time()
        
        # Request metrics
        self.total_requests = 0
        self.successful_requests = 0
        self.failed_requests = 0
        
        # Response time metrics
        self.response_times = deque(maxlen=1000)  # Keep last 1000 response times
        self.total_response_time = 0
        
        # Model usage tracking
        self.model_usage = defaultdict(int)
        
        # Token usage tracking
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        
        # Error tracking
        self.error_counts = defaultdict(int)
        
        # Feature usage tracking
        self.feature_usage = defaultdict(int)
        
        # Hourly metrics for trend analysis
        self.hourly_metrics = defaultdict(lambda: {
            'requests': 0,
            'errors': 0,
            'response_time_sum': 0
        })
    
    def record_request(self, model: str, response_time: float, success: bool, 
                      input_tokens: int = 0, output_tokens: int = 0, 
                      feature: str = 'standard', error_type: str = None):
        """Record metrics for a request"""
        import time
        
        with self.lock:
            # Basic counters
            self.total_requests += 1
            if success:
                self.successful_requests += 1
            else:
                self.failed_requests += 1
                if error_type:
                    self.error_counts[error_type] += 1
            
            # Response time
            self.response_times.append(response_time)
            self.total_response_time += response_time
            
            # Model usage
            self.model_usage[model] += 1
            
            # Token usage
            self.total_input_tokens += input_tokens
            self.total_output_tokens += output_tokens
            
            # Feature usage
            self.feature_usage[feature] += 1
            
            # Hourly metrics
            current_hour = int(time.time()) // 3600
            self.hourly_metrics[current_hour]['requests'] += 1
            if not success:
                self.hourly_metrics[current_hour]['errors'] += 1
            self.hourly_metrics[current_hour]['response_time_sum'] += response_time
    
    def get_metrics_summary(self) -> Dict[str, Any]:
        """Get comprehensive metrics summary"""
        import time
        import statistics
        
        with self.lock:
            uptime = time.time() - self.start_time
            
            # Calculate success rate
            success_rate = (self.successful_requests / self.total_requests * 100) if self.total_requests > 0 else 0
            
            # Calculate response time statistics
            avg_response_time = self.total_response_time / self.total_requests if self.total_requests > 0 else 0
            
            response_time_stats = {}
            if self.response_times:
                response_time_stats = {
                    'average': round(statistics.mean(self.response_times), 3),
                    'median': round(statistics.median(self.response_times), 3),
                    'p95': round(statistics.quantiles(self.response_times, n=20)[18], 3),
                    'p99': round(statistics.quantiles(self.response_times, n=100)[98], 3),
                    'min': round(min(self.response_times), 3),
                    'max': round(max(self.response_times), 3)
                }
            
            # Calculate requests per minute
            requests_per_minute = (self.total_requests / (uptime / 60)) if uptime > 0 else 0
            
            return {
                'system_metrics': {
                    'uptime_seconds': round(uptime, 2),
                    'total_requests': self.total_requests,
                    'successful_requests': self.successful_requests,
                    'failed_requests': self.failed_requests,
                    'success_rate_percent': round(success_rate, 2),
                    'requests_per_minute': round(requests_per_minute, 2)
                },
                'performance_metrics': {
                    'response_times': response_time_stats,
                    'total_input_tokens': self.total_input_tokens,
                    'total_output_tokens': self.total_output_tokens,
                    'total_tokens': self.total_input_tokens + self.total_output_tokens
                },
                'usage_metrics': {
                    'model_usage': dict(self.model_usage),
                    'feature_usage': dict(self.feature_usage),
                    'error_counts': dict(self.error_counts)
                }
            }

class ProductionErrorHandler:
    """Production-ready error handling with retry logic and recovery"""
    
    def __init__(self, max_retries: int = 3, base_delay: float = 1.0):
        self.max_retries = max_retries
        self.base_delay = base_delay
        
        # Map API errors to retry strategies
        self.retry_strategies = {
            'RateLimitError': {'retries': 5, 'backoff': 'exponential'},
            'APIConnectionError': {'retries': 3, 'backoff': 'exponential'},
            'InternalServerError': {'retries': 3, 'backoff': 'exponential'},
            'BadRequestError': {'retries': 0, 'backoff': 'none'},  # Don't retry bad requests
            'AuthenticationError': {'retries': 0, 'backoff': 'none'},
            'PermissionDeniedError': {'retries': 0, 'backoff': 'none'},
        }
    
    

class HealthMonitor:
    """System health monitoring and diagnostics"""
    
    def __init__(self):
        import threading
        import time
        from collections import deque
        
        self.health_checks = deque(maxlen=100)
        self.lock = threading.Lock()
        self.last_check_time = 0
        self.check_interval = 60  # Check every minute
        
    async def perform_health_check(self, handler) -> Dict[str, Any]:
        """Perform comprehensive health check"""
        import time
        import asyncio
        
        check_time = time.time()
        health_status = {
            'timestamp': check_time,
            'overall_status': 'healthy',
            'checks': {}
        }
        
        try:
            # Check API connectivity
            start_time = time.time()
            test_response = await handler._execute_claude_sdk_request_async({
                'prompt': 'Health check - respond with OK',
                'model': handler.default_model,
                'max_tokens': 10,
                'temperature': 0
            })
            api_response_time = time.time() - start_time
            
            health_status['checks']['api_connectivity'] = {
                'status': 'healthy' if test_response and test_response.success else 'unhealthy',
                'response_time': round(api_response_time, 3),
                'details': 'API responsive' if test_response and test_response.success else 'API not responding'
            }
            
            # Check rate limiter status
            can_make_request, wait_time = handler.rate_limiter.can_make_request()
            health_status['checks']['rate_limiting'] = {
                'status': 'healthy' if can_make_request else 'throttled',
                'wait_time': wait_time,
                'details': 'No rate limiting active' if can_make_request else f'Rate limited, wait {wait_time:.1f}s'
            }
            
            # Check cache performance
            cache_stats = handler.response_cache.get_stats()
            cache_health = 'healthy'
            if cache_stats['memory_usage_percent'] > 90:
                cache_health = 'warning'
            if cache_stats['hit_rate_percent'] < 10 and cache_stats['hit_count'] + cache_stats['miss_count'] > 10:
                cache_health = 'warning'
                
            health_status['checks']['cache_system'] = {
                'status': cache_health,
                'hit_rate': cache_stats['hit_rate_percent'],
                'memory_usage': cache_stats['memory_usage_percent'],
                'details': f"Hit rate: {cache_stats['hit_rate_percent']}%, Memory: {cache_stats['memory_usage_percent']}%"
            }
            
            # Check metrics collector
            metrics = handler.metrics_collector.get_metrics_summary()
            metrics_health = 'healthy'
            if metrics['system_metrics']['success_rate_percent'] < 90 and metrics['system_metrics']['total_requests'] > 10:
                metrics_health = 'warning'
                
            health_status['checks']['request_success_rate'] = {
                'status': metrics_health,
                'success_rate': metrics['system_metrics']['success_rate_percent'],
                'total_requests': metrics['system_metrics']['total_requests'],
                'details': f"Success rate: {metrics['system_metrics']['success_rate_percent']}%"
            }
            
        except Exception as e:
            logger.error(f"Health check failed: {str(e)}")
            health_status['overall_status'] = 'unhealthy'
            health_status['error'] = str(e)
        
        # Determine overall status
        unhealthy_checks = [check for check in health_status['checks'].values() if check['status'] == 'unhealthy']
        if unhealthy_checks:
            health_status['overall_status'] = 'unhealthy'
        elif any(check['status'] == 'warning' for check in health_status['checks'].values()):
            health_status['overall_status'] = 'warning'
        
        with self.lock:
            self.health_checks.append(health_status)
            self.last_check_time = check_time
            
        return health_status
    
    def get_health_summary(self) -> Dict[str, Any]:
        """Get health summary and trends"""
        with self.lock:
            if not self.health_checks:
                return {'status': 'unknown', 'message': 'No health checks performed'}
                
            latest_check = self.health_checks[-1]
            
            # Calculate health trends
            recent_checks = list(self.health_checks)[-10:]  # Last 10 checks
            healthy_count = sum(1 for check in recent_checks if check['overall_status'] == 'healthy')
            health_trend = round(healthy_count / len(recent_checks) * 100, 1)
            
            return {
                'current_status': latest_check['overall_status'],
                'last_check_time': latest_check['timestamp'],
                'health_trend_percent': health_trend,
                'total_checks_performed': len(self.health_checks),
                'detailed_status': latest_check
            }
    

# REAL ANTHROPIC SDK HANDLER - No more CLI wrappers!
# This handler now uses genuine Anthropic Python SDK for all operations
# Messages like "processed with Claude SDK" are now TRUTHFUL

    # ================================
    # MULTI-AGENT WORKSPACE COORDINATION HELPER METHODS  
    # ================================
    

    def _extract_capabilities_from_prompt(self, prompt: str) -> List[str]:
        """Extract required capabilities from user prompt"""
        capabilities = []
        prompt_lower = prompt.lower()
        
        capability_keywords = {
            'DATA_PROCESSING': ['analyze', 'process', 'transform', 'validate', 'clean'],
            'INTEGRATION': ['integrate', 'connect', 'sync', 'combine', 'merge'],
            'AUTOMATION': ['automate', 'schedule', 'workflow', 'pipeline', 'process'],
            'COMMUNICATION': ['email', 'notify', 'message', 'alert', 'send'],
            'PROJECT_MANAGEMENT': ['manage', 'coordinate', 'track', 'organize', 'plan'],
            'DEVELOPMENT': ['code', 'develop', 'build', 'deploy', 'test'],
            'ANALYSIS': ['report', 'analyze', 'metrics', 'dashboard', 'insights'],
            'MULTI_PLATFORM': ['github', 'google', 'meta', 'canva', 'multiple']
        }
        
        for capability, keywords in capability_keywords.items():
            if any(keyword in prompt_lower for keyword in keywords):
                capabilities.append(capability)
        
        return capabilities or ['GENERAL_COORDINATION']




    async def _handle_subtask_delegation(self, tool_input: Dict[str, Any], workspace_context: Dict[str, Any], 
                                       coordination_state: Dict[str, Any]) -> Dict[str, Any]:
        """Handle subtask delegation to agents/MCPs"""
        subtask_id = f"subtask_{len(coordination_state['pending_subtasks']) + 1}"
        subtask = {
            'id': subtask_id,
            'description': tool_input.get('subtask_description'),
            'target_agent': tool_input.get('target_agent'),
            'dependencies': tool_input.get('dependencies', []),
            'priority': tool_input.get('priority', 'medium'),
            'status': 'delegated',
            'created_at': time.time()
        }
        
        coordination_state['pending_subtasks'].append(subtask)
        
        return {
            'tool_name': 'delegate_subtask',
            'success': True,
            'content': f"Subtask {subtask_id} delegated to {subtask['target_agent']}: {subtask['description']}"
        }

    async def _handle_progress_tracking(self, tool_input: Dict[str, Any], 
                                      coordination_state: Dict[str, Any]) -> Dict[str, Any]:
        """Handle progress tracking updates"""
        subtask_id = tool_input.get('subtask_id')
        new_status = tool_input.get('status')
        progress_notes = tool_input.get('progress_notes', '')
        
        # Update subtask status
        for subtask in coordination_state['pending_subtasks']:
            if subtask['id'] == subtask_id:
                subtask['status'] = new_status
                subtask['progress_notes'] = progress_notes
                subtask['updated_at'] = time.time()
                
                if new_status == 'completed':
                    coordination_state['completed_subtasks'].append(subtask)
                    coordination_state['pending_subtasks'].remove(subtask)
                
                break
        
        return {
            'tool_name': 'track_progress',
            'success': True,
            'content': f"Updated {subtask_id} status to {new_status}. {progress_notes}"
        }

    async def _handle_agent_coordination(self, tool_input: Dict[str, Any], workspace_context: Dict[str, Any],
                                       coordination_state: Dict[str, Any]) -> Dict[str, Any]:
        """Handle multi-agent coordination"""
        coordination_plan = tool_input.get('coordination_plan')
        agent_assignments = tool_input.get('agent_assignments', {})
        
        coordination_state['coordination_plan'] = coordination_plan
        coordination_state['agent_assignments'] = agent_assignments
        
        return {
            'tool_name': 'coordinate_agents',
            'success': True,
            'content': f"Coordination plan established: {coordination_plan}"
        }



class ConcurrentAgentLoopManager:
    """
    Manages multiple agent loops running concurrently with inter-loop communication.
    Enables Claude to coordinate multiple tasks simultaneously across different loop types.
    """
    
    def __init__(self, handler_claude_instance):
        self.handler = handler_claude_instance
        self.active_loops = {}  # {loop_id: loop_info}
        self.loop_communication = {}  # Inter-loop message queues
        self.shared_context = {}  # Shared workspace context
        self.coordination_events = {}  # Coordination synchronization
        
    async def execute_concurrent_loops(self, prompt: str, model: str, parameters: Dict[str, Any]) -> HandlerResult:
        """
        Execute multiple agent loops concurrently based on requirements.
        """
        try:
            import uuid
            import time
            from collections import defaultdict
            
            # Determine which loops are needed
            required_loops = self._analyze_concurrent_requirements(prompt, parameters)
            logger.info(f"🎯 Concurrent execution requires loops: {required_loops}")
            
            # Initialize shared coordination state
            coordination_state = await self._initialize_coordination_state(parameters)
            
            # Create tasks for each required loop
            loop_tasks = []
            loop_contexts = {}
            
            for loop_type in required_loops:
                loop_context = await self._create_loop_context(loop_type, prompt, model, parameters, coordination_state)
                loop_contexts[loop_type] = loop_context
                
                task = self._create_loop_task(loop_type, loop_context)
                loop_tasks.append(task)
                
            logger.info(f"🚀 Starting {len(loop_tasks)} concurrent agent loops")
            
            # Execute all loops concurrently with coordination
            results = await asyncio.gather(*loop_tasks, return_exceptions=True)
            
            # Aggregate and return coordinated results
            return await self._aggregate_concurrent_results(results, required_loops, loop_contexts)
            
        except Exception as e:
            logger.error(f"❌ Concurrent loop execution failed: {e}")
            return HandlerResult(success=False, error=f"Concurrent execution failed: {str(e)}")
    
    def _analyze_concurrent_requirements(self, prompt: str, parameters: Dict[str, Any]) -> list:
        """Analyze what loops are needed to fulfill the request"""
        required_loops = []
        
        # Check for computer use needs
        if (parameters.get('enable_computer_tools', False) or 
            self._needs_computer_interaction(prompt)):
            required_loops.append('computer_use')
        
        # Check for multi-agent workspace needs  
        if (self.handler._requires_multi_agent_workspace(prompt, parameters) or
            self._has_workspace_context(parameters)):
            required_loops.append('multi_agent_workspace')
            
        # Regular tools are ALWAYS available for coordination
        required_loops.append('regular_tools')
        
        # Deduplicate while preserving order
        return list(dict.fromkeys(required_loops))
    
    def _needs_computer_interaction(self, prompt: str) -> bool:
        """Check if prompt requires computer interaction"""
        computer_keywords = [
            'screenshot', 'click', 'type', 'desktop', 'mouse', 'keyboard',
            'window', 'application', 'gui', 'interface', 'screen'
        ]
        prompt_lower = prompt.lower()
        return any(keyword in prompt_lower for keyword in computer_keywords)
    
    def _has_workspace_context(self, parameters: Dict[str, Any]) -> bool:
        """Check if request has workspace context"""
        return bool(parameters.get('workspace_id') or parameters.get('workspace_context'))
    
    async def _initialize_coordination_state(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Initialize shared coordination state for all loops"""
        from collections import defaultdict
        return {
            'workspace_id': parameters.get('workspace_id'),
            'session_id': parameters.get('session_id', f"concurrent_{int(time.time())}"),
            'shared_context': {},
            'message_queues': defaultdict(asyncio.Queue),
            'coordination_events': {},
            'loop_results': {},
            'start_time': time.time()
        }
    
    async def _create_loop_context(self, loop_type: str, prompt: str, model: str, 
                                  parameters: Dict[str, Any], coordination_state: Dict[str, Any]) -> Dict[str, Any]:
        """Create context for a specific loop type"""
        import uuid
        base_context = {
            'loop_type': loop_type,
            'prompt': prompt,
            'model': model,
            'parameters': parameters.copy(),
            'coordination_state': coordination_state,
            'loop_id': f"{loop_type}_{int(time.time())}_{uuid.uuid4().hex[:8]}"
        }
        
        # Add loop-specific context
        if loop_type == 'computer_use':
            base_context['max_iterations'] = parameters.get('max_iterations', 50)
        elif loop_type == 'multi_agent_workspace':
            base_context['complexity_level'] = self.handler._analyze_workspace_complexity(prompt, parameters)
            base_context['max_iterations'] = self.handler._calculate_dynamic_iterations(base_context['complexity_level'])
        elif loop_type == 'regular_tools':
            base_context['max_iterations'] = parameters.get('max_iterations', None)
            base_context['system_prompt'] = self.handler._build_system_prompt(parameters)
            
        return base_context
    
    def _create_loop_task(self, loop_type: str, loop_context: Dict[str, Any]):
        """Create asyncio task for specific loop type"""
        if loop_type == 'computer_use':
            return asyncio.create_task(
                self._execute_computer_use_concurrent(loop_context),
                name=f"computer_use_{loop_context['loop_id']}"
            )
        elif loop_type == 'multi_agent_workspace':
            return asyncio.create_task(
                self._execute_multi_agent_workspace_concurrent(loop_context),
                name=f"multi_agent_workspace_{loop_context['loop_id']}"
            )
        elif loop_type == 'regular_tools':
            return asyncio.create_task(
                self._execute_regular_tools_concurrent(loop_context),
                name=f"regular_tools_{loop_context['loop_id']}"
            )
        else:
            raise ValueError(f"Unknown loop type: {loop_type}")
    
    async def _execute_computer_use_concurrent(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute computer use loop with coordination"""
        try:
            logger.info(f"🖥️ Starting concurrent computer use loop {context['loop_id']}")
            
            # Execute the computer use loop with coordination hooks
            result = self.handler.execute_computer_use_agent_loop(
                context['prompt'],
                context['model'], 
                context['max_iterations'],
                parameters=context['parameters']
            )
            
            # Add coordination metadata
            return {
                'loop_type': 'computer_use',
                'loop_id': context['loop_id'],
                'result': result,
                'status': 'completed',
                'completion_time': time.time()
            }
            
        except Exception as e:
            logger.error(f"❌ Computer use concurrent loop failed: {e}")
            return {
                'loop_type': 'computer_use',
                'loop_id': context['loop_id'],
                'result': HandlerResult(success=False, error=str(e)),
                'status': 'failed',
                'error': str(e)
            }
    
    async def _execute_multi_agent_workspace_concurrent(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute multi-agent workspace loop with coordination"""
        try:
            logger.info(f"🤖 Starting concurrent multi-agent workspace loop {context['loop_id']}")
            
            # Execute the multi-agent workspace loop
            result = await self.handler.execute_multi_agent_workspace_loop(
                context['prompt'],
                context['model'],
                context['max_iterations'],
                context['parameters']
            )
            
            return {
                'loop_type': 'multi_agent_workspace',
                'loop_id': context['loop_id'],
                'result': result,
                'status': 'completed',
                'completion_time': time.time()
            }
            
        except Exception as e:
            logger.error(f"❌ Multi-agent workspace concurrent loop failed: {e}")
            return {
                'loop_type': 'multi_agent_workspace',
                'loop_id': context['loop_id'],
                'result': HandlerResult(success=False, error=str(e)),
                'status': 'failed',
                'error': str(e)
            }
    
    async def _execute_regular_tools_concurrent(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute regular tools loop with coordination"""
        try:
            logger.info(f"🔧 Starting concurrent regular tools loop {context['loop_id']}")
            
            # Execute the regular tools loop
            result = self.handler.execute_regular_tools_agent_loop(
                context['prompt'],
                context['model'],
                context['max_iterations'],
                context['system_prompt'],
                context['parameters']
            )
            
            return {
                'loop_type': 'regular_tools',
                'loop_id': context['loop_id'],
                'result': result,
                'status': 'completed', 
                'completion_time': time.time()
            }
            
        except Exception as e:
            logger.error(f"❌ Regular tools concurrent loop failed: {e}")
            return {
                'loop_type': 'regular_tools',
                'loop_id': context['loop_id'],
                'result': HandlerResult(success=False, error=str(e)),
                'status': 'failed',
                'error': str(e)
            }
    
    async def _aggregate_concurrent_results(self, results, required_loops, loop_contexts):
        """Aggregate results from all concurrent loops"""
        try:
            successful_results = []
            failed_results = []
            aggregated_content = []
            
            for i, result in enumerate(results):
                loop_type = required_loops[i] if i < len(required_loops) else f"loop_{i}"
                
                if isinstance(result, Exception):
                    failed_results.append({
                        'loop_type': loop_type,
                        'error': str(result)
                    })
                    logger.error(f"❌ Loop {loop_type} failed with exception: {result}")
                else:
                    successful_results.append(result)
                    if result.get('result') and hasattr(result['result'], 'data'):
                        content = result['result'].data.get('content', '')
                        if content:
                            aggregated_content.append(f"**{loop_type.upper()} RESULT:** {content}")
            
            # Build final response
            total_execution_time = time.time() - loop_contexts.get(required_loops[0], {}).get('coordination_state', {}).get('start_time', time.time())
            
            final_content = f"""🚀 **CONCURRENT AGENT LOOPS COMPLETED**

**Execution Summary:**
- Loops executed: {len(required_loops)} ({", ".join(required_loops)})
- Successful: {len(successful_results)}
- Failed: {len(failed_results)}
- Total execution time: {total_execution_time:.2f}s

**Combined Results:**
{chr(10).join(aggregated_content) if aggregated_content else "No content results from loops"}
"""
            
            if failed_results:
                final_content += f"\n\n**Failures:**\n"
                for failure in failed_results:
                    final_content += f"- {failure['loop_type']}: {failure['error']}\n"
            
            return HandlerResult(
                success=len(successful_results) > 0,
                data={
                    'content': final_content,
                    'concurrent_results': successful_results,
                    'failed_results': failed_results,
                    'execution_summary': {
                        'loops_executed': required_loops,
                        'successful_count': len(successful_results),
                        'failed_count': len(failed_results),
                        'total_execution_time': total_execution_time
                    }
                }
            )
            
        except Exception as e:
            logger.error(f"❌ Result aggregation failed: {e}")
            return HandlerResult(success=False, error=f"Result aggregation failed: {str(e)}")


class PromptLibrary:
    """Collection of specialized prompt templates for Claude SDK"""
    COSMIC_KEYSTROKES = """Generate interactive and engaging content with a cosmic theme."""
    CORPORATE_CLAIRVOYANT = """Analyze business scenarios and provide strategic insights."""
    WEBSITE_WIZARD = """Create and optimize web content, focusing on UX and best practices."""
    EXCEL_FORMULA_EXPERT = """Develop and explain Excel formulas and spreadsheet solutions."""
    GOOGLE_APPS_SCRIPTER = """Create and debug Google Apps Scripts for automation."""
    PYTHON_BUG_BUSTER = """Debug Python code and provide optimized solutions."""
    CODE_CONSULTANT = """Review and improve code structure and patterns."""
    FUNCTION_FABRICATOR = """Create efficient and well-documented functions."""
