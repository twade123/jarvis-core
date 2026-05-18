---
type: correction
created: 2026-03-23
tags: [validator, task-string, chart-first, rubber-stamping, quality]
agent: log
decomposed_from: agents/claude-code/log/2026-03.md
---

## 🔧 Fixed validator rubber-stamping TA: restructured task string to be chart-first with independent analysis
**Date:** 2026-03-23T10:09:29
**Type:** correction
**Tags:** validator, task-string, chart-first, rubber-stamping, quality

> [!warning] CORRECTION
> Validator was restating the TA package instead of doing its own chart analysis. Root cause: task string led with dense TA sections and the validator anchored on that text instead of reading the chart independently. Fix: restructured trading_cycle.py task string with 3 sections: (1) YOUR TASK — numbered instructions matching floor_chat preamble: look at chart first, form own read, cross-check TA, layer intelligence, use DB tools, give SNIPE with specific prices. (2) SUPPORTING DATA — TA sections labeled as cross-check evidence, not primary analysis. (3) RESPONSE FORMAT — JSON only, reasoning must start with 'CHART READ:'. Key instruction: 'Every pair has an opportunity forming — find it.' This matches the floor_chat chart submission preamble that produces detailed independent analysis.
