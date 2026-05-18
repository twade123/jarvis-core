#!/usr/bin/env python3
"""
Universal Training Data Extractor — Jarvis AI Ecosystem
Pulls from all 7 data sources and routes into correct training JSONL files.

Usage:
    python3 Core/universal_extractor.py
    python3 Core/universal_extractor.py --dry-run
    python3 Core/universal_extractor.py --source scout
"""

import os
import json
import hashlib
import sqlite3
import glob
import re
from pathlib import Path
from collections import defaultdict
from datetime import datetime

# ─── Output Paths ─────────────────────────────────────────────────────────────
OUTPUT_SESSION   = "~/Jarvis/training_data/sessions/session_training.jsonl"
OUTPUT_VALIDATOR = "~/jarvis/models/training_data/validator_35b_training.jsonl"
OUTPUT_TA        = "~/jarvis/models/training_data/ta_9b_training.jsonl"

# ─── Source Paths ─────────────────────────────────────────────────────────────
TREVOR_DB       = "~/jarvis/Database/trevor_database.db"
CLAUDE_PROJECTS = [
    "~/.claude/projects/-Users-timothywade-Jarvis/",
    "~/.claude/projects/-Users-timothywade-Jarvis-Trading-Bot/",
]
FLIGHT_DB       = "~/jarvis/Forex Trading Team/Source/flight_recorder.db"
DISTILL_DB      = "~/jarvis/training_data/distillation/distillation.db"
KNOWLEDGE_ROOT  = "~/jarvis/knowledge/"
KNOWLEDGE_INDEX = "~/jarvis/knowledge/_index.db"

# ─── Stats tracking ───────────────────────────────────────────────────────────
stats = {
    "claude_conversations": {"new": 0, "skipped": 0, "output": "session_training.jsonl"},
    "claude_code":          {"new": 0, "skipped": 0, "output": "session_training.jsonl"},
    "scout_findings":       {"new": 0, "skipped": 0, "output": "validator_35b_training.jsonl"},
    "exit_learning":        {"new": 0, "skipped": 0, "output": "ta_9b_training.jsonl"},
    "flight_recorder":      {"new": 0, "skipped": 0, "output": "validator_35b_training.jsonl"},
    "distillation":         {"new": 0, "skipped": 0, "output": "session_training.jsonl"},
    "knowledge_vault":      {"new": 0, "skipped": 0, "output": "session_training.jsonl"},
}

# ─── Dedup set (populated from existing files on startup) ─────────────────────
seen_hashes: set = set()


def content_hash(user_content: str, assistant_content: str) -> str:
    return hashlib.md5((user_content + assistant_content).encode("utf-8", errors="replace")).hexdigest()


def load_existing_hashes():
    """Load hashes from all output files to avoid duplicates on re-run."""
    for path in [OUTPUT_SESSION, OUTPUT_VALIDATOR, OUTPUT_TA]:
        if not os.path.exists(path):
            continue
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                    conv = rec.get("conversation", [])
                    if len(conv) >= 2:
                        u = conv[0].get("content", "")
                        a = conv[1].get("content", "")
                        seen_hashes.add(content_hash(u, a))
                except Exception:
                    pass


def make_record(domain: str, source: str, user_content: str, assistant_content: str,
                negative_example: bool = False, metadata: dict = None) -> dict:
    return {
        "domain": domain,
        "source": source,
        "conversation": [
            {"role": "user", "content": user_content},
            {"role": "assistant", "content": assistant_content},
        ],
        "negative_example": negative_example,
        "metadata": metadata or {},
    }


def write_record(record: dict, output_path: str, dry_run: bool, source_key: str):
    conv = record["conversation"]
    u = conv[0]["content"]
    a = conv[1]["content"]
    h = content_hash(u, a)
    if h in seen_hashes:
        stats[source_key]["skipped"] += 1
        return
    seen_hashes.add(h)
    if not dry_run:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    stats[source_key]["new"] += 1


