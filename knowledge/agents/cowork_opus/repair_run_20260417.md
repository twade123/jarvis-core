# Connection Doctor Repair Run — 2026-04-17T19:57Z

**Agent**: cowork_opus (scheduled)
**Result**: Root-cause code fix applied; 85 stale queue items categorized; DB cleanup deferred to host

## Headline finding

The repair queue had grown to **85 pending items** (from empty on 2026-04-09) because
`connection_doctor/cycle.py::_run_api_sentry` — unlike `_run_db_sentry` and
`_run_mcp_sentry` — did **not** consult `expected_state` before raising alerts.
That meant on-demand services (mlx_cto, mlx_cso, mlx_cro, ollama) kept generating
API_ERROR warnings every time they were idle, and each sentry cycle left a new
queue row even after `incident_commander` auto-resolved the incident.

Prior repair runs (see `learnings.md` 2026-04-14) had already flagged this fix:
"api_sentry should exempt MLX/Ollama from warning status when idle-exit is
expected behavior." This run implemented it.

## Code fix applied

File: `connection_doctor/cycle.py` → `_run_api_sentry`

Before: raised `API_ERROR` alerts for any endpoint reporting `down` or `error`.

After: looks up `expected_state` for the target and **skips the alert** when
`mode in ('on_demand', 'disabled')`. Unknown/missing rows preserve the old
behavior (alert by default), so oanda / serve_ui / trade_scout / redis still
get flagged.

```python
def _run_api_sentry(self, flight, cd_db) -> dict:
    from connection_doctor.skills.api import check_endpoints
    from connection_doctor.skills.schedule import check_expected_state
    apis = check_endpoints()
    alerts = 0
    for api in apis:
        if isinstance(api, dict) and api.get("status") in ("down", "error"):
            name = api.get("name", "unknown")
            state = check_expected_state(cd_db, target=name)
            if state.get("mode") in ("on_demand", "disabled"):
                continue
            from connection_doctor.skills.alerts import raise_alert
            raise_alert(cd_db, flight, target=name,
                        severity="warning", detected_by="api_sentry",
                        stage="API_ERROR", details=api)
            alerts += 1
    return {"total": len(apis), "alerts": alerts}
```

Tested via `importlib.reload(cycle)` — module parses clean. Unit-checked
against the live `expected_state` table:

| target   | mode          | suppressed now? |
|----------|---------------|-----------------|
| mlx_cto  | on_demand     | yes             |
| mlx_cso  | on_demand     | yes             |
| ollama   | on_demand     | yes             |
| mlx_cro  | unknown (no row) | **no** — needs expected_state row, see cleanup script |
| oanda    | unknown       | no (correct — external API)   |
| serve_ui | unknown       | no (correct — always-on)      |

## Pending queue cleanup (85 items)

Written to `/Forex Trading Team/connection_doctor_cleanup_20260417.py` for
Tim's Mac to run. Categorization:

| Category | Count | Disposition |
|---|---:|---|
| Stale (incident already resolved by commander) | 80 | `skipped` — "incident already resolved; stale queue entry" |
| Open on_demand (mlx_cto, mlx_cso, ollama) | 3 | `skipped`; incidents marked `resolved` ("idle per expected_state on_demand") |
| Open oanda (SSL handshake timeout) | 1 | `skipped`; incident left open for host's next probe to auto-heal |
| CLAUDE.md README_STALE | 1 | `skipped` — same 8 paths as qid=14, needs Tim review |

The script also inserts `expected_state(mlx_cro, on_demand)` so the third MLX
server stops generating alerts post-patch.

## Why the Cowork agent didn't apply the DB updates itself

Same as prior runs: SQLite writes against `~/Jarvis/Database/v2/connection_doctor.db`
from this virtiofs mount fail with `disk I/O error` — even no-op creates on new
.db files in the same directory fail. File writes to `.py` / `.md` files in
the same tree work fine, which is why the code fix above landed cleanly.

The `.py` cleanup script is idempotent (every UPDATE has `status='pending'`
guard) and the host's own auto-heal rate is 80.95% over 24h, so leaving the
queue in its current state until Tim runs the script is low-risk.

## System Health Snapshot

Read-only snapshot from sandbox (localhost checks all fail here — actual
host values will differ for MCP/API/SSE):

| Domain | Total | Healthy | Notes |
|---|---:|---:|---|
| Database | 111 | 104 | 6 degraded, 1 down — all historical corrupted/disabled entries |
| API (from sandbox) | 15 | 0 | All localhost down in sandbox; host view is the truth |
| MCP (from sandbox) | 35 | 0 | Sandbox can't reach host MCPs |
| SSE | — | — | not reachable from sandbox |
| Tokens | 6 | 0 | all "unknown" status without creds in sandbox |

- **Open incidents**: 4 (mlx_cso #253, mlx_cto #251, ollama #252, oanda #250)
- **Auto-heal rate (24h)**: 80.95%

## Actions Tim should take

1. `python3 ~/Forex\ Trading\ Team/connection_doctor_cleanup_20260417.py`
   — applies the 85-item queue cleanup and the `mlx_cro` expected_state row.
2. `pkill -f serve_ui.py` — watchdog restarts it within 15s with the new
   api_sentry logic in place.
3. Optional: decide whether `oanda` should have `expected_state(market_hours)`
   so weekend TLS timeouts don't alert.
4. Optional: review the 8 stale CLAUDE.md path references (logged under
   incident #14 / #198).

## Sentry Status (from agent_activity, last 10 minutes)

All sentries are cycling normally on the host: db_sentry, api_sentry,
mcp_sentry, sse_sentry, token_sentry, incident_commander, schedule_manager,
reporter — all reporting `status=ok`.
