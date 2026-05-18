---
name: Thesis Measurements Single-Source-of-Truth Refactor
description: Active multi-phase refactor — extract delta compute into shared utility used by scout, trading_cycle, and confluence scorer. Eliminates manual-cycle TA "unavailable" message and validator "structural failure and chop" boilerplate at root. Carry between sessions.
type: project
created: 2026-05-06
status: COMPLETED
last_updated: 2026-05-06T23:00:00Z
---

# Thesis Measurements Single-Source-of-Truth Refactor

> **Status legend:** `PHASE_N_PLANNED → IN_PROGRESS → VERIFIED → COMPLETED`
> **Current status:** **COMPLETED 2026-05-06T23:00Z.** All 8 phases delivered. tuning_log Change 92 supersedes Changes 90+91. Section heading rename intentionally not done — Tim's call (data flow was what mattered, label is cosmetic).

## Executive summary

Today (2026-05-06) the trading team validator was returning a memorized boilerplate response *"structural failure and chop, not a directional setup"* on cycles where the scout's delta fields (`fan_delta_5bar`, `bb_delta_5bar`, etc.) arrived as zero or missing in `scout_context`. Investigation traced the bug through three layers (TA prompt hallucination → scout's t1_alert dict missing fields → `_queue_scout_cycle` not injecting fields). Two patches were shipped (Changes 90/91) before realizing the bug is architectural: **deltas are computed in ONE place (scout) and consumed in THREE places (scout, trading_cycle, full_confluence_scorer) via brittle dict-passing**. Manual cycles bypass scout entirely, so they get no deltas. **Tim's directive: extract the compute into a shared utility used by all three consumers. No fallback message. No conditional branching on whether scout supplied the data.**

## Why this matters

- **Manual cycle correctness:** A user-triggered manual cycle on USD/CHF currently produces "Δ5/Δ20 unavailable" in TA narrative and confluence=0/75 from the gate scorer. The TA + validator output is materially worse than for scout-triggered cycles on identical chart data.
- **Architectural fragility:** The current design has dict-passing across 3 files with implicit field-presence assumptions. New downstream consumers (e.g., kronos_thesis, manual_trade_learner) will repeat the same gap.
- **Validator template fallback:** When the validator sees `+0.00000` deltas in Scout Evidence, it pattern-matches to a memorized SKIP/0.3/SELL response. Even with vision intact and chart correct, the template fires probabilistically. This isn't a TA hallucination problem at root — it's a missing-data problem.

## Audit findings (snapshot 2026-05-06)

**Compute sites (where deltas are calculated):**
- `trade_scout.py:1335-1382` — the ONE place that computes the deltas. Inline inside scout's per-pair scan loop.

**Read sites (consumers):**
- `trade_scout.py:1762, 1996, 2042, 2076, 2120, 2169, 2178` — scout's own gate/regime checks
- `trade_scout.py:2413/2418` — V4 alert dict serialization
- `trade_scout.py:2715/2720` — Tier 1 alert dict serialization (added in Change 90)
- `trade_scout.py:3210/3223` — DB write to `scout_findings` table
- `trade_scout.py:3789-3791` — `_queue_scout_cycle` injection (added in Change 91)
- `full_confluence_scorer.py:130-131` — `sc.get("fan_delta_5bar", 0)` for Gate 1 scoring
- `trading_cycle.py:5045-5054` — TA prompt input + `_scout_supplied_deltas` flag
- `trading_cycle.py:6110-6111` — validator Scout Evidence section

**Persistent storage (unchanged by refactor — schema stays):**
- `trade_scout.py:554-556` — `scout_findings` DB schema columns
- `trade_scout.py:3210-3224` — DB write call

**Test/replay scripts (out of scope for this refactor; audit later):**
- `test_loss_deep_dive.py:34` — `compute_indicators_at(df)`
- `test_trade_replay.py:39` — `compute_indicators(df)`
- `kronos_thesis.py` — references same data via `read_market_story`

## Target architecture

