---
type: pattern
created: 2026-03-26T22:03:50
updated: 2026-04-12T08:15:21
tags: [learning-sentry]
links: []
status: active
---

# learning-sentry — Learnings


## 💡 EUR_USD churned 11 times today (36% WR, -35.9 pips) while cooldown gate failed to prevent re-entry
**Date:** 2026-03-26T22:03:50
**Type:** discovery
**Tags:** post-mortem, 2026-03-26, churning, eur-usd, gate-failure, indicator-gap

> [!tip] DISCOVERY
> 2026-03-26 post-mortem: EUR_USD had 11 trades (4W/7L, 36% WR, -35.9 net pips). Min gap between entries was 56 minutes, average 111 min. The 2-hour cooldown gate after a loss on the same pair appears to be bypassed or not enforced. This is the single biggest driver of losses today. AUD_USD S5 with indicators was 75% WR (+11.1 pips). EUR_USD S16 without bb_width data was 44% WR (-26.8 pips). Fan state expanding = 67% WR (9 trades) vs empty/null fan = 27% WR (11 trades). 100% of 23 trades have NULL finding_id (orphaned). 83% of trades have NULL indicator snapshot. Validation gate1/gate2 fields are all NULL - validator not recording pass/fail data.


---

## 💡 Expanding fan state is highly predictive: 67% WR vs 27% WR for empty/null fan state
**Date:** 2026-03-26T22:04:02
**Type:** discovery
**Tags:** post-mortem, 2026-03-26, fan-state, indicator, snipe-filter

> [!tip] DISCOVERY
> 2026-03-26 data: Trades with fan_state='expanding' had 6W/3L (67% WR). Trades with fan_state empty/null had 3W/8L (27% WR). All trades today were 'sell' direction. fan_state='contracting' had 1W/0L (100%, but single trade). fan_state='stable' had 1W/1L (50%). This suggests the snipe_direct entry filter should REQUIRE fan_state in ('expanding') for sell entries, or at minimum not allow entries with empty fan state. The bb_width gate (6.0 pips) cannot be evaluated for 83% of trades due to NULL indicator data - this is a critical gap.


---

## 💡 GBP_JPY churned 6x on 2026-03-27 with cooldown gate failure — 2W/4L net -43.8p
**Date:** 2026-03-28T10:22:38
**Type:** discovery
**Tags:** post-mortem, 2026-03-27, churning, gbp_jpy, cooldown-gate, s16, finding-id-regression

> [!tip] DISCOVERY
> 12 trades on 2026-03-27, 25% WR (3W/9L), -127.7 net pips. GBP_JPY traded 6 times (avg 41min gap), 2W/4L, net -43.8p. The 2h-after-loss and max-3/day cooldown gates did NOT fire. S16 setup went 0/4 (-89.2p). All trades were SELL direction. BB width analysis: winners avg 17.9p vs losers 14.2p — raising gate to 10p would filter 3 losers, 0 winners. finding_id was NULL on 100% of trades — traceability regression.


---

## 💡 BB width gate at 10 pips would filter 3/9 losers with 0 winner casualties on 2026-03-27
**Date:** 2026-03-28T10:22:45
**Type:** discovery
**Tags:** post-mortem, 2026-03-27, bb-width, indicator-analysis, gate-optimization

> [!tip] DISCOVERY
> Indicator analysis for 2026-03-27: Winners avg BB width 17.92 pips, Losers avg 14.16 pips. At 8p gate: filters 2L/0W. At 10p gate: filters 3L/0W. At 12p gate: filters 4L/1W. Current gate is 6.0 pips — far too permissive. Recommend raising to 10 pips for optimal loss filtering without winner impact. RSI also showed divergence: winners avg 69.9 vs losers 41.2 — losers were selling into oversold conditions.


---

## 💡 GBP_JPY churned 6 trades in 3.5h averaging 42min apart with -43.8 pips; cooldown gate failure confirmed on 2026-03-27
**Date:** 2026-03-28T22:12:39
**Type:** discovery
**Tags:** post-mortem, 2026-03-27, churning, gbp-jpy, cooldown-gate, s16

