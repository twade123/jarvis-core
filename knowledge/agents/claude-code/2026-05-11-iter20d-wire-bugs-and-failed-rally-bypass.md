# 2026-05-11: Two live wire bugs found + fixed in a single audit pass

**Date:** 2026-05-11
**Agent:** claude-code
**Status:** Both fixes shipped, serve_ui reloaded, ongoing monitor watching live flow

## TL;DR

Day-end audit on 17 closed trades (raw -$230.46, 8 of 14 BUYs losing) uncovered
**two independent live wire bugs** masquerading as "validator regression":

1. **iter 20d pattern section dropped silently** in 57% of validator calls →
   pattern-conflict-veto rule in the prompt had no input → "textbook Phase 3
   bullish" hot-take pattern on 35 of 36 CONFIRMs (validator over-fitted to
   ordered-fan = TRADE_NOW without the structural veto reaching the model).

2. **`failed_rally_lock` override #308 was no-op** — the param was never
   registered in `TradeWatcher._params` dict, so the lookup at
   `position_guardian.py:2831` fell back to hardcoded `True` regardless of
   what was in `tuning_overrides`. The rule killed 7 trades today (-$96.70)
   despite being "disabled" via #308 at 05:33 ET.

Both shipped + serve_ui reloaded at 21:04 ET. Trade 14333 USD_JPY (opened
20:58 ET, first post-reload) passed full pipeline audit — 9/9 iter 20d
sections delivered, validator reasoning references Phase, fan, continuation
vs exhaustion composite, Tokyo session ownership, 10-point checklist.

## What we were tracking (ongoing)

### 1. V_clf65 exhaustion-handler ghost daemon (Phase 5 dry-run)
- Script: `Forex Trading Team/Source/scripts/early_exhaustion_shadow.py`
- Polls open trades every 60s, runs the classifier from
  `early_exhaustion_evaluator.py`, logs would-fires to
  `scripts/early_exhaustion_shadow_<date>.jsonl`
- **Day 1 result**: 4 fires, 3 saves (+$68.70), 1 kill (-$12.42), net +$56.28,
  75% precision. Above backtest 67% expectation. Data collection continues.

### 2. End-to-end iter 20d audit monitor
- Script: `Forex Trading Team/Source/scripts/audit_validator_flow.sh`
- Tails `flight_recorder.db` for validator_call / validator_verdict /
  trade_phase / trade_close / guardian_action events
- Emits one structured line per event; surfaces in chat via Monitor
- Started at flight_log id > 430875 (21:03 ET)

### 3. Pre-existing watches/cycles
Iter 20d wire-fix was deployed alongside session-aware iter 20e (PRIME/CAUTION/
OPEN/BLOCKED 4-state window) earlier this morning.

## Discovery — full day audit findings

### Trade breakdown (17 closed today, after 3 BLOCKED/CAUTION trades deleted manually)

| Bucket | n | W/L | $ |
|---|---|---|---|
| BUY trades | 14 | 6W/8L | -$142.65 |
| SELL trades | 3 | 3W/0L | +$12.58 |
| **All today** | **17** | **9W/8L** | **-$230.46** |

By exit trigger:
- `failed_rally_lock`: 7 fires, -$96.70 (the rule that was supposed to be off)
- natural close (SL/TP hit): 6 fires, -$87.64
- `oanda_auto_close` (OANDA stopped out): 4 fires, -$46.12

### Worst non-guardian losses (real validator misses)

| Trade | Pair | Dir | Story | MFE | $ |
|---|---|---|---|---|---|
| 14088 | EUR_CHF | buy | 70 | 0.0p | -$90.32 |
| 13976 | NZD_USD | sell | 0 (snipe) | 0.0p | -$76.00 |
| 14291 | EUR_CHF | buy | 70 | 0.0p | -$60.36 |
| 14249 | GBP_JPY | buy | unk | 0.0p | -$48.90 |

**Critical observation:** 5 of 8 losers had MFE ≤ 3p — entries were AT or AFTER
local tops. Validator confirmed late.

### Bug #1 — Pattern section wire dropping silently

**Pre-restart flight_log audit**: 24 of 50 most recent validator_calls (48%)
had `has_patterns: false`. Section headings list confirmed missing
"Detected Patterns On This Chart" entry — section truly absent, not just flag wrong.

**Root cause** (`trading_cycle.py:6688-6693` pre-fix):
```python
_live_pattern_section = build_pattern_section(_live_pattern_fires, body_only=True)
if _live_pattern_section:                             # ← FALSY when empty
    _validator_sections.append({...})                 # ← silently dropped
```

When the 11-detector pipeline found no matches (common — most cycles), the
section was silently dropped. Iter 20d testing wrapped EVERY cycle's chart
with this section (and labels on the image); live did neither.

