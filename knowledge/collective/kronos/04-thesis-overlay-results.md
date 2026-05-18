---
type: discovery
created: 2026-04-14
tags: [kronos, thesis-overlay, scout-gap, coverage, setup-discovery]
---

# Kronos Thesis Overlay — scout's thesis vs Kronos discoveries

**Test:** ran scout's deterministic thesis engine (`market_story.read_market_story()` —
the actual brain, 3-layer: trend/structure/momentum) on all 2,834 Kronos signals at
their anchor_time. Joined with existing `candle_walk_replay` outcomes (TUNING-driven,
same engine that produced the +7,462p headline).

Script: `research/kronos/kronos_thesis_overlay.py`
Data: `research/kronos/results/kronos_thesis_overlay.csv`
Summary: `research/kronos/results/kronos_thesis_overlay_summary.json`

## Headline

```
Bucket              n     wr     total_pips  avg_pips
in_thesis         490   85.9%     +1,454.8    +2.97   scout thesis AGREES with Kronos direction
opposite_thesis   734   80.9%     +1,574.8    +2.15   scout thesis sees OPPOSITE opportunity — Kronos wins anyway
out_of_thesis   1,610   84.7%     +4,432.4    +2.75   scout thesis sees NOTHING — Kronos wins big
                ────                ────────
                2,834               +7,462.0
```

**Scout's current thesis engine sees only 17% of what Kronos finds. The other 83% —
worth +6,007 pips over 60 days — is completely invisible to scout.**

The "opposite_thesis" bucket is especially interesting: 734 moments where scout's
thesis would have gone the OTHER direction (or blocked the trade). Kronos wins 80.9%
of them. Scout's thesis is actively wrong, not just blind, at these moments.

## In-thesis breakdown by entry type (scout's own categories)

| entry_type | n | wr | pips | avg | verdict |
|---|---|---|---|---|---|
| trend_continuation | 39 | **100.0%** | +253.3 | +6.49 | perfect — scout nails these |
| early_expansion | 79 | 89.9% | +384.1 | +4.86 | excellent |
| counter_trend_reversal | 183 | 86.9% | +676.5 | +3.70 | solid |
| breakout | 154 | 81.8% | +191.0 | +1.24 | marginal — low pip yield despite high wr |
| **e100_bounce** | **35** | **74.3%** | **-50.1** | **-1.43** | **⚠️ broken — net loss even when Kronos agrees direction** |

Actionable: `e100_bounce` setup is a real problem. Scout triggers 35 of these, wins
most, but loses pips net. TP/trailing too tight OR entries too late — worth a separate
audit. `trend_continuation` (100% wr, highest avg) should be expanded — only 39 hits
in 60 days means scout is catching few but high-quality.

## Out-of-thesis win clusters — NEW SETUP GOLD

Top cluster signatures among 1,363 out-of-thesis WINS:

| fan_state | fan_dir | momentum | n | pips | avg |
|---|---|---|---|---|---|
| contracting | bullish | neutral | 305 | +1,835 | +6.02 |
| contracting | bearish | neutral | 245 | +1,646 | +6.72 |
| stable | bullish | neutral | 228 | +1,344 | +5.90 |
| stable | bearish | neutral | 156 | +836 | +5.36 |
| stable | neutral | neutral | 94 | +427 | +4.55 |
| expanding | neutral | neutral | 93 | +505 | +5.43 |
| decelerating | bearish | neutral | 22 | +219 | **+9.96** |
| peaked | bearish | neutral | 17 | +190 | **+11.15** |
| decelerating | bullish | neutral | 18 | +133 | +7.36 |
| peaked | bullish | neutral | 19 | +156 | +8.22 |

**Two major new setup categories emerge:**

1. **"Compression pre-breakout" — fan contracting + neutral momentum** (550 wins,
   +3,481 pips total). Scout's thesis refuses these because fan isn't expanding.
   But Kronos detects these right before the move resumes. avg +6.3p each.

