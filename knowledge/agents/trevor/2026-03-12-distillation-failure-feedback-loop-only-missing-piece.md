---
type: note
created: 2026-03-12
tags: [distillation, feedback-loop, failure-capture, training, todo, opus-replacement]
agent: trevor
decomposed_from: agents/trevor/learnings.md
---

## 📝 Distillation failure feedback loop — only missing piece
**Date:** 2026-03-12T07:36:24
**Type:** note
**Tags:** distillation, feedback-loop, failure-capture, training, todo, opus-replacement

Confirmed 2026-03-12: The full distillation pipeline is already built and running. Every agent outcome, CoT, Claude Code run, boardroom decision, and trading cycle is captured. The one gap is the FAILURE FEEDBACK LOOP — when the local model produces a wrong answer and a frontier model corrects it, that correction is not being systematically captured as training data. Those correction moments are the highest-signal examples. The trading system has partial scaffolding already (trade outcomes → validator training, guardian stops flagging bad entries). That pattern needs to be extended to cover general model outputs across all domains, not just trading decisions. When we return to distillation work: extend the existing trade outcome capture pattern to a general correction capture system. Any time frontier model overrides or corrects local model output, log: (1) the local model's answer, (2) the correct answer, (3) the reasoning chain that shows why it was wrong. Feed those back into training.
