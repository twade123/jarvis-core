---
type: correction
created: 2026-03-20
tags: [ta-agent, chart-delivery, validator-input, root-cause, audit-2026-03-20-phase3]
agent: log
decomposed_from: agents/claude-code/log/2026-03.md
---

## 🔧 TA agent root cause: raw numbers instead of annotated chart picture
**Date:** 2026-03-20T20:00:01
**Type:** correction
**Tags:** ta-agent, chart-delivery, validator-input, root-cause, audit-2026-03-20-phase3

Root cause of validator rejection: the TA agent was outputting raw indicator numbers (EMA values, RSI numbers, BB widths) instead of an annotated chart picture with structured sections. The validator prompt expects a visual chart annotation to synthesize a complete story — receiving raw numbers gave it nothing to work with. This is an INPUT problem, not an intelligence problem. The validator works perfectly when given Tim's manually annotated charts.

Fix: TA agent prompt completely redesigned. Now outputs a 6-section annotated chart picture: EMA STATE, BB STATE, CANDLE TESTS, RSI, RETRACEMENT STATUS, CASCADE PHASE. Each section is a structured annotation the validator can synthesize.

**Evidence:** Validator confirms correctly on Tim's annotated charts. Pre-fix TA output was raw numbers. Post-fix: 6-section structured annotation.
