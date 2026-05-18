---
name: db-explorer
description: Explore, query, and inspect any database — discover schemas, sample data, map table relationships, check row counts, and run ad-hoc queries. Use when the user mentions "show me tables," "what's in the database," "explore the DB," "query the database," "database schema," "list tables," "describe table," "sample rows," "database overview," "how big is this table," "what columns does X have," "show me the data," "check the DB," or provides a .db/.sqlite file path. Works with SQLite, PostgreSQL, MySQL, and any database accessible via Python. For writing optimized analytical SQL, see sql-queries. For schema changes, see db-migration. For database problems, see db-troubleshoot.
---

# Database Explorer

Explore any database safely — read-only by default, with full schema discovery and data sampling.

## Workflow

1. **Identify the database** — User provides a path or connection string
2. **Discover schema** — List tables with row counts, show columns/types/keys
3. **Sample data** — Show first 5-10 rows of requested tables
4. **Answer the question** — Run targeted queries, present results clearly

## SQLite Discovery

```sql
-- List all tables with row counts
SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;
-- Then for each: SELECT COUNT(*) FROM [table_name];

-- Table schema
PRAGMA table_info('table_name');

-- Indexes and foreign keys
PRAGMA index_list('table_name');
PRAGMA foreign_key_list('table_name');

-- Database health
PRAGMA journal_mode;
PRAGMA page_count;
PRAGMA page_size;
```

## PostgreSQL Discovery

```sql
-- Tables with row estimates
SELECT schemaname, tablename, n_live_tup as est_rows
FROM pg_stat_user_tables ORDER BY n_live_tup DESC;

-- Column details
SELECT column_name, data_type, is_nullable, column_default
FROM information_schema.columns WHERE table_name = 'X' ORDER BY ordinal_position;

-- Table sizes
SELECT tablename, pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename))
FROM pg_tables WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;

-- Foreign keys
SELECT tc.constraint_name, kcu.column_name,
       ccu.table_name AS foreign_table, ccu.column_name AS foreign_column
FROM information_schema.table_constraints tc
JOIN information_schema.key_column_usage kcu ON tc.constraint_name = kcu.constraint_name
JOIN information_schema.constraint_column_usage ccu ON ccu.constraint_name = tc.constraint_name
WHERE tc.constraint_type = 'FOREIGN KEY' AND tc.table_name = 'X';
```

## MySQL Discovery

```sql
SELECT table_name, table_rows, data_length, index_length
FROM information_schema.tables WHERE table_schema = DATABASE();

DESCRIBE table_name;
SHOW INDEX FROM table_name;
```

## Python Connection Patterns

```python
# SQLite
import sqlite3
with sqlite3.connect('/path/to/db.sqlite') as conn:
    conn.row_factory = sqlite3.Row
    rows = conn.execute("SELECT * FROM table LIMIT 10").fetchall()

# PostgreSQL
import psycopg2
with psycopg2.connect("dbname=mydb user=myuser") as conn:
    with conn.cursor() as cur:
        cur.execute("SELECT * FROM table LIMIT 10")

# MySQL
import mysql.connector
conn = mysql.connector.connect(host="localhost", database="mydb")
cursor = conn.cursor(dictionary=True)
cursor.execute("SELECT * FROM table LIMIT 10")
conn.close()
```

## Safety Rules

- **Read-only by default.** Never INSERT/UPDATE/DELETE/DROP unless explicitly asked.
- Always use `LIMIT` — default 10 rows, max 100.
- Use parameterized queries for user-provided values.
- Close connections after use (context managers).
- Warn before expensive queries on databases >1GB.

## Output Format

Present small results (< 20 rows) as markdown tables. For larger results, summarize with counts, distributions, and key statistics.

## Cross-Skill References

- Complex analytical SQL → `sql-queries`
- Schema changes → `db-migration`
- Database problems → `db-troubleshoot`
- New schema design → `db-design`
