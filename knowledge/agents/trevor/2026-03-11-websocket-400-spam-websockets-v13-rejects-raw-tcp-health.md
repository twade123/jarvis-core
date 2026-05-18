---
type: correction
created: 2026-03-11
tags: [websocket, watchdog, health-check, scout]
agent: trevor
decomposed_from: agents/trevor/learnings.md
---

## 🔧 WebSocket 400 spam — websockets v13 rejects raw TCP health checks; fixed with HTTP endpoint on port 8768
**Date:** 2026-03-11T14:22:13
**Type:** correction
**Workspace:** workspaces/forex-trading-team
**Tags:** websocket, watchdog, health-check, scout

websockets v13 changed behavior: raw TCP health checks (curl/wget to WS port) now return 400 Bad Request and log noise. Fix: added lightweight HTTP health endpoint on http://127.0.0.1:8768/ in trade_scout.py. Watchdog updated from health_port:8767 to health_url:http://127.0.0.1:8768/.