def classify_domain_by_keywords(text: str) -> str:
    text_lower = text.lower()
    trading_kw = ["trading", "forex", "trade", "pair", "pip", "entry", "exit", "signal",
                  "scout", "sniper", "eurusd", "gbpusd", "usdjpy", "audusd", "usdcad",
                  "xauusd", "nzdusd", "position", "long", "short", "breakout", "confluence",
                  "rsi", "ema", "stoch", "candle", "market", "volatility", "bid", "ask",
                  "spread", "lot", "risk", "reward", "oanda"]
    coding_kw = ["code", "build", "fix", "implement", "function", "class", "python",
                 "script", "bug", "error", "debug", "test", "deploy", "install",
                 "database", "query", "sql", "api", "endpoint", "refactor", "update",
                 "create", "write", "add", "modify", "change"]

    trading_score = sum(1 for kw in trading_kw if kw in text_lower)
    coding_score = sum(1 for kw in coding_kw if kw in text_lower)

    if trading_score > coding_score and trading_score > 0:
        return "trading"
    elif coding_score > 0:
        return "coding"
    return "general"


def classify_path_domain(path: str, content: str = "") -> str:
    """Classify domain from a file path or content."""
    path_lower = path.lower()
    if any(kw in path_lower for kw in ["trading", "forex", "scout", "trade", "backtest"]):
        return "trading"
    if any(kw in path_lower for kw in ["knowledge", "skills", "agents", "decision"]):
        return "general"
    if content:
        return classify_domain_by_keywords(content)
    return "general"


# ══════════════════════════════════════════════════════════════════════════════
# SOURCE 1: claude_conversations
# ══════════════════════════════════════════════════════════════════════════════

GENERIC_FILLER_STARTS = [
    "i'll help you create a workspace",
    "i will help you create a workspace",
]

def extract_claude_conversations(dry_run: bool):
    if not os.path.exists(TREVOR_DB):
        print(f"  [SKIP] trevor_database.db not found at {TREVOR_DB}")
        return
    try:
        conn = sqlite3.connect(TREVOR_DB)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("SELECT user_request, claude_response, created_at FROM claude_conversations")
        rows = cur.fetchall()
        conn.close()
    except Exception as e:
        print(f"  [ERROR] claude_conversations: {e}")
        return

    for row in rows:
        user_req = (row["user_request"] or "").strip()
        claude_resp = (row["claude_response"] or "").strip()

        if not user_req or not claude_resp:
            stats["claude_conversations"]["skipped"] += 1
            continue

        resp_lower = claude_resp.lower()
        if any(resp_lower.startswith(filler) for filler in GENERIC_FILLER_STARTS):
            stats["claude_conversations"]["skipped"] += 1
            continue

        domain = classify_domain_by_keywords(user_req)
        record = make_record(
            domain=domain,
            source="claude_conversations",
            user_content=user_req,
            assistant_content=claude_resp,
            metadata={"created_at": row["created_at"] or ""},
        )
        write_record(record, OUTPUT_SESSION, dry_run, "claude_conversations")


# ══════════════════════════════════════════════════════════════════════════════
# SOURCE 2: Claude Code sessions
# ══════════════════════════════════════════════════════════════════════════════

SKIP_USER_PATTERNS = [
    r"<command-message>",
    r"\[Request interrupted",
    r"\[Tool result\]",
]


def _is_skip_user(text: str) -> bool:
    if not text:
        return True
    for pattern in SKIP_USER_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            return True
    return False


def _extract_text_from_content(content) -> str:
    """Extract plain text from Claude Code message content (string or list of blocks)."""
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, dict):
                btype = block.get("type", "")
                if btype == "text":
                    parts.append(block.get("text", ""))
                elif btype in ("tool_result", "tool_use"):
                    continue  # skip
                # skip thinking blocks too
            elif isinstance(block, str):
                parts.append(block)
        return " ".join(p.strip() for p in parts if p.strip())
    return ""


def extract_claude_code_sessions(dry_run: bool):
    for project_dir in CLAUDE_PROJECTS:
        if not os.path.isdir(project_dir):
            print(f"  [SKIP] Claude Code project dir not found: {project_dir}")
            continue

        is_trading = "Trading" in project_dir

        # Recursive: captures both top-level sessions AND per-UUID-subdir sessions
        # Subagent files (*/subagents/*.jsonl) are also valuable CoT training data
        jsonl_files = glob.glob(os.path.join(project_dir, "**/*.jsonl"), recursive=True)
        if not jsonl_files:
            continue

        for jsonl_path in jsonl_files:
            try:
                _process_claude_code_file(jsonl_path, is_trading, dry_run)
            except Exception as e:
                print(f"  [ERROR] claude_code {jsonl_path}: {e}")


