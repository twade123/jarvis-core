"""
Request Logger — Captures every LLM interaction for the self-improving pipeline.
Logs to intelligence.db (v2) request_log table.
This is the data collection layer that feeds:
1. Shadow model training
2. Fine-tuning pipeline
3. Quality dashboards
4. Agent learning
"""

import sqlite3
import json
import time
import threading
import functools
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Any, Callable
from concurrent.futures import ThreadPoolExecutor

DB_PATH = Path.home() / "jarvis" / "Database" / "v2" / "intelligence.db"

# Background thread pool for non-blocking writes
_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="req_logger")
_local = threading.local()

# Cost estimates per 1K tokens (USD) — update as pricing changes
MODEL_COSTS = {
    "gpt-4o":        {"in": 0.0025, "out": 0.010},
    "gpt-4o-mini":   {"in": 0.00015, "out": 0.0006},
    "gpt-4-turbo":   {"in": 0.01, "out": 0.03},
    "gpt-3.5-turbo": {"in": 0.0005, "out": 0.0015},
    "claude-3-opus":  {"in": 0.015, "out": 0.075},
    "claude-3-sonnet":{"in": 0.003, "out": 0.015},
    "claude-3-haiku": {"in": 0.00025, "out": 0.00125},
    "claude-sonnet-4-20250514": {"in": 0.003, "out": 0.015},
    "local":          {"in": 0.0, "out": 0.0},
}

FAILURE_PATTERNS = re.compile(
    r"try again|that'?s wrong|not what i asked|incorrect|"
    r"no,?\s+i meant|wrong answer|redo|fix that",
    re.IGNORECASE,
)

IMPLICIT_SUCCESS_WINDOW = 2  # messages without correction = implicit success

# Valid outcomes per DB CHECK constraint
OUTCOME_MAP = {
    "success": "success",
    "implicit_success": "success",  # maps to 'success' in DB
    "failure": "failure",
    "pending": "partial",  # 'partial' used as pending state
    "partial": "partial",
    "fallback": "fallback",
}


def _get_conn() -> sqlite3.Connection:
    """Thread-local DB connection."""
    if not hasattr(_local, "conn") or _local.conn is None:
        _local.conn = sqlite3.connect(str(DB_PATH), timeout=10, isolation_level=None)
        _local.conn.execute("PRAGMA journal_mode=DELETE")
        _local.conn.execute("PRAGMA busy_timeout=5000")
    return _local.conn


def init_db():
    """Create request_log table if it doesn't exist, migrate if needed."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH), timeout=10, isolation_level=None)

    # Check if table exists and get its columns
    existing_cols = set()
    try:
        cursor = conn.execute("PRAGMA table_info(request_log)")
        existing_cols = {row[1] for row in cursor.fetchall()}
    except Exception:
        pass

    if not existing_cols:
        # Fresh create
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS request_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                user_id TEXT,
                request_text TEXT,
                intent_classified TEXT,
                handler_routed TEXT,
                model_used TEXT,
                response_text TEXT,
                tool_calls TEXT,
                outcome TEXT DEFAULT 'pending',
                latency_ms REAL,
                tokens_in INTEGER,
                tokens_out INTEGER,
                cost_estimate REAL,
                trade_id TEXT,
                correction_text TEXT,
                created_at TEXT DEFAULT (datetime('now'))
            );
        """)
    else:
        # Migrate: add missing columns
        migrations = {
            "trade_id": "ALTER TABLE request_log ADD COLUMN trade_id TEXT",
            "correction_text": "ALTER TABLE request_log ADD COLUMN correction_text TEXT",
            "cost_estimate": "ALTER TABLE request_log ADD COLUMN cost_estimate REAL",
            "tokens_in": "ALTER TABLE request_log ADD COLUMN tokens_in INTEGER",
            "tokens_out": "ALTER TABLE request_log ADD COLUMN tokens_out INTEGER",
            "latency_ms": "ALTER TABLE request_log ADD COLUMN latency_ms REAL",
            "outcome": "ALTER TABLE request_log ADD COLUMN outcome TEXT DEFAULT 'pending'",
            "intent_classified": "ALTER TABLE request_log ADD COLUMN intent_classified TEXT",
            "handler_routed": "ALTER TABLE request_log ADD COLUMN handler_routed TEXT",
            "tool_calls": "ALTER TABLE request_log ADD COLUMN tool_calls TEXT",
        }
        for col, sql in migrations.items():
            if col not in existing_cols:
                try:
                    conn.execute(sql)
                except Exception:
                    pass

    conn.execute("CREATE INDEX IF NOT EXISTS idx_request_log_timestamp ON request_log(timestamp)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_request_log_outcome ON request_log(outcome)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_request_log_user ON request_log(user_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_request_log_trade ON request_log(trade_id)")
    conn.commit()
    conn.close()


