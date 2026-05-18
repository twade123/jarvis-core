"""
Trading Team Handler for Jarvis

Wraps the Trading Bot's agent team (TradingCycle, TradingTeamSetup) as a
Jarvis MCP handler so the 7-agent trading team is accessible through the
standard MCP handler ecosystem.

Delegates all trading operations to Forex Trading Team/Source/agents/.
"""

import time
import json
import logging
import inspect
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional
import sys
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("TradingTeam")

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


class TradingTeamOrchestratorAgent:
    """Agent for orchestrating communication between TradingTeam and Jarvis system."""

    def __init__(self, system_name="TradingTeamSystem"):
        if hasattr(system_name, "name"):
            self.trading_team_handler = system_name
            self.system_name = "TradingTeamOrchestratorAgent"
        else:
            self.system_name = system_name
            self.trading_team_handler = None

        self.conversation_history = []
        self.active = True
        self.current_journey_id = None

        # BoardRoom was archived (Phase 3). Tracking uses V2 databases directly.
        self.boardroom = None
        logger.info(f"TradingTeamOrchestratorAgent initialised for {self.system_name}")

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
            request_id = generate_simple_id("trading_team_req_")

        if not journey_id:
            journey_id = f"trading_team_{request_id}_{int(time.time())}"
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

        if self.trading_team_handler and hasattr(
            self.trading_team_handler, "process_jarvis_message"
        ):
            try:
                response = await self.trading_team_handler.process_jarvis_message(
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
# Lazy initialisation
# ======================================================================

_trading_cycle = None
_team_setup = None


def _get_team_setup():
    """Lazy import and initialise TradingTeamSetup."""
    global _team_setup
    if _team_setup is None:
        try:
            bot_dir = Path(__file__).parent.parent / "Forex Trading Team"
            if str(bot_dir) not in sys.path:
                sys.path.insert(0, str(bot_dir))
            from Source.agents.team_setup import TradingTeamSetup

            _team_setup = TradingTeamSetup()
            logger.info("TradingTeamSetup initialised for handler")
        except ImportError as e:
            logger.warning(f"TradingTeamSetup not available: {e}")
            _team_setup = None
    return _team_setup


def _get_trading_cycle():
    """Lazy import and initialise TradingCycle."""
    global _trading_cycle
    if _trading_cycle is None:
        try:
            bot_dir = Path(__file__).parent.parent / "Forex Trading Team"
            if str(bot_dir) not in sys.path:
                sys.path.insert(0, str(bot_dir))
            from Source.agents.trading_cycle import TradingCycle
            from Source.agents.comment_protocol import CommentProtocol

            setup = _get_team_setup()
            if setup is None:
                logger.warning("TradingCycle cannot initialise without TradingTeamSetup")
                return None
            protocol = CommentProtocol()
            _trading_cycle = TradingCycle(setup, protocol)
            logger.info("TradingCycle initialised for handler")
        except ImportError as e:
            logger.warning(f"TradingCycle not available: {e}")
            _trading_cycle = None
    return _trading_cycle


# ======================================================================
# Handler
# ======================================================================


class TradingTeamHandler(BaseHandler):
    """Handler for trading team operations via the Jarvis MCP ecosystem.

    Wraps TradingCycle and TradingTeamSetup from Forex Trading Team/Source/agents/ with:
    - Action dispatch for all trading cycle and team management operations
    - Journey tracking for every trading action
    - BoardRoom integration for agent performance
    - Orchestrator communication
    """

    def __init__(
        self,
        workspace_id=None,
        agent_id=None,
        journey_id=None,
    ):
        super().__init__(app_name="TradingTeam")
        self.logger = logging.getLogger("TradingTeam")
        self.logger.info("TradingTeamHandler initialised")

        self.workspace_id = workspace_id
        self.agent_id = agent_id or generate_simple_id()
        self.current_journey_id = journey_id

        # Orchestrator agent (same pattern as RiskManagerHandler)
        self._orchestrator_agent = TradingTeamOrchestratorAgent(self)

        # Action dispatch table
        self.action_handlers = {
            # Cycle operations
            "run_cycle": self._handle_run_cycle,
            "run_position_update": self._handle_position_update,
            # Operator commands
            "operator_command": self._handle_operator_command,
            # Status
            "get_status": self._handle_get_status,
            "get_cycle_config": self._handle_get_cycle_config,
            # Team management
            "setup_team": self._handle_setup_team,
            "get_team_status": self._handle_get_team_status,
            # Risk integration
            "get_risk_status": self._handle_get_risk_status,
            # Scheduler control (Phase 10)
            "start_schedule": self._handle_start_schedule,
            "stop_schedule": self._handle_stop_schedule,
            "get_schedule_status": self._handle_get_schedule_status,
            "update_schedule": self._handle_update_schedule,
            # Backtesting (Phase 11)
            "run_backtest": self._handle_run_backtest,
            "run_comparison": self._handle_run_comparison,
            "get_backtest_results": self._handle_get_backtest_results,
            # Logging & Reporting (Phase 12)
            "get_trade_log": self._handle_get_trade_log,
            "get_signal_log": self._handle_get_signal_log,
            "get_weekly_report": self._handle_get_weekly_report,
            "get_instrument_ranking": self._handle_get_instrument_ranking,
        }

        # Lazy scheduler singleton
        self._scheduler_manager = None

        # Lazy backtest analysis singleton and results store
        self._backtest_analysis = None
        self._backtest_results: Dict[str, Any] = {}

        # Lazy trade logger singleton (Phase 12)
        self._trade_logger = None

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
        step_type: str = "trading",
        input_data: Optional[Dict] = None,
        output_data: Optional[Dict] = None,
        error: Optional[str] = None,
    ):
        """Track a trading operation step in the journey."""
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
    # Handle entry point (same pattern as RiskManagerHandler)
    # ------------------------------------------------------------------

    async def handle(self, request: Dict[str, Any], data: Dict[str, Any] = None) -> Dict[str, Any]:
        """Handle a trading team request.

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
            self.logger.error(f"Error handling trading team request '{action}': {e}")
            raise

    # ------------------------------------------------------------------
    # Action implementations
    # ------------------------------------------------------------------

    async def _handle_run_cycle(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Run a complete trading cycle for an instrument."""
        cycle = _get_trading_cycle()
        if cycle is None:
            return {"error": "TradingCycle not available -- Trading Bot Source not found"}

        instrument = params.get("instrument", "EUR_USD")
        timeframe = params.get("timeframe", "H1")
        result = cycle.run_cycle(instrument, timeframe)

        self._track_step(
            "run_cycle",
            input_data={"instrument": instrument, "timeframe": timeframe},
            output_data={"action": result.get("action", "unknown")},
        )
        return result

    async def _handle_position_update(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Run position monitoring update for open trades."""
        cycle = _get_trading_cycle()
        if cycle is None:
            return {"error": "TradingCycle not available"}

        instruments = params.get("instruments")
        result = cycle.run_position_update(instruments)

        self._track_step(
            "run_position_update",
            input_data={"instruments": instruments},
            output_data={"actions_count": len(result.get("actions", []))},
        )
        return result

    async def _handle_operator_command(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Process an operator command (pause, resume, set_profile, etc.)."""
        cycle = _get_trading_cycle()
        if cycle is None:
            return {"error": "TradingCycle not available"}

        command = params.get("command")
        cmd_params = params.get("params", {})
        if not command:
            return {"error": "No command specified"}

        result = cycle.handle_operator_command(command, cmd_params)

        self._track_step(
            "operator_command",
            input_data={"command": command},
            output_data=result,
        )
        return result

    async def _handle_get_status(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Return current cycle status."""
        cycle = _get_trading_cycle()
        if cycle is None:
            return {"error": "TradingCycle not available"}

        status = cycle.get_cycle_status()
        self._track_step("get_status", output_data=status)
        return status

    async def _handle_get_cycle_config(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Return cycle configuration for an instrument."""
        try:
            bot_dir = Path(__file__).parent.parent / "Forex Trading Team"
            if str(bot_dir) not in sys.path:
                sys.path.insert(0, str(bot_dir))
            from Source.agents import orchestrator_agent

            instrument = params.get("instrument", "EUR_USD")
            config = orchestrator_agent.get_cycle_config(instrument)

            self._track_step(
                "get_cycle_config",
                input_data={"instrument": instrument},
                output_data=config,
            )
            return config
        except ImportError as e:
            return {"error": f"orchestrator_agent not available: {e}"}

    async def _handle_setup_team(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Set up the trading team: workspaces, agents, and team formation."""
        setup = _get_team_setup()
        if setup is None:
            return {"error": "TradingTeamSetup not available"}

        try:
            ws_result = setup.setup_workspaces()
            reg_result = setup.register_agents()
            team_result = setup.create_trading_team()
            result = {
                "workspaces": ws_result,
                "agents": reg_result,
                "team": team_result,
                "status": "team_setup_complete",
            }
        except Exception as e:
            result = {"error": f"Team setup failed: {e}", "status": "failed"}

        self._track_step("setup_team", output_data=result)
        return result

    async def _handle_get_team_status(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Return team registration and workspace status."""
        setup = _get_team_setup()
        if setup is None:
            return {"error": "TradingTeamSetup not available"}

        status = setup.get_team_status()
        self._track_step("get_team_status", output_data=status)
        return status

    async def _handle_get_risk_status(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Return risk status from the orchestrator agent."""
        try:
            bot_dir = Path(__file__).parent.parent / "Forex Trading Team"
            if str(bot_dir) not in sys.path:
                sys.path.insert(0, str(bot_dir))
            from Source.agents import orchestrator_agent

            status = orchestrator_agent.get_risk_status()

            self._track_step("get_risk_status", output_data=status)
            return status
        except ImportError as e:
            return {"error": f"orchestrator_agent not available: {e}"}

    # ------------------------------------------------------------------
    # Scheduler actions (Phase 10)
    # ------------------------------------------------------------------

    def _get_scheduler(self, params: Dict[str, Any] = None):
        """Lazy import and create WorkspaceScheduleManager.

        Creates from config_path or config_dict in params on first call.
        Subsequent calls return the existing singleton.
        """
        if self._scheduler_manager is not None:
            return self._scheduler_manager

        try:
            bot_dir = Path(__file__).parent.parent / "Forex Trading Team"
            if str(bot_dir) not in sys.path:
                sys.path.insert(0, str(bot_dir))
            from Source.scheduler import WorkspaceScheduleManager

            params = params or {}
            config_path = params.get("config_path")
            config_dict = params.get("config_dict")

            if config_path:
                self._scheduler_manager = WorkspaceScheduleManager(
                    config_path=config_path
                )
            elif config_dict:
                self._scheduler_manager = WorkspaceScheduleManager(
                    config_dict=config_dict
                )
            else:
                self.logger.warning(
                    "No config_path or config_dict provided for scheduler"
                )
                return None

            self.logger.info("WorkspaceScheduleManager initialised for handler")
        except ImportError as e:
            self.logger.warning(f"WorkspaceScheduleManager not available: {e}")
            return None

        return self._scheduler_manager

    async def _handle_start_schedule(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Start the workspace schedule manager."""
        mgr = self._get_scheduler(params)
        if mgr is None:
            return {
                "error": "WorkspaceScheduleManager not available -- "
                "provide config_path or config_dict"
            }

        mgr.start()
        status = mgr.get_status()

        self._track_step("start_schedule", output_data=status)
        return {"status": "started", **status}

    async def _handle_stop_schedule(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Stop the workspace schedule manager."""
        mgr = self._get_scheduler(params)
        if mgr is None:
            return {"error": "No scheduler running"}

        mgr.stop()

        self._track_step("stop_schedule", output_data={"stopped": True})
        return {"status": "stopped"}

    async def _handle_get_schedule_status(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Return schedule status including weekend state."""
        mgr = self._get_scheduler(params)
        if mgr is None:
            return {"error": "No scheduler initialised"}

        status = mgr.get_status()

        self._track_step("get_schedule_status", output_data=status)
        return status

    async def _handle_update_schedule(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Update scheduler config and restart if running."""
        mgr = self._get_scheduler(params)
        if mgr is None:
            return {"error": "No scheduler initialised"}

        updates = params.get("updates", {})
        if not updates:
            return {"error": "No updates provided"}

        mgr.update_config(updates)
        status = mgr.get_status()

        self._track_step("update_schedule", output_data=status)
        return {"status": "updated", **status}

    # ------------------------------------------------------------------
    # Backtesting actions (Phase 11)
    # ------------------------------------------------------------------

    def _get_backtest_analysis(self, market_type: str = "forex"):
        """Get or create BacktestAnalysis for a market type.

        Uses OandaClient as default CandleProvider for forex.
        Future: add Coinbase/futures provider selection based on market_type.
        """
        if (
            self._backtest_analysis is None
            or self._backtest_analysis._market_type != market_type
        ):
            try:
                bot_dir = Path(__file__).parent.parent / "Forex Trading Team"
                if str(bot_dir) not in sys.path:
                    sys.path.insert(0, str(bot_dir))
                from Source.oanda_client import OandaClient
                from Source.backtest_analysis import BacktestAnalysis

                client = OandaClient()
                self._backtest_analysis = BacktestAnalysis(
                    client, market_type=market_type
                )
                self.logger.info(
                    "BacktestAnalysis initialised for market_type=%s", market_type
                )
            except ImportError as e:
                self.logger.warning(f"BacktestAnalysis not available: {e}")
                return None
        return self._backtest_analysis

    @staticmethod
    def _parse_iso_time(time_str: str) -> datetime:
        """Parse ISO 8601 time string to UTC datetime."""
        s = time_str.replace("Z", "+00:00")
        return datetime.fromisoformat(s)

    async def _handle_run_backtest(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Run a single backtest with walk-forward optimization.

        Required params: instrument, from_time, to_time.
        Optional: market_type (default 'forex'), initial_balance, risk_per_trade.
        """
        instrument = params.get("instrument")
        from_time_str = params.get("from_time")
        to_time_str = params.get("to_time")

        if not all([instrument, from_time_str, to_time_str]):
            return {"error": "Required: instrument, from_time, to_time"}

        market_type = params.get("market_type", "forex")
        analysis = self._get_backtest_analysis(market_type)
        if analysis is None:
            return {"error": "BacktestAnalysis not available -- Trading Bot Source not found"}

        try:
            from_time = self._parse_iso_time(from_time_str)
            to_time = self._parse_iso_time(to_time_str)
        except (ValueError, TypeError) as e:
            return {"error": f"Invalid time format: {e}"}

        try:
            bot_dir = Path(__file__).parent.parent / "Forex Trading Team"
            if str(bot_dir) not in sys.path:
                sys.path.insert(0, str(bot_dir))
            from Source.backtester import BacktestConfig, Backtester, WalkForwardOptimizer

            config_kwargs: Dict[str, Any] = {"market_type": market_type}
            if "initial_balance" in params:
                config_kwargs["initial_balance"] = float(params["initial_balance"])
            if "risk_per_trade" in params:
                config_kwargs["risk_per_trade"] = float(params["risk_per_trade"])

            config = BacktestConfig(**config_kwargs)
            bt = Backtester(config)
            wfo = WalkForwardOptimizer()

            candle_data = analysis._fetch_all_timeframes(instrument, from_time, to_time)
            wfo_result = wfo.run(candle_data, instrument, bt)

            run_id = str(uuid.uuid4())[:8]
            self._backtest_results[run_id] = {
                "run_id": run_id,
                "instrument": instrument,
                "market_type": market_type,
                "from_time": from_time_str,
                "to_time": to_time_str,
                "result": wfo_result,
                "timestamp": time.time(),
            }

            # Summarise for response
            test_m = wfo_result.get("test", {}).get("metrics", {})
            overfit = wfo_result.get("overfit_check", {})
            summary = {
                "run_id": run_id,
                "instrument": instrument,
                "market_type": market_type,
                "test_sharpe": test_m.get("sharpe_ratio", 0.0),
                "test_max_drawdown": test_m.get("max_drawdown_pct", "?"),
                "test_profit_factor": test_m.get("profit_factor", 0.0),
                "test_win_rate": test_m.get("win_rate", 0.0),
                "test_trades": test_m.get("total_trades", 0),
                "overfit_verdict": overfit.get("verdict", "unknown"),
            }

            self._track_step(
                "run_backtest",
                input_data={"instrument": instrument, "market_type": market_type},
                output_data=summary,
            )
            return summary

        except Exception as e:
            self.logger.error(f"Backtest failed: {e}")
            return {"error": f"Backtest failed: {e}"}

    async def _handle_run_comparison(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Run a comparison analysis.

        Required: instrument, from_time, to_time, comparison_type.
        comparison_type: 'ema_periods', 'candlestick_patterns', 'chart_patterns', 'full'.
        Optional: market_type (default 'forex').
        """
        instrument = params.get("instrument")
        from_time_str = params.get("from_time")
        to_time_str = params.get("to_time")
        comparison_type = params.get("comparison_type")

        if not all([instrument, from_time_str, to_time_str, comparison_type]):
            return {
                "error": "Required: instrument, from_time, to_time, comparison_type"
            }

        market_type = params.get("market_type", "forex")
        analysis = self._get_backtest_analysis(market_type)
        if analysis is None:
            return {"error": "BacktestAnalysis not available"}

        try:
            from_time = self._parse_iso_time(from_time_str)
            to_time = self._parse_iso_time(to_time_str)
        except (ValueError, TypeError) as e:
            return {"error": f"Invalid time format: {e}"}

        try:
            if comparison_type == "ema_periods":
                result = analysis.compare_ema_periods(instrument, from_time, to_time)
            elif comparison_type == "candlestick_patterns":
                result = analysis.analyze_candlestick_patterns(
                    instrument, from_time, to_time
                )
            elif comparison_type == "chart_patterns":
                result = analysis.analyze_chart_patterns(
                    instrument, from_time, to_time
                )
            elif comparison_type == "full":
                result = analysis.run_full_analysis(instrument, from_time, to_time)
            else:
                return {
                    "error": f"Invalid comparison_type: {comparison_type}. "
                    "Valid: ema_periods, candlestick_patterns, chart_patterns, full"
                }

            run_id = str(uuid.uuid4())[:8]
            self._backtest_results[run_id] = {
                "run_id": run_id,
                "comparison_type": comparison_type,
                "instrument": instrument,
                "market_type": market_type,
                "result": result,
                "timestamp": time.time(),
            }

            # For full analysis, include formatted report
            if comparison_type == "full":
                result["formatted_report"] = analysis.format_comparison_report(result)

            result["run_id"] = run_id

            self._track_step(
                "run_comparison",
                input_data={
                    "instrument": instrument,
                    "comparison_type": comparison_type,
                },
                output_data={"run_id": run_id},
            )
            return result

        except Exception as e:
            self.logger.error(f"Comparison failed: {e}")
            return {"error": f"Comparison failed: {e}"}

    async def _handle_get_backtest_results(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Retrieve stored backtest results.

        Optional: run_id (returns latest if not specified).
        """
        run_id = params.get("run_id")

        if not self._backtest_results:
            return {"error": "No backtest results stored"}

        if run_id:
            if run_id not in self._backtest_results:
                return {"error": f"Run ID not found: {run_id}"}
            return self._backtest_results[run_id]

        # Return most recent result
        latest = max(
            self._backtest_results.values(),
            key=lambda r: r.get("timestamp", 0),
        )
        return latest

    # ------------------------------------------------------------------
    # Logging & Reporting actions (Phase 12)
    # ------------------------------------------------------------------

    def _get_trade_logger(self):
        """Get or create TradeLogger singleton."""
        if self._trade_logger is None:
            try:
                bot_dir = Path(__file__).parent.parent / "Forex Trading Team"
                if str(bot_dir) not in sys.path:
                    sys.path.insert(0, str(bot_dir))
                from Source.trade_logger import TradeLogger

                self._trade_logger = TradeLogger()
                self.logger.info("TradeLogger initialised for handler")
            except ImportError as e:
                self.logger.warning(f"TradeLogger not available: {e}")
                return None
        return self._trade_logger

    async def _handle_get_trade_log(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Query the trade log with optional filters.

        Optional params: instrument, from_date, to_date, limit (default 50).
        """
        tl = self._get_trade_logger()
        if tl is None:
            return {"error": "TradeLogger not available -- Trading Bot Source not found"}

        instrument = params.get("instrument")
        from_date = params.get("from_date")
        to_date = params.get("to_date")
        limit = params.get("limit", 50)

        trades = tl.get_trades(
            instrument=instrument,
            from_date=from_date,
            to_date=to_date,
            limit=limit,
        )

        self._track_step(
            "get_trade_log",
            input_data={"instrument": instrument, "limit": limit},
            output_data={"count": len(trades)},
        )
        return {"trades": trades, "count": len(trades)}

    async def _handle_get_signal_log(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Query the signal log with optional filters.

        Optional params: instrument, from_date, to_date, limit (default 50).
        """
        tl = self._get_trade_logger()
        if tl is None:
            return {"error": "TradeLogger not available -- Trading Bot Source not found"}

        instrument = params.get("instrument")
        from_date = params.get("from_date")
        to_date = params.get("to_date")
        limit = params.get("limit", 50)

        signals = tl.get_signals(
            instrument=instrument,
            from_date=from_date,
            to_date=to_date,
            limit=limit,
        )

        self._track_step(
            "get_signal_log",
            input_data={"instrument": instrument, "limit": limit},
            output_data={"count": len(signals)},
        )
        return {"signals": signals, "count": len(signals)}

    async def _handle_get_weekly_report(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Generate a weekly performance report.

        Optional params: instruments (list of instrument names).
        """
        try:
            bot_dir = Path(__file__).parent.parent / "Forex Trading Team"
            if str(bot_dir) not in sys.path:
                sys.path.insert(0, str(bot_dir))
            from Source.agents.reporting_agent import generate_weekly_report

            instruments = params.get("instruments")
            report = generate_weekly_report(instruments)

            self._track_step(
                "get_weekly_report",
                input_data={"instruments": instruments},
                output_data={"total_trades": report.get("total_trades", 0)},
            )
            return report
        except ImportError as e:
            return {"error": f"reporting_agent not available: {e}"}

    async def _handle_get_instrument_ranking(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Return instruments ranked by profitability.

        Optional params: lookback_days (default 30).
        """
        try:
            bot_dir = Path(__file__).parent.parent / "Forex Trading Team"
            if str(bot_dir) not in sys.path:
                sys.path.insert(0, str(bot_dir))
            from Source.agents.reporting_agent import get_instrument_comparison

            lookback_days = params.get("lookback_days", 30)
            ranking = get_instrument_comparison(lookback_days)

            self._track_step(
                "get_instrument_ranking",
                input_data={"lookback_days": lookback_days},
                output_data={"instruments_count": len(ranking.get("instruments", []))},
            )
            return ranking
        except ImportError as e:
            return {"error": f"reporting_agent not available: {e}"}
