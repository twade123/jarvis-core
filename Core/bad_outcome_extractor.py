"""
bad_outcome_extractor.py
------------------------
Scans session_training.db for conversations where user corrections appear,
extracts 4-turn correction sequences as negative training pairs, and writes:
  - Appends to: training_data/sessions/session_training.jsonl
  - Creates:    training_data/sessions/negative_outcomes.jsonl

Output schema:
  {
    "domain": "correction",
    "source": "negative_outcome",
    "conversation": [...],
    "negative_example": true,
    "correction_type": "..."
  }

Usage:
    python3 bad_outcome_extractor.py
"""

import json
import sqlite3
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
DB_PATH = Path("~/Jarvis/training_data/sessions/session_training.db")
JSONL_PATH = Path("~/Jarvis/training_data/sessions/session_training.jsonl")
NEG_JSONL_PATH = Path("~/Jarvis/training_data/sessions/negative_outcomes.jsonl")

# ---------------------------------------------------------------------------
# Correction markers (case-insensitive)
# ---------------------------------------------------------------------------
CORRECTION_MARKERS = [
    "that didn't work",
    "that didnt work",
    "wrong",
    "actually",
    "no that's",
    "no thats",
    "fix it again",
    "still broken",
    "you missed",
    "incorrect",
    "try again",
    "that's not right",
    "thats not right",
    "not right",
    "still not",
    "you got it wrong",
    "that's wrong",
    "thats wrong",
]

MARKER_PATTERN = re.compile(
    "|".join(re.escape(m) for m in CORRECTION_MARKERS),
    re.IGNORECASE,
)


def _classify_correction(text: str) -> str:
    """Return a rough correction_type label based on the text."""
    t = text.lower()
    if any(k in t for k in ("code", "python", "function", "error", "syntax", "import")):
        return "code_error"
    if any(k in t for k in ("trade", "validator", "guardian", "snipe", "confluence", "ema")):
        return "trading_logic"
    if any(k in t for k in ("config", "setting", "file", "path", "server", "restart")):
        return "config_error"
    if any(k in t for k in ("output", "format", "schema", "json", "response")):
        return "output_format"
    return "general_correction"


# ---------------------------------------------------------------------------
# Extract from training_pairs  (instruction / response flat pairs)
# ---------------------------------------------------------------------------

def _extract_from_pairs(conn: sqlite3.Connection) -> List[Dict[str, Any]]:
    """
    Look for pairs where the instruction contains a correction marker.
    We reconstruct a 4-turn window by grabbing the rows before/after
    that share the same session_key, ordered by id.
    """
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        """
        SELECT id, session_key, domain, instruction, response
        FROM training_pairs
        ORDER BY session_key, id
        """
    ).fetchall()

    # Group by session_key, preserve row order
    sessions: Dict[str, List[sqlite3.Row]] = {}
    for r in rows:
        sessions.setdefault(r["session_key"] or "__none__", []).append(r)

    results: List[Dict[str, Any]] = []

    for key, session_rows in sessions.items():
        for idx, row in enumerate(session_rows):
            instr = row["instruction"] or ""
            resp  = row["response"] or ""

            # Check if this instruction IS a correction
            m = MARKER_PATTERN.search(instr)
            if not m:
                continue

            # Build 4-turn window: 1 turn before correction + correction turn + 2 turns after
            start = max(0, idx - 1)
            end   = min(len(session_rows), idx + 3)
            window = session_rows[start:end]

            conversation = []
            for w in window:
                conversation.append({"role": "user",      "content": (w["instruction"] or "")})
                conversation.append({"role": "assistant", "content": (w["response"] or "")})

            # Mark the correction turn
            correction_text = instr
            correction_type = _classify_correction(correction_text + resp)

            results.append({
                "domain": "correction",
                "source": "negative_outcome",
                "session_key": key,
                "original_domain": row["domain"] or "unknown",
                "conversation": conversation,
                "negative_example": True,
                "correction_type": correction_type,
                "correction_marker": m.group(0).lower(),
                "extracted_at": datetime.utcnow().isoformat(),
            })

    return results


# ---------------------------------------------------------------------------
# Extract from task_arcs  (multi-turn JSON blobs)
# ---------------------------------------------------------------------------

