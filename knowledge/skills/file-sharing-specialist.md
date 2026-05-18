---
name: file-sharing-specialist
description: Specialist agent with complete mastery of file_sharing MCP tools. Handles file upload, download, transfer, and share link generation across multiple platforms including AirDrop, email, iMessage, cloud services, and network sharing.
version: 1.0.0
category: mcp-specialist
author: Claude Code Agent Skills System
triggers:
  - "upload file"
  - "download file"
  - "share file"
  - "file transfer"
  - "send file"
  - "share via email"
  - "share via message"
  - "AirDrop"
  - "shared folder"
capabilities:
  - file_upload
  - file_download
  - share_link_generation
  - transfer_management
  - airdrop_operations
  - email_attachment_sharing
  - imessage_file_sharing
  - cloud_service_integration
  - network_folder_sharing
  - bulk_recipient_sharing
  - file_validation
  - transfer_control
mcp_server: file_sharing
parent_orchestrator: mcp-domain-orchestrator
---

# File Sharing Specialist

Complete mastery of file_sharing MCP operations for comprehensive file sharing across multiple platforms and methods.

## MCP Overview

The file_sharing MCP provides enterprise-grade file sharing capabilities through the `handle_file_sharing_intent` function with support for:
- **Local sharing**: AirDrop with visibility controls and device discovery
- **Communication sharing**: Email attachments and iMessage file transfers
- **Cloud integration**: Dropbox and Google Drive upload interfaces
- **Network sharing**: SMB/AFP protocol folder sharing
- **File management**: Size validation, compatibility checking, and transfer monitoring

**Handler Location**: `~/Jarvis/Handler/handler_file_sharing.py`
**MCP Type**: Handler-based (function: `handle_file_sharing_intent`)
**Port**: 8094 (configured via SSE)

## Available Tools

### Core Sharing Operations

#### `send_files` (AirDrop Transfer)
Send file via AirDrop to nearby devices.

**Parameters:**
- `command`: "send_files"
- `file_path`: Path to file (required)
- `recipient`: Not used for basic AirDrop

**Usage Pattern:**
```
Use file_sharing MCP with send_files command to share {file_path} via AirDrop
```

#### `receive_files` (AirDrop Receiver)
Open AirDrop interface to receive files from nearby devices.

**Parameters:**
- `command`: "receive_files"

**Usage Pattern:**
```
Use file_sharing MCP with receive_files command to open AirDrop receiver
```

#### `share_via_email` (Email Attachment)
Share file as email attachment to single recipient.

**Parameters:**
- `command`: "share_via_email"
- `file_path`: Path to file (required)
- `recipient`: Email address (required)

**Usage Pattern:**
```
Use file_sharing MCP with share_via_email command to send {file_path} to {email}
```

#### `share_via_messaging` (iMessage Transfer)
Share file via iMessage to single recipient.

**Parameters:**
- `command`: "share_via_messaging"
- `file_path`: Path to file (required)
- `recipient`: iMessage address or phone number (required)

**Usage Pattern:**
```
Use file_sharing MCP with share_via_messaging command to send {file_path} to {phone_number}
```

### Bulk Operations

#### `bulk_email_share` (Multiple Email Recipients)
Share file via email to multiple recipients simultaneously.

**Parameters:**
- `command`: "bulk_email_share"
- `file_path`: Path to file (required)
- `recipient`: Comma-separated email list (required)

**Usage Pattern:**
```
Use file_sharing MCP with bulk_email_share to send {file_path} to {email1},{email2},{email3}
```

#### `bulk_message_share` (Multiple iMessage Recipients)
Share file via iMessage to multiple recipients simultaneously.

**Parameters:**
- `command`: "bulk_message_share"
- `file_path`: Path to file (required)
- `recipient`: Comma-separated phone numbers or iMessage addresses (required)

**Usage Pattern:**
```
Use file_sharing MCP with bulk_message_share to send {file_path} to {phone1},{phone2},{phone3}
```

### AirDrop Management

#### `enable_airdrop` / `disable_airdrop`
Toggle AirDrop functionality on/off.

**Parameters:**
- `command`: "enable_airdrop" or "disable_airdrop"

#### `set_airdrop_visibility`
Configure who can see this device via AirDrop.

**Parameters:**
- `command`: "set_airdrop_visibility"
- `recipient`: Visibility level ("Everyone", "Contacts Only", "No One")

