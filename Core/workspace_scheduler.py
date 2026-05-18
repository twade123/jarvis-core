"""
Workspace Scheduler — priority-based access control for shared MLX model servers.

Models are shared infrastructure. Both the trading workspace and boardroom workspace
use ports 11500 (9B) and 11502 (35B). This scheduler ensures:

  - Trading gets CRITICAL priority when an open trade is active
  - Trading gets HIGH priority during market hours (Mon-Fri 8AM-5PM ET)
  - Boardroom has EXCLUSIVE access to ports 11501 (CTO) and 11503 (CDO)
  - On shared ports, boardroom yields to trading during market hours
  - Off-hours: all workspaces run at equal NORMAL priority

Architecture: per-port asyncio.PriorityQueues drained by background workers.
Each request is (priority, timestamp, future, task_fn). Lower priority = runs first.
Timestamp breaks ties (FIFO within same priority).
"""
import asyncio
import json
import logging
import time
import urllib.request
from datetime import datetime, time as dtime
from typing import Any, Callable, Dict, Optional

try:
    from zoneinfo import ZoneInfo
except ImportError:
    from backports.zoneinfo import ZoneInfo   # Python < 3.9

logger = logging.getLogger(__name__)

# ── Priority constants (lower = higher priority) ──────────────────────────────
PRIORITY_CRITICAL = 0   # open trade — position management, never wait
PRIORITY_HIGH     = 1   # market hours trading OR boardroom on exclusive port
PRIORITY_NORMAL   = 2   # off-hours tasks, deliberation
PRIORITY_LOW      = 3   # briefings, reporting, housekeeping

# ── Market hours ──────────────────────────────────────────────────────────────
ET           = ZoneInfo("America/New_York")
MARKET_OPEN  = dtime(8, 0)
MARKET_CLOSE = dtime(17, 0)

# Ports shared by both trading and boardroom
TRADING_SHARED_PORTS   = {11500, 11502}
# Ports only boardroom uses (trading never touches these)
BOARDROOM_ONLY_PORTS   = {11501, 11503}

# Default timeout before a queued request gives up
DEFAULT_REQUEST_TIMEOUT = 300.0   # 5 minutes


