---
type: correction
created: 2026-03-11
tags: [user_watch, gate1, trading_cycle, regression, claude-code-overhaul]
agent: trevor
decomposed_from: agents/trevor/learnings.md
---

## 🔧 user_watch Gate1 bypass regression — morning overhaul (08:25 AM 2026-03-11) dropped user_watch from bypass list
**Date:** 2026-03-11T14:21:33
**Type:** correction
**Workspace:** workspaces/forex-trading-team
**Tags:** user_watch, gate1, trading_cycle, regression, claude-code-overhaul

trading_cycle.py was rewritten by Claude Code overhaul at 08:25 AM. Change: _user_requested = _triggered_by in ("user_chat", "user_watch") → only ("user_chat",). Result: Tim's chart submissions hit Gate1, validator never saw them. Fix: re-added user_watch to bypass list. Also added early exit block before Step 5 (orchestrator) — user_watch cycles should only run validator, then stop. Scout owns the trade trigger (scout_snipe), not the chat interface.

**Evidence:** Confirmed via file birth time (08:25 AM = overhaul timestamp). No git history on trading_cycle.py.
