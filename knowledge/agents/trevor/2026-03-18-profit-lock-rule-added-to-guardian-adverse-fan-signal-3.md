---
type: improvement
created: 2026-03-18
tags: [trading, guardian, profit_lock, trailing_stop, adverse_fan, peaked_against, smart_exit]
agent: trevor
decomposed_from: agents/trevor/learnings.md
---

## 📈 Profit-lock rule added to guardian: adverse fan signal 3+ consecutive minutes while in profit locks SL at 50% of peak
**Date:** 2026-03-18T09:58:41
**Type:** improvement
**Workspace:** workspaces/forex-trading-team
**Tags:** trading, guardian, profit_lock, trailing_stop, adverse_fan, peaked_against, smart_exit

Analysis of last week's losses showed 4 trades that hit profit then gave it all back. Guardian was already generating 'peaked against trade' and 'collapsing against trade' reason strings but these only added 8-10 to threat score. New rule in _check_smart_exit: if guardian reasons contain 'peaked against trade' OR 'collapsing against trade' for 3+ consecutive minutes while pnl_pips >= 3.0, SL moves to entry + 50% of peak pips seen so far. Uses peak pips not current pips to avoid locking near zero on dips. Simulation on 20 last-week trades: 0 false cuts on winning trades, saves EUR_USD #1644 (- → ~flat). Thresholds deliberately conservative: 3 minutes not 2, 3 pips not 1, 50% of peak not 70% of current. Trade can still ride upward — only the floor moves.

**Evidence:** Pre-fix: EUR_USD #1644 peaked at +.60, guardian said 'peaked against trade' from minute 1 (12:32), price crossed zero at 12:43, closed at - at 12:58. 9-minute window existed. GBP_USD #1586 peaked +/bin/zsh.70, 4-minute window, ended -.50. EUR_JPY #1612 peaked +.31, 7-minute window, ended -.18. Simulation result: 0 false cuts, 2 correct saves.
