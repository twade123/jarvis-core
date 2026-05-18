---
type: correction
created: 2026-03-24
tags: [trading_api_routes, performance, db_pool, NameError, TRADE_LOG_DB]
agent: log
decomposed_from: agents/claude-code/log/2026-03.md
---

## 🔧 Fixed performance panel missing from Team Intelligence - 3 bugs in trading_api_routes.py
**Date:** 2026-03-24T20:49:45
**Type:** correction
**Tags:** trading_api_routes, performance, db_pool, NameError, TRADE_LOG_DB

> [!warning] CORRECTION
> Bug 1: sqlite3.Row NameError on line 5985 - sqlite3 imported as _psq but code used sqlite3.Row, fixed to _psq.Row. Bug 2: TRADE_LOG_DB undefined variable on line 6029 - legacy variable never defined after DB migration, replaced with get_trading_forex() from db_pool. Bug 3: _build_session_compare() still referenced TRADE_LOG_DB - switched to db_pool internally, removed trade_log_db_path parameter. All three bugs caused the performance endpoint to silently fail (caught by except block), hiding the admin panel entirely.
