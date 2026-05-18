---
type: improvement
created: 2026-03-23
tags: [watch-manifest, watch-trigger, fallback-builder, snipe-context]
agent: log
decomposed_from: agents/claude-code/log/2026-03.md
---

## 📈 Built watch_manifest, watch_trigger, watch_for from available data when validator returns null
**Date:** 2026-03-23T12:31:41
**Type:** improvement
**Tags:** watch-manifest, watch-trigger, fallback-builder, snipe-context

> [!success] IMPROVEMENT
> The validator includes these keys in its JSON but sets them to null — it puts all analysis in reasoning and re_entry_conditions instead. Fix: when null, build from available data. watch_manifest: constructed from fishing_line (entry zone, direction, time limit), trigger_conditions (from re_entry_conditions with progress_pct), and confidence metadata. watch_trigger: built from price_target_entry + first 3 condition descriptions. watch_for: falls back to first 300 chars of reasoning. confidence_trajectory: defaults to 'stable'. These fields are now always populated in the snipe context.
