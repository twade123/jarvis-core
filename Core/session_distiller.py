#!/usr/bin/env python3
"""
Session Distiller — Capture Trevor↔Tim conversations as training data.
=====================================================================

Every Opus response Trevor gives Tim is premium training data. This module
extracts high-quality instruction/response pairs from OpenClaw session history
and stores them for fine-tuning.

Domains captured:
  - Coding (Python, architecture, debugging)
  - Trading strategy (thesis, indicators, backtesting)
  - System administration (config, MLX, MCP, OpenClaw)
  - Analysis (data analysis, market research)
  - General knowledge (explanations, decisions)

Pipeline:
  1. Pull session history from OpenClaw API
  2. Chunk into instruction/response pairs (user message → assistant response)
  3. Classify by domain + quality
  4. Filter: skip short/trivial, keep substantive exchanges
  5. Store in training JSONL (Alpaca format for MLX LoRA fine-tuning)

Usage:
  python session_distiller.py --extract          # Extract from recent sessions
  python session_distiller.py --status           # Check training data stats
  python session_distiller.py --export           # Export JSONL for fine-tuning
"""

import json
import os
import sys
import sqlite3
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Any, Optional

JARVIS_ROOT = Path(__file__).parent.parent
TRAINING_DIR = JARVIS_ROOT / "training_data" / "sessions"
TRAINING_DB = TRAINING_DIR / "session_training.db"
OUTPUT_JSONL = TRAINING_DIR / "session_training.jsonl"

# Minimum lengths to consider a pair "substantive"
MIN_USER_CHARS = 20        # Skip "ok" / "yes" / "nice"
MIN_ASSISTANT_CHARS = 100  # Skip short acks
MAX_ASSISTANT_CHARS = 15000  # Truncate extremely long responses

# Domain classification keywords
DOMAIN_KEYWORDS = {
    "coding": ["python", "function", "class", "import", "def ", "error", "bug", "fix", "code",
               "script", "module", "refactor", "test", "debug", "traceback", "exception"],
    "trading": ["trade", "forex", "oanda", "pair", "ema", "rsi", "bollinger", "candle", "pip",
                "sniper", "thesis", "validator", "scout", "guardian", "backtest", "confluence",
                "expansion", "fan", "snipe", "position", "entry", "exit", "stop loss"],
    "architecture": ["agent", "pipeline", "swarm", "handler", "mcp", "workspace", "database",
                      "schema", "table", "api", "endpoint", "route", "server", "model", "prompt"],
    "system": ["openclaw", "mlx", "ollama", "config", "cron", "heartbeat", "telegram",
               "dashboard", "deploy", "install", "port", "process"],
    "analysis": ["data", "chart", "graph", "metric", "pattern", "trend", "correlation",
                 "statistics", "performance", "result", "compare"],
}


