---
type: discovery
created: 2026-03-20
tags: [validator, chart-quality, input-quality, key-insight, audit-2026-03-20-phase3]
agent: log
decomposed_from: agents/claude-code/log/2026-03.md
---

## 💡 Validator works perfectly with Tim's annotated charts — input problem, not intelligence
**Date:** 2026-03-20T20:00:05
**Type:** discovery
**Tags:** validator, chart-quality, input-quality, key-insight, audit-2026-03-20-phase3

Critical insight from Phase 3 audit: the validator is NOT broken. When given Tim's manually annotated charts with proper EMA fan state, BB positioning, candle pattern identification, RSI context, and retracement status, the validator produces correct CONFIRM/SKIP decisions with proper reasoning. The entire validation failure chain traces back to the TA agent delivering inadequate input.

This reframes the problem from "validator is too strict" to "TA agent isn't giving the validator what it needs to do its job." The validator's job is synthesis and judgment — it cannot synthesize what it doesn't receive.

**Evidence:** Validator correctly confirms on Tim's manual charts. Rejects on TA's raw number output. Delta: input quality, not model capability.
