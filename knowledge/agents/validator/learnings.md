---
type: pattern
updated: 2026-03-11T07:00:49.943118
tags: [validator, decision-maker, sonnet]
---

# Validator — Learnings

## ⚠️ Ignoring trader annotations (fixed 2026-03-11)
**Date:** 2026-03-11
**Type:** critical_bug_fix
Validator was not reading `user_chart_annotations` before making direction decisions.
Tim marked NZD_USD as SELL multiple times. Validator returned BUY. Trade opened as BUY. Loss.
**Fix:** v4_pipeline now fetches active annotations (48h window) and injects them as hard context.
Validator must now explicitly justify any direction that contradicts Tim's call.
`overrode_trader_call` flag logged on every verdict.

## 💡 Blank chart = SKIP (non-event, re-trigger)
**Date:** 2026-03-11
**Type:** known_issue
EUR_GBP returned SKIP because chart rendered blank white frame.
Not a real SKIP — chart generation issue. Re-trigger cycle to get real verdict.

## 💡 Confidence 3-4 = WATCH not fire
**Date:** 2026-03-11
**Type:** calibration
conf=3-4 means fan not yet expanded enough. Wait for structure to develop before expecting trigger.
conf=7+ (EUR_CHF) = fire when conditions met.

## 🎣 Fishing Line Protocol (added 2026-03-16)
**Type:** improvement
WATCH verdicts now require `watch_manifest` JSON alongside `re_entry_conditions`. Key calibrations:
- `time_limit_candles` default = 8 (2 hours on M15). Reduce to 5 for sniper/mean-reversion setups, allow up to 10 for multi-bar expansion buildouts.
- `minimum_trigger_confidence` = 7. Below this, the setup isn't mature enough to fire even if conditions technically check. Never set below 6.
- `velocity` = "degrading" AND `death_flags` non-empty → skip WATCH entirely, issue REJECT immediately.
- `confidence_trend` = "falling" for 2+ consecutive WATCHes on the same pair → REJECT. The setup is dying, not pausing.
- `progress_pct` on `trigger_conditions` should reflect actual proximity: 0-20% = not started, 40-70% = actively forming, 80%+ = nearly there. Don't default everything to 0.
- Lead indicators fire 2–4 bars before a valid entry: first green fan bar after flat, RSI diverging histogram, Stoch %K approaching cross. When these appear, `expected_trigger_candles` should be 2–4, not null.
- `confidence_trajectory` field is now mandatory on ALL verdicts (TRADE_NOW, WATCH, SKIP). Self-assess whether conviction is rising/stable/falling based on current chart state.

## 💡 Trajectory fields from TA (added 2026-03-16)
**Type:** improvement
Technical analyst now outputs `trajectory` block: `fan_velocity_trend`, `rsi_trajectory`, `stoch_trajectory`, `setup_maturity_estimate`. Use these to populate `watch_manifest.trajectory_assessment` without extra inference. `setup_maturity_estimate` directly maps to how many checklist items are converging vs stalled.

## 🔧 Validator Prompt — Phase Behavioral Patterns Added (2026-03-29)
**Date:** 2026-03-29
**Type:** improvement
**Tags:** validator, prompt, phase-patterns, teaching-charts

> [!success] MAJOR UPDATE
> Added "What Each Phase Actually Looks Like" section to validator prompt based on studying all 20 teaching charts. Five phases codified with behavioral rules (not specific numbers — those vary):
>
> - **CASCADE START**: Everything quiet then breaks. BB squeeze→breakout, stoch crossing from extreme, small candles→big candle, ADX waking up.
> - **PEAK OF CASCADE**: Everything stretched. Fan at maximum width, BB outer band being tested, RSI at extreme, stoch pegged.
> - **RETRACEMENT**: EMAs still ordered (never cross), BB contracting expected, RSI divergence (higher lows while price lower lows), stoch reloading from opposite extreme.
> - **RE-ENTRY**: Price at E55/E100, reversal candle forms there, stoch crossing back from opposite extreme, RSI turning from midzone. This is the entry point.
> - **REGIME CHANGE**: E21 crosses back through E55 (kill signal), counter-trend candles large and growing, RSI blows through 50 to opposite extreme.
>
> Also replaced generic teaching image descriptions with actual chart observations and added stoch/EMA rows to retracement vs reversal table with chart citations.

## 💡 48-Hour Watch Expiry = Destructive on Weekends (2026-03-29)
**Date:** 2026-03-29
**Type:** correction
**Tags:** watch-manager, expiry, weekend, sanity-gate

> [!warning] CORRECTION
> Time-based watch expiry (48h) mass-expired all 25 active watches on Sunday because markets close Friday 5pm — every watch was naturally >48h. Rule deleted entirely. The Direction Sanity Gate (watch_manager.py ~line 2126) already validates live market conditions before firing. Watches should be validated by market state, not by age.


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
