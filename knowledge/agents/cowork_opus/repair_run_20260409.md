# Connection Doctor Repair Run — 2026-04-09T12:02Z

**Agent**: cowork_opus (scheduled)
**Result**: No repairs needed

## Repair Queue
Empty — no pending items.

## Open Incidents (4)
| ID | Target | Severity | Stage | Detected |
|----|--------|----------|-------|----------|
| 136 | oanda | warning | API_ERROR | 2026-04-09 03:57 |
| 135 | mlx_cso | warning | API_ERROR | 2026-04-08 19:49 |
| 134 | ollama | warning | API_ERROR | 2026-04-08 19:41 |
| 133 | mlx_cto | warning | API_ERROR | 2026-04-08 19:41 |

**Assessment**: All 4 open incidents are API_ERROR warnings for services expected to be idle (MLX servers are on-demand, Ollama/Oanda may not be running). These are informational, not actionable by the repair agent.

## System Health Snapshot
- **Database**: 102/107 healthy (5 degraded, 0 down) — no alerts
- **API**: 10/15 healthy, 3 down (on-demand services) — 2 alerts
- **MCP**: 35 total, 0 alerts from mcp_sentry
- **SSE**: 3 active, 0 stale
- **Tokens**: 5/6 healthy, 0 expiring
- **Auto-heal rate**: 63.6%
- **Incidents**: 136 total, 132 resolved, 4 open

## Sentry Status (all OK)
- db_sentry: 107 DBs, 102 healthy, 0 alerts
- api_sentry: 15 endpoints, 2-3 alerts (idle services)
- mcp_sentry: 35 servers, 0 alerts
- sse_sentry: 3 active, 0 stale
- token_sentry: 6 tokens, 0 expiring
- incident_commander: correlating, 0 groups found

## Actions Taken
None required — system is healthy. DB writes skipped due to sandbox read-only mount.
