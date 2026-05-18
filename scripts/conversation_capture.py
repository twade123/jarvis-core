#!/usr/bin/env python3
"""
conversation_capture.py — Lightweight logger for all agent-to-agent and
human-to-agent conversations across the boardroom and trading floor.

All sources write here. build_combined_dataset.py reads from here.

DB: ~/jarvis/training_data/conversations_capture.db

Usage (import anywhere):
    from scripts.conversation_capture import log_conversation, log_turn

    # Log a full multi-turn conversation at once
    log_conversation(
        source="boardroom",          # boardroom | floor_chat | swarm | handler
        topic="EUR_USD analysis",
        turns=[
            {"role": "user", "content": "..."},
            {"role": "assistant", "content": "...", "agent": "CTO"},
        ]
    )

    # Or log individual turns as they happen
    session_id = log_turn(source="floor_chat", role="user", content="...", pair="EUR_USD")
    log_turn(source="floor_chat", role="assistant", content="...", agent="validator", session_id=session_id)
"""

import json
import sqlite3
import time
import uuid
from pathlib import Path
from typing import Optional

_DB_PATH = Path.home() / "jarvis/training_data/conversations_capture.db"
_DB_PATH.parent.mkdir(parents=True, exist_ok=True)


def _get_conn():
    conn = sqlite3.connect(str(_DB_PATH), timeout=10, check_same_thread=False)
    conn.execute("PRAGMA journal_mode=DELETE")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS conversations (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id  TEXT NOT NULL,
            source      TEXT NOT NULL,
            topic       TEXT,
            pair        TEXT,
            agent       TEXT,
            role        TEXT NOT NULL,
            content     TEXT NOT NULL,
            metadata    TEXT,
            timestamp   REAL NOT NULL,
            exported    INTEGER DEFAULT 0
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_session ON conversations(session_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_source  ON conversations(source)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_exported ON conversations(exported)")
    conn.commit()
    return conn


def log_turn(
    source: str,
    role: str,
    content: str,
    session_id: Optional[str] = None,
    topic: Optional[str] = None,
    pair: Optional[str] = None,
    agent: Optional[str] = None,
    metadata: Optional[dict] = None,
) -> str:
    """Log a single turn. Returns session_id (create or reuse)."""
    if not content or not content.strip():
        return session_id or str(uuid.uuid4())
    sid = session_id or str(uuid.uuid4())
    try:
        conn = _get_conn()
        conn.execute(
            "INSERT INTO conversations (session_id,source,topic,pair,agent,role,content,metadata,timestamp) "
            "VALUES (?,?,?,?,?,?,?,?,?)",
            (sid, source, topic, pair, agent, role, content.strip(),
             json.dumps(metadata) if metadata else None, time.time())
        )
        conn.commit()
        conn.close()
    except Exception as e:
        pass  # Never block the caller
    return sid


def log_conversation(
    source: str,
    turns: list,
    topic: Optional[str] = None,
    pair: Optional[str] = None,
    metadata: Optional[dict] = None,
):
    """Log a complete multi-turn conversation."""
    if not turns:
        return
    sid = str(uuid.uuid4())
    try:
        conn = _get_conn()
        for turn in turns:
            role = turn.get("role", "assistant")
            content = (turn.get("content") or "").strip()
            if not content:
                continue
            conn.execute(
                "INSERT INTO conversations (session_id,source,topic,pair,agent,role,content,metadata,timestamp) "
                "VALUES (?,?,?,?,?,?,?,?,?)",
                (sid, source, topic, pair,
                 turn.get("agent"), role, content,
                 json.dumps(metadata) if metadata else None, time.time())
            )
        conn.commit()
        conn.close()
    except Exception as e:
        pass


def get_unexported_as_pairs(min_turns: int = 2) -> list:
    """
    Return all unexported conversations as training pairs (messages format).
    Groups turns by session_id, builds multi-turn message lists.
    """
    try:
        conn = _get_conn()
        rows = conn.execute(
            "SELECT session_id, role, content, agent FROM conversations "
            "WHERE exported=0 ORDER BY session_id, timestamp"
        ).fetchall()
        conn.close()
    except Exception:
        return []

    # Group by session
    sessions: dict = {}
    for sid, role, content, agent in rows:
        sessions.setdefault(sid, []).append({
            "role": role,
            "content": f"[{agent}] {content}" if agent and role == "assistant" else content
        })

    pairs = []
    for sid, turns in sessions.items():
        if len(turns) < min_turns:
            continue
        # Ensure starts with user, ends with assistant
        if turns[0]["role"] != "user" or turns[-1]["role"] != "assistant":
            continue
        pairs.append({"messages": turns, "session_id": sid})
    return pairs


def mark_exported(session_ids: list):
    """Mark sessions as exported so they aren't re-included."""
    if not session_ids:
        return
    try:
        conn = _get_conn()
        placeholders = ",".join("?" * len(session_ids))
        conn.execute(f"UPDATE conversations SET exported=1 WHERE session_id IN ({placeholders})",
                     session_ids)
        conn.commit()
        conn.close()
    except Exception:
        pass


if __name__ == "__main__":
    # Status check
    try:
        conn = _get_conn()
        total = conn.execute("SELECT COUNT(*) FROM conversations").fetchone()[0]
        sources = conn.execute(
            "SELECT source, COUNT(DISTINCT session_id), COUNT(*) FROM conversations "
            "GROUP BY source ORDER BY COUNT(*) DESC"
        ).fetchall()
        unexported = conn.execute(
            "SELECT COUNT(DISTINCT session_id) FROM conversations WHERE exported=0"
        ).fetchone()[0]
        conn.close()
        print(f"Conversation capture DB: {_DB_PATH}")
        print(f"Total turns: {total} | Unexported sessions: {unexported}")
        print("By source:")
        for src, sessions, turns in sources:
            print(f"  {src}: {sessions} sessions / {turns} turns")
    except Exception as e:
        print(f"Error: {e}")