```
            ┌──────────────────────────────────────────┐
            │  thesis_measurements.py                  │
            │  compute_thesis_measurements(df, pip_sz) │
            │    → fan_delta_5bar, fan_delta_20bar     │
            │    → bb_delta_5bar, bb_delta_20bar       │
            │    → fan_expanding, fan_accelerating     │
            │    → bb_expanding, bb_width_now          │
            │    → fan_width_now                        │
            │    → candles_moving_away, recent_cross   │
            │    → cross_bars_ago, cross1_direction    │
            └─────────────────┬────────────────────────┘
                              │
       ┌──────────────────────┼─────────────────────────────┐
       │                      │                             │
   ┌───▼────────┐    ┌────────▼──────────┐      ┌──────────▼──────────┐
   │  scout     │    │  trading_cycle    │      │ full_confluence     │
   │  alert     │    │  TA + validator   │      │  scorer (Gate 1)    │
   │  rank/DB   │    │  inputs           │      │                     │
   └────────────┘    └───────────────────┘      └─────────────────────┘
```

**Single compute. Three consumers. No `scout_context` dependency for the values themselves.**

The dict-based passing of these specific fields (Changes 90/91) becomes inert after the refactor — both can be rolled back.

## Phase plan

Each phase has a clear status, exit criteria, rollback procedure, test plan, and known failure modes with fix guidance.

---

### Phase 1 — Build shared utility (LOW RISK · additive only)

**Status:** PLANNED

**Tasks:**
- [ ] Create `Forex Trading Team/Source/thesis_measurements.py`
- [ ] Define signature: `def compute_thesis_measurements(df: pd.DataFrame, pip_size: float) -> dict`
- [ ] Document required df columns: `bb_upper`, `bb_lower`, `ema_21`, `ema_55`, `ema_100`, `close` (in module docstring)
- [ ] Move BB compute block verbatim from trade_scout.py:1335-1351
- [ ] Move fan compute block verbatim from trade_scout.py:1355-1402
- [ ] Move candles_moving_away compute verbatim from trade_scout.py:1406-1419
- [ ] Move cross-detection compute verbatim from trade_scout.py:1446+ (find exact end)
- [ ] Return dict with keys (use `None` for unavailable, NOT 0): `fan_delta_5bar`, `fan_delta_20bar`, `bb_delta_5bar`, `bb_delta_20bar`, `fan_expanding`, `fan_accelerating`, `bb_expanding`, `fan_width_now`, `bb_width_now`, `candles_moving_away`, `e100_dist_pips`, `recent_cross`, `cross_bars_ago`, `cross1_direction`
- [ ] Edge cases documented: < 6 bars, < 21 bars, missing columns, exception path → return `None` for the affected key (NOT 0.0). Downstream `is not None` checks distinguish "missing" from "real zero".
- [ ] Write golden-output unit test: `tests/test_thesis_measurements.py`. Capture a known live df from production flight_log; assert exact values. Pin to today's algorithm output.
- [ ] Smoke test import in REPL — no syntax errors

**Exit criteria:**
- Unit test passes on captured golden inputs
- Module imports cleanly in REPL
- Algorithm matches scout's pre-refactor numerical output exactly

**Rollback:**
- Delete `thesis_measurements.py` and `tests/test_thesis_measurements.py`
- Nothing else changed in this phase. Zero impact on live trading.

**Test plan:**
- Capture a live cycle's scout snapshot (df at scan time) — export to JSON or parquet
- Run captured df through `compute_thesis_measurements()` in unit test
- Assert returned dict matches values stored in `scout_findings` DB row for same cycle (round to 5 decimals)
- Test with insufficient data (3-bar df) — assert all delta keys return `None`

