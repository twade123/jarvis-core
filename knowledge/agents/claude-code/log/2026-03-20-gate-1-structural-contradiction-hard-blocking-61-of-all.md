---
type: correction
created: 2026-03-20
tags: [gate-1, fan-state, retracement, structural-contradiction, audit-2026-03-20-phase3-gate1]
agent: log
decomposed_from: agents/claude-code/log/2026-03.md
---

## 🔧 Gate 1 structural contradiction — hard-blocking 61% of all cycles, killing retracement setups
**Date:** 2026-03-20T21:00:00
**Type:** correction
**Tags:** gate-1, fan-state, retracement, structural-contradiction, audit-2026-03-20-phase3-gate1

Gate 1 (fan state filter) was hard-blocking 61% of all cycles (22 out of 36). Root cause: a structural contradiction between Gate 1 and Gate 2. Gate 2 rewards E100 retest with +15 points (the fishing line setup), but Gate 1 hard-blocked peaked and contracting fan states before the cycle could ever reach Gate 2's scoring. This killed the fishing line setup before it could be evaluated — the exact setup the system was designed to find.

27 high-quality retracement signals (story_score >= 40, named entry_type) were being killed by Gate 1's blanket fan-state block.

**Fix 1:** Added retracement override path in Gate 1. Conditions: is_retracement=true + fan_ordered=true + story_score >= 40 + named entry_type (not "none"). When all four conditions are met, the cycle bypasses Gate 1's fan-state block and proceeds to Gate 2 for proper scoring.

**Fix 2:** Widened bars_since_cross threshold from 20 bars (5 hours) to 30 bars (7.5 hours). The original 20-bar window was too tight — valid retracement setups that developed over 5-7 hours were being rejected as "too old" when the cross was still structurally relevant.

**Guards kept:** Low-quality retracements (story_score < 40 or entry_type="none") are still blocked by Gate 1. The override only applies to signals with sufficient confluence and a classified entry pattern.

**Evidence:** 22/36 cycles blocked at Gate 1 (61%). 27 high-quality retracement signals killed. Gate 2 E100 retest +15pts unreachable due to Gate 1 block. Post-fix: retracement override path + bars_since_cross 20→30.
