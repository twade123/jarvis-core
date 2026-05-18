---
type: note
created: 2026-03-20
tags: [openclaw, compaction, anthropic, billing, config]
agent: log
decomposed_from: agents/claude-code/log/2026-03.md
---

## 📝 OpenClaw compaction model changed to anthropic/claude-sonnet-4-6 — watch API costs
**Date:** 2026-03-20T07:48:35
**Type:** note
**Tags:** openclaw, compaction, anthropic, billing, config

Changed in ~/.openclaw/openclaw.json: agents.defaults.compaction.model was 'ollama/trevor-base', now 'anthropic/claude-sonnet-4-6'. Reason: local model cannot reliably handle compaction because OpenClaw streams tool calls and Ollama's streaming doesn't emit tool_calls delta chunks — compaction silently fails every time with local model. Compaction fires when context hits softThresholdTokens (60000) or forceFlushTranscriptBytes (200kb). Each compaction run = 1 Claude Sonnet API call. Watch billing for unexpected frequency. If compaction fires too often, consider raising softThresholdTokens or forceFlushTranscriptBytes. To revert if costs are high: change compaction.model back to ollama/trevor-base (accept that compaction will be unreliable). Also changed: requestTimeout:120000 on trevor-base, params:{think:false} at model level, apiKey:'ollama-local' (was 'ollama' — fixes subagent credential bug), subagents.model.primary:'ollama/trevor-base' explicitly set.
