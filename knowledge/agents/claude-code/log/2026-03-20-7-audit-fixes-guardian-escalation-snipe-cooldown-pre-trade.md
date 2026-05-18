---
type: improvement
created: 2026-03-20
tags: [log]
agent: log
decomposed_from: agents/claude-code/log/2026-03.md
---

## 📈 7 audit fixes: guardian escalation, snipe cooldown, pre-trade gate, watch dedup, TTL, stale watches, H4 gate
**Date:** 2026-03-20T12:36:56
**Type:** improvement

Implemented all 7 fixes from 2026-03-13 trade audit. Fix1: score_threat() now adds +25 when trade is 10+min old, YELLOW zone, never profitable → pushes stuck losers to RED. Fix2: Added pair_last_close cooldown check in the watch-check API route loop (line ~3152 in trading_api_routes.py) before priority=high bypass — was the missing gate that let 8 snipes fire in 20min. Fix3: Guardian pre-trade gate in snipe_direct path (step 5b) calls score_threat() on M15 candles before place_market_order — blocks YELLOW entries from opening. Fix4: Max-2-per-instrument dedup in create_watch() — expires oldest watch (expired_dedup) before inserting new one when count >= 2. Fix5: watch_ttl_hours=0.0 in config was triggering 9999-year expiry — now defaults to 8h when ttl<=0. Fix6: SQL ran directly — expired 10 stale peak_progress>=1.0 watches. Fix7: H4 alignment gate in check_active_watches() queries flight_recorder scout_scan fan_direction — blocks BUY watches when H4 is bearish and vice versa.
