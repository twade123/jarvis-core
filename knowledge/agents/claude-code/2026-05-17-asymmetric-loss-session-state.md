# 2026-05-17 Asymmetric Loss Investigation — Session State

**Session focus:** Losers run 2-3× bigger than winners. Find guardian logic or prompt refinement (no gates if possible) to stop trading into exhaustion. Tim explicitly asked for sub-agent-driven deep audit.

**Status:** RESEARCH COMPLETE — design decisions and code changes pending Tim's approval. No code shipped this session.

---

## Headline numbers (30d, validator family = snipe_direct + scout)

- Total trades: 244 | Winners: 38 (≥5p) | Losses: 91 | Net: **-713p (lost money)**
- Asymmetry: avg win +4.8p, avg loss -14.6p, ratio **3.0×** (Tim's "2× intuition" understates it)
- 25 trades closed ≥-20p ("big losers") accounting for -753p of bleed
- Big-loser split: **12 never-positive (NP, -349p) + 13 brief-positive (BP, -385p)**

---

## Ghost replay (LIVE prompt vs 99 historical losers) — DONE

- **Live prompt** = `Forex Trading Team/Prompts/ghost_validator_v1.md` (permissive, iter20f/iter22-derivative, NOT iter36)
- iter36 was the conservative version Tim tested separately on full 30d (252 trades, -190.7p net)
- Output: `/tmp/ghost_v2/LIVE_v1_30d_losers_30d_losers_results.json`
- Result: **68 WATCH (71% of losers would be skipped), 27 TRADE_NOW (residual leakers), 1 SKIP**
- Of 27 leakers: **12 big (≥20p, -376p), 15 small (-10.6p avg, -159p)**
- **Winners-side replay running in background** (PID 1530 at start of session, may still be active). Output: `/tmp/ghost_v2/LIVE_v1_30d_winners_30d_winners_results.json` + log `/tmp/ghost_v2_winners.log`. Needed to confirm winner-side cost.

---

## Rules tested & verdicts

| Rule | Cohort | Catch | Pip impact | Status |
|---|---|---|---|---|
| **V_clf65** (12-feature logistic classifier, gated off) | 25 big losers | 0/25 | -- | **REJECTED** — keep dry-run; 64% FP rate on winners |
| **R3** (trending→retracing flip in records 1-2 + MFE≥3p → BE) | 91 losers | 2/91 | +5.5p / 30d | **REJECTED** — small-sample artifact |
| **R3-broad** (any trending→retracing flip, drop MFE precondition) | 25 big | 19/25 | +768p / 30d but 29% winner kill | **NOT shippable as-is**, separate audit needed |
| **Rule A** (stoch_k ≤10 SELL / ≥90 BUY → skip at entry) | NP cohort | 7/7 indicator-side | +268p / 30d, -38.7p winners | **IS A GATE** — Tim's directive was no gate; awaiting architectural decision |
| **R2 culmination** (JPY × SELL × fan_expanding → skip) | 12 big leakers | 6/12 | +119.6p / 30d | **IS A GATE** — same |
| **Bar2 fan-slippage** (bar2 phase=peak OR retracing + fan_sep_delta ≥1.0p + MFE≥3p → SL→BE) | 13 BP big | 5-7/13 (refined vs raw) | +111p / 30d | **Guardian rule (not a gate)** — paper-test before ship |
| **bar2_phase=peak + bar2_pnl≤-5p** (cleanest single signal) | 4 NP big | 4/4 (100%) | -- (sample n=4) | **Strongest discriminator in cohort**, perfect on this sample, 0 winners killed |

**Key insight from exit-marker hypothesis (Tim's bet):** Marker is present on 87% of losers BUT 63% of winners too. Discrimination is **recency** (within 3-5 bars: losers 68%, winners 18% — 3.8× ratio).

---

## CRITICAL BUG DISCOVERED

**`guardian.entry_marker_fresh` is enabled but NOT WIRED.**

- `tuning_overrides.guardian.entry_marker_fresh_enabled = True`
- State variables initialized in `position_guardian.py:1360-1362` (`_em_fresh_evaluated`, `_em_fresh_armed`, `_em_fresh_lock_price`)
- **No evaluation logic exists in `_evaluate_trade()`** — the FRONT-HALF marker detector was designed with +101.3p / 30d backtest, marked shipped, but never coded into the runtime loop
- This is precisely the rule for Tim's "kill the trade when opp marker is on chart at entry" scenario
- **Silent +101p/30d sitting on the floor**
- Action: wire the rule (task #11)

---

## Friday 2026-05-15 changes audit (~3 trading days live)

| Change | Verdict | Note |
|---|---|---|
| `guardian.widen_oanda_sl_enabled = false` | **KEEP** | Directly responsible for capping tail losses; no catastrophic floor fires since deploy |
| `guardian.rt_loser_pattern_enabled = true` (all sources) | **INVESTIGATE** | Zero fires Friday — either no late-entry exhaustion regime OR silent wiring gap like entry_marker_fresh |
| `gate.fan_exhaustion_logic = direct_geometry` + `min_pips = 4.0` | **KEEP** | Removed ~30 blocks/day; need to monitor for FN reversals |
| `gate.validator_fan_alignment_enabled = false` | **KEEP** | Eliminated 254 blocks w/ 73% FP rate from prior week |
| `gate.snipe_refire_max_gap_minutes = 99999` | **KEEP, monitor** | Effectively disables refire-gap; live data n=0 events Friday |
| `guardian.profit_floor_threshold_pips: 5.0 → 4.5` | **NOT FOUND** | Tim's brief mentioned this; not present in tuning_overrides. Either misnamed or never persisted — verify |
| `guardian.exit_marker_be` (from 2026-05-14) | **TWEAK** | See R1 refinement below |

---

## Exit-marker recovery audit (n=16 in-loss fires, ~24h live cohort)

**Tim's hypothesis ("no recovery after marker") mostly confirmed:**
- Recovered to ≥0: 3 (19%)
- Kill-equivalent: 2 (12%)
- Worsened: 11 (69%)

**Kill-at-market vs current Tighten counterfactual:** Kill wins by **-46.7p** on Friday cohort (-171p tighten vs -124p kill). Scout drives the delta; snipe is roughly break-even.

But: pre-deployment 60-event backtest projected +373p / 30d for tighten. n=16 is too small to override. Don't bulk-flip; instead **gate by pnl-at-fire bucket** (R1 refinement).

**Trade 15509 (-42.2p) smoking gun:** Guardian process restart mid-trade rebuilt marker baseline from current state → all pre-existing opposing markers re-counted as "new" → immediate exit_marker fire AFTER the disaster. Restore-baseline bug.

---

## Top 3 refinement recommendations (ranked by pip leverage)

**R1 — Split `exit_marker_be` action by pnl-at-fire bucket** (highest leverage, ~+34.5p/Friday-cohort saved)
- `fire_pnl > 0` → take-profit (unchanged, 3/3 won)
- `-3 ≤ fire_pnl ≤ 0` → tighten with 1p buffer (recovery zone, 3/3 recovered when in -3 to -6p band)
- `fire_pnl < -3` → **kill at market** (11/13 worsened in this band, kill saves slippage + reduces worst outcomes)

**R2 — Fix guardian-restore baseline bug** (prevents single-trade -42p+ outliers)
- Persist `_em_baseline_marker_times` and `_em_baseline_m15_count` to DB on each tick
- On restore: load from DB instead of recompute from current state

**R3 — Wire `entry_marker_fresh` evaluation** (silent +101p/30d projected)
- FRONT-HALF complement to `rt_loser_pattern`
- At first M15 close after entry: opposing peak_sep within last K=10 bars + reversal candle + price retraced → SL→entry±2p buffer
- This is the exact "kill on marker at entry" scenario Tim described

---

## Architectural question awaiting Tim's decision

**Strict no-gate path:** ship R1 + R2 + R3 + bar2 fan-slippage. Accepts ~-97p/mo from the 3 NP cohort. Net projected ~+250-380p/30d.

**Allow minimal deterministic gate:** add Rule A (stoch_k extreme entry filter). Picks up another ~+97p but it IS a gate. Tim's directive was "no gate if possible."

**Both, but staged:** ship R1+R2+R3+bar2 first, observe live, decide on Rule A after seeing residual.

---

## Active task list

1. DECISION: gate-vs-no-gate architecture for NP cohort (pending Tim)
2. Refine bar2 fan-slippage guardian rule (in_progress)
3. BACKLOG: Fix scout indicator writer (rsi/stoch_k/bb_* NULL on scout-source) (in_progress)
4. BACKLOG: Investigate empty ta_llm narrative on scout-side big losers (pending)
5. BACKLOG: Add MAE-at-bar2 telemetry capture (pending)
6. BACKLOG: Capture H1/H4 trend context at entry (pending)
7. R3-broad audit (separate hypothesis) (pending)
8. CLOSED: V_clf65 cutover REJECTED
9. CLOSED: R3 (as originally specified) REJECTED
10. CLOSED: Verify exit marker presence + build NP guardian picture
11. **CRITICAL BUG: Wire entry_marker_fresh evaluation** (pending)
12. Audit: change exit_marker_be in-loss action from tighten to kill (pending — answered by R1)

---

## Key artifacts

- Ghost replay losers output: `/tmp/ghost_v2/LIVE_v1_30d_losers_30d_losers_results.json`
- Ghost replay winners output: `/tmp/ghost_v2/LIVE_v1_30d_winners_30d_winners_results.json` (in-progress at session pause)
- Winners replay log: `/tmp/ghost_v2_winners.log`
- Leaker feature table: `/tmp/leaker_features.json`
- Part A audit artifacts: `/tmp/part_a_audit/`
- Live prompt file: `Forex Trading Team/Prompts/ghost_validator_v1.md` (has uncommitted exit_marker veto edit — loads from disk at runtime so it IS live)

## Key file references

- Guardian exit_marker_be implementation: `Forex Trading Team/Source/position_guardian.py:2990-3165`
- Guardian entry_marker_fresh state init (no eval logic): `Forex Trading Team/Source/position_guardian.py:1360-1362`
- Marker generation: `Forex Trading Team/Source/backtester/ema_separation.py:1253-1490` (`format_chart_signals`)
- Chart most-recent-marker filter: `Forex Trading Team/Source/chart_generator.py:567-580`
- Tuning params: `Forex Trading Team/Source/tuning_config.py:144-192`

---

## Memory updates this session

- `feedback_guardian_no_exhaustion.md` — Guardian does NOT have real-time exhaustion detection (in-profit rules ≠ exhaustion)
- `feedback_prompt_versioning.md` — Live prompt ≠ iter36 (permissive vs conservative). Always check `ghost_validator_v1.md` on disk.

---

## Resume hooks for next session

1. Check if winners-side ghost replay completed: `ls /tmp/ghost_v2/LIVE_v1_30d_winners_30d_winners_results.json` — if exists, parse verdict distribution to confirm net-positive bracket
2. Tim to decide gate-vs-no-gate architecture (task #1)
3. If approved: implement R1 + R2 + R3 + bar2 fan-slippage as ship package
4. Backlog: scout indicator writer, ta_llm narrative regression, MAE-at-bar2, H1/H4 capture
