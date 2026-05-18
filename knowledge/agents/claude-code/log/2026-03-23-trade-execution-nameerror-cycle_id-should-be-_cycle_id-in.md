---
type: correction
created: 2026-03-23
tags: [execution, cycle_id, typo, trading_cycle, critical]
agent: log
decomposed_from: agents/claude-code/log/2026-03.md
---

## 🔧 Trade execution NameError: cycle_id should be _cycle_id in place_market_order call
**Date:** 2026-03-23T07:32:44
**Type:** correction
**Tags:** execution, cycle_id, typo, trading_cycle, critical

> [!warning] CORRECTION
> EUR_CHF validator said TRADE_NOW/BUY conf=9, execution attempted at 07:29:03 but crashed with 'name cycle_id is not defined'. Line 5511 in trading_cycle.py passed cycle_id= to place_market_order but the variable is _cycle_id (with underscore prefix, defined at line 1867). Single-character typo prevented all cycle-originated trades from executing. Snipe-direct trades use a different code path and were unaffected.
