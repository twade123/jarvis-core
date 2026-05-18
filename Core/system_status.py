"""
System Status API — real-time platform health for the dashboard.

Provides:
  get_status()          → full JSON snapshot (tier, models, memory, scheduler)
  status_router()       → FastAPI/Starlette router you can mount at /api/system

Usage (standalone):
    python3 Core/system_status.py
"""
import asyncio
import subprocess
import time
from typing import Dict, Any

from Core.resource_config import (
    MODEL_CATALOG, detect_hardware_tier, get_tier_profile,
)
from Core.mlx_registry import get_registry


# ── Status snapshot ───────────────────────────────────────────────────────────

async def get_status() -> Dict[str, Any]:
    """Return a complete platform status snapshot — safe to call frequently."""
    tier    = detect_hardware_tier()
    profile = get_tier_profile()
    registry = get_registry()
    await registry.refresh_async()

    # RAM from vm_stat
    ram_free_gb = _get_free_ram_gb()
    total_gb    = _get_total_ram_gb()
    used_gb     = round(total_gb - ram_free_gb, 1)
    pressure    = round(used_gb / max(1, total_gb), 3)

    # Model breakdown
    models = {}
    loaded_gb = 0.0
    for key, spec in MODEL_CATALOG.items():
        status = registry._cache.get(key)
        alive = status.alive if status else False
        mem   = MODEL_CATALOG[key].memory_gb if alive else 0.0
        if alive:
            loaded_gb += mem
        role = "resident" if key in profile.resident_models else "on_demand"
        models[key] = {
            "port":       spec.port,
            "alive":      alive,
            "role":       role,
            "memory_gb":  round(mem, 1),
            "hf_repo":    spec.hf_repo,
            "board_seat": spec.board_seat,
        }

    budget_used_pct = round(loaded_gb / max(1, profile.model_budget_gb) * 100, 1)

    # Trading status (is a trading cycle running?)
    trading_active = _check_port_alive(8766)   # serve_ui / trading dashboard

    # Idle monitor running?
    idle_monitor = _idle_monitor_running()

    return {
        "timestamp":      time.time(),
        "tier":           tier.value,
        "ram": {
            "total_gb":   round(total_gb, 1),
            "used_gb":    used_gb,
            "free_gb":    round(ram_free_gb, 1),
            "pressure":   pressure,        # 0.0–1.0
            "danger":     pressure > 0.90,
        },
        "models": {
            "loaded_gb":      round(loaded_gb, 1),
            "budget_gb":      profile.model_budget_gb,
            "budget_used_pct": budget_used_pct,
            "detail":         models,
        },
        "services": {
            "trading_ui":      trading_active,
            "idle_monitor":    idle_monitor,
            "mlx_alive":       [k for k, v in models.items() if v["alive"]],
            "mlx_offline":     [k for k, v in models.items() if not v["alive"]],
        },
        "tier_config": {
            "resident_models":      profile.resident_models,
            "on_demand_models":     profile.on_demand_models,
            "unload_after_min":     profile.unload_idle_after_minutes,
            "max_parallel":         profile.max_parallel_sessions,
        },
    }


# ── FastAPI/Starlette router (optional — only if fastapi is available) ────────

def make_status_router():
    """
    Returns a FastAPI APIRouter with GET /status.
    Mount with: app.include_router(make_status_router(), prefix="/api/system")
    """
    try:
        from fastapi import APIRouter
        router = APIRouter()

        @router.get("/status")
        async def system_status():
            return await get_status()

        @router.get("/health")
        async def health_check():
            """Lightweight liveness probe — no registry refresh."""
            tier = detect_hardware_tier()
            return {"ok": True, "tier": tier.value, "ts": time.time()}

        return router
    except ImportError:
        return None


# ── Low-level helpers ─────────────────────────────────────────────────────────

def _get_total_ram_gb() -> float:
    try:
        out = subprocess.check_output(["sysctl", "-n", "hw.memsize"], stderr=subprocess.DEVNULL)
        return int(out.strip()) / (1024 ** 3)
    except Exception:
        return 0.0


def _get_free_ram_gb() -> float:
    """Reads vm_stat for free + inactive pages (macOS)."""
    try:
        out = subprocess.check_output(["vm_stat"], stderr=subprocess.DEVNULL).decode()
        free = inactive = 0
        page = 16384
        for line in out.splitlines():
            if "Pages free:" in line:
                free = int(line.split(":")[1].strip().rstrip("."))
            elif "Pages inactive:" in line:
                inactive = int(line.split(":")[1].strip().rstrip("."))
        return (free + inactive) * page / (1024 ** 3)
    except Exception:
        return 0.0


def _check_port_alive(port: int) -> bool:
    import socket
    with socket.socket() as s:
        return s.connect_ex(("127.0.0.1", port)) == 0


def _idle_monitor_running() -> bool:
    """Check if asyncio idle monitor task is active in current event loop."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            tasks = [t for t in asyncio.all_tasks(loop) if "_idle_monitor" in str(t.get_coro())]
            return len(tasks) > 0
        return False
    except Exception:
        return False


# ── Standalone ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import json

    async def _run():
        status = await get_status()
        print(json.dumps(status, indent=2))

    asyncio.run(_run())
