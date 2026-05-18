---
type: improvement
created: 2026-03-20
tags: [openclaw, architecture, cost, local-model, acpx]
agent: log
decomposed_from: agents/claude-code/log/2026-03.md
---

## 📈 OpenClaw redesign: trevor-9b primary + acpx Claude Code ACP + Max plan
**Date:** 2026-03-20T09:18:29
**Type:** improvement
**Tags:** openclaw, architecture, cost, local-model, acpx

Switched primary from trevor-base 35B to trevor-9b 9B (vision-capable, ~16GB). Enabled acpx plugin for Claude Code ACP delegation — all coding goes through Max plan (was k/month API). Validator + compaction stay on per-token API. Memory baseline ~34GB leaving 30GB headroom.
