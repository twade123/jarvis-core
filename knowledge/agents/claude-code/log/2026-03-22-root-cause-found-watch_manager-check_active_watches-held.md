---
type: correction
created: 2026-03-22
tags: [database, root-cause, watch-manager, transaction, lock, commit]
agent: log
decomposed_from: agents/claude-code/log/2026-03.md
---

## 🔧 Root cause found: watch_manager check_active_watches held RESERVED lock across entire loop — missing per-watch commit + missing rollback on exception
**Date:** 2026-03-22T20:43:09
**Type:** correction
**Tags:** database, root-cause, watch-manager, transaction, lock, commit

> [!warning] CORRECTION
> check_active_watches() iterated over all watches doing UPDATE statements through db_pool connection. The implicit transaction was only committed at end of loop (line 1706), holding RESERVED lock for entire duration. If any watch check failed mid-loop, exception handler caught it but left prior watches' transaction OPEN — permanent lock. Fix: (1) conn.commit() after each watch's progress update, (2) conn.rollback() in exception handler. This was the real reason 'database is locked' prevented snipe INSERTs.
