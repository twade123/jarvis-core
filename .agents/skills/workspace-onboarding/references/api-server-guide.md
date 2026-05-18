# Workspace API Server Guide

Flask API server pattern for Jarvis workspace dashboards. Extracted from the Forex Trading
Team `api_server.py` and `serve_ui.py`.

## Table of Contents
- [Architecture](#architecture)
- [Server Template](#server-template)
- [Core Endpoints](#core-endpoints)
- [SSE Streaming](#sse-streaming)
- [Database Access](#database-access)
- [Authentication](#authentication)
- [Deployment](#deployment)

---

## Architecture

Each workspace dashboard runs a lightweight Flask server:
- **Port**: Assign per workspace (8800 for Forex, 8766 for Trevor Desktop)
- **No heavy imports**: Read from SQLite databases directly, no Jarvis SDK imports
- **Self-bootstrap**: Auto-activates virtual environment on startup
- **Lazy loading**: Heavy components init on first access, not at startup

```
Browser (index.html)
    |
    +-- GET /api/config
    +-- GET /api/agents
    +-- GET /api/conversations
    +-- GET /api/activities
    +-- GET /api/health
    +-- POST /api/task
    +-- GET /api/stream (SSE)
    |
Flask API Server (api_server.py)
    |
    +-- workspace_shard_XX.db (conversations, activities)
    +-- workspace-specific DBs (trade_log.db, etc.)
    +-- boardroom.db (agent registry, performance)
```

---

## Server Template

```python
#!/usr/bin/env python3
"""
{Workspace Name} Dashboard API Server

Lightweight Flask API that reads workspace state from shard DB
and workspace-specific databases. No heavy jarvis imports.

Usage:
    cd ~/jarvis
    source ~/myenv/bin/activate
    python "{Workspace Name}/dashboard/api_server.py"

Opens dashboard at http://localhost:{PORT}
"""

import sqlite3
import json
import os
import time
import queue
import threading
from datetime import datetime, timezone
from pathlib import Path
from flask import Flask, send_from_directory, request, jsonify, Response, stream_with_context

# ── Paths ──
JARVIS_ROOT = Path(__file__).resolve().parent.parent.parent
WORKSPACE_ROOT = JARVIS_ROOT / "Workspace Name"
CONFIG_FILE = WORKSPACE_ROOT / "Config" / "workspace_config.json"
SHARD_DB = JARVIS_ROOT / "Database" / "workspace_shard_00.db"
BOARDROOM_DB = JARVIS_ROOT / "Database" / "boardroom.db"
DASHBOARD_DIR = Path(__file__).resolve().parent

PORT = 8801  # Assign a unique port per workspace

# ── Agent definitions (no imports needed) ──
AGENTS = {
    "orchestrator": {"role": "Coordinator", "icon": "O", "mcp": None},
    # Add your agents here
}

# ── Flask App ──
app = Flask(__name__, static_folder=str(DASHBOARD_DIR))

# ── SSE Infrastructure ──
_sse_clients = []
_sse_lock = threading.Lock()


def broadcast_event(event_type, data):
    """Send event to all connected SSE clients."""
    msg = f"event: {event_type}\ndata: {json.dumps(data)}\n\n"
    dead = []
    with _sse_lock:
        for q in _sse_clients:
            try:
                q.put_nowait(msg)
            except queue.Full:
                dead.append(q)
        for q in dead:
            _sse_clients.remove(q)


# ── Static Files ──
@app.route('/')
def index():
    return send_from_directory(str(DASHBOARD_DIR), 'index.html')


@app.route('/<path:filename>')
def static_files(filename):
    return send_from_directory(str(DASHBOARD_DIR), filename)


# ── API Endpoints ──
@app.route('/api/config')
def api_config():
    if CONFIG_FILE.exists():
        return jsonify(json.loads(CONFIG_FILE.read_text()))
    return jsonify({"error": "No config found"}), 404


@app.route('/api/agents')
def api_agents():
    return jsonify(AGENTS)


@app.route('/api/conversations')
def api_conversations():
    workspace_id = request.args.get('workspace_id')
    limit = int(request.args.get('limit', 50))
    if not SHARD_DB.exists():
        return jsonify([])
    try:
        conn = sqlite3.connect(str(SHARD_DB))
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """SELECT participant_name, participant_type, message_content,
                      phase, timestamp, event_type, metadata
               FROM workspace_conversations
               WHERE workspace_id = ?
               ORDER BY timestamp DESC LIMIT ?""",
            (workspace_id, limit)
        ).fetchall()
        conn.close()
        return jsonify([dict(r) for r in rows])
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/activities')
def api_activities():
    workspace_id = request.args.get('workspace_id')
    limit = int(request.args.get('limit', 50))
    if not SHARD_DB.exists():
        return jsonify([])
    try:
        conn = sqlite3.connect(str(SHARD_DB))
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """SELECT activity_type, activity_data, user_id, created_at
               FROM workspace_activities
               WHERE workspace_id = ?
               ORDER BY created_at DESC LIMIT ?""",
            (workspace_id, limit)
        ).fetchall()
        conn.close()
        return jsonify([dict(r) for r in rows])
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/health')
def api_health():
    return jsonify({
        "status": "ok",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "agents": len(AGENTS),
        "shard_db_exists": SHARD_DB.exists(),
    })


@app.route('/api/task', methods=['POST'])
def api_create_task():
    data = request.get_json()
    if not data or 'title' not in data:
        return jsonify({"error": "title required"}), 400

    # Create task via workspace task comments
    # (Import lazily to avoid heavy init)
    try:
        from Database.workspace_task_comments import WorkspaceTaskCommentManager
        mgr = WorkspaceTaskCommentManager()
        task_id = mgr.create_task(
            title=data['title'],
            workspace_id=data.get('workspace_id'),
            assigned_agent_id=data.get('assigned_to', 'orchestrator'),
        )
        broadcast_event('task_update', {
            'task_id': task_id,
            'title': data['title'],
            'status': 'created'
        })
        return jsonify({"task_id": task_id})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/stream')
def api_stream():
    q = queue.Queue(maxsize=100)
    with _sse_lock:
        _sse_clients.append(q)

    def generate():
        try:
            while True:
                try:
                    msg = q.get(timeout=30)
                    yield msg
                except queue.Empty:
                    yield ": keepalive\n\n"
        finally:
            with _sse_lock:
                if q in _sse_clients:
                    _sse_clients.remove(q)

    return Response(
        stream_with_context(generate()),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'X-Accel-Buffering': 'no',
            'Connection': 'keep-alive',
        }
    )


if __name__ == '__main__':
    print(f"Dashboard: http://localhost:{PORT}")
    app.run(host='0.0.0.0', port=PORT, debug=False, threaded=True)
```

---

## Core Endpoints

### Minimum Viable API
Every workspace dashboard needs at least these endpoints:

| Endpoint | Method | Returns | Source |
|----------|--------|---------|--------|
| `/api/config` | GET | Workspace config JSON | Config file |
| `/api/agents` | GET | Agent roster | Hardcoded dict |
| `/api/conversations` | GET | Agent messages | workspace_shard DB |
| `/api/activities` | GET | Activity log | workspace_shard DB |
| `/api/health` | GET | Server health status | Runtime checks |
| `/api/task` | POST | Create task for orchestrator | WorkspaceTaskCommentManager |
| `/api/stream` | GET | SSE event stream | Queue-based broadcast |

### Adding Custom Endpoints
For workspace-specific data (trade logs, analytics, etc.), add endpoints that read
from workspace-specific databases:

```python
@app.route('/api/custom-data')
def api_custom_data():
    db_path = WORKSPACE_ROOT / "Data" / "custom.db"
    if not db_path.exists():
        return jsonify([])
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    rows = conn.execute("SELECT * FROM custom_table ORDER BY created_at DESC LIMIT 50").fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])
```

---

## SSE Streaming

### Event Format
```
event: {event_type}
data: {json_payload}

```

### Standard Event Types
```python
# Agent completed a task step
broadcast_event('agent_activity', {
    'agent': 'technical_analyst',
    'action': 'analysis_complete',
    'details': {'pair': 'EUR_USD', 'signal': 'bullish'},
    'timestamp': time.time()
})

# Task status changed
broadcast_event('task_update', {
    'task_id': 42,
    'status': 'completed',
    'agent': 'validator',
    'result': 'APPROVED'
})

# New conversation message
broadcast_event('conversation', {
    'from': 'orchestrator',
    'content': 'Analysis cycle complete. 2 signals approved.',
    'timestamp': time.time()
})

# Workspace health change
broadcast_event('workspace_status', {
    'status': 'healthy',
    'agents_active': 8,
    'tasks_pending': 3
})
```

---

## Database Access

### Pattern: Direct SQLite reads (no ORM)
```python
def query_db(db_path, sql, params=(), one=False):
    """Simple DB query helper."""
    if not Path(db_path).exists():
        return None if one else []
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(sql, params).fetchall()
        return dict(rows[0]) if one and rows else [dict(r) for r in rows]
    except Exception as e:
        return {"error": str(e)}
    finally:
        conn.close()
```

### Key Databases
- **Workspace shard**: `Database/workspace_shard_00.db` — conversations, activities
- **Boardroom**: `Database/boardroom.db` — agent_registry, agent performance
- **Workspace-specific**: `{Workspace}/Data/*.db` — domain data

---

## Authentication

### Local Development (auto-login)
```python
@app.before_request
def check_auth():
    # Skip auth for static files and health check
    if request.path in ['/', '/api/health'] or not request.path.startswith('/api/'):
        return None

    # Auto-login on localhost
    if request.remote_addr in ('127.0.0.1', '::1'):
        return None

    # Token check for remote access
    token = request.args.get('token') or request.headers.get('Authorization', '').replace('Bearer ', '')
    if not token:
        return jsonify({"error": "unauthorized"}), 401
```

---

## Deployment

### Starting the Server
```bash
cd ~/jarvis
source ~/myenv/bin/activate
python "{Workspace Name}/dashboard/api_server.py"
```

### Port Allocation
| Workspace | Port |
|-----------|------|
| Trevor Desktop (serve_ui.py) | 8766 |
| Forex Trading Team | 8800 |
| New workspaces | 8801+ |

### Logging
```python
import logging
from logging.handlers import RotatingFileHandler

LOG_DIR = WORKSPACE_ROOT / "logs"
LOG_DIR.mkdir(exist_ok=True)

handler = RotatingFileHandler(
    LOG_DIR / "api_server.log",
    maxBytes=10*1024*1024,  # 10MB
    backupCount=5
)
logging.basicConfig(level=logging.INFO, handlers=[handler])
```
