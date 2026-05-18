---
type: correction
created: 2026-03-23
tags: [database, sqlite, isolation-level, system-wide, root-cause, CRITICAL]
agent: log
decomposed_from: agents/claude-code/log/2026-03.md
---

## 🔧 FULL SYSTEM SWEEP: isolation_level=None added to ALL 283 live sqlite3.connect calls across entire Jarvis codebase
**Date:** 2026-03-23T06:37:46
**Type:** correction
**Tags:** database, sqlite, isolation-level, system-wide, root-cause, CRITICAL

> [!warning] CORRECTION
> Extended the trading team DB lock fix to the entire Jarvis system. Fixed 166 additional calls beyond the 110 trading team calls: Handler/ (30), Jarvis_Agent_SDK/ (22), Database/ (67), serve_ui.py (13), knowledge/ (29), trevor_escalation.py (4), boardroom_data_poller.py (1). Also fixed 3 infrastructure layers: db_helper.py (V2 pool), db_connection.py (shared context manager), db_pool.py (already done). Total: 283 protected connections across all live runtime paths. Only test/script/backtester cold-path calls remain unprotected (39 in trading team). Root cause: Python sqlite3 default mode starts implicit transactions on DML. Failed statements hold RESERVED locks permanently because nothing commits/rollbacks them. isolation_level=None puts connections in autocommit mode — each statement commits immediately, no implicit transactions.
