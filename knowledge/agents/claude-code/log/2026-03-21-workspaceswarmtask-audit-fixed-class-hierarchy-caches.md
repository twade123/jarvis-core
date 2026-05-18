---
type: improvement
created: 2026-03-21
tags: [workspace, swarm, task, audit, indexes, persistence]
agent: log
decomposed_from: agents/claude-code/log/2026-03.md
---

## 📈 Workspace/Swarm/Task audit: fixed class hierarchy, caches, indexes, DB persistence
**Date:** 2026-03-21T13:17:22
**Type:** improvement
**Tags:** workspace, swarm, task, audit, indexes, persistence

> [!success] IMPROVEMENT
> Switched 6 files from WorkspaceSharingManager (base) to get_workspace_sharing() singleton (returns WorkspaceSharing subclass with correct add_task, history, deps). Removed dead base add_task. Initialized swarm caches in __init__ (was hasattr lazy-init race). Added 6 DB indexes. Added TaskStatusRegistry DB persistence bridge (restored 2190 tasks). Connected task comments to status tracking. Added health_check() to swarm. Fixed sqlite3 connection leaks with context managers. Removed sys.modules hack from import_helper.
