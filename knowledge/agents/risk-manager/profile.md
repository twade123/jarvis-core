---
type: agent
created: 2026-03-01T08:00:00
updated: 2026-03-01T08:00:00
tags: [risk-manager, risk]
links: [/knowledge/workspaces/forex-trading-team/]
status: active
---
# Risk Manager

## Role
Risk assessment and position sizing — integrated into validator and guardian pipelines

## Model
N/A (logic embedded in validator + guardian)

## Type
risk

## MCP Tools
(none — risk logic embedded in validator pipeline and guardian threat scoring)

## Capabilities
2% max account risk per trade, Kelly criterion sizing, correlated pair exposure limits, spread awareness, margin monitoring

## Registered Skills
(embedded in validator 4-step pipeline and guardian threat scoring)

## Notes
Risk management is distributed: validator gates entry risk, guardian manages open position risk. Not a standalone LLM agent — logic is in code.

## Skills
- risk_assessment
- exposure_calculation
- position_sizing
