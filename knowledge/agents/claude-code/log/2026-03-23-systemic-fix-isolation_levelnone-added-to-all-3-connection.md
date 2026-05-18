---
type: correction
created: 2026-03-23
tags: [database, sqlite, isolation-level, v2-migration, root-cause, CRITICAL, systemic-fix]
agent: log
decomposed_from: agents/claude-code/log/2026-03.md
---

## 🔧 SYSTEMIC FIX: isolation_level=None added to ALL 3 connection layers + 60+ direct sqlite3.connect calls
**Date:** 2026-03-23T06:22:35
**Type:** correction
**Tags:** database, sqlite, isolation-level, v2-migration, root-cause, CRITICAL, systemic-fix

> [!warning] CORRECTION
> Root cause of persistent DB locking after V2 migration: db_helper.py (V2 pool) and db_connection.py (shared context manager) both created connections WITHOUT isolation_level=None. Python sqlite3 default mode starts implicit transactions on ANY DML. If that DML fails (e.g., query hits missing table), the implicit transaction holds a RESERVED lock FOREVER. db_pool.py was fixed last night but db_helper.py and db_connection.py were not. Since V2 moved snipe/watch/trade tables to trading_forex.db (served by db_helper.py), every snipe operation went through the broken path. FIX: (1) db_helper.py: added isolation_level=None, busy_timeout=30000, wal_autocheckpoint=0, synchronous=NORMAL. (2) db_connection.py: added isolation_level=None to both readonly and write connect calls, removed implicit commit (autocommit handles it), added explicit BEGIN IMMEDIATE in quick_write/quick_write_many. (3) 60+ direct sqlite3.connect() calls across floor_chat, flight_recorder, position_guardian, scout_profiles, intelligence_store, intelligence_rules_engine, intelligence_package_builder, full_confluence_scorer, cot_data_fetcher, trade_outcome_fetcher, setup_revenue, validation_analyst, validator_reconciliation, training_collector, snipe_cleanup, trade_logger, knowledge_store, trade_auditor, manual_trade_store, workspace_provisioner, broker_credentials, outcome_reconciler, journey_tracker, historical_data, setup_learner, setup_discovery, validator_training_extractor, trading_cycle, ta_summary_fetcher, trading_eod_analysis, vision_validator, comment_protocol, lightweight_registrar, manual_trade_analyzer, tuning_config, scout_retrospective, mirofish_backtest, cycle_health_check, team_setup, backtester/trading_db.py. Remaining unfixed: test files, scripts/, and backtester batch tools (cold path only, not run during live trading).
