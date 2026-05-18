---
type: note
created: 2026-03-11
tags: [user_watch, architecture, scout, validator, pipeline]
agent: trevor
decomposed_from: agents/trevor/learnings.md
---

## 📝 user_watch architecture: validator sets snipe conditions → early exit → scout monitors → scout_snipe fires full pipeline
**Date:** 2026-03-11T14:21:39
**Type:** note
**Workspace:** workspaces/forex-trading-team
**Tags:** user_watch, architecture, scout, validator, pipeline

Correct flow: (1) chart submitted → user_watch cycle. (2) Gate1 bypassed — Tim's chart IS the signal. (3) Validator runs → sets snipe/watch conditions. (4) STOP — early exit before orchestrator. No trading cycle. (5) Scout monitors conditions. When met → scout_snipe fires → full pipeline → trade. Key: orchestrator + execution NEVER run on a user_watch cycle. Scout owns the trade trigger.
