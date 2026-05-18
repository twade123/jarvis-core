---
type: correction
created: 2026-03-23
tags: [dashboard, snipe, ghost-signal, chart, fix]
agent: log
decomposed_from: agents/claude-code/log/2026-03.md
---

## 🔧 Fixed 4 ghost snipe indicator sources in trading dashboard
**Date:** 2026-03-23T17:36:21
**Type:** correction
**Tags:** dashboard, snipe, ghost-signal, chart, fix

> [!warning] CORRECTION
> Ghost snipes had 4 root causes: (1) Scout alerts reused snipe-flash green animation — now separate scout-flash (blue). (2) showSnipeTrigger() markers lacked _isSnipe flag so updateSnipeMarkers() never cleaned them — tagged now. (3) showSnipeTrigger() price lines were permanent with no cleanup — now tracked in _snipePriceLines array and removed when no active snipes. (4) fetchWatches() auto-opened chart tabs for every watching snipe every 30s — removed. All fixes in dashboard/index.html.
