---
type: correction
created: 2026-03-24
tags: [snipe, trigger, guardian, watch-timer, m1-fast, launcher, boardroom-db]
agent: log
decomposed_from: agents/claude-code/log/2026-03.md
---

## 🔧 Fixed snipe trigger pipeline: M1 fast→full escalation, watch timer logging, guardian reset DB path, launcher orphan-kill race
**Date:** 2026-03-24T09:01:24
**Type:** correction
**Tags:** snipe, trigger, guardian, watch-timer, m1-fast, launcher, boardroom-db

> [!warning] CORRECTION
> 4 fixes: (1) M1 fast check now runs full check_active_watches() immediately when all fast conditions met — closes the 5min gap where transient conditions were missed. (2) Watch timer thread now logs every check with counts — was producing zero output before. (3) position_guardian.py snipe reset after trade close was writing to trading_forex.db instead of boardroom.db — snipes never reset after trade close. (4) trading_launcher.sh _kill_orphans now snapshots PIDs before stop_service runs — prevents killing newly started scout during restart.
