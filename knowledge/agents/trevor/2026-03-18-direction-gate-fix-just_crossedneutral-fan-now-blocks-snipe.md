---
type: improvement
created: 2026-03-18
tags: [trading, direction_gate, just_crossed, snipe_direct, watch, regime_change, trading_cycle]
agent: trevor
decomposed_from: agents/trevor/learnings.md
---

## 📈 Direction gate fix: just_crossed+neutral fan now blocks snipe execution (prevents stale watch firing into regime change)
**Date:** 2026-03-18T09:59:01
**Type:** improvement
**Workspace:** workspaces/forex-trading-team
**Tags:** trading, direction_gate, just_crossed, snipe_direct, watch, regime_change, trading_cycle

Watch #1497 AUD_JPY BUY was created March 17 16:32 on a valid bullish retracement thesis. 20 hours later at 12:14 March 18, the 5th condition (bb_expanding) fired and the trade executed. By that time the EMA fan had flipped to just_crossed+neutral — the trend was reversing. The old direction gate only blocked if fan_direction == 'bearish'. At the exact moment it fired, direction was 'neutral' (cross was happening but not yet confirmed bearish). Trade opened BUY into a bearish cross, hit SL at -.99, then AUD_JPY dropped another 21 pips. Fix: added just_crossed_neutral check — if fan_state is 'just_crossed' or 'forming' AND fan_direction is not bullish/bearish (neutral/empty), treat as conflict for any directional trade. Logged as 'just_crossed+neutral fan (regime shift)'. AUD_JPY 2026-03-18 #1635 would have been blocked by this rule.

**Evidence:** Watch #1497 conditions all met at 12:14. Scout scan at 12:12 showed fan_state=just_crossed, fan_direction=neutral. Old gate: _bearish_fan = False (neutral != bearish), conflict = False, trade placed. New gate: _just_crossed_neutral = True, conflict = True, trade blocked. AUD_JPY dropped to 112.539 (-12.3p) from entry 112.720 by 12:49.
