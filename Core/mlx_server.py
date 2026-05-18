"""
MLX Model Server Manager — Apple Silicon Optimized Inference

Manages MLX-LM model servers for the Trevor Platform.
Each board seat gets a dedicated MLX server instance on a unique port.

Architecture:
  Mac (MLX):    Metal GPU → native inference → OpenAI-compat API
  Server (GPU): vLLM/TGI → CUDA inference → OpenAI-compat API
  
Both expose the same OpenAI-compatible API. LLMRouter doesn't care which backend.

Usage:
    manager = MLXServerManager()
    await manager.start_model("CRO", "mlx-community/Qwen2.5-7B-Instruct-4bit", port=11500)
    await manager.start_model("CTO", "mlx-community/DeepSeek-R1-Distill-Qwen-32B-4bit", port=11501)
    
    # Models stay resident — no swap latency between board member calls
    # LLMRouter routes to localhost:PORT/v1 just like Ollama

    manager.stop_all()
"""

import os
import sys
import json
import time
import signal
import logging
import asyncio
import subprocess
import shutil
from pathlib import Path
from typing import Dict, Optional, List, Tuple
from dataclasses import dataclass, field

logger = logging.getLogger("MLXServer")

# ──────────────────────────────────────────────────────────
# Model Registry — what to serve where
# ──────────────────────────────────────────────────────────

MLX_MODELS = {
    "CRO": {
        "hf_repo": "mlx-community/Qwen2.5-7B-Instruct-4bit",
        "port": 11500,
        "description": "CRO/CDO seat — fast risk analysis, 4-bit quantized",
        "memory_gb": 4.5,
        "speed_est": "~2-4s response",
    },
    "CTO": {
        "hf_repo": "mlx-community/DeepSeek-R1-Distill-Qwen-32B-4bit",
        "port": 11501,
        "description": "CTO seat — deep reasoning, chain-of-thought (upgraded 14B→32B 2026-03-12)",
        "memory_gb": 19.0,
        "speed_est": "~25-45s response",
    },
    "CSO": {
        "hf_repo": "mlx-community/Qwen3-30B-A3B-4bit",
        "port": 11502,
        "description": "CSO seat — strategy, MoE architecture",
        "memory_gb": 20.0,
        "speed_est": "~8-15s response",
    },
    "CDO": {
        # Until trevor-domain is fine-tuned, CDO shares CRO's model
        # After fine-tuning: local path to MLX adapter
        "hf_repo": "mlx-community/Qwen2.5-7B-Instruct-4bit",
        "port": 11503,
        "adapter_path": None,  # Will be set after fine-tuning: ~/jarvis/models/trevor-domain-adapter
        "description": "CDO seat — domain expert (fine-tuned after Phase 8)",
        "memory_gb": 4.5,
        "speed_est": "~2-4s response",
    },
    "Coder": {
        "hf_repo": "mlx-community/Qwen2.5-Coder-32B-Instruct-4bit",
        "port": 11504,
        "description": "Coding/distillation — NOT a board seat, on-demand only",
        "memory_gb": 19.0,
        "speed_est": "~20-40s response",
    },
}

# Memory budget: M1 Max 64GB
# macOS + apps: ~8-10GB
# Available for models: ~54GB
# Resident set: CRO(4.5) + CTO(9) + CSO(20) = 33.5GB — fits easily
# Add CDO(4.5) = 38GB — still fine
# Coder(19) only loaded on-demand — would push to 57GB, tight but possible

MEMORY_BUDGET_GB = 54  # Leave ~10GB for macOS + apps
ALWAYS_RESIDENT = ["CRO", "CTO", "CSO"]  # ~33.5GB — always loaded
ON_DEMAND = ["CDO", "Coder"]  # Loaded when needed, unloaded after


@dataclass
class ModelServer:
    """Tracks a running MLX server process."""
    name: str
    port: int
    hf_repo: str
    process: Optional[subprocess.Popen] = None
    pid: Optional[int] = None
    started_at: Optional[float] = None
    adapter_path: Optional[str] = None
    status: str = "stopped"  # stopped, starting, running, error
    memory_gb: float = 0.0
    request_count: int = 0
    last_request: Optional[float] = None


