---
type: correction
created: 2026-03-22
tags: [database, sqlite, connection, lock, root-cause, BEGIN-IMMEDIATE]
agent: log
decomposed_from: agents/claude-code/log/2026-03.md
---

## 🔧 Root cause: Python sqlite3 BEGIN DEFERRED ignores busy_timeout on lock upgrade — fixed with BEGIN IMMEDIATE
**Date:** 2026-03-22T20:31:20
**Type:** correction
**Tags:** database, sqlite, connection, lock, root-cause, BEGIN-IMMEDIATE

> [!warning] CORRECTION
> SQLite 'database is locked' on snipe INSERT was caused by Python's default BEGIN DEFERRED transaction mode. When upgrading from read to write lock, SQLite returns SQLITE_BUSY IMMEDIATELY without respecting busy_timeout. The fix: use isolation_level=None + explicit BEGIN IMMEDIATE, which acquires the write lock upfront and properly waits. Also set wal_autocheckpoint=0 on pooled connections to prevent checkpoint blocking with multiple readers. Also reverted floor_chat to use _call_agent swarm path for validator (manages own connection lifecycle). Per SQLite docs: https://sqlite.org/wal.html
