---
type: note
created: 2026-03-18
tags: [trading, baseline, metrics, benchmark, session_audit]
agent: trevor
decomposed_from: agents/trevor/learnings.md
---

## 📝 Trading bot baseline metrics 2026-03-18 (pre-fix session) — benchmark for improvement tracking
**Date:** 2026-03-18T07:30:36
**Type:** note
**Workspace:** workspaces/forex-trading-team
**Tags:** trading, baseline, metrics, benchmark, session_audit

This is the before-state benchmark. All subsequent sessions should be compared against these numbers to measure impact of the R:R fix, pair cooldown, and London open block. Key metrics to track each session: total P&L, win rate, avg win pips, avg loss pips, R:R ratio, number of snipe queue entries per pair (churn indicator), EUR_AUD trades during 01:00-03:00 ET window.

**Evidence:** Session 2026-03-18 00:00-11:00 ET: 22 trades, 12W/10L, 55% WR. Net P&L: -$53.09 (balance $<amount>→$<amount>). Avg win: +$3.58 / +4.8p. Avg loss: -$8.31 / -13.3p. Avg R:R: 0.37. Break-even WR needed: 73%. Profit left on table: 157p across 10 wins. Pair breakdown: AUD_JPY +$4.75 (only profitable pair), EUR_JPY -$12.13, GBP_USD -$21.80, EUR_AUD -$23.91. Snipe churn: GBP_USD 35 entries in 3h, EUR_AUD 30+ entries 1-3 AM.

