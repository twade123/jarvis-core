"""
Risk Manager Handler for Jarvis

Wraps the Trading Bot's RiskManager as a Jarvis MCP handler so agents can
access risk decisions (position sizing, stop management, profile switching,
circuit breaker status) through the standard MCP handler ecosystem.

Delegates all risk calculations to Forex Trading Team/Source/risk_manager.py.
"""

import time
import json
import logging
import inspect
from typing import Any, Dict, Optional
import sys
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("RiskManager")

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
    track_journey_step_sync,
)
from Database.v2.db_helper import connection as v2_connection


# ======================================================================
# Orchestrator Agent
# ======================================================================


class RiskManagerOrchestratorAgent:
    """Agent for orchestrating communication between RiskManager and Jarvis system."""

    def __init__(self, system_name="RiskManagerSystem"):
        if hasattr(system_name, "name"):
            self.risk_manager_handler = system_name
            self.system_name = "RiskManagerOrchestratorAgent"
        else:
            self.system_name = system_name
            self.risk_manager_handler = None

        self.conversation_history = []
        self.active = True
        self.current_journey_id = None

        # BoardRoom was archived (Phase 3). Tracking uses V2 databases directly.
        self.boardroom = None
        logger.info(f"RiskManagerOrchestratorAgent initialised for {self.system_name}")

    def _track_jarvis_communication(
        self, direction, message, journey_id=None, _prevent_recursion=False
    ):
        """Track communication with the Jarvis orchestrator."""
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
            logger.error(f"Error preparing message data: {e}")
            safe_message = str(message)[:100]
            step_data["output_data"] = safe_message

        if self.boardroom and not _prevent_recursion:
            try:
                if journey_id and hasattr(self.boardroom, "track_journey_step"):
                    sig = inspect.signature(self.boardroom.track_journey_step)
                    if "_prevent_recursion" in sig.parameters:
                        self.boardroom.track_journey_step(
                            journey_id=journey_id,
                            step_name=f"jarvis_communication_{direction}",
                            **step_data,
                            _prevent_recursion=True,
                        )
                    else:
                        self.boardroom.track_journey_step(
                            journey_id=journey_id,
                            step_name=f"jarvis_communication_{direction}",
                            **step_data,
                        )
            except Exception as e:
                logger.error(f"Error tracking Jarvis communication: {e}")

        self.conversation_history.append(
            {
                "timestamp": time.time(),
                "direction": direction,
                "message": safe_message,
                "journey_id": journey_id,
            }
        )

        return True

    def send_message_to_jarvis(
        self,
        message,
        context=None,
        handler_params=None,
        message_type="update",
        request_id=None,
        journey_id=None,
    ):
        """Send a message to the Jarvis orchestrator."""
        if not request_id:
            request_id = generate_simple_id("risk_manager_req_")

        if not journey_id:
            journey_id = f"risk_manager_{request_id}_{int(time.time())}"
            self.current_journey_id = journey_id

        message_payload = {
            "message": message,
            "context": context or {},
            "request_id": request_id,
            "journey_id": journey_id,
            "handler_params": handler_params or {},
            "timestamp": time.time(),
            "system": self.system_name,
            "message_type": message_type,
        }

        self._track_jarvis_communication("outgoing", message_payload, journey_id)

        try:
            logger.info(f"Message sent to Jarvis: {message[:100]}...")
            return True, journey_id
        except Exception as e:
            logger.error(f"Error sending message to Jarvis: {e}")
            return False, journey_id

    async def receive_message_from_jarvis(
        self, message, context=None, message_type="instruction", journey_id=None
    ):
        """Receive a message from the Jarvis orchestrator."""
        if not journey_id:
            journey_id = self.current_journey_id or f"jarvis_comm_{int(time.time())}"

        self._track_jarvis_communication("incoming", message, journey_id)
        logger.info(f"Received message from Jarvis: {message[:100]}...")

        if self.risk_manager_handler and hasattr(
            self.risk_manager_handler, "process_jarvis_message"
        ):
            try:
                response = await self.risk_manager_handler.process_jarvis_message(
                    message=message,
                    context=context,
                    message_type=message_type,
                    journey_id=journey_id,
                )
                return response
            except Exception as e:
                logger.error(f"Error processing message from Jarvis: {e}")
                return {"error": str(e), "status": "error"}

        return {"status": "received", "timestamp": time.time()}


# ======================================================================
# Lazy RiskManager initialisation
# ======================================================================

_risk_manager = None


