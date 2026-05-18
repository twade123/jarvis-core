---
type: pattern
updated: 2026-05-15T13:09:33
tags: [guardian, monitoring, trade-monitor]
---

## 🔧 Audit Fix 10/10: E21 trailing stop for tighter profit protection in trending markets
**Date:** 2026-03-20T16:00:00
**Type:** correction
**Tags:** trailing-stop, profit-protection, dynamic-sl, e21, e55, audit-2026-03-20-phase2

Dynamic SL logic updated: when unrealized profit reaches +8 pips AND E21 is available in trending/continuing market state, trailing stop anchor switches from E55±5p to E21±3p.

Root cause: Trade #1930 (EUR_USD) peaked at +13.8 pips but E55±5p trailing was too loose — price reversed all the way through profit back to -0.6 pips. The E55 anchor sits too far from price during strong trending moves, providing no meaningful profit lock.

With E21±3p: SL would have trailed ~8-10 pips from entry once the +8p threshold was reached. Conditional on trending/continuing market state to avoid whipsaws in ranging conditions.

**Evidence:** Trade #1930: +13.8p peak → -0.6p close (E55±5p). Projected with E21±3p: +8-10p locked. ~9-11 pip improvement.

---

## 💡 Guardian role clarified: profit capture and risk management only
**Date:** 2026-03-20T20:00:00
**Type:** discovery
**Tags:** architecture, role-definition, audit-2026-03-20-phase3

Phase 3 audit codified the guardian's role: profit capture and risk management AFTER entry. Guardian does NOT make entry decisions (that's the validator's job via precision snipes). Guardian does NOT assess chart quality (that's the TA's job). Guardian's pre-trade gate (Fix 3) is the one exception — it blocks entries into already-degraded market structure, which is a risk management function.

Guardian's scope: dynamic SL management, threat scoring, zone escalation (GREEN→YELLOW→RED→BLACK), trailing stop logic (E55→E21 switch), time-based escalation, position monitoring.

**Evidence:** Architecture principles documented in Phase 3 audit.

---

## 💡 All 6 historical losses had broken R:R (0.40) — guardian cannot save bad entries
**Date:** 2026-03-20T20:00:01
**Type:** discovery
**Tags:** risk-reward, structural-flaw, entry-quality, audit-2026-03-20-phase3

Phase 3 loss analysis: all 6 significant historical losses had R:R of ~0.40 (risking 2.5x to make 1x). No amount of guardian sophistication can make a structurally negative-expectancy trade profitable. The guardian's job is to PROTECT profits and LIMIT losses — but if the entry itself has broken R:R, the trade is doomed before the guardian even engages.

Key takeaway: guardian improvements (E21 trailing, YELLOW escalation, etc.) are necessary but not sufficient. The quality of the snipe IS the quality of the trade. Fix the input (validator precision snipes with enforced R:R), and the guardian's existing logic becomes effective.

**Evidence:** 6 losses, all R:R ~0.40. Required WR at 0.40 R:R: >71%. Actual WR: 30-50%.

---

## 📈 Snipe thresholds now vary by setup type — guardian sees different risk profiles
**Date:** 2026-03-20T20:00:02
**Type:** improvement
**Tags:** snipe-threshold, setup-type, risk-profile, audit-2026-03-20-phase3

Snipe confidence thresholds now differentiated: retracement 0.75, breakout 0.80, reversal 0.85, continuation 0.90. This means the guardian will see different trade quality entering its domain — reversals and continuations will have passed a higher bar before the guardian takes over position management. This should reduce the frequency of immediate YELLOW scoring on newly opened positions.

**Evidence:** 4-tier threshold system implemented. Previously: single threshold.

---

## ❌ ❌ AUD_JPY SELL loss: -11.6p / $-0.37 (13min)
**Date:** 2026-03-20T15:52:32
**Type:** failure
**Tags:** loss, audjpy, guardian, S5

**Pair:** AUD_JPY | **Direction:** SELL
**PnL:** -11.6 pips / $-0.37 | **R:** -0.36
**Duration:** 13 min | **Close reason:** RED
**Peak pips:** 0.0
**Setup:** S5

---

## 💡 💰 USD_CHF SELL win: +0.6p / $+7.55 (26min)
**Date:** 2026-03-24T20:05:51
**Type:** discovery
**Tags:** win, usdchf, guardian, unknown

> [!tip] DISCOVERY
> **Pair:** USD_CHF | **Direction:** SELL
> **PnL:** +0.6 pips / $+7.55 | **R:** 0.04
> **Duration:** 26 min | **Close reason:** GREEN
> **Peak pips:** 2.1
> **Setup:** unknown


---

## 💡 💰 USD_CHF SELL win: +2.0p / $+23.52 (26min)
**Date:** 2026-03-24T20:05:52
**Type:** discovery
**Tags:** win, usdchf, guardian, unknown

> [!tip] DISCOVERY
> **Pair:** USD_CHF | **Direction:** SELL
> **PnL:** +2.0 pips / $+23.52 | **R:** 0.11
> **Duration:** 26 min | **Close reason:** GREEN
> **Peak pips:** 2.6
> **Setup:** unknown


---

## 💡 💰 EUR_JPY BUY win: +14.9p / $+0.67 (35min)
**Date:** 2026-03-24T20:14:41
**Type:** discovery
**Tags:** win, eurjpy, guardian, S1

> [!tip] DISCOVERY
> **Pair:** EUR_JPY | **Direction:** BUY
> **PnL:** +14.9 pips / $+0.67 | **R:** 4.97
> **Duration:** 35 min | **Close reason:** YELLOW
> **Peak pips:** 15.0
> **Setup:** S1


---

## ❌ ❌ EUR_JPY BUY loss: -16.3p / $-0.66 (96min)
**Date:** 2026-03-24T22:53:47
**Type:** failure
**Tags:** loss, eurjpy, guardian, S15

> [!danger] FAILURE
> **Pair:** EUR_JPY | **Direction:** BUY
> **PnL:** -16.3 pips / $-0.66 | **R:** -0.65
> **Duration:** 96 min | **Close reason:** RED
> **Peak pips:** 1.7
> **Setup:** S15


---

## ❌ ❌ EUR_USD SELL loss: -6.5p / $-6.50 (8min)
**Date:** 2026-03-25T23:23:16
**Type:** failure
**Tags:** loss, eurusd, guardian, S5

> [!danger] FAILURE
> **Pair:** EUR_USD | **Direction:** SELL
> **PnL:** -6.5 pips / $-6.50 | **R:** -1.02
> **Duration:** 8 min | **Close reason:** YELLOW
> **Peak pips:** 0.0
> **Setup:** S5


---

## 💡 💰 EUR_USD SELL win: +6.4p / $+6.40 (1min)
**Date:** 2026-03-26T01:52:07
**Type:** discovery
**Tags:** win, eurusd, guardian, unknown

> [!tip] DISCOVERY
> **Pair:** EUR_USD | **Direction:** SELL
> **PnL:** +6.4 pips / $+6.40 | **R:** 1.33
> **Duration:** 1 min | **Close reason:** GREEN
> **Peak pips:** 6.1
> **Setup:** unknown


---

## ❌ ❌ EUR_USD SELL loss: -6.8p / $-6.80 (1min)
**Date:** 2026-03-26T02:55:03
**Type:** failure
**Tags:** loss, eurusd, guardian, unknown

> [!danger] FAILURE
> **Pair:** EUR_USD | **Direction:** SELL
> **PnL:** -6.8 pips / $-6.80 | **R:** -1.01
> **Duration:** 1 min | **Close reason:** YELLOW
> **Peak pips:** 0.0
> **Setup:** unknown


---

## 💡 💰 EUR_USD SELL win: +2.1p / $+2.10 (3min)
**Date:** 2026-03-26T03:45:38
**Type:** discovery
**Tags:** win, eurusd, guardian, S15

> [!tip] DISCOVERY
> **Pair:** EUR_USD | **Direction:** SELL
> **PnL:** +2.1 pips / $+2.10 | **R:** 0.91
> **Duration:** 3 min | **Close reason:** YELLOW
> **Peak pips:** 4.5
> **Setup:** S15


---

## ❌ ❌ AUD_JPY SELL loss: -3.0p / $-1.89 (22min)
**Date:** 2026-03-26T06:23:12
**Type:** failure
**Tags:** loss, audjpy, guardian, unknown

> [!danger] FAILURE
> **Pair:** AUD_JPY | **Direction:** SELL
> **PnL:** -3.0 pips / $-1.89 | **R:** -0.19
> **Duration:** 22 min | **Close reason:** RED
> **Peak pips:** 0.1
> **Setup:** unknown


---

## 💡 💰 EUR_USD SELL win: +1.1p / $+1.10 (63min)
**Date:** 2026-03-26T07:02:30
**Type:** discovery
**Tags:** win, eurusd, guardian, unknown

> [!tip] DISCOVERY
> **Pair:** EUR_USD | **Direction:** SELL
> **PnL:** +1.1 pips / $+1.10 | **R:** 0.10
> **Duration:** 63 min | **Close reason:** RED
> **Peak pips:** 1.8
> **Setup:** unknown


---

## ❌ ❌ EUR_USD SELL loss: +0.0p / $+12.80 (6min)
**Date:** 2026-03-26T07:59:23
**Type:** failure
**Tags:** loss, eurusd, guardian, S1

> [!danger] FAILURE
> **Pair:** EUR_USD | **Direction:** SELL
> **PnL:** +0.0 pips / $+12.80 | **R:** 0.00
> **Duration:** 6 min | **Close reason:** YELLOW
> **Peak pips:** 13.7
> **Setup:** S1


---

## 💡 💰 AUD_JPY SELL win: +3.0p / $+1.87 (12min)
**Date:** 2026-03-26T08:05:29
**Type:** discovery
**Tags:** win, audjpy, guardian, S1

> [!tip] DISCOVERY
> **Pair:** AUD_JPY | **Direction:** SELL
> **PnL:** +3.0 pips / $+1.87 | **R:** 1.00
> **Duration:** 12 min | **Close reason:** YELLOW
> **Peak pips:** 9.7
> **Setup:** S1


---

## ❌ ❌ EUR_USD SELL loss: -12.8p / $-12.80 (2min)
**Date:** 2026-03-26T09:15:14
**Type:** failure
**Tags:** loss, eurusd, guardian, S5

> [!danger] FAILURE
> **Pair:** EUR_USD | **Direction:** SELL
> **PnL:** -12.8 pips / $-12.80 | **R:** -1.00
> **Duration:** 2 min | **Close reason:** YELLOW
> **Peak pips:** 0.0
> **Setup:** S5


---

## ❌ ❌ EUR_USD SELL loss: -12.5p / $-12.50 (7min)
**Date:** 2026-03-26T09:45:07
**Type:** failure
**Tags:** loss, eurusd, guardian, S5

> [!danger] FAILURE
> **Pair:** EUR_USD | **Direction:** SELL
> **PnL:** -12.5 pips / $-12.50 | **R:** -1.01
> **Duration:** 7 min | **Close reason:** YELLOW
> **Peak pips:** 0.0
> **Setup:** S5


---

## ❌ ❌ AUD_JPY SELL loss: -15.5p / $-9.77 (9min)
**Date:** 2026-03-26T09:48:00
**Type:** failure
**Tags:** loss, audjpy, guardian, S5

> [!danger] FAILURE
> **Pair:** AUD_JPY | **Direction:** SELL
> **PnL:** -15.5 pips / $-9.77 | **R:** -1.00
> **Duration:** 9 min | **Close reason:** YELLOW
> **Peak pips:** 0.0
> **Setup:** S5


---

## 🔧 OANDA hard SL widened from 1.5xATR to 3xATR for ALL trades — guardian manages exits
**Date:** 2026-03-26T10:23:47
**Type:** correction
**Tags:** guardian, stop-loss, oanda, exit-management, 3xATR, retrace

> [!warning] CORRECTION
> MODULE: position_guardian.py | LAYER: exit_management | CHANGE: _watch_loop() SL widening removed _is_retracement_entry gate — now runs unconditionally for every TradeWatcher. OANDA hard SL pushed to 3xATR as catastrophic safety net. Guardian threat system (retrace state machine, EMA fan, BB width, dynamic SL trailing on E55/E100) is the real exit manager. | BEFORE: SL widening only for retracement entries. Trades 2143 EUR_USD(-12.8p) and 2153 AUD_JPY(-15.5p) killed by OANDA SL while guardian YELLOW(40-50). | AFTER: All trades get 3xATR safety net. Guardian has room to hold through retracements. | ACTIVATED: ~14:00 UTC 2026-03-26 after server restart. Trades BEFORE this time used old 1.5xATR SL.


---

## 📈 Snipe_direct thesis enriched with fan_state, is_retracement_entry, invalidation_level
**Date:** 2026-03-26T10:24:11
**Type:** improvement
**Tags:** guardian, thesis, snipe_direct, trading_cycle, retracement

> [!success] IMPROVEMENT
> MODULE: agents/trading_cycle.py | LAYER: thesis_registration | CHANGE: register_thesis() for snipe_direct trades now passes fan_state_at_entry, fan_direction_at_entry, is_retracement_entry, invalidation_level, setup_name, regime from scout_context. | BEFORE: Bare-bones thesis with only entry_type, thesis text, direction, watch_id, opportunity_score. Guardian could not detect retracement entries from snipe trades. | AFTER: Guardian _is_retracement_entry flag correctly fires for snipe_direct trades that entered during fan contraction. | ACTIVATED: ~13:00 UTC 2026-03-26


---

## 💡 💰 AUD_USD SELL win: +12.7p / $+125.35 (38min)
**Date:** 2026-03-26T10:55:12
**Type:** discovery
**Tags:** win, audusd, guardian, S5

> [!tip] DISCOVERY
> **Pair:** AUD_USD | **Direction:** SELL
> **PnL:** +12.7 pips / $+125.35 | **R:** 6.05
> **Duration:** 38 min | **Close reason:** GREEN
> **Peak pips:** 12.9
> **Setup:** S5


---

## 🔧 Retrace state machine: EMA-only trigger for fast M1 retracements
**Date:** 2026-03-26T15:30:00
**Type:** correction
**Tags:** retrace, state-machine, ema-contraction, bb-lag, guardian

MODULE: position_guardian.py
LAYER: _check_dynamic_exit / retrace state machine (line ~2251)
BEFORE: Retrace state transition (trending→retracing) required `both_contracting` = BB width shrinking AND EMA separation shrinking on same candle. M15 BB is too slow to confirm fast M1 retracements — trade 2165 went -6.6p in retracement but retrace_state never left 'trending', so retracement banner never showed.
AFTER: Transition now triggers on EITHER (a) BB+EMA both contracting (classic), OR (b) EMA contraction sustained for 3+ consecutive candles (fast M1 retrace). Also computes retrace depth from EMA separation peak when BB depth is 0.
ACTIVATED: 2026-03-26T15:30:00

**Root cause:** Trade 2165 (AUD_USD SELL) experienced a -6.6p retracement over ~12 minutes. EMA separation contracted immediately on M1, but M15 BB width was still expanding from the prior trend impulse. The `both_contracting` gate kept `retrace_state='trending'` the entire trade, which meant:
1. The retracement awareness banner never appeared on the chart card
2. `retrace_depth_pct` stayed at 0% despite clear visual retracement
3. Guardian still held correctly (threat scoring worked independently), but the UI gave no retracement context

**Evidence:** Trade 2165 flight log: 93 entries, retrace_state='' throughout, retrace_depth=0%. Trade went -6.6p at 14:22-14:34, recovered to +12.7p close. EMA separation was clearly contracting (threat scored YELLOW/RED) but BB width on M15 didn't confirm.

---

## ❌ ❌ AUD_USD SELL loss: -13.1p / $-117.49 (18min)
**Date:** 2026-03-26T11:12:38
**Type:** failure
**Tags:** loss, audusd, guardian, S5

> [!danger] FAILURE
> **Pair:** AUD_USD | **Direction:** SELL
> **PnL:** -13.1 pips / $-117.49 | **R:** -0.43
> **Duration:** 18 min | **Close reason:** RED
> **Peak pips:** 0.0
> **Setup:** S5


---

## 🔧 Dashboard: inline reconciliation for stale 'open' trades
**Date:** 2026-03-26T15:45:00
**Type:** correction
**Tags:** dashboard, live_trades, reconciliation, trades-today

MODULE: trading_api_routes.py
LAYER: /api/trading/performance endpoint / trades_today section
BEFORE: Dashboard showed trades as LIVE with dashes for pips/P&L even after they closed on OANDA. Root cause: when server recycles during a close, the guardian's reconcile loop never runs for that trade.
AFTER: Performance endpoint does inline reconciliation — checks OANDA for any 'open' rows that are actually closed, updates DB and response immediately.
ACTIVATED: 2026-03-26T15:45:00

---

## 🔧 Suppress RED escalation to Trade Monitor during retracement
**Date:** 2026-03-26T16:00:00
**Type:** correction
**Tags:** guardian, retrace, escalation, trade-monitor, kill-prevention

MODULE: position_guardian.py
LAYER: _evaluate_once / RED zone escalation path (line ~1427)
BEFORE: When threat hit RED (61-80) during a recognized retracement, guardian escalated to Trade Monitor LLM. The Trade Monitor had ZERO retracement context in the escalation report — only saw "RED 76, E100 BROKEN, structural level lost" — and decided to close. AUD_USD trade killed at -12.7p / -$117.49 while candles hadn't even reached EMA 55, RSI and Stoch both in healthy range.
AFTER: When `retrace_state == 'retracing'`, RED escalation to Trade Monitor is SUPPRESSED. The guardian's own dynamic exit rules (Rule 0 suppressed, Rule 1 E100 tests, Rule 5 peak-decel) manage retracement exits with full context. Also added `retrace_context` dict to escalation report for non-retracement RED escalations so Trade Monitor has the info if state machine isn't in 'retracing' but retrace data exists.
ACTIVATED: 2026-03-26T16:00:00

**Root cause chain:**
1. Trade enters, price retraces (normal pullback behavior)
2. EMA-only retrace trigger fires → `retrace_state = 'retracing'` ✅
3. Threat score climbs to RED 76 due to E100 proximity + structure scoring
4. Guardian escalates to Trade Monitor at RED zone
5. Escalation report has NO retrace context — Trade Monitor sees only danger signals
6. Trade Monitor closes trade at -12.7p
7. Price continues retracement then resumes trend (would have been profitable)

**Evidence:** AUD_USD SELL, threat 76 (RED), structure=40, E100 BROKEN (3 breaks). RSI and Stoch in healthy range (not oversold/overbought). Candles hadn't reached EMA 55. Retracement banner was showing correctly. Guardian's own rules (Rule 0, Signal A, Signal B) were all correctly suppressed during retracement — but the Trade Monitor LLM wasn't aware.

---

## 💡 💰 AUD_USD SELL win: +2.9p / $+26.78 (27min)
**Date:** 2026-03-26T11:46:40
**Type:** discovery
**Tags:** win, audusd, guardian, S5

> [!tip] DISCOVERY
> **Pair:** AUD_USD | **Direction:** SELL
> **PnL:** +2.9 pips / $+26.78 | **R:** 0.97
> **Duration:** 27 min | **Close reason:** GREEN
> **Peak pips:** 9.5
> **Setup:** S5


---

## 💡 💰 AUD_USD SELL win: +8.6p / $+78.54 (35min)
**Date:** 2026-03-26T12:25:16
**Type:** discovery
**Tags:** win, audusd, guardian, S15

> [!tip] DISCOVERY
> **Pair:** AUD_USD | **Direction:** SELL
> **PnL:** +8.6 pips / $+78.54 | **R:** 2.87
> **Duration:** 35 min | **Close reason:** GREEN
> **Peak pips:** 10.1
> **Setup:** S15


---

## ❌ ❌ AUD_JPY SELL loss: +0.0p / $+2.87 (42min)
**Date:** 2026-03-26T13:04:11
**Type:** failure
**Tags:** loss, audjpy, guardian, S1

> [!danger] FAILURE
> **Pair:** AUD_JPY | **Direction:** SELL
> **PnL:** +0.0 pips / $+2.87 | **R:** 0.00
> **Duration:** 42 min | **Close reason:** YELLOW
> **Peak pips:** 7.7
> **Setup:** S1


---

## ❌ ❌ AUD_JPY SELL loss: -2.4p / $-1.51 (12min)
**Date:** 2026-03-26T13:31:30
**Type:** failure
**Tags:** loss, audjpy, guardian, S1

> [!danger] FAILURE
> **Pair:** AUD_JPY | **Direction:** SELL
> **PnL:** -2.4 pips / $-1.51 | **R:** -0.08
> **Duration:** 12 min | **Close reason:** RED
> **Peak pips:** 0.9
> **Setup:** S1


---

## ❌ ❌ EUR_USD SELL loss: -0.7p / $-0.70 (78min)
**Date:** 2026-03-26T15:19:21
**Type:** failure
**Tags:** loss, eurusd, guardian, S5

> [!danger] FAILURE
> **Pair:** EUR_USD | **Direction:** SELL
> **PnL:** -0.7 pips / $-0.70 | **R:** -0.03
> **Duration:** 78 min | **Close reason:** RED
> **Peak pips:** 1.7
> **Setup:** S5


---

## 💡 💰 AUD_JPY SELL win: +8.6p / $+5.35 (23min)
**Date:** 2026-03-26T15:50:23
**Type:** discovery
**Tags:** win, audjpy, guardian, S1

> [!tip] DISCOVERY
> **Pair:** AUD_JPY | **Direction:** SELL
> **PnL:** +8.6 pips / $+5.35 | **R:** 2.69
> **Duration:** 23 min | **Close reason:** YELLOW
> **Peak pips:** 10.4
> **Setup:** S1


---

## ❌ ❌ EUR_USD SELL loss: +0.0p / $+1.60 (20min)
**Date:** 2026-03-26T16:11:48
**Type:** failure
**Tags:** loss, eurusd, guardian, S1

> [!danger] FAILURE
> **Pair:** EUR_USD | **Direction:** SELL
> **PnL:** +0.0 pips / $+1.60 | **R:** 0.00
> **Duration:** 20 min | **Close reason:** YELLOW
> **Peak pips:** 2.8
> **Setup:** S1


---

## ❌ ❌ AUD_JPY SELL loss: -27.9p / $-17.57 (35min)
**Date:** 2026-03-26T23:17:11
**Type:** failure
**Tags:** loss, audjpy, guardian, S15

> [!danger] FAILURE
> **Pair:** AUD_JPY | **Direction:** SELL
> **PnL:** -27.9 pips / $-17.57 | **R:** -1.01
> **Duration:** 35 min | **Close reason:** RED
> **Peak pips:** 0.0
> **Setup:** S15


---

## ❌ ❌ GBP_JPY SELL loss: -30.7p / $-19.30 (27min)
**Date:** 2026-03-27T09:43:29
**Type:** failure
**Tags:** loss, gbpjpy, guardian, S5

> [!danger] FAILURE
> **Pair:** GBP_JPY | **Direction:** SELL
> **PnL:** -30.7 pips / $-19.30 | **R:** -1.00
> **Duration:** 27 min | **Close reason:** RED
> **Peak pips:** 0.0
> **Setup:** S5


---

## ❌ ❌ GBP_USD SELL loss: -26.1p / $-26.10 (43min)
**Date:** 2026-03-27T10:11:52
**Type:** failure
**Tags:** loss, gbpusd, guardian, S5

> [!danger] FAILURE
> **Pair:** GBP_USD | **Direction:** SELL
> **PnL:** -26.1 pips / $-26.10 | **R:** -1.00
> **Duration:** 43 min | **Close reason:** RED
> **Peak pips:** 2.1
> **Setup:** S5


---

## ❌ ❌ NZD_USD SELL loss: -15.6p / $-15.60 (47min)
**Date:** 2026-03-27T10:20:49
**Type:** failure
**Tags:** loss, nzdusd, guardian, S15

> [!danger] FAILURE
> **Pair:** NZD_USD | **Direction:** SELL
> **PnL:** -15.6 pips / $-15.60 | **R:** -1.01
> **Duration:** 47 min | **Close reason:** RED
> **Peak pips:** 0.0
> **Setup:** S15


---

## ❌ ❌ GBP_JPY SELL loss: -32.1p / $-20.18 (11min)
**Date:** 2026-03-27T11:24:31
**Type:** failure
**Tags:** loss, gbpjpy, guardian, unknown

> [!danger] FAILURE
> **Pair:** GBP_JPY | **Direction:** SELL
> **PnL:** -32.1 pips / $-20.18 | **R:** -0.78
> **Duration:** 11 min | **Close reason:** BLACK
> **Peak pips:** 0.0
> **Setup:** unknown


---

## ❌ ❌ EUR_USD SELL loss: -13.7p / $-13.70 (10min)
**Date:** 2026-03-27T11:24:34
**Type:** failure
**Tags:** loss, eurusd, guardian, S1

> [!danger] FAILURE
> **Pair:** EUR_USD | **Direction:** SELL
> **PnL:** -13.7 pips / $-13.70 | **R:** -0.55
> **Duration:** 10 min | **Close reason:** RED
> **Peak pips:** 0.0
> **Setup:** S1


---

## ❌ ❌ GBP_JPY SELL loss: -13.1p / $-8.24 (10min)
**Date:** 2026-03-27T11:35:12
**Type:** failure
**Tags:** loss, gbpjpy, guardian, unknown

> [!danger] FAILURE
> **Pair:** GBP_JPY | **Direction:** SELL
> **PnL:** -13.1 pips / $-8.24 | **R:** -0.33
> **Duration:** 10 min | **Close reason:** RED
> **Peak pips:** 0.0
> **Setup:** unknown


---

## 💡 💰 GBP_JPY SELL win: +27.0p / $+16.79 (20min)
**Date:** 2026-03-27T11:57:39
**Type:** discovery
**Tags:** win, gbpjpy, guardian, unknown

> [!tip] DISCOVERY
> **Pair:** GBP_JPY | **Direction:** SELL
> **PnL:** +27.0 pips / $+16.79 | **R:** 6.92
> **Duration:** 20 min | **Close reason:** GREEN
> **Peak pips:** 22.4
> **Setup:** unknown


---

## 💡 💰 GBP_JPY SELL win: +17.8p / $+11.06 (15min)
**Date:** 2026-03-27T12:37:09
**Type:** discovery
**Tags:** win, gbpjpy, guardian, unknown

> [!tip] DISCOVERY
> **Pair:** GBP_JPY | **Direction:** SELL
> **PnL:** +17.8 pips / $+11.06 | **R:** 2.02
> **Duration:** 15 min | **Close reason:** YELLOW
> **Peak pips:** 23.3
> **Setup:** unknown


---

## ❌ ❌ GBP_JPY SELL loss: -12.7p / $-7.97 (11min)
**Date:** 2026-03-27T12:51:47
**Type:** failure
**Tags:** loss, gbpjpy, guardian, unknown

> [!danger] FAILURE
> **Pair:** GBP_JPY | **Direction:** SELL
> **PnL:** -12.7 pips / $-7.97 | **R:** -0.25
> **Duration:** 11 min | **Close reason:** YELLOW
> **Peak pips:** 0.0
> **Setup:** unknown


---

## 💡 💰 GBP_USD SELL win: +11.9p / $+11.90 (41min)
**Date:** 2026-03-27T13:42:13
**Type:** discovery
**Tags:** win, gbpusd, guardian, S5

> [!tip] DISCOVERY
> **Pair:** GBP_USD | **Direction:** SELL
> **PnL:** +11.9 pips / $+11.90 | **R:** 1.47
> **Duration:** 41 min | **Close reason:** YELLOW
> **Peak pips:** 14.8
> **Setup:** S5


---

## ❌ ❌ GBP_USD SELL loss: -12.5p / $-12.50 (40min)
**Date:** 2026-03-27T16:01:27
**Type:** failure
**Tags:** loss, gbpusd, guardian, S5

> [!danger] FAILURE
> **Pair:** GBP_USD | **Direction:** SELL
> **PnL:** -12.5 pips / $-12.50 | **R:** -0.33
> **Duration:** 40 min | **Close reason:** RED
> **Peak pips:** 0.0
> **Setup:** S5


---

## 💡 💰 GBP_JPY SELL win: +16.7p / $+10.37 (11min)
**Date:** 2026-03-29T19:57:04
**Type:** discovery
**Tags:** win, gbpjpy, guardian, S15

> [!tip] DISCOVERY
> **Pair:** GBP_JPY | **Direction:** SELL
> **PnL:** +16.7 pips / $+10.37 | **R:** 2.11
> **Duration:** 11 min | **Close reason:** YELLOW
> **Peak pips:** 18.9
> **Setup:** S15


---

## ❌ ❌ EUR_JPY SELL loss: -11.6p / $-11.67 (31min)
**Date:** 2026-03-30T02:37:37
**Type:** failure
**Tags:** loss, eurjpy, guardian, S5

> [!danger] FAILURE
> **Pair:** EUR_JPY | **Direction:** SELL
> **PnL:** -11.6 pips / $-11.67 | **R:** -0.50
> **Duration:** 31 min | **Close reason:** BLACK
> **Peak pips:** 2.9
> **Setup:** S5


---

## ❌ ❌ GBP_JPY SELL loss: -4.4p / $-4.43 (16min)
**Date:** 2026-03-30T02:52:45
**Type:** failure
**Tags:** loss, gbpjpy, guardian, S5

> [!danger] FAILURE
> **Pair:** GBP_JPY | **Direction:** SELL
> **PnL:** -4.4 pips / $-4.43 | **R:** -0.16
> **Duration:** 16 min | **Close reason:** RED
> **Peak pips:** 0.0
> **Setup:** S5


---

## 💡 💰 GBP_JPY SELL win: +6.0p / $+5.98 (6min)
**Date:** 2026-03-30T11:10:10
**Type:** discovery
**Tags:** win, gbpjpy, guardian, S5

> [!tip] DISCOVERY
> **Pair:** GBP_JPY | **Direction:** SELL
> **PnL:** +6.0 pips / $+5.98 | **R:** 1.00
> **Duration:** 6 min | **Close reason:** YELLOW
> **Peak pips:** 10.6
> **Setup:** S5


---

## 💡 💰 EUR_USD SELL win: +11.9p / $+11.90 (27min)
**Date:** 2026-03-30T11:14:12
**Type:** discovery
**Tags:** win, eurusd, guardian, S1

> [!tip] DISCOVERY
> **Pair:** EUR_USD | **Direction:** SELL
> **PnL:** +11.9 pips / $+11.90 | **R:** 3.97
> **Duration:** 27 min | **Close reason:** YELLOW
> **Peak pips:** 12.8
> **Setup:** S1


---

## 💡 💰 GBP_USD SELL win: +1.9p / $+1.90 (10min)
**Date:** 2026-03-30T11:48:18
**Type:** discovery
**Tags:** win, gbpusd, guardian, S5

> [!tip] DISCOVERY
> **Pair:** GBP_USD | **Direction:** SELL
> **PnL:** +1.9 pips / $+1.90 | **R:** 1.00
> **Duration:** 10 min | **Close reason:** YELLOW
> **Peak pips:** 5.8
> **Setup:** S5


---

## ❌ ❌ GBP_JPY SELL loss: -4.9p / $-4.91 (34min)
**Date:** 2026-03-30T12:16:17
**Type:** failure
**Tags:** loss, gbpjpy, guardian, S1

> [!danger] FAILURE
> **Pair:** GBP_JPY | **Direction:** SELL
> **PnL:** -4.9 pips / $-4.91 | **R:** -1.00
> **Duration:** 34 min | **Close reason:** YELLOW
> **Peak pips:** 5.4
> **Setup:** S1


---

## ❌ ❌ EUR_CHF SELL loss: -5.6p / $-5.63 (71min)
**Date:** 2026-03-30T12:43:01
**Type:** failure
**Tags:** loss, eurchf, guardian, S5

> [!danger] FAILURE
> **Pair:** EUR_CHF | **Direction:** SELL
> **PnL:** -5.6 pips / $-5.63 | **R:** -0.38
> **Duration:** 71 min | **Close reason:** RED
> **Peak pips:** 0.0
> **Setup:** S5


---

## ❌ ❌ EUR_CHF SELL loss: -3.8p / $-3.82 (99min)
**Date:** 2026-03-30T14:26:19
**Type:** failure
**Tags:** loss, eurchf, guardian, S5

> [!danger] FAILURE
> **Pair:** EUR_CHF | **Direction:** SELL
> **PnL:** -3.8 pips / $-3.82 | **R:** -0.27
> **Duration:** 99 min | **Close reason:** RED
> **Peak pips:** 0.0
> **Setup:** S5


---

## ❌ ❌ AUD_USD SELL loss: -16.5p / $-16.50 (7min)
**Date:** 2026-03-30T20:46:06
**Type:** failure
**Tags:** loss, audusd, guardian, S15

> [!danger] FAILURE
> **Pair:** AUD_USD | **Direction:** SELL
> **PnL:** -16.5 pips / $-16.50 | **R:** -1.00
> **Duration:** 7 min | **Close reason:** GREEN
> **Peak pips:** 0.0
> **Setup:** S15


---

## 💡 💰 EUR_JPY SELL win: +3.0p / $+2.99 (23min)
**Date:** 2026-03-30T22:40:06
**Type:** discovery
**Tags:** win, eurjpy, guardian, unknown

> [!tip] DISCOVERY
> **Pair:** EUR_JPY | **Direction:** SELL
> **PnL:** +3.0 pips / $+2.99 | **R:** 1.00
> **Duration:** 23 min | **Close reason:** GREEN
> **Peak pips:** 6.1
> **Setup:** unknown


---

## 💡 💰 AUD_USD SELL win: +9.7p / $+9.70 (55min)
**Date:** 2026-03-30T23:50:53
**Type:** discovery
**Tags:** win, audusd, guardian, unknown

> [!tip] DISCOVERY
> **Pair:** AUD_USD | **Direction:** SELL
> **PnL:** +9.7 pips / $+9.70 | **R:** 1.29
> **Duration:** 55 min | **Close reason:** YELLOW
> **Peak pips:** 14.2
> **Setup:** unknown


---

## 💡 💰 AUD_JPY SELL win: +4.5p / $+4.49 (6min)
**Date:** 2026-03-31T02:11:09
**Type:** discovery
**Tags:** win, audjpy, guardian, unknown

> [!tip] DISCOVERY
> **Pair:** AUD_JPY | **Direction:** SELL
> **PnL:** +4.5 pips / $+4.49 | **R:** 1.00
> **Duration:** 6 min | **Close reason:** YELLOW
> **Peak pips:** 6.2
> **Setup:** unknown


---

## 💡 💰 EUR_AUD SELL win: +7.9p / $+7.83 (11min)
**Date:** 2026-03-31T05:02:56
**Type:** discovery
**Tags:** win, euraud, guardian, S15

> [!tip] DISCOVERY
> **Pair:** EUR_AUD | **Direction:** SELL
> **PnL:** +7.9 pips / $+7.83 | **R:** 1.07
> **Duration:** 11 min | **Close reason:** YELLOW
> **Peak pips:** 12.5
> **Setup:** S15


---

## ❌ ❌ EUR_JPY SELL loss: -16.4p / $-16.53 (11min)
**Date:** 2026-03-31T05:25:37
**Type:** failure
**Tags:** loss, eurjpy, guardian, unknown

> [!danger] FAILURE
> **Pair:** EUR_JPY | **Direction:** SELL
> **PnL:** -16.4 pips / $-16.53 | **R:** -0.45
> **Duration:** 11 min | **Close reason:** YELLOW
> **Peak pips:** 0.0
> **Setup:** unknown


---

## 💡 💰 AUD_USD SELL win: +4.4p / $+4.40 (60min)
**Date:** 2026-03-31T06:16:15
**Type:** discovery
**Tags:** win, audusd, guardian, unknown

> [!tip] DISCOVERY
> **Pair:** AUD_USD | **Direction:** SELL
> **PnL:** +4.4 pips / $+4.40 | **R:** 1.47
> **Duration:** 60 min | **Close reason:** YELLOW
> **Peak pips:** 5.1
> **Setup:** unknown


---

## ❌ ❌ EUR_AUD SELL loss: -11.9p / $-11.97 (77min)
**Date:** 2026-03-31T06:38:10
**Type:** failure
**Tags:** loss, euraud, guardian, unknown

> [!danger] FAILURE
> **Pair:** EUR_AUD | **Direction:** SELL
> **PnL:** -11.9 pips / $-11.97 | **R:** -0.26
> **Duration:** 77 min | **Close reason:** BLACK
> **Peak pips:** 0.9
> **Setup:** unknown


---

## ❌ ❌ EUR_JPY SELL loss: -23.2p / $-23.30 (11min)
**Date:** 2026-03-31T10:03:29
**Type:** failure
**Tags:** loss, eurjpy, guardian, S15

> [!danger] FAILURE
> **Pair:** EUR_JPY | **Direction:** SELL
> **PnL:** -23.2 pips / $-23.30 | **R:** -0.65
> **Duration:** 11 min | **Close reason:** YELLOW
> **Peak pips:** 0.0
> **Setup:** S15


---

## 💡 💰 NZD_USD BUY win: +2.9p / $+2.90 (13min)
**Date:** 2026-03-31T10:05:45
**Type:** discovery
**Tags:** win, nzdusd, guardian, S5

> [!tip] DISCOVERY
> **Pair:** NZD_USD | **Direction:** BUY
> **PnL:** +2.9 pips / $+2.90 | **R:** 0.97
> **Duration:** 13 min | **Close reason:** YELLOW
> **Peak pips:** 9.1
> **Setup:** S5


---

## 💡 💰 NZD_USD SELL win: +13.4p / $+13.40 (11min)
**Date:** 2026-03-31T10:55:37
**Type:** discovery
**Tags:** win, nzdusd, guardian, S15

> [!tip] DISCOVERY
> **Pair:** NZD_USD | **Direction:** SELL
> **PnL:** +13.4 pips / $+13.40 | **R:** 4.47
> **Duration:** 11 min | **Close reason:** GREEN
> **Peak pips:** 14.8
> **Setup:** S15


---

## 💡 💰 EUR_AUD BUY win: +2.3p / $+2.29 (13min)
**Date:** 2026-03-31T12:15:30
**Type:** discovery
**Tags:** win, euraud, guardian, S5

> [!tip] DISCOVERY
> **Pair:** EUR_AUD | **Direction:** BUY
> **PnL:** +2.3 pips / $+2.29 | **R:** 1.00
> **Duration:** 13 min | **Close reason:** YELLOW
> **Peak pips:** 6.3
> **Setup:** S5


---

## ❌ ❌ GBP_JPY SELL loss: -13.7p / $-13.77 (11min)
**Date:** 2026-03-31T12:44:29
**Type:** failure
**Tags:** loss, gbpjpy, guardian, S5

> [!danger] FAILURE
> **Pair:** GBP_JPY | **Direction:** SELL
> **PnL:** -13.7 pips / $-13.77 | **R:** -0.17
> **Duration:** 11 min | **Close reason:** YELLOW
> **Peak pips:** 0.0
> **Setup:** S5


---

## ❌ ❌ GBP_JPY SELL loss: -28.2p / $-28.36 (11min)
**Date:** 2026-03-31T13:00:52
**Type:** failure
**Tags:** loss, gbpjpy, guardian, S5

> [!danger] FAILURE
> **Pair:** GBP_JPY | **Direction:** SELL
> **PnL:** -28.2 pips / $-28.36 | **R:** -0.32
> **Duration:** 11 min | **Close reason:** YELLOW
> **Peak pips:** 0.0
> **Setup:** S5


---

## ❌ ❌ AUD_JPY SELL loss: -25.6p / $-25.75 (36min)
**Date:** 2026-03-31T13:10:42
**Type:** failure
**Tags:** loss, audjpy, guardian, S1

> [!danger] FAILURE
> **Pair:** AUD_JPY | **Direction:** SELL
> **PnL:** -25.6 pips / $-25.75 | **R:** -0.51
> **Duration:** 36 min | **Close reason:** YELLOW
> **Peak pips:** 0.0
> **Setup:** S1


---

## ❌ ❌ GBP_JPY SELL loss: -12.6p / $-0.22 (11min)
**Date:** 2026-03-31T13:26:49
**Type:** failure
**Tags:** loss, gbpjpy, guardian, S5

> [!danger] FAILURE
> **Pair:** GBP_JPY | **Direction:** SELL
> **PnL:** -12.6 pips / $-0.22 | **R:** -0.15
> **Duration:** 11 min | **Close reason:** YELLOW
> **Peak pips:** 0.0
> **Setup:** S5


---

## 💡 💰 AUD_USD SELL win: +3.4p / $+34.00 (5min)
**Date:** 2026-03-31T13:39:35
**Type:** discovery
**Tags:** win, audusd, guardian, S1

> [!tip] DISCOVERY
> **Pair:** AUD_USD | **Direction:** SELL
> **PnL:** +3.4 pips / $+34.00 | **R:** 0.12
> **Duration:** 5 min | **Close reason:** YELLOW
> **Peak pips:** 4.4
> **Setup:** S1


---

## ❌ ❌ GBP_USD BUY loss: -2.1p / $-10.27 (1min)
**Date:** 2026-03-31T13:42:37
**Type:** failure
**Tags:** loss, gbpusd, guardian, unknown

> [!danger] FAILURE
> **Pair:** GBP_USD | **Direction:** BUY
> **PnL:** -2.1 pips / $-10.27 | **R:** -0.03
> **Duration:** 1 min | **Close reason:** BLACK
> **Peak pips:** 0.0
> **Setup:** unknown


---

## ❌ ❌ GBP_JPY SELL loss: -6.3p / $-39.84 (24min)
**Date:** 2026-03-31T14:03:32
**Type:** failure
**Tags:** loss, gbpjpy, guardian, S5

> [!danger] FAILURE
> **Pair:** GBP_JPY | **Direction:** SELL
> **PnL:** -6.3 pips / $-39.84 | **R:** -1.02
> **Duration:** 24 min | **Close reason:** YELLOW
> **Peak pips:** 3.2
> **Setup:** S5


---

## ❌ ❌ GBP_JPY SELL loss: -2.9p / $-18.35 (20min)
**Date:** 2026-03-31T14:36:06
**Type:** failure
**Tags:** loss, gbpjpy, guardian, S5

> [!danger] FAILURE
> **Pair:** GBP_JPY | **Direction:** SELL
> **PnL:** -2.9 pips / $-18.35 | **R:** -1.04
> **Duration:** 20 min | **Close reason:** GREEN
> **Peak pips:** 3.8
> **Setup:** S5


---

## 💡 💰 GBP_JPY SELL win: +11.7p / $+11.65 (10min)
**Date:** 2026-03-31T14:56:25
**Type:** discovery
**Tags:** win, gbpjpy, guardian, S5

> [!tip] DISCOVERY
> **Pair:** GBP_JPY | **Direction:** SELL
> **PnL:** +11.7 pips / $+11.65 | **R:** 1.04
> **Duration:** 10 min | **Close reason:** YELLOW
> **Peak pips:** 16.1
> **Setup:** S5


---

## 💡 💰 GBP_JPY SELL win: +9.4p / $+0.20 (28min)
**Date:** 2026-03-31T15:39:31
**Type:** discovery
**Tags:** win, gbpjpy, guardian, S5

> [!tip] DISCOVERY
> **Pair:** GBP_JPY | **Direction:** SELL
> **PnL:** +9.4 pips / $+0.20 | **R:** 0.15
> **Duration:** 28 min | **Close reason:** YELLOW
> **Peak pips:** 13.7
> **Setup:** S5


---

## 💡 💰 GBP_JPY SELL win: +2.9p / $+2.89 (17min)
**Date:** 2026-03-31T15:43:02
**Type:** discovery
**Tags:** win, gbpjpy, guardian, S5

> [!tip] DISCOVERY
> **Pair:** GBP_JPY | **Direction:** SELL
> **PnL:** +2.9 pips / $+2.89 | **R:** 0.97
> **Duration:** 17 min | **Close reason:** YELLOW
> **Peak pips:** 10.5
> **Setup:** S5


---

## 💡 💰 EUR_GBP BUY win: +5.3p / $+69.80 (48min)
**Date:** 2026-03-31T15:58:55
**Type:** discovery
**Tags:** win, eurgbp, guardian, S5

> [!tip] DISCOVERY
> **Pair:** EUR_GBP | **Direction:** BUY
> **PnL:** +5.3 pips / $+69.80 | **R:** 1.29
> **Duration:** 48 min | **Close reason:** YELLOW
> **Peak pips:** 5.4
> **Setup:** S5


---

## 💡 💰 EUR_GBP BUY win: +1.7p / $+1.70 (23min)
**Date:** 2026-03-31T15:59:10
**Type:** discovery
**Tags:** win, eurgbp, guardian, S5

> [!tip] DISCOVERY
> **Pair:** EUR_GBP | **Direction:** BUY
> **PnL:** +1.7 pips / $+1.70 | **R:** 0.11
> **Duration:** 23 min | **Close reason:** GREEN
> **Peak pips:** 2.4
> **Setup:** S5


---

## 💡 💰 GBP_JPY SELL win: +2.9p / $+18.18 (29min)
**Date:** 2026-03-31T16:32:25
**Type:** discovery
**Tags:** win, gbpjpy, guardian, S5

> [!tip] DISCOVERY
> **Pair:** GBP_JPY | **Direction:** SELL
> **PnL:** +2.9 pips / $+18.18 | **R:** 0.97
> **Duration:** 29 min | **Close reason:** YELLOW
> **Peak pips:** 11.7
> **Setup:** S5


---

## 💡 💰 GBP_JPY SELL win: +2.9p / $+1.82 (44min)
**Date:** 2026-03-31T19:28:36
**Type:** discovery
**Tags:** win, gbpjpy, guardian, S5

> [!tip] DISCOVERY
> **Pair:** GBP_JPY | **Direction:** SELL
> **PnL:** +2.9 pips / $+1.82 | **R:** 0.85
> **Duration:** 44 min | **Close reason:** YELLOW
> **Peak pips:** 6.9
> **Setup:** S5


---

## 💡 💰 USD_JPY SELL win: +8.6p / $+53.90 (18min)
**Date:** 2026-03-31T21:54:14
**Type:** discovery
**Tags:** win, usdjpy, guardian, S5

> [!tip] DISCOVERY
> **Pair:** USD_JPY | **Direction:** SELL
> **PnL:** +8.6 pips / $+53.90 | **R:** 3.44
> **Duration:** 18 min | **Close reason:** YELLOW
> **Peak pips:** 9.6
> **Setup:** S5


---

## 💡 💰 EUR_AUD SELL win: +2.8p / $+19.28 (5min)
**Date:** 2026-03-31T22:06:27
**Type:** discovery
**Tags:** win, euraud, guardian, S5

> [!tip] DISCOVERY
> **Pair:** EUR_AUD | **Direction:** SELL
> **PnL:** +2.8 pips / $+19.28 | **R:** 0.93
> **Duration:** 5 min | **Close reason:** YELLOW
> **Peak pips:** 5.1
> **Setup:** S5


---

## ❌ ❌ EUR_AUD SELL loss: -12.9p / $-89.65 (19min)
**Date:** 2026-03-31T22:26:37
**Type:** failure
**Tags:** loss, euraud, guardian, S5

> [!danger] FAILURE
> **Pair:** EUR_AUD | **Direction:** SELL
> **PnL:** -12.9 pips / $-89.65 | **R:** -0.33
> **Duration:** 19 min | **Close reason:** YELLOW
> **Peak pips:** 0.0
> **Setup:** S5


---

## ❌ ❌ GBP_JPY SELL loss: -3.6p / $-22.80 (1min)
**Date:** 2026-03-31T22:52:32
**Type:** failure
**Tags:** loss, gbpjpy, guardian, unknown

> [!danger] FAILURE
> **Pair:** GBP_JPY | **Direction:** SELL
> **PnL:** -3.6 pips / $-22.80 | **R:** -0.10
> **Duration:** 1 min | **Close reason:** BLACK
> **Peak pips:** 0.0
> **Setup:** unknown


---

## 💡 💰 USD_CHF SELL win: +2.9p / $+36.17 (18min)
**Date:** 2026-03-31T23:01:07
**Type:** discovery
**Tags:** win, usdchf, guardian, unknown

> [!tip] DISCOVERY
> **Pair:** USD_CHF | **Direction:** SELL
> **PnL:** +2.9 pips / $+36.17 | **R:** 0.97
> **Duration:** 18 min | **Close reason:** YELLOW
> **Peak pips:** 6.4
> **Setup:** unknown


---

## ❌ ❌ USD_JPY SELL loss: -11.0p / $-69.65 (20min)
**Date:** 2026-03-31T23:35:20
**Type:** failure
**Tags:** loss, usdjpy, guardian, unknown

> [!danger] FAILURE
> **Pair:** USD_JPY | **Direction:** SELL
> **PnL:** -11.0 pips / $-69.65 | **R:** -1.00
> **Duration:** 20 min | **Close reason:** YELLOW
> **Peak pips:** 3.0
> **Setup:** unknown


---

## ❌ ❌ USD_CAD SELL loss: -11.1p / $-76.78 (31min)
**Date:** 2026-03-31T23:47:29
**Type:** failure
**Tags:** loss, usdcad, guardian, S5

> [!danger] FAILURE
> **Pair:** USD_CAD | **Direction:** SELL
> **PnL:** -11.1 pips / $-76.78 | **R:** -0.73
> **Duration:** 31 min | **Close reason:** YELLOW
> **Peak pips:** 0.0
> **Setup:** S5


---

## ❌ ❌ USD_JPY SELL loss: -8.5p / $-53.76 (23min)
**Date:** 2026-04-01T00:19:35
**Type:** failure
**Tags:** loss, usdjpy, guardian, S15

> [!danger] FAILURE
> **Pair:** USD_JPY | **Direction:** SELL
> **PnL:** -8.5 pips / $-53.76 | **R:** -0.22
> **Duration:** 23 min | **Close reason:** YELLOW
> **Peak pips:** 1.5
> **Setup:** S15


---

## 💡 💰 USD_CHF SELL win: +7.6p / $+94.92 (112min)
**Date:** 2026-04-01T01:46:29
**Type:** discovery
**Tags:** win, usdchf, guardian, S15

> [!tip] DISCOVERY
> **Pair:** USD_CHF | **Direction:** SELL
> **PnL:** +7.6 pips / $+94.92 | **R:** 2.53
> **Duration:** 112 min | **Close reason:** YELLOW
> **Peak pips:** 8.8
> **Setup:** S15


---

## 💡 💰 USD_CAD SELL win: +8.5p / $+51.17 (105min)
**Date:** 2026-04-01T01:49:31
**Type:** discovery
**Tags:** win, usdcad, guardian, S15

> [!tip] DISCOVERY
> **Pair:** USD_CAD | **Direction:** SELL
> **PnL:** +8.5 pips / $+51.17 | **R:** 2.83
> **Duration:** 105 min | **Close reason:** RED
> **Peak pips:** 9.1
> **Setup:** S15


---

## 💡 💰 EUR_AUD SELL win: +3.9p / $+26.91 (5min)
**Date:** 2026-04-01T04:06:33
**Type:** discovery
**Tags:** win, euraud, guardian, S5

> [!tip] DISCOVERY
> **Pair:** EUR_AUD | **Direction:** SELL
> **PnL:** +3.9 pips / $+26.91 | **R:** 0.95
> **Duration:** 5 min | **Close reason:** YELLOW
> **Peak pips:** 8.2
> **Setup:** S5


---

## 💡 💰 EUR_AUD SELL win: +3.0p / $+20.72 (8min)
**Date:** 2026-04-01T04:24:43
**Type:** discovery
**Tags:** win, euraud, guardian, S5

> [!tip] DISCOVERY
> **Pair:** EUR_AUD | **Direction:** SELL
> **PnL:** +3.0 pips / $+20.72 | **R:** 1.00
> **Duration:** 8 min | **Close reason:** GREEN
> **Peak pips:** 5.3
> **Setup:** S5


---

## ❌ ❌ EUR_GBP SELL loss: -1.7p / $-22.75 (3min)
**Date:** 2026-04-01T07:14:35
**Type:** failure
**Tags:** loss, eurgbp, guardian, unknown

> [!danger] FAILURE
> **Pair:** EUR_GBP | **Direction:** SELL
> **PnL:** -1.7 pips / $-22.75 | **R:** -0.11
> **Duration:** 3 min | **Close reason:** BLACK
> **Peak pips:** 0.0
> **Setup:** unknown


---

## 💡 💰 EUR_GBP SELL win: +1.6p / $+21.20 (22min)
**Date:** 2026-04-01T07:42:15
**Type:** discovery
**Tags:** win, eurgbp, guardian, S15

> [!tip] DISCOVERY
> **Pair:** EUR_GBP | **Direction:** SELL
> **PnL:** +1.6 pips / $+21.20 | **R:** 0.11
> **Duration:** 22 min | **Close reason:** YELLOW
> **Peak pips:** 2.3
> **Setup:** S15


---

## 💡 💰 EUR_AUD SELL win: +3.8p / $+0.12 (13min)
**Date:** 2026-04-01T07:48:18
**Type:** discovery
**Tags:** win, euraud, guardian, S1

> [!tip] DISCOVERY
> **Pair:** EUR_AUD | **Direction:** SELL
> **PnL:** +3.8 pips / $+0.12 | **R:** 0.10
> **Duration:** 13 min | **Close reason:** GREEN
> **Peak pips:** 10.0
> **Setup:** S1


---

## 💡 💰 EUR_CHF SELL win: +7.1p / $+89.25 (61min)
**Date:** 2026-04-01T08:20:18
**Type:** discovery
**Tags:** win, eurchf, guardian, S1

> [!tip] DISCOVERY
> **Pair:** EUR_CHF | **Direction:** SELL
> **PnL:** +7.1 pips / $+89.25 | **R:** 17.75
> **Duration:** 61 min | **Close reason:** YELLOW
> **Peak pips:** 8.2
> **Setup:** S1


---

## 💡 💰 USD_JPY SELL win: +4.9p / $+3.62 (62min)
**Date:** 2026-04-01T08:21:19
**Type:** discovery
**Tags:** win, usdjpy, guardian, S13

> [!tip] DISCOVERY
> **Pair:** USD_JPY | **Direction:** SELL
> **PnL:** +4.9 pips / $+3.62 | **R:** 1.00
> **Duration:** 62 min | **Close reason:** YELLOW
> **Peak pips:** 15.0
> **Setup:** S13


---

## ❌ ❌ USD_CHF SELL loss: -5.2p / $-65.96 (36min)
**Date:** 2026-04-01T08:26:36
**Type:** failure
**Tags:** loss, usdchf, guardian, S5

> [!danger] FAILURE
> **Pair:** USD_CHF | **Direction:** SELL
> **PnL:** -5.2 pips / $-65.96 | **R:** -1.02
> **Duration:** 36 min | **Close reason:** YELLOW
> **Peak pips:** 6.0
> **Setup:** S5


---

## ❌ ❌ EUR_AUD SELL loss: -38.2p / $-119.28 (4min)
**Date:** 2026-04-01T08:56:34
**Type:** failure
**Tags:** loss, euraud, guardian, S15

> [!danger] FAILURE
> **Pair:** EUR_AUD | **Direction:** SELL
> **PnL:** -38.2 pips / $-119.28 | **R:** -1.00
> **Duration:** 4 min | **Close reason:** GREEN
> **Peak pips:** 0.0
> **Setup:** S15


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

## ❌ ❌ USD_JPY SELL loss: -2.0p / $-0.16 (43min)
**Date:** 2026-04-01T11:14:16
**Type:** failure
**Tags:** loss, usdjpy, guardian, unknown

> [!danger] FAILURE
> **Pair:** USD_JPY | **Direction:** SELL
> **PnL:** -2.0 pips / $-0.16 | **R:** -1.05
> **Duration:** 43 min | **Close reason:** YELLOW
> **Peak pips:** 10.6
> **Setup:** unknown


---

## 💡 💰 EUR_GBP SELL win: +6.8p / $+90.21 (28min)
**Date:** 2026-04-01T11:56:31
**Type:** discovery
**Tags:** win, eurgbp, guardian, S15

> [!tip] DISCOVERY
> **Pair:** EUR_GBP | **Direction:** SELL
> **PnL:** +6.8 pips / $+90.21 | **R:** 0.99
> **Duration:** 28 min | **Close reason:** YELLOW
> **Peak pips:** 8.9
> **Setup:** S15


---

## 💡 💰 USD_JPY SELL win: +8.5p / $+53.34 (9min)
**Date:** 2026-04-01T12:59:35
**Type:** discovery
**Tags:** win, usdjpy, guardian, unknown

> [!tip] DISCOVERY
> **Pair:** USD_JPY | **Direction:** SELL
> **PnL:** +8.5 pips / $+53.34 | **R:** 4.05
> **Duration:** 9 min | **Close reason:** RED
> **Peak pips:** 9.4
> **Setup:** unknown


---

## 💡 💰 EUR_GBP SELL win: +1.6p / $+3.39 (17min)
**Date:** 2026-04-01T13:07:09
**Type:** discovery
**Tags:** win, eurgbp, guardian, S15

> [!tip] DISCOVERY
> **Pair:** EUR_GBP | **Direction:** SELL
> **PnL:** +1.6 pips / $+3.39 | **R:** 0.11
> **Duration:** 17 min | **Close reason:** YELLOW
> **Peak pips:** 1.6
> **Setup:** S15


---

## ❌ ❌ EUR_GBP BUY loss: -1.5p / $-16.90 (10min)
**Date:** 2026-04-01T13:16:29
**Type:** failure
**Tags:** loss, eurgbp, guardian, S15

> [!danger] FAILURE
> **Pair:** EUR_GBP | **Direction:** BUY
> **PnL:** -1.5 pips / $-16.90 | **R:** -0.11
> **Duration:** 10 min | **Close reason:** YELLOW
> **Peak pips:** 0.0
> **Setup:** S15


---

## ❌ ❌ USD_CHF SELL loss: -23.1p / $-292.10 (95min)
**Date:** 2026-04-01T15:00:15
**Type:** failure
**Tags:** loss, usdchf, guardian, S15

> [!danger] FAILURE
> **Pair:** USD_CHF | **Direction:** SELL
> **PnL:** -23.1 pips / $-292.10 | **R:** -1.00
> **Duration:** 95 min | **Close reason:** BLACK
> **Peak pips:** 0.0
> **Setup:** S15


---

## 💡 💰 EUR_CHF SELL win: +2.3p / $+6.87 (96min)
**Date:** 2026-04-01T15:00:30
**Type:** discovery
**Tags:** win, eurchf, guardian, S15

> [!tip] DISCOVERY
> **Pair:** EUR_CHF | **Direction:** SELL
> **PnL:** +2.3 pips / $+6.87 | **R:** 0.68
> **Duration:** 96 min | **Close reason:** BLACK
> **Peak pips:** 6.8
> **Setup:** S15


---

## ❌ ❌ EUR_CHF SELL loss: -7.9p / $-99.66 (26min)
**Date:** 2026-04-01T22:01:47
**Type:** failure
**Tags:** loss, eurchf, guardian, S15

> [!danger] FAILURE
> **Pair:** EUR_CHF | **Direction:** SELL
> **PnL:** -7.9 pips / $-99.66 | **R:** -1.00
> **Duration:** 26 min | **Close reason:** YELLOW
> **Peak pips:** 0.0
> **Setup:** S15


---

## 💡 💰 NZD_USD SELL win: +7.1p / $+71.00 (126min)
**Date:** 2026-04-02T00:52:48
**Type:** discovery
**Tags:** win, nzdusd, guardian, S1

> [!tip] DISCOVERY
> **Pair:** NZD_USD | **Direction:** SELL
> **PnL:** +7.1 pips / $+71.00 | **R:** 2.37
> **Duration:** 126 min | **Close reason:** RED
> **Peak pips:** 10.5
> **Setup:** S1


---

## 💡 💰 GBP_JPY SELL win: +14.0p / $+87.40 (21min)
**Date:** 2026-04-02T02:05:50
**Type:** discovery
**Tags:** win, gbpjpy, guardian, S15

> [!tip] DISCOVERY
> **Pair:** GBP_JPY | **Direction:** SELL
> **PnL:** +14.0 pips / $+87.40 | **R:** 3.04
> **Duration:** 21 min | **Close reason:** YELLOW
> **Peak pips:** 17.9
> **Setup:** S15


---

## 💡 💰 EUR_JPY BUY win: +16.9p / $+105.36 (25min)
**Date:** 2026-04-02T03:15:21
**Type:** discovery
**Tags:** win, eurjpy, guardian, S15

> [!tip] DISCOVERY
> **Pair:** EUR_JPY | **Direction:** BUY
> **PnL:** +16.9 pips / $+105.36 | **R:** 3.38
> **Duration:** 25 min | **Close reason:** YELLOW
> **Peak pips:** 18.7
> **Setup:** S15


---

## 💡 💰 GBP_JPY SELL win: +2.4p / $+14.96 (43min)
**Date:** 2026-04-02T06:43:23
**Type:** discovery
**Tags:** win, gbpjpy, guardian, S13

> [!tip] DISCOVERY
> **Pair:** GBP_JPY | **Direction:** SELL
> **PnL:** +2.4 pips / $+14.96 | **R:** 0.80
> **Duration:** 43 min | **Close reason:** YELLOW
> **Peak pips:** 9.5
> **Setup:** S13


---

## 💡 💰 AUD_USD SELL win: +5.4p / $+54.00 (67min)
**Date:** 2026-04-02T07:14:52
**Type:** discovery
**Tags:** win, audusd, guardian, S1

> [!tip] DISCOVERY
> **Pair:** AUD_USD | **Direction:** SELL
> **PnL:** +5.4 pips / $+54.00 | **R:** 1.80
> **Duration:** 67 min | **Close reason:** YELLOW
> **Peak pips:** 7.0
> **Setup:** S1


---

## ❌ ❌ AUD_USD SELL loss: -16.6p / $-166.00 (95min)
**Date:** 2026-04-02T09:47:14
**Type:** failure
**Tags:** loss, audusd, guardian, S1

> [!danger] FAILURE
> **Pair:** AUD_USD | **Direction:** SELL
> **PnL:** -16.6 pips / $-166.00 | **R:** -1.00
> **Duration:** 95 min | **Close reason:** BLACK
> **Peak pips:** 0.5
> **Setup:** S1


---

## ❌ ❌ EUR_USD SELL loss: -8.5p / $-85.00 (106min)
**Date:** 2026-04-02T10:02:51
**Type:** failure
**Tags:** loss, eurusd, guardian, S5

> [!danger] FAILURE
> **Pair:** EUR_USD | **Direction:** SELL
> **PnL:** -8.5 pips / $-85.00 | **R:** -0.42
> **Duration:** 106 min | **Close reason:** BLACK
> **Peak pips:** 1.8
> **Setup:** S5


---

## 💡 💰 EUR_AUD SELL win: +2.7p / $+18.53 (23min)
**Date:** 2026-04-02T10:34:01
**Type:** discovery
**Tags:** win, euraud, guardian, S15

> [!tip] DISCOVERY
> **Pair:** EUR_AUD | **Direction:** SELL
> **PnL:** +2.7 pips / $+18.53 | **R:** 0.90
> **Duration:** 23 min | **Close reason:** GREEN
> **Peak pips:** 5.2
> **Setup:** S15


---

## ❌ ❌ EUR_AUD SELL loss: -17.6p / $-122.08 (7min)
**Date:** 2026-04-02T10:50:21
**Type:** failure
**Tags:** loss, euraud, guardian, unknown

> [!danger] FAILURE
> **Pair:** EUR_AUD | **Direction:** SELL
> **PnL:** -17.6 pips / $-122.08 | **R:** -1.01
> **Duration:** 7 min | **Close reason:** YELLOW
> **Peak pips:** 3.5
> **Setup:** unknown


---

## 💡 💰 NZD_USD SELL win: +1.1p / $+11.00 (8min)
**Date:** 2026-04-02T12:12:42
**Type:** discovery
**Tags:** win, nzdusd, guardian, unknown

> [!tip] DISCOVERY
> **Pair:** NZD_USD | **Direction:** SELL
> **PnL:** +1.1 pips / $+11.00 | **R:** 0.92
> **Duration:** 8 min | **Close reason:** YELLOW
> **Peak pips:** 3.4
> **Setup:** unknown


---

## ❌ ❌ EUR_JPY BUY loss: -17.1p / $-107.83 (9min)
**Date:** 2026-04-02T12:13:58
**Type:** failure
**Tags:** loss, eurjpy, guardian, unknown

> [!danger] FAILURE
> **Pair:** EUR_JPY | **Direction:** BUY
> **PnL:** -17.1 pips / $-107.83 | **R:** -0.44
> **Duration:** 9 min | **Close reason:** YELLOW
> **Peak pips:** 0.0
> **Setup:** unknown


---

## 💡 💰 EUR_AUD SELL win: +1.0p / $+3.82 (2min)
**Date:** 2026-04-02T12:22:09
**Type:** discovery
**Tags:** win, euraud, guardian, S5

> [!tip] DISCOVERY
> **Pair:** EUR_AUD | **Direction:** SELL
> **PnL:** +1.0 pips / $+3.82 | **R:** 0.91
> **Duration:** 2 min | **Close reason:** GREEN
> **Peak pips:** 3.8
> **Setup:** S5


---

## 💡 💰 EUR_AUD SELL win: +1.0p / $+6.88 (11min)
**Date:** 2026-04-02T12:33:14
**Type:** discovery
**Tags:** win, euraud, guardian, S5

> [!tip] DISCOVERY
> **Pair:** EUR_AUD | **Direction:** SELL
> **PnL:** +1.0 pips / $+6.88 | **R:** 1.00
> **Duration:** 11 min | **Close reason:** GREEN
> **Peak pips:** 3.4
> **Setup:** S5


---

## 💡 💰 EUR_JPY BUY win: +1.0p / $+6.24 (4min)
**Date:** 2026-04-02T13:06:44
**Type:** discovery
**Tags:** win, eurjpy, guardian, S15

> [!tip] DISCOVERY
> **Pair:** EUR_JPY | **Direction:** BUY
> **PnL:** +1.0 pips / $+6.24 | **R:** 1.00
> **Duration:** 4 min | **Close reason:** YELLOW
> **Peak pips:** 3.3
> **Setup:** S15


---

## 💡 💰 EUR_AUD SELL win: +2.8p / $+19.25 (21min)
**Date:** 2026-04-02T14:06:39
**Type:** discovery
**Tags:** win, euraud, guardian, S5

> [!tip] DISCOVERY
> **Pair:** EUR_AUD | **Direction:** SELL
> **PnL:** +2.8 pips / $+19.25 | **R:** 0.93
> **Duration:** 21 min | **Close reason:** YELLOW
> **Peak pips:** 8.0
> **Setup:** S5


---

## 💡 💰 EUR_AUD SELL win: +1.6p / $+11.01 (88min)
**Date:** 2026-04-02T20:41:12
**Type:** discovery
**Tags:** win, euraud, guardian, S13

> [!tip] DISCOVERY
> **Pair:** EUR_AUD | **Direction:** SELL
> **PnL:** +1.6 pips / $+11.01 | **R:** 1.00
> **Duration:** 88 min | **Close reason:** GREEN
> **Peak pips:** 5.3
> **Setup:** S13


---

## 💡 💰 GBP_USD SELL win: +4.4p / $+44.00 (12min)
**Date:** 2026-04-03T10:12:25
**Type:** discovery
**Tags:** win, gbpusd, guardian, unknown

> [!tip] DISCOVERY
> **Pair:** GBP_USD | **Direction:** SELL
> **PnL:** +4.4 pips / $+44.00 | **R:** 1.47
> **Duration:** 12 min | **Close reason:** YELLOW
> **Peak pips:** 5.6
> **Setup:** unknown


---

## 💡 💰 EUR_USD SELL win: +6.2p / $+62.00 (21min)
**Date:** 2026-04-03T10:23:46
**Type:** discovery
**Tags:** win, eurusd, guardian, S15

> [!tip] DISCOVERY
> **Pair:** EUR_USD | **Direction:** SELL
> **PnL:** +6.2 pips / $+62.00 | **R:** 2.07
> **Duration:** 21 min | **Close reason:** YELLOW
> **Peak pips:** 7.1
> **Setup:** S15


---

## ❌ ❌ GBP_JPY SELL loss: -9.5p / $-59.80 (27min)
**Date:** 2026-04-03T11:59:45
**Type:** failure
**Tags:** loss, gbpjpy, guardian, S5

> [!danger] FAILURE
> **Pair:** GBP_JPY | **Direction:** SELL
> **PnL:** -9.5 pips / $-59.80 | **R:** -1.07
> **Duration:** 27 min | **Close reason:** GREEN
> **Peak pips:** 4.1
> **Setup:** S5


---

## 💡 💰 EUR_USD SELL win: +4.2p / $+42.00 (17min)
**Date:** 2026-04-03T12:22:51
**Type:** discovery
**Tags:** win, eurusd, guardian, unknown

> [!tip] DISCOVERY
> **Pair:** EUR_USD | **Direction:** SELL
> **PnL:** +4.2 pips / $+42.00 | **R:** 0.98
> **Duration:** 17 min | **Close reason:** GREEN
> **Peak pips:** 5.2
> **Setup:** unknown


---

## ❌ ❌ GBP_JPY SELL loss: -0.8p / $-5.04 (96min)
**Date:** 2026-04-03T14:28:03
**Type:** failure
**Tags:** loss, gbpjpy, guardian, S5

> [!danger] FAILURE
> **Pair:** GBP_JPY | **Direction:** SELL
> **PnL:** -0.8 pips / $-5.04 | **R:** -0.50
> **Duration:** 96 min | **Close reason:** YELLOW
> **Peak pips:** 5.3
> **Setup:** S5


---

## ❌ ❌ GBP_JPY SELL loss: -42.7p / $-268.69 (4min)
**Date:** 2026-04-05T17:39:55
**Type:** failure
**Tags:** loss, gbpjpy, guardian, S5

> [!danger] FAILURE
> **Pair:** GBP_JPY | **Direction:** SELL
> **PnL:** -42.7 pips / $-268.69 | **R:** -1.07
> **Duration:** 4 min | **Close reason:** YELLOW
> **Peak pips:** 0.0
> **Setup:** S5


---

## ❌ ❌ GBP_JPY SELL loss: -24.4p / $-153.46 (79min)
**Date:** 2026-04-05T20:10:20
**Type:** failure
**Tags:** loss, gbpjpy, guardian, S15

> [!danger] FAILURE
> **Pair:** GBP_JPY | **Direction:** SELL
> **PnL:** -24.4 pips / $-153.46 | **R:** -0.43
> **Duration:** 79 min | **Close reason:** YELLOW
> **Peak pips:** 0.0
> **Setup:** S15


---

## 💡 💰 EUR_USD SELL win: +4.7p / $+47.00 (61min)
**Date:** 2026-04-05T21:10:03
**Type:** discovery
**Tags:** win, eurusd, guardian, S5

> [!tip] DISCOVERY
> **Pair:** EUR_USD | **Direction:** SELL
> **PnL:** +4.7 pips / $+47.00 | **R:** 0.66
> **Duration:** 61 min | **Close reason:** GREEN
> **Peak pips:** 5.6
> **Setup:** S5


---

## ❌ ❌ EUR_USD SELL loss: -13.4p / $-134.00 (53min)
**Date:** 2026-04-05T22:11:15
**Type:** failure
**Tags:** loss, eurusd, guardian, S15

> [!danger] FAILURE
> **Pair:** EUR_USD | **Direction:** SELL
> **PnL:** -13.4 pips / $-134.00 | **R:** -0.67
> **Duration:** 53 min | **Close reason:** YELLOW
> **Peak pips:** 2.7
> **Setup:** S15


---

## 💡 💰 EUR_AUD SELL win: +4.2p / $+28.98 (18min)
**Date:** 2026-04-06T04:35:50
**Type:** discovery
**Tags:** win, euraud, guardian, S15

> [!tip] DISCOVERY
> **Pair:** EUR_AUD | **Direction:** SELL
> **PnL:** +4.2 pips / $+28.98 | **R:** 0.68
> **Duration:** 18 min | **Close reason:** GREEN
> **Peak pips:** 6.3
> **Setup:** S15


---

## ❌ ❌ EUR_AUD SELL loss: -5.4p / $-37.59 (6min)
**Date:** 2026-04-06T06:00:27
**Type:** failure
**Tags:** loss, euraud, guardian, S5

> [!danger] FAILURE
> **Pair:** EUR_AUD | **Direction:** SELL
> **PnL:** -5.4 pips / $-37.59 | **R:** -0.19
> **Duration:** 6 min | **Close reason:** YELLOW
> **Peak pips:** 0.0
> **Setup:** S5


---

## ❌ ❌ USD_JPY SELL loss: -7.9p / $-49.79 (98min)
**Date:** 2026-04-06T06:41:29
**Type:** failure
**Tags:** loss, usdjpy, guardian, unknown

> [!danger] FAILURE
> **Pair:** USD_JPY | **Direction:** SELL
> **PnL:** -7.9 pips / $-49.79 | **R:** -0.32
> **Duration:** 98 min | **Close reason:** BLACK
> **Peak pips:** 2.5
> **Setup:** unknown


---

## 💡 💰 EUR_AUD SELL win: +5.8p / $+40.00 (32min)
**Date:** 2026-04-06T07:48:43
**Type:** discovery
**Tags:** win, euraud, guardian, S5

> [!tip] DISCOVERY
> **Pair:** EUR_AUD | **Direction:** SELL
> **PnL:** +5.8 pips / $+40.00 | **R:** 0.94
> **Duration:** 32 min | **Close reason:** GREEN
> **Peak pips:** 7.2
> **Setup:** S5


---

## ❌ ❌ EUR_AUD SELL loss: -11.5p / $-80.11 (93min)
**Date:** 2026-04-06T09:46:17
**Type:** failure
**Tags:** loss, euraud, guardian, unknown

> [!danger] FAILURE
> **Pair:** EUR_AUD | **Direction:** SELL
> **PnL:** -11.5 pips / $-80.11 | **R:** -0.35
> **Duration:** 93 min | **Close reason:** RED
> **Peak pips:** 0.0
> **Setup:** unknown


---

## 💡 💰 NZD_USD SELL win: +5.2p / $+52.00 (23min)
**Date:** 2026-04-06T21:39:28
**Type:** discovery
**Tags:** win, nzdusd, guardian, S1

> [!tip] DISCOVERY
> **Pair:** NZD_USD | **Direction:** SELL
> **PnL:** +5.2 pips / $+52.00 | **R:** 0.98
> **Duration:** 23 min | **Close reason:** YELLOW
> **Peak pips:** 6.5
> **Setup:** S1


---

## ❌ ❌ NZD_USD BUY loss: -6.8p / $-68.00 (3min)
**Date:** 2026-04-06T22:13:14
**Type:** failure
**Tags:** loss, nzdusd, guardian, S1

> [!danger] FAILURE
> **Pair:** NZD_USD | **Direction:** BUY
> **PnL:** -6.8 pips / $-68.00 | **R:** -0.57
> **Duration:** 3 min | **Close reason:** YELLOW
> **Peak pips:** 0.0
> **Setup:** S1


---

## ❌ ❌ EUR_USD SELL loss: -6.6p / $-66.00 (92min)
**Date:** 2026-04-07T00:00:46
**Type:** failure
**Tags:** loss, eurusd, guardian, unknown

> [!danger] FAILURE
> **Pair:** EUR_USD | **Direction:** SELL
> **PnL:** -6.6 pips / $-66.00 | **R:** -0.51
> **Duration:** 92 min | **Close reason:** BLACK
> **Peak pips:** 0.0
> **Setup:** unknown


---

## ❌ ❌ NZD_USD SELL loss: -8.5p / $-85.00 (123min)
**Date:** 2026-04-07T00:37:10
**Type:** failure
**Tags:** loss, nzdusd, guardian, S5

> [!danger] FAILURE
> **Pair:** NZD_USD | **Direction:** SELL
> **PnL:** -8.5 pips / $-85.00 | **R:** -0.48
> **Duration:** 123 min | **Close reason:** BLACK
> **Peak pips:** 0.0
> **Setup:** S5


---

## 💡 💰 EUR_AUD SELL win: +5.0p / $+34.51 (15min)
**Date:** 2026-04-07T08:02:16
**Type:** discovery
**Tags:** win, euraud, guardian, unknown

> [!tip] DISCOVERY
> **Pair:** EUR_AUD | **Direction:** SELL
> **PnL:** +5.0 pips / $+34.51 | **R:** 0.60
> **Duration:** 15 min | **Close reason:** GREEN
> **Peak pips:** 6.9
> **Setup:** unknown


---

## 💡 💰 EUR_AUD SELL win: +1.9p / $+13.19 (10min)
**Date:** 2026-04-07T16:34:08
**Type:** discovery
**Tags:** win, euraud, guardian, S15

> [!tip] DISCOVERY
> **Pair:** EUR_AUD | **Direction:** SELL
> **PnL:** +1.9 pips / $+13.19 | **R:** 0.21
> **Duration:** 10 min | **Close reason:** GREEN
> **Peak pips:** 5.2
> **Setup:** S15


---

## ❌ ❌ USD_CAD SELL loss: -13.0p / $-94.32 (58min)
**Date:** 2026-04-07T20:48:02
**Type:** failure
**Tags:** loss, usdcad, guardian, S5

> [!danger] FAILURE
> **Pair:** USD_CAD | **Direction:** SELL
> **PnL:** -13.0 pips / $-94.32 | **R:** -1.00
> **Duration:** 58 min | **Close reason:** YELLOW
> **Peak pips:** 4.9
> **Setup:** S5


---

## 💡 💰 EUR_AUD SELL win: +3.9p / $+27.41 (17min)
**Date:** 2026-04-07T21:13:54
**Type:** discovery
**Tags:** win, euraud, guardian, S5

> [!tip] DISCOVERY
> **Pair:** EUR_AUD | **Direction:** SELL
> **PnL:** +3.9 pips / $+27.41 | **R:** 0.32
> **Duration:** 17 min | **Close reason:** YELLOW
> **Peak pips:** 5.3
> **Setup:** S5


---

## ❌ ❌ EUR_GBP SELL loss: -1.4p / $-18.85 (97min)
**Date:** 2026-04-07T23:53:49
**Type:** failure
**Tags:** loss, eurgbp, guardian, S5

> [!danger] FAILURE
> **Pair:** EUR_GBP | **Direction:** SELL
> **PnL:** -1.4 pips / $-18.85 | **R:** -0.12
> **Duration:** 97 min | **Close reason:** BLACK
> **Peak pips:** 0.7
> **Setup:** S5


---

## ❌ ❌ EUR_AUD SELL loss: -0.5p / $-3.54 (17min)
**Date:** 2026-04-08T14:03:23
**Type:** failure
**Tags:** loss, euraud, guardian, S15

> [!danger] FAILURE
> **Pair:** EUR_AUD | **Direction:** SELL
> **PnL:** -0.5 pips / $-3.54 | **R:** -0.83
> **Duration:** 17 min | **Close reason:** GREEN
> **Peak pips:** 3.1
> **Setup:** S15


---

## 💡 💰 EUR_AUD SELL win: +3.8p / $+26.66 (17min)
**Date:** 2026-04-08T15:57:33
**Type:** discovery
**Tags:** win, euraud, guardian, S15

> [!tip] DISCOVERY
> **Pair:** EUR_AUD | **Direction:** SELL
> **PnL:** +3.8 pips / $+26.66 | **R:** 0.95
> **Duration:** 17 min | **Close reason:** GREEN
> **Peak pips:** 5.7
> **Setup:** S15


---

## 💡 💰 USD_CHF SELL win: +3.1p / $+39.03 (23min)
**Date:** 2026-04-09T09:12:09
**Type:** discovery
**Tags:** win, usdchf, guardian, S15

> [!tip] DISCOVERY
> **Pair:** USD_CHF | **Direction:** SELL
> **PnL:** +3.1 pips / $+39.03 | **R:** 0.94
> **Duration:** 23 min | **Close reason:** GREEN
> **Peak pips:** 3.9
> **Setup:** S15


---

## 💡 💰 USD_CHF SELL win: +4.2p / $+52.95 (11min)
**Date:** 2026-04-09T09:39:52
**Type:** discovery
**Tags:** win, usdchf, guardian, S1

> [!tip] DISCOVERY
> **Pair:** USD_CHF | **Direction:** SELL
> **PnL:** +4.2 pips / $+52.95 | **R:** 0.53
> **Duration:** 11 min | **Close reason:** GREEN
> **Peak pips:** 5.0
> **Setup:** S1


---

## 💡 💰 USD_CHF SELL win: +4.5p / $+56.74 (13min)
**Date:** 2026-04-09T10:16:56
**Type:** discovery
**Tags:** win, usdchf, guardian, S15

> [!tip] DISCOVERY
> **Pair:** USD_CHF | **Direction:** SELL
> **PnL:** +4.5 pips / $+56.74 | **R:** 0.65
> **Duration:** 13 min | **Close reason:** GREEN
> **Peak pips:** 5.3
> **Setup:** S15


---

## 💡 💰 EUR_AUD SELL win: +4.4p / $+31.01 (6min)
**Date:** 2026-04-09T11:58:47
**Type:** discovery
**Tags:** win, euraud, guardian, S1

> [!tip] DISCOVERY
> **Pair:** EUR_AUD | **Direction:** SELL
> **PnL:** +4.4 pips / $+31.01 | **R:** 1.00
> **Duration:** 6 min | **Close reason:** GREEN
> **Peak pips:** 6.3
> **Setup:** S1


---

## 💡 💰 EUR_AUD SELL win: +3.5p / $+24.68 (4min)
**Date:** 2026-04-09T12:02:49
**Type:** discovery
**Tags:** win, euraud, guardian, S1

> [!tip] DISCOVERY
> **Pair:** EUR_AUD | **Direction:** SELL
> **PnL:** +3.5 pips / $+24.68 | **R:** 0.97
> **Duration:** 4 min | **Close reason:** GREEN
> **Peak pips:** 5.1
> **Setup:** S1


---

## 💡 💰 USD_CHF SELL win: +4.4p / $+55.56 (87min)
**Date:** 2026-04-09T13:41:56
**Type:** discovery
**Tags:** win, usdchf, guardian, S5

> [!tip] DISCOVERY
> **Pair:** USD_CHF | **Direction:** SELL
> **PnL:** +4.4 pips / $+55.56 | **R:** 0.58
> **Duration:** 87 min | **Close reason:** YELLOW
> **Peak pips:** 5.1
> **Setup:** S5


---

## 💡 💰 EUR_AUD SELL win: +3.0p / $+21.15 (240min)
**Date:** 2026-04-09T16:19:11
**Type:** discovery
**Tags:** win, euraud, guardian, S1

> [!tip] DISCOVERY
> **Pair:** EUR_AUD | **Direction:** SELL
> **PnL:** +3.0 pips / $+21.15 | **R:** 0.83
> **Duration:** 240 min | **Close reason:** YELLOW
> **Peak pips:** 5.1
> **Setup:** S1


---

## 💡 💰 USD_CHF SELL win: +7.6p / $+95.86 (50min)
**Date:** 2026-04-10T05:19:40
**Type:** discovery
**Tags:** win, usdchf, guardian, S1

> [!tip] DISCOVERY
> **Pair:** USD_CHF | **Direction:** SELL
> **PnL:** +7.6 pips / $+95.86 | **R:** 0.78
> **Duration:** 50 min | **Close reason:** GREEN
> **Peak pips:** 7.6
> **Setup:** S1


---

## 💡 💰 USD_CHF SELL win: +4.3p / $+54.21 (35min)
**Date:** 2026-04-10T06:58:56
**Type:** discovery
**Tags:** win, usdchf, guardian, S15

> [!tip] DISCOVERY
> **Pair:** USD_CHF | **Direction:** SELL
> **PnL:** +4.3 pips / $+54.21 | **R:** 0.64
> **Duration:** 35 min | **Close reason:** GREEN
> **Peak pips:** 5.1
> **Setup:** S15


---

## 💡 💰 USD_CHF SELL win: +4.7p / $+59.31 (60min)
**Date:** 2026-04-10T08:14:01
**Type:** discovery
**Tags:** win, usdchf, guardian, S15

> [!tip] DISCOVERY
> **Pair:** USD_CHF | **Direction:** SELL
> **PnL:** +4.7 pips / $+59.31 | **R:** 0.66
> **Duration:** 60 min | **Close reason:** GREEN
> **Peak pips:** 5.4
> **Setup:** S15


---

## 💡 💰 USD_CHF SELL win: +4.6p / $+58.09 (40min)
**Date:** 2026-04-10T09:08:41
**Type:** discovery
**Tags:** win, usdchf, guardian, S1

> [!tip] DISCOVERY
> **Pair:** USD_CHF | **Direction:** SELL
> **PnL:** +4.6 pips / $+58.09 | **R:** 0.63
> **Duration:** 40 min | **Close reason:** GREEN
> **Peak pips:** 5.4
> **Setup:** S1


---

## 💡 💰 USD_CHF SELL win: +7.2p / $+91.12 (6min)
**Date:** 2026-04-10T09:29:51
**Type:** discovery
**Tags:** win, usdchf, guardian, S1

> [!tip] DISCOVERY
> **Pair:** USD_CHF | **Direction:** SELL
> **PnL:** +7.2 pips / $+91.12 | **R:** 0.63
> **Duration:** 6 min | **Close reason:** GREEN
> **Peak pips:** 7.6
> **Setup:** S1


---

## ❌ ❌ USD_CHF SELL loss: -35.3p / $-449.15 (9min)
**Date:** 2026-04-10T10:55:28
**Type:** failure
**Tags:** loss, usdchf, guardian, S5

> [!danger] FAILURE
> **Pair:** USD_CHF | **Direction:** SELL
> **PnL:** -35.3 pips / $-449.15 | **R:** -1.01
> **Duration:** 9 min | **Close reason:** GREEN
> **Peak pips:** 0.0
> **Setup:** S5


---

## 💡 💰 USD_CHF SELL win: +3.9p / $+48.95 (5min)
**Date:** 2026-04-13T09:51:19
**Type:** discovery
**Tags:** win, usdchf, guardian, S1

> [!tip] DISCOVERY
> **Pair:** USD_CHF | **Direction:** SELL
> **PnL:** +3.9 pips / $+48.95 | **R:** 1.00
> **Duration:** 5 min | **Close reason:** GREEN
> **Peak pips:** 5.5
> **Setup:** S1


---

## 💡 💰 USD_CHF SELL win: +4.3p / $+54.07 (19min)
**Date:** 2026-04-13T10:40:24
**Type:** discovery
**Tags:** win, usdchf, guardian, S1

> [!tip] DISCOVERY
> **Pair:** USD_CHF | **Direction:** SELL
> **PnL:** +4.3 pips / $+54.07 | **R:** 0.53
> **Duration:** 19 min | **Close reason:** GREEN
> **Peak pips:** 5.2
> **Setup:** S1


---

## 💡 💰 EUR_CHF SELL win: +4.5p / $+56.59 (98min)
**Date:** 2026-04-13T12:24:56
**Type:** discovery
**Tags:** win, eurchf, guardian, S5

> [!tip] DISCOVERY
> **Pair:** EUR_CHF | **Direction:** SELL
> **PnL:** +4.5 pips / $+56.59 | **R:** 0.68
> **Duration:** 98 min | **Close reason:** GREEN
> **Peak pips:** 5.3
> **Setup:** S5


---

## 💡 💰 USD_CHF SELL win: +4.8p / $+60.41 (107min)
**Date:** 2026-04-13T12:35:17
**Type:** discovery
**Tags:** win, usdchf, guardian, S5

> [!tip] DISCOVERY
> **Pair:** USD_CHF | **Direction:** SELL
> **PnL:** +4.8 pips / $+60.41 | **R:** 0.64
> **Duration:** 107 min | **Close reason:** GREEN
> **Peak pips:** 5.1
> **Setup:** S5


---

## 💡 💰 EUR_AUD SELL win: +4.4p / $+30.85 (23min)
**Date:** 2026-04-13T12:50:54
**Type:** discovery
**Tags:** win, euraud, guardian, S15

> [!tip] DISCOVERY
> **Pair:** EUR_AUD | **Direction:** SELL
> **PnL:** +4.4 pips / $+30.85 | **R:** 0.96
> **Duration:** 23 min | **Close reason:** YELLOW
> **Peak pips:** 6.5
> **Setup:** S15


---

## 💡 💰 USD_CHF SELL win: +4.9p / $+61.73 (14min)
**Date:** 2026-04-13T12:51:40
**Type:** discovery
**Tags:** win, usdchf, guardian, S5

> [!tip] DISCOVERY
> **Pair:** USD_CHF | **Direction:** SELL
> **PnL:** +4.9 pips / $+61.73 | **R:** 0.56
> **Duration:** 14 min | **Close reason:** GREEN
> **Peak pips:** 5.9
> **Setup:** S5


---

## 💡 💰 USD_CHF SELL win: +4.8p / $+60.54 (10min)
**Date:** 2026-04-13T13:19:05
**Type:** discovery
**Tags:** win, usdchf, guardian, S1

> [!tip] DISCOVERY
> **Pair:** USD_CHF | **Direction:** SELL
> **PnL:** +4.8 pips / $+60.54 | **R:** 0.53
> **Duration:** 10 min | **Close reason:** YELLOW
> **Peak pips:** 5.7
> **Setup:** S1


---

## 💡 💰 EUR_CHF SELL win: +4.5p / $+56.78 (86min)
**Date:** 2026-04-13T14:23:50
**Type:** discovery
**Tags:** win, eurchf, guardian, S5

> [!tip] DISCOVERY
> **Pair:** EUR_CHF | **Direction:** SELL
> **PnL:** +4.5 pips / $+56.78 | **R:** 0.65
> **Duration:** 86 min | **Close reason:** GREEN
> **Peak pips:** 5.4
> **Setup:** S5


---

## ❌ ❌ EUR_AUD SELL loss: -26.3p / $-188.50 (182min)
**Date:** 2026-04-13T17:41:12
**Type:** failure
**Tags:** loss, euraud, guardian, S13

> [!danger] FAILURE
> **Pair:** EUR_AUD | **Direction:** SELL
> **PnL:** -26.3 pips / $-188.50 | **R:** -0.67
> **Duration:** 182 min | **Close reason:** BLACK
> **Peak pips:** 0.0
> **Setup:** S13


---

## ❌ ❌ USD_CHF SELL loss: -4.6p / $-59.30 (219min)
**Date:** 2026-04-13T21:43:40
**Type:** failure
**Tags:** loss, usdchf, guardian, S5

> [!danger] FAILURE
> **Pair:** USD_CHF | **Direction:** SELL
> **PnL:** -4.6 pips / $-59.30 | **R:** -0.08
> **Duration:** 219 min | **Close reason:** BLACK
> **Peak pips:** 0.7
> **Setup:** S5


---

## 💡 💰 USD_CHF SELL win: +4.4p / $+55.83 (29min)
**Date:** 2026-04-14T03:35:27
**Type:** discovery
**Tags:** win, usdchf, guardian, S1

> [!tip] DISCOVERY
> **Pair:** USD_CHF | **Direction:** SELL
> **PnL:** +4.4 pips / $+55.83 | **R:** 0.46
> **Duration:** 29 min | **Close reason:** GREEN
> **Peak pips:** 5.3
> **Setup:** S1


---

## 💡 💰 EUR_CHF SELL win: +4.3p / $+54.54 (28min)
**Date:** 2026-04-14T04:59:24
**Type:** discovery
**Tags:** win, eurchf, guardian, S1

> [!tip] DISCOVERY
> **Pair:** EUR_CHF | **Direction:** SELL
> **PnL:** +4.3 pips / $+54.54 | **R:** 0.60
> **Duration:** 28 min | **Close reason:** GREEN
> **Peak pips:** 5.3
> **Setup:** S1


---

## ❌ ❌ USD_CHF SELL loss: -5.3p / $-68.56 (182min)
**Date:** 2026-04-14T06:53:42
**Type:** failure
**Tags:** loss, usdchf, guardian, S5

> [!danger] FAILURE
> **Pair:** USD_CHF | **Direction:** SELL
> **PnL:** -5.3 pips / $-68.56 | **R:** -0.10
> **Duration:** 182 min | **Close reason:** BLACK
> **Peak pips:** 1.9
> **Setup:** S5


---

## 💡 💰 EUR_AUD SELL win: +3.6p / $+25.39 (19min)
**Date:** 2026-04-14T07:21:10
**Type:** discovery
**Tags:** win, euraud, guardian, unknown

> [!tip] DISCOVERY
> **Pair:** EUR_AUD | **Direction:** SELL
> **PnL:** +3.6 pips / $+25.39 | **R:** 0.90
> **Duration:** 19 min | **Close reason:** GREEN
> **Peak pips:** 5.7
> **Setup:** unknown


---

## ❌ ❌ EUR_AUD SELL loss: +0.0p / $+31.74 (7min)
**Date:** 2026-04-14T07:43:49
**Type:** failure
**Tags:** loss, euraud, guardian, unknown

> [!danger] FAILURE
> **Pair:** EUR_AUD | **Direction:** SELL
> **PnL:** +0.0 pips / $+31.74 | **R:** 0.00
> **Duration:** 7 min | **Close reason:** GREEN
> **Peak pips:** 6.3
> **Setup:** unknown


---

## 💡 💰 EUR_AUD SELL win: +2.9p / $+20.47 (5min)
**Date:** 2026-04-14T08:43:45
**Type:** discovery
**Tags:** win, euraud, guardian, S5

> [!tip] DISCOVERY
> **Pair:** EUR_AUD | **Direction:** SELL
> **PnL:** +2.9 pips / $+20.47 | **R:** 0.81
> **Duration:** 5 min | **Close reason:** GREEN
> **Peak pips:** 5.1
> **Setup:** S5


---

## 💡 💰 EUR_AUD SELL win: +4.8p / $+33.92 (28min)
**Date:** 2026-04-14T09:59:20
**Type:** discovery
**Tags:** win, euraud, guardian, S5

> [!tip] DISCOVERY
> **Pair:** EUR_AUD | **Direction:** SELL
> **PnL:** +4.8 pips / $+33.92 | **R:** 0.50
> **Duration:** 28 min | **Close reason:** GREEN
> **Peak pips:** 6.4
> **Setup:** S5


---

## ❌ ❌ USD_CHF SELL loss: -16.4p / $-212.10 (182min)
**Date:** 2026-04-14T16:26:20
**Type:** failure
**Tags:** loss, usdchf, guardian, unknown

> [!danger] FAILURE
> **Pair:** USD_CHF | **Direction:** SELL
> **PnL:** -16.4 pips / $-212.10 | **R:** -0.41
> **Duration:** 182 min | **Close reason:** BLACK
> **Peak pips:** 0.0
> **Setup:** unknown


---

## ❌ ❌ EUR_AUD SELL loss: +0.0p / $-285.04 (17min)
**Date:** 2026-04-14T17:04:55
**Type:** failure
**Tags:** loss, euraud, guardian, S1

> [!danger] FAILURE
> **Pair:** EUR_AUD | **Direction:** SELL
> **PnL:** +0.0 pips / $-285.04 | **R:** 0.00
> **Duration:** 17 min | **Close reason:** GREEN
> **Peak pips:** 0.0
> **Setup:** S1


---

## 💡 💰 EUR_AUD SELL win: +3.9p / $+27.53 (16min)
**Date:** 2026-04-14T22:50:50
**Type:** discovery
**Tags:** win, euraud, guardian, S1

> [!tip] DISCOVERY
> **Pair:** EUR_AUD | **Direction:** SELL
> **PnL:** +3.9 pips / $+27.53 | **R:** 1.00
> **Duration:** 16 min | **Close reason:** GREEN
> **Peak pips:** 5.6
> **Setup:** S1


---

## 💡 💰 EUR_AUD SELL win: +3.8p / $+26.85 (125min)
**Date:** 2026-04-15T01:11:02
**Type:** discovery
**Tags:** win, euraud, guardian, S5

> [!tip] DISCOVERY
> **Pair:** EUR_AUD | **Direction:** SELL
> **PnL:** +3.8 pips / $+26.85 | **R:** 0.97
> **Duration:** 125 min | **Close reason:** GREEN
> **Peak pips:** 5.6
> **Setup:** S5


---

## 💡 💰 EUR_JPY SELL win: +5.2p / $+0.02 (9min)
**Date:** 2026-04-15T02:19:04
**Type:** discovery
**Tags:** win, eurjpy, guardian, S15

> [!tip] DISCOVERY
> **Pair:** EUR_JPY | **Direction:** SELL
> **PnL:** +5.2 pips / $+0.02 | **R:** 0.62
> **Duration:** 9 min | **Close reason:** GREEN
> **Peak pips:** 6.7
> **Setup:** S15


---

## ❌ ❌ EUR_AUD SELL loss: -7.1p / $-51.19 (10min)
**Date:** 2026-04-15T02:20:05
**Type:** failure
**Tags:** loss, euraud, guardian, S5

> [!danger] FAILURE
> **Pair:** EUR_AUD | **Direction:** SELL
> **PnL:** -7.1 pips / $-51.19 | **R:** -0.17
> **Duration:** 10 min | **Close reason:** BLACK
> **Peak pips:** 0.0
> **Setup:** S5


---

## 💡 💰 USD_JPY SELL win: +5.5p / $+0.02 (77min)
**Date:** 2026-04-15T04:04:50
**Type:** discovery
**Tags:** win, usdjpy, guardian, S1

> [!tip] DISCOVERY
> **Pair:** USD_JPY | **Direction:** SELL
> **PnL:** +5.5 pips / $+0.02 | **R:** 0.55
> **Duration:** 77 min | **Close reason:** GREEN
> **Peak pips:** 6.5
> **Setup:** S1


---

## 💡 💰 EUR_CHF SELL win: +3.9p / $+49.48 (76min)
**Date:** 2026-04-15T04:15:40
**Type:** discovery
**Tags:** win, eurchf, guardian, S1

> [!tip] DISCOVERY
> **Pair:** EUR_CHF | **Direction:** SELL
> **PnL:** +3.9 pips / $+49.48 | **R:** 0.54
> **Duration:** 76 min | **Close reason:** GREEN
> **Peak pips:** 5.0
> **Setup:** S1


---

## ❌ ❌ NZD_USD SELL loss: -5.5p / $-9.32 (97min)
**Date:** 2026-04-15T04:25:15
**Type:** failure
**Tags:** loss, nzdusd, guardian, S15

> [!danger] FAILURE
> **Pair:** NZD_USD | **Direction:** SELL
> **PnL:** -5.5 pips / $-9.32 | **R:** -1.00
> **Duration:** 97 min | **Close reason:** GREEN
> **Peak pips:** 3.8
> **Setup:** S15


---

## ❌ ❌ EUR_AUD SELL loss: -3.8p / $-27.42 (15min)
**Date:** 2026-04-15T04:30:52
**Type:** failure
**Tags:** loss, euraud, guardian, S5

> [!danger] FAILURE
> **Pair:** EUR_AUD | **Direction:** SELL
> **PnL:** -3.8 pips / $-27.42 | **R:** -0.09
> **Duration:** 15 min | **Close reason:** BLACK
> **Peak pips:** 0.0
> **Setup:** S5


---

## ❌ ❌ EUR_USD BUY loss: -8.8p / $-88.00 (48min)
**Date:** 2026-04-15T05:02:50
**Type:** failure
**Tags:** loss, eurusd, guardian, S15

> [!danger] FAILURE
> **Pair:** EUR_USD | **Direction:** BUY
> **PnL:** -8.8 pips / $-88.00 | **R:** -1.00
> **Duration:** 48 min | **Close reason:** GREEN
> **Peak pips:** 4.3
> **Setup:** S15


---

## 💡 💰 AUD_USD SELL win: +4.2p / $+42.00 (101min)
**Date:** 2026-04-15T05:10:39
**Type:** discovery
**Tags:** win, audusd, guardian, S5

> [!tip] DISCOVERY
> **Pair:** AUD_USD | **Direction:** SELL
> **PnL:** +4.2 pips / $+42.00 | **R:** 0.55
> **Duration:** 101 min | **Close reason:** GREEN
> **Peak pips:** 5.0
> **Setup:** S5


---

## ❌ ❌ GBP_USD BUY loss: -21.2p / $-15.63 (144min)
**Date:** 2026-04-15T05:11:40
**Type:** failure
**Tags:** loss, gbpusd, guardian, S1

> [!danger] FAILURE
> **Pair:** GBP_USD | **Direction:** BUY
> **PnL:** -21.2 pips / $-15.63 | **R:** -1.00
> **Duration:** 144 min | **Close reason:** YELLOW
> **Peak pips:** 0.0
> **Setup:** S1


---

## 💡 💰 AUD_JPY BUY win: +5.0p / $+31.15 (70min)
**Date:** 2026-04-15T05:54:59
**Type:** discovery
**Tags:** win, audjpy, guardian, S5

> [!tip] DISCOVERY
> **Pair:** AUD_JPY | **Direction:** BUY
> **PnL:** +5.0 pips / $+31.15 | **R:** 0.57
> **Duration:** 70 min | **Close reason:** GREEN
> **Peak pips:** 6.3
> **Setup:** S5


---

## 💡 💰 AUD_USD SELL win: +4.5p / $+45.00 (73min)
**Date:** 2026-04-15T06:27:46
**Type:** discovery
**Tags:** win, audusd, guardian, S15

> [!tip] DISCOVERY
> **Pair:** AUD_USD | **Direction:** SELL
> **PnL:** +4.5 pips / $+45.00 | **R:** 0.56
> **Duration:** 73 min | **Close reason:** GREEN
> **Peak pips:** 5.2
> **Setup:** S15


---

## 💡 💰 USD_JPY SELL win: +4.6p / $+28.65 (16min)
**Date:** 2026-04-15T06:45:40
**Type:** discovery
**Tags:** win, usdjpy, guardian, S13

> [!tip] DISCOVERY
> **Pair:** USD_JPY | **Direction:** SELL
> **PnL:** +4.6 pips / $+28.65 | **R:** 0.54
> **Duration:** 16 min | **Close reason:** YELLOW
> **Peak pips:** 5.3
> **Setup:** S13


---

## ❌ ❌ USD_JPY SELL loss: -12.6p / $-79.99 (47min)
**Date:** 2026-04-15T07:47:06
**Type:** failure
**Tags:** loss, usdjpy, guardian, S15

> [!danger] FAILURE
> **Pair:** USD_JPY | **Direction:** SELL
> **PnL:** -12.6 pips / $-79.99 | **R:** -1.03
> **Duration:** 47 min | **Close reason:** GREEN
> **Peak pips:** 3.7
> **Setup:** S15


---

## 💡 💰 AUD_JPY BUY win: +4.5p / $+28.01 (117min)
**Date:** 2026-04-15T07:56:41
**Type:** discovery
**Tags:** win, audjpy, guardian, S15

> [!tip] DISCOVERY
> **Pair:** AUD_JPY | **Direction:** BUY
> **PnL:** +4.5 pips / $+28.01 | **R:** 0.51
> **Duration:** 117 min | **Close reason:** GREEN
> **Peak pips:** 5.4
> **Setup:** S15


---

## ❌ ❌ NZD_USD BUY loss: -5.9p / $-29.50 (17min)
**Date:** 2026-04-15T08:46:56
**Type:** failure
**Tags:** loss, nzdusd, guardian, S15

> [!danger] FAILURE
> **Pair:** NZD_USD | **Direction:** BUY
> **PnL:** -5.9 pips / $-29.50 | **R:** -0.40
> **Duration:** 17 min | **Close reason:** BLACK
> **Peak pips:** 0.0
> **Setup:** S15


---

## 💡 💰 EUR_JPY BUY win: +6.1p / $+18.98 (28min)
**Date:** 2026-04-15T08:57:45
**Type:** discovery
**Tags:** win, eurjpy, guardian, S1

> [!tip] DISCOVERY
> **Pair:** EUR_JPY | **Direction:** BUY
> **PnL:** +6.1 pips / $+18.98 | **R:** 0.69
> **Duration:** 28 min | **Close reason:** YELLOW
> **Peak pips:** 7.3
> **Setup:** S1


---

## 💡 💰 EUR_CHF BUY win: +4.1p / $+51.88 (39min)
**Date:** 2026-04-15T08:58:01
**Type:** discovery
**Tags:** win, eurchf, guardian, unknown

> [!tip] DISCOVERY
> **Pair:** EUR_CHF | **Direction:** BUY
> **PnL:** +4.1 pips / $+51.88 | **R:** 0.62
> **Duration:** 39 min | **Close reason:** GREEN
> **Peak pips:** 5.2
> **Setup:** unknown


---

## ❌ ❌ GBP_USD SELL loss: -8.8p / $-44.00 (15min)
**Date:** 2026-04-15T09:30:07
**Type:** failure
**Tags:** loss, gbpusd, guardian, S15

> [!danger] FAILURE
> **Pair:** GBP_USD | **Direction:** SELL
> **PnL:** -8.8 pips / $-44.00 | **R:** -0.34
> **Duration:** 15 min | **Close reason:** BLACK
> **Peak pips:** 0.0
> **Setup:** S15


---

## 💡 💰 AUD_USD SELL win: +5.1p / $+25.50 (14min)
**Date:** 2026-04-15T09:43:47
**Type:** discovery
**Tags:** win, audusd, guardian, unknown

> [!tip] DISCOVERY
> **Pair:** AUD_USD | **Direction:** SELL
> **PnL:** +5.1 pips / $+25.50 | **R:** 0.75
> **Duration:** 14 min | **Close reason:** BLACK
> **Peak pips:** 6.0
> **Setup:** unknown


---

## 💡 💰 AUD_USD BUY win: +4.4p / $+22.00 (21min)
**Date:** 2026-04-15T10:05:42
**Type:** discovery
**Tags:** win, audusd, guardian, S15

> [!tip] DISCOVERY
> **Pair:** AUD_USD | **Direction:** BUY
> **PnL:** +4.4 pips / $+22.00 | **R:** 0.67
> **Duration:** 21 min | **Close reason:** YELLOW
> **Peak pips:** 5.2
> **Setup:** S15


---

## ❌ ❌ EUR_CHF BUY loss: -13.2p / $-85.32 (65min)
**Date:** 2026-04-15T10:10:15
**Type:** failure
**Tags:** loss, eurchf, guardian, S15

> [!danger] FAILURE
> **Pair:** EUR_CHF | **Direction:** BUY
> **PnL:** -13.2 pips / $-85.32 | **R:** -1.01
> **Duration:** 65 min | **Close reason:** YELLOW
> **Peak pips:** 0.0
> **Setup:** S15


---

## 💡 💰 AUD_JPY SELL win: +2.9p / $+9.03 (10min)
**Date:** 2026-04-15T10:40:12
**Type:** discovery
**Tags:** win, audjpy, guardian, S1

> [!tip] DISCOVERY
> **Pair:** AUD_JPY | **Direction:** SELL
> **PnL:** +2.9 pips / $+9.03 | **R:** 1.00
> **Duration:** 10 min | **Close reason:** BLACK
> **Peak pips:** 5.3
> **Setup:** S1


---

## ❌ ❌ EUR_GBP SELL loss: -1.1p / $-7.54 (10min)
**Date:** 2026-04-15T11:09:40
**Type:** failure
**Tags:** loss, eurgbp, guardian, unknown

> [!danger] FAILURE
> **Pair:** EUR_GBP | **Direction:** SELL
> **PnL:** -1.1 pips / $-7.54 | **R:** -0.12
> **Duration:** 10 min | **Close reason:** BLACK
> **Peak pips:** 0.3
> **Setup:** unknown


---

## 💡 💰 EUR_USD BUY win: +4.0p / $+20.00 (104min)
**Date:** 2026-04-15T11:13:41
**Type:** discovery
**Tags:** win, eurusd, guardian, S15

> [!tip] DISCOVERY
> **Pair:** EUR_USD | **Direction:** BUY
> **PnL:** +4.0 pips / $+20.00 | **R:** 0.57
> **Duration:** 104 min | **Close reason:** YELLOW
> **Peak pips:** 5.2
> **Setup:** S15


---

## 💡 💰 EUR_JPY BUY win: +3.6p / $+11.21 (131min)
**Date:** 2026-04-15T11:15:58
**Type:** discovery
**Tags:** win, eurjpy, guardian, unknown

> [!tip] DISCOVERY
> **Pair:** EUR_JPY | **Direction:** BUY
> **PnL:** +3.6 pips / $+11.21 | **R:** 0.46
> **Duration:** 131 min | **Close reason:** YELLOW
> **Peak pips:** 5.0
> **Setup:** unknown


---

## ❌ ❌ AUD_JPY SELL loss: -2.7p / $-8.58 (20min)
**Date:** 2026-04-15T11:49:47
**Type:** failure
**Tags:** loss, audjpy, guardian, S1

> [!danger] FAILURE
> **Pair:** AUD_JPY | **Direction:** SELL
> **PnL:** -2.7 pips / $-8.58 | **R:** -0.13
> **Duration:** 20 min | **Close reason:** BLACK
> **Peak pips:** 1.6
> **Setup:** S1


---

## 💡 💰 EUR_AUD SELL win: +3.4p / $+12.05 (105min)
**Date:** 2026-04-15T12:06:10
**Type:** discovery
**Tags:** win, euraud, guardian, S5

> [!tip] DISCOVERY
> **Pair:** EUR_AUD | **Direction:** SELL
> **PnL:** +3.4 pips / $+12.05 | **R:** 0.89
> **Duration:** 105 min | **Close reason:** YELLOW
> **Peak pips:** 5.4
> **Setup:** S5


---

## 💡 💰 USD_JPY SELL win: +4.2p / $+13.08 (14min)
**Date:** 2026-04-15T12:13:43
**Type:** discovery
**Tags:** win, usdjpy, guardian, unknown

> [!tip] DISCOVERY
> **Pair:** USD_JPY | **Direction:** SELL
> **PnL:** +4.2 pips / $+13.08 | **R:** 0.58
> **Duration:** 14 min | **Close reason:** BLACK
> **Peak pips:** 5.3
> **Setup:** unknown


---

## ❌ ❌ EUR_JPY BUY loss: -25.5p / $-81.11 (3min)
**Date:** 2026-04-15T12:23:29
**Type:** failure
**Tags:** loss, eurjpy, guardian, S1

> [!danger] FAILURE
> **Pair:** EUR_JPY | **Direction:** BUY
> **PnL:** -25.5 pips / $-81.11 | **R:** -1.00
> **Duration:** 3 min | **Close reason:** black
> **Peak pips:** 0.0
> **Setup:** S1


---

## 💡 💰 USD_JPY SELL win: +7.7p / $+23.99 (5min)
**Date:** 2026-04-15T12:25:15
**Type:** discovery
**Tags:** win, usdjpy, guardian, S15

> [!tip] DISCOVERY
> **Pair:** USD_JPY | **Direction:** SELL
> **PnL:** +7.7 pips / $+23.99 | **R:** 0.96
> **Duration:** 5 min | **Close reason:** black
> **Peak pips:** 14.5
> **Setup:** S15


---

## 💡 💰 EUR_USD SELL win: +1.5p / $+7.50 (3min)
**Date:** 2026-04-15T12:30:57
**Type:** discovery
**Tags:** win, eurusd, guardian, unknown

> [!tip] DISCOVERY
> **Pair:** EUR_USD | **Direction:** SELL
> **PnL:** +1.5 pips / $+7.50 | **R:** 0.07
> **Duration:** 3 min | **Close reason:** BLACK
> **Peak pips:** 2.2
> **Setup:** unknown


---

## 💡 💰 USD_CAD SELL win: +1.6p / $+5.77 (37min)
**Date:** 2026-04-15T13:09:10
**Type:** discovery
**Tags:** win, usdcad, guardian, S5

> [!tip] DISCOVERY
> **Pair:** USD_CAD | **Direction:** SELL
> **PnL:** +1.6 pips / $+5.77 | **R:** 0.57
> **Duration:** 37 min | **Close reason:** GREEN
> **Peak pips:** 4.4
> **Setup:** S5


---

## ❌ ❌ USD_JPY SELL loss: -31.3p / $-99.35 (78min)
**Date:** 2026-04-15T13:49:58
**Type:** failure
**Tags:** loss, usdjpy, guardian, S15

> [!danger] FAILURE
> **Pair:** USD_JPY | **Direction:** SELL
> **PnL:** -31.3 pips / $-99.35 | **R:** -1.00
> **Duration:** 78 min | **Close reason:** RED
> **Peak pips:** 0.0
> **Setup:** S15


---

## 💡 💰 EUR_AUD SELL win: +2.9p / $+10.29 (85min)
**Date:** 2026-04-15T13:57:01
**Type:** discovery
**Tags:** win, euraud, guardian, S5

> [!tip] DISCOVERY
> **Pair:** EUR_AUD | **Direction:** SELL
> **PnL:** +2.9 pips / $+10.29 | **R:** 0.55
> **Duration:** 85 min | **Close reason:** YELLOW
> **Peak pips:** 4.7
> **Setup:** S5


---

## ❌ ❌ EUR_GBP SELL loss: -7.3p / $-49.99 (4min)
**Date:** 2026-04-15T17:34:36
**Type:** failure
**Tags:** loss, eurgbp, guardian, S15

> [!danger] FAILURE
> **Pair:** EUR_GBP | **Direction:** SELL
> **PnL:** -7.3 pips / $-49.99 | **R:** -1.00
> **Duration:** 4 min | **Close reason:** RED
> **Peak pips:** 0.0
> **Setup:** S15


---

## 💡 💰 EUR_JPY SELL win: +3.7p / $+11.53 (71min)
**Date:** 2026-04-15T18:56:09
**Type:** discovery
**Tags:** win, eurjpy, guardian, S15

> [!tip] DISCOVERY
> **Pair:** EUR_JPY | **Direction:** SELL
> **PnL:** +3.7 pips / $+11.53 | **R:** 0.57
> **Duration:** 71 min | **Close reason:** GREEN
> **Peak pips:** 5.1
> **Setup:** S15


---

## ❌ ❌ GBP_USD SELL loss: -7.5p / $-37.50 (97min)
**Date:** 2026-04-15T19:17:41
**Type:** failure
**Tags:** loss, gbpusd, guardian, S15

> [!danger] FAILURE
> **Pair:** GBP_USD | **Direction:** SELL
> **PnL:** -7.5 pips / $-37.50 | **R:** -1.04
> **Duration:** 97 min | **Close reason:** YELLOW
> **Peak pips:** 4.7
> **Setup:** S15


---

## 💡 💰 NZD_USD SELL win: +3.7p / $+18.50 (65min)
**Date:** 2026-04-15T20:04:49
**Type:** discovery
**Tags:** win, nzdusd, guardian, S15

> [!tip] DISCOVERY
> **Pair:** NZD_USD | **Direction:** SELL
> **PnL:** +3.7 pips / $+18.50 | **R:** 0.60
> **Duration:** 65 min | **Close reason:** GREEN
> **Peak pips:** 5.1
> **Setup:** S15


---

## 💡 💰 EUR_JPY SELL win: +4.7p / $+14.65 (39min)
**Date:** 2026-04-15T20:08:52
**Type:** discovery
**Tags:** win, eurjpy, guardian, S1

> [!tip] DISCOVERY
> **Pair:** EUR_JPY | **Direction:** SELL
> **PnL:** +4.7 pips / $+14.65 | **R:** 0.63
> **Duration:** 39 min | **Close reason:** GREEN
> **Peak pips:** 6.1
> **Setup:** S1


---

## ❌ ❌ AUD_USD BUY loss: -8.6p / $-43.00 (155min)
**Date:** 2026-04-15T21:35:24
**Type:** failure
**Tags:** loss, audusd, guardian, S1

> [!danger] FAILURE
> **Pair:** AUD_USD | **Direction:** BUY
> **PnL:** -8.6 pips / $-43.00 | **R:** -1.00
> **Duration:** 155 min | **Close reason:** RED
> **Peak pips:** 3.9
> **Setup:** S1


---

## 💡 💰 EUR_USD SELL win: +1.2p / $+6.00 (219min)
**Date:** 2026-04-15T21:38:57
**Type:** discovery
**Tags:** win, eurusd, guardian, S15

> [!tip] DISCOVERY
> **Pair:** EUR_USD | **Direction:** SELL
> **PnL:** +1.2 pips / $+6.00 | **R:** 0.40
> **Duration:** 219 min | **Close reason:** GREEN
> **Peak pips:** 2.9
> **Setup:** S15


---

## 💡 💰 EUR_AUD SELL win: +3.9p / $+13.87 (5min)
**Date:** 2026-04-15T22:32:06
**Type:** discovery
**Tags:** win, euraud, guardian, S1

> [!tip] DISCOVERY
> **Pair:** EUR_AUD | **Direction:** SELL
> **PnL:** +3.9 pips / $+13.87 | **R:** 0.95
> **Duration:** 5 min | **Close reason:** GREEN
> **Peak pips:** 5.9
> **Setup:** S1


---

## 💡 💰 AUD_JPY BUY win: +5.2p / $+16.22 (303min)
**Date:** 2026-04-15T22:43:12
**Type:** discovery
**Tags:** win, audjpy, guardian, S1

> [!tip] DISCOVERY
> **Pair:** AUD_JPY | **Direction:** BUY
> **PnL:** +5.2 pips / $+16.22 | **R:** 0.44
> **Duration:** 303 min | **Close reason:** GREEN
> **Peak pips:** 7.0
> **Setup:** S1


---

## 💡 💰 USD_CHF SELL win: +5.5p / $+34.88 (116min)
**Date:** 2026-04-15T22:43:42
**Type:** discovery
**Tags:** win, usdchf, guardian, S1

> [!tip] DISCOVERY
> **Pair:** USD_CHF | **Direction:** SELL
> **PnL:** +5.5 pips / $+34.88 | **R:** 0.64
> **Duration:** 116 min | **Close reason:** YELLOW
> **Peak pips:** 6.5
> **Setup:** S1


---

## 💡 💰 USD_JPY SELL win: +4.6p / $+14.35 (106min)
**Date:** 2026-04-15T22:50:16
**Type:** discovery
**Tags:** win, usdjpy, guardian, S1

> [!tip] DISCOVERY
> **Pair:** USD_JPY | **Direction:** SELL
> **PnL:** +4.6 pips / $+14.35 | **R:** 0.52
> **Duration:** 106 min | **Close reason:** YELLOW
> **Peak pips:** 5.3
> **Setup:** S1


---

## 💡 💰 EUR_AUD SELL win: +4.8p / $+17.09 (58min)
**Date:** 2026-04-15T23:47:14
**Type:** discovery
**Tags:** win, euraud, guardian, S5

> [!tip] DISCOVERY
> **Pair:** EUR_AUD | **Direction:** SELL
> **PnL:** +4.8 pips / $+17.09 | **R:** 1.00
> **Duration:** 58 min | **Close reason:** YELLOW
> **Peak pips:** 6.8
> **Setup:** S5


---

## ❌ ❌ EUR_AUD SELL loss: -9.6p / $-34.84 (70min)
**Date:** 2026-04-16T01:14:24
**Type:** failure
**Tags:** loss, euraud, guardian, S5

> [!danger] FAILURE
> **Pair:** EUR_AUD | **Direction:** SELL
> **PnL:** -9.6 pips / $-34.84 | **R:** -1.00
> **Duration:** 70 min | **Close reason:** RED
> **Peak pips:** 4.9
> **Setup:** S5


---

## ❌ ❌ USD_JPY SELL loss: -38.4p / $-122.02 (174min)
**Date:** 2026-04-16T02:30:36
**Type:** failure
**Tags:** loss, usdjpy, guardian, S15

> [!danger] FAILURE
> **Pair:** USD_JPY | **Direction:** SELL
> **PnL:** -38.4 pips / $-122.02 | **R:** -1.00
> **Duration:** 174 min | **Close reason:** BLACK
> **Peak pips:** 0.0
> **Setup:** S15


---

## ❌ ❌ USD_CHF SELL loss: -14.8p / $-95.63 (194min)
**Date:** 2026-04-16T02:31:53
**Type:** failure
**Tags:** loss, usdchf, guardian, S15

> [!danger] FAILURE
> **Pair:** USD_CHF | **Direction:** SELL
> **PnL:** -14.8 pips / $-95.63 | **R:** -1.01
> **Duration:** 194 min | **Close reason:** BLACK
> **Peak pips:** 0.1
> **Setup:** S15


---

## ❌ ❌ GBP_USD SELL loss: -7.9p / $-39.50 (7min)
**Date:** 2026-04-16T07:06:39
**Type:** failure
**Tags:** loss, gbpusd, guardian, S5

> [!danger] FAILURE
> **Pair:** GBP_USD | **Direction:** SELL
> **PnL:** -7.9 pips / $-39.50 | **R:** -0.35
> **Duration:** 7 min | **Close reason:** BLACK
> **Peak pips:** 0.0
> **Setup:** S5


---

## 💡 💰 AUD_USD BUY win: +4.7p / $+23.50 (58min)
**Date:** 2026-04-16T07:57:31
**Type:** discovery
**Tags:** win, audusd, guardian, S15

> [!tip] DISCOVERY
> **Pair:** AUD_USD | **Direction:** BUY
> **PnL:** +4.7 pips / $+23.50 | **R:** 0.77
> **Duration:** 58 min | **Close reason:** GREEN
> **Peak pips:** 5.4
> **Setup:** S15


---

## ❌ ❌ NZD_USD SELL loss: -0.3p / $-1.50 (3min)
**Date:** 2026-04-16T08:44:46
**Type:** failure
**Tags:** loss, nzdusd, guardian, S5

> [!danger] FAILURE
> **Pair:** NZD_USD | **Direction:** SELL
> **PnL:** -0.3 pips / $-1.50 | **R:** -0.03
> **Duration:** 3 min | **Close reason:** GREEN
> **Peak pips:** 3.0
> **Setup:** S5


---

## ❌ ❌ EUR_JPY SELL loss: -18.0p / $-57.14 (3min)
**Date:** 2026-04-16T08:45:18
**Type:** failure
**Tags:** loss, eurjpy, guardian, S1

> [!danger] FAILURE
> **Pair:** EUR_JPY | **Direction:** SELL
> **PnL:** -18.0 pips / $-57.14 | **R:** -1.01
> **Duration:** 3 min | **Close reason:** RED
> **Peak pips:** 0.0
> **Setup:** S1


---

## 💡 💰 EUR_CHF SELL win: +0.6p / $+3.79 (4min)
**Date:** 2026-04-16T08:45:33
**Type:** discovery
**Tags:** win, eurchf, guardian, unknown

> [!tip] DISCOVERY
> **Pair:** EUR_CHF | **Direction:** SELL
> **PnL:** +0.6 pips / $+3.79 | **R:** 0.08
> **Duration:** 4 min | **Close reason:** YELLOW
> **Peak pips:** 2.6
> **Setup:** unknown


---

## ❌ ❌ AUD_JPY BUY loss: -0.7p / $-2.22 (22min)
**Date:** 2026-04-16T09:07:13
**Type:** failure
**Tags:** loss, audjpy, guardian, S1

> [!danger] FAILURE
> **Pair:** AUD_JPY | **Direction:** BUY
> **PnL:** -0.7 pips / $-2.22 | **R:** -0.06
> **Duration:** 22 min | **Close reason:** GREEN
> **Peak pips:** 3.4
> **Setup:** S1


---

## 💡 💰 AUD_USD BUY win: +0.2p / $+1.00 (58min)
**Date:** 2026-04-16T09:39:44
**Type:** discovery
**Tags:** win, audusd, guardian, S15

> [!tip] DISCOVERY
> **Pair:** AUD_USD | **Direction:** BUY
> **PnL:** +0.2 pips / $+1.00 | **R:** 0.02
> **Duration:** 58 min | **Close reason:** GREEN
> **Peak pips:** 1.8
> **Setup:** S15


---

## ❌ ❌ EUR_USD BUY loss: -15.0p / $-75.00 (67min)
**Date:** 2026-04-16T09:52:40
**Type:** failure
**Tags:** loss, eurusd, guardian, S1

> [!danger] FAILURE
> **Pair:** EUR_USD | **Direction:** BUY
> **PnL:** -15.0 pips / $-75.00 | **R:** -1.00
> **Duration:** 67 min | **Close reason:** RED
> **Peak pips:** 0.0
> **Setup:** S1


---

## ❌ ❌ AUD_USD BUY loss: -10.9p / $-54.50 (11min)
**Date:** 2026-04-16T09:55:48
**Type:** failure
**Tags:** loss, audusd, guardian, S15

> [!danger] FAILURE
> **Pair:** AUD_USD | **Direction:** BUY
> **PnL:** -10.9 pips / $-54.50 | **R:** -1.01
> **Duration:** 11 min | **Close reason:** RED
> **Peak pips:** 0.8
> **Setup:** S15


---

## ❌ ❌ USD_JPY SELL loss: -3.1p / $-9.83 (1min)
**Date:** 2026-04-16T10:00:51
**Type:** failure
**Tags:** loss, usdjpy, guardian, S1

> [!danger] FAILURE
> **Pair:** USD_JPY | **Direction:** SELL
> **PnL:** -3.1 pips / $-9.83 | **R:** -0.16
> **Duration:** 1 min | **Close reason:** BLACK
> **Peak pips:** 0.0
> **Setup:** S1


---

## 💡 💰 EUR_CHF BUY win: +0.1p / $+0.63 (5min)
**Date:** 2026-04-16T10:04:38
**Type:** discovery
**Tags:** win, eurchf, guardian, S13

> [!tip] DISCOVERY
> **Pair:** EUR_CHF | **Direction:** BUY
> **PnL:** +0.1 pips / $+0.63 | **R:** 0.01
> **Duration:** 5 min | **Close reason:** YELLOW
> **Peak pips:** 3.4
> **Setup:** S13


---

## 💡 💰 EUR_GBP BUY win: +7.9p / $+52.90 (5min)
**Date:** 2026-04-16T10:22:11
**Type:** discovery
**Tags:** win, eurgbp, guardian, S1

> [!tip] DISCOVERY
> **Pair:** EUR_GBP | **Direction:** BUY
> **PnL:** +7.9 pips / $+52.90 | **R:** 0.99
> **Duration:** 5 min | **Close reason:** GREEN
> **Peak pips:** 8.6
> **Setup:** S1


---

## 💡 💰 EUR_CHF BUY win: +0.5p / $+3.16 (11min)
**Date:** 2026-04-16T10:50:38
**Type:** discovery
**Tags:** win, eurchf, guardian, unknown

> [!tip] DISCOVERY
> **Pair:** EUR_CHF | **Direction:** BUY
> **PnL:** +0.5 pips / $+3.16 | **R:** 0.05
> **Duration:** 11 min | **Close reason:** GREEN
> **Peak pips:** 2.0
> **Setup:** unknown


---

## 💡 💰 GBP_USD SELL win: +4.8p / $+24.00 (6min)
**Date:** 2026-04-16T11:21:15
**Type:** discovery
**Tags:** win, gbpusd, guardian, S5

> [!tip] DISCOVERY
> **Pair:** GBP_USD | **Direction:** SELL
> **PnL:** +4.8 pips / $+24.00 | **R:** 0.80
> **Duration:** 6 min | **Close reason:** YELLOW
> **Peak pips:** 5.7
> **Setup:** S5


---

## 💡 💰 GBP_USD BUY win: +0.5p / $+2.50 (15min)
**Date:** 2026-04-16T12:01:58
**Type:** discovery
**Tags:** win, gbpusd, guardian, S5

> [!tip] DISCOVERY
> **Pair:** GBP_USD | **Direction:** BUY
> **PnL:** +0.5 pips / $+2.50 | **R:** 0.03
> **Duration:** 15 min | **Close reason:** GREEN
> **Peak pips:** 3.0
> **Setup:** S5


---

## ❌ ❌ EUR_CHF SELL loss: -0.5p / $-3.22 (17min)
**Date:** 2026-04-16T12:03:59
**Type:** failure
**Tags:** loss, eurchf, guardian, S13

> [!danger] FAILURE
> **Pair:** EUR_CHF | **Direction:** SELL
> **PnL:** -0.5 pips / $-3.22 | **R:** -0.06
> **Duration:** 17 min | **Close reason:** GREEN
> **Peak pips:** 1.4
> **Setup:** S13


---

## 💡 💰 EUR_GBP SELL win: +0.2p / $+1.34 (13min)
**Date:** 2026-04-16T12:37:00
**Type:** discovery
**Tags:** win, eurgbp, guardian, unknown

> [!tip] DISCOVERY
> **Pair:** EUR_GBP | **Direction:** SELL
> **PnL:** +0.2 pips / $+1.34 | **R:** 0.03
> **Duration:** 13 min | **Close reason:** GREEN
> **Peak pips:** 1.5
> **Setup:** unknown


---

## ❌ ❌ GBP_USD BUY loss: -17.0p / $-85.00 (24min)
**Date:** 2026-04-16T12:54:37
**Type:** failure
**Tags:** loss, gbpusd, guardian, S5

> [!danger] FAILURE
> **Pair:** GBP_USD | **Direction:** BUY
> **PnL:** -17.0 pips / $-85.00 | **R:** -1.01
> **Duration:** 24 min | **Close reason:** RED
> **Peak pips:** 0.0
> **Setup:** S5


---

## ❌ ❌ NZD_USD BUY loss: -5.4p / $-27.00 (13min)
**Date:** 2026-04-16T13:15:04
**Type:** failure
**Tags:** loss, nzdusd, guardian, S1

> [!danger] FAILURE
> **Pair:** NZD_USD | **Direction:** BUY
> **PnL:** -5.4 pips / $-27.00 | **R:** -0.60
> **Duration:** 13 min | **Close reason:** BLACK
> **Peak pips:** 0.0
> **Setup:** S1


---

## 💡 💰 AUD_USD BUY win: +0.4p / $+2.00 (4min)
**Date:** 2026-04-16T15:23:26
**Type:** discovery
**Tags:** win, audusd, guardian, S5

> [!tip] DISCOVERY
> **Pair:** AUD_USD | **Direction:** BUY
> **PnL:** +0.4 pips / $+2.00 | **R:** 0.04
> **Duration:** 4 min | **Close reason:** GREEN
> **Peak pips:** 1.4
> **Setup:** S5


---

## 💡 💰 AUD_USD SELL win: +0.3p / $+1.50 (12min)
**Date:** 2026-04-16T15:55:45
**Type:** discovery
**Tags:** win, audusd, guardian, S5

> [!tip] DISCOVERY
> **Pair:** AUD_USD | **Direction:** SELL
> **PnL:** +0.3 pips / $+1.50 | **R:** 0.04
> **Duration:** 12 min | **Close reason:** YELLOW
> **Peak pips:** 1.3
> **Setup:** S5


---

## 💡 💰 AUD_USD SELL win: +0.2p / $+1.00 (13min)
**Date:** 2026-04-16T16:26:45
**Type:** discovery
**Tags:** win, audusd, guardian, S5

> [!tip] DISCOVERY
> **Pair:** AUD_USD | **Direction:** SELL
> **PnL:** +0.2 pips / $+1.00 | **R:** 0.02
> **Duration:** 13 min | **Close reason:** GREEN
> **Peak pips:** 1.2
> **Setup:** S5


---

## ❌ ❌ EUR_GBP SELL loss: -8.1p / $-55.32 (67min)
**Date:** 2026-04-16T16:27:16
**Type:** failure
**Tags:** loss, eurgbp, guardian, S1

> [!danger] FAILURE
> **Pair:** EUR_GBP | **Direction:** SELL
> **PnL:** -8.1 pips / $-55.32 | **R:** -1.00
> **Duration:** 67 min | **Close reason:** YELLOW
> **Peak pips:** 0.0
> **Setup:** S1


---

## ❌ ❌ AUD_USD SELL loss: -2.4p / $-18.00 (36min)
**Date:** 2026-04-16T17:05:06
**Type:** failure
**Tags:** loss, audusd, guardian, S5

> [!danger] FAILURE
> **Pair:** AUD_USD | **Direction:** SELL
> **PnL:** -2.4 pips / $-18.00 | **R:** -0.27
> **Duration:** 36 min | **Close reason:** YELLOW
> **Peak pips:** 0.0
> **Setup:** S5


---

## ❌ ❌ AUD_JPY SELL loss: -4.0p / $-20.31 (105min)
**Date:** 2026-04-16T17:05:08
**Type:** failure
**Tags:** loss, audjpy, guardian, S15

> [!danger] FAILURE
> **Pair:** AUD_JPY | **Direction:** SELL
> **PnL:** -4.0 pips / $-20.31 | **R:** -0.27
> **Duration:** 105 min | **Close reason:** YELLOW
> **Peak pips:** 0.0
> **Setup:** S15


---

## ❌ ❌ EUR_AUD BUY loss: -7.9p / $+0.00 (107min)
**Date:** 2026-04-16T17:06:40
**Type:** failure
**Tags:** loss, euraud, guardian, unknown

> [!danger] FAILURE
> **Pair:** EUR_AUD | **Direction:** BUY
> **PnL:** -7.9 pips / $+0.00 | **R:** -0.25
> **Duration:** 107 min | **Close reason:** YELLOW
> **Peak pips:** 0.0
> **Setup:** unknown


---

## ❌ ❌ USD_JPY BUY loss: -16.8p / $-53.34 (21min)
**Date:** 2026-04-16T18:05:32
**Type:** failure
**Tags:** loss, usdjpy, guardian, S1

> [!danger] FAILURE
> **Pair:** USD_JPY | **Direction:** BUY
> **PnL:** -16.8 pips / $-53.34 | **R:** -1.00
> **Duration:** 21 min | **Close reason:** RED
> **Peak pips:** 0.0
> **Setup:** S1


---

## ❌ ❌ EUR_USD SELL loss: -11.3p / $-56.50 (35min)
**Date:** 2026-04-16T18:06:03
**Type:** failure
**Tags:** loss, eurusd, guardian, S15

> [!danger] FAILURE
> **Pair:** EUR_USD | **Direction:** SELL
> **PnL:** -11.3 pips / $-56.50 | **R:** -1.00
> **Duration:** 35 min | **Close reason:** RED
> **Peak pips:** 0.0
> **Setup:** S15


---

## ❌ ❌ GBP_USD SELL loss: -0.3p / $-1.50 (33min)
**Date:** 2026-04-16T19:01:50
**Type:** failure
**Tags:** loss, gbpusd, guardian, unknown

> [!danger] FAILURE
> **Pair:** GBP_USD | **Direction:** SELL
> **PnL:** -0.3 pips / $-1.50 | **R:** -0.03
> **Duration:** 33 min | **Close reason:** YELLOW
> **Peak pips:** 1.2
> **Setup:** unknown


---

## ❌ ❌ EUR_CHF BUY loss: -5.3p / $-34.18 (50min)
**Date:** 2026-04-16T19:19:33
**Type:** failure
**Tags:** loss, eurchf, guardian, S15

> [!danger] FAILURE
> **Pair:** EUR_CHF | **Direction:** BUY
> **PnL:** -5.3 pips / $-34.18 | **R:** -1.02
> **Duration:** 50 min | **Close reason:** YELLOW
> **Peak pips:** 0.0
> **Setup:** S15


---

## 💡 💰 NZD_USD SELL win: +2.3p / $+11.50 (84min)
**Date:** 2026-04-16T19:52:51
**Type:** discovery
**Tags:** win, nzdusd, guardian, S1

> [!tip] DISCOVERY
> **Pair:** NZD_USD | **Direction:** SELL
> **PnL:** +2.3 pips / $+11.50 | **R:** 0.62
> **Duration:** 84 min | **Close reason:** GREEN
> **Peak pips:** 3.7
> **Setup:** S1


---

## ❌ ❌ NZD_USD SELL loss: -0.7p / $-3.50 (12min)
**Date:** 2026-04-16T20:55:56
**Type:** failure
**Tags:** loss, nzdusd, guardian, unknown

> [!danger] FAILURE
> **Pair:** NZD_USD | **Direction:** SELL
> **PnL:** -0.7 pips / $-3.50 | **R:** -0.17
> **Duration:** 12 min | **Close reason:** YELLOW
> **Peak pips:** 1.0
> **Setup:** unknown


---

## ❌ ❌ GBP_USD SELL loss: -0.2p / $-1.00 (20min)
**Date:** 2026-04-16T23:35:18
**Type:** failure
**Tags:** loss, gbpusd, guardian, S5

> [!danger] FAILURE
> **Pair:** GBP_USD | **Direction:** SELL
> **PnL:** -0.2 pips / $-1.00 | **R:** -0.02
> **Duration:** 20 min | **Close reason:** GREEN
> **Peak pips:** 1.2
> **Setup:** S5


---

## ❌ ❌ EUR_USD SELL loss: -7.2p / $-36.00 (73min)
**Date:** 2026-04-16T23:42:52
**Type:** failure
**Tags:** loss, eurusd, guardian, unknown

> [!danger] FAILURE
> **Pair:** EUR_USD | **Direction:** SELL
> **PnL:** -7.2 pips / $-36.00 | **R:** -1.00
> **Duration:** 73 min | **Close reason:** RED
> **Peak pips:** 0.0
> **Setup:** unknown


---

## 💡 💰 USD_JPY BUY win: +1.9p / $+5.90 (146min)
**Date:** 2026-04-17T00:55:55
**Type:** discovery
**Tags:** win, usdjpy, guardian, S5

> [!tip] DISCOVERY
> **Pair:** USD_JPY | **Direction:** BUY
> **PnL:** +1.9 pips / $+5.90 | **R:** 0.11
> **Duration:** 146 min | **Close reason:** GREEN
> **Peak pips:** 2.3
> **Setup:** S5


---

## ❌ ❌ AUD_USD SELL loss: -0.1p / $-0.50 (35min)
**Date:** 2026-04-17T01:04:45
**Type:** failure
**Tags:** loss, audusd, guardian, S13

> [!danger] FAILURE
> **Pair:** AUD_USD | **Direction:** SELL
> **PnL:** -0.1 pips / $-0.50 | **R:** -0.03
> **Duration:** 35 min | **Close reason:** YELLOW
> **Peak pips:** 1.0
> **Setup:** S13


---

## ❌ ❌ EUR_CHF BUY loss: -0.7p / $-4.51 (9min)
**Date:** 2026-04-17T01:23:55
**Type:** failure
**Tags:** loss, eurchf, guardian, S15

> [!danger] FAILURE
> **Pair:** EUR_CHF | **Direction:** BUY
> **PnL:** -0.7 pips / $-4.51 | **R:** -0.19
> **Duration:** 9 min | **Close reason:** GREEN
> **Peak pips:** 0.8
> **Setup:** S15


---

## ❌ ❌ NZD_USD SELL loss: -4.2p / $-21.00 (24min)
**Date:** 2026-04-17T01:24:26
**Type:** failure
**Tags:** loss, nzdusd, guardian, S15

> [!danger] FAILURE
> **Pair:** NZD_USD | **Direction:** SELL
> **PnL:** -4.2 pips / $-21.00 | **R:** -1.00
> **Duration:** 24 min | **Close reason:** YELLOW
> **Peak pips:** 0.5
> **Setup:** S15


---

## 💡 💰 AUD_JPY BUY win: +3.9p / $+12.11 (15min)
**Date:** 2026-04-17T03:31:01
**Type:** discovery
**Tags:** win, audjpy, guardian, S5

> [!tip] DISCOVERY
> **Pair:** AUD_JPY | **Direction:** BUY
> **PnL:** +3.9 pips / $+12.11 | **R:** 0.75
> **Duration:** 15 min | **Close reason:** YELLOW
> **Peak pips:** 5.1
> **Setup:** S5


---

## ❌ ❌ USD_JPY BUY loss: -9.3p / $-29.49 (14min)
**Date:** 2026-04-17T03:59:51
**Type:** failure
**Tags:** loss, usdjpy, guardian, S1

> [!danger] FAILURE
> **Pair:** USD_JPY | **Direction:** BUY
> **PnL:** -9.3 pips / $-29.49 | **R:** -1.02
> **Duration:** 14 min | **Close reason:** RED
> **Peak pips:** 1.8
> **Setup:** S1


---

## ❌ ❌ EUR_JPY BUY loss: -1.0p / $-3.17 (8min)
**Date:** 2026-04-17T04:22:31
**Type:** failure
**Tags:** loss, eurjpy, guardian, S1

> [!danger] FAILURE
> **Pair:** EUR_JPY | **Direction:** BUY
> **PnL:** -1.0 pips / $-3.17 | **R:** -0.31
> **Duration:** 8 min | **Close reason:** YELLOW
> **Peak pips:** 3.4
> **Setup:** S1


---

## ❌ ❌ AUD_JPY BUY loss: +0.0p / $+0.00 (17min)
**Date:** 2026-04-17T04:46:58
**Type:** failure
**Tags:** loss, audjpy, guardian, S5

> [!danger] FAILURE
> **Pair:** AUD_JPY | **Direction:** BUY
> **PnL:** +0.0 pips / $+0.00 | **R:** 0.00
> **Duration:** 17 min | **Close reason:** GREEN
> **Peak pips:** 3.2
> **Setup:** S5


---

## ❌ ❌ EUR_AUD SELL loss: -9.2p / $-33.34 (79min)
**Date:** 2026-04-17T05:22:43
**Type:** failure
**Tags:** loss, euraud, guardian, unknown

> [!danger] FAILURE
> **Pair:** EUR_AUD | **Direction:** SELL
> **PnL:** -9.2 pips / $-33.34 | **R:** -1.00
> **Duration:** 79 min | **Close reason:** RED
> **Peak pips:** 4.5
> **Setup:** unknown


---

## ❌ ❌ USD_CHF SELL loss: -1.7p / $-10.98 (3min)
**Date:** 2026-04-17T06:09:33
**Type:** failure
**Tags:** loss, usdchf, guardian, S15

> [!danger] FAILURE
> **Pair:** USD_CHF | **Direction:** SELL
> **PnL:** -1.7 pips / $-10.98 | **R:** -0.13
> **Duration:** 3 min | **Close reason:** GREEN
> **Peak pips:** 0.0
> **Setup:** S15


---

## ❌ ❌ EUR_USD BUY loss: -6.2p / $-31.00 (3min)
**Date:** 2026-04-17T06:09:49
**Type:** failure
**Tags:** loss, eurusd, guardian, S15

> [!danger] FAILURE
> **Pair:** EUR_USD | **Direction:** BUY
> **PnL:** -6.2 pips / $-31.00 | **R:** -0.41
> **Duration:** 3 min | **Close reason:** YELLOW
> **Peak pips:** 0.0
> **Setup:** S15


---

## ❌ ❌ AUD_USD BUY loss: -4.5p / $-22.50 (4min)
**Date:** 2026-04-17T06:10:19
**Type:** failure
**Tags:** loss, audusd, guardian, unknown

> [!danger] FAILURE
> **Pair:** AUD_USD | **Direction:** BUY
> **PnL:** -4.5 pips / $-22.50 | **R:** -0.45
> **Duration:** 4 min | **Close reason:** YELLOW
> **Peak pips:** 0.0
> **Setup:** unknown


---

## ❌ ❌ USD_CHF BUY loss: -2.0p / $-12.91 (5min)
**Date:** 2026-04-17T06:47:31
**Type:** failure
**Tags:** loss, usdchf, guardian, S13

> [!danger] FAILURE
> **Pair:** USD_CHF | **Direction:** BUY
> **PnL:** -2.0 pips / $-12.91 | **R:** -0.16
> **Duration:** 5 min | **Close reason:** GREEN
> **Peak pips:** 0.0
> **Setup:** S13


---

## 💡 💰 USD_CHF SELL win: +5.6p / $+5.97 (6min)
**Date:** 2026-04-17T09:00:06
**Type:** discovery
**Tags:** win, usdchf, guardian, S1

> [!tip] DISCOVERY
> **Pair:** USD_CHF | **Direction:** SELL
> **PnL:** +5.6 pips / $+5.97 | **R:** 0.49
> **Duration:** 6 min | **Close reason:** GREEN
> **Peak pips:** 5.6
> **Setup:** S1


---

## 💡 💰 EUR_AUD SELL win: +5.3p / $+3.79 (20min)
**Date:** 2026-04-17T09:53:08
**Type:** discovery
**Tags:** win, euraud, guardian, S15

> [!tip] DISCOVERY
> **Pair:** EUR_AUD | **Direction:** SELL
> **PnL:** +5.3 pips / $+3.79 | **R:** 0.46
> **Duration:** 20 min | **Close reason:** GREEN
> **Peak pips:** 6.3
> **Setup:** S15


---

## 💡 💰 USD_CHF SELL win: +5.1p / $+32.44 (29min)
**Date:** 2026-04-17T10:04:29
**Type:** discovery
**Tags:** win, usdchf, guardian, S5

> [!tip] DISCOVERY
> **Pair:** USD_CHF | **Direction:** SELL
> **PnL:** +5.1 pips / $+32.44 | **R:** 0.60
> **Duration:** 29 min | **Close reason:** YELLOW
> **Peak pips:** 5.8
> **Setup:** S5


---

## 💡 💰 GBP_JPY SELL win: +4.1p / $+12.86 (6min)
**Date:** 2026-04-17T10:37:46
**Type:** discovery
**Tags:** win, gbpjpy, guardian, S1

> [!tip] DISCOVERY
> **Pair:** GBP_JPY | **Direction:** SELL
> **PnL:** +4.1 pips / $+12.86 | **R:** 0.31
> **Duration:** 6 min | **Close reason:** GREEN
> **Peak pips:** 5.4
> **Setup:** S1


---

## ❌ ❌ USD_CHF SELL loss: -4.0p / $-25.92 (33min)
**Date:** 2026-04-17T11:37:13
**Type:** failure
**Tags:** loss, usdchf, guardian, S5

> [!danger] FAILURE
> **Pair:** USD_CHF | **Direction:** SELL
> **PnL:** -4.0 pips / $-25.92 | **R:** -0.23
> **Duration:** 33 min | **Close reason:** BLACK
> **Peak pips:** 3.2
> **Setup:** S5


---

## ❌ ❌ EUR_AUD SELL loss: -15.5p / $-56.24 (86min)
**Date:** 2026-04-17T13:50:42
**Type:** failure
**Tags:** loss, euraud, guardian, S5

> [!danger] FAILURE
> **Pair:** EUR_AUD | **Direction:** SELL
> **PnL:** -15.5 pips / $-56.24 | **R:** -0.36
> **Duration:** 86 min | **Close reason:** BLACK
> **Peak pips:** 0.0
> **Setup:** S5


---

## ❌ ❌ EUR_CHF SELL loss: -25.7p / $-165.81 (184min)
**Date:** 2026-04-19T20:25:05
**Type:** failure
**Tags:** loss, eurchf, guardian, S1

> [!danger] FAILURE
> **Pair:** EUR_CHF | **Direction:** SELL
> **PnL:** -25.7 pips / $-165.81 | **R:** -0.67
> **Duration:** 184 min | **Close reason:** BLACK
> **Peak pips:** 0.3
> **Setup:** S1


---

## ❌ ❌ AUD_JPY SELL loss: -54.9p / $-174.40 (206min)
**Date:** 2026-04-19T21:12:28
**Type:** failure
**Tags:** loss, audjpy, guardian, S13

> [!danger] FAILURE
> **Pair:** AUD_JPY | **Direction:** SELL
> **PnL:** -54.9 pips / $-174.40 | **R:** -0.69
> **Duration:** 206 min | **Close reason:** BLACK
> **Peak pips:** 0.7
> **Setup:** S13


---

## 💡 💰 USD_CHF SELL win: +4.2p / $+26.62 (47min)
**Date:** 2026-04-20T07:18:40
**Type:** discovery
**Tags:** win, usdchf, guardian, S15

> [!tip] DISCOVERY
> **Pair:** USD_CHF | **Direction:** SELL
> **PnL:** +4.2 pips / $+26.62 | **R:** 0.59
> **Duration:** 47 min | **Close reason:** YELLOW
> **Peak pips:** 5.1
> **Setup:** S15


---

## 💡 💰 USD_CHF SELL win: +6.0p / $+38.09 (11min)
**Date:** 2026-04-20T09:29:57
**Type:** discovery
**Tags:** win, usdchf, guardian, S1

> [!tip] DISCOVERY
> **Pair:** USD_CHF | **Direction:** SELL
> **PnL:** +6.0 pips / $+38.09 | **R:** 0.55
> **Duration:** 11 min | **Close reason:** YELLOW
> **Peak pips:** 7.2
> **Setup:** S1


---

## 💡 💰 EUR_CHF SELL win: +3.9p / $+24.76 (41min)
**Date:** 2026-04-20T09:30:13
**Type:** discovery
**Tags:** win, eurchf, guardian, S1

> [!tip] DISCOVERY
> **Pair:** EUR_CHF | **Direction:** SELL
> **PnL:** +3.9 pips / $+24.76 | **R:** 0.98
> **Duration:** 41 min | **Close reason:** YELLOW
> **Peak pips:** 5.0
> **Setup:** S1


---

## ❌ ❌ EUR_CHF SELL loss: -1.7p / $-11.01 (24min)
**Date:** 2026-04-20T10:22:52
**Type:** failure
**Tags:** loss, eurchf, guardian, S5

> [!danger] FAILURE
> **Pair:** EUR_CHF | **Direction:** SELL
> **PnL:** -1.7 pips / $-11.01 | **R:** -0.08
> **Duration:** 24 min | **Close reason:** BLACK
> **Peak pips:** 0.2
> **Setup:** S5


---

## 💡 💰 EUR_CHF SELL win: +6.2p / $+39.37 (15min)
**Date:** 2026-04-20T10:53:56
**Type:** discovery
**Tags:** win, eurchf, guardian, S1

> [!tip] DISCOVERY
> **Pair:** EUR_CHF | **Direction:** SELL
> **PnL:** +6.2 pips / $+39.37 | **R:** 0.61
> **Duration:** 15 min | **Close reason:** YELLOW
> **Peak pips:** 7.3
> **Setup:** S1


---

## 💡 💰 USD_CHF SELL win: +6.3p / $+40.05 (69min)
**Date:** 2026-04-20T10:55:43
**Type:** discovery
**Tags:** win, usdchf, guardian, S1

> [!tip] DISCOVERY
> **Pair:** USD_CHF | **Direction:** SELL
> **PnL:** +6.3 pips / $+40.05 | **R:** 0.56
> **Duration:** 69 min | **Close reason:** GREEN
> **Peak pips:** 7.2
> **Setup:** S1


---

## ❌ ❌ EUR_AUD SELL loss: -9.9p / $-35.83 (81min)
**Date:** 2026-04-20T11:21:02
**Type:** failure
**Tags:** loss, euraud, guardian, unknown

> [!danger] FAILURE
> **Pair:** EUR_AUD | **Direction:** SELL
> **PnL:** -9.9 pips / $-35.83 | **R:** -0.38
> **Duration:** 81 min | **Close reason:** BLACK
> **Peak pips:** 2.7
> **Setup:** unknown


---

## 💡 💰 USD_JPY SELL win: +5.8p / $+18.10 (53min)
**Date:** 2026-04-20T11:26:54
**Type:** discovery
**Tags:** win, usdjpy, guardian, S15

> [!tip] DISCOVERY
> **Pair:** USD_JPY | **Direction:** SELL
> **PnL:** +5.8 pips / $+18.10 | **R:** 0.53
> **Duration:** 53 min | **Close reason:** YELLOW
> **Peak pips:** 6.7
> **Setup:** S15


---

## 💡 💰 USD_CHF SELL win: +4.8p / $+30.55 (28min)
**Date:** 2026-04-20T11:26:55
**Type:** discovery
**Tags:** win, usdchf, guardian, S1

> [!tip] DISCOVERY
> **Pair:** USD_CHF | **Direction:** SELL
> **PnL:** +4.8 pips / $+30.55 | **R:** 0.48
> **Duration:** 28 min | **Close reason:** GREEN
> **Peak pips:** 5.7
> **Setup:** S1


---

## ❌ ❌ EUR_CHF SELL loss: -5.4p / $-35.05 (57min)
**Date:** 2026-04-20T12:11:07
**Type:** failure
**Tags:** loss, eurchf, guardian, S5

> [!danger] FAILURE
> **Pair:** EUR_CHF | **Direction:** SELL
> **PnL:** -5.4 pips / $-35.05 | **R:** -0.16
> **Duration:** 57 min | **Close reason:** BLACK
> **Peak pips:** 0.6
> **Setup:** S5


---

## ❌ ❌ USD_JPY SELL loss: -4.5p / $-14.32 (41min)
**Date:** 2026-04-20T12:25:28
**Type:** failure
**Tags:** loss, usdjpy, guardian, S15

> [!danger] FAILURE
> **Pair:** USD_JPY | **Direction:** SELL
> **PnL:** -4.5 pips / $-14.32 | **R:** -0.12
> **Duration:** 41 min | **Close reason:** BLACK
> **Peak pips:** 1.3
> **Setup:** S15


---

## ❌ ❌ USD_CHF SELL loss: -0.5p / $-6.49 (15min)
**Date:** 2026-04-20T12:59:44
**Type:** failure
**Tags:** loss, usdchf, guardian, S1

> [!danger] FAILURE
> **Pair:** USD_CHF | **Direction:** SELL
> **PnL:** -0.5 pips / $-6.49 | **R:** -0.02
> **Duration:** 15 min | **Close reason:** BLACK
> **Peak pips:** 1.1
> **Setup:** S1


---

## ❌ ❌ EUR_AUD SELL loss: -3.2p / $-11.60 (28min)
**Date:** 2026-04-20T15:50:12
**Type:** failure
**Tags:** loss, euraud, guardian, S15

> [!danger] FAILURE
> **Pair:** EUR_AUD | **Direction:** SELL
> **PnL:** -3.2 pips / $-11.60 | **R:** -0.15
> **Duration:** 28 min | **Close reason:** BLACK
> **Peak pips:** 0.1
> **Setup:** S15


---

## ❌ ❌ EUR_GBP SELL loss: -0.3p / $-2.05 (13min)
**Date:** 2026-04-20T16:35:31
**Type:** failure
**Tags:** loss, eurgbp, guardian, unknown

> [!danger] FAILURE
> **Pair:** EUR_GBP | **Direction:** SELL
> **PnL:** -0.3 pips / $-2.05 | **R:** -0.08
> **Duration:** 13 min | **Close reason:** YELLOW
> **Peak pips:** 0.6
> **Setup:** unknown


---

## ❌ ❌ NZD_USD BUY loss: -0.2p / $-1.00 (21min)
**Date:** 2026-04-20T16:49:53
**Type:** failure
**Tags:** loss, nzdusd, guardian, unknown

> [!danger] FAILURE
> **Pair:** NZD_USD | **Direction:** BUY
> **PnL:** -0.2 pips / $-1.00 | **R:** -0.04
> **Duration:** 21 min | **Close reason:** GREEN
> **Peak pips:** 1.5
> **Setup:** unknown


---

## ❌ ❌ EUR_AUD SELL loss: -5.0p / $-30.81 (42min)
**Date:** 2026-04-20T17:05:09
**Type:** failure
**Tags:** loss, euraud, guardian, unknown

> [!danger] FAILURE
> **Pair:** EUR_AUD | **Direction:** SELL
> **PnL:** -5.0 pips / $-30.81 | **R:** -0.26
> **Duration:** 42 min | **Close reason:** RED
> **Peak pips:** 0.0
> **Setup:** unknown


---

## ❌ ❌ EUR_JPY BUY loss: -19.3p / $-61.39 (37min)
**Date:** 2026-04-20T17:59:03
**Type:** failure
**Tags:** loss, eurjpy, guardian, S5

> [!danger] FAILURE
> **Pair:** EUR_JPY | **Direction:** BUY
> **PnL:** -19.3 pips / $-61.39 | **R:** -1.00
> **Duration:** 37 min | **Close reason:** RED
> **Peak pips:** 0.0
> **Setup:** S5


---

## ❌ ❌ EUR_USD BUY loss: -0.4p / $-2.00 (92min)
**Date:** 2026-04-20T18:53:13
**Type:** failure
**Tags:** loss, eurusd, guardian, S15

> [!danger] FAILURE
> **Pair:** EUR_USD | **Direction:** BUY
> **PnL:** -0.4 pips / $-2.00 | **R:** -0.04
> **Duration:** 92 min | **Close reason:** GREEN
> **Peak pips:** 1.6
> **Setup:** S15


---

## ❌ ❌ AUD_USD SELL loss: -1.3p / $-6.50 (1min)
**Date:** 2026-04-20T19:14:34
**Type:** failure
**Tags:** loss, audusd, guardian, unknown

> [!danger] FAILURE
> **Pair:** AUD_USD | **Direction:** SELL
> **PnL:** -1.3 pips / $-6.50 | **R:** -0.22
> **Duration:** 1 min | **Close reason:** BLACK
> **Peak pips:** 0.0
> **Setup:** unknown


---

## 💡 💰 USD_JPY BUY win: +0.4p / $+1.25 (24min)
**Date:** 2026-04-20T19:37:30
**Type:** discovery
**Tags:** win, usdjpy, guardian, unknown

> [!tip] DISCOVERY
> **Pair:** USD_JPY | **Direction:** BUY
> **PnL:** +0.4 pips / $+1.25 | **R:** 0.03
> **Duration:** 24 min | **Close reason:** GREEN
> **Peak pips:** 2.6
> **Setup:** unknown


---

## ❌ ❌ GBP_USD BUY loss: -16.4p / $-82.00 (74min)
**Date:** 2026-04-20T20:26:09
**Type:** failure
**Tags:** loss, gbpusd, guardian, S1

> [!danger] FAILURE
> **Pair:** GBP_USD | **Direction:** BUY
> **PnL:** -16.4 pips / $-82.00 | **R:** -1.01
> **Duration:** 74 min | **Close reason:** GREEN
> **Peak pips:** 0.0
> **Setup:** S1


---

## ❌ ❌ USD_JPY SELL loss: -15.5p / $-49.24 (54min)
**Date:** 2026-04-20T20:37:30
**Type:** failure
**Tags:** loss, usdjpy, guardian, S15

> [!danger] FAILURE
> **Pair:** USD_JPY | **Direction:** SELL
> **PnL:** -15.5 pips / $-49.24 | **R:** -1.00
> **Duration:** 54 min | **Close reason:** GREEN
> **Peak pips:** 0.3
> **Setup:** S15


---

## ❌ ❌ NZD_USD SELL loss: -3.0p / $-15.00 (1min)
**Date:** 2026-04-20T20:59:11
**Type:** failure
**Tags:** loss, nzdusd, guardian, S5

> [!danger] FAILURE
> **Pair:** NZD_USD | **Direction:** SELL
> **PnL:** -3.0 pips / $-15.00 | **R:** -0.27
> **Duration:** 1 min | **Close reason:** BLACK
> **Peak pips:** 0.0
> **Setup:** S5


---

## 💡 💰 EUR_GBP SELL win: +0.1p / $+0.67 (59min)
**Date:** 2026-04-20T21:42:17
**Type:** discovery
**Tags:** win, eurgbp, guardian, unknown

> [!tip] DISCOVERY
> **Pair:** EUR_GBP | **Direction:** SELL
> **PnL:** +0.1 pips / $+0.67 | **R:** 0.03
> **Duration:** 59 min | **Close reason:** GREEN
> **Peak pips:** 1.1
> **Setup:** unknown


---

## ❌ ❌ EUR_GBP SELL loss: -0.3p / $-2.05 (43min)
**Date:** 2026-04-20T22:26:06
**Type:** failure
**Tags:** loss, eurgbp, guardian, unknown

> [!danger] FAILURE
> **Pair:** EUR_GBP | **Direction:** SELL
> **PnL:** -0.3 pips / $-2.05 | **R:** -0.08
> **Duration:** 43 min | **Close reason:** YELLOW
> **Peak pips:** 0.6
> **Setup:** unknown


---

## 💡 💰 EUR_JPY SELL win: +1.1p / $+3.43 (50min)
**Date:** 2026-04-20T22:48:12
**Type:** discovery
**Tags:** win, eurjpy, guardian, S15

> [!tip] DISCOVERY
> **Pair:** EUR_JPY | **Direction:** SELL
> **PnL:** +1.1 pips / $+3.43 | **R:** 0.37
> **Duration:** 50 min | **Close reason:** RED
> **Peak pips:** 3.9
> **Setup:** S15


---

## 💡 💰 EUR_JPY SELL win: +0.8p / $+2.49 (11min)
**Date:** 2026-04-20T23:09:15
**Type:** discovery
**Tags:** win, eurjpy, guardian, S15

> [!tip] DISCOVERY
> **Pair:** EUR_JPY | **Direction:** SELL
> **PnL:** +0.8 pips / $+2.49 | **R:** 0.14
> **Duration:** 11 min | **Close reason:** RED
> **Peak pips:** 2.7
> **Setup:** S15


---

## ❌ ❌ EUR_USD BUY loss: -7.0p / $-35.00 (38min)
**Date:** 2026-04-20T23:36:14
**Type:** failure
**Tags:** loss, eurusd, guardian, S15

> [!danger] FAILURE
> **Pair:** EUR_USD | **Direction:** BUY
> **PnL:** -7.0 pips / $-35.00 | **R:** -1.00
> **Duration:** 38 min | **Close reason:** GREEN
> **Peak pips:** 0.0
> **Setup:** S15


---

## ❌ ❌ EUR_AUD SELL loss: -23.9p / $-86.49 (126min)
**Date:** 2026-04-20T23:38:31
**Type:** failure
**Tags:** loss, euraud, guardian, S15

> [!danger] FAILURE
> **Pair:** EUR_AUD | **Direction:** SELL
> **PnL:** -23.9 pips / $-86.49 | **R:** -1.00
> **Duration:** 126 min | **Close reason:** YELLOW
> **Peak pips:** 0.0
> **Setup:** S15


---

## ❌ ❌ NZD_USD SELL loss: -2.7p / $-13.50 (1min)
**Date:** 2026-04-21T00:59:20
**Type:** failure
**Tags:** loss, nzdusd, guardian, S5

> [!danger] FAILURE
> **Pair:** NZD_USD | **Direction:** SELL
> **PnL:** -2.7 pips / $-13.50 | **R:** -0.30
> **Duration:** 1 min | **Close reason:** BLACK
> **Peak pips:** 0.0
> **Setup:** S5


---

## ❌ ❌ AUD_USD BUY loss: -0.4p / $-2.00 (96min)
**Date:** 2026-04-21T01:04:08
**Type:** failure
**Tags:** loss, audusd, guardian, unknown

> [!danger] FAILURE
> **Pair:** AUD_USD | **Direction:** BUY
> **PnL:** -0.4 pips / $-2.00 | **R:** -0.09
> **Duration:** 96 min | **Close reason:** GREEN
> **Peak pips:** 0.9
> **Setup:** unknown


---

## 💡 💰 EUR_JPY SELL win: +2.9p / $+9.04 (137min)
**Date:** 2026-04-21T02:00:43
**Type:** discovery
**Tags:** win, eurjpy, guardian, S1

> [!tip] DISCOVERY
> **Pair:** EUR_JPY | **Direction:** SELL
> **PnL:** +2.9 pips / $+9.04 | **R:** 0.21
> **Duration:** 137 min | **Close reason:** YELLOW
> **Peak pips:** 1.4
> **Setup:** S1


---

## ❌ ❌ EUR_JPY BUY loss: -5.6p / $-17.80 (5min)
**Date:** 2026-04-21T02:33:02
**Type:** failure
**Tags:** loss, eurjpy, guardian, S1

> [!danger] FAILURE
> **Pair:** EUR_JPY | **Direction:** BUY
> **PnL:** -5.6 pips / $-17.80 | **R:** -1.00
> **Duration:** 5 min | **Close reason:** GREEN
> **Peak pips:** 0.0
> **Setup:** S1


---

## ❌ ❌ EUR_GBP BUY loss: -0.5p / $-3.41 (10min)
**Date:** 2026-04-21T02:38:05
**Type:** failure
**Tags:** loss, eurgbp, guardian, unknown

> [!danger] FAILURE
> **Pair:** EUR_GBP | **Direction:** BUY
> **PnL:** -0.5 pips / $-3.41 | **R:** -0.12
> **Duration:** 10 min | **Close reason:** GREEN
> **Peak pips:** 0.8
> **Setup:** unknown


---

## 💡 💰 AUD_USD BUY win: +0.4p / $+2.00 (9min)
**Date:** 2026-04-21T05:22:08
**Type:** discovery
**Tags:** win, audusd, guardian, S5

> [!tip] DISCOVERY
> **Pair:** AUD_USD | **Direction:** BUY
> **PnL:** +0.4 pips / $+2.00 | **R:** 0.07
> **Duration:** 9 min | **Close reason:** RED
> **Peak pips:** 2.4
> **Setup:** S5


---

## 💡 💰 AUD_USD BUY win: +1.8p / $+9.00 (30min)
**Date:** 2026-04-21T05:58:00
**Type:** discovery
**Tags:** win, audusd, guardian, S5

> [!tip] DISCOVERY
> **Pair:** AUD_USD | **Direction:** BUY
> **PnL:** +1.8 pips / $+9.00 | **R:** 0.60
> **Duration:** 30 min | **Close reason:** RED
> **Peak pips:** 3.5
> **Setup:** S5


---

## 💡 💰 AUD_USD BUY win: +1.5p / $+7.50 (13min)
**Date:** 2026-04-21T06:11:10
**Type:** discovery
**Tags:** win, audusd, guardian, S5

> [!tip] DISCOVERY
> **Pair:** AUD_USD | **Direction:** BUY
> **PnL:** +1.5 pips / $+7.50 | **R:** 0.10
> **Duration:** 13 min | **Close reason:** RED
> **Peak pips:** 2.6
> **Setup:** S5


---

## 💡 💰 AUD_USD BUY win: +1.5p / $+7.50 (49min)
**Date:** 2026-04-21T07:02:11
**Type:** discovery
**Tags:** win, audusd, guardian, S5

> [!tip] DISCOVERY
> **Pair:** AUD_USD | **Direction:** BUY
> **PnL:** +1.5 pips / $+7.50 | **R:** 0.10
> **Duration:** 49 min | **Close reason:** RED
> **Peak pips:** 2.5
> **Setup:** S5


---

## 💡 💰 AUD_USD BUY win: +4.5p / $+22.50 (12min)
**Date:** 2026-04-21T07:25:11
**Type:** discovery
**Tags:** win, audusd, guardian, S5

> [!tip] DISCOVERY
> **Pair:** AUD_USD | **Direction:** BUY
> **PnL:** +4.5 pips / $+22.50 | **R:** 0.69
> **Duration:** 12 min | **Close reason:** YELLOW
> **Peak pips:** 5.1
> **Setup:** S5


---

## ❌ ❌ NZD_USD SELL loss: -10.2p / $-51.00 (3min)
**Date:** 2026-04-21T07:31:18
**Type:** failure
**Tags:** loss, nzdusd, guardian, S15

> [!danger] FAILURE
> **Pair:** NZD_USD | **Direction:** SELL
> **PnL:** -10.2 pips / $-51.00 | **R:** -0.83
> **Duration:** 3 min | **Close reason:** BLACK
> **Peak pips:** 0.0
> **Setup:** S15


---

## 💡 💰 EUR_GBP BUY win: +1.0p / $+6.69 (13min)
**Date:** 2026-04-21T07:56:47
**Type:** discovery
**Tags:** win, eurgbp, guardian, S13

> [!tip] DISCOVERY
> **Pair:** EUR_GBP | **Direction:** BUY
> **PnL:** +1.0 pips / $+6.69 | **R:** 0.18
> **Duration:** 13 min | **Close reason:** GREEN
> **Peak pips:** 1.9
> **Setup:** S13


---

## 💡 💰 EUR_JPY SELL win: +1.1p / $+3.42 (17min)
**Date:** 2026-04-21T08:16:03
**Type:** discovery
**Tags:** win, eurjpy, guardian, S15

> [!tip] DISCOVERY
> **Pair:** EUR_JPY | **Direction:** SELL
> **PnL:** +1.1 pips / $+3.42 | **R:** 0.05
> **Duration:** 17 min | **Close reason:** YELLOW
> **Peak pips:** 1.3
> **Setup:** S15


---

## ❌ ❌ EUR_AUD BUY loss: -18.3p / $-66.23 (40min)
**Date:** 2026-04-21T09:24:12
**Type:** failure
**Tags:** loss, euraud, guardian, S15

> [!danger] FAILURE
> **Pair:** EUR_AUD | **Direction:** BUY
> **PnL:** -18.3 pips / $-66.23 | **R:** -1.00
> **Duration:** 40 min | **Close reason:** GREEN
> **Peak pips:** 0.0
> **Setup:** S15


---

## 💡 💰 EUR_USD BUY win: +4.8p / $+24.00 (56min)
**Date:** 2026-04-21T09:33:10
**Type:** discovery
**Tags:** win, eurusd, guardian, S1

> [!tip] DISCOVERY
> **Pair:** EUR_USD | **Direction:** BUY
> **PnL:** +4.8 pips / $+24.00 | **R:** 0.51
> **Duration:** 56 min | **Close reason:** YELLOW
> **Peak pips:** 5.9
> **Setup:** S1


---

## 💡 💰 AUD_USD BUY win: +4.6p / $+23.00 (58min)
**Date:** 2026-04-21T09:35:12
**Type:** discovery
**Tags:** win, audusd, guardian, S15

> [!tip] DISCOVERY
> **Pair:** AUD_USD | **Direction:** BUY
> **PnL:** +4.6 pips / $+23.00 | **R:** 0.54
> **Duration:** 58 min | **Close reason:** YELLOW
> **Peak pips:** 5.4
> **Setup:** S15


---

## ❌ ❌ AUD_JPY SELL loss: -11.3p / $-35.87 (17min)
**Date:** 2026-04-21T09:45:17
**Type:** failure
**Tags:** loss, audjpy, guardian, S15

> [!danger] FAILURE
> **Pair:** AUD_JPY | **Direction:** SELL
> **PnL:** -11.3 pips / $-35.87 | **R:** -1.01
> **Duration:** 17 min | **Close reason:** RED
> **Peak pips:** 0.0
> **Setup:** S15


---

## 💡 💰 EUR_JPY BUY win: +1.6p / $+4.98 (11min)
**Date:** 2026-04-21T10:08:01
**Type:** discovery
**Tags:** win, eurjpy, guardian, unknown

> [!tip] DISCOVERY
> **Pair:** EUR_JPY | **Direction:** BUY
> **PnL:** +1.6 pips / $+4.98 | **R:** 0.17
> **Duration:** 11 min | **Close reason:** GREEN
> **Peak pips:** 4.2
> **Setup:** unknown


---

## 💡 💰 EUR_JPY BUY win: +0.9p / $+2.80 (11min)
**Date:** 2026-04-21T10:24:15
**Type:** discovery
**Tags:** win, eurjpy, guardian, unknown

> [!tip] DISCOVERY
> **Pair:** EUR_JPY | **Direction:** BUY
> **PnL:** +0.9 pips / $+2.80 | **R:** 0.08
> **Duration:** 11 min | **Close reason:** GREEN
> **Peak pips:** 3.1
> **Setup:** unknown


---

## ❌ ❌ AUD_USD SELL loss: -7.0p / $-35.00 (31min)
**Date:** 2026-04-21T10:30:21
**Type:** failure
**Tags:** loss, audusd, guardian, S15

> [!danger] FAILURE
> **Pair:** AUD_USD | **Direction:** SELL
> **PnL:** -7.0 pips / $-35.00 | **R:** -1.00
> **Duration:** 31 min | **Close reason:** YELLOW
> **Peak pips:** 0.3
> **Setup:** S15


---

## 💡 💰 EUR_USD BUY win: +5.2p / $+26.00 (11min)
**Date:** 2026-04-21T10:39:18
**Type:** discovery
**Tags:** win, eurusd, guardian, S15

> [!tip] DISCOVERY
> **Pair:** EUR_USD | **Direction:** BUY
> **PnL:** +5.2 pips / $+26.00 | **R:** 1.00
> **Duration:** 11 min | **Close reason:** YELLOW
> **Peak pips:** 6.5
> **Setup:** S15


---

## 💡 💰 USD_JPY SELL win: +3.7p / $+11.51 (13min)
**Date:** 2026-04-21T10:41:04
**Type:** discovery
**Tags:** win, usdjpy, guardian, unknown

> [!tip] DISCOVERY
> **Pair:** USD_JPY | **Direction:** SELL
> **PnL:** +3.7 pips / $+11.51 | **R:** 3.70
> **Duration:** 13 min | **Close reason:** RED
> **Peak pips:** 5.2
> **Setup:** unknown


---

## ❌ ❌ EUR_USD BUY loss: -16.2p / $-81.00 (12min)
**Date:** 2026-04-21T10:55:49
**Type:** failure
**Tags:** loss, eurusd, guardian, S15

> [!danger] FAILURE
> **Pair:** EUR_USD | **Direction:** BUY
> **PnL:** -16.2 pips / $-81.00 | **R:** -1.00
> **Duration:** 12 min | **Close reason:** RED
> **Peak pips:** 0.0
> **Setup:** S15


---

## ❌ ❌ EUR_JPY SELL loss: -0.3p / $-0.95 (55min)
**Date:** 2026-04-21T11:38:15
**Type:** failure
**Tags:** loss, eurjpy, guardian, unknown

> [!danger] FAILURE
> **Pair:** EUR_JPY | **Direction:** SELL
> **PnL:** -0.3 pips / $-0.95 | **R:** -0.10
> **Duration:** 55 min | **Close reason:** YELLOW
> **Peak pips:** 3.4
> **Setup:** unknown


---

## 💡 💰 USD_CAD BUY win: +4.8p / $+17.40 (32min)
**Date:** 2026-04-21T12:41:24
**Type:** discovery
**Tags:** win, usdcad, guardian, S15

> [!tip] DISCOVERY
> **Pair:** USD_CAD | **Direction:** BUY
> **PnL:** +4.8 pips / $+17.40 | **R:** 0.50
> **Duration:** 32 min | **Close reason:** YELLOW
> **Peak pips:** 5.1
> **Setup:** S15


---

## 💡 💰 GBP_JPY SELL win: +3.5p / $+10.86 (46min)
**Date:** 2026-04-21T12:55:23
**Type:** discovery
**Tags:** win, gbpjpy, guardian, S5

> [!tip] DISCOVERY
> **Pair:** GBP_JPY | **Direction:** SELL
> **PnL:** +3.5 pips / $+10.86 | **R:** 0.88
> **Duration:** 46 min | **Close reason:** BLACK
> **Peak pips:** 5.0
> **Setup:** S5


---

## ❌ ❌ NZD_USD BUY loss: -6.0p / $-30.00 (20min)
**Date:** 2026-04-21T13:03:35
**Type:** failure
**Tags:** loss, nzdusd, guardian, S15

> [!danger] FAILURE
> **Pair:** NZD_USD | **Direction:** BUY
> **PnL:** -6.0 pips / $-30.00 | **R:** -1.00
> **Duration:** 20 min | **Close reason:** GREEN
> **Peak pips:** 0.5
> **Setup:** S15


---

## 💡 💰 GBP_JPY SELL win: +7.5p / $+23.26 (15min)
**Date:** 2026-04-21T13:13:34
**Type:** discovery
**Tags:** win, gbpjpy, guardian, S5

> [!tip] DISCOVERY
> **Pair:** GBP_JPY | **Direction:** SELL
> **PnL:** +7.5 pips / $+23.26 | **R:** 0.96
> **Duration:** 15 min | **Close reason:** RED
> **Peak pips:** 9.2
> **Setup:** S5


---

## ❌ ❌ GBP_USD BUY loss: -3.7p / $-18.50 (2min)
**Date:** 2026-04-21T13:15:50
**Type:** failure
**Tags:** loss, gbpusd, guardian, S1

> [!danger] FAILURE
> **Pair:** GBP_USD | **Direction:** BUY
> **PnL:** -3.7 pips / $-18.50 | **R:** -1.06
> **Duration:** 2 min | **Close reason:** BLACK
> **Peak pips:** 0.0
> **Setup:** S1


---

## ❌ ❌ EUR_AUD BUY loss: -14.2p / $-51.29 (8min)
**Date:** 2026-04-21T13:39:09
**Type:** failure
**Tags:** loss, euraud, guardian, unknown

> [!danger] FAILURE
> **Pair:** EUR_AUD | **Direction:** BUY
> **PnL:** -14.2 pips / $-51.29 | **R:** -1.01
> **Duration:** 8 min | **Close reason:** YELLOW
> **Peak pips:** 0.0
> **Setup:** unknown


---

## 💡 💰 GBP_JPY SELL win: +4.7p / $+14.60 (10min)
**Date:** 2026-04-21T13:53:38
**Type:** discovery
**Tags:** win, gbpjpy, guardian, unknown

> [!tip] DISCOVERY
> **Pair:** GBP_JPY | **Direction:** SELL
> **PnL:** +4.7 pips / $+14.60 | **R:** 0.92
> **Duration:** 10 min | **Close reason:** RED
> **Peak pips:** 6.4
> **Setup:** unknown


---

## 💡 💰 AUD_JPY SELL win: +0.2p / $+0.62 (25min)
**Date:** 2026-04-21T14:24:19
**Type:** discovery
**Tags:** win, audjpy, guardian, unknown

> [!tip] DISCOVERY
> **Pair:** AUD_JPY | **Direction:** SELL
> **PnL:** +0.2 pips / $+0.62 | **R:** 0.01
> **Duration:** 25 min | **Close reason:** YELLOW
> **Peak pips:** 2.7
> **Setup:** unknown


---

## 💡 💰 USD_CHF BUY win: +5.5p / $+34.83 (2min)
**Date:** 2026-04-21T14:26:06
**Type:** discovery
**Tags:** win, usdchf, guardian, unknown

> [!tip] DISCOVERY
> **Pair:** USD_CHF | **Direction:** BUY
> **PnL:** +5.5 pips / $+34.83 | **R:** 0.30
> **Duration:** 2 min | **Close reason:** GREEN
> **Peak pips:** 7.6
> **Setup:** unknown


---

## 💡 💰 EUR_CHF SELL win: +0.9p / $+5.70 (29min)
**Date:** 2026-04-21T14:53:01
**Type:** discovery
**Tags:** win, eurchf, guardian, S15

> [!tip] DISCOVERY
> **Pair:** EUR_CHF | **Direction:** SELL
> **PnL:** +0.9 pips / $+5.70 | **R:** 0.90
> **Duration:** 29 min | **Close reason:** GREEN
> **Peak pips:** 2.0
> **Setup:** S15


---

## 💡 💰 AUD_USD SELL win: +7.4p / $+45.00 (76min)
**Date:** 2026-04-21T15:42:17
**Type:** discovery
**Tags:** win, audusd, guardian, S15

> [!tip] DISCOVERY
> **Pair:** AUD_USD | **Direction:** SELL
> **PnL:** +7.4 pips / $+45.00 | **R:** 0.86
> **Duration:** 76 min | **Close reason:** GREEN
> **Peak pips:** 7.4
> **Setup:** S15


---

## 💡 💰 AUD_JPY SELL win: +7.6p / $+23.57 (73min)
**Date:** 2026-04-21T15:42:18
**Type:** discovery
**Tags:** win, audjpy, guardian, S15

> [!tip] DISCOVERY
> **Pair:** AUD_JPY | **Direction:** SELL
> **PnL:** +7.6 pips / $+23.57 | **R:** 0.97
> **Duration:** 73 min | **Close reason:** YELLOW
> **Peak pips:** 9.2
> **Setup:** S15


---

## 💡 💰 EUR_CHF BUY win: +1.3p / $+8.23 (47min)
**Date:** 2026-04-21T15:45:34
**Type:** discovery
**Tags:** win, eurchf, guardian, unknown

> [!tip] DISCOVERY
> **Pair:** EUR_CHF | **Direction:** BUY
> **PnL:** +1.3 pips / $+8.23 | **R:** 0.43
> **Duration:** 47 min | **Close reason:** YELLOW
> **Peak pips:** 3.5
> **Setup:** unknown


---

## ❌ ❌ AUD_JPY BUY loss: -0.8p / $-6.01 (11min)
**Date:** 2026-04-21T16:09:50
**Type:** failure
**Tags:** loss, audjpy, guardian, S15

> [!danger] FAILURE
> **Pair:** AUD_JPY | **Direction:** BUY
> **PnL:** -0.8 pips / $-6.01 | **R:** -0.05
> **Duration:** 11 min | **Close reason:** GREEN
> **Peak pips:** 0.0
> **Setup:** S15


---

## 💡 💰 AUD_USD BUY win: +4.9p / $+24.50 (14min)
**Date:** 2026-04-21T16:28:17
**Type:** discovery
**Tags:** win, audusd, guardian, S15

> [!tip] DISCOVERY
> **Pair:** AUD_USD | **Direction:** BUY
> **PnL:** +4.9 pips / $+24.50 | **R:** 0.43
> **Duration:** 14 min | **Close reason:** YELLOW
> **Peak pips:** 5.4
> **Setup:** S15


---

## 💡 💰 AUD_JPY SELL win: +1.9p / $+5.90 (6min)
**Date:** 2026-04-21T16:34:52
**Type:** discovery
**Tags:** win, audjpy, guardian, unknown

> [!tip] DISCOVERY
> **Pair:** AUD_JPY | **Direction:** SELL
> **PnL:** +1.9 pips / $+5.90 | **R:** 0.19
> **Duration:** 6 min | **Close reason:** RED
> **Peak pips:** 3.5
> **Setup:** unknown


---

## ❌ ❌ GBP_JPY SELL loss: -26.4p / $-83.63 (9min)
**Date:** 2026-04-21T16:58:44
**Type:** failure
**Tags:** loss, gbpjpy, guardian, S15

> [!danger] FAILURE
> **Pair:** GBP_JPY | **Direction:** SELL
> **PnL:** -26.4 pips / $-83.63 | **R:** -1.00
> **Duration:** 9 min | **Close reason:** BLACK
> **Peak pips:** 0.0
> **Setup:** S15


---

## ❌ ❌ EUR_GBP BUY loss: -9.9p / $-78.45 (16min)
**Date:** 2026-04-21T17:05:04
**Type:** failure
**Tags:** loss, eurgbp, guardian, unknown

> [!danger] FAILURE
> **Pair:** EUR_GBP | **Direction:** BUY
> **PnL:** -9.9 pips / $-78.45 | **R:** -0.74
> **Duration:** 16 min | **Close reason:** RED
> **Peak pips:** 0.0
> **Setup:** unknown


---

## 💡 💰 AUD_JPY SELL win: +3.6p / $-6.97 (21min)
**Date:** 2026-04-21T17:10:23
**Type:** discovery
**Tags:** win, audjpy, guardian, unknown

> [!tip] DISCOVERY
> **Pair:** AUD_JPY | **Direction:** SELL
> **PnL:** +3.6 pips / $-6.97 | **R:** 1.20
> **Duration:** 21 min | **Close reason:** YELLOW
> **Peak pips:** 3.6
> **Setup:** unknown


---

## 💡 💰 AUD_USD BUY win: +1.5p / $+7.50 (12min)
**Date:** 2026-04-21T19:53:17
**Type:** discovery
**Tags:** win, audusd, guardian, S15

> [!tip] DISCOVERY
> **Pair:** AUD_USD | **Direction:** BUY
> **PnL:** +1.5 pips / $+7.50 | **R:** 0.12
> **Duration:** 12 min | **Close reason:** YELLOW
> **Peak pips:** 2.5
> **Setup:** S15


---

## ❌ ❌ AUD_USD BUY loss: -0.3p / $-1.50 (4min)
**Date:** 2026-04-21T20:02:01
**Type:** failure
**Tags:** loss, audusd, guardian, S15

> [!danger] FAILURE
> **Pair:** AUD_USD | **Direction:** BUY
> **PnL:** -0.3 pips / $-1.50 | **R:** -0.04
> **Duration:** 4 min | **Close reason:** YELLOW
> **Peak pips:** 1.2
> **Setup:** S15


---

## 💡 💰 EUR_USD BUY win: +1.4p / $+7.00 (24min)
**Date:** 2026-04-21T20:05:19
**Type:** discovery
**Tags:** win, eurusd, guardian, S15

> [!tip] DISCOVERY
> **Pair:** EUR_USD | **Direction:** BUY
> **PnL:** +1.4 pips / $+7.00 | **R:** 0.47
> **Duration:** 24 min | **Close reason:** YELLOW
> **Peak pips:** 3.2
> **Setup:** S15


---

## 💡 💰 USD_JPY SELL win: +4.5p / $+13.99 (4min)
**Date:** 2026-04-21T20:10:07
**Type:** discovery
**Tags:** win, usdjpy, guardian, S15

> [!tip] DISCOVERY
> **Pair:** USD_JPY | **Direction:** SELL
> **PnL:** +4.5 pips / $+13.99 | **R:** 1.00
> **Duration:** 4 min | **Close reason:** YELLOW
> **Peak pips:** 5.6
> **Setup:** S15


---

## 💡 💰 NZD_USD BUY win: +0.1p / $+0.50 (7min)
**Date:** 2026-04-21T20:35:02
**Type:** discovery
**Tags:** win, nzdusd, guardian, S15

> [!tip] DISCOVERY
> **Pair:** NZD_USD | **Direction:** BUY
> **PnL:** +0.1 pips / $+0.50 | **R:** 0.03
> **Duration:** 7 min | **Close reason:** GREEN
> **Peak pips:** 1.9
> **Setup:** S15


---

## ❌ ❌ GBP_JPY BUY loss: -0.6p / $-1.90 (6min)
**Date:** 2026-04-21T21:19:01
**Type:** failure
**Tags:** loss, gbpjpy, guardian, S13

> [!danger] FAILURE
> **Pair:** GBP_JPY | **Direction:** BUY
> **PnL:** -0.6 pips / $-1.90 | **R:** -0.11
> **Duration:** 6 min | **Close reason:** GREEN
> **Peak pips:** 2.2
> **Setup:** S13


---

## ❌ ❌ NZD_USD BUY loss: -0.2p / $-1.00 (6min)
**Date:** 2026-04-21T22:31:14
**Type:** failure
**Tags:** loss, nzdusd, guardian, S13

> [!danger] FAILURE
> **Pair:** NZD_USD | **Direction:** BUY
> **PnL:** -0.2 pips / $-1.00 | **R:** -0.02
> **Duration:** 6 min | **Close reason:** GREEN
> **Peak pips:** 1.4
> **Setup:** S13


---

## ❌ ❌ EUR_USD BUY loss: -9.1p / $-45.50 (3min)
**Date:** 2026-04-21T23:01:14
**Type:** failure
**Tags:** loss, eurusd, guardian, S15

> [!danger] FAILURE
> **Pair:** EUR_USD | **Direction:** BUY
> **PnL:** -9.1 pips / $-45.50 | **R:** -1.00
> **Duration:** 3 min | **Close reason:** RED
> **Peak pips:** 0.0
> **Setup:** S15


---

## ❌ ❌ EUR_GBP SELL loss: -0.2p / $-1.36 (8min)
**Date:** 2026-04-21T23:05:37
**Type:** failure
**Tags:** loss, eurgbp, guardian, unknown

> [!danger] FAILURE
> **Pair:** EUR_GBP | **Direction:** SELL
> **PnL:** -0.2 pips / $-1.36 | **R:** -0.07
> **Duration:** 8 min | **Close reason:** GREEN
> **Peak pips:** 0.9
> **Setup:** unknown


---

## 💡 💰 EUR_JPY BUY win: +0.6p / $+1.86 (20min)
**Date:** 2026-04-21T23:35:18
**Type:** discovery
**Tags:** win, eurjpy, guardian, unknown

> [!tip] DISCOVERY
> **Pair:** EUR_JPY | **Direction:** BUY
> **PnL:** +0.6 pips / $+1.86 | **R:** 0.07
> **Duration:** 20 min | **Close reason:** GREEN
> **Peak pips:** 2.9
> **Setup:** unknown


---

## ❌ ❌ EUR_JPY SELL loss: -0.4p / $-1.27 (17min)
**Date:** 2026-04-22T00:15:39
**Type:** failure
**Tags:** loss, eurjpy, guardian, unknown

> [!danger] FAILURE
> **Pair:** EUR_JPY | **Direction:** SELL
> **PnL:** -0.4 pips / $-1.27 | **R:** -0.05
> **Duration:** 17 min | **Close reason:** GREEN
> **Peak pips:** 1.4
> **Setup:** unknown


---

## ❌ ❌ EUR_CHF SELL loss: -2.7p / $-17.46 (30min)
**Date:** 2026-04-22T00:28:54
**Type:** failure
**Tags:** loss, eurchf, guardian, unknown

> [!danger] FAILURE
> **Pair:** EUR_CHF | **Direction:** SELL
> **PnL:** -2.7 pips / $-17.46 | **R:** -1.00
> **Duration:** 30 min | **Close reason:** GREEN
> **Peak pips:** 0.0
> **Setup:** unknown


---

## ❌ ❌ USD_JPY SELL loss: -0.1p / $-0.32 (5min)
**Date:** 2026-04-22T01:02:57
**Type:** failure
**Tags:** loss, usdjpy, guardian, unknown

> [!danger] FAILURE
> **Pair:** USD_JPY | **Direction:** SELL
> **PnL:** -0.1 pips / $-0.32 | **R:** -0.02
> **Duration:** 5 min | **Close reason:** YELLOW
> **Peak pips:** 1.5
> **Setup:** unknown


---

## 💡 💰 EUR_AUD SELL win: +0.7p / $+2.48 (31min)
**Date:** 2026-04-22T01:14:17
**Type:** discovery
**Tags:** win, euraud, guardian, S15

> [!tip] DISCOVERY
> **Pair:** EUR_AUD | **Direction:** SELL
> **PnL:** +0.7 pips / $+2.48 | **R:** 0.05
> **Duration:** 31 min | **Close reason:** GREEN
> **Peak pips:** 3.8
> **Setup:** S15


---

## ❌ ❌ AUD_JPY SELL loss: -25.4p / $-80.55 (81min)
**Date:** 2026-04-22T01:16:34
**Type:** failure
**Tags:** loss, audjpy, guardian, S15

> [!danger] FAILURE
> **Pair:** AUD_JPY | **Direction:** SELL
> **PnL:** -25.4 pips / $-80.55 | **R:** -1.02
> **Duration:** 81 min | **Close reason:** RED
> **Peak pips:** 0.0
> **Setup:** S15


---

## ❌ ❌ USD_CHF BUY loss: -16.2p / $-104.91 (84min)
**Date:** 2026-04-22T01:19:06
**Type:** failure
**Tags:** loss, usdchf, guardian, S1

> [!danger] FAILURE
> **Pair:** USD_CHF | **Direction:** BUY
> **PnL:** -16.2 pips / $-104.91 | **R:** -1.00
> **Duration:** 84 min | **Close reason:** GREEN
> **Peak pips:** 0.0
> **Setup:** S1


---

## ❌ ❌ USD_CAD BUY loss: -27.1p / $-100.26 (84min)
**Date:** 2026-04-22T01:19:37
**Type:** failure
**Tags:** loss, usdcad, guardian, S1

> [!danger] FAILURE
> **Pair:** USD_CAD | **Direction:** BUY
> **PnL:** -27.1 pips / $-100.26 | **R:** -1.00
> **Duration:** 84 min | **Close reason:** GREEN
> **Peak pips:** 0.0
> **Setup:** S1


---

## ❌ ❌ GBP_JPY BUY loss: -9.4p / $-29.81 (5min)
**Date:** 2026-04-22T02:03:13
**Type:** failure
**Tags:** loss, gbpjpy, guardian, unknown

> [!danger] FAILURE
> **Pair:** GBP_JPY | **Direction:** BUY
> **PnL:** -9.4 pips / $-29.81 | **R:** -1.00
> **Duration:** 5 min | **Close reason:** GREEN
> **Peak pips:** 0.0
> **Setup:** unknown


---

## 💡 💰 EUR_AUD SELL win: +3.1p / $+11.01 (57min)
**Date:** 2026-04-22T02:38:45
**Type:** discovery
**Tags:** win, euraud, guardian, S15

> [!tip] DISCOVERY
> **Pair:** EUR_AUD | **Direction:** SELL
> **PnL:** +3.1 pips / $+11.01 | **R:** 0.33
> **Duration:** 57 min | **Close reason:** GREEN
> **Peak pips:** 4.9
> **Setup:** S15


---

## ❌ ❌ NZD_USD BUY loss: -6.4p / $-32.00 (40min)
**Date:** 2026-04-22T03:23:10
**Type:** failure
**Tags:** loss, nzdusd, guardian, S5

> [!danger] FAILURE
> **Pair:** NZD_USD | **Direction:** BUY
> **PnL:** -6.4 pips / $-32.00 | **R:** -1.02
> **Duration:** 40 min | **Close reason:** GREEN
> **Peak pips:** 0.7
> **Setup:** S5


---

## ❌ ❌ EUR_AUD SELL loss: -19.0p / $-68.74 (47min)
**Date:** 2026-04-22T03:43:55
**Type:** failure
**Tags:** loss, euraud, guardian, S15

> [!danger] FAILURE
> **Pair:** EUR_AUD | **Direction:** SELL
> **PnL:** -19.0 pips / $-68.74 | **R:** -0.67
> **Duration:** 47 min | **Close reason:** YELLOW
> **Peak pips:** 0.0
> **Setup:** S15


---

## ❌ ❌ EUR_GBP BUY loss: -5.0p / $-34.14 (33min)
**Date:** 2026-04-22T03:46:45
**Type:** failure
**Tags:** loss, eurgbp, guardian, unknown

> [!danger] FAILURE
> **Pair:** EUR_GBP | **Direction:** BUY
> **PnL:** -5.0 pips / $-34.14 | **R:** -1.04
> **Duration:** 33 min | **Close reason:** RED
> **Peak pips:** 0.0
> **Setup:** unknown


---

## 💡 💰 EUR_USD BUY win: +0.2p / $+1.00 (16min)
**Date:** 2026-04-22T04:13:58
**Type:** discovery
**Tags:** win, eurusd, guardian, S15

> [!tip] DISCOVERY
> **Pair:** EUR_USD | **Direction:** BUY
> **PnL:** +0.2 pips / $+1.00 | **R:** 0.02
> **Duration:** 16 min | **Close reason:** GREEN
> **Peak pips:** 1.9
> **Setup:** S15


---

## 💡 💰 USD_CHF SELL win: +0.8p / $+5.08 (106min)
**Date:** 2026-04-22T04:18:01
**Type:** discovery
**Tags:** win, usdchf, guardian, S15

> [!tip] DISCOVERY
> **Pair:** USD_CHF | **Direction:** SELL
> **PnL:** +0.8 pips / $+5.08 | **R:** 0.89
> **Duration:** 106 min | **Close reason:** YELLOW
> **Peak pips:** 1.9
> **Setup:** S15


---

## 💡 💰 GBP_USD BUY win: +1.9p / $+9.50 (4min)
**Date:** 2026-04-22T04:47:00
**Type:** discovery
**Tags:** win, gbpusd, guardian, S15

> [!tip] DISCOVERY
> **Pair:** GBP_USD | **Direction:** BUY
> **PnL:** +1.9 pips / $+9.50 | **R:** 0.16
> **Duration:** 4 min | **Close reason:** GREEN
> **Peak pips:** 3.5
> **Setup:** S15


---

## ❌ ❌ EUR_JPY BUY loss: -0.5p / $-1.58 (6min)
**Date:** 2026-04-22T04:49:01
**Type:** failure
**Tags:** loss, eurjpy, guardian, S15

> [!danger] FAILURE
> **Pair:** EUR_JPY | **Direction:** BUY
> **PnL:** -0.5 pips / $-1.58 | **R:** -0.06
> **Duration:** 6 min | **Close reason:** GREEN
> **Peak pips:** 1.7
> **Setup:** S15


---

## ❌ ❌ EUR_CHF SELL loss: -10.2p / $-66.04 (188min)
**Date:** 2026-04-22T05:10:11
**Type:** failure
**Tags:** loss, eurchf, guardian, S15

> [!danger] FAILURE
> **Pair:** EUR_CHF | **Direction:** SELL
> **PnL:** -10.2 pips / $-66.04 | **R:** -1.02
> **Duration:** 188 min | **Close reason:** RED
> **Peak pips:** 0.0
> **Setup:** S15


---

## 💡 💰 AUD_USD SELL win: +3.8p / $+19.00 (15min)
**Date:** 2026-04-22T05:58:11
**Type:** discovery
**Tags:** win, audusd, guardian, S15

> [!tip] DISCOVERY
> **Pair:** AUD_USD | **Direction:** SELL
> **PnL:** +3.8 pips / $+19.00 | **R:** 0.75
> **Duration:** 15 min | **Close reason:** YELLOW
> **Peak pips:** 4.8
> **Setup:** S15


---

## ❌ ❌ AUD_USD BUY loss: -1.5p / $-7.50 (1min)
**Date:** 2026-04-22T05:59:12
**Type:** failure
**Tags:** loss, audusd, guardian, S15

> [!danger] FAILURE
> **Pair:** AUD_USD | **Direction:** BUY
> **PnL:** -1.5 pips / $-7.50 | **R:** -1.00
> **Duration:** 1 min | **Close reason:** GREEN
> **Peak pips:** 0.0
> **Setup:** S15


---

## ❌ ❌ GBP_JPY BUY loss: -5.9p / $-18.70 (10min)
**Date:** 2026-04-22T06:24:11
**Type:** failure
**Tags:** loss, gbpjpy, guardian, unknown

> [!danger] FAILURE
> **Pair:** GBP_JPY | **Direction:** BUY
> **PnL:** -5.9 pips / $-18.70 | **R:** -1.02
> **Duration:** 10 min | **Close reason:** GREEN
> **Peak pips:** 0.9
> **Setup:** unknown


---

## 💡 💰 GBP_USD BUY win: +1.0p / $+5.00 (11min)
**Date:** 2026-04-22T06:54:14
**Type:** discovery
**Tags:** win, gbpusd, guardian, unknown

> [!tip] DISCOVERY
> **Pair:** GBP_USD | **Direction:** BUY
> **PnL:** +1.0 pips / $+5.00 | **R:** 0.11
> **Duration:** 11 min | **Close reason:** GREEN
> **Peak pips:** 2.3
> **Setup:** unknown


---

## ❌ ❌ GBP_USD BUY loss: -12.3p / $-61.50 (29min)
**Date:** 2026-04-22T07:27:32
**Type:** failure
**Tags:** loss, gbpusd, guardian, S15

> [!danger] FAILURE
> **Pair:** GBP_USD | **Direction:** BUY
> **PnL:** -12.3 pips / $-61.50 | **R:** -1.01
> **Duration:** 29 min | **Close reason:** GREEN
> **Peak pips:** 0.0
> **Setup:** S15


---

## ❌ ❌ NZD_USD BUY loss: -5.7p / $-28.50 (27min)
**Date:** 2026-04-22T07:55:45
**Type:** failure
**Tags:** loss, nzdusd, guardian, S15

> [!danger] FAILURE
> **Pair:** NZD_USD | **Direction:** BUY
> **PnL:** -5.7 pips / $-28.50 | **R:** -1.00
> **Duration:** 27 min | **Close reason:** GREEN
> **Peak pips:** 0.0
> **Setup:** S15


---

## 💡 💰 EUR_CHF SELL win: +2.9p / $+18.34 (7min)
**Date:** 2026-04-22T09:05:14
**Type:** discovery
**Tags:** win, eurchf, guardian, unknown

> [!tip] DISCOVERY
> **Pair:** EUR_CHF | **Direction:** SELL
> **PnL:** +2.9 pips / $+18.34 | **R:** 3.22
> **Duration:** 7 min | **Close reason:** RED
> **Peak pips:** 4.4
> **Setup:** unknown


---

## ❌ ❌ EUR_GBP BUY loss: -3.7p / $-25.22 (41min)
**Date:** 2026-04-22T09:09:24
**Type:** failure
**Tags:** loss, eurgbp, guardian, S15

> [!danger] FAILURE
> **Pair:** EUR_GBP | **Direction:** BUY
> **PnL:** -3.7 pips / $-25.22 | **R:** -1.00
> **Duration:** 41 min | **Close reason:** RED
> **Peak pips:** 0.4
> **Setup:** S15


---

## ❌ ❌ EUR_AUD BUY loss: -19.7p / $-71.20 (51min)
**Date:** 2026-04-22T09:19:44
**Type:** failure
**Tags:** loss, euraud, guardian, S15

> [!danger] FAILURE
> **Pair:** EUR_AUD | **Direction:** BUY
> **PnL:** -19.7 pips / $-71.20 | **R:** -1.00
> **Duration:** 51 min | **Close reason:** RED
> **Peak pips:** 0.0
> **Setup:** S15


---

## 💡 💰 EUR_JPY BUY win: +0.5p / $+1.55 (10min)
**Date:** 2026-04-22T09:23:16
**Type:** discovery
**Tags:** win, eurjpy, guardian, unknown

> [!tip] DISCOVERY
> **Pair:** EUR_JPY | **Direction:** BUY
> **PnL:** +0.5 pips / $+1.55 | **R:** 0.08
> **Duration:** 10 min | **Close reason:** BLACK
> **Peak pips:** 3.1
> **Setup:** unknown


---

## 💡 💰 EUR_JPY SELL win: +1.3p / $+4.04 (9min)
**Date:** 2026-04-22T09:37:08
**Type:** discovery
**Tags:** win, eurjpy, guardian, unknown

> [!tip] DISCOVERY
> **Pair:** EUR_JPY | **Direction:** SELL
> **PnL:** +1.3 pips / $+4.04 | **R:** 0.24
> **Duration:** 9 min | **Close reason:** GREEN
> **Peak pips:** 3.2
> **Setup:** unknown


---

## ❌ ❌ AUD_USD SELL loss: -15.5p / $-77.50 (40min)
**Date:** 2026-04-22T09:41:26
**Type:** failure
**Tags:** loss, audusd, guardian, S15

> [!danger] FAILURE
> **Pair:** AUD_USD | **Direction:** SELL
> **PnL:** -15.5 pips / $-77.50 | **R:** -1.01
> **Duration:** 40 min | **Close reason:** GREEN
> **Peak pips:** 0.0
> **Setup:** S15


---

## 💡 💰 EUR_CHF BUY win: +4.2p / $+26.58 (21min)
**Date:** 2026-04-22T09:49:15
**Type:** discovery
**Tags:** win, eurchf, guardian, S15

> [!tip] DISCOVERY
> **Pair:** EUR_CHF | **Direction:** BUY
> **PnL:** +4.2 pips / $+26.58 | **R:** 0.76
> **Duration:** 21 min | **Close reason:** GREEN
> **Peak pips:** 5.3
> **Setup:** S15


---

## 💡 💰 AUD_USD BUY win: +1.0p / $+5.00 (6min)
**Date:** 2026-04-22T11:51:08
**Type:** discovery
**Tags:** win, audusd, guardian, unknown

> [!tip] DISCOVERY
> **Pair:** AUD_USD | **Direction:** BUY
> **PnL:** +1.0 pips / $+5.00 | **R:** 0.38
> **Duration:** 6 min | **Close reason:** YELLOW
> **Peak pips:** 1.6
> **Setup:** unknown


---

## 💡 💰 EUR_USD BUY win: +0.5p / $+2.50 (7min)
**Date:** 2026-04-22T11:52:09
**Type:** discovery
**Tags:** win, eurusd, guardian, S5

> [!tip] DISCOVERY
> **Pair:** EUR_USD | **Direction:** BUY
> **PnL:** +0.5 pips / $+2.50 | **R:** 0.09
> **Duration:** 7 min | **Close reason:** BLACK
> **Peak pips:** 2.0
> **Setup:** S5


---

## 💡 💰 AUD_USD BUY win: +0.3p / $+1.50 (8min)
**Date:** 2026-04-22T12:07:08
**Type:** discovery
**Tags:** win, audusd, guardian, unknown

> [!tip] DISCOVERY
> **Pair:** AUD_USD | **Direction:** BUY
> **PnL:** +0.3 pips / $+1.50 | **R:** 0.04
> **Duration:** 8 min | **Close reason:** YELLOW
> **Peak pips:** 2.1
> **Setup:** unknown


---

## 💡 💰 AUD_USD SELL win: +1.9p / $+9.50 (8min)
**Date:** 2026-04-22T12:21:15
**Type:** discovery
**Tags:** win, audusd, guardian, unknown

> [!tip] DISCOVERY
> **Pair:** AUD_USD | **Direction:** SELL
> **PnL:** +1.9 pips / $+9.50 | **R:** 0.25
> **Duration:** 8 min | **Close reason:** GREEN
> **Peak pips:** 2.9
> **Setup:** unknown


---

## ❌ ❌ EUR_CHF BUY loss: +0.0p / $+0.00 (13min)
**Date:** 2026-04-22T12:26:18
**Type:** failure
**Tags:** loss, eurchf, guardian, unknown

> [!danger] FAILURE
> **Pair:** EUR_CHF | **Direction:** BUY
> **PnL:** +0.0 pips / $+0.00 | **R:** 0.00
> **Duration:** 13 min | **Close reason:** GREEN
> **Peak pips:** 1.2
> **Setup:** unknown


---

## 💡 💰 NZD_USD BUY win: +1.1p / $+5.50 (43min)
**Date:** 2026-04-22T13:11:41
**Type:** discovery
**Tags:** win, nzdusd, guardian, unknown

> [!tip] DISCOVERY
> **Pair:** NZD_USD | **Direction:** BUY
> **PnL:** +1.1 pips / $+5.50 | **R:** 0.18
> **Duration:** 43 min | **Close reason:** GREEN
> **Peak pips:** 3.0
> **Setup:** unknown


---

## 💡 💰 NZD_USD BUY win: +0.2p / $+1.00 (20min)
**Date:** 2026-04-22T13:34:00
**Type:** discovery
**Tags:** win, nzdusd, guardian, unknown

> [!tip] DISCOVERY
> **Pair:** NZD_USD | **Direction:** BUY
> **PnL:** +0.2 pips / $+1.00 | **R:** 0.02
> **Duration:** 20 min | **Close reason:** GREEN
> **Peak pips:** 1.6
> **Setup:** unknown


---

## ❌ ❌ EUR_JPY BUY loss: -13.9p / $-44.02 (133min)
**Date:** 2026-04-22T13:54:29
**Type:** failure
**Tags:** loss, eurjpy, guardian, S15

> [!danger] FAILURE
> **Pair:** EUR_JPY | **Direction:** BUY
> **PnL:** -13.9 pips / $-44.02 | **R:** -1.01
> **Duration:** 133 min | **Close reason:** BLACK
> **Peak pips:** 1.7
> **Setup:** S15


---

## ❌ ❌ NZD_USD BUY loss: -5.5p / $-27.50 (19min)
**Date:** 2026-04-22T14:17:26
**Type:** failure
**Tags:** loss, nzdusd, guardian, unknown

> [!danger] FAILURE
> **Pair:** NZD_USD | **Direction:** BUY
> **PnL:** -5.5 pips / $-27.50 | **R:** -1.02
> **Duration:** 19 min | **Close reason:** GREEN
> **Peak pips:** 0.0
> **Setup:** unknown


---

## 💡 💰 AUD_USD SELL win: +0.9p / $+4.50 (6min)
**Date:** 2026-04-22T14:19:12
**Type:** discovery
**Tags:** win, audusd, guardian, unknown

> [!tip] DISCOVERY
> **Pair:** AUD_USD | **Direction:** SELL
> **PnL:** +0.9 pips / $+4.50 | **R:** 0.16
> **Duration:** 6 min | **Close reason:** GREEN
> **Peak pips:** 1.9
> **Setup:** unknown


---

## 💡 💰 EUR_USD BUY win: +0.8p / $+4.00 (5min)
**Date:** 2026-04-22T14:46:03
**Type:** discovery
**Tags:** win, eurusd, guardian, S5

> [!tip] DISCOVERY
> **Pair:** EUR_USD | **Direction:** BUY
> **PnL:** +0.8 pips / $+4.00 | **R:** 0.11
> **Duration:** 5 min | **Close reason:** BLACK
> **Peak pips:** 1.9
> **Setup:** S5


---

## ❌ ❌ GBP_JPY BUY loss: -11.2p / $-35.46 (20min)
**Date:** 2026-04-22T15:01:12
**Type:** failure
**Tags:** loss, gbpjpy, guardian, unknown

> [!danger] FAILURE
> **Pair:** GBP_JPY | **Direction:** BUY
> **PnL:** -11.2 pips / $-35.46 | **R:** -1.01
> **Duration:** 20 min | **Close reason:** GREEN
> **Peak pips:** 0.0
> **Setup:** unknown


---

## 💡 💰 USD_JPY BUY win: +2.0p / $+6.21 (24min)
**Date:** 2026-04-22T15:52:51
**Type:** discovery
**Tags:** win, usdjpy, guardian, S15

> [!tip] DISCOVERY
> **Pair:** USD_JPY | **Direction:** BUY
> **PnL:** +2.0 pips / $+6.21 | **R:** 6.67
> **Duration:** 24 min | **Close reason:** GREEN
> **Peak pips:** 3.1
> **Setup:** S15


---

## 💡 💰 USD_JPY SELL win: +1.1p / $+3.41 (10min)
**Date:** 2026-04-22T16:24:29
**Type:** discovery
**Tags:** win, usdjpy, guardian, unknown

> [!tip] DISCOVERY
> **Pair:** USD_JPY | **Direction:** SELL
> **PnL:** +1.1 pips / $+3.41 | **R:** 0.13
> **Duration:** 10 min | **Close reason:** RED
> **Peak pips:** 2.1
> **Setup:** unknown


---

## ❌ ❌ EUR_AUD BUY loss: -13.2p / $-47.73 (21min)
**Date:** 2026-04-22T16:55:03
**Type:** failure
**Tags:** loss, euraud, guardian, S1

> [!danger] FAILURE
> **Pair:** EUR_AUD | **Direction:** BUY
> **PnL:** -13.2 pips / $-47.73 | **R:** -1.01
> **Duration:** 21 min | **Close reason:** BLACK
> **Peak pips:** 0.0
> **Setup:** S1


---

## 💡 💰 AUD_USD SELL win: +2.0p / $-6.00 (10min)
**Date:** 2026-04-22T17:19:26
**Type:** discovery
**Tags:** win, audusd, guardian, S15

> [!tip] DISCOVERY
> **Pair:** AUD_USD | **Direction:** SELL
> **PnL:** +2.0 pips / $-6.00 | **R:** 0.27
> **Duration:** 10 min | **Close reason:** GREEN
> **Peak pips:** 2.3
> **Setup:** S15


---

## ❌ ❌ GBP_USD SELL loss: -9.0p / $-45.00 (6min)
**Date:** 2026-04-22T17:48:54
**Type:** failure
**Tags:** loss, gbpusd, guardian, S15

> [!danger] FAILURE
> **Pair:** GBP_USD | **Direction:** SELL
> **PnL:** -9.0 pips / $-45.00 | **R:** -1.00
> **Duration:** 6 min | **Close reason:** GREEN
> **Peak pips:** 0.0
> **Setup:** S15


---

## ❌ ❌ EUR_JPY SELL loss: -0.5p / $-1.58 (43min)
**Date:** 2026-04-22T19:13:25
**Type:** failure
**Tags:** loss, eurjpy, guardian, S5

> [!danger] FAILURE
> **Pair:** EUR_JPY | **Direction:** SELL
> **PnL:** -0.5 pips / $-1.58 | **R:** -0.07
> **Duration:** 43 min | **Close reason:** GREEN
> **Peak pips:** 1.5
> **Setup:** S5


---

## 💡 💰 EUR_USD SELL win: +0.1p / $+0.50 (1min)
**Date:** 2026-04-22T20:15:09
**Type:** discovery
**Tags:** win, eurusd, guardian, S1

> [!tip] DISCOVERY
> **Pair:** EUR_USD | **Direction:** SELL
> **PnL:** +0.1 pips / $+0.50 | **R:** 0.01
> **Duration:** 1 min | **Close reason:** GREEN
> **Peak pips:** 0.3
> **Setup:** S1


---

## 💡 💰 AUD_USD SELL win: +4.9p / $+24.50 (2min)
**Date:** 2026-04-22T20:16:26
**Type:** discovery
**Tags:** win, audusd, guardian, S1

> [!tip] DISCOVERY
> **Pair:** AUD_USD | **Direction:** SELL
> **PnL:** +4.9 pips / $+24.50 | **R:** 4.90
> **Duration:** 2 min | **Close reason:** GREEN
> **Peak pips:** 3.5
> **Setup:** S1


---

## ❌ ❌ AUD_JPY BUY loss: -10.6p / $-33.59 (10min)
**Date:** 2026-04-22T20:54:30
**Type:** failure
**Tags:** loss, audjpy, guardian, unknown

> [!danger] FAILURE
> **Pair:** AUD_JPY | **Direction:** BUY
> **PnL:** -10.6 pips / $-33.59 | **R:** -1.00
> **Duration:** 10 min | **Close reason:** GREEN
> **Peak pips:** 0.7
> **Setup:** unknown


---

## ❌ ❌ USD_CHF SELL loss: -4.6p / $-29.61 (43min)
**Date:** 2026-04-22T21:57:47
**Type:** failure
**Tags:** loss, usdchf, guardian, S5

> [!danger] FAILURE
> **Pair:** USD_CHF | **Direction:** SELL
> **PnL:** -4.6 pips / $-29.61 | **R:** -1.00
> **Duration:** 43 min | **Close reason:** BLACK
> **Peak pips:** 0.3
> **Setup:** S5


---

## ❌ ❌ EUR_CHF BUY loss: -0.8p / $-5.15 (20min)
**Date:** 2026-04-22T22:03:22
**Type:** failure
**Tags:** loss, eurchf, guardian, unknown

> [!danger] FAILURE
> **Pair:** EUR_CHF | **Direction:** BUY
> **PnL:** -0.8 pips / $-5.15 | **R:** -0.22
> **Duration:** 20 min | **Close reason:** GREEN
> **Peak pips:** 0.6
> **Setup:** unknown


---

## 💡 💰 AUD_USD SELL win: +1.0p / $+5.00 (57min)
**Date:** 2026-04-22T22:45:14
**Type:** discovery
**Tags:** win, audusd, guardian, unknown

> [!tip] DISCOVERY
> **Pair:** AUD_USD | **Direction:** SELL
> **PnL:** +1.0 pips / $+5.00 | **R:** 1.00
> **Duration:** 57 min | **Close reason:** GREEN
> **Peak pips:** 3.0
> **Setup:** unknown


---

## 💡 💰 AUD_USD SELL win: +3.2p / $+16.00 (10min)
**Date:** 2026-04-22T23:12:59
**Type:** discovery
**Tags:** win, audusd, guardian, S1

> [!tip] DISCOVERY
> **Pair:** AUD_USD | **Direction:** SELL
> **PnL:** +3.2 pips / $+16.00 | **R:** 0.46
> **Duration:** 10 min | **Close reason:** GREEN
> **Peak pips:** 3.8
> **Setup:** S1


---

## 💡 💰 EUR_AUD BUY win: +6.4p / $+22.62 (11min)
**Date:** 2026-04-22T23:24:06
**Type:** discovery
**Tags:** win, euraud, guardian, S1

> [!tip] DISCOVERY
> **Pair:** EUR_AUD | **Direction:** BUY
> **PnL:** +6.4 pips / $+22.62 | **R:** 0.90
> **Duration:** 11 min | **Close reason:** YELLOW
> **Peak pips:** 8.3
> **Setup:** S1


---

## ❌ ❌ USD_CAD BUY loss: -7.1p / $-26.23 (123min)
**Date:** 2026-04-23T01:46:43
**Type:** failure
**Tags:** loss, usdcad, guardian, unknown

> [!danger] FAILURE
> **Pair:** USD_CAD | **Direction:** BUY
> **PnL:** -7.1 pips / $-26.23 | **R:** -1.00
> **Duration:** 123 min | **Close reason:** GREEN
> **Peak pips:** 0.1
> **Setup:** unknown


---

## ❌ ❌ EUR_GBP SELL loss: -11.3p / $-76.99 (401min)
**Date:** 2026-04-23T02:00:37
**Type:** failure
**Tags:** loss, eurgbp, guardian, S1

> [!danger] FAILURE
> **Pair:** EUR_GBP | **Direction:** SELL
> **PnL:** -11.3 pips / $-76.99 | **R:** -1.03
> **Duration:** 401 min | **Close reason:** GREEN
> **Peak pips:** 0.0
> **Setup:** S1


---

## 💡 💰 USD_JPY BUY win: +0.9p / $+2.79 (5min)
**Date:** 2026-04-23T03:02:55
**Type:** discovery
**Tags:** win, usdjpy, guardian, S1

> [!tip] DISCOVERY
> **Pair:** USD_JPY | **Direction:** BUY
> **PnL:** +0.9 pips / $+2.79 | **R:** 0.09
> **Duration:** 5 min | **Close reason:** GREEN
> **Peak pips:** 2.4
> **Setup:** S1


---

## ❌ ❌ USD_CHF BUY loss: -3.7p / $-23.81 (5min)
**Date:** 2026-04-23T03:48:35
**Type:** failure
**Tags:** loss, usdchf, guardian, S5

> [!danger] FAILURE
> **Pair:** USD_CHF | **Direction:** BUY
> **PnL:** -3.7 pips / $-23.81 | **R:** -1.00
> **Duration:** 5 min | **Close reason:** GREEN
> **Peak pips:** 0.0
> **Setup:** S5


---

## ❌ ❌ USD_JPY BUY loss: -10.1p / $-31.96 (47min)
**Date:** 2026-04-23T04:00:12
**Type:** failure
**Tags:** loss, usdjpy, guardian, unknown

> [!danger] FAILURE
> **Pair:** USD_JPY | **Direction:** BUY
> **PnL:** -10.1 pips / $-31.96 | **R:** -1.02
> **Duration:** 47 min | **Close reason:** GREEN
> **Peak pips:** 0.0
> **Setup:** unknown


---

## 💡 💰 GBP_USD BUY win: +1.6p / $+8.00 (5min)
**Date:** 2026-04-23T04:48:15
**Type:** discovery
**Tags:** win, gbpusd, guardian, S1

> [!tip] DISCOVERY
> **Pair:** GBP_USD | **Direction:** BUY
> **PnL:** +1.6 pips / $+8.00 | **R:** 0.08
> **Duration:** 5 min | **Close reason:** YELLOW
> **Peak pips:** 3.1
> **Setup:** S1


---

## ❌ ❌ EUR_JPY SELL loss: -16.4p / $-51.86 (17min)
**Date:** 2026-04-23T04:59:52
**Type:** failure
**Tags:** loss, eurjpy, guardian, unknown

> [!danger] FAILURE
> **Pair:** EUR_JPY | **Direction:** SELL
> **PnL:** -16.4 pips / $-51.86 | **R:** -1.00
> **Duration:** 17 min | **Close reason:** GREEN
> **Peak pips:** 0.0
> **Setup:** unknown


---

## 💡 💰 AUD_JPY SELL win: +2.5p / $+1.55 (5min)
**Date:** 2026-04-23T05:01:25
**Type:** discovery
**Tags:** win, audjpy, guardian, S13

> [!tip] DISCOVERY
> **Pair:** AUD_JPY | **Direction:** SELL
> **PnL:** +2.5 pips / $+1.55 | **R:** 0.13
> **Duration:** 5 min | **Close reason:** GREEN
> **Peak pips:** 3.7
> **Setup:** S13


---

## ❌ ❌ EUR_USD SELL loss: -0.8p / $-4.00 (24min)
**Date:** 2026-04-23T05:26:30
**Type:** failure
**Tags:** loss, eurusd, guardian, S15

> [!danger] FAILURE
> **Pair:** EUR_USD | **Direction:** SELL
> **PnL:** -0.8 pips / $-4.00 | **R:** -0.06
> **Duration:** 24 min | **Close reason:** GREEN
> **Peak pips:** 2.3
> **Setup:** S15


---

## ❌ ❌ EUR_CHF SELL loss: -4.3p / $-27.65 (11min)
**Date:** 2026-04-23T05:41:26
**Type:** failure
**Tags:** loss, eurchf, guardian, unknown

> [!danger] FAILURE
> **Pair:** EUR_CHF | **Direction:** SELL
> **PnL:** -4.3 pips / $-27.65 | **R:** -1.00
> **Duration:** 11 min | **Close reason:** GREEN
> **Peak pips:** 0.0
> **Setup:** unknown


---

## 💡 💰 EUR_JPY SELL win: +1.0p / $+3.10 (5min)
**Date:** 2026-04-23T06:12:50
**Type:** discovery
**Tags:** win, eurjpy, guardian, S15

> [!tip] DISCOVERY
> **Pair:** EUR_JPY | **Direction:** SELL
> **PnL:** +1.0 pips / $+3.10 | **R:** 1.00
> **Duration:** 5 min | **Close reason:** GREEN
> **Peak pips:** 4.7
> **Setup:** S15


---

## 💡 💰 AUD_JPY SELL win: +1.4p / $+4.34 (18min)
**Date:** 2026-04-23T06:31:45
**Type:** discovery
**Tags:** win, audjpy, guardian, S15

> [!tip] DISCOVERY
> **Pair:** AUD_JPY | **Direction:** SELL
> **PnL:** +1.4 pips / $+4.34 | **R:** 0.10
> **Duration:** 18 min | **Close reason:** YELLOW
> **Peak pips:** 2.9
> **Setup:** S15


---

## 💡 💰 EUR_CHF SELL win: +4.2p / $+5.30 (9min)
**Date:** 2026-04-23T07:58:41
**Type:** discovery
**Tags:** win, eurchf, guardian, S1

> [!tip] DISCOVERY
> **Pair:** EUR_CHF | **Direction:** SELL
> **PnL:** +4.2 pips / $+5.30 | **R:** 1.00
> **Duration:** 9 min | **Close reason:** GREEN
> **Peak pips:** 5.3
> **Setup:** S1


---

## 💡 💰 NZD_USD SELL win: +2.0p / $+10.00 (6min)
**Date:** 2026-04-23T08:25:17
**Type:** discovery
**Tags:** win, nzdusd, guardian, S5

> [!tip] DISCOVERY
> **Pair:** NZD_USD | **Direction:** SELL
> **PnL:** +2.0 pips / $+10.00 | **R:** 0.37
> **Duration:** 6 min | **Close reason:** GREEN
> **Peak pips:** 4.1
> **Setup:** S5


---

## ❌ ❌ GBP_JPY BUY loss: -42.7p / $-135.14 (12min)
**Date:** 2026-04-23T08:49:43
**Type:** failure
**Tags:** loss, gbpjpy, guardian, S15

> [!danger] FAILURE
> **Pair:** GBP_JPY | **Direction:** BUY
> **PnL:** -42.7 pips / $-135.14 | **R:** -1.01
> **Duration:** 12 min | **Close reason:** YELLOW
> **Peak pips:** 0.0
> **Setup:** S15


---

## ❌ ❌ EUR_JPY BUY loss: -18.5p / $-58.55 (9min)
**Date:** 2026-04-23T09:14:53
**Type:** failure
**Tags:** loss, eurjpy, guardian, unknown

> [!danger] FAILURE
> **Pair:** EUR_JPY | **Direction:** BUY
> **PnL:** -18.5 pips / $-58.55 | **R:** -0.76
> **Duration:** 9 min | **Close reason:** YELLOW
> **Peak pips:** 0.0
> **Setup:** unknown


---

## 💡 💰 NZD_USD SELL win: +2.6p / $+13.00 (11min)
**Date:** 2026-04-23T09:16:27
**Type:** discovery
**Tags:** win, nzdusd, guardian, S5

> [!tip] DISCOVERY
> **Pair:** NZD_USD | **Direction:** SELL
> **PnL:** +2.6 pips / $+13.00 | **R:** 0.36
> **Duration:** 11 min | **Close reason:** GREEN
> **Peak pips:** 3.9
> **Setup:** S5


---

## 💡 💰 USD_JPY BUY win: +0.1p / $+0.31 (3min)
**Date:** 2026-04-23T09:17:00
**Type:** discovery
**Tags:** win, usdjpy, guardian, unknown

> [!tip] DISCOVERY
> **Pair:** USD_JPY | **Direction:** BUY
> **PnL:** +0.1 pips / $+0.31 | **R:** 0.01
> **Duration:** 3 min | **Close reason:** GREEN
> **Peak pips:** 4.3
> **Setup:** unknown


---

## 💡 💰 GBP_USD SELL win: +3.1p / $+15.50 (13min)
**Date:** 2026-04-23T09:18:32
**Type:** discovery
**Tags:** win, gbpusd, guardian, S15

> [!tip] DISCOVERY
> **Pair:** GBP_USD | **Direction:** SELL
> **PnL:** +3.1 pips / $+15.50 | **R:** 0.44
> **Duration:** 13 min | **Close reason:** GREEN
> **Peak pips:** 4.2
> **Setup:** S15


---

## ❌ ❌ GBP_USD SELL loss: -4.3p / $-21.50 (7min)
**Date:** 2026-04-23T10:00:06
**Type:** failure
**Tags:** loss, gbpusd, guardian, unknown

> [!danger] FAILURE
> **Pair:** GBP_USD | **Direction:** SELL
> **PnL:** -4.3 pips / $-21.50 | **R:** -0.14
> **Duration:** 7 min | **Close reason:** GREEN
> **Peak pips:** 0.0
> **Setup:** unknown


---

## ❌ ❌ AUD_USD SELL loss: -7.3p / $-72.50 (7min)
**Date:** 2026-04-23T10:00:09
**Type:** failure
**Tags:** loss, audusd, guardian, unknown

> [!danger] FAILURE
> **Pair:** AUD_USD | **Direction:** SELL
> **PnL:** -7.3 pips / $-72.50 | **R:** -0.33
> **Duration:** 7 min | **Close reason:** GREEN
> **Peak pips:** 0.0
> **Setup:** unknown


---

## 💡 💰 NZD_USD SELL win: +0.9p / $+4.50 (3min)
**Date:** 2026-04-23T10:03:49
**Type:** discovery
**Tags:** win, nzdusd, guardian, S5

> [!tip] DISCOVERY
> **Pair:** NZD_USD | **Direction:** SELL
> **PnL:** +0.9 pips / $+4.50 | **R:** 0.90
> **Duration:** 3 min | **Close reason:** GREEN
> **Peak pips:** 5.8
> **Setup:** S5


---

## 💡 💰 GBP_JPY BUY win: +2.6p / $+8.07 (8min)
**Date:** 2026-04-23T10:21:47
**Type:** discovery
**Tags:** win, gbpjpy, guardian, S15

> [!tip] DISCOVERY
> **Pair:** GBP_JPY | **Direction:** BUY
> **PnL:** +2.6 pips / $+8.07 | **R:** 0.21
> **Duration:** 8 min | **Close reason:** GREEN
> **Peak pips:** 9.2
> **Setup:** S15


---

## ❌ ❌ AUD_JPY SELL loss: -24.6p / $-77.89 (20min)
**Date:** 2026-04-23T10:26:52
**Type:** failure
**Tags:** loss, audjpy, guardian, S15

> [!danger] FAILURE
> **Pair:** AUD_JPY | **Direction:** SELL
> **PnL:** -24.6 pips / $-77.89 | **R:** -1.01
> **Duration:** 20 min | **Close reason:** YELLOW
> **Peak pips:** 1.3
> **Setup:** S15


---

## 💡 💰 NZD_USD SELL win: +2.4p / $+12.00 (16min)
**Date:** 2026-04-23T11:08:54
**Type:** discovery
**Tags:** win, nzdusd, guardian, S5

> [!tip] DISCOVERY
> **Pair:** NZD_USD | **Direction:** SELL
> **PnL:** +2.4 pips / $+12.00 | **R:** 0.50
> **Duration:** 16 min | **Close reason:** GREEN
> **Peak pips:** 3.6
> **Setup:** S5


---

## 💡 💰 EUR_JPY SELL win: +2.8p / $+8.69 (16min)
**Date:** 2026-04-23T11:08:56
**Type:** discovery
**Tags:** win, eurjpy, guardian, unknown

> [!tip] DISCOVERY
> **Pair:** EUR_JPY | **Direction:** SELL
> **PnL:** +2.8 pips / $+8.69 | **R:** 0.55
> **Duration:** 16 min | **Close reason:** GREEN
> **Peak pips:** 4.1
> **Setup:** unknown


---

## 💡 💰 USD_CHF SELL win: +0.9p / $+5.68 (5min)
**Date:** 2026-04-23T11:19:25
**Type:** discovery
**Tags:** win, usdchf, guardian, S15

> [!tip] DISCOVERY
> **Pair:** USD_CHF | **Direction:** SELL
> **PnL:** +0.9 pips / $+5.68 | **R:** 0.23
> **Duration:** 5 min | **Close reason:** GREEN
> **Peak pips:** 2.0
> **Setup:** S15


---

## 💡 💰 NZD_USD BUY win: +2.8p / $+14.00 (6min)
**Date:** 2026-04-23T11:28:11
**Type:** discovery
**Tags:** win, nzdusd, guardian, S5

> [!tip] DISCOVERY
> **Pair:** NZD_USD | **Direction:** BUY
> **PnL:** +2.8 pips / $+14.00 | **R:** 0.48
> **Duration:** 6 min | **Close reason:** YELLOW
> **Peak pips:** 4.1
> **Setup:** S5


---

## ❌ ❌ AUD_JPY BUY loss: -3.8p / $-12.03 (1min)
**Date:** 2026-04-23T11:45:27
**Type:** failure
**Tags:** loss, audjpy, guardian, unknown

> [!danger] FAILURE
> **Pair:** AUD_JPY | **Direction:** BUY
> **PnL:** -3.8 pips / $-12.03 | **R:** -1.06
> **Duration:** 1 min | **Close reason:** YELLOW
> **Peak pips:** 0.0
> **Setup:** unknown


---

## 💡 💰 EUR_JPY SELL win: +1.0p / $+3.10 (5min)
**Date:** 2026-04-23T11:46:15
**Type:** discovery
**Tags:** win, eurjpy, guardian, unknown

> [!tip] DISCOVERY
> **Pair:** EUR_JPY | **Direction:** SELL
> **PnL:** +1.0 pips / $+3.10 | **R:** 1.00
> **Duration:** 5 min | **Close reason:** GREEN
> **Peak pips:** 4.3
> **Setup:** unknown


---

## 💡 💰 GBP_USD SELL win: +7.9p / $+39.50 (6min)
**Date:** 2026-04-23T11:46:47
**Type:** discovery
**Tags:** win, gbpusd, guardian, unknown

> [!tip] DISCOVERY
> **Pair:** GBP_USD | **Direction:** SELL
> **PnL:** +7.9 pips / $+39.50 | **R:** 1.00
> **Duration:** 6 min | **Close reason:** GREEN
> **Peak pips:** 9.3
> **Setup:** unknown


---

## 💡 💰 EUR_JPY SELL win: +2.7p / $+8.38 (7min)
**Date:** 2026-04-23T12:05:46
**Type:** discovery
**Tags:** win, eurjpy, guardian, unknown

> [!tip] DISCOVERY
> **Pair:** EUR_JPY | **Direction:** SELL
> **PnL:** +2.7 pips / $+8.38 | **R:** 0.51
> **Duration:** 7 min | **Close reason:** GREEN
> **Peak pips:** 4.1
> **Setup:** unknown


---

## 💡 💰 EUR_JPY BUY win: +1.0p / $+3.10 (13min)
**Date:** 2026-04-23T12:35:24
**Type:** discovery
**Tags:** win, eurjpy, guardian, unknown

> [!tip] DISCOVERY
> **Pair:** EUR_JPY | **Direction:** BUY
> **PnL:** +1.0 pips / $+3.10 | **R:** 1.00
> **Duration:** 13 min | **Close reason:** GREEN
> **Peak pips:** 3.3
> **Setup:** unknown


---

## ❌ ❌ NZD_USD BUY loss: -18.6p / $-93.00 (1min)
**Date:** 2026-04-23T13:09:50
**Type:** failure
**Tags:** loss, nzdusd, guardian, S1

> [!danger] FAILURE
> **Pair:** NZD_USD | **Direction:** BUY
> **PnL:** -18.6 pips / $-93.00 | **R:** -1.01
> **Duration:** 1 min | **Close reason:** GREEN
> **Peak pips:** 0.0
> **Setup:** S1


---

## ❌ ❌ GBP_USD BUY loss: -29.8p / $-74.50 (2min)
**Date:** 2026-04-23T13:10:38
**Type:** failure
**Tags:** loss, gbpusd, guardian, S1

> [!danger] FAILURE
> **Pair:** GBP_USD | **Direction:** BUY
> **PnL:** -29.8 pips / $-74.50 | **R:** -1.00
> **Duration:** 2 min | **Close reason:** GREEN
> **Peak pips:** 1.8
> **Setup:** S1


---

## 💡 💰 GBP_USD BUY win: +5.5p / $+27.50 (3min)
**Date:** 2026-04-23T13:49:12
**Type:** discovery
**Tags:** win, gbpusd, guardian, S1

> [!tip] DISCOVERY
> **Pair:** GBP_USD | **Direction:** BUY
> **PnL:** +5.5 pips / $+27.50 | **R:** 0.95
> **Duration:** 3 min | **Close reason:** YELLOW
> **Peak pips:** 7.3
> **Setup:** S1


---

## 💡 💰 EUR_USD BUY win: +3.0p / $+15.00 (25min)
**Date:** 2026-04-23T13:57:47
**Type:** discovery
**Tags:** win, eurusd, guardian, unknown

> [!tip] DISCOVERY
> **Pair:** EUR_USD | **Direction:** BUY
> **PnL:** +3.0 pips / $+15.00 | **R:** 0.67
> **Duration:** 25 min | **Close reason:** BLACK
> **Peak pips:** 3.7
> **Setup:** unknown


---

## 💡 💰 NZD_USD BUY win: +7.0p / $+35.00 (19min)
**Date:** 2026-04-23T13:58:19
**Type:** discovery
**Tags:** win, nzdusd, guardian, S5

> [!tip] DISCOVERY
> **Pair:** NZD_USD | **Direction:** BUY
> **PnL:** +7.0 pips / $+35.00 | **R:** 0.99
> **Duration:** 19 min | **Close reason:** BLACK
> **Peak pips:** 8.3
> **Setup:** S5


---

## ❌ ❌ EUR_AUD BUY loss: -37.8p / $-27.29 (10min)
**Date:** 2026-04-23T14:02:08
**Type:** failure
**Tags:** loss, euraud, guardian, unknown

> [!danger] FAILURE
> **Pair:** EUR_AUD | **Direction:** BUY
> **PnL:** -37.8 pips / $-27.29 | **R:** -1.00
> **Duration:** 10 min | **Close reason:** GREEN
> **Peak pips:** 0.0
> **Setup:** unknown


---

## 💡 💰 USD_CAD SELL win: +1.2p / $+4.34 (4min)
**Date:** 2026-04-23T14:32:18
**Type:** discovery
**Tags:** win, usdcad, guardian, S5

> [!tip] DISCOVERY
> **Pair:** USD_CAD | **Direction:** SELL
> **PnL:** +1.2 pips / $+4.34 | **R:** 0.09
> **Duration:** 4 min | **Close reason:** BLACK
> **Peak pips:** 2.9
> **Setup:** S5


---

## ❌ ❌ EUR_USD BUY loss: -9.3p / $-46.50 (20min)
**Date:** 2026-04-23T15:04:08
**Type:** failure
**Tags:** loss, eurusd, guardian, unknown

> [!danger] FAILURE
> **Pair:** EUR_USD | **Direction:** BUY
> **PnL:** -9.3 pips / $-46.50 | **R:** -1.00
> **Duration:** 20 min | **Close reason:** RED
> **Peak pips:** 0.0
> **Setup:** unknown


---

## ❌ ❌ USD_CHF SELL loss: -3.4p / $-21.84 (20min)
**Date:** 2026-04-23T15:29:09
**Type:** failure
**Tags:** loss, usdchf, guardian, unknown

> [!danger] FAILURE
> **Pair:** USD_CHF | **Direction:** SELL
> **PnL:** -3.4 pips / $-21.84 | **R:** -0.15
> **Duration:** 20 min | **Close reason:** RED
> **Peak pips:** 0.0
> **Setup:** unknown


---

## 💡 💰 AUD_USD SELL win: +3.5p / $+17.50 (9min)
**Date:** 2026-04-23T16:12:38
**Type:** discovery
**Tags:** win, audusd, guardian, S5

> [!tip] DISCOVERY
> **Pair:** AUD_USD | **Direction:** SELL
> **PnL:** +3.5 pips / $+17.50 | **R:** 0.45
> **Duration:** 9 min | **Close reason:** GREEN
> **Peak pips:** 4.1
> **Setup:** S5


---

## ❌ ❌ GBP_JPY SELL loss: -13.3p / $-42.04 (16min)
**Date:** 2026-04-23T16:57:44
**Type:** failure
**Tags:** loss, gbpjpy, guardian, S15

> [!danger] FAILURE
> **Pair:** GBP_JPY | **Direction:** SELL
> **PnL:** -13.3 pips / $-42.04 | **R:** -1.04
> **Duration:** 16 min | **Close reason:** GREEN
> **Peak pips:** 0.0
> **Setup:** S15


---

## ❌ ❌ EUR_JPY BUY loss: -0.2p / $-6.01 (5min)
**Date:** 2026-04-23T17:05:08
**Type:** failure
**Tags:** loss, eurjpy, guardian, S15

> [!danger] FAILURE
> **Pair:** EUR_JPY | **Direction:** BUY
> **PnL:** -0.2 pips / $-6.01 | **R:** -0.01
> **Duration:** 5 min | **Close reason:** GREEN
> **Peak pips:** 3.0
> **Setup:** S15


---

## ❌ ❌ NZD_USD BUY loss: -14.3p / $-78.50 (5min)
**Date:** 2026-04-23T17:05:26
**Type:** failure
**Tags:** loss, nzdusd, guardian, S5

> [!danger] FAILURE
> **Pair:** NZD_USD | **Direction:** BUY
> **PnL:** -14.3 pips / $-78.50 | **R:** -0.55
> **Duration:** 5 min | **Close reason:** GREEN
> **Peak pips:** 0.0
> **Setup:** S5


---

## 💡 💰 USD_CHF SELL win: +4.2p / $-21.85 (6min)
**Date:** 2026-04-23T17:05:59
**Type:** discovery
**Tags:** win, usdchf, guardian, S5

> [!tip] DISCOVERY
> **Pair:** USD_CHF | **Direction:** SELL
> **PnL:** +4.2 pips / $-21.85 | **R:** 4.20
> **Duration:** 6 min | **Close reason:** GREEN
> **Peak pips:** 4.2
> **Setup:** S5


---

## ❌ ❌ EUR_AUD BUY loss: -1.4p / $-5.04 (31min)
**Date:** 2026-04-23T20:44:11
**Type:** failure
**Tags:** loss, euraud, guardian, unknown

> [!danger] FAILURE
> **Pair:** EUR_AUD | **Direction:** BUY
> **PnL:** -1.4 pips / $-5.04 | **R:** -0.16
> **Duration:** 31 min | **Close reason:** GREEN
> **Peak pips:** 1.7
> **Setup:** unknown


---

## 💡 💰 NZD_USD BUY win: +0.9p / $+4.50 (14min)
**Date:** 2026-04-23T21:02:37
**Type:** discovery
**Tags:** win, nzdusd, guardian, S15

> [!tip] DISCOVERY
> **Pair:** NZD_USD | **Direction:** BUY
> **PnL:** +0.9 pips / $+4.50 | **R:** 0.90
> **Duration:** 14 min | **Close reason:** BLACK
> **Peak pips:** 2.0
> **Setup:** S15


---

## ❌ ❌ GBP_USD BUY loss: -6.8p / $-34.00 (4min)
**Date:** 2026-04-23T21:32:23
**Type:** failure
**Tags:** loss, gbpusd, guardian, S5

> [!danger] FAILURE
> **Pair:** GBP_USD | **Direction:** BUY
> **PnL:** -6.8 pips / $-34.00 | **R:** -1.01
> **Duration:** 4 min | **Close reason:** RED
> **Peak pips:** 0.0
> **Setup:** S5


---

## 💡 💰 EUR_USD BUY win: +0.7p / $+3.50 (12min)
**Date:** 2026-04-23T21:54:10
**Type:** discovery
**Tags:** win, eurusd, guardian, S15

> [!tip] DISCOVERY
> **Pair:** EUR_USD | **Direction:** BUY
> **PnL:** +0.7 pips / $+3.50 | **R:** 0.70
> **Duration:** 12 min | **Close reason:** YELLOW
> **Peak pips:** 1.6
> **Setup:** S15


---

## ❌ ❌ AUD_USD BUY loss: -11.0p / $-55.00 (26min)
**Date:** 2026-04-23T22:25:29
**Type:** failure
**Tags:** loss, audusd, guardian, S1

> [!danger] FAILURE
> **Pair:** AUD_USD | **Direction:** BUY
> **PnL:** -11.0 pips / $-55.00 | **R:** -1.00
> **Duration:** 26 min | **Close reason:** GREEN
> **Peak pips:** 0.0
> **Setup:** S1


---

## ❌ ❌ USD_CAD BUY loss: -0.1p / $-0.37 (43min)
**Date:** 2026-04-23T22:26:16
**Type:** failure
**Tags:** loss, usdcad, guardian, S15

> [!danger] FAILURE
> **Pair:** USD_CAD | **Direction:** BUY
> **PnL:** -0.1 pips / $-0.37 | **R:** -0.02
> **Duration:** 43 min | **Close reason:** GREEN
> **Peak pips:** 1.2
> **Setup:** S15


---

## ❌ ❌ NZD_USD BUY loss: -8.1p / $-40.50 (55min)
**Date:** 2026-04-23T22:27:03
**Type:** failure
**Tags:** loss, nzdusd, guardian, S15

> [!danger] FAILURE
> **Pair:** NZD_USD | **Direction:** BUY
> **PnL:** -8.1 pips / $-40.50 | **R:** -1.00
> **Duration:** 55 min | **Close reason:** BLACK
> **Peak pips:** 0.8
> **Setup:** S15


---

## ❌ ❌ GBP_USD BUY loss: -8.1p / $-40.50 (1min)
**Date:** 2026-04-23T23:29:33
**Type:** failure
**Tags:** loss, gbpusd, guardian, S1

> [!danger] FAILURE
> **Pair:** GBP_USD | **Direction:** BUY
> **PnL:** -8.1 pips / $-40.50 | **R:** -0.58
> **Duration:** 1 min | **Close reason:** YELLOW
> **Peak pips:** 0.0
> **Setup:** S1


---

## ❌ ❌ EUR_JPY SELL loss: -18.2p / $-57.56 (38min)
**Date:** 2026-04-24T03:57:28
**Type:** failure
**Tags:** loss, eurjpy, guardian, S15

> [!danger] FAILURE
> **Pair:** EUR_JPY | **Direction:** SELL
> **PnL:** -18.2 pips / $-57.56 | **R:** -1.01
> **Duration:** 38 min | **Close reason:** YELLOW
> **Peak pips:** 0.3
> **Setup:** S15


---

## ❌ ❌ AUD_USD SELL loss: -25.8p / $-129.00 (417min)
**Date:** 2026-04-24T07:07:28
**Type:** failure
**Tags:** loss, audusd, guardian, S1

> [!danger] FAILURE
> **Pair:** AUD_USD | **Direction:** SELL
> **PnL:** -25.8 pips / $-129.00 | **R:** -1.00
> **Duration:** 417 min | **Close reason:** BLACK
> **Peak pips:** 0.0
> **Setup:** S1


---

## ❌ ❌ USD_JPY BUY loss: -0.3p / $-0.95 (7min)
**Date:** 2026-04-24T12:57:51
**Type:** failure
**Tags:** loss, usdjpy, guardian, S5

> [!danger] FAILURE
> **Pair:** USD_JPY | **Direction:** BUY
> **PnL:** -0.3 pips / $-0.95 | **R:** -0.01
> **Duration:** 7 min | **Close reason:** YELLOW
> **Peak pips:** 4.2
> **Setup:** S5


---

## 💡 💰 USD_JPY BUY win: +3.4p / $+10.56 (24min)
**Date:** 2026-04-24T13:41:31
**Type:** discovery
**Tags:** win, usdjpy, guardian, S5

> [!tip] DISCOVERY
> **Pair:** USD_JPY | **Direction:** BUY
> **PnL:** +3.4 pips / $+10.56 | **R:** 0.85
> **Duration:** 24 min | **Close reason:** GREEN
> **Peak pips:** 5.0
> **Setup:** S5


---

## 💡 💰 USD_JPY BUY win: +2.2p / $+6.83 (377min)
**Date:** 2026-04-26T17:05:12
**Type:** discovery
**Tags:** win, usdjpy, guardian, S1

> [!tip] DISCOVERY
> **Pair:** USD_JPY | **Direction:** BUY
> **PnL:** +2.2 pips / $+6.83 | **R:** 0.38
> **Duration:** 377 min | **Close reason:** YELLOW
> **Peak pips:** 7.2
> **Setup:** S1


---

## 💡 💰 USD_CHF BUY win: +10.5p / $+66.07 (377min)
**Date:** 2026-04-26T17:05:16
**Type:** discovery
**Tags:** win, usdchf, guardian, S1

> [!tip] DISCOVERY
> **Pair:** USD_CHF | **Direction:** BUY
> **PnL:** +10.5 pips / $+66.07 | **R:** 0.84
> **Duration:** 377 min | **Close reason:** GREEN
> **Peak pips:** 13.9
> **Setup:** S1


---

## ❌ ❌ USD_CHF SELL loss: -1.3p / $-4.18 (7min)
**Date:** 2026-04-26T17:40:58
**Type:** failure
**Tags:** loss, usdchf, guardian, unknown

> [!danger] FAILURE
> **Pair:** USD_CHF | **Direction:** SELL
> **PnL:** -1.3 pips / $-4.18 | **R:** -0.26
> **Duration:** 7 min | **Close reason:** GREEN
> **Peak pips:** 6.3
> **Setup:** unknown


---

## 💡 💰 USD_CHF SELL win: +0.8p / $+5.05 (32min)
**Date:** 2026-04-26T23:03:06
**Type:** discovery
**Tags:** win, usdchf, guardian, S15

> [!tip] DISCOVERY
> **Pair:** USD_CHF | **Direction:** SELL
> **PnL:** +0.8 pips / $+5.05 | **R:** 0.80
> **Duration:** 32 min | **Close reason:** GREEN
> **Peak pips:** 1.6
> **Setup:** S15


---

## 💡 💰 NZD_USD SELL win: +1.2p / $+6.00 (121min)
**Date:** 2026-04-27T13:03:35
**Type:** discovery
**Tags:** win, nzdusd, guardian, S15

> [!tip] DISCOVERY
> **Pair:** NZD_USD | **Direction:** SELL
> **PnL:** +1.2 pips / $+6.00 | **R:** 0.40
> **Duration:** 121 min | **Close reason:** BLACK
> **Peak pips:** 2.3
> **Setup:** S15


---

## ❌ ❌ GBP_USD BUY loss: -4.4p / $-22.00 (2min)
**Date:** 2026-04-27T15:57:49
**Type:** failure
**Tags:** loss, gbpusd, guardian, S15

> [!danger] FAILURE
> **Pair:** GBP_USD | **Direction:** BUY
> **PnL:** -4.4 pips / $-22.00 | **R:** -1.00
> **Duration:** 2 min | **Close reason:** GREEN
> **Peak pips:** 0.0
> **Setup:** S15


---

## ❌ ❌ AUD_USD BUY loss: +0.0p / $+0.00 (14min)
**Date:** 2026-04-27T23:57:15
**Type:** failure
**Tags:** loss, audusd, guardian, unknown

> [!danger] FAILURE
> **Pair:** AUD_USD | **Direction:** BUY
> **PnL:** +0.0 pips / $+0.00 | **R:** 0.00
> **Duration:** 14 min | **Close reason:** GREEN
> **Peak pips:** 1.1
> **Setup:** unknown


---

## 💡 💰 USD_JPY SELL win: +5.9p / $+18.37 (41min)
**Date:** 2026-04-28T00:44:39
**Type:** discovery
**Tags:** win, usdjpy, guardian, unknown

> [!tip] DISCOVERY
> **Pair:** USD_JPY | **Direction:** SELL
> **PnL:** +5.9 pips / $+18.37 | **R:** 0.48
> **Duration:** 41 min | **Close reason:** GREEN
> **Peak pips:** 6.6
> **Setup:** unknown


---

## ❌ ❌ USD_CHF SELL loss: -7.9p / $-50.62 (61min)
**Date:** 2026-04-28T02:39:05
**Type:** failure
**Tags:** loss, usdchf, guardian, S1

> [!danger] FAILURE
> **Pair:** USD_CHF | **Direction:** SELL
> **PnL:** -7.9 pips / $-50.62 | **R:** -1.00
> **Duration:** 61 min | **Close reason:** BLACK
> **Peak pips:** 0.4
> **Setup:** S1


---

## ❌ ❌ USD_JPY SELL loss: -31.8p / $-100.76 (134min)
**Date:** 2026-04-28T03:14:23
**Type:** failure
**Tags:** loss, usdjpy, guardian, S15

> [!danger] FAILURE
> **Pair:** USD_JPY | **Direction:** SELL
> **PnL:** -31.8 pips / $-100.76 | **R:** -1.01
> **Duration:** 134 min | **Close reason:** YELLOW
> **Peak pips:** 2.0
> **Setup:** S15


---

## 💡 💰 USD_CHF SELL win: +0.8p / $+5.02 (10min)
**Date:** 2026-04-28T03:26:32
**Type:** discovery
**Tags:** win, usdchf, guardian, S5

> [!tip] DISCOVERY
> **Pair:** USD_CHF | **Direction:** SELL
> **PnL:** +0.8 pips / $+5.02 | **R:** 0.80
> **Duration:** 10 min | **Close reason:** GREEN
> **Peak pips:** 4.0
> **Setup:** S5


---

## 💡 💰 EUR_USD BUY win: +3.8p / $+19.00 (6min)
**Date:** 2026-04-28T04:19:21
**Type:** discovery
**Tags:** win, eurusd, guardian, S5

> [!tip] DISCOVERY
> **Pair:** EUR_USD | **Direction:** BUY
> **PnL:** +3.8 pips / $+19.00 | **R:** 0.27
> **Duration:** 6 min | **Close reason:** RED
> **Peak pips:** 4.8
> **Setup:** S5


---

## 💡 💰 AUD_USD SELL win: +2.5p / $+12.50 (268min)
**Date:** 2026-04-28T07:17:21
**Type:** discovery
**Tags:** win, audusd, guardian, S5

> [!tip] DISCOVERY
> **Pair:** AUD_USD | **Direction:** SELL
> **PnL:** +2.5 pips / $+12.50 | **R:** 0.35
> **Duration:** 268 min | **Close reason:** YELLOW
> **Peak pips:** 3.1
> **Setup:** S5


---

## 💡 💰 GBP_USD SELL win: +6.7p / $+33.50 (7min)
**Date:** 2026-04-28T07:37:46
**Type:** discovery
**Tags:** win, gbpusd, guardian, S1

> [!tip] DISCOVERY
> **Pair:** GBP_USD | **Direction:** SELL
> **PnL:** +6.7 pips / $+33.50 | **R:** 0.50
> **Duration:** 7 min | **Close reason:** GREEN
> **Peak pips:** 7.5
> **Setup:** S1


---

## ❌ ❌ USD_CHF SELL loss: -19.9p / $-127.09 (169min)
**Date:** 2026-04-28T07:49:08
**Type:** failure
**Tags:** loss, usdchf, guardian, S1

> [!danger] FAILURE
> **Pair:** USD_CHF | **Direction:** SELL
> **PnL:** -19.9 pips / $-127.09 | **R:** -1.00
> **Duration:** 169 min | **Close reason:** YELLOW
> **Peak pips:** 1.1
> **Setup:** S1


---

## ❌ ❌ EUR_USD BUY loss: -19.6p / $-98.00 (169min)
**Date:** 2026-04-28T07:49:41
**Type:** failure
**Tags:** loss, eurusd, guardian, S1

> [!danger] FAILURE
> **Pair:** EUR_USD | **Direction:** BUY
> **PnL:** -19.6 pips / $-98.00 | **R:** -1.00
> **Duration:** 169 min | **Close reason:** YELLOW
> **Peak pips:** 0.6
> **Setup:** S1


---

## ❌ ❌ NZD_USD BUY loss: -5.0p / $-25.00 (4min)
**Date:** 2026-04-28T10:02:42
**Type:** failure
**Tags:** loss, nzdusd, guardian, S5

> [!danger] FAILURE
> **Pair:** NZD_USD | **Direction:** BUY
> **PnL:** -5.0 pips / $-25.00 | **R:** -1.02
> **Duration:** 4 min | **Close reason:** RED
> **Peak pips:** 0.0
> **Setup:** S5


---

## 💡 💰 GBP_JPY BUY win: +0.6p / $+1.86 (24min)
**Date:** 2026-04-28T10:13:34
**Type:** discovery
**Tags:** win, gbpjpy, guardian, S15

> [!tip] DISCOVERY
> **Pair:** GBP_JPY | **Direction:** BUY
> **PnL:** +0.6 pips / $+1.86 | **R:** 0.23
> **Duration:** 24 min | **Close reason:** BLACK
> **Peak pips:** 3.7
> **Setup:** S15


---

## 💡 💰 EUR_JPY BUY win: +0.9p / $+2.79 (6min)
**Date:** 2026-04-28T10:34:00
**Type:** discovery
**Tags:** win, eurjpy, guardian, S15

> [!tip] DISCOVERY
> **Pair:** EUR_JPY | **Direction:** BUY
> **PnL:** +0.9 pips / $+2.79 | **R:** 0.06
> **Duration:** 6 min | **Close reason:** YELLOW
> **Peak pips:** 3.5
> **Setup:** S15


---

## 💡 💰 USD_CHF SELL win: +2.4p / $+15.06 (16min)
**Date:** 2026-04-28T11:38:44
**Type:** discovery
**Tags:** win, usdchf, guardian, S15

> [!tip] DISCOVERY
> **Pair:** USD_CHF | **Direction:** SELL
> **PnL:** +2.4 pips / $+15.06 | **R:** 0.62
> **Duration:** 16 min | **Close reason:** BLACK
> **Peak pips:** 3.2
> **Setup:** S15


---

## ❌ ❌ AUD_USD SELL loss: -24.2p / $-121.00 (110min)
**Date:** 2026-04-28T11:39:32
**Type:** failure
**Tags:** loss, audusd, guardian, S15

> [!danger] FAILURE
> **Pair:** AUD_USD | **Direction:** SELL
> **PnL:** -24.2 pips / $-121.00 | **R:** -1.00
> **Duration:** 110 min | **Close reason:** BLACK
> **Peak pips:** 4.2
> **Setup:** S15


---

## ❌ ❌ GBP_USD SELL loss: -38.7p / $-193.50 (52min)
**Date:** 2026-04-28T13:48:37
**Type:** failure
**Tags:** loss, gbpusd, guardian, S15

> [!danger] FAILURE
> **Pair:** GBP_USD | **Direction:** SELL
> **PnL:** -38.7 pips / $-193.50 | **R:** -1.00
> **Duration:** 52 min | **Close reason:** YELLOW
> **Peak pips:** 1.2
> **Setup:** S15


---

## ❌ ❌ EUR_CHF SELL loss: -2.3p / $-14.72 (271min)
**Date:** 2026-04-28T18:01:48
**Type:** failure
**Tags:** loss, eurchf, guardian, unknown

> [!danger] FAILURE
> **Pair:** EUR_CHF | **Direction:** SELL
> **PnL:** -2.3 pips / $-14.72 | **R:** -0.20
> **Duration:** 271 min | **Close reason:** BLACK
> **Peak pips:** 0.5
> **Setup:** unknown


---

## 💡 💰 AUD_USD SELL win: +2.6p / $+13.00 (52min)
**Date:** 2026-04-29T02:12:57
**Type:** discovery
**Tags:** win, audusd, guardian, S5

> [!tip] DISCOVERY
> **Pair:** AUD_USD | **Direction:** SELL
> **PnL:** +2.6 pips / $+13.00 | **R:** 0.38
> **Duration:** 52 min | **Close reason:** GREEN
> **Peak pips:** 3.2
> **Setup:** S5


---

## 💡 💰 GBP_USD SELL win: +2.3p / $+11.50 (6min)
**Date:** 2026-04-29T02:34:47
**Type:** discovery
**Tags:** win, gbpusd, guardian, S1

> [!tip] DISCOVERY
> **Pair:** GBP_USD | **Direction:** SELL
> **PnL:** +2.3 pips / $+11.50 | **R:** 0.28
> **Duration:** 6 min | **Close reason:** GREEN
> **Peak pips:** 3.1
> **Setup:** S1


---

## 💡 💰 EUR_USD SELL win: +0.8p / $+4.00 (66min)
**Date:** 2026-04-29T04:06:48
**Type:** discovery
**Tags:** win, eurusd, guardian, S15

> [!tip] DISCOVERY
> **Pair:** EUR_USD | **Direction:** SELL
> **PnL:** +0.8 pips / $+4.00 | **R:** 0.80
> **Duration:** 66 min | **Close reason:** GREEN
> **Peak pips:** 2.1
> **Setup:** S15


---

## 💡 💰 AUD_USD SELL win: +3.9p / $+19.50 (51min)
**Date:** 2026-04-29T05:40:49
**Type:** discovery
**Tags:** win, audusd, guardian, S1

> [!tip] DISCOVERY
> **Pair:** AUD_USD | **Direction:** SELL
> **PnL:** +3.9 pips / $+19.50 | **R:** 0.57
> **Duration:** 51 min | **Close reason:** GREEN
> **Peak pips:** 4.4
> **Setup:** S1


---

## 💡 💰 GBP_USD SELL win: +3.6p / $+18.00 (6min)
**Date:** 2026-04-29T09:34:10
**Type:** discovery
**Tags:** win, gbpusd, guardian, S1

> [!tip] DISCOVERY
> **Pair:** GBP_USD | **Direction:** SELL
> **PnL:** +3.6 pips / $+18.00 | **R:** 0.43
> **Duration:** 6 min | **Close reason:** GREEN
> **Peak pips:** 4.5
> **Setup:** S1


---

## 💡 💰 GBP_JPY SELL win: +5.2p / $+16.07 (7min)
**Date:** 2026-04-29T09:48:03
**Type:** discovery
**Tags:** win, gbpjpy, guardian, unknown

> [!tip] DISCOVERY
> **Pair:** GBP_JPY | **Direction:** SELL
> **PnL:** +5.2 pips / $+16.07 | **R:** 0.84
> **Duration:** 7 min | **Close reason:** YELLOW
> **Peak pips:** 7.7
> **Setup:** unknown


---

## ❌ ❌ EUR_JPY SELL loss: -18.7p / $-58.98 (104min)
**Date:** 2026-04-29T10:35:10
**Type:** failure
**Tags:** loss, eurjpy, guardian, S15

> [!danger] FAILURE
> **Pair:** EUR_JPY | **Direction:** SELL
> **PnL:** -18.7 pips / $-58.98 | **R:** -1.01
> **Duration:** 104 min | **Close reason:** BLACK
> **Peak pips:** 1.0
> **Setup:** S15


---

## 💡 💰 USD_CHF SELL win: +1.7p / $+10.65 (11min)
**Date:** 2026-04-29T10:39:14
**Type:** discovery
**Tags:** win, usdchf, guardian, S5

> [!tip] DISCOVERY
> **Pair:** USD_CHF | **Direction:** SELL
> **PnL:** +1.7 pips / $+10.65 | **R:** 0.20
> **Duration:** 11 min | **Close reason:** BLACK
> **Peak pips:** 3.1
> **Setup:** S5


---

## 💡 💰 GBP_JPY SELL win: +4.4p / $+13.58 (103min)
**Date:** 2026-04-29T14:11:18
**Type:** discovery
**Tags:** win, gbpjpy, guardian, S5

> [!tip] DISCOVERY
> **Pair:** GBP_JPY | **Direction:** SELL
> **PnL:** +4.4 pips / $+13.58 | **R:** 0.88
> **Duration:** 103 min | **Close reason:** YELLOW
> **Peak pips:** 6.3
> **Setup:** S5


---

## 💡 💰 EUR_USD BUY win: +1.0p / $+5.00 (4min)
**Date:** 2026-04-29T14:37:24
**Type:** discovery
**Tags:** win, eurusd, guardian, S13

> [!tip] DISCOVERY
> **Pair:** EUR_USD | **Direction:** BUY
> **PnL:** +1.0 pips / $+5.00 | **R:** 1.00
> **Duration:** 4 min | **Close reason:** YELLOW
> **Peak pips:** 5.1
> **Setup:** S13


---

## ❌ ❌ AUD_USD BUY loss: -28.0p / $-140.00 (17min)
**Date:** 2026-04-29T14:37:56
**Type:** failure
**Tags:** loss, audusd, guardian, S1

> [!danger] FAILURE
> **Pair:** AUD_USD | **Direction:** BUY
> **PnL:** -28.0 pips / $-140.00 | **R:** -1.00
> **Duration:** 17 min | **Close reason:** BLACK
> **Peak pips:** 0.0
> **Setup:** S1


---

## ❌ ❌ GBP_USD BUY loss: -36.2p / $-181.00 (17min)
**Date:** 2026-04-29T14:37:58
**Type:** failure
**Tags:** loss, gbpusd, guardian, S1

> [!danger] FAILURE
> **Pair:** GBP_USD | **Direction:** BUY
> **PnL:** -36.2 pips / $-181.00 | **R:** -1.01
> **Duration:** 17 min | **Close reason:** BLACK
> **Peak pips:** 0.0
> **Setup:** S1


---

## 💡 💰 GBP_JPY SELL win: +0.1p / $+0.31 (19min)
**Date:** 2026-04-29T14:48:41
**Type:** discovery
**Tags:** win, gbpjpy, guardian, S1

> [!tip] DISCOVERY
> **Pair:** GBP_JPY | **Direction:** SELL
> **PnL:** +0.1 pips / $+0.31 | **R:** 0.03
> **Duration:** 19 min | **Close reason:** YELLOW
> **Peak pips:** 3.8
> **Setup:** S1


---

## 💡 💰 EUR_USD BUY win: +4.6p / $+23.00 (16min)
**Date:** 2026-04-29T15:17:54
**Type:** discovery
**Tags:** win, eurusd, guardian, S5

> [!tip] DISCOVERY
> **Pair:** EUR_USD | **Direction:** BUY
> **PnL:** +4.6 pips / $+23.00 | **R:** 1.00
> **Duration:** 16 min | **Close reason:** BLACK
> **Peak pips:** 5.8
> **Setup:** S5


---

## ❌ ❌ USD_CHF SELL loss: -0.7p / $-4.47 (31min)
**Date:** 2026-04-29T15:59:32
**Type:** failure
**Tags:** loss, usdchf, guardian, S5

> [!danger] FAILURE
> **Pair:** USD_CHF | **Direction:** SELL
> **PnL:** -0.7 pips / $-4.47 | **R:** -0.09
> **Duration:** 31 min | **Close reason:** BLACK
> **Peak pips:** 1.3
> **Setup:** S5


---

## ❌ ❌ EUR_AUD SELL loss: -1.1p / $-3.95 (33min)
**Date:** 2026-04-29T16:01:20
**Type:** failure
**Tags:** loss, euraud, guardian, S5

> [!danger] FAILURE
> **Pair:** EUR_AUD | **Direction:** SELL
> **PnL:** -1.1 pips / $-3.95 | **R:** -0.08
> **Duration:** 33 min | **Close reason:** BLACK
> **Peak pips:** 2.6
> **Setup:** S5


---

## 💡 💰 AUD_USD BUY win: +1.8p / $+9.00 (90min)
**Date:** 2026-04-29T16:32:09
**Type:** discovery
**Tags:** win, audusd, guardian, S5

> [!tip] DISCOVERY
> **Pair:** AUD_USD | **Direction:** BUY
> **PnL:** +1.8 pips / $+9.00 | **R:** 0.90
> **Duration:** 90 min | **Close reason:** RED
> **Peak pips:** 4.1
> **Setup:** S5


---

## ❌ ❌ EUR_AUD SELL loss: -24.5p / $-88.03 (5min)
**Date:** 2026-04-29T17:06:34
**Type:** failure
**Tags:** loss, euraud, guardian, S5

> [!danger] FAILURE
> **Pair:** EUR_AUD | **Direction:** SELL
> **PnL:** -24.5 pips / $-88.03 | **R:** -0.67
> **Duration:** 5 min | **Close reason:** YELLOW
> **Peak pips:** 0.0
> **Setup:** S5


---

## ❌ ❌ AUD_USD BUY loss: -7.5p / $-37.50 (5min)
**Date:** 2026-04-29T17:06:37
**Type:** failure
**Tags:** loss, audusd, guardian, S5

> [!danger] FAILURE
> **Pair:** AUD_USD | **Direction:** BUY
> **PnL:** -7.5 pips / $-37.50 | **R:** -0.28
> **Duration:** 5 min | **Close reason:** YELLOW
> **Peak pips:** 0.0
> **Setup:** S5


---

## ❌ ❌ GBP_JPY SELL loss: -30.9p / $-97.26 (5min)
**Date:** 2026-04-29T17:06:56
**Type:** failure
**Tags:** loss, gbpjpy, guardian, S1

> [!danger] FAILURE
> **Pair:** GBP_JPY | **Direction:** SELL
> **PnL:** -30.9 pips / $-97.26 | **R:** -0.92
> **Duration:** 5 min | **Close reason:** GREEN
> **Peak pips:** 0.0
> **Setup:** S1


---

## ❌ ❌ EUR_USD BUY loss: -5.5p / $-27.50 (5min)
**Date:** 2026-04-29T17:06:59
**Type:** failure
**Tags:** loss, eurusd, guardian, S5

> [!danger] FAILURE
> **Pair:** EUR_USD | **Direction:** BUY
> **PnL:** -5.5 pips / $-27.50 | **R:** -0.22
> **Duration:** 5 min | **Close reason:** GREEN
> **Peak pips:** 0.0
> **Setup:** S5


---

## 💡 💰 AUD_USD SELL win: +2.9p / $+14.50 (71min)
**Date:** 2026-04-30T01:55:57
**Type:** discovery
**Tags:** win, audusd, guardian, S15

> [!tip] DISCOVERY
> **Pair:** AUD_USD | **Direction:** SELL
> **PnL:** +2.9 pips / $+14.50 | **R:** 0.49
> **Duration:** 71 min | **Close reason:** GREEN
> **Peak pips:** 3.2
> **Setup:** S15


---

## ❌ ❌ AUD_JPY SELL loss: -44.5p / $-140.01 (221min)
**Date:** 2026-04-30T03:12:46
**Type:** failure
**Tags:** loss, audjpy, guardian, S15

> [!danger] FAILURE
> **Pair:** AUD_JPY | **Direction:** SELL
> **PnL:** -44.5 pips / $-140.01 | **R:** -1.00
> **Duration:** 221 min | **Close reason:** YELLOW
> **Peak pips:** 0.0
> **Setup:** S15


---

## ❌ ❌ AUD_USD SELL loss: -26.8p / $-134.00 (112min)
**Date:** 2026-04-30T04:04:08
**Type:** failure
**Tags:** loss, audusd, guardian, S15

> [!danger] FAILURE
> **Pair:** AUD_USD | **Direction:** SELL
> **PnL:** -26.8 pips / $-134.00 | **R:** -1.00
> **Duration:** 112 min | **Close reason:** YELLOW
> **Peak pips:** 0.0
> **Setup:** S15


---

## 💡 💰 USD_CAD SELL win: +4.3p / $+15.58 (10min)
**Date:** 2026-04-30T05:31:32
**Type:** discovery
**Tags:** win, usdcad, guardian, S15

> [!tip] DISCOVERY
> **Pair:** USD_CAD | **Direction:** SELL
> **PnL:** +4.3 pips / $+15.58 | **R:** 0.67
> **Duration:** 10 min | **Close reason:** GREEN
> **Peak pips:** 5.3
> **Setup:** S15


---

## 💡 💰 USD_CAD SELL win: +1.0p / $+3.62 (41min)
**Date:** 2026-04-30T06:27:41
**Type:** discovery
**Tags:** win, usdcad, guardian, S15

> [!tip] DISCOVERY
> **Pair:** USD_CAD | **Direction:** SELL
> **PnL:** +1.0 pips / $+3.62 | **R:** 1.00
> **Duration:** 41 min | **Close reason:** GREEN
> **Peak pips:** 2.8
> **Setup:** S15


---

## 💡 💰 GBP_JPY SELL win: +19.2p / $+59.81 (14min)
**Date:** 2026-04-30T06:28:44
**Type:** discovery
**Tags:** win, gbpjpy, guardian, S5

> [!tip] DISCOVERY
> **Pair:** GBP_JPY | **Direction:** SELL
> **PnL:** +19.2 pips / $+59.81 | **R:** 0.80
> **Duration:** 14 min | **Close reason:** GREEN
> **Peak pips:** 21.9
> **Setup:** S5


---

## 💡 💰 AUD_JPY SELL win: +71.9p / $+225.23 (42min)
**Date:** 2026-04-30T06:31:48
**Type:** discovery
**Tags:** win, audjpy, guardian, S1

> [!tip] DISCOVERY
> **Pair:** AUD_JPY | **Direction:** SELL
> **PnL:** +71.9 pips / $+225.23 | **R:** 8.36
> **Duration:** 42 min | **Close reason:** GREEN
> **Peak pips:** 69.6
> **Setup:** S1


---

## 💡 💰 AUD_JPY SELL win: +8.2p / $+25.79 (20min)
**Date:** 2026-04-30T07:09:19
**Type:** discovery
**Tags:** win, audjpy, guardian, S1

> [!tip] DISCOVERY
> **Pair:** AUD_JPY | **Direction:** SELL
> **PnL:** +8.2 pips / $+25.79 | **R:** 0.08
> **Duration:** 20 min | **Close reason:** GREEN
> **Peak pips:** 34.6
> **Setup:** S1


---

## 💡 💰 EUR_CHF SELL win: +17.9p / $+226.51 (27min)
**Date:** 2026-04-30T10:15:05
**Type:** discovery
**Tags:** win, eurchf, guardian, S5

> [!tip] DISCOVERY
> **Pair:** EUR_CHF | **Direction:** SELL
> **PnL:** +17.9 pips / $+226.51 | **R:** 0.63
> **Duration:** 27 min | **Close reason:** GREEN
> **Peak pips:** 18.7
> **Setup:** S5


---

## 💡 💰 USD_CAD SELL win: +4.1p / $+29.84 (150min)
**Date:** 2026-04-30T14:15:07
**Type:** discovery
**Tags:** win, usdcad, guardian, S1

> [!tip] DISCOVERY
> **Pair:** USD_CAD | **Direction:** SELL
> **PnL:** +4.1 pips / $+29.84 | **R:** 0.22
> **Duration:** 150 min | **Close reason:** GREEN
> **Peak pips:** 5.0
> **Setup:** S1


---

## 💡 💰 EUR_AUD SELL win: +7.1p / $+50.69 (55min)
**Date:** 2026-05-01T13:28:30
**Type:** discovery
**Tags:** win, euraud, guardian, S1

> [!tip] DISCOVERY
> **Pair:** EUR_AUD | **Direction:** SELL
> **PnL:** +7.1 pips / $+50.69 | **R:** 0.99
> **Duration:** 55 min | **Close reason:** GREEN
> **Peak pips:** 11.0
> **Setup:** S1


---

## 💡 💰 EUR_USD SELL win: +1.0p / $+10.00 (5min)
**Date:** 2026-05-04T06:18:53
**Type:** discovery
**Tags:** win, eurusd, guardian, S1

> [!tip] DISCOVERY
> **Pair:** EUR_USD | **Direction:** SELL
> **PnL:** +1.0 pips / $+10.00 | **R:** 1.00
> **Duration:** 5 min | **Close reason:** GREEN
> **Peak pips:** 7.3
> **Setup:** S1


---

## ❌ ❌ NZD_USD SELL loss: -13.2p / $-132.00 (16min)
**Date:** 2026-05-04T06:31:02
**Type:** failure
**Tags:** loss, nzdusd, guardian, S5

> [!danger] FAILURE
> **Pair:** NZD_USD | **Direction:** SELL
> **PnL:** -13.2 pips / $-132.00 | **R:** -0.42
> **Duration:** 16 min | **Close reason:** GREEN
> **Peak pips:** 0.3
> **Setup:** S5


---

## 💡 💰 EUR_USD SELL win: +3.5p / $+35.00 (49min)
**Date:** 2026-05-04T07:54:30
**Type:** discovery
**Tags:** win, eurusd, guardian, S5

> [!tip] DISCOVERY
> **Pair:** EUR_USD | **Direction:** SELL
> **PnL:** +3.5 pips / $+35.00 | **R:** 0.36
> **Duration:** 49 min | **Close reason:** GREEN
> **Peak pips:** 4.4
> **Setup:** S5


---

## 💡 💰 NZD_USD SELL win: +6.8p / $+68.00 (21min)
**Date:** 2026-05-04T12:08:44
**Type:** discovery
**Tags:** win, nzdusd, guardian, S1

> [!tip] DISCOVERY
> **Pair:** NZD_USD | **Direction:** SELL
> **PnL:** +6.8 pips / $+68.00 | **R:** 0.99
> **Duration:** 21 min | **Close reason:** GREEN
> **Peak pips:** 8.3
> **Setup:** S1


---

## 💡 💰 EUR_USD SELL win: +3.9p / $+39.00 (6min)
**Date:** 2026-05-04T12:09:18
**Type:** discovery
**Tags:** win, eurusd, guardian, S15

> [!tip] DISCOVERY
> **Pair:** EUR_USD | **Direction:** SELL
> **PnL:** +3.9 pips / $+39.00 | **R:** 0.41
> **Duration:** 6 min | **Close reason:** GREEN
> **Peak pips:** 4.7
> **Setup:** S15


---

## ❌ ❌ AUD_JPY SELL loss: -12.3p / $-79.00 (58min)
**Date:** 2026-05-04T13:05:33
**Type:** failure
**Tags:** loss, audjpy, guardian, S5

> [!danger] FAILURE
> **Pair:** AUD_JPY | **Direction:** SELL
> **PnL:** -12.3 pips / $-79.00 | **R:** -0.30
> **Duration:** 58 min | **Close reason:** GREEN
> **Peak pips:** 4.1
> **Setup:** S5


---

## 💡 💰 AUD_USD SELL win: +3.5p / $+35.00 (535min)
**Date:** 2026-05-04T21:46:14
**Type:** discovery
**Tags:** win, audusd, guardian, S5

> [!tip] DISCOVERY
> **Pair:** AUD_USD | **Direction:** SELL
> **PnL:** +3.5 pips / $+35.00 | **R:** 0.36
> **Duration:** 535 min | **Close reason:** GREEN
> **Peak pips:** 5.5
> **Setup:** S5


---

## 💡 💰 USD_CHF SELL win: +1.0p / $+12.66 (5min)
**Date:** 2026-05-05T19:05:35
**Type:** discovery
**Tags:** win, usdchf, guardian, S1

> [!tip] DISCOVERY
> **Pair:** USD_CHF | **Direction:** SELL
> **PnL:** +1.0 pips / $+12.66 | **R:** 1.00
> **Duration:** 5 min | **Close reason:** GREEN
> **Peak pips:** 2.1
> **Setup:** S1


---

## 💡 💰 USD_CHF SELL win: +3.0p / $+38.01 (6min)
**Date:** 2026-05-05T20:36:06
**Type:** discovery
**Tags:** win, usdchf, guardian, S5

> [!tip] DISCOVERY
> **Pair:** USD_CHF | **Direction:** SELL
> **PnL:** +3.0 pips / $+38.01 | **R:** 0.44
> **Duration:** 6 min | **Close reason:** GREEN
> **Peak pips:** 3.9
> **Setup:** S5


---

## 💡 💰 USD_CHF SELL win: +1.0p / $+12.67 (22min)
**Date:** 2026-05-05T21:30:19
**Type:** discovery
**Tags:** win, usdchf, guardian, S5

> [!tip] DISCOVERY
> **Pair:** USD_CHF | **Direction:** SELL
> **PnL:** +1.0 pips / $+12.67 | **R:** 1.00
> **Duration:** 22 min | **Close reason:** GREEN
> **Peak pips:** 2.8
> **Setup:** S5


---

## 💡 💰 GBP_USD BUY win: +6.2p / $+62.00 (280min)
**Date:** 2026-05-06T00:30:26
**Type:** discovery
**Tags:** win, gbpusd, guardian, S1

> [!tip] DISCOVERY
> **Pair:** GBP_USD | **Direction:** BUY
> **PnL:** +6.2 pips / $+62.00 | **R:** 0.89
> **Duration:** 280 min | **Close reason:** YELLOW
> **Peak pips:** 8.2
> **Setup:** S1


---

## 💡 💰 USD_CAD SELL win: +4.6p / $+33.51 (150min)
**Date:** 2026-05-06T00:39:05
**Type:** discovery
**Tags:** win, usdcad, guardian, S1

> [!tip] DISCOVERY
> **Pair:** USD_CAD | **Direction:** SELL
> **PnL:** +4.6 pips / $+33.51 | **R:** 1.00
> **Duration:** 150 min | **Close reason:** GREEN
> **Peak pips:** 5.8
> **Setup:** S1


---

## ❌ ❌ USD_CHF SELL loss: -11.1p / $-143.97 (53min)
**Date:** 2026-05-06T08:00:55
**Type:** failure
**Tags:** loss, usdchf, guardian, S5

> [!danger] FAILURE
> **Pair:** USD_CHF | **Direction:** SELL
> **PnL:** -11.1 pips / $-143.97 | **R:** -0.27
> **Duration:** 53 min | **Close reason:** GREEN
> **Peak pips:** 0.5
> **Setup:** S5


---

## ❌ ❌ AUD_JPY SELL loss: -12.3p / $-79.46 (68min)
**Date:** 2026-05-06T22:59:36
**Type:** failure
**Tags:** loss, audjpy, guardian, S15

> [!danger] FAILURE
> **Pair:** AUD_JPY | **Direction:** SELL
> **PnL:** -12.3 pips / $-79.46 | **R:** -0.49
> **Duration:** 68 min | **Close reason:** YELLOW
> **Peak pips:** 0.0
> **Setup:** S15


---

## ❌ ❌ NZD_USD BUY loss: -16.0p / $-160.00 (16min)
**Date:** 2026-05-07T11:30:59
**Type:** failure
**Tags:** loss, nzdusd, guardian, S15

> [!danger] FAILURE
> **Pair:** NZD_USD | **Direction:** BUY
> **PnL:** -16.0 pips / $-160.00 | **R:** -0.59
> **Duration:** 16 min | **Close reason:** GREEN
> **Peak pips:** 1.9
> **Setup:** S15


---

## ❌ ❌ EUR_USD BUY loss: -10.2p / $-102.00 (16min)
**Date:** 2026-05-07T11:31:03
**Type:** failure
**Tags:** loss, eurusd, guardian, S15

> [!danger] FAILURE
> **Pair:** EUR_USD | **Direction:** BUY
> **PnL:** -10.2 pips / $-102.00 | **R:** -0.38
> **Duration:** 16 min | **Close reason:** GREEN
> **Peak pips:** 2.5
> **Setup:** S15


---

## 💡 💰 NZD_USD SELL win: +2.4p / $+24.00 (9min)
**Date:** 2026-05-07T18:05:47
**Type:** discovery
**Tags:** win, nzdusd, guardian, S1

> [!tip] DISCOVERY
> **Pair:** NZD_USD | **Direction:** SELL
> **PnL:** +2.4 pips / $+24.00 | **R:** 0.25
> **Duration:** 9 min | **Close reason:** GREEN
> **Peak pips:** 4.0
> **Setup:** S1


---

## ❌ ❌ AUD_JPY SELL loss: -26.7p / $-171.88 (239min)
**Date:** 2026-05-08T00:53:46
**Type:** failure
**Tags:** loss, audjpy, guardian, S1

> [!danger] FAILURE
> **Pair:** AUD_JPY | **Direction:** SELL
> **PnL:** -26.7 pips / $-171.88 | **R:** -1.00
> **Duration:** 239 min | **Close reason:** YELLOW
> **Peak pips:** 5.0
> **Setup:** S1


---

## ❌ ❌ AUD_USD SELL loss: -30.4p / $-304.00 (472min)
**Date:** 2026-05-08T04:46:01
**Type:** failure
**Tags:** loss, audusd, guardian, S15

> [!danger] FAILURE
> **Pair:** AUD_USD | **Direction:** SELL
> **PnL:** -30.4 pips / $-304.00 | **R:** -0.79
> **Duration:** 472 min | **Close reason:** GREEN
> **Peak pips:** 3.3
> **Setup:** S15


---

## 💡 💰 GBP_JPY BUY win: +29.3p / $+92.55 (111min)
**Date:** 2026-05-08T05:00:40
**Type:** discovery
**Tags:** win, gbpjpy, guardian, S1

> [!tip] DISCOVERY
> **Pair:** GBP_JPY | **Direction:** BUY
> **PnL:** +29.3 pips / $+92.55 | **R:** 0.91
> **Duration:** 111 min | **Close reason:** GREEN
> **Peak pips:** 31.1
> **Setup:** S1


---

## ❌ ❌ AUD_JPY BUY loss: -7.7p / $-24.80 (32min)
**Date:** 2026-05-08T07:48:38
**Type:** failure
**Tags:** loss, audjpy, guardian, S5

> [!danger] FAILURE
> **Pair:** AUD_JPY | **Direction:** BUY
> **PnL:** -7.7 pips / $-24.80 | **R:** -0.35
> **Duration:** 32 min | **Close reason:** GREEN
> **Peak pips:** 0.1
> **Setup:** S5


---

## ❌ ❌ GBP_USD BUY loss: -5.1p / $-25.50 (139min)
**Date:** 2026-05-08T09:04:35
**Type:** failure
**Tags:** loss, gbpusd, guardian, S5

> [!danger] FAILURE
> **Pair:** GBP_USD | **Direction:** BUY
> **PnL:** -5.1 pips / $-25.50 | **R:** -0.15
> **Duration:** 139 min | **Close reason:** GREEN
> **Peak pips:** 5.3
> **Setup:** S5


---

## 💡 💰 EUR_USD BUY win: +4.7p / $+23.50 (195min)
**Date:** 2026-05-08T10:00:36
**Type:** discovery
**Tags:** win, eurusd, guardian, S5

> [!tip] DISCOVERY
> **Pair:** EUR_USD | **Direction:** BUY
> **PnL:** +4.7 pips / $+23.50 | **R:** 0.57
> **Duration:** 195 min | **Close reason:** GREEN
> **Peak pips:** 14.8
> **Setup:** S5


---

## 💡 💰 EUR_JPY BUY win: +5.1p / $+16.12 (306min)
**Date:** 2026-05-08T11:51:41
**Type:** discovery
**Tags:** win, eurjpy, guardian, S15

> [!tip] DISCOVERY
> **Pair:** EUR_JPY | **Direction:** BUY
> **PnL:** +5.1 pips / $+16.12 | **R:** 0.93
> **Duration:** 306 min | **Close reason:** GREEN
> **Peak pips:** 6.9
> **Setup:** S15


---

## ❌ ❌ EUR_GBP SELL loss: -33.2p / $-228.56 (3221min)
**Date:** 2026-05-10T17:05:04
**Type:** failure
**Tags:** loss, eurgbp, guardian, S1

> [!danger] FAILURE
> **Pair:** EUR_GBP | **Direction:** SELL
> **PnL:** -33.2 pips / $-228.56 | **R:** -2.91
> **Duration:** 3221 min | **Close reason:** GREEN
> **Peak pips:** 1.2
> **Setup:** S1


---

## ❌ ❌ USD_CAD BUY loss: -22.5p / $-83.04 (130min)
**Date:** 2026-05-10T20:31:37
**Type:** failure
**Tags:** loss, usdcad, guardian, S16

> [!danger] FAILURE
> **Pair:** USD_CAD | **Direction:** BUY
> **PnL:** -22.5 pips / $-83.04 | **R:** -0.41
> **Duration:** 130 min | **Close reason:** GREEN
> **Peak pips:** 0.0
> **Setup:** S16


---

## ❌ ❌ USD_JPY BUY loss: -1.9p / $-6.11 (46min)
**Date:** 2026-05-11T00:20:03
**Type:** failure
**Tags:** loss, usdjpy, guardian, C9_BEAR_EXP_PULLBACK

> [!danger] FAILURE
> **Pair:** USD_JPY | **Direction:** BUY
> **PnL:** -1.9 pips / $-6.11 | **R:** -0.05
> **Duration:** 46 min | **Close reason:** GREEN
> **Peak pips:** 1.5
> **Setup:** C9_BEAR_EXP_PULLBACK


---

## ❌ ❌ EUR_CHF BUY loss: -1.8p / $-11.66 (155min)
**Date:** 2026-05-11T01:03:43
**Type:** failure
**Tags:** loss, eurchf, guardian, unknown

> [!danger] FAILURE
> **Pair:** EUR_CHF | **Direction:** BUY
> **PnL:** -1.8 pips / $-11.66 | **R:** -0.22
> **Duration:** 155 min | **Close reason:** GREEN
> **Peak pips:** 0.6
> **Setup:** unknown


---

## ❌ ❌ GBP_USD SELL loss: -18.7p / $-93.50 (80min)
**Date:** 2026-05-11T02:59:39
**Type:** failure
**Tags:** loss, gbpusd, guardian, C5_FIB_REACTION

> [!danger] FAILURE
> **Pair:** GBP_USD | **Direction:** SELL
> **PnL:** -18.7 pips / $-93.50 | **R:** -1.01
> **Duration:** 80 min | **Close reason:** YELLOW
> **Peak pips:** 0.5
> **Setup:** C5_FIB_REACTION


---

## 💡 💰 EUR_JPY BUY win: +4.0p / $+12.61 (286min)
**Date:** 2026-05-11T03:24:10
**Type:** discovery
**Tags:** win, eurjpy, guardian, C9_BEAR_EXP_PULLBACK

> [!tip] DISCOVERY
> **Pair:** EUR_JPY | **Direction:** BUY
> **PnL:** +4.0 pips / $+12.61 | **R:** 0.93
> **Duration:** 286 min | **Close reason:** GREEN
> **Peak pips:** 5.4
> **Setup:** C9_BEAR_EXP_PULLBACK


---

## 💡 💰 AUD_JPY BUY win: +5.6p / $+17.64 (341min)
**Date:** 2026-05-11T04:11:25
**Type:** discovery
**Tags:** win, audjpy, guardian, C12_CASCADE_CONTINUATION

> [!tip] DISCOVERY
> **Pair:** AUD_JPY | **Direction:** BUY
> **PnL:** +5.6 pips / $+17.64 | **R:** 0.73
> **Duration:** 341 min | **Close reason:** GREEN
> **Peak pips:** 10.7
> **Setup:** C12_CASCADE_CONTINUATION


---

## ❌ ❌ NZD_USD SELL loss: -15.2p / $-76.00 (211min)
**Date:** 2026-05-11T04:18:54
**Type:** failure
**Tags:** loss, nzdusd, guardian, C4_CHART_PATTERN_BREAK

> [!danger] FAILURE
> **Pair:** NZD_USD | **Direction:** SELL
> **PnL:** -15.2 pips / $-76.00 | **R:** -1.00
> **Duration:** 211 min | **Close reason:** BLACK
> **Peak pips:** 0.0
> **Setup:** C4_CHART_PATTERN_BREAK


---

## ❌ ❌ GBP_JPY BUY loss: -3.5p / $-11.25 (61min)
**Date:** 2026-05-11T05:22:47
**Type:** failure
**Tags:** loss, gbpjpy, guardian, C4_CHART_PATTERN_BREAK

> [!danger] FAILURE
> **Pair:** GBP_JPY | **Direction:** BUY
> **PnL:** -3.5 pips / $-11.25 | **R:** -0.07
> **Duration:** 61 min | **Close reason:** GREEN
> **Peak pips:** 2.8
> **Setup:** C4_CHART_PATTERN_BREAK


---

## 💡 💰 AUD_JPY BUY win: +4.1p / $+12.92 (59min)
**Date:** 2026-05-11T06:32:45
**Type:** discovery
**Tags:** win, audjpy, guardian, S16

> [!tip] DISCOVERY
> **Pair:** AUD_JPY | **Direction:** BUY
> **PnL:** +4.1 pips / $+12.92 | **R:** 0.82
> **Duration:** 59 min | **Close reason:** GREEN
> **Peak pips:** 6.2
> **Setup:** S16


---

## 💡 💰 EUR_JPY BUY win: +8.0p / $+25.21 (216min)
**Date:** 2026-05-11T09:09:43
**Type:** discovery
**Tags:** win, eurjpy, guardian, C11_BIG_MOVE

> [!tip] DISCOVERY
> **Pair:** EUR_JPY | **Direction:** BUY
> **PnL:** +8.0 pips / $+25.21 | **R:** 0.98
> **Duration:** 216 min | **Close reason:** GREEN
> **Peak pips:** 9.6
> **Setup:** C11_BIG_MOVE


---

## 💡 💰 EUR_AUD SELL win: +1.3p / $+4.67 (18min)
**Date:** 2026-05-11T10:58:59
**Type:** discovery
**Tags:** win, euraud, guardian, C5_FIB_REACTION

> [!tip] DISCOVERY
> **Pair:** EUR_AUD | **Direction:** SELL
> **PnL:** +1.3 pips / $+4.67 | **R:** 0.15
> **Duration:** 18 min | **Close reason:** GREEN
> **Peak pips:** 3.3
> **Setup:** C5_FIB_REACTION


---

## ❌ ❌ EUR_CHF BUY loss: -13.9p / $-90.32 (326min)
**Date:** 2026-05-11T11:00:16
**Type:** failure
**Tags:** loss, eurchf, guardian, C12_CASCADE_CONTINUATION

> [!danger] FAILURE
> **Pair:** EUR_CHF | **Direction:** BUY
> **PnL:** -13.9 pips / $-90.32 | **R:** -1.00
> **Duration:** 326 min | **Close reason:** YELLOW
> **Peak pips:** 0.0
> **Setup:** C12_CASCADE_CONTINUATION


---

## 💡 💰 EUR_AUD SELL win: +2.2p / $+7.91 (18min)
**Date:** 2026-05-11T11:25:31
**Type:** discovery
**Tags:** win, euraud, guardian, C12_CASCADE_CONTINUATION

> [!tip] DISCOVERY
> **Pair:** EUR_AUD | **Direction:** SELL
> **PnL:** +2.2 pips / $+7.91 | **R:** 0.28
> **Duration:** 18 min | **Close reason:** GREEN
> **Peak pips:** 3.7
> **Setup:** C12_CASCADE_CONTINUATION


---

## ❌ ❌ NZD_USD BUY loss: -4.7p / $-23.50 (108min)
**Date:** 2026-05-11T12:56:06
**Type:** failure
**Tags:** loss, nzdusd, guardian, S13

> [!danger] FAILURE
> **Pair:** NZD_USD | **Direction:** BUY
> **PnL:** -4.7 pips / $-23.50 | **R:** -0.31
> **Duration:** 108 min | **Close reason:** GREEN
> **Peak pips:** 2.8
> **Setup:** S13


---

## ❌ ❌ AUD_USD BUY loss: -3.6p / $-18.00 (231min)
**Date:** 2026-05-11T13:08:01
**Type:** failure
**Tags:** loss, audusd, guardian, C12_CASCADE_CONTINUATION

> [!danger] FAILURE
> **Pair:** AUD_USD | **Direction:** BUY
> **PnL:** -3.6 pips / $-18.00 | **R:** -0.26
> **Duration:** 231 min | **Close reason:** YELLOW
> **Peak pips:** 7.7
> **Setup:** C12_CASCADE_CONTINUATION


---

## 💡 💰 AUD_JPY BUY win: +3.9p / $+12.29 (157min)
**Date:** 2026-05-11T13:38:50
**Type:** discovery
**Tags:** win, audjpy, guardian, S16

> [!tip] DISCOVERY
> **Pair:** AUD_JPY | **Direction:** BUY
> **PnL:** +3.9 pips / $+12.29 | **R:** 0.38
> **Duration:** 157 min | **Close reason:** GREEN
> **Peak pips:** 7.2
> **Setup:** S16


---

## 💡 💰 EUR_JPY BUY win: +3.9p / $+12.28 (291min)
**Date:** 2026-05-11T15:26:36
**Type:** discovery
**Tags:** win, eurjpy, guardian, C12_CASCADE_CONTINUATION

> [!tip] DISCOVERY
> **Pair:** EUR_JPY | **Direction:** BUY
> **PnL:** +3.9 pips / $+12.28 | **R:** 0.91
> **Duration:** 291 min | **Close reason:** GREEN
> **Peak pips:** 5.4
> **Setup:** C12_CASCADE_CONTINUATION


---

## ❌ ❌ EUR_CHF BUY loss: -9.3p / $-60.36 (45min)
**Date:** 2026-05-11T17:05:08
**Type:** failure
**Tags:** loss, eurchf, guardian, C12_CASCADE_CONTINUATION

> [!danger] FAILURE
> **Pair:** EUR_CHF | **Direction:** BUY
> **PnL:** -9.3 pips / $-60.36 | **R:** -1.07
> **Duration:** 45 min | **Close reason:** GREEN
> **Peak pips:** 1.5
> **Setup:** C12_CASCADE_CONTINUATION


---

## ❌ ❌ EUR_JPY BUY loss: -8.0p / $-25.70 (93min)
**Date:** 2026-05-11T17:11:01
**Type:** failure
**Tags:** loss, eurjpy, guardian, C12_CASCADE_CONTINUATION

> [!danger] FAILURE
> **Pair:** EUR_JPY | **Direction:** BUY
> **PnL:** -8.0 pips / $-25.70 | **R:** -0.19
> **Duration:** 93 min | **Close reason:** GREEN
> **Peak pips:** 2.6
> **Setup:** C12_CASCADE_CONTINUATION


---

## ❌ ❌ EUR_JPY BUY loss: -1.6p / $-5.14 (79min)
**Date:** 2026-05-11T18:39:53
**Type:** failure
**Tags:** loss, eurjpy, guardian, C11_BIG_MOVE

> [!danger] FAILURE
> **Pair:** EUR_JPY | **Direction:** BUY
> **PnL:** -1.6 pips / $-5.14 | **R:** -0.04
> **Duration:** 79 min | **Close reason:** GREEN
> **Peak pips:** 1.1
> **Setup:** C11_BIG_MOVE


---

## ❌ ❌ EUR_USD BUY loss: -1.4p / $-7.00 (515min)
**Date:** 2026-05-11T18:54:03
**Type:** failure
**Tags:** loss, eurusd, guardian, C9_BEAR_EXP_PULLBACK

> [!danger] FAILURE
> **Pair:** EUR_USD | **Direction:** BUY
> **PnL:** -1.4 pips / $-7.00 | **R:** -0.07
> **Duration:** 515 min | **Close reason:** GREEN
> **Peak pips:** 1.3
> **Setup:** C9_BEAR_EXP_PULLBACK


---

## ❌ ❌ GBP_JPY BUY loss: -48.9p / $-156.97 (446min)
**Date:** 2026-05-11T20:47:54
**Type:** failure
**Tags:** loss, gbpjpy, guardian, S16

> [!danger] FAILURE
> **Pair:** GBP_JPY | **Direction:** BUY
> **PnL:** -48.9 pips / $-156.97 | **R:** -0.62
> **Duration:** 446 min | **Close reason:** YELLOW
> **Peak pips:** 0.0
> **Setup:** S16


---

## 💡 💰 USD_JPY BUY win: +13.3p / $+41.79 (26min)
**Date:** 2026-05-11T21:29:00
**Type:** discovery
**Tags:** win, usdjpy, guardian, C12_CASCADE_CONTINUATION

> [!tip] DISCOVERY
> **Pair:** USD_JPY | **Direction:** BUY
> **PnL:** +13.3 pips / $+41.79 | **R:** 1.09
> **Duration:** 26 min | **Close reason:** GREEN
> **Peak pips:** 11.8
> **Setup:** C12_CASCADE_CONTINUATION


---

## 💡 💰 USD_JPY BUY win: +6.2p / $+19.47 (77min)
**Date:** 2026-05-11T22:45:43
**Type:** discovery
**Tags:** win, usdjpy, guardian, C12_CASCADE_CONTINUATION

> [!tip] DISCOVERY
> **Pair:** USD_JPY | **Direction:** BUY
> **PnL:** +6.2 pips / $+19.47 | **R:** 0.51
> **Duration:** 77 min | **Close reason:** GREEN
> **Peak pips:** 8.6
> **Setup:** C12_CASCADE_CONTINUATION


---

## 💡 💰 GBP_USD SELL win: +2.9p / $+14.50 (67min)
**Date:** 2026-05-11T23:36:29
**Type:** discovery
**Tags:** win, gbpusd, guardian, C12_CASCADE_CONTINUATION

> [!tip] DISCOVERY
> **Pair:** GBP_USD | **Direction:** SELL
> **PnL:** +2.9 pips / $+14.50 | **R:** 0.32
> **Duration:** 67 min | **Close reason:** GREEN
> **Peak pips:** 3.8
> **Setup:** C12_CASCADE_CONTINUATION


---

## 💡 💰 USD_JPY BUY win: +4.0p / $+12.56 (104min)
**Date:** 2026-05-12T01:11:25
**Type:** discovery
**Tags:** win, usdjpy, guardian, C12_CASCADE_CONTINUATION

> [!tip] DISCOVERY
> **Pair:** USD_JPY | **Direction:** BUY
> **PnL:** +4.0 pips / $+12.56 | **R:** 0.87
> **Duration:** 104 min | **Close reason:** GREEN
> **Peak pips:** 5.7
> **Setup:** C12_CASCADE_CONTINUATION


---

## ❌ ❌ AUD_JPY BUY loss: -22.1p / $-70.91 (54min)
**Date:** 2026-05-12T01:56:08
**Type:** failure
**Tags:** loss, audjpy, guardian, C12_CASCADE_CONTINUATION

> [!danger] FAILURE
> **Pair:** AUD_JPY | **Direction:** BUY
> **PnL:** -22.1 pips / $-70.91 | **R:** -1.18
> **Duration:** 54 min | **Close reason:** GREEN
> **Peak pips:** 2.6
> **Setup:** C12_CASCADE_CONTINUATION


---

## 💡 💰 GBP_USD SELL win: +5.0p / $+25.00 (6min)
**Date:** 2026-05-12T02:20:25
**Type:** discovery
**Tags:** win, gbpusd, guardian, C5_FIB_REACTION

> [!tip] DISCOVERY
> **Pair:** GBP_USD | **Direction:** SELL
> **PnL:** +5.0 pips / $+25.00 | **R:** 0.44
> **Duration:** 6 min | **Close reason:** GREEN
> **Peak pips:** 5.9
> **Setup:** C5_FIB_REACTION


---

## 💡 💰 GBP_JPY SELL win: +11.2p / $+35.19 (6min)
**Date:** 2026-05-12T03:08:00
**Type:** discovery
**Tags:** win, gbpjpy, guardian, C4_CHART_PATTERN_BREAK

> [!tip] DISCOVERY
> **Pair:** GBP_JPY | **Direction:** SELL
> **PnL:** +11.2 pips / $+35.19 | **R:** 0.72
> **Duration:** 6 min | **Close reason:** GREEN
> **Peak pips:** 13.2
> **Setup:** C4_CHART_PATTERN_BREAK


---

## 💡 💰 EUR_USD SELL win: +5.0p / $+25.00 (43min)
**Date:** 2026-05-12T04:37:52
**Type:** discovery
**Tags:** win, eurusd, guardian, C9_BEAR_EXP_PULLBACK

> [!tip] DISCOVERY
> **Pair:** EUR_USD | **Direction:** SELL
> **PnL:** +5.0 pips / $+25.00 | **R:** 0.58
> **Duration:** 43 min | **Close reason:** GREEN
> **Peak pips:** 5.8
> **Setup:** C9_BEAR_EXP_PULLBACK


---

## ❌ ❌ EUR_AUD BUY loss: -27.2p / $-99.26 (170min)
**Date:** 2026-05-12T06:52:28
**Type:** failure
**Tags:** loss, euraud, guardian, S16

> [!danger] FAILURE
> **Pair:** EUR_AUD | **Direction:** BUY
> **PnL:** -27.2 pips / $-99.26 | **R:** -1.00
> **Duration:** 170 min | **Close reason:** YELLOW
> **Peak pips:** 1.8
> **Setup:** S16


---

## 💡 💰 EUR_USD SELL win: +2.8p / $+14.00 (124min)
**Date:** 2026-05-12T06:58:50
**Type:** discovery
**Tags:** win, eurusd, guardian, C9_BEAR_EXP_PULLBACK

> [!tip] DISCOVERY
> **Pair:** EUR_USD | **Direction:** SELL
> **PnL:** +2.8 pips / $+14.00 | **R:** 0.38
> **Duration:** 124 min | **Close reason:** GREEN
> **Peak pips:** 3.6
> **Setup:** C9_BEAR_EXP_PULLBACK


---

## 💡 💰 USD_CHF BUY win: +4.4p / $+27.88 (127min)
**Date:** 2026-05-12T06:59:22
**Type:** discovery
**Tags:** win, usdchf, guardian, C4_CHART_PATTERN_BREAK

> [!tip] DISCOVERY
> **Pair:** USD_CHF | **Direction:** BUY
> **PnL:** +4.4 pips / $+27.88 | **R:** 0.43
> **Duration:** 127 min | **Close reason:** GREEN
> **Peak pips:** 5.3
> **Setup:** C4_CHART_PATTERN_BREAK


---

## 💡 💰 USD_CAD BUY win: +5.7p / $+20.58 (157min)
**Date:** 2026-05-12T07:04:32
**Type:** discovery
**Tags:** win, usdcad, guardian, C11_BIG_MOVE

> [!tip] DISCOVERY
> **Pair:** USD_CAD | **Direction:** BUY
> **PnL:** +5.7 pips / $+20.58 | **R:** 0.46
> **Duration:** 157 min | **Close reason:** GREEN
> **Peak pips:** 6.6
> **Setup:** C11_BIG_MOVE


---

## ❌ ❌ NZD_USD SELL loss: -20.6p / $-103.00 (227min)
**Date:** 2026-05-12T15:12:54
**Type:** failure
**Tags:** loss, nzdusd, guardian, C9_BEAR_EXP_PULLBACK

> [!danger] FAILURE
> **Pair:** NZD_USD | **Direction:** SELL
> **PnL:** -20.6 pips / $-103.00 | **R:** -1.00
> **Duration:** 227 min | **Close reason:** RED
> **Peak pips:** 0.0
> **Setup:** C9_BEAR_EXP_PULLBACK


---

## ❌ ❌ EUR_CHF BUY loss: -6.7p / $-43.35 (319min)
**Date:** 2026-05-12T15:27:40
**Type:** failure
**Tags:** loss, eurchf, guardian, C9_BEAR_EXP_PULLBACK

> [!danger] FAILURE
> **Pair:** EUR_CHF | **Direction:** BUY
> **PnL:** -6.7 pips / $-43.35 | **R:** -0.74
> **Duration:** 319 min | **Close reason:** YELLOW
> **Peak pips:** 3.2
> **Setup:** C9_BEAR_EXP_PULLBACK


---

## 💡 💰 EUR_AUD SELL win: +2.9p / $+10.39 (27min)
**Date:** 2026-05-12T15:54:02
**Type:** discovery
**Tags:** win, euraud, guardian, C12_CASCADE_CONTINUATION

> [!tip] DISCOVERY
> **Pair:** EUR_AUD | **Direction:** SELL
> **PnL:** +2.9 pips / $+10.39 | **R:** 0.28
> **Duration:** 27 min | **Close reason:** GREEN
> **Peak pips:** 4.7
> **Setup:** C12_CASCADE_CONTINUATION


---

## 💡 💰 EUR_AUD SELL win: +1.6p / $+5.73 (54min)
**Date:** 2026-05-12T17:05:33
**Type:** discovery
**Tags:** win, euraud, guardian, C12_CASCADE_CONTINUATION

> [!tip] DISCOVERY
> **Pair:** EUR_AUD | **Direction:** SELL
> **PnL:** +1.6 pips / $+5.73 | **R:** 0.27
> **Duration:** 54 min | **Close reason:** GREEN
> **Peak pips:** 9.0
> **Setup:** C12_CASCADE_CONTINUATION


---

## ❌ ❌ EUR_GBP BUY loss: -21.9p / $-149.74 (468min)
**Date:** 2026-05-12T17:56:44
**Type:** failure
**Tags:** loss, eurgbp, guardian, S16

> [!danger] FAILURE
> **Pair:** EUR_GBP | **Direction:** BUY
> **PnL:** -21.9 pips / $-149.74 | **R:** -0.61
> **Duration:** 468 min | **Close reason:** YELLOW
> **Peak pips:** 2.6
> **Setup:** S16


---

## ❌ ❌ EUR_JPY SELL loss: -23.8p / $-76.18 (60min)
**Date:** 2026-05-12T20:55:01
**Type:** failure
**Tags:** loss, eurjpy, guardian, C8_TRIANGLE_BREAKOUT

> [!danger] FAILURE
> **Pair:** EUR_JPY | **Direction:** SELL
> **PnL:** -23.8 pips / $-76.18 | **R:** -1.00
> **Duration:** 60 min | **Close reason:** YELLOW
> **Peak pips:** 0.0
> **Setup:** C8_TRIANGLE_BREAKOUT


---

## ❌ ❌ USD_JPY BUY loss: -13.1p / $-41.98 (74min)
**Date:** 2026-05-12T21:49:27
**Type:** failure
**Tags:** loss, usdjpy, guardian, C12_CASCADE_CONTINUATION

> [!danger] FAILURE
> **Pair:** USD_JPY | **Direction:** BUY
> **PnL:** -13.1 pips / $-41.98 | **R:** -0.86
> **Duration:** 74 min | **Close reason:** GREEN
> **Peak pips:** 7.7
> **Setup:** C12_CASCADE_CONTINUATION


---

## ❌ ❌ USD_CHF BUY loss: -18.8p / $-121.71 (114min)
**Date:** 2026-05-12T21:49:45
**Type:** failure
**Tags:** loss, usdchf, guardian, C11_BIG_MOVE

> [!danger] FAILURE
> **Pair:** USD_CHF | **Direction:** BUY
> **PnL:** -18.8 pips / $-121.71 | **R:** -1.00
> **Duration:** 114 min | **Close reason:** GREEN
> **Peak pips:** 3.0
> **Setup:** C11_BIG_MOVE


---

## ❌ ❌ NZD_USD BUY loss: -12.3p / $-61.50 (30min)
**Date:** 2026-05-12T23:04:25
**Type:** failure
**Tags:** loss, nzdusd, guardian, C9_BEAR_EXP_PULLBACK

> [!danger] FAILURE
> **Pair:** NZD_USD | **Direction:** BUY
> **PnL:** -12.3 pips / $-61.50 | **R:** -1.00
> **Duration:** 30 min | **Close reason:** GREEN
> **Peak pips:** 0.0
> **Setup:** C9_BEAR_EXP_PULLBACK


---

## ❌ ❌ AUD_JPY BUY loss: -19.1p / $-61.18 (38min)
**Date:** 2026-05-12T23:10:20
**Type:** failure
**Tags:** loss, audjpy, guardian, C12_CASCADE_CONTINUATION

> [!danger] FAILURE
> **Pair:** AUD_JPY | **Direction:** BUY
> **PnL:** -19.1 pips / $-61.18 | **R:** -0.70
> **Duration:** 38 min | **Close reason:** GREEN
> **Peak pips:** 0.0
> **Setup:** C12_CASCADE_CONTINUATION


---

## 💡 💰 NZD_USD SELL win: +0.9p / $+4.50 (25min)
**Date:** 2026-05-13T00:43:41
**Type:** discovery
**Tags:** win, nzdusd, guardian, C9_BEAR_EXP_PULLBACK

> [!tip] DISCOVERY
> **Pair:** NZD_USD | **Direction:** SELL
> **PnL:** +0.9 pips / $+4.50 | **R:** 0.90
> **Duration:** 25 min | **Close reason:** GREEN
> **Peak pips:** 2.5
> **Setup:** C9_BEAR_EXP_PULLBACK


---

## 💡 💰 EUR_AUD SELL win: +3.4p / $+12.19 (235min)
**Date:** 2026-05-13T02:12:43
**Type:** discovery
**Tags:** win, euraud, guardian, S16

> [!tip] DISCOVERY
> **Pair:** EUR_AUD | **Direction:** SELL
> **PnL:** +3.4 pips / $+12.19 | **R:** 0.38
> **Duration:** 235 min | **Close reason:** GREEN
> **Peak pips:** 4.1
> **Setup:** S16


---

## 💡 💰 EUR_USD SELL win: +2.7p / $+13.50 (29min)
**Date:** 2026-05-13T02:51:44
**Type:** discovery
**Tags:** win, eurusd, guardian, C4_CHART_PATTERN_BREAK

> [!tip] DISCOVERY
> **Pair:** EUR_USD | **Direction:** SELL
> **PnL:** +2.7 pips / $+13.50 | **R:** 0.38
> **Duration:** 29 min | **Close reason:** GREEN
> **Peak pips:** 3.5
> **Setup:** C4_CHART_PATTERN_BREAK


---

## 💡 💰 NZD_USD SELL win: +1.0p / $+5.00 (110min)
**Date:** 2026-05-13T02:53:34
**Type:** discovery
**Tags:** win, nzdusd, guardian, C9_BEAR_EXP_PULLBACK

> [!tip] DISCOVERY
> **Pair:** NZD_USD | **Direction:** SELL
> **PnL:** +1.0 pips / $+5.00 | **R:** 1.00
> **Duration:** 110 min | **Close reason:** GREEN
> **Peak pips:** 2.8
> **Setup:** C9_BEAR_EXP_PULLBACK


---

## 💡 💰 EUR_AUD SELL win: +3.2p / $+11.46 (25min)
**Date:** 2026-05-13T02:57:40
**Type:** discovery
**Tags:** win, euraud, guardian, S16

> [!tip] DISCOVERY
> **Pair:** EUR_AUD | **Direction:** SELL
> **PnL:** +3.2 pips / $+11.46 | **R:** 0.35
> **Duration:** 25 min | **Close reason:** GREEN
> **Peak pips:** 4.7
> **Setup:** S16


---

## 💡 💰 EUR_JPY SELL win: +2.0p / $+6.28 (10min)
**Date:** 2026-05-13T03:12:40
**Type:** discovery
**Tags:** win, eurjpy, guardian, C12_CASCADE_CONTINUATION

> [!tip] DISCOVERY
> **Pair:** EUR_JPY | **Direction:** SELL
> **PnL:** +2.0 pips / $+6.28 | **R:** 0.23
> **Duration:** 10 min | **Close reason:** GREEN
> **Peak pips:** 3.3
> **Setup:** C12_CASCADE_CONTINUATION


---

## 💡 💰 EUR_GBP SELL win: +0.9p / $+6.03 (28min)
**Date:** 2026-05-13T04:31:02
**Type:** discovery
**Tags:** win, eurgbp, guardian, C12_CASCADE_CONTINUATION

> [!tip] DISCOVERY
> **Pair:** EUR_GBP | **Direction:** SELL
> **PnL:** +0.9 pips / $+6.03 | **R:** 0.90
> **Duration:** 28 min | **Close reason:** GREEN
> **Peak pips:** 2.2
> **Setup:** C12_CASCADE_CONTINUATION


---

## 💡 💰 EUR_USD SELL win: +6.9p / $+34.50 (54min)
**Date:** 2026-05-13T05:35:20
**Type:** discovery
**Tags:** win, eurusd, guardian, C12_CASCADE_CONTINUATION

> [!tip] DISCOVERY
> **Pair:** EUR_USD | **Direction:** SELL
> **PnL:** +6.9 pips / $+34.50 | **R:** 0.68
> **Duration:** 54 min | **Close reason:** GREEN
> **Peak pips:** 9.7
> **Setup:** C12_CASCADE_CONTINUATION


---

## 💡 💰 EUR_AUD SELL win: +3.5p / $+12.55 (55min)
**Date:** 2026-05-13T06:14:34
**Type:** discovery
**Tags:** win, euraud, guardian, C4_CHART_PATTERN_BREAK

> [!tip] DISCOVERY
> **Pair:** EUR_AUD | **Direction:** SELL
> **PnL:** +3.5 pips / $+12.55 | **R:** 0.56
> **Duration:** 55 min | **Close reason:** GREEN
> **Peak pips:** 10.4
> **Setup:** C4_CHART_PATTERN_BREAK


---

## ❌ ❌ EUR_CHF SELL loss: -13.5p / $-87.09 (306min)
**Date:** 2026-05-13T09:03:45
**Type:** failure
**Tags:** loss, eurchf, guardian, C8_TRIANGLE_BREAKOUT

> [!danger] FAILURE
> **Pair:** EUR_CHF | **Direction:** SELL
> **PnL:** -13.5 pips / $-87.09 | **R:** -1.00
> **Duration:** 306 min | **Close reason:** BLACK
> **Peak pips:** 0.1
> **Setup:** C8_TRIANGLE_BREAKOUT


---

## 💡 💰 EUR_AUD SELL win: +5.1p / $+18.29 (152min)
**Date:** 2026-05-13T09:21:33
**Type:** discovery
**Tags:** win, euraud, guardian, C4_CHART_PATTERN_BREAK

> [!tip] DISCOVERY
> **Pair:** EUR_AUD | **Direction:** SELL
> **PnL:** +5.1 pips / $+18.29 | **R:** 0.44
> **Duration:** 152 min | **Close reason:** GREEN
> **Peak pips:** 9.4
> **Setup:** C4_CHART_PATTERN_BREAK


---

## ❌ ❌ GBP_JPY SELL loss: -25.7p / $-82.25 (42min)
**Date:** 2026-05-13T10:04:56
**Type:** failure
**Tags:** loss, gbpjpy, guardian, S16

> [!danger] FAILURE
> **Pair:** GBP_JPY | **Direction:** SELL
> **PnL:** -25.7 pips / $-82.25 | **R:** -0.67
> **Duration:** 42 min | **Close reason:** GREEN
> **Peak pips:** 3.8
> **Setup:** S16


---

## 💡 💰 USD_CHF BUY win: +1.7p / $+10.75 (30min)
**Date:** 2026-05-13T10:57:18
**Type:** discovery
**Tags:** win, usdchf, guardian, C9_BEAR_EXP_PULLBACK

> [!tip] DISCOVERY
> **Pair:** USD_CHF | **Direction:** BUY
> **PnL:** +1.7 pips / $+10.75 | **R:** 0.10
> **Duration:** 30 min | **Close reason:** GREEN
> **Peak pips:** 5.9
> **Setup:** C9_BEAR_EXP_PULLBACK


---

## 💡 💰 EUR_AUD SELL win: +3.5p / $+12.60 (9min)
**Date:** 2026-05-13T11:41:51
**Type:** discovery
**Tags:** win, euraud, guardian, S16

> [!tip] DISCOVERY
> **Pair:** EUR_AUD | **Direction:** SELL
> **PnL:** +3.5 pips / $+12.60 | **R:** 0.83
> **Duration:** 9 min | **Close reason:** GREEN
> **Peak pips:** 5.2
> **Setup:** S16


---

## ❌ ❌ EUR_JPY SELL loss: -22.7p / $-72.61 (327min)
**Date:** 2026-05-13T16:40:00
**Type:** failure
**Tags:** loss, eurjpy, guardian, C9_BEAR_EXP_PULLBACK

> [!danger] FAILURE
> **Pair:** EUR_JPY | **Direction:** SELL
> **PnL:** -22.7 pips / $-72.61 | **R:** -0.87
> **Duration:** 327 min | **Close reason:** YELLOW
> **Peak pips:** 6.8
> **Setup:** C9_BEAR_EXP_PULLBACK


---

## ❌ ❌ EUR_CHF SELL loss: -6.2p / $-40.05 (73min)
**Date:** 2026-05-13T16:59:15
**Type:** failure
**Tags:** loss, eurchf, guardian, C4_CHART_PATTERN_BREAK

> [!danger] FAILURE
> **Pair:** EUR_CHF | **Direction:** SELL
> **PnL:** -6.2 pips / $-40.05 | **R:** -1.03
> **Duration:** 73 min | **Close reason:** YELLOW
> **Peak pips:** 0.0
> **Setup:** C4_CHART_PATTERN_BREAK


---

## ❌ ❌ EUR_USD SELL loss: -18.1p / $-90.50 (241min)
**Date:** 2026-05-13T22:07:59
**Type:** failure
**Tags:** loss, eurusd, guardian, V4_retracement

> [!danger] FAILURE
> **Pair:** EUR_USD | **Direction:** SELL
> **PnL:** -18.1 pips / $-90.50 | **R:** -0.46
> **Duration:** 241 min | **Close reason:** RED
> **Peak pips:** 0.0
> **Setup:** V4_retracement


---

## ❌ ❌ EUR_AUD SELL loss: -40.7p / $-148.98 (241min)
**Date:** 2026-05-13T22:08:04
**Type:** failure
**Tags:** loss, euraud, guardian, C4_CHART_PATTERN_BREAK

> [!danger] FAILURE
> **Pair:** EUR_AUD | **Direction:** SELL
> **PnL:** -40.7 pips / $-148.98 | **R:** -0.62
> **Duration:** 241 min | **Close reason:** GREEN
> **Peak pips:** 2.9
> **Setup:** C4_CHART_PATTERN_BREAK


---

## ❌ ❌ USD_CHF BUY loss: -10.9p / $-70.42 (245min)
**Date:** 2026-05-13T22:11:40
**Type:** failure
**Tags:** loss, usdchf, guardian, C12_CASCADE_CONTINUATION

> [!danger] FAILURE
> **Pair:** USD_CHF | **Direction:** BUY
> **PnL:** -10.9 pips / $-70.42 | **R:** -0.63
> **Duration:** 245 min | **Close reason:** RED
> **Peak pips:** 0.0
> **Setup:** C12_CASCADE_CONTINUATION


---

## ❌ ❌ NZD_USD SELL loss: -11.9p / $-59.50 (360min)
**Date:** 2026-05-14T02:04:59
**Type:** failure
**Tags:** loss, nzdusd, guardian, C9_BEAR_EXP_PULLBACK

> [!danger] FAILURE
> **Pair:** NZD_USD | **Direction:** SELL
> **PnL:** -11.9 pips / $-59.50 | **R:** -1.00
> **Duration:** 360 min | **Close reason:** BLACK
> **Peak pips:** 0.4
> **Setup:** C9_BEAR_EXP_PULLBACK


---

## 💡 💰 EUR_USD SELL win: +0.8p / $+4.00 (187min)
**Date:** 2026-05-14T02:15:36
**Type:** discovery
**Tags:** win, eurusd, guardian, C5_FIB_REACTION

> [!tip] DISCOVERY
> **Pair:** EUR_USD | **Direction:** SELL
> **PnL:** +0.8 pips / $+4.00 | **R:** 0.80
> **Duration:** 187 min | **Close reason:** GREEN
> **Peak pips:** 1.6
> **Setup:** C5_FIB_REACTION


---

## 💡 💰 GBP_USD SELL win: +2.4p / $+12.00 (25min)
**Date:** 2026-05-14T03:57:40
**Type:** discovery
**Tags:** win, gbpusd, guardian, C12_CASCADE_CONTINUATION

> [!tip] DISCOVERY
> **Pair:** GBP_USD | **Direction:** SELL
> **PnL:** +2.4 pips / $+12.00 | **R:** 0.40
> **Duration:** 25 min | **Close reason:** GREEN
> **Peak pips:** 3.4
> **Setup:** C12_CASCADE_CONTINUATION


---

## ❌ ❌ EUR_CHF SELL loss: -7.5p / $-48.44 (69min)
**Date:** 2026-05-14T03:57:57
**Type:** failure
**Tags:** loss, eurchf, guardian, C8_TRIANGLE_BREAKOUT

> [!danger] FAILURE
> **Pair:** EUR_CHF | **Direction:** SELL
> **PnL:** -7.5 pips / $-48.44 | **R:** -1.00
> **Duration:** 69 min | **Close reason:** GREEN
> **Peak pips:** 0.3
> **Setup:** C8_TRIANGLE_BREAKOUT


---

## 💡 💰 AUD_USD SELL win: +3.5p / $+17.50 (28min)
**Date:** 2026-05-14T06:41:55
**Type:** discovery
**Tags:** win, audusd, guardian, C4_CHART_PATTERN_BREAK

> [!tip] DISCOVERY
> **Pair:** AUD_USD | **Direction:** SELL
> **PnL:** +3.5 pips / $+17.50 | **R:** 0.58
> **Duration:** 28 min | **Close reason:** YELLOW
> **Peak pips:** 4.2
> **Setup:** C4_CHART_PATTERN_BREAK


---

## 💡 💰 EUR_USD SELL win: +2.6p / $+13.00 (11min)
**Date:** 2026-05-14T07:36:57
**Type:** discovery
**Tags:** win, eurusd, guardian, C5_FIB_REACTION

> [!tip] DISCOVERY
> **Pair:** EUR_USD | **Direction:** SELL
> **PnL:** +2.6 pips / $+13.00 | **R:** 0.45
> **Duration:** 11 min | **Close reason:** GREEN
> **Peak pips:** 3.4
> **Setup:** C5_FIB_REACTION


---

## 💡 💰 EUR_JPY SELL win: +1.0p / $+3.13 (42min)
**Date:** 2026-05-14T08:33:21
**Type:** discovery
**Tags:** win, eurjpy, guardian, C12_CASCADE_CONTINUATION

> [!tip] DISCOVERY
> **Pair:** EUR_JPY | **Direction:** SELL
> **PnL:** +1.0 pips / $+3.13 | **R:** 1.00
> **Duration:** 42 min | **Close reason:** GREEN
> **Peak pips:** 2.7
> **Setup:** C12_CASCADE_CONTINUATION


---

## 💡 💰 EUR_USD SELL win: +2.3p / $+11.50 (63min)
**Date:** 2026-05-14T08:43:31
**Type:** discovery
**Tags:** win, eurusd, guardian, V4_retracement

> [!tip] DISCOVERY
> **Pair:** EUR_USD | **Direction:** SELL
> **PnL:** +2.3 pips / $+11.50 | **R:** 0.35
> **Duration:** 63 min | **Close reason:** GREEN
> **Peak pips:** 3.1
> **Setup:** V4_retracement


---

## 💡 💰 AUD_USD SELL win: +2.6p / $+13.00 (86min)
**Date:** 2026-05-14T08:51:57
**Type:** discovery
**Tags:** win, audusd, guardian, C4_CHART_PATTERN_BREAK

> [!tip] DISCOVERY
> **Pair:** AUD_USD | **Direction:** SELL
> **PnL:** +2.6 pips / $+13.00 | **R:** 0.38
> **Duration:** 86 min | **Close reason:** YELLOW
> **Peak pips:** 3.3
> **Setup:** C4_CHART_PATTERN_BREAK


---

## 💡 💰 NZD_USD SELL win: +0.6p / $+3.00 (63min)
**Date:** 2026-05-14T09:03:22
**Type:** discovery
**Tags:** win, nzdusd, guardian, C9_BEAR_EXP_PULLBACK

> [!tip] DISCOVERY
> **Pair:** NZD_USD | **Direction:** SELL
> **PnL:** +0.6 pips / $+3.00 | **R:** 0.60
> **Duration:** 63 min | **Close reason:** GREEN
> **Peak pips:** 1.9
> **Setup:** C9_BEAR_EXP_PULLBACK


---

## 💡 💰 EUR_JPY SELL win: +2.1p / $+6.58 (36min)
**Date:** 2026-05-14T09:21:37
**Type:** discovery
**Tags:** win, eurjpy, guardian, C12_CASCADE_CONTINUATION

> [!tip] DISCOVERY
> **Pair:** EUR_JPY | **Direction:** SELL
> **PnL:** +2.1 pips / $+6.58 | **R:** 0.30
> **Duration:** 36 min | **Close reason:** GREEN
> **Peak pips:** 3.4
> **Setup:** C12_CASCADE_CONTINUATION


---

## 💡 💰 NZD_USD SELL win: +1.0p / $+5.00 (26min)
**Date:** 2026-05-14T09:31:36
**Type:** discovery
**Tags:** win, nzdusd, guardian, S13

> [!tip] DISCOVERY
> **Pair:** NZD_USD | **Direction:** SELL
> **PnL:** +1.0 pips / $+5.00 | **R:** 1.00
> **Duration:** 26 min | **Close reason:** GREEN
> **Peak pips:** 2.5
> **Setup:** S13


---

## 💡 💰 USD_JPY BUY win: +6.3p / $+19.73 (11min)
**Date:** 2026-05-14T09:36:48
**Type:** discovery
**Tags:** win, usdjpy, guardian, C9_BEAR_EXP_PULLBACK

> [!tip] DISCOVERY
> **Pair:** USD_JPY | **Direction:** BUY
> **PnL:** +6.3 pips / $+19.73 | **R:** 0.98
> **Duration:** 11 min | **Close reason:** GREEN
> **Peak pips:** 8.0
> **Setup:** C9_BEAR_EXP_PULLBACK


---

## 💡 💰 EUR_JPY SELL win: +36.5p / $+114.58 (7min)
**Date:** 2026-05-14T09:44:44
**Type:** discovery
**Tags:** win, eurjpy, guardian, C9_BEAR_EXP_PULLBACK

> [!tip] DISCOVERY
> **Pair:** EUR_JPY | **Direction:** SELL
> **PnL:** +36.5 pips / $+114.58 | **R:** 1.86
> **Duration:** 7 min | **Close reason:** GREEN
> **Peak pips:** 0.0
> **Setup:** C9_BEAR_EXP_PULLBACK


---

## 💡 💰 EUR_CHF SELL win: +3.6p / $+22.78 (139min)
**Date:** 2026-05-14T09:51:41
**Type:** discovery
**Tags:** win, eurchf, guardian, C12_CASCADE_CONTINUATION

> [!tip] DISCOVERY
> **Pair:** EUR_CHF | **Direction:** SELL
> **PnL:** +3.6 pips / $+22.78 | **R:** 0.97
> **Duration:** 139 min | **Close reason:** GREEN
> **Peak pips:** 4.6
> **Setup:** C12_CASCADE_CONTINUATION


---

## 💡 💰 USD_CAD BUY win: +3.7p / $+13.34 (157min)
**Date:** 2026-05-14T11:01:19
**Type:** discovery
**Tags:** win, usdcad, guardian, C4_CHART_PATTERN_BREAK

> [!tip] DISCOVERY
> **Pair:** USD_CAD | **Direction:** BUY
> **PnL:** +3.7 pips / $+13.34 | **R:** 1.00
> **Duration:** 157 min | **Close reason:** GREEN
> **Peak pips:** 4.6
> **Setup:** C4_CHART_PATTERN_BREAK


---

## ❌ ❌ EUR_GBP SELL loss: -13.5p / $-91.80 (194min)
**Date:** 2026-05-14T12:11:29
**Type:** failure
**Tags:** loss, eurgbp, guardian, C9_BEAR_EXP_PULLBACK

> [!danger] FAILURE
> **Pair:** EUR_GBP | **Direction:** SELL
> **PnL:** -13.5 pips / $-91.80 | **R:** -1.00
> **Duration:** 194 min | **Close reason:** YELLOW
> **Peak pips:** 0.7
> **Setup:** C9_BEAR_EXP_PULLBACK


---

## 💡 💰 AUD_USD SELL win: +4.2p / $+21.00 (179min)
**Date:** 2026-05-14T12:31:49
**Type:** discovery
**Tags:** win, audusd, guardian, S16

> [!tip] DISCOVERY
> **Pair:** AUD_USD | **Direction:** SELL
> **PnL:** +4.2 pips / $+21.00 | **R:** 0.34
> **Duration:** 179 min | **Close reason:** GREEN
> **Peak pips:** 4.8
> **Setup:** S16


---

## 💡 💰 EUR_USD SELL win: +4.0p / $+20.00 (58min)
**Date:** 2026-05-14T12:33:38
**Type:** discovery
**Tags:** win, eurusd, guardian, C12_CASCADE_CONTINUATION

> [!tip] DISCOVERY
> **Pair:** EUR_USD | **Direction:** SELL
> **PnL:** +4.0 pips / $+20.00 | **R:** 0.28
> **Duration:** 58 min | **Close reason:** GREEN
> **Peak pips:** 4.8
> **Setup:** C12_CASCADE_CONTINUATION


---

## 💡 💰 EUR_GBP BUY win: +5.3p / $+35.22 (10min)
**Date:** 2026-05-14T13:27:09
**Type:** discovery
**Tags:** win, eurgbp, guardian, S16

> [!tip] DISCOVERY
> **Pair:** EUR_GBP | **Direction:** BUY
> **PnL:** +5.3 pips / $+35.22 | **R:** 0.32
> **Duration:** 10 min | **Close reason:** GREEN
> **Peak pips:** 6.0
> **Setup:** S16


---

## ❌ ❌ EUR_CHF SELL loss: -1.3p / $-8.38 (1min)
**Date:** 2026-05-14T13:40:55
**Type:** failure
**Tags:** loss, eurchf, guardian, C12_CASCADE_CONTINUATION

> [!danger] FAILURE
> **Pair:** EUR_CHF | **Direction:** SELL
> **PnL:** -1.3 pips / $-8.38 | **R:** -0.13
> **Duration:** 1 min | **Close reason:** GREEN
> **Peak pips:** 4.1
> **Setup:** C12_CASCADE_CONTINUATION


---

## ❌ ❌ EUR_JPY SELL loss: -42.2p / $-134.73 (1min)
**Date:** 2026-05-14T13:40:57
**Type:** failure
**Tags:** loss, eurjpy, guardian, S16

> [!danger] FAILURE
> **Pair:** EUR_JPY | **Direction:** SELL
> **PnL:** -42.2 pips / $-134.73 | **R:** -0.70
> **Duration:** 1 min | **Close reason:** GREEN
> **Peak pips:** 0.0
> **Setup:** S16


---

## 💡 💰 EUR_GBP BUY win: +5.0p / $+33.18 (20min)
**Date:** 2026-05-14T14:02:17
**Type:** discovery
**Tags:** win, eurgbp, guardian, S16

> [!tip] DISCOVERY
> **Pair:** EUR_GBP | **Direction:** BUY
> **PnL:** +5.0 pips / $+33.18 | **R:** 0.27
> **Duration:** 20 min | **Close reason:** GREEN
> **Peak pips:** 5.6
> **Setup:** S16


---

## 💡 💰 USD_CHF BUY win: +0.3p / $+1.90 (62min)
**Date:** 2026-05-14T15:10:40
**Type:** discovery
**Tags:** win, usdchf, guardian, C4_CHART_PATTERN_BREAK

> [!tip] DISCOVERY
> **Pair:** USD_CHF | **Direction:** BUY
> **PnL:** +0.3 pips / $+1.90 | **R:** 0.02
> **Duration:** 62 min | **Close reason:** GREEN
> **Peak pips:** 3.4
> **Setup:** C4_CHART_PATTERN_BREAK


---

## 💡 💰 USD_JPY BUY win: +8.9p / $+27.83 (70min)
**Date:** 2026-05-14T15:18:34
**Type:** discovery
**Tags:** win, usdjpy, guardian, C12_CASCADE_CONTINUATION

> [!tip] DISCOVERY
> **Pair:** USD_JPY | **Direction:** BUY
> **PnL:** +8.9 pips / $+27.83 | **R:** 1.00
> **Duration:** 70 min | **Close reason:** GREEN
> **Peak pips:** 10.5
> **Setup:** C12_CASCADE_CONTINUATION


---

## 💡 💰 GBP_USD SELL win: +7.1p / $+35.50 (21min)
**Date:** 2026-05-14T15:40:12
**Type:** discovery
**Tags:** win, gbpusd, guardian, C12_CASCADE_CONTINUATION

> [!tip] DISCOVERY
> **Pair:** GBP_USD | **Direction:** SELL
> **PnL:** +7.1 pips / $+35.50 | **R:** 0.24
> **Duration:** 21 min | **Close reason:** GREEN
> **Peak pips:** 8.0
> **Setup:** C12_CASCADE_CONTINUATION


---

## ❌ ❌ EUR_GBP BUY loss: -8.2p / $-55.51 (56min)
**Date:** 2026-05-14T17:40:47
**Type:** failure
**Tags:** loss, eurgbp, guardian, C4_CHART_PATTERN_BREAK

> [!danger] FAILURE
> **Pair:** EUR_GBP | **Direction:** BUY
> **PnL:** -8.2 pips / $-55.51 | **R:** -0.18
> **Duration:** 56 min | **Close reason:** GREEN
> **Peak pips:** 0.0
> **Setup:** C4_CHART_PATTERN_BREAK


---

## 💡 💰 EUR_AUD SELL win: +0.2p / $+0.71 (10min)
**Date:** 2026-05-14T19:29:19
**Type:** discovery
**Tags:** win, euraud, guardian, S16

> [!tip] DISCOVERY
> **Pair:** EUR_AUD | **Direction:** SELL
> **PnL:** +0.2 pips / $+0.71 | **R:** 0.20
> **Duration:** 10 min | **Close reason:** GREEN
> **Peak pips:** 2.2
> **Setup:** S16


---

## ❌ ❌ EUR_AUD SELL loss: -8.6p / $-31.35 (19min)
**Date:** 2026-05-14T19:48:07
**Type:** failure
**Tags:** loss, euraud, guardian, S16

> [!danger] FAILURE
> **Pair:** EUR_AUD | **Direction:** SELL
> **PnL:** -8.6 pips / $-31.35 | **R:** -0.58
> **Duration:** 19 min | **Close reason:** GREEN
> **Peak pips:** 0.0
> **Setup:** S16


---

## 💡 💰 NZD_USD SELL win: +4.5p / $+22.50 (13min)
**Date:** 2026-05-14T20:50:59
**Type:** discovery
**Tags:** win, nzdusd, guardian, C12_CASCADE_CONTINUATION

> [!tip] DISCOVERY
> **Pair:** NZD_USD | **Direction:** SELL
> **PnL:** +4.5 pips / $+22.50 | **R:** 0.98
> **Duration:** 13 min | **Close reason:** GREEN
> **Peak pips:** 5.7
> **Setup:** C12_CASCADE_CONTINUATION


---

## 💡 💰 AUD_USD SELL win: +4.3p / $+21.50 (8min)
**Date:** 2026-05-14T20:54:49
**Type:** discovery
**Tags:** win, audusd, guardian, C4_CHART_PATTERN_BREAK

> [!tip] DISCOVERY
> **Pair:** AUD_USD | **Direction:** SELL
> **PnL:** +4.3 pips / $+21.50 | **R:** 0.34
> **Duration:** 8 min | **Close reason:** GREEN
> **Peak pips:** 4.7
> **Setup:** C4_CHART_PATTERN_BREAK


---

## 💡 💰 NZD_USD SELL win: +4.9p / $+24.50 (32min)
**Date:** 2026-05-14T21:30:17
**Type:** discovery
**Tags:** win, nzdusd, guardian, C11_BIG_MOVE

> [!tip] DISCOVERY
> **Pair:** NZD_USD | **Direction:** SELL
> **PnL:** +4.9 pips / $+24.50 | **R:** 1.00
> **Duration:** 32 min | **Close reason:** GREEN
> **Peak pips:** 6.1
> **Setup:** C11_BIG_MOVE


---

## 💡 💰 NZD_USD SELL win: +3.7p / $+18.50 (19min)
**Date:** 2026-05-14T22:08:51
**Type:** discovery
**Tags:** win, nzdusd, guardian, S16

> [!tip] DISCOVERY
> **Pair:** NZD_USD | **Direction:** SELL
> **PnL:** +3.7 pips / $+18.50 | **R:** 0.93
> **Duration:** 19 min | **Close reason:** GREEN
> **Peak pips:** 5.0
> **Setup:** S16


---

## ❌ ❌ EUR_JPY SELL loss: -12.5p / $-39.82 (94min)
**Date:** 2026-05-14T23:28:06
**Type:** failure
**Tags:** loss, eurjpy, guardian, C9_BEAR_EXP_PULLBACK

> [!danger] FAILURE
> **Pair:** EUR_JPY | **Direction:** SELL
> **PnL:** -12.5 pips / $-39.82 | **R:** -0.57
> **Duration:** 94 min | **Close reason:** GREEN
> **Peak pips:** 0.0
> **Setup:** C9_BEAR_EXP_PULLBACK


---

## 💡 💰 USD_CAD BUY win: +3.8p / $+13.68 (104min)
**Date:** 2026-05-15T00:52:12
**Type:** discovery
**Tags:** win, usdcad, guardian, C11_BIG_MOVE

> [!tip] DISCOVERY
> **Pair:** USD_CAD | **Direction:** BUY
> **PnL:** +3.8 pips / $+13.68 | **R:** 1.00
> **Duration:** 104 min | **Close reason:** GREEN
> **Peak pips:** 4.8
> **Setup:** C11_BIG_MOVE


---

## 💡 💰 AUD_JPY SELL win: +3.7p / $+11.55 (173min)
**Date:** 2026-05-15T00:53:18
**Type:** discovery
**Tags:** win, audjpy, guardian, S16

> [!tip] DISCOVERY
> **Pair:** AUD_JPY | **Direction:** SELL
> **PnL:** +3.7 pips / $+11.55 | **R:** 0.97
> **Duration:** 173 min | **Close reason:** GREEN
> **Peak pips:** 4.7
> **Setup:** S16


---

## 💡 💰 AUD_USD SELL win: +3.9p / $+19.50 (172min)
**Date:** 2026-05-15T00:56:07
**Type:** discovery
**Tags:** win, audusd, guardian, S16

> [!tip] DISCOVERY
> **Pair:** AUD_USD | **Direction:** SELL
> **PnL:** +3.9 pips / $+19.50 | **R:** 0.27
> **Duration:** 172 min | **Close reason:** GREEN
> **Peak pips:** 4.6
> **Setup:** S16


---

## 💡 💰 USD_JPY BUY win: +5.6p / $+17.48 (149min)
**Date:** 2026-05-15T01:08:49
**Type:** discovery
**Tags:** win, usdjpy, guardian, C12_CASCADE_CONTINUATION

> [!tip] DISCOVERY
> **Pair:** USD_JPY | **Direction:** BUY
> **PnL:** +5.6 pips / $+17.48 | **R:** 0.41
> **Duration:** 149 min | **Close reason:** GREEN
> **Peak pips:** 6.4
> **Setup:** C12_CASCADE_CONTINUATION


---

## 💡 💰 GBP_USD SELL win: +3.8p / $+19.00 (29min)
**Date:** 2026-05-15T02:28:31
**Type:** discovery
**Tags:** win, gbpusd, guardian, C9_BEAR_EXP_PULLBACK

> [!tip] DISCOVERY
> **Pair:** GBP_USD | **Direction:** SELL
> **PnL:** +3.8 pips / $+19.00 | **R:** 1.00
> **Duration:** 29 min | **Close reason:** GREEN
> **Peak pips:** 4.8
> **Setup:** C9_BEAR_EXP_PULLBACK


---

## 💡 💰 AUD_JPY SELL win: +10.0p / $+31.24 (34min)
**Date:** 2026-05-15T02:51:06
**Type:** discovery
**Tags:** win, audjpy, guardian, C12_CASCADE_CONTINUATION

> [!tip] DISCOVERY
> **Pair:** AUD_JPY | **Direction:** SELL
> **PnL:** +10.0 pips / $+31.24 | **R:** 0.49
> **Duration:** 34 min | **Close reason:** GREEN
> **Peak pips:** 11.0
> **Setup:** C12_CASCADE_CONTINUATION


---

## 💡 💰 AUD_USD SELL win: +4.4p / $+22.00 (21min)
**Date:** 2026-05-15T02:53:16
**Type:** discovery
**Tags:** win, audusd, guardian, C9_BEAR_EXP_PULLBACK

> [!tip] DISCOVERY
> **Pair:** AUD_USD | **Direction:** SELL
> **PnL:** +4.4 pips / $+22.00 | **R:** 0.24
> **Duration:** 21 min | **Close reason:** GREEN
> **Peak pips:** 5.0
> **Setup:** C9_BEAR_EXP_PULLBACK


---

## 💡 💰 EUR_USD SELL win: +4.2p / $+21.00 (56min)
**Date:** 2026-05-15T03:01:00
**Type:** discovery
**Tags:** win, eurusd, guardian, C9_BEAR_EXP_PULLBACK

> [!tip] DISCOVERY
> **Pair:** EUR_USD | **Direction:** SELL
> **PnL:** +4.2 pips / $+21.00 | **R:** 0.41
> **Duration:** 56 min | **Close reason:** GREEN
> **Peak pips:** 5.1
> **Setup:** C9_BEAR_EXP_PULLBACK


---

## 💡 💰 EUR_CHF SELL win: +0.2p / $+1.26 (29min)
**Date:** 2026-05-15T03:01:03
**Type:** discovery
**Tags:** win, eurchf, guardian, C5_FIB_REACTION

> [!tip] DISCOVERY
> **Pair:** EUR_CHF | **Direction:** SELL
> **PnL:** +0.2 pips / $+1.26 | **R:** 0.22
> **Duration:** 29 min | **Close reason:** GREEN
> **Peak pips:** 1.1
> **Setup:** C5_FIB_REACTION


---

## ❌ ❌ GBP_USD SELL loss: -31.0p / $-155.00 (46min)
**Date:** 2026-05-15T03:15:03
**Type:** failure
**Tags:** loss, gbpusd, guardian, C12_CASCADE_CONTINUATION

> [!danger] FAILURE
> **Pair:** GBP_USD | **Direction:** SELL
> **PnL:** -31.0 pips / $-155.00 | **R:** -0.34
> **Duration:** 46 min | **Close reason:** GREEN
> **Peak pips:** 0.0
> **Setup:** C12_CASCADE_CONTINUATION


---

## 💡 💰 EUR_CHF SELL win: +0.6p / $+3.78 (5min)
**Date:** 2026-05-15T03:29:04
**Type:** discovery
**Tags:** win, eurchf, guardian, C12_CASCADE_CONTINUATION

> [!tip] DISCOVERY
> **Pair:** EUR_CHF | **Direction:** SELL
> **PnL:** +0.6 pips / $+3.78 | **R:** 0.60
> **Duration:** 5 min | **Close reason:** GREEN
> **Peak pips:** 1.7
> **Setup:** C12_CASCADE_CONTINUATION


---

## ❌ ❌ EUR_AUD BUY loss: -18.5p / $-66.99 (47min)
**Date:** 2026-05-15T03:37:44
**Type:** failure
**Tags:** loss, euraud, guardian, C12_CASCADE_CONTINUATION

> [!danger] FAILURE
> **Pair:** EUR_AUD | **Direction:** BUY
> **PnL:** -18.5 pips / $-66.99 | **R:** -0.25
> **Duration:** 47 min | **Close reason:** GREEN
> **Peak pips:** 2.2
> **Setup:** C12_CASCADE_CONTINUATION


---

## 💡 💰 EUR_JPY SELL win: +0.7p / $+2.19 (46min)
**Date:** 2026-05-15T03:55:13
**Type:** discovery
**Tags:** win, eurjpy, guardian, C11_BIG_MOVE

> [!tip] DISCOVERY
> **Pair:** EUR_JPY | **Direction:** SELL
> **PnL:** +0.7 pips / $+2.19 | **R:** 0.02
> **Duration:** 46 min | **Close reason:** GREEN
> **Peak pips:** 3.3
> **Setup:** C11_BIG_MOVE


---

## 💡 💰 EUR_USD SELL win: +3.8p / $+19.00 (74min)
**Date:** 2026-05-15T04:18:01
**Type:** discovery
**Tags:** win, eurusd, guardian, C11_BIG_MOVE

> [!tip] DISCOVERY
> **Pair:** EUR_USD | **Direction:** SELL
> **PnL:** +3.8 pips / $+19.00 | **R:** 0.29
> **Duration:** 74 min | **Close reason:** GREEN
> **Peak pips:** 4.6
> **Setup:** C11_BIG_MOVE


---

## 💡 💰 EUR_JPY SELL win: +3.7p / $+11.56 (31min)
**Date:** 2026-05-15T04:28:59
**Type:** discovery
**Tags:** win, eurjpy, guardian, S16

> [!tip] DISCOVERY
> **Pair:** EUR_JPY | **Direction:** SELL
> **PnL:** +3.7 pips / $+11.56 | **R:** 0.92
> **Duration:** 31 min | **Close reason:** GREEN
> **Peak pips:** 5.0
> **Setup:** S16


---

## ❌ ❌ USD_CHF BUY loss: -17.8p / $-114.57 (53min)
**Date:** 2026-05-15T06:45:49
**Type:** failure
**Tags:** loss, usdchf, guardian, C9_BEAR_EXP_PULLBACK

> [!danger] FAILURE
> **Pair:** USD_CHF | **Direction:** BUY
> **PnL:** -17.8 pips / $-114.57 | **R:** -0.77
> **Duration:** 53 min | **Close reason:** GREEN
> **Peak pips:** 0.0
> **Setup:** C9_BEAR_EXP_PULLBACK


---

## ❌ ❌ EUR_CHF SELL loss: -3.5p / $-22.51 (175min)
**Date:** 2026-05-15T07:27:01
**Type:** failure
**Tags:** loss, eurchf, guardian, C12_CASCADE_CONTINUATION

> [!danger] FAILURE
> **Pair:** EUR_CHF | **Direction:** SELL
> **PnL:** -3.5 pips / $-22.51 | **R:** -0.33
> **Duration:** 175 min | **Close reason:** GREEN
> **Peak pips:** 3.1
> **Setup:** C12_CASCADE_CONTINUATION


---

## ❌ ❌ EUR_USD SELL loss: -9.1p / $-45.50 (64min)
**Date:** 2026-05-15T09:42:35
**Type:** failure
**Tags:** loss, eurusd, guardian, S16

> [!danger] FAILURE
> **Pair:** EUR_USD | **Direction:** SELL
> **PnL:** -9.1 pips / $-45.50 | **R:** -0.46
> **Duration:** 64 min | **Close reason:** YELLOW
> **Peak pips:** 0.4
> **Setup:** S16


---

## 💡 💰 USD_JPY BUY win: +6.7p / $+20.89 (9min)
**Date:** 2026-05-15T09:50:47
**Type:** discovery
**Tags:** win, usdjpy, guardian, C9_BEAR_EXP_PULLBACK

> [!tip] DISCOVERY
> **Pair:** USD_JPY | **Direction:** BUY
> **PnL:** +6.7 pips / $+20.89 | **R:** 0.42
> **Duration:** 9 min | **Close reason:** GREEN
> **Peak pips:** 7.5
> **Setup:** C9_BEAR_EXP_PULLBACK


---

## ❌ ❌ EUR_USD SELL loss: -7.6p / $-38.00 (16min)
**Date:** 2026-05-15T10:33:56
**Type:** failure
**Tags:** loss, eurusd, guardian, C9_BEAR_EXP_PULLBACK

> [!danger] FAILURE
> **Pair:** EUR_USD | **Direction:** SELL
> **PnL:** -7.6 pips / $-38.00 | **R:** -0.44
> **Duration:** 16 min | **Close reason:** GREEN
> **Peak pips:** 2.6
> **Setup:** C9_BEAR_EXP_PULLBACK


---

## 💡 💰 USD_CHF BUY win: +3.5p / $+22.03 (16min)
**Date:** 2026-05-15T10:44:51
**Type:** discovery
**Tags:** win, usdchf, guardian, C12_CASCADE_CONTINUATION

> [!tip] DISCOVERY
> **Pair:** USD_CHF | **Direction:** BUY
> **PnL:** +3.5 pips / $+22.03 | **R:** 0.35
> **Duration:** 16 min | **Close reason:** GREEN
> **Peak pips:** 4.3
> **Setup:** C12_CASCADE_CONTINUATION


---

## ❌ ❌ USD_CAD BUY loss: -5.1p / $-18.72 (49min)
**Date:** 2026-05-15T11:07:02
**Type:** failure
**Tags:** loss, usdcad, guardian, C9_BEAR_EXP_PULLBACK

> [!danger] FAILURE
> **Pair:** USD_CAD | **Direction:** BUY
> **PnL:** -5.1 pips / $-18.72 | **R:** -0.24
> **Duration:** 49 min | **Close reason:** GREEN
> **Peak pips:** 2.2
> **Setup:** C9_BEAR_EXP_PULLBACK


---

## ❌ ❌ GBP_JPY SELL loss: -18.9p / $-60.15 (49min)
**Date:** 2026-05-15T13:09:33
**Type:** failure
**Tags:** loss, gbpjpy, guardian, S15

> [!danger] FAILURE
> **Pair:** GBP_JPY | **Direction:** SELL
> **PnL:** -18.9 pips / $-60.15 | **R:** -0.45
> **Duration:** 49 min | **Close reason:** YELLOW
> **Peak pips:** 0.0
> **Setup:** S15


---
