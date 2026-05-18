---
type: improvement
created: 2026-03-21
tags: [openclaw, ollama, mlx, compaction, token-counting]
agent: log
decomposed_from: agents/claude-code/log/2026-03.md
---

## 📈 Eliminated Ollama from serving path — MLX servers provide accurate token counts for OpenClaw compaction
**Date:** 2026-03-21T15:52:08
**Type:** improvement
**Tags:** openclaw, ollama, mlx, compaction, token-counting

> [!success] IMPROVEMENT
> Ollama returned inaccurate/missing token counts (prompt_tokens=0), breaking OpenClaw compaction timing. MLX servers on ports 11500-11503 return accurate usage data. Updated mlx_lm_server_lenient.py: removed strict=False patch (no longer needed in mlx_lm 0.31.1), kept KV cache cap patch (still needed). Upgraded mlx-lm 0.30.7→0.31.1, transformers 4.57.6→5.3.0. Removed Ollama fallback from distillation_engine.py. GGUF pipeline kept cold for future non-Apple deployment. Compaction settings for 16K KV cache: reserveTokens=4096, keepRecentTokens=6000, memoryFlush.softThresholdTokens=2000.
