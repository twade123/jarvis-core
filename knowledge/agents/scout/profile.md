---
type: agent
created: 2026-03-01T08:00:00
updated: 2026-03-01T08:00:00
tags: [scout, data-collection, oanda]
links: [/knowledge/workspaces/forex-trading-team/]
status: active
---
# Trade Scout (oanda_data)

## Role
Market data collection — fetch candles, pricing, account state from OANDA

## Model
claude-3-5-haiku

## Type
data_collection

## MCP Tools
handler_oanda

## Capabilities
Fetch H1/H4/M15 candles (250 per TF), account summary, live pricing, instrument specs, multi-timeframe data

## Registered Skills
fetch_candles, get_account_summary, fetch_multi_timeframe, get_current_pricing, get_instrument_specs

## Notes
Background scanner: 13 pairs × 17 elite setups every 5min. Elite playbook: 88-91% win rate, 1000+ trades, PF>1.2. Wired into watch_manager → auto-creates snipes → auto-triggers cycles.

## Skills
- market_scanning
- pattern_detection
