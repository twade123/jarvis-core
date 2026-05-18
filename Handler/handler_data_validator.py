"""
Data Validator Handler for Jarvis

Migrated from OpenAI to Anthropic SDK (claude-sonnet-4-5-20250929).
Validates data against multiple rule types with AI-powered reasoning,
schema validation via jsonschema, and integrity checks.

Consolidated: removed duplicate DataValidator class — DataValidatorHandler is the single source.
"""

import time
import json
import logging
import traceback
import asyncio
import hashlib
import os
from typing import Dict, Any, List, Optional, Union
import sys
from pathlib import Path
from datetime import datetime
import psutil
import inspect
import uuid
import jsonschema
import sqlite3

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Add project root to Python path
project_root = Path(__file__).parent.parent.absolute()
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Base imports
from Handler.handler_base import BaseHandler, HandlerResult

# Import from Jarvis_Agent_SDK for common utilities
from Jarvis_Agent_SDK.boardroom_connector import (
    generate_request_id,
    generate_simple_id,
    track_journey_step_sync
)
from Jarvis_Agent_SDK.import_helper import get_workspace_sharing, get_unified_database
from Database.v2.db_helper import connection as v2_connection

# Anthropic SDK import
try:
    from anthropic import Anthropic
    HAS_ANTHROPIC = True
except ImportError:
    logger.warning("Anthropic SDK not available. Install with: pip install anthropic")
    HAS_ANTHROPIC = False

# Default model for validation tasks
VALIDATION_MODEL = "claude-sonnet-4-5-20250929"
# Vision model for chart analysis (requires Opus-tier reasoning for multi-image vision)
VISION_MODEL = "claude-sonnet-4-20250514"
# Local model config (35B VLM for ghost trading / future primary validator)
LOCAL_MODEL_PORT = 11502  # CSO seat: Qwen3.5-35B-A3B-4bit VLM
LOCAL_MODEL_NAME = "mlx-community/Qwen3.5-35B-A3B-4bit"
LOCAL_MODEL_ENABLED = False  # Flip to True to replace Anthropic entirely
GHOST_MODE_ENABLED = True   # Run local model in parallel, compare verdicts


class DataValidatorOrchestratorAgent:
    """Agent for orchestrating communication between DataValidator and Jarvis system"""

    def __init__(self, system_name="DataValidatorSystem", tracker=None):
        if hasattr(system_name, 'name'):
            self.data_validator_handler = system_name
            self.system_name = "DataValidatorOrchestratorAgent"
        else:
            self.system_name = system_name
            self.data_validator_handler = None

        self.conversation_history = []
        self.active = True
        self.current_journey_id = None

        # Use injected tracker if provided; BoardRoom was archived (Phase 3)
        if tracker is not None:
            self.boardroom = tracker
            logger.info(f"DataValidatorOrchestratorAgent using injected tracker for {self.system_name}")
        else:
            self.boardroom = None
            logger.info(f"DataValidatorOrchestratorAgent initialized for {self.system_name}")

    def _track_jarvis_communication(self, direction, message, journey_id=None, _prevent_recursion=False):
        """Track communication with the Jarvis orchestrator"""
        if not journey_id:
            journey_id = self.current_journey_id or f"jarvis_comm_{int(time.time())}"

        step_data = {"description": f"Jarvis communication: {direction}"}

        try:
            if isinstance(message, dict):
                try:
                    safe_message = json.dumps(message)[:500]
                except Exception:
                    safe_message = str(message)[:500]
            else:
                safe_message = str(message)[:500]

            if direction == "incoming":
                step_data["input_data"] = safe_message
            else:
                step_data["output_data"] = safe_message
        except Exception as e:
            logger.error(f"Error preparing message data: {str(e)}")
            safe_message = str(message)[:100]
            step_data["output_data"] = safe_message

        if self.boardroom and not _prevent_recursion:
            try:
                if journey_id and hasattr(self.boardroom, 'track_journey_step'):
                    sig = inspect.signature(self.boardroom.track_journey_step)
                    if '_prevent_recursion' in sig.parameters:
                        self.boardroom.track_journey_step(
                            journey_id=journey_id,
                            step_name=f"jarvis_communication_{direction}",
                            **step_data,
                            _prevent_recursion=True
                        )
                    else:
                        self.boardroom.track_journey_step(
                            journey_id=journey_id,
                            step_name=f"jarvis_communication_{direction}",
                            **step_data
                        )
            except Exception as e:
                logger.error(f"Error tracking Jarvis communication: {str(e)}")

        self.conversation_history.append({
            "timestamp": time.time(),
            "direction": direction,
            "message": safe_message,
            "journey_id": journey_id
        })

        return True

    def send_message_to_jarvis(self, message, context=None, handler_params=None, message_type="update", request_id=None, journey_id=None):
        """Send a message to the Jarvis orchestrator"""
        if not request_id:
            request_id = generate_simple_id("data_validator_req_")

        if not journey_id:
            journey_id = f"data_validator_{request_id}_{int(time.time())}"
            self.current_journey_id = journey_id

        message_payload = {
            "message": message,
            "context": context or {},
            "request_id": request_id,
            "journey_id": journey_id,
            "handler_params": handler_params or {},
            "timestamp": time.time(),
            "system": self.system_name,
            "message_type": message_type
        }

        self._track_jarvis_communication("outgoing", message_payload, journey_id)

        try:
            logger.info(f"Message sent to Jarvis: {message[:100]}...")
            return True, journey_id
        except Exception as e:
            logger.error(f"Error sending message to Jarvis: {str(e)}")
            return False, journey_id

    async def receive_message_from_jarvis(self, message, context=None, message_type="instruction", journey_id=None):
        """Receive a message from the Jarvis orchestrator"""
        if not journey_id:
            journey_id = self.current_journey_id or f"jarvis_comm_{int(time.time())}"

        self._track_jarvis_communication("incoming", message, journey_id)
        logger.info(f"Received message from Jarvis: {message[:100]}...")

        if self.data_validator_handler and hasattr(self.data_validator_handler, 'process_jarvis_message'):
            try:
                response = await self.data_validator_handler.process_jarvis_message(
                    message=message, context=context, message_type=message_type, journey_id=journey_id
                )
                return response
            except Exception as e:
                logger.error(f"Error processing message from Jarvis: {str(e)}")
                return {"error": str(e), "status": "error"}

        return {"status": "received", "timestamp": time.time()}


# Lazy imports to avoid circular dependencies
_handler_all = None
_workflow_tools = None
_boardroom = None
_tracking = None
_workspace = None

def _get_handler_all():
    global _handler_all
    if _handler_all is None:
        try:
            from Handler import handler_all
            _handler_all = handler_all
        except ImportError as e:
            logger.warning(f"Could not import handler_all: {e}")
    return _handler_all

def _get_workflow_tools():
    global _workflow_tools
    if _workflow_tools is None:
        try:
            from Jarvis_Agent_SDK import workflow_tools
            _workflow_tools = workflow_tools
            logger.info("Successfully imported workflow tools from Jarvis_Agent_SDK")
        except ImportError as e:
            logger.warning(f"Could not import workflow_tools: {e}")
            try:
                from Jarvis_Agent_SDK.workflow_tools import (
                    execute_validated_analysis_workflow,
                    route_to_appropriate_system
                )
                _workflow_tools = type('WorkflowTools', (), {
                    'execute_validated_analysis_workflow': execute_validated_analysis_workflow,
                    'route_to_appropriate_system': route_to_appropriate_system
                })
            except ImportError as e:
                logger.error(f"Failed to import workflow tools (both attempts): {e}")
    return _workflow_tools

def _get_tracking():
    global _tracking
    if _tracking is None:
        try:
            from Jarvis_Agent_SDK.common_utils import track_request_journey, track_journey_step
            _tracking = {
                'track_request': track_request_journey,
                'track_step': track_journey_step
            }
        except Exception as e:
            logger.warning(f"Could not setup tracking: {e}")
            _tracking = {
                'track_request': lambda *args, **kwargs: None,
                'track_step': lambda *args, **kwargs: None
            }
    return _tracking

def _get_boardroom():
    """Legacy stub — BoardRoom was archived (Phase 3). Returns None.
    Actual DB tracking now goes through Database.v2.db_helper.connection()."""
    return None

def _get_workspace():
    global _workspace
    if _workspace is None:
        try:
            _workspace = get_workspace_sharing()
            if _workspace:
                logger.info("Successfully initialized workspace sharing")
        except ImportError as e:
            logger.warning(f"Could not import workspace: {e}")
    return _workspace


# ======================================================================
# Trading data sources -- lazy-loaded on first trading validation
# ======================================================================
_trading_sources = {}


def _ensure_trading_bot_path():
    """Add Trading Bot to sys.path if not already present."""
    bot_dir = Path(__file__).parent.parent / "Forex Trading Team"
    if str(bot_dir) not in sys.path:
        sys.path.insert(0, str(bot_dir))
    return bot_dir


def _get_trade_validator():
    """Lazy import: TradeValidator for heuristic pre-analysis."""
    if "trade_validator" not in _trading_sources:
        try:
            _ensure_trading_bot_path()
            from Source.trade_validator import TradeValidator
            _trading_sources["trade_validator"] = TradeValidator()
            logger.info("TradeValidator loaded as trading dataset adapter")
        except ImportError as e:
            logger.warning(f"TradeValidator not available: {e}")
            _trading_sources["trade_validator"] = None
    return _trading_sources["trade_validator"]


def _get_knowledge_store():
    """Lazy import: KnowledgeStore for per-instrument learned patterns and win rates."""
    if "knowledge_store" not in _trading_sources:
        try:
            _ensure_trading_bot_path()
            from Source.knowledge_store import KnowledgeStore
            _trading_sources["knowledge_store"] = KnowledgeStore()
            logger.info("KnowledgeStore loaded for historical pattern data")
        except ImportError as e:
            logger.warning(f"KnowledgeStore not available: {e}")
            _trading_sources["knowledge_store"] = None
    return _trading_sources["knowledge_store"]


def _get_trade_snapshot():
    """Lazy import: TradeSnapshot for chart images and indicator state snapshots."""
    if "trade_snapshot" not in _trading_sources:
        try:
            _ensure_trading_bot_path()
            from Source.trade_snapshot import TradeSnapshot
            _trading_sources["trade_snapshot"] = TradeSnapshot()
            logger.info("TradeSnapshot loaded for chart/indicator snapshots")
        except ImportError as e:
            logger.warning(f"TradeSnapshot not available: {e}")
            _trading_sources["trade_snapshot"] = None
    return _trading_sources["trade_snapshot"]


def _get_validation_analyst():
    """Lazy import: ValidationAnalyst for on-demand + hourly LLM analysis."""
    if "validation_analyst" not in _trading_sources:
        try:
            _ensure_trading_bot_path()
            from Source.validation_analyst import ValidationAnalyst
            _trading_sources["validation_analyst"] = ValidationAnalyst()
            logger.info("ValidationAnalyst loaded for LLM batch analysis")
        except ImportError as e:
            logger.warning(f"ValidationAnalyst not available: {e}")
            _trading_sources["validation_analyst"] = None
    return _trading_sources["validation_analyst"]


def _get_instrument_profile():
    """Lazy import: InstrumentProfile for spread, ATR, volatility, session data."""
    if "instrument_profile" not in _trading_sources:
        try:
            _ensure_trading_bot_path()
            from Source.instrument_profile import InstrumentProfile
            _trading_sources["instrument_profile"] = InstrumentProfile
            logger.info("InstrumentProfile class loaded for instrument context")
        except ImportError as e:
            logger.warning(f"InstrumentProfile not available: {e}")
            _trading_sources["instrument_profile"] = None
    return _trading_sources["instrument_profile"]


def _load_api_key(key_type='CLAUDE'):
    """Load API key safely"""
    try:
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        api_dir = os.path.join(base_dir, "API")
        paths = {
            'CLAUDE': os.path.join(api_dir, "CLAUDE_API_KEY.txt"),
            'OPENAI': os.path.join(api_dir, "OPENAI_API_KEY.txt"),
            'FLASK': os.path.join(api_dir, "FLASK_API_KEY.txt"),
            'GHL': os.path.join(api_dir, "GHL_API_KEY.txt"),
            'HEALTHIE': os.path.join(api_dir, "HEALTHIE_API_KEY.txt"),
            'NEWS': os.path.join(api_dir, "NEWS_API_KEY.txt"),
            'OPENWEATHER': os.path.join(api_dir, "OPENWEATHER_API_KEY.txt"),
            'TMDB': os.path.join(api_dir, "TMDB_API_KEY.txt"),
            'WOLFRAM': os.path.join(api_dir, "WOLFRAM_API_KEY.txt"),
        }
        api_key_path = paths.get(key_type)
        if api_key_path and os.path.exists(api_key_path):
            with open(api_key_path, 'r') as f:
                return f.read().strip()
        return os.environ.get(f"{key_type}_API_KEY", "") or os.environ.get("ANTHROPIC_API_KEY", "")
    except Exception as e:
        logger.error(f"Error loading API key: {str(e)}")
        return ""


