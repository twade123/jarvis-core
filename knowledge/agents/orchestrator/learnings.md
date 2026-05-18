---
type: pattern
updated: 2026-03-11T07:00:49.943118
tags: [orchestrator, haiku]
---

# Cycle Orchestrator — Learnings

## ⚠️ Cannot override validator WATCH/REJECT
**Date:** 2026-03-11
**Type:** architecture_rule
Hard rule: validator WATCH/REJECT = code-level block. Orchestrator CANNOT override.
This is intentional. The validator is the trading authority, not the orchestrator.
