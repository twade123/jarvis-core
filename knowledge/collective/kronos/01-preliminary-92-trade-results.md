---
type: discovery
created: 2026-04-14
tags: [kronos, backtest, preliminary, scout, head-to-head]
---

# Kronos Part A — 92-Trade Preliminary Results

**Methodology:** For each of our completed trades, fetch 400 M15 bars before entry,
run Kronos-base forecast (60-bar horizon, 20 MC paths), derive direction + ATR-based
SL/TP from live `tuning_config.TUNING`, simulate via `optimizer.replay.candle_walk_replay()`.

## Headline (92 of 217 done before pivot)
| | Our actual | Kronos sim |
|---|---|---|
| Win rate | 55.4% | **82.6%** |
| Total pips | -117.9 | **+346.5** |
| Δ |  | **+464.4 pips** |

## Direction agreement
- Kronos agrees with us only **35%** of the time
- When **agreed** (32 trades): same direction, Kronos's exits won 28/32 vs our 18/32
- When **disagreed** (60 trades): Kronos won 48/60 (80%), we won 33/60 (55%)

## Confidence calibration (drift/cone ratio)
| Min Conf | n | Win % | Avg Pips |
|---|---|---|---|
| 0.0 | 92 | 82.6% | +3.77 |
| 0.4 | 55 | 80.0% | +4.47 |
| 0.6 | 40 | 72.5% | +1.81 |
| 0.8 | 23 | 73.9% | +2.57 |
| 0.9 | 3 | 33.3% | -10.03 |

**Key:** the drift/cone confidence metric is NOT a useful filter. High confidence
does not improve win rate. Need a better metric.

## Per-pair (preliminary, low N per pair)
- **Strong for Kronos:** EUR_AUD +196p, GBP_USD +82p, EUR_USD +64p, AUD_JPY +62p
- **Weak for Kronos:** USD_CHF -42p, GBP_JPY -46p

## Critical caveats — DO NOT cheer the +464 number
1. **No spread cost** in `candle_walk_replay`. ~1.5p/trade × 92 = -138p adjustment.
2. **Apples-to-oranges exits.** Sim uses mechanical SL/TP/trailing on Kronos direction.
   Our actual trades went through full guardian threat-layer scoring (4 layers,
   cooldowns, threat-based exits). The right control is "same exit logic on OUR
   direction" — we don't have that comparison yet.
3. **N=92** — early sample. Distribution may shift on full 217.
4. Our 55.4% win rate in this sample is higher than typical (45-50%), so this isn't
   worst-case for us.

## Why the test was paused at 92
User correctly identified that Part A only answers "at moments scout flagged a trade,
who's better?" It does NOT answer "would Kronos find trades scout missed?" Pivoted
to full scout-shadow scan (see 02-scout-shadow-methodology.md).

## Files
- Raw data: `research/kronos/results/partA_progress.csv` (preserved)
- Backtest script: `research/kronos/kronos_backtest.py`
