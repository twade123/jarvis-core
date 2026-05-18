---
type: improvement
created: 2026-03-24
tags: [learning_integrator, trade_auditor, guardian, flight_recorder, closed_loop]
agent: log
decomposed_from: agents/claude-code/log/2026-03.md
---

## 📈 Wired guardian flight data into learning loop - trade_auditor.py + learning_integrator.py enhanced
**Date:** 2026-03-24T20:50:09
**Type:** improvement
**Tags:** learning_integrator, trade_auditor, guardian, flight_recorder, closed_loop

> [!success] IMPROVEMENT
> trade_auditor.py: Added _get_guardian_actions() and _get_guardian_phases() methods that query flight_log for guardian_action and trade_phase stages. Audit results now include guardian_actions, guardian_phases, guardian_sl_moves, guardian_tp_moves counts. learning_integrator.py: Added 5 new learning patterns to _extract_guardian_learnings(): (1) trail_too_aggressive - 3+ SL moves + loss, (2) ratchet_tp_success - TP extended + win >5p, (3) breakeven_clip - BE move + loss <3p, (4) phase_oscillation - 6+ phase changes + loss, (5) full_action_timeline - always writes complete SL/TP history. All patterns write to vault via record_agent_learning.