def init_db():
    """Create session training database."""
    TRAINING_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(TRAINING_DB))

    # Create tables with IF NOT EXISTS
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS training_pairs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_key TEXT,
            timestamp TEXT,
            domain TEXT,
            instruction TEXT NOT NULL,
            response TEXT NOT NULL,
            instruction_len INTEGER,
            response_len INTEGER,
            has_code INTEGER DEFAULT 0,
            has_tool_use INTEGER DEFAULT 0,
            quality_score REAL DEFAULT NULL,
            exported INTEGER DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS task_arcs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_key TEXT,
            started_at TEXT,
            ended_at TEXT,
            turn_count INTEGER,
            domain TEXT,
            messages_json TEXT NOT NULL,
            quality_score REAL DEFAULT NULL,
            exported INTEGER DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS extraction_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_key TEXT,
            pairs_extracted INTEGER,
            pairs_skipped INTEGER,
            extracted_at TEXT DEFAULT (datetime('now'))
        );

        CREATE INDEX IF NOT EXISTS idx_pairs_domain ON training_pairs(domain);
        CREATE INDEX IF NOT EXISTS idx_pairs_exported ON training_pairs(exported);
        CREATE INDEX IF NOT EXISTS idx_pairs_quality ON training_pairs(quality_score);
        CREATE INDEX IF NOT EXISTS idx_task_arcs_domain ON task_arcs(domain);
        CREATE INDEX IF NOT EXISTS idx_task_arcs_exported ON task_arcs(exported);
    """)

    # Migrate existing schema - add COT and source columns if missing
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(training_pairs)")
    columns = {row[1] for row in cursor.fetchall()}

    if "has_cot" not in columns:
        print("Migrating database: adding COT columns...")
        conn.execute("ALTER TABLE training_pairs ADD COLUMN has_cot INTEGER DEFAULT 0")
        conn.execute("ALTER TABLE training_pairs ADD COLUMN cot_text TEXT")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_pairs_cot ON training_pairs(has_cot)")
        conn.commit()
        print("Migration complete")

    if "source" not in columns:
        print("Migrating database: adding source column...")
        conn.execute("ALTER TABLE training_pairs ADD COLUMN source TEXT DEFAULT 'openclaw'")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_pairs_source ON training_pairs(source)")
        conn.commit()
        print("Migration complete")

    if "skill_name" not in columns:
        print("Migrating database: adding skill_name column...")
        conn.execute("ALTER TABLE training_pairs ADD COLUMN skill_name TEXT DEFAULT NULL")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_pairs_skill ON training_pairs(skill_name)")
        conn.commit()
        print("Migration complete")

    conn.close()


def classify_domain(text: str) -> str:
    """Classify a conversation pair into a domain based on keyword density."""
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
    """Check if text contains code."""
    return "```" in text or "def " in text or "import " in text


def has_chain_of_thought(text: str) -> tuple[bool, str]:
    """Detect if text contains diagnostic chain-of-thought reasoning.

    Returns:
        (has_cot, cot_text): Tuple of bool and extracted COT text
    """
    # COT indicators
    cot_indicators = [
        "Found", "The issue is", "Let me check", "I see",
        "First,", "Second,", "Third,", "Next,", "Finally,",
        "Here's what", "The problem", "This is because",
        "Step 1", "Step 2", "Step 3",
    ]

    # Must be multi-paragraph and substantive
    paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
    if len(paragraphs) < 2 or len(text) < 200:
        return False, ""

    # Check for COT markers
    indicator_count = sum(1 for ind in cot_indicators if ind in text)

    # Look for numbered lists or bullet reasoning
    has_numbered_steps = bool(re.search(r'\b(\d+\.|\d+\))\s+\w', text))
    has_bullets = bool(re.search(r'\n\s*[-•*]\s+\w', text))

    # Contains code + explanation is a good COT signal
    has_code_explanation = has_code_block(text) and indicator_count >= 2

    if indicator_count >= 3 or has_numbered_steps or has_code_explanation:
        return True, text

    return False, ""


def extract_tool_sequence(messages: List[Dict], start_idx: int) -> Optional[Dict]:
    """Extract a tool-use sequence starting from start_idx.

    Returns dict with instruction + tool calls + final response, or None.
    """
    if start_idx >= len(messages):
        return None

    user_msg = messages[start_idx]
    if user_msg.get("role") != "user":
        return None

    user_text = user_msg.get("content", "")
    if isinstance(user_text, list):
        user_text = " ".join(
            b.get("text", "") for b in user_text
            if isinstance(b, dict) and b.get("type") == "text"
        )

    # Collect tool calls and results
    tool_calls = []
    final_response = None

    i = start_idx + 1
    while i < len(messages):
        msg = messages[i]
        content = msg.get("content", [])

        # Look for tool_use and tool_result in content blocks
        if isinstance(content, list):
            for block in content:
                if isinstance(block, dict):
                    if block.get("type") == "tool_use":
                        tool_calls.append({
                            "name": block.get("name"),
                            "input": block.get("input")
                        })
                    elif block.get("type") == "tool_result":
                        if tool_calls:  # Associate with last tool call
                            tool_calls[-1]["result"] = block.get("content")
                    elif block.get("type") == "text" and msg.get("role") == "assistant":
                        # Final assistant response
                        final_response = block.get("text", "")

        # Stop when we hit next user message
        if msg.get("role") == "user" and i > start_idx + 1:
            break

        i += 1

    if not tool_calls or not final_response:
        return None

    # Build instruction with tool context
    tool_context = f"\n\nUsing tools: {', '.join(t['name'] for t in tool_calls)}"
    instruction = user_text + tool_context

    # Build response with tool sequence
    response_parts = []
    for tc in tool_calls:
        response_parts.append(f"[Tool: {tc['name']}]")
        if tc.get("input"):
            response_parts.append(f"Input: {json.dumps(tc['input'])}")
        if tc.get("result"):
            response_parts.append(f"Result: {tc['result']}")
    response_parts.append(f"\n{final_response}")
    response = "\n".join(response_parts)

    return {
        "instruction": instruction,
        "response": response,
        "tool_count": len(tool_calls),
        "has_tool_use": True
    }


def detect_task_boundaries(messages: List[Dict]) -> List[tuple]:
    """Detect task arc boundaries in message list.

    Returns:
        List of (start_idx, end_idx) tuples marking task boundaries
    """
    # Completion indicators
    completion_phrases = ["ok", "good", "thanks", "got it", "looks good",
                         "perfect", "great", "thank you", "awesome", "nice",
                         "that works", "sounds good"]

    arcs = []
    start_idx = None

    for i, msg in enumerate(messages):
        if msg.get("role") == "user":
            content = msg.get("content", "")
            if isinstance(content, list):
                content = " ".join(
                    b.get("text", "") for b in content
                    if isinstance(b, dict) and b.get("type") == "text"
                )

            content_lower = content.lower().strip()

            # Check if this is a completion acknowledgment
            is_completion = any(phrase in content_lower for phrase in completion_phrases)
            is_short = len(content_lower.split()) <= 3

            if is_completion and is_short:
                # End current arc
                if start_idx is not None:
                    arcs.append((start_idx, i))
                    start_idx = None
            elif start_idx is None and len(content) > MIN_USER_CHARS:
                # Start new arc
                start_idx = i

    # Capture any unclosed arc at the end
    if start_idx is not None:
        arcs.append((start_idx, len(messages) - 1))

    return arcs


def extract_pairs_from_messages(messages: List[Dict], session_key: str = "") -> List[Dict]:
    """Extract instruction/response pairs from a message list.
    
    Messages should be [{role: "user"/"assistant", content: "..."}]
    """
    pairs = []
    
    i = 0
    while i < len(messages) - 1:
        msg = messages[i]
        
        # Find user message
        if msg.get("role") == "user":
            user_text = msg.get("content", "")
            if isinstance(user_text, list):
                # Handle content blocks
                user_text = " ".join(
                    b.get("text", "") for b in user_text 
                    if isinstance(b, dict) and b.get("type") == "text"
                )
            
            # Skip system messages, heartbeats, compaction prompts
            if not user_text or len(user_text) < MIN_USER_CHARS:
                i += 1
                continue
            skip_patterns = ["HEARTBEAT", "Pre-compaction", "NO_REPLY", "HEARTBEAT_OK",
                           "System:", "[message_id:"]
            if any(p in user_text[:100] for p in skip_patterns):
                i += 1
                continue
            
            # Find next assistant response
            j = i + 1
            while j < len(messages) and messages[j].get("role") != "assistant":
                j += 1
            
            if j < len(messages):
                asst_text = messages[j].get("content", "")
                if isinstance(asst_text, list):
                    asst_text = " ".join(
                        b.get("text", "") for b in asst_text
                        if isinstance(b, dict) and b.get("type") == "text"
                    )
                
                # Skip trivial responses
                if not asst_text or len(asst_text) < MIN_ASSISTANT_CHARS:
                    i = j + 1
                    continue
                if asst_text.strip() in ["NO_REPLY", "HEARTBEAT_OK"]:
                    i = j + 1
                    continue
                
                # Truncate very long responses
                if len(asst_text) > MAX_ASSISTANT_CHARS:
                    asst_text = asst_text[:MAX_ASSISTANT_CHARS] + "\n[...truncated for training]"
                
                combined = user_text + " " + asst_text
                domain = classify_domain(combined)

                # Check for chain of thought
                has_cot, cot_text = has_chain_of_thought(asst_text)

                pair = {
                    "session_key": session_key,
                    "timestamp": msg.get("timestamp", datetime.now(timezone.utc).isoformat()),
                    "domain": domain,
                    "instruction": user_text,
                    "response": asst_text,
                    "instruction_len": len(user_text),
                    "response_len": len(asst_text),
                    "has_code": has_code_block(asst_text),
                    "has_tool_use": False,  # Will be updated if tools detected
                    "has_cot": has_cot,
                    "cot_text": cot_text if has_cot else None,
                }
                pairs.append(pair)
                i = j + 1
            else:
                i += 1
        else:
            i += 1
    
    return pairs


# Positive quality signal phrases — user explicitly praising the output
POSITIVE_QUALITY_SIGNALS = [
    "perfect", "exactly", "nailed it", "that's exactly", "thats exactly",
    "great job", "well done", "that's what i wanted", "thats what i wanted",
    "exactly right", "exactly what i needed", "spot on", "love it",
    "that's perfect", "thats perfect", "awesome job",
]


def _extract_skill_name_from_text(text: str) -> Optional[str]:
    """
    Parse a SKILL.md YAML frontmatter block and return the skill name.
    Returns None if the text is not a SKILL.md.

    Expected format:
        ---
        name: canvas-design
        description: ...
        ---
    """
    text = text.strip()
    if not text.startswith("---"):
        return None
    # Must have both name: and description: to be a SKILL.md (not some other YAML file)
    if "name:" not in text[:300] or "description:" not in text[:600]:
        return None
    for line in text.split("\n"):
        line = line.strip()
        if line.startswith("name:"):
            name = line[len("name:"):].strip().strip('"').strip("'")
            if name:
                return name
    return None


def extract_skill_pairs_from_messages(messages: List[Dict],
                                       session_key: str = "") -> List[Dict]:
    """
    Extract skill-tagged training pairs from an OpenClaw message list.

    OpenClaw transcripts interleave:
      role=user        — the original request
      role=assistant   — thinking turns (often empty text)
      role=toolResult  — tool outputs, including SKILL.md file content
      role=assistant   — final response (the one with real content)

    This function:
    1. Scans for toolResult messages containing SKILL.md frontmatter
    2. Traces back to the nearest preceding user message
    3. Scans forward for the next substantial assistant response
    4. Returns training pairs tagged with skill_name

    Also detects positive quality signals (user praise after response)
    and sets quality_score = 1.0 on the preceding pair.
    """
    pairs = []

    for i, msg in enumerate(messages):
        if msg.get("role") != "toolResult":
            continue

        # Check if this toolResult is a SKILL.md read
        content = msg.get("content", "")
        if isinstance(content, list):
            text = " ".join(
                b.get("text", "") for b in content
                if isinstance(b, dict) and b.get("type") == "text"
            )
        else:
            text = str(content)

        skill_name = _extract_skill_name_from_text(text)
        if not skill_name:
            continue

        # ── Find preceding user message ───────────────────────────────
        user_text = None
        user_ts = None
        for j in range(i - 1, -1, -1):
            prev = messages[j]
            if prev.get("role") == "user":
                raw = prev.get("content", "")
                if isinstance(raw, list):
                    user_text = " ".join(
                        b.get("text", "") for b in raw
                        if isinstance(b, dict) and b.get("type") == "text"
                    )
                else:
                    user_text = str(raw)
                user_ts = prev.get("timestamp", "")
                break

        if not user_text or len(user_text) < MIN_USER_CHARS:
            continue

        # Skip system / heartbeat messages
        skip_patterns = ["HEARTBEAT", "Pre-compaction", "NO_REPLY", "[message_id:"]
        if any(p in user_text[:100] for p in skip_patterns):
            continue

        # ── Find the next substantial assistant response ──────────────
        response_text = None
        response_ts = None
        for k in range(i + 1, min(i + 20, len(messages))):
            nxt = messages[k]
            if nxt.get("role") != "assistant":
                continue
            raw = nxt.get("content", "")
            if isinstance(raw, list):
                candidate = " ".join(
                    b.get("text", "") for b in raw
                    if isinstance(b, dict) and b.get("type") == "text"
                )
            else:
                candidate = str(raw)
            if len(candidate) >= MIN_ASSISTANT_CHARS:
                response_text = candidate
                response_ts = nxt.get("timestamp", "")
                break

        if not response_text:
            continue

        # Truncate very long responses
        if len(response_text) > MAX_ASSISTANT_CHARS:
            response_text = response_text[:MAX_ASSISTANT_CHARS] + "\n[...truncated for training]"

        # ── Check next user message for positive quality signal ───────
        quality_score = None
        for m in range(k + 1, min(k + 5, len(messages))):
            nxt2 = messages[m]
            if nxt2.get("role") != "user":
                continue
            raw2 = nxt2.get("content", "")
            if isinstance(raw2, list):
                ack = " ".join(
                    b.get("text", "") for b in raw2
                    if isinstance(b, dict) and b.get("type") == "text"
                ).lower()
            else:
                ack = str(raw2).lower()
            if any(sig in ack for sig in POSITIVE_QUALITY_SIGNALS):
                quality_score = 1.0
            break  # only check immediately following user message

        combined = user_text + " " + response_text
        domain = "skill:" + skill_name.lower().replace(" ", "-")
        has_cot, cot_text = has_chain_of_thought(response_text)

        pair = {
            "session_key": session_key,
            "timestamp": user_ts or datetime.now(timezone.utc).isoformat(),
            "domain": domain,
            "skill_name": skill_name,
            "instruction": user_text,
            "response": response_text,
            "instruction_len": len(user_text),
            "response_len": len(response_text),
            "has_code": has_code_block(response_text),
            "has_tool_use": True,
            "has_cot": has_cot,
            "cot_text": cot_text if has_cot else None,
            "quality_score": quality_score,
            "source": "openclaw",
        }
        pairs.append(pair)

    return pairs


def store_pairs(pairs: List[Dict]) -> int:
    """Store extracted pairs in the training database. Returns count stored."""
    conn = sqlite3.connect(str(TRAINING_DB))
    stored = 0

    for pair in pairs:
        try:
            conn.execute("""
                INSERT INTO training_pairs
                (session_key, timestamp, domain, instruction, response,
                 instruction_len, response_len, has_code, has_tool_use, has_cot, cot_text,
                 source, skill_name, quality_score)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, [
                pair["session_key"], pair["timestamp"], pair["domain"],
                pair["instruction"], pair["response"],
                pair["instruction_len"], pair["response_len"],
                1 if pair["has_code"] else 0,
                1 if pair["has_tool_use"] else 0,
                1 if pair.get("has_cot", False) else 0,
                pair.get("cot_text"),
                pair.get("source", "openclaw"),
                pair.get("skill_name"),
                pair.get("quality_score"),
            ])
            stored += 1
        except sqlite3.IntegrityError:
            pass  # Duplicate

    conn.commit()
    conn.close()
    return stored


