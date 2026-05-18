---
name: db-migration
description: Safely migrate database schemas — add columns, create tables, rename fields, move data between databases, and track schema versions. Use when the user mentions "add a column," "create table," "alter table," "schema change," "database migration," "migrate data," "rename column," "add index," "drop table," "schema update," "move data from X to Y," "consolidate databases," "merge tables," "upgrade schema," "migration script," or any structural change to an existing database. Covers SQLite, PostgreSQL, and MySQL. For querying existing data, see db-explorer. For database problems, see db-troubleshoot. For designing new schemas from scratch, see db-design.
---

# Database Migration

Safe, reversible schema changes with backup-first discipline.

## Workflow

1. **Analyze current state** — Read existing schema before changing anything
2. **Back up** — Copy database or create savepoint before destructive changes
3. **Plan forward migration** — Write the change SQL
4. **Plan rollback** — Write the reverse SQL
5. **Execute** — Run the migration
6. **Verify** — Confirm change took effect, data intact

## Backup Patterns

### SQLite — File Copy

```python
import shutil
from datetime import datetime
backup = f"{db_path}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
shutil.copy2(db_path, backup)
```

### SQLite — Online Backup API

```python
import sqlite3
source = sqlite3.connect(db_path)
backup = sqlite3.connect(backup_path)
source.backup(backup)
backup.close(); source.close()
```

### PostgreSQL

```bash
pg_dump -Fc dbname > backup_$(date +%Y%m%d_%H%M%S).dump
```

## Common Migrations

### Add Column

```sql
-- SQLite
ALTER TABLE users ADD COLUMN email TEXT DEFAULT '';

-- PostgreSQL
ALTER TABLE users ADD COLUMN email VARCHAR(255) DEFAULT '' NOT NULL;
```

### Add Index

```sql
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
-- PostgreSQL concurrent (no table lock):
CREATE INDEX CONCURRENTLY idx_users_email ON users(email);
```

### Create Table

```sql
-- SQLite
CREATE TABLE IF NOT EXISTS audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    table_name TEXT NOT NULL,
    action TEXT NOT NULL,
    row_id INTEGER,
    changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Rename Column

```sql
-- SQLite 3.25+, PostgreSQL, MySQL
ALTER TABLE users RENAME COLUMN old_name TO new_name;
```

### Move Data Between SQLite Databases

```python
import sqlite3
target = sqlite3.connect(target_path)
target.execute(f"ATTACH DATABASE '{source_path}' AS src")
target.execute("CREATE TABLE IF NOT EXISTS t AS SELECT * FROM src.t")
target.execute("DETACH DATABASE src")
target.commit(); target.close()
```

## SQLite Recreate Pattern

For operations SQLite can't do directly (change type, drop column pre-3.35):

```sql
CREATE TABLE users_new (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    email TEXT NOT NULL DEFAULT ''
);
INSERT INTO users_new (id, name, email) SELECT id, name, email FROM users;
DROP TABLE users;
ALTER TABLE users_new RENAME TO users;
-- Recreate indexes after rename
```

## Schema Version Tracking

```sql
CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER PRIMARY KEY,
    description TEXT NOT NULL,
    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
-- Check: SELECT MAX(version) FROM schema_version;
-- Record: INSERT INTO schema_version (version, description) VALUES (1, 'Add email column');
```

## Safety Rules

- **Always back up** before DROP, ALTER with data loss, or DELETE.
- **Test on a copy first** for production databases.
- **Verify row counts** before and after data moves.
- **Use transactions** — wrap multi-step migrations in BEGIN/COMMIT.
- **Never assume column order** — name columns in INSERT...SELECT.
- **Check foreign keys** before dropping or renaming tables.

## Verification

```sql
-- Confirm schema
PRAGMA table_info('table_name');  -- SQLite
\d table_name                     -- PostgreSQL

-- Confirm counts and spot-check
SELECT COUNT(*) FROM table_name;
SELECT * FROM table_name LIMIT 5;
```

## Cross-Skill References

- Explore DB first → `db-explorer`
- Database locked during migration → `db-troubleshoot`
- Design new schema → `db-design`
- Complex data transformation queries → `sql-queries`
