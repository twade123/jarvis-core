---
type: agent
created: 2026-03-01T08:00:00
updated: 2026-03-01T08:00:00
tags: [guardian, monitoring, trade-monitor]
links: [/knowledge/workspaces/forex-trading-team/]
status: active
---
# Position Guardian

## Role
Continuous position monitoring with 4-layer contextual threat scoring + trade execution

## Model
claude-sonnet-4.5 (monitor) / claude-3-5-haiku (execution)

## Type
monitoring + execution

## MCP Tools
handler_oanda

## Capabilities
Per-trade async watchers, 4-layer threat scoring (trend structure, price structure, momentum, emergency), profit protection (breakeven at 1.5R, trailing at 2.0R), BB dynamic exit, EMA separation velocity tracking

## Registered Skills
monitor_open_positions, check_spread_conditions, get_position_status, alert_orchestrator, place_market_order, update_monitored_positions

## Notes
75+ threat = auto-close. 61-74 = Trade Monitor LLM evaluates. BLACK zone = safety kill bypassing agents. Replaced old position monitor entirely.

## Skills
- risk_monitoring
- threat_scoring
- position_management
