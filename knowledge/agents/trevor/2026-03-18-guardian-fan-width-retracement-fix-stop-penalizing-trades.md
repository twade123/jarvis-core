---
type: improvement
created: 2026-03-18
tags: [trading, guardian, retracement, fan_width, threat_score, ema_order, position_guardian]
agent: trevor
decomposed_from: agents/trevor/learnings.md
---

## 📈 Guardian fan-width retracement fix: stop penalizing trades during normal M15 fan compression
**Date:** 2026-03-18T09:58:25
**Type:** improvement
**Workspace:** workspaces/forex-trading-team
**Tags:** trading, guardian, retracement, fan_width, threat_score, ema_order, position_guardian

Guardian threat calculator was adding +20 proximity_risk whenever fan_width_pct < 0.03% near E100, regardless of whether the fan order was still intact. During normal M15 retracements the EMA fan compresses as EMAs converge — that is healthy structure, not a failure. This was artificially inflating threat scores by 20 points during every consolidation/retracement candle, causing trades to be killed by the 75-threshold auto-close during normal price breathing. Fix in position_guardian.py assess_threat(): now checks fan_favorable before applying the +20 penalty. If fan is compressed but still in correct order (E21<E55<E100 for SELL, E21>E55>E100 for BUY), logs 'retracement, order intact' with zero threat increase. Only applies +20 if fan has actually inverted (order broken). Example: EUR_USD SELL #1656 had threat 50-53 from fan compression during retracement despite SELL order (E21<E55<E100) being fully intact.

**Evidence:** EUR_USD SELL #1656 2026-03-18: fan_width=0.000-0.018% triggering 'trend structure gone' every minute. M15 EMA check showed E21=1.15237 < E55=1.15308 < E100=1.15331 — fully intact SELL order. Threat was 50-53 purely from width, no structural break. Pre-fix: threat inflated 20pts during all retracements. Post-fix: retracement compression adds 0 threat if order intact.