def _extract_from_arcs(conn: sqlite3.Connection) -> List[Dict[str, Any]]:
    """
    task_arcs stores full multi-turn conversations in messages_json.
    Find turns where a user message contains a correction marker,
    then slice out the 4-turn window around it.
    """
    conn.row_factory = sqlite3.Row
    arcs = conn.execute(
        "SELECT id, session_key, domain, messages_json FROM task_arcs"
    ).fetchall()

    results: List[Dict[str, Any]] = []

    for arc in arcs:
        try:
            messages = json.loads(arc["messages_json"] or "[]")
        except (json.JSONDecodeError, TypeError):
            continue

        if not isinstance(messages, list):
            continue

        for i, msg in enumerate(messages):
            if msg.get("role") != "user":
                continue
            content = msg.get("content", "")
            if not isinstance(content, str):
                # Some messages have list content (tool results)
                if isinstance(content, list):
                    content = " ".join(
                        p.get("text", "") for p in content if isinstance(p, dict)
                    )
                else:
                    content = str(content)

            m = MARKER_PATTERN.search(content)
            if not m:
                continue

            # 4-turn window (message-level, each msg = 1 item)
            start = max(0, i - 1)
            end   = min(len(messages), i + 4)
            window = messages[start:end]

            conversation = []
            for w in window:
                c = w.get("content", "")
                if isinstance(c, list):
                    c = " ".join(p.get("text", "") for p in c if isinstance(p, dict))
                conversation.append({
                    "role": w.get("role", "unknown"),
                    "content": str(c)[:2000],  # cap length for training
                })

            correction_type = _classify_correction(content)

            results.append({
                "domain": "correction",
                "source": "negative_outcome",
                "session_key": arc["session_key"] or "__none__",
                "original_domain": arc["domain"] or "unknown",
                "conversation": conversation,
                "negative_example": True,
                "correction_type": correction_type,
                "correction_marker": m.group(0).lower(),
                "extracted_at": datetime.utcnow().isoformat(),
            })

    return results


# ---------------------------------------------------------------------------
# Deduplication  (by session_key + first correction marker position)
# ---------------------------------------------------------------------------

def _dedup(items: List[Dict]) -> List[Dict]:
    seen = set()
    out  = []
    for item in items:
        key = (
            item["session_key"],
            item["correction_marker"],
            item["conversation"][0]["content"][:80] if item["conversation"] else "",
        )
        if key not in seen:
            seen.add(key)
            out.append(item)
    return out


# ---------------------------------------------------------------------------
# Load already-written negative outcomes to avoid duplicates
# ---------------------------------------------------------------------------

def _load_existing_neg(path: Path) -> set:
    keys = set()
    if not path.exists():
        return keys
    with open(path) as f:
        for line in f:
            try:
                obj = json.loads(line)
                conv = obj.get("conversation", [])
                first = conv[0]["content"][:80] if conv else ""
                keys.add((obj.get("session_key", ""), obj.get("correction_marker", ""), first))
            except Exception:
                pass
    return keys


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    if not DB_PATH.exists():
        print(f"ERROR: DB not found at {DB_PATH}")
        return

    conn = sqlite3.connect(str(DB_PATH))

    print("Scanning training_pairs …")
    pair_results = _extract_from_pairs(conn)
    print(f"  Found {len(pair_results)} correction hits in training_pairs")

    print("Scanning task_arcs …")
    arc_results = _extract_from_arcs(conn)
    print(f"  Found {len(arc_results)} correction hits in task_arcs")

    conn.close()

    all_results = _dedup(pair_results + arc_results)
    print(f"\nTotal unique correction sequences: {len(all_results)}")

    # --- Load existing to skip duplicates ---
    existing = _load_existing_neg(NEG_JSONL_PATH)
    new_results = []
    for item in all_results:
        conv = item.get("conversation", [])
        first = conv[0]["content"][:80] if conv else ""
        k = (item["session_key"], item["correction_marker"], first)
        if k not in existing:
            new_results.append(item)

    print(f"New (not yet written): {len(new_results)}")

    if not new_results:
        print("\nNothing new to write.")
        _print_report(all_results)
        return

    # --- Write negative_outcomes.jsonl ---
    NEG_JSONL_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(NEG_JSONL_PATH, "a") as f:
        for item in new_results:
            f.write(json.dumps(item) + "\n")
    print(f"\nWrote {len(new_results)} records → {NEG_JSONL_PATH}")

    # --- Append to session_training.jsonl ---
    with open(JSONL_PATH, "a") as f:
        for item in new_results:
            f.write(json.dumps(item) + "\n")
    print(f"Appended {len(new_results)} records → {JSONL_PATH}")

    _print_report(all_results)


def _print_report(all_results: List[Dict]) -> None:
    from collections import Counter
    print("\n══════════════════════════════════════")
    print("  BAD OUTCOME EXTRACTION REPORT")
    print("══════════════════════════════════════")
    print(f"  Total correction sequences : {len(all_results)}")

    type_counts = Counter(r["correction_type"] for r in all_results)
    print("\n  By correction_type:")
    for ct, count in type_counts.most_common():
        print(f"    {ct:30s} {count}")

    marker_counts = Counter(r["correction_marker"] for r in all_results)
    print("\n  Top correction markers:")
    for mk, count in marker_counts.most_common(10):
        print(f"    '{mk}'{' ' * max(1, 35 - len(mk))}{count}")

    domain_counts = Counter(r["original_domain"] for r in all_results)
    print("\n  By original domain:")
    for d, count in domain_counts.most_common():
        print(f"    {d:30s} {count}")

    print("══════════════════════════════════════\n")


if __name__ == "__main__":
    main()
