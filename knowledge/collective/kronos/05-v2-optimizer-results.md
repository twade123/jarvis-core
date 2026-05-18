---
type: discovery
created: 2026-04-14
tags: [kronos, v2-optimizer, tuning, optuna, guardian, parameter-sweep]
---

# Kronos V2 Optimizer — 500-trial TPE sweep

**Test:** ran the same `optimizer.engine_v2` Optuna TPE engine that produced the
current live TUNING from 198 real trades — but with the 2,834 Kronos signals as
the trade source. `candle_walk_replay` per trade with 48 post-entry M15 bars;
composite score scaled for trade count (MDD floor/norm ×14.17 to match 2,834 vs
baseline 200).

Script: `research/kronos/kronos_v2_optimizer.py`
Study DB: `research/kronos/results/kronos_v2_<stamp>.db`
JSON: `research/kronos/results/kronos_v2_optimizer_result.json`
Runtime: 273s / 500 trials (~0.55s/trial incl. full 2,834-trade replay)

## Headline — BASELINE vs OPTIMIZED

| metric | baseline (current TUNING) | optimized (Kronos-specific) | Δ |
|---|---|---|---|
| win_rate | 80.1% | **87.4%** | +7.3% |
| avg_pips | +2.13 | **+3.99** | +1.86 |
| total_pips | +6,042 | **+11,315** | **+5,273** |
| profit_factor | 1.61 | 2.19 | +0.58 |
| max_drawdown | 194.7p | 220.6p | +25.9p |

**+87% more pips** (6,042 → 11,315) on the same 2,834 trades just by re-tuning
guardian/SL/TP for Kronos characteristics. This is the "money left on the table"
answer — we were capturing ~53% of what's possible.

## Parameter deltas — what changed

| param | current | optimal | Δ | importance |
|---|---|---|---|---|
| **guardian.ratchet_step_pips** | 3.67 | **0.80** | **-2.87** | **57.9%** |
| **gate.tp_atr_mult** | 1.50 | **3.81** | **+2.31** | **17.8%** |
| **guardian.trailing_activation_rr** | 0.20 | 0.16 | -0.04 | 12.6% |
| **guardian.profit_floor_5p** | 0.70 | **0.25** | **-0.45** | 3.6% |
| guardian.trailing_atr_mult | 0.30 | 0.34 | +0.04 | 3.4% |
| gate.sl_atr_mult | 2.00 | 2.17 | +0.17 | 2.1% |
| guardian.sl_buffer_pips | 1 | **8** | **+7** | minor |
| guardian.profit_floor_8p | 0.80 | 0.94 | +0.14 | minor |
| guardian.profit_floor_12p | 0.90 | 0.97 | +0.07 | minor |
| guardian.profit_floor_20p | 0.95 | 0.83 | -0.12 | minor |

## Three big findings

### 1. Ratchet step should be much smaller (3.67 → 0.80 pips) — 58% of signal

Current TUNING ratchets the locked profit floor in 3.67-pip steps. Optimizer
wants 0.80p steps — finer granularity. Net effect: the profit floor moves up
much more smoothly, locking in gains as they accrue rather than in chunks.
This alone is the #1 change by importance (58%).

### 2. TP should be WAY wider (1.5× → 3.8× ATR) — 18% of signal

Current TP is ~12-15p on typical pairs (1.5× ATR). Optimizer wants ~30-40p TP
(3.8× ATR). This matches the e100_bounce finding: wins peak avg +7.5p with TP
at 11-15p, meaning TP wasn't the binding exit — so why does wider TP help?
Because Kronos trades run further than current TP allows on the winners.
The 18% wr on current tp_hits averaging +12p suggests big moves are being cut
short. Let them breathe: the ratchet+trailing combo can catch the giveback.

### 3. Early profit_floor_5p should be much looser (0.70 → 0.25) — 4% of signal

Current config locks 70% of peak at 5p. Optimizer wants 25%. Reason: at 5p on
a ~30p-TP trade, locking 70% cuts the trade off too tight and converts small
winners to break-even trades. Let them breathe until 8p (where floor tightens
back to 0.94). Combined with smaller ratchet steps, this lets trades
pull back slightly into a "cooldown" then resume.

## Why MDD went up slightly (+26p)

Wider TPs + looser early floors = trades give back more during their ride.
This is *expected* — higher-yield strategies have higher running drawdowns.
Still well inside acceptable range (220p on 2,834 trades is <0.08p/trade DD).

## Comparison to current TUNING deriation (198 trades, live)

Current TUNING was tuned on 198 real OUR-pipeline trades. Those trades had
different characteristics: narrower direction range, scout+validator gated
entries, shorter average holds. The Kronos-optimal params diverge because:

