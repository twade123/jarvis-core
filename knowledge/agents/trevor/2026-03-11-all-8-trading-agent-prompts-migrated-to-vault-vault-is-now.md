---
type: improvement
created: 2026-03-11
tags: [vault, architecture, migration, trading-team]
agent: trevor
decomposed_from: agents/trevor/learnings.md
---

## 📈 All 8 trading agent prompts migrated to vault — vault is now single source of truth
**Date:** 2026-03-11T07:41:55
**Type:** improvement
**Tags:** vault, architecture, migration, trading-team

Migrated from Trading Bot/Prompts/ to knowledge/agents/{name}/prompt.md. team_setup._load_agent_prompt() reads vault-first with legacy fallback. vision_validator._load_system_prompt() reads vault-first. trading_cycle._load_orchestrator_prompt() reads vault-first. Shared knowledge in collective/trading-knowledge/. System is now duplicatable: new trading team = same vault brain.
