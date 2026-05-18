"""
Model Lifecycle Manager — dynamic loading and unloading of MLX server processes.

Handles:
  ensure_loaded(key)  — guarantee model is warm before calling it (idempotent)
  prefetch(key)       — background load: start now, don't wait (hides load latency)
  maybe_unload(key)   — free GPU memory if over budget and model is idle
  get_memory_pressure — 0.0–1.0 gauge of how full the budget is

Tier-aware behaviour:
  POWER_USER (64GB): never unload — always enough headroom; prefetch hides latency
  STANDARD   (32GB): LRU eviction after 10 min idle; DeepSeek-14B on-demand only
  MINIMAL    (16GB): strict 1-at-a-time; unload after 1 min
  PRO/SERVER       : same as POWER_USER — never unload
"""
import asyncio
import logging
import os
import socket
import subprocess
import time
import urllib.request
from typing import Dict, Optional

from Core.resource_config import (
    MODEL_CATALOG, ModelSpec, HardwareTier,
    detect_hardware_tier, get_tier_profile,
    get_health_endpoint,
)
from Core.mlx_registry import get_registry

logger = logging.getLogger(__name__)

VENV          = "~/myenv/bin/activate"
LOG_DIR       = "~/jarvis/Logs/mlx"
STARTUP_TIMEOUT_S = 90   # max seconds to wait for server to become ready
POLL_INTERVAL_S   = 2    # seconds between ready-checks during startup


