---
type: correction
created: 2026-03-23
tags: [TA, 9B-model, misleading, computed-facts, validator-input]
agent: log
decomposed_from: agents/claude-code/log/2026-03.md
---

## 🔧 Replaced 9B LLM TA narrative with computed factual indicator data — eliminates misleading descriptions
**Date:** 2026-03-23T11:14:31
**Type:** correction
**Tags:** TA, 9B-model, misleading, computed-facts, validator-input

> [!warning] CORRECTION
> The local 9B MLX model was generating misleading TA descriptions. Example: AUD_USD showed V-reversal from bearish grind, E21 just crossed E55, price at E100 resistance — but TA said 'bullish EMA fan stalled, no recent cross.' The 9B model reads NUMBER SNAPSHOTS not the chart, so it missed the visual story. Fix: replaced _v4_ta_narrative (9B text) and EMA Market Narrative with purely computed factual data: exact EMA values, pip distances, fan ordering from actual values, cross recency, RSI/Stoch/MACD exact levels, BB width+delta, ADX, ATR, patterns. No LLM interpretation — just facts. The validator reads the CHART IMAGE for the story and these numbers for confirmation. Section header says '(computed — no interpretation)' to be explicit.
