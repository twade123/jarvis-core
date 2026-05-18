---
type: correction
created: 2026-03-11
tags: [snipe-direct, tp, sl, spread, fill-price, oanda, atr, bug]
agent: trevor
decomposed_from: agents/trevor/learnings.md
---

## 🔧 SNIPE DIRECT TP/SL bug: calculated from bid price, fill at ask — TP ends up 1 pip from fill if spread is wide. Fixed by amending TP/SL post-fill from actual entry price.
**Date:** 2026-03-11T17:58:53
**Type:** correction
**Workspace:** workspaces/forex-trading-team
**Tags:** snipe-direct, tp, sl, spread, fill-price, oanda, atr, bug

USD/CHF #1101 lost -$9.92 (2026-03-11 17:16 EDT). TP was 0.78060, fill was 0.78050 — only 1 pip of profit room. Root cause: trading_cycle.py SNIPE DIRECT path calculates _tp_price = _current_price + tp_dist where _current_price is bid/mid (0.78022). BUY fills at ASK (0.78050, 2.8 pips higher). TP never adjusted. Fix: after fill, if fill_price differs from _current_price by >0.5 pips, recalculate SL/TP from fill_price and call oanda_client.set_trade_orders() to amend the live orders. Threshold check: abs(fill_price - current_price) > 0.00005. Also: this trade fired at 80% threshold (17:16 EDT) — 3 minutes before the 90% fix was applied (17:19 EDT).