def _get_risk_manager():
    """Lazy import and initialise Trading Bot's RiskManager."""
    global _risk_manager
    if _risk_manager is None:
        try:
            bot_dir = Path(__file__).parent.parent / "Forex Trading Team"
            if str(bot_dir) not in sys.path:
                sys.path.insert(0, str(bot_dir))
            from Source.oanda_client import OandaClient
            from Source.account_manager import AccountManager
            from Source.risk_manager import RiskManager

            client = OandaClient()
            acct = AccountManager(client)
            _risk_manager = RiskManager(client, acct)
            logger.info("RiskManager initialised for handler")
        except ImportError as e:
            logger.warning(f"RiskManager not available: {e}")
            _risk_manager = None
    return _risk_manager


# ======================================================================
# Handler
# ======================================================================


class RiskManagerHandler(BaseHandler):
    """Handler for risk management decisions via the Jarvis MCP ecosystem.

    Wraps RiskManager from Forex Trading Team/Source/ with:
    - Action dispatch for all risk operations
    - Journey tracking for every risk decision
    - BoardRoom integration for agent performance
    - Orchestrator communication
    """

    def __init__(
        self,
        workspace_id=None,
        agent_id=None,
        journey_id=None,
    ):
        super().__init__(app_name="RiskManager")
        self.logger = logging.getLogger("RiskManager")
        self.logger.info("RiskManagerHandler initialised")

        self.workspace_id = workspace_id
        self.agent_id = agent_id or generate_simple_id()
        self.current_journey_id = journey_id

        # Orchestrator agent (same pattern as DataValidatorHandler)
        self._orchestrator_agent = RiskManagerOrchestratorAgent(self)

        # Action dispatch table
        self.action_handlers = {
            # Pre-trade (primary entry point for agents)
            "pre_trade_check": self._handle_pre_trade_check,
            # Profile management
            "get_profile": self._handle_get_profile,
            "set_profile": self._handle_set_profile,
            "get_risk_limits": self._handle_get_risk_limits,
            # Circuit breakers
            "get_circuit_breaker_status": self._handle_get_cb_status,
            "reset_circuit_breakers": self._handle_reset_cb,
            # Trade lifecycle
            "record_trade_result": self._handle_record_result,
            "register_trade": self._handle_register_trade,
            "update_open_trades": self._handle_update_trades,
            # Status
            "get_status": self._handle_get_status,
            "get_position_status": self._handle_get_position_status,
        }

        # BoardRoom was archived (Phase 3). Journey tracking uses track_journey_step_sync directly.
        self._boardroom = None

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def orchestrator_agent(self):
        """Get the orchestrator agent for this handler."""
        return self._orchestrator_agent

    # ------------------------------------------------------------------
    # Journey tracking helper
    # ------------------------------------------------------------------

    def _track_step(
        self,
        step_name: str,
        step_type: str = "risk",
        input_data: Optional[Dict] = None,
        output_data: Optional[Dict] = None,
        error: Optional[str] = None,
    ):
        """Track a risk decision step in the journey."""
        journey_id = self.current_journey_id
        if not journey_id:
            return

        try:
            track_journey_step_sync(
                journey_id=journey_id,
                step_name=step_name,
                step_type=step_type,
                input_data=input_data,
                output_data=output_data,
                error=error,
            )
        except Exception as e:
            self.logger.debug(f"Journey tracking failed: {e}")

    # ------------------------------------------------------------------
    # Handle entry point (same pattern as DataValidatorHandler)
    # ------------------------------------------------------------------

    async def handle(self, request: Dict[str, Any], data: Dict[str, Any] = None) -> Dict[str, Any]:
        """Handle a risk management request.

        Args:
            request: Dict with ``action`` and ``parameters`` keys.
            data: Optional data override.
        """
        action = request.get("action")
        if not action:
            raise ValueError("No action specified in request")

        parameters = request.get("parameters", {})
        if data is not None:
            parameters["data"] = data

        handler_fn = self.action_handlers.get(action)
        if not handler_fn:
            raise ValueError(
                f"Invalid action: {action}. "
                f"Valid actions: {list(self.action_handlers.keys())}"
            )

        start_time = time.time()
        self._track_step(f"start_{action}", input_data={"action": action})

        try:
            result = await handler_fn(parameters)
            elapsed = time.time() - start_time
            self._track_step(
                f"complete_{action}",
                output_data={"elapsed_s": round(elapsed, 3)},
            )
            return result
        except Exception as e:
            elapsed = time.time() - start_time
            self._track_step(f"error_{action}", error=str(e))
            self.logger.error(f"Error handling risk request '{action}': {e}")
            raise

    # ------------------------------------------------------------------
    # Action implementations
    # ------------------------------------------------------------------

    async def _handle_pre_trade_check(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Primary agent entry point: run full pre-trade risk assessment."""
        rm = _get_risk_manager()
        if rm is None:
            return {"error": "RiskManager not available -- Trading Bot Source not found"}

        result = rm.pre_trade_check(
            instrument=params["instrument"],
            direction=params["direction"],
            atr_value=params["atr_value"],
            regime=params["regime"],
            current_price=params["current_price"],
            pip_size=params["pip_size"],
            display_precision=params["display_precision"],
            spread_pips=params["spread_pips"],
            news_data=params.get("news_data"),
            candles=params.get("candles"),
            atr_50=params.get("atr_50"),
        )

        self._track_step(
            "pre_trade_check",
            input_data={"instrument": params["instrument"], "direction": params["direction"]},
            output_data={"allowed": result.get("allowed")},
        )
        return result

    async def _handle_get_profile(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Return the active risk profile parameters."""
        rm = _get_risk_manager()
        if rm is None:
            return {"error": "RiskManager not available"}
        profile = rm.profile_manager.get_active_profile()
        result = {
            "name": profile.name,
            "risk_pct": profile.risk_pct,
            "max_concurrent_trades": profile.max_concurrent_trades,
            "min_rr_ratio": profile.min_rr_ratio,
            "min_confluence": profile.min_confluence,
        }
        self._track_step("get_profile", output_data=result)
        return result

    async def _handle_set_profile(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Switch to a named risk profile."""
        rm = _get_risk_manager()
        if rm is None:
            return {"error": "RiskManager not available"}
        name = params["name"]
        result = rm.set_profile(name)
        self._track_step("set_profile", input_data={"name": name}, output_data=result)
        return result

    async def _handle_get_risk_limits(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Return current risk limits (for TradeValidator bridge)."""
        rm = _get_risk_manager()
        if rm is None:
            return {"error": "RiskManager not available"}
        limits = rm.profile_manager.get_risk_limits()
        self._track_step("get_risk_limits", output_data=limits)
        return limits

    async def _handle_get_cb_status(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Return circuit breaker status across all 6 layers."""
        rm = _get_risk_manager()
        if rm is None:
            return {"error": "RiskManager not available"}
        status = rm.circuit_breaker.check_all()
        self._track_step("get_circuit_breaker_status", output_data=status)
        return status

    async def _handle_reset_cb(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Operator override: reset all circuit breaker states."""
        rm = _get_risk_manager()
        if rm is None:
            return {"error": "RiskManager not available"}
        rm.reset_circuit_breakers()
        result = {"status": "reset", "message": "All circuit breakers cleared"}
        self._track_step("reset_circuit_breakers", output_data=result)
        return result

    async def _handle_record_result(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Record a trade outcome (win/loss). May trigger auto-adjustment."""
        rm = _get_risk_manager()
        if rm is None:
            return {"error": "RiskManager not available"}
        trade_result = params["result"]
        rm.record_trade_result(trade_result)
        status = rm.get_status()
        result = {
            "recorded": trade_result,
            "profile_status": status.get("profile"),
            "circuit_breaker_status": status.get("circuit_breaker"),
        }
        self._track_step(
            "record_trade_result",
            input_data={"result": trade_result},
            output_data=result,
        )
        return result

    async def _handle_register_trade(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Register a new trade for active position monitoring."""
        rm = _get_risk_manager()
        if rm is None:
            return {"error": "RiskManager not available"}
        result = rm.register_new_trade(
            trade_id=params["trade_id"],
            instrument=params["instrument"],
            direction=params["direction"],
            entry_price=params["entry_price"],
            initial_stop=params["initial_stop"],
            units=params["units"],
            pip_size=params["pip_size"],
            display_precision=params["display_precision"],
            atr_value=params.get("atr_value", 0.0),
        )
        self._track_step(
            "register_trade",
            input_data={"trade_id": params["trade_id"], "instrument": params["instrument"]},
            output_data=result,
        )
        return result

    async def _handle_update_trades(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Run the position monitor update loop for all open trades."""
        rm = _get_risk_manager()
        if rm is None:
            return {"error": "RiskManager not available"}
        actions = rm.update_open_trades(
            candles_by_instrument=params["candles_by_instrument"],
            current_prices=params["current_prices"],
        )
        result = {"actions": actions, "count": len(actions)}
        self._track_step("update_open_trades", output_data=result)
        return result

    async def _handle_get_status(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Return composite status from all risk sub-components."""
        rm = _get_risk_manager()
        if rm is None:
            return {"error": "RiskManager not available"}
        status = rm.get_status()
        self._track_step("get_status", output_data=status)
        return status

    async def _handle_get_position_status(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Return monitored trade positions only."""
        rm = _get_risk_manager()
        if rm is None:
            return {"error": "RiskManager not available"}
        positions = rm.position_monitor.get_all_statuses()
        result = {"positions": positions, "count": len(positions)}
        self._track_step("get_position_status", output_data=result)
        return result
