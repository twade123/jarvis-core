---
type: improvement
created: 2026-03-24
tags: [v2-migration, phase6, database]
agent: log
decomposed_from: agents/claude-code/log/2026-03.md
---

## 📈 Phase 6: Rewired all Jarvis_Agent_SDK files from legacy DBs to V2 db_helper
**Date:** 2026-03-24T10:37:03
**Type:** improvement
**Tags:** v2-migration, phase6, database

> [!success] IMPROVEMENT
> Migrated 5 files: boardroom_connector.py (removed DatabaseConnectionPool, rewired 15+ journey_tracking calls to v2_connection('journeys')), jarvis_orchestrator.py (ConversationHistoryManager to v2_connection('conversations')), jarvis_orchestrated_intelligence.py (model_storage and handler_analysis to v2_connection('intelligence')), database_directory.py (model_metrics, model_storage, boardroom tables to v2_connection('intelligence')), conversation_aggregator.py (_get_database_connection now routes through v2 pool). token_manager.py, workflow_tools.py, common_utils.py, import_helper.py had no DB-level changes needed (only BoardRoom object refs).
