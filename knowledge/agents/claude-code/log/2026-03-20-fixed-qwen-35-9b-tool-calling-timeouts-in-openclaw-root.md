---
type: correction
created: 2026-03-20
tags: [openclaw, ollama, qwen, tool-calling, timeout, fix]
agent: log
decomposed_from: agents/claude-code/log/2026-03.md
---

## 🔧 Fixed Qwen 3.5 9B tool calling timeouts in OpenClaw — root cause was 262k context + Ollama non-streaming bug
**Date:** 2026-03-20T15:56:37
**Type:** correction
**Tags:** openclaw, ollama, qwen, tool-calling, timeout, fix

Qwen 3.5 9B was timing out at 120s on every tool call through OpenClaw. Full audit found 4 root causes: (1) Ollama 0.18.2 has a bug where non-streaming tool calls (stream:false) freeze the runner process — the original plan to add streaming:false would have made it WORSE. Streaming mode works correctly. (2) contextWindow:262144 in openclaw.json caused Ollama to allocate 20GB VRAM and 15s cold starts. Created qwen3.5:9b-32k model variant with PARAMETER num_ctx 32768 baked into Modelfile — now 9.7GB VRAM, 4s cold start. (3) Stale trevor-base-keepalive cron job running every 60s against a model that no longer exists, wasting resources — disabled. (4) Invalid requestTimeout key at provider level caused Config invalid warnings — already cleaned by doctor. Fixes applied: primary model changed to ollama/qwen3.5:9b-32k, added Claude fallback, set timeoutSeconds:120, removed streaming:false. Tool calls now complete in 2-4 seconds.
