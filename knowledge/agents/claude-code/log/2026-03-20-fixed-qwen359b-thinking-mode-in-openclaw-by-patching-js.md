---
type: correction
created: 2026-03-20
tags: [openclaw, ollama, qwen3.5, think, patch, 9b]
agent: log
decomposed_from: agents/claude-code/log/2026-03.md
---

## 🔧 Fixed qwen3.5:9b thinking mode in OpenClaw by patching JS bundle to inject think:false
**Date:** 2026-03-20T11:03:05
**Type:** correction
**Tags:** openclaw, ollama, qwen3.5, think, patch, 9b

Root cause: OpenClaw's Ollama driver (createOllamaStreamFn in reply-Bm8VrLQh.js) only passes temperature/num_predict/num_ctx to Ollama — no mechanism exists to pass think:false. Qwen3.5 defaults to thinking mode, taking 2m52s per response and timing out OpenClaw (2min limit). Fix: patched the bundle to add think:false to the top-level request body. Confirmed: responses now 2-4s, no thinking chain. Backup at reply-Bm8VrLQh.js.backup. IMPORTANT: must re-apply after OpenClaw npm updates.
