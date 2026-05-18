---
type: correction
created: 2026-03-20
tags: [snipe-list, s-codes, v4-alerts, format-mismatch, audit-2026-03-20-phase3]
agent: log
decomposed_from: agents/claude-code/log/2026-03.md
---

## 🔧 Snipe list had old S-code format — didn't match V4 alert types
**Date:** 2026-03-20T20:00:03
**Type:** correction
**Tags:** snipe-list, s-codes, v4-alerts, format-mismatch, audit-2026-03-20-phase3

The user_snipe_list in trevor_database.db contained entries using the old S-code format (S1, S5, S13, S15) which didn't match the V4 alert type format (CRITERIA_MET, BREAKOUT_CONFIRMED, REVERSAL_SIGNAL, CONTINUATION_PATTERN, etc.). Phase 2 Fix 9 (snipe list enforcement) was checking setup+pair+direction against these entries, but no match could ever succeed because the formats were incompatible.

Fix: Snipe list repopulated with 39 new entries using V4 alert type format. Old S-code entries replaced.

**Evidence:** Old format: S1/S5/S13/S15. V4 format: CRITERIA_MET/BREAKOUT_CONFIRMED/etc. 39 new entries added.
