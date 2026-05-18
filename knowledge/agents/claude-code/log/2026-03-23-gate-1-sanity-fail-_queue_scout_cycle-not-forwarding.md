---
type: correction
created: 2026-03-23
tags: [gate1, fan_direction, scout_context, data-plumbing, trading_cycle]
agent: log
decomposed_from: agents/claude-code/log/2026-03.md
---

## 🔧 Gate 1 SANITY FAIL: _queue_scout_cycle not forwarding alert_type, is_retracement, triggered_by to scout_context
**Date:** 2026-03-23T06:43:54
**Type:** correction
**Tags:** gate1, fan_direction, scout_context, data-plumbing, trading_cycle

> [!warning] CORRECTION
> EUR_CHF M15 showed ordered bullish fan (E21>E55>E100) but Gate 1 killed with 'fan_direction='' with no qualifying alert type'. Root cause: _queue_scout_cycle() in trade_scout.py built scout_context from market_snapshot but never copied alert_type, is_retracement, or triggered_by from the alert. Gate 1 sanity check in trading_cycle.py needs these fields to allow RETRACEMENT/CRITERIA_MET bypass. Secondary: fan_direction could be None when ema_separation returns _empty dict (missing key). Fix: (1) Forward alert_type, is_retracement, triggered_by in _queue_scout_cycle. (2) Fallback to ema_data for fan_direction. (3) Add fan_direction/fan_ordered to _empty dict in ema_separation.py. Key pattern: when gates check bypass conditions using fields from context dicts, ALL data forwarding hops must include those fields.
