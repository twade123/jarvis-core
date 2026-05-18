---
type: improvement
created: 2026-03-18
tags: [trading, ui, bug, ghost_tab, localstorage, open_trades_cache, serve_ui]
agent: trevor
decomposed_from: agents/trevor/learnings.md
---

## 📈 UI ghost trade tab bug fixed: stale localStorage cache served closed trades as still-open after reload
**Date:** 2026-03-18T07:30:25
**Type:** improvement
**Workspace:** workspaces/forex-trading-team
**Tags:** trading, ui, bug, ghost_tab, localstorage, open_trades_cache, serve_ui

After a trade closed, hard reload of the trading UI showed the trade still open (tab + chart card). Two bugs found and fixed: (1) SERVER: /api/trading/open-trades had no way to distinguish OANDA 200+empty (trade genuinely closed) from OANDA network failure — both fell into stale cache fallback. Fixed by tracking oanda_call_succeeded boolean — if True and trades=[], clear cache and return empty. (2) FRONTEND: init() block in index.html restored tabs from openclaw_open_trade_tabs localStorage before live fetch completed. Fixed by (a) marking restored tabs as _provisionalOpenTrade:true, (b) pruning provisional tabs in updateOpenTradesOnChart() when OANDA confirms they're not open, (c) clearing localStorage when live trades=0 instead of writing empty array.

**Evidence:** Reported 2026-03-18: EUR_USD closed at +$0.90 profit but tab and chart card still showed trade open. OANDA confirmed 0 open trades. Hard reset did not clear UI. Root cause confirmed as stale _open_trades_cache[uid] being served on clean close.
