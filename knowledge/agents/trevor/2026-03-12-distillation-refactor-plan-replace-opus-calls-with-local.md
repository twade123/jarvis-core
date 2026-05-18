---
type: note
created: 2026-03-12
tags: [distillation, 30b-model, refactor-plan, opus-replacement, architecture, training, local-models]
agent: trevor
decomposed_from: agents/trevor/learnings.md
---

## 📝 Distillation refactor plan: replace Opus calls with local 30B model
**Date:** 2026-03-12T07:20:04
**Type:** note
**Tags:** distillation, 30b-model, refactor-plan, opus-replacement, architecture, training, local-models

Tim is building a 30B model distilled from all teachers (Claude, Claude Code, Qwen, DeepSeek, Anthropic practices) with full chain-of-thought captured across every domain — trading, agent development, debugging, architecture decisions. Goal is to eventually replace Anthropic Opus API calls entirely. The model runs on local hardware (no latency, no cost, no dependency). Key architectural notes: (1) Multi-teacher CoT distillation across all domains, not just trading. (2) Every session/Claude Code run/boardroom debate/trade cycle feeds the training corpus. (3) Short term: 30B handles covered domains, frontier models cover gaps. Medium term: gap shrinks as corpus grows. Long term: Opus calls become exception-only for genuinely novel problems. CRITICAL for success: build a feedback loop that captures cases where the local model gets it wrong — failure cases are the most valuable training data. A model that can replace Opus needs to know its own blind spots. Systematically route failures back into training. This is what separates 'pretty good most of the time' from 'trustworthy at Opus level'. Distillation architecture already wired: every agent outcome, Claude Code output, Anthropic dev practice, reasoning chain captured into training pipeline.
