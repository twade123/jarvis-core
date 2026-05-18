---
type: correction
created: 2026-03-20
tags: [watch-manager, database, cleanup, stale-watches, audit-2026-03-20]
agent: log
decomposed_from: agents/claude-code/log/2026-03.md
---

## 🔧 Audit Fix 6/7: Stale watches accumulating — peak_progress >= 1.0 but never completed
**Date:** 2026-03-20T14:00:05
**Type:** correction
**Tags:** watch-manager, database, cleanup, stale-watches, audit-2026-03-20

boardroom.db: Found 10 watches with peak_progress >= 1.0 (all conditions met at some point) but still status=active and never completed/expired. These watches hit their trigger conditions but the system never acted on them or cleaned them up.

Expired all 10 as expired_stale via direct SQL update. Combined with Fix 4's dedup cleanup (5 expired_dedup), total of 15 watches cleaned up in this pass.

**Evidence:** SQL query: 10 watches with peak_progress >= 1.0, status=active. Additional 5 duplicates expired_dedup. Total cleanup: 15 watches.
