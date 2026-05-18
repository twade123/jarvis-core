---
type: improvement
created: 2026-03-18
tags: [trading, snipe, watch_manager, leaderboard, dedup, conditions_hash, annotations, validator, staleness]
agent: trevor
decomposed_from: agents/trevor/learnings.md
---

## 📈 Snipe system overhaul: conditions-hash dedup, leaderboard wired, validator watch context, annotation ownership, staleness grading
**Date:** 2026-03-18T08:16:20
**Type:** improvement
**Workspace:** workspaces/forex-trading-team
**Tags:** trading, snipe, watch_manager, leaderboard, dedup, conditions_hash, annotations, validator, staleness

Five changes to watch_manager.py, trading_cycle.py, trading_api_routes.py, snipe_cleanup.py:
1. DEDUP: create_watch() now uses conditions fingerprint hash (MD5 of sorted field:op:bucketed_value) instead of pair-based supersede. Multiple watches on same pair with different conditions all coexist. Exact same conditions = return existing watch ID, no new row. Replaces broken logic that was nuking valid co-existing watches.
2. LEADERBOARD: record_outcome() now calls _upsert_leaderboard() after every close. Aggregates win rate, total pips, trigger count per conditions_hash+instrument. snipe_leaderboard was created but never written to — now wired.
3. VALIDATOR WATCH CONTEXT: get_watches_for_validator() injected into validator prompt on clean scout cycles (not snipe-triggered cycles). Validator sees active watches for the pair, their progress, age, staleness, leaderboard history. Read-only — cannot cancel, can suggest staleness to user.
4. ANNOTATION OWNERSHIP: snipe_id FK added to user_chart_annotations. Chart render and validator only get annotations owned by triggering watch (or recent pair annotations as fallback). Clean scout cycles get zero annotations. Fixes stale annotation contamination bug.
5. STALENESS GRADE: get_active_watches() returns staleness_score (0-100), staleness_label (fresh/aging/stale/expired), age_hours, conditions_hash, direction, leaderboard stats on every watch. snipe_cleanup.py also pulls leaderboard history for CRO to use in KEEP/REMOVE decisions.

**Evidence:** Pre-fix: 1220 EUR_USD watch from March 12 (145h old) and 135 EUR_USD bias annotation from March 12 were contaminating every EUR_USD cycle. Validator was building analysis around 6-day-old markup. Also: pair-based dedup was superseding valid co-existing BUY and SELL watches on same pair.
