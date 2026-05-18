#!/usr/bin/env python3
"""
Context Injector — Layer 2 per-turn system prompt injection.
============================================================

Assembles live Jarvis state every turn and prepends it to the system prompt.
Thin wrapper around jarvis_bridge — handles caching + formatting for injection.

Usage (in OpenClaw hook or handler):
    from Core.context_injector import ContextInjector
    injector = ContextInjector(user_id=2)
    prefix = injector.get_prefix()  # <2KB string, prepend to system prompt

Layers:
    Layer 1 — IDENTITY  (SOUL.md / USER.md / MEMORY.md — static, OpenClaw loads)
    Layer 2 — SESSION   (THIS FILE — live state, refreshed each turn)
    Layer 3 — THREAD    (OpenClaw compaction manages conversation history)
    Layer 4 — INTENT    (on-demand: trading Q → trading summary, etc.)
"""

import json
import logging
import sqlite3
import time
from pathlib import Path
from typing import Optional

# Jarvis conversation history DB (aggregates all platform conversations)
_CONV_HISTORY_DB = Path.home() / "jarvis" / "Database" / "conversation_history.db"
# Max recent messages to pull from conversation aggregator
_CONV_RECENT_LIMIT = 6

logger = logging.getLogger(__name__)

# Cache TTL — refresh context at most every N seconds per user
CACHE_TTL_SECONDS = 30

# Hard cap on injected context
MAX_CHARS = 2000

# Path to write the JARVIS_CONTEXT.md file (picked up by bootstrap-extra-files)
CONTEXT_FILE = Path.home() / ".openclaw" / "workspace" / "JARVIS_CONTEXT.md"