> [!tip] DISCOVERY
> On 2026-03-27, GBP_JPY was traded 6 times (2W/4L, -43.8 pips net) with avg interval of 0.7 hours between entries. The 2h cooldown gate and max-3/day-per-pair limit both failed to engage. S16 setup went 0/4 on the day (-89.2 pips). Overall day: 12 trades, 25% WR, -127.7 pips. Dead market entries (BB width < 8 pips) accounted for 2 losses. Indicator snapshot now populated on 100% of trades (0 NULL). BB width winners avg 17.9 pips vs losers 14.2 pips.


---

## 💡 S16 SAR flip setup 0% win rate on 2026-03-27: 0/4 trades, -89.2 pips — needs immediate scout threshold review
**Date:** 2026-03-28T22:12:44
**Type:** discovery
**Tags:** post-mortem, 2026-03-27, s16, setup-performance, scout

> [!tip] DISCOVERY
> S16 (SAR flip) was the worst performing setup on 2026-03-27 with 0 wins out of 4 trades and -89.2 total pips (-22.3 avg). All 4 S16 trades were on GBP_JPY sell side. V4_CRITERIA_MET was 1/3 (33.3% WR, -26.7 pips). Only S15 (50% WR, +4.7 pips) and S13 (100% WR, +27.0 pips) were profitable. The S16 signal appears to be generating false SAR flips in ranging/choppy conditions.


---

## 💡 CRITICAL: finding_id is NULL on 100% of 2026-03-27 trades (0/12) — watch-to-trade linkage pipeline broken
**Date:** 2026-03-28T22:15:05
**Type:** discovery
**Tags:** post-mortem, 2026-03-27, finding-id, regression, pipeline

> [!tip] DISCOVERY
> On 2026-03-27, zero out of 12 trades had finding_id populated. This means no trade can be traced back to its originating watch suggestion, completely breaking condition effectiveness analysis. Indicator snapshot data IS populated (100% coverage, confirmed post-2026-03-26 fix), but the finding_id linkage was either never functional or has regressed. This must be fixed in snipe_direct to enable the learning loop.


---

## 💡 GBP_JPY churned 6 trades in 3.4h on 2026-03-27, avg gap 41min, net -43.8 pips — cooldown gate did not fire
**Date:** 2026-03-29T22:13:02
**Type:** discovery
**Tags:** post-mortem, 2026-03-29, churning, GBP_JPY, cooldown-gate, S16

> [!tip] DISCOVERY
> Post-mortem 2026-03-29 analyzing 2026-03-27 (12 trades, 25% WR, -127.7 net pips). GBP_JPY had 6 trades with only 41min avg gap between entries despite 2h cooldown rule. 4 of 6 were losses. S16 setup went 0-for-4 losing 89.2 pips. finding_id NULL on 100% of trades — traceability fully broken. Indicator snapshots populated on 100% of trades (post-fix success). RSI shows clear separation: winners avg 69.9 vs losers 41.2. BB width winners avg 17.9 pips vs losers 14.2 pips.


---

## 💡 finding_id NULL on 100% of trades — trade-to-watch traceability completely broken since snipe_direct refactor
**Date:** 2026-03-29T22:13:11
**Type:** discovery
**Tags:** post-mortem, 2026-03-29, finding_id, traceability, regression

> [!tip] DISCOVERY
> All 13 trades analyzed (2026-03-27 + 2026-03-29) had finding_id=NULL. Watches exist and were matched by fuzzy pair+direction+time, but snipe_direct is not writing finding_id back to live_trades at trade creation. This makes automated post-mortem attribution unreliable and prevents closing the feedback loop to validators. This is a regression — finding_id was working pre-refactor.


---

## 💡 finding_id NULL on 100% of trades on 2026-03-30 - watch tracing broken
**Date:** 2026-03-30T22:14:29
**Type:** discovery
**Tags:** post-mortem, 2026-03-30, finding-orphan, regression

> [!tip] DISCOVERY
> Cannot trace trades to watches directly. All 4 trades have finding_id=NULL. Matched via proximity but this breaks audit trail.


---

