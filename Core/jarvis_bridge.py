"""
Jarvis Bridge — injects live Jarvis context into Trevor's awareness each turn.

This is the missing piece that connects OpenClaw (Trevor) to the Jarvis backend.
It assembles a compact (<2KB) context snapshot from:
  - Recent workspace messages (conversation thread)
  - Open workspace tasks assigned to this user
  - Trading flight recorder (last 2 cycles, recent issues)
  - System model state (RAM, which MLX seats alive)

Usage (in Trevor's system prompt assembly):
    from Core.jarvis_bridge import get_context_for_prompt
    snippet = get_context_for_prompt(user_id=2, workspace_id=920)
    # prepend snippet to system prompt

This module is READ-ONLY with respect to workspace state.
Write operations go through conversation_workspace.write_message().
"""

import asyncio
import logging
import os
import sys
import time
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

_JARVIS = os.path.expanduser("~/Jarvis")
_FLIGHT_RECORDER_DB = os.path.join(_JARVIS, "Trading Bot/Source/flight_recorder.db")
_WORKSPACES_DB = os.path.expanduser("~/Jarvis/Database/v2/workspaces.db")
_CONVERSATIONS_DB = os.path.expanduser("~/Jarvis/Database/v2/conversations.db")
_TRADING_PAIRS = ["EUR_USD", "GBP_USD", "USD_JPY", "XAU_USD"]

# ── Public API ────────────────────────────────────────────────────────────────

def get_context_for_prompt(
    user_id: int,
    workspace_id: Optional[int] = None,
    include_trading: bool = True,
    include_system: bool = True,
    max_chars: int = 2000,
) -> str:
    """
    Build a compact context string to prepend to Trevor's system prompt.

    Args:
        user_id:        Jarvis user_id (from user_session.resolve_user)
        workspace_id:   conversation workspace id (from conversation_workspace.get_or_create)
        include_trading: include trading flight recorder snapshot
        include_system:  include model/RAM state
        max_chars:       hard cap on output length

    Returns:
        Multi-line string with ===JARVIS CONTEXT=== header, or "" if nothing available.
    """
    sections: List[str] = []

    # 1. Workspace conversation thread (most recent messages)
    if workspace_id:
        thread = _get_conversation_thread(workspace_id, limit=6)
        if thread:
            sections.append("=== RECENT CONVERSATION ===")
            sections.extend(thread)

    # 2. Open workspace tasks
    tasks = _get_open_tasks(workspace_id, user_id)
    if tasks:
        sections.append("\n=== OPEN TASKS ===")
        sections.extend(tasks)

    # 3. User memory (long-term facts about this user)
    memory = _get_user_memory(user_id)
    if memory:
        sections.append("\n=== USER MEMORY ===")
        sections.extend(memory)

    # 4. Cross-session context (what we talked about in recent past sessions)
    if workspace_id:
        past = _get_cross_session_context(user_id, workspace_id)
        if past:
            sections.append("\n=== RECENT SESSION HISTORY ===")
            sections.extend(past)

    # 5. Trading flight recorder
    if include_trading:
        trading = _get_trading_snapshot()
        if trading:
            sections.append("\n=== TRADING STATUS ===")
            sections.extend(trading)

    # 6. System state
    if include_system:
        sys_state = _get_system_state()
        if sys_state:
            sections.append("\n=== SYSTEM STATE ===")
            sections.extend(sys_state)

        # 6b. Process health — only injected when actively trading.
        # Prevents cluttering non-trading sessions with infrastructure status.
        if _is_actively_trading():
            proc_issues = _get_process_health()
            if proc_issues:
                sections.append("\n=== ⚠ TRADING PROCESS ALERTS ===")
                sections.extend(proc_issues)

    if not sections:
        return ""

    raw = "\n".join(sections)
    if len(raw) > max_chars:
        raw = raw[:max_chars] + "\n[...truncated]"

    return f"\n---\n{raw}\n---\n"