def export_jsonl(min_response_len: int = 200, domains: List[str] = None) -> int:
    """Export training pairs as JSONL in Alpaca format for MLX LoRA fine-tuning.
    
    Format: {"instruction": "...", "input": "", "output": "..."}
    """
    conn = sqlite3.connect(str(TRAINING_DB))
    
    query = "SELECT instruction, response, domain FROM training_pairs WHERE exported = 0 AND response_len >= ?"
    params = [min_response_len]
    
    if domains:
        placeholders = ",".join("?" for _ in domains)
        query += f" AND domain IN ({placeholders})"
        params.extend(domains)
    
    rows = conn.execute(query, params).fetchall()
    
    exported = 0
    with open(OUTPUT_JSONL, "a") as f:
        for instruction, response, domain in rows:
            entry = {
                "instruction": instruction,
                "input": "",
                "output": response,
                "domain": domain,
            }
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
            exported += 1
    
    if exported:
        conn.execute(
            f"UPDATE training_pairs SET exported = 1 WHERE exported = 0 AND response_len >= ?",
            [min_response_len]
        )
        conn.commit()
    
    conn.close()
    return exported


def get_stats() -> Dict[str, Any]:
    """Get training data statistics."""
    conn = sqlite3.connect(str(TRAINING_DB))

    total = conn.execute("SELECT COUNT(*) FROM training_pairs").fetchone()[0]
    exported = conn.execute("SELECT COUNT(*) FROM training_pairs WHERE exported = 1").fetchone()[0]

    domains = {}
    for row in conn.execute("SELECT domain, COUNT(*), AVG(response_len) FROM training_pairs GROUP BY domain"):
        domains[row[0]] = {"count": row[1], "avg_response_len": round(row[2]) if row[2] else 0}

    with_code = conn.execute("SELECT COUNT(*) FROM training_pairs WHERE has_code = 1").fetchone()[0]
    with_cot = conn.execute("SELECT COUNT(*) FROM training_pairs WHERE has_cot = 1").fetchone()[0]
    with_tool_use = conn.execute("SELECT COUNT(*) FROM training_pairs WHERE has_tool_use = 1").fetchone()[0]

    # Task arcs stats
    task_arcs_count = conn.execute("SELECT COUNT(*) FROM task_arcs").fetchone()[0]
    task_arcs_exported = conn.execute("SELECT COUNT(*) FROM task_arcs WHERE exported = 1").fetchone()[0]

    # Recovery pairs
    recovery_count = conn.execute("SELECT COUNT(*) FROM training_pairs WHERE domain = 'recovery'").fetchone()[0]

    # Source breakdown (openclaw vs claude_code)
    openclaw_count = conn.execute("SELECT COUNT(*) FROM training_pairs WHERE source = 'openclaw'").fetchone()[0]
    claude_code_count = conn.execute("SELECT COUNT(*) FROM training_pairs WHERE source = 'claude_code'").fetchone()[0]

    conn.close()

    return {
        "total_pairs": total,
        "exported": exported,
        "pending": total - exported,
        "sources": {
            "openclaw": openclaw_count,
            "claude_code": claude_code_count,
        },
        "domains": domains,
        "with_code": with_code,
        "with_cot": with_cot,
        "with_tool_use": with_tool_use,
        "task_arcs": task_arcs_count,
        "task_arcs_exported": task_arcs_exported,
        "recovery_pairs": recovery_count,
        "jsonl_path": str(OUTPUT_JSONL),
    }