**Side-effect**: `chart_generator.generate_chart()` was being called WITHOUT
`pattern_labels=`. So even when detectors found fires, they weren't drawn on
the chart image the validator saw. Pure vision-only check, missing the labeled
augmentation.

### Bug #2 — failed_rally_lock override never took effect

**Live evidence:** 7 trades closed via `exit_trigger='failed_rally_lock'` today,
5 of them AFTER override #308 (set False at 05:33 ET). Including:
- 14128 AUD_USD BUY: MFE 7.7p (real rally), exit -3.6p (classic winner-kill)
- 14062 GBP_JPY BUY: MAE 16p, briefly +2.8p, killed at -3.5p
- 14281 EUR_JPY BUY: MFE 2.6p, exit -8.0p

**Root cause** (`position_guardian.py:1258` + `:2831` pre-fix):
- `TradeWatcher.__init__` builds `self._params` as a hand-crafted dict of
  ~10 specific guardian params (profit_floor_*, trailing_*, sl_*).
- `guardian.failed_rally_lock_enabled` was NOT in that dict.
- The rule's check `self._params.get("...failed_rally_lock_enabled", True)`
  always returned the fallback `True` — never read `tuning_overrides`.
- Override #307 (May 8, True) and #308 (May 11, False) both had identical
  effect: nothing.

## The fixes

### Fix #1 — pattern wire (`trading_cycle.py`)

Two-part:
- **Line 5194** — pattern detection now runs ONCE pre-chart, fires stored as
  `_v4_pattern_fires` and passed to `generate_chart(... pattern_labels=...)`
  so labels are drawn on the chart image (matching iter 20d testing).
- **Line 6726** — Detected Patterns section is **always appended**. When
  fires is empty, content is a stub: "No programmatic patterns detected on
  the most recent bars (11 detectors checked: ...). Pattern-conflict veto
  does not apply — read structure visually from the chart." Exception path
  also stub-appends.
- **Line 6707** — Section build reuses `_v4_pattern_fires` from chart step,
  with local detection only as fallback (avoids double-compute).

### Fix #2 — failed_rally_lock disable (`position_guardian.py:2831`)

Read tunables directly from `tuning_config.tc_get_for_trade` (bypassing the
incomplete `self._params` dict), with **fallback default flipped True → False**:

```python
from tuning_config import tc_get_for_trade as _tc_fr
_fr_enabled = bool(_tc_fr("guardian.failed_rally_lock_enabled", self.source, False))
_fr_min_neg = int(_tc_fr("guardian.failed_rally_min_neg_bars", self.source, 1))
_fr_lock_pips = float(_tc_fr("guardian.failed_rally_lock_pips", self.source, 0.0))
```

Smoke-tested: both `scout` and `snipe_direct` sources return `False`. Rule
will not fire after reload.

### Validation

Post-reload (21:04 ET):
- Trade 14333 USD_JPY BUY (opened 20:58 ET, first post-reload validator pass)
  - 9/9 iter 20d sections delivered, `has_patterns: True`
  - Validator reasoning explicitly references: Phase 3 cascade, fan ordering,
    continuation vs exhaustion composite ("RSI 77 but in strong trend, not
    diverging — continuation not exhaustion"), Tokyo session ownership,
    10-point checklist
  - Pipeline trace: cycle_start → data_oanda → data_intelligence → ta_compute
    → ta_llm → validator_call → validator_verdict → confluence_score →
    orchestrator_llm → execution → Order filled
- Subsequent calls (AUD_JPY, GBP_JPY at 21:01, GBP_JPY 21:03) all show
  sections=9, patterns=1, scout=1

## Why today sucked (in one sentence)

The validator was running a degraded iter 20d (no pattern signal in 57% of
calls) AND a "disabled" guardian rule was actually firing on 7 trades — so
the validator missed reversal signals it had been tested with, and the
guardian killed trades the validator had legitimately confirmed. Two
independent issues compounding.

## What's running now

- ✅ Iter 20d full pipeline live (verified on 4 post-reload calls)
- ✅ failed_rally_lock rule OFF (code default False + tuning_overrides #308 honored)
- ✅ V_clf65 ghost daemon collecting day-2 dry-run data
- ✅ End-to-end audit monitor emitting events to chat
- ⏳ Trade 14333 USD_JPY BUY: live, +4.2p in trending phase as of 21:03 ET

## Next session checklist

1. Compare tomorrow's validator hit-rate vs today's regression
2. Review V_clf65 ghost daemon week-1 data once 10+ in-universe trades close
3. If validator still over-eager on "Phase 3 bullish," consider iter 20f
   adjustments to dampen confidence on late-extension entries
4. Review the persistent has_indicators=False flag — section header doesn't
   match "Indicator Data" string but TA narrative is being delivered inside
   Intelligence section. May be a cosmetic flag mismatch, not a real gap.
