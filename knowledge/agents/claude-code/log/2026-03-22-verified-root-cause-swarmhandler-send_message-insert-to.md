---
type: correction
created: 2026-03-22
tags: [database, sqlite, root-cause, autocommit, swarm, CRITICAL]
agent: log
decomposed_from: agents/claude-code/log/2026-03.md
---

## 🔧 VERIFIED root cause: SwarmHandler send_message INSERT to missing agent_communication table left implicit transaction open on pooled connection → permanent DB lock
**Date:** 2026-03-22T22:29:40
**Type:** correction
**Tags:** database, sqlite, root-cause, autocommit, swarm, CRITICAL

> [!warning] CORRECTION
> Fixed by setting isolation_level=None (autocommit) on db_pool connections. In Python sqlite3 default mode, a failed INSERT starts an implicit BEGIN that holds a RESERVED lock until commit/rollback. The pool never commits/rollbacks because the exception is caught by the swarm error handler. With autocommit mode, failed statements don't create implicit transactions. The specific trigger: swarm send_message(validator→cycle_orchestrator) → INSERT INTO agent_communication → table doesn't exist → lock held forever → all boardroom.db writes fail.
