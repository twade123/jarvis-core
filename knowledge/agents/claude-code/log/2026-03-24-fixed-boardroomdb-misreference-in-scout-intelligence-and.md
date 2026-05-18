---
type: correction
created: 2026-03-24
tags: [boardroom, database, api, snipes, watch_suggestions, data-pipeline]
agent: log
decomposed_from: agents/claude-code/log/2026-03.md
---

## 🔧 Fixed boardroom.db misreference in scout-intelligence and performance API endpoints
**Date:** 2026-03-24T07:31:52
**Type:** correction
**Tags:** boardroom, database, api, snipes, watch_suggestions, data-pipeline

> [!warning] CORRECTION
> trading_api_routes.py lines 5425 and 5760 set BOARDROOM_DB/BOARD_DB to _TRADING_FOREX_DB (v2/trading_forex.db) instead of actual Database/boardroom.db. watch_suggestions (snipes) are written to boardroom.db by watch_manager but the scout-intelligence and performance endpoints were reading from trading_forex.db — showing 0 active snipes and empty leaderboard. Same root cause as the scout_alerts mismatch: DB consolidation left some endpoints pointing to the wrong database.
