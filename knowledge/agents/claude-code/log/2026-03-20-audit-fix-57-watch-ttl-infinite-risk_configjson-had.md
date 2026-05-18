---
type: correction
created: 2026-03-20
tags: [watch-manager, ttl, config, bug-fix, audit-2026-03-20]
agent: log
decomposed_from: agents/claude-code/log/2026-03.md
---

## 🔧 Audit Fix 5/7: Watch TTL infinite — risk_config.json had watch_ttl_hours: 0.0
**Date:** 2026-03-20T14:00:04
**Type:** correction
**Tags:** watch-manager, ttl, config, bug-fix, audit-2026-03-20

agents/watch_manager.py: risk_config.json had watch_ttl_hours: 0.0 which triggered infinite expiry calculation (expires_at set to 9999-12-31). Every watch created was effectively permanent, never auto-expiring even when conditions became irrelevant.

Fixed by defaulting TTL <= 0 to 8 hours. Now all watches auto-expire after 8h unless explicitly given a longer TTL. Also ran SQL to update 21 existing watches from infinite expiry to 8h TTL.

**Evidence:** Config: watch_ttl_hours was 0.0 → expires_at=9999-12-31. Post-fix: 21 watches updated to proper 8h expiry.
