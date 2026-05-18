---
type: note
created: 2026-04-14
tags: [kronos, scout-shadow, methodology, full-mirror]
---

# Kronos Scout Shadow — Full Mirror Methodology

## Goal
Answer the real question: **"if Kronos had been our scout for the last 60 days,
how many trades would it have found, what's the overlap with what we actually took,
and how would the full Kronos discovery set perform under our guardian?"**

## Setup
- **All 13 scout pairs:** AUD_JPY, AUD_USD, EUR_AUD, EUR_CHF, EUR_GBP, EUR_JPY,
  EUR_USD, GBP_JPY, GBP_USD, NZD_USD, USD_CAD, USD_CHF, USD_JPY
- **60-day window** ending current time
- **15-minute anchors** (matches scout's M15 polling cadence) → ~4,009 anchors
  (excludes weekend forex closure: Sat all day, Sun before 22:00 UTC, Fri after 21:00 UTC)
- **Kronos-base** (102M params), **batched inference** via `predict_batch()` —
  all 13 pairs at one anchor processed in one forward pass
- **Local parquet candle cache** for 13 pairs × 60 days = ~13 OANDA fetches total

## Quality gate (mirrors scout setup detection)
A signal is emitted only when:
1. `|drift_pips| >= 5` (absolute floor — ignore micro-noise)
2. `|drift_pips| >= 0.5 × ATR_pips` (signal must be material vs volatility)
3. **Per-pair 4-hour cooldown** after any signal (prevents over-trading same pair)

## Trade build (uses live TUNING)
- Entry: current close at anchor
- SL: `entry ± gate.sl_atr_mult × ATR` (currently 2.0×)
- TP: `entry ± gate.tp_atr_mult × ATR` (currently 1.5×)
- Then: `candle_walk_replay()` walks actual post-anchor M15 candles with full
  guardian sim (profit floor tiers, ratchet, trailing stop, reaction delays)

## Output
- `kronos_scout_progress.csv` (incremental — one row per qualifying signal)
- `kronos_scout_summary_<stamp>.json` — final stats:
  - Total Kronos signals
  - Win rate, total pips
  - Overlap with our 217 actual (same pair + direction + ±2h window)
  - Kronos-only (trades scout missed)
  - Our trades Kronos missed
  - Per-pair breakdown

## Compute
- ~4,009 anchors × ~2s batched forecast = **~2-3 hours total**
- All 4,009 batched calls each process 13 pairs simultaneously (up to 52K forecasts equivalent)
- MPS auto-cleanup after each batch keeps memory flat

## Files
- Script: `research/kronos/kronos_scout_full.py`
- Cache: `research/kronos/candle_cache/{pair}_M15_60d_{date}.parquet`
- Live progress: `research/kronos/results/kronos_scout_progress.csv`
- Log: `research/kronos/results/scout_full.log`

## Status
Launched 2026-04-14. Results in progress. Will append findings here when complete.
