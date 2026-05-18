# Failed-rally rule rewrite — classifier-based exhaustion handler

**Date:** 2026-05-11
**Agent:** claude-code
**Status:** Phase 5 dry-run live; live cutover pending forward-validation

## Summary

The old `failed_rally_lock` guardian rule was disabled 2026-05-11 via tuning
override #308 after 5 live fires netted -20p/-$79 (vs claimed +76.8p in 21d
backtest). The rewrite is a logistic-regression classifier trained on 90d of
real trades, plus a 6-tunable param set wired through `tuning_config.py`. A
standalone shadow daemon dry-runs the rewrite without touching live guardian
code.

## What was wrong with the old rule

1. **No MFE-quality gate** — armed on ANY positive close (a 0.1p "rally"
   counted same as 6p).
2. **No structural read** — fired purely on PnL pattern (neg → pos → neg M15
   closes), no fan-break / ADX / RSI / BB context.
3. **Execution slippage** — `_close_with_reason` market-closes when M1 low
   touches BE; by then bid has already moved past, so "lock at BE" became
   "exit at -1.8 to -3.5p" in practice.
4. **Killed 3 of today's 5 fires** — EUR_CHF 13944 the worst (cut at -1.8p,
   trade went +9.4p afterward = pure winner-kill).
5. **Backtest mirage** — old rule shows +125.6p over 90d in the new
   simulator. Live execution gap is the difference between "lock-touch
   detected at M15 close" vs "modify SL order at peak."

## Methodology — measurement-driven 4-phase iteration

**Phase 1 — Discovery.** Pull 90d + post-tune closed trades, exclude kronos,
measure per-trade: MFE, MFE_bar, MAE, MAE_at_peak, pattern bucket
(never_positive / long_neg_then_brief_pos / short_neg_then_brief_pos /
positive_at_entry), fan_state at peak. Output: distributions per bucket.

**Key finding:** brief-positive pattern is NOT a clean loss signal. 37 winners
share the same pattern as 16 losers. Differentiator is MFE size + indicator
state, not the pattern alone.

**Phase 2 — Multi-indicator classifier.** Snapshot 12 indicators at the
decision bar (peak + first negative close):
- RSI, stoch_K, ADX, MACD_hist
- BB_pos (touching upper/lower/inside), BB_width_ratio
- fan_ordered, fan_inverted, e21_e55_pips, e55_e100_pips, fan_velocity
- candle_vs_e21, counter_color_count, is_reversal_candle
- (+ derived: mfe, mfe_bar, mae_at_peak, decision_bar)

Fit logistic regression on V1-rule-candidate universe (MFE>=3p, brief-pos
pattern, decision_bar<=8). 51 candidates: 41 winners, 10 losers.

**Top discriminating features** (coef magnitude, scaled):
| Feature | Coef | Direction |
|---|---|---|
| mfe | -1.46 | winner+ (bigger peak = winner) |
| bb_pos | +0.91 | loser+ (at BB band = exhaustion) |
| mfe_bar | -0.86 | winner+ (later peak = winner) |
| is_reversal_candle | -0.56 | winner+ (healthy pullback signal) |
| fan_ordered | +0.53 | loser+ (losers fired early, structure intact) |
| rsi | +0.51 | loser+ (less-oversold = less room to run) |
| adx | -0.45 | winner+ (stronger trend = winner) |
| e55_e100_pips | +0.39 | loser+ (late-cascade entries fail) |

mae_at_peak was NOT discriminating (loser p50 -7.95p, winner p50 -7.50p) —
dropped from final design.

**K-means** found 2 loser sub-clusters: exhausted-momentum (high RSI, high
stoch, deep MAE) and late-cascade (high ADX, wide EMA gaps).

**Phase 3 — Variant sweep.** 8 rule variants × 2 cohorts (90d + post-tune).
V_clf65 (classifier P>=0.65) won on every cohort:

| Variant | 90d net | post-tune net | 90d precision |
|---|---|---|---|
| V0 (old rule) | +125.6p | +30.4p | 28% |
| V1 (MFE>=3 alone) | +5.4p | +28.5p | 20% |
| V3 (rule with all gates) | +39.4p | +16.0p | 42% |
| **V_clf65 (classifier)** | **+73.2p** | **+42.7p** | **67%** |
| V_clf70 (conservative) | +70.3p | +32.3p | 75% |

V_clf65: 12 fires, 8 saves, 4 kills, 80% recall.