**Usage Pattern:**
```
Use file_sharing MCP with set_airdrop_visibility command with recipient="Contacts Only"
```

#### `check_airdrop_status`
Check current AirDrop status and configuration.

**Parameters:**
- `command`: "check_airdrop_status"

#### `discover_airdrop_devices`
Open AirDrop to discover available nearby devices.

**Parameters:**
- `command`: "discover_airdrop_devices"

#### `airdrop_settings`
Open System Preferences to AirDrop settings panel.

**Parameters:**
- `command`: "airdrop_settings"

### Folder Management

#### `create_shared_folder`
Create new shared folder with write permissions.

**Parameters:**
- `command`: "create_shared_folder"
- `file_path`: Path for shared folder (default: ~/SharedFolder)

**Usage Pattern:**
```
Use file_sharing MCP with create_shared_folder command at {custom_path}
```

#### `remove_shared_folder`
Delete shared folder and contents.

**Parameters:**
- `command`: "remove_shared_folder"
- `file_path`: Path to shared folder (default: ~/SharedFolder)

#### `list_shared_folder_contents`
List all files in shared folder.

**Parameters:**
- `command`: "list_shared_folder_contents"
- `file_path`: Path to shared folder (default: ~/SharedFolder)

#### `set_folder_permissions`
Set Unix permissions on shared folder.

**Parameters:**
- `command`: "set_folder_permissions"
- `file_path`: Path to folder (default: ~/SharedFolder)
- `recipient`: Permission code (default: "755")

**Usage Pattern:**
```
Use file_sharing MCP with set_folder_permissions, file_path={path}, recipient="777"
```

#### `network_share_folder`
Share folder over network via SMB/AFP.

**Parameters:**
- `command`: "network_share_folder"
- `file_path`: Path to folder (default: ~/SharedFolder)
- `recipient`: Share name (default: "SharedFolder")

**Usage Pattern:**
```
Use file_sharing MCP with network_share_folder at {path} with share name {name}
```

### File Validation

#### `validate_file_size`
Check file size and compatibility with different sharing methods.

**Parameters:**
- `command`: "validate_file_size"
- `file_path`: Path to file (required)

**Returns:** Email compatibility (≤25MB), Message compatibility (≤100MB), AirDrop compatibility (unlimited)

**Usage Pattern:**
```
Use file_sharing MCP with validate_file_size command for {file_path} before sharing
```

#### `get_file_info`
Get comprehensive file information including size, type, and sharing compatibility.

**Parameters:**
- `command`: "get_file_info"
- `file_path`: Path to file (required)

**Returns:** Name, size (bytes and MB), extension, email/message/AirDrop compatibility

### Cloud Integration

#### `share_via_cloud`
Open cloud service web interface for manual file upload.

**Parameters:**
- `command`: "share_via_cloud"
- `file_path`: Path to file (required)
- `recipient`: Cloud service name ("Dropbox" or "GoogleDrive")

**Usage Pattern:**
```
Use file_sharing MCP with share_via_cloud to upload {file_path} to {Dropbox|GoogleDrive}
```

### Transfer Management

#### `cancel_transfer`
Attempt to cancel ongoing file transfer.

**Parameters:**
- `command`: "cancel_transfer"

#### `check_sharing_history`
View recent file sharing activity (basic tracking).

**Parameters:**
- `command`: "check_sharing_history"

## Common Workflows

### Workflow 1: Share File to Single Recipient
1. Validate file size: `validate_file_size` with file_path
2. Choose method based on compatibility:
   - ≤25MB → Email: `share_via_email`
   - ≤100MB → iMessage: `share_via_messaging`
   - Any size → AirDrop: `send_files`
3. Confirm completion

### Workflow 2: Bulk Share to Team
1. Get file info: `get_file_info` with file_path
2. Use bulk operation:
   - Email team: `bulk_email_share` with comma-separated emails
   - iMessage group: `bulk_message_share` with comma-separated numbers
3. Monitor transfer

### Workflow 3: Cloud Upload
1. Validate file compatibility: `validate_file_size`
2. Select cloud service (Dropbox or Google Drive)
3. Use `share_via_cloud` to open upload interface
4. Guide user to drag file to upload

### Workflow 4: Network Folder Setup
1. Create shared folder: `create_shared_folder` at desired path
2. Set appropriate permissions: `set_folder_permissions` (755 for read-only, 777 for write)
3. Enable network sharing: `network_share_folder` with custom share name
4. Verify contents: `list_shared_folder_contents`

