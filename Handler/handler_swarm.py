#!/usr/bin/env python3
"""
SwarmHandler - Agent Swarm Management Module

Migrated from OpenAI to Anthropic SDK (claude-sonnet-4-5-20250929).
Manages a swarm of agents that communicate and collaborate on tasks,
with support for tool execution, team formation, and performance tracking.

Consolidated: moved dead init code into __init__, removed triple imports,
removed duplicate sync track_journey_step, fixed register_agent return type,
added missing actions (distribute_tasks, coordinate_parallel, get_status, assign_work).
"""

import os
import sys
from pathlib import Path

# Add the project root to Python path
ROOT_DIR = Path(__file__).parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import json
import time as time_module
import logging
import uuid
import hashlib
import asyncio
import traceback
import random
import inspect
import importlib
from typing import Dict, List, Any, Optional, Callable, Union, Tuple
from datetime import datetime

from pydantic import BaseModel
from Handler.handler_base import BaseHandler, HandlerResult, DatabaseManager

# Import from Jarvis_Agent_SDK for common utilities
from Jarvis_Agent_SDK.boardroom_connector import (
    generate_request_id,
    generate_simple_id,
    track_journey_step_sync,
    track_request_journey,
    get_direct_tracking_interface
)
from Database.v2.db_helper import connection as v2_connection
from Jarvis_Agent_SDK.import_helper import get_workspace_sharing

# Configure logging
logger = logging.getLogger("SwarmHandler")
logger.setLevel(logging.INFO)
if not logger.handlers:
    _stream_handler = logging.StreamHandler()
    _formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    _stream_handler.setFormatter(_formatter)
    logger.addHandler(_stream_handler)

# Anthropic SDK import
try:
    from anthropic import Anthropic
    HAS_ANTHROPIC = True
except ImportError:
    logger.warning("Anthropic SDK not available. Install with: pip install anthropic")
    HAS_ANTHROPIC = False

# Default model for swarm coordination tasks
SWARM_MODEL = "claude-sonnet-4-5-20250929"


def _load_api_key(key_type='CLAUDE'):
    """Load API key from file or environment variable."""
    key_paths = {
        'CLAUDE': os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                               "API", "CLAUDE_API_KEY.txt"),
    }
    key_path = key_paths.get(key_type)
    if key_path and os.path.exists(key_path):
        with open(key_path, 'r') as f:
            return f.read().strip()
    env_key = os.environ.get('ANTHROPIC_API_KEY')
    if env_key:
        return env_key
    return None


# Import database components lazily to avoid circular dependencies
def get_database_components():
    try:
        from Jarvis_Agent_SDK.database import SQLiteDatabase
        from Database.database_user import WorkspaceManager
        return SQLiteDatabase, WorkspaceManager
    except ImportError as e:
        logger.warning(f"Could not import database components: {e}")
        return None, None


class SwarmAgent(BaseModel):
    """Represents an agent in the swarm"""
    name: str
    instructions: str
    tools: List[Callable] = []
    mcp_tools: List[str] = []  # MCP handler names this agent can use (e.g. ["data_validator", "terminal"])
    model: str = SWARM_MODEL


