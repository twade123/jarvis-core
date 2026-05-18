# Universal Scout Analyst Patterns — 2026-03-26

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

