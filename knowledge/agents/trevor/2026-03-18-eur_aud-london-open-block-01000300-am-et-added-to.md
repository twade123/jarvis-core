---
type: improvement
created: 2026-03-18
tags: [trading, eur_aud, london_open, session_filter, time_filter, snipe]
agent: trevor
decomposed_from: agents/trevor/learnings.md
---

## 📈 EUR_AUD London open block (01:00–03:00 AM ET) added to _fire_snipe_cycle
**Date:** 2026-03-18T07:30:25
**Type:** improvement
**Workspace:** workspaces/forex-trading-team
**Tags:** trading, eur_aud, london_open, session_filter, time_filter, snipe

EUR_AUD loses violently during London open (01:00-03:00 AM ET). Trades 1534 and 1544 both hit full stops (-21.4p and -22.7p) within 50 minutes during this window on 2026-03-18. Fix: added timezone-aware ET hour check in _fire_snipe_cycle in trading_api_routes.py. If instrument is in _VOLATILE_PAIRS set (currently {'EUR_AUD'}) and current ET time is between 01:00-02:59, snipe is skipped with log. Uses zoneinfo.ZoneInfo('America/New_York'). Exception-safe (fails open = skips block if TZ lookup fails). Easy to expand _VOLATILE_PAIRS or adjust hours if needed.

**Evidence:** 2026-03-18: EUR_AUD P&L breakdown — W:2 L:2 net -$23.91. Both losses were during London open window. Trades 1534 (02:08 close, -$15.29) and 1544 (02:58 close, -$16.20). Both had fan_state=expanding bearish scout signal — correct signal, wrong session timing.
