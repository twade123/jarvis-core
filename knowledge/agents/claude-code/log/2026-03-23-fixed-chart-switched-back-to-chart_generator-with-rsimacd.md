---
type: correction
created: 2026-03-23
tags: [chart, validator, RSI, MACD, visual, root-cause]
agent: log
decomposed_from: agents/claude-code/log/2026-03.md
---

## 🔧 Fixed chart: switched back to chart_generator with RSI+MACD subpanels — validator was seeing bare candlesticks
**Date:** 2026-03-23T10:33:54
**Type:** correction
**Tags:** chart, validator, RSI, MACD, visual, root-cause

> [!warning] CORRECTION
> Critical bug: chart_renderer was receiving flat indicator dict but expected arrays — all indicator overlays silently failed. Validator received bare candlesticks with empty RSI/MACD panels, no EMAs, no BBs. Fix: switched back to chart_generator.py which computes EMAs+BBs from raw candles. Added 3-panel layout with RSI(14) subplot (OB/OS bands) and MACD subplot (line+signal+histogram). Chart now shows full visual context: EMA21/55/100, BB upper/lower/mid, RSI with 70/30 bands, MACD with green/red histogram. This was the root cause of the validator rubber-stamping the TA text — it had nothing to visually analyze.
