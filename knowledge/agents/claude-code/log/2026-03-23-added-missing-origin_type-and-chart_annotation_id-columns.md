---
type: correction
created: 2026-03-23
tags: [database, schema, watch-suggestions, boardroom, snipe-creation]
agent: log
decomposed_from: agents/claude-code/log/2026-03.md
---

## 🔧 Added missing origin_type and chart_annotation_id columns to boardroom.db watch_suggestions
**Date:** 2026-03-23T09:01:26
**Type:** correction
**Tags:** database, schema, watch-suggestions, boardroom, snipe-creation

> [!warning] CORRECTION
> Snipe creation was failing with 'table watch_suggestions has no column named origin_type'. The columns existed in trading_forex.db but not boardroom.db. create_watch() in watch_manager.py writes to boardroom.db. Fixed with ALTER TABLE. This was the final blocker preventing snipes from being created on trading cycle WATCH verdicts.
