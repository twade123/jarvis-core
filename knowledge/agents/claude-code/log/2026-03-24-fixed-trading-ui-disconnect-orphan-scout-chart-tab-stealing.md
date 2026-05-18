---
type: correction
created: 2026-03-24
tags: [scout, dashboard, snipe, chart-tabs, websocket, pid-guard]
agent: log
decomposed_from: agents/claude-code/log/2026-03.md
---

## 🔧 Fixed trading UI disconnect: orphan scout, chart-tab-stealing, missing triggered-snipe tabs
**Date:** 2026-03-24T07:01:51
**Type:** correction
**Tags:** scout, dashboard, snipe, chart-tabs, websocket, pid-guard

> [!warning] CORRECTION
> Root cause: orphan scout process held WebSocket port 8767, new scout couldn't broadcast. Fixed: (1) PID file guard in trade_scout.py kills stale scout on startup, (2) signal handler uses stored loop ref instead of asyncio.get_event_loop() which crashes in threads, (3) restored triggered-snipe tab opening in fetchWatches() (removed by 13204a07), (4) fixed 3 places that stole user focus (queueScoutAutoAnalyze, showSnipeTrigger, updateRunningCycleIndicators) — all now background-only