## 💡 67%% of losses on 2026-03-30 triggered off stale-flagged watches - stale enforcement gate missing
**Date:** 2026-03-30T22:15:40
**Type:** discovery
**Tags:** post-mortem, 2026-03-30, stale-watch, bb-expanding, finding-orphan

> [!tip] DISCOVERY
> 3 losses, 2 had stale_flagged_at set on matched watch. System executed trades against expired market theses. bb_expanding condition at 0%% WR (0/3). finding_id NULL on 100%% of trades. Winner had RSI 32.4 vs loser avg 48.0 suggesting RSI extremes predict better.


---

## 💡 finding_id NULL on 100% of 2026-03-31 trades — watch-to-trade linkage completely broken, blocking condition-level learning
**Date:** 2026-03-31T22:51:07
**Type:** discovery
**Tags:** post-mortem, 2026-03-31, finding-id, regression, churning, gbp-jpy

> [!tip] DISCOVERY
> 22 trades on 2026-03-31: 59.1% WR (13W/9L) but -51.7 net pips. finding_id is NULL on all 22 trades — snipe_direct is not populating the watch reference. This means Phase 5 (condition effectiveness) cannot run. GBP_JPY churned 7 trades (-10.5 pips) despite cooldown gate. S5 setup (manual) was best at 75% WR. Win rate improving trend: 25%(3/27) -> 47.8%(3/26) -> 59.1%(3/31) but losses are 2x larger than wins on average.


---

## 💡 GBP_JPY cooldown gate failure: 7 trades in single day despite max-3/day rule, avg 59min gap
**Date:** 2026-03-31T22:51:14
**Type:** discovery
**Tags:** post-mortem, 2026-03-31, churning, cooldown-gate, gbp-jpy, gate-failure

> [!tip] DISCOVERY
> On 2026-03-31, GBP_JPY had 7 trades (4W/3L) with -10.5 net pips and avg 59 min between entries. The cooldown gate in trading_cycle.py is supposed to enforce max 3 trades/day/pair and 2h wait after a loss. This gate is clearly not firing for GBP_JPY. Possible causes: pair counter reset bug, gate bypass in S5 setup path, or cooldown check only on automated entries not manual.


---

## 💡 Cooldown gate NOT enforcing 3/day limit: USD_CHF had 7 trades, EUR_AUD 7 trades on 2026-04-01
**Date:** 2026-04-01T22:12:53
**Type:** discovery
**Tags:** post-mortem, 2026-04-01, cooldown-gate-failure, churning, finding-id-gap, mfe-gap

> [!tip] DISCOVERY
> On 2026-04-01, the pair cooldown gate (max 3 trades/day per pair, 2h after loss) failed to limit trades. USD_CHF: 7 trades, -17.8 net pips. EUR_AUD: 7 trades, -40.6 net pips. USD_JPY: 6 trades. Churning accounted for 36.4% of losses. Additionally, ALL 29 trades have finding_id=NULL meaning zero watch-to-trade tracing is working. MFE is also NULL on all trades — guardian cannot protect profits it cannot measure. BB width gate at 6.0 pips: winners avg 21.27 pips vs losers avg 13.66 pips, suggesting raising gate to 10-12 pips could help. JPY pair BB widths are sub-1 pip on M1 which may indicate a calculation bug in snipe_direct for JPY pairs.


---

## 💡 finding_id NULL on 100% of trades Mar26-Apr3 — trade-to-watch linkage completely broken
**Date:** 2026-04-04T13:13:49
**Type:** discovery
**Tags:** post-mortem, 2026-04-04, finding-id, pipeline-gap, critical

> [!tip] DISCOVERY
> Analyzed 114 trades from 2026-03-26 to 2026-04-03. Every single trade has finding_id=NULL, meaning zero trades are linked to their originating watch suggestion. This makes automated condition effectiveness analysis impossible and indicates snipe_direct or the trading cycle is not writing finding_id when executing trades. 93 of 114 trades (81.6%) matched to stale watches via time proximity. Additionally, max_favorable_excursion_pips is NULL on 100% of trades, preventing guardian leak detection. Indicator snapshot coverage is 76.3% (87/114 trades have bb_width populated). Priority fix: ensure trading_cycle writes finding_id on every trade entry.


---

