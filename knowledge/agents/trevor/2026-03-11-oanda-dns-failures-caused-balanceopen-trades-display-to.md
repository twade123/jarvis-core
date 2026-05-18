---
type: correction
created: 2026-03-11
tags: [oanda, dashboard, cache, dns, balance]
agent: trevor
decomposed_from: agents/trevor/learnings.md
---

## 🔧 OANDA DNS failures caused balance/open-trades display to blank — fixed with server-side cache + 4s timeout
**Date:** 2026-03-11T14:22:06
**Type:** correction
**Workspace:** workspaces/forex-trading-team
**Tags:** oanda, dashboard, cache, dns, balance

Root cause: /api/trading/status and /api/trading/open-trades hit OANDA live on every 10s poll with 10s timeout. DNS failures (api-fxpractice.oanda.com) caused live_balance to drop silently from response. Fix: added _balance_cache and _open_trades_cache in trading_api_routes.py. Successful fetches write to cache; failures return cached value. Frontend now preserves displayed value if API returns null. Timeout reduced to 4s.

**Evidence:** Log: WARNING: Failed to fetch live balance: Failed to resolve 'api-fxpractice.oanda.com' ([Errno 8] nodename nor servname provided) at 09:46 AM
