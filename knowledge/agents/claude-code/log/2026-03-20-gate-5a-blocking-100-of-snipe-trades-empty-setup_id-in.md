---
type: correction
created: 2026-03-20
tags: [gate-5a, setup-id, watch-context, snipe-path, bug-fix, audit-2026-03-20-phase3]
agent: log
decomposed_from: agents/claude-code/log/2026-03.md
---

## 🔧 Gate 5a blocking 100% of snipe trades — empty setup_id in watch context
**Date:** 2026-03-20T20:00:02
**Type:** correction
**Tags:** gate-5a, setup-id, watch-context, snipe-path, bug-fix, audit-2026-03-20-phase3

Gate 5a (setup validation from Phase 2 Fix 8) was blocking 100% of trades coming through the watch→snipe path because watch context has an empty setup_id field. The gate correctly rejects empty setup_id, but the watch→snipe path never populates it — creating a complete blockade on the primary execution path.

Fix: Gate 5a now injects alert_type as the setup identifier when setup_id is empty in watch context. Since watch→snipe trades are triggered by V4 alerts (CRITERIA_MET, BREAKOUT_CONFIRMED, etc.), alert_type is the correct identifier for these trades.

**Evidence:** 100% snipe trade rejection at Gate 5a pre-fix. Root cause: watch context setup_id="" → gate blocks. Post-fix: alert_type injected as fallback.