# ── Ingest from OpenClaw session transcripts (JSONL) ──

SESSIONS_DIR = Path.home() / ".openclaw" / "agents" / "main" / "sessions"


def extract_from_transcript(jsonl_path: str, session_key: str = None) -> int:
    """Extract training pairs from an OpenClaw session transcript JSONL file.
    
    Each line is a JSON object with type='message' and message={role, content}.
    We pair user messages with their next assistant response.
    """
    if session_key is None:
        session_key = Path(jsonl_path).stem
    
    messages = []       # user + assistant only — for standard pair extraction
    all_messages = []   # includes toolResult — for skill execution detection
    with open(jsonl_path) as f:
        for line in f:
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue

            if entry.get("type") != "message":
                continue

            msg = entry.get("message", {})
            role = msg.get("role")
            if role not in ("user", "assistant", "toolResult"):
                continue

            # Extract text content
            content = msg.get("content", "")
            if isinstance(content, list):
                text_parts = []
                for block in content:
                    if isinstance(block, dict):
                        if block.get("type") == "text":
                            text_parts.append(block.get("text", ""))
                    elif isinstance(block, str):
                        text_parts.append(block)
                content = "\n".join(text_parts)

            if content and content.strip():
                record = {
                    "role": role,
                    "content": content.strip(),
                    "timestamp": entry.get("timestamp", ""),
                }
                all_messages.append(record)
                if role in ("user", "assistant"):
                    messages.append(record)
    
    # Standard user↔assistant pairs
    pairs = extract_pairs_from_messages(messages, session_key)

    # Skill-execution pairs — needs full message list including toolResult roles
    skill_pairs = extract_skill_pairs_from_messages(all_messages, session_key)
    if skill_pairs:
        pairs.extend(skill_pairs)
        # Write to vault for each skill execution found
        try:
            import sys as _sys
            _sys.path.insert(0, str(JARVIS_ROOT))
            from knowledge.vault_writer import VaultWriter
            writer = VaultWriter()
            for sp in skill_pairs:
                writer.record_skill_execution(
                    skill_name=sp["skill_name"],
                    task_summary=sp["instruction"][:200],
                    response_summary=sp["response"][:300],
                    quality_score=sp.get("quality_score"),
                    session_key=session_key,
                )
        except Exception as e:
            # Non-fatal — training data still stored even if vault write fails
            print(f"  vault_writer warning: {e}")

    if pairs:
        stored = store_pairs(pairs)
        return stored
    return 0


