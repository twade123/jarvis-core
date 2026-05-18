---
type: improvement
created: 2026-03-18
tags: [trading, cooldown, snipe, churn, watch, pair_last_close, position_guardian]
agent: trevor
decomposed_from: agents/trevor/learnings.md
---

## 📈 Pair-level 30-min cooldown added — fixes snipe churn where same pair re-fired every 5 min after close
**Date:** 2026-03-18T07:30:04
**Type:** improvement
**Workspace:** workspaces/forex-trading-team
**Tags:** trading, cooldown, snipe, churn, watch, pair_last_close, position_guardian

Root cause of GBP_USD churn (35 queue entries in 3 hours) and EUR_AUD double-loss at 2 AM: the per-watch 15-min cooldown only applied to the specific watch that filled, not to the pair. Other watches on the same pair fired immediately. Fix: added module-level pair_last_close dict in trading_api_routes.py (shared between _fire_snipe_cycle reads and position_guardian writes). Guardian stamps pair_last_close[instrument]=time.time() on every trade close (both primary and fallback watch reset paths). _fire_snipe_cycle checks this before queuing any cycle — if pair closed within 30 min, skip with log. Old per-watch cooldown kept as belt-and-suspenders. Cooldown constant: PAIR_COOLDOWN_SECS=1800.

**Evidence:** 2026-03-18 queue log: GBP_USD had snipe entries at 04:32, 04:37, 04:42, 04:47, 04:52, 04:57, 05:07, 05:12... every 5 min from 4:30 AM to 7:15 AM. EUR_AUD had 30+ snipe entries 01:00-03:00 AM leading to two consecutive full-stop losses ($-15.29 and $-16.20) within 50 minutes on the same setup.
