---
type: correction
created: 2026-03-11
tags: [chart-submission, user_watch, user_chat, floor_chat, trading_cycle, early-exit, dispatcher]
agent: trevor
decomposed_from: agents/trevor/learnings.md
---

## 🔧 Chart submission flow fix (5th time): __SUBMIT_CHART__ now bypasses MLX dispatcher in floor_chat.py; user_chat cycles also early-exit in trading_cycle.py
**Date:** 2026-03-11T15:47:00
**Type:** correction
**Workspace:** workspaces/forex-trading-team
**Tags:** chart-submission, user_watch, user_chat, floor_chat, trading_cycle, early-exit, dispatcher

Root cause: _orchestrator_decide (Qwen MLX model) could route __SUBMIT_CHART__ to run_cycle action. The image override at line 576-577 was the only safety net — if it failed, a user_chat cycle fired the FULL pipeline including orchestrator. Fix 1 (floor_chat.py): added _is_chart_submission_msg check BEFORE dispatcher call — __SUBMIT_CHART__ messages are hardcoded to action=ask_validator, dispatcher never runs. Fix 2 (trading_cycle.py): expanded early exit to cover BOTH user_watch AND user_chat triggered_by values, so even if a user_chat cycle fires it stops after the validator. Neither the orchestrator nor execution agents should EVER run on a user chart submission.
