# Scout Analyst Learnings

## 2026-03-26

---
date: 2026-03-26
agent: scout-analyst
type: discovery
summary: ema_velocity >= 0.005 threshold is structurally impossible for EUR_AUD, AUD_JPY, AUD_USD
context: Watch 1727 (EUR_AUD) scanned 533 times at 96.1% criteria hit rate but never triggered because ema_velocity sits at 0.0019 vs 0.005 target (38% of threshold). Real-world velocity range for these pairs is 0.002-0.004/bar. The 0.005 threshold is effectively unreachable under normal market expansion for slow pairs. Same issue observed on AUD_JPY watches (#1725, #1726). Recommend: set ema_velocity threshold to 0.003 for EUR_AUD/AUD_USD/AUD_JPY, 0.004 for GBP_JPY/USD_JPY.
evidence: Watch 1727 velocity=0.001917 vs target 0.005; Watch 1725 velocity=0.001965 vs target 0.005; Watch 1728 same pattern
tags: validator,ema_velocity,threshold,EUR_AUD,AUD_JPY,watch_conditions
universal: true
---

---
date: 2026-03-26
agent: scout-analyst
type: discovery
summary: S16 EUR/USD is profitable London session (05-11 UTC) and destructive NY session (12-20 UTC)
context: On 2026-03-26, S16 EUR/USD London trades (05:18-11:41 UTC) went 4W/1L net +12.9 pips. S16 NY trades (12:37-19:51 UTC) went 0W/4L net -42.7 pips. The afternoon trades showed losses of -12.8, -12.5, -0.7, -16.7 pips. EUR/USD appears to be in a sustained bearish trend with persistent intraday reversals/buying during NY session. Adding a no_new_entry_after_17_UTC filter to S16 would have converted today from -26.8p to approximately +12.9p on EUR/USD alone.
evidence: S16 trades: 05:18 +6.4p, 06:17 -6.8p, 07:15 +2.1p, 08:17 +1.1p, 11:41 +13.1p, 12:37 -12.8p, 13:34 -12.5p, 18:01 -0.7p, 19:51 -16.7p
tags: S16,EUR_USD,session_filter,london,ny_session,churning
universal: false
---

---
date: 2026-03-26
agent: scout-analyst
type: correction
summary: All live trades have finding_id=NULL — scout and execution pipelines are completely disconnected
context: On 2026-03-26, all 23 live trades have finding_id=NULL. The scout_findings.snipe_created field is 0 for all 45 alerts. The watch_suggestions table (17 entries) is populated from the validator cycle independently. The S16/V4/S5 execution pipelines run in parallel to the scout workflow without any cross-referencing. This makes retrospective analysis of scout quality impossible — cannot determine which scout alerts led to winning vs losing trades. The fix requires execution code to stamp finding_id at the time of trade entry by looking up the most recent matching scout_findings record.
evidence: SELECT COUNT(*) FROM live_trades WHERE date(entry_time)='2026-03-26' AND finding_id IS NULL = 23 (all trades)
tags: data_integrity,finding_id,scout_findings,pipeline,attribution
universal: true
---

---
date: 2026-03-26
agent: scout-analyst
type: discovery
summary: Validator uses bb_expanding==True (boolean) only — no BB width threshold in watch conditions creates execution gate conflict
context: 100% of the 17 watch conditions created today use bb_expanding==True (boolean). None use a numeric BB width threshold (bb_bandwidth >= X pips). The SNIPE DIRECT gate enforces 6.0 pip minimum at execution. This creates a conflict: a watch can trigger when BBs are minimally expanding, then the SNIPE DIRECT gate blocks execution because width is insufficient. Adding bb_bandwidth >= 4.0 (JPY pairs) or bb_width >= 0.003% (non-JPY) as a required watch condition would align the watch trigger with the execution gate and prevent false triggers.
evidence: bb_width now captured in live_trades (avg 0.0055 for S5 AUD/USD on 2026-03-26). SNIPE DIRECT gate passed at 20.2 pips for AUD_JPY.
tags: validator,bb_width,bb_expanding,watch_conditions,execution_gate,alignment
universal: true
---

---


## 2026-03-27T17:09:15.352654 — Cooldown gate fail-open bug + S16 0% WR day + per-pair limit not enforced on SNIPE DIRECT

2026-03-27: 25% WR (3W/9L, -127.7 pips). Three critical issues found: (1) Cooldown gate has timestamp parsing bug - fromisoformat() fails on nanosecond precision timestamps (e.g. '2026-03-27T14:11:40.485847192'), causing 5 trades to bypass cooldown (fail-open). (2) S16 went 0/4 for -89.2 pips today, now 4/17 (23.5% WR) over 3 days for -116 pip total destruction. S16 enters without fan confirmation (fan_state empty/stable, story_score=0). (3) GBP_JPY had 6 trades despite documented max 3/day - SNIPE DIRECT path bypasses per-pair daily limit. Additionally, scout pipeline remains fully disconnected for 2nd consecutive day - 0/40 findings linked to trades, 0/20 watches triggered. All trades came via SNIPE DIRECT path.

Tags: scout, daily-report, 2026-03-27, cooldown-bug, S16, churning, pipeline-disconnect

---

## 💡 bb_width stored as percentage not pips — BB gate non-functional for 2nd consecutive day; story_score=0 on all trades due to missing field propagation
**Date:** 2026-03-30T17:10:01
**Type:** discovery
**Tags:** scout, daily-report, 2026-03-30, bb-width, story-score, pipeline-disconnect

> [!tip] DISCOVERY
> 2026-03-30: 4 trades, 1W/3L, -19.0 pips. bb_width values 0.001-0.139 (percentage) vs 6.0 pip gate threshold. All story_score=0 because flight recorder missing story_score/entry_type/fan_state fields on all 13 pairs. S16 on GBP_JPY now 0-for-6 across 2 days (-53.1p). USD_JPY Watch 1752 armed 20+ times Grade A/B but never executed. Pipeline still fully disconnected: 54 findings, 27 watches, 0 triggers, 0 finding-linked trades.


---

## 🔧 S16+GBP_JPY should be suspended: 0-for-6 over 2 sessions totaling -53.1 pips
**Date:** 2026-03-30T17:10:11
**Type:** correction
**Tags:** scout, S16, GBP_JPY, suspension, 2026-03-30

> [!warning] CORRECTION
> GBP_JPY S16 results: 2026-03-27 had 4 losses (-43.8p), 2026-03-30 had 2 losses (-9.3p). All entries were SELL with confidence 43-48, story_score=0. The setup is consistently failing on this pair. Recommend blacklisting S16+GBP_JPY until story_score pipeline is fixed and confidence gate implemented.


---

## 💡 2026-03-31: 57% WR but -54.6p net — avg win +6.7p vs avg loss -16.8p reveals critical R:R inversion
**Date:** 2026-03-31T17:11:28
**Type:** discovery
**Tags:** scout, daily-report, 2026-03-31, rr-inversion, bb-width-bug, churning

> [!tip] DISCOVERY
> 21 trades today. Win rate improved to 57% from 25% prior days, but pips deeply negative. Root causes: (1) BB width gate still non-functional (stored as price ratio not pips — carried from 3/30), (2) GBP_JPY churned 6 trades for -13.4p net including a -28.2p S15 counter-trend loss, (3) S5 manual trades bypass daily pair limit allowing 5 GBP_JPY entries. Top 3 losses (-28.2, -25.6, -23.2p) = 77p of damage. A 15-pip max-loss cap would have saved ~47 pips. S5 manual was best setup at 71% WR / +23.5p. All automated trades still have story_score=0 and finding_id=NULL.


---

## 🔧 BB width gate has been non-functional for 6+ days — stored as price ratio not pip value
**Date:** 2026-03-31T17:11:37
**Type:** correction
**Tags:** bb-width, gate, bug, critical, recurring

> [!warning] CORRECTION
> BB width values in live_trades range 0.0003-0.315 (price ratio format). The 6.0-pip gate threshold reads these values and always passes. JPY pairs show higher ratios (0.06-0.31) while USD pairs show 0.0003-0.008. Fix: either convert to pips at storage (multiply by 10000 for non-JPY, by 100 for JPY) OR change gate threshold to ratio (e.g., 0.004 for majors, 0.10 for JPY). Reported on 3/30 and still unfixed on 3/31.


---


---

### 2026-04-01: Tuning Dashboard — Log ALL parameter changes
**Type:** improvement
**Universal:** true

When you adjust ANY parameter (thresholds, gates, weights, rules), you MUST log it:

```python
from tuning_logger import log_tuning_change
log_tuning_change(
    param="guardian.rule6_peak_threshold",  # dotted: category.param_name
    value="5.0",
    previous_value="3.0",
    reason="Rule 6 firing too early on trades that recover after E100 test",
    approved_by="guardian"
)
```

Categories: gate.*, watch.*, scout.*, validator.*, guardian.*, snipe.*, manual_trade.*, fix.*
Types: param_change, new_gate, new_feature, new_rule, bug_fix, revert, removal

This feeds the tuning dashboard in admin Performance panel. Without it, changes are invisible and unmeasurable. See collective/patterns/2026-04-01.md for full documentation.

---

## 💡 2026-04-01: 100% of validator watches use BB as boolean, zero use numeric width threshold — validator never enforces minimum BB pip width
**Date:** 2026-04-01T17:09:47
**Type:** discovery
**Tags:** scout, daily-report, 2026-04-01, bb-width, validator, churning

> [!tip] DISCOVERY
> 29 trades, 56% WR, -53.2p net. All 22 watches use bb_expanding==True or bb_squeeze_break==True. None use bb_width>=X. USD_CHF had triple-entry bug (3 identical S1 trades in 35s). EUR_AUD S1 lost -38.2p — worst single trade. S15 was best setup at 80% WR. System averages +4.6p wins vs -9.5p losses (0.48:1 RR inversion). Story scores now populated on most trades (improvement from yesterday). All 29 trades were SELL direction.


---

## 💡 79 watch-triggered snipes blocked by missing market picture data on 2026-04-02 — largest pipeline gap
**Date:** 2026-04-02T17:10:30
**Type:** discovery
**Tags:** scout, pipeline-gap, market-picture, 2026-04-02

> [!tip] DISCOVERY
> 28 watches created with 7 conditions each, but 79 snipe execution attempts failed with 'no market picture (fan data required for snipe)'. This is the #1 reason watches are not converting to trades. The watch system works correctly but the execution handoff lacks access to current indicator data. Fix: ensure snipe execution always has access to latest indicator snapshot.


---

## 💡 R:R inversion worsening: 0.22:1 on Apr 2 (wins avg 3.0p, losses avg 13.4p) despite 69% WR
**Date:** 2026-04-02T17:10:34
**Type:** discovery
**Tags:** scout, rr-ratio, profitability, 2026-04-02

> [!tip] DISCOVERY
> 16 trades on 2026-04-02 with 69% win rate but -20.4 net pips. Avg win = +3.0 pips, avg loss = -13.4 pips. This is worse than Mar 31 (0.40:1). The system picks direction correctly but TP targets are too tight and SL too wide. Need minimum TP distance or trailing stop. S16 was best at 80% WR / +25.9p.


---

## 2026-04-03T17:10:37.430837 — Scout-to-trade attribution completely broken — all 5 trades on 2026-04-03 have finding_id=NULL despite matching scout findings

**Type**: discovery  
**Context**: 10 scout findings fired on EUR_USD (7 EARLY_WARNING) and GBP_JPY (3 CRITERIA_MET) with story scores of 45-70. 5 trades executed on those same pairs in the same directions. Yet finding_id is NULL on all trades. The automated pipeline isn't linking scout detections to trade executions. Additionally, 3 of 5 trades classified as 'unknown' setup despite having story=70 (should be V4-type). pnl_pips also records 0.0 for these trades despite valid USD P&L.  
**Tags**: scout, daily-report, 2026-04-03, attribution-bug, pipeline-gap

---

## 2026-04-03T17:10:37.431792 — S16 (44% WR, -92.8p) and V4_EARLY_WARNING (47% WR, -103.9p) are persistent 30-day losers

**Type**: discovery  
**Context**: Over the last 30 days, S16 has 25 trades at 44% WR and -92.8 net pips. V4_EARLY_WARNING has 17 trades at 47% WR and -103.9 pips. Both setups are consistently negative. Today's S16 GBP_JPY trade entered with story=0 and lost. Recommendation: raise S16 sniper threshold to 15, require V4_EW story>=50 and 3/4 thesis gates.  
**Tags**: scout, daily-report, 2026-04-03, setup-performance, S16, V4_EARLY_WARNING

---

## 💡 Apr 6: Scout-trade direction mismatch — 44 BULL alerts, 7 SELL trades, 0% pipeline conversion
**Date:** 2026-04-06T17:11:59
**Type:** discovery
**Tags:** scout, daily-report, 2026-04-06, pipeline-disconnect, direction-mismatch

> [!tip] DISCOVERY
> All 44 scout findings today were bullish (EUR_USD, JPY pairs, USD_CHF bear) but all 7 executed trades were SELL direction. 0 watches triggered. EUR_AUD churned 4x in 4 hours with no cooldown applied. USD_CHF watch hit 71% criteria but never triggered. 100% of watch BB conditions are boolean (no width threshold). Last 3 triggered watches (30d) were all losses. Gate logging absent on Sunday session. WR=43%, net -15.6 pips / -85.51.


---

## 2026-04-08T17:11:25.337172 — BB width gate proved predictive: tight BB entry (0.00063) lost while wider BB entries won. Watch system 0/17 triggers for 2nd straight day.

**Type**: discovery
**Tags**: scout, daily-report, 2026-04-08, bb-width, pipeline-disconnect, watch-trigger

Apr 8: 4 trades (2W/2L, +7.2p). EUR_AUD S1 trade #4904 entered with bb_width=0.00063 (squeeze) and immediately reversed for -0.5p. Both winners had bb_width >= 0.001. 64 scout findings, 17 watches created, 0 triggered. Pipeline disconnect persists. bb_expanding condition is strongest win discriminator (82% WR when present vs 29% in losses). Only 1/17 watches used bb_bandwidth threshold; rest use boolean only. NZD_USD had highest sniper scores (76.7 avg) but 0 watches/trades — routing gap.

---

## 💡 2026-04-09: USD_CHF blind spot - 4 wins +16.2p with zero scout coverage; watch TRADE_NOW pipeline still disconnected
**Date:** 2026-04-09T17:10:39
**Type:** discovery
**Tags:** scout, daily-report, 2026-04-09, pipeline, blind-spot

> [!tip] DISCOVERY
> Perfect 7/7 day (+27.1p). USD_CHF had 4 snipe_direct wins but 0 scout findings/alerts — complete scout blind spot. EUR_AUD watch reached peak_progress=1.0 with TRADE_NOW verdict (conf=1.6) but no auto-execution occurred — same pipeline disconnect since at least 2026-04-07. 30-day watch data shows criteria_hit_rate>=40% correlates with 80% WR vs 47% for lower. No watches use BB width threshold — all use boolean bb_expanding only (62% WR vs 33% without). Recommend: (1) audit scout pair coverage for USD_CHF, (2) fix watch-to-execution handoff, (3) add bb_width minimum to watch conditions.


---

## 💡 2026-04-13: 8W/0L/2-open +22.3p. BB used as boolean in 82.6% of 30d watches vs 0.5% width-threshold. Scout-source entry_price=0 bug hid ~$174 of wins.
**Date:** 2026-04-13T17:09:12
**Type:** discovery
**Tags:** scout, daily-report, 2026-04-13, bb-width, entry-price-bug

> [!tip] DISCOVERY
> All 10 trades today SELL on USD_CHF/EUR_CHF/EUR_AUD. Disabled momentum_trap+oscillator gates would have blocked 10+ real winners (RSI=16 Stoch=0 called exhausted, market disagreed). Three scout_direct trades #5294 #5300 #5438 logged entry_price=0.0 due to V3 'NO LIVE CHART RECEIVED' window 14:47-16:58 UTC; trades filled correctly but DB kept zeros. Conditions >=7: 64% WR -2.3p; <7: 60% WR -8.4p — volume helps marginally, quality filter missing. Recs: (1) fix entry_price=0 in scout executor, (2) add bb_width numeric threshold alongside bb_expanding boolean, (3) keep momentum/oscillator gates disabled pending more shadow data.


---

## 💡 Scout pipeline produced 0 executed trades on 2026-04-17 despite 72 findings with sniper_score 70-80
**Date:** 2026-04-17T17:12:18
**Type:** discovery
**Tags:** scout, daily-report, 2026-04-17, pipeline-leak, bb-threshold

> [!tip] DISCOVERY
> Daily scout report 2026-04-17: 72 scout_findings logged with sniper_score up to 80 across 15 pairs, zero were promoted to snipe_leaderboard (snipe_created=0 on all rows, snipe_triggered=0, trade_executed=0). All 6 actual fills came through source=snipe_direct (5) or scout_direct (1). Likely cause: one of today's 18 tuning overrides (most plausibly #178 snipe.direction_source rewire to watch_direction) broke the scout_findings->snipe promoter. Left unfixed, the scout arm is dark. Also reconfirmed BB-threshold propagation bug: watch #1934 has bb_bandwidth 0.0035 in watch_manifest.trigger_conditions but it did not copy into the gradable conditions JSON — 49 of last 72 watches used bb_expanding boolean, only 3 used a width threshold. Third occurrence of this finding.


---

## 💡 Scout-to-snipe promotion broken: 24 findings, 22 with story>=55, 0 snipes created on 2026-04-20
**Date:** 2026-04-20T21:12:53
**Type:** discovery
**Tags:** scout, pipeline, promoter, 2026-04-20, daily-report

> [!tip] DISCOVERY
> Every scout_findings row on 2026-04-20 has snipe_created=0. Story scores were healthy (22/24 >=55, 14/24 at 70+). All 15 closed fills today came via direct sniper triggers or kronos — not a single trade originated from the validator/watch pipeline. Watch queue received only 3 new watches (GBP_JPY, EUR_AUD, USD_JPY) and 0 triggered. Rolling 30-day watch trigger rate is 0.7%. Net result: validator/watch/scout pipeline is currently a no-op on live execution. Primary suspect: scout->snipe promoter worker not running or threshold misconfigured. Secondary: validator conditions use boolean bb_expanding that rarely flips True in time to catch price movement.


---

## 💡 BB width gate in WOULD_BLOCK (disabled) mode let trade 7843 fill at exactly 3.0 pips
**Date:** 2026-04-20T21:12:53
**Type:** discovery
**Tags:** gate, bb-width, tuning-override, 2026-04-20, execution

> [!tip] DISCOVERY
> dashboard.log 2026-04-20 16:15:35 shows: 'SNIPE DIRECT EUR_AUD BLOCKED: BB width 3.0 pips < 3.0 minimum (expanding=None) — dead market, no energy for directional move' immediately followed by 'WOULD_BLOCK (disabled): BB width 3.0 < 3.0 min'. Trade 7843 filled anyway (entry 1.64156, SL 1.64265, TP 1.64068, 50000 units), then resolved as oanda_404_not_found on reconcile (outcome=unknown, 0 pips). The gate already knows this is a dead-market setup. Tuning override: gate.bb_width_min_pips = 3.0 is loaded but enforcement is off. Fix: flip gate.bb_width_enforce to true (or equivalent). Expected impact: prevents ~1 trade/day of dead-market EUR_AUD attempts and removes a known 404 failure path.


---

## 📈 Validator still emits bb_expanding boolean instead of numeric bb_bandwidth threshold in 2 of 3 watches today
**Date:** 2026-04-20T21:12:53
**Type:** improvement
**Tags:** validator, conditions, bb-bandwidth, prompt, 2026-04-20

> [!success] IMPROVEMENT
> Today's watches: #1936 GBP_JPY and #1938 USD_JPY use bb_expanding==True + bb_squeeze_break==True (boolean). Only #1937 EUR_AUD carries bb_bandwidth >= 0.0035 (threshold). 30-day rolling: boolean_only n=350 vs width_threshold n=5 — the boolean dominates 70:1. Boolean-only triggers 0.6% of the time (watches expire before band-flip catches the directional move). Repeat of the same finding already flagged on 2026-04-13 and 2026-04-17. Recommended validator prompt edit: always emit bb_bandwidth >= X pair-scaled threshold alongside the boolean (majors ~0.0030, JPY crosses ~0.05). Do not remove the boolean — add the numeric threshold so the grader has both specificity AND directional confirmation.


---
