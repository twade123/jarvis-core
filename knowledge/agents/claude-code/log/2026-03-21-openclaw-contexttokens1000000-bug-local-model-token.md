---
type: discovery
created: 2026-03-21
tags: [openclaw, compaction, token-tracking, mlx, bug]
agent: log
decomposed_from: agents/claude-code/log/2026-03.md
---

## 💡 OpenClaw contextTokens=1000000 bug — local model token tracking broken, always falls back to Anthropic
**Date:** 2026-03-21T17:05:07
**Type:** discovery
**Tags:** openclaw, compaction, token-tracking, mlx, bug

> [!tip] DISCOVERY
> Configured OpenClaw with MLX 35B on port 11502 (openai-completions API). MLX returns correct usage data (verified via curl). But OpenClaw reports contextTokens=1000000 and totalTokens=41935 after one hello message. System prompt alone is ~30K tokens (12K bootstrap files + 7K skills list + 7.5K tool schemas + 3K overhead). Even with 65K KV cache, OpenClaw thinks context is full because it reads max_position_embeddings (262144) not actual usage. Result: immediate compaction -> fallback to Anthropic. Root cause is in OpenClaw's token tracking for openai-completions providers, not in our config. Need to investigate OpenClaw source: how contextTokens is set for non-Anthropic providers.
