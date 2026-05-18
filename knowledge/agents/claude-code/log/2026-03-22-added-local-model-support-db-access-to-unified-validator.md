---
type: improvement
created: 2026-03-22
tags: [validator, local-model, db-access, phase4]
agent: log
decomposed_from: agents/claude-code/log/2026-03.md
---

## 📈 Added local model support + DB access to unified validator
**Date:** 2026-03-22T15:06:44
**Type:** improvement
**Tags:** validator, local-model, db-access, phase4

> [!success] IMPROVEMENT
> _call_llm routes between Anthropic (vision) and local MLX model (text-only). LOCAL_MODEL_ENABLED flag controls routing. Pass 1 always uses Anthropic Opus for vision. Pass 2 can use local model when ready. Added _fetch_pair_history (flight_recorder.db) and _check_elite_playbook for DB context in evaluations.