def extract_all_sessions(min_size_kb: int = 50, limit: int = None) -> Dict[str, Any]:
    """Extract training data from all OpenClaw session transcripts.
    
    Only processes sessions larger than min_size_kb (skip trivial sessions).
    """
    init_db()
    
    if not SESSIONS_DIR.exists():
        return {"error": f"Sessions directory not found: {SESSIONS_DIR}"}
    
    # Get already-processed sessions
    conn = sqlite3.connect(str(TRAINING_DB))
    processed = set(
        r[0] for r in conn.execute("SELECT DISTINCT session_key FROM extraction_log").fetchall()
    )
    conn.close()
    
    # Find transcript files
    transcripts = sorted(SESSIONS_DIR.glob("*.jsonl"), key=lambda p: p.stat().st_size, reverse=True)
    
    total_pairs = 0
    total_skipped = 0
    sessions_processed = 0
    
    for path in transcripts:
        if limit and sessions_processed >= limit:
            break
        
        session_key = path.stem
        
        # Skip already processed
        if session_key in processed:
            continue
        
        # Skip tiny sessions
        size_kb = path.stat().st_size / 1024
        if size_kb < min_size_kb:
            continue
        
        print(f"Processing {session_key} ({size_kb:.0f} KB)...")
        try:
            pairs_stored = extract_from_transcript(str(path), session_key)
            total_pairs += pairs_stored
            sessions_processed += 1
            
            # Log extraction
            conn = sqlite3.connect(str(TRAINING_DB))
            conn.execute(
                "INSERT INTO extraction_log (session_key, pairs_extracted, pairs_skipped) VALUES (?, ?, ?)",
                [session_key, pairs_stored, 0]
            )
            conn.commit()
            conn.close()
            
            print(f"  → {pairs_stored} training pairs extracted")
        except Exception as e:
            print(f"  → ERROR: {e}")
            total_skipped += 1
    
    return {
        "sessions_processed": sessions_processed,
        "sessions_skipped": total_skipped,
        "total_pairs": total_pairs,
        "transcripts_available": len(transcripts),
    }


def extract_tool_pairs_from_transcript(jsonl_path: str, session_key: str = None) -> int:
    """Extract tool-use training pairs from OpenClaw session transcripts.

    Returns count of tool pairs extracted.
    """
    if session_key is None:
        session_key = Path(jsonl_path).stem

    messages = []
    with open(jsonl_path) as f:
        for line in f:
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue

            if entry.get("type") != "message":
                continue

            msg = entry.get("message", {})
            messages.append(msg)

    tool_pairs = []
    i = 0
    while i < len(messages):
        tool_pair = extract_tool_sequence(messages, i)
        if tool_pair:
            tool_pair["session_key"] = session_key
            tool_pair["timestamp"] = messages[i].get("timestamp", datetime.now(timezone.utc).isoformat())
            tool_pair["domain"] = classify_domain(tool_pair["instruction"] + " " + tool_pair["response"])
            tool_pair["instruction_len"] = len(tool_pair["instruction"])
            tool_pair["response_len"] = len(tool_pair["response"])
            tool_pair["has_code"] = has_code_block(tool_pair["response"])
            has_cot, cot_text = has_chain_of_thought(tool_pair["response"])
            tool_pair["has_cot"] = has_cot
            tool_pair["cot_text"] = cot_text if has_cot else None
            tool_pairs.append(tool_pair)
            # Skip ahead past this sequence
            i += tool_pair.get("tool_count", 1) + 2
        else:
            i += 1

    if tool_pairs:
        return store_pairs(tool_pairs)
    return 0


