---
type: correction
created: 2026-03-22
tags: [database, sqlite, root-cause, path-case, lock, CRITICAL]
agent: log
decomposed_from: agents/claude-code/log/2026-03.md
---

## 🔧 ACTUAL root cause: path case mismatch — '/jarvis/' vs '/Jarvis/' caused SQLite lock manager to treat same DB as two separate databases
**Date:** 2026-03-22T21:13:46
**Type:** correction
**Tags:** database, sqlite, root-cause, path-case, lock, CRITICAL

> [!warning] CORRECTION
> floor_chat.py used lowercase '~/jarvis/Database/boardroom.db' while db_pool.py used uppercase '~/Jarvis/Database/boardroom.db'. macOS filesystem is case-insensitive (same inode) but SQLite lock manager uses path STRING to coordinate locks. Different strings = no in-process lock coordination = BEGIN IMMEDIATE waits forever because SQLite doesn't know the connections are to the same file. Fix: one character change (j→J). Previous fixes (busy_timeout, BEGIN IMMEDIATE, wal_autocheckpoint, per-watch commit, teardown hooks) were all band-aids because the lock coordination was fundamentally broken by the path mismatch.
