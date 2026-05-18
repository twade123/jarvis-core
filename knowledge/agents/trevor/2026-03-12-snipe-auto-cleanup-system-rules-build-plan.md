---
type: note
created: 2026-03-12
tags: [snipe, cleanup, auto-cleanup, build-plan, trading-ui, todo]
agent: trevor
decomposed_from: agents/trevor/learnings.md
---

## 📝 Snipe auto-cleanup system — rules + build plan
**Date:** 2026-03-12T07:47:28
**Type:** note
**Tags:** snipe, cleanup, auto-cleanup, build-plan, trading-ui, todo

SNIPE CLEANUP SYSTEM

PROBLEM: Snipe list grows indefinitely. Stale snipes from dead setups remain active and can trigger bad trades (e.g. #1115 USD_CAD was a SELL snipe after market flipped bullish).

RULES (implemented in snipe_cleanup logic):

KEEP if ANY true:
- peak_progress >= 70% (was close, market could return to setup)
- created < 24h ago (too fresh to judge)

REMOVE if ALL true:
- peak_progress < 70%
- age > 3 days (user_requested snipes)
- age > 36 hours (validator_structured snipes — market context goes stale faster)

REMOVE IMMEDIATELY (dangerous, regardless of age):
- Direction conflict: snipe direction opposes current fan_direction AND peak_progress < 50%
- This is the bad one — can fire a trade against the market

BUILD PLAN (~2 hours):
1. API endpoint in trading_api_routes.py — runs rules against current scout data from flight_recorder.db, returns flagged list with reasons
2. Dashboard button 'Snipe Check' — calls endpoint, shows flagged snipes, confirm to cancel
3. Auto-cleanup cron — same logic, runs daily at market open, cancels automatically, logs to flight_recorder

LOCAL MODEL TRAINING:
Classification task: input = (snipe age, peak_progress, fan_direction vs snipe_direction, conditions_met, pair) → output = keep/remove + reason. Feed cleanup decisions back as training data. Eventually local model runs snipe check autonomously.
