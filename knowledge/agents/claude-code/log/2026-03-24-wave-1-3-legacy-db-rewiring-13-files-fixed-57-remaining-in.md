---
type: correction
created: 2026-03-24
tags: [migration, v2, legacy-rewire, ui-stack-debugger]
agent: log
decomposed_from: agents/claude-code/log/2026-03.md
---

## 🔧 Wave 1-3 legacy DB rewiring: 13 files fixed, 57 remaining in broader scan
**Date:** 2026-03-24T14:05:33
**Type:** correction
**Tags:** migration, v2, legacy-rewire, ui-stack-debugger

> [!warning] CORRECTION
> Fixed 4 runtime failures (setup_learner, validator_training_extractor, scout_profiles, tuning_config pointing to trevor_database.db), 6 stale docstrings, 3 test files. Re-scan revealed 57 more refs in Handler/, Jarvis_Agent_SDK/, scripts/, backtester/. Biggest: database_directory.py (11), jarvis_orchestrated_intelligence.py (5), trading_api_routes.py (2 boardroom.db). journeys.db was fine — diagnostic had wrong table name (journey_tracking vs journey_steps).
