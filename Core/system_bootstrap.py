"""
System Bootstrap — hardware-aware startup for the Jarvis platform.

Detects the Mac's hardware tier at startup, loads the right resident models,
and returns a status report. The shell script (mlx_servers.sh) remains as
a dumb launcher; all scheduling intelligence lives here.

Usage:
    python3 Core/system_bootstrap.py               # detect + start models
    python3 Core/system_bootstrap.py --detect-only  # just report, don't start
    python3 Core/system_bootstrap.py --no-start     # same as detect-only
"""
import asyncio
import json
import logging
import subprocess
import sys
import time
from pathlib import Path
from typing import Optional

from Core.resource_config import (
    MODEL_CATALOG, HardwareTier,
    detect_hardware_tier, get_tier_profile,
)
from Core.mlx_registry import get_registry
from Core.model_lifecycle import get_lifecycle, start_idle_monitor

logger = logging.getLogger(__name__)

MLX_SERVERS_SH = str(Path(__file__).parent.parent / "scripts" / "mlx_servers.sh")


class SystemBootstrap:
    """
    One-time startup sequence.

    Call bootstrap() once at system start (serve_ui.py, trading_launcher.sh, etc.).
    Multiple calls are safe — idempotent checks prevent double-starting.
    """

    def __init__(self):
        self.tier      = detect_hardware_tier()
        self.profile   = get_tier_profile()
        self.registry  = get_registry()
        self.lifecycle = get_lifecycle()

    # ── Hardware detection ────────────────────────────────────────────────────

    def detect_and_report(self) -> dict:
        """Return hardware info without starting anything."""
        try:
            total_bytes = int(subprocess.check_output(
                ["sysctl", "-n", "hw.memsize"], stderr=subprocess.DEVNULL
            ).strip())
            total_gb = round(total_bytes / (1024 ** 3), 1)
        except Exception:
            total_gb = 0.0

        try:
            cpu_cores = int(subprocess.check_output(
                ["sysctl", "-n", "hw.physicalcpu"], stderr=subprocess.DEVNULL
            ).strip())
        except Exception:
            cpu_cores = 0

        try:
            chip = subprocess.check_output(
                ["sysctl", "-n", "machdep.cpu.brand_string"],
                stderr=subprocess.DEVNULL
            ).decode().strip()
        except Exception:
            chip = "unknown"

        return {
            "tier":                self.tier.value,
            "chip":                chip,
            "total_ram_gb":        total_gb,
            "cpu_cores":           cpu_cores,
            "model_budget_gb":     self.profile.model_budget_gb,
            "resident_models":     self.profile.resident_models,
            "on_demand_models":    self.profile.on_demand_models,
            "max_parallel_sessions": self.profile.max_parallel_sessions,
            "unload_after_min":    self.profile.unload_idle_after_minutes,
        }

    # ── Model startup ─────────────────────────────────────────────────────────

    def _start_via_shell(self, key: str) -> bool:
        """
        Start one MLX server via mlx_servers.sh (the dumb launcher).
        Maps model key → board seat name for the script.
        """
        spec = MODEL_CATALOG.get(key)
        if not spec:
            return False
        seat = spec.board_seat if spec.board_seat else key.upper()
        try:
            result = subprocess.run(
                ["bash", MLX_SERVERS_SH, "start", seat],
                capture_output=True, text=True, timeout=120,
            )
            if result.returncode == 0:
                logger.info("✅ Started %s (%s)", key, seat)
                return True
            else:
                logger.warning(
                    "mlx_servers.sh start %s returned %d: %s",
                    seat, result.returncode, result.stderr[:200],
                )
                return False
        except subprocess.TimeoutExpired:
            logger.error("%s startup timed out", key)
            return False
        except Exception as e:
            logger.error("Failed to start %s: %s", key, e)
            return False

    # ── Main entry point ──────────────────────────────────────────────────────

    async def bootstrap(self, start_models: bool = True) -> dict:
        """
        Full startup sequence.

        1. Detect hardware tier
        2. Log tier + budget
        3. Start resident models in parallel (if start_models=True)
        4. Refresh registry and return status report
        """
        report = self.detect_and_report()

        logger.info(
            "🚀 Jarvis bootstrap — tier=%s chip=%s ram=%.0fGB budget=%.0fGB",
            report["tier"], report["chip"],
            report["total_ram_gb"], report["model_budget_gb"],
        )

        if self.tier == HardwareTier.MINIMAL:
            logger.warning(
                "⚠️  16GB mode: no models pre-loaded. "
                "Lifecycle manager will load on demand (~20-30s per model). "
                "Full system requires 64GB+ Mac."
            )

        started, failed = [], []

        if start_models and self.profile.resident_models:
            logger.info("Starting resident models: %s", self.profile.resident_models)
            loop = asyncio.get_event_loop()

            tasks = {
                key: loop.run_in_executor(None, self._start_via_shell, key)
                for key in self.profile.resident_models
            }
            results = await asyncio.gather(*tasks.values(), return_exceptions=True)

            for key, result in zip(tasks.keys(), results):
                if result is True:
                    started.append(key)
                else:
                    failed.append(key)
                    logger.warning("Failed to start resident model %s", key)

        # Brief pause then refresh registry
        if started:
            await asyncio.sleep(2)

        status = self.registry.refresh()
        alive        = [k for k, s in status.items() if s.alive]
        loaded_gb    = self.registry.get_loaded_memory_gb()

        result = {
            **report,
            "started":          started,
            "failed":           failed,
            "alive_models":     alive,
            "loaded_memory_gb": round(loaded_gb, 1),
            "budget_used_pct":  round(loaded_gb / max(1, report["model_budget_gb"]) * 100, 1),
        }

        logger.info(
            "✅ Bootstrap complete — %d/%d models alive (%.1fGB / %.0fGB budget, %.0f%%)",
            len(alive), len(MODEL_CATALOG),
            loaded_gb, report["model_budget_gb"], result["budget_used_pct"],
        )

        if failed:
            logger.warning("Models that failed to start: %s", failed)

        # Start background idle monitor (auto-unloads on-demand models after idle threshold)
        if self.profile.on_demand_models and self.profile.unload_idle_after_minutes > 0:
            start_idle_monitor()
            logger.info(
                "⏰ Idle monitor active — will unload %s after %.0f min idle",
                self.profile.on_demand_models, self.profile.unload_idle_after_minutes,
            )

        return result

    async def graceful_shutdown(self):
        """Signal all workers to finish in-flight requests then exit."""
        logger.info("Graceful shutdown initiated...")
        try:
            from Core.workspace_scheduler import get_scheduler
            await get_scheduler().shutdown()
        except Exception as e:
            logger.debug("Scheduler shutdown: %s", e)
        logger.info("Shutdown complete.")


# ── Convenience helpers ───────────────────────────────────────────────────────

async def run_bootstrap(start_models: bool = True) -> dict:
    """Top-level convenience for import into serve_ui.py, launchers, etc."""
    return await SystemBootstrap().bootstrap(start_models=start_models)


def get_system_info() -> dict:
    """Synchronous — safe to call before event loop starts."""
    bs = SystemBootstrap()
    return bs.detect_and_report()


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(name)s: %(message)s",
    )

    detect_only = "--detect-only" in sys.argv or "--no-start" in sys.argv
    result = asyncio.run(run_bootstrap(start_models=not detect_only))
    print(json.dumps(result, indent=2))