## 💡 Churning remains top loss driver — 10 pair-day instances with 4+ trades, most net negative
**Date:** 2026-04-04T13:14:13
**Type:** discovery
**Tags:** post-mortem, 2026-04-04, churning, cooldown-gate, priority-fix

> [!tip] DISCOVERY
> Week of Mar 26 - Apr 3: Found 10 pair-day instances where the same pair was traded 4+ times in a single day. Worst offenders: EUR_USD 11 trades on Mar 26 (-35.9 pips), EUR_AUD 7 trades on Apr 1 (-40.6 pips) and 7 on Apr 2 (-34.2 pips), GBP_JPY 6 trades on Mar 27 (-43.8 pips). The cooldown gate (2h after loss, max 3/day per pair) is clearly not preventing this. On Apr 3, GBP_JPY had 2 losses with only 1.3h gap between entries — cooldown should have blocked the 2nd trade. Total estimated churning cost: ~167 pips lost on churned pairs.


---

## 💡 ema_cross_above (69.6% WR) and ema_cross_below (57.7% WR) are most predictive watch conditions; watch_trigger and story conditions near 0%
**Date:** 2026-04-04T13:14:21
**Type:** discovery
**Tags:** post-mortem, 2026-04-04, condition-effectiveness, validator, ema-cross

> [!tip] DISCOVERY
> Condition effectiveness analysis across 114 trades matched to watches by time proximity: Top 3 conditions — ema_cross_above: 23 watches 69.6% WR, ema_cross_below: 57 watches 57.7% WR, bb_expanding: 87 watches 55.8% WR. Bottom 3 — watch_trigger: 5 watches 20% WR, story_has_opportunity: 2 watches 0% WR, story_opportunity_score: 2 watches 0% WR. The ema_fan_state condition (48.1% WR) and close condition (48.1% WR) are actually counterproductive. Recommendation: weight ema_cross conditions and bb_expanding more heavily in validator scoring, and consider dropping story-based conditions.


---

## 💡 finding_id NULL on 100% of trades for 7+ consecutive days - watch-to-trade linkage completely broken
**Date:** 2026-04-04T22:13:03
**Type:** discovery
**Tags:** post-mortem, 2026-04-03, finding-id, traceability, regression

> [!tip] DISCOVERY
> Post-mortem 2026-04-03: All 5 trades (and all 91 trades from Mar 27 to Apr 3) have finding_id=NULL. Watch suggestions exist (5 matched by instrument+time proximity) but the trade pipeline is not writing finding_id. This means no automated traceability from trade back to the watch that triggered it. Orphan matching by instrument+time works as fallback but is imprecise. Root cause: likely snipe_direct or trading_cycle not passing finding_id through to live_trades on insertion. Priority fix needed.


---

## 💡 Indicator snapshot coverage only 40% on Apr 3 - regression from expected 100% post-Mar-26 fix
**Date:** 2026-04-04T22:13:10
**Type:** discovery
**Tags:** post-mortem, 2026-04-03, indicators, regression, bb-width

> [!tip] DISCOVERY
> Post-mortem 2026-04-03: Only 2/5 trades have bb_width, rsi, stoch_k populated. 3 trades have NULL indicators. After the 2026-03-26 fix, indicator snapshots should be 100%. BB width data shows winners avg 0.0011 (very narrow, likely pip-denominated issue) vs losers avg 0.0774. One dead market loss detected. RSI winners avg 35.0 vs losers 31.1. Stoch K winners 44.4 vs losers 36.2. The 60% missing indicator data prevents reliable gate analysis.


---

## 💡 finding_id NULL on 100% of trades persists 10+ days — learning loop fully broken
**Date:** 2026-04-05T22:11:38
**Type:** discovery
**Tags:** post-mortem, 2026-04-06, finding-id, learning-loop, critical

> [!tip] DISCOVERY
> 7-day analysis (Mar 30 - Apr 6): 79 closed trades, 43W/32L (54.4% WR), -201.8 net pips. finding_id NULL on 100% of trades blocking all watch-to-trade tracing. Risk/reward severely inverted: avg win +4.3 pips vs avg loss -10 to -42 pips. Churning detected on 9 pair-days with 4+ trades. Dead market entries (BB width < 8 pips) account for 25% of losses. Top recommendation: fix finding_id population in snipe_direct before any other optimization.


