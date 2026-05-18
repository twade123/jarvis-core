---
type: correction
created: 2026-03-22
tags: [database, v2-migration, root-cause, workspace-tasks, conversations-db, CRITICAL]
agent: log
decomposed_from: agents/claude-code/log/2026-03.md
---

## 🔧 V2 migration audit: 6 DB mismatches found — trading_api_routes queried workspace_tasks from conversations.db instead of workspaces.db
**Date:** 2026-03-22T23:03:07
**Type:** correction
**Tags:** database, v2-migration, root-cause, workspace-tasks, conversations-db, CRITICAL

> [!warning] CORRECTION
> Full audit mapped 10 databases, 45+ tables, 34 code connections. Found 6 critical mismatches where code queries tables that don't exist in the connected DB. Root cause of permanent DB lock: dashboard endpoint queries workspace_tasks from conversations.db → table doesn't exist → implicit transaction holds RESERVED lock → all writes blocked. Fix: workspace_tasks/comments queries routed to v2/workspaces.db, agent_communications queries use correct V2 plural table name and column names. Also set isolation_level=None on all direct connections to prevent future implicit transaction locks.
