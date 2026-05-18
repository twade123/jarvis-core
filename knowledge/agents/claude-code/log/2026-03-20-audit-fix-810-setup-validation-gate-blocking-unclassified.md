---
type: correction
created: 2026-03-20
tags: [trading-cycle, setup-validation, signal-quality, bug-fix, audit-2026-03-20-phase2]
agent: log
decomposed_from: agents/claude-code/log/2026-03.md
---

## 🔧 Audit Fix 8/10: Setup validation gate — blocking unclassified setups from executing
**Date:** 2026-03-20T16:00:00
**Type:** correction
**Tags:** trading-cycle, setup-validation, signal-quality, bug-fix, audit-2026-03-20-phase2

agents/trading_cycle.py step 5a: Added a gate that blocks trade execution when setup_id is empty or "unknown". Root cause: scout was generating signals with no classified setup, and the system executed them anyway. On Mar 20, 2 EUR_USD trades with setup="unknown" both lost money — the system had no basis for validating these trades because there was no setup to validate against.

The gate checks setup_id before any execution logic runs. If setup_id is empty string or "unknown", the trade is rejected and logged as "setup_unknown" to flight_recorder. This ensures every executed trade has a classified, auditable setup behind it.

**Evidence:** 2 EUR_USD "unknown" setup trades on Mar 20, both losses. Post-fix: setup_unknown rejection logged to flight_recorder.
