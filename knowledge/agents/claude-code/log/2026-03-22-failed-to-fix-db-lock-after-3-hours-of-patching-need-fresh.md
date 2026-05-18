---
type: failure
created: 2026-03-22
tags: [database, v2-migration, failure, architecture, CRITICAL]
agent: log
decomposed_from: agents/claude-code/log/2026-03.md
---

## ❌ FAILED to fix DB lock after 3+ hours of patching — need fresh approach with proper V2 migration
**Date:** 2026-03-22T23:30:49
**Type:** failure
**Tags:** database, v2-migration, failure, architecture, CRITICAL

> [!danger] FAILURE
> Root problem: V2 database migration was incomplete. 172+ sqlite3.connect calls across codebase, many pointing to wrong DBs with missing tables. Python sqlite3 default mode leaves implicit transactions on failed queries, causing permanent RESERVED locks. Individual file patches (isolation_level=None, per-watch commits, path case fixes, table name fixes) fixed individual symptoms but new lock sources kept appearing. The real fix requires: (1) Complete V2 migration audit — every query mapped to correct DB, (2) ALL connections use isolation_level=None as standard, (3) Missing tables either created or queries removed, (4) Long-term: PostgreSQL for multi-user. The db_pool.py changes, trading_api_routes fixes, watch_manager commits, and floor_chat path fixes are all valid improvements but don't solve the systemic problem of 172 unprotected connections.
