#!/usr/bin/env python3
"""
Workspace Dashboard API Server — Base Template

Lightweight Flask API that reads workspace state from shard DB.
No heavy jarvis imports — just SQLite reads and SSE broadcasting.

Customize this for your workspace:
1. Update WORKSPACE_ROOT, PORT, and AGENTS
2. Add workspace-specific endpoints
3. Add workspace-specific SSE event types

Usage:
    cd ~/jarvis
    source ~/myenv/bin/activate
    python "{Workspace Name}/dashboard/api_server.py"
"""

import sqlite3
import json
import os
import time
import queue
import threading
import logging
from datetime import datetime, timezone
from pathlib import Path
from logging.handlers import RotatingFileHandler

from flask import (
    Flask, send_from_directory, request, jsonify,
    Response, stream_with_context
)

# ── Configuration (CUSTOMIZE THESE) ──────────────────────────────────────────
JARVIS_ROOT = Path(__file__).resolve().parent.parent.parent
WORKSPACE_ROOT = JARVIS_ROOT / "Workspace Name"       # <- Change this
CONFIG_FILE = WORKSPACE_ROOT / "Config" / "workspace_config.json"
SHARD_DB = JARVIS_ROOT / "Database" / "workspace_shard_00.db"
BOARDROOM_DB = JARVIS_ROOT / "Database" / "boardroom.db"
DASHBOARD_DIR = Path(__file__).resolve().parent

PORT = 8801                                             # <- Change this

# Agent definitions (no imports needed, just metadata for the UI)
AGENTS = {
    "orchestrator": {"role": "Coordinator", "icon": "O", "mcp": None},
    # Add your agents here:
    # "analyst": {"role": "Data Analysis", "icon": "A", "mcp": "handler_data_validator"},
}

# ── Logging ──────────────────────────────────────────────────────────────────
LOG_DIR = WORKSPACE_ROOT / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s: %(message)s',
    handlers=[
        RotatingFileHandler(LOG_DIR / "api_server.log", maxBytes=10*1024*1024, backupCount=5),
        logging.StreamHandler(),
    ]
)
logger = logging.getLogger(__name__)

# ── Flask App ────────────────────────────────────────────────────────────────
app = Flask(__name__, static_folder=str(DASHBOARD_DIR))

# ── SSE Infrastructure ───────────────────────────────────────────────────────
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


# ── DB Helper ────────────────────────────────────────────────────────────────
def query_db(db_path, sql, params=(), one=False):
    """Simple read-only DB query helper."""
    if not Path(db_path).exists():
        return None if one else []
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(sql, params).fetchall()
        return dict(rows[0]) if one and rows else [dict(r) for r in rows]
    except Exception as e:
        logger.error("DB query error: %s", e)
        return {"error": str(e)}
    finally:
        conn.close()


# ── Static Files ─────────────────────────────────────────────────────────────
@app.route('/')
def index():
    return send_from_directory(str(DASHBOARD_DIR), 'index.html')


@app.route('/<path:filename>')
def static_files(filename):
    return send_from_directory(str(DASHBOARD_DIR), filename)


# ── API Endpoints ────────────────────────────────────────────────────────────
@app.route('/api/config')
def api_config():
    """Return workspace configuration."""
    if CONFIG_FILE.exists():
        return jsonify(json.loads(CONFIG_FILE.read_text()))
    return jsonify({
        "workspace_name": WORKSPACE_ROOT.name,
        "workspace_id": None,
        "boardroom_mode": "dormant",
    })


@app.route('/api/agents')
def api_agents():
    """Return agent roster."""
    return jsonify(AGENTS)


@app.route('/api/conversations')
def api_conversations():
    """Get recent workspace conversations (agent messages)."""
    workspace_id = request.args.get('workspace_id')
    limit = int(request.args.get('limit', 50))
    rows = query_db(SHARD_DB,
        """SELECT participant_name, participant_type, message_content,
                  phase, timestamp, event_type, metadata
           FROM workspace_conversations
           WHERE workspace_id = ?
           ORDER BY timestamp DESC LIMIT ?""",
        (workspace_id, limit))
    return jsonify(rows)


@app.route('/api/activities')
def api_activities():
    """Get recent workspace activities."""
    workspace_id = request.args.get('workspace_id')
    limit = int(request.args.get('limit', 50))
    rows = query_db(SHARD_DB,
        """SELECT activity_type, activity_data, user_id, created_at
           FROM workspace_activities
           WHERE workspace_id = ?
           ORDER BY created_at DESC LIMIT ?""",
        (workspace_id, limit))
    return jsonify(rows)


@app.route('/api/health')
def api_health():
    """Workspace health check."""
    return jsonify({
        "status": "ok",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "agents": len(AGENTS),
        "shard_db_exists": SHARD_DB.exists(),
        "config_exists": CONFIG_FILE.exists(),
    })


@app.route('/api/task', methods=['POST'])
def api_create_task():
    """Create a task for the workspace orchestrator."""
    data = request.get_json()
    if not data or 'title' not in data:
        return jsonify({"error": "title required"}), 400

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
            'status': 'created',
            'timestamp': time.time(),
        })
        return jsonify({"task_id": task_id})
    except Exception as e:
        logger.error("Task creation failed: %s", e)
        return jsonify({"error": str(e)}), 500


@app.route('/api/stream')
def api_stream():
    """SSE event stream for real-time dashboard updates."""
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


# ── Auth Middleware ───────────────────────────────────────────────────────────
@app.before_request
def check_auth():
    """Auto-login on localhost, token check for remote."""
    if not request.path.startswith('/api/') or request.path == '/api/health':
        return None
    if request.remote_addr in ('127.0.0.1', '::1'):
        return None
    token = (request.args.get('token')
             or request.headers.get('Authorization', '').replace('Bearer ', ''))
    if not token:
        return jsonify({"error": "unauthorized"}), 401


# ── Main ─────────────────────────────────────────────────────────────────────
if __name__ == '__main__':
    logger.info("Starting workspace dashboard on port %d", PORT)
    logger.info("Dashboard: http://localhost:%d", PORT)
    app.run(host='0.0.0.0', port=PORT, debug=False, threaded=True)
