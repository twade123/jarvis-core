---
type: scout_tuning_data
date: 2026-03-06
pairs: [GBP_JPY, USD_CAD, EUR_CHF]
tags: [scout, tuning, missed-opportunities, fan-flip, M15, feedback-loop]
source: visual_chart_analysis
---

# Scout Tuning Data — 2026-03-06 Missed Opportunities

## Root Cause: Scout Only Fires on Existing Ordered Fans
Scout currently requires a pre-existing ordered fan (E21>E55>E100 or inverse) before it will scan a pair.
It MISSES the fan-flip breakout — when a fan compresses → re-orders in new direction → expands.
All three missed pairs today were fan-flip breakout setups, not retracement setups.

---

## GBP/JPY (+71 pips missed — fan-flip bearish breakout)
- **Fan at session open:** Bullish ordered. By bar 55-60 flipped to bearish ordered.
- **What scout saw:** DEEP RETRACEMENT alerts but GBP_JPY watches were all cancelled (conf=0.0)
- **Entry scout missed:** Short at ~209.85-209.90 (bar 65-68), price retesting E21 from below after bearish fan established. SL above E55, TP at lower BB.
- **R:R:** 3:1
- **Trigger that was missing:** Fan re-ordering event — E21 crosses below E55 AND fan width starts expanding from compression (>5 pips and growing)

## EUR/CHF (-48 pips missed — fan-flip bearish breakout)
- **Fan at session open:** Tangled (near-zero width)
- **What scout saw:** Snipe watch #952 stuck at 2/6 conditions (33%) all day, never cycled
- **Entry scout missed:** Short at ~0.9058-0.9060 (bar 85-87), price pulling back to E21 after bearish fan flip. SL above E100 (~0.9063), TP at lower BB (~0.9042).
- **R:R:** 4:1
- **Trigger that was missing:** BB width acceleration coinciding with fan flip — EUR/CHF fan width 6.8p is proportionally significant (ATR-relative thresholds needed)

## USD/CAD (-76 pips missed — disordered fan, pure breakout)
- **Fan at session open:** DISORDERED (E21≈E55≈E100 all tangled at 1.3662-1.3664)
- **What scout saw:** Blocked multiple times ("E100 dist < 5p chop zone") then eventually DEEP RETRACEMENT
- **Root cause:** Scout's chop zone block prevented cycle even as a 90-pip directional move developed
- **Tuning needed:** Chop zone block should not apply when BB width is expanding AND price is breaking away from the EMA cluster (not just hovering)

---

## Tuning Recommendations (Priority Order)

### 1. ADD: Fan-Flip Detection Trigger (HIGH PRIORITY)
When fan was compressed (width < threshold for N bars) AND now re-orders bearishly/bullishly AND width is expanding → trigger validation cycle.
This catches the most powerful setups (trend reversals after consolidation).

### 2. ADD: Post-Flip Fishing-Line Trigger
After a fan flip (< 10 bars old), if price retests E21 from the counter-trend side → trigger cycle.
This is the classic "entry into a new trend" setup the validator is trained to see.

### 3. FIX: Scale Fan-Width Thresholds by ATR
EUR/CHF 6.8p fan = GBP/JPY ~25p fan proportionally. Use ATR-relative thresholds instead of fixed pip values.
Current 5p minimum threshold is correct for JPY pairs but too high for low-volatility pairs (EUR/CHF, EUR/GBP).

### 4. FIX: Chop Zone Override for BB Expansion
USD/CAD was blocked by E100 chop zone filter. Add override: if BB width is accelerating (rate of change > threshold) AND price has already moved >10p from EMA cluster → allow cycle despite chop zone flag.

### 5. MONITOR: GBP/JPY Watch Cancellation Pattern
All GBP_JPY watches are being cancelled (conf=0.0). Investigate why confidence is zero — validator may be consistently rejecting this pair at a structural level.

---

## Data Quality Note
These are M15 retrospective observations based on EOD chart analysis and log review.
All three pairs had validator-confirmable setups. The miss was at the SCOUT TRIGGER layer, not the validator.
