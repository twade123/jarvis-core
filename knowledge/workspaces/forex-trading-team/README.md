---
type: workspace
created: 2026-03-01T08:00:00
updated: 2026-03-22T14:45:00
tags: [forex, trading, oanda, sniper-strategy]
links: [/knowledge/agents/]
status: active
validator_agent: validator
knowledge_base: collective/trading-knowledge
---

# Forex Trading Team

## Overview
8-agent autonomous trading team executing a sniper strategy on OANDA forex markets.

## Broker
- **OANDA** (REST API v20)
- Practice account: `101-001-24637237-001`
- Practice URL: `https://api-fxpractice.oanda.com`
- API key: `~/jarvis/API/OANDA_API_KEY.txt`

## Strategy: Sniper
- Extreme mean reversion + candlestick confirmation + tight TP
- Scoring: RSI/Stoch extremes, BB penetration, consecutive candles, candle patterns, H4 bias, divergence
- Sweet spot: threshold 12-14, TP=0.3-0.5×ATR, SL=2.0-2.5×ATR
- Best results: EUR_USD 90.4% win PF=1.56, GBP_USD 90.8% win PF=1.36
- Goal: 80%+ win rate, $100-$300/day

## Instruments (13)
EUR_USD, USD_JPY, GBP_USD, AUD_USD, NZD_USD, USD_CAD, USD_CHF, EUR_GBP, EUR_JPY, GBP_JPY, AUD_NZD, EUR_CHF, EUR_AUD

## Agents (8)
1. **oanda_data** — Market data collection (Haiku)
2. **intelligence** — News/weather/statistical analysis (Haiku)
3. **technical_analyst** — TA with indicators + patterns (Haiku)
4. **validator** — Trading authority, sole decision maker (Sonnet 4.6)
5. **execution** — Trade execution + position management (Haiku)
6. **trade_monitor** — Position monitoring, 5-min checks (Sonnet 4.5)
7. **reporter** — Logging + knowledge management (Haiku)
8. **cycle_orchestrator** — Team coordinator/CEO (Haiku)

## Pipeline
Scout FINDS → Thesis CONFIRMS → Validator GATES → EMA/BB EXIT

## Key Architecture
- Tim: user_id=2, workspace=896, team=`2676292a`
- Dashboard: `localhost:8766/trading`
- Position Guardian: parallel trade monitoring with threat scoring
- Market Story: 3-layer thesis builder (trend narrative, price structure, momentum)
- 20 S-code setups (S1-S20), middle zone playbook, auto-discovery pipeline
