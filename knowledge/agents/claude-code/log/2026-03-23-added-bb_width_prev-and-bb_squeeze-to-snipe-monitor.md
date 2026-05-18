---
type: correction
created: 2026-03-23
tags: [scout, snipe-monitor, bb-width-prev, bb-squeeze, conditions]
agent: log
decomposed_from: agents/claude-code/log/2026-03.md
---

## 🔧 Added bb_width_prev and bb_squeeze to snipe monitor indicators — fixes bb_expanding and bb_squeeze_break condition evaluation
**Date:** 2026-03-23T10:01:54
**Type:** correction
**Tags:** scout, snipe-monitor, bb-width-prev, bb-squeeze, conditions

> [!warning] CORRECTION
> The snipe monitor in trade_scout.py _snipe_only_scan() passes latest_row to check_conditions() but was missing bb_width_prev (needed for bb_expanding check) and bb_squeeze (needed for bb_squeeze_break check). Without bb_width_prev, bb_expanding always evaluated as False. Fix: copy previous row's bb_width into latest_row['bb_width_prev'], compute bb_squeeze as bb_width < 0.003. Also verified all 12 condition types across 6 active snipes have working evaluation handlers. Next priority: M1 fast-check loop for price-level conditions (price_zone, invalidation) — currently checked only every 5 min on M15.
