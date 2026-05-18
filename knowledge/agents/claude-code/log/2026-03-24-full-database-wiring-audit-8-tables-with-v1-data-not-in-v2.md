---
type: discovery
created: 2026-03-24
tags: [database, v2-migration, audit, wiring, split-brain, CRITICAL]
agent: log
decomposed_from: agents/claude-code/log/2026-03.md
---

## 💡 Full database wiring audit: 8 tables with V1 data not in V2, 34 LEGACY+V2 conflicts, 3 active split-brain tables
**Date:** 2026-03-24T09:37:39
**Type:** discovery
**Tags:** database, v2-migration, audit, wiring, split-brain, CRITICAL

> [!tip] DISCOVERY
> Complete audit written to .planning/database_wiring_audit.md. Key findings: (1) watch_suggestions, workspace_tasks, workspace_task_comments are ACTIVELY being written to boardroom.db (V1) while V2 copies are stale — split brain. (2) scout_findings has 3 weeks of V1 writes missing from V2. (3) agent_communication has 27277 rows in V1, 0 in V2. (4) intelligence_cache has 44 rows in V1 not in V2. (5) agent_registry has 130 more entries in V1 than V2. (6) Code reads from wrong DB for: watch_suggestions (boardroom instead of v2/trading_forex), trade_decisions (trevor instead of v2/trading_forex), trading_preferences (users.db instead of v2/core.db), broker_credentials (users.db instead of v2/core.db), intelligence_cache (trevor instead of v2/intelligence.db). Migration plan: Phase 0 sync data, Phase 1 rewire trading, Phase 2 rewire auth, Phase 3 rewire agents/workspaces, Phase 4 rewire intelligence, Phase 5 deprecate legacy. NO CODE CHANGES MADE — map only.
