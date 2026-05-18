---
type: correction
created: 2026-03-23
tags: [snipe, floor-chat, watch-manager, scout, dedup]
agent: log
decomposed_from: agents/claude-code/log/2026-03.md
---

## 🔧 floor_chat.py mass-superseded all watches per pair — fixed to conditions-hash dedup
**Date:** 2026-03-23T14:02:34
**Type:** correction
**Tags:** snipe, floor-chat, watch-manager, scout, dedup

> [!warning] CORRECTION
> floor_chat.py:1098 ran UPDATE SET status=superseded WHERE instrument=? AND status=watching every time a user snipe was created. This killed ALL watching watches for a pair (1021 superseded in DB). Fix: replaced blanket supersede with conditions-hash dedup using existing _compute_conditions_hash() from watch_manager.py. Now only exact-same-criteria watches get replaced. Also added startup revive logic in watch_manager.py to restore wrongly-superseded watches (max-2-per-instrument). Also relaxed scout quality gates: snipe-listed pairs bypass _WEAK_PAIRS filter and get lower story threshold (20 vs 35).