class SwarmHandler(BaseHandler):
    """Handler for managing AI agent swarms and collaborative task execution"""

    def __init__(self, log_path: str = None, orchestrator_agent_class=None, db_path: str = None, tracker=None):
        """Initialize the SwarmHandler."""
        if not db_path:
            db_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "Database")
            db_path = os.path.join(db_dir, "v2", "agents.db")

        super().__init__(app_name="SwarmHandler", db_path=db_path)
        self.registry = {}
        self.agents = {}
        self.is_initialized = False
        self.active_agents = []
        self.agent_registry_handler = None
        self.db_path = db_path

        # Ensure the database directory exists
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)

        # Initialize activity tracking storage (agent_activity, agent_communication, journey_steps tables)
        self._init_tracking_tables()

        # Use injected tracker if provided, otherwise fall back to BoardRoom
        if tracker is not None:
            self.boardroom = tracker
            logger.info("SwarmHandler using injected tracker (skipping BoardRoom init)")

        # Orchestrator agent removed — OpenClaw is the orchestrator now
        self.orchestrator_agent = None

        # Initialize Anthropic client
        self._initialize_client()

        # Workspace context — set externally via set_workspace() before operations
        self._workspace_sharing = None
        self._workspace_id = None  # Integer DB ID, set by caller
        self._agent_workspace_map = {}  # agent_name -> agent_id
        self.teams = {}
        self.task_assignments = {}
        self._agent_mcp_cache = {}
        self._handler_instance_cache = {}
        self.conversations = {}
        self._init_workspace_sharing()

        # Handler metadata for detection
        self.name = "swarm"
        self.handler_type = "SwarmHandler"
        self.capabilities = [
            "agent_registration",
            "multi_agent_conversation",
            "tool_execution",
            "team_performance_tracking",
            "task_management",
            "agent_learning_paths",
            "collaboration_pattern_analysis",
            "workload_balancing"
        ]
        self.patterns = [
            "register agent with {capabilities}",
            "start conversation with {agent}",
            "execute tool {tool_name}",
            "handoff to {agent}",
            "track team {team_name}",
            "analyze performance",
            "optimize collaboration",
            "balance workload",
            "monitor task {task_id}"
        ]

    def _init_workspace_sharing(self):
        """Get workspace sharing manager reference."""
        try:
            self._workspace_sharing = get_workspace_sharing()
            if self._workspace_sharing:
                logger.info("WorkspaceSharingManager connected")
        except Exception as e:
            logger.warning(f"Workspace sharing init skipped: {e}")

    def set_workspace(self, workspace_id: int):
        """Set the workspace this swarm operates in. Called by the system before operations.
        
        ARCHITECTURE NOTE: Workspaces are INHERITED, not created by the swarm.
        The workspace_id comes from the conversation/UI layer — every user conversation
        gets a workspace assigned at the start. If the conversation becomes a project,
        the workspace already has the full history. The conversation aggregator finds
        and connects related workspaces. The boardroom monitors workspaces but never creates them.
        """
        self._workspace_id = workspace_id
        self._workspace_mcp_config = {}  # handler_name -> mcp_server_name
        logger.info(f"Swarm bound to workspace {workspace_id}")

    async def load_workspace_mcp(self):
        """Load the workspace's MCP configuration so agents can use MCP tools.
        Call after set_workspace() in an async context."""
        if not self._workspace_id or not self._workspace_sharing:
            return
        try:
            mcp_config = await self._workspace_sharing.get_workspace_mcp_handlers(self._workspace_id)
            if mcp_config:
                self._workspace_mcp_config = mcp_config
                logger.info(f"Loaded {len(mcp_config)} MCP handlers for workspace {self._workspace_id}: {list(mcp_config.keys())}")
        except Exception as e:
            logger.warning(f"Could not load workspace MCP config: {e}")

    async def _assign_agent_to_workspace(self, agent_id: str, agent_name: str, role: str = "contributor"):
        """Assign an agent to the current workspace."""
        if not self._workspace_id or not self._workspace_sharing:
            self._agent_workspace_map[agent_name] = agent_id
            return False
        
        # Check if WorkspaceSharingManager has the assign_agent_to_workspace method
        if not hasattr(self._workspace_sharing, 'assign_agent_to_workspace'):
            logger.debug(f"WorkspaceSharingManager does not have assign_agent_to_workspace method")
            self._agent_workspace_map[agent_name] = agent_id
            return False
        
        try:
            # Add timeout to prevent long waits
            import asyncio
            success = await asyncio.wait_for(
                self._workspace_sharing.assign_agent_to_workspace(
                    agent_id=agent_id,
                    workspace_id=self._workspace_id,
                    role=role
                ),
                timeout=1.0  # 1 second timeout instead of 20 seconds
            )
            if success:
                self._agent_workspace_map[agent_name] = agent_id
                logger.info(f"Assigned agent {agent_name} to workspace {self._workspace_id}")
            return success
        except asyncio.TimeoutError:
            logger.warning(f"Workspace assignment for {agent_name} timed out after 1s")
            self._agent_workspace_map[agent_name] = agent_id
            return False
        except AttributeError as e:
            logger.warning(f"WorkspaceSharingManager missing method: {e}")
            self._agent_workspace_map[agent_name] = agent_id
            return False
        except Exception as e:
            logger.warning(f"Could not assign agent to workspace: {e}")
            self._agent_workspace_map[agent_name] = agent_id
            return False

    async def _create_workspace_task(self, title: str, description: str = None,
                                     assigned_agent_name: str = None,
                                     priority: str = "medium") -> Optional[int]:
        """Create a task in the workspace database via WorkspaceSharing API."""
        if not self._workspace_id or not self._workspace_sharing:
            return None
        try:
            agent_id = self._agent_workspace_map.get(assigned_agent_name, assigned_agent_name)
            task_id = await self._workspace_sharing.add_task(
                workspace_id=self._workspace_id,
                title=title,
                description=description,
                priority=priority,
                assigned_agent_id=agent_id
            )
            if task_id:
                logger.info(f"Created workspace task #{task_id}: {title}")
            return task_id
        except Exception as e:
            logger.warning(f"Could not create workspace task: {e}")
        return None

    def _init_tracking_tables(self):
        """Initialize database tables for tracking agent activities.

        Tables are created in V2 databases:
        - agent_activity, agent_communication → agents.db
        - journey_steps → agents.db (local copy; canonical in journeys.db)
        - deliberation_history → journeys.db
        """
        try:
            with v2_connection("agents") as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS agent_activity (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        agent_id TEXT NOT NULL,
                        agent_name TEXT NOT NULL,
                        agent_type TEXT NOT NULL,
                        workspace_id TEXT NOT NULL,
                        action_type TEXT NOT NULL,
                        details TEXT,
                        performance_metrics TEXT,
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS agent_communication (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        message_id TEXT NOT NULL,
                        sender_agent_id TEXT NOT NULL,
                        sender_agent_name TEXT NOT NULL,
                        receiver_agent_id TEXT NOT NULL,
                        receiver_agent_name TEXT NOT NULL,
                        task_id TEXT,
                        message_type TEXT,
                        content TEXT,
                        metadata TEXT,
                        timestamp TEXT,
                        journey_id TEXT,
                        workspace_id TEXT
                    )
                """)
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS journey_steps (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        step_id TEXT NOT NULL,
                        journey_id TEXT NOT NULL,
                        step_name TEXT NOT NULL,
                        description TEXT,
                        step_type TEXT,
                        input_data TEXT,
                        output_data TEXT,
                        status TEXT,
                        error TEXT,
                        timestamp TEXT
                    )
                """)
            logger.info("Initialized tracking tables in V2 agents.db")

            # Ensure deliberation_history exists in journeys.db
            with v2_connection("journeys") as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS deliberation_history (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        workspace_id INTEGER,
                        user_id INTEGER,
                        topic TEXT,
                        context TEXT,
                        contributions TEXT,
                        synthesis TEXT,
                        opus_review TEXT,
                        created_at REAL
                    )
                """)
            logger.info("Ensured deliberation_history in V2 journeys.db")

            # Keep db_manager as None — all DB access goes through v2_connection
            self.db_manager = None
        except Exception as e:
            logger.error(f"Error initializing V2 tracking tables: {str(e)}")
            self._init_local_tracking()

        if hasattr(self, 'boardroom') and self.boardroom:
            logger.info("Using BoardRoom for tracking tables")

    def _init_local_tracking(self):
        """Initialize local dictionary-based tracking as fallback"""
        self.agent_activity_log = {}
        self.agent_performance_metrics = {}
        self.team_status_tracking = {}
        self.agent_communication_log = {}
        logger.info("Initialized local tracking tables as fallback")

    def _initialize_client(self):
        """Initialize the LLM client for swarm coordination.
        
        Uses LLMRouter when available (supports Anthropic + Ollama + any OpenAI-compatible).
        Falls back to direct Anthropic client for backward compatibility.
        """
        # Try LLMRouter first (THE swap point for cloud ↔ local)
        try:
            from Handler.modules.claude_client import LLMRouter, AnthropicClient, OpenAICompatibleClient
            api_key = _load_api_key('CLAUDE')
            self.llm_router = LLMRouter()
            if api_key:
                _anthropic = AnthropicClient(api_key=api_key)
                self.llm_router.register_client("anthropic/", _anthropic, is_default=True)
                self.llm_router.register_client("claude-", _anthropic)
            # MLX servers — per-seat ports, same OpenAI-compat API
            _mlx_ports = {"CRO": 11500, "CTO": 11501, "CSO": 11502, "CDO": 11503, "Coder": 11504}
            for seat, port in _mlx_ports.items():
                _mlx_client = OpenAICompatibleClient(
                    base_url=f"http://127.0.0.1:{port}",  # mlx_vlm.server has no /v1 prefix
                    api_key="mlx-local",
                    default_model="default",
                )
                self.llm_router.register_client(f"mlx/{seat}", _mlx_client)
            # Keep backward-compat self.anthropic_client reference
            self.anthropic_client = _anthropic.client if api_key else None
            logger.info("✅ SwarmHandler LLMRouter initialized (Anthropic + MLX)")
            return
        except Exception as e:
            logger.warning(f"LLMRouter init failed, falling back to direct Anthropic: {e}")
            self.llm_router = None

        # Fallback: direct Anthropic client
        try:
            api_key = _load_api_key('CLAUDE')
            if api_key:
                # Explicit timeout — default 600s read timeout causes 5+ min hangs on
                # stuck server connections. Vision calls need ~90s; 120s is safe margin.
                try:
                    import httpx as _httpx
                    _swarm_timeout = _httpx.Timeout(connect=10.0, read=120.0, write=60.0, pool=10.0)
                except ImportError:
                    _swarm_timeout = 120.0
                self.anthropic_client = Anthropic(api_key=api_key, timeout=_swarm_timeout)
                logger.info("Successfully initialized Anthropic client for swarm operations (read_timeout=120s)")
            else:
                logger.warning("Anthropic API key not found")
                self.anthropic_client = None
        except Exception as e:
            logger.error(f"Error initializing Anthropic client: {e}")
            self.anthropic_client = None

    def _call_llm(self, system_prompt: str, user_prompt: str, 
                  max_tokens: int = 1024, model: str = None) -> str:
        """Centralized LLM call — routes through LLMRouter when available.
        
        Supports Anthropic and MLX (OpenAI-compatible) endpoints.
        To run agents on local models, pass model="mlx/CSO" (or another seat).
        """
        model = model or SWARM_MODEL
        
        # Try LLMRouter first (supports any backend)
        if hasattr(self, 'llm_router') and self.llm_router:
            try:
                import asyncio
                response = asyncio.get_event_loop().run_until_complete(
                    self.llm_router.create_message(
                        model=model,
                        system=system_prompt,
                        messages=[{"role": "user", "content": user_prompt}],
                        max_tokens=max_tokens,
                        temperature=0,
                    )
                )
                # Extract text from either Anthropic or OpenAI response format
                if hasattr(response, 'content'):
                    for block in response.content:
                        if hasattr(block, 'text') and block.text:
                            return block.text
                if hasattr(response, 'choices'):
                    msg = response.choices[0].message
                    text = msg.content or ""
                    # Thinking models (qwen3.5, deepseek-r1) via the MLX
                    # OpenAI-compat layer put reasoning in 'reasoning_content'
                    # and may leave 'content' empty.
                    reasoning = (
                        getattr(msg, 'reasoning_content', None)
                        or getattr(msg, 'reasoning', None)
                        or ""
                    )
                    # If content is empty but reasoning has the answer, use it
                    if not text.strip() and reasoning:
                        text = reasoning
                    # Strip <think>...</think> tags if present
                    if "<think>" in text:
                        import re as _re
                        text = _re.sub(r"<think>.*?</think>", "", text, flags=_re.DOTALL).strip()
                    return text or str(response)
                return str(response)
            except Exception as e:
                logger.warning(f"LLMRouter call failed, falling back to direct Anthropic: {e}")
        
        # Fallback: direct Anthropic client
        if not self.anthropic_client:
            raise RuntimeError("No LLM client available — check API key and LLMRouter")
        import time as _time_llm
        _llm_kwargs = dict(
            model=model,
            max_tokens=max_tokens,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
            temperature=0,
        )
        for _attempt_llm in range(3):
            try:
                response = self.anthropic_client.messages.create(**_llm_kwargs)
                break
            except Exception as _exc_llm:
                _es = str(_exc_llm)
                if ("rate_limit" in _es.lower() or "429" in _es) and _attempt_llm < 2:
                    _wait = 5 * (2 ** _attempt_llm)
                    logger.warning("[_call_llm] 429 rate limited — waiting %ds (attempt %d/3)", _wait, _attempt_llm + 1)
                    _time_llm.sleep(_wait)
                else:
                    raise
        return response.content[0].text

    def _call_anthropic(self, system_prompt: str, user_prompt: str, max_tokens: int = 1024) -> str:
        """Backward-compat wrapper — delegates to _call_llm."""
        return self._call_llm(system_prompt, user_prompt, max_tokens=max_tokens)

    # ------------------------------------------------------------------
    # MCP Server Management — launch, cache, and expose tools for agents
    # ------------------------------------------------------------------

    def _launch_agent_mcps(self, agent_name: str) -> dict:
        """Build tool definitions for an agent's MCP handlers.

        Uses handler introspection to discover public methods — the same
        methods that workspace_sharing.execute_method_via_mcp() can call.
        No separate FastMCP server is launched; tools route through the
        existing workspace MCP infrastructure.

        Returns dict of {short_name: {"tools": [tool_defs], "methods": [str]}}
        """
        if agent_name in self._agent_mcp_cache:
            return self._agent_mcp_cache[agent_name]

        agent = self.agents.get(agent_name)
        if not agent or not agent.mcp_tools:
            self._agent_mcp_cache[agent_name] = {}
            return {}

        from Jarvis_Agent_SDK.mcp_server_launcher import HANDLER_REGISTRY
        import inspect as _inspect

        servers = {}
        for mcp_name in agent.mcp_tools:
            short_name = mcp_name.replace("handler_", "") if mcp_name.startswith("handler_") else mcp_name
            try:
                # Map agent mcp_tools names to HANDLER_REGISTRY keys
                # e.g. handler_news_info → try: news_info, news, handler_news_info
                candidates = [short_name, mcp_name]
                # Also try without trailing suffix (news_info → news)
                if '_' in short_name:
                    candidates.append(short_name.split('_')[0])
                reg_key = None
                for c in candidates:
                    if c in HANDLER_REGISTRY:
                        reg_key = c
                        break
                if not reg_key:
                    logger.warning("Handler %s not in HANDLER_REGISTRY (tried %s)", mcp_name, candidates)
                    continue
                module_path, class_name = HANDLER_REGISTRY[reg_key]
                module = importlib.import_module(module_path)
                handler_class_or_func = getattr(module, class_name)

                # Cache handler instance (only for classes, not functions)
                cache_key = f"{short_name}_{class_name}"

                # Determine if it's a class or function-based handler
                is_class = _inspect.isclass(handler_class_or_func)

                if is_class:
                    if cache_key not in self._handler_instance_cache:
                        # Pass tracker to handlers that support it (avoids BoardRoom init)
                        try:
                            init_sig = _inspect.signature(handler_class_or_func.__init__)
                            if 'tracker' in init_sig.parameters and hasattr(self, 'boardroom'):
                                self._handler_instance_cache[cache_key] = handler_class_or_func(tracker=self.boardroom)
                            else:
                                self._handler_instance_cache[cache_key] = handler_class_or_func()
                        except (ValueError, TypeError):
                            self._handler_instance_cache[cache_key] = handler_class_or_func()
                    handler = self._handler_instance_cache[cache_key]
                    introspect_target = handler
                else:
                    # Function-based handler (e.g., handler_weather.weather is an async func)
                    # Introspect the MODULE for callable functions instead
                    handler = None
                    introspect_target = module

                # Discover public methods/functions → Anthropic tool definitions
                tool_defs = []
                method_names = []
                members = dir(introspect_target)
                for method_name in members:
                    if method_name.startswith('_'):
                        continue
                    method = getattr(introspect_target, method_name, None)
                    if not callable(method):
                        continue
                    # Skip non-action items (imports, classes, constants)
                    if _inspect.isclass(method) or _inspect.ismodule(method):
                        continue
                    # Skip common non-action methods
                    if method_name in ('handle', 'execute', 'create_success_result',
                                       'create_error_result', 'check_handler_dependencies',
                                       'log_agent_activity', 'receive_message_from_jarvis',
                                       'get_active_objects', 'get_journey_steps',
                                       'execute_action', 'load_api_key',
                                       'analyze_handler_capabilities'):
                        continue

                    # Build input schema from signature
                    try:
                        sig = _inspect.signature(method)
                        properties = {}
                        required = []
                        for pname, param in sig.parameters.items():
                            if pname in ('self', 'context', 'kwargs'):
                                continue
                            prop = {"type": "string"}
                            if param.default is inspect.Parameter.empty:
                                required.append(pname)
                            else:
                                prop["default"] = str(param.default) if param.default is not None else None
                            properties[pname] = prop

                        tool_defs.append({
                            "name": method_name,
                            "description": (method.__doc__ or f"Execute {short_name}.{method_name}")[:200].strip(),
                            "input_schema": {
                                "type": "object",
                                "properties": properties,
                                "required": required,
                            },
                        })
                        method_names.append(method_name)
                    except (ValueError, TypeError):
                        continue

                servers[short_name] = {
                    "tools": tool_defs,
                    "methods": method_names,
                    "registry_key": reg_key,  # The key that HANDLER_REGISTRY actually uses
                }
                logger.info(
                    "Introspected handler %s (registry: %s) for agent %s: %d tools exposed",
                    short_name, reg_key, agent_name, len(tool_defs),
                )

            except Exception as exc:
                logger.error("Failed to introspect handler %s for %s: %s", short_name, agent_name, exc)

        self._agent_mcp_cache[agent_name] = servers
        return servers

    def _build_workspace_context(self, board_member_name: str) -> str:
        """Build full workspace architecture context for a board member.

        Gives the board member situational awareness of:
        - Workspace structure & active projects
        - Team organization (which agents, what skills, who reports where)
        - Task assignments & status
        - Communication channels between agents/teams
        - Available data sources and tools
        """
        sections = []

        # --- 1. Workspace overview ---
        workspace_info = []
        if self._workspace_id:
            workspace_info.append(f"Boardroom Workspace ID: {self._workspace_id}")
        try:
            with v2_connection("workspaces") as conn:
                # Find this board member's division workspace
                rows = conn.execute(
                    """SELECT w.id, w.name, w.workspace_type, w.status, w.parent_workspace_id
                       FROM workspaces w
                       WHERE w.status='active' AND w.workspace_type IN ('boardroom', 'division')
                       ORDER BY w.parent_workspace_id NULLS FIRST, w.id
                       LIMIT 30"""
                ).fetchall()
                if rows:
                    workspace_info.append("Workspace hierarchy:")
                    my_division_id = None
                    for r in rows:
                        prefix = "  " if r['parent_workspace_id'] else ""
                        marker = " ← YOUR DIVISION" if (
                            r['workspace_type'] == 'division' and
                            board_member_name.upper() in (r['name'] or '').upper()
                        ) else ""
                        if marker:
                            my_division_id = r['id']
                        workspace_info.append(
                            f"{prefix}  - [{r['id']}] {r['name']} "
                            f"(type={r['workspace_type']}, status={r['status']}){marker}"
                        )

                    # Pull tasks for this member's division
                    if my_division_id:
                        tasks = conn.execute(
                            """SELECT id, title, status, priority, assigned_agent_id
                               FROM workspace_tasks
                               WHERE workspace_id = ? AND status != 'archived'
                               ORDER BY priority DESC, created_at DESC LIMIT 10""",
                            (my_division_id,)
                        ).fetchall()
                        if tasks:
                            workspace_info.append(f"\nYour division tasks ({len(tasks)}):")
                            for t in tasks:
                                assigned = t['assigned_agent_id'] or 'unassigned'
                                workspace_info.append(
                                    f"  - [{t['id']}] {t['title']} "
                                    f"(status={t['status']}, priority={t['priority']}, agent={assigned})"
                                )

                    # Pull agents assigned to this member's division
                    if my_division_id:
                        agents = conn.execute(
                            """SELECT agent_id, role FROM workspace_agent_assignments
                               WHERE workspace_id = ? AND status = 'active'""",
                            (my_division_id,)
                        ).fetchall()
                        if agents:
                            workspace_info.append(f"\nAgents in your division ({len(agents)}):")
                            for a in agents:
                                workspace_info.append(f"  - {a['agent_id']} (role={a['role']})")
        except Exception:
            pass

        if workspace_info:
            sections.append("## Workspace Architecture\n" + "\n".join(workspace_info))

        # --- 2. Team organization ---
        team_info = []
        try:
            # Board members from boardroom_template
            from Handler.boardroom_template import BOARD_MEMBERS
            team_info.append("### Board of Directors")
            for seat, member in BOARD_MEMBERS.items():
                model = member.get("model", "unknown")
                role = member.get("title", seat)
                team_info.append(f"  - **{seat}** ({role}): model={model}")
        except Exception:
            pass

        # Agent teams from registry
        try:
            agents_by_type = {}
            for aname, aobj in self.agents.items():
                atype = getattr(aobj, 'agent_type', 'unassigned') or 'unassigned'
                agents_by_type.setdefault(atype, []).append(aname)

            if agents_by_type:
                team_info.append("\n### Agent Teams")
                for atype, members in sorted(agents_by_type.items()):
                    team_info.append(f"  **{atype}** ({len(members)} agents): {', '.join(members[:10])}"
                                    + (f" +{len(members)-10} more" if len(members) > 10 else ""))
        except Exception:
            pass

        # Agent skills summary
        try:
            skilled_agents = []
            for aname, aobj in self.agents.items():
                skills = getattr(aobj, 'mcp_tools', None) or []
                if skills:
                    skilled_agents.append(f"  - {aname}: {', '.join(skills[:5])}"
                                         + (f" +{len(skills)-5}" if len(skills) > 5 else ""))
            if skilled_agents:
                team_info.append("\n### Agent Capabilities (tools)")
                team_info.extend(skilled_agents[:30])
                if len(skilled_agents) > 30:
                    team_info.append(f"  ... +{len(skilled_agents)-30} more agents with tools")
        except Exception:
            pass

        if team_info:
            sections.append("\n".join(team_info))

        # --- 3. Active tasks ---
        try:
            with v2_connection("workspaces") as db:
                cursor = db.execute(
                    """SELECT id, title, status, assigned_agent, priority
                       FROM workspace_tasks
                       WHERE status IN ('pending', 'in_progress', 'blocked')
                       ORDER BY priority DESC LIMIT 15"""
                )
                tasks = cursor.fetchall()
                if tasks:
                    task_lines = ["## Active Tasks"]
                    for t in tasks:
                        assigned = t[3] or "unassigned"
                        task_lines.append(f"  - [{t[1]}] status={t[2]}, assigned={assigned}, priority={t[4]}")
                    sections.append("\n".join(task_lines))
        except Exception:
            pass

        # --- 4. Communication channels ---
        comm_info = [
            "## Communication",
            "- Board members deliberate through sequential rounds (Chair synthesizes each round)",
            "- Board → Agent: dispatch tasks via dispatch_agent tool or DISPATCH: directive",
            "- Agent → Board: results returned as tool output after execution",
            "- Agent ↔ Agent: via workspace_sharing message bus (tracked in agent_communication table)",
            "- Teams → Board: progress updates via task status changes",
            "- CEO (user) participates between rounds — Chair relays questions",
        ]
        sections.append("\n".join(comm_info))

        # --- 5. Available data sources ---
        data_sources = ["## Data Sources"]
        try:
            import os
            db_dir = os.path.expanduser("~/jarvis/Database/v2")
            if os.path.isdir(db_dir):
                dbs = [f for f in os.listdir(db_dir) if f.endswith('.db')]
                if dbs:
                    data_sources.append("Databases: " + ", ".join(sorted(dbs)))
        except Exception:
            pass

        try:
            import os
            vault_dir = os.path.expanduser("~/jarvis/knowledge")
            if os.path.isdir(vault_dir):
                vault_count = sum(1 for f in os.listdir(vault_dir) if f.endswith('.md'))
                data_sources.append(f"Knowledge vault: {vault_count} documents (searchable via FTS5)")
        except Exception:
            pass

        data_sources.append("Live APIs: OANDA (forex), News MCP, Wolfram MCP")
        sections.append("\n".join(data_sources))

        if not sections:
            return ""

        return "\n\n" + "\n\n".join(sections) + "\n"

    def _get_agent_tools(self, agent_name: str) -> list:
        """Get Anthropic-format tool definitions for an agent from its MCP handlers.
        
        Deduplicates by tool name — Anthropic API requires unique tool names.
        When duplicates exist, first occurrence wins.
        """
        servers = self._launch_agent_mcps(agent_name)
        all_tools = []
        seen_names = set()
        for short_name, info in servers.items():
            for tool in info["tools"]:
                name = tool.get("name", "")
                if name and name not in seen_names:
                    all_tools.append(tool)
                    seen_names.add(name)
                elif name:
                    logger.debug("Skipping duplicate tool '%s' from %s", name, short_name)
        return all_tools

    def _execute_agent_mcp_call(self, agent_name: str, tool_name: str, arguments: dict) -> str:
        """Execute a tool call through workspace_sharing.execute_method_via_mcp.

        Routes the LLM's tool call through the same workspace MCP path that
        execute_tool() uses — handler methods invoked via workspace context.
        """
        # --- Normalize LLM tool arguments ---
        # Local models (Qwen3) sometimes wrap args in {"parameters": "{\"cmd\": ...}"}
        # because the tool schema exposes `parameters` as the only arg.
        # Unwrap to the format the handler method actually expects.
        if tool_name == "execute_command" and "parameters" in arguments:
            inner = arguments["parameters"]
            if isinstance(inner, str):
                try:
                    inner = json.loads(inner)
                except (json.JSONDecodeError, TypeError):
                    inner = {"command": inner}
            if isinstance(inner, dict):
                # Map various key names to "command"
                cmd = inner.get("command") or inner.get("cmd") or inner.get("parameters", "")
                arguments = {"command": cmd} if isinstance(cmd, str) else inner
        # Also handle direct {"cmd": "..."} without wrapping
        if tool_name == "execute_command" and "cmd" in arguments and "command" not in arguments:
            arguments["command"] = arguments.pop("cmd")
        agent = self.agents.get(agent_name)
        if not agent or not agent.mcp_tools:
            return json.dumps({"error": f"Agent {agent_name} has no MCP tools"})

        # Find which handler has this method
        servers = self._launch_agent_mcps(agent_name)
        for short_name, info in servers.items():
            if tool_name in info.get("methods", []):
                # Use the registry key for workspace routing (e.g. "news" not "news_info")
                handler_key = info.get("registry_key", short_name)
                # Route through workspace sharing — the proven path
                if self._workspace_id and self._workspace_sharing:
                    try:
                        coro = self._workspace_sharing.execute_method_via_mcp(
                            workspace_id=self._workspace_id,
                            handler_name=handler_key,
                            method_name=tool_name,
                            parameters=arguments,
                        )
                        # Run async in sync context
                        try:
                            loop = asyncio.get_running_loop()
                            import concurrent.futures
                            with concurrent.futures.ThreadPoolExecutor() as pool:
                                result = pool.submit(asyncio.run, coro).result()
                        except RuntimeError:
                            result = asyncio.run(coro)

                        logger.info("Agent %s MCP call: %s.%s via workspace %s",
                                   agent_name, short_name, tool_name, self._workspace_id)
                        return json.dumps(result, default=str) if isinstance(result, dict) else str(result)
                    except Exception as exc:
                        logger.error("Workspace MCP call %s.%s failed: %s", short_name, tool_name, exc)
                        return json.dumps({"error": str(exc)})

                # Fallback: direct handler call from cache
                cache_key = None
                for k in getattr(self, '_handler_instance_cache', {}):
                    if k.startswith(short_name):
                        cache_key = k
                        break
                if cache_key and cache_key in self._handler_instance_cache:
                    handler = self._handler_instance_cache[cache_key]
                    method = getattr(handler, tool_name, None)
                    if method:
                        try:
                            result = method(**arguments)
                            return json.dumps(result, default=str) if isinstance(result, dict) else str(result)
                        except Exception as exc:
                            return json.dumps({"error": str(exc)})

        return json.dumps({"error": f"Tool {tool_name} not found on any handler for agent {agent_name}"})
    # ------------------------------------------------------------------
    # Agent Task Execution — LLM + MCP tool_use loop
    # ------------------------------------------------------------------

    async def execute_agent_task(self, agent_name: str, task: str,
                                  context: dict = None, max_tokens: int = 4096,
                                  max_tool_rounds: int = 10,
                                  images: list = None) -> HandlerResult:
        """Execute a task using an agent's LLM with MCP tool access.

        This is the core agent execution method. It:
        1. Loads the agent's system prompt (instructions)
        2. Launches the agent's MCP servers and gets tool definitions
        3. Calls Anthropic with the task + tools
        4. Runs the tool_use loop (agent calls MCP → execute → return → agent continues)
        5. Returns the agent's final structured response

        Parameters
        ----------
        agent_name : str
            Name of the agent to execute as.
        task : str
            The task description / user message for the agent.
        context : dict, optional
            Additional context (prior agent results, market data, etc.)
        max_tokens : int
            Max output tokens for the LLM.
        max_tool_rounds : int
            Max tool_use iterations to prevent runaway loops.

        Returns
        -------
        HandlerResult
            The agent's response with tool call history.
        """
        agent = self.agents.get(agent_name)
        if not agent:
            return self.create_error_result(f"Agent {agent_name} not registered in swarm")

        effective_model_check = agent.model or SWARM_MODEL
        if not effective_model_check.startswith("mlx/") and not self.anthropic_client:
            return self.create_error_result("Anthropic client not initialized (needed for cloud models)")

        # 1. Build system prompt from agent instructions.
        # Agents with a distilled local variant carry _instructions_local (lean prompt)
        # alongside agent.instructions (full cloud prompt). Pick based on active model
        # so flipping validator between mlx/CSO and claude-sonnet-4-6 auto-swaps the prompt.
        _model_for_prompt = agent.model or SWARM_MODEL
        _local_prompt = getattr(agent, "_instructions_local", None)
        if _local_prompt and _model_for_prompt.startswith("mlx/"):
            system_prompt = _local_prompt
        else:
            system_prompt = agent.instructions or f"You are {agent_name}, a trading agent."

        # 2. Get MCP tools for this agent (skip if max_tool_rounds=0 — pure LLM synthesis)
        tools = self._get_agent_tools(agent_name) if max_tool_rounds > 0 else []
        logger.info(
            "Agent %s executing task: %d tools available, prompt=%d chars",
            agent_name, len(tools), len(system_prompt),
        )

        # 3. Build user message with task + context
        user_content = task
        if context:
            try:
                ctx_str = json.dumps(context, indent=2, default=str)
                user_content = f"{task}\n\n## Context\n```json\n{ctx_str}\n```"
            except Exception:
                user_content = f"{task}\n\n## Context\n{str(context)[:2000]}"

        # 3b. Vision support — build multi-part content when images provided
        if images and isinstance(images, list) and len(images) > 0:
            # Build content array: text + interleaved images
            content_blocks = []
            for img in images:
                # Each image: {"b64": "...", "media_type": "image/png", "description": "..."}
                if img.get("b64"):
                    content_blocks.append({
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": img.get("media_type", "image/png"),
                            "data": img["b64"],
                        },
                    })
                if img.get("description"):
                    content_blocks.append({
                        "type": "text",
                        "text": img["description"],
                    })
            # Add the main task text after images
            content_blocks.append({"type": "text", "text": user_content})
            messages = [{"role": "user", "content": content_blocks}]
            logger.info("Agent %s: vision mode with %d images + text", agent_name, len(images))
        else:
            messages = [{"role": "user", "content": user_content}]

        tool_call_log = []
        effective_model = agent.model or SWARM_MODEL

        # 4. LLM call — local MLX model path
        is_local = effective_model.startswith("mlx/")

        if is_local:
            # --- LOCAL MODEL PATH: MLX backend (Apple Silicon, OpenAI-compat API) ---
            #
            # CAPABILITY-BASED:
            # - Models with tool support (qwen*): get MCP tools directly for speed
            #   PLUS dispatch_agent for delegating to other agents
            # - Models without tool support (deepseek-r1, CTO seat): get text-based
            #   DISPATCH: directives to request data from agents
            #
            # ALL board members get full workspace architecture context so they
            # understand the teams, agents, tasks, and communication channels
            # they're directing.
            import re as _re
            import urllib.request

            # MLX server config — maps board seat names to ports and HF repo names
            MLX_SERVERS = {
                "CRO": {"port": 11500, "hf_repo": "mlx-community/Qwen3.5-9B-4bit"},
                "CTO": {"port": 11501, "hf_repo": "mlx-community/DeepSeek-R1-Distill-Qwen-14B-4bit"},
                "CSO": {"port": 11503, "hf_repo": "mlx-community/Qwen3.5-35B-A3B-4bit"},  # via serving gateway
                "CDO": {"port": 11503, "hf_repo": "mlx-community/Qwen2.5-7B-Instruct-4bit"},
                "Coder": {"port": 11504, "hf_repo": "mlx-community/Qwen2.5-Coder-32B-Instruct-4bit"},
            }

            mlx_seat = effective_model.replace("mlx/", "")
            mlx_cfg = MLX_SERVERS.get(mlx_seat) or MLX_SERVERS.get(agent_name)
            if not mlx_cfg:
                raise RuntimeError(
                    f"No MLX config for seat '{mlx_seat}' (agent={agent_name}). "
                    f"Known seats: {list(MLX_SERVERS.keys())}"
                )
            llm_endpoint = f"http://127.0.0.1:{mlx_cfg['port']}/v1/chat/completions"
            request_model = mlx_cfg["hf_repo"]
            logger.info("Agent %s using MLX backend on port %d (%s)",
                       agent_name, mlx_cfg['port'], mlx_cfg['hf_repo'])

            # Seats that don't support OpenAI tool calling
            NO_TOOL_SEATS = {"CTO"}  # DeepSeek R1 distill — no tool support
            supports_tools = mlx_seat not in NO_TOOL_SEATS

            # --- Build workspace architecture context ---
            # Only boardroom agents (CTO, CSO, CRO, CDO, Opus) need org/workspace context.
            # Trading team agents are a separate operational layer — they must NOT receive
            # boardroom structure, board member lists, or cross-team workspace data.
            # Injecting it causes 10-12K token bloat → prefill timeouts on local models.
            _BOARDROOM_AGENTS = {"CTO", "CSO", "CRO", "CDO", "Opus", "opus"}
            if agent_name in _BOARDROOM_AGENTS:
                workspace_context = self._build_workspace_context(agent_name)
            else:
                workspace_context = ""

            # --- Build tools list (capable models only) ---
            openai_tools = []
            dispatch_instruction = ""

            if supports_tools and max_tool_rounds > 0:
                # 1. MCP tools (from handler introspection)
                for t in tools:
                    openai_tools.append({
                        "type": "function",
                        "function": {
                            "name": t.get("name", ""),
                            "description": t.get("description", ""),
                            "parameters": t.get("input_schema", {"type": "object", "properties": {}}),
                        }
                    })

                # 2. Python callable tools (from agent.tools)
                #    Introspect function signatures to build clean schemas.
                #    Any agent can register Python functions as tools.
                callable_tools = agent.tools if hasattr(agent, 'tools') and agent.tools else []
                for func in callable_tools:
                    if not callable(func):
                        continue
                    try:
                        sig = inspect.signature(func)
                        props = {}
                        required = []
                        for pname, param in sig.parameters.items():
                            if pname == 'self':
                                continue
                            props[pname] = {"type": "string", "description": pname}
                            if param.default is inspect.Parameter.empty:
                                required.append(pname)
                            else:
                                props[pname]["default"] = str(param.default) if param.default is not None else ""
                        openai_tools.append({
                            "type": "function",
                            "function": {
                                "name": func.__name__,
                                "description": (func.__doc__ or f"Call {func.__name__}")[:200].strip(),
                                "parameters": {
                                    "type": "object",
                                    "properties": props,
                                    "required": required,
                                },
                            }
                        })
                    except (ValueError, TypeError) as exc:
                        logger.warning("Skipping callable tool %s: %s", getattr(func, '__name__', '?'), exc)

                if callable_tools:
                    logger.info("Agent %s: %d MCP tools + %d callable tools exposed",
                               agent_name, len(tools), len(callable_tools))

                # Also give dispatch_agent for delegating complex tasks
                openai_tools.append({
                    "type": "function",
                    "function": {
                        "name": "dispatch_agent",
                        "description": "Delegate a task to a worker agent. The agent runs with its own tools and returns findings. Use for complex multi-step research or when you need a specialist.",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "agent_name": {"type": "string", "description": "Agent name from the team roster"},
                                "task": {"type": "string", "description": "What you need the agent to do"},
                            },
                            "required": ["agent_name", "task"]
                        }
                    }
                })

                logger.info("Agent %s (local/tools): %d MCP tools + dispatch_agent, seat=%s",
                           agent_name, len(openai_tools) - 1, mlx_seat)
            elif not supports_tools and max_tool_rounds > 0:
                # Text-based dispatch — ONLY for non-tool-capable models (e.g. DeepSeek R1)
                # that still want multi-turn delegation. Adds a DISPATCH: directive hint
                # to the system prompt so the model can request data via text patterns.
                dispatch_instruction = (
                    "\n\n## Requesting Information\n"
                    "You cannot call tools directly. To request data from an agent, "
                    "include a DISPATCH directive:\n"
                    "DISPATCH: agent_name | task description\n\n"
                    "Example: DISPATCH: Technical_Analyst | Pull EUR_USD H1 candle data and EMA separation for last 48 hours\n\n"
                    "You can include multiple DISPATCH lines. I will run the agents and "
                    "return their findings. Then give your analysis.\n"
                    "If you already have enough context, skip DISPATCH and go straight to your analysis.\n"
                )
                logger.info("Agent %s (local/no-tools): text dispatch mode, seat=%s",
                           agent_name, mlx_seat)
            else:
                # Single-shot path: tool-capable model with max_tool_rounds=0 (intentional
                # single-shot, e.g. validator in automated cycle), or non-tool model with
                # max_tool_rounds=0. NO tools, NO dispatch hint — clean vision/text answer
                # matching ghost_replay's payload shape exactly.
                logger.info("Agent %s (local/single-shot): no tools, no dispatch hint, seat=%s",
                           agent_name, mlx_seat)

            # Augment system prompt with architecture + dispatch instructions
            augmented_system = system_prompt + workspace_context + dispatch_instruction

            # Build user content for the MLX endpoint. The MLX VLM server expects
            # OpenAI image_url format; Anthropic-style image blocks return 422.
            # When images are passed, build a multipart array (image_url + text).
            # When no images, plain string is equivalent (text-only agents).
            # The bug being fixed: this branch previously built a string-only user
            # message, silently dropping the chart for vision agents (validator).
            if images:
                mlx_user_content = []
                for img in images:
                    if img.get("b64"):
                        media = img.get("media_type", "image/png")
                        mlx_user_content.append({
                            "type": "image_url",
                            "image_url": {"url": f"data:{media};base64,{img['b64']}"},
                        })
                    if img.get("description"):
                        mlx_user_content.append({"type": "text", "text": img["description"]})
                mlx_user_content.append({"type": "text", "text": user_content})
                mlx_messages = [
                    {"role": "system", "content": augmented_system},
                    {"role": "user", "content": mlx_user_content},
                ]
            else:
                mlx_messages = [
                    {"role": "system", "content": augmented_system},
                    {"role": "user", "content": user_content},
                ]

            # ── TEMP DEBUG: dump validator vision payload so we can replay it ──
            # Remove after isolating the production-vs-test divergence.
            if agent_name == "validator" and images:
                try:
                    import time as _t_dbg
                    _dbg_path = f"/tmp/validator_payload_{int(_t_dbg.time())}.json"
                    _redacted = []
                    for _m in mlx_messages:
                        _content = _m.get("content")
                        if isinstance(_content, list):
                            _new_blocks = []
                            for _b in _content:
                                if isinstance(_b, dict) and _b.get("type") == "image_url":
                                    _url = _b.get("image_url", {}).get("url", "")
                                    _new_blocks.append({
                                        "type": "image_url",
                                        "image_url_truncated": _url[:80] + "..." + _url[-20:] if len(_url) > 100 else _url,
                                        "image_url_length": len(_url),
                                    })
                                else:
                                    _new_blocks.append(_b)
                            _redacted.append({"role": _m.get("role"), "content": _new_blocks})
                        else:
                            _redacted.append({"role": _m.get("role"),
                                              "content_len": len(_content) if isinstance(_content, str) else 0,
                                              "content_preview": (_content or "")[:500] if isinstance(_content, str) else _content})
                    with open(_dbg_path, "w") as _df:
                        json.dump({
                            "agent": agent_name,
                            "model": request_model,
                            "max_tool_rounds": max_tool_rounds,
                            "tools_count": len(openai_tools),
                            "messages": _redacted,
                        }, _df, indent=2, default=str)
                    logger.info("[VALIDATOR PAYLOAD DUMP] %s", _dbg_path)
                except Exception as _dbg_exc:
                    logger.warning("payload dump failed: %s", _dbg_exc)

            for round_num in range(max(1, max_tool_rounds)):
                try:
                    payload = {
                        "model": request_model,
                        "messages": mlx_messages,
                        "temperature": 0,
                        "max_tokens": max_tokens,
                        # Disable Qwen3 extended thinking for all local agents.
                        # Without this, Qwen3.5-9B generates 10-16K token <think> blocks
                        # before answering — adding 30-60s latency per call.
                        # Trading agents (TA, reporter, orchestrator) don't need deep reasoning.
                        "chat_template_kwargs": {"enable_thinking": False},
                    }
                    if openai_tools:
                        payload["tools"] = openai_tools

                    # Tag the gateway with the right tenant so swarm-dispatched
                    # agents land at the correct priority. Boardroom seats route
                    # to 'boardroom' (5); everyone else (validator, TA, etc.) is
                    # the trading lane (0). Without this header, swarm calls
                    # land as tenant=default (priority 7) which is *behind* the
                    # 5 directly-migrated trading helpers — backwards.
                    _tenant_header = "boardroom" if agent_name in _BOARDROOM_AGENTS else "trading"

                    req = urllib.request.Request(
                        llm_endpoint,
                        data=json.dumps(payload).encode(),
                        headers={
                            "Content-Type": "application/json",
                            "X-Jarvis-Tenant": _tenant_header,
                        },
                    )
                    # Timeouts sized for local-model queue wait. With scout firing 5 cycles
                    # concurrently, pair 5's validator physically waits 4×~120s behind prior
                    # cycles on the 35B (single MLX server, one request at a time), then runs
                    # its own ~120s = ~625s end-to-end. Need ≥900s to cover without killing
                    # patient queued requests. Prior 300s timed out cycles 3-5 under load.
                    if agent_name == "validator":
                        _local_timeout = 900
                    elif agent_name == "technical_analyst":
                        _local_timeout = 240
                    else:
                        _local_timeout = 120
                    resp = urllib.request.urlopen(req, timeout=_local_timeout)
                    data = json.loads(resp.read())
                except Exception as exc:
                    # Local model failed — NO paid fallback. Error out cleanly.
                    # Haiku fallback REMOVED 2026-03-31: was silently burning API credits
                    # when 9B timed out. 9B handles all non-validator agent roles.
                    logger.error("Agent %s local LLM call failed (round %d): %s — NO FALLBACK (paid fallback disabled)",
                                 agent_name, round_num, exc)
                    return self.create_error_result(f"Local LLM call failed: {exc}")

                choice = data["choices"][0]
                msg = choice["message"]
                finish = choice.get("finish_reason", "stop")

                # Extract content (handle thinking models — reasoning_content)
                content = msg.get("content") or ""
                reasoning = msg.get("reasoning_content") or msg.get("reasoning") or ""
                if not content.strip() and reasoning:
                    content = reasoning
                if "<think>" in content:
                    content = _re.sub(r"<think>.*?</think>", "", content, flags=_re.DOTALL).strip()

                # 2026-04-28 capture: when validator emits 0-char post-strip,
                # dump the raw msg so we can see what the model ACTUALLY returned
                # (only-<think>? empty? reasoning-only? prose?). One file per failure.
                if agent_name == "validator" and not content.strip():
                    try:
                        import time as _ts
                        _dump = {
                            "timestamp": _ts.time(),
                            "agent": agent_name,
                            "finish_reason": finish,
                            "raw_msg": msg,
                            "raw_content_len": len(msg.get("content") or ""),
                            "raw_reasoning_len": len(msg.get("reasoning_content") or msg.get("reasoning") or ""),
                            "had_think_tag": "<think>" in (msg.get("content") or ""),
                            "usage": data.get("usage", {}),
                            "round_num": round_num,
                        }
                        _path = f"/tmp/validator_empty_{int(_ts.time())}.json"
                        with open(_path, "w") as _f:
                            json.dump(_dump, _f, default=str, indent=2)
                        logger.warning("[VALIDATOR EMPTY DUMP] wrote raw response to %s "
                                       "(content_len=%d reasoning_len=%d had_think=%s finish=%s)",
                                       _path, _dump["raw_content_len"], _dump["raw_reasoning_len"],
                                       _dump["had_think_tag"], finish)
                    except Exception as _dump_exc:
                        logger.warning("[VALIDATOR EMPTY DUMP] failed: %s", _dump_exc)

                # --- Handle OpenAI-style tool calls (qwen, etc.) ---
                # 2026-04-28: removed `finish == "tool_calls"` gate. The MLX VLM
                # server returns finish_reason="stop" on multimodal+tool-call
                # combos even when tool_calls are populated, causing them to be
                # silently dropped. Presence of tool_calls is the authoritative
                # signal to execute. Diagnosis: validator was calling
                # get_upcoming_news for the intelligence cache, the call got
                # dropped, content was empty, validator returned 0 chars and
                # downstream parser failed twice → GATE1_BLOCK.
                if msg.get("tool_calls"):
                    mlx_messages.append(msg)

                    for tc in msg["tool_calls"]:
                        fn = tc["function"]
                        tool_name = fn["name"]
                        try:
                            tool_args = json.loads(fn["arguments"]) if isinstance(fn["arguments"], str) else fn["arguments"]
                        except json.JSONDecodeError:
                            tool_args = {}

                        if tool_name == "dispatch_agent":
                            # Delegate to another agent (prevent self-dispatch recursion)
                            target_agent = tool_args.get("agent_name", "")
                            dispatch_task = tool_args.get("task", "")
                            logger.info("Board %s → dispatch %s: %s",
                                       agent_name, target_agent, dispatch_task[:100])

                            if target_agent == agent_name:
                                tool_output = "[Cannot dispatch to self — answer directly from your expertise]"
                            else:
                                worker_result = await self.execute_agent_task(
                                    agent_name=target_agent,
                                    task=dispatch_task,
                                    context=context,
                                    max_tokens=2048,
                                    max_tool_rounds=3,  # Limit recursion depth
                                )
                                if worker_result.success and worker_result.data:
                                    tool_output = worker_result.data.get("response", str(worker_result.data))
                                else:
                                    tool_output = f"[Agent {target_agent} error: {worker_result.error}]"
                        else:
                            # Check Python callable tools first, then MCP
                            callable_match = None
                            for func in callable_tools:
                                if callable(func) and getattr(func, '__name__', '') == tool_name:
                                    callable_match = func
                                    break

                            if callable_match:
                                # Direct Python function call
                                logger.info("Board %s → callable %s(%s)",
                                           agent_name, tool_name, str(tool_args)[:100])
                                try:
                                    tool_output = str(callable_match(**tool_args))
                                except Exception as exc:
                                    tool_output = f"Error calling {tool_name}: {exc}"
                                    logger.error("Callable %s failed: %s", tool_name, exc)
                            else:
                                # MCP tool call
                                logger.info("Board %s → MCP tool %s(%s)",
                                           agent_name, tool_name, str(tool_args)[:100])
                                tool_output = self._execute_agent_mcp_call(agent_name, tool_name, tool_args)

                        tool_call_log.append({
                            "tool": tool_name, "input": tool_args,
                            "output_preview": str(tool_output)[:200],
                            "output": str(tool_output),
                            "round": round_num,
                        })

                        mlx_messages.append({
                            "role": "tool",
                            "tool_call_id": tc.get("id", f"call_{round_num}"),
                            "content": str(tool_output)[:4000],
                        })

                    # Re-attach images so the chat template emits <|image_pad|> placeholders
                    # on round 2+. mlx_vlm's Qwen3.5 chat template only inserts placeholders
                    # for the LAST user turn. After tool messages are appended, the original
                    # user-with-images becomes historical and loses placeholders, while the
                    # vision encoder still extracts features from the historical image_url
                    # blocks — producing the ValueError(tokens:0, features:N) crash.
                    # Re-attaching the same images at the tail makes the tool-result the
                    # context and the chart the current input, restoring vision on every round.
                    if images:
                        _reattach_content = []
                        for _img in images:
                            if _img.get("b64"):
                                _media = _img.get("media_type", "image/png")
                                _reattach_content.append({
                                    "type": "image_url",
                                    "image_url": {"url": f"data:{_media};base64,{_img['b64']}"},
                                })
                        _reattach_content.append({
                            "type": "text",
                            "text": "Continue your analysis using the tool result above. The chart and any reference images are re-attached so you can keep them in view.",
                        })
                        mlx_messages.append({"role": "user", "content": _reattach_content})

                    continue  # next round

                # --- Handle text-based DISPATCH: directives (deepseek-r1) ---
                dispatch_matches = _re.findall(
                    r'DISPATCH:\s*(\S+)\s*\|\s*(.+?)(?:\n|$)', content, _re.IGNORECASE
                )
                if dispatch_matches and round_num < max_tool_rounds - 1:
                    agent_results = []
                    for target_agent, dispatch_task in dispatch_matches:
                        logger.info("Board %s (text) → %s: %s",
                                   agent_name, target_agent, dispatch_task[:100])

                        worker_result = await self.execute_agent_task(
                            agent_name=target_agent,
                            task=dispatch_task.strip(),
                            context=context,
                            max_tokens=2048,
                            max_tool_rounds=5,
                        )
                        if worker_result.success and worker_result.data:
                            agent_response = worker_result.data.get("response", str(worker_result.data))
                        else:
                            agent_response = f"[Agent {target_agent} error: {worker_result.error}]"

                        agent_results.append(f"### {target_agent} reports:\n{agent_response[:2000]}")
                        tool_call_log.append({
                            "tool": "dispatch_agent",
                            "input": {"agent_name": target_agent, "task": dispatch_task.strip()},
                            "output_preview": agent_response[:200],
                            "output": agent_response,
                            "round": round_num,
                        })

                    # Feed results back
                    mlx_messages.append({"role": "assistant", "content": content})
                    mlx_messages.append({
                        "role": "user",
                        "content": "## Agent Reports\n\n" + "\n\n".join(agent_results) +
                                   "\n\nSynthesize these findings into your analysis."
                    })
                    continue  # next round

                # --- Final response (no more dispatches) ---
                final_text = content
                input_tokens = data.get("usage", {}).get("prompt_tokens", 0)
                output_tokens = data.get("usage", {}).get("completion_tokens", 0)

                logger.info(
                    "Agent %s done (local): %d tool/dispatch calls, %d chars, model=%s",
                    agent_name, len(tool_call_log), len(final_text), effective_model,
                )

                await self.track_agent_activity(
                    agent_id=agent_name, agent_name=agent_name,
                    action_type="task_execution",
                    details={
                        "task": task[:200], "tool_calls": len(tool_call_log),
                        "response_length": len(final_text),
                        "model": effective_model, "rounds": round_num + 1,
                    },
                    agent_type="swarm_agent",
                )

                return self.create_success_result({
                    "agent": agent_name, "response": final_text,
                    "tool_calls": tool_call_log, "model": effective_model,
                    "rounds": round_num + 1,
                    "input_tokens": input_tokens, "output_tokens": output_tokens,
                })

            # Hit max rounds
            return self.create_success_result({
                "agent": agent_name,
                "response": content if content else f"[{agent_name} max rounds ({max_tool_rounds})]",
                "tool_calls": tool_call_log, "model": effective_model,
                "rounds": max_tool_rounds,
                "input_tokens": 0, "output_tokens": 0,
            })

        # --- ANTHROPIC PATH (cloud models with tool_use loop) ---
        # Strip provider prefix before sending to raw SDK (e.g. "anthropic/claude-opus-4..." → "claude-opus-4...")
        bare_model = effective_model
        for prefix in ("anthropic/", "claude-api/"):
            if bare_model.startswith(prefix):
                bare_model = bare_model[len(prefix):]
                break

        for round_num in range(max(1, max_tool_rounds)):
            try:
                kwargs = {
                    "model": bare_model,
                    "max_tokens": max_tokens,
                    "system": system_prompt,
                    "messages": messages,
                    "temperature": 0,
                }
                if tools:
                    kwargs["tools"] = tools

                # Extended thinking models need the beta header and adjusted params
                _thinking_models = ("claude-opus-4", "claude-sonnet-4-5")
                if any(t in bare_model for t in _thinking_models):
                    _budget = 10000
                    kwargs["thinking"] = {"type": "enabled", "budget_tokens": _budget}
                    kwargs["temperature"] = 1
                    kwargs["max_tokens"] = max(kwargs["max_tokens"], _budget + 1000)
                    kwargs["extra_headers"] = {"anthropic-beta": "interleaved-thinking-2025-05-14"}

                response = self.anthropic_client.messages.create(**kwargs)
            except Exception as exc:
                _exc_str = str(exc)
                # Auto-recover: if 400 credit/auth error, re-read key from file and retry once
                if "credit balance" in _exc_str or "invalid_api_key" in _exc_str or "401" in _exc_str:
                    logger.warning("Agent %s: API auth error — re-reading key from file and retrying", agent_name)
                    try:
                        _fresh_key = _load_api_key('CLAUDE')
                        if _fresh_key:
                            from anthropic import Anthropic as _Ant
                            self.anthropic_client = _Ant(api_key=_fresh_key)
                            if hasattr(self, 'llm_router') and self.llm_router:
                                from Handler.modules.claude_client import AnthropicClient
                                _new_ac = AnthropicClient(api_key=_fresh_key)
                                self.llm_router.register_client("anthropic/", _new_ac, is_default=True)
                                self.llm_router.register_client("claude-", _new_ac)
                                self.anthropic_client = _new_ac.client
                            response = self.anthropic_client.messages.create(**kwargs)
                            logger.info("Agent %s: retry with fresh key succeeded", agent_name)
                    except Exception as retry_exc:
                        logger.error("Agent %s LLM call failed after key reload (round %d): %s", agent_name, round_num, retry_exc)
                        return self.create_error_result(f"LLM call failed: {retry_exc}")
                elif any(kw in _exc_str.lower() for kw in ("connection", "timeout", "network", "ssl", "connect", "remote", "eof", "reset", "broken pipe")):
                    # Transient network error — exponential backoff retries (5s, 15s, 45s)
                    import time as _time
                    _retry_delays = [15]  # 1 retry only — outer layers handle longer outages
                    _retry_success = False
                    for _attempt, _delay in enumerate(_retry_delays):
                        logger.warning("Agent %s: connection error (round %d, attempt %d/%d), retrying in %ds: %s",
                                       agent_name, round_num, _attempt + 1, len(_retry_delays), _delay, exc)
                        _time.sleep(_delay)
                        try:
                            response = self.anthropic_client.messages.create(**kwargs)
                            logger.info("Agent %s: connection retry #%d succeeded", agent_name, _attempt + 1)
                            _retry_success = True
                            break
                        except Exception as retry_exc:
                            exc = retry_exc  # update for next iteration / final error
                            if not any(kw in str(retry_exc).lower() for kw in ("connection", "timeout", "network", "ssl", "connect", "remote", "eof", "reset")):
                                # Non-connection error on retry — stop retrying
                                logger.error("Agent %s: non-connection error on retry #%d — stopping: %s", agent_name, _attempt + 1, retry_exc)
                                break
                    if not _retry_success:
                        logger.error("Agent %s: all connection retries exhausted: %s", agent_name, exc)
                        return self.create_error_result(f"LLM call failed: {exc}")
                elif "rate_limit" in _exc_str.lower() or "429" in _exc_str or "rate limit" in _exc_str.lower():
                    # 429 Rate Limited — exponential backoff, up to 3 attempts
                    import time as _time
                    _retry_delays_429 = [5, 10, 20]
                    _retry_success_429 = False
                    for _attempt_429, _delay_429 in enumerate(_retry_delays_429):
                        logger.warning("Agent %s: 429 rate limited (round %d, attempt %d/3) — waiting %ds",
                                       agent_name, round_num, _attempt_429 + 1, _delay_429)
                        _time.sleep(_delay_429)
                        try:
                            response = self.anthropic_client.messages.create(**kwargs)
                            logger.info("Agent %s: 429 retry #%d succeeded", agent_name, _attempt_429 + 1)
                            _retry_success_429 = True
                            break
                        except Exception as retry_exc_429:
                            exc = retry_exc_429
                    if not _retry_success_429:
                        logger.error("Agent %s: all 429 retries exhausted: %s", agent_name, exc)
                        return self.create_error_result(f"LLM call failed (rate limited): {exc}")
                else:
                    logger.error("Agent %s LLM call failed (round %d): %s", agent_name, round_num, exc)
                    return self.create_error_result(f"LLM call failed: {exc}")

            # Check stop reason
            if response.stop_reason == "end_turn" or response.stop_reason != "tool_use":
                # Agent finished — extract text response
                text_parts = []
                for block in response.content:
                    if hasattr(block, 'text'):
                        text_parts.append(block.text)
                final_text = '\n'.join(text_parts)

                logger.info(
                    "Agent %s completed: %d tool calls, %d chars response",
                    agent_name, len(tool_call_log), len(final_text),
                )

                # Track agent communication
                await self.track_agent_activity(
                    agent_id=agent_name,
                    agent_name=agent_name,
                    action_type="task_execution",
                    details={
                        "task": task[:200],
                        "tool_calls": len(tool_call_log),
                        "response_length": len(final_text),
                        "model": agent.model or SWARM_MODEL,
                        "rounds": round_num + 1,
                    },
                    agent_type="swarm_agent",
                )

                return self.create_success_result({
                    "agent": agent_name,
                    "response": final_text,
                    "tool_calls": tool_call_log,
                    "model": agent.model or SWARM_MODEL,
                    "rounds": round_num + 1,
                    "input_tokens": getattr(response.usage, 'input_tokens', 0),
                    "output_tokens": getattr(response.usage, 'output_tokens', 0),
                })

            # Agent wants to call tools
            tool_use_blocks = [b for b in response.content if getattr(b, 'type', '') == 'tool_use']
            if not tool_use_blocks:
                break

            # Execute tool calls
            tool_results = []
            for tool_block in tool_use_blocks:
                tool_name = tool_block.name
                tool_input = tool_block.input
                tool_use_id = tool_block.id

                logger.info("Agent %s calling tool: %s(%s)", agent_name, tool_name, str(tool_input)[:100])

                tool_output = self._execute_agent_mcp_call(agent_name, tool_name, tool_input)

                tool_call_log.append({
                    "tool": tool_name,
                    "input": tool_input,
                    "output_preview": str(tool_output)[:200],
                    "output": str(tool_output),  # Full output for downstream extraction
                    "round": round_num,
                })

                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": tool_use_id,
                    "content": str(tool_output),
                })

            # Append assistant message + tool results for next round
            messages.append({"role": "assistant", "content": response.content})
            messages.append({"role": "user", "content": tool_results})

        # Hit max rounds
        logger.warning("Agent %s hit max tool rounds (%d)", agent_name, max_tool_rounds)
        return self.create_error_result(f"Agent {agent_name} exceeded max tool rounds")

    def _safe_json(self, data):
        """Convert data to a JSON-safe representation."""
        if data is None:
            return {}
        try:
            json.dumps(data)
            return data
        except (TypeError, OverflowError, ValueError):
            return {"str_repr": str(data)[:500]}

    async def handle(self, task_description: Dict[str, Any]) -> HandlerResult:
        """
        Main entry point for handling swarm-related operations.

        Args:
            task_description: Dictionary containing the task details
                - action: String specifying the action to perform
                - parameters: Dictionary of parameters for the action

        Returns:
            HandlerResult object with the operation results
        """
        action = task_description.get("action", "")
        parameters = task_description.get("parameters", {})

        try:
            if action == "register_agent":
                return await self.register_agent(**parameters)
            elif action == "create_team":
                return await self.create_team(**parameters)
            elif action == "start_conversation":
                return await self.start_conversation(**parameters)
            elif action == "send_message":
                return await self.send_message(**parameters)
            elif action == "execute_tool":
                return await self.execute_tool(**parameters)
            elif action == "get_conversation_history":
                return await self.get_conversation_history(**parameters)
            elif action == "distribute_tasks":
                return await self.distribute_tasks(**parameters)
            elif action == "get_status":
                return await self.get_status(**parameters)
            elif action == "coordinate_parallel":
                return await self.coordinate_parallel(**parameters)
            elif action == "assign_work":
                return await self.assign_work(**parameters)
            elif action == "find_agent":
                return await self._handle_find_agent(**parameters)
            elif action == "get_agent":
                return await self._handle_get_agent(**parameters)
            elif action == "list_agents":
                return await self._handle_list_agents(**parameters)
            elif action == "get_top_agents":
                return await self._handle_get_top_agents(**parameters)
            elif action == "clone_agent":
                return await self._handle_clone_agent(**parameters)
            elif action == "get_team_performance":
                return await self._handle_get_team_performance(**parameters)
            elif action == "execute_agent_task":
                return await self.execute_agent_task(**parameters)
            elif action == "sequential_deliberation":
                return await self.sequential_deliberation(**parameters)
            else:
                return self.create_error_result(f"Unknown action: {action}")
        except Exception as e:
            logger.error(f"Error in SwarmHandler.handle: {str(e)}")
            logger.debug(traceback.format_exc())
            return self.create_error_result(f"Error in SwarmHandler: {str(e)}")

    async def track_journey_step(self, journey_id, step_name, description=None,
                                 step_type=None, input_data=None, output_data=None,
                                 error=None, _prevent_recursion=False):
        """Track a step in a journey. Uses BoardRoom if available, falls back to local tracking."""
        if _prevent_recursion:
            if not hasattr(self, 'tracking_data'):
                self.tracking_data = {}
            if journey_id not in self.tracking_data:
                self.tracking_data[journey_id] = []
            self.tracking_data[journey_id].append({
                'step_name': step_name,
                'description': description,
                'step_type': step_type,
                'error': str(error) if error else None,
                'status': "completed",
                'timestamp': time_module.time()
            })
            logger.info(f"Journey step (local tracking): {journey_id} - {step_name}")
            return True

        step_data = {}
        if description:
            step_data['description'] = description
        if step_type:
            step_data['step_type'] = step_type

        # Handle complex data structures safely
        for key, val in [('input_data', input_data), ('output_data', output_data)]:
            if val:
                try:
                    json.dumps(val)
                    step_data[key] = val
                except (TypeError, OverflowError, ValueError):
                    step_data[key] = str(val)[:500]

        step_data['timestamp'] = time_module.time()
        if error:
            step_data['error'] = str(error)

        logger.debug(f"Journey {journey_id}: {step_name}")

        try:
            if hasattr(self, 'boardroom') and self.boardroom is not None:
                if hasattr(self.boardroom, 'track_journey_step'):
                    if asyncio.iscoroutinefunction(self.boardroom.track_journey_step):
                        return await self.boardroom.track_journey_step(
                            journey_id=journey_id, step_name=step_name,
                            description=description, step_type=step_type,
                            input_data=step_data.get('input_data'),
                            output_data=step_data.get('output_data'), error=error
                        )
                    else:
                        self.boardroom.track_journey_step(
                            journey_id=journey_id, step_name=step_name,
                            description=description, step_type=step_type,
                            input_data=step_data.get('input_data'),
                            output_data=step_data.get('output_data'), error=error
                        )
                        return True

            try:
                from Jarvis_Agent_SDK.boardroom_connector import track_journey_step_async
                return await track_journey_step_async(
                    journey_id=journey_id, step_name=step_name,
                    description=description, step_type=step_type,
                    input_data=step_data.get('input_data'),
                    output_data=step_data.get('output_data'), error=error
                )
            except ImportError:
                logger.warning("Could not import track_journey_step_async, falling back to local")

            return await self.track_journey_step(
                journey_id=journey_id, step_name=step_name,
                description=description, step_type=step_type,
                input_data=input_data, output_data=output_data,
                error=error, _prevent_recursion=True
            )

        except Exception as e:
            logger.warning(f"Error in track_journey_step: {str(e)}")
            return await self.track_journey_step(
                journey_id=journey_id, step_name=step_name,
                description=description, step_type=step_type,
                input_data=input_data, output_data=output_data,
                error=f"External tracking failed: {str(e)}",
                _prevent_recursion=True
            )

    async def register_agent(self, agent=None, **kwargs) -> HandlerResult:
        """Register an agent with the swarm handler."""
        try:
            if agent is None:
                agent = SwarmAgent(
                    name=kwargs.get('name', f'agent_{int(time_module.time())}'),
                    instructions=kwargs.get('instructions', 'You are a helpful agent.'),
                    tools=kwargs.get('tools', []),
                    mcp_tools=kwargs.get('mcp_tools', []),
                    model=kwargs.get('model') or SWARM_MODEL
                )

            self.agents[agent.name] = agent
            agent_id = f"{agent.name}_{int(time_module.time())}"

            logger.info(f"Registered agent: {agent.name} with model {agent.model}")

            current_timestamp = int(time_module.time())
            workspace_id = f"swarm_{current_timestamp}"

            await self.track_agent_activity(
                agent_id=agent_id,
                agent_name=agent.name,
                action_type="registration",
                details={
                    "model": agent.model,
                    "tools_count": len(agent.tools) if hasattr(agent, 'tools') else 0,
                    "mcp_tools_count": len(agent.mcp_tools) if hasattr(agent, 'mcp_tools') else 0,
                    "mcp_tools": agent.mcp_tools if hasattr(agent, 'mcp_tools') else [],
                    "registration_time": current_timestamp
                },
                agent_type="swarm_agent",
                workspace_id=workspace_id,
                performance_metrics={"registration_timestamp": current_timestamp}
            )

            # Try to register with AgentRegistryHandler
            try:
                from Handler.handler_agent_registry import AgentRegistryHandler
                registry_handler = AgentRegistryHandler()

                capabilities = []
                if hasattr(agent, 'tools') and agent.tools:
                    for tool in agent.tools:
                        if hasattr(tool, '__name__'):
                            capabilities.append(tool.__name__)
                if hasattr(agent, 'mcp_tools') and agent.mcp_tools:
                    capabilities.extend([f"mcp:{t}" for t in agent.mcp_tools])

                metadata = {
                    "model": agent.model,
                    "instructions": (agent.instructions[:100] + "..."
                                     if len(agent.instructions) > 100 else agent.instructions),
                    "registered_by": "SwarmHandler",
                    "registration_time": time_module.time()
                }

                result_coro = registry_handler.register_module_agent(
                    agent_id=agent_id,
                    agent_name=agent.name,
                    agent_type="swarm_agent",
                    module_name="swarm_handler",
                    capabilities=capabilities,
                    metadata=metadata
                )

                if asyncio.iscoroutine(result_coro):
                    await result_coro

                logger.info(f"Agent {agent.name} registered with AgentRegistryHandler")
            except Exception as e:
                logger.warning(f"Could not register agent with AgentRegistryHandler: {str(e)}")

            # Assign agent to workspace (persistent DB tracking)
            await self._assign_agent_to_workspace(agent_id, agent.name, role="contributor")

            return self.create_success_result({
                "agent_id": agent_id,
                "agent_name": agent.name,
                "workspace_id": self._workspace_id,
                "message": f"Agent {agent.name} registered successfully"
            })

        except Exception as e:
            logger.error(f"Error registering agent: {str(e)}")
            return self.create_error_result(f"Failed to register agent: {str(e)}")

    async def track_agent_activity(self, agent_id, agent_name, action_type, details=None,
                                   agent_type=None, workspace_id=None, performance_metrics=None):
        """Track agent activity for monitoring and analytics."""
        try:
            timestamp = time_module.time()
            agent_type = agent_type or "swarm_agent"
            workspace_id = workspace_id or f"default_{int(timestamp)}"
            journey_id = f"agent_activity_{agent_name}_{int(timestamp)}"

            safe_details = self._safe_json(details)
            safe_metrics = self._safe_json(performance_metrics)

            safe_input_data = {
                "agent_id": agent_id,
                "agent_name": agent_name,
                "agent_type": agent_type,
                "workspace_id": workspace_id,
                "action_type": action_type,
                "details": safe_details,
                "performance_metrics": safe_metrics,
                "timestamp": timestamp
            }

            await self.track_journey_step(
                journey_id=journey_id,
                step_name=f"agent_{action_type}",
                description=f"Agent {agent_name} performed {action_type}",
                step_type="agent_activity",
                input_data=safe_input_data,
                _prevent_recursion=True
            )

            try:
                with v2_connection("agents") as _aconn:
                    _aconn.execute(
                        """INSERT INTO agent_activity
                        (agent_id, agent_name, agent_type, workspace_id, action_type,
                         details, performance_metrics, timestamp)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                        (agent_id, agent_name, agent_type, workspace_id, action_type,
                         json.dumps(safe_details), json.dumps(safe_metrics), timestamp)
                    )
                logger.info(f"Agent activity tracked: {agent_name} - {action_type}")
            except Exception as db_error:
                logger.error(f"Error storing agent activity in database: {str(db_error)}")

            return True
        except Exception as e:
            logger.error(f"Error tracking agent activity: {str(e)}")
            return False

    async def track_agent_communication(self, sender_agent_id, sender_agent_name,
                                        receiver_agent_id, receiver_agent_name, task_id,
                                        journey_id=None, message_type=None, content=None,
                                        metadata=None, workspace_id="default"):
        """Track communication between agents."""
        try:
            message_id = f"msg_{int(time_module.time())}_{hashlib.md5(str(time_module.time()).encode()).hexdigest()[:8]}"
            timestamp = datetime.now().isoformat()
            content_summary = content[:100] + "..." if content and len(content) > 100 else content

            if not journey_id:
                journey_id = f"comm_{sender_agent_id}_{receiver_agent_id}_{hashlib.md5(str(time_module.time()).encode()).hexdigest()[:8]}"

            await self.track_journey_step(
                journey_id=journey_id,
                step_name="agent_communication",
                description=f"Communication from {sender_agent_name} to {receiver_agent_name}",
                step_type="agent_communication",
                input_data={
                    "sender_agent_id": sender_agent_id,
                    "sender_agent_name": sender_agent_name,
                    "receiver_agent_id": receiver_agent_id,
                    "receiver_agent_name": receiver_agent_name,
                    "task_id": task_id,
                    "message_type": message_type,
                    "content_summary": content_summary,
                    "metadata": metadata
                },
                _prevent_recursion=True
            )

            try:
                with v2_connection("agents") as _aconn:
                    _aconn.execute(
                        """INSERT INTO agent_communication (
                            message_id, sender_agent_id, sender_agent_name,
                            receiver_agent_id, receiver_agent_name, task_id,
                            message_type, content, metadata, timestamp,
                            journey_id, workspace_id
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                        (message_id, sender_agent_id, sender_agent_name,
                         receiver_agent_id, receiver_agent_name, task_id,
                         message_type, content, json.dumps(metadata) if metadata else None,
                         timestamp, journey_id, workspace_id)
                    )
            except Exception as db_error:
                logger.error(f"Failed to store agent communication: {str(db_error)}")

            logger.info(
                f"Agent Communication: {sender_agent_name} -> {receiver_agent_name}, "
                f"Type: {message_type}, Task: {task_id}"
            )
            return True
        except Exception as e:
            logger.error(f"Error tracking agent communication: {str(e)}")
            return False


    # -----------------------------------------------------------------------
    # Tracking methods migrated from handler_board_room.py (Phase 3)
    # These ensure no tracking capability is lost when boardroom = workspace+swarm
    # -----------------------------------------------------------------------

    async def track_agent_performance(self, agent_id: str, agent_name: str, agent_type: str,
                                       workspace_id: int, task_id: str, success: bool,
                                       completion_time: float = None, error_count: int = 0,
                                       quality_score: float = None, metadata: dict = None):
        """Track agent performance metrics — success/fail, quality, timing.
        Writes to agent_performance + agent_registry in V2 agents.db."""
        try:
            timestamp = time_module.time()
            with v2_connection("agents") as _aconn:
                _aconn.execute(
                    """INSERT INTO agent_performance
                       (agent_id, agent_name, agent_type, workspace_id, task_id,
                        success, completion_time, error_count, quality_score, metadata, timestamp)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (agent_id, agent_name, agent_type, workspace_id, task_id,
                     1 if success else 0, completion_time, error_count, quality_score,
                     json.dumps(metadata) if metadata else None, timestamp))

                # Sync to agent_registry (source of truth for performance)
                try:
                    _aconn.execute("""
                        UPDATE agent_registry SET
                            success_count = COALESCE(success_count, 0) + ?,
                            failure_count = COALESCE(failure_count, 0) + ?,
                            total_requests = COALESCE(total_requests, 0) + 1,
                            avg_response_time = CASE
                                WHEN COALESCE(total_requests, 0) = 0 THEN ?
                                ELSE (COALESCE(avg_response_time, 0) * COALESCE(total_requests, 0) + ?) / (COALESCE(total_requests, 0) + 1)
                            END,
                            last_request_at = ?,
                            updated_at = ?
                        WHERE agent_id = ?
                    """, (
                        1 if success else 0,
                        0 if success else 1,
                        completion_time or 0,
                        completion_time or 0,
                        time_module.strftime('%Y-%m-%d %H:%M:%S'),
                        time_module.time(),
                        agent_id,
                    ))
                except Exception as _re:
                    logger.debug("Registry perf sync for %s: %s", agent_id, _re)

            return True
        except Exception as e:
            logger.error(f"Error tracking agent performance: {e}")
            return False

    async def track_request_journey(self, journey_id: str = None, description: str = None,
                                     system_id: str = "swarm", journey_type: str = "task",
                                     request_id: str = None, task: str = None) -> str:
        """Create parent journey record linking all journey_steps. Returns journey_id."""
        try:
            if not journey_id:
                journey_id = f"{system_id}_{int(time_module.time())}_{uuid.uuid4().hex[:8]}"
            with v2_connection("journeys") as _jconn:
                _jconn.execute(
                    """INSERT OR IGNORE INTO request_journeys
                       (journey_id, request_id, system_id, journey_type, task, description, created_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (journey_id, request_id, system_id, journey_type, task, description, time_module.time()))
            return journey_id
        except Exception as e:
            logger.error(f"Error creating request journey: {e}")
            return journey_id or f"fallback_{int(time_module.time())}"

    async def log_deliberation(self, workspace_id: int, user_id: int, topic: str,
                                contributions: dict = None, synthesis: str = None,
                                opus_review: str = None, context: str = None) -> int:
        """Log a boardroom deliberation for training data capture. Returns deliberation_id."""
        try:
            with v2_connection("journeys") as _jconn:
                cursor = _jconn.execute(
                    """INSERT INTO deliberation_history
                       (workspace_id, user_id, topic, context, contributions, synthesis, opus_review, created_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    (workspace_id, user_id, topic, context,
                     json.dumps(contributions) if contributions else None,
                     synthesis, opus_review, time_module.time()))
                deliberation_id = cursor.lastrowid
                return deliberation_id
        except Exception as e:
            logger.error(f"Error logging deliberation: {e}")
            return -1

    def calculate_performance_score(self, agent_id: str, db_path: str = None) -> float:
        """Calculate weighted performance score for agent from historical data.
        Score 0-100: success_rate(40%) + quality(30%) + speed(15%) + low_errors(15%).
        db_path parameter is kept for API compatibility but ignored — reads from V2 agents.db."""
        try:
            with v2_connection("agents") as _aconn:
                row = _aconn.execute("""
                    SELECT COUNT(*) as total,
                        SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successes,
                        AVG(quality_score) as avg_quality,
                        AVG(completion_time) as avg_time,
                        SUM(error_count) as total_errors
                    FROM agent_performance WHERE agent_id = ? AND timestamp > ?
                """, (agent_id, time_module.time() - 30 * 86400)).fetchone()
            if not row or row[0] == 0:
                return 50.0
            total, successes, avg_quality, avg_time, total_errors = row
            success_rate = (successes / total) * 100 if total > 0 else 50
            quality = avg_quality or 50
            time_score = max(0, min(100, 100 - (avg_time or 0) * 10))
            error_rate = max(0, 100 - (total_errors / max(total, 1)) * 100)
            return round(success_rate * 0.40 + quality * 0.30 + time_score * 0.15 + error_rate * 0.15, 2)
        except Exception as e:
            logger.error(f"Error calculating performance score for {agent_id}: {e}")
            return 50.0

    async def send_message_to_jarvis(self, message, context=None, handler_params=None,
                                     message_type="update", request_id=None, journey_id=None):
        """Send a message to the Jarvis orchestrator."""
        try:
            journey_id = journey_id or f"swarm_message_{int(time_module.time())}"
            logger.info(f"Message to Jarvis ({message_type}): {str(message)[:100]}")

            if not hasattr(self, 'jarvis_messages'):
                self.jarvis_messages = []
            self.jarvis_messages.append({
                'timestamp': time_module.time(),
                'message': message,
                'context': context,
                'message_type': message_type,
                'journey_id': journey_id
            })
            return True, journey_id
        except Exception as e:
            logger.error(f"Error sending message to Jarvis: {str(e)}")
            return False, None

    async def create_team(self, name: str, members: List[str] = None) -> HandlerResult:
        """Create a new agent team with workspace sub-workspace."""
        try:
            team_id = f"team_{name}_{int(time_module.time())}"
            team = {
                'id': team_id,
                'name': name,
                'members': members or [],
                'created_at': time_module.time(),
                'conversation_history': [],
                'workspace_id': None
            }

            # Create sub-workspace for the team if workspace is set
            if self._workspace_id and self._workspace_sharing:
                try:
                    sub_ws_id = await self._workspace_sharing.create_sub_workspace(
                        parent_workspace_id=self._workspace_id,
                        name=f"Team_{name}",
                        description=f"Sub-workspace for team {name}",
                        metadata={"team_id": team_id, "members": members or []}
                    )
                    if sub_ws_id:
                        team['workspace_id'] = sub_ws_id
                        logger.info(f"Created sub-workspace {sub_ws_id} for team {name}")
                        # Assign team members to the sub-workspace
                        for member in (members or []):
                            agent_id = self._agent_workspace_map.get(member)
                            if agent_id:
                                await self._workspace_sharing.assign_agent_to_workspace(
                                    agent_id=agent_id, workspace_id=sub_ws_id, role="contributor"
                                )
                except Exception as e:
                    logger.warning(f"Could not create team sub-workspace: {e}")

            self.teams[team_id] = team
            logger.info(f"Created team {name} with ID {team_id}")
            return self.create_success_result({
                "team_id": team_id,
                "workspace_id": team.get('workspace_id'),
                "message": f"Team {name} created successfully"
            })
        except Exception as e:
            logger.error(f"Error creating team: {str(e)}")
            return self.create_error_result(f"Failed to create team: {str(e)}")

    async def start_conversation(self, agents: List[str], topic: str = None) -> HandlerResult:
        """Start a conversation between multiple agents."""
        try:
            conversation_id = f"conv_{int(time_module.time())}_{uuid.uuid4().hex[:8]}"
            conversation = {
                'id': conversation_id,
                'agents': agents,
                'topic': topic,
                'started_at': time_module.time(),
                'messages': [],
                'current_agent': agents[0] if agents else None
            }
            self.conversations[conversation_id] = conversation
            logger.info(f"Started conversation {conversation_id} with agents: {agents}")
            return self.create_success_result({
                "conversation_id": conversation_id,
                "message": f"Conversation started with {len(agents)} agents"
            })
        except Exception as e:
            logger.error(f"Error starting conversation: {str(e)}")
            return self.create_error_result(f"Failed to start conversation: {str(e)}")

    async def send_message(self, conversation_id: str, message: str,
                           sender_agent: str = None) -> HandlerResult:
        """Send a message in a conversation, with optional AI processing via Anthropic."""
        try:
            if conversation_id not in self.conversations:
                return self.create_error_result(f"Conversation {conversation_id} not found")

            conversation = self.conversations[conversation_id]
            message_data = {
                'id': f"msg_{int(time_module.time())}_{uuid.uuid4().hex[:8]}",
                'sender': sender_agent or 'system',
                'content': message,
                'timestamp': time_module.time()
            }
            conversation['messages'].append(message_data)

            # Use Anthropic for agent processing if client is available
            if self.anthropic_client:
                try:
                    history_context = "\n".join([
                        f"{m['sender']}: {m['content']}"
                        for m in conversation['messages'][-10:]
                    ])

                    agent_response = self._call_anthropic(
                        system_prompt=(
                            "You are a swarm coordination agent. Process this conversation "
                            "message and provide a helpful response."
                        ),
                        user_prompt=(
                            f"Conversation topic: {conversation.get('topic', 'general')}\n\n"
                            f"Recent messages:\n{history_context}\n\n"
                            f"Respond to the latest message."
                        ),
                        max_tokens=1024
                    )

                    response_data = {
                        'id': f"msg_{int(time_module.time())}_{uuid.uuid4().hex[:8]}",
                        'sender': 'swarm_coordinator',
                        'content': agent_response,
                        'timestamp': time_module.time()
                    }
                    conversation['messages'].append(response_data)
                except Exception as agent_error:
                    logger.warning(f"Agent processing failed: {agent_error}")

            logger.info(f"Message sent in conversation {conversation_id}")
            return self.create_success_result({
                "message_id": message_data['id'],
                "message": "Message sent successfully"
            })
        except Exception as e:
            logger.error(f"Error sending message: {str(e)}")
            return self.create_error_result(f"Failed to send message: {str(e)}")

    async def execute_tool(self, tool_name: str, agent_name: str = None, **kwargs) -> HandlerResult:
        """Execute a tool on behalf of an agent.

        Resolution order:
        1. Python callable in agent.tools (direct function call)
        2. MCP handler via agent.mcp_tools (workspace MCP bridge)
        3. Workspace-level MCP config (any handler available to the workspace)
        """
        try:
            # --- Resolve which agent owns this tool ---
            target_agent = None
            if agent_name and agent_name in self.agents:
                target_agent = self.agents[agent_name]
            else:
                # Search Python callables first
                for agent in self.agents.values():
                    if hasattr(agent, 'tools') and agent.tools:
                        for tool in agent.tools:
                            if hasattr(tool, '__name__') and tool.__name__ == tool_name:
                                target_agent = agent
                                break
                    if target_agent:
                        break
                # Then search MCP tool assignments
                if not target_agent:
                    for agent in self.agents.values():
                        if hasattr(agent, 'mcp_tools') and tool_name in agent.mcp_tools:
                            target_agent = agent
                            break

            # --- 1. Try Python callable ---
            if target_agent and hasattr(target_agent, 'tools') and target_agent.tools:
                for tool in target_agent.tools:
                    if hasattr(tool, '__name__') and tool.__name__ == tool_name:
                        result = tool(**kwargs)
                        logger.info(f"Executed Python tool {tool_name} for agent {target_agent.name}")
                        return self.create_success_result({
                            "tool_result": result,
                            "execution_type": "python_callable",
                            "agent": target_agent.name,
                            "message": f"Tool {tool_name} executed successfully"
                        })

            # --- 2. Try MCP via agent.mcp_tools ---
            # If the agent has MCP handlers assigned, route tool_name as an action
            # to the agent's MCP handler. e.g. agent has mcp_tools=["handler_oanda"],
            # tool_name="get_candles" → call handler_oanda with action="get_candles"
            if target_agent and hasattr(target_agent, 'mcp_tools') and target_agent.mcp_tools:
                # Check if tool_name IS a handler name (direct MCP call)
                if tool_name in target_agent.mcp_tools:
                    return await self._execute_mcp_tool(tool_name, target_agent.name, **kwargs)
                # Otherwise, route tool_name as a direct method call on the agent's MCP handler
                # Strip 'handler_' prefix for mcp_wrapper compatibility
                for mcp_handler in target_agent.mcp_tools:
                    handler_short = mcp_handler.replace("handler_", "") if mcp_handler.startswith("handler_") else mcp_handler
                    return await self._execute_mcp_tool(
                        handler_short, target_agent.name,
                        method=tool_name,
                        parameters=kwargs,
                    )

            # --- 3. Try workspace-level MCP config (any MCP assigned to the workspace) ---
            ws_mcp = getattr(self, '_workspace_mcp_config', {})
            if tool_name in ws_mcp:
                agent_label = target_agent.name if target_agent else "workspace"
                return await self._execute_mcp_tool(tool_name, agent_label, **kwargs)

            # --- Nothing found ---
            return self.create_error_result(
                f"Tool '{tool_name}' not found. Checked: Python callables, agent MCP tools, "
                f"workspace MCP config ({len(ws_mcp)} MCPs available: {list(ws_mcp.keys())})"
            )

        except Exception as e:
            logger.error(f"Error executing tool: {str(e)}")
            return self.create_error_result(f"Failed to execute tool: {str(e)}")

    async def _execute_mcp_tool(self, mcp_name: str, agent_label: str, **kwargs) -> HandlerResult:
        """Execute a tool through the MCP bridge.

        Resolution:
        1. workspace_sharing.execute_method_via_mcp (handler-based MCPs with workspace context)
        2. mcp_wrapper.get_handler_wrapper (handler-based or standalone MCPs, no workspace context)
        """
        try:
            method_name = kwargs.pop('method', 'handle')
            parameters = kwargs.pop('parameters', kwargs) if 'parameters' in kwargs else kwargs

            # Route 1: Through workspace sharing manager (has workspace context)
            if self._workspace_id and self._workspace_sharing:
                result = await self._workspace_sharing.execute_method_via_mcp(
                    workspace_id=self._workspace_id,
                    handler_name=mcp_name,
                    method_name=method_name,
                    parameters=parameters
                )
                logger.info(f"Executed MCP {mcp_name}.{method_name} via workspace {self._workspace_id} for {agent_label}")
                return self.create_success_result({
                    "tool_result": result,
                    "execution_type": "workspace_mcp",
                    "mcp": mcp_name,
                    "method": method_name,
                    "workspace_id": self._workspace_id,
                    "agent": agent_label,
                    "message": f"MCP {mcp_name}.{method_name} executed successfully"
                })

            # Route 2: Direct wrapper (supports both handler-based and standalone MCPs)
            from Jarvis_Agent_SDK.mcp_wrapper import get_handler_wrapper
            wrapper = get_handler_wrapper(mcp_name)
            if wrapper:
                result = wrapper.execute(action=method_name, parameters=parameters)
                logger.info(f"Executed MCP {mcp_name}.{method_name} via direct wrapper for {agent_label}")
                return self.create_success_result({
                    "tool_result": result,
                    "execution_type": "direct_mcp",
                    "mcp": mcp_name,
                    "method": method_name,
                    "agent": agent_label,
                    "message": f"MCP {mcp_name}.{method_name} executed successfully"
                })

            return self.create_error_result(
                f"MCP '{mcp_name}' not found in handler or standalone registry"
            )

        except Exception as e:
            logger.error(f"Error executing MCP {mcp_name}: {str(e)}")
            return self.create_error_result(f"Failed to execute MCP tool: {str(e)}")

    async def get_conversation_history(self, conversation_id: str = None) -> HandlerResult:
        """Get conversation history for a specific conversation or all conversations."""
        try:
            if conversation_id:
                if conversation_id in self.conversations:
                    return self.create_success_result({
                        "conversation": self.conversations[conversation_id],
                        "message": f"Retrieved conversation {conversation_id}"
                    })
                else:
                    return self.create_error_result(f"Conversation {conversation_id} not found")
            else:
                return self.create_success_result({
                    "conversations": list(self.conversations.values()),
                    "message": f"Retrieved {len(self.conversations)} conversations"
                })
        except Exception as e:
            logger.error(f"Error getting conversation history: {str(e)}")
            return self.create_error_result(f"Failed to get conversation history: {str(e)}")

    async def distribute_tasks(self, tasks: List[Dict[str, Any]],
                               strategy: str = "round_robin") -> HandlerResult:
        """Distribute tasks among registered agents."""
        try:
            if not self.agents:
                return self.create_error_result("No agents registered to distribute tasks to")

            agent_names = list(self.agents.keys())
            assignments = {}

            for i, task in enumerate(tasks):
                if strategy == "round_robin":
                    assigned_agent = agent_names[i % len(agent_names)]
                elif strategy == "random":
                    assigned_agent = random.choice(agent_names)
                else:
                    assigned_agent = agent_names[0]

                task_id = task.get('id', f"task_{int(time_module.time())}_{i}")

                # Persist to workspace DB
                db_task_id = await self._create_workspace_task(
                    title=task.get('description', task.get('title', task_id)),
                    description=json.dumps(task),
                    assigned_agent_name=assigned_agent,
                    priority=task.get('priority', 'medium')
                )

                assignments[task_id] = {
                    "agent": assigned_agent,
                    "task": task,
                    "assigned_at": time_module.time(),
                    "status": "assigned",
                    "workspace_task_id": db_task_id
                }

            self.task_assignments.update(assignments)

            logger.info(f"Distributed {len(tasks)} tasks among {len(agent_names)} agents using {strategy}")
            return self.create_success_result({
                "assignments": assignments,
                "message": f"Distributed {len(tasks)} tasks using {strategy} strategy"
            })
        except Exception as e:
            logger.error(f"Error distributing tasks: {str(e)}")
            return self.create_error_result(f"Failed to distribute tasks: {str(e)}")

    async def health_check(self) -> HandlerResult:
        """Validate workspace, task, and agent subsystems are operational."""
        results = {}
        results["workspace_sharing"] = self._workspace_sharing is not None
        if self._workspace_id and self._workspace_sharing:
            try:
                ws = await self._workspace_sharing.get_workspace(self._workspace_id)
                results["current_workspace"] = ws is not None
            except Exception:
                results["current_workspace"] = False
        results["registered_agents"] = len(self.agents)
        results["teams"] = len(self.teams)
        results["conversations"] = len(self.conversations)
        results["mcp_cache_size"] = len(self._agent_mcp_cache)
        all_ok = results["workspace_sharing"] and results["registered_agents"] >= 0
        if all_ok:
            return self.create_success_result(results)
        return self.create_error_result("Health check failed", metadata=results)

    async def get_status(self, include_agents: bool = True, include_teams: bool = True,
                         include_conversations: bool = False) -> HandlerResult:
        """Get the current status of the swarm."""
        try:
            ws_mcp = getattr(self, '_workspace_mcp_config', {})
            status = {
                "registered_agents": len(self.agents),
                "active": self.is_initialized or bool(self.agents),
                "anthropic_client_ready": self.anthropic_client is not None,
                "workspace_id": self._workspace_id,
                "workspace_connected": self._workspace_sharing is not None,
                "workspace_mcp_handlers": len(ws_mcp),
                "workspace_mcp_available": list(ws_mcp.keys()) if ws_mcp else [],
                "tasks_tracked": len(self.task_assignments),
                "timestamp": time_module.time()
            }

            if include_agents:
                status["agents"] = {
                    name: {
                        "model": agent.model,
                        "tools_count": len(agent.tools) if hasattr(agent, 'tools') else 0,
                        "mcp_tools": agent.mcp_tools if hasattr(agent, 'mcp_tools') else [],
                        "mcp_tools_count": len(agent.mcp_tools) if hasattr(agent, 'mcp_tools') else 0
                    }
                    for name, agent in self.agents.items()
                }

            if include_teams and hasattr(self, 'teams'):
                status["teams"] = {
                    tid: {"name": t['name'], "members": len(t.get('members', []))}
                    for tid, t in self.teams.items()
                }

            if include_conversations:
                status["conversations"] = len(self.conversations)

            return self.create_success_result(status)
        except Exception as e:
            logger.error(f"Error getting status: {str(e)}")
            return self.create_error_result(f"Failed to get status: {str(e)}")

    async def coordinate_parallel(self, tasks: List[Dict[str, Any]],
                                  timeout: float = 30.0) -> HandlerResult:
        """Coordinate parallel execution of tasks across agents using Anthropic for planning."""
        try:
            if not self.anthropic_client:
                return self.create_error_result("Anthropic client not initialized — cannot coordinate")

            task_descriptions = json.dumps(
                [t.get('description', str(t)) for t in tasks], indent=2
            )
            agent_info = json.dumps({
                name: {"model": a.model, "instructions": a.instructions[:200]}
                for name, a in self.agents.items()
            }, indent=2)

            plan_response = self._call_anthropic(
                system_prompt=(
                    "You are a task coordination planner. Given a list of tasks and available agents, "
                    "create an execution plan that assigns tasks to the most appropriate agents for "
                    "parallel execution. Return a JSON object with 'assignments' mapping task indices "
                    "to agent names."
                ),
                user_prompt=(
                    f"Tasks:\n{task_descriptions}\n\n"
                    f"Available agents:\n{agent_info}\n\n"
                    f"Create an assignment plan."
                ),
                max_tokens=1024
            )

            try:
                plan = json.loads(plan_response)
            except json.JSONDecodeError:
                plan = {
                    "assignments": {
                        str(i): list(self.agents.keys())[i % len(self.agents)]
                        for i in range(len(tasks))
                    }
                }

            logger.info(f"Created parallel coordination plan for {len(tasks)} tasks")
            return self.create_success_result({
                "plan": plan,
                "tasks_count": len(tasks),
                "agents_available": len(self.agents),
                "message": f"Coordination plan created for {len(tasks)} tasks"
            })
        except Exception as e:
            logger.error(f"Error coordinating parallel tasks: {str(e)}")
            return self.create_error_result(f"Failed to coordinate: {str(e)}")

    async def assign_work(self, agent_name: str, task: Dict[str, Any]) -> HandlerResult:
        """Assign a specific task to a specific agent, persisted to workspace DB.
        
        Registry-first: if the named agent isn't loaded in the swarm,
        check the registry for a matching skill agent. If still not found,
        use AgentBuilder to create one on the fly.
        """
        try:
            if agent_name not in self.agents:
                # Registry-first: find or spawn agent, load into swarm
                try:
                    from Core.team_loader import find_or_spawn_agent
                    task_desc = task.get("description", task.get("title", agent_name))
                    board_seat = task.get("board_seat")
                    result = find_or_spawn_agent(task_desc, board_seat=board_seat)
                    
                    if result.get("agent"):
                        agent_data = result["agent"]
                        found_name = agent_data.get("agent_name", agent_name)
                        logger.info(
                            "Registry lookup for '%s': %s agent '%s'",
                            agent_name, result["action"], found_name,
                        )
                        # Load into swarm from registry data
                        if found_name not in self.agents:
                            agent = SwarmAgent(
                                name=found_name,
                                instructions=agent_data.get("system_prompt", agent_data.get("agent_type", "")),
                                tools=[],
                                mcp_tools=agent_data.get("mcp_tools", []),
                                model=agent_data.get("model", SWARM_MODEL),
                            )
                            self.agents[found_name] = agent
                            logger.info("Loaded %s into swarm from registry (model=%s)", found_name, agent_data.get("model"))
                        agent_name = found_name
                except Exception as e:
                    logger.warning("Registry lookup failed for %s: %s", agent_name, e)
                    return self.create_error_result(f"Agent {agent_name} not found")

            task_id = task.get('id', f"task_{int(time_module.time())}_{uuid.uuid4().hex[:8]}")

            assignment = {
                "task_id": task_id,
                "agent": agent_name,
                "task": task,
                "assigned_at": time_module.time(),
                "status": "assigned",
                "workspace_task_id": None
            }

            # Persist task to workspace DB
            db_task_id = await self._create_workspace_task(
                title=task.get('description', task.get('title', task_id)),
                description=json.dumps(task),
                assigned_agent_name=agent_name,
                priority=task.get('priority', 'medium')
            )
            if db_task_id:
                assignment["workspace_task_id"] = db_task_id

            self.task_assignments[task_id] = assignment

            await self.track_agent_activity(
                agent_id=self._agent_workspace_map.get(agent_name, f"{agent_name}_{int(time_module.time())}"),
                agent_name=agent_name,
                action_type="task_assigned",
                details={"task_id": task_id, "task": task, "workspace_task_id": db_task_id},
                agent_type="swarm_agent",
                workspace_id=str(self._workspace_id) if self._workspace_id else f"swarm_{int(time_module.time())}"
            )

            logger.info(f"Assigned task {task_id} to agent {agent_name}")
            return self.create_success_result({
                "task_id": task_id,
                "agent": agent_name,
                "workspace_task_id": db_task_id,
                "message": f"Task {task_id} assigned to {agent_name}"
            })
        except Exception as e:
            logger.error(f"Error assigning work: {str(e)}")
            return self.create_error_result(f"Failed to assign work: {str(e)}")

    # -----------------------------------------------------------------------
    # Sequential Deliberation — Boardroom coordination mode (Phase 3)
    # Ideas evolve through sequential rounds, not parallel execution.
    # Each board member reads ALL previous contributions and builds on them.
    # -----------------------------------------------------------------------

    async def sequential_deliberation(self, topic: str, context: str = None,
                                       member_order: List[str] = None,
                                       user_id: int = None,
                                       workspace_id: int = None,
                                       opus_qc: bool = True,
                                       max_rounds: int = 5,
                                       converge: bool = True,
                                       on_request_info: callable = None) -> HandlerResult:
        """
        Collaborative building protocol — the boardroom's core coordination mode.

        State machine: PRESENTING → DELIBERATING → USER_INPUT → SYNTHESIZING → 
                       STRESS_TEST → OPUS_QC → COMPLETE

        Parameters
        ----------
        topic : str
            The request/question to deliberate on.
        context : str, optional
            Additional context (knowledge vault excerpts, prior decisions, etc.)
        member_order : list[str], optional
            Agent names in deliberation order. Default: CSO → CTO → CRO → CDO.
            Broadest thinker first, domain specialist last.
        user_id : int, optional
            User ID for deliberation logging.
        workspace_id : int, optional
            Boardroom workspace ID.
        opus_qc : bool
            If True, send final plan to Opus for QC (mandatory during training phase).
        max_rounds : int
            Maximum deliberation rounds (default 5). With converge=True, may stop earlier.
        converge : bool
            If True (default), the Chair evaluates after each round whether consensus
            has been reached. Deliberation continues until convergence or max_rounds.
        on_request_info : callable, optional
            Async callback: on_request_info(questions: list[str]) -> str (user's answers).
            If None, REQUEST_INFO flags are collected but not resolved.

        Returns
        -------
        HandlerResult with data:
            topic, contributions (per member), synthesis, opus_review,
            info_requests, deliberation_id, status
        """
        import re as _re

        state = "PRESENTING"
        contributions = {}
        info_requests = []
        synthesis = None
        opus_review = None
        deliberation_id = None

        # Default member order: broadest first, domain specialist last
        # During Phase A training, Opus goes LAST as full deliberating member
        if not member_order:
            member_order = [n for n in ["CSO", "CTO", "CRO", "CDO"] if n in self.agents]
            if not member_order:
                # Fallback: use all registered agents (exclude Opus variants)
                member_order = [n for n in self.agents.keys() 
                               if n not in ("Opus", "Opus_Consultant")]
            # Phase A: add Opus as last deliberating member
            try:
                from Handler.boardroom_template import OPUS_TRAINING_PHASE
                if OPUS_TRAINING_PHASE == "A" and "Opus" in self.agents:
                    if "Opus" not in member_order:
                        member_order.append("Opus")
            except ImportError:
                pass

        if not member_order:
            return self.create_error_result("No board members registered in swarm")

        logger.info(f"Sequential deliberation starting: '{topic[:80]}...' with {member_order}")

        # Create journey for tracking
        journey_id = await self.track_request_journey(
            system_id="boardroom", journey_type="deliberation",
            task=topic[:200], description=f"Boardroom deliberation: {topic[:100]}"
        )

        try:
            # --- DELIBERATING ---
            state = "DELIBERATING"

            for round_num in range(max_rounds):
                for member_name in member_order:
                    agent = self.agents.get(member_name)
                    if not agent:
                        logger.warning(f"Board member {member_name} not registered, skipping")
                        continue

                    # Load agent's vault context (learnings, patterns, improvements)
                    vault_context = ""
                    try:
                        from knowledge.vault_writer import VaultWriter
                        vault = VaultWriter()
                        vault_context = vault.load_agent_context(member_name, max_learnings=10)
                        if vault_context:
                            vault_context = f"\n\n## Your Knowledge (from vault)\n{vault_context}\n"
                    except Exception:
                        pass  # vault not available, continue without

                    # Build the task with all prior contributions
                    prior_text = ""
                    if contributions:
                        prior_text = "\n\n## Previous Board Member Contributions\n"
                        for prev_name, prev_contribution in contributions.items():
                            prior_text += f"\n### {prev_name}:\n{prev_contribution}\n"

                    round_label = f" (Round {round_num + 1})" if max_rounds > 1 else ""
                    task_prompt = (
                        f"## Boardroom Deliberation{round_label}\n\n"
                        f"**Topic:** {topic}\n\n"
                    )
                    if vault_context:
                        task_prompt += vault_context + "\n\n"
                    if context:
                        task_prompt += f"**Context:**\n{context}\n\n"
                    if prior_text:
                        task_prompt += prior_text + "\n\n"
                    task_prompt += (
                        f"**Your turn, {member_name}.** Read everything above and contribute "
                        f"your analysis from your area of expertise. Build on what came before — "
                        f"don't repeat, ADD what's missing. If you need information from the "
                        f"user, include REQUEST_INFO: [your question]."
                    )

                    # Execute the agent's LLM call
                    result = await self.execute_agent_task(
                        agent_name=member_name,
                        task=task_prompt,
                        context={"deliberation": True, "round": round_num + 1},
                        max_tokens=4096,
                        max_tool_rounds=5  # allow some tool use for DB/vault lookups
                    )

                    if result.success and result.data:
                        response_text = result.data.get("response", str(result.data))
                        contributions[member_name] = response_text

                        # Extract REQUEST_INFO flags
                        info_matches = _re.findall(
                            r'REQUEST_INFO:\s*(.+?)(?:\n|$)', response_text, _re.IGNORECASE
                        )
                        if info_matches:
                            info_requests.extend(info_matches)

                        # Track the contribution
                        await self.track_journey_step(
                            journey_id=journey_id,
                            step_name=f"contribution_{member_name}_round{round_num+1}",
                            description=f"{member_name} contributed to deliberation",
                            input_data=json.dumps({"topic": topic[:200]}),
                            output_data=response_text[:2000],
                            step_type="deliberation_contribution"
                        )

                        logger.info(f"Board member {member_name} contributed "
                                   f"({len(response_text)} chars, {len(info_matches)} info requests)")
                    else:
                        error_msg = result.error if result.error else "Unknown error"
                        contributions[member_name] = f"[{member_name} unavailable: {error_msg}]"
                        logger.error(f"Board member {member_name} failed: {error_msg}")

                # --- USER_INPUT --- (between rounds if there are info requests)
                if info_requests and on_request_info and round_num < max_rounds - 1:
                    state = "USER_INPUT"
                    try:
                        user_answers = await on_request_info(info_requests)
                        if user_answers:
                            context = (context or "") + f"\n\n## User Answers:\n{user_answers}"
                            info_requests = []  # clear for next round
                    except Exception as e:
                        logger.warning(f"Error getting user input: {e}")
                    state = "DELIBERATING"

                # --- USER COLLABORATION --- (between rounds)
                # The user (CEO) is an active participant, not a passive recipient.
                # After each round, summarize where the board is and invite input.
                if on_request_info and round_num < max_rounds - 1:
                    # Build a summary of this round for the user
                    round_summary_parts = []
                    for name, contribution in contributions.items():
                        # Extract the key point (first 200 chars or first paragraph)
                        first_para = contribution.split("\n\n")[0][:300]
                        round_summary_parts.append(f"**{name}:** {first_para}")
                    
                    round_summary = "\n".join(round_summary_parts)
                    
                    # Collect any REQUEST_INFO items AND invite general feedback
                    user_prompt_parts = []
                    if info_requests:
                        user_prompt_parts.append("The board has questions for you:")
                        for q in info_requests:
                            user_prompt_parts.append(f"  • {q}")
                        user_prompt_parts.append("")
                    
                    user_prompt_parts.append(
                        f"📋 **Round {round_num + 1} Summary:**\n{round_summary}\n\n"
                        f"Any thoughts, corrections, or direction? (or 'continue' to let the board keep working)"
                    )
                    
                    try:
                        user_input = await on_request_info(user_prompt_parts)
                        if user_input and user_input.strip().lower() not in ("continue", "ok", "good", ""):
                            context = (context or "") + f"\n\n## User Input After Round {round_num + 1}:\n{user_input}"
                            # Add user input to contributions so board members see it
                            contributions["User_CEO"] = f"[Round {round_num + 1} feedback] {user_input}"
                            info_requests = []  # clear resolved questions
                            logger.info(f"User provided input after round {round_num + 1}")
                        else:
                            info_requests = []
                    except Exception as e:
                        logger.warning(f"Error getting user input: {e}")

                # --- CONVERGENCE CHECK --- (between rounds)
                if converge and round_num < max_rounds - 1 and len(contributions) >= 2:
                    convergence_prompt = (
                        f"You are the Chair evaluating whether the board has reached consensus.\n\n"
                        f"**Topic:** {topic}\n\n"
                        f"## Round {round_num + 1} Contributions\n"
                    )
                    for name, contribution in contributions.items():
                        convergence_prompt += f"\n### {name}:\n{contribution[:1500]}\n"
                    convergence_prompt += (
                        "\n\nHave the board members converged on a plan? Consider:\n"
                        "- Are there unresolved disagreements?\n"
                        "- Are there major gaps no one has addressed?\n"
                        "- Has the user (CEO) raised concerns that aren't addressed?\n"
                        "- Would another round meaningfully improve the plan?\n\n"
                        "Respond with EXACTLY one of:\n"
                        "- CONVERGED: [brief reason] — if the plan is solid enough to synthesize\n"
                        "- CONTINUE: [what still needs work] — if another round would help\n"
                    )
                    chair_agent = self.agents.get("Chair") or self.agents.get(member_order[0])
                    if chair_agent:
                        chair_name = "Chair" if "Chair" in self.agents else member_order[0]
                        conv_result = await self.execute_agent_task(
                            agent_name=chair_name,
                            task=convergence_prompt,
                            max_tokens=200,
                            max_tool_rounds=0
                        )
                        if conv_result.success and conv_result.data:
                            conv_text = conv_result.data.get("response", str(conv_result.data))
                            if "CONVERGED" in conv_text.upper():
                                logger.info(f"Deliberation converged after round {round_num + 1}: {conv_text[:100]}")
                                break
                            else:
                                logger.info(f"Deliberation continuing: {conv_text[:100]}")
                                context = (context or "") + f"\n\n## Chair's Note After Round {round_num + 1}:\n{conv_text}"

            # --- SYNTHESIZING ---
            state = "SYNTHESIZING"

            synthesis_prompt = (
                f"## Chairman Synthesis\n\n"
                f"**Topic:** {topic}\n\n"
                f"You are the Chair of this boardroom. Below are all board members' contributions. "
                f"Synthesize them into ONE evolved plan — not a vote count, but a refined synthesis "
                f"that incorporates the strongest elements from each perspective.\n\n"
                f"## Board Contributions\n"
            )
            for name, contribution in contributions.items():
                synthesis_prompt += f"\n### {name}:\n{contribution}\n"

            if info_requests:
                synthesis_prompt += (
                    f"\n## Unresolved Questions for User\n"
                    + "\n".join(f"- {q}" for q in info_requests)
                )

            synthesis_prompt += (
                "\n\n## Your Synthesis\n"
                "Create a single, actionable plan that:\n"
                "1. Incorporates the strongest elements from each board member\n"
                "2. Addresses risks flagged by the CRO\n"
                "3. Is technically feasible per the CTO's assessment\n"
                "4. Aligns with strategy per the CSO\n"
                "5. Accounts for domain context per the CDO\n"
                "6. Includes concrete next steps and success criteria\n"
            )

            # Use the first available agent for synthesis (or a dedicated Chair agent)
            chair_agent = self.agents.get("Chair") or self.agents.get(member_order[0])
            if chair_agent:
                chair_name = "Chair" if "Chair" in self.agents else member_order[0]
                synth_result = await self.execute_agent_task(
                    agent_name=chair_name,
                    task=synthesis_prompt,
                    max_tokens=4096,
                    max_tool_rounds=0  # pure synthesis, no tools
                )
                if synth_result.success and synth_result.data:
                    synthesis = synth_result.data.get("response", str(synth_result.data))
                else:
                    synthesis = "Synthesis failed — individual contributions available above."

            # --- OPUS_QC --- governed by graduation system
            # Phase A: always QC. Phase B: 10% spot-check. Phase C: skip.
            do_opus_qc = opus_qc
            if do_opus_qc:
                try:
                    from knowledge.graduation import GraduationTracker
                    grad = GraduationTracker()
                    do_opus_qc = grad.should_opus_qc("boardroom_deliberation")
                    if not do_opus_qc:
                        logger.info("Graduation system: skipping Opus QC (graduated/spot-check miss)")
                except Exception:
                    pass  # graduation not available, default to opus_qc param

            if do_opus_qc and "Opus_Consultant" in self.agents:
                state = "OPUS_QC"
                opus_prompt = (
                    f"## Expert Review Request\n\n"
                    f"**Topic:** {topic}\n\n"
                    f"A board of local AI models deliberated on this topic. "
                    f"Review their work and provide structured feedback.\n\n"
                    f"## Board Contributions\n"
                )
                for name, contribution in contributions.items():
                    opus_prompt += f"\n### {name}:\n{contribution}\n"
                opus_prompt += f"\n## Chair's Synthesis:\n{synthesis}\n"
                opus_prompt += (
                    "\n## Your Review (structured):\n"
                    "### STRENGTHS\n[What the board got right]\n\n"
                    "### GAPS\n[What's missing or undercooked]\n\n"
                    "### CORRECTIONS\n[Specific errors in reasoning]\n\n"
                    "### RECOMMENDATION\n[Your improved version or approval]\n"
                )

                opus_result = await self.execute_agent_task(
                    agent_name="Opus_Consultant",
                    task=opus_prompt,
                    max_tokens=4096,
                    max_tool_rounds=0
                )
                if opus_result.success and opus_result.data:
                    opus_review = opus_result.data.get("response", str(opus_result.data))
                    logger.info(f"Opus QC review received ({len(opus_review)} chars)")

                    # Score the match for graduation tracking
                    # Heuristic: fewer CORRECTIONS = higher match score
                    try:
                        from knowledge.graduation import GraduationTracker
                        review_lower = opus_review.lower()
                        # Simple heuristic scoring — count severity signals
                        corrections_section = review_lower.split("### corrections")[-1].split("###")[0] if "### corrections" in review_lower else ""
                        gaps_section = review_lower.split("### gaps")[-1].split("###")[0] if "### gaps" in review_lower else ""
                        
                        issue_signals = corrections_section.count("- ") + gaps_section.count("- ")
                        # 0 issues = 1.0, 1 = 0.9, 2 = 0.8, 5+ = 0.5
                        match_score = max(0.3, 1.0 - (issue_signals * 0.1))
                        
                        grad = GraduationTracker()
                        for member_name in contributions:
                            grad.record_comparison(
                                category="boardroom_deliberation",
                                match_score=match_score,
                                agent=member_name,
                                notes=f"Topic: {topic[:100]}"
                            )
                        logger.info(f"Graduation: recorded match_score={match_score:.2f} "
                                   f"({issue_signals} issues found)")
                    except Exception as grad_err:
                        logger.debug(f"Graduation tracking failed (non-fatal): {grad_err}")

            # --- COMPLETE ---
            state = "COMPLETE"

            # Log the deliberation
            deliberation_id = await self.log_deliberation(
                workspace_id=workspace_id or self._workspace_id or 0,
                user_id=user_id or 0,
                topic=topic,
                contributions=contributions,
                synthesis=synthesis,
                opus_review=opus_review,
                context=context
            )

            # Track performance for each participating member
            for member_name in contributions:
                await self.track_agent_performance(
                    agent_id=f"boardroom_{member_name.lower()}",
                    agent_name=member_name,
                    agent_type="board_member",
                    workspace_id=workspace_id or self._workspace_id or 0,
                    task_id=f"deliberation_{deliberation_id}",
                    success=True,
                    quality_score=None  # updated later when outcome is known
                )

            # Write to knowledge vault — decisions + Opus corrections as training data
            try:
                from knowledge.vault_writer import VaultWriter
                vault = VaultWriter()
                vault.record_decision(
                    topic=topic,
                    decision=synthesis or "No synthesis produced",
                    reasoning="See board member contributions",
                    contributions=contributions,
                    opus_review=opus_review,
                )
                # If Opus reviewed, record each correction as training data
                if opus_review:
                    for member_name, contribution in contributions.items():
                        vault.record_opus_correction(
                            agent_name=member_name,
                            task=f"Boardroom deliberation: {topic[:100]}",
                            local_output=contribution[:1000],
                            opus_correction=opus_review[:1000],
                            opus_reasoning="Opus QC review of boardroom deliberation",
                            category="boardroom_deliberation"
                        )
            except Exception as vault_err:
                logger.warning(f"Vault write failed (non-fatal): {vault_err}")

            return self.create_success_result({
                "topic": topic,
                "contributions": contributions,
                "synthesis": synthesis,
                "opus_review": opus_review,
                "info_requests": info_requests,
                "deliberation_id": deliberation_id,
                "member_order": member_order,
                "rounds_completed": round_num + 1,
                "max_rounds": max_rounds,
                "converged": converge,
                "state": state,
            })

        except Exception as e:
            logger.error(f"Sequential deliberation failed at state {state}: {e}")
            logger.debug(traceback.format_exc())

            # Still log what we have
            if contributions:
                await self.log_deliberation(
                    workspace_id=workspace_id or self._workspace_id or 0,
                    user_id=user_id or 0,
                    topic=topic,
                    contributions=contributions,
                    synthesis=synthesis,
                    context=f"FAILED at state {state}: {e}"
                )

            return self.create_error_result(
                f"Deliberation failed at {state}: {str(e)}",
                data={"contributions": contributions, "state": state}
            )

    async def resource_aware_deliberation(
        self,
        topic: str,
        workspace_id: int = 914,
        user_id: int = 2,
        opus_qc: bool = True,
        on_request_info: callable = None,
    ) -> list:
        """
        Resource-optimized boardroom deliberation.

        Wraps seat execution with:
          - ensure_loaded()  before each seat  (no-op on 64GB, loads on 32GB)
          - prefetch()       for next seat while current generates (hides latency)
          - scheduler        routes through priority queue for shared ports

        Returns list of {seat, result} dicts.
        """
        from Core.resource_config import SEAT_TO_MODEL, MODEL_CATALOG
        from Core.workspace_scheduler import get_scheduler, PRIORITY_NORMAL
        from Core.model_lifecycle import get_lifecycle

        lifecycle = get_lifecycle()
        scheduler = get_scheduler()

        seat_order = ["CRO", "CTO", "CSO", "CDO"]
        if opus_qc:
            seat_order.append("Opus")

        results        = []
        full_context   = f"Topic: {topic}\n\nPrevious contributions:\n"

        for i, seat in enumerate(seat_order):
            model_key = SEAT_TO_MODEL.get(seat)          # None for Opus
            spec      = MODEL_CATALOG.get(model_key) if model_key else None
            port      = spec.port if spec else None

            # ── Ensure this seat's model is loaded ───────────────────────────
            if model_key:
                loaded = await lifecycle.ensure_loaded(model_key)
                if not loaded:
                    logger.warning("%s model failed to load — skipping seat", seat)
                    results.append({"seat": seat, "result": {"success": False,
                                    "error": "model failed to load"}})
                    continue

            # ── Prefetch NEXT seat in background while this one generates ────
            if i + 1 < len(seat_order):
                next_key = SEAT_TO_MODEL.get(seat_order[i + 1])
                if next_key:
                    asyncio.create_task(lifecycle.prefetch(next_key))

            # ── Build prompt with all prior contributions ─────────────────────
            seat_prompt = (
                f"{full_context}\n"
                f"Now it is your turn ({seat}). Analyze the topic from your unique "
                f"perspective and build meaningfully on what has been said. "
                f"Be specific and actionable.\n\nTopic: {topic}"
            )

            logger.info("🎙️  %s deliberating (model_key=%s)...", seat, model_key or "anthropic/opus")

            # ── Execute via scheduler if port known, else direct API ──────────
            if port:
                async def _run_seat(s=seat, p=seat_prompt):
                    return await self.execute_agent_task(s, p, max_tool_rounds=0)

                try:
                    result = await scheduler.request_model(
                        port=port,
                        workspace="boardroom",
                        task_fn=_run_seat,
                        priority=PRIORITY_NORMAL,
                    )
                except Exception as exc:
                    logger.error("%s scheduler error: %s", seat, exc)
                    result = {"success": False, "error": str(exc)}
            else:
                # Opus — direct Anthropic API call, no port queuing needed
                try:
                    result = await self.execute_agent_task(seat, seat_prompt, max_tool_rounds=0)
                except Exception as exc:
                    result = {"success": False, "error": str(exc)}

            results.append({"seat": seat, "result": result})

            # ── Append contribution to rolling context ────────────────────────
            # execute_agent_task returns HandlerResult(success, data) or plain dict
            if hasattr(result, "success"):
                # HandlerResult object
                r_success = result.success
                r_data    = result.data or {}
                response_text = r_data.get("response", "")
            elif isinstance(result, dict):
                r_success = result.get("success", False)
                response_text = result.get("response", "")
            else:
                r_success, response_text = False, ""

            if r_success and response_text:
                full_context += f"\n### {seat}:\n{response_text}\n"
                logger.info("✅ %s done (%d chars)", seat, len(response_text))

            # ── Schedule potential memory cleanup (no-op on POWER_USER) ───────
            if model_key:
                asyncio.create_task(lifecycle.maybe_unload(model_key))

        return results

    async def boardroom_management_review(self,
                                          deliberation_id: int,
                                          status_update: str,
                                          workspace_id: int = None,
                                          user_id: int = None,
                                          on_request_info: callable = None) -> HandlerResult:
        """
        Management mode — the boardroom reviews progress on an active plan.
        
        After a plan is built via sequential_deliberation, the boardroom doesn't
        disband. It reconvenes to:
        1. Review status updates (from task monitor, user, or agents)
        2. Each member evaluates progress through their lens
        3. Identify blockers, course corrections, or escalation needs
        4. Produce updated action items
        
        This is lighter than full deliberation — single round, focused on deltas.
        Can be triggered by cron, task monitor escalation, or user request.
        """
        import re as _re

        # Load the original deliberation for context
        original_context = ""
        try:
            with v2_connection("journeys") as conn:
                row = conn.execute(
                    "SELECT topic, synthesis FROM deliberation_history WHERE id = ?",
                    (deliberation_id,)
                ).fetchone()
                if row:
                    original_context = f"## Original Plan\n**Topic:** {row[0]}\n**Plan:** {row[1][:2000]}"
        except Exception:
            pass

        # Quick single-round review — each member gets the status update + original plan
        contributions = {}
        action_items = []
        
        member_order = [n for n in ["CSO", "CTO", "CRO", "CDO"] if n in self.agents]
        
        # Phase A: include Opus in management reviews too
        try:
            from Handler.boardroom_template import OPUS_TRAINING_PHASE
            if OPUS_TRAINING_PHASE == "A" and "Opus" in self.agents:
                member_order.append("Opus")
        except ImportError:
            pass

        for member_name in member_order:
            if member_name not in self.agents:
                continue
                
            review_prompt = (
                f"## Management Review — Deliberation #{deliberation_id}\n\n"
                f"{original_context}\n\n"
                f"## Status Update\n{status_update}\n\n"
            )
            if contributions:
                review_prompt += "## Other Members' Assessments\n"
                for prev_name, prev in contributions.items():
                    review_prompt += f"\n### {prev_name}:\n{prev}\n"
            
            review_prompt += (
                f"\n\n**{member_name}**, review this status update against the original plan. "
                f"From your perspective:\n"
                f"1. Is the plan on track? What's working?\n"
                f"2. Any blockers or risks materializing?\n"
                f"3. Course corrections needed?\n"
                f"4. Specific ACTION_ITEM: [task] entries for next steps\n"
            )
            
            result = await self.execute_agent_task(
                agent_name=member_name,
                task=review_prompt,
                max_tokens=2048,
                max_tool_rounds=3
            )
            
            if result.success and result.data:
                response_text = result.data.get("response", str(result.data))
                contributions[member_name] = response_text
                
                # Extract action items
                items = _re.findall(r'ACTION_ITEM:\s*(.+?)(?:\n|$)', response_text, _re.IGNORECASE)
                action_items.extend([(member_name, item.strip()) for item in items])

        # Log to vault
        try:
            from knowledge.vault_writer import VaultWriter
            vault = VaultWriter()
            vault.record_decision(
                topic=f"Management review: deliberation #{deliberation_id}",
                decision=f"Status: {status_update[:500]}\nAction items: {json.dumps(action_items)}",
                reasoning="Boardroom management review",
                contributions=contributions,
            )
        except Exception:
            pass

        return self.create_success_result({
            "deliberation_id": deliberation_id,
            "status_update": status_update,
            "contributions": contributions,
            "action_items": action_items,
            "members_reviewed": list(contributions.keys()),
        })


# Handler docstring
handler_doc = """
SwarmHandler - Agent Swarm Management (Anthropic SDK)

Manages a swarm of agents that communicate and collaborate on tasks.
Uses Anthropic Claude (claude-sonnet-4-5-20250929) for coordination and reasoning.

Actions:
    - register_agent: Register a new agent with the swarm
    - create_team: Create a team of agents
    - start_conversation: Start a multi-agent conversation
    - send_message: Send a message in a conversation
    - execute_tool: Execute a tool on behalf of an agent
    - get_conversation_history: Retrieve conversation history
    - distribute_tasks: Distribute tasks among agents
    - get_status: Get swarm status overview
    - coordinate_parallel: Plan parallel task execution with AI
    - assign_work: Assign a specific task to a specific agent

Patterns:
    - "register agent with {capabilities}"
    - "start conversation with {agent}"
    - "execute tool {tool_name}"
    - "handoff to {agent}"
    - "distribute tasks to agents"
    - "coordinate parallel execution"
    - "assign work to {agent}"
    - "get swarm status"

Intents:
    - swarm_register_agent
    - swarm_conversation
    - swarm_tool_execution
    - swarm_handoff
    - swarm_distribute
    - swarm_coordinate
    - swarm_assign
    - swarm_status

Parameters:
    - agent: SwarmAgent
    - conversation_id: string
    - tool_call: Any
    - team_name: string
    - task_id: string
    - report_type: string
    - filters: Dict
    - performance_data: Dict
"""


# ---------------------------------------------------------------------------
# SwarmRegistry — per-workspace swarm instances for multi-tenant parallel ops
# ---------------------------------------------------------------------------

import threading

class SwarmRegistry:
    """Manages one SwarmHandler per workspace for multi-tenant parallel operation.
    
    Each workspace gets its own isolated swarm with its own agents, teams, and
    MCP tool configuration. Swarms run in parallel across users/workspaces.
    
    Usage:
        registry = get_swarm_registry()
        swarm = registry.get_or_create(workspace_id=42)
        result = await swarm.handle({"action": "execute_agent_task", ...})
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._swarms = {}  # workspace_id -> SwarmHandler
                    cls._instance._default = None  # backward compat
        return cls._instance
    
    def get_or_create(self, workspace_id: int, tracker=None) -> "SwarmHandler":
        """Get existing swarm for workspace, or create a new one.
        
        Thread-safe. Each workspace gets an isolated SwarmHandler instance
        with its own agents, teams, and MCP configuration.
        """
        if workspace_id in self._swarms:
            return self._swarms[workspace_id]
        
        with self._lock:
            # Double-check after acquiring lock
            if workspace_id in self._swarms:
                return self._swarms[workspace_id]
            
            swarm = SwarmHandler(tracker=tracker)
            swarm.set_workspace(workspace_id)
            self._swarms[workspace_id] = swarm
            logger.info(f"SwarmRegistry: created swarm for workspace {workspace_id} "
                       f"(total: {len(self._swarms)} active swarms)")
            return swarm
    
    def get(self, workspace_id: int) -> "SwarmHandler | None":
        """Get existing swarm for workspace, or None."""
        return self._swarms.get(workspace_id)
    
    def remove(self, workspace_id: int) -> None:
        """Remove and clean up a workspace's swarm."""
        swarm = self._swarms.pop(workspace_id, None)
        if swarm:
            logger.info(f"SwarmRegistry: removed swarm for workspace {workspace_id}")
    
    def list_active(self) -> dict:
        """List all active workspace swarms with agent counts."""
        return {
            ws_id: {
                "agents": len(swarm.agents),
                "workspace_id": swarm._workspace_id,
            }
            for ws_id, swarm in self._swarms.items()
        }
    
    @property
    def default(self) -> "SwarmHandler":
        """Backward-compat: get a default swarm (no workspace binding)."""
        if self._default is None:
            self._default = SwarmHandler()
        return self._default


def get_swarm_registry() -> SwarmRegistry:
    """Get the global SwarmRegistry singleton."""
    return SwarmRegistry()


def get_swarm_for_workspace(workspace_id: int, tracker=None) -> "SwarmHandler":
    """Convenience: get or create a swarm for a specific workspace."""
    return get_swarm_registry().get_or_create(workspace_id, tracker=tracker)


# SwarmHandlerOrchestratorAgent, handle_swarm_intent, _LazySwarmProxy removed
# March 1, 2026 — OpenClaw is the orchestrator now