<!-- merged from collective/patterns/2026-03-18.md -->
type: collective_patterns
created: 2026-03-18T07:30:04
tags: [collective, patterns]
# Collective Patterns — 2026-03-18
### Trading bot R:R fix: flipped from 0.4 R:R to 1.33 R:R — SL 2.5→1.5×ATR, TP 1.0→2.0×ATR
**Source:** agents/trevor
**Date:** 2026-03-18T07:30:04
24hr audit (2026-03-18): 12W/10L at 55% WR but net -$53.09. Root cause was inverted R:R. Avg win $3.50 vs avg loss $8.30. Required 73% WR to break even at 0.4 R:R. Fix: changed snipe_direct defaults in trading_cycle.py — SL from 2.5×ATR to 1.5×ATR (~12p), TP from 1.0×ATR to 2.0×ATR (~16p). Added hard R:R gate: if calculated R:R < 1.2, TP auto-widens before order is placed. Also stored new multipliers in trading_preferences DB (user_id=2): risk_sniper_sl_atr=1.5, risk_sniper_tp_atr=2.0, min_rr_ratio=1.33. Trailing stop activation lowered from 1.0 R to 0.5 R so it locks in after ~6 pips instead of ~12. 157 pips of profit was left on table in winning trades today due to TP being too tight.
**Evidence:** Baseline session 2026-03-18: balance $<amount>→$<amount>. Avg TP=5.0p, Avg SL=14.1p, R:R=0.37. Winning trades left 157 pips uncaptured. Worst examples: 1490 AUD_JPY exited +3.4p, ran 20p more. 1604 EUR_JPY exited +8.0p, ran 38.8p more. 1510 EUR_AUD exited +5.7p, ran 22.9p more.
### Snipe system overhaul: conditions-hash dedup, leaderboard wired, validator watch context, annotation ownership, staleness grading
**Source:** agents/trevor
**Date:** 2026-03-18T08:16:20
Five changes to watch_manager.py, trading_cycle.py, trading_api_routes.py, snipe_cleanup.py:
1. DEDUP: create_watch() now uses conditions fingerprint hash (MD5 of sorted field:op:bucketed_value) instead of pair-based supersede. Multiple watches on same pair with different conditions all coexist. Exact same conditions = return existing watch ID, no new row. Replaces broken logic that was nuking valid co-existing watches.
2. LEADERBOARD: record_outcome() now calls _upsert_leaderboard() after every close. Aggregates win rate, total pips, trigger count per conditions_hash+instrument. snipe_leaderboard was created but never written to — now wired.
3. VALIDATOR WATCH CONTEXT: get_watches_for_validator() injected into validator prompt on clean scout cycles (not snipe-triggered cycles). Validator sees active watches for the pair, their progress, age, staleness, leaderboard history. Read-only — cannot cancel, can suggest staleness to user.
4. ANNOTATION OWNERSHIP: snipe_id FK added to user_chart_annotations. Chart render and validator only get annotations owned by triggering watch (or recent pair annotations as fallback). Clean scout cycles get zero annotations. Fixes stale annotation contamination bug.
5. STALENESS GRADE: get_active_watches() returns staleness_score (0-100), staleness_label (fresh/aging/stale/expired), age_hours, conditions_hash, direction, leaderboard stats on every watch. snipe_cleanup.py also pulls leaderboard history for CRO to use in KEEP/REMOVE decisions.
**Evidence:** Pre-fix: 1220 EUR_USD watch from March 12 (145h old) and 135 EUR_USD bias annotation from March 12 were contaminating every EUR_USD cycle. Validator was building analysis around 6-day-old markup. Also: pair-based dedup was superseding valid co-existing BUY and SELL watches on same pair.
### Execution agent removed from trade placement — direct Python place_market_order now used for all trade types
**Source:** agents/trevor
**Date:** 2026-03-18T09:58:25
The LLM execution agent added zero value at trade execution: direction, units, SL, and TP are all pre-computed before it was called. It introduced 60-second latency and could silently fail by responding in prose instead of calling place_market_order. Root cause of AUD_JPY missed SELL on 2026-03-18 at 13:18 — validator said CONFIRM, orchestrator passed to execution agent, agent responded 'I'll place the market order' in natural language without calling the tool, trade_id=null, no trade opened. AUD_JPY dropped 12.3 pips. Fix: replaced _agent_task('execution') in trading_cycle.py Step 7 with direct place_market_order() Python call — same path used by snipe_direct. Result: all trade executions now unified on one deterministic path, <1s execution time, no LLM cost, clear error on failure.
**Evidence:** AUD_JPY 2026-03-18 13:18: exec_agent_result showed 'I'll place the market order for AUD_JPY' text, tool_calls=[], trade_id=null. OANDA confirmed no trade opened. Price moved 12.3p in correct direction after miss. All 17 other trades today used snipe_direct (Python) successfully.
### Guardian fan-width retracement fix: stop penalizing trades during normal M15 fan compression
**Source:** agents/trevor
**Date:** 2026-03-18T09:58:25
Guardian threat calculator was adding +20 proximity_risk whenever fan_width_pct < 0.03% near E100, regardless of whether the fan order was still intact. During normal M15 retracements the EMA fan compresses as EMAs converge — that is healthy structure, not a failure. This was artificially inflating threat scores by 20 points during every consolidation/retracement candle, causing trades to be killed by the 75-threshold auto-close during normal price breathing. Fix in position_guardian.py assess_threat(): now checks fan_favorable before applying the +20 penalty. If fan is compressed but still in correct order (E21<E55<E100 for SELL, E21>E55>E100 for BUY), logs 'retracement, order intact' with zero threat increase. Only applies +20 if fan has actually inverted (order broken). Example: EUR_USD SELL #1656 had threat 50-53 from fan compression during retracement despite SELL order (E21<E55<E100) being fully intact.
**Evidence:** EUR_USD SELL #1656 2026-03-18: fan_width=0.000-0.018% triggering 'trend structure gone' every minute. M15 EMA check showed E21=1.15237 < E55=1.15308 < E100=1.15331 — fully intact SELL order. Threat was 50-53 purely from width, no structural break. Pre-fix: threat inflated 20pts during all retracements. Post-fix: retracement compression adds 0 threat if order intact.
### Trading performance dashboard + Trevor review lightbox — full improvement feedback loop
**Source:** agents/trevor
**Date:** 2026-03-18T13:28:32
Built complete performance feedback system: (1) /api/trading/performance endpoint (Tim-only) returning real data from flight_recorder.db — session P&L, pipeline funnel, scout correlation, guardian rule attribution, cascade phases, snipe leaderboard, session history comparison, tune recommendations. (2) Team Intelligence panel updated with real data instead of stale markdown files. (3) Performance Dashboard (⚙️ button) shows all metrics with clickable drilldowns on pipeline nodes. (4) 📤 Request Review button opens direct-to-Trevor lightbox — same OpenClaw gateway as this conversation, skip_boardroom=true so no boardroom routing. Response streams live. Follow-up questions in same thread. (5) Pipeline funnel flowchart replaces broken 'missed opportunities' count — shows scout→cycles→confirm→trades→wins chain with drop-off reasons. (6) EOD cron updated to include trading_eod_analysis.py output — pipeline funnel, cascade phases, guardian rules, tune recommendations sent to Telegram at 9PM with existing summary. Files: trading_api_routes.py (performance endpoint + pipeline funnel), index.html (dashboard UI), serve_ui.py (skip_boardroom flag), trading_eod_analysis.py (new EOD script).
**Evidence:** Lightbox confirmed working 2026-03-18 13:27 ET — Tim tested and got direct Trevor response. Pipeline funnel shows today: 98 alerts → 99 cycles → 25 decisions → 11 trades → 4 wins. Real missed = 1 execution failure (not 97 as the old broken metric showed).
### Scout→snipe→outcome full feedback loop completed + pair quality filter + session_metrics table
**Source:** agents/trevor
**Date:** 2026-03-18T14:32:15
Completed the full scout performance tracking chain: (1) _store_alert() now returns lastrowid and sets alert['scout_alert_id']. (2) scout_alert_id travels in scout_context → _watch_context → display_context → stored in watch_suggestions.context. (3) record_outcome() reads scout_alert_id from watch context and UPDATE scout_alerts SET outcome, pips_result, snipe_triggered=1, trade_executed=1. (4) Pair quality filter added to trade_scout.py: _WEAK_PAIRS = {USD_JPY, USD_CAD, USD_CHF, NZD_USD, GBP_USD} — EARLY_WARNING blocked on these pairs (need CRITERIA_MET). Based on labeled chart analysis: USD_JPY 0%WR, USD_CAD 0%WR, USD_CHF 0%WR, NZD_USD 0%WR vs AUD_JPY 64%, EUR_AUD 69%, EUR_JPY 57%. (5) session_metrics table added to flight_recorder.db — tracks per-day: trades, wins, WR, P&L, avg_pips, scout_alerts, cycles_run, exec_failures, phase3_count, phase5_count, phase3_survival_rate. trading_eod_analysis.py write_session_metrics() called at EOD. Now every alert, snipe, and trade outcome is linked and measurable.
**Evidence:** 
