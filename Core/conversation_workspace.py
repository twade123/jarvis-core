"""
Conversation Workspace — auto-provisions a workspace for every OpenClaw session.

Each OpenClaw session_key gets exactly ONE workspace in workspaces.db.
The workspace:
  - Lives in workspaces.db (workspaces, workspace_tasks, workspace_agent_assignments)
  - Has workspace_type = 'conversation'
  - Has all messages written to workspace_conversations (conversations.db)
  - Has swarm agents assigned to it
  - Is scoped to one user_id — no cross-user access

Public API:
  get_or_create(session_key, user_id)         → workspace_id (int)
  write_message(workspace_id, role, content)  → None
  get_recent_messages(workspace_id, limit=10) → List[Dict]
  attach_swarm(workspace_id, swarm)           → None (async)

Architecture note (from handler_swarm.py set_workspace docstring):
  "Workspaces are INHERITED, not created by the swarm."
  This module is the owner. The swarm inherits from here.
"""

import asyncio
import logging
import os
import sqlite3
import time
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

_WORKSPACES_DB = os.path.expanduser("~/Jarvis/Database/v2/workspaces.db")
_CONVERSATIONS_DB = os.path.expanduser("~/Jarvis/Database/v2/conversations.db")

# In-process cache: session_key → workspace_id
_SESSION_WORKSPACE: Dict[str, int] = {}


# ── Public API ────────────────────────────────────────────────────────────────

def get_or_create(session_key: str, user_id: int) -> int:
    """
    Get existing workspace for this session, or create one.

    Returns:
        workspace_id (integer, workspaces.db workspaces.id)
    """
    if session_key in _SESSION_WORKSPACE:
        return _SESSION_WORKSPACE[session_key]

    conn = _connect_workspaces()
    try:
        # Check for existing workspace linked to this session
        row = conn.execute(
            """SELECT id FROM workspaces
               WHERE metadata LIKE ? AND owner_id = ? AND deleted_at IS NULL""",
            (f'%"session_key": "{session_key}"%', user_id),
        ).fetchone()

        if row:
            workspace_id = row[0]
            logger.debug("Found existing workspace %d for session %s", workspace_id, session_key[:8])
        else:
            workspace_id = _create_workspace(conn, session_key, user_id)
            logger.info("Created workspace %d for session %s (user=%d)", workspace_id, session_key[:8], user_id)

        conn.commit()
        _SESSION_WORKSPACE[session_key] = workspace_id
        return workspace_id
    finally:
        conn.close()


