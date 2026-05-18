---
type: improvement
created: 2026-03-23
tags: [scout, snipe-monitor, M1, fast-check, guardian-pattern, real-time]
agent: log
decomposed_from: agents/claude-code/log/2026-03.md
---

## 📈 Guardian-style M1 fast-check loop added to scout snipe monitor — real-time price/EMA condition checking every 60s
**Date:** 2026-03-23T10:05:44
**Type:** improvement
**Tags:** scout, snipe-monitor, M1, fast-check, guardian-pattern, real-time

> [!success] IMPROVEMENT
> Added _snipe_fast_check_loop() and _fast_check_active_snipes() to trade_scout.py. Runs alongside existing 5-min M15 monitor. Every 60 seconds: fetches M1 candles for pairs with active snipes, computes EMAs on M1, checks FAST conditions (price_zone, price_above/below, invalidation_level, close, ema_cross_below/above). Structural conditions (fan_state, bb_expanding, velocity, momentum) stay on 5-min M15 cadence. When all fast conditions met, logs and updates progress in DB. When invalidation hit, warns for potential cancel. Pattern mirrors position_guardian's M1 evaluation loop. Also fixed main _scan_pair to pass bb_width_prev and bb_squeeze to check_conditions (same as snipe_only_scan fix).
