---
type: correction
created: 2026-03-20
tags: [watch-manager, dedup, database, bug-fix, audit-2026-03-20]
agent: log
decomposed_from: agents/claude-code/log/2026-03.md
---

## 🔧 Audit Fix 4/7: Watch deduplication missing — 34 watches across 12 pairs
**Date:** 2026-03-20T14:00:03
**Type:** correction
**Tags:** watch-manager, dedup, database, bug-fix, audit-2026-03-20

agents/watch_manager.py: No deduplication logic existed for watches. System accumulated 34 watches across 12 pairs with no dedup. EUR_GBP alone had 5 duplicate watches with overlapping conditions.

Fixed with two mechanisms: (1) Conditions hash fingerprint — same conditions on create_watch() returns existing watch ID instead of creating duplicate. (2) Max-2-per-instrument cap — when count >= 2 for a pair, expires oldest watch (status=expired_dedup) before inserting new one.

**Evidence:** Pre-fix: 34 watches, EUR_GBP had 5. Post-fix cleanup: 5 duplicates expired as expired_dedup. Max 2 per pair enforced.
