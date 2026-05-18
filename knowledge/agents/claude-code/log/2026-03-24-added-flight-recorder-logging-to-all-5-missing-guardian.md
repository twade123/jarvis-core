---
type: improvement
created: 2026-03-24
tags: [flight_recorder, guardian, position_guardian, set_trade_orders, audit]
agent: log
decomposed_from: agents/claude-code/log/2026-03.md
---

## 📈 Added flight recorder logging to all 5 missing guardian set_trade_orders call sites in position_guardian.py
**Date:** 2026-03-24T20:50:00
**Type:** improvement
**Tags:** flight_recorder, guardian, position_guardian, set_trade_orders, audit

> [!success] IMPROVEMENT
> Guardian was making SL/TP modifications without recording them to flight log. Added FlightStage.GUARDIAN_ACTION logging at: (1) failsafe_floor_sl ~line 1460, (2) ratchet_tp_extend ~line 1605, (3) exhaustion_partial_floor ~line 2347, (4) retrace_trail_e100 ~line 2399, (5) fan_failure_sl_tighten ~line 2624. Each records action name, old_sl/tp, new_sl/tp, pnl_pips, and contextual data. This enables post-trade auditing of every guardian decision.