class ContextInjector:
    """Assembles and caches Layer 2 context for injection into system prompts."""

    # Class-level cache: user_id → (timestamp, context_str)
    _cache: dict = {}

    def __init__(self, user_id: int = 2, workspace_id: Optional[int] = None):
        self.user_id = user_id
        self.workspace_id = workspace_id

    def get_prefix(self, force_refresh: bool = False) -> str:
        """Return the live context string (<2KB). Cached for CACHE_TTL_SECONDS.

        Args:
            force_refresh: bypass cache and regenerate immediately
        """
        now = time.time()
        cached = self._cache.get(self.user_id)
        if not force_refresh and cached:
            ts, ctx = cached
            if now - ts < CACHE_TTL_SECONDS:
                return ctx

        ctx = self._build()
        self._cache[self.user_id] = (now, ctx)
        return ctx

    def refresh_file(self) -> bool:
        """Regenerate JARVIS_CONTEXT.md. Called by the jarvis-context hook."""
        try:
            ctx = self._build()
            CONTEXT_FILE.write_text(ctx)
            self._cache[self.user_id] = (time.time(), ctx)
            return True
        except Exception as e:
            logger.warning("context_injector refresh_file failed: %s", e)
            return False

    def _build(self) -> str:
        """Core assembly — pulls from jarvis_bridge, adds universal flight events."""
        try:
            from Core.jarvis_bridge import get_context_for_prompt
            base = get_context_for_prompt(
                user_id=self.user_id,
                workspace_id=self.workspace_id,
            )
        except Exception as e:
            logger.warning("jarvis_bridge unavailable: %s", e)
            base = ""

        # Layer 2B: knowledge vault — scout retrospectives, patterns, learnings
        vault_ctx = self._get_vault_context()
        if vault_ctx:
            base = base.rstrip() + "\n" + vault_ctx

        # Layer 2C: recent Jarvis conversation context (boardroom, floor, workspace)
        conv_ctx = self._get_recent_conversations()
        if conv_ctx:
            base = base.rstrip() + "\n" + conv_ctx

        # Layer 2C: recent universal flight events (boardroom, skills, MCP)
        universal = self._get_universal_events()
        if universal:
            base = base.rstrip() + "\n" + universal

        # Enforce hard cap
        if len(base) > MAX_CHARS:
            base = base[:MAX_CHARS] + "\n[…context truncated]"

        return base

    def _get_vault_context(self) -> str:
        """
        Pull high-value vault documents into context:
        - Latest scout retrospective (recent performance)
        - Active collective patterns (what setups are working)
        - Tim's preferences (communication/workflow prefs)
        Max ~600 chars to stay within the overall 2KB cap.
        """
        vault_dir = Path.home() / "jarvis" / "knowledge"
        vault_db = vault_dir / "_index.db"
        if not vault_db.exists():
            return ""
        try:
            conn = sqlite3.connect(str(vault_db))
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()

            lines = ["=== KNOWLEDGE VAULT ==="]

            # Latest scout retrospective
            cur.execute("""SELECT path FROM files WHERE file_type='scout_retrospective'
                           ORDER BY updated_at DESC LIMIT 1""")
            row = cur.fetchone()
            if row:
                retro_path = vault_dir / row["path"]
                if retro_path.exists():
                    content = retro_path.read_text()
                    # Pull just the summary table (first 400 chars after frontmatter)
                    body = content.split("---", 2)[-1].strip()[:350]
                    lines.append(f"Scout Retrospective:\n{body}")

            # Active collective patterns
            cur.execute("""SELECT path FROM files WHERE file_type='collective_patterns'
                           ORDER BY updated_at DESC LIMIT 1""")
            row = cur.fetchone()
            if row:
                pat_path = vault_dir / row["path"]
                if pat_path.exists():
                    content = pat_path.read_text()
                    body = content.split("---", 2)[-1].strip()[:200]
                    lines.append(f"Collective Patterns:\n{body}")

            conn.close()
            return "\n".join(lines) if len(lines) > 1 else ""

        except Exception as e:
            logger.debug("_get_vault_context failed: %s", e)
            return ""

    def _get_recent_conversations(self) -> str:
        """
        Pull the last N messages from Jarvis conversation history DB.
        Gives Trevor recent context from boardroom/floor/workspace conversations
        even in a fresh session with no compacted history.
        """
        if not _CONV_HISTORY_DB.exists():
            return ""
        try:
            conn = sqlite3.connect(str(_CONV_HISTORY_DB))
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            cur.execute("""
                SELECT m.role, m.content, m.timestamp, c.title
                FROM messages m
                LEFT JOIN conversations c ON m.conversation_id = c.id
                ORDER BY m.timestamp DESC
                LIMIT ?
            """, (_CONV_RECENT_LIMIT,))
            rows = list(reversed(cur.fetchall()))
            conn.close()

            if not rows:
                return ""

            lines = ["=== RECENT JARVIS CONVERSATIONS ==="]
            for r in rows:
                role = str(r["role"] or "").upper()[:9]
                ts = str(r["timestamp"] or "")[:16].replace("T", " ")
                title = str(r["title"] or "")[:30]
                content = str(r["content"] or "").strip()
                # Truncate long messages — just enough for context
                if len(content) > 120:
                    content = content[:120] + "…"
                lines.append(f"  [{ts}] {role}: {content}")
            return "\n".join(lines)

        except Exception as e:
            logger.debug("_get_recent_conversations failed: %s", e)
            return ""

    def _get_universal_events(self) -> str:
        """Pull recent boardroom/skill/MCP events from flight recorder."""
        try:
            import sys
            sys.path.insert(0, str(Path(__file__).parent.parent / "Forex Trading Team" / "Source"))
            from flight_recorder import FlightRecorder

            fr = FlightRecorder(user_id=self.user_id)
            rows = fr.get_recent_universal(limit=8)
            if not rows:
                return ""

            lines = ["=== RECENT ACTIVITY ==="]
            for r in rows:
                stage = r["stage"]
                try:
                    data = json.loads(r["data"]) if r["data"] else {}
                except Exception:
                    data = {}

                ts = r["timestamp"][:16].replace("T", " ")

                if stage == "boardroom_end":
                    outcome = data.get("outcome", "?")
                    seats = data.get("seats_used", "?")
                    lines.append(f"  [{ts}] Boardroom: {outcome} ({seats} seats)")
                elif stage == "skill_end":
                    skill = data.get("skill", stage)
                    q = data.get("quality_score", "")
                    q_str = f" quality={q}" if q else ""
                    lines.append(f"  [{ts}] Skill: {skill}{q_str}")
                elif stage == "trevor_training":
                    domain = data.get("domain", "?")
                    captured = data.get("captured", False)
                    if captured:
                        lines.append(f"  [{ts}] Training pair captured: {domain}")
                # Skip low-signal stages (trevor_intent/route/mcp_call) from summary

            return "\n".join(lines) if len(lines) > 1 else ""

        except Exception as e:
            logger.debug("universal events unavailable: %s", e)
            return ""


