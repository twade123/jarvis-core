"""
Model Server Manager — starts, stops, and routes to MLX model servers.

Key design: multiple seats share servers. The manager tracks which servers
are loaded and only starts/stops at the server level, never per-seat.
"""

import os
import sys
import socket
import logging
import subprocess
import threading
import time
from typing import Dict, List, Optional, Set

logger = logging.getLogger("ModelServerManager")

# Import seat registry — try package import first, fall back to direct import
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
try:
    from Handler.seat_registry import MODEL_SERVERS, SEATS, get_servers_for_seats
except ModuleNotFoundError:
    from seat_registry import MODEL_SERVERS, SEATS, get_servers_for_seats


class ModelServerManager:
    """Manages MLX model server lifecycle for boardroom seats."""

    def __init__(self):
        self._active_servers: Set[str] = set()  # server IDs currently running
        self._lock = threading.Lock()
        self._mlx_server_script = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "scripts", "mlx_vlm_server_with_tools.py"
        )

    def port_open(self, port: int, host: str = "127.0.0.1") -> bool:
        """Quick TCP check — returns True if port is accepting connections."""
        try:
            with socket.create_connection((host, port), timeout=1.0):
                return True
        except OSError:
            return False

    def get_server_status(self) -> Dict[str, bool]:
        """Return {server_id: is_running} for all servers."""
        return {
            sid: self.port_open(srv["port"])
            for sid, srv in MODEL_SERVERS.items()
        }

    def active_memory_gb(self) -> float:
        """Return total memory used by currently running servers."""
        return sum(
            MODEL_SERVERS[sid]["memory_gb"]
            for sid in self._active_servers
            if sid in MODEL_SERVERS
        )

    def start_servers_for_seats(self, seat_ids: List[str],
                                 push_fn=None) -> Dict[str, bool]:
        """
        Start the MLX servers needed for the given seats.
        Returns {server_id: started_ok} for each server that was started.
        Servers already running are skipped (no-op).
        """
        needed = get_servers_for_seats(seat_ids)
        results = {}

        for server_id, server_cfg in needed.items():
            port = server_cfg["port"]
            if self.port_open(port):
                # Already running
                with self._lock:
                    self._active_servers.add(server_id)
                results[server_id] = True
                continue

            # Start the server
            model_path = self._resolve_model_path(server_cfg["model"])
            if not model_path:
                logger.error(f"Model path not found for server {server_id}: {server_cfg['model']}")
                results[server_id] = False
                continue

            try:
                # Pick the correct server script based on model type
                server_type = server_cfg.get("server_type", "lm")
                scripts_dir = os.path.join(
                    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                    "scripts"
                )
                if server_type == "lm":
                    cmd = [sys.executable, "-m", "mlx_lm.server",
                           "--model", model_path,
                           "--port", str(port), "--host", "127.0.0.1"]
                elif server_type == "lm_lenient":
                    lenient_script = os.path.join(scripts_dir, "mlx_lm_server_lenient.py")
                    cmd = [sys.executable, lenient_script,
                           "--model", model_path,
                           "--port", str(port), "--host", "127.0.0.1"]
                else:  # vlm / vlm_with_tools
                    cmd = [sys.executable, self._mlx_server_script,
                           "--model", model_path,
                           "--port", str(port), "--host", "127.0.0.1"]

                logger.info(f"Starting server {server_id} ({server_type}): {' '.join(cmd[:4])}...")
                subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

                # Wait for server to become ready (up to 30s)
                ready = self._wait_for_port(port, timeout=30)
                if ready:
                    with self._lock:
                        self._active_servers.add(server_id)
                    logger.info(f"Server {server_id} started on port {port} "
                                f"({server_cfg['model']}, ~{server_cfg['memory_gb']}GB)")
                    if push_fn:
                        push_fn("boardroom_update", {
                            "type": "server_ready", "server_id": server_id, "port": port
                        })
                results[server_id] = ready
            except Exception as e:
                logger.error(f"Failed to start server {server_id}: {e}")
                results[server_id] = False

        return results

    def stop_servers_for_seats(self, seat_ids: List[str],
                                keep_chair: bool = True) -> List[str]:
        """
        Stop servers that are ONLY used by the given seats.
        If other active seats also use a server, it stays running.
        Returns list of server IDs that were stopped.
        """
        servers_to_check = get_servers_for_seats(seat_ids)
        stopped = []

        for server_id in servers_to_check:
            if keep_chair and server_id == "A":
                continue  # Never stop the chair server

            # Check if any other active meeting seats use this server
            # (This will be checked by Meeting Broker in Phase 2 —
            #  for now, just stop it)
            port = MODEL_SERVERS[server_id]["port"]
            self._kill_port(port)
            with self._lock:
                self._active_servers.discard(server_id)
            stopped.append(server_id)
            logger.info(f"Stopped server {server_id} (port {port})")

        return stopped

    def stop_all(self, keep_chair: bool = True):
        """Stop all board servers. Optionally keep the chair server running."""
        for server_id, srv in MODEL_SERVERS.items():
            if keep_chair and server_id == "A":
                continue
            self._kill_port(srv["port"])
            with self._lock:
                self._active_servers.discard(server_id)
        logger.info(f"All board servers stopped (keep_chair={keep_chair})")

    def resolve_endpoint(self, seat_id: str) -> Optional[Dict]:
        """
        Resolve a seat to its server endpoint.
        Returns {"port": int, "model": str, "server_type": str} or None.
        """
        seat = SEATS.get(seat_id.upper())
        if not seat:
            return None
        server = MODEL_SERVERS.get(seat["server_id"])
        if not server:
            return None
        if not self.port_open(server["port"]):
            return None
        return {
            "port": server["port"],
            "model": server["model"],
            "server_type": server.get("server_type", "lm"),
        }

    def _resolve_model_path(self, model_id: str) -> Optional[str]:
        """Resolve a model ID to its local path in HuggingFace cache."""
        hf_cache = os.path.expanduser("~/.cache/huggingface/hub")
        model_dir = os.path.join(hf_cache, f"models--{model_id.replace('/', '--')}")
        if not os.path.isdir(model_dir):
            return None
        # Find the latest snapshot
        snapshots_dir = os.path.join(model_dir, "snapshots")
        if not os.path.isdir(snapshots_dir):
            return model_dir
        snaps = sorted(os.listdir(snapshots_dir))
        if snaps:
            return os.path.join(snapshots_dir, snaps[-1])
        return model_dir

    def _wait_for_port(self, port: int, timeout: int = 30) -> bool:
        """Wait for a port to become available."""
        deadline = time.time() + timeout
        while time.time() < deadline:
            if self.port_open(port):
                return True
            time.sleep(0.5)
        return False

    def _kill_port(self, port: int):
        """Kill any process listening on the given port."""
        try:
            result = subprocess.run(
                ["lsof", "-ti", f":{port}"],
                capture_output=True, text=True, timeout=5
            )
            pids = result.stdout.strip().split('\n')
            for pid in pids:
                if pid.strip():
                    subprocess.run(["kill", pid.strip()], timeout=5)
        except Exception as e:
            logger.warning(f"Failed to kill port {port}: {e}")
