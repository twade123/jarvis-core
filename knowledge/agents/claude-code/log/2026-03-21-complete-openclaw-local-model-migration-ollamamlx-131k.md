---
type: improvement
created: 2026-03-21
tags: [openclaw, migration, mlx, ollama, compaction, qwen, architecture]
agent: log
decomposed_from: agents/claude-code/log/2026-03.md
---

## 📈 Complete OpenClaw local model migration: Ollama→MLX, 131K context, compaction fixed, thinking disabled
**Date:** 2026-03-21T17:45:17
**Type:** improvement
**Tags:** openclaw, migration, mlx, ollama, compaction, qwen, architecture

> [!success] IMPROVEMENT
> Full migration session 2026-03-21. Changes: (1) Removed Ollama from serving path, MLX 35B on port 11502 is sole backend. (2) Upgraded mlx-lm 0.30.7→0.31.1, transformers 4.57.6→5.3.0, removed strict=False patch (no longer needed). (3) KV cache cap raised to 131072 tokens (10GB, comfortable on 64GB). (4) OpenClaw config: provider=mlx with openai-completions API, contextWindow=131072, agents.defaults.contextTokens=131072 (critical — without this, compaction system defaults to 200K/1M and triggers instantly). (5) Disabled Qwen3.5 thinking mode via --chat-template-args enable_thinking=false (model was returning empty content, only reasoning field). (6) Compaction tuned: reserveTokens=16000, keepRecentTokens=24000, softThresholdTokens=10000. Memory flush at ~80% (105K), compaction at ~88% (115K). (7) Anthropic fallback removed for testing — local model only. (8) GGUF pipeline kept as cold export tool for future non-Apple deployment. (9) Only 35B model needed for OpenClaw (subagents use same model). 9B kept in mlx_servers.sh for boardroom CRO seat but not used by OpenClaw.
