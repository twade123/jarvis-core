---
name: db-design
description: Design database schemas for new projects or features — table structure, relationships, data types, indexes, normalization, and connection patterns. Use when the user mentions "design a database," "create a schema," "database architecture," "data model," "entity relationship," "ER diagram," "normalize," "what tables do I need," "database structure," "how should I store," "schema design," "plan the database," "new database," or asks how to structure data for a new feature or project. Covers SQLite, PostgreSQL, and MySQL with best practices for each. For changing existing schemas, see db-migration. For exploring existing databases, see db-explorer. For database problems, see db-troubleshoot.
---

# Database Design

Design clean, maintainable schemas for any project.

## Design Workflow

1. **Identify entities** — What things does the system store?
2. **Define relationships** — 1:1, 1:N, N:M between entities
3. **Choose data types** — Right type for each column
4. **Normalize** — Eliminate redundancy (aim 3NF, denormalize deliberately)
5. **Add indexes** — Columns in WHERE, JOIN, ORDER BY
6. **Add constraints** — NOT NULL, UNIQUE, CHECK, FOREIGN KEY
7. **Plan for growth** — Data volume, query patterns, future needs

## Choosing a Database

| Need | Best fit |
|---|---|
| Single-user, embedded, local | **SQLite** |
| Multi-user web app, complex queries | **PostgreSQL** |
| High-throughput, replication | **MySQL/MariaDB** |
| Time-series, metrics | **TimescaleDB** or **InfluxDB** |
| Document-oriented, flexible schema | **MongoDB** |

## SQLite Setup

```sql
-- Always set these PRAGMAs at connection time
PRAGMA journal_mode = WAL;
PRAGMA busy_timeout = 5000;
PRAGMA foreign_keys = ON;
PRAGMA synchronous = NORMAL;
```

### SQLite Types

| Concept | Type | Notes |
|---|---|---|
| Primary key | `INTEGER PRIMARY KEY` | Auto-increments, is rowid |
| Text | `TEXT` | No length limit needed |
| Number | `INTEGER` or `REAL` | |
| Boolean | `INTEGER` | 0/1 |
| Timestamp | `TEXT` | ISO 8601: `'2025-01-15T09:30:00Z'` |
| JSON | `TEXT` | Query with `json_extract()` |
| Binary | `BLOB` | |

### SQLite Example

```sql
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    email TEXT NOT NULL,
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS posts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    title TEXT NOT NULL,
    body TEXT NOT NULL,
    status TEXT DEFAULT 'draft' CHECK(status IN ('draft','published','archived')),
    created_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE INDEX idx_posts_user_id ON posts(user_id);
CREATE INDEX idx_posts_status ON posts(status);
```

## PostgreSQL Example

```sql
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    email VARCHAR(255) NOT NULL,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TYPE post_status AS ENUM ('draft', 'published', 'archived');

CREATE TABLE posts (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title VARCHAR(200) NOT NULL,
    body TEXT NOT NULL,
    status post_status DEFAULT 'draft',
    tags TEXT[] DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_posts_user_id ON posts(user_id);
CREATE INDEX idx_posts_tags ON posts USING GIN(tags);
CREATE INDEX idx_users_metadata ON users USING GIN(metadata);
```

## Relationship Patterns

### One-to-Many

```sql
CREATE TABLE posts (
    user_id INTEGER NOT NULL REFERENCES users(id),
    ...
);
```

### Many-to-Many

```sql
CREATE TABLE user_groups (
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    group_id INTEGER NOT NULL REFERENCES groups(id) ON DELETE CASCADE,
    role TEXT DEFAULT 'member',
    PRIMARY KEY (user_id, group_id)
);
```

### One-to-One

```sql
CREATE TABLE user_profiles (
    user_id INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    bio TEXT,
    avatar_url TEXT
);
```

### Self-Referencing (Tree)

```sql
CREATE TABLE categories (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    parent_id INTEGER REFERENCES categories(id) ON DELETE SET NULL
);
```

## Indexing Guidelines

**Always index:** Foreign keys, WHERE columns, JOIN columns, ORDER BY columns.

**Skip indexing:** Low-cardinality columns, tables < 1000 rows, rarely-queried columns.

**Composite indexes:**
```sql
-- For queries filtering on status AND created_at
CREATE INDEX idx_posts_status_created ON posts(status, created_at);
-- Most selective column first
```

## Normalization Quick Guide

| Form | Rule | Violation example |
|---|---|---|
| **1NF** | Atomic values, no repeating groups | `tags: "a,b,c"` → use separate table |
| **2NF** | No partial dependencies on composite PK | Product name on order line |
| **3NF** | No transitive dependencies | City + zip on same table |

**When to denormalize:** Read-heavy workloads, caching computed values, historical snapshots. Always document intentional denormalization.

## Python Connection Patterns

```python
# SQLite
import sqlite3
def get_connection(db_path):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA busy_timeout = 5000")
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

with get_connection("app.db") as conn:
    conn.execute("INSERT INTO users (name) VALUES (?)", ("Alice",))
```

```python
# PostgreSQL pool
from psycopg2 import pool
db_pool = pool.ThreadedConnectionPool(minconn=2, maxconn=10, dsn="...")
conn = db_pool.getconn()
try:
    with conn.cursor() as cur:
        cur.execute("INSERT INTO users (name) VALUES (%s)", ("Alice",))
    conn.commit()
finally:
    db_pool.putconn(conn)
```

## Anti-Patterns

| Bad | Why | Do instead |
|---|---|---|
| CSV in a column | Can't query/index | Separate table |
| `SELECT *` | Wastes bandwidth | Name columns |
| No foreign keys | Orphaned data | Always define FKs |
| Money as FLOAT | Rounding errors | INTEGER (cents) or DECIMAL |
| God table (100+ cols) | Slow, unmaintainable | Split into related tables |
| No timestamps | Can't audit | Add `created_at`, `updated_at` |

## Cross-Skill References

- Implement the schema → `db-migration`
- Explore existing DB first → `db-explorer`
- Database problems → `db-troubleshoot`
- Complex analytical queries → `sql-queries`
