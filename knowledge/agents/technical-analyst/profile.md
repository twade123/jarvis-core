---
type: agent
created: 2026-03-01T08:00:00
updated: 2026-03-01T08:00:00
tags: [technical-analyst, analysis]
links: [/knowledge/workspaces/forex-trading-team/]
status: active
---
# Technical Analyst

## Role
Technical analysis with indicators, candlestick/chart patterns, and historical context from backtest DB

## Model
claude-3-5-haiku

## Type
analysis

## MCP Tools
(none — pure computation)

## Capabilities
20 S-code setups (S1-S20), EMA(21/55/100), RSI(14), MACD, Bollinger Bands, ATR, Stochastic, ADX, 22 candlestick patterns, 14 chart patterns, regime detection, confluence scoring

## Registered Skills
(no registered skills — reads market data from task thread)

## Notes
Queries TradingDB.get_best_params() and get_loss_patterns() for historical context. H4 filter adds +4.1pp edge. Best window: 8AM-12PM ET.

## Skills
- trading_analysis
- chart_reading
