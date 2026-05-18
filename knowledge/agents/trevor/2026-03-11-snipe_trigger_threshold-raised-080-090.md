---
type: improvement
created: 2026-03-11
tags: [snipe, threshold, rsi, scout, tuning]
agent: trevor
decomposed_from: agents/trevor/learnings.md
---

## 📈 SNIPE_TRIGGER_THRESHOLD raised 0.80 → 0.90 (2026-03-11) — both losses had RSI>55 as missing 5th condition
**Date:** 2026-03-11T14:21:48
**Type:** improvement
**Workspace:** workspaces/forex-trading-team
**Tags:** snipe, threshold, rsi, scout, tuning

GBP_USD #1190 and NZD_USD #1186 both triggered at 4/5 conditions (80%). The missing 5th condition on both was rsi<=55 — the validator's own 'buyers taking control' flag. RSI was elevated on both entries; both reversed hard within 20 minutes. At 90% threshold, 5-condition snipes require all 5. Review in 2 weeks — if valid trades are being skipped, consider condition weighting (RSI as hard gate vs BB expanding as soft confirmation) rather than flat threshold.

**Evidence:** Both trades: peaked >70% to TP then reversed in same candle (13:58 UTC). Guardian closes correct — GBP would have SL'd -35p within 2 min of close.

<!-- merged from agents/trevor/2026-03-11-snipe_trigger_threshold-corrected-to-090-in-watch_managerpy.md -->
type: correction
tags: [snipe, threshold, watch_manager, 0.90, overhaul-rollback]
## 🔧 SNIPE_TRIGGER_THRESHOLD corrected to 0.90 in watch_manager.py — morning overhaul had rolled it back to 0.80
**Date:** 2026-03-11T17:18:57
**Type:** correction
**Tags:** snipe, threshold, watch_manager, 0.90, overhaul-rollback
watch_manager.py line 1084: SNIPE_TRIGGER_THRESHOLD was 0.80 after the morning overhaul. Should be 0.90. Reason: both 2026-03-11 losses (GBP_USD #1190, NZD_USD #1186) triggered at 4/5 conditions (80%) — missing 5th was rsi<=55. At 90%, 5-condition snipes require all 5. Added inline comment to make this harder to overwrite silently.
