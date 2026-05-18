---
type: note
created: 2026-03-12
tags: [snipe, cleanup, CRO, local-model, training-loop, build-plan, todo]
agent: trevor
decomposed_from: agents/trevor/learnings.md
---

## 📝 Snipe cleanup — use CRO (local 9B TA model) not hard-coded rules
**Date:** 2026-03-12T07:48:17
**Type:** note
**Tags:** snipe, cleanup, CRO, local-model, training-loop, build-plan, todo

UPDATED APPROACH: Snipe cleanup uses CRO (port 11500, Qwen3.5-9B) for the keep/remove decision instead of hard-coded rules.

WHY: CRO already does TA analysis. It gets the current market state + snipe conditions and reasons about whether the setup is still valid. Every decision it makes gets logged to flight_recorder — those become training data for distillation. Over time the model learns snipe cleanup from its own decisions.

HOW IT WORKS:
1. For each active snipe: pull snipe details (conditions, progress, age, direction, thesis) + current scout scan data for that pair (fan_state, fan_direction, story_score, bb_expanding, ADX)
2. Send to CRO with a structured prompt: 'Given this snipe setup and current market state, is this snipe still market-relevant? Answer: KEEP or REMOVE with one-line reason.'
3. Parse CRO response → keep/remove + reasoning
4. Log to flight_recorder: stage='snipe_review', pair=instrument, data={snipe_id, decision, reasoning, market_state_snapshot, model='CRO-9B'}
5. Apply: cancelled snipes set status='cancelled' with note from CRO

BUILD:
- snipe_cleanup.py — calls CRO via existing _call_local_model() pattern in wrappers.py
- API endpoint in trading_api_routes.py — /api/trading/snipe-check
- Dashboard button fires endpoint, shows CRO's decisions + reasoning before confirming
- Auto mode: runs daily at market open, auto-cancels removes, logs everything

TRAINING LOOP: flight_recorder logs accumulate CRO's snipe decisions → distillation pipeline picks them up → local model gets better at snipe triage over time. Same pattern as trade validator training.