def extract_task_arcs_from_transcript(jsonl_path: str, session_key: str = None) -> int:
    """Extract task arc bundles from OpenClaw session transcripts.

    Returns count of task arcs extracted.
    """
    if session_key is None:
        session_key = Path(jsonl_path).stem

    messages = []
    with open(jsonl_path) as f:
        for line in f:
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue

            if entry.get("type") != "message":
                continue

            msg = entry.get("message", {})
            role = msg.get("role")
            if role in ("user", "assistant"):
                messages.append(msg)

    arcs = detect_task_boundaries(messages)

    conn = sqlite3.connect(str(TRAINING_DB))
    stored = 0

    for start_idx, end_idx in arcs:
        arc_messages = messages[start_idx:end_idx + 1]
        turn_count = len(arc_messages)

        # Skip trivial arcs
        if turn_count < 4:
            continue

        # Build messages JSON (strip to essential content)
        arc_json = []
        for msg in arc_messages:
            content = msg.get("content", "")
            if isinstance(content, list):
                content = " ".join(
                    b.get("text", "") for b in content
                    if isinstance(b, dict) and b.get("type") == "text"
                )
            arc_json.append({
                "role": msg.get("role"),
                "content": content
            })

        # Classify domain based on full arc
        combined_text = " ".join(m["content"] for m in arc_json)
        domain = classify_domain(combined_text)

        started_at = messages[start_idx].get("timestamp", "")
        ended_at = messages[end_idx].get("timestamp", "")

        try:
            conn.execute("""
                INSERT INTO task_arcs
                (session_key, started_at, ended_at, turn_count, domain, messages_json)
                VALUES (?, ?, ?, ?, ?, ?)
            """, [
                session_key, started_at, ended_at, turn_count, domain,
                json.dumps(arc_json, ensure_ascii=False)
            ])
            stored += 1
        except sqlite3.IntegrityError:
            pass

    conn.commit()
    conn.close()
    return stored


def extract_recovery_pairs_from_transcript(jsonl_path: str, session_key: str = None) -> int:
    """Extract error-recovery training pairs.

    Returns count of recovery pairs extracted.
    """
    if session_key is None:
        session_key = Path(jsonl_path).stem

    messages = []
    with open(jsonl_path) as f:
        for line in f:
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue

            if entry.get("type") != "message":
                continue

            messages.append(entry.get("message", {}))

    recovery_pairs = []
    i = 0
    while i < len(messages) - 1:
        msg = messages[i]
        next_msg = messages[i + 1]

        # Look for tool_result with error in content
        content = msg.get("content", [])
        if isinstance(content, list):
            for block in content:
                if isinstance(block, dict) and block.get("type") == "tool_result":
                    result_content = block.get("content", "")
                    # Check for error indicators
                    if any(err in result_content.lower() for err in ["error", "failed", "exception", "traceback"]):
                        # Next assistant message is the fix
                        if next_msg.get("role") == "assistant":
                            asst_content = next_msg.get("content", [])
                            if isinstance(asst_content, list):
                                fix_text = " ".join(
                                    b.get("text", "") for b in asst_content
                                    if isinstance(b, dict) and b.get("type") == "text"
                                )
                                if fix_text and len(fix_text) > MIN_ASSISTANT_CHARS:
                                    # Build recovery pair
                                    instruction = f"Error occurred: {result_content}\n\nHow do you fix this?"
                                    response = fix_text

                                    has_cot, cot_text = has_chain_of_thought(response)

                                    recovery_pairs.append({
                                        "session_key": session_key,
                                        "timestamp": next_msg.get("timestamp", datetime.now(timezone.utc).isoformat()),
                                        "domain": "recovery",
                                        "instruction": instruction,
                                        "response": response,
                                        "instruction_len": len(instruction),
                                        "response_len": len(response),
                                        "has_code": has_code_block(response),
                                        "has_tool_use": False,
                                        "has_cot": has_cot,
                                        "cot_text": cot_text if has_cot else None,
                                    })
        i += 1

    if recovery_pairs:
        return store_pairs(recovery_pairs)
    return 0


