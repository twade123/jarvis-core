---
type: note
created: 2026-03-17
tags: [trading, patterns, EUR_AUD, AUD_JPY, GBP_USD, guardian, R:R]
agent: trevor
decomposed_from: agents/trevor/learnings.md
---

## 📝 Trade pattern analysis: winning vs losing entry signatures on EUR_AUD, AUD_JPY, GBP_USD
**Date:** 2026-03-17T18:14:39
**Type:** note
**Tags:** trading, patterns, EUR_AUD, AUD_JPY, GBP_USD, guardian, R:R

From 2026-03-17 8-trade audit with chart analysis:

LOSING PATTERN (0.33 R:R, wide SL):
- Entry in mature/contracting fan (fan peaked, velocity decelerating)
- SL = 2.5×ATR (24-31p), TP = 1×ATR (8-10p)
- Often entry at upper/lower range extreme, not at EMA pullback
- Stochastic moving against trade direction (recovering/rolling)
- Result: SL hit in 3-29 min, full loss

WINNING PATTERN (3:1+ R:R, tight SL after guardian tighten):
- Entry while fan still has energy (guardian tightens SL as trade moves)
- EMA deceleration triggers SL tighten at peak (8-9 consecutive bars)
- Original SL ~33p, guardian tightens to 3p after MFE reached
- TP hit quickly (9-10 min) at the right entry point
- Stochastic confirming direction

GUARDIAN TIGHTEN PATTERNS OBSERVED:
- 'EMA-only deceleration 8x → tighten': Fires after 8 bars of EMA contraction while in profit. Very effective — both trades it fired on won (#1443, #1449).
- 'E100 tested 3x in retrace → tighten': Fires when price tests E100 during retracement. Too aggressive when MFE > 60% TP (#1461 issue).
- 'Peak-decel close': Fires when EMA separation velocity decelerates 3 consecutive bars. Worked well for #1437 GBP_USD.

CURRENT PAIR STATUS (2026-03-17 18:11 EDT):
- GBP_USD: Strongest setup. Fan expanding, 24.8p width. Coiled at highs. BUY on EMA21 dip.
- AUD_JPY: Bullish but stoch rolling from high. Wait for EMA55 pullback (~112.75).
- EUR_AUD: Fan exhausted/flat after big bearish move. No edge right now.

R:R IMBALANCE ROOT CAUSE:
sl_atr=2.5 (25p) and tp_atr=1.0 (10p) in risk_config.json produces 0.33 R:R structurally.
Need 75%+ win rate to break even at 0.33 R:R — that's not sustainable.
Fix: cap SL to 1.5×ATR in non-expanding fans. Consider raising tp_atr to 1.5 in Config/risk_config.json.
