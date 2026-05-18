---
type: correction
created: 2026-03-24
tags: [scout, trade_decisions, database, check-constraint, data-pipeline]
agent: log
decomposed_from: agents/claude-code/log/2026-03.md
---

## 🔧 Fixed two data pipeline breaks: scout_alerts DB mismatch + trade_decisions CHECK constraint
**Date:** 2026-03-24T07:24:12
**Type:** correction
**Tags:** scout, trade_decisions, database, check-constraint, data-pipeline

> [!warning] CORRECTION
> 1) Scout wrote to trevor_database.db but API read from trading_forex.db — changed _store_alert to use v2/trading_forex.db path. 2) trade_decisions table had CHECK constraints requiring direction IN (long,short) and final_action IN (trade,skip,watchlist,defer) — cycles produced None/hold/watch which violated constraints, silently failing every INSERT since March 20. Fixed by normalizing values before INSERT: direction defaults to 'long' for skips, action maps hold→watchlist.