### Workflow 5: AirDrop Configuration
1. Check current status: `check_airdrop_status`
2. Set visibility: `set_airdrop_visibility` (Everyone/Contacts Only/No One)
3. Discover devices: `discover_airdrop_devices`
4. Send file: `send_files` with file_path

## Protocol Support

### AirDrop
- Peer-to-peer wireless protocol (Bluetooth + WiFi)
- No file size limit
- Requires macOS or iOS devices
- Range: ~30 feet
- Visibility controls: Everyone, Contacts Only, No One

### Email (SMTP)
- Attachment limit: 25MB (most email servers)
- Universal compatibility
- Requires email client (Mail.app)
- Support for multiple recipients

### iMessage (Apple Messages)
- Attachment limit: 100MB
- Requires Apple ID
- Supports phone numbers and email addresses
- Group messaging compatible

### Cloud Services
- Dropbox: Manual web upload interface
- Google Drive: Manual web upload interface
- No practical size limit
- Requires internet connection

### Network Sharing (SMB/AFP)
- Server Message Block (SMB) protocol
- Apple Filing Protocol (AFP) for macOS
- Local network only
- Supports permission management

## Size Management

### File Size Limits by Method

| Method | Recommended Limit | Hard Limit | Notes |
|--------|------------------|------------|-------|
| Email | 10-20MB | 25MB | Server-dependent |
| iMessage | 50-80MB | 100MB | Network-dependent |
| AirDrop | Unlimited | None | Peer-to-peer transfer |
| Cloud | Unlimited | Account storage | Internet speed varies |
| Network Share | Unlimited | Disk space | LAN speed only |

### Validation Strategy
Always validate file size before sharing:
1. Use `validate_file_size` to check compatibility
2. Review email/message/AirDrop flags
3. Select appropriate method based on flags
4. Fall back to AirDrop or cloud for large files

## Best Practices

### Selection Strategy
1. **Small files (<25MB)**: Email for universal compatibility
2. **Medium files (25-100MB)**: iMessage for Apple ecosystem, AirDrop if nearby
3. **Large files (>100MB)**: AirDrop (nearby) or cloud services (remote)
4. **Bulk sharing**: Use bulk commands for efficiency
5. **Permanent sharing**: Network shares for continuous access

### Security Considerations
1. Set AirDrop to "Contacts Only" by default (prevent unsolicited files)
2. Use appropriate folder permissions (755 for read-only, 777 only when necessary)
3. Validate file contents before sharing
4. Use email for audit trails (delivery confirmation)
5. Disable AirDrop when not in use

### Error Recovery
1. **Transfer failure**: Check file exists, validate size, verify network
2. **Email bounce**: Verify recipient address, check attachment size
3. **AirDrop not working**: Check visibility settings, verify devices nearby
4. **Permission denied**: Check file permissions with `get_file_info`

### Performance Optimization
1. Validate before attempting transfer (avoid wasted time)
2. Use bulk operations for multiple recipients (single operation)
3. Choose method based on file size (avoid email server limits)
4. Use network shares for frequent access (avoid repeated transfers)

## Usage Examples

### Example 1: Email Large Report to Manager
```
1. Use file_sharing MCP with validate_file_size for /Users/tim/report.pdf
2. If email_compatible: Use share_via_email with recipient="manager@company.com"
3. Else: Use share_via_cloud with recipient="GoogleDrive", then email link
```

### Example 2: Share Presentation to Team via iMessage
```
Use file_sharing MCP with bulk_message_share command:
- file_path="/Users/tim/presentation.pptx"
- recipient="555-0101,555-0102,555-0103"
```

### Example 3: Setup Project Folder for Team
```
1. Use file_sharing MCP with create_shared_folder at /Users/tim/ProjectX
2. Use set_folder_permissions with file_path=/Users/tim/ProjectX, recipient="777"
3. Use network_share_folder with file_path=/Users/tim/ProjectX, recipient="ProjectX-Share"
4. Notify team of network path
```

### Example 4: Quick AirDrop to Nearby Device
```
1. Use file_sharing MCP with discover_airdrop_devices
2. Use send_files with file_path="/Users/tim/document.pdf"
3. User selects device from AirDrop interface
```

