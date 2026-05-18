---
type: improvement
created: 2026-03-20
tags: [snipe-threshold, setup-type, retracement, breakout, reversal, continuation, audit-2026-03-20-phase3]
agent: log
decomposed_from: agents/claude-code/log/2026-03.md
---

## 📈 Snipe thresholds tuned by setup type
**Date:** 2026-03-20T20:00:08
**Type:** improvement
**Tags:** snipe-threshold, setup-type, retracement, breakout, reversal, continuation, audit-2026-03-20-phase3

Snipe confidence thresholds differentiated by setup type instead of using a single universal threshold:
- Retracement: 0.75 (most common, best-understood setup)
- Breakout: 0.80 (needs momentum confirmation)
- Reversal: 0.85 (counter-trend, higher bar)
- Continuation: 0.90 (trend-following, highest bar to avoid late entries)

Rationale: different setup types have different base rates of success and different risk profiles. A retracement into a trending fan with good R:R deserves a lower bar than a late continuation entry.

**Evidence:** Previous: single threshold for all types. Post-fix: 4 tiers by setup type.
