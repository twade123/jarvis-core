---
type: correction
created: 2026-03-20
tags: [position-guardian, trailing-stop, profit-protection, dynamic-sl, e21, bug-fix, audit-2026-03-20-phase2]
agent: log
decomposed_from: agents/claude-code/log/2026-03.md
---

## 🔧 Audit Fix 10/10: Tighter profit protection — E21 trailing stop for trending markets
**Date:** 2026-03-20T16:00:02
**Type:** correction
**Tags:** position-guardian, trailing-stop, profit-protection, dynamic-sl, e21, bug-fix, audit-2026-03-20-phase2

agents/position_guardian.py dynamic SL logic: When unrealized profit reaches +8 pips AND the E21 EMA is available in a trending/continuing market state, the trailing stop anchor now switches from E55±5 pips to E21±3 pips. This creates a much tighter profit lock once a trade has proven itself.

Root cause: Trade #1930 (EUR_USD) peaked at +13.8 pips profit but the loose E55±5p trailing stop gave it all back, closing at -0.6 pips. The E55 anchor was too far from price in a trending move, allowing a full reversal through profit back into loss. With E21±3p, the SL would have been ~8-10 pips from entry once profit hit +8p, locking in the majority of the move.

The switch is conditional on market state (trending/continuing) to avoid whipsaws in ranging conditions where E21 proximity would cause premature exits.

**Evidence:** Trade #1930: peaked +13.8p, closed -0.6p with E55±5p. With E21±3p: would have locked +8-10p. Net improvement: ~9-11 pips saved on this single trade.
