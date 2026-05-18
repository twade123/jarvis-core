---
type: correction
created: 2026-03-24
tags: [migration, v2, legacy-rewire, complete]
agent: log
decomposed_from: agents/claude-code/log/2026-03.md
---

## 🔧 V1-V2 migration complete: 57→1 legacy refs. All runtime paths, comments, scripts, backtester, SDK, Handler rewired.
**Date:** 2026-03-24T14:12:21
**Type:** correction
**Tags:** migration, v2, legacy-rewire, complete

> [!warning] CORRECTION
> Wave 4 fixed remaining 57 legacy refs: database_directory.py (central registry rewired to V2), prompt_registry.py (boardroom→prompts.db), handler_adapter.py (boardroom→conversations.db), handler_base.py (filename mapping updated), trading_api_routes.py (dead BOARDROOM_DB/BOARD_DB vars removed), 8 backtester scripts, 5 utility scripts, 3 test files. Only intentional backward-compat check remains in jarvis_orchestrated_intelligence.py:4202. Total across all waves: ~40 files modified, 70+ individual edits.
