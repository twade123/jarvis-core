---
type: improvement
created: 2026-03-23
tags: [parse-suggestions, price-extraction, snipe-conditions, watch-manager]
agent: log
decomposed_from: agents/claude-code/log/2026-03.md
---

## 📈 parse_suggestions now merges price-level conditions from validator text into structured conditions
**Date:** 2026-03-23T09:32:01
**Type:** improvement
**Tags:** parse-suggestions, price-extraction, snipe-conditions, watch-manager

> [!success] IMPROVEMENT
> Fixed parse_suggestions() early return at line 285 that skipped regex extraction when re_entry_conditions existed. Now after building structured conditions, also scans reasoning+watch_trigger+watch_for text for: price_zone (entry at X-Y), invalidation_level (invalidation above/below X), ema_cross_below/above (E21 crosses E55), bb_squeeze_break. Only adds conditions not already in structured list. Test: EUR_CHF validator response with 4 structured + text containing prices → 8 total conditions (4 structured + 4 text-extracted: price_zone 0.9120-0.9128, invalidation 0.9095, ema_cross_above, bb_squeeze_break).