def extract_claude_code_sessions(limit: int = None) -> Dict[str, Any]:
    """Extract training data from Claude Code session transcripts.

    Scans ~/.claude/projects/ for *.jsonl files and extracts:
    - Tool-use sequences (Read, Write, Edit, Bash tools)
    - Task arcs (problem → work → resolution)
    - Chain-of-thought reasoning in coding tasks

    Args:
        limit: Max number of sessions to process

    Returns:
        Dict with extraction statistics
    """
    init_db()

    claude_projects_dir = Path.home() / ".claude" / "projects"

    if not claude_projects_dir.exists():
        return {"error": f"Claude projects directory not found: {claude_projects_dir}"}

    # Find all JSONL files in projects and subagents
    jsonl_files = []
    for root, dirs, files in os.walk(claude_projects_dir):
        for file in files:
            if file.endswith('.jsonl'):
                jsonl_files.append(Path(root) / file)

    # Sort by modification time (most recent first)
    jsonl_files.sort(key=lambda p: p.stat().st_mtime, reverse=True)

    stats = {
        "sessions_processed": 0,
        "basic_pairs": 0,
        "tool_pairs": 0,
        "task_arcs": 0,
        "total_sessions_found": len(jsonl_files),
    }

    for jsonl_path in jsonl_files:
        if limit and stats["sessions_processed"] >= limit:
            break

        # Use relative path as session key
        session_key = str(jsonl_path.relative_to(claude_projects_dir))

        # Skip tiny files
        size_kb = jsonl_path.stat().st_size / 1024
        if size_kb < 10:
            continue

        print(f"Processing Claude Code session: {session_key} ({size_kb:.0f} KB)...")

        try:
            # Parse JSONL file
            messages = []
            with open(jsonl_path) as f:
                for line in f:
                    try:
                        entry = json.loads(line)

                        # Extract message content
                        msg_data = entry.get("message", {})
                        role = msg_data.get("role")

                        if role not in ("user", "assistant"):
                            continue

                        content = msg_data.get("content", "")

                        # Handle content blocks for assistant
                        if isinstance(content, list):
                            text_parts = []
                            for block in content:
                                if isinstance(block, dict):
                                    if block.get("type") == "text":
                                        text_parts.append(block.get("text", ""))
                            content = "\n".join(text_parts)

                        if content and content.strip():
                            messages.append({
                                "role": role,
                                "content": content.strip(),
                                "timestamp": entry.get("timestamp", ""),
                                "raw_message": msg_data  # Keep raw for tool extraction
                            })
                    except json.JSONDecodeError:
                        continue

            # Extract basic pairs
            basic_pairs = extract_pairs_from_messages(messages, session_key)
            # Mark as claude_code source
            for pair in basic_pairs:
                pair["source"] = "claude_code"
            stats["basic_pairs"] += store_pairs(basic_pairs)

            # Extract tool-use sequences
            tool_pairs = _extract_cc_tool_sequences(messages, session_key)
            stats["tool_pairs"] += store_pairs(tool_pairs)

            # Extract task arcs
            arcs = _extract_cc_task_arcs(messages, session_key)
            stats["task_arcs"] += arcs

            stats["sessions_processed"] += 1

            print(f"  → {len(basic_pairs)} basic, {len(tool_pairs)} tool, {arcs} arcs")

        except Exception as e:
            print(f"  → ERROR: {e}")

    return stats


def _extract_cc_tool_sequences(messages: List[Dict], session_key: str) -> List[Dict]:
    """Extract tool-use sequences from Claude Code sessions.

    Claude Code format has tool_use and tool_result blocks in assistant content.
    """
    tool_pairs = []

    i = 0
    while i < len(messages):
        msg = messages[i]

        if msg.get("role") != "user":
            i += 1
            continue

        user_text = msg.get("content", "")

        # Look ahead for assistant response with tools
        if i + 1 < len(messages):
            next_msg = messages[i + 1]
            if next_msg.get("role") == "assistant":
                raw_content = next_msg.get("raw_message", {}).get("content", [])

                # Extract tool calls
                tool_calls = []
                final_text = []

                thinking_chain = []  # Claude Code's actual reasoning blocks

                if isinstance(raw_content, list):
                    for block in raw_content:
                        if isinstance(block, dict):
                            if block.get("type") == "thinking":
                                # This is the gold — Claude Code's chain of thought
                                thinking_text = block.get("thinking", "").strip()
                                if thinking_text and len(thinking_text) > 50:
                                    thinking_chain.append(thinking_text)
                            elif block.get("type") == "tool_use":
                                tool_calls.append({
                                    "name": block.get("name"),
                                    "input": block.get("input")
                                })
                            elif block.get("type") == "tool_result":
                                if tool_calls:
                                    tool_calls[-1]["result"] = block.get("content", "")
                            elif block.get("type") == "text":
                                final_text.append(block.get("text", ""))

                # If we found tools or thinking, create a training pair
                if tool_calls or thinking_chain or final_text:
                    tool_context = f"\n\nUsing tools: {', '.join(t['name'] for t in tool_calls)}" if tool_calls else ""
                    instruction = user_text + tool_context

                    # Build response: thinking chain first, then tool sequence, then final answer
                    response_parts = []

                    # Prepend thinking chain — this is the chain of thought
                    if thinking_chain:
                        response_parts.append("<thinking>")
                        for thought in thinking_chain:
                            # Truncate very long thoughts but keep the substance
                            if len(thought) > 1000:
                                thought = thought[:1000] + "...[continued]"
                            response_parts.append(thought)
                        response_parts.append("</thinking>")

                    # Tool call sequence
                    for tc in tool_calls:
                        response_parts.append(f"[Tool: {tc['name']}]")
                        if tc.get("input"):
                            response_parts.append(f"Input: {json.dumps(tc['input'])}")
                        if tc.get("result"):
                            result_str = str(tc['result'])
                            if len(result_str) > 500:
                                result_str = result_str[:500] + "...[truncated]"
                            response_parts.append(f"Result: {result_str}")

                    # Final answer
                    if final_text:
                        response_parts.append("\n" + "\n".join(final_text))

                    response = "\n".join(response_parts)

                    has_cot = bool(thinking_chain)
                    cot_text = "\n\n".join(thinking_chain) if thinking_chain else None
                    domain = classify_domain(instruction + " " + response)

                    tool_pairs.append({
                        "session_key": session_key,
                        "timestamp": msg.get("timestamp", datetime.now(timezone.utc).isoformat()),
                        "domain": domain,
                        "instruction": instruction,
                        "response": response,
                        "instruction_len": len(instruction),
                        "response_len": len(response),
                        "has_code": has_code_block(response),
                        "has_tool_use": bool(tool_calls),
                        "has_cot": has_cot,
                        "cot_text": cot_text,
                        "source": "claude_code",
                    })

        i += 1

    return tool_pairs


