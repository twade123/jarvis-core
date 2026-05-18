---
type: improvement
created: 2026-03-24
tags: [v2-migration, handler-swarm, database-consolidation]
agent: log
decomposed_from: agents/claude-code/log/2026-03.md
---

## 📈 Rewired handler_swarm.py from get_boardroom()/raw sqlite3 to V2 db_helper connection()
**Date:** 2026-03-24T10:16:10
**Type:** improvement
**Tags:** v2-migration, handler-swarm, database-consolidation

> [!success] IMPROVEMENT
> Replaced 9 raw sqlite3.connect() call sites and removed get_boardroom import. Table routing: agent_activity/agent_communication/agent_performance/agent_registry/journey_steps→connection('agents'), workspaces/workspace_tasks/workspace_agent_assignments→connection('workspaces'), request_journeys/deliberation_history→connection('journeys'). Created deliberation_history table in journeys.db (did not exist in any V2 DB). Removed broken 'from Database.v2 import get_db' call. Set self.db_manager=None since all DB access now goes through v2_connection.
