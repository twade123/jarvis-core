---
type: improvement
created: 2026-03-18
tags: [trading, scout, quality, cascade_phase, composite, EARLY_WARNING, filter, scout_alerts]
agent: trevor
decomposed_from: agents/trevor/learnings.md
---

## 📈 Scout signal quality upgrade: cascade phase + composite data + EARLY_WARNING quality gate
**Date:** 2026-03-18T14:06:36
**Type:** improvement
**Workspace:** workspaces/forex-trading-team
**Tags:** trading, scout, quality, cascade_phase, composite, EARLY_WARNING, filter, scout_alerts

Three changes to trade_scout.py: (1) schema: added 11 new columns to scout_alerts DB — cascade_phase, fan_width_pips, fan_delta_5bar, bb_width_pct, bb_delta_5bar, is_retracement, both_expanding, both_contracting, e100_dist_pips, story_score, checklist_score. Each alert now stores the same composite picture the guardian tracks per trade. (2) _store_alert() updated to compute and write cascade_phase (trending/retracing/forming from both_expanding/both_contracting), fan separation in pips, BB width as %, both_expanding and both_contracting flags. (3) EARLY_WARNING quality gate tightened: was just story_score>=30, now requires story_score>=35 AND bb_width_pct>0.0003 (real BB width) AND (fan_expanding OR is_retracement OR bb_squeeze_breakout). Kills score=11-13 noise alerts with bb_expanding=False. Labeled chart baseline: AUD_JPY 64%WR, EUR_AUD 69%WR, EUR_JPY 57%WR — these are the real setups. USD_JPY 0%, GBP_USD 33% — noise pairs. In 2 weeks the cascade data will show which scout alert phases correlate with wins.

**Evidence:** First new-format alert: 2026-03-18T14:04 EUR_AUD RETRACEMENT phase=retracing fan=9.6p story=30. All prior alerts have empty cascade fields. 1,317 historical alerts have no composite data — new data builds from today.
