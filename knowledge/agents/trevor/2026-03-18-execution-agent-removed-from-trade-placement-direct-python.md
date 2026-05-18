---
type: improvement
created: 2026-03-18
tags: [trading, execution, snipe_direct, llm_agent, place_market_order, reliability]
agent: trevor
decomposed_from: agents/trevor/learnings.md
---

## 📈 Execution agent removed from trade placement — direct Python place_market_order now used for all trade types
**Date:** 2026-03-18T09:58:25
**Type:** improvement
**Workspace:** workspaces/forex-trading-team
**Tags:** trading, execution, snipe_direct, llm_agent, place_market_order, reliability

The LLM execution agent added zero value at trade execution: direction, units, SL, and TP are all pre-computed before it was called. It introduced 60-second latency and could silently fail by responding in prose instead of calling place_market_order. Root cause of AUD_JPY missed SELL on 2026-03-18 at 13:18 — validator said CONFIRM, orchestrator passed to execution agent, agent responded 'I'll place the market order' in natural language without calling the tool, trade_id=null, no trade opened. AUD_JPY dropped 12.3 pips. Fix: replaced _agent_task('execution') in trading_cycle.py Step 7 with direct place_market_order() Python call — same path used by snipe_direct. Result: all trade executions now unified on one deterministic path, <1s execution time, no LLM cost, clear error on failure.

**Evidence:** AUD_JPY 2026-03-18 13:18: exec_agent_result showed 'I'll place the market order for AUD_JPY' text, tool_calls=[], trade_id=null. OANDA confirmed no trade opened. Price moved 12.3p in correct direction after miss. All 17 other trades today used snipe_direct (Python) successfully.
