---
type: correction
created: 2026-03-20
tags: [wolfram, sys-path, deep-queries, news, silent-failure, audit-2026-03-20-phase4]
agent: log
decomposed_from: agents/claude-code/log/2026-03.md
---

## 🔧 PHASE 4 AUDIT: Wolfram queries silently failing — sys.path hardcoded to non-existent directory
**Date:** 2026-03-20T23:59:02
**Type:** correction
**Tags:** wolfram, sys-path, deep-queries, news, silent-failure, audit-2026-03-20-phase4

All Wolfram deep queries and news fetches were silently failing. Root cause: sys.path was hardcoded to "Trading Bot" directory which no longer exists (renamed to "Forex Trading Team"). Fixed using `__file__`-relative path computation instead of hardcoded string.

Also fixed: Wolfram commodity queries used ambiguous phrasing. "WTI crude oil price" returns monthly EIA data, not live spot. All queries updated to "current X spot price" format. Note: WTI specifically is monthly data from Wolfram even with this fix — supplement with Yahoo Finance for intraday WTI data.

**Wolfram Pro data confirmed flowing:** Fed funds rate, treasury yields, gold spot (same-day), FX rates with cross-rates, volatility indices, min/max ranges. All now synthesized through 35B for quality output.