**Adversarial test on today's 5 fires:** V_clf65 spares ALL — including the
EUR_CHF 13944 winner-kill that the old rule made. Misses the GBP_USD 13809
"slow recovery" save, but that's a different pattern (MFE peaked at bar 12,
outside arm_window=8) and needs a separate rule.

**Phase 4 — Candle-walk.** Hand-verified V_clf65 decisions on 9
representative trades. Kills concentrated in EUR_AUD SELL pair (possible
overfit), small in magnitude (-0.6 to -5.3p). Saves are clean ~+5-12p each.

**Phase 4b — Tier 1 BE-trail sweep (REJECTED).** Initially proposed a Tier 1
universal BE-trail at MFE>=10p with lock at +1.5p. Tim rejected the scope:
universal BE-trail is profit management, not exhaustion handling. Final
design uses ONLY the classifier-gated rule on failing trades.

## Final design (Phase 5)

**Scope:** acts ONLY on trades that aren't recovering. Does NOT touch profit
management (profit floor, trailing SL, partial exits — all owned by existing
systems).

**Trigger conditions (all required):**
- Pattern is `long_neg_then_brief_pos` or `short_neg_then_brief_pos`
- 3.0 <= MFE < 10.0 pips
- decision_bar (first negative M15 close after MFE peak) <= 8 bars from open
- Classifier P(loser | features at decision bar) >= 0.65

**Action when triggered:** modify OANDA SL order to entry + 0.5p in profit
direction. NOT market close — that's what caused the original execution
slippage.

**Path B** for never-positive collapses is a separate future rule. Not in
this rewrite.

## Files added/changed

| Path | Purpose |
|---|---|
| `Forex Trading Team/Source/scripts/failed_rally_discovery.py` | Phase 1 measurement script |
| `Forex Trading Team/Source/scripts/failed_rally_phase2.py` | Phase 2 classifier fit |
| `Forex Trading Team/Source/scripts/failed_rally_phase3_sweep.py` | Phase 3 variant matrix |
| `Forex Trading Team/Source/scripts/failed_rally_phase4_candle_walk.py` | Phase 4 candle-walk |
| `Forex Trading Team/Source/scripts/failed_rally_phase4b_tier1_sweep.py` | Tier 1 sweep (informational) |
| `Forex Trading Team/Source/scripts/early_exhaustion_shadow.py` | Dry-run polling daemon |
| `Forex Trading Team/Source/early_exhaustion_evaluator.py` | Pure-function classifier evaluator |
| `Forex Trading Team/Source/early_exhaustion_classifier.json` | Pinned classifier coefs + scaler |
| `Forex Trading Team/Source/tuning_config.py` | Registered 7 new tunables |

## Tunables (all default-off, dry-run-on)

```
guardian.early_exhaustion_enabled              = False (master switch)
guardian.early_exhaustion_dry_run              = True  (log-only mode)
guardian.early_exhaustion_mfe_min_pips         = 3.0   (rally floor)
guardian.early_exhaustion_mfe_max_pips         = 10.0  (rule ceiling)
guardian.early_exhaustion_arm_window_bars      = 8     (decision_bar limit)
guardian.early_exhaustion_classifier_threshold = 0.65  (P(loser) cutoff)
guardian.early_exhaustion_lock_pips            = 0.5   (SL move target)
```

## Phase 5 dry-run

`early_exhaustion_shadow.py` polls open trades every 60s, runs
`evaluate_trade()` from `early_exhaustion_evaluator.py`, logs FIRE / NEAR_FIRE
events to JSONL at `scripts/early_exhaustion_shadow_<date>.jsonl`. Takes NO
live action — guardian code untouched. Stop file:
`scripts/early_exhaustion_shadow_STOP`.

## Live cutover gates

Before flipping `guardian.early_exhaustion_enabled` to True:
1. Dry-run must show at least 3-5 fires with verifiable outcomes (trade
   closed after fire, can compare sim_pnl vs actual).
2. Per-fire delta distribution matches backtest expectations (saves ~+10p,
   kills <=5p).
3. No "fire on healthy trade" false positives in dry-run.
4. SL-modify execution path verified (the new rule MUST modify SL order, not
   market-close).

## Open questions for next session

- Path B (never-positive hard-cut) — separate rule, separate backtest. 48 of
  79 90d losers are never_positive, avg MAE -19p. Plenty of pip recovery
  potential.
- Slow-recovery pattern (GBP_USD 13809 type) — MFE peaks >8 bars after
  entry. Not handled by current design. Worth investigating after Path B.
- Classifier cross-val AUC was 0.657 ± 0.253 — high variance. More data
  (full 180d cohort) might tighten bounds or expose overfit.