def _process_claude_code_file(path: str, is_trading_project: bool, dry_run: bool):
    """Process one Claude Code session JSONL file."""
    sessions: dict = defaultdict(list)
    cwd_by_session: dict = {}

    with open(path, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except Exception:
                continue

            entry_type = entry.get("type", "")
            if entry_type not in ("user", "assistant"):
                continue

            session_id = entry.get("sessionId", "unknown")
            if not cwd_by_session.get(session_id) and entry.get("cwd"):
                cwd_by_session[session_id] = entry["cwd"]

            sessions[session_id].append(entry)

    # Now pair user→assistant turns per session
    for session_id, entries in sessions.items():
        cwd = cwd_by_session.get(session_id, "")
        trading_by_cwd = "Trading" in cwd or is_trading_project

        i = 0
        while i < len(entries):
            entry = entries[i]
            if entry.get("type") != "user":
                i += 1
                continue

            msg = entry.get("message", {})
            # skip tool_result user entries
            content = msg.get("content", "")
            if isinstance(content, list):
                # pure tool_result turn — skip
                if all(
                    isinstance(b, dict) and b.get("type") in ("tool_result",)
                    for b in content
                    if isinstance(b, dict)
                ):
                    i += 1
                    continue

            user_text = _extract_text_from_content(content)

            if _is_skip_user(user_text) or len(user_text) <= 20:
                i += 1
                continue

            # Find next assistant turn WITH actual text (skip pure tool_use intermediaries)
            # Claude Code pattern: user → asst(tool_use) → user(tool_result) → asst(tool_use) → ... → asst(TEXT)
            j = i + 1
            assistant_text = ""
            next_user_gap = 0
            while j < len(entries) and next_user_gap < 3:
                etype = entries[j].get("type", "")
                if etype == "user":
                    # Count how many real user turns we've passed (not tool_result)
                    c = entries[j].get("message", {}).get("content", "")
                    is_tool_result = isinstance(c, list) and all(
                        isinstance(b, dict) and b.get("type") == "tool_result"
                        for b in c if isinstance(b, dict)
                    )
                    if not is_tool_result:
                        next_user_gap += 1  # real user turn — stop after this
                elif etype == "assistant":
                    a_msg = entries[j].get("message", {})
                    a_content = a_msg.get("content", [])
                    text_parts = []
                    if isinstance(a_content, list):
                        for block in a_content:
                            if isinstance(block, dict) and block.get("type") == "text":
                                text_parts.append(block.get("text", ""))
                    candidate = " ".join(p.strip() for p in text_parts if p.strip())
                    if len(candidate) > 50:
                        assistant_text = candidate
                        break  # found a real response
                j += 1

            if not assistant_text or len(assistant_text) <= 50:
                i += 1
                continue

            # Classify domain
            combined = user_text + " " + assistant_text
            if trading_by_cwd or classify_domain_by_keywords(combined) == "trading":
                domain = "trading"
            else:
                domain = "coding"

            record = make_record(
                domain=domain,
                source="claude_code",
                user_content=user_text,
                assistant_content=assistant_text,
                metadata={
                    "session_id": session_id,
                    "cwd": cwd,
                    "file": os.path.basename(path),
                },
            )
            write_record(record, OUTPUT_SESSION, dry_run, "claude_code")
            i = j + 1  # advance past the assistant turn we just consumed


# ══════════════════════════════════════════════════════════════════════════════
# SOURCE 3: scout_findings
# ══════════════════════════════════════════════════════════════════════════════

def extract_scout_findings(dry_run: bool):
    if not os.path.exists(TREVOR_DB):
        return
    try:
        conn = sqlite3.connect(TREVOR_DB)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("""
            SELECT pair, setup_type, setup_name, direction, scout_confidence,
                   reasoning, sniper_score, historical_win_rate, outcome,
                   alert_type, snipe_created, created_at
            FROM scout_findings
            WHERE outcome IS NOT NULL
        """)
        rows = cur.fetchall()
        conn.close()
    except Exception as e:
        print(f"  [ERROR] scout_findings: {e}")
        return

    for row in rows:
        try:
            pair          = row["pair"] or "UNKNOWN"
            direction     = row["direction"] or "UNKNOWN"
            setup_type    = row["setup_type"] or "UNKNOWN"
            conf          = float(row["scout_confidence"] or 0)
            sniper        = row["sniper_score"] or 0
            hist_wr       = float(row["historical_win_rate"] or 0)
            reasoning     = (row["reasoning"] or "").strip()
            outcome       = (row["outcome"] or "").strip()

            if not reasoning or not outcome:
                stats["scout_findings"]["skipped"] += 1
                continue

            user_text = (
                f"Evaluate this {pair} {direction} {setup_type} setup: "
                f"confidence={conf:.0%}, sniper_score={sniper}, "
                f"historical_wr={hist_wr:.0%}. Reasoning: {reasoning}"
            )

            is_win = outcome.lower() in ("win", "won", "profit", "success", "tp")
            is_loss = outcome.lower() in ("loss", "lose", "lost", "sl", "stopped_out", "fail")

            if is_win:
                outcome_text = f"Outcome: {outcome}. This setup confirmed the signal"
            elif is_loss:
                outcome_text = f"Outcome: {outcome}. This setup failed — the signal did not play out"
            else:
                outcome_text = f"Outcome: {outcome}."

            record = make_record(
                domain="validator",
                source="scout_findings",
                user_content=user_text,
                assistant_content=outcome_text,
                negative_example=is_loss,
                metadata={
                    "pair": pair,
                    "direction": direction,
                    "outcome": outcome,
                    "created_at": row["created_at"] or "",
                },
            )
            write_record(record, OUTPUT_VALIDATOR, dry_run, "scout_findings")

        except Exception as e:
            stats["scout_findings"]["skipped"] += 1


# ══════════════════════════════════════════════════════════════════════════════
# SOURCE 4: exit_learning
# ══════════════════════════════════════════════════════════════════════════════

def _safe_float(val, default=0.0):
    try:
        return float(val) if val is not None else default
    except (TypeError, ValueError):
        return default


def extract_exit_learning(dry_run: bool):
    if not os.path.exists(TREVOR_DB):
        return
    try:
        conn = sqlite3.connect(TREVOR_DB)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("""
            SELECT pair, direction, entry_type, exit_reason, pnl_pips, pnl_usd,
                   actual_rr, duration_minutes, max_favorable_excursion_pips,
                   max_adverse_excursion_pips, primary_exit_signal,
                   threat_zone_at_exit, fan_state_at_exit, fan_direction_at_exit,
                   rsi_at_exit, stoch_at_exit, setup_name, created_at
            FROM exit_learning
        """)
        rows = cur.fetchall()
        conn.close()
    except Exception as e:
        print(f"  [ERROR] exit_learning: {e}")
        return

    for row in rows:
        try:
            pair         = row["pair"] or "UNKNOWN"
            direction    = row["direction"] or "UNKNOWN"
            setup_name   = row["setup_name"] or "UNKNOWN"
            entry_type   = row["entry_type"] or "UNKNOWN"
            exit_reason  = row["exit_reason"] or "UNKNOWN"
            pnl_pips     = _safe_float(row["pnl_pips"])
            pnl_usd      = _safe_float(row["pnl_usd"])
            actual_rr    = _safe_float(row["actual_rr"])
            dur_min      = row["duration_minutes"] or 0
            mfe          = _safe_float(row["max_favorable_excursion_pips"])
            mae          = _safe_float(row["max_adverse_excursion_pips"])
            fan_state    = row["fan_state_at_exit"] or "UNKNOWN"
            fan_dir      = row["fan_direction_at_exit"] or "UNKNOWN"
            rsi          = _safe_float(row["rsi_at_exit"])
            threat_zone  = row["threat_zone_at_exit"] or "UNKNOWN"

            user_text = (
                f"Trade exit analysis: {pair} {direction} {setup_name}. "
                f"Entry type: {entry_type}. "
                f"Market at exit: fan={fan_state}/{fan_dir}, RSI={rsi:.0f}, threat={threat_zone}. "
                f"MFE={mfe:.1f}p, MAE={mae:.1f}p. How should this exit be evaluated?"
            )

            # Build assistant text
            if pnl_pips > 0:
                outcome_note = "Exit captured profit — threat zone correctly identified reversal"
            else:
                if pnl_pips > -2:
                    exit_quality = "too early"
                else:
                    exit_quality = "stopped out"
                if mfe > abs(pnl_pips):
                    timing_note = "better exit timing possible"
                else:
                    timing_note = "trade had limited profit potential"
                outcome_note = f"Exit was {exit_quality} — MFE of {mfe:.1f}p suggests {timing_note}"

            assistant_text = (
                f"Exit via {exit_reason} at {pnl_pips:+.1f} pips "
                f"(${pnl_usd:+.2f}, {actual_rr:.2f}R) after {dur_min}min. "
                f"{outcome_note}"
            )

            record = make_record(
                domain="guardian",
                source="exit_learning",
                user_content=user_text,
                assistant_content=assistant_text,
                negative_example=pnl_pips < 0,
                metadata={
                    "pair": pair,
                    "pnl_pips": pnl_pips,
                    "actual_rr": actual_rr,
                    "created_at": row["created_at"] or "",
                },
            )
            write_record(record, OUTPUT_TA, dry_run, "exit_learning")

        except Exception as e:
            stats["exit_learning"]["skipped"] += 1


# ══════════════════════════════════════════════════════════════════════════════
# SOURCE 5: flight_recorder
# ══════════════════════════════════════════════════════════════════════════════

def extract_flight_recorder(dry_run: bool):
    if not os.path.exists(FLIGHT_DB):
        print(f"  [SKIP] flight_recorder.db not found: {FLIGHT_DB}")
        return
    try:
        conn = sqlite3.connect(FLIGHT_DB)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("""
            SELECT stage, pair, cycle_id, trade_id, status,
                   duration_ms, data, note
            FROM flight_log
            WHERE cycle_id != ''
            ORDER BY cycle_id, id
        """)
        rows = cur.fetchall()
        conn.close()
    except Exception as e:
        print(f"  [ERROR] flight_recorder: {e}")
        return

    # Group by cycle_id
    cycles: dict = defaultdict(list)
    for row in rows:
        cycles[row["cycle_id"]].append(dict(row))

    for cycle_id, entries in cycles.items():
        if len(entries) < 3:
            stats["flight_recorder"]["skipped"] += 1
            continue

        stages = {e["stage"]: e for e in entries}
        stage_names = {e["stage"] for e in entries}

        # Must have an entry-like and close-like stage
        entry_stages = {s for s in stage_names if any(kw in s.upper() for kw in
                        ("ENTRY", "OPEN", "EXECUTION", "EXECUTE"))}
        close_stages = {s for s in stage_names if any(kw in s.upper() for kw in
                        ("CLOSE", "EXIT", "TRADE_CLOSE", "CYCLE_END"))}

        if not entry_stages or not close_stages:
            stats["flight_recorder"]["skipped"] += 1
            continue

        pair = entries[0].get("pair") or "UNKNOWN"

        # Summarize all stages
        stage_summaries = []
        for e in entries:
            data_str = e.get("data") or "{}"
            try:
                data_parsed = json.loads(data_str)
            except Exception:
                data_parsed = {}

            # Extract key fields from data
            key_items = []
            for key in ["direction", "entry_price", "sl", "tp", "rr", "pnl_pips",
                        "exit_price", "reason", "action", "signal", "confidence"]:
                if key in data_parsed and data_parsed[key] is not None:
                    key_items.append(f"{key}={data_parsed[key]}")

            summary = f"{e['stage']}"
            if key_items:
                summary += f" ({', '.join(key_items[:4])})"
            if e.get("note"):
                summary += f" note='{e['note'][:80]}'"
            stage_summaries.append(summary)

        # Get close stage note
        close_stage = None
        for s in close_stages:
            if s in stages:
                close_stage = stages[s]
                break
        close_note = close_stage["note"] if close_stage else "unknown"

        user_text = (
            f"Reconstruct this {pair} trade lifecycle from flight data: "
            f"{'; '.join(stage_summaries[:8])}"
        )
        assistant_text = (
            f"Trade {cycle_id}: "
            + " → ".join(stage_summaries[:10])
            + f". Outcome: {close_note}"
        )

        record = make_record(
            domain="trading",
            source="flight_recorder",
            user_content=user_text,
            assistant_content=assistant_text,
            metadata={
                "cycle_id": cycle_id,
                "pair": pair,
                "stage_count": len(entries),
            },
        )
        write_record(record, OUTPUT_VALIDATOR, dry_run, "flight_recorder")


# ══════════════════════════════════════════════════════════════════════════════
# SOURCE 6: distillation.db CoT pairs
# ══════════════════════════════════════════════════════════════════════════════

def extract_distillation(dry_run: bool):
    if not os.path.exists(DISTILL_DB):
        print(f"  [SKIP] distillation.db not found: {DISTILL_DB}")
        return
    try:
        conn = sqlite3.connect(DISTILL_DB)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("""
            SELECT t.task_text, t.category,
                   j.best_response, j.opus_reasoning, j.quality_tier,
                   tr.response AS fallback_response
            FROM tasks t
            JOIN judgments j ON j.task_id = t.id
            LEFT JOIN teacher_responses tr ON tr.task_id = t.id AND tr.model_name = j.best_model
            WHERE j.quality_tier IS NOT NULL
        """)
        rows = cur.fetchall()
        conn.close()
    except Exception as e:
        print(f"  [ERROR] distillation: {e}")
        return

    for row in rows:
        try:
            task_text = (row["task_text"] or "").strip()
            if not task_text:
                stats["distillation"]["skipped"] += 1
                continue

            best_response = (row["best_response"] or "").strip()
            fallback      = (row["fallback_response"] or "").strip()
            assistant_text = best_response or fallback

            if not assistant_text:
                stats["distillation"]["skipped"] += 1
                continue

            # Prepend CoT reasoning if present
            opus_reasoning = (row["opus_reasoning"] or "").strip()
            if opus_reasoning:
                assistant_text = f"[Reasoning: {opus_reasoning}]\n\n{assistant_text}"

            quality_tier = (row["quality_tier"] or "").lower()
            domain = (row["category"] or "general").lower() or "general"

            record = make_record(
                domain=domain,
                source="distillation",
                user_content=task_text,
                assistant_content=assistant_text,
                negative_example=(quality_tier == "poor"),
                metadata={"quality_tier": quality_tier},
            )
            write_record(record, OUTPUT_SESSION, dry_run, "distillation")

        except Exception as e:
            stats["distillation"]["skipped"] += 1


# ══════════════════════════════════════════════════════════════════════════════
# SOURCE 7: knowledge vault → training pairs
# ══════════════════════════════════════════════════════════════════════════════

VAULT_SKIP_PATTERNS = [
    r"\.git/",
    r"__pycache__",
    r"node_modules",
]

QA_PATTERNS = [
    re.compile(r"^#+\s*Q[:\s]", re.MULTILINE | re.IGNORECASE),    # ## Q: ...
    re.compile(r"^#+\s*Question[:\s]", re.MULTILINE | re.IGNORECASE),
    re.compile(r"##\s*(Lesson|Decision|TIL|Key\s+Insight)", re.MULTILINE | re.IGNORECASE),
    re.compile(r"^-\s+\*\*(Lesson|Decision|Key|Result)", re.MULTILINE | re.IGNORECASE),
]

DECISION_PATTERNS = [
    "## decision", "## lesson", "## key insight", "## summary",
    "## outcome", "## result", "## what we learned", "## retrospective",
    "# decision record", "# lesson learned",
]


def _has_useful_content(content: str) -> bool:
    """Return True if the markdown doc looks like it has Q&A, decisions, or lessons."""
    content_lower = content.lower()
    for pattern in DECISION_PATTERNS:
        if pattern in content_lower:
            return True
    for pattern in QA_PATTERNS:
        if pattern.search(content):
            return True
    return False


def _get_topic_from_path(path: str) -> str:
    """Derive a readable topic from the file path."""
    stem = Path(path).stem
    # Convert hyphens/underscores to spaces, title case
    topic = stem.replace("-", " ").replace("_", " ")
    # Remove dates like 2026-03-05
    topic = re.sub(r"\d{4}-\d{2}-\d{2}", "", topic).strip()
    return topic.title() if topic else "this topic"


def extract_knowledge_vault(dry_run: bool):
    md_files = glob.glob(os.path.join(KNOWLEDGE_ROOT, "**/*.md"), recursive=True)

    for md_path in md_files:
        # Skip undesired paths
        skip = False
        for pat in VAULT_SKIP_PATTERNS:
            if re.search(pat, md_path):
                skip = True
                break
        if skip:
            stats["knowledge_vault"]["skipped"] += 1
            continue

        try:
            with open(md_path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
        except Exception:
            stats["knowledge_vault"]["skipped"] += 1
            continue

        content = content.strip()
        if len(content) < 200:
            stats["knowledge_vault"]["skipped"] += 1
            continue

        if not _has_useful_content(content):
            stats["knowledge_vault"]["skipped"] += 1
            continue

        topic = _get_topic_from_path(md_path)
        user_text = f"What do we know about {topic}?"
        assistant_text = content[:8000]  # cap at 8K chars to avoid huge training examples

        domain = classify_path_domain(md_path, content[:500])

        record = make_record(
            domain=domain,
            source="knowledge_vault",
            user_content=user_text,
            assistant_content=assistant_text,
            metadata={
                "path": md_path.replace(KNOWLEDGE_ROOT, ""),
                "length": len(content),
            },
        )
        write_record(record, OUTPUT_SESSION, dry_run, "knowledge_vault")


# ══════════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════════

SOURCE_MAP = {
    "conversations": extract_claude_conversations,
    "cc":            extract_claude_code_sessions,
    "claude_code":   extract_claude_code_sessions,
    "scout":         extract_scout_findings,
    "exit":          extract_exit_learning,
    "flight":        extract_flight_recorder,
    "distillation":  extract_distillation,
    "vault":         extract_knowledge_vault,
}

ORDERED_SOURCES = [
    ("claude_conversations", extract_claude_conversations),
    ("claude_code",          extract_claude_code_sessions),
    ("scout_findings",       extract_scout_findings),
    ("exit_learning",        extract_exit_learning),
    ("flight_recorder",      extract_flight_recorder),
    ("distillation",         extract_distillation),
    ("knowledge_vault",      extract_knowledge_vault),
]


def print_report():
    print("\n=== Universal Extractor Results ===")
    print(f"{'Source':<25}| {'New Pairs':>9} | {'Skipped':>7} | Output")
    print("-" * 25 + "|" + "-" * 11 + "|" + "-" * 9 + "|" + "-" * 35)
    total_new = 0
    total_skipped = 0
    for key, vals in stats.items():
        print(f"{key:<25}| {vals['new']:>9} | {vals['skipped']:>7} | {vals['output']}")
        total_new += vals["new"]
        total_skipped += vals["skipped"]
    print("-" * 25 + "|" + "-" * 11 + "|" + "-" * 9 + "|" + "-" * 35)
    print(f"{'TOTAL':<25}| {total_new:>9} | {total_skipped:>7} |")


def run_all(dry_run: bool = False, only_source: str = None):
    print(f"\n{'[DRY RUN] ' if dry_run else ''}Universal Extractor — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("Loading existing hashes for dedup...")
    load_existing_hashes()
    print(f"  Loaded {len(seen_hashes)} existing hashes\n")

    if only_source:
        fn = SOURCE_MAP.get(only_source)
        if not fn:
            print(f"Unknown source: {only_source}. Options: {list(SOURCE_MAP.keys())}")
            return
        print(f"Running source: {only_source}")
        fn(dry_run)
    else:
        for source_key, fn in ORDERED_SOURCES:
            print(f"Extracting: {source_key} ...")
            fn(dry_run)

    print_report()


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Universal Training Data Extractor")
    parser.add_argument("--dry-run", action="store_true",
                        help="Count pairs without writing to disk")
    parser.add_argument("--source", default=None,
                        help="Run only one source: conversations|cc|scout|exit|flight|distillation|vault")
    args = parser.parse_args()
    run_all(dry_run=args.dry_run, only_source=args.source)