async def get_context_async(
    user_id: int,
    workspace_id: Optional[int] = None,
    **kwargs,
) -> str:
    """Async wrapper for event-loop contexts."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None, lambda: get_context_for_prompt(user_id, workspace_id, **kwargs)
    )


# ── Internal: conversation thread ────────────────────────────────────────────

def _get_conversation_thread(workspace_id: int, limit: int = 6) -> List[str]:
    """Return last `limit` messages from workspace_conversations."""
    try:
        import sqlite3
        conn = sqlite3.connect(_CONVERSATIONS_DB)
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """SELECT participant_type as role, participant_name, message_content as content
               FROM workspace_conversations
               WHERE workspace_id = ?
               ORDER BY id DESC LIMIT ?""",
            (workspace_id, limit),
        ).fetchall()
        conn.close()

        msgs = list(reversed([dict(r) for r in rows]))
        lines = []
        for m in msgs:
            name = m.get("participant_name") or m.get("role", "?")
            content = (m.get("content") or "")[:120].replace("\n", " ")
            lines.append(f"  [{name}]: {content}")
        return lines
    except Exception as exc:
        logger.debug("conversation thread unavailable: %s", exc)
        return []


# ── Internal: workspace tasks ─────────────────────────────────────────────────

def _get_open_tasks(workspace_id: Optional[int], user_id: int) -> List[str]:
    """Return open tasks for the workspace or user."""
    try:
        import sqlite3
        conn = sqlite3.connect(_WORKSPACES_DB)
        conn.row_factory = sqlite3.Row

        if workspace_id:
            rows = conn.execute(
                """SELECT title, status, priority, assigned_agent_id
                   FROM workspace_tasks
                   WHERE workspace_id = ? AND status NOT IN ('completed','cancelled')
                   ORDER BY priority DESC, created_at DESC LIMIT 5""",
                (workspace_id,),
            ).fetchall()
        else:
            rows = conn.execute(
                """SELECT title, status, priority, assigned_agent_id
                   FROM workspace_tasks
                   WHERE assigned_user_id = ? AND status NOT IN ('completed','cancelled')
                   ORDER BY priority DESC, created_at DESC LIMIT 5""",
                (user_id,),
            ).fetchall()

        conn.close()

        if not rows:
            return []

        lines = []
        for t in rows:
            agent = t["assigned_agent_id"] or "unassigned"
            lines.append(f"  [{t['priority']}] {t['title']} — {t['status']} (agent: {agent})")
        return lines
    except Exception as exc:
        logger.debug("workspace tasks unavailable: %s", exc)
        return []


# ── Internal: user memory ────────────────────────────────────────────────────

def _get_user_memory(user_id: int) -> List[str]:
    """Return long-term memory facts for this user from conversations.db user_memory table."""
    try:
        import sqlite3
        conn = sqlite3.connect(_CONVERSATIONS_DB)
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """SELECT category, content FROM user_memory
               WHERE user_id = ?
               ORDER BY updated_at DESC LIMIT 10""",
            (user_id,),
        ).fetchall()
        conn.close()
        if not rows:
            return []
        lines = []
        for r in rows:
            cat = r["category"] or "general"
            content = (r["content"] or "")[:150].replace("\n", " ")
            lines.append(f"  [{cat}] {content}")
        return lines
    except Exception as exc:
        logger.debug("user memory unavailable: %s", exc)
        return []


# ── Internal: cross-session context ──────────────────────────────────────────

def _get_cross_session_context(user_id: int, current_workspace_id: int) -> List[str]:
    """
    Return titles/summaries of the 3 most recent OTHER conversation sessions for this user.
    Gives Trevor awareness of what was discussed in past sessions.
    """
    try:
        import sqlite3
        # workspaces table lives in workspaces.db; workspace_conversations in conversations.db
        ws_conn = sqlite3.connect(_WORKSPACES_DB)
        ws_conn.row_factory = sqlite3.Row
        conv_conn = sqlite3.connect(_CONVERSATIONS_DB)
        conv_conn.row_factory = sqlite3.Row

        # Get recent workspaces owned by this user (excluding the current one)
        # Exclude cron/heartbeat/system sessions — only real human conversations
        workspaces = ws_conn.execute(
            """SELECT id, name, updated_at FROM workspaces
               WHERE owner_id = ? AND workspace_type = 'conversation'
                 AND id != ? AND deleted_at IS NULL
                 AND name NOT LIKE '%cron:%'
                 AND name NOT LIKE '%heartbeat%'
                 AND name NOT LIKE '%HEARTBEAT%'
               ORDER BY updated_at DESC LIMIT 5""",
            (user_id, current_workspace_id),
        ).fetchall()

        if not workspaces:
            ws_conn.close()
            conv_conn.close()
            return []

        lines = []
        shown = 0
        for ws in workspaces:
            ws_id = ws["id"]
            ws_name = (ws["name"] or "")[:70]
            ws_date = str(ws["updated_at"] or "")[:10]

            # Get the last meaningful assistant message (skip NO_REPLY/HEARTBEAT_OK)
            last_msg = conv_conn.execute(
                """SELECT message_content FROM workspace_conversations
                   WHERE workspace_id = ? AND participant_type = 'assistant'
                     AND message_content NOT IN ('NO_REPLY', 'HEARTBEAT_OK')
                     AND length(message_content) > 20
                   ORDER BY id DESC LIMIT 1""",
                (ws_id,),
            ).fetchone()

            if not last_msg:
                continue  # Skip sessions with no real content

            summary = (last_msg["message_content"] or "")[:120].replace("\n", " ")
            lines.append(f"  [{ws_date}] {summary}")
            shown += 1
            if shown >= 3:
                break

        ws_conn.close()
        conv_conn.close()
        return lines
    except Exception as exc:
        logger.debug("cross-session context unavailable: %s", exc)
        return []


# ── Internal: trading flight recorder ────────────────────────────────────────

def _get_trading_snapshot() -> List[str]:
    """Return a brief trading status from flight_recorder."""
    if not os.path.exists(_FLIGHT_RECORDER_DB):
        return []

    try:
        sys.path.insert(0, os.path.join(_JARVIS, "Forex Trading Team/Source"))
        from flight_recorder import FlightRecorder

        fr = FlightRecorder(_FLIGHT_RECORDER_DB)
        lines = []

        # Get last 2 cycles for top pairs
        for pair in _TRADING_PAIRS[:3]:
            cycles = fr.get_cycles(pair, limit=1)
            if not cycles:
                continue
            c = cycles[0]
            status = "✅" if c["healthy"] else "⚠️"
            decision = str(c.get("decision", ""))[:40]
            dt = str(c.get("ended", c.get("started", "")))[:16]
            lines.append(f"  {status} {pair}: {decision} ({dt})")

        # Recent issues (errors/warnings)
        issues = fr.get_latest_issues(limit=3)
        if issues:
            lines.append("  Issues:")
            for iss in issues:
                lines.append(f"    ⚠ {iss['stage']} ({iss['pair']}): {str(iss.get('note',''))[:60]}")

        return lines
    except Exception as exc:
        logger.debug("flight recorder unavailable: %s", exc)
        return []


# ── Internal: system state ────────────────────────────────────────────────────

def _is_actively_trading() -> bool:
    """Return True if the user has had active trading in the last 2 hours."""
    try:
        if not os.path.exists(_FLIGHT_RECORDER_DB):
            return False
        import sqlite3
        conn = sqlite3.connect(_FLIGHT_RECORDER_DB)
        row = conn.execute("""
            SELECT COUNT(*) FROM flight_log
            WHERE stage IN ('cycle_end', 'guardian_spawn', 'execution')
            AND timestamp > datetime('now', '-2 hours')
        """).fetchone()
        conn.close()
        return (row[0] or 0) > 0
    except Exception:
        return False


def _get_process_health() -> List[str]:
    """Return warnings for any critical trading processes that are down.
    Only called when actively trading — not shown during quiet/off-market hours.
    """
    import socket, subprocess
    issues = []

    # serve_ui health check
    try:
        import urllib.request
        urllib.request.urlopen("http://127.0.0.1:8766/", timeout=2)
    except Exception:
        issues.append("  ⛔ serve_ui (trading dashboard) is DOWN — guardian not running")

    # trade_scout WebSocket health check (port 8767)
    try:
        with socket.create_connection(("127.0.0.1", 8767), timeout=2):
            pass
    except Exception:
        issues.append("  ⛔ trade_scout is DOWN — market not being scanned")

    return issues


def _get_system_state() -> List[str]:
    """Return model liveness + RAM pressure summary."""
    try:
        sys.path.insert(0, _JARVIS)
        import asyncio as _asyncio

        async def _inner():
            from Core.system_status import get_status
            return await get_status()

        # Run in a new event loop if we're not in one
        try:
            loop = _asyncio.get_running_loop()
            # We're inside an async context — schedule as task
            status = loop.run_until_complete(_inner())
        except RuntimeError:
            status = _asyncio.run(_inner())

        ram   = status["ram"]
        alive = status["services"]["mlx_alive"]
        danger = "🔴" if ram["danger"] else "🟢"
        return [
            f"  RAM: {danger} {ram['used_gb']}GB / {ram['total_gb']}GB ({ram['pressure']*100:.0f}%)",
            f"  MLX alive: {', '.join(alive) if alive else 'none'}",
        ]
    except Exception as exc:
        logger.debug("system state unavailable: %s", exc)
        return []
