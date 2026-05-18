---
type: correction
created: 2026-03-20
tags: [openclaw, ollama, trevor-base, config, fix]
agent: log
decomposed_from: agents/claude-code/log/2026-03.md
---

## 🔧 OpenClaw + Ollama trevor-base config fixes — 3 root causes found and patched
**Date:** 2026-03-20T07:38:56
**Type:** correction
**Tags:** openclaw, ollama, trevor-base, config, fix

Root causes of trevor-base failing in OpenClaw: (1) Streaming+tool calling bug — OpenClaw sends stream:true but Ollama streaming doesnt emit tool_calls chunks, tools silently fail. Fixed by switching to native Ollama API (api: ollama, no /v1). (2) Qwen3.5 think mode emits output in reasoning field not content — OpenClaw sees empty content, falls back to Claude. Fixed by adding params:{think:false} at model level in openclaw.json. (3) Compaction was set to ollama/trevor-base — compaction needs tool calls + file writes in streaming, always fails with local model. Fixed: changed compaction model to anthropic/claude-sonnet-4-6. Also added requestTimeout:120000 to prevent cold-start timeouts. Subagent credential bug (#43945) still pending: apiKey:'ollama' treated as marker, not propagated to subagents — workaround is changing to 'ollama-local'. Plan: use trevor-9b for subagents once tested.
