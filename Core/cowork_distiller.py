#!/usr/bin/env python3
"""
Cowork Session Distiller — Capture Claude Desktop (Cowork) chain-of-thought as training data.
==============================================================================================

Reads Cowork session transcripts from the Claude projects directory, extracts
instruction/response pairs with chain-of-thought detection, and inserts them
into session_training.db alongside OpenClaw and Claude Code pairs.

The session_distiller.py handles OpenClaw + Claude Code. This handles Cowork.
Same DB, same Alpaca format, same CoT columns. All three sources feed the
LoRA fine-tuning pipeline for the 35B model.

Pipeline:
  1. Scan for Cowork transcript JSONL files
  2. Extract instruction/response pairs (user message → assistant response)
  3. Detect chain-of-thought reasoning patterns
  4. Detect tool use sequences (Read, Edit, Bash, Grep, etc.)
  5. Classify by domain (trading, architecture, coding, etc.)
  6. Insert into session_training.db with source='cowork'
  7. Write to vault learnings for narrative memory

Usage:
  python cowork_distiller.py                    # Process all unprocessed transcripts
  python cowork_distiller.py --status           # Show stats
  python cowork_distiller.py --session <id>     # Process specific session
"""

import argparse
import glob
import json
import os
import re
import sqlite3
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple

JARVIS_ROOT = Path(__file__).parent.parent
TRAINING_DIR = JARVIS_ROOT / "training_data" / "sessions"
TRAINING_DB = TRAINING_DIR / "session_training.db"

# Cowork transcript locations — Claude stores them here
COWORK_PROJECTS_DIR = Path.home() / ".claude" / "projects"

# Minimum lengths to consider a pair "substantive"
MIN_USER_CHARS = 30
MIN_ASSISTANT_CHARS = 150
MAX_ASSISTANT_CHARS = 15000

# Domain classification keywords (same as session_distiller.py)
DOMAIN_KEYWORDS = {
    "coding": ["python", "function", "class", "import", "def ", "error", "bug", "fix", "code",
               "script", "module", "refactor", "test", "debug", "traceback", "exception"],
    "trading": ["trade", "forex", "oanda", "pair", "ema", "rsi", "bollinger", "candle", "pip",
                "sniper", "thesis", "validator", "scout", "guardian", "backtest", "confluence",
                "expansion", "fan", "snipe", "position", "entry", "exit", "stop loss",
                "reconcil", "pnl", "learning_integrator", "trade_auditor", "outcome"],
    "architecture": ["agent", "pipeline", "swarm", "handler", "mcp", "workspace", "database",
                      "schema", "table", "api", "endpoint", "route", "server", "model", "prompt",
                      "vault", "knowledge", "distill", "training"],
    "system": ["openclaw", "mlx", "ollama", "config", "cron", "heartbeat", "telegram",
               "dashboard", "deploy", "install", "port", "process", "cowork", "trevor"],
    "analysis": ["data", "chart", "graph", "metric", "pattern", "trend", "correlation",
                 "statistics", "performance", "result", "compare"],
}

# Chain-of-thought indicators
COT_INDICATORS = [
    "Found", "The issue is", "Let me check", "I see",
    "First,", "Second,", "Third,", "Next,", "Finally,",
    "Here's what", "The problem", "This is because",
    "Step 1", "Step 2", "Step 3",
    "Root cause", "The fix", "The root cause",
    "Chain of thought", "I need to",
]

# Tool use patterns in Cowork responses
TOOL_PATTERNS = [
    r"Read tool", r"Edit tool", r"Bash tool", r"Grep tool", r"Glob tool",
    r"<tool_use>", r"tool_use", r"```python", r"```bash",
    r"Let me read", r"Let me search", r"Let me check",
]


def classify_domain(text: str) -> str:
    """Classify text into a domain based on keyword density."""
    text_lower = text.lower()
    scores = {}
    for domain, keywords in DOMAIN_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw in text_lower)
        if score > 0:
            scores[domain] = score
    if not scores:
        return "general"
    return max(scores, key=scores.get)


def has_code_block(text: str) -> bool:
    return "```" in text or "def " in text or "import " in text


def detect_cot(text: str) -> Tuple[bool, str]:
    """Detect chain-of-thought reasoning in text."""
    paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
    if len(paragraphs) < 2 or len(text) < 200:
        return False, ""

    indicator_count = sum(1 for ind in COT_INDICATORS if ind in text)
    has_numbered_steps = bool(re.search(r'\b(\d+\.|\d+\))\s+\w', text))
    has_bullets = bool(re.search(r'\n\s*[-•*]\s+\w', text))
    has_code_explanation = has_code_block(text) and indicator_count >= 2

    if indicator_count >= 3 or has_numbered_steps or has_code_explanation:
        return True, text
    return False, ""