# ── Module-level convenience functions ──────────────────────────────────────

_default_injector: Optional[ContextInjector] = None


def get_injector(user_id: int = 2, workspace_id: Optional[int] = None) -> ContextInjector:
    """Get or create the default injector for this user."""
    global _default_injector
    if _default_injector is None or _default_injector.user_id != user_id:
        _default_injector = ContextInjector(user_id=user_id, workspace_id=workspace_id)
    return _default_injector


def inject_context(user_id: int = 2, workspace_id: Optional[int] = None) -> str:
    """One-shot convenience: return the Layer 2 context string."""
    return get_injector(user_id, workspace_id).get_prefix()


def record_trevor_turn(
    intent: str,
    handler: str,
    response_len: int,
    duration_ms: float,
    training_captured: bool = False,
    domain: str = "general",
    quality_signal: str = "none",
) -> None:
    """Record a Trevor interaction into the universal flight recorder.

    Call this at the end of every Trevor turn (from the jarvis-context hook
    or a PostMessage hook) to keep the flight recorder current.
    """
    try:
        import sys
        sys.path.insert(0, str(Path(__file__).parent.parent / "Forex Trading Team" / "Source"))
        from flight_recorder import FlightRecorder, FlightStage

        fr = FlightRecorder()
        fr.record_event(FlightStage.TREVOR_INTENT, {"intent": intent})
        fr.record_event(FlightStage.TREVOR_ROUTE, {"handler": handler}, duration_ms=duration_ms)
        fr.record_event(
            FlightStage.TREVOR_RESPONSE,
            {"length": response_len, "quality_signal": quality_signal},
        )
        if training_captured:
            fr.record_event(
                FlightStage.TREVOR_TRAINING,
                {"captured": True, "domain": domain},
            )
    except Exception as e:
        logger.debug("record_trevor_turn failed: %s", e)


def record_boardroom_cycle(
    topic: str,
    seats_used: int,
    outcome: str,
    duration_ms: float,
    opus_called: bool = False,
) -> None:
    """Record a boardroom deliberation into the universal flight recorder."""
    try:
        import sys
        sys.path.insert(0, str(Path(__file__).parent.parent / "Forex Trading Team" / "Source"))
        from flight_recorder import FlightRecorder, FlightStage

        fr = FlightRecorder()
        fr.record_event(FlightStage.BOARDROOM_START, {"topic": topic[:80]})
        if opus_called:
            fr.record_event(FlightStage.BOARDROOM_OPUS, {"topic": topic[:40]})
        fr.record_event(
            FlightStage.BOARDROOM_END,
            {"outcome": outcome, "seats_used": seats_used, "topic": topic[:80]},
            duration_ms=duration_ms,
        )
    except Exception as e:
        logger.debug("record_boardroom_cycle failed: %s", e)


def record_skill_execution(
    skill_name: str,
    quality_score: float = 0.0,
    domain: str = "general",
    duration_ms: float = 0,
) -> None:
    """Record a skill execution into the universal flight recorder."""
    try:
        import sys
        sys.path.insert(0, str(Path(__file__).parent.parent / "Forex Trading Team" / "Source"))
        from flight_recorder import FlightRecorder, FlightStage

        fr = FlightRecorder()
        fr.record_event(FlightStage.SKILL_START, {"skill": skill_name})
        fr.record_event(
            FlightStage.SKILL_END,
            {"skill": skill_name, "quality_score": quality_score, "domain": domain},
            duration_ms=duration_ms,
        )
    except Exception as e:
        logger.debug("record_skill_execution failed: %s", e)
