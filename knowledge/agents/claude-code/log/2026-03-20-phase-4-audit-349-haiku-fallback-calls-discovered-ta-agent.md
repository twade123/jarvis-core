---
type: correction
created: 2026-03-20
tags: [haiku, fallback, ta-agent, cost, model-hygiene, audit-2026-03-20-phase4]
agent: log
decomposed_from: agents/claude-code/log/2026-03.md
---

## 🔧 PHASE 4 AUDIT: 349 Haiku fallback calls discovered — TA agent silently calling paid API
**Date:** 2026-03-20T23:59:00
**Type:** correction
**Tags:** haiku, fallback, ta-agent, cost, model-hygiene, audit-2026-03-20-phase4

TA agent was silently falling back to claude-haiku-4-5 (paid API) when the local 9B model timed out under load. 349 total fallback calls discovered. 169 on March 17 alone. The fallback was invisible — no logging, no alerts, just silent cost. All Haiku fallback paths removed. TA errors now route to swarm; chat path returns an error message instead of escalating to paid API.

**Intentional Haiku usage confirmed:** oanda_data and execution agents correctly use Haiku for tool calling and order placement. These are not fallbacks — they are deliberate use of a fast, cheap model for high-frequency, structured tool calls. Do not remove.
