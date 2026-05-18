---
type: correction
created: 2026-03-20
tags: [trading-cycle, guardian, pre-trade-check, market-structure, bug-fix, audit-2026-03-20]
agent: log
decomposed_from: agents/claude-code/log/2026-03.md
---

## 🔧 Audit Fix 3/7: No pre-trade market structure check — entering degraded markets
**Date:** 2026-03-20T14:00:02
**Type:** correction
**Tags:** trading-cycle, guardian, pre-trade-check, market-structure, bug-fix, audit-2026-03-20

agents/trading_cycle.py: The snipe_direct execution path had no market structure validation before placing orders. Trades could enter already-degraded market structure where the guardian would immediately start scoring YELLOW on the new position.

Fixed by running guardian score_threat() as a pre-check in step 5b before place_market_order. Blocks entry if threat >= ZONE_YELLOW. This creates a consistent gate: if market structure is bad enough that the guardian would immediately worry about an existing position, don't open a new one.

**Evidence:** Added in step 5b of trading_cycle.py. Pre-check runs score_threat() on M15 candles for the target pair.
