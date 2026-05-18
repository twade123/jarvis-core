---
type: discovery
created: 2026-03-22
tags: [scout, watch-manager, snipe, conditions, price-levels]
agent: log
decomposed_from: agents/claude-code/log/2026-03.md
---

## 💡 Scout watch_manager check_conditions needs price-level and BB bandwidth condition types for new validator snipe format
**Date:** 2026-03-22T20:34:38
**Type:** discovery
**Tags:** scout, watch-manager, snipe, conditions, price-levels

> [!tip] DISCOVERY
> watch_manager.py check_conditions() (line 853) evaluates snipe conditions against live data. Currently supports: ema_fan_state, bb_expanding, momentum_candles, ema_velocity, ema_price_near_e100, close_vs_ema, has_reversal_pattern. Missing: price_level conditions (entry zone 0.9098-0.9103), price_invalidation (above 0.9115), bb_bandwidth threshold (target 0.00350+). The validator now produces specific prices in snipe triggers that the scout can't evaluate yet. Also: the auto-snipe fallback (P3 in floor_chat) generates generic conditions instead of using the validator's specific ones. Priority: add price_in_zone, price_above, price_below, bb_bandwidth fields to check_conditions.
