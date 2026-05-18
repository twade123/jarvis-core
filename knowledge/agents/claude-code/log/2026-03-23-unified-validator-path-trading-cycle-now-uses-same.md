---
type: improvement
created: 2026-03-23
tags: [validator, unified, swarm-handler, agent-task, quality-parity]
agent: log
decomposed_from: agents/claude-code/log/2026-03.md
---

## 📈 Unified validator path: trading cycle now uses same SwarmHandler agent as chart submissions
**Date:** 2026-03-23T09:20:51
**Type:** improvement
**Tags:** validator, unified, swarm-handler, agent-task, quality-parity

> [!success] IMPROVEMENT
> Replaced all _call_unified_validator() calls in trading_cycle.py with _agent_task('validator', task, images=images). Both floor_chat chart submissions and trading cycle scout alerts now go through the SAME SwarmHandler → validator agent path with: same system prompt (knowledge/agents/validator/prompt.md), same MCP tools (handler_data_validator), same Claude Sonnet model with vision, same tool loop. Task string built from _validator_sections (unbiased TA). Images include teaching examples + live 3-panel chart. The old DataValidatorHandler.evaluate_with_full_context() direct call is no longer used. This ensures identical quality output regardless of whether the validator gets a user-annotated chart or a TA-generated chart.