def estimate_cost(model: str, tokens_in: int, tokens_out: int) -> float:
    """Estimate cost in USD."""
    costs = MODEL_COSTS.get(model, MODEL_COSTS.get("local", {"in": 0, "out": 0}))
    return (tokens_in / 1000 * costs["in"]) + (tokens_out / 1000 * costs["out"])


def _write_log(entry: dict) -> Optional[str]:
    """Blocking write — runs in background thread. Returns the log ID."""
    import uuid
    log_id = str(uuid.uuid4())
    raw_outcome = entry.get("outcome", "pending")
    db_outcome = OUTCOME_MAP.get(raw_outcome, "partial")
    try:
        conn = _get_conn()
        conn.execute("""
            INSERT INTO request_log
            (id, timestamp, user_id, request_text, intent_classified, handler_routed,
             model_used, response_text, tool_calls, outcome, latency_ms,
             tokens_in, tokens_out, cost_estimate, trade_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            log_id,
            entry["timestamp"],
            entry.get("user_id") or "system",
            entry.get("request_text") or "",
            entry.get("intent_classified"),
            entry.get("handler_routed"),
            entry.get("model_used"),
            entry.get("response_text"),
            json.dumps(entry.get("tool_calls")) if entry.get("tool_calls") else None,
            db_outcome,
            entry.get("latency_ms"),
            entry.get("tokens_in"),
            entry.get("tokens_out"),
            entry.get("cost_estimate"),
            entry.get("trade_id"),
        ))
        conn.commit()
        return log_id
    except Exception as e:
        print(f"[RequestLogger] Write error: {e}")
        return None


def log_request(entry: dict):
    """Non-blocking: submit log entry to background thread."""
    _executor.submit(_write_log, entry)


def log_llm_call(
    user_id: str = None,
    request_text: str = None,
    intent: str = None,
    handler: str = None,
    model: str = None,
    response_text: str = None,
    tool_calls: list = None,
    latency_ms: float = None,
    tokens_in: int = 0,
    tokens_out: int = 0,
    trade_id: str = None,
    outcome: str = "pending",
):
    """Convenience function to log a single LLM call."""
    cost = estimate_cost(model or "local", tokens_in or 0, tokens_out or 0)
    log_request({
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "user_id": user_id,
        "request_text": request_text,
        "intent_classified": intent,
        "handler_routed": handler,
        "model_used": model,
        "response_text": response_text,
        "tool_calls": tool_calls,
        "outcome": outcome,
        "latency_ms": latency_ms,
        "tokens_in": tokens_in,
        "tokens_out": tokens_out,
        "cost_estimate": cost,
        "trade_id": trade_id,
    })


def llm_logged(
    model: str = None,
    handler: str = None,
    intent: str = None,
    user_id: str = None,
):
    """
    Decorator that wraps an LLM call function and logs it automatically.

    The wrapped function should return a dict with at least:
      - response_text: str
    Optionally:
      - tool_calls: list
      - tokens_in: int
      - tokens_out: int
      - model: str (overrides decorator param)
    """
    def decorator(fn: Callable) -> Callable:
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            request_text = kwargs.get("prompt") or kwargs.get("request_text") or (args[0] if args else None)
            start = time.perf_counter()
            result = fn(*args, **kwargs)
            elapsed_ms = (time.perf_counter() - start) * 1000

            if isinstance(result, dict):
                used_model = result.get("model", model) or "unknown"
                t_in = result.get("tokens_in", 0)
                t_out = result.get("tokens_out", 0)
                log_llm_call(
                    user_id=result.get("user_id", user_id),
                    request_text=str(request_text)[:10000] if request_text else None,
                    intent=result.get("intent", intent),
                    handler=result.get("handler", handler),
                    model=used_model,
                    response_text=str(result.get("response_text", ""))[:50000],
                    tool_calls=result.get("tool_calls"),
                    latency_ms=elapsed_ms,
                    tokens_in=t_in,
                    tokens_out=t_out,
                    trade_id=result.get("trade_id"),
                )
            return result
        return wrapper
    return decorator


# --- Outcome Tracker ---

class OutcomeTracker:
    """
    Tracks outcomes of logged requests based on subsequent user messages.
    
    - Tool calls that succeed → success
    - User says "try again" / "that's wrong" → failure
    - No correction within 2 messages → implicit_success
    - Trading decisions linked to trade_id for later reconciliation
    """

    def __init__(self):
        self._pending: list[int] = []  # request_log IDs awaiting outcome
        self._message_count: dict[int, int] = {}  # id → messages since

    def track(self, log_id: str):
        """Start tracking a pending request."""
        self._pending.append(log_id)
        self._message_count[log_id] = 0

    def on_user_message(self, message_text: str):
        """Call this on every user message to evaluate pending outcomes."""
        is_failure = bool(FAILURE_PATTERNS.search(message_text))
        resolved = []

        for log_id in self._pending:
            self._message_count[log_id] = self._message_count.get(log_id, 0) + 1

            if is_failure and self._message_count[log_id] == 1:
                _executor.submit(self._update_outcome, log_id, "failure", message_text)
                resolved.append(log_id)
            elif self._message_count[log_id] >= IMPLICIT_SUCCESS_WINDOW:
                _executor.submit(self._update_outcome, log_id, "success")
                resolved.append(log_id)

        for rid in resolved:
            self._pending.remove(rid)
            self._message_count.pop(rid, None)

    def mark_success(self, log_id: str):
        """Explicitly mark a request as successful."""
        _executor.submit(self._update_outcome, log_id, "success")
        if log_id in self._pending:
            self._pending.remove(log_id)
            self._message_count.pop(log_id, None)

    def mark_trade_outcome(self, log_id: str, trade_id: str, outcome: str):
        """Link a trading decision to its trade outcome."""
        db_outcome = OUTCOME_MAP.get(outcome, "partial")
        def _update():
            try:
                conn = _get_conn()
                conn.execute(
                    "UPDATE request_log SET trade_id=?, outcome=? WHERE id=?",
                    (trade_id, db_outcome, log_id),
                )
                conn.commit()
            except Exception as e:
                print(f"[OutcomeTracker] Trade update error: {e}")
        _executor.submit(_update)

    @staticmethod
    def _update_outcome(log_id: str, outcome: str, correction: str = None):
        db_outcome = OUTCOME_MAP.get(outcome, "partial")
        try:
            conn = _get_conn()
            if correction:
                conn.execute(
                    "UPDATE request_log SET outcome=?, correction_text=? WHERE id=?",
                    (db_outcome, correction, log_id),
                )
            else:
                conn.execute(
                    "UPDATE request_log SET outcome=? WHERE id=?",
                    (db_outcome, log_id),
                )
            conn.commit()
        except Exception as e:
            print(f"[OutcomeTracker] Update error: {e}")


# Singleton tracker
outcome_tracker = OutcomeTracker()

# Initialize DB on import
init_db()
