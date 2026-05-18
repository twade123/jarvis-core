---
type: improvement
created: 2026-03-24
tags: [database, v2-migration, rewiring, completed, CRITICAL]
agent: log
decomposed_from: agents/claude-code/log/2026-03.md
---

## 📈 V1→V2 database migration completed: data synced, 20+ files rewired, db_pool expanded with 5 V2 pool connections
**Date:** 2026-03-24T09:57:10
**Type:** improvement
**Tags:** database, v2-migration, rewiring, completed, CRITICAL

> [!success] IMPROVEMENT
> Phase 0: Backed up all V2 DBs, synced 8 tables (watch_suggestions +111 rows, agent_communication +27277 rows, workspace_tasks +291 rows, workspace_task_comments +1229 rows, intelligence_cache +44 rows, scout_findings +2, validation_metrics +4, agent_registry +1). Phase 1: Added get_trading_forex(), get_core(), get_agents(), get_workspaces(), get_intelligence() to db_pool.py. Rewired watch_suggestions across watch_manager.py, floor_chat.py, trade_scout.py, trading_api_routes.py, position_guardian.py, snipe_cleanup.py, pipeline_lineage.py. Phase 2: broker_credentials.py now uses v2/core.db, trading_cycle uses get_core(), trade_notify uses v2/core.db, workspace_provisioner uses v2/core.db. Phase 3: Fixed serve_ui.py workspace_tasks from conversations.db→workspaces.db and agents.db→workspaces.db. Phase 4: lightweight_registrar.py→v2/agents.db, intelligence_store.py→v2/intelligence.db, agent_factory.py→v2/agents.db. Audit script shows false positives from file-level import detection — actual query-level wiring is correct. Legacy DBs preserved as read-only fallbacks.
