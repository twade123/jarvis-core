---
type: improvement
created: 2026-03-20
tags: [validator, prompt-redesign, synthesis, precision-snipe, audit-2026-03-20-phase3]
agent: log
decomposed_from: agents/claude-code/log/2026-03.md
---

## 📈 Validator prompt redesigned — synthesis protocol + precision snipe output
**Date:** 2026-03-20T20:00:07
**Type:** improvement
**Tags:** validator, prompt-redesign, synthesis, precision-snipe, audit-2026-03-20-phase3

Validator prompt overhauled with three major changes:

(1) Synthesis protocol runs BEFORE checklist — validator now builds a complete market story from the annotated chart picture before running the pass/fail checklist. Previous flow was checklist-first which caused premature rejection on individual indicators without considering the complete picture.

(2) Phase 2.5 TRADE_NOW verdict at score 7 — new verdict tier between WATCH and CONFIRM for high-conviction setups that meet most but not all criteria.

(3) No-chart fallback — instead of mandatory SKIP when chart is missing, validator can proceed at max score 9 (cannot CONFIRM without chart). Chart delivery retry logic added: 2 attempts with 5s delay before fallback.

(4) Precision snipe output — when confirming, validator now outputs exact entry price, invalidation level, and target with reasoning. The snipe IS the trade plan.

**Evidence:** Three prompt sections rewritten. New TRADE_NOW tier at score 7. Fallback mode max 9. Precision output format added.
