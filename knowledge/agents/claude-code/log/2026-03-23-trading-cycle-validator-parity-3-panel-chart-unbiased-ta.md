---
type: improvement
created: 2026-03-23
tags: [trading-cycle, validator, chart-renderer, gate1, direction-fix]
agent: log
decomposed_from: agents/claude-code/log/2026-03.md
---

## 📈 Trading cycle validator parity: 3-panel chart, unbiased TA, Gate1 bypass, direction fix, full indicators
**Date:** 2026-03-23T08:24:36
**Type:** improvement
**Tags:** trading-cycle, validator, chart-renderer, gate1, direction-fix

> [!success] IMPROVEMENT
> 5 fixes to trading_cycle.py: (1) Switched from chart_generator (1 panel) to chart_renderer (3 panels: candlesticks+EMAs+BBs, RSI, MACD). Validator now sees same visual indicators as chart submissions. (2) Rebuilt _validator_sections as unbiased TA — removed Scout Evidence, Scout alert type, Thesis Progress, Entry Type labels. Validator finds opportunities on its own. (3) Added full indicators to _unified_params (RSI, Stoch K/D, ADX, MACD hist, BB width/upper/lower, ATR, close, high, low). (4) Gate1 now allows CRITERIA_MET/WATCH/TRADE_NOW to bypass — only EARLY_WARNING gated. (5) Fixed direction 'buy'/'sell' → 'long'/'short' in trade_decisions INSERT (was silently failing every write).