---

## 💡 finding_id NULL on 100% of trades (7d) - watch-to-trade tracing completely broken
**Date:** 2026-04-06T22:12:15
**Type:** discovery
**Tags:** post-mortem, 2026-04-06, finding-id, pipeline-gap, critical

> [!tip] DISCOVERY
> All 82 closed trades in the last 7 days have finding_id=NULL. This means watch_suggestions are never being linked to executed trades. The trade-to-watch pipeline is disconnected. Without this link, condition effectiveness cannot be measured, stale watch detection cannot work, and the learning loop is blind. Root cause likely in snipe_direct or trading_cycle not writing finding_id on trade creation. PRIORITY: Fix finding_id population immediately.


---

## 💡 EUR_AUD chronic churning: 4-7 trades/day on multiple days with negative net pips
**Date:** 2026-04-06T22:12:24
**Type:** discovery
**Tags:** post-mortem, 2026-04-06, churning, EUR_AUD, cooldown-gate, gate-failure

> [!tip] DISCOVERY
> EUR_AUD churned on Apr 1 (7 trades, -40.6 pips), Apr 2 (6 trades, -34.2 pips), Apr 6 (4 trades, -6.9 pips). Also GBP_JPY (7 trades, -10.5 pips on Mar 31) and USD_CHF (7 trades, -17.8 pips on Apr 1). The cooldown gate (2h after loss, max 3/day) is not catching these. Possible gate failure or gate being bypassed by manual entries. 18.2% of all losses in last 7 days attributed to churning.


---

## 💡 finding_id NULL on 100% of trades for 12+ consecutive days — watch-to-trade tracing completely broken
**Date:** 2026-04-07T22:11:30
**Type:** discovery
**Tags:** post-mortem, 2026-04-07, finding-id, traceability, critical

> [!tip] DISCOVERY
> All 70 trades in the last 7 days have finding_id=NULL. This means: (1) condition effectiveness cannot be measured per-trade, (2) weak_conditions and stale_watch failure buckets are blind, (3) the validator feedback loop is broken. The watch_suggestions table HAS outcome data via trade_outcome column (21 watches with outcomes in 30 days), but the reverse link from live_trades to watches does not exist. This is the single highest-priority fix for improving win rate — without traceability, no learning loop can function. BB width analysis shows winners avg 0.096 vs losers avg 0.080 (raw), suggesting the 6.0 pip gate is too loose. 30-day WR is 46.7% with -516 pips net.


---

## 💡 Dead market filter caught EUR_AUD loss at 6.34 pip BB width - current 6.0 gate barely missed it; winners avg 17.24 pips vs losers 6.34 pips
**Date:** 2026-04-08T22:12:06
**Type:** discovery
**Tags:** post-mortem, 2026-04-08, bb-width, dead-market, indicator-gap

> [!tip] DISCOVERY
> Date: 2026-04-08. 4 trades, 2W/2L, 50% WR. EUR_AUD trade 4904 lost with BB width 6.34 pips - just above the 6.0 gate. Winners averaged 17.24 pip BB width vs losers 6.34 pips (2.7x ratio). Raising gate to 8.0 would have filtered this loss without touching winners. finding_id still NULL on 100% of trades (day 13+). max_favorable_excursion_pips still NULL on all trades - guardian leak detection remains impossible. EUR_GBP scout trade had NULL indicators entirely - scout source does not populate indicator snapshots.


---

## 💡 Scout-sourced trades have zero indicator data - scout pipeline skips snipe_direct indicator snapshot
**Date:** 2026-04-08T22:12:13
**Type:** discovery
**Tags:** post-mortem, 2026-04-08, scout, indicator-gap, regression

> [!tip] DISCOVERY
> Date: 2026-04-08. Trade 4896 (EUR_GBP sell, scout source) had NULL for bb_width, rsi, atr, stoch_k. Entry_price was 0.0 which is also anomalous. All 3 snipe_direct trades had indicators populated. This means the scout entry path bypasses the indicator snapshot logic entirely. This is a regression or a never-implemented feature for scout entries. Without indicators, failure attribution cannot classify scout losses properly.