class MLXServerManager:
    """
    Manages multiple MLX-LM model servers on Apple Silicon.
    
    Each model gets its own HTTP server on a dedicated port.
    All servers expose OpenAI-compatible /v1/chat/completions endpoint.
    LLMRouter in claude_client.py points to these instead of Ollama.
    
    For server deployment, swap this for vLLM/TGI manager with same API.
    """
    
    def __init__(self, model_cache_dir: str = None):
        self.servers: Dict[str, ModelServer] = {}
        self.model_cache_dir = model_cache_dir or os.path.expanduser("~/.cache/huggingface/hub")
        self._total_memory_used = 0.0
        
    def get_memory_usage(self) -> float:
        """Total estimated GPU memory used by running models."""
        return sum(s.memory_gb for s in self.servers.values() if s.status == "running")
    
    def get_available_memory(self) -> float:
        return MEMORY_BUDGET_GB - self.get_memory_usage()
    
    async def start_model(self, name: str, hf_repo: str = None, port: int = None,
                          adapter_path: str = None) -> bool:
        """Start an MLX-LM server for a model.
        
        Args:
            name: Model name (e.g., "CRO", "CTO")
            hf_repo: HuggingFace repo (default: from MLX_MODELS registry)
            port: Port number (default: from MLX_MODELS registry)
            adapter_path: Optional LoRA adapter path for fine-tuned models
            
        Returns:
            True if server started successfully
        """
        config = MLX_MODELS.get(name, {})
        hf_repo = hf_repo or config.get("hf_repo")
        port = port or config.get("port", 11500 + len(self.servers))
        adapter_path = adapter_path or config.get("adapter_path")
        memory_gb = config.get("memory_gb", 5.0)
        
        if not hf_repo:
            logger.error(f"No model repo specified for {name}")
            return False
        
        # Check memory budget
        if self.get_available_memory() < memory_gb:
            logger.warning(f"Not enough memory for {name} ({memory_gb}GB needed, "
                         f"{self.get_available_memory():.1f}GB available)")
            # Try to free on-demand models
            freed = await self._free_on_demand_models(memory_gb)
            if not freed:
                logger.error(f"Cannot free enough memory for {name}")
                return False
        
        # Stop existing server on same name/port
        if name in self.servers and self.servers[name].status == "running":
            await self.stop_model(name)
        
        # Build command
        cmd = [
            sys.executable, "-m", "mlx_lm", "server",
            "--model", hf_repo,
            "--port", str(port),
            "--host", "127.0.0.1",
        ]
        if adapter_path and os.path.exists(adapter_path):
            cmd.extend(["--adapter-path", adapter_path])
        
        logger.info(f"Starting MLX server for {name}: {hf_repo} on port {port}")
        
        try:
            # Start server process
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                preexec_fn=os.setsid,  # New process group for clean shutdown
            )
            
            server = ModelServer(
                name=name,
                port=port,
                hf_repo=hf_repo,
                process=proc,
                pid=proc.pid,
                started_at=time.time(),
                adapter_path=adapter_path,
                status="starting",
                memory_gb=memory_gb,
            )
            self.servers[name] = server
            
            # Wait for server to be ready (poll /v1/models endpoint)
            ready = await self._wait_for_ready(name, timeout=120)
            if ready:
                server.status = "running"
                logger.info(f"✅ {name} server ready on port {port} "
                           f"(~{memory_gb}GB, total used: {self.get_memory_usage():.1f}GB)")
                return True
            else:
                server.status = "error"
                logger.error(f"❌ {name} server failed to start within timeout")
                await self.stop_model(name)
                return False
                
        except Exception as e:
            logger.error(f"Failed to start {name}: {e}")
            return False
    
    async def stop_model(self, name: str) -> bool:
        """Stop a model server."""
        server = self.servers.get(name)
        if not server or not server.process:
            return True
        
        try:
            # Kill the process group
            os.killpg(os.getpgid(server.process.pid), signal.SIGTERM)
            server.process.wait(timeout=10)
        except (ProcessLookupError, subprocess.TimeoutExpired):
            try:
                os.killpg(os.getpgid(server.process.pid), signal.SIGKILL)
            except ProcessLookupError:
                pass
        
        server.status = "stopped"
        server.process = None
        logger.info(f"Stopped {name} server (freed ~{server.memory_gb}GB)")
        return True
    
    async def stop_all(self):
        """Stop all model servers."""
        for name in list(self.servers.keys()):
            await self.stop_model(name)
    
    async def start_resident_models(self) -> Dict[str, bool]:
        """Start all always-resident models (CRO, CTO, CSO)."""
        results = {}
        for name in ALWAYS_RESIDENT:
            results[name] = await self.start_model(name)
        return results
    
    async def ensure_model(self, name: str) -> bool:
        """Ensure a model is running. Start if needed (for on-demand models)."""
        server = self.servers.get(name)
        if server and server.status == "running":
            return True
        return await self.start_model(name)
    
    async def _wait_for_ready(self, name: str, timeout: float = 120) -> bool:
        """Poll until server responds to /v1/models."""
        import urllib.request
        server = self.servers[name]
        start = time.time()
        
        while time.time() - start < timeout:
            try:
                url = f"http://127.0.0.1:{server.port}/v1/models"
                req = urllib.request.Request(url)
                with urllib.request.urlopen(req, timeout=2) as resp:
                    if resp.status == 200:
                        return True
            except Exception:
                pass
            
            # Check if process died
            if server.process and server.process.poll() is not None:
                stderr = server.process.stderr.read().decode() if server.process.stderr else ""
                logger.error(f"{name} process died during startup: {stderr[:500]}")
                return False
            
            await asyncio.sleep(2)
        
        return False
    
    async def _free_on_demand_models(self, needed_gb: float) -> bool:
        """Free on-demand models to make room."""
        for name in ON_DEMAND:
            server = self.servers.get(name)
            if server and server.status == "running":
                await self.stop_model(name)
                if self.get_available_memory() >= needed_gb:
                    return True
        return self.get_available_memory() >= needed_gb
    
    def get_status(self) -> Dict:
        """Get status of all model servers."""
        return {
            "memory_used_gb": self.get_memory_usage(),
            "memory_available_gb": self.get_available_memory(),
            "memory_budget_gb": MEMORY_BUDGET_GB,
            "servers": {
                name: {
                    "status": s.status,
                    "port": s.port,
                    "model": s.hf_repo,
                    "memory_gb": s.memory_gb,
                    "pid": s.pid,
                    "uptime_s": int(time.time() - s.started_at) if s.started_at else 0,
                    "requests": s.request_count,
                    "adapter": s.adapter_path,
                }
                for name, s in self.servers.items()
            }
        }
    
    def get_llm_router_config(self) -> Dict:
        """Generate LLMRouter config for running MLX servers.
        
        Returns config dict that can be used to update claude_client.py's
        OpenAICompatibleClient endpoints.
        """
        config = {}
        for name, server in self.servers.items():
            if server.status == "running":
                config[name] = {
                    "base_url": f"http://127.0.0.1:{server.port}/v1",
                    "model": server.hf_repo.split("/")[-1],
                    "api_key": "mlx-local",  # MLX doesn't need auth
                }
        return config


