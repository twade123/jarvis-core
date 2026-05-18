---
name: flight-recorder
description: Universal observability system — a ring-buffer black box that records every stage of any pipeline, workspace, or agent operation. Use when the user mentions "flight recorder," "flight log," "pipeline visibility," "what happened in the last cycle," "show me errors," "record this stage," "wire up flight recorder," "add observability," "add flight recording," "check the flight log," "what went wrong," "pipeline audit," "stage timing," "bottleneck," "flow check," "sentry agent," "monitoring agent," or asks what happened in any automated pipeline. Also use when building new workspaces or features that need observability, when wiring new components into existing flight recorders, when building sentry/monitoring agents that watch the flight log, or when querying flight recorder data to answer user questions about system behavior.
---

# Flight Recorder

A ring-buffer audit system that records every stage of any pipeline. Think airplane black box: always recording, never growing unbounded. Each workspace or system gets its own flight recorder instance with domain-specific stages.

## Core Concepts

- **Stage**: A discrete step in a pipeline (e.g., `data_fetch`, `llm_call`, `validation`, `execution`)
- **Cycle**: A complete run through the pipeline, linked by `cycle_id`
- **Ring buffer**: Keeps last N cycles per entity, auto-purges older ones
- **Status**: Every record is `ok`, `warn`, `error`, or `skip`
- **Required fields**: Each stage declares what data it MUST include — missing fields are logged
- **Categories**: Stages are grouped into categories with independent row ceilings

## Architecture Pattern

Every flight recorder follows this structure:

```python
import sqlite3
import json
from datetime import datetime, timezone
from enum import Enum
from contextlib import contextmanager

class FlightStage(str, Enum):
    """Define stages for your pipeline. Order matters for flow checking."""
    STAGE_ONE = "stage_one"
    STAGE_TWO = "stage_two"
    STAGE_THREE = "stage_three"
    # Add stages matching your pipeline

# Expected order for flow-check validation
STAGE_ORDER = [FlightStage.STAGE_ONE, FlightStage.STAGE_TWO, FlightStage.STAGE_THREE]

# Optional stages that won't be flagged as missing
OPTIONAL_STAGES = {FlightStage.STAGE_THREE.value}

# Fields each stage MUST include in data dict
REQUIRED_FIELDS = {
    FlightStage.STAGE_ONE: ["input_count", "source"],
    FlightStage.STAGE_TWO: ["result", "confidence"],
}

# Ring buffer config
RING_SIZE = 4      # Keep last N complete cycles per entity
MAX_ROWS = 2000    # Hard ceiling — purge oldest regardless
```

## Schema

```sql
CREATE TABLE IF NOT EXISTS flight_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    stage TEXT NOT NULL,
    entity TEXT DEFAULT '',        -- the thing being processed (pair, user, workspace)
    cycle_id TEXT DEFAULT '',      -- links events within one pipeline run
    context_id TEXT DEFAULT '',    -- secondary ID (trade_id, request_id, etc.)
    status TEXT NOT NULL DEFAULT 'ok',  -- ok | warn | error | skip
    duration_ms REAL DEFAULT 0,
    data TEXT DEFAULT '{}',        -- JSON — stage-specific metrics
    note TEXT DEFAULT '',          -- human-readable summary
    missing_fields TEXT DEFAULT ''  -- auto-populated if required fields absent
);

CREATE INDEX IF NOT EXISTS idx_flight_cycle ON flight_log(cycle_id, stage);
CREATE INDEX IF NOT EXISTS idx_flight_entity_time ON flight_log(entity, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_flight_status ON flight_log(status) WHERE status IN ('warn', 'error');
```

## Recording Events

```python
recorder.record(
    stage=FlightStage.STAGE_ONE,
    entity="workspace_123",
    cycle_id="run_2026-03-23T14:00:00",
    data={"input_count": 42, "source": "api"},
    status="ok",
    duration_ms=234,
    note="Fetched 42 items from API",
)
```

**Status values:**
- `ok` — stage completed successfully
- `warn` — completed but with issues (degraded data, fallback used)
- `error` — stage failed (pipeline may continue or abort)
- `skip` — stage intentionally skipped (conditional branch)

## Querying the Flight Recorder

### Recent issues
```sql
SELECT timestamp, stage, entity, status, note
FROM flight_log
WHERE status IN ('warn', 'error')
ORDER BY timestamp DESC LIMIT 20;
```

### Full cycle trace
```sql
SELECT stage, status, duration_ms, data, note
FROM flight_log
WHERE cycle_id = ?
ORDER BY timestamp;
```

