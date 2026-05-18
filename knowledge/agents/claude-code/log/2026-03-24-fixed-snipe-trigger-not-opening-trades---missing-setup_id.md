---
type: correction
created: 2026-03-24
tags: [snipe, setup_id, trading_cycle, trading_api_routes, validation_gate]
agent: log
decomposed_from: agents/claude-code/log/2026-03.md
---

## 🔧 Fixed snipe trigger not opening trades - missing setup_id in snipe context dicts
**Date:** 2026-03-24T20:49:52
**Type:** correction
**Tags:** snipe, setup_id, trading_cycle, trading_api_routes, validation_gate

> [!warning] CORRECTION
> Snipe notifications fired but no trade opened. Root cause: both snipe_ctx dicts in trading_api_routes.py (lines ~3232 and ~3508) omitted setup_id field. trading_cycle.py lines 2282-2298 has a validation gate that blocks execution if setup_id is empty/unknown. Every user-submitted snipe hit this gate silently. Fix: added setup_id to both snipe_ctx dicts, pulling from watch context setup_id or setup_name as fallback.
