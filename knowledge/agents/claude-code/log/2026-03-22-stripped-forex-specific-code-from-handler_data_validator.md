---
type: correction
created: 2026-03-22
tags: [validator, handler, generic, correction]
agent: log
decomposed_from: agents/claude-code/log/2026-03.md
---

## 🔧 Stripped forex-specific code from handler_data_validator — handler is now fully generic
**Date:** 2026-03-22T15:14:45
**Type:** correction
**Tags:** validator, handler, generic, correction

> [!warning] CORRECTION
> Removed _fetch_pair_history, _check_elite_playbook, hardcoded forex field names, and trading-specific output format from handler. _build_evaluation_text now formats whatever data the caller provides. _search_vault_for_context uses generic FTS. All domain knowledge (prompts, setups, DB access, snipe building) must come from vault or the caller (trading_cycle). Handler is a dumb pipe: receive data + load vault knowledge + call LLM + return response.