class ModelLifecycleManager:
    """
    Manages MLX server process lifecycle.
    Per-model asyncio Locks prevent concurrent start attempts.
    """

    def __init__(self):
        self._tier    = detect_hardware_tier()
        self._profile = get_tier_profile()
        self._locks:           Dict[str, asyncio.Lock] = {k: asyncio.Lock() for k in MODEL_CATALOG}
        self._prefetch_tasks:  Dict[str, asyncio.Task] = {}
        self._last_used:       Dict[str, float]        = {}
        os.makedirs(LOG_DIR, exist_ok=True)
        logger.info(
            "ModelLifecycleManager ready — tier=%s budget=%.0fGB resident=%s",
            self._tier.value, self._profile.model_budget_gb, self._profile.resident_models,
        )

    # ── Low-level helpers ─────────────────────────────────────────────────────

    def _port_open(self, port: int) -> bool:
        with socket.socket() as s:
            return s.connect_ex(("127.0.0.1", port)) == 0

    def _is_alive(self, key: str) -> bool:
        spec = MODEL_CATALOG.get(key)
        if not spec:
            return False
        ep  = get_health_endpoint(spec)
        url = f"http://127.0.0.1:{spec.port}{ep}"
        try:
            with urllib.request.urlopen(url, timeout=3):
                return True
        except Exception:
            return False

    def _start_server_sync(self, key: str) -> bool:
        """Launch the MLX server process. Blocks until ready or timeout."""
        spec = MODEL_CATALOG.get(key)
        if not spec:
            logger.error("Unknown model key: %s", key)
            return False

        if self._port_open(spec.port):
            logger.info("%s port %d already occupied — checking liveness", key, spec.port)
            return self._is_alive(key)

        log_path = os.path.join(LOG_DIR, f"{key}.log")

        if spec.server_type == "lm_lenient":
            # VLM weights loaded as text model via mlx_lm with strict=False.
            # Enables tool calling; ignores vision tower weights.
            # Uses mlx_lm_server_lenient.py wrapper script.
            lenient_script = os.path.expanduser("~/jarvis/scripts/mlx_lm_server_lenient.py")
            cmd = (
                f"source {VENV} && "
                f"python3 {lenient_script} --model {spec.hf_repo} "
                f"--port {spec.port} --host 127.0.0.1 "
                f">> {log_path} 2>&1 &"
            )
        elif spec.server_type == "vlm":
            # Pure VLM (vision required): mlx_vlm.server, model passed per-request
            cmd = (
                f"source {VENV} && "
                f"python3 -m mlx_vlm.server --port {spec.port} --host 127.0.0.1 "
                f">> {log_path} 2>&1 &"
            )
        else:
            # Standard text model: mlx_lm.server with explicit --model
            cmd = (
                f"source {VENV} && "
                f"python3 -m mlx_lm.server --model {spec.hf_repo} "
                f"--port {spec.port} --host 127.0.0.1 "
                f">> {log_path} 2>&1 &"
            )

        logger.info("Starting %s (port %d, %s)...", key, spec.port, spec.hf_repo)
        subprocess.Popen(cmd, shell=True, executable="/bin/bash")

        # Poll until ready or timeout
        deadline = time.time() + STARTUP_TIMEOUT_S
        while time.time() < deadline:
            time.sleep(POLL_INTERVAL_S)
            if self._is_alive(key):
                elapsed = STARTUP_TIMEOUT_S - (deadline - time.time())
                logger.info("✅ %s ready in %.0fs (port %d)", key, elapsed, spec.port)
                return True

        logger.error("❌ %s failed to start within %ds", key, STARTUP_TIMEOUT_S)
        return False

    def _unload_server_sync(self, key: str) -> bool:
        """Stop the MLX server — try /unload endpoint first, then kill PID."""
        spec = MODEL_CATALOG.get(key)
        if not spec:
            return False

        if not self._port_open(spec.port):
            return True  # already gone

        # Try graceful /unload (mlx_vlm supports this, lm_lenient does not)
        if spec.server_type == "vlm":
            try:
                import json as _json
                url = f"http://127.0.0.1:{spec.port}/unload"
                req = urllib.request.Request(
                    url, data=b"{}",
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                urllib.request.urlopen(req, timeout=5)
                logger.info("Unloaded %s via /unload endpoint", key)
                return True
            except Exception as e:
                logger.debug("VLM /unload failed for %s: %s — falling back to kill", key, e)

        # Fallback: kill process by port
        try:
            result = subprocess.run(
                ["lsof", "-ti", f":{spec.port}"],
                capture_output=True, text=True,
            )
            pids = result.stdout.strip().split()
            for pid in pids:
                if pid:
                    subprocess.run(["kill", pid], capture_output=True)
            if pids:
                logger.info("Killed %s (port %d, PIDs: %s)", key, spec.port, pids)
            return True
        except Exception as e:
            logger.error("Failed to kill %s: %s", key, e)
            return False

    # ── Public API ────────────────────────────────────────────────────────────

    async def ensure_loaded(self, key: str) -> bool:
        """
        Guarantee model is ready to serve requests.
        Idempotent — if already loaded, returns True instantly.
        Waits for any in-progress prefetch before re-launching.
        """
        self._last_used[key] = time.time()

        if self._is_alive(key):
            return True

        # If a prefetch is running, wait for it instead of double-launching
        task = self._prefetch_tasks.get(key)
        if task and not task.done():
            logger.info("Waiting for in-progress prefetch of %s...", key)
            try:
                await task
                if self._is_alive(key):
                    return True
            except Exception:
                pass

        # Take the lock and launch
        async with self._locks[key]:
            if self._is_alive(key):
                return True  # someone else started it while we waited
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, self._start_server_sync, key)

    async def prefetch(self, key: str):
        """
        Start loading in the background. Non-blocking.
        Called while the PREVIOUS model is generating to hide load latency.
        Respects budget — won't prefetch if it won't fit.
        """
        if self._is_alive(key):
            return  # already up

        task = self._prefetch_tasks.get(key)
        if task and not task.done():
            return  # already prefetching

        # Budget check before launching
        spec = MODEL_CATALOG.get(key)
        if spec:
            registry  = get_registry()
            available = self._profile.model_budget_gb - registry.get_loaded_memory_gb()
            if spec.memory_gb > available + 1.0:  # +1GB tolerance
                logger.info(
                    "Skip prefetch %s — budget tight (%.1fGB free, need %.1fGB)",
                    key, available, spec.memory_gb,
                )
                return

        async def _do_prefetch():
            async with self._locks[key]:
                if not self._is_alive(key):
                    loop = asyncio.get_event_loop()
                    await loop.run_in_executor(None, self._start_server_sync, key)

        logger.info("Prefetching %s in background...", key)
        self._prefetch_tasks[key] = asyncio.create_task(_do_prefetch())

    async def maybe_unload(self, key: str):
        """
        Free memory if tier policy says to and model is idle.

        POWER_USER/PRO/SERVER: no-op (0 = never unload)
        STANDARD:              unload if idle > 10 min
        MINIMAL:               unload if idle > 1 min
        """
        threshold_min = self._profile.unload_idle_after_minutes
        if threshold_min == 0:
            return  # POWER_USER / PRO / SERVER — never unload

        last_ts       = self._last_used.get(key, 0)
        idle_min      = (time.time() - last_ts) / 60.0

        if idle_min < threshold_min:
            return  # still warm

        if not self._is_alive(key):
            return  # already gone

        logger.info(
            "Unloading %s — idle %.1f min (threshold %.1f min)", key, idle_min, threshold_min
        )
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._unload_server_sync, key)

    async def get_memory_pressure(self) -> float:
        """
        Returns 0.0–1.0.
        0.0 = nothing loaded, 1.0 = at budget ceiling.
        Above 0.8 consider proactive unload of idle models.
        """
        registry = get_registry()
        await registry.refresh_async()
        loaded = registry.get_loaded_memory_gb()
        return min(1.0, loaded / max(1.0, self._profile.model_budget_gb))

    def get_tier(self) -> HardwareTier:
        return self._tier

    def get_budget_gb(self) -> float:
        return self._profile.model_budget_gb


