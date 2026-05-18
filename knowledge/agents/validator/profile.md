---
type: agent
created: 2026-03-01T08:00:00
updated: 2026-03-01T08:00:00
tags: [validator, decision-maker, sonnet]
links: [/knowledge/workspaces/forex-trading-team/]
status: active
---
# Validator (Trading Authority / CTO)

## Role
TRADING AUTHORITY — sole trade decision maker with 4-step pipeline, 8.5M backtest evidence

## Model
claude-sonnet-4.6

## Type
validation

## MCP Tools
handler_data_validator

## Capabilities
4-step validation pipeline (data quality → trade quality → DB evidence → verdict), loss pattern detection, performance drift, confluence checking

## Registered Skills
run_full_validation, trade_validator.validate, validation_analyst.analyze_on_demand

## Notes
Verdicts: CONFIRM/WATCH/REJECT. WATCH/REJECT = code-level trade block — orchestrator CANNOT override. DecisionLogger: 212ms e2e. Story-aware thesis validation (not indicator stacking).

## Skills
- data_validation
- risk_assessment
- setup_evaluation