2. **"Silent continuation" — fan stable + neutral momentum** (384 wins, +2,180 pips).
   Scout skips stable fans (waits for acceleration). Kronos finds directional signal
   in boring conditions. avg +5.7p each.

3. **"Exhaustion under the radar" — fan peaked/decelerating + NEUTRAL momentum**
   (76 trades, avg +8-11p). Scout's counter_trend_reversal setup REQUIRES exhausted
   momentum. These are the setups where momentum isn't yet oscillating — Kronos
   catches the exhaustion 1-2 bars before the RSI/Stoch shows it.

## Per-pair out-of-thesis win rates (all 13)

```
pair      in-th  opp   OOT   in-wr%  OOT-wr%
AUD_JPY     38    60   137    86.8     85.4
AUD_USD     52    54   122    86.5     84.4
EUR_AUD     39    64   131    84.6     87.0
EUR_CHF     27    40   118    92.6     83.1
EUR_GBP     22    51    87    86.4     79.3
EUR_JPY     36    55   133    77.8     81.2
EUR_USD     40    63   122    77.5     80.3
GBP_JPY     34    67   129    76.5     87.6
GBP_USD     52    47   135    94.2     80.7
NZD_USD     38    56   113    86.8     85.8
USD_CAD     33    63   122    90.9     88.5
USD_CHF     42    59   116    90.5     87.9
USD_JPY     37    55   145    83.8     87.6
```

Out-of-thesis win rates are 79-88% across ALL pairs. This is systemic, not a one-pair
quirk. Scout's thesis is too narrow uniformly.

## Implications for Kronos integration

1. **Kronos Hunter (the Phase 1 module) should NOT be gated by scout's thesis.**
   Scout's thesis would cut 83% of Kronos's winning trades. Spec is correct to have
   Hunter as a parallel independent discovery path.

2. **Kronos Filter (pre-validator sanity) remains valid** — it's a DIRECTIONAL veto,
   not a thesis-agreement check. Different function.

3. **Phase 1.5 (thesis codification) gets concrete targets:**
   - Build "compression_prebreakout" setup detector (fan=contracting, ADX rising,
     BB squeezing → directional pre-break). Would unlock ~550 setups/60d.
   - Build "silent_continuation" setup (fan=stable, directional drift without extreme
     momentum). Would unlock ~380 setups/60d.
   - Fix `e100_bounce` setup — 35 hits but -50p net. Likely TP too tight.
   - Fix scout's sensitivity on peaked/decelerating fans — momentum doesn't have to
     be visibly exhausted, Kronos catches it earlier.

4. **"Opposite_thesis" bucket (734 trades) deserves deeper analysis.** Scout's thesis
   says sell, Kronos says buy, Kronos wins 81%. Suggests scout's counter_trend_reversal
   logic fires TOO EARLY — fading moves that still have one more leg.

## Caveats

- Thesis engine called with 256 M15 bars, no H1/H4 context. Scout live also has
  multi-timeframe alignment which might redirect some "opposite_thesis" decisions.
  Still — this is scout's M15-native thesis, which is the primary entry gate.
- `out_of_thesis` includes cases where thesis score was 1-49 (saw something faint).
  Could further sub-bucket by score to see if 25-49 is different from 0-24.
- All same caveats as 03-final-results.md (no spread cost, candle_walk_replay ≠ full
  guardian).

## Next

- Overlay winning Kronos trades on chart images (post-tuning subset Apr 10+) —
  visually confirm the "compression_prebreakout" and "silent_continuation" clusters
  look like real setups a trader would recognize.
- Consider re-running with **Kronos-base** to verify small-model results carry through.
- Phase 1.6 — feed the 2,834 signals through `optimizer/engine_v2.py` to see if
  Kronos trades prefer different TUNING (wider TP? slower trailing?).
