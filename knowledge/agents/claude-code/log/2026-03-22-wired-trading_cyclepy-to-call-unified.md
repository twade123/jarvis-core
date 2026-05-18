---
type: improvement
created: 2026-03-22
tags: [trading-cycle, validator, unified, wiring]
agent: log
decomposed_from: agents/claude-code/log/2026-03.md
---

## 📈 Wired trading_cycle.py to call unified handler_data_validator instead of _agent_task
**Date:** 2026-03-22T15:26:57
**Type:** improvement
**Tags:** trading-cycle, validator, unified, wiring

> [!success] IMPROVEMENT
> Replaced validator_task text string + _agent_task('validator') calls with _unified_params dict + _call_unified_validator(). Data assembly stays in trading_cycle (forex-specific), handler is generic. Bridge function _call_unified_validator() lazy-loads handler singleton, runs async evaluate_with_full_context synchronously, wraps result in {response: json, tool_calls: []} format for compatibility with downstream code. Old _v4_images_for_call building is now dead code (handler loads images via vault).
