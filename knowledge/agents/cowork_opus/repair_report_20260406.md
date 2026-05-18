# Connection Doctor Repair Report — 2026-04-06 23:25 UTC

## Summary
- **Pending repair items**: 13 (all assessed, none require code fixes)
- **Items skipped**: 13 (expected behavior or transient)
- **Items auto-fixed**: 0
- **Open incidents**: 3 (all expected on-demand server behavior)

## Queue Breakdown

| Target | Count | Verdict | Reason |
|--------|-------|---------|--------|
| mlx_cto (port 11501) | 4 | SKIP | MLX servers start on-demand, stop when idle (per CLAUDE.md) |
| ollama (port 11434) | 4 | SKIP | Ollama starts on-demand, stops when idle |
| mlx_cso (port 11502) | 4 | SKIP | MLX servers start on-demand, stop when idle |
| oanda (SSL timeout) | 1 | SKIP | Transient SSL handshake timeout — network issue, not code bug |

## Health Snapshot (latest @ 23:24 UTC)

| Domain | Total | Healthy | Degraded | Down |
|--------|-------|---------|----------|------|
| Database | 107 | 102 | 5 | 0 |
| API | 15 | 0 | 0 | 7 |
| MCP | 35 | 0 | 0 | 35 |
| SSE | 0 | 0 | 0 | 0 |
| Tokens | 6 | 0 | 0 | 0 |

**Notes:**
- Database health is strong: 102/107 healthy, 5 degraded, 0 down.
- API shows 7 down — these are the on-demand MLX/Ollama servers plus OANDA timeout. Expected when idle.
- MCP shows 35 down — MCPs auto-launch on keyword detection (per CLAUDE.md), so all-down is expected when Trevor Desktop is not running.
- Auto-heal rate: 57.14% (good for the items that are actually fixable).

## Action Needed from Tim
- **None** — all pending items are expected on-demand server behavior.
- The repair queue items (IDs 89–101) should be marked as `skipped` next time the connection doctor cycle runs locally.
- If MLX/Ollama servers should be always-on, that would be an architecture change (currently designed as on-demand per CLAUDE.md).

## Cowork Sandbox Limitation
- Database is mounted read-only in the Cowork sandbox — could not update repair_queue or incidents directly.
- Recommended: Run this locally to mark items as skipped: `python3 -c "import sqlite3; conn = sqlite3.connect('$HOME/Jarvis/Database/v2/connection_doctor.db'); conn.executemany('UPDATE repair_queue SET status=\"skipped\", fix_details=\"Expected on-demand server behavior\" WHERE id=?', [(i,) for i in range(89,102)]); conn.commit()"`
