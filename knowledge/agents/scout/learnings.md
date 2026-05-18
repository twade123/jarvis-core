---
type: pattern
updated: 2026-03-26T17:09:46
tags: [scout, data-collection, oanda]
---

# Trade Scout — Learnings

## 💡 S15 + squeeze on EUR_USD during London = 89% win rate
**Date:** 2026-03-01
**Type:** discovery
Backtested 5000 trades. Fails during Asian session (73% WR).

## 💡 EUR_CHF highest conviction setup (2026-03-11)
**Date:** 2026-03-11
**Type:** pattern
EUR_CHF with bearish/expanding fan, story=70, S=13 B=3, validator SELL conf=7 = fire.
All three signals aligned (Tim annotation + scout + validator). Best setup of the day.

## 💡 Bullish scout vs SELL call contradiction (USD_JPY)
**Date:** 2026-03-11
**Type:** observation
Scout showing bullish/expanding (B=13 S=0) but Tim + validator both saying SELL.
Scout may be catching expansion peak before reversal begins.
When this pattern appears: wait for BB to stop expanding and fan to start contracting before acting.

## 💡 story=0 / fan=unknown = pair in cooldown
**Date:** 2026-03-11
**Type:** interpretation
EUR_USD, GBP_USD, NZD_USD, USD_CHF showing story=0, fan=? after trades fire.
Not broken — cooldown period after cycle. Re-trigger manually if setup is still live.

## 📝 Daily scout report 2026-03-25: 49 CRITERIA_MET, 0% validator acceptance, 1 missed opportunity
**Date:** 2026-03-25T17:10:07
**Type:** note
**Tags:** scout, daily-report, performance

> [!info] NOTE
> Key findings: Zero TRADE_NOW verdicts all week — validator extremely conservative. 67 total alerts (49 CM + 11 EW + 7 RT). EUR_JPY manual trade missed by scout (entered 01:04 UTC, scout alerted 06:01). New V4 columns (separation_accelerating, confirmed_reexpansion) not yet populating. 10 strong trending+expanding alerts with score>=70 went unacted on.


---

## 📈 Manual trade entry_type hardcoded to 'manual' — market_story was returning 'none'
**Date:** 2026-03-26T10:24:17
**Type:** improvement
**Tags:** manual-trade, entry_type, trading_api_routes, dashboard

> [!success] IMPROVEMENT
> MODULE: trading_api_routes.py | LAYER: manual_trade_insert | CHANGE: Line 4977 changed from (market_story or {}).get('entry_type', 'manual') to hardcoded 'manual'. Story's entry_type goes to story_entry_type column instead. | BEFORE: Manual trades got entry_type='none' because market_story.entry_type returned string 'none'. Caused wrong SOURCE badge and SQL bucketing. | AFTER: Manual trades always entry_type='manual'. | ACTIVATED: ~14:15 UTC 2026-03-26


---

## 📝 Daily scout report 2026-03-26: 29 CRITERIA_MET, 0% validator acceptance, 0 missed opportunities
**Date:** 2026-03-26T17:09:30
**Type:** note
**Tags:** scout, daily-report, performance

> [!info] NOTE
> Key findings: Validator TRADE_NOW blockage continues for day 2 — 0 TRADE_NOW verdicts despite 29 CRITERIA_MET alerts. Vision model gave 22 SKIP + 6 GATE1_BLOCK. Tim manually traded AUD_USD for +11.1 pips on signals validator rejected. New cascade/retracement fields not yet wired into conditions JSON. Regime early warnings 67% predictive on forming alerts.


---

## 📈 Validator TRADE_NOW pipeline blocked 2 consecutive days — needs investigation
**Date:** 2026-03-26T17:09:46
**Type:** improvement
**Tags:** validator, blockage, improvement, urgent

> [!success] IMPROVEMENT
> 0 TRADE_NOW verdicts on 2026-03-25 (49 CM alerts) and 2026-03-26 (29 CM alerts). Vision validator giving 65% SKIP, 18% GATE1_BLOCK. Tim profitably traded AUD_USD manually on setups the validator rejected. Recommendation: Review Gate 1 thresholds and vision model confidence calibration. Also wire cross2_bars_ago and separation_accelerating into scout conditions JSON for threshold analysis.


---

## 🔧 Scout Audit: 7 Detection Gaps Fixed (2026-03-29)
**Date:** 2026-03-29
**Type:** improvement
**Tags:** scout, audit, retracement, stoch, rsi, candle-detection

> [!success] MAJOR OVERHAUL
> Audited trade_scout.py against behavioral patterns from all 20 teaching charts. Found 7 gaps where scout couldn't detect setups that validator/guardian understand. All fixed:
>
> **GAP 1+6 — PATH A Retracement Forming**: Scout only detected retracements AFTER 3-bar BB re-expansion (too late). Added PATH A that fires at E55/E100 touch with ≥1 confirming signal (stoch cross, RSI divergence, reversal candle). This is WHERE the entry is on the charts.
>
> **GAP 2 — Stochastic Cross Detection**: Added %K/%D crossover detection in oversold (<35) and overbought (>65) zones. Strongest re-entry signal across all 20 teaching charts — scout had zero detection for it.
>
> **GAP 3 — RSI Divergence Wired In**: TA computed rsi_bull_div/rsi_bear_div but scout never read them. Now wired into retracement logic.
>
> **GAP 4 — Consolidation Filter**: Was blocking ordered retracements. Added exemption for bullish/bearish fan direction.
>
> **GAP 5 — Dual-Cross Window**: Left as-is (5 bars). PATH A handles older crosses.
>
> **GAP 7 — Reversal Candle at EMA**: Added hammer/pin bar detection within 5 pips of E55/E100.
>
> **Protective updates**: Dead move block and chop zone filter exempt retracement_forming. Checklist score includes new signals. Flight recorder logs everything.


---

## 💡 Stoch cross at E55/E100 = highest-probability re-entry signal
**Date:** 2026-03-29
**Type:** discovery
**Tags:** stochastic, retracement, re-entry, pattern

> [!info] PATTERN
> Across all 20 teaching charts: %K crossing %D from the opposite extreme zone while EMAs remain ordered and price is at E55 or E100 = the single most reliable re-entry signal. Scout now detects this as part of PATH A.


---

## 💡 Retracement entry is BEFORE BB re-expansion, not after
**Date:** 2026-03-29
**Type:** discovery
**Tags:** bollinger, retracement, entry-timing

> [!info] PATTERN
> Entry candle forms at E55/E100 while BB still contracting or flat. BB re-expansion comes 2-5 bars AFTER entry. Old PATH B (3-bar confirmed re-expansion) was 10-20 pips late. PATH A now fires at the touch.


---


---

### 2026-04-01: Tuning Dashboard — Log ALL parameter changes
**Type:** improvement
**Universal:** true

When you adjust ANY parameter (thresholds, gates, weights, rules), you MUST log it:

```python
from tuning_logger import log_tuning_change
log_tuning_change(
    param="guardian.rule6_peak_threshold",  # dotted: category.param_name
    value="5.0",
    previous_value="3.0",
    reason="Rule 6 firing too early on trades that recover after E100 test",
    approved_by="guardian"
)
```

Categories: gate.*, watch.*, scout.*, validator.*, guardian.*, snipe.*, manual_trade.*, fix.*
Types: param_change, new_gate, new_feature, new_rule, bug_fix, revert, removal

This feeds the tuning dashboard in admin Performance panel. Without it, changes are invisible and unmeasurable. See collective/patterns/2026-04-01.md for full documentation.

---
