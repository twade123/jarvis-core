#!/usr/bin/env python3
"""
MLX LM server with KV cache capping.

Patches make_prompt_cache to use max_kv_size=16384 (RotatingKVCache),
capping per-request KV cache at a fixed token window. Without this, the
server accumulates unbounded KVCache objects across requests.

Note: mlx_lm.server has no --max-kv-size CLI argument — the cap must be
patched directly into make_prompt_cache.

Usage: python3 mlx_lm_server_lenient.py --model <path> --port <port>

History:
  - Patch 1 (strict=False) removed — mlx_lm >=0.31.1 loads Qwen3.5 VLM
    weights natively without needing strict=False.
  - Patch 2 (KV cache cap) still required — mlx_lm.server still calls
    make_prompt_cache(model) without max_kv_size.
"""

# ── Patch: cap KV cache at 16384 tokens via RotatingKVCache ──────────────────
# mlx_lm.server calls make_prompt_cache(model) with no max_kv_size, creating
# unbounded KVCache objects that accumulate across requests. Patching here
# forces RotatingKVCache (sliding window, discards oldest tokens) on every call.
import mlx_lm.models.cache as _cache
_original_make_prompt_cache = _cache.make_prompt_cache

_MAX_KV_SIZE = 131072  # tokens; 10GB KV for 35B (2 KV heads), 26GB total on 64GB Mac


def _capped_make_prompt_cache(model, max_kv_size=_MAX_KV_SIZE, **kwargs):
    """Always use RotatingKVCache with a fixed token cap."""
    kwargs['max_kv_size'] = max_kv_size
    return _original_make_prompt_cache(model, **kwargs)


_cache.make_prompt_cache = _capped_make_prompt_cache

# Patch the server's imported reference too (it imports make_prompt_cache
# directly at module level, so we must patch the server module's namespace)
import mlx_lm.server as _server
_server.make_prompt_cache = _capped_make_prompt_cache

# ── Run the standard server — picks up the patch ────────────────────────────
from mlx_lm.server import main
main()