class DataValidatorHandler(BaseHandler):
    """
    Handler for data validation using Anthropic's Claude for AI-powered reasoning validation,
    jsonschema for schema validation, and custom integrity checks.

    Single consolidated class — replaces the previous duplicate DataValidator + DataValidatorHandler.
    """

    def __init__(self, workspace_id=None, agent_id=None, db_path=None, board_room=None, journey_id=None, tracker=None):
        """Initialize the DataValidatorHandler."""
        super().__init__(app_name="DataValidator")

        self.logger = logging.getLogger("DataValidator")
        self.logger.info("DataValidatorHandler initialized")

        self.workspace_id = workspace_id
        self.agent_id = agent_id or generate_simple_id()
        self.current_journey_id = journey_id
        self.communication_history = []

        # Use injected tracker if provided, otherwise fall back to BoardRoom
        if tracker is not None:
            self._boardroom = tracker
            
        # Initialize orchestrator agent with tracker
        self._orchestrator_agent = DataValidatorOrchestratorAgent(self, tracker=tracker)

        # Initialize database
        self.db_path = db_path or os.path.join(os.path.dirname(os.path.dirname(__file__)), "Database", "v2", "journeys.db")
        try:
            from Database.database_base import DatabaseManager
            self.db_manager = DatabaseManager(self.db_path)
        except ImportError:
            self.db_manager = None

        # Initialize Anthropic client (replaces OpenAI)
        try:
            if not HAS_ANTHROPIC:
                raise ImportError("Anthropic SDK not installed")

            api_key = _load_api_key('CLAUDE')
            if not api_key:
                from Core.config import load_api_key as core_load_api_key
                api_key = core_load_api_key("CLAUDE_API_KEY") or core_load_api_key("CLAUDE")

            if not api_key:
                self.logger.warning("Anthropic API key not found, AI validation features will be limited")
                self.anthropic_client = None
            else:
                self.anthropic_client = Anthropic(api_key=api_key)
                self.logger.info("Anthropic client initialized successfully")
        except Exception as e:
            self.logger.error(f"Error initializing Anthropic client: {str(e)}")
            self.anthropic_client = None

        # Initialize schema validator
        self.schema = None
        try:
            from jsonschema import Draft7Validator
            self.schema_validator = Draft7Validator
        except ImportError:
            self.logger.warning("jsonschema module not available, schema validation will be limited")
            self.schema_validator = None

        # Initialize action dispatch table for handle()
        self.action_handlers = {
            "validate_data": self._handle_validate_data,
            "validate_schema": self._handle_validate_schema,
            "validate_integrity": self._handle_validate_integrity,
            "validate_data_integrity": self._handle_validate_integrity,
            "get_metrics": self._handle_get_metrics,
            "get_history": self._handle_get_history,
            # Trading dataset -- heuristics feed LLM for every validation
            "validate_trade_data": self._handle_validate_trade_data,
            "validate_pre_trade": self._handle_validate_pre_trade,
            "detect_contradictions": self._handle_detect_contradictions,
            "validate_trade_pipeline": self._handle_validate_trade_pipeline,
            "get_trade_metrics": self._handle_get_trade_metrics,
            "run_trade_hourly_analysis": self._handle_trade_hourly_analysis,
            # Backtest DB-powered validation (Phase 2)
            "validate_trade_setup": self._handle_validate_trade_setup,
            "get_loss_patterns": self._handle_get_loss_patterns,
            "check_confluence": self._handle_check_confluence,
            "check_performance_drift": self._handle_check_performance_drift,
            "get_best_params": self._handle_get_best_params,
            "log_decision": self._handle_log_decision,
            "log_live_trade": self._handle_log_live_trade,
            "get_upcoming_news": self._handle_get_upcoming_news,
            # Full decision pipeline (Phase 3) — runs all 4 steps + logs
            "evaluate_trade": self._handle_evaluate_trade,
            # Position management (Phase 3) — all 12 exit rules
            "check_positions": self._handle_check_positions,
            # Unified validation with vision + intelligence + vault (Phase 4)
            "evaluate_with_full_context": self._handle_evaluate_with_full_context,
            # Trade history query
            "get_trade_history": self._handle_get_trade_history,
            # OANDA live data
            "get_live_price": self._handle_get_live_price,
            "get_recent_candles": self._handle_get_recent_candles,
            "get_account_summary": self._handle_get_account_summary,
            # Wolfram computational engine
            "wolfram_calculate": self._handle_wolfram_calculate,
        }

        # Initialize trading database query layer
        self._trading_db = None

        # Accumulated heuristic results for hourly batch LLM analysis
        self._trade_heuristic_history = []
        self._trade_history_max = 500

        # Initialize tracking
        self._boardroom = board_room
        self._setup_tracking()

    def _setup_tracking(self):
        """Set up journey tracking using V2 journeys database directly."""
        def v2_track(journey_id, step_name=None, description=None,
                     step_type=None, input_data=None, output_data=None,
                     error=None, metadata=None, status=None):
            self.logger.info(f"V2 tracking: {step_name} ({step_type}) for journey {journey_id}")
            try:
                if input_data and isinstance(input_data, (dict, list)):
                    input_data = json.dumps(input_data)
                if output_data and isinstance(output_data, (dict, list)):
                    output_data = json.dumps(output_data)
                with v2_connection("journeys") as conn:
                    conn.execute('''
                        INSERT INTO journey_steps
                        (journey_id, step_name, step_type, description, input_data, output_data, error, status)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (journey_id, step_name, step_type or step_name, description,
                          input_data, output_data, error, status))
                return True
            except Exception as e:
                self.logger.error(f"Error in V2 tracking: {str(e)}")
            return None

        self._track_journey_step_fn = v2_track

        # If tracker was injected, wrap it with V2 fallback
        if self._boardroom and hasattr(self._boardroom, 'track_journey_step'):
            original_fn = self._boardroom.track_journey_step

            def wrapped_track(journey_id, step_name=None, description=None,
                             step_type=None, input_data=None, output_data=None,
                             error=None, metadata=None, status=None, **kwargs):
                try:
                    return original_fn(
                        journey_id=journey_id,
                        step_type=step_type or step_name,
                        step_name=step_name,
                        description=description,
                        input_data=input_data,
                        output_data=output_data,
                        error=error,
                        metadata=metadata
                    )
                except Exception as e:
                    self.logger.warning(f"Tracker failed: {e}, using V2 fallback")
                    return v2_track(journey_id, step_name, description,
                                    step_type, input_data, output_data, error, metadata, status)

            self._track_journey_step_fn = wrapped_track
            self.logger.info("Successfully connected to injected tracker for tracking")

        self._initialize_tracking_tables()

    def _initialize_tracking_tables(self):
        """Initialize database tables for tracking validation metrics in V2 journeys DB."""
        try:
            with v2_connection("journeys") as conn:
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS validation_metrics (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        validation_id TEXT,
                        journey_id TEXT,
                        workspace_id TEXT,
                        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                        success BOOLEAN,
                        execution_time FLOAT,
                        error_count INTEGER,
                        data_size INTEGER
                    )
                ''')

                conn.execute('''
                    CREATE TABLE IF NOT EXISTS journey_steps (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        journey_id TEXT NOT NULL,
                        step_type TEXT,
                        step_name TEXT,
                        description TEXT,
                        input_data TEXT,
                        output_data TEXT,
                        error TEXT,
                        status TEXT,
                        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
        except Exception as e:
            self.logger.error(f"Error creating tracking tables: {str(e)}")

    @property
    def _db(self):
        """Legacy property — callers should migrate to v2_connection('journeys') context manager."""
        if hasattr(self, 'db_manager') and self.db_manager and hasattr(self.db_manager, 'connection'):
            return self.db_manager
        return None

    @property
    def db(self):
        """Get the database connection from the database manager."""
        if hasattr(self, 'db_manager') and self.db_manager and hasattr(self.db_manager, 'connection'):
            return self.db_manager.connection
        return None

    @db.setter
    def db(self, value):
        if hasattr(self, 'db_manager') and self.db_manager:
            self.db_manager.connection = value

    @property
    def orchestrator_agent(self):
        """Get the orchestrator agent for this handler"""
        return self._orchestrator_agent

    # ==================== CORE VALIDATION METHODS (Anthropic-powered) ====================

    def _call_anthropic(self, system_prompt: str, user_prompt: str, max_tokens: int = 1024) -> str:
        """
        Make a call to Anthropic's Claude API for AI-powered validation.

        Args:
            system_prompt: System prompt for the validation context
            user_prompt: The validation prompt with data to check
            max_tokens: Maximum tokens in response

        Returns:
            str: The response text from Claude

        Raises:
            RuntimeError: If Anthropic client is not available
        """
        if not self.anthropic_client:
            raise RuntimeError("Anthropic client not initialized — check API key")

        response = self.anthropic_client.messages.create(
            model=VALIDATION_MODEL,
            max_tokens=max_tokens,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
            temperature=0
        )

        return response.content[0].text

    def _call_llm(
        self,
        system_prompt: str,
        content_blocks: list,
        max_tokens: int = 2500,
        model: str = None,
    ) -> str:
        """Unified LLM call — routes to Anthropic API or local model.

        When LOCAL_MODEL_ENABLED is True, routes ALL calls (text + vision) to
        the local MLX model. When False, uses Anthropic API.
        When GHOST_MODE_ENABLED is True, also runs local model in background
        and logs comparison for verdict matching analysis.

        Args:
            system_prompt: System prompt
            content_blocks: List of content blocks (text + optional image blocks).
            max_tokens: Max response tokens
            model: Model override

        Returns:
            str: Response text (from primary model)
        """
        if LOCAL_MODEL_ENABLED:
            return self._call_local_model(system_prompt, content_blocks, max_tokens)

        # Primary: Anthropic
        anthropic_response = self._call_anthropic_vision(system_prompt, content_blocks, max_tokens, model)

        # Ghost: run local model in parallel thread (non-blocking)
        if GHOST_MODE_ENABLED:
            import threading
            def _ghost_compare():
                try:
                    local_response = self._call_local_model(system_prompt, content_blocks, max_tokens)
                    self._log_ghost_comparison(anthropic_response, local_response, content_blocks)
                except Exception as e:
                    self.logger.warning("[GHOST] Local model call failed: %s", e)
            threading.Thread(target=_ghost_compare, daemon=True).start()

        return anthropic_response

    def _get_validator_tools(self) -> list:
        """Build Anthropic tool definitions from action_handlers that the validator can call.

        Only exposes DB query tools — not write/mutation tools.
        """
        return [
            {
                "name": "validate_trade_setup",
                "description": (
                    "Query 46K backtest trades for historical performance of a setup. "
                    "Valid setup names: S1 (hammer), S2 (engulfing), S3 (morning/evening star), S4 (doji), "
                    "S5 (BB+stoch), S6 (BB+stoch sell), S7 (MACD+RSI), S8 (SAR+EMA), S9 (EMA trend), "
                    "S10 (fibonacci), S11 (SMA50/100+MACD), S12 (BB squeeze), S13 (stochastic range), "
                    "S14 (momentum divergence), S15 (hidden divergence), S16 (SAR reverse), "
                    "S17 (triangle breakout), S18 (head & shoulders), S19 (double top/bottom), S20 (flag). "
                    "Returns win_rate, profit_factor, trade_count, best_session."
                ),
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "pair": {"type": "string", "description": "e.g. EUR_USD"},
                        "setup": {"type": "string", "description": "Setup code: S1-S20"},
                        "direction": {"type": "string", "description": "buy or sell"},
                        "regime": {"type": "string", "description": "trending, ranging, exhaustion, compression (optional)"},
                    },
                    "required": ["pair"],
                },
            },
            {
                "name": "get_loss_patterns",
                "description": "Get loss pattern analysis — what indicator conditions led to losses for a setup.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "pair": {"type": "string"},
                        "setup": {"type": "string", "description": "S1-S20"},
                    },
                    "required": ["pair"],
                },
            },
            {
                "name": "check_confluence",
                "description": "Check historical win rate when multiple setups fire together.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "pair": {"type": "string"},
                        "setups": {"type": "array", "items": {"type": "string"}, "description": "e.g. ['S5', 'S14']"},
                    },
                    "required": ["pair", "setups"],
                },
            },
            {
                "name": "get_upcoming_news",
                "description": "Check for upcoming high-impact economic events that could affect the trade.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "currencies": {"type": "array", "items": {"type": "string"}, "description": "e.g. ['NZD', 'USD']"},
                        "hours_ahead": {"type": "integer", "description": "How far ahead to look (default 24)"},
                    },
                    "required": ["currencies"],
                },
            },
            {
                "name": "get_trade_history",
                "description": "Get recent trade outcomes for a pair — wins, losses, pips, streaks.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "pair": {"type": "string", "description": "e.g. NZD_USD"},
                        "limit": {"type": "integer", "description": "Number of recent trades (default 10)"},
                    },
                    "required": ["pair"],
                },
            },
            {
                "name": "get_live_price",
                "description": "Get current live bid/ask price for a pair from OANDA. Use to confirm current price levels for snipe entry zones.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "pair": {"type": "string", "description": "e.g. NZD_USD"},
                    },
                    "required": ["pair"],
                },
            },
            {
                "name": "get_recent_candles",
                "description": "Get recent M15 candle data from OANDA — OHLC prices, EMAs, current spread. Use to check current indicator values when they weren't provided in the data package.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "pair": {"type": "string", "description": "e.g. NZD_USD"},
                        "count": {"type": "integer", "description": "Number of candles (default 10, max 50)"},
                        "granularity": {"type": "string", "description": "M15, H1, H4 (default M15)"},
                    },
                    "required": ["pair"],
                },
            },
            {
                "name": "get_account_summary",
                "description": "Get OANDA account summary — balance, unrealized P&L, open trade count, margin used.",
                "input_schema": {
                    "type": "object",
                    "properties": {},
                },
            },
            {
                "name": "wolfram_calculate",
                "description": (
                    "Run computational queries via Wolfram Alpha. Use for mathematical analysis, "
                    "statistical calculations, and financial computations the validator needs. Examples:\n"
                    "- 'linear regression of {1.0850, 1.0842, 1.0835, 1.0828, 1.0820}' (EMA trend direction)\n"
                    "- 'standard deviation of {12, -5, 8, -3, 15, -7, 10}' (pip volatility)\n"
                    "- 'correlation of {1.08, 1.07, 1.06} and {0.58, 0.57, 0.56}' (pair correlation)\n"
                    "- 'fibonacci retracement levels between 1.0900 and 1.0800' (key price levels)\n"
                    "- 'probability of 7 successes in 10 trials with probability 0.65' (win rate)\n"
                    "- 'NZD/USD exchange rate' (current live rate)\n"
                    "- 'US 10 year treasury yield' (macro rates)\n"
                    "- 'gold spot price' (commodity correlation)\n"
                    "- 'MACD 12 26 9 of {close prices}' (technical indicator calculation)\n"
                    "- 'moving average of {data} with period 14' (EMA/SMA from raw data)\n"
                    "- 'solve for x: risk = 0.01 * balance, pips = x, pip_value = 10' (position sizing)\n"
                ),
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Natural language math/stats/financial query for Wolfram Alpha"},
                    },
                    "required": ["query"],
                },
            },
        ]

    def _call_llm_with_tools(
        self,
        system_prompt: str,
        content_blocks: list,
        max_tokens: int = 2500,
        model: str = None,
        max_tool_rounds: int = 5,
    ) -> tuple:
        """Call Claude with tool use support. Returns (response_text, tool_calls_log).

        The LLM can call DB query tools during its reasoning. We execute the tools
        and feed results back until the LLM produces a final text response.
        """
        if not self.anthropic_client:
            raise RuntimeError("Anthropic client not initialized")

        tools = self._get_validator_tools()
        has_images = any(b.get("type") == "image" for b in content_blocks if isinstance(b, dict))
        default_model = VISION_MODEL if has_images else VALIDATION_MODEL

        messages = [{"role": "user", "content": content_blocks}]
        tool_calls_log = []

        for round_num in range(max_tool_rounds):
            response = self.anthropic_client.messages.create(
                model=model or default_model,
                max_tokens=max_tokens,
                system=system_prompt,
                messages=messages,
                tools=tools if tools else None,
                temperature=0,
            )

            # Check if the response has tool use
            has_tool_use = any(b.type == "tool_use" for b in response.content)

            if not has_tool_use or response.stop_reason == "end_turn":
                # Final response — extract text
                text_parts = [b.text for b in response.content if b.type == "text"]
                return "\n".join(text_parts), tool_calls_log

            # Execute tool calls
            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    tool_name = block.name
                    tool_input = block.input
                    self.logger.info(f"[VALIDATOR_TOOL] Round {round_num+1}: {tool_name}({json.dumps(tool_input)[:100]})")

                    # Execute the tool
                    try:
                        handler_fn = self.action_handlers.get(tool_name)
                        if handler_fn:
                            # Normalize param names (LLM may use setup_name, handler expects setup)
                            if "setup_name" in tool_input and "setup" not in tool_input:
                                tool_input["setup"] = tool_input.pop("setup_name")
                            import asyncio
                            try:
                                loop = asyncio.get_running_loop()
                                import concurrent.futures
                                with concurrent.futures.ThreadPoolExecutor() as pool:
                                    result = pool.submit(
                                        lambda fn=handler_fn, inp=tool_input: asyncio.run(fn(inp))
                                    ).result(timeout=30)
                            except RuntimeError:
                                result = asyncio.run(handler_fn(tool_input))
                            tool_output = json.dumps(result, default=str)[:3000]
                        else:
                            tool_output = json.dumps({"error": f"Unknown tool: {tool_name}"})
                    except Exception as e:
                        tool_output = json.dumps({"error": str(e)})
                        self.logger.warning(f"[VALIDATOR_TOOL] {tool_name} failed: {e}")

                    tool_calls_log.append({
                        "tool": tool_name,
                        "input": tool_input,
                        "output_preview": tool_output[:200],
                    })
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": tool_output,
                    })

            # Add assistant message + tool results and continue
            messages.append({"role": "assistant", "content": response.content})
            messages.append({"role": "user", "content": tool_results})

        # Max rounds exceeded — extract whatever text we have
        text_parts = [b.text for b in response.content if b.type == "text"]
        return "\n".join(text_parts), tool_calls_log

    def _call_anthropic_vision(
        self,
        system_prompt: str,
        content_blocks: list,
        max_tokens: int = 2500,
        model: str = None,
    ) -> str:
        """Call Claude with vision support (text + images in content blocks).

        Args:
            system_prompt: System prompt
            content_blocks: List of content blocks — mix of text and image blocks.
            max_tokens: Max response tokens
            model: Model override (defaults to VISION_MODEL for vision, VALIDATION_MODEL otherwise)

        Returns:
            str: Response text from Claude
        """
        if not self.anthropic_client:
            raise RuntimeError("Anthropic client not initialized — check API key")

        # Auto-detect if this is a vision call (has image blocks)
        has_images = any(
            b.get("type") == "image" for b in content_blocks if isinstance(b, dict)
        )
        default_model = VISION_MODEL if has_images else VALIDATION_MODEL

        response = self.anthropic_client.messages.create(
            model=model or default_model,
            max_tokens=max_tokens,
            system=system_prompt,
            messages=[{"role": "user", "content": content_blocks}],
            temperature=0,
        )

        return response.content[0].text

    def _call_local_model(
        self,
        system_prompt: str,
        content_blocks: list,
        max_tokens: int = 2500,
    ) -> str:
        """Call local MLX model via OpenAI-compatible endpoint.

        The local 35B model supports multi-modal (text + images). Content blocks
        are converted to OpenAI vision format for image support.

        Args:
            system_prompt: System prompt
            content_blocks: List of content blocks (text + image blocks)
            max_tokens: Max response tokens

        Returns:
            str: Response text from local model
        """
        try:
            from openai import OpenAI
        except ImportError:
            self.logger.warning("OpenAI SDK not available for local model — falling back to Anthropic")
            return self._call_anthropic_vision(system_prompt, content_blocks, max_tokens)

        client = OpenAI(base_url=f"http://localhost:{LOCAL_MODEL_PORT}", api_key="mlx-local")

        # Convert Anthropic content blocks to OpenAI vision format
        openai_content = []
        for block in content_blocks:
            if isinstance(block, dict):
                if block.get("type") == "text":
                    openai_content.append({"type": "text", "text": block["text"]})
                elif block.get("type") == "image":
                    # Anthropic: {"type": "image", "source": {"type": "base64", "media_type": "...", "data": "..."}}
                    # OpenAI:    {"type": "image_url", "image_url": {"url": "data:image/png;base64,..."}}
                    source = block.get("source", {})
                    media_type = source.get("media_type", "image/png")
                    data = source.get("data", "")
                    openai_content.append({
                        "type": "image_url",
                        "image_url": {"url": f"data:{media_type};base64,{data}"},
                    })
            elif isinstance(block, str):
                openai_content.append({"type": "text", "text": block})

        try:
            response = client.chat.completions.create(
                model=LOCAL_MODEL_NAME,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": openai_content},
                ],
                max_tokens=max_tokens,
                temperature=0,
            )
            result = response.choices[0].message.content

            # Strip Qwen3 thinking tags if present
            import re
            result = re.sub(r"<think>[\s\S]*?</think>", "", result).strip()
            return result
        except Exception as e:
            self.logger.error(f"Local model call failed: {e} — falling back to Anthropic")
            return self._call_anthropic_vision(system_prompt, content_blocks, max_tokens)

    def _log_ghost_comparison(self, anthropic_response: str, local_response: str,
                              content_blocks: list) -> None:
        """Log Anthropic vs local model verdicts for ghost trading comparison.

        Parses both responses for verdict/direction/confidence and logs to
        ghost_verdicts table for analysis. 95%+ match rate needed to graduate.
        """
        import json
        import re
        import sqlite3
        from datetime import datetime, timezone

        def _extract_verdict(raw: str) -> dict:
            """Extract verdict JSON from raw LLM response."""
            text = raw.strip()
            # Strip markdown code blocks
            text = re.sub(r"```(?:json)?\s*", "", text)
            text = re.sub(r"```\s*$", "", text)
            text = text.strip()
            try:
                parsed = json.loads(text)
            except json.JSONDecodeError:
                match = re.search(r'\{[^{}]*"verdict"[^{}]*\}', text, re.DOTALL)
                if match:
                    try:
                        parsed = json.loads(match.group())
                    except json.JSONDecodeError:
                        parsed = {}
                else:
                    parsed = {}
            return {
                "verdict": str(parsed.get("verdict", "PARSE_ERROR")).upper(),
                "direction": str(parsed.get("direction", "")).upper() or None,
                "confidence": float(parsed.get("confidence", 0)),
                "reasoning": str(parsed.get("reasoning", "")),
            }

        anthropic_parsed = _extract_verdict(anthropic_response)
        local_parsed = _extract_verdict(local_response)

        # Extract pair from content blocks
        pair = "UNKNOWN"
        for block in content_blocks:
            if isinstance(block, dict) and block.get("type") == "text":
                text = block.get("text", "")
                import re as _re
                m = _re.search(r"(EUR|GBP|USD|AUD|NZD|CAD|CHF|JPY)_(EUR|GBP|USD|AUD|NZD|CAD|CHF|JPY)", text)
                if m:
                    pair = m.group(0)
                    break

        verdict_match = anthropic_parsed["verdict"] == local_parsed["verdict"]
        direction_match = anthropic_parsed["direction"] == local_parsed["direction"]
        confidence_delta = abs(anthropic_parsed["confidence"] - local_parsed["confidence"])

        self.logger.info(
            "[GHOST] %s: Anthropic=%s/%s (%.2f) vs Local=%s/%s (%.2f) — verdict %s, direction %s",
            pair,
            anthropic_parsed["verdict"], anthropic_parsed["direction"], anthropic_parsed["confidence"],
            local_parsed["verdict"], local_parsed["direction"], local_parsed["confidence"],
            "MATCH" if verdict_match else "MISMATCH",
            "MATCH" if direction_match else "MISMATCH",
        )

        # Write to DB
        try:
            db_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                "Database", "v2", "trading_forex.db"
            )
            conn = sqlite3.connect(db_path, timeout=10)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS ghost_verdicts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    pair TEXT NOT NULL,
                    anthropic_verdict TEXT,
                    anthropic_direction TEXT,
                    anthropic_confidence REAL,
                    anthropic_reasoning TEXT,
                    anthropic_raw_response TEXT,
                    local_verdict TEXT,
                    local_direction TEXT,
                    local_confidence REAL,
                    local_reasoning TEXT,
                    local_raw_response TEXT,
                    verdict_match BOOLEAN,
                    direction_match BOOLEAN,
                    confidence_delta REAL,
                    local_model TEXT
                )
            """)
            conn.execute("""
                INSERT INTO ghost_verdicts (
                    timestamp, pair,
                    anthropic_verdict, anthropic_direction, anthropic_confidence, anthropic_reasoning,
                    anthropic_raw_response,
                    local_verdict, local_direction, local_confidence, local_reasoning,
                    local_raw_response,
                    verdict_match, direction_match, confidence_delta, local_model
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                datetime.now(timezone.utc).isoformat(), pair,
                anthropic_parsed["verdict"], anthropic_parsed["direction"],
                anthropic_parsed["confidence"], anthropic_parsed["reasoning"],
                anthropic_response,
                local_parsed["verdict"], local_parsed["direction"],
                local_parsed["confidence"], local_parsed["reasoning"],
                local_response,
                verdict_match, direction_match, confidence_delta,
                LOCAL_MODEL_NAME,
            ))
            conn.commit()
            conn.close()
        except Exception as e:
            self.logger.warning("[GHOST] DB write failed: %s", e)

    async def validate_data(self, data: Dict[str, Any], rules: Dict[str, str] = None,
                           schema: Dict[str, Any] = None, journey_id: str = None) -> Dict[str, Any]:
        """
        High-level validation: combines schema validation + integrity validation.

        Args:
            data: The data to validate
            rules: Optional rules for integrity validation
            schema: Optional JSON schema (overrides self.schema if provided)
            journey_id: Optional journey ID for tracking

        Returns:
            Combined validation results with valid status and issues list
        """
        # Use explicit schema parameter, fall back to self.schema only if set
        active_schema = schema or self.schema
        start_time = time.time()
        journey_id = journey_id or self.current_journey_id
        issues = []
        valid = True

        try:
            self._track_journey_step_fn(
                journey_id=journey_id, step_name="validation_start",
                step_type="validation", input_data={"data": data}
            )
        except Exception:
            pass

        # Schema validation if schema is set
        if active_schema:
            try:
                schema_result = await self.validate_schema(active_schema, data, journey_id)
                if not schema_result.get('valid', False):
                    valid = False
                    issues.extend(schema_result.get('issues', []) if isinstance(schema_result.get('issues'), list) else
                                 [schema_result.get('error', 'Unknown schema validation error')])
            except Exception as e:
                valid = False
                issues.append(f"Error during schema validation: {str(e)}")

        # Integrity validation if rules provided
        if rules and valid:
            try:
                integrity_result = await self.validate_data_integrity(data, rules, journey_id)
                if not integrity_result.get('valid', False):
                    valid = False
                    issues.extend(integrity_result.get('issues', []))
            except Exception as e:
                valid = False
                issues.append(f"Error during integrity validation: {str(e)}")

        # AI reasoning validation (no rules needed — general quality check)
        if valid and not rules:
            try:
                ai_result = await self._perform_ai_validation(data)
                if not ai_result.get("is_valid", True):
                    valid = False
                    if ai_result.get("issue"):
                        issues.append(ai_result["issue"])
            except Exception as e:
                self.logger.warning(f"AI validation skipped: {str(e)}")

        execution_time = time.time() - start_time
        result = {"valid": valid, "issues": issues, "execution_time": execution_time}

        try:
            self._track_journey_step_fn(
                journey_id=journey_id, step_name="validation_complete",
                step_type="validation", output_data=result
            )
        except Exception:
            pass

        return result

    async def validate_schema(self, schema, data, journey_id=None):
        """Validate data against a JSON schema using jsonschema."""
        journey_id = journey_id or self.current_journey_id

        try:
            self._track_journey_step_fn(
                journey_id=journey_id, step_name="schema_validation_start",
                step_type="validation", input_data={"schema": schema, "data": data}
            )
        except Exception:
            pass

        try:
            jsonschema.validate(instance=data, schema=schema)

            try:
                self._track_journey_step_fn(
                    journey_id=journey_id, step_name="validation_success",
                    step_type="validation", output_data={"valid": True}
                )
            except Exception:
                pass

            return {"valid": True}

        except jsonschema.exceptions.ValidationError as e:
            error_msg = str(e)
            self.logger.warning(f"Validation error: {error_msg}")
            return {"valid": False, "error": error_msg}

        except jsonschema.exceptions.SchemaError as e:
            error_msg = f"Schema error: {str(e)}"
            self.logger.error(error_msg)
            return {"valid": False, "error": error_msg}

    async def validate_data_integrity(self, data: Dict[str, Any], rules: Dict[str, str], journey_id: str = None) -> Dict[str, Any]:
        """
        Validate data integrity using Anthropic Claude for AI-powered reasoning.

        Args:
            data: The data to validate
            rules: Rules for validation (field_name -> rule_description)
            journey_id: Optional journey ID for tracking

        Returns:
            Dict with valid status, issues list, and execution time
        """
        start_time = time.time()
        journey_id = journey_id or self.current_journey_id
        issues = []

        try:
            self._track_journey_step_fn(
                journey_id=journey_id, step_name="integrity_validation_start",
                step_type="validation", input_data={"data": data, "rules": rules}
            )
        except Exception:
            pass

        try:
            valid = True
            for field, rule in rules.items():
                if field not in data:
                    issues.append(f"Field '{field}' is missing from data")
                    valid = False
                    continue

                try:
                    if self.anthropic_client:
                        result = self._validate_field_with_ai(field, data[field], rule, full_record=data)
                        if not result.get("is_valid", True):
                            issues.append(result.get("issue", f"Validation failed for field '{field}'"))
                            valid = False
                    else:
                        self.logger.warning(f"Anthropic client not available, skipping AI validation for field '{field}'")
                except Exception as e:
                    error_msg = f"Error validating field '{field}': {str(e)}"
                    self.logger.error(error_msg)
                    issues.append(error_msg)
                    valid = False

            try:
                self._track_journey_step_fn(
                    journey_id=journey_id,
                    step_name="integrity_validation_success" if valid else "integrity_validation_error",
                    step_type="validation",
                    output_data={"valid": valid, "issues": issues}
                )
            except Exception:
                pass

        except Exception as e:
            error_msg = f"Error during integrity validation: {str(e)}"
            issues.append(error_msg)
            valid = False

        return {"valid": valid, "issues": issues, "execution_time": time.time() - start_time}

    async def validate_integrity(self, data: Dict[str, Any], rules: Dict[str, str], journey_id: str = None) -> Dict[str, Any]:
        """Alias for validate_data_integrity."""
        return await self.validate_data_integrity(data, rules, journey_id)

    def _validate_field_with_ai(self, field: str, value: Any, rule: str,
                                full_record: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Use Anthropic Claude to validate a single field value against a rule.

        Args:
            field: Field name
            value: Field value
            rule: Validation rule description
            full_record: Optional full data record for cross-field context

        Returns:
            Dict with is_valid and issue keys
        """
        context_section = ""
        if full_record:
            # Provide other fields as context for cross-field rules
            other_fields = {k: v for k, v in full_record.items() if k != field}
            if other_fields:
                context_section = f"\nOther fields in this record (for cross-field validation):\n{json.dumps(other_fields, indent=2)}\n"

        prompt = f"""Analyze the following value against the specified rule.

Field: {field}
Value: {value}
Rule: {rule}
{context_section}
Consider:
1. Does the value match the expected format/pattern?
2. Is the value logically consistent with the rule?
3. Are there any potential data quality issues?
4. Use the other fields for cross-field comparisons if the rule requires it.

Return only a JSON object with:
- "is_valid": boolean indicating if value is valid
- "issue": detailed explanation if invalid, null if valid"""

        try:
            content = self._call_anthropic(
                system_prompt="You are a data validation assistant. Return ONLY a raw JSON object with keys \"is_valid\" (boolean) and \"issue\" (string or null). No markdown, no code fences, no explanation.",
                user_prompt=prompt
            )

            # Strip markdown code fences if Claude wraps the response
            cleaned = content.strip()
            if cleaned.startswith("```"):
                # Remove opening fence (```json or ```)
                first_newline = cleaned.index("\n")
                cleaned = cleaned[first_newline + 1:]
                # Remove closing fence
                if cleaned.rstrip().endswith("```"):
                    cleaned = cleaned.rstrip()[:-3].rstrip()

            result = json.loads(cleaned)
            if not isinstance(result, dict) or "is_valid" not in result:
                raise ValueError("Invalid response format")
            return result

        except json.JSONDecodeError:
            return {"is_valid": False, "issue": f"Could not parse validation response for field '{field}'"}
        except Exception as e:
            self.logger.error(f"Error in AI field validation: {str(e)}")
            return {"is_valid": False, "issue": f"Error validating field '{field}': {str(e)}"}

    async def _perform_ai_validation(self, data) -> Dict[str, Any]:
        """
        General AI-powered data quality validation using Anthropic Claude.

        Args:
            data: The data to validate

        Returns:
            Dict with is_valid and issue keys
        """
        prompt = f"""You are a helpful assistant designed to validate the quality of datasets. You will be given a single row of data, and your task is to determine whether the data is valid.

- Carefully analyze the data for any inconsistencies, contradictions, missing values, or implausible information.
- Consider the logical relationships between different fields.
- Use your domain knowledge to assess the validity of the data.
- Focus solely on the information provided without making assumptions beyond the given data.

**Return only a JSON object** with the following two properties:
- "is_valid": a boolean (true or false) indicating whether the data is valid.
- "issue": if "is_valid" is false, provide a brief explanation of the issue; if "is_valid" is true, set "issue" to null.

DATA TO VALIDATE:
{json.dumps(data, indent=2)}"""

        try:
            content = self._call_anthropic(
                system_prompt="You are a data validation assistant. Return ONLY a raw JSON object with keys \"is_valid\" (boolean) and \"issue\" (string or null). No markdown, no code fences.",
                user_prompt=prompt,
                max_tokens=2000
            )

            # Strip markdown code fences if Claude wraps the response
            cleaned = content.strip()
            if cleaned.startswith("```"):
                first_newline = cleaned.index("\n")
                cleaned = cleaned[first_newline + 1:]
                if cleaned.rstrip().endswith("```"):
                    cleaned = cleaned.rstrip()[:-3].rstrip()

            result = json.loads(cleaned)
            if not isinstance(result, dict) or "is_valid" not in result or "issue" not in result:
                raise ValueError("Invalid response format")
            return result

        except json.JSONDecodeError:
            return {"is_valid": False, "issue": "Failed to parse validation response"}
        except Exception as e:
            self.logger.error(f"Error in AI validation: {str(e)}")
            return {"is_valid": False, "issue": f"Error during validation: {str(e)}"}

    async def _validate_field_dependencies(self, field: str, value: Any, dependencies: Dict[str, Any], rule_config: Dict) -> Dict[str, Any]:
        """Validate field dependencies using Anthropic Claude."""
        prompt = f"""Analyze if the field value is valid considering its dependencies.

Field: {field}
Value: {value}
Dependencies: {json.dumps(dependencies)}
Rules: {json.dumps(rule_config)}

Return only a JSON object with:
- "is_valid": boolean indicating if dependencies are valid
- "issue": detailed explanation if invalid, null if valid"""

        try:
            content = self._call_anthropic(
                system_prompt="You are a data validation assistant that analyzes relationships between fields.",
                user_prompt=prompt
            )
            result = json.loads(content)
            return {"valid": result["is_valid"], "message": result.get("issue")}
        except Exception as e:
            return {"valid": False, "message": f"Error validating dependencies for field '{field}': {str(e)}"}

    async def _validate_relationship(self, data: Dict[str, Any], relationship_config: Dict[str, Any]) -> Dict[str, Any]:
        """Validate relationships between fields using Anthropic Claude."""
        prompt = f"""Analyze if the relationship between fields is valid.

Data: {json.dumps(data)}
Relationship Rules: {json.dumps(relationship_config)}

Return only a JSON object with:
- "is_valid": boolean indicating if the relationship is valid
- "issue": detailed explanation if invalid, null if valid"""

        try:
            content = self._call_anthropic(
                system_prompt="You are a data validation assistant that analyzes relationships between fields.",
                user_prompt=prompt
            )
            result = json.loads(content)
            return {"valid": result["is_valid"], "message": result.get("issue")}
        except Exception as e:
            return {"valid": False, "message": f"Error validating relationship: {str(e)}"}

    # ==================== TRACKING & METRICS ====================

    async def track_validation_performance(self, validation_result: Dict, workspace_id: str = None):
        """Track validation performance metrics in V2 journeys database."""
        try:
            success = validation_result.get("valid", False)
            execution_time = validation_result.get("execution_time", 0)
            error_count = len(validation_result.get("issues", []))
            validation_id = validation_result.get("validation_id", generate_simple_id("val_"))

            with v2_connection("journeys") as conn:
                conn.execute('''
                    INSERT INTO validation_metrics
                    (validation_id, journey_id, workspace_id, success, execution_time, error_count)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (validation_id, self.current_journey_id, workspace_id, success, execution_time, error_count))

            return True
        except Exception as e:
            self.logger.error(f"Error tracking agent performance: {e}")
            return False

    async def get_validation_metrics(self, request_data):
        """Get metrics about the validation process from V2 journeys database."""
        try:
            with v2_connection("journeys") as conn:
                metrics_row = conn.execute('''
                    SELECT COUNT(*) as total,
                           SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as success_count
                    FROM validation_metrics
                ''').fetchone()
                total = metrics_row[0] if metrics_row else 0
                success_count = metrics_row[1] if metrics_row else 0

                avg_time_row = conn.execute('SELECT AVG(execution_time) FROM validation_metrics').fetchone()
                avg_time = avg_time_row[0] if avg_time_row and avg_time_row[0] else 0

                error_rows = conn.execute('''
                    SELECT error_count, COUNT(*) as count
                    FROM validation_metrics GROUP BY error_count ORDER BY error_count
                ''').fetchall()
                error_dist = {str(row[0]): row[1] for row in error_rows}

            success_rate = (success_count / total) * 100 if total > 0 else 0

            return {
                "status": "success",
                "metrics": {
                    "total_validations": total,
                    "success_count": success_count,
                    "success_rate": success_rate,
                    "avg_execution_time": avg_time,
                    "error_distribution": error_dist
                }
            }
        except Exception as e:
            self.logger.error(f"Error retrieving validation metrics: {str(e)}")
            return {"status": "error", "message": f"Failed to retrieve validation metrics: {str(e)}"}

    def get_validation_history(self, request_data=None):
        """Get validation history from the V2 journeys database."""
        try:
            limit = request_data.get("limit", 10) if request_data else 10
            with v2_connection("journeys") as conn:
                rows = conn.execute(
                    'SELECT * FROM validation_metrics ORDER BY timestamp DESC LIMIT ?', (limit,)
                ).fetchall()
                columns = [desc[0] for desc in conn.execute(
                    'SELECT * FROM validation_metrics LIMIT 0').description] if rows else []
                results = [dict(zip(columns, row)) for row in rows]

            return {"status": "success", "history": results}
        except Exception as e:
            self.logger.error(f"Error getting validation history: {str(e)}")
            return {"status": "error", "message": f"Failed to get validation history: {str(e)}"}

    def get_journey_steps(self, journey_id):
        """Get journey steps from the V2 journeys database for a specific journey."""
        try:
            with v2_connection("journeys") as conn:
                col_info = conn.execute("PRAGMA table_info(journey_steps)").fetchall()
                columns = [col[1] for col in col_info]
                time_column = "timestamp" if "timestamp" in columns else ("created_at" if "created_at" in columns else "id")

                rows = conn.execute(
                    f"SELECT * FROM journey_steps WHERE journey_id = ? ORDER BY {time_column}",
                    (journey_id,)
                ).fetchall()
                cols = [col[0] for col in conn.execute("SELECT * FROM journey_steps LIMIT 0").description] if rows else columns
                steps = [dict(zip(cols, row)) for row in rows]
            return steps
        except Exception as e:
            self.logger.error(f"Error retrieving journey steps: {str(e)}")
            return []

    # ==================== ORCHESTRATOR COMMUNICATION ====================

    async def send_message_to_jarvis(self, message: str, message_type: str = "update", context: Dict = None) -> Dict:
        """Send a message to the Jarvis orchestrator."""
        try:
            await self._track_bidirectional_communication("outbound", message, {
                "message_type": message_type, "context": context,
                "communication_type": "orchestrator_to_jarvis"
            })

            if self._boardroom and hasattr(self._boardroom, 'send_orchestrator_message'):
                return await self._boardroom.send_orchestrator_message(
                    message=message, sender_id=self.agent_id,
                    sender_type="orchestrator", message_type=message_type, context=context
                )
            else:
                return {"status": "error", "message": "No BoardRoom connection available"}
        except Exception as e:
            self.logger.error(f"Error sending message to Jarvis: {str(e)}")
            return {"status": "error", "message": str(e)}

    async def receive_message_from_jarvis(self, message: str, message_type: str = "instruction", context: Dict = None) -> Dict:
        """Handle a message received from Jarvis orchestrator."""
        try:
            await self._track_bidirectional_communication("inbound", message, {
                "message_type": message_type, "context": context
            })

            if message_type == "instruction":
                self.logger.info(f"Processing Jarvis instruction: {message}")
                return {"status": "success", "message": "Instruction processed", "instruction": message}
            else:
                return {"status": "warning", "message": f"Unknown message type: {message_type}"}
        except Exception as e:
            self.logger.error(f"Error processing message from Jarvis: {str(e)}")
            return {"status": "error", "message": str(e)}

    async def _track_bidirectional_communication(self, direction: str, message: str, metadata: Dict = None):
        """Track bidirectional communication with the Jarvis orchestrator."""
        try:
            communication_data = {
                "agent_id": self.agent_id, "agent_type": "orchestrator",
                "message": message, "timestamp": time.time(),
                "journey_id": self.current_journey_id, "metadata": metadata or {}
            }

            if self._boardroom and hasattr(self._boardroom, 'track_natural_language_communication'):
                await self._boardroom.track_natural_language_communication(
                    journey_id=self.current_journey_id, agent_id=self.agent_id,
                    message_type=direction, content=message, metadata=communication_data
                )

            self.communication_history.append(communication_data)
            if len(self.communication_history) > 100:
                self.communication_history = self.communication_history[-100:]
        except Exception as e:
            self.logger.warning(f"Error tracking communication: {e}")

    # ==================== HANDLER ENTRY POINT ====================

    def _track_validation_step(self, step_name: str, step_type: str = "validation", metadata: Optional[Dict] = None):
        """Track a validation step in the journey."""
        try:
            if self._boardroom and hasattr(self._boardroom, 'track_journey_step'):
                self._boardroom.track_journey_step(
                    journey_id=self.current_journey_id, step_name=step_name,
                    description=f"Validation step: {step_name}",
                    step_type=step_type, metadata=metadata or {}
                )
        except Exception as e:
            self.logger.error(f"Error tracking validation step: {str(e)}")

    def _track_validation_metrics(self, action: str, success: bool, execution_time: float):
        """Track validation metrics in the database."""
        try:
            if self.db_manager:
                self.db_manager.insert("validation_metrics", {
                    "journey_id": self.current_journey_id,
                    "action": action,
                    "success": success,
                    "execution_time": execution_time,
                    "timestamp": datetime.now().isoformat()
                })
        except Exception as e:
            self.logger.error(f"Error tracking validation metrics: {str(e)}")

    async def handle(self, request: Dict[str, Any], data: Dict[str, Any] = None) -> Dict[str, Any]:
        """Handle a validation request.

        Args:
            request: Dict with 'action' and 'parameters' keys
            data: Optional data override (if not provided, uses request['parameters'])
        """
        try:
            action = request.get('action')
            if not action:
                raise ValueError("No action specified in request")

            parameters = request.get('parameters', {})
            if data is not None:
                parameters['data'] = data

            self._track_validation_step(step_name=f"start_{action}", step_type="validation_start", metadata={"action": action})

            handler_fn = self.action_handlers.get(action)
            if not handler_fn:
                raise ValueError(f"Invalid action: {action}. Valid actions: {list(self.action_handlers.keys())}")

            start_time = time.time()
            try:
                result = await handler_fn(parameters)
                success = True
            except Exception as e:
                success = False
                result = {"error": str(e)}
                raise
            finally:
                execution_time = time.time() - start_time
                self._track_validation_metrics(action, success, execution_time)
                self._track_validation_step(
                    step_name=f"complete_{action}", step_type="validation_complete",
                    metadata={"action": action, "success": success, "execution_time": execution_time}
                )

            return result
        except Exception as e:
            self.logger.error(f"Error handling validation request: {str(e)}")
            self._track_validation_step(step_name="error", step_type="validation_error", metadata={"error": str(e)})
            raise

    # --- Action handler dispatch methods ---

    async def _handle_validate_data(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Dispatch for validate_data action."""
        data = params.get('data', {})
        rules = params.get('rules')
        schema = params.get('schema')
        journey_id = params.get('journey_id')
        return await self.validate_data(data, rules=rules, schema=schema, journey_id=journey_id)

    async def _handle_validate_schema(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Dispatch for validate_schema action."""
        schema = params.get('schema', self.schema)
        data = params.get('data', {})
        journey_id = params.get('journey_id')
        return await self.validate_schema(schema, data, journey_id=journey_id)

    async def _handle_validate_integrity(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Dispatch for validate_integrity action."""
        data = params.get('data', {})
        rules = params.get('rules', {})
        journey_id = params.get('journey_id')
        return await self.validate_data_integrity(data, rules, journey_id=journey_id)

    async def _handle_get_metrics(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Dispatch for get_metrics action."""
        return await self.get_validation_metrics(params)

    async def _handle_get_history(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Dispatch for get_history action."""
        return await self.get_validation_history(params)

    # ==================== TRADING DATASET ACTIONS (LLM-over-heuristics) ====================

    async def _handle_validate_trade_data(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Trading dataset: Gate 1 heuristics -> LLM final judgment."""
        tv = _get_trade_validator()
        if tv is None:
            return {"error": "TradeValidator not available -- Trading Bot Source not found"}

        # Step 1: Run heuristics (fast, <5ms)
        heuristic_result = tv.validate_data_integrity(
            candles=params.get("candles"),
            indicators_result=params.get("indicators_result"),
            advanced_result=params.get("advanced_result"),
            pattern_results=params.get("pattern_results"),
            alignment_snapshot=params.get("alignment_snapshot"),
            news_data=params.get("news_data"),
            aggregator_output=params.get("aggregator_output"),
        )

        heuristic_summary = {
            "gate": heuristic_result.gate,
            "passed": heuristic_result.passed,
            "issues": heuristic_result.issues,
            "confidence": heuristic_result.confidence,
            "data_type": heuristic_result.data_type,
        }

        # Step 2: Feed heuristics + raw data to LLM for final judgment
        llm_result = self._validate_trading_with_llm(
            validation_type="data_integrity",
            heuristic_summary=heuristic_summary,
            raw_data=params,
        )

        # Step 3: Accumulate for hourly batch
        self._accumulate_trade_result(heuristic_summary, llm_result)

        logger.info(
            "Trading validate_trade_data: heuristic_passed=%s llm_passed=%s confidence=%.2f",
            heuristic_summary["passed"],
            llm_result.get("passed"),
            llm_result.get("confidence", 0.0),
        )

        return {
            "heuristic": heuristic_summary,
            "llm_judgment": llm_result,
            "final_passed": llm_result.get("passed", heuristic_result.passed),
            "final_confidence": llm_result.get("confidence", heuristic_result.confidence),
            "elapsed_ms": heuristic_result.elapsed_ms,
        }

    async def _handle_validate_pre_trade(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Trading dataset: Gate 2 heuristics -> LLM final judgment on trade decision."""
        tv = _get_trade_validator()
        if tv is None:
            return {"error": "TradeValidator not available -- Trading Bot Source not found"}

        # Step 1: Run heuristics
        heuristic_result = tv.validate_pre_trade(
            trade_decision=params.get("trade_decision", {}),
            news_data=params.get("news_data"),
            risk_limits=params.get("risk_limits"),
            indicators_result=params.get("indicators_result"),
            advanced_result=params.get("advanced_result"),
            confluence_output=params.get("confluence_output"),
        )

        heuristic_summary = {
            "gate": heuristic_result.gate,
            "passed": heuristic_result.passed,
            "issues": heuristic_result.issues,
            "confidence": heuristic_result.confidence,
            "needs_llm_escalation": heuristic_result.needs_llm_escalation,
        }

        # Step 2: Feed heuristics + trade decision to LLM
        llm_result = self._validate_trading_with_llm(
            validation_type="pre_trade",
            heuristic_summary=heuristic_summary,
            raw_data=params,
        )

        # Step 3: Accumulate for hourly batch
        self._accumulate_trade_result(heuristic_summary, llm_result)

        logger.info(
            "Trading validate_pre_trade: heuristic_passed=%s llm_passed=%s recommendation=%s",
            heuristic_summary["passed"],
            llm_result.get("passed"),
            llm_result.get("recommendation", "unknown"),
        )

        return {
            "heuristic": heuristic_summary,
            "llm_judgment": llm_result,
            "final_passed": llm_result.get("passed", heuristic_result.passed),
            "final_confidence": llm_result.get("confidence", heuristic_result.confidence),
            "llm_recommendation": llm_result.get("recommendation", "proceed" if heuristic_result.passed else "hold"),
        }

    async def _handle_detect_contradictions(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Trading dataset: heuristic contradiction detection -> LLM interpretation."""
        tv = _get_trade_validator()
        if tv is None:
            return {"error": "TradeValidator not available"}

        # Step 1: Heuristic contradiction detection (13 rules)
        contradictions = tv.detect_contradictions(
            indicators_result=params.get("indicators_result"),
            advanced_result=params.get("advanced_result"),
            confluence_output=params.get("confluence_output"),
        )

        # Step 2: LLM interprets the contradictions in market context
        llm_result = self._validate_trading_with_llm(
            validation_type="contradiction_analysis",
            heuristic_summary=contradictions,
            raw_data=params,
        )

        logger.info(
            "Trading detect_contradictions: %d warnings, %d critical, llm_available=%s",
            len(contradictions.get("warnings", [])),
            len(contradictions.get("critical", [])),
            llm_result.get("llm_available", False),
        )

        return {
            "heuristic_contradictions": contradictions,
            "llm_interpretation": llm_result,
        }

    async def _handle_validate_trade_pipeline(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Trading dataset: full pipeline (Gate 1 + Gate 2 + contradictions) -> LLM final decision.

        This is the PRIMARY entry point for trading agents. Runs complete heuristic
        pipeline, feeds ALL results to LLM, returns final go/no-go with reasoning.
        """
        tv = _get_trade_validator()
        if tv is None:
            return {"error": "TradeValidator not available"}

        # Step 1: Full heuristic pipeline
        pipeline_result = tv.validate_full_pipeline(
            candles=params.get("candles", []),
            indicators_result=params.get("indicators_result"),
            advanced_result=params.get("advanced_result"),
            pattern_results=params.get("pattern_results"),
            trade_decision=params.get("trade_decision", {}),
            news_data=params.get("news_data"),
            risk_limits=params.get("risk_limits"),
            confluence_output=params.get("confluence_output"),
            alignment_snapshot=params.get("alignment_snapshot"),
            aggregator_output=params.get("aggregator_output"),
        )

        # Serialize heuristic results for LLM context
        heuristic_summary = {
            "overall_passed": pipeline_result["overall_passed"],
            "needs_llm_escalation": pipeline_result["needs_llm_escalation"],
            "total_elapsed_ms": pipeline_result["total_elapsed_ms"],
            "contradictions": pipeline_result["contradictions"],
        }
        if pipeline_result["gate_1"]:
            g1 = pipeline_result["gate_1"]
            heuristic_summary["gate_1"] = {
                "passed": g1.passed, "issues": g1.issues,
                "elapsed_ms": g1.elapsed_ms, "confidence": g1.confidence,
            }
        if pipeline_result["gate_2"]:
            g2 = pipeline_result["gate_2"]
            heuristic_summary["gate_2"] = {
                "passed": g2.passed, "issues": g2.issues,
                "elapsed_ms": g2.elapsed_ms, "confidence": g2.confidence,
            }

        # Step 2: Feed ENTIRE heuristic pipeline output to LLM for final decision
        llm_result = self._validate_trading_with_llm(
            validation_type="full_pipeline",
            heuristic_summary=heuristic_summary,
            raw_data=params,
        )

        # Step 3: Accumulate for hourly batch
        self._accumulate_trade_result(heuristic_summary, llm_result)

        logger.info(
            "Trading validate_trade_pipeline: heuristic_passed=%s llm_passed=%s llm_recommendation=%s",
            pipeline_result["overall_passed"],
            llm_result.get("passed"),
            llm_result.get("recommendation", "unknown"),
        )

        return {
            "heuristic": heuristic_summary,
            "llm_judgment": llm_result,
            "final_passed": llm_result.get("passed", pipeline_result["overall_passed"]),
            "final_confidence": llm_result.get("confidence", 0.5),
            "llm_recommendation": llm_result.get("recommendation", "hold"),
            "llm_reasoning": llm_result.get("reasoning", ""),
        }

    async def _handle_get_trade_metrics(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Get TradeValidator heuristic metrics + LLM validation stats."""
        tv = _get_trade_validator()
        metrics = tv.get_metrics() if tv else {}
        metrics["llm_validations_accumulated"] = len(self._trade_heuristic_history)
        return metrics

    async def _handle_trade_hourly_analysis(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Hourly batch: feed ALL accumulated heuristic results to LLM for systematic analysis.

        Called on a schedule (every hour) or on-demand. The LLM reviews all recent
        heuristic results looking for:
        - Systematic data quality issues (repeated failures in same data type)
        - Regime changes (heuristics becoming less reliable in current market)
        - Parameter drift (thresholds that need adjustment)
        - Pattern correlations (which contradictions preceded losses)
        """
        analyst = _get_validation_analyst()
        history = list(self._trade_heuristic_history)  # snapshot

        if not history:
            return {"status": "no_data", "message": "No accumulated heuristic results to analyze"}

        # Build comprehensive context for LLM
        hourly_context = json.dumps({
            "period": "last_hour",
            "total_validations": len(history),
            "results": history[-100:],  # last 100 for LLM context window
            "summary": {
                "total_passed": sum(1 for h in history if h.get("heuristic", {}).get("passed")),
                "total_failed": sum(1 for h in history if not h.get("heuristic", {}).get("passed")),
                "llm_overrides": sum(1 for h in history if h.get("llm_disagreed")),
                "avg_confidence": sum(h.get("heuristic", {}).get("confidence", 0) for h in history) / max(len(history), 1),
            },
        }, indent=2, default=str)

        # LLM systematic analysis via handler's _call_anthropic
        llm_analysis = None
        try:
            llm_analysis = self._call_anthropic(
                system_prompt=(
                    "You are a trading data quality analyst. You are reviewing the accumulated "
                    "heuristic validation results from the last hour. Identify systematic issues, "
                    "regime changes, parameter drift, and patterns that need attention. "
                    "Return JSON with: systematic_issues (list), regime_observations (str), "
                    "parameter_recommendations (list of {param, current, suggested, reason}), "
                    "overall_health (good/warning/critical), summary (str)."
                ),
                user_prompt=f"Hourly heuristic validation batch:\n\n{hourly_context}",
                max_tokens=2000,
            )
        except Exception as e:
            logger.error(f"Hourly LLM analysis failed: {e}")

        # Also run ValidationAnalyst's hourly analysis if available
        analyst_result = None
        if analyst and hasattr(analyst, 'analyze_hourly'):
            try:
                analyst_result = analyst.analyze_hourly()
            except Exception as e:
                logger.warning(f"ValidationAnalyst hourly analysis failed: {e}")

        parsed = {}
        if llm_analysis:
            try:
                parsed = json.loads(llm_analysis)
            except (json.JSONDecodeError, TypeError):
                parsed = {"raw_analysis": str(llm_analysis), "overall_health": "unknown"}

        logger.info(
            "Trading hourly analysis: %d validations analyzed, health=%s",
            len(history),
            parsed.get("overall_health", "unknown"),
        )

        return {
            "handler_llm_analysis": parsed,
            "validation_analyst_result": analyst_result,
            "validations_analyzed": len(history),
        }

    # ==================== TRADING CONTEXT ASSEMBLY ====================

    def _assemble_trading_context(self, instrument: str, raw_data: dict) -> dict:
        """Assemble ALL available trading data sources for LLM context.

        A master trader does not make decisions from one data source. They pull
        together: current market data, heuristic analysis, historical performance,
        visual chart context, instrument behavior, and accumulated knowledge.

        This method gathers from every available source and structures it for
        the LLM. Sources that are not available yet (e.g. backtesting before
        Phase 11) gracefully return empty -- the LLM works with what is available
        and gets smarter as more data sources come online.

        Data sources assembled:
        1. Knowledge Store -- per-instrument patterns, win rates, learned parameters
        2. Positive Patterns KB -- winning trade examples from backtesting
        3. Recent Trade Snapshots -- recent chart images and indicator state
        4. Instrument Profile -- spread, ATR, volatility, session behavior
        5. Raw data is passed through separately (indicators, candles, etc.)

        Returns:
            Dict with each data source's contribution (empty dict if unavailable)
        """
        context = {
            "instrument": instrument,
            "knowledge_store": {},
            "positive_patterns": {},
            "recent_snapshots": [],
            "instrument_profile": {},
            "data_sources_available": [],
        }

        # 1. Knowledge Store -- historical patterns and win rates
        ks = _get_knowledge_store()
        if ks:
            try:
                knowledge = ks.get_knowledge(instrument)
                patterns = ks.get_patterns(instrument)
                if knowledge or patterns:
                    context["knowledge_store"] = {
                        "patterns": patterns,
                        "parameters": knowledge.get("parameters", {}),
                        "performance": knowledge.get("performance", {}),
                        "statistics": knowledge.get("statistics", {}),
                    }
                    context["data_sources_available"].append("knowledge_store")
                    logger.info(f"Knowledge store loaded: {len(patterns)} patterns for {instrument}")
            except Exception as e:
                logger.warning(f"Knowledge store load failed: {e}")

        # 2. Positive Patterns KB -- winning trade examples (populated by Phase 11 backtesting)
        try:
            kb_path = Path("Forex Trading Team/Data") / instrument / "knowledge_base" / "positive_patterns.json"
            if kb_path.exists():
                with open(kb_path) as f:
                    positive = json.load(f)
                context["positive_patterns"] = {
                    "count": len(positive.get("patterns", [])),
                    "examples": positive.get("patterns", [])[:10],  # top 10 for context window
                    "summary": positive.get("summary", ""),
                }
                context["data_sources_available"].append("positive_patterns_kb")
        except Exception as e:
            logger.debug(f"Positive patterns KB not available: {e}")

        # 3. Recent Trade Snapshots -- what the chart looked like on recent trades
        try:
            snap_dir = Path("Forex Trading Team/Data") / instrument / "snapshots"
            if snap_dir.exists():
                # Get most recent snapshot directory (sorted by date)
                date_dirs = sorted(snap_dir.iterdir(), reverse=True)
                recent_snaps = []
                for date_dir in date_dirs[:3]:  # last 3 days
                    json_files = sorted(date_dir.glob("*.json"), reverse=True)
                    for jf in json_files[:5]:  # last 5 snapshots per day
                        try:
                            with open(jf) as f:
                                snap = json.load(f)
                            # Include the image path so multimodal LLM can reference it
                            png_path = jf.with_suffix(".png")
                            snap["_chart_image_path"] = str(png_path) if png_path.exists() else None
                            recent_snaps.append(snap)
                        except Exception:
                            pass
                    if len(recent_snaps) >= 10:
                        break
                if recent_snaps:
                    context["recent_snapshots"] = recent_snaps
                    context["data_sources_available"].append("trade_snapshots")
        except Exception as e:
            logger.debug(f"Trade snapshots not available: {e}")

        # 4. Instrument Profile -- spread, ATR, volatility, session data
        ProfileClass = _get_instrument_profile()
        if ProfileClass:
            try:
                profile_path = Path("Forex Trading Team/Data") / instrument / "profile.json"
                if profile_path.exists():
                    with open(profile_path) as f:
                        profile_data = json.load(f)
                    context["instrument_profile"] = {
                        "spread": profile_data.get("spread", {}),
                        "atr": profile_data.get("atr", {}),
                        "volatility": profile_data.get("volatility", {}),
                        "sessions": profile_data.get("sessions", {}),
                    }
                    context["data_sources_available"].append("instrument_profile")
            except Exception as e:
                logger.debug(f"Instrument profile not available: {e}")

        logger.info(f"Trading context assembled for {instrument}: {context['data_sources_available']}")
        return context

    def _validate_trading_with_llm(self, validation_type: str,
                                    heuristic_summary: dict,
                                    raw_data: dict) -> dict:
        """Feed heuristic results + ALL available trading context to LLM for final judgment.

        The LLM gets EVERYTHING a master trader would use:
        1. Heuristic analysis (fast rule-based checks)
        2. Historical pattern data (what happened in similar setups)
        3. Winning trade examples (what good trades looked like)
        4. Instrument behavior (spread, volatility, session context)
        5. Recent chart snapshots (what the market has been doing)
        6. Raw current data (indicators, candles, patterns, news)

        The LLM compares current setup against historical knowledge, validates
        the heuristic assessment, and makes the final call with full context.

        Args:
            validation_type: "data_integrity", "pre_trade", "contradiction_analysis", "full_pipeline"
            heuristic_summary: Structured output from TradeValidator heuristics
            raw_data: Original parameters (indicators, candles, trade decision, etc.)

        Returns:
            Dict with passed, confidence, recommendation, reasoning
        """
        if not HAS_ANTHROPIC or not self.anthropic_client:
            logger.warning("Anthropic SDK not available -- returning heuristic result only")
            return {
                "passed": heuristic_summary.get("passed", heuristic_summary.get("overall_passed", False)),
                "confidence": heuristic_summary.get("confidence", 0.5),
                "recommendation": "proceed" if heuristic_summary.get("passed") else "hold",
                "reasoning": "LLM unavailable -- heuristic result used as fallback",
                "llm_available": False,
            }

        # Extract instrument from raw_data for context assembly
        instrument = (raw_data.get("instrument")
                      or raw_data.get("trade_decision", {}).get("instrument")
                      or "unknown")

        # Assemble ALL trading data sources
        trading_context = self._assemble_trading_context(instrument, raw_data)

        # Build the master trader system prompt
        system_prompt = (
            "You are a master forex trader making a validation decision. You have access to:\n"
            "1. HEURISTIC ANALYSIS -- fast rule-based checks (Gate 1 data integrity, Gate 2 pre-trade, "
            "13 contradiction rules)\n"
            "2. HISTORICAL KNOWLEDGE -- per-instrument pattern win rates, learned parameters, "
            "and performance stats from past trades\n"
            "3. WINNING TRADE EXAMPLES -- what similar successful trades looked like "
            "(from backtesting knowledge base, grows over time)\n"
            "4. INSTRUMENT PROFILE -- spread behavior, ATR ranges, volatility classification, "
            "session-specific characteristics\n"
            "5. RECENT SNAPSHOTS -- what the market did on recent validated signals\n"
            "6. CURRENT MARKET DATA -- live indicators, candles, patterns, news\n\n"
            "Compare the current setup against historical data. Does this setup match "
            "patterns that historically won? Does the instrument behave well in this regime? "
            "Do the heuristics align with what you see in the data?\n\n"
            "Be conservative -- protect the account. When historical data is thin, weight "
            "heuristics more heavily. As the knowledge base grows, let historical evidence "
            "guide your confidence.\n\n"
            "Return ONLY a JSON object with:\n"
            '- "passed": boolean (your FINAL judgment)\n'
            '- "confidence": float 0.0-1.0\n'
            '- "recommendation": "proceed" | "hold" | "reduce_size"\n'
            '- "reasoning": your analysis referencing specific data sources used\n'
            '- "heuristic_agreement": boolean (do you agree with the heuristic result?)\n'
            '- "historical_match": string (how well does this match historical winners?)\n'
            '- "data_quality_note": string (any concerns about the data)\n'
            '- "issues_found": list of any additional issues beyond heuristics'
        )

        # Truncate raw_data for context window (keep structure, limit arrays)
        truncated_data = {}
        for k, v in raw_data.items():
            if isinstance(v, list) and len(v) > 10:
                truncated_data[k] = f"[{len(v)} items, last 5: {json.dumps(v[-5:], default=str)}]"
            elif isinstance(v, dict) and len(json.dumps(v, default=str)) > 2000:
                truncated_data[k] = f"[large dict, {len(v)} keys: {list(v.keys())}]"
            else:
                truncated_data[k] = v

        # Truncate knowledge store for context window
        ks_summary = trading_context.get("knowledge_store", {})
        if ks_summary.get("patterns"):
            # Summarize patterns: name, win_rate, count for each
            ks_summary["patterns"] = {
                name: {k: v for k, v in data.items() if k in ("count", "win_rate", "avg_return", "last_seen")}
                for name, data in list(ks_summary["patterns"].items())[:20]
            }

        # Summarize recent snapshots (just outcomes and actions, not full data)
        snap_summary = []
        for snap in trading_context.get("recent_snapshots", [])[:5]:
            snap_summary.append({
                "action": snap.get("action"),
                "score": snap.get("confluence_score"),
                "regime": snap.get("regime"),
                "outcome": snap.get("outcome"),  # null until Phase 8/12 fills it
                "timestamp": snap.get("timestamp"),
            })

        prompt = (
            f"VALIDATION TYPE: {validation_type}\n"
            f"INSTRUMENT: {instrument}\n\n"
            f"=== HEURISTIC ENGINE RESULTS ===\n"
            f"{json.dumps(heuristic_summary, indent=2, default=str)}\n\n"
            f"=== HISTORICAL KNOWLEDGE (per-instrument learned data) ===\n"
            f"{json.dumps(ks_summary, indent=2, default=str) if ks_summary else 'No historical data yet -- first trades for this instrument'}\n\n"
            f"=== WINNING TRADE EXAMPLES (backtesting knowledge base) ===\n"
            f"{json.dumps(trading_context.get('positive_patterns', {}), indent=2, default=str) if trading_context.get('positive_patterns') else 'Not yet available -- will populate after Phase 11 backtesting'}\n\n"
            f"=== INSTRUMENT PROFILE ===\n"
            f"{json.dumps(trading_context.get('instrument_profile', {}), indent=2, default=str) if trading_context.get('instrument_profile') else 'Profile data not loaded'}\n\n"
            f"=== RECENT TRADE SNAPSHOTS ===\n"
            f"{json.dumps(snap_summary, indent=2, default=str) if snap_summary else 'No recent snapshots'}\n\n"
            f"=== CURRENT MARKET DATA ===\n"
            f"{json.dumps(truncated_data, indent=2, default=str)}\n\n"
            f"=== DATA SOURCES AVAILABLE ===\n"
            f"{', '.join(trading_context.get('data_sources_available', [])) or 'Heuristics only (other sources will come online as bot collects data)'}\n\n"
            f"Based on ALL available evidence, provide your final assessment."
        )

        try:
            content = self._call_anthropic(
                system_prompt=system_prompt,
                user_prompt=prompt,
                max_tokens=2000,
            )

            # Parse response
            cleaned = content.strip()
            if cleaned.startswith("```"):
                first_newline = cleaned.index("\n")
                cleaned = cleaned[first_newline + 1:]
                if cleaned.rstrip().endswith("```"):
                    cleaned = cleaned.rstrip()[:-3].rstrip()

            result = json.loads(cleaned)
            result["llm_available"] = True
            result["data_sources_used"] = trading_context.get("data_sources_available", [])
            return result

        except (json.JSONDecodeError, Exception) as e:
            logger.error(f"LLM trading validation error: {e}")
            return {
                "passed": heuristic_summary.get("passed", heuristic_summary.get("overall_passed", False)),
                "confidence": heuristic_summary.get("confidence", 0.5),
                "recommendation": "hold",
                "reasoning": f"LLM error ({e}) -- defaulting to conservative hold",
                "llm_available": False,
                "data_sources_used": [],
            }

    def _accumulate_trade_result(self, heuristic_summary: dict, llm_result: dict):
        """Accumulate heuristic + LLM results for hourly batch analysis."""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "heuristic": heuristic_summary,
            "llm": llm_result,
            "llm_disagreed": heuristic_summary.get("passed") != llm_result.get("passed"),
        }
        self._trade_heuristic_history.append(entry)
        # Rolling window
        if len(self._trade_heuristic_history) > self._trade_history_max:
            self._trade_heuristic_history = self._trade_heuristic_history[-self._trade_history_max:]

    def _local_track_journey_step(self, journey_id, step_name=None, description=None, step_type=None, input_data=None, output_data=None, error=None):
        """Local fallback for journey step tracking."""
        self.logger.debug(f"Local tracking: {journey_id} - {step_name or step_type} - {description}")
        return True

    # ==================== BACKTEST DB VALIDATION (Phase 2) ====================

    @property
    def trading_db(self):
        """Lazy-load the TradingDB query layer."""
        if self._trading_db is None:
            try:
                import sys
                from pathlib import Path
                # Try multiple paths — handler may run from different working dirs
                candidates = [
                    Path(__file__).parent.parent / "Forex Trading Team",
                    Path.home() / "Jarvis" / "Forex Trading Team",
                ]
                for trading_bot in candidates:
                    if trading_bot.exists() and str(trading_bot) not in sys.path:
                        sys.path.insert(0, str(trading_bot))
                from Source.backtester.trading_db import TradingDB
                self._trading_db = TradingDB()
                self.logger.info("TradingDB connected successfully")
            except Exception as e:
                self.logger.error(f"Failed to load TradingDB: {e}")
                return None
        return self._trading_db

    async def _handle_validate_trade_setup(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Validate a trade setup against 8.5M backtest trades.
        
        Params:
            pair: str (e.g., "EUR_USD")
            regime: str (e.g., "ranging")
            setup: str (e.g., "S15" or "S15_rr2.0_sl2.5")
            direction: str (optional — "buy" or "sell")
            indicators: dict (optional — current indicator values)
            h4_agrees: bool (optional)
            session: str (optional — "Asian", "London", "NY_Overlap", "NY")
        
        Returns verdict with full evidence from backtest database.
        """
        db = self.trading_db
        if db is None:
            return {"error": "TradingDB not available"}

        result = db.validate_trade_setup(
            pair=params.get("pair"),
            regime=params.get("regime"),
            setup=params.get("setup"),
            direction=params.get("direction"),
            indicators=params.get("indicators"),
            h4_agrees=params.get("h4_agrees"),
            session=params.get("session"),
        )

        self.logger.info(
            "validate_trade_setup: %s %s %s → %s (%.1f%% conf, %s trades)",
            params.get("pair"), params.get("regime"), params.get("setup"),
            result.get("verdict", "?"), (result.get("confidence") or 0) * 100,
            (result.get("historical_stats") or {}).get("total_trades", 0)
        )
        return result

    async def _handle_get_loss_patterns(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Get loss pattern analysis for a setup.
        
        Params: pair, setup, regime, limit (optional)
        """
        db = self.trading_db
        if db is None:
            return {"error": "TradingDB not available"}
        return {
            "patterns": db.get_loss_patterns(
                pair=params.get("pair"),
                setup=params.get("setup"),
                regime=params.get("regime"),
                limit=params.get("limit", 10),
            )
        }

    async def _handle_check_confluence(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Check how concurrent setups affect win rate.
        
        Params: pair, setups_firing (list), regime (optional)
        """
        db = self.trading_db
        if db is None:
            return {"error": "TradingDB not available"}
        return db.check_confluence(
            pair=params.get("pair"),
            setups_firing=params.get("setups_firing", []),
            regime=params.get("regime"),
        )

    async def _handle_check_performance_drift(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Compare live vs backtest performance.
        
        Params: pair, setup, regime (optional)
        """
        db = self.trading_db
        if db is None:
            return {"error": "TradingDB not available"}
        return db.check_performance_drift(
            pair=params.get("pair"),
            setup=params.get("setup"),
            regime=params.get("regime"),
        )

    async def _handle_get_best_params(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Get best performing parameters for a pair+regime.
        
        Params: pair, regime, base_setup (optional), min_trades (optional)
        """
        db = self.trading_db
        if db is None:
            return {"error": "TradingDB not available"}
        return {
            "best_params": db.get_best_params(
                pair=params.get("pair"),
                regime=params.get("regime"),
                base_setup=params.get("base_setup"),
                min_trades=params.get("min_trades", 10),
            )
        }

    async def _handle_log_decision(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Log a trade decision to the audit trail.
        
        Params: pair, timeframe, setup, direction, regime, verdict, reasoning, ...
        """
        db = self.trading_db
        if db is None:
            return {"error": "TradingDB not available"}
        decision_id = db.log_decision(**params)
        return {"decision_id": decision_id, "status": "logged"}

    async def _handle_log_live_trade(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Log a live/paper trade.
        
        Params: trade_data (dict matching live_trades schema)
        """
        db = self.trading_db
        if db is None:
            return {"error": "TradingDB not available"}
        trade_id = db.log_live_trade(params.get("trade_data", params))
        return {"trade_id": trade_id, "status": "logged"}

    async def _handle_get_upcoming_news(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Check for upcoming high-impact news events.

        Params: currencies (list, optional), hours_ahead (int, optional)
        """
        db = self.trading_db
        if db is None:
            return {"events": [], "weather_warnings": [], "note": "TradingDB not available"}
        try:
            events = db.get_upcoming_high_impact_news(
                currencies=params.get("currencies"),
                hours_ahead=params.get("hours_ahead", 24),
            )
        except Exception:
            events = []
        try:
            weather = db.get_active_weather_warnings(
                currencies=params.get("currencies"),
            )
        except Exception:
            weather = []
        return {"events": events or [], "weather_warnings": weather or []}

    def _get_oanda_client(self):
        """Lazy-load OandaClient for live market data."""
        if not hasattr(self, '_oanda_client') or self._oanda_client is None:
            try:
                import sys
                from pathlib import Path
                candidates = [
                    Path(__file__).parent.parent / "Forex Trading Team",
                    Path.home() / "Jarvis" / "Forex Trading Team",
                ]
                for p in candidates:
                    if p.exists() and str(p) not in sys.path:
                        sys.path.insert(0, str(p))
                from Source.oanda_client import OandaClient
                self._oanda_client = OandaClient()
                self.logger.info("OandaClient connected")
            except Exception as e:
                self.logger.warning(f"OandaClient failed: {e}")
                self._oanda_client = None
        return self._oanda_client

    async def _handle_get_live_price(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Get current live bid/ask price from OANDA."""
        pair = params.get("pair", "")
        client = self._get_oanda_client()
        if not client:
            return {"error": "OANDA client not available", "pair": pair}
        try:
            pricing = client.get_pricing([pair])
            prices = pricing.get("prices", [])
            if prices:
                p = prices[0]
                bids = p.get("bids", [{}])
                asks = p.get("asks", [{}])
                return {
                    "pair": pair,
                    "bid": float(bids[0].get("price", 0)) if bids else 0,
                    "ask": float(asks[0].get("price", 0)) if asks else 0,
                    "spread": round(float(asks[0].get("price", 0)) - float(bids[0].get("price", 0)), 5) if bids and asks else 0,
                    "tradeable": p.get("tradeable", False),
                    "time": p.get("time", ""),
                }
            return {"pair": pair, "error": "No pricing data returned"}
        except Exception as e:
            return {"pair": pair, "error": str(e)}

    async def _handle_get_recent_candles(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Get recent candle data from OANDA with computed indicators."""
        pair = params.get("pair", "")
        count = min(params.get("count", 10), 50)
        granularity = params.get("granularity", "M15")
        client = self._get_oanda_client()
        if not client:
            return {"error": "OANDA client not available", "pair": pair}
        try:
            candles = client.get_candles(pair, granularity=granularity, count=count)
            # Summarize — don't send all raw data, just key info
            summary = []
            for c in candles[-count:]:
                mid = c.get("mid", {})
                summary.append({
                    "time": c.get("time", "")[:19],
                    "o": float(mid.get("o", 0)),
                    "h": float(mid.get("h", 0)),
                    "l": float(mid.get("l", 0)),
                    "c": float(mid.get("c", 0)),
                    "vol": c.get("volume", 0),
                    "complete": c.get("complete", True),
                })
            # Add current price context
            last = summary[-1] if summary else {}
            return {
                "pair": pair,
                "granularity": granularity,
                "candle_count": len(summary),
                "latest_close": last.get("c"),
                "latest_time": last.get("time"),
                "candles": summary,
            }
        except Exception as e:
            return {"pair": pair, "error": str(e)}

    async def _handle_get_account_summary(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Get OANDA account summary — balance, P&L, open trades."""
        client = self._get_oanda_client()
        if not client:
            return {"error": "OANDA client not available"}
        try:
            summary = client.get_account_summary()
            acct = summary.get("account", {})
            return {
                "balance": acct.get("balance"),
                "unrealized_pl": acct.get("unrealizedPL"),
                "realized_pl": acct.get("pl"),
                "open_trade_count": acct.get("openTradeCount"),
                "open_position_count": acct.get("openPositionCount"),
                "margin_used": acct.get("marginUsed"),
                "margin_available": acct.get("marginAvailable"),
                "currency": acct.get("currency"),
            }
        except Exception as e:
            return {"error": str(e)}

    async def _handle_wolfram_calculate(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Run a computational query via Wolfram Alpha.

        Used by the validator for statistical analysis, regression, probability,
        technical indicator calculations, live rates, and financial math.
        """
        query = params.get("query", "")
        if not query:
            return {"error": "No query provided"}
        try:
            from Handler.handler_wolfram import WolframHandler
            wolfram = WolframHandler()
            result = wolfram.query_wolfram_alpha(query, format_type="plaintext")
            # Trim large results to avoid flooding the LLM context
            if isinstance(result, dict):
                text = result.get("result", result.get("plaintext", str(result)))
                if isinstance(text, str) and len(text) > 2000:
                    text = text[:2000] + "... (truncated)"
                return {"query": query, "result": text}
            return {"query": query, "result": str(result)[:2000]}
        except Exception as e:
            return {"query": query, "error": str(e)}

    async def _handle_get_trade_history(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Get recent trade outcomes for a pair from trade_decisions + live_trades.

        Returns wins, losses, pips, streaks so the validator knows pair performance.
        """
        pair = params.get("pair", "")
        limit = params.get("limit", 10)

        db = self.trading_db
        if db is None:
            return {"pair": pair, "trades": [], "note": "TradingDB not available"}

        try:
            # Query live_trades for actual trade outcomes
            rows = db.conn.execute("""
                SELECT pair, direction, setup, entry_time, exit_time,
                       pips, result, confidence, entry_price, exit_price
                FROM live_trades
                WHERE pair = ?
                ORDER BY entry_time DESC
                LIMIT ?
            """, (pair, limit)).fetchall()

            trades = []
            for r in rows:
                trades.append({
                    "direction": r[1],
                    "setup": r[2],
                    "entry_time": r[3],
                    "exit_time": r[4],
                    "pips": r[5],
                    "outcome": r[6],
                    "confidence": r[7],
                    "entry_price": r[8],
                    "exit_price": r[9],
                })

            closed = [t for t in trades if t.get("outcome") and t["outcome"] != "open"]
            wins = sum(1 for t in closed if t["outcome"] == "win")
            losses = sum(1 for t in closed if t["outcome"] == "loss")
            total_pips = sum(t.get("pips") or 0 for t in closed)

            return {
                "pair": pair,
                "total_decisions": len(trades),
                "closed_trades": len(closed),
                "wins": wins,
                "losses": losses,
                "win_rate": round(wins / len(closed), 3) if closed else 0,
                "total_pips": round(total_pips, 1),
                "recent_trades": trades[:5],
            }
        except Exception as e:
            return {"pair": pair, "error": str(e), "trades": []}

    # ==================== FULL DECISION PIPELINE (Phase 3) ====================

    async def _handle_evaluate_trade(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Run the full 4-step decision pipeline and log to trade_decisions.

        This is the PRIMARY entry point for live trading decisions.
        Runs: Gate 1 → Gate 2 → DB evidence → final verdict, logs everything.

        Params:
            pair, timeframe, setup, direction, regime (required)
            indicators, h4_agrees, session, candles (optional)
            market_data, news_data, weather_data, wolfram_data (optional)
            confluence_output (optional)
        """
        try:
            _ensure_trading_bot_path()
            from Source.decision_logger import DecisionLogger
            dl = DecisionLogger()
            result = dl.evaluate_and_log(**params)
            self.logger.info(
                "evaluate_trade: %s %s %s → %s (%.0f%% conf, %dms)",
                params.get("pair"), params.get("regime"), params.get("setup"),
                result["verdict"], result["confidence"] * 100,
                result["execution_time_ms"],
            )
            return result
        except Exception as e:
            self.logger.error("evaluate_trade failed: %s", e)
            return {"error": str(e)}

    async def _handle_check_positions(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Check open positions against all 12 exit rules.

        Params:
            positions: list of dicts with OpenPosition fields
            market_state: dict with prices, regimes, sessions, upcoming_news, candle_data
        """
        try:
            _ensure_trading_bot_path()
            from Source.position_manager import PositionManager, OpenPosition

            pm = PositionManager()

            # Convert dicts to OpenPosition objects
            positions = []
            for p in params.get("positions", []):
                positions.append(OpenPosition(**{
                    k: v for k, v in p.items()
                    if k in OpenPosition.__dataclass_fields__
                }))

            market_state = params.get("market_state", {})
            actions = pm.check_positions(positions, market_state)
            actions = pm.deduplicate_actions(actions)

            return {
                "actions": [
                    {
                        "trade_id": a.trade_id,
                        "action": a.action,
                        "reason": a.reason,
                        "rule": a.rule,
                        "urgency": a.urgency,
                        "new_sl": a.new_sl,
                        "close_fraction": a.close_fraction,
                        "details": a.details,
                    }
                    for a in actions
                ],
                "position_count": len(positions),
                "actions_count": len(actions),
            }
        except Exception as e:
            self.logger.error("check_positions failed: %s", e)
            return {"error": str(e)}

    # ==================== SYNC MCP WRAPPERS ====================
    # These sync methods are discovered by MCP introspection in handler_swarm.py.
    # They wrap the async _handle_* methods so the agent LLM can call them as tools.
    # Each method creates a FRESH TradingDB to avoid SQLite threading errors.

    def _fresh_trading_db(self):
        """Create a new TradingDB instance for the current thread (avoids SQLite threading errors)."""
        try:
            _ensure_trading_bot_path()
            from Source.backtester.trading_db import TradingDB
            return TradingDB()
        except Exception as e:
            self.logger.error(f"Failed to create TradingDB: {e}")
            return None

    def validate_full(self, pair: str, regime: str, setup: str,
                       direction: str = None, indicators: dict = None,
                       h4_agrees: bool = None, session: str = None,
                       min_trades: int = 10, loss_limit: int = 10, **kwargs) -> dict:
        """ONE-CALL comprehensive validation — runs all DB queries in parallel.
        
        Returns combined results from:
        - validate_trade_setup (verdict + historical stats)
        - get_loss_patterns (what causes losses)
        - get_best_params (optimal parameters for this pair+regime)
        
        This replaces 3 sequential tool calls with 1, saving ~20-30 seconds per cycle.
        
        Args:
            pair: Currency pair (e.g. 'EUR_USD')
            regime: Market regime (exhaustion|high_volatility|mixed|ranging|squeeze|strong_trend)
            setup: Setup ID (e.g. 'S15_rr2.0_sl1.0' or just 'S15' for broader search)
            direction: 'buy' or 'sell'
            indicators: Current indicator values
            h4_agrees: Whether H4 confirms direction
            session: Current session (Asian|London|NY_Overlap|NY)
            min_trades: Min trades for best_params significance
            loss_limit: Max loss patterns to return
        """
        db = self._fresh_trading_db()
        if db is None:
            return {"error": "TradingDB not available"}
        
        # Auto-fix: LLM sometimes passes natural language setup names instead of S-codes.
        # If setup doesn't start with "S" or "SNP", try to find a valid S-code.
        import re as _re
        if setup and not _re.match(r'^(S\d|SNP)', setup):
            self.logger.warning("validate_full got non-S-code setup '%s' — attempting auto-fix", setup)
            # Try to find S-code embedded in the string (e.g. "Counter Trend Reversal · S12 BB Squeeze")
            _s_match = _re.search(r'\b(S\d+)\b', setup)
            if _s_match:
                setup = _s_match.group(1)
                self.logger.info("Extracted S-code from string: %s", setup)
            else:
                # Last resort: query DB for all setups for this pair+regime and pick the best
                try:
                    _best = db.get_best_params(pair=pair, regime=regime, min_trades=10)
                    if _best and isinstance(_best, list) and len(_best) > 0:
                        setup = _best[0].get("setup", setup).split("_rr")[0]
                        self.logger.info("Auto-selected best setup from DB: %s", setup)
                except Exception:
                    pass
        
        # Extract base setup for broader search (S15_rr2.0_sl1.0 → S15)
        base_setup = setup.split("_rr")[0] if "_rr" in setup else setup
        
        # Run sequentially — each query is ~2ms, threading causes SQLite
        # "objects created in a thread" errors since they share one connection.
        results = {}
        try:
            results["validation"] = db.validate_trade_setup(
                pair=pair, regime=regime, setup=setup,
                direction=direction, indicators=indicators,
                h4_agrees=h4_agrees, session=session,
            )
        except Exception as e:
            results["validation"] = {"error": str(e)}
        try:
            results["loss_patterns"] = db.get_loss_patterns(
                pair=pair, setup=base_setup, regime=regime, limit=loss_limit,
            )
        except Exception as e:
            results["loss_patterns"] = {"error": str(e)}
        try:
            results["best_params"] = db.get_best_params(
                pair=pair, regime=regime, base_setup=base_setup, min_trades=min_trades,
            )
        except Exception as e:
            results["best_params"] = {"error": str(e)}
        
        # Also try broader search if exact setup got no data
        validation = results.get("validation", {})
        if isinstance(validation, dict) and validation.get("verdict") == "REJECT" and setup != base_setup:
            try:
                broader = db.validate_trade_setup(
                    pair=pair, regime=regime, setup=base_setup,
                    direction=direction,
                )
                results["broader_validation"] = broader
            except Exception:
                pass
        
        # Cross-regime lookup: show the BEST regime for this setup+pair
        # so the validator knows "S12 is elite in strong_trend (93% WR) but weak in ranging (45% WR)"
        try:
            best_regime_stats = {}
            for _regime in ["strong_trend", "moderate_trend", "mixed", "ranging", "squeeze", "high_volatility"]:
                if _regime == regime:
                    continue  # already queried
                try:
                    _xr = db.validate_trade_setup(pair=pair, regime=_regime, setup=base_setup, direction=direction)
                    if isinstance(_xr, dict):
                        _xhs = _xr.get("historical_stats")
                        if isinstance(_xhs, dict) and _xhs.get("best_win_rate", 0) > 75 and _xhs.get("best_trade_count", 0) >= 30:
                            best_regime_stats[_regime] = {
                                "win_rate": _xhs["best_win_rate"],
                                "trade_count": _xhs["best_trade_count"],
                                "profit_factor": _xhs.get("best_profit_factor", 0),
                                "total_pips": _xhs.get("best_total_pips", 0),
                            }
                except Exception:
                    pass
            if best_regime_stats:
                results["cross_regime"] = best_regime_stats
                self.logger.info("Cross-regime data for %s %s: %s", base_setup, pair,
                    ", ".join(f"{r}: {s['win_rate']}% WR ({s['trade_count']} trades)" for r, s in best_regime_stats.items()))
        except Exception as _xr_exc:
            self.logger.debug("Cross-regime lookup failed: %s", _xr_exc)
        
        return results

    def validate_trade_setup(self, pair: str, regime: str, setup: str,
                              direction: str = None, indicators: dict = None,
                              h4_agrees: bool = None, session: str = None, **kwargs) -> dict:
        """Validate a trade setup against backtest database (39K+ patterns).
        
        Args:
            pair: Currency pair (e.g. 'EUR_USD')
            regime: Market regime (e.g. 'ranging', 'strong_trend', 'moderate_trend')
            setup: Setup ID (e.g. 'S15' or 'S15_rr2.0_sl2.5')
            direction: Optional - 'buy' or 'sell'
            h4_agrees: Optional - whether H4 timeframe confirms direction
            session: Optional - 'Asian', 'London', 'NY_Overlap', 'NY'
        
        Returns:
            dict with verdict, confidence, historical_stats, evidence
        """
        db = self._fresh_trading_db()
        if db is None:
            return {"error": "TradingDB not available"}
        return db.validate_trade_setup(
            pair=pair, regime=regime, setup=setup,
            direction=direction, indicators=indicators,
            h4_agrees=h4_agrees, session=session,
        )

    def get_loss_patterns(self, pair: str, setup: str, regime: str = None,
                          limit: int = 10, **kwargs) -> dict:
        """Get loss pattern analysis for a setup — what conditions cause losses.
        
        Args:
            pair: Currency pair
            setup: Setup ID
            regime: Optional market regime filter
            limit: Max patterns to return
        """
        db = self._fresh_trading_db()
        if db is None:
            return {"error": "TradingDB not available"}
        return {"patterns": db.get_loss_patterns(pair=pair, setup=setup, regime=regime, limit=limit)}

    def check_confluence_performance(self, pair: str, setups_firing: list,
                                      regime: str = None, **kwargs) -> dict:
        """Check how concurrent setups affect win rate.
        
        Args:
            pair: Currency pair
            setups_firing: List of setup IDs currently triggering
            regime: Optional regime filter
        """
        db = self._fresh_trading_db()
        if db is None:
            return {"error": "TradingDB not available"}
        return db.check_confluence(pair=pair, setups_firing=setups_firing, regime=regime)

    def get_best_params(self, pair: str, regime: str, base_setup: str = None,
                        min_trades: int = 10, **kwargs) -> dict:
        """Get best performing parameters for a pair+regime from backtests.
        
        Args:
            pair: Currency pair
            regime: Market regime
            base_setup: Optional base setup to filter (e.g. 'S15')
            min_trades: Minimum trade count for statistical significance
        """
        db = self._fresh_trading_db()
        if db is None:
            return {"error": "TradingDB not available"}
        return {"best_params": db.get_best_params(pair=pair, regime=regime, base_setup=base_setup, min_trades=min_trades)}

    def check_performance_drift(self, pair: str, setup: str,
                                 regime: str = None, **kwargs) -> dict:
        """Compare live trading vs backtest performance — detect strategy decay.
        
        Args:
            pair: Currency pair
            setup: Setup ID
            regime: Optional regime filter
        """
        db = self._fresh_trading_db()
        if db is None:
            return {"error": "TradingDB not available"}
        return db.check_performance_drift(pair=pair, setup=setup, regime=regime)

    def evaluate_trade(self, pair: str, timeframe: str, setup: str,
                       direction: str, regime: str, **kwargs) -> dict:
        """Run the full 4-step decision pipeline: Gate 1 → Gate 2 → DB evidence → verdict.
        
        This is the PRIMARY validation entry point. Logs decision to audit trail.
        
        Args:
            pair: Currency pair (e.g. 'EUR_USD')
            timeframe: Candle timeframe (e.g. 'H1')
            setup: Setup ID (e.g. 'S15_rr2.0_sl2.5')
            direction: 'buy' or 'sell'
            regime: Market regime
            **kwargs: indicators, h4_agrees, session, candles, market_data, news_data, etc.
        """
        try:
            _ensure_trading_bot_path()
            from Source.decision_logger import DecisionLogger
            dl = DecisionLogger()
            result = dl.evaluate_and_log(
                pair=pair, timeframe=timeframe, setup=setup,
                direction=direction, regime=regime, **kwargs
            )
            return result
        except Exception as e:
            self.logger.error("evaluate_trade sync failed: %s", e)
            return {"error": str(e)}

    def get_upcoming_news(self, currencies: list = None,
                          hours_ahead: int = 24, **kwargs) -> dict:
        """Check for upcoming high-impact news events that could affect trades.
        
        Args:
            currencies: List of currency codes to check (e.g. ['EUR', 'USD'])
            hours_ahead: How far ahead to look (default 24h)
        """
        db = self._fresh_trading_db()
        if db is None:
            return {"error": "TradingDB not available"}
        return {
            "events": db.get_upcoming_high_impact_news(currencies=currencies, hours_ahead=hours_ahead),
            "weather_warnings": db.get_active_weather_warnings(currencies=currencies),
        }

    # ==================== UNIFIED VALIDATION WITH VISION + VAULT ====================

    async def _handle_evaluate_with_full_context(self, parameters: Dict) -> Dict:
        """Action handler wrapper for evaluate_with_full_context."""
        return await self.evaluate_with_full_context(parameters)

    async def evaluate_with_full_context(self, params: Dict) -> Dict:
        """Unified validation combining vision + intelligence + vault knowledge.

        This is the ONE validator method. It replaces both vision_validator.evaluate()
        and validation_analyst.analyze() by combining chart vision, intelligence data,
        TA narrative, DB evidence, and vault knowledge in a two-pass LLM approach.

        Args:
            params: Dict containing:
                Required:
                    pair (str): Instrument (e.g., "EUR_USD")
                    chart_path (str): Path to M15 chart PNG
                    indicators (dict): Current indicator values
                Optional:
                    ta_narrative (str): TA agent's market description
                    intelligence_data (dict): Macro/COT/calendar from cache
                    trader_annotations (list): Tim's chart marks
                    user_chart_path (str): User-submitted annotated chart
                    confluence_output (dict): Confluence scorer results
                    contradictions (dict): Cross-field contradictions
                    backtest_evidence (dict): Historical setup performance
                    alert_data (dict): Scout alert context
                    alert_id (int): DB linking ID
                    workspace_id (str): Override workspace (default: self.workspace_id)

        Returns:
            Dict with verdict, direction, confidence, reasoning, chart_read,
            setup_identified, checklist, intelligence_alignment, snipe, etc.
        """
        import base64
        import time

        start_time = time.time()
        pair = params.get("pair", "UNKNOWN")
        chart_path = params.get("chart_path", "")
        indicators = params.get("indicators", {})

        self.logger.info(f"[UNIFIED_VALIDATOR] Evaluating {pair} with full context")

        # --- 1. Load vault knowledge based on workspace ---
        workspace_id = params.get("workspace_id") or self.workspace_id
        vault_knowledge = self._load_vault_knowledge(workspace_id)

        # --- 2. Build system prompt from vault ---
        system_prompt = vault_knowledge.get("system_prompt", "")
        learnings = vault_knowledge.get("learnings", "")
        if learnings:
            system_prompt += f"\n\n## RECENT LEARNINGS (from vault)\n{learnings}"

        # --- 3. Build content blocks (text + images) for Pass 1 ---
        content_blocks = []

        # Add teaching images first (validator needs reference examples)
        teaching_images = vault_knowledge.get("teaching_images", [])
        for img in teaching_images:
            img_data, img_media = self._load_image_as_base64(img.get("file_path", ""))
            if img_data:
                content_blocks.append({
                    "type": "text",
                    "text": f"**Teaching example**: {img.get('description', '')}",
                })
                content_blocks.append({
                    "type": "image",
                    "source": {"type": "base64", "media_type": img_media, "data": img_data},
                })

        # Add the live chart (ALWAYS LAST among chart images)
        live_chart_data, live_chart_media = self._load_image_as_base64(chart_path)
        if live_chart_data:
            content_blocks.append({
                "type": "text",
                "text": f"**LIVE CHART — {pair} M15** (This is the CURRENT chart to evaluate):",
            })
            content_blocks.append({
                "type": "image",
                "source": {"type": "base64", "media_type": live_chart_media, "data": live_chart_data},
            })

        # Add user-submitted annotated chart if present
        user_chart_path = params.get("user_chart_path")
        if user_chart_path:
            user_chart_data, user_chart_media = self._load_image_as_base64(user_chart_path)
            if user_chart_data:
                content_blocks.append({
                    "type": "text",
                    "text": "**USER ANNOTATED CHART** — Trader submitted this annotated chart. Read their markups.",
                })
                content_blocks.append({
                    "type": "image",
                    "source": {"type": "base64", "media_type": user_chart_media, "data": user_chart_data},
                })

        # Add text data (TA report, intelligence, indicators, DB context)
        text_data = self._build_evaluation_text(params, vault_knowledge)
        content_blocks.append({"type": "text", "text": text_data})

        # --- 4. PASS 1: LLM reads chart + all data, identifies setup ---
        self.logger.info(f"[UNIFIED_VALIDATOR] Pass 1: {len(content_blocks)} content blocks, {len(teaching_images)} teaching images")

        try:
            pass1_response, tool_calls = self._call_llm_with_tools(
                system_prompt=system_prompt,
                content_blocks=content_blocks,
                max_tokens=2500,
            )
            if tool_calls:
                self.logger.info(f"[UNIFIED_VALIDATOR] Pass 1 used {len(tool_calls)} tool calls: {[tc['tool'] for tc in tool_calls]}")

            # Ghost mode: run local model on same inputs in background
            if GHOST_MODE_ENABLED:
                import threading
                _ghost_blocks = list(content_blocks)
                _ghost_sys = system_prompt
                _ghost_anthropic = pass1_response
                def _ghost_pass1():
                    try:
                        local_resp = self._call_local_model(_ghost_sys, _ghost_blocks, 2500)
                        self._log_ghost_comparison(_ghost_anthropic, local_resp, _ghost_blocks)
                    except Exception as ge:
                        self.logger.warning("[GHOST] Pass 1 local model failed: %s", ge)
                threading.Thread(target=_ghost_pass1, daemon=True).start()

        except Exception as e:
            self.logger.error(f"[UNIFIED_VALIDATOR] Pass 1 failed: {e}")
            return {
                "verdict": "SKIP",
                "direction": None,
                "confidence": 0.0,
                "reasoning": f"Validation failed: {str(e)}",
                "error": str(e),
                "elapsed_seconds": time.time() - start_time,
            }

        # --- 5. Parse Pass 1 response ---
        result = self._parse_validator_response(pass1_response)

        # --- 6. PASS 2 (optional): If validator identified a setup, search vault for matching education ---
        setup_identified = result.get("setup_identified", "")
        chart_read = result.get("chart_read", "")
        self.logger.info(
            f"[UNIFIED_VALIDATOR] Pass 2 check: setup_identified='{(setup_identified or '')[:50]}' "
            f"chart_read='{(chart_read or '')[:50]}' → trigger={'YES' if (setup_identified and setup_identified.strip()) or (chart_read and chart_read.strip()) else 'NO'}"
        )
        if (setup_identified and setup_identified.strip()) or (chart_read and chart_read.strip()):
            vault_education = self._search_vault_for_context(
                setup_identified, chart_read, params, vault_knowledge
            )
            if vault_education:
                # Ask the validator to refine with vault context
                self.logger.info(f"[UNIFIED_VALIDATOR] Pass 2: vault education found ({len(vault_education)} chars)")
                pass2_blocks = [
                    {"type": "text", "text": (
                        f"## VAULT EDUCATION CONTEXT\n"
                        f"Based on what you identified ({setup_identified}), here is relevant knowledge:\n\n"
                        f"{vault_education}\n\n"
                        f"## YOUR PASS 1 ASSESSMENT\n{pass1_response}\n\n"
                        f"Refine your assessment with this education context. "
                        f"Does this change your verdict or confidence? "
                        f"Return the same JSON format with any adjustments."
                    )},
                ]
                try:
                    pass2_response = self._call_llm(
                        system_prompt=system_prompt,
                        content_blocks=pass2_blocks,
                        max_tokens=2000,
                    )
                    result = self._parse_validator_response(pass2_response)
                    result["two_pass"] = True
                    result["vault_education_used"] = True
                except Exception as e:
                    self.logger.warning(f"[UNIFIED_VALIDATOR] Pass 2 failed, using Pass 1: {e}")
                    result["two_pass"] = False

        # --- 7. Add metadata ---
        result["pair"] = pair
        result["chart_path"] = chart_path
        result["model_used"] = VISION_MODEL
        result["elapsed_seconds"] = time.time() - start_time
        result["teaching_images_count"] = len(teaching_images)
        result["workspace_id"] = workspace_id
        result["tool_calls"] = tool_calls if tool_calls else []
        result["tool_calls_count"] = len(tool_calls) if tool_calls else 0
        result.setdefault("two_pass", False)
        result.setdefault("vault_education_used", False)

        self.logger.info(
            f"[UNIFIED_VALIDATOR] {pair} → {result.get('verdict', 'UNKNOWN')} "
            f"conf={result.get('confidence', 0)} "
            f"({result['elapsed_seconds']:.1f}s, 2-pass={result['two_pass']})"
        )

        return result

    def _load_vault_knowledge(self, workspace_id: str = None) -> Dict:
        """Load all vault knowledge for this workspace."""
        try:
            import sys
            jarvis_root = os.path.dirname(os.path.dirname(__file__))
            if jarvis_root not in sys.path:
                sys.path.insert(0, jarvis_root)
            from knowledge.vault_knowledge_loader import VaultKnowledgeLoader

            loader = VaultKnowledgeLoader(workspace_id or "forex-trading-team")

            knowledge = {
                "system_prompt": loader.load_system_prompt() or "",
                "learnings": loader.load_learnings() or "",
                "domain": loader.load_domain_knowledge(),
                "loader": loader,  # Keep reference for education search
            }

            # Get teaching images matching common setups
            teaching_images = loader.get_teaching_images(
                {"setup_type": "fan_expansion"}, limit=8
            )
            knowledge["teaching_images"] = teaching_images

            return knowledge
        except Exception as e:
            self.logger.warning(f"[UNIFIED_VALIDATOR] Vault load failed: {e}")
            return {"system_prompt": "", "learnings": "", "domain": {}, "teaching_images": []}

    def _build_evaluation_text(self, params: Dict, vault_knowledge: Dict) -> str:
        """Build the text portion of the evaluation prompt.

        This method is GENERIC — it formats whatever data sections the caller
        provides. It does not know about forex, trading, or any domain-specific
        concepts. All domain logic lives in the vault prompt and the caller.

        The caller can pass data in two ways:
        1. Pre-formatted sections: params["data_sections"] = [{"heading": "...", "content": "..."}]
        2. Individual fields: params["indicators"], params["intelligence_data"], etc.
           These get auto-formatted into sections with ## headings.
        """
        sections = []

        # Option 1: Caller provided pre-formatted sections (preferred)
        if "data_sections" in params:
            for section in params["data_sections"]:
                heading = section.get("heading", "DATA")
                content = section.get("content", "")
                if isinstance(content, dict):
                    content = json.dumps(content, indent=2, default=str)
                elif isinstance(content, list):
                    content = json.dumps(content, indent=2, default=str)
                sections.append(f"## {heading}\n{content}")
            return "\n\n".join(sections)

        # Option 2: Auto-format individual fields (backwards compatible)
        # Process all params that look like data, format each as a section
        skip_keys = {"pair", "chart_path", "user_chart_path", "workspace_id",
                      "alert_id", "data_sections", "images", "teaching_images"}

        for key, value in params.items():
            if key in skip_keys or value is None:
                continue
            if isinstance(value, str) and not value.strip():
                continue

            # Format the section heading from the key name
            heading = key.upper().replace("_", " ")

            if isinstance(value, (dict, list)):
                content = json.dumps(value, indent=2, default=str)
            else:
                content = str(value)

            sections.append(f"## {heading}\n{content}")

        # Add vault education if available (small, targeted excerpt)
        loader = vault_knowledge.get("loader")
        if loader and params.get("indicators"):
            edu_context = loader.load_relevant_education(
                params.get("indicators", {}), max_tokens=300
            )
            if edu_context:
                sections.append(f"## RELEVANT KNOWLEDGE (from vault)\n{edu_context}")

        return "\n\n".join(sections)

    def _search_vault_for_context(
        self, setup_identified: str, chart_read: str,
        params: Dict, vault_knowledge: Dict
    ) -> str:
        """Search vault for education matching what the LLM identified in Pass 1.

        Generic — uses the setup_identified and chart_read text to build
        a search query. No domain-specific keywords hardcoded.
        """
        loader = vault_knowledge.get("loader")
        if not loader:
            return ""

        # Build search context from what the LLM found
        context = {"setup_type": setup_identified}

        # Pass chart_read as free text query for FTS
        if chart_read:
            context["text_query"] = chart_read
        if setup_identified:
            context["text_query"] = (context.get("text_query", "") + " " + setup_identified).strip()

        # Pass through any indicator-like fields from params
        indicators = params.get("indicators", {})
        if isinstance(indicators, dict):
            for key in ["fan_state", "pattern_name", "regime", "phase"]:
                if key in indicators:
                    context[key] = str(indicators[key])

        education = loader.load_relevant_education(context, max_tokens=400)
        return education

    def _load_image_as_base64(self, image_path: str) -> tuple:
        """Load an image file and return (base64_data, media_type).

        Auto-detects JPEG vs PNG from file magic bytes.
        Returns ("", "image/png") if file not found or error.
        """
        if not image_path or not os.path.exists(image_path):
            return "", "image/png"
        try:
            import base64
            with open(image_path, "rb") as f:
                raw = f.read()
            # Detect media type from magic bytes
            if raw[:3] == b'\xff\xd8\xff':
                media_type = "image/jpeg"
            elif raw[:8] == b'\x89PNG\r\n\x1a\n':
                media_type = "image/png"
            elif raw[:4] == b'RIFF' and raw[8:12] == b'WEBP':
                media_type = "image/webp"
            else:
                media_type = "image/png"
            return base64.b64encode(raw).decode("utf-8"), media_type
        except Exception as e:
            self.logger.warning(f"Failed to load image {image_path}: {e}")
            return "", "image/png"

    def _parse_validator_response(self, response_text: str) -> Dict:
        """Parse the validator's JSON response, handling markdown fences."""
        cleaned = response_text.strip()

        # Strip markdown code fences
        if cleaned.startswith("```"):
            first_nl = cleaned.index("\n")
            cleaned = cleaned[first_nl + 1:]
            if cleaned.rstrip().endswith("```"):
                cleaned = cleaned.rstrip()[:-3].rstrip()

        try:
            result = json.loads(cleaned)
        except json.JSONDecodeError:
            # Try to extract JSON from mixed text
            import re
            json_match = re.search(r'\{[\s\S]*\}', cleaned)
            if json_match:
                try:
                    result = json.loads(json_match.group())
                except json.JSONDecodeError:
                    result = {
                        "verdict": "SKIP",
                        "direction": None,
                        "confidence": 0.0,
                        "reasoning": cleaned,
                        "parse_error": True,
                    }
            else:
                result = {
                    "verdict": "SKIP",
                    "direction": None,
                    "confidence": 0.0,
                    "reasoning": cleaned,
                    "parse_error": True,
                }

        # Ensure required fields exist
        result.setdefault("verdict", "SKIP")
        result.setdefault("direction", None)
        result.setdefault("confidence", 0.0)
        result.setdefault("reasoning", "")
        result.setdefault("chart_read", "")
        result.setdefault("setup_identified", "")

        return result
