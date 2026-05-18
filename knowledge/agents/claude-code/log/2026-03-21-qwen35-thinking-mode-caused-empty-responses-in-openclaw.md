---
type: correction
created: 2026-03-21
tags: [openclaw, qwen, thinking, mlx, compaction, fix]
agent: log
decomposed_from: agents/claude-code/log/2026-03.md
---

## 🔧 Qwen3.5 thinking mode caused empty responses in OpenClaw — disabled via --chat-template-args
**Date:** 2026-03-21T17:39:54
**Type:** correction
**Tags:** openclaw, qwen, thinking, mlx, compaction, fix

> [!warning] CORRECTION
> Qwen3.5-35B defaults to thinking mode where chain-of-thought goes in 'reasoning' field and answer in 'content'. With limited max_tokens, thinking exhausts the budget and content returns empty. OpenClaw only reads content field, sees empty response, silently fails. Fix: --chat-template-args '{"enable_thinking":false}' on mlx_lm server startup. Also found root cause of contextTokens=1000000: agents.defaults.contextTokens was not set, causing fallback to DEFAULT_CONTEXT_TOKENS. Fix: add contextTokens: 131072 to agents.defaults in openclaw.json.