### Example 5: Validate Before Sharing
```
1. Use file_sharing MCP with get_file_info for /Users/tim/video.mp4
2. Review compatibility flags (email/message/airdrop)
3. Select method: If >100MB, use share_via_cloud with recipient="Dropbox"
4. Else use share_via_messaging with recipient="555-0100"
```

## Integration Points

### With MCP Domain Orchestrator
Report file sharing operations to MCP Domain Orchestrator for:
- Operation tracking and audit trails
- Performance monitoring (transfer speeds)
- Error aggregation and resolution
- Capacity planning (storage usage)

### With Terminal Handler
Coordinate for:
- File system operations (move, copy, rename before sharing)
- Permission verification before network sharing
- Batch file operations before bulk sharing

### With Email Handler
Coordinate for:
- Advanced email composition (custom subjects, bodies)
- Attachment management beyond basic sharing
- Email tracking and delivery confirmation

### With Finder Handler
Coordinate for:
- File location discovery before sharing
- File metadata retrieval for sharing decisions
- Folder organization before network sharing

## Troubleshooting Guide

### AirDrop Issues
- **Not discoverable**: Check `set_airdrop_visibility` is not "No One"
- **Device not found**: Use `discover_airdrop_devices`, ensure Bluetooth/WiFi on
- **Transfer fails**: Move devices closer, check AirDrop is enabled on both

### Email Issues
- **Too large**: Use `validate_file_size`, fall back to cloud or AirDrop
- **Bounce back**: Verify recipient email format is valid
- **Not sending**: Check Mail.app is configured with account

### Network Sharing Issues
- **Cannot connect**: Verify File Sharing enabled in System Preferences
- **Permission denied**: Check folder permissions with `set_folder_permissions`
- **Slow transfer**: Use wired connection, check network congestion

### General Issues
- **File not found**: Verify `file_path` is correct absolute path
- **Command not recognized**: Check command spelling, refer to available tools
- **No response**: Verify MCP server is running on port 8094

