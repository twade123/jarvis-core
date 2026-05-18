---
type: correction
created: 2026-03-20
tags: [snipe-cycle, cooldown, trading-api, bug-fix, audit-2026-03-20]
agent: log
decomposed_from: agents/claude-code/log/2026-03.md
---

## 🔧 Audit Fix 2/7: Snipe re-firing bypass — /check-watches skipped cooldown gate
**Date:** 2026-03-20T14:00:01
**Type:** correction
**Tags:** snipe-cycle, cooldown, trading-api, bug-fix, audit-2026-03-20

trading_api_routes.py: The /check-watches API route called _queue_cycle directly, bypassing the cooldown gate in _fire_snipe_cycle. This was the root cause of 8 snipe cycles firing in 20 minutes on Mar 13 — the watch-check path had no cooldown awareness.

Fixed by adding pair cooldown check (PAIR_COOLDOWN_SECS=1800) in the watch-check loop before priority=high bypass. Now the same pair cannot fire multiple snipe cycles within the 30-minute cooldown window regardless of entry path.

**Evidence:** Line ~3152 in trading_api_routes.py. Mar 13 had 8 rapid-fire snipes on same pair. Post-fix: cooldown enforced on all paths.