### Stage timing analysis
```sql
SELECT stage, COUNT(*) as runs,
       ROUND(AVG(duration_ms)) as avg_ms,
       ROUND(MAX(duration_ms)) as max_ms
FROM flight_log
WHERE entity = ? AND timestamp > datetime('now', '-24 hours')
GROUP BY stage ORDER BY avg_ms DESC;
```

### Pipeline funnel (drop-off analysis)
```sql
SELECT stage, COUNT(DISTINCT cycle_id) as cycles
FROM flight_log
WHERE entity = ? AND timestamp > datetime('now', '-24 hours')
GROUP BY stage
ORDER BY MIN(timestamp);
```

## Flow Checking

Validate a cycle completed all expected stages:

```python
def check_flow(self, cycle_id):
    rows = self._get_cycle_rows(cycle_id)
    seen = {r["stage"] for r in rows}
    expected = {s.value for s in STAGE_ORDER} - OPTIONAL_STAGES

    missing = expected - seen
    errors = [r for r in rows if r["status"] == "error"]

    # Check required fields
    data_gaps = []
    for r in rows:
        stage = FlightStage(r["stage"]) if r["stage"] in FlightStage._value2member_map_ else None
        if stage and stage in REQUIRED_FIELDS:
            data = json.loads(r["data"])
            missing_f = [f for f in REQUIRED_FIELDS[stage] if f not in data]
            if missing_f:
                data_gaps.append({"stage": r["stage"], "missing": missing_f})

    # Timing bottlenecks (>2x average)
    timings = [(r["stage"], r["duration_ms"]) for r in rows if r["duration_ms"]]
    avg = sum(t for _, t in timings) / max(len(timings), 1)
    bottlenecks = [s for s, t in timings if t > avg * 2]

    return {"missing_stages": list(missing), "errors": errors,
            "data_gaps": data_gaps, "bottlenecks": bottlenecks}
```

## Ring Buffer Purge

After each record, enforce the ring buffer:

```python
def _maybe_purge(self, entity):
    """Keep only last RING_SIZE complete cycles per entity."""
    cycles = conn.execute("""
        SELECT DISTINCT cycle_id FROM flight_log
        WHERE entity = ? AND cycle_id != '' AND stage = ?
        ORDER BY timestamp DESC
    """, (entity, self._end_stage)).fetchall()

    if len(cycles) > RING_SIZE:
        old = [r[0] for r in cycles[RING_SIZE:]]
        placeholders = ",".join("?" * len(old))
        conn.execute(f"DELETE FROM flight_log WHERE cycle_id IN ({placeholders})", old)
```

## Wiring Into a New System

To add flight recording to any workspace or pipeline:

1. **Define stages** — List every discrete step as a `FlightStage` enum
2. **Define stage order** — The expected sequence for flow validation
3. **Define required fields** — What data each stage MUST capture
4. **Set ring size** — How many complete cycles to keep per entity
5. **Instrument** — Add `recorder.record(...)` calls at each pipeline stage
6. **Add end marker** — Record a final stage so the purge knows when a cycle is complete

### Stage Design Guidelines

- One stage per discrete operation (not per line of code)
- Include timing (`duration_ms`) for performance-sensitive stages
- Put actionable metrics in `data` — what a sentry agent would need to decide something
- Use `note` for human-readable context that aids debugging
- Status `warn` for degraded-but-continuing, `error` for failures

## Session Metrics (Optional)

For systems that run repeated sessions (daily, hourly), add a summary table:

```sql
CREATE TABLE IF NOT EXISTS session_metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_date TEXT NOT NULL UNIQUE,
    total_runs INTEGER DEFAULT 0,
    successes INTEGER DEFAULT 0,
    failures INTEGER DEFAULT 0,
    success_rate REAL DEFAULT 0,
    avg_duration_ms REAL DEFAULT 0,
    created_at TEXT DEFAULT (datetime('now'))
);
```

## Sentry Agent Integration

Sentry agents watch the flight recorder and alert on anomalies:

```python
# Pattern for a sentry agent querying flight data
issues = recorder.get_latest_issues(limit=20)
summary = recorder.get_today_summary()
flow = recorder.check_flow(latest_cycle_id)

# Sentry checks:
# 1. Error rate spike (>10% of stages in last hour = error)
# 2. Missing stages (flow check shows gaps)
# 3. Timing anomalies (stage >3x its rolling average)
# 4. Data quality (required fields missing)
# 5. Stale cycles (no new cycle_end in expected interval)
```

## Reference Implementation

The trading forex workspace has the most mature flight recorder implementation. See `references/trading-stages.md` for the full 26-stage trading pipeline definition, category ceilings, and session metrics schema.
