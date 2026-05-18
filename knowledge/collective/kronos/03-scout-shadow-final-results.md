---
type: discovery
created: 2026-04-14
tags: [kronos, scout-shadow, final-results, backtest, complete]
---

# Kronos Scout Shadow — FINAL RESULTS (60-day, 13 pairs, 1003 anchors)

**Test config:**
- Kronos-small (24.7M, MPS), sample_count=3, PRED_LEN=24, LOOKBACK=256
- Hourly anchors (1003 total, weekday-aware)
- All 13 scout pairs, batched inference
- Quality gate: |drift|≥5p AND |drift|≥0.5×ATR, 4h per-pair cooldown
- Exits via `candle_walk_replay()` with LIVE TUNING values
- Spread NOT deducted (caveat below)

## Headline Numbers

| | KRONOS | OUR ACTUAL (60d) |
|---|---|---|
| Trades found | 2,834 | 234 |
| Wins | 2,378 | 132 |
| Win rate | **83.9%** | 56.4% |
| Total pips | **+7,462** | -547 |
| Avg pips/trade | +2.63 | -2.34 |
| Pairs covered | 13 (even) | 13 (uneven) |

## Overlap Analysis (Same pair + direction, ±2h)

- Overlap (both found same setup): **44** (1.6% of Kronos, 19% of ours)
- Kronos-only (we missed): **2,790**
- Ours that Kronos missed: **190**

Kronos and scout find largely DIFFERENT setups. Each has unique discoveries.

## Post-Tuning Subset (Apr 10+ → most relevant)

| | KRONOS | OURS |
|---|---|---|
| Trades | 194 | 24 |
| Win rate | 83.2% | 79.2% |
| Total pips | **+330.8** | **-65.2** |
| Pairs traded | All 13 | Only 3 (EUR_AUD, EUR_CHF, USD_CHF) |

**+396 pip swing.** Same period, similar win rate, but Kronos covered all 13 pairs while we only touched 3.

## Pair Coverage (60-day)

```
pair       us  kronos  k_pips    k_wr
AUD_JPY    19    235  +907.8p  86.2%
AUD_USD    15    228  +520.1p  84.4%
EUR_AUD    51    234 +1051.9p  86.8%
EUR_CHF    10    185  +157.6p  85.3%
EUR_GBP     9    160  +111.0p  83.3%
EUR_JPY     9    224  +389.4p  82.0%
EUR_USD    20    225  +355.6p  82.1%
GBP_JPY    24    230 +1266.7p  87.0%  ← biggest pip earner
GBP_USD    10    234  +628.5p  83.3%
NZD_USD    15    207  +497.3p  85.4%
USD_CAD     9    218  +379.6p  87.2%  ← highest win rate
USD_CHF    27    217  +511.6p  86.6%
USD_JPY    16    237  +684.9p  83.5%
```

Every pair profitable. Kronos finds 5-25× more setups per pair than scout.

## Confidence Calibration — Naive Metric Useless

```
Confidence  n      win%   total_pips   avg
0.0-0.2     52    86.5%   +222.1p     +4.27
0.2-0.4    699    84.4%  +1963.2p     +2.81
0.4-0.6   1007    85.1%  +2656.3p     +2.64
0.6-0.8    818    85.5%  +2150.5p     +2.63
0.8-1.0    226    82.7%   +469.9p     +2.08
```

Win rate flat 82-86% across ALL bands. Drift/cone confidence ratio does NOT filter signal quality.
Action: set `kronos.hunter_min_confidence=0` in TUNING. Replace with better metric (MC path-agreement %) in v2.

## Exit Reason Distribution

```
trailing_sl  1821 (64%)  avg=+4.64p   ← bulk of wins from trailing
tp_hit        515 (18%)  avg=+12.06p  ← TP hits big when they happen
sl_hit        424 (15%)  avg=-17.57p  ← losses bounded by SL
floor_breach   42 ( 1%)  avg=+6.05p
```

Kronos's direction calls let trailing stop ride moves until reversal. TP hits when continuation is strong.

## Critical Caveats

1. **No spread cost.** ~1.5p × 2834 = -4,250p adjustment. **Net: ~+3,200p.** Still strongly positive.
2. **`candle_walk_replay()` ≠ full guardian.** Same engine the V2 optimizer used to tune the live values, but doesn't model:
   - 4-layer threat model
   - Phase cascade transitions
   - Retrace state machine
   - Post-win exhaustion gate
   - Manual grace, oscillator freshness
3. **Hourly anchors** in test → production at 15-min cadence will likely find more.
4. **47 trades/day is unrealistic** for actual trading exposure. Need stricter `max_concurrent` enforcement.

## Key Insight

**Scout's pair concentration is the #1 missed-opportunity driver.** Post-tuning we trade 3 pairs and lose pips; Kronos finds 4× more trades across all 13 and gains pips. The opportunity gap isn't model accuracy — it's coverage.

## Files

- Backtest script: `research/kronos/kronos_scout_full.py`
- Raw signals: `research/kronos/results/kronos_scout_progress.csv` (2834 rows)
- Summary JSON: `research/kronos/results/kronos_scout_summary_20260415T021040.json`
- Design spec: `docs/superpowers/specs/2026-04-14-kronos-scout-component-design.md`

## Next Steps

1. (Recommended) Re-run with **Kronos-base (102M)** at 15-min cadence to confirm production-model results match
2. Phase 1.5: thesis alignment analysis on 2834 signals → bucket in/out of validator thesis
3. Phase 1.6: feed Kronos signals through `optimizer/engine_v2.py` for parameter validation
4. Build per spec → paper trading