---

## 💡 2026-04-09: Perfect 7W-0L day (100% WR, 27.1 pips) but finding_id NULL on all 7 trades — watch tracing broken
**Date:** 2026-04-09T22:13:26
**Type:** discovery
**Tags:** post-mortem, 2026-04-09, perfect-day, finding-id-broken, churning-flag

> [!tip] DISCOVERY
> Date=2026-04-09. 7 trades, all winners. 100% win rate, 27.1 net pips. USD_CHF: 4 trades (S16 setup, all wins, 15.8 pips). EUR_AUD: 3 trades (S1/S5 setup, all wins, 11.9 pips). BB width avg for winners: 14.79 pips — well above 6.0 gate. RSI avg 32.4 (bearish bias confirmed). All indicator snapshots populated (0 gaps). CRITICAL: finding_id is NULL on 7/7 trades — the watch-to-trade linkage is completely broken. Proximity matching works but is fragile. USD_CHF flagged for churning (4 trades) but net positive so not harmful today. Fan state was expanding on all trades, aligned with sell direction.


---

## 💡 2026-04-09: Trend reversal — 100% WR today vs 42.9% past 2 days. Weekly pips still net negative (-96.1).
**Date:** 2026-04-09T22:14:05
**Type:** discovery
**Tags:** post-mortem, 2026-04-09, weekly-trend, recovery, pips-asymmetry

> [!tip] DISCOVERY
> Weekly trend: Apr 9: 7W-0L (100%, +27.1p), Apr 8: 2W-2L (50%, +7.2p), Apr 7: 3W-4L (42.9%, -32.2p), Apr 6: 3W-4L (42.9%, -15.6p), Apr 5: 0W-1L (0%, -42.7p), Apr 3: 3W-2L (60%, +3.6p), Apr 2: 11W-6L (64.7%, -43.5p). Today was a strong recovery day but the week is still net negative. Apr 2 had 18 trades with 64.7% WR but -43.5 pips — winners are too small relative to losers. USD_CHF S16 setup was the star today (4 trades, all wins, 15.8 pips). EUR_AUD S1/S5 also strong (3 wins, 11.9 pips). The system needs to maintain today quality while addressing the pips-per-winner vs pips-per-loser asymmetry visible in earlier days.


---

## 💡 EUR_AUD churning: 13 trades in week with net -11.1 pips despite 69% win rate - single large loss (-29.2 pips) wiping all gains
**Date:** 2026-04-12T08:15:13
**Type:** discovery
**Tags:** post-mortem, 2026-04-12, churning, EUR_AUD, bb-width, finding-id

> [!tip] DISCOVERY
> Week of Apr 6-10 2026: EUR_AUD had 13 trades (W=9 L=4) but net -11.1 pips. The pair averaged 6.7h between entries but had clusters of rapid re-entries. One large loss on Apr 7 (-29.2 pips on trade 4848) wiped cumulative gains. Cooldown gate appears insufficient - pair should have been locked after 3rd trade per day. finding_id NULL on 100% of trades - watch traceability still broken. S16 setup performed excellently (91% WR, +14 pips) while unknown setup trades were 0% WR. Losers had HIGHER avg BB width (16.79 pips) than winners (13.36 pips) - current BB gate at 6.0 is not filtering losses effectively.


---

## 💡 finding_id still NULL on 100% of trades as of Apr 10 - watch-to-trade traceability completely broken
**Date:** 2026-04-12T08:15:21
**Type:** discovery
**Tags:** post-mortem, 2026-04-12, finding-id, pipeline-gap, regression

> [!tip] DISCOVERY
> All 32 trades in the Apr 6-10 week have finding_id=NULL. This means no trade can be directly traced back to the watch that triggered it. Fuzzy matching by pair+time was used as fallback but is unreliable. All Apr 10 USD_CHF trades matched to watch 1901 which was flagged stale on Apr 8 - 2 days before the trades executed. This is a critical pipeline gap: the snipe/trigger system is not writing finding_id back to live_trades. Without this linkage, condition effectiveness analysis (Phase 5) is impossible.


---