def write_message(
    workspace_id: int,
    role: str,
    content: str,
    participant_name: str = None,
    message_type: str = "conversation",
    phase: str = "active",
    metadata: dict = None,
):
    """
    Write a message to workspace_conversations in conversations.db.

    Args:
        workspace_id:     workspaces.db workspace id
        role:             'user' | 'assistant' | 'system' | 'agent'
        content:          message text
        participant_name: display name (optional)
        message_type:     conversation | task_creation | analysis | etc.
        phase:            active | planning | implementation | completion
        metadata:         extra JSON (optional)
    """
    import json

    conn = _connect_conversations()
    try:
        now = time.strftime("%Y-%m-%d %H:%M:%S")
        conn.execute(
            """INSERT INTO workspace_conversations
               (workspace_id, participant_id, participant_type, participant_name,
                message_content, message_type, phase, timestamp, metadata)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                workspace_id,
                0,              # participant_id (0 = system/Trevor)
                role,
                participant_name or role,
                content,
                message_type,
                phase,
                now,
                json.dumps(metadata) if metadata else None,
            ),
        )
        conn.commit()
    finally:
        conn.close()


def get_recent_messages(workspace_id: int, limit: int = 10) -> List[Dict]:
    """Return last `limit` messages from this workspace, newest last."""
    conn = _connect_conversations()
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            """SELECT participant_type as role, participant_name, message_content as content,
                      message_type, phase, timestamp
               FROM workspace_conversations
               WHERE workspace_id = ?
               ORDER BY id DESC LIMIT ?""",
            (workspace_id, limit),
        ).fetchall()
        return list(reversed([dict(r) for r in rows]))
    finally:
        conn.close()


async def attach_swarm(workspace_id: int, swarm: Any):
    """
    Bind the swarm to this workspace and assign its agents.

    Args:
        workspace_id: from get_or_create()
        swarm:        SwarmHandler instance
    """
    swarm.set_workspace(workspace_id)
    await swarm.load_workspace_mcp()

    # Assign each loaded agent to the workspace
    for agent_name, agent in swarm.agents.items():
        agent_id = getattr(agent, "agent_id", agent_name)
        await swarm._assign_agent_to_workspace(
            agent_id=agent_id,
            agent_name=agent_name,
            role="contributor",
        )
    logger.info("Swarm attached to workspace %d (%d agents)", workspace_id, len(swarm.agents))


def get_workspace_info(workspace_id: int) -> Optional[Dict]:
    """Return workspace record as dict."""
    conn = _connect_workspaces()
    conn.row_factory = sqlite3.Row
    try:
        row = conn.execute(
            "SELECT * FROM workspaces WHERE id = ?", (workspace_id,)
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def list_user_workspaces(user_id: int, limit: int = 20) -> List[Dict]:
    """List recent conversation workspaces for a user."""
    conn = _connect_workspaces()
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            """SELECT id, name, description, created_at, updated_at, status
               FROM workspaces
               WHERE owner_id = ?
                 AND workspace_type = 'conversation'
                 AND deleted_at IS NULL
               ORDER BY updated_at DESC LIMIT ?""",
            (user_id, limit),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


# ── Internal helpers ──────────────────────────────────────────────────────────

def _connect_workspaces() -> sqlite3.Connection:
    """Connect to workspaces.db (workspaces, workspace_tasks, workspace_agent_assignments)."""
    conn = sqlite3.connect(_WORKSPACES_DB)
    conn.execute("PRAGMA journal_mode=DELETE")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def _connect_conversations() -> sqlite3.Connection:
    """Connect to conversations.db (workspace_conversations)."""
    conn = sqlite3.connect(_CONVERSATIONS_DB)
    conn.execute("PRAGMA journal_mode=DELETE")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def _ensure_schema(conn: sqlite3.Connection):
    """Ensure workspace_conversations exists in conversations.db."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS workspace_conversations (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            workspace_id     INTEGER NOT NULL,
            participant_id   INTEGER DEFAULT 0,
            participant_type TEXT NOT NULL,
            participant_name TEXT,
            message_content  TEXT NOT NULL,
            message_type     TEXT DEFAULT 'conversation',
            phase            TEXT DEFAULT 'active',
            timestamp        TEXT NOT NULL,
            metadata         TEXT,
            FOREIGN KEY (workspace_id) REFERENCES workspaces(id) ON DELETE CASCADE
        )
    """)
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_wc_workspace_id ON workspace_conversations(workspace_id)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_wc_timestamp ON workspace_conversations(timestamp)"
    )


def _create_workspace(conn: sqlite3.Connection, session_key: str, user_id: int) -> int:
    import json

    # Ensure workspace_conversations schema exists in conversations.db
    conv_conn = _connect_conversations()
    _ensure_schema(conv_conn)
    conv_conn.commit()
    conv_conn.close()

    now = time.strftime("%Y-%m-%d %H:%M:%S")
    # Short human-readable name using session_key prefix
    name = f"Conversation {session_key[:8]}"
    meta = json.dumps({
        "session_key": session_key,
        "user_id":     user_id,
        "created_by":  "conversation_workspace",
    })

    conn.execute(
        """INSERT INTO workspaces
           (name, description, created_by, created_at, updated_at,
            status, workspace_type, owner_id, metadata)
           VALUES (?, ?, ?, ?, ?, 'active', 'conversation', ?, ?)""",
        (
            name,
            f"Auto-provisioned workspace for session {session_key[:8]}",
            user_id,
            now,
            now,
            user_id,
            meta,
        ),
    )
    return conn.execute("SELECT last_insert_rowid()").fetchone()[0]
