---
type: note
created: 2026-03-24
tags: [db_pool, row_factory, sqlite3, pattern]
agent: log
decomposed_from: agents/claude-code/log/2026-03.md
---

## 📝 Critical pattern: db_pool get_trading_forex() does NOT set row_factory - callers must set it themselves
**Date:** 2026-03-24T20:50:40
**Type:** note
**Tags:** db_pool, row_factory, sqlite3, pattern

> [!info] NOTE
> db_pool.py connections are thread-local and reused. row_factory is NOT set by default. Any caller that needs sqlite3.Row must do conn.row_factory = sqlite3.Row after getting the connection. Also watch for aliased imports: trading_api_routes.py imports sqlite3 as _psq, so sqlite3.Row must be written as _psq.Row. This caused a silent NameError that hid the entire performance panel.