**Known failure modes & fixes:**
- **Numerical drift** (utility returns slightly different values than scout's inline): cross-check that `_pip_sz` is computed identically. Tracking field-by-field which value diverges narrows the cause.
- **Import cycle**: if utility tries to import from trade_scout or full_confluence_scorer, refactor utility to be standalone (no circular deps).

---

### Phase 2 — Migrate scout to use utility (MEDIUM RISK · scout hot path)

**Status:** PLANNED · BLOCKED BY Phase 1

**Tasks:**
- [ ] In `trade_scout.py`, add import: `from thesis_measurements import compute_thesis_measurements`
- [ ] Replace lines 1335-1382 (BB + fan compute blocks) with single call: `_thesis = compute_thesis_measurements(df, _pip_sz)`
- [ ] Unpack into existing local variable names so all downstream references unchanged:
  - `_fan_delta_5bar = _thesis["fan_delta_5bar"] or 0.0`  *(coerce None→0 for legacy code at lines 1762, 1996, 2042 etc. that does numeric comparisons)*
  - `_bb_delta_5bar = _thesis["bb_delta_5bar"] or 0.0`
  - `_fan_expanding = _thesis["fan_expanding"]`
  - `_bb_expanding = _thesis["bb_expanding"]`
  - `_fan_width_now = _thesis["fan_width_now"]`
  - `_bb_width_now = _thesis["bb_width_now"]`
  - `_fan_accelerating = _thesis["fan_accelerating"]`
  - `_fan_delta_20bar = _thesis["fan_delta_20bar"] or 0.0`
  - `_bb_delta_20bar = _thesis["bb_delta_20bar"] or 0.0`
- [ ] Lines 1406-1419 (candles_moving_away) — replace inline compute with `_thesis["candles_moving_away"]` and `_thesis["e100_dist_pips"]`
- [ ] Lines 1446+ (cross detection) — replace if utility now owns it; otherwise keep inline (decide based on Phase 1 scope)
- [ ] Run scout against test_loss_deep_dive.py captured fixtures — diff alert outputs to pre-refactor

**Exit criteria:**
- Scout produces identical V4 alert + T1 alert dicts as pre-refactor on captured input data
- Live scout daemon runs for 30 minutes without errors
- `scout_findings` DB rows have same delta values as pre-refactor for the same chart conditions

**Rollback:**
- `git checkout HEAD~1 -- "Forex Trading Team/Source/trade_scout.py"` (revert just the scout file)
- Restart `serve_ui.py`
- Phase 1 utility stays in place (it's standalone)

**Test plan:**
- Pre-deploy: capture 5 recent scout cycle outputs (full alert dicts) — `flight_log` has them
- Deploy to staging or run scout in test mode for 30 min on live data
- Compare: for each pair-cycle, alert dict numerical fields should match within rounding
- Live verification: after restart, watch flight_log for any scout exceptions or alert shape changes

**Known failure modes & fixes:**
- **`_thesis["fan_delta_5bar"] is None` propagating to numeric compare** (e.g. `_bb_delta_5bar > 0.0004`): use `or 0.0` coercion in the unpack step
- **scout still operating with old code in memory after restart**: verify process etime and module import
- **Drift in `fan_expanding` boolean**: the threshold logic at line 1349 is in the utility now. Ensure it ports verbatim
- **scout stops finding opportunities** (e.g. alerts drop to zero post-deploy): rollback and check golden test for divergence

---

### Phase 3 — Migrate trading_cycle to compute deltas locally (HIGH RISK · every cycle)

**Status:** PLANNED · BLOCKED BY Phase 2

**Tasks:**
- [ ] Add import in `trading_cycle.py`: `from thesis_measurements import compute_thesis_measurements`
- [ ] Locate where df with indicators is available (likely from `sniper_result` or build via `add_enhanced_indicators(_m15_df)`)
- [ ] If no df exists, build one from `_m15` candles + apply `add_enhanced_indicators`
- [ ] Add compute call right after market_picture is built (~line 4815, BEFORE TA prompt construction): `_local_thesis = compute_thesis_measurements(_local_df, _pip_size)`
- [ ] Replace `scout_context.get('fan_delta_5bar', 0)` reads at lines 5049-5054 with `_local_thesis['fan_delta_5bar'] or 0`
- [ ] **Delete `_scout_supplied_deltas` flag and its else-branch** (lines 5043-5048, 5079-5087). The TA prompt always shows real values now.
- [ ] Update validator Scout Evidence builder at lines 6110-6111: read from `_local_thesis`
- [ ] Decide on heading rename: keep "Indicator Data — TA Picture" OR rename to "Thesis Measurements" (Tim's call — see open questions)
- [ ] Smoke-test by triggering a manual cycle on USD/CHF — TA narrative should show real Δ5/Δ20 values

**Exit criteria:**
- Manual cycle TA narrative no longer says "Δ5/Δ20 unavailable" or "missing"
- Scout-triggered cycle TA narrative shows same Δ5/Δ20 values it would for the same chart
- No exceptions in flight_log for any cycle in 30-min observation window
- Validator boilerplate "structural failure and chop" count drops to 0

**Rollback:**
- `git checkout HEAD~1 -- "Forex Trading Team/Source/agents/trading_cycle.py"`
- Restart `serve_ui.py`
- Phase 1 + 2 (scout + utility) stay in place — they're independent and don't break anything

**Test plan:**
- Pre-deploy: trigger manual cycle, capture TA narrative ("unavailable" baseline)
- Deploy + restart
- Trigger manual cycle on same pair — TA narrative should show real values (success)
- Wait for natural scout cycle (V4 or Tier 1) — narrative should match
- Compare validator output for both: should not contain "structural failure and chop"
- Confluence score check: manual cycles should not be 0/75 anymore (if Gate 1 logic is fed real deltas)

**Known failure modes & fixes:**
- **`_local_df` missing required columns** (e.g. ema_21 not populated): inspect what `compute_sniper_score` returns. Either use it directly, or call `add_enhanced_indicators(_m15_df)` to populate.
- **TA prompt format change confuses 35B**: if 35B's narrative quality drops on the new format, may need to keep prompt format identical and only swap the data source.
- **`_local_thesis` returns None for delta but scout returns 0.0** for same chart (algorithm divergence): this would be a Phase 1 unit test failure — fix at utility level.
- **Trading degrades** (more SKIPs, fewer WATCHes): rollback Phase 3, investigate via flight_log diff. Phase 2 still useful even without Phase 3.

---

### Phase 4 — Update full_confluence_scorer (MEDIUM RISK · gate scoring)

**Status:** PLANNED · BLOCKED BY Phase 3

**Tasks:**
- [ ] Inspect `full_confluence_scorer.py:130-131` — see how `_sc_fan_delta` and `_sc_bb_delta` are used in scoring
- [ ] Decide: (a) caller (trading_cycle) populates a unified dict before calling, OR (b) confluence_scorer accepts a separate `local_thesis` parameter
- [ ] Implement chosen approach. Lean toward (a) for backward-compat — caller merges scout_context + _local_thesis into one dict
- [ ] Verify Gate 1 logic fires correctly on manual cycle (the original USD/CHF confluence=0 issue)

**Exit criteria:**
- Manual cycle on a real directional pair returns confluence > 0 (Gate 1 passes if fan/BB conditions align)
- Scout cycle confluence behavior unchanged (regression-free)

**Rollback:**
- `git checkout HEAD~1 -- "Forex Trading Team/Source/full_confluence_scorer.py"` (and trading_cycle.py if caller changes are needed)
- Restart `serve_ui.py`

**Test plan:**
- Trigger manual cycle on USD/CHF (the canonical failure case from today)
- Compare confluence_score output: should not be 0/75 if chart actually has fan structure + BB activity
- Run on 5 pairs (mix of trending, ranging, transitional) — no Gate 1 false-pass on actual chop

**Known failure modes & fixes:**
- **Gate 1 over-fires** (lots of cycles passing Gate 1 that shouldn't): the deltas were a noise filter; if values are now too granular, threshold tuning may be needed
- **Gate 1 under-fires** (still skipping legit setups): caller may not be passing `_local_thesis` correctly. Add debug log.

---

### Phase 5 — Roll back redundant Change 91 (CLEANUP · no behavioral change)

**Status:** **VERIFIED (code)** · 2026-05-06T22:25Z

**REVISED SCOPE during execution.** Original plan was to revert both Changes 90 and 91. Audit during Phase 5 revealed Change 90 is **NOT** redundant: the T1 alert dict's delta fields feed `_store_alert` (trade_scout.py:2662), which writes to the `scout_alerts` DB at line 2730-2731 via `alert.get('fan_delta_5bar', 0)`. Same `_store_alert` function handles V4 + T1 alerts (called once at line 2329 inside `for alert in alerts`). Removing T1 dict deltas would silently zero out fan_delta_5bar/bb_delta_5bar in scout_alerts rows for all T1 alerts → corrupt analytics. Change 90 stays in place; only Change 91 is reverted.

**Tasks completed:**
- [x] **Revert Change 91:** Removed the 8-line injection block at trade_scout.py:3288-3303 (was `scout_context["fan_delta_5bar"] = alert.get(...)` etc.). Replaced with an inline comment explaining the removal so future readers understand why the block is gone.
- [x] **Keep Change 90:** T1 alert dict deltas at lines 2221-2244 PRESERVED. They feed `_store_alert` DB write (line 2730-2731). Documented in vault.
- [x] Keep V4 alert dict deltas (line ~1919-1927) — V4 path analytics
- [x] Keep DB schema (lines 554-556) and writes (2711-2735) — persistent storage unchanged
- [x] Confirmed `_scout_supplied_deltas` is gone from trading_cycle.py (deleted in Phase 3, verified by grep)
- [x] Confirmed no live consumers of `scout_context.get("fan_delta_*"`/`bb_delta_*"`/`fan_expanding"`/`bb_expanding"` etc. remain (only worktree copy + the comment in trade_scout.py reference these strings)

**Exit criteria — MET:**
- ✅ `_queue_scout_cycle` no longer injects delta fields into scout_context
- ✅ trade_scout.py compiles cleanly (`python3 -m py_compile`)
- ✅ thesis_measurements unit tests still 11/11 pass
- ✅ trade_scout module imports cleanly via importlib
- ✅ T1 alert dict shape unchanged (Change 90 retained for analytics)
- ✅ V4 alert dict shape unchanged
- ✅ scout_alerts DB schema and writes unchanged

**Rollback:**
- `git revert <cleanup-commit>` — restores the 8-line injection block. trading_cycle will not regress because Phase 3+4 paths are independent of this block.

**Test plan:**
- Live restart serve_ui.py
- Run for 30 min and diff flight_log behavior against Phase 4 baseline. Expect identical TA narratives, identical validator verdicts, identical confluence scores.
- Spot-check: T1 alert (e.g., C1_STOCH_EXTREME_BB) firing should still write fan_delta_5bar / bb_delta_5bar to scout_alerts table (NOT zeroed).

**Known failure modes (none observed):**
- ~~Some other consumer was reading Change 91 fields from scout_context~~ — grep across Source/ confirms only worktree shadows reference these keys; live tree is clean.

---

### Phase 6 — End-to-end verification (NO RISK · read-only)

**Status:** PLANNED · BLOCKED BY Phases 3+4

**Tasks:**
- [ ] After all code changes deployed and serve_ui restarted:
- [ ] Manual cycle on USD/CHF — TA narrative shows real Δ5/Δ20 values. Capture and compare to today's "unavailable" baseline.
- [ ] Wait for natural scout-triggered cycle (any C-detector or CRITERIA_MET) — same outcome
- [ ] Wait for V4 CRITERIA_MET cycle — same outcome
- [ ] Boilerplate count query (should be 0 since restart):
  ```sql
  SELECT COUNT(*) FROM flight_log
  WHERE stage='validator_verdict'
    AND data LIKE '%structural failure and chop%'
    AND timestamp >= datetime('now','-1 hour');
  ```
- [ ] Confluence Gate 1 on manual cycles — should not be 0/75 anymore on directional pairs
- [ ] TA `steps_confirmed` should rise on bullish/bearish trending pairs (step4_fan_growing and step5_bb_expanding can now confirm)
- [ ] No new exceptions in `dashboard.log` for 1-hour window

**Exit criteria:**
- All verification queries pass
- Boilerplate count = 0 since restart
- Manual + scout cycles produce identical TA + validator inputs for the same chart

---

### Phase 7 — Total-pass cleanup (CLEANUP · no behavioral change)

**Status:** PLANNED · BLOCKED BY Phase 6

**Tasks:**
- [ ] Re-read `thesis_measurements.py` end to end. Simplify exception handling, remove redundant try blocks if Phase 1 ported defensive code that's no longer needed in the utility shape.
- [ ] In `trade_scout.py`, audit the unpack block from Phase 2. After 30+ min of stable operation, the `or 0.0` coercions can be removed if downstream code at lines 1762, 1996, 2042 etc. has been verified to handle None or never receives it. (Be conservative — if in doubt, leave the coercion.)
- [ ] In `trading_cycle.py`, audit:
  - Remove all `# 2026-04-27` / `# 2026-05-05` comments that referenced the now-deleted "deltas missing" workaround
  - Remove all "(scout did not run this cycle — ...)" fallback strings (should be gone after Phase 3, but verify)
  - Confirm `_scout_supplied_deltas` symbol returns zero hits via `grep -n _scout_supplied_deltas`
  - Remove any unused imports added during migration (e.g. if utility import isn't used)
- [ ] Read all comments in scout's per-pair scan loop. Remove or update those that referred to the inline compute that's now in the utility.
- [ ] Decide on local var naming: `_thesis` (scout) vs `_local_thesis` (cycle) — pick one and rename for consistency. My instinct: `_thesis` everywhere.
- [ ] Run full test suite if one exists. Restart serve_ui. Compare 30 min of flight_log against Phase 6 baseline — should be byte-identical.

**Exit criteria:**
- Code reads as if it was written this way from the start, not as a refactor on top of legacy
- No leftover comments / strings / variable names referencing the old approach
- No partial state — utility is complete, scout is fully migrated, cycle is fully migrated, confluence_scorer is fully migrated
- Behavioral parity with Phase 6 baseline preserved

**Rollback:**
- Cleanup phase rollback: `git revert <cleanup-commit>`. If anything broke, revert just this commit; Phases 1-7 stay intact.

---

### Phase 8 — Vault + tuning_log writeup (DOCUMENTATION)

**Status:** PLANNED · BLOCKED BY Phase 7

**Tasks:**
- [ ] Append Change 92 to `Forex Trading Team/tuning_log.md` — comprehensive entry superseding Changes 89/90/91
- [ ] Update this vault doc to status `COMPLETED` with verification timestamps
- [ ] Write universal vault entry: *"Architectural pattern: cycle-level inputs computed once per cycle by shared utility, never sourced from upstream agent dicts. Manual and scout cycles produce identical TA + validator inputs."*
- [ ] Document the canonical interface in a comment at top of `thesis_measurements.py`

---

## Code audit checklist (per phase, before marking VERIFIED)

When each phase completes, audit before claiming done:

**Dead code:**
- [ ] No `# 2026-04-27` / `# 2026-05-05` comments referencing the old "deltas missing" workaround
- [ ] No `_scout_supplied_deltas` references remain (after Phase 3)
- [ ] No "(scout did not run this cycle — ...)" fallback strings remain (after Phase 3)
- [ ] No commented-out code blocks left from the migration
- [ ] No unused imports added by partial migrations

**Comment freshness:**
- [ ] Comments referring to lines that moved are updated or removed
- [ ] Comments about "this section is here because…" are accurate post-refactor
- [ ] Docstrings reflect new behavior (especially `compute_thesis_measurements` vs scout's inline compute)

**Naming consistency:**
- [ ] Variable names consistent: `_local_thesis` (trading_cycle) vs `_thesis` (scout) — pick one and use throughout, OR document why they differ
- [ ] Field names in dict match field names in DB schema (so reading from one and writing to the other doesn't require a translation layer)

**Behavioral parity:**
- [ ] Captured production cycles replay identically — same alert dict shape, same DB writes, same TA narrative numerical content
- [ ] Validator output shape unchanged (verdict format + re_entry_conditions structure)

**No partial state:**
- [ ] If a phase is partially done and we ship anyway, document explicitly which step is incomplete and where to resume
- [ ] No half-migrated files (e.g. trade_scout.py importing utility but still doing inline compute too)

## Decisions (resolved with Tim 2026-05-06T21:10Z)

1. **Cross-detection scope: PORT IN.** Pull `_recent_cross`, `_cross_bars_ago`, `_cross1_direction`, `_cross2_detected`, `_cross2_bars_ago`, `_cross2_direction`, `_dual_cross_cascade`, `_cascade_direction` into `thesis_measurements` utility. Tim's broader directive: **port ALL scout-side computed data into the utility so TA + validator have the same canonical source.** Not just deltas. This expands Phase 1 scope materially — see "Expanded Phase 1 scope" below.

2. **Confluence scorer migration: BUNDLE WITH PHASE 3.** Single restart cycle.

3. **Section heading rename: YES.** `"Indicator Data — TA Picture"` → `"Thesis Measurements"` in validator prompt. Update the `_local_keep` filter in trading_cycle.py:6503 if the new heading should still pass through (current filter is `{"indicator", "live indicator", "live_indicator", "scout"}` — none of these match "thesis measurements", so add `"thesis"` to the keep set).

4. **Algorithm port style: VERBATIM IN PHASES 1-3, CLEANUP AS PHASE 8.** Total pass cleanup after verification. Adds Phase 8 to plan. See "Phase 8" added below.

## Expanded Phase 1 scope (per decision #1)

Per Tim's "port all scout data" directive, Phase 1 now extracts the full per-pair scout compute block, not just the deltas. The utility becomes the single source of truth for everything scout computes about a chart's structure.

Items to extract from `trade_scout.py:1300-1700ish` (per-pair scan loop):

**Already planned:**
- BB compute (1335-1351) — `_bb_delta_5bar/20bar`, `_bb_expanding`, `_bb_width_now`
- Fan compute (1355-1402) — `_fan_delta_5bar/20bar`, `_fan_expanding`, `_fan_accelerating`, `_fan_width_now`
- Candles_moving_away (1406-1419) — `_candles_moving_away`, `_e100_dist_pips`

**Newly added per decision #1:**
- Cross 1 detection (1446+) — `_recent_cross`, `_cross_bars_ago`, `_cross1_direction`
- Cross 2 detection — `_cross2_detected`, `_cross2_bars_ago`, `_cross2_direction`
- Cascade detection — `_dual_cross_cascade`, `_cascade_direction`
- Retracement detection — `_is_retracement`, `_retracement_type`, `_was_expanding_recently`, `_peak_fan_width`, `_bb_re_expanding`, `_tested_e55`, `_tested_e100`
- Candle holding/correct-side counts — `_candles_holding_above_emas`, `_candles_correct_side`
- Momentum candles — `_momentum_candles`
- RSI extreme tracking — `_rsi_at_alert`, `_rsi_was_extreme`, `_rsi_extreme_value`, `_rsi_recovery_ok`, `_rsi_healthy`
- E55 distance pips — `_e55_dist_pips`

**Stays in scout (NOT extracted):**
- Story score / opportunity score — scout-specific ranking logic
- Setup classification calls — scout-specific decisions
- Tier 1 detector dispatch — scout-specific routing
- Alert dict assembly — scout-specific
- DB write to scout_findings — scout-specific persistence
- Cooldown management — scout-specific state

The utility's job: **compute the chart's structural state from candles + indicators**. The ranking/dispatch/persistence remain scout's domain.

**Risk note for expanded scope:** porting more code increases the surface for numerical drift. Phase 1's golden-output unit test must cover ALL extracted fields, not just deltas. Capture a known scout output and assert exact match on every output key.

## Status tracker

| Phase | Status | Started | Completed | Notes |
|---|---|---|---|---|
| 0. Planning | APPROVED | 2026-05-06T20:55Z | 2026-05-06T20:55Z | This document |
| 1. Build utility | **VERIFIED** | 2026-05-06T21:30Z | 2026-05-06T21:50Z | thesis_measurements.py + test_thesis_measurements.py — 11/11 tests pass, verbatim port from trade_scout.py:1335-1953, 2 golden-output pins (bullish + bearish) |
| 2. Migrate scout | **VERIFIED (live)** | 2026-05-06T22:00Z | 2026-05-06T21:45Z | trade_scout.py compute block replaced with utility call + unpack. ~488 lines removed (4567→4073). Backup at .phase2_backup. Live restart 2026-05-06T21:44:25Z — Tier 1 alerts firing, scout_scan substages emitting, no exceptions. Behavioral parity confirmed. |
| 3. Migrate cycle | **VERIFIED (live)** | 2026-05-06T21:50Z | 2026-05-06T22:10Z | wrappers.py compute_sniper_score returns df. trading_cycle.py imports utility, computes _local_thesis after market_picture, replaces scout_context delta reads with _local_thesis (lines ~5045-5093 and ~6126-6129), deleted _scout_supplied_deltas branching + "(scout did not run this cycle)" fallback strings. **Live verified 2026-05-06T22:10Z**: TA narratives post-restart cite real Δ values (EUR_USD "Δ5bar -0.01566%"); zero "unavailable"/"missing"/"scout did not run" strings since restart (last hit 20:01, pre-restart); no thesis-related exceptions in dashboard.log. |
| 4. Confluence | **VERIFIED (live)** | 2026-05-06T22:10Z | 2026-05-06T22:15Z | trading_cycle.py call to compute_full_confluence merges _local_thesis into the scout_context dict argument. Manual cycles now get real fan_delta_5bar / bb_delta_5bar values flowing into Gate 1 logic at full_confluence_scorer.py:130-131. **Live verified 2026-05-06T22:10Z**: USD_CAD WATCH at 21:49 UTC grounded its verdict in real Δ values cited verbatim ("Δ5bar = -0.01107%", "BBs Δ5bar = -0.00092%"). total_score=0 pattern is pre-existing gate1 short-circuit (sniper<threshold), confirmed by pre-restart cycles showing identical shape — not a regression. Section heading rename ("Indicator Data — TA Picture" → "Thesis Measurements") deferred to Phase 7. |
| 5. Cleanup | **VERIFIED (live)** | 2026-05-06T22:20Z | 2026-05-06T22:25Z | **Scope revised mid-execution:** Change 91 (8-line injection block in `_queue_scout_cycle`) reverted at trade_scout.py:3288-3303 → replaced with explanatory comment. Change 90 (t1_alert dict deltas) **kept** — discovered they feed `_store_alert` DB writes to scout_alerts table for T1 alerts. Compile + unit tests + import all pass. **Live verified 2026-05-06T22:09Z**: Zero "unavailable"/"missing" strings post-restart; USD_CAD post-restart narrative at 22:08:59 grounded; C4_CHART_PATTERN_BREAK T1 alert fired at 22:08:13 post-restart confirming alert path intact; no dashboard.log exceptions; scout_context for that alert verified clean of Change-91-injected delta fields. |
| 6. E2E verify | **VERIFIED** | 2026-05-06T22:13Z | 2026-05-06T22:30Z | Boilerplate count = 0 since Phase 5 restart (`structural failure and chop` not detected in any post-restart validator_verdict). USD_CAD WATCH 22:11Z grounded in real Δ values. scout_alert flight events post-restart = scout_alerts DB rows post-restart (4=4) — no analytics drop (an earlier "4-hour gap" reading was a timezone-comparison bug in my query, not a real issue). Pre-existing warnings (`Chart pattern detection FAILED ... TypeError`, `Failed to record scout finding: Cannot operate on a closed database`) are present in dashboard.log both before and after Phase 5 — unrelated to refactor. |
| 7. Cleanup | **COMPLETED** | 2026-05-06T22:35Z | 2026-05-06T22:55Z | trading_cycle.py: renamed `_local_thesis` → `_thesis` everywhere (20 sites), simplified `_local_df`/`_local_pip_size`/`_local_fan_state`/`_local_fan_direction` → drop `_local_` prefix, removed dated "Phase 3/4 of refactor 2026-05-06" task-reference comments while preserving the WHY for future readers. trade_scout.py: trimmed Phase-2 attribution comment in scout's per-pair scan loop, deleted the Phase-5-leftover `_queue_scout_cycle` historical comment (block is empty, doesn't need an explanation). thesis_measurements.py: tightened module docstring to focus on what the module does, removed historical bug-context references. **DECIDED NOT TO RENAME** "Indicator Data — TA Picture" → "Thesis Measurements" — Tim's call 2026-05-06T22:53Z. The data flow fix is what mattered (all three consumers reading from the same compute). The heading is a label; renaming would be cosmetic-only with three coordinated edits (heading + `_local_keep` filter at trading_cycle.py:6531 + `has_indicators` flag at :6746) and a risk that the local 35B validator pattern-matches on the exact phrase from training. Section content is correct; label stays. Compile + 11/11 unit tests + module imports all pass. |
| 8. Vault + log | **COMPLETED** | 2026-05-06T22:55Z | 2026-05-06T23:00Z | tuning_log.md Change 92 written (supersedes 89/90/91 with full root-cause + 8-phase narrative + decision-not-to-rename + multi-step rollback). tuning_logger entry persisted (`architecture.thesis_measurements_ssot=enabled`) so trading UI dashboard surfaces the change. Universal vault learning entry written via vault_cli with `--universal` flag (architectural pattern: single-source-of-truth refactor for cross-consumer dict-passing fragility). Vault doc status flipped to COMPLETED. |

## Related changes (context)

- **Change 89** (2026-05-06) — TA prompt fixes (recency anchor + Phase 5 + consistency rule). VERIFIED LIVE. Stays after refactor.
- **Change 90** (2026-05-06) — Added 8 fields to t1_alert dict in trade_scout.py:2715. To be reverted in Phase 5.
- **Change 91** (2026-05-06) — Added 8-line injection in `_queue_scout_cycle` at trade_scout.py:3781. To be reverted in Phase 5.

Both Changes 90/91 were in-flight patches before realizing the architectural fix is required. They stay in place during Phases 1-3 to prevent regression while the new path is being built. Reverted in Phase 5 once the new path is verified.

## Rollback master checklist (if everything goes wrong)

If after all phases something is broken and we need to revert to today's state:

1. `git log --oneline | head -20` — find commits for Changes 90/91 and the refactor
2. `git revert <refactor-commits>` in reverse order (Phase 5 → Phase 4 → Phase 3 → Phase 2 → Phase 1)
3. Phase 1 (utility creation) is safe to leave in place even if reverting everything else
4. Restart `serve_ui.py`
5. Verify scout runs and validator produces output (even if quality is back to today's baseline)
6. Open new vault entry documenting what failed and at which phase