# ── Background idle monitor ───────────────────────────────────────────────────

async def _idle_monitor_loop(manager: "ModelLifecycleManager", interval_s: int = 300):
    """
    Runs every `interval_s` seconds (default 5 min).
    Calls maybe_unload on all on-demand models from the tier profile.
    Resident models are never touched.
    """
    profile = manager._profile
    on_demand = profile.on_demand_models
    if not on_demand or profile.unload_idle_after_minutes == 0:
        logger.info("Idle monitor: no on-demand models or unload disabled — exiting")
        return

    logger.info(
        "Idle monitor started — checking %s every %ds (threshold=%.0fmin)",
        on_demand, interval_s, profile.unload_idle_after_minutes,
    )
    while True:
        await asyncio.sleep(interval_s)
        for key in on_demand:
            try:
                await manager.maybe_unload(key)
            except Exception as exc:
                logger.warning("Idle monitor error for %s: %s", key, exc)


def start_idle_monitor(loop: Optional[asyncio.AbstractEventLoop] = None) -> asyncio.Task:
    """
    Spawn the background idle-monitor coroutine.
    Call once at application startup (after the event loop is running).
    Returns the Task so the caller can cancel it on shutdown.
    """
    manager = get_lifecycle()
    coro    = _idle_monitor_loop(manager)
    if loop:
        task = loop.create_task(coro)
    else:
        task = asyncio.create_task(coro)
    logger.info("Idle monitor task scheduled")
    return task


# ── Module-level singleton ────────────────────────────────────────────────────

_lifecycle: Optional[ModelLifecycleManager] = None


def get_lifecycle() -> ModelLifecycleManager:
    global _lifecycle
    if _lifecycle is None:
        _lifecycle = ModelLifecycleManager()
    return _lifecycle


if __name__ == "__main__":
    import asyncio
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s: %(message)s")

    async def _test():
        lc = get_lifecycle()
        print(f"Tier:       {lc.get_tier().value}")
        print(f"Budget:     {lc.get_budget_gb()}GB")
        pressure = await lc.get_memory_pressure()
        print(f"Pressure:   {pressure:.0%}")
        print("\nChecking liveness:")
        from Core.resource_config import MODEL_CATALOG
        for key in MODEL_CATALOG:
            alive = lc._is_alive(key)
            print(f"  {key}: {'✅ alive' if alive else '❌ offline'}")

    asyncio.run(_test())
