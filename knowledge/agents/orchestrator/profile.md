---
type: agent
created: 2026-03-01T08:00:00
updated: 2026-03-01T08:00:00
tags: [orchestrator, coordinator, haiku]
links: [/knowledge/workspaces/forex-trading-team/]
status: active
---
# Cycle Orchestrator (CEO)

## Role
TEAM COORDINATOR (CEO) — manages 7-agent trading team, communicates status, does NOT make trade decisions

## Model
claude-3-5-haiku

## Type
coordinator

## MCP Tools
(none)

## Capabilities
Cycle readiness evaluation, risk status monitoring, operator command processing, quality control, team health tracking, pipeline narration

## Registered Skills
evaluate_cycle_readiness, make_trade_decision, get_risk_status, should_escalate_to_llm, process_operator_command, cycle_orchestration, quality_control

## Notes
Validator is the authority — orchestrator CANNOT override REJECT/WATCH verdicts. Dead LLM call removed in V3 (337 lines). Cost: ~$0.095/cycle.

## Skills
- planning
- team_coordination
- decision_making