<!-- merged from skills/db-migration.md -->
name: db-migration
description: Safely migrate database schemas — add columns, create tables, rename fields, move data between databases, and track schema versions. Use when the user mentions "add a column," "create table," "alter table," "schema change," "database migration," "migrate data," "rename column," "add index," "drop table," "schema update," "move data from X to Y," "consolidate databases," "merge tables," "upgrade schema," "migration script," or any structural change to an existing database. Covers SQLite, PostgreSQL, and MySQL. For querying existing data, see db-explorer. For database problems, see db-troubleshoot. For designing new schemas from scratch, see db-design.
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
### SQLite — Online Backup API
```python
import sqlite3
source = sqlite3.connect(db_path)
backup = sqlite3.connect(backup_path)
source.backup(backup)
backup.close(); source.close()
### PostgreSQL
```bash
pg_dump -Fc dbname > backup_$(date +%Y%m%d_%H%M%S).dump
## Common Migrations
### Add Column
```sql
-- SQLite
ALTER TABLE users ADD COLUMN email TEXT DEFAULT '';
-- PostgreSQL
ALTER TABLE users ADD COLUMN email VARCHAR(255) DEFAULT '' NOT NULL;
### Add Index
```sql
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
-- PostgreSQL concurrent (no table lock):
CREATE INDEX CONCURRENTLY idx_users_email ON users(email);
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
### Rename Column
```sql
-- SQLite 3.25+, PostgreSQL, MySQL
ALTER TABLE users RENAME COLUMN old_name TO new_name;
### Move Data Between SQLite Databases
```python
import sqlite3
target = sqlite3.connect(target_path)
target.execute(f"ATTACH DATABASE '{source_path}' AS src")
target.execute("CREATE TABLE IF NOT EXISTS t AS SELECT * FROM src.t")
target.execute("DETACH DATABASE src")
target.commit(); target.close()
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
## Schema Version Tracking
```sql
CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER PRIMARY KEY,
    description TEXT NOT NULL,
    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
-- Check: SELECT MAX(version) FROM schema_version;
-- Record: INSERT INTO schema_version (version, description) VALUES (1, 'Add email column');
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
## Cross-Skill References
- Explore DB first → `db-explorer`
- Database locked during migration → `db-troubleshoot`
- Design new schema → `db-design`
- Complex data transformation queries → `sql-queries`

<!-- merged from skills/db-troubleshoot.md -->
name: db-troubleshoot
description: Diagnose and fix database problems — locked databases, connection leaks, slow queries, corruption, WAL issues, disk space, cross-database foreign key failures, and connection pool exhaustion. Use when the user mentions "database is locked," "OperationalError," "connection leak," "too many connections," "database is slow," "query timeout," "WAL," "corrupt database," "integrity check," "disk full," "database won't open," "sqlite3.OperationalError," "deadlock," "connection pool," "busy timeout," "SQLITE_BUSY," "SQLITE_LOCKED," "database malformed," "recover database," "foreign key constraint failed," or any database error message. Covers SQLite, PostgreSQL, and MySQL. For exploring database contents, see db-explorer. For schema changes, see db-migration.
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
fuser /path/to/database.db 2>/dev/null   # Who has it open?
lsof /path/to/database.db 2>/dev/null
ls -la /path/to/database.db*              # WAL/journal files?
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
PRAGMA integrity_check;  -- Full check
PRAGMA quick_check;      -- Faster, less thorough
**Recovery:**
# Dump and rebuild
sqlite3 corrupt.db ".dump" | sqlite3 recovered.db
# Or use .recover (handles more damage)
sqlite3 corrupt.db ".recover" | sqlite3 recovered.db
# Selective recovery
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
## SQLite: WAL Issues
PRAGMA journal_mode;                  -- Check current mode
PRAGMA wal_checkpoint(PASSIVE);       -- Check WAL status
PRAGMA wal_checkpoint(TRUNCATE);      -- Force flush + truncate WAL
## SQLite: Cross-DB Foreign Key Failures
**Symptom:** `FOREIGN KEY constraint failed` referencing table in another .db file.
PRAGMA foreign_key_list('problem_table');   -- See what it references
SELECT name FROM sqlite_master WHERE type='table';  -- Is reference local?
**Fixes:**
-- Disable FK enforcement (use with caution)
PRAGMA foreign_keys = OFF;
-- Or attach the other database
ATTACH DATABASE '/path/to/other.db' AS other;
## SQLite: Quick Health Check
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
## PostgreSQL: Connection Issues
-- Connections vs limit
SELECT COUNT(*) FROM pg_stat_activity;
SHOW max_connections;
-- What's using connections
SELECT datname, usename, state, COUNT(*)
FROM pg_stat_activity GROUP BY datname, usename, state;
-- Kill idle connections older than 10 min
SELECT pg_terminate_backend(pid) FROM pg_stat_activity
WHERE state = 'idle' AND query_start < NOW() - INTERVAL '10 minutes';
## PostgreSQL: Slow Queries
-- Missing indexes (sequential scans on large tables)
SELECT relname, seq_scan, idx_scan, n_live_tup
FROM pg_stat_user_tables
WHERE seq_scan > idx_scan AND n_live_tup > 10000
ORDER BY seq_scan - idx_scan DESC;
-- Explain a query
EXPLAIN (ANALYZE, BUFFERS) SELECT ...;
## PostgreSQL: Bloat
SELECT tablename, n_dead_tup, n_live_tup,
       round(n_dead_tup::numeric / NULLIF(n_live_tup, 0) * 100, 1) as dead_pct
FROM pg_stat_user_tables WHERE n_dead_tup > 1000 ORDER BY n_dead_tup DESC;
VACUUM ANALYZE table_name;
## PostgreSQL: Deadlocks
SELECT blocked.pid, blocked.query AS blocked_query,
       blocking.pid AS blocking_pid, blocking.query AS blocking_query
FROM pg_stat_activity blocked
JOIN pg_locks bl ON bl.pid = blocked.pid
JOIN pg_locks bkl ON bkl.locktype = bl.locktype AND bkl.relation = bl.relation AND bkl.pid != bl.pid
JOIN pg_stat_activity blocking ON blocking.pid = bkl.pid
WHERE NOT bl.granted;
## MySQL: Quick Checks
SHOW STATUS LIKE 'Threads_connected';
SHOW VARIABLES LIKE 'max_connections';
SHOW FULL PROCESSLIST;
## Connection Pool Pattern (Python)
from queue import Queue
class ConnectionPool:
    def __init__(self, db_path, max_size=5):
        self._pool = Queue(maxsize=max_size)
        for _ in range(max_size):
            self._pool.put(sqlite3.connect(db_path))
    def get(self):
        return self._pool.get(timeout=30)
    def put(self, conn):
        self._pool.put(conn)
- Explore database contents → `db-explorer`
- Fix the schema → `db-migration`
- Design a new database → `db-design`