def get_boardroom_mlx_config() -> Dict:
    """Generate the model mapping for boardroom_template.py when using MLX.
    
    Returns dict mapping board seat → model string for LLMRouter.
    Format: "mlx/<seat>" which LLMRouter resolves to the MLX server port.
    """
    return {
        "CTO": {"model": "mlx/CTO", "endpoint": f"http://127.0.0.1:{MLX_MODELS['CTO']['port']}/v1"},
        "CSO": {"model": "mlx/CSO", "endpoint": f"http://127.0.0.1:{MLX_MODELS['CSO']['port']}/v1"},
        "CRO": {"model": "mlx/CRO", "endpoint": f"http://127.0.0.1:{MLX_MODELS['CRO']['port']}/v1"},
        "CDO": {"model": "mlx/CDO", "endpoint": f"http://127.0.0.1:{MLX_MODELS['CDO']['port']}/v1"},
    }


# ──────────────────────────────────────────────────────────
# CLI interface
# ──────────────────────────────────────────────────────────

async def main():
    """CLI: start resident models and show status."""
    import argparse
    parser = argparse.ArgumentParser(description="MLX Model Server Manager")
    parser.add_argument("action", choices=["start", "stop", "status", "benchmark"],
                       help="Action to perform")
    parser.add_argument("--model", help="Specific model to start/stop")
    parser.add_argument("--all", action="store_true", help="Start all resident models")
    args = parser.parse_args()
    
    manager = MLXServerManager()
    
    if args.action == "start":
        if args.model:
            ok = await manager.start_model(args.model)
            print(f"{'✅' if ok else '❌'} {args.model}")
        elif args.all:
            results = await manager.start_resident_models()
            for name, ok in results.items():
                print(f"{'✅' if ok else '❌'} {name}")
        else:
            print("Specify --model NAME or --all")
    
    elif args.action == "stop":
        if args.model:
            await manager.stop_model(args.model)
        else:
            await manager.stop_all()
        print("Stopped")
    
    elif args.action == "status":
        status = manager.get_status()
        print(json.dumps(status, indent=2))
    
    elif args.action == "benchmark":
        # Quick benchmark: start CRO, send a request, measure time
        print("Starting CRO for benchmark...")
        ok = await manager.start_model("CRO")
        if ok:
            import urllib.request
            port = MLX_MODELS["CRO"]["port"]
            payload = json.dumps({
                "model": "default",
                "messages": [{"role": "user", "content": "What is 2+2? Answer in one word."}],
                "max_tokens": 10,
            }).encode()
            
            start = time.time()
            req = urllib.request.Request(
                f"http://127.0.0.1:{port}/v1/chat/completions",
                data=payload,
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=30) as resp:
                result = json.loads(resp.read())
            elapsed = time.time() - start
            
            answer = result["choices"][0]["message"]["content"]
            print(f"MLX CRO: '{answer}' in {elapsed:.2f}s")
            
            # Compare with Ollama
            payload2 = json.dumps({
                "model": "qwen2.5:7b",
                "messages": [{"role": "user", "content": "What is 2+2? Answer in one word."}],
                "max_tokens": 10,
            }).encode()
            start = time.time()
            req2 = urllib.request.Request(
                "http://127.0.0.1:11434/v1/chat/completions",
                data=payload2,
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req2, timeout=30) as resp:
                result2 = json.loads(resp.read())
            elapsed2 = time.time() - start
            answer2 = result2["choices"][0]["message"]["content"]
            print(f"Ollama CRO: '{answer2}' in {elapsed2:.2f}s")
            print(f"Speedup: {elapsed2/elapsed:.1f}x")
            
            await manager.stop_all()


if __name__ == "__main__":
    asyncio.run(main())