- Kronos trades are more numerous → need smaller ratchet granularity
- Kronos signals are purely directional → benefit from longer runs (wider TP)
- Kronos has no pre-entry retrace gate → initial profit floor can be looser

**Conclusion:** Kronos Hunter should use its OWN TUNING namespace.
Our live TUNING is correct for scout+validator pipeline. Kronos Hunter trades
need `kronos.gate.tp_atr_mult=3.8`, `kronos.guardian.ratchet_step_pips=0.80`,
`kronos.guardian.profit_floor_5p=0.25`, etc.

Exactly what Phase 1.6 in the design spec proposed — now we have concrete values.

## Proposed Kronos Hunter TUNING namespace (for spec update)

```python
# tuning_config.py — new Kronos Hunter namespace
"kronos.gate.sl_atr_mult":             2.17,   # vs global 2.00
"kronos.gate.tp_atr_mult":             3.81,   # vs global 1.50 — let winners run
"kronos.guardian.profit_floor_5p":     0.25,   # vs global 0.70 — early breathing room
"kronos.guardian.profit_floor_8p":     0.94,   # vs global 0.80 — tighten once real
"kronos.guardian.profit_floor_12p":    0.97,   # vs global 0.90
"kronos.guardian.profit_floor_20p":    0.83,   # vs global 0.95 — counter-intuitive (looser at big peak)
"kronos.guardian.ratchet_step_pips":   0.80,   # vs global 3.67 — smooth ratchet
"kronos.guardian.trailing_activation_rr": 0.16, # vs global 0.20
"kronos.guardian.trailing_atr_mult":   0.34,   # vs global 0.30
"kronos.guardian.sl_buffer_pips":      8,      # vs global 1 — wider SL buffer
```

These would activate only for `live_trades.source='kronos_hunter'` trades.
All other trades (scout, snipe, manual) continue using the global namespace.

## Caveats

- Still NO SPREAD COST. ~1.5p × 2,834 = -4,250p. Net after spread: ~+7,065p
  vs baseline +1,792p after spread. Still a **4× improvement** after spreads.
- candle_walk_replay ≠ full guardian. 4-layer threat model, phase cascade,
  retrace state machine are not modeled. These could:
  - Kick out some losing trades earlier → improves both baseline and optimized
  - Prevent some winning rides from continuing → reduces optimized more
- The profit_floor_20p drop (0.95 → 0.83) is counter-intuitive. Optimizer may
  have found a pathological case where locking only 83% at 20p+ peak lets a
  reversal ride back for a re-peak. Worth sanity-check before deploying.
- 500 trials may be under-converged for a 10-dim space; best score plateaued
  but not dramatically. A 1,000-trial run could refine further.

## Validation plan

Before shipping Kronos Hunter with these params:

1. **Walk-forward split** — train on Feb-Mar Kronos signals, test on April
   signals with optimized params frozen. Confirm it doesn't overfit.
2. **Full-guardian sim** — build a guardian simulator that includes the 4-layer
   threat model, re-run both TUNINGs on 2,834 trades. See how much of the
   improvement survives.
3. **Paper trading** — per the spec, Phase 2.0 is 1 week / 30 trades paper.
   With optimized params, target WR ≥ 75% and avg_pips ≥ +3.0.

## 1,000-trial refinement (2026-04-14 post-500)

Re-ran with 1,000 trials (549s). Slight refinement:

| metric | 500-trial | 1000-trial |
|---|---|---|
| composite score | 84.82 | 85.19 |
| win rate | 87.4% | **88.2%** |
| total pips | 11,315 | 10,593 |
| profit factor | 2.19 | 2.17 |
| max drawdown | 220.6p | **207.2p** |

The 1,000-trial settled on slightly less aggressive params — higher WR, lower
MDD, but fewer total pips. More robust for live deployment.

**1,000-trial best params (recommended for live):**
```
gate.sl_atr_mult:                 2.204   (vs global 2.00)
gate.tp_atr_mult:                 3.690   (vs global 1.50)
guardian.profit_floor_5p:         0.547   (vs global 0.70)
guardian.profit_floor_8p:         0.925   (vs global 0.80)
guardian.profit_floor_12p:        0.930   (vs global 0.90)
guardian.profit_floor_20p:        0.820   (vs global 0.95)
guardian.ratchet_step_pips:       1.434   (vs global 3.67)
guardian.trailing_activation_rr:  0.133   (vs global 0.20)
guardian.trailing_atr_mult:       0.283   (vs global 0.30)
guardian.sl_buffer_pips:          8       (vs global 1)
```

## Walk-forward validation (2026-04-14)

Split: TRAIN = Feb 15 – Mar 31 (2,178 trades), TEST = Apr 1 – Apr 14 (656).
Optimized on TRAIN only, applied to held-out TEST.