class WorkspaceScheduler:
    """
    Per-port priority queue with background drain workers.
    Thread-safe via asyncio primitives.
    """

    def __init__(self, oanda_account_id: str = "101-001-24637237-001",
                 oanda_api_key: str = ""):
        self._queues:  Dict[int, asyncio.PriorityQueue] = {}
        self._workers: Dict[int, asyncio.Task] = {}
        self._oanda_account  = oanda_account_id
        self._oanda_key      = oanda_api_key
        self._open_trade_count: int = 0
        self._last_trade_check: float = 0.0
        self._trade_check_ttl: float  = 30.0   # re-check every 30s

    # ── Queue management ──────────────────────────────────────────────────────

    def _ensure_worker(self, port: int):
        """Lazily create a queue + drain worker for a port."""
        if port not in self._queues:
            self._queues[port]  = asyncio.PriorityQueue()
            self._workers[port] = asyncio.create_task(
                self._drain_worker(port),
                name=f"sched-worker-{port}",
            )

    async def _drain_worker(self, port: int):
        """Background task: drain requests for one port, one at a time."""
        q = self._queues[port]
        while True:
            try:
                priority, ts, future, task_fn = await q.get()
                if future.cancelled():
                    q.task_done()
                    continue
                try:
                    result = await task_fn()
                    if not future.done():
                        future.set_result(result)
                except Exception as exc:
                    if not future.done():
                        future.set_exception(exc)
                finally:
                    q.task_done()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Scheduler worker port %d error: %s", port, e)

    # ── Priority detection ────────────────────────────────────────────────────

    def is_market_hours(self) -> bool:
        """True Mon-Fri 8:00–17:00 ET."""
        now = datetime.now(ET)
        if now.weekday() >= 5:  # Saturday=5, Sunday=6
            return False
        return MARKET_OPEN <= now.time() <= MARKET_CLOSE

    async def _check_open_trades(self) -> bool:
        """Query OANDA for open positions. Result cached for trade_check_ttl seconds."""
        now = time.time()
        if now - self._last_trade_check < self._trade_check_ttl:
            return self._open_trade_count > 0

        self._last_trade_check = now

        if not self._oanda_key:
            return False

        try:
            url = (f"https://api-fxtrade.oanda.com/v3/accounts/"
                   f"{self._oanda_account}/openTrades")
            req = urllib.request.Request(
                url, headers={"Authorization": f"Bearer {self._oanda_key}"}
            )
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read())
                self._open_trade_count = len(data.get("trades", []))
        except Exception as e:
            logger.debug("OANDA trade check failed (non-critical): %s", e)
            self._open_trade_count = 0

        return self._open_trade_count > 0

    async def get_trading_priority(self) -> int:
        """Compute priority for a trading workspace request."""
        if await self._check_open_trades():
            return PRIORITY_CRITICAL
        if self.is_market_hours():
            return PRIORITY_HIGH
        return PRIORITY_NORMAL

    def get_boardroom_priority(self, port: int) -> int:
        """Compute priority for a boardroom workspace request."""
        # Boardroom owns these ports — always HIGH
        if port in BOARDROOM_ONLY_PORTS:
            return PRIORITY_HIGH
        # Shared port during market hours — yield to trading
        if self.is_market_hours():
            return PRIORITY_NORMAL
        return PRIORITY_HIGH

    # ── Main API ──────────────────────────────────────────────────────────────

    async def request_model(
        self,
        port: int,
        workspace: str,
        task_fn: Callable[[], Any],
        priority: Optional[int] = None,
        timeout: float = DEFAULT_REQUEST_TIMEOUT,
    ) -> Any:
        """
        Submit a model request and await its result.

        Args:
            port:      MLX server port (11500–11503)
            workspace: "trading" or "boardroom" (used for auto-priority)
            task_fn:   async callable — the actual inference call
            priority:  override auto-detected priority (optional)
            timeout:   max seconds to wait for queue + execution

        Returns: whatever task_fn() returns
        Raises:  asyncio.TimeoutError if wait exceeds timeout
        """
        # Auto-detect priority if not provided
        if priority is None:
            if workspace == "trading":
                priority = await self.get_trading_priority()
            else:
                priority = self.get_boardroom_priority(port)

        self._ensure_worker(port)
        loop  = asyncio.get_event_loop()
        future: asyncio.Future = loop.create_future()

        # PriorityQueue item: (priority, monotonic_ts for FIFO tiebreak, future, fn)
        await self._queues[port].put((priority, time.monotonic(), future, task_fn))

        q_depth = self._queues[port].qsize()
        logger.debug(
            "[%s] queued on port %d — priority=%d, queue_depth=%d",
            workspace, port, priority, q_depth,
        )

        try:
            return await asyncio.wait_for(asyncio.shield(future), timeout=timeout)
        except asyncio.TimeoutError:
            future.cancel()
            raise asyncio.TimeoutError(
                f"[{workspace}] request on port {port} timed out after {timeout:.0f}s"
            )

    def queue_depth(self, port: int) -> int:
        q = self._queues.get(port)
        return q.qsize() if q else 0

    def is_busy(self, port: int) -> bool:
        return self.queue_depth(port) > 0

    async def shutdown(self):
        """Cancel all worker tasks cleanly."""
        for task in self._workers.values():
            task.cancel()
        await asyncio.gather(*self._workers.values(), return_exceptions=True)
        self._workers.clear()
        self._queues.clear()

    def status_summary(self) -> dict:
        return {
            "market_hours": self.is_market_hours(),
            "open_trades":  self._open_trade_count,
            "queues": {
                port: self.queue_depth(port)
                for port in self._queues
            },
        }


# ── Module-level singleton ────────────────────────────────────────────────────

_scheduler: Optional[WorkspaceScheduler] = None


def get_scheduler(oanda_key: str = "") -> WorkspaceScheduler:
    global _scheduler
    if _scheduler is None:
        key = oanda_key
        if not key:
            key = os.environ.get('OANDA_API_KEY', '')
            if not key:
                try:
                    with open("~/jarvis/API/OANDA_API_KEY.txt") as f:
                        key = f.read().strip()
                except Exception:
                    pass
        _scheduler = WorkspaceScheduler(oanda_api_key=key)
    return _scheduler


if __name__ == "__main__":
    import asyncio
    logging.basicConfig(level=logging.INFO)

    async def _test():
        sched = get_scheduler()
        print(f"Market hours:   {sched.is_market_hours()}")
        print(f"Trading prio:   {await sched.get_trading_priority()}")
        print(f"Boardroom prio (11500): {sched.get_boardroom_priority(11500)}")
        print(f"Boardroom prio (11501): {sched.get_boardroom_priority(11501)}")
        print(f"Status: {sched.status_summary()}")

    asyncio.run(_test())
