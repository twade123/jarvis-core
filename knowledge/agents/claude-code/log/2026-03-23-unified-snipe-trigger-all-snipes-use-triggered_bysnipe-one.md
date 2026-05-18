---
type: improvement
created: 2026-03-23
tags: [snipe, triggered-by, unified, snipe-direct]
agent: log
decomposed_from: agents/claude-code/log/2026-03.md
---

## 📈 Unified snipe trigger: all snipes use triggered_by='snipe' — one path, no source distinctions
**Date:** 2026-03-23T10:19:49
**Type:** improvement
**Tags:** snipe, triggered-by, unified, snipe-direct

> [!success] IMPROVEMENT
> Replaced all scout_snipe/user_watch/user_chat triggered_by values with single 'snipe' across trading_cycle.py, trading_api_routes.py, trade_scout.py. A snipe is a snipe regardless of whether it came from scout, user chart submission, or trading cycle. When conditions are met → snipe_direct path → place_market_order(). No full pipeline re-run. Removed conditional branching based on snipe source. One trigger value, one execution path.