| dataset | baseline wr | optimized wr | baseline pips | optimized pips |
|---|---|---|---|---|
| TRAIN in-sample | 80.5% | 88.6% | +5,161 | +10,160 |
| TEST OOS | 78.5% | **87.8%** | +881 | **+1,961** |

TEST set gained +1,080p out-of-sample (+2.2× multiple). Per-trade gain:
TRAIN +2.30p/trade, TEST +1.64p/trade. Normalized ratio 0.71 →
**params generalize well**. Raw pip-ratio 0.22 is misleading due to size mismatch.

## Kronos-optimal vs our real trades (2026-04-14)

Applied Kronos-optimal TUNING to our 234 real live trades (Feb 14 – Apr 14),
same candle_walk_replay engine, just different params.

| | current TUNING | Kronos-optimal | Δ |
|---|---|---|---|
| wr | 78.6% | **84.6%** | +6.0% |
| total pips | +740.6 | **+1,239.9** | +499.3 (+67%) |
| profit factor | 1.82 | 2.29 | +0.47 |
| max drawdown | 137.3p | **106.8p** | **-30.5p (DD DROPPED)** |

**Kronos-optimal beats current on OUR trades across every metric AND reduces
drawdown.** Most likely because:
1. Current TUNING was derived from 198 trades — 2,834 Kronos signals give
   the optimizer 14× more statistical power.
2. Upstream composite_score_v2 has a hard MDD floor (80p) that zeroed
   otherwise-viable candidates on the 198-trade dataset.
3. Params genuinely generalize — smaller ratchet, wider TP, looser early
   floor work across both trade sources.

## Combined portfolio test

Combined: our 234 + 2,790 Kronos-only (44 overlaps deduped by pair+dir±2h).

| | current TUNING | Kronos-optimal | Δ |
|---|---|---|---|
| wr | 80.0% | 87.3% | +7.3% |
| total pips | +6,721 | **+12,456** | +5,734 |

Almost no overlap — only 1.6% of Kronos signals matched our trades.
Kronos and scout find entirely different opportunities.

## CONCLUSION (FINAL — post-review with Tim)

**Ship as `kronos.*` namespace, not global switch.** Even though the
params are better on BOTH Kronos trades and our replayed scout trades,
live deployment requires proving them on Kronos first before extending
to scout. Three reasons:

1. **System integrity.** The 10 params were jointly optimized. They work
   as a system (wider TP needs smoother ratchet needs looser early floor).
   Partial/incremental rollout on scout would break the interaction.
2. **Clean validation path.** Kronos Hunter is a brand-new module with no
   live execution history. Putting optimized params there has zero risk
   to existing trades and gives us first-party production validation.
3. **Recent bug fixes (Apr 14)** — margin-pct formula, is_snipe flag,
   late-snipe retrace gate — need 1–2 weeks to generate clean scout
   baseline data. Only THEN is scout-reoptimization valid.

## Final deployment path

**Phase A — Kronos Hunter with kronos.\* namespace:**
Scout + snipe trades keep current TUNING untouched. Guardian routes by
`live_trades.source`:
- `source IN ('scout','snipe_direct','manual')` → global TUNING
- `source = 'kronos_hunter'` → kronos.* namespace

Ship shadow mode first (records signals to `kronos_signals` table,
no execution) for 2 weeks. Then paper trade 30 Kronos trades. Then
real money at 50% size. Then full size.

**Phase B — scout re-evaluation (2-4 weeks out):**
After today's fixes produce ~50+ clean scout trades, re-run V2 optimizer
on THAT fresh dataset with Kronos-scaled scoring. If it independently
converges to params close to current Kronos-optimal → high confidence
for global switch. If it diverges → keeps scout on current values,
learn what's different.

## Kronos.* namespace params (locked for Phase A)

```python
# tuning_config.py — Kronos Hunter namespace, active for source='kronos_hunter'
"kronos.gate.sl_atr_mult":                2.20,
"kronos.gate.tp_atr_mult":                3.69,
"kronos.guardian.profit_floor_5p":        0.55,
"kronos.guardian.profit_floor_8p":        0.93,
"kronos.guardian.profit_floor_12p":       0.93,
"kronos.guardian.profit_floor_20p":       0.82,
"kronos.guardian.ratchet_step_pips":      1.43,
"kronos.guardian.trailing_activation_rr": 0.13,
"kronos.guardian.trailing_atr_mult":      0.28,
"kronos.guardian.sl_buffer_pips":         8,
```

## Next step

Invoke `superpowers:writing-plans` to convert the design spec
(`docs/superpowers/specs/2026-04-14-kronos-scout-component-design.md`)
plus these validated params into an ordered implementation plan.
