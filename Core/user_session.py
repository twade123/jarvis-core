"""
User Session — maps OpenClaw channel identities to Jarvis user_ids.

Responsibilities:
  - Resolve chat_id (e.g. "telegram:6368550107") → user_id in core.db
  - Auto-create user record on first contact
  - Cache mapping in-process (no repeated DB lookups per turn)
  - Provide user record lookup for downstream modules

Does NOT manage workspaces — that's conversation_workspace.py.
Does NOT inject context — that's jarvis_bridge.py.
"""

import os
import sqlite3
import logging
import time
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

_USERS_DB = os.path.expanduser("~/Jarvis/Database/v2/core.db")

# In-process cache: chat_id → user_id
_CACHE: Dict[str, int] = {}


def resolve_user(chat_id: str) -> int:
    """
    Resolve an OpenClaw chat_id to a Jarvis user_id.
    Creates the user record if it doesn't exist.

    Args:
        chat_id: OpenClaw channel identity, e.g. "telegram:6368550107"

    Returns:
        user_id (integer primary key in core.db)
    """
    if chat_id in _CACHE:
        return _CACHE[chat_id]

    conn = sqlite3.connect(_USERS_DB)
    conn.row_factory = sqlite3.Row
    try:
        # Look up by path field (stores chat_id as external identifier)
        row = conn.execute(
            "SELECT id FROM users WHERE path = ?", (chat_id,)
        ).fetchone()

        if row:
            user_id = row["id"]
        else:
            # New user — derive display name from chat_id
            parts = chat_id.split(":")
            channel = parts[0] if len(parts) > 1 else "unknown"
            uid_part = parts[-1]
            username = f"{channel}_{uid_part}"
            now = time.strftime("%Y-%m-%d %H:%M:%S")

            conn.execute(
                """INSERT INTO users (username, path, created_at, last_login)
                   VALUES (?, ?, ?, ?)""",
                (username, chat_id, now, now),
            )
            conn.commit()
            user_id = conn.execute(
                "SELECT id FROM users WHERE path = ?", (chat_id,)
            ).fetchone()["id"]
            logger.info("Created new user record: chat_id=%s user_id=%d", chat_id, user_id)

        _CACHE[chat_id] = user_id
        return user_id
    finally:
        conn.close()


def get_user(user_id: int) -> Optional[Dict[str, Any]]:
    """Return full user record as dict, or None if not found."""
    conn = sqlite3.connect(_USERS_DB)
    conn.row_factory = sqlite3.Row
    try:
        row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def update_last_login(user_id: int):
    """Touch last_login timestamp for a user."""
    now = time.strftime("%Y-%m-%d %H:%M:%S")
    conn = sqlite3.connect(_USERS_DB)
    try:
        conn.execute("UPDATE users SET last_login = ? WHERE id = ?", (now, user_id))
        conn.commit()
    finally:
        conn.close()


def clear_cache():
    """Clear in-process cache (for testing)."""
    _CACHE.clear()
