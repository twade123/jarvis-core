---
type: improvement
created: 2026-03-23
tags: [snipe, watch-manager, conditions, mirofish-removal, validator]
agent: log
decomposed_from: agents/claude-code/log/2026-03.md
---

## 📈 Snipe quality alignment: 8 new condition types + MiroFish removal + regex extraction for price zones
**Date:** 2026-03-23T08:02:59
**Type:** improvement
**Tags:** snipe, watch-manager, conditions, mirofish-removal, validator

> [!success] IMPROVEMENT
> Fix 1: Added price_zone, price_above/below, invalidation_level, bb_bandwidth, bb_squeeze_break, ema_cross_below/above to watch_manager VALID_FIELDS and check_conditions(). Enhanced parse_suggestions() with regex for price zones, invalidation levels, EMA crosses, BB squeeze breaks from validator text. Updated floor_chat.py to use parse_suggestions instead of keyword fallback. Fix 4: Removed MiroFish from intelligence_rules_engine (Rules 2+3 deleted, 7 rules remain), intelligence_package_builder (to_mirofish_seed removed), validation_analyst (Layer 2 MiroFish removed, now 2-layer context). EUR_CHF test: same validator text now extracts 5 structured conditions instead of 2 generic + text blob.