def detect_tool_use(text: str) -> bool:
    return any(re.search(p, text, re.IGNORECASE) for p in TOOL_PATTERNS)


def find_cowork_transcripts() -> List[Path]:
    """Find all Cowork session transcript JSONL files."""
    transcripts = []
    if COWORK_PROJECTS_DIR.exists():
        for jsonl in COWORK_PROJECTS_DIR.rglob("*.jsonl"):
            # Filter for Cowork sessions (they have 'sessions' in path)
            if "sessions" in str(jsonl).lower():
                transcripts.append(jsonl)
    return sorted(transcripts, key=lambda p: p.stat().st_mtime, reverse=True)


def get_processed_sessions(conn: sqlite3.Connection) -> set:
    """Get set of already-processed session keys."""
    rows = conn.execute(
        "SELECT DISTINCT session_key FROM training_pairs WHERE source = 'cowork'"
    ).fetchall()
    return {r[0] for r in rows}


def extract_pairs_from_jsonl(jsonl_path: Path) -> List[Dict]:
    """Extract instruction/response pairs from a Cowork transcript JSONL."""
    pairs = []
    messages = []

    with open(jsonl_path) as f:
        for line in f:
            try:
                msg = json.loads(line.strip())
                messages.append(msg)
            except json.JSONDecodeError:
                continue

    # Walk through messages looking for user→assistant pairs
    i = 0
    while i < len(messages) - 1:
        msg = messages[i]

        if msg.get("role") == "user":
            user_text = msg.get("content", "")
            if isinstance(user_text, list):
                user_text = " ".join(
                    b.get("text", "") for b in user_text
                    if isinstance(b, dict) and b.get("type") == "text"
                )

            # Skip trivial / system messages
            if not user_text or len(user_text) < MIN_USER_CHARS:
                i += 1
                continue
            skip_patterns = ["HEARTBEAT", "Pre-compaction", "NO_REPLY", "System:",
                           "[message_id:", "summary below covers"]
            if any(p in user_text[:200] for p in skip_patterns):
                i += 1
                continue

            # Collect assistant response (may span multiple message blocks with tool use)
            j = i + 1
            asst_parts = []
            tool_calls = []

            while j < len(messages):
                amsg = messages[j]
                if amsg.get("role") == "user" and j > i + 1:
                    break  # Next user turn

                content = amsg.get("content", "")
                if amsg.get("role") == "assistant":
                    if isinstance(content, str):
                        asst_parts.append(content)
                    elif isinstance(content, list):
                        for block in content:
                            if isinstance(block, dict):
                                if block.get("type") == "text":
                                    asst_parts.append(block.get("text", ""))
                                elif block.get("type") == "tool_use":
                                    tool_calls.append({
                                        "name": block.get("name", ""),
                                        "input": block.get("input", {}),
                                    })
                j += 1

            asst_text = "\n".join(p for p in asst_parts if p.strip())

            if not asst_text or len(asst_text) < MIN_ASSISTANT_CHARS:
                i = j
                continue

            # Truncate extremely long responses
            if len(asst_text) > MAX_ASSISTANT_CHARS:
                asst_text = asst_text[:MAX_ASSISTANT_CHARS] + "\n[truncated]"

            # Classify
            combined = user_text + " " + asst_text
            domain = classify_domain(combined)
            has_cot, cot_text = detect_cot(asst_text)
            has_tool = detect_tool_use(asst_text) or len(tool_calls) > 0
            has_code = has_code_block(asst_text)

            # Build tool context for instruction if tools were used
            instruction = user_text
            if tool_calls:
                tool_names = list(set(t["name"] for t in tool_calls))
                instruction += f"\n\n[Tools used: {', '.join(tool_names)}]"

            pairs.append({
                "instruction": instruction,
                "response": asst_text,
                "domain": domain,
                "has_code": 1 if has_code else 0,
                "has_tool_use": 1 if has_tool else 0,
                "has_cot": 1 if has_cot else 0,
                "cot_text": cot_text if has_cot else "",
                "quality_score": _estimate_quality(user_text, asst_text, has_cot, has_code, len(tool_calls)),
            })

            i = j
        else:
            i += 1

    return pairs


def _estimate_quality(user: str, asst: str, has_cot: bool, has_code: bool, tool_count: int) -> float:
    """Heuristic quality score 0.0-1.0 based on content signals."""
    score = 0.5  # baseline

    # Length bonuses
    if len(asst) > 500:
        score += 0.1
    if len(asst) > 1500:
        score += 0.1

    # CoT is high value
    if has_cot:
        score += 0.15

    # Code + explanation = high value
    if has_code and has_cot:
        score += 0.1

    # Tool use = real work, not just chat
    if tool_count > 0:
        score += 0.05

    return min(score, 1.0)


