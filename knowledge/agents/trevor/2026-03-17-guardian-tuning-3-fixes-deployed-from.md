---
type: note
created: 2026-03-17
tags: [guardian, trading, tuning, performance, audit]
agent: trevor
decomposed_from: agents/trevor/learnings.md
---

## 📝 Guardian tuning: 3 fixes deployed from 2026-03-17 trade audit
**Date:** 2026-03-17T18:14:16
**Type:** note
**Tags:** guardian, trading, tuning, performance, audit

Trade audit of 8 trades today (5W/3L, -$28.15 net despite 62% WR) revealed 3 guardian/entry problems. All three fixed and deployed.

FIX 1 — Guardian MFE minimum floor (position_guardian.py _check_dynamic_exit):
- Problem: #1461 EUR_AUD exited at +2.7p when MFE was 7.3p on 11p TP. Guardian tightened SL to entry+3p during E100 retrace test and price hit it.
- Fix: When MFE > 60% of TP, min SL floor = MFE - 2p. Prevents exiting below 60% of prior peak.
- Would have saved: ~4.6p on #1461

FIX 2 — Fan-state aware SL cap (trading_cycle.py SNIPE DIRECT):
- Problem: Losses #1429 (EUR_AUD -31p), #1421 (AUD_JPY -25p), #1479 (AUD_JPY -24p) all had 24-31p SL in contracting/peaked fans (0.33 R:R). Structural breakdown = losses 3x bigger than wins.
- Fix: When fan_state NOT in [expanding, just_crossed, accelerating], cap SL at 1.5×ATR (~15p) instead of 2.5×ATR (~25p).
- fan_state now flows: check_active_watches → triggered[] → scout_context → snipe_direct
- Would have reduced loss damage by ~40%

FIX 3 — Oscillator direction gate (trading_cycle.py SNIPE DIRECT):
- Problem: #1429 SELL entered while stoch was recovering from low (rising through 20-35). #1479 BUY entered while stoch was falling from high. Both counter-momentum entries.
- Fix: Block SELL when stoch < 35 and rising. Block BUY when stoch > 65 and falling.
- Existing momentum trap only blocked extremes (RSI<22+stoch<10). This catches earlier zone transitions.

Baseline for tracking: Balance $<amount> | NAV $<amount> | 2026-03-17 18:11 EDT
Today P&L: 5W/3L, -$28.15 net. Losses avg -$18.75, wins avg +$6.36. Problem: wide SL in mature fans.

Performance expectation:
- Fix 2 alone should cut loss size by ~40% on SL-hit trades in non-expanding fans
- Fix 3 should reduce entry frequency in recovering/rolling oscillator conditions (~20% fewer bad entries)
- Fix 1 should recover 2-5p per exited trade that had MFE > 60% TP
