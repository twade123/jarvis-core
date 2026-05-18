---
type: agent
created: 2026-03-01T08:00:00
updated: 2026-03-01T08:00:00
tags: [registry, master-list]
links: [/knowledge/workspaces/forex-trading-team/]
status: active
---

# Agent Registry

Master agent list. Canonical source: `boardroom.db` → `agent_registry` table.

## Forex Trading Team (team: `2676292a`)

| Agent | Model | Type | MCP Tools |
|-------|-------|------|-----------|
| oanda_data | claude-3-5-haiku | data_collection | handler_oanda |
| intelligence | claude-3-5-haiku | data_collection | handler_news_info, handler_weather, handler_wolfram |
| technical_analyst | claude-3-5-haiku | analysis | (none — pure computation) |
| validator | claude-sonnet-4.6 | validation | handler_data_validator |
| execution | claude-3-5-haiku | execution | handler_oanda |
| trade_monitor | claude-sonnet-4.5 | monitoring | handler_oanda |
| reporter | claude-3-5-haiku | reporting | (none) |
| cycle_orchestrator | claude-3-5-haiku | coordinator | (none) |

## Source
- Team setup: `~/jarvis/Forex Trading Team/Source/agents/team_setup.py`
- Agent specs: `AGENT_SPECS` list in team_setup.py
- Prompts: `~/jarvis/Forex Trading Team/Prompts/*.md`
- Skills: `~/jarvis/Forex Trading Team/Skills/*.md`