def process_transcript(jsonl_path: Path, session_key: str, conn: sqlite3.Connection) -> int:
    """Process one transcript and insert pairs into DB."""
    pairs = extract_pairs_from_jsonl(jsonl_path)
    if not pairs:
        return 0

    now = datetime.now().isoformat(timespec='seconds')
    inserted = 0

    for p in pairs:
        conn.execute("""
            INSERT INTO training_pairs (
                session_key, timestamp, domain, instruction, response,
                instruction_len, response_len, has_code, has_tool_use,
                has_cot, cot_text, quality_score, source, skill_name, exported
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'cowork', NULL, 0)
        """, (
            session_key, now, p["domain"],
            p["instruction"], p["response"],
            len(p["instruction"]), len(p["response"]),
            p["has_code"], p["has_tool_use"],
            p["has_cot"], p["cot_text"],
            p["quality_score"],
        ))
        inserted += 1

    conn.commit()
    return inserted


def process_all():
    """Process all unprocessed Cowork transcripts."""
    conn = sqlite3.connect(str(TRAINING_DB), timeout=10)
    processed = get_processed_sessions(conn)

    transcripts = find_cowork_transcripts()
    print(f"Found {len(transcripts)} Cowork transcripts, {len(processed)} already processed")

    total_inserted = 0
    for t in transcripts:
        session_key = f"cowork-{t.stem}"
        if session_key in processed:
            continue

        pairs_count = process_transcript(t, session_key, conn)
        if pairs_count > 0:
            print(f"  {t.name}: {pairs_count} pairs extracted")
            total_inserted += pairs_count

    conn.close()
    print(f"\nTotal new pairs: {total_inserted}")
    return total_inserted


def get_stats():
    """Show training data stats for Cowork source."""
    conn = sqlite3.connect(str(TRAINING_DB), timeout=10)

    total = conn.execute("SELECT COUNT(*) FROM training_pairs WHERE source = 'cowork'").fetchone()[0]
    exported = conn.execute("SELECT COUNT(*) FROM training_pairs WHERE source = 'cowork' AND exported = 1").fetchone()[0]
    with_cot = conn.execute("SELECT COUNT(*) FROM training_pairs WHERE source = 'cowork' AND has_cot = 1").fetchone()[0]
    with_code = conn.execute("SELECT COUNT(*) FROM training_pairs WHERE source = 'cowork' AND has_code = 1").fetchone()[0]
    with_tools = conn.execute("SELECT COUNT(*) FROM training_pairs WHERE source = 'cowork' AND has_tool_use = 1").fetchone()[0]

    domains = {}
    for row in conn.execute(
        "SELECT domain, COUNT(*), AVG(response_len) FROM training_pairs WHERE source = 'cowork' GROUP BY domain"
    ):
        domains[row[0]] = {"count": row[1], "avg_response_len": round(row[2]) if row[2] else 0}

    sessions = conn.execute(
        "SELECT DISTINCT session_key FROM training_pairs WHERE source = 'cowork'"
    ).fetchall()

    # Compare to other sources
    openclaw = conn.execute("SELECT COUNT(*) FROM training_pairs WHERE source = 'openclaw'").fetchone()[0]
    claude_code = conn.execute("SELECT COUNT(*) FROM training_pairs WHERE source = 'claude_code'").fetchone()[0]

    conn.close()

    print("=" * 50)
    print("Cowork Distiller Stats")
    print("=" * 50)
    print(f"  Total pairs:     {total}")
    print(f"  Exported:        {exported}")
    print(f"  Pending export:  {total - exported}")
    print(f"  With CoT:        {with_cot}")
    print(f"  With code:       {with_code}")
    print(f"  With tool use:   {with_tools}")
    print(f"  Sessions:        {len(sessions)}")
    print(f"\n  By domain:")
    for d, info in sorted(domains.items()):
        print(f"    {d:15s}: {info['count']:4d} pairs (avg {info['avg_response_len']:,d} chars)")
    print(f"\n  All sources:")
    print(f"    OpenClaw:      {openclaw:,d}")
    print(f"    Claude Code:   {claude_code:,d}")
    print(f"    Cowork:        {total:,d}")
    print(f"    TOTAL:         {openclaw + claude_code + total:,d}")


def main():
    parser = argparse.ArgumentParser(description="Cowork Session Distiller")
    parser.add_argument("--status", action="store_true", help="Show stats")
    parser.add_argument("--session", type=str, help="Process specific session JSONL path")
    args = parser.parse_args()

    if args.status:
        get_stats()
    elif args.session:
        conn = sqlite3.connect(str(TRAINING_DB), timeout=10)
        path = Path(args.session)
        key = f"cowork-{path.stem}"
        n = process_transcript(path, key, conn)
        conn.close()
        print(f"Extracted {n} pairs from {path.name}")
    else:
        process_all()


if __name__ == "__main__":
    main()
