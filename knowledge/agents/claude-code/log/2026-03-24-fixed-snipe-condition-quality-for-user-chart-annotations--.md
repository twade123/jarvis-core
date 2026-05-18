---
type: improvement
created: 2026-03-24
tags: [watch_manager, snipe_conditions, chart_annotation, regex, parse_suggestions]
agent: log
decomposed_from: agents/claude-code/log/2026-03.md
---

## 📈 Fixed snipe condition quality for user chart annotations - watch_manager.py text extraction + live snipe 1692 patched
**Date:** 2026-03-24T20:50:33
**Type:** improvement
**Tags:** watch_manager, snipe_conditions, chart_annotation, regex, parse_suggestions

> [!success] IMPROVEMENT
> User chart annotation snipes only got 3 generic conditions (ema_fan_state, bb_expanding, watch_trigger text blob) while scout snipes got 7 structured ones. Root cause: PRIORITY 1 path in parse_suggestions() kept LLM re_entry_conditions as-is without extracting numeric values from watch_trigger text. Fix in watch_manager.py: Added regex extraction for price_zone, bb_bandwidth threshold, close below/above price levels, and invalidation_level from validator text. Added non-checkable field filter to drop watch_trigger/watch_for/reasoning/note fields. Added _existing_fields.add() after each append to prevent duplicate close conditions. Also patched live snipe 1692 (USD_CHF SELL) directly in DB from 3 generic to 6 specific conditions.
