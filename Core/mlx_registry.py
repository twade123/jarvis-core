"""
MLX Model Registry — live status of all running MLX server instances.

Polls health endpoints to determine what's loaded, what's available,
and how much memory is in use. Lightweight — no side effects, just reads.
"""
import asyncio
import json
import logging
import time
import urllib.request
from dataclasses import dataclass, field
from typing import Dict, Optional

from Core.resource_config import MODEL_CATALOG, ModelSpec, get_health_endpoint

logger = logging.getLogger(__name__)


@dataclass
class ServerStatus:
    key: str
    port: int
    alive: bool
    model_loaded: str = ""                  # HF repo name reported by server
    last_inference_memory_gb: float = 0.0   # peak_memory from last inference response
    last_check_ts: float = field(default_factory=time.time)
    last_inference_ts: float = 0.0
    error: str = ""


class MLXRegistry:
    """
    Global, non-singleton registry of MLX server health.
    Call refresh() or refresh_async() to update state.
    """

    HEALTH_TIMEOUT = 3  # seconds per port check

    def __init__(self):
        self._cache: Dict[str, ServerStatus] = {}

    # ── Internal ──────────────────────────────────────────────────────────────

    def _check_one(self, spec: ModelSpec) -> ServerStatus:
        """Synchronous health check for a single server."""
        key  = spec.key
        port = spec.port

        # Try the canonical endpoint, then fallback
        # lm_lenient uses mlx_lm.server which has /v1/ prefix (same as lm)
        if spec.server_type == "vlm":
            endpoints = ["/models", "/v1/models"]
        else:  # "lm" or "lm_lenient"
            endpoints = ["/v1/models", "/models"]

        for ep in endpoints:
            try:
                url = f"http://127.0.0.1:{port}{ep}"
                req = urllib.request.Request(url)
                with urllib.request.urlopen(req, timeout=self.HEALTH_TIMEOUT) as resp:
                    data = json.loads(resp.read())
                    model_id = (data.get("data") or [{}])[0].get("id", "")
                    return ServerStatus(key=key, port=port, alive=True,
                                       model_loaded=model_id,
                                       last_check_ts=time.time())
            except Exception:
                continue

        return ServerStatus(key=key, port=port, alive=False,
                           last_check_ts=time.time(), error="not responding")

    # ── Public API ────────────────────────────────────────────────────────────

    def refresh(self) -> Dict[str, ServerStatus]:
        """Check all servers synchronously. Updates internal cache. Returns copy."""
        for key, spec in MODEL_CATALOG.items():
            status = self._check_one(spec)
            self._cache[key] = status
        return dict(self._cache)

    async def refresh_async(self) -> Dict[str, ServerStatus]:
        """Async wrapper — runs checks in thread pool so we don't block the event loop."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.refresh)

    def get_status(self, key: str) -> Optional[ServerStatus]:
        return self._cache.get(key)

    def is_alive(self, key: str) -> bool:
        s = self._cache.get(key)
        return bool(s and s.alive)

    def get_loaded_memory_gb(self) -> float:
        """Sum of expected memory for all currently responding servers."""
        total = 0.0
        for key, status in self._cache.items():
            if status.alive:
                spec = MODEL_CATALOG.get(key)
                if spec:
                    total += spec.memory_gb
        return total

    def get_available_budget_gb(self, budget_gb: float) -> float:
        return max(0.0, budget_gb - self.get_loaded_memory_gb())

    def get_alive_keys(self) -> list:
        return [k for k, s in self._cache.items() if s.alive]

    def get_alive_ports(self) -> Dict[int, str]:
        """Returns {port: model_key} for all live servers."""
        result = {}
        for key, status in self._cache.items():
            if status.alive:
                spec = MODEL_CATALOG.get(key)
                if spec:
                    result[spec.port] = key
        return result

    def update_inference_memory(self, key: str, peak_memory_gb: float):
        """
        Called after each inference to record actual GPU memory used.
        MLX returns peak_memory in responses — use that for accurate accounting.
        """
        if key in self._cache:
            self._cache[key].last_inference_memory_gb = peak_memory_gb
            self._cache[key].last_inference_ts = time.time()

    def summary(self) -> str:
        """Human-readable status for logging / dashboard."""
        if not self._cache:
            return "  (no status — call refresh() first)"
        lines = []
        for key, status in self._cache.items():
            spec = MODEL_CATALOG.get(key)
            mem  = f"{spec.memory_gb:.1f}GB" if spec else "?GB"
            seat = f" [{spec.board_seat}]" if spec and spec.board_seat else ""
            if status.alive:
                lines.append(f"  ✅ {key}{seat} (port {status.port}): {mem} loaded")
            else:
                lines.append(f"  ❌ {key}{seat} (port {status.port}): offline")
        total = self.get_loaded_memory_gb()
        lines.append(f"  ──")
        lines.append(f"  Total loaded: {total:.1f}GB")
        return "\n".join(lines)

    def to_dict(self) -> dict:
        """Serializable snapshot for dashboard API."""
        return {
            key: {
                "alive": s.alive,
                "port": s.port,
                "model_loaded": s.model_loaded,
                "memory_gb": MODEL_CATALOG[key].memory_gb if key in MODEL_CATALOG else 0,
                "board_seat": MODEL_CATALOG[key].board_seat if key in MODEL_CATALOG else "",
                "last_inference_memory_gb": s.last_inference_memory_gb,
                "last_check_ts": s.last_check_ts,
            }
            for key, s in self._cache.items()
        }


# ── Module-level singleton ────────────────────────────────────────────────────

_registry: Optional[MLXRegistry] = None


def get_registry() -> MLXRegistry:
    global _registry
    if _registry is None:
        _registry = MLXRegistry()
    return _registry


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    r = get_registry()
    print("Checking all MLX servers...\n")
    r.refresh()
    print(r.summary())
    print(f"\nLoaded memory: {r.get_loaded_memory_gb():.1f}GB")
    print(f"Alive ports:   {r.get_alive_ports()}")