def _extract_cc_task_arcs(messages: List[Dict], session_key: str) -> int:
    """Extract task arcs from Claude Code sessions and store in task_arcs table."""
    arcs = detect_task_boundaries(messages)

    conn = sqlite3.connect(str(TRAINING_DB))
    stored = 0

    for start_idx, end_idx in arcs:
        arc_messages = messages[start_idx:end_idx + 1]
        turn_count = len(arc_messages)

        # Skip trivial arcs
        if turn_count < 4:
            continue

        # Build messages JSON
        arc_json = []
        for msg in arc_messages:
            content = msg.get("content", "")
            arc_json.append({
                "role": msg.get("role"),
                "content": content
            })

        # Classify domain
        combined_text = " ".join(m["content"] for m in arc_json)
        domain = classify_domain(combined_text)

        started_at = messages[start_idx].get("timestamp", "")
        ended_at = messages[end_idx].get("timestamp", "")

        try:
            conn.execute("""
                INSERT INTO task_arcs
                (session_key, started_at, ended_at, turn_count, domain, messages_json)
                VALUES (?, ?, ?, ?, ?, ?)
            """, [
                session_key, started_at, ended_at, turn_count, domain,
                json.dumps(arc_json, ensure_ascii=False)
            ])
            stored += 1
        except sqlite3.IntegrityError:
            pass

    conn.commit()
    conn.close()
    return stored


def ingest_manual(instruction: str, response: str, domain: str = "general",
                  session_key: str = "manual") -> bool:
    """Manually add a training pair."""
    init_db()
    has_cot, cot_text = has_chain_of_thought(response)
    pairs = [{
        "session_key": session_key,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "domain": domain,
        "instruction": instruction,
        "response": response,
        "instruction_len": len(instruction),
        "response_len": len(response),
        "has_code": has_code_block(response),
        "has_tool_use": False,
        "has_cot": has_cot,
        "cot_text": cot_text if has_cot else None,
    }]
    return store_pairs(pairs) > 0


def extract_all_rich(min_size_kb: int = 50, limit: int = None) -> Dict[str, Any]:
    """Run all rich extractors: tool-use, COT, task arcs, and recovery.

    Returns summary statistics.
    """
    init_db()

    if not SESSIONS_DIR.exists():
        return {"error": f"Sessions directory not found: {SESSIONS_DIR}"}

    # Get already-processed sessions
    conn = sqlite3.connect(str(TRAINING_DB))
    processed = set(
        r[0] for r in conn.execute("SELECT DISTINCT session_key FROM extraction_log").fetchall()
    )
    conn.close()

    # Find transcript files
    transcripts = sorted(SESSIONS_DIR.glob("*.jsonl"), key=lambda p: p.stat().st_size, reverse=True)

    stats = {
        "sessions_processed": 0,
        "basic_pairs": 0,
        "tool_pairs": 0,
        "task_arcs": 0,
        "recovery_pairs": 0,
    }

    for path in transcripts:
        if limit and stats["sessions_processed"] >= limit:
            break

        session_key = path.stem

        # Skip already processed
        if session_key in processed:
            continue

        # Skip tiny sessions
        size_kb = path.stat().st_size / 1024
        if size_kb < min_size_kb:
            continue

        print(f"Processing {session_key} ({size_kb:.0f} KB)...")
        try:
            # Extract basic pairs
            basic = extract_from_transcript(str(path), session_key)
            stats["basic_pairs"] += basic

            # Extract tool sequences
            tool = extract_tool_pairs_from_transcript(str(path), session_key)
            stats["tool_pairs"] += tool

            # Extract task arcs
            arcs = extract_task_arcs_from_transcript(str(path), session_key)
            stats["task_arcs"] += arcs

            # Extract recovery pairs
            recovery = extract_recovery_pairs_from_transcript(str(path), session_key)
            stats["recovery_pairs"] += recovery

            stats["sessions_processed"] += 1

            # Log extraction
            conn = sqlite3.connect(str(TRAINING_DB))
            conn.execute(
                "INSERT INTO extraction_log (session_key, pairs_extracted, pairs_skipped) VALUES (?, ?, ?)",
                [session_key, basic + tool + recovery, 0]
            )
            conn.commit()
            conn.close()

            print(f"  → {basic} basic, {tool} tool, {arcs} arcs, {recovery} recovery")
        except Exception as e:
            print(f"  → ERROR: {e}")

    return stats


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Session Distiller — capture conversations as training data")
    parser.add_argument("--extract", action="store_true", help="Extract basic pairs from recent sessions")
    parser.add_argument("--extract-rich", action="store_true", help="Extract all rich features (COT, tool-use, task arcs, recovery)")
    parser.add_argument("--extract-cc", action="store_true", help="Extract from Claude Code session transcripts")
    parser.add_argument("--status", action="store_true", help="Show training data stats")
    parser.add_argument("--export", action="store_true", help="Export JSONL for fine-tuning")
    parser.add_argument("--gateway-log", type=str, help="Path to OpenClaw gateway database")
    args = parser.parse_args()

    init_db()

    if args.status:
        stats = get_stats()
        print(json.dumps(stats, indent=2))
    elif args.export:
        count = export_jsonl()
        print(f"Exported {count} training pairs to {OUTPUT_JSONL}")
    elif args.extract_cc:
        result = extract_claude_code_sessions(limit=50)  # Process up to 50 sessions at a time
        print(json.dumps(result, indent=2))
    elif args.extract_rich:
        result = extract_all_rich(limit=50)  # Process up to 50 sessions at a time
        print(json.dumps(result, indent=2))
    elif args.extract:
        result = extract_all_sessions(limit=50)  # Process up to 50 sessions at a time
        print(json.dumps(result, indent=2))
    else:
        parser.print_help()
