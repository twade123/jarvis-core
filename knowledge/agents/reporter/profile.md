---
type: agent
created: 2026-03-01T08:00:00
updated: 2026-03-01T08:00:00
tags: [reporter, logging, knowledge]
links: [/knowledge/workspaces/forex-trading-team/]
status: active
---
# Reporter

## Role
Trade logging, knowledge management, and performance reporting

## Model
claude-3-5-haiku

## Type
reporting

## MCP Tools
(none)

## Capabilities
Trade logging (67-column schema), decision logging, KnowledgeStore V2 (SQLite-first), cycle summaries, performance drift detection, outcome linkage (scout→trade)

## Registered Skills
generate_cycle_summary, log_trade_to_knowledge, trade_logger.log_signal, trade_logger.log_trade, knowledge_store.store_decision, knowledge_store.get_instrument_knowledge

## Notes
Outcome linkage wired in V3: scout_finding_id→trade_id. BEAR/BEARISH normalization applied. Backfills trade_decisions outcomes.

## Skills
- data_summarization
- report_generation
- communication
