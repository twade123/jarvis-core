---
name: db-troubleshoot
description: Diagnose and fix database problems — locked databases, connection leaks, slow queries, corruption, WAL issues, disk space, cross-database foreign key failures, and connection pool exhaustion. Use when the user mentions "database is locked," "OperationalError," "connection leak," "too many connections," "database is slow," "query timeout," "WAL," "corrupt database," "integrity check," "disk full," "database won't open," "sqlite3.OperationalError," "deadlock," "connection pool," "busy timeout," "SQLITE_BUSY," "SQLITE_LOCKED," "database malformed," "recover database," "foreign key constraint failed," or any database error message. Covers SQLite, PostgreSQL, and MySQL. For exploring database contents, see db-explorer. For schema changes, see db-migration.
---

# Database Troubleshoot

Systematic diagnosis for common database problems.

## Diagnostic Workflow

1. **Identify symptom** — What error message or behavior?
2. **Check basics** — File exists? Permissions? Disk space?
3. **Run diagnostics** — Appropriate queries from below
4. **Identify root cause** — Match to known patterns
5. **Fix and verify**

## SQLite: "database is locked" / SQLITE_BUSY

**Diagnosis:**
```bash
fuser /path/to/database.db 2>/dev/null   # Who has it open?
lsof /path/to/database.db 2>/dev/null
ls -la /path/to/database.db*              # WAL/journal files?
```

**Fixes:**

1. **Set busy timeout** (wait instead of failing):
   ```sql
   PRAGMA busy_timeout = 30000;  -- 30 seconds
   ```

2. **Enable WAL mode** (concurrent reads during writes):
   ```sql
   PRAGMA journal_mode = WAL;
   ```

3. **Fix connection leaks** — use context managers:
   ```python
   # Always this pattern:
   with sqlite3.connect("db.sqlite") as conn:
       conn.execute("...")
   ```

4. **Flush stale WAL:**
   ```sql
   PRAGMA wal_checkpoint(TRUNCATE);
   ```

## SQLite: Corruption

**Diagnosis:**
```sql
PRAGMA integrity_check;  -- Full check
PRAGMA quick_check;      -- Faster, less thorough
```

**Recovery:**
```bash
# Dump and rebuild
sqlite3 corrupt.db ".dump" | sqlite3 recovered.db

# Or use .recover (handles more damage)
sqlite3 corrupt.db ".recover" | sqlite3 recovered.db
```

```python
# Selective recovery
import sqlite3
source = sqlite3.connect("corrupt.db")
target = sqlite3.connect("recovered.db")
for name, sql in source.execute("SELECT name, sql FROM sqlite_master WHERE type='table'"):
    try:
        target.execute(sql)
        rows = source.execute(f"SELECT * FROM [{name}]").fetchall()
        if rows:
            ph = ",".join(["?"] * len(rows[0]))
            target.executemany(f"INSERT INTO [{name}] VALUES ({ph})", rows)
        print(f"OK: {name} ({len(rows)} rows)")
    except Exception as e:
        print(f"FAIL: {name}: {e}")
target.commit()
```

## SQLite: WAL Issues

```sql
PRAGMA journal_mode;                  -- Check current mode
PRAGMA wal_checkpoint(PASSIVE);       -- Check WAL status
PRAGMA wal_checkpoint(TRUNCATE);      -- Force flush + truncate WAL
```

## SQLite: Cross-DB Foreign Key Failures

**Symptom:** `FOREIGN KEY constraint failed` referencing table in another .db file.

```sql
PRAGMA foreign_key_list('problem_table');   -- See what it references
SELECT name FROM sqlite_master WHERE type='table';  -- Is reference local?
```

**Fixes:**
```sql
-- Disable FK enforcement (use with caution)
PRAGMA foreign_keys = OFF;

-- Or attach the other database
ATTACH DATABASE '/path/to/other.db' AS other;
```

## SQLite: Quick Health Check

```python
import sqlite3, os

def diagnose(db_path):
    size_mb = os.path.getsize(db_path) / (1024 * 1024)
    print(f"Database: {db_path} ({size_mb:.1f} MB)")

    wal = f"{db_path}-wal"
    if os.path.exists(wal):
        wal_mb = os.path.getsize(wal) / (1024 * 1024)
        print(f"WAL: {wal_mb:.1f} MB {'(LARGE!)' if wal_mb > 100 else ''}")

    conn = sqlite3.connect(db_path)
    print(f"Journal: {conn.execute('PRAGMA journal_mode').fetchone()[0]}")
    print(f"FK: {'ON' if conn.execute('PRAGMA foreign_keys').fetchone()[0] else 'OFF'}")

    tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    print(f"\nTables ({len(tables)}):")
    for (name,) in tables:
        count = conn.execute(f"SELECT COUNT(*) FROM [{name}]").fetchone()[0]
        print(f"  {name}: {count:,} rows")

    print(f"\nIntegrity: {conn.execute('PRAGMA quick_check').fetchone()[0]}")
    conn.close()
```

## PostgreSQL: Connection Issues

```sql
-- Connections vs limit
SELECT COUNT(*) FROM pg_stat_activity;
SHOW max_connections;

-- What's using connections
SELECT datname, usename, state, COUNT(*)
FROM pg_stat_activity GROUP BY datname, usename, state;

-- Kill idle connections older than 10 min
SELECT pg_terminate_backend(pid) FROM pg_stat_activity
WHERE state = 'idle' AND query_start < NOW() - INTERVAL '10 minutes';
```

## PostgreSQL: Slow Queries

```sql
-- Missing indexes (sequential scans on large tables)
SELECT relname, seq_scan, idx_scan, n_live_tup
FROM pg_stat_user_tables
WHERE seq_scan > idx_scan AND n_live_tup > 10000
ORDER BY seq_scan - idx_scan DESC;

-- Explain a query
EXPLAIN (ANALYZE, BUFFERS) SELECT ...;
```

## PostgreSQL: Bloat

```sql
SELECT tablename, n_dead_tup, n_live_tup,
       round(n_dead_tup::numeric / NULLIF(n_live_tup, 0) * 100, 1) as dead_pct
FROM pg_stat_user_tables WHERE n_dead_tup > 1000 ORDER BY n_dead_tup DESC;

VACUUM ANALYZE table_name;
```

## PostgreSQL: Deadlocks

```sql
SELECT blocked.pid, blocked.query AS blocked_query,
       blocking.pid AS blocking_pid, blocking.query AS blocking_query
FROM pg_stat_activity blocked
JOIN pg_locks bl ON bl.pid = blocked.pid
JOIN pg_locks bkl ON bkl.locktype = bl.locktype AND bkl.relation = bl.relation AND bkl.pid != bl.pid
JOIN pg_stat_activity blocking ON blocking.pid = bkl.pid
WHERE NOT bl.granted;
```

## MySQL: Quick Checks

```sql
SHOW STATUS LIKE 'Threads_connected';
SHOW VARIABLES LIKE 'max_connections';
SHOW FULL PROCESSLIST;
```

## Connection Pool Pattern (Python)

```python
from queue import Queue
import sqlite3

class ConnectionPool:
    def __init__(self, db_path, max_size=5):
        self._pool = Queue(maxsize=max_size)
        for _ in range(max_size):
            self._pool.put(sqlite3.connect(db_path))

    def get(self):
        return self._pool.get(timeout=30)

    def put(self, conn):
        self._pool.put(conn)
```

## Cross-Skill References

- Explore database contents → `db-explorer`
- Fix the schema → `db-migration`
- Design a new database → `db-design`
