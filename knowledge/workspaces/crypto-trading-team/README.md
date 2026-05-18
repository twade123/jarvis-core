---
type: workspace
created: 2026-03-01T08:00:00
updated: 2026-03-01T08:00:00
tags: [crypto, trading, coinbase, planned]
links: [/knowledge/workspaces/forex-trading-team/]
status: planned
---

# Crypto Trading Team

## Status: PLANNED (March 2026)

## Overview
Clone of the forex trading team (8 agents), adapted for cryptocurrency markets via Coinbase.

## Broker
- **Coinbase** (API keys working — verified in test_coinbase_connection.py)
- 5x legacy Coinbase folders exist in jarvis root (components to evaluate)

## Architecture
- Duplicate forex team → connect Coinbase API → backtest on crypto pairs → retrain agents
- Same 8-agent structure, swap OANDA MCP for Coinbase MCP

## Key Differences from Forex
- 24/7 markets (no session-based filtering)
- Higher volatility
- Different liquidity patterns
- No London/NY overlap concept — different session dynamics
