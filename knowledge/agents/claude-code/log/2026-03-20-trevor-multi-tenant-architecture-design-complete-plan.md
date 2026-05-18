---
type: architecture
created: 2026-03-20
tags: [multi-tenant, architecture, trevor, trading-platform]
agent: log
decomposed_from: agents/claude-code/log/2026-03.md
---

## 📐 Trevor multi-tenant architecture design — complete plan
**Date:** 2026-03-20T00:00:00
**Type:** architecture
**Tags:** multi-tenant, architecture, trevor, trading-platform

Full multi-tenant design created: `.planning/trevor_multitenant_architecture.md` + `.planning/trevor_architecture_map.md`

**Core finding:** Schema is ~80% multi-tenant ready. `users`, `broker_credentials`, `user_snipe_list`, `setup_trades`, `live_trades` all have `user_id` columns. What's broken is the **runtime pipeline** — `user_id` is never threaded through from route handler into TradingCycle.

**Root cause of everything:** 4 hardcoded `user_id=2` in `trading_api_routes.py` (lines 1136, 1513, 3104, 3361) + `position_guardian.py`. Fix these and multi-tenancy flows from every route.

**Critical gaps ranked:**
1. ⛔ `user_id=2` hardcoded in trading runtime — root cause of all isolation failures
2. ⛔ `trade_scout.py` uses global `user_id=2` — per-user scout instances for ≤5 users
3. ⚠️ `watch_suggestions` has no `user_id` — schema migration needed
4. ⚠️ SSE stream broadcasts to all clients — add `user_id` to `active_sse_clients` dict
5. ⚠️ Boardroom conversations have no user isolation — configurable per deployment
6. ⚠️ Admin seed resets password on every boot — `INSERT OR IGNORE` without update
7. ⚠️ `pair_last_close` cooldown is shared — re-key by `(user_id, pair)`
8. ⚠️ PositionGuardian lacks user context — pass `user_id` into constructor

**What already works (don't touch):** `broker_credentials.py` encryption (perfect), route auth `_get_authenticated_user()`, `trading_preferences` risk overrides, `user_snipe_list` schema.

**Architecture:** One server, one model pool, N user contexts. Trading cycles = cloud Claude API (no MLX RAM impact, N users supported). Boardroom = MLX inference, sequential per model seat. SQLite WAL mode + shared databases with `user_id` partitioning — don't split into per-user files.

**MLX model pool:** CRO=9B(11500), CTO=14B(11501), CSO=35B(11502), CDO=7B(11503), Coder=32B(11504)
