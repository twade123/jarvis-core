"""
Training Data Formatter — Converts logged interactions into fine-tuning format.
Outputs: ShareGPT format (for most models), Alpaca format (alternative)
Filters: only successful interactions and corrected interactions
"""

import sqlite3
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

DB_PATH = Path.home() / "jarvis" / "Database" / "v2" / "intelligence.db"


def _get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH), timeout=10, isolation_level=None)
    conn.row_factory = sqlite3.Row
    return conn


def _query_logs(since_date: str = None, outcome_filter: list[str] = None) -> list[dict]:
    """Fetch logs with optional filters."""
    conn = _get_conn()
    sql = "SELECT * FROM request_log WHERE request_text IS NOT NULL AND response_text IS NOT NULL"
    params = []

    if since_date:
        sql += " AND timestamp >= ?"
        params.append(since_date)

    if outcome_filter:
        placeholders = ",".join("?" * len(outcome_filter))
        sql += f" AND outcome IN ({placeholders})"
        params.extend(outcome_filter)

    sql += " ORDER BY timestamp ASC"
    rows = conn.execute(sql, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def export_sharegpt(since_date: str = None) -> list[dict]:
    """
    Export logs as ShareGPT format conversations.
    
    Format:
    {"conversations": [
        {"from": "human", "value": "..."},
        {"from": "gpt", "value": "..."}
    ]}
    """
    logs = _query_logs(since_date, ["success"])
    results = []

    for log in logs:
        conv = {
            "conversations": [
                {"from": "human", "value": log["request_text"]},
                {"from": "gpt", "value": log["response_text"]},
            ]
        }
        # Add system context if we have intent/handler info
        if log.get("intent_classified") or log.get("handler_routed"):
            system_msg = []
            if log.get("intent_classified"):
                system_msg.append(f"Intent: {log['intent_classified']}")
            if log.get("handler_routed"):
                system_msg.append(f"Handler: {log['handler_routed']}")
            if log.get("tool_calls"):
                system_msg.append(f"Tools available: {log['tool_calls']}")
            conv["conversations"].insert(0, {
                "from": "system",
                "value": ". ".join(system_msg),
            })
        results.append(conv)

    return results


def export_alpaca(since_date: str = None) -> list[dict]:
    """
    Export logs as Alpaca format.
    
    Format:
    {"instruction": "...", "input": "", "output": "..."}
    """
    logs = _query_logs(since_date, ["success"])
    results = []

    for log in logs:
        entry = {
            "instruction": log["request_text"],
            "input": "",
            "output": log["response_text"],
        }
        if log.get("intent_classified"):
            entry["input"] = f"[Intent: {log['intent_classified']}]"
        results.append(entry)

    return results


def filter_quality(min_confidence: float = 0.8, since_date: str = None) -> list[dict]:
    """
    Filter for high-quality training examples.
    
    Quality heuristics:
    - Explicit success > implicit success
    - Has tool_calls that succeeded = higher quality
    - Longer, substantive responses preferred
    - Low latency suggests simpler/cached = lower training value
    """
    logs = _query_logs(since_date, ["success"])
    scored = []

    for log in logs:
        score = 0.5  # base

        # Explicit success is worth more
        if log["outcome"] == "success":
            score += 0.3
        elif log["outcome"] == "implicit_success":
            score += 0.1

        # Tool calls that worked = valuable
        if log.get("tool_calls"):
            score += 0.15

        # Substantive response (not just "ok" or "done")
        resp_len = len(log.get("response_text", ""))
        if resp_len > 200:
            score += 0.1
        elif resp_len < 20:
            score -= 0.2

        # Substantive request
        req_len = len(log.get("request_text", ""))
        if req_len > 50:
            score += 0.05

        score = max(0.0, min(1.0, score))

        if score >= min_confidence:
            log["_quality_score"] = round(score, 3)
            scored.append(log)

    return sorted(scored, key=lambda x: x["_quality_score"], reverse=True)


def include_corrections(since_date: str = None) -> list[dict]:
    """
    Get failed interactions WITH their corrections.
    These are the highest-value training examples — they show what went wrong
    and what the user actually wanted.
    
    Returns ShareGPT format with the correction as a follow-up turn.
    """
    conn = _get_conn()
    sql = """
        SELECT * FROM request_log 
        WHERE outcome = 'failure' 
        AND correction_text IS NOT NULL
        AND request_text IS NOT NULL
        AND response_text IS NOT NULL
    """
    params = []
    if since_date:
        sql += " AND timestamp >= ?"
        params.append(since_date)

    sql += " ORDER BY timestamp ASC"
    rows = conn.execute(sql, params).fetchall()
    conn.close()

    results = []
    for row in rows:
        log = dict(row)
        conv = {
            "conversations": [
                {"from": "human", "value": log["request_text"]},
                {"from": "gpt", "value": log["response_text"]},
                {"from": "human", "value": log["correction_text"]},
                # The correction itself becomes training signal:
                # "Given this correction, the better response would have been..."
            ],
            "_meta": {
                "type": "correction",
                "original_outcome": "failure",
                "model": log.get("model_used"),
            },
        }
        results.append(conv)

    return results


def save_to_jsonl(data: list[dict], path: str):
    """Write training data to JSONL file ready for MLX fine-tuning."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w") as f:
        for entry in data:
            # Strip internal metadata
            clean = {k: v for k, v in entry.items() if not k.startswith("_")}
            f.write(json.dumps(clean, ensure_ascii=False) + "\n")
    print(f"[TrainingFormatter] Wrote {len(data)} examples to {p}")
    return len(data)


def export_all(since_date: str = None, output_dir: str = None) -> dict:
    """
    Export all formats at once. Convenience method.
    Returns paths to generated files.
    """
    if output_dir is None:
        output_dir = str(Path.home() / "jarvis" / "Training" / "data")
    
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out = Path(output_dir)

    sharegpt = export_sharegpt(since_date)
    alpaca = export_alpaca(since_date)
    corrections = include_corrections(since_date)
    quality = filter_quality(0.8, since_date)

    # Convert quality logs to ShareGPT for training
    quality_sharegpt = []
    for log in quality:
        quality_sharegpt.append({
            "conversations": [
                {"from": "human", "value": log["request_text"]},
                {"from": "gpt", "value": log["response_text"]},
            ]
        })

    paths = {}
    if sharegpt:
        p = str(out / f"sharegpt_{ts}.jsonl")
        save_to_jsonl(sharegpt, p)
        paths["sharegpt"] = p
    if alpaca:
        p = str(out / f"alpaca_{ts}.jsonl")
        save_to_jsonl(alpaca, p)
        paths["alpaca"] = p
    if corrections:
        p = str(out / f"corrections_{ts}.jsonl")
        save_to_jsonl(corrections, p)
        paths["corrections"] = p
    if quality_sharegpt:
        p = str(out / f"quality_{ts}.jsonl")
        save_to_jsonl(quality_sharegpt, p)
        paths["quality"] = p

    return paths
