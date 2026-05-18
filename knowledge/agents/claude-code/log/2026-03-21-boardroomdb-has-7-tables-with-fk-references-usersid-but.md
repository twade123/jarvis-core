---
type: discovery
created: 2026-03-21
tags: [database, users, boardroom, fk-constraint, multitenant]
agent: log
decomposed_from: agents/claude-code/log/2026-03.md
---

## 💡 boardroom.db has 7 tables with FK REFERENCES users(id) but users table lives in users.db
**Date:** 2026-03-21T13:37:48
**Type:** discovery
**Tags:** database, users, boardroom, fk-constraint, multitenant

> [!tip] DISCOVERY
> Tables affected: teams, team_members, workspace_sharing, workspace_activity, workspace_user_preferences, workspace_files, file_versions. All have FOREIGN KEY (user_id) REFERENCES users(id) but users table is in Database/users.db not boardroom.db. Causes 'no such table: main.users' on INSERT when PRAGMA foreign_keys=ON. Fixed the 3 SELECT queries (get_workspace_members, get_workspace_activity) by rewriting to avoid cross-DB JOINs and resolving usernames via _get_username()/_get_usernames_bulk() helpers that query users.db directly. The INSERT FK constraint issue needs the multitenant Phase 0-1 DB consolidation to properly resolve.
