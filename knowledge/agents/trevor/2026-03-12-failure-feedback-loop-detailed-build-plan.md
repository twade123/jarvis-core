---
type: note
created: 2026-03-12
tags: [distillation, feedback-loop, build-plan, correction-logger, todo]
agent: trevor
decomposed_from: agents/trevor/learnings.md
---

## 📝 Failure feedback loop — detailed build plan
**Date:** 2026-03-12T07:42:33
**Type:** note
**Tags:** distillation, feedback-loop, build-plan, correction-logger, todo

BUILD PLAN — Failure Feedback Loop for Distillation Pipeline

SCOPE: Small build, ~1 day total. Slots into existing infrastructure.

PIECE 1 — correction_logger.py (~30 lines)
- Function: log_correction(local_answer, correct_answer, reasoning_chain, domain, source)
- Writes structured JSON to vault in format distillation pipeline already reads
- Fields: timestamp, domain (trading/agent/general), local_model_output, correct_output, correction_reasoning, teacher_model (which frontier model corrected it), confidence_delta
- Lives in ~/jarvis/knowledge/ alongside vault_cli.py

PIECE 2A — Manual flag (build first, ~half day)
- Add thumbs-down / 'mark as correction' button to trading UI dashboard
- On click: opens modal showing local model's reasoning, lets Tim confirm/edit correct answer, fires correction_logger
- Also works for non-trading: a simple CLI call or chat command 'that was wrong, correct answer is X'

PIECE 2B — Auto-detection (build second, ~1 day)
- After every local model call, if a frontier model call happens on the same context within the same cycle and produces a materially different answer, auto-log as correction
- 'Materially different' = verdict changes (WATCH→REJECT) or confidence delta > 30%
- Don't auto-log if answers agree — only capture genuine disagreements

PIECE 3 — Wire into existing failure points (~2 hours)
- Guardian never-positive stop fires → pull the validator reasoning that approved the entry → call log_correction(validator_reasoning, 'entry was wrong', guardian_data)
- Already have all the data, just needs the one-liner to call the logger
- Extend same pattern to: news API failures that caused bad intelligence, wolfram misses that led to wrong macro context

PRIORITY ORDER: Piece 3 first (zero UI work, highest signal data), then Piece 2A (manual flag), then Piece 2B (auto-detect).

NOTE: Manual flagging should precede auto-detection. You want Tim in the loop on what counts as a correction before automating that judgment.
