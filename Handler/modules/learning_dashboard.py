"""
Learning Dashboard — Tracks shadow model performance and identifies weak areas.
Queries intelligence.db to compute accuracy metrics by category.
Powers the UI dashboard showing model learning progress.
"""

import sqlite3
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional

DB_PATH = Path.home() / "jarvis" / "Database" / "v2" / "intelligence.db"

CATEGORIES = [
    "intent_routing",
    "tool_selection",
    "trading_analysis",
    "complex_reasoning",
    "creative_tasks",
    "code_generation",
    "user_interaction",
]

# Map handler_routed / intent_classified values to categories
INTENT_TO_CATEGORY = {
    # intent_routing: meta — did we pick the right handler?
    "trading": "trading_analysis",
    "trade": "trading_analysis",
    "market": "trading_analysis",
    "stock": "trading_analysis",
    "code": "code_generation",
    "debug": "code_generation",
    "program": "code_generation",
    "write": "creative_tasks",
    "brainstorm": "creative_tasks",
    "creative": "creative_tasks",
    "plan": "complex_reasoning",
    "analyze": "complex_reasoning",
    "reason": "complex_reasoning",
    "research": "complex_reasoning",
    "chat": "user_interaction",
    "help": "user_interaction",
    "question": "user_interaction",
}


def _get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH), timeout=10, isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=DELETE")
    return conn


def _classify_category(row: sqlite3.Row) -> str:
    """Classify a request_log row into a category."""
    intent = (row["intent_classified"] or "").lower()
    handler = (row["handler_routed"] or "").lower()
    tool_calls = row["tool_calls"] or ""

    # Check intent keywords
    for keyword, cat in INTENT_TO_CATEGORY.items():
        if keyword in intent or keyword in handler:
            return cat

    # Check tool_calls for tool_selection category
    if tool_calls and tool_calls != "null" and tool_calls != "[]":
        return "tool_selection"

    return "user_interaction"  # default


class LearningDashboard:
    """Tracks shadow model performance and identifies weak areas."""

    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path), timeout=10, isolation_level=None)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=DELETE")
        return conn

    def get_overall_accuracy(self, model_version: str) -> float:
        """Compute overall accuracy for a model version.
        
        Accuracy = successful outcomes / total resolved outcomes.
        """
        conn = self._conn()
        try:
            row = conn.execute("""
                SELECT
                    COUNT(*) as total,
                    SUM(CASE WHEN outcome IN ('success', 'implicit_success') THEN 1 ELSE 0 END) as good
                FROM request_log
                WHERE model_used = ?
                  AND outcome != 'pending'
            """, (model_version,)).fetchone()
            if not row or row["total"] == 0:
                return 0.0
            return round(row["good"] / row["total"] * 100, 2)
        finally:
            conn.close()

    def get_accuracy_by_category(self, model_version: str) -> dict[str, float]:
        """Compute accuracy broken down by category."""
        conn = self._conn()
        try:
            rows = conn.execute("""
                SELECT * FROM request_log
                WHERE model_used = ? AND outcome != 'pending'
            """, (model_version,)).fetchall()

            cat_stats: dict[str, dict] = {c: {"total": 0, "good": 0} for c in CATEGORIES}
            for row in rows:
                cat = _classify_category(row)
                if cat in cat_stats:
                    cat_stats[cat]["total"] += 1
                    if row["outcome"] in ("success", "implicit_success"):
                        cat_stats[cat]["good"] += 1

            return {
                cat: round(s["good"] / s["total"] * 100, 2) if s["total"] > 0 else 0.0
                for cat, s in cat_stats.items()
            }
        finally:
            conn.close()

    def get_weak_areas(self, model_version: str, threshold: float = 75.0) -> list[dict]:
        """Find categories below the accuracy threshold."""
        by_cat = self.get_accuracy_by_category(model_version)
        return [
            {"category": cat, "accuracy": acc, "gap": round(threshold - acc, 2)}
            for cat, acc in sorted(by_cat.items(), key=lambda x: x[1])
            if acc < threshold
        ]

    def get_training_data_stats(self) -> dict:
        """Stats on all training data in request_log."""
        conn = self._conn()
        try:
            total = conn.execute("SELECT COUNT(*) as c FROM request_log").fetchone()["c"]
            by_outcome = {}
            for row in conn.execute(
                "SELECT outcome, COUNT(*) as c FROM request_log GROUP BY outcome"
            ).fetchall():
                by_outcome[row["outcome"]] = row["c"]

            by_model = {}
            for row in conn.execute(
                "SELECT model_used, COUNT(*) as c FROM request_log GROUP BY model_used"
            ).fetchall():
                by_model[row["model_used"] or "unknown"] = row["c"]

            # By category (need to classify each row)
            all_rows = conn.execute("SELECT * FROM request_log").fetchall()
            by_category: dict[str, int] = {c: 0 for c in CATEGORIES}
            for row in all_rows:
                cat = _classify_category(row)
                if cat in by_category:
                    by_category[cat] += 1

            return {
                "total_examples": total,
                "by_outcome": by_outcome,
                "by_model": by_model,
                "by_category": by_category,
            }
        finally:
            conn.close()

    def get_improvement_trend(self, model_version: str, days: int = 30) -> list[dict]:
        """Daily accuracy scores over the past N days."""
        conn = self._conn()
        try:
            cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
            rows = conn.execute("""
                SELECT
                    DATE(timestamp) as day,
                    COUNT(*) as total,
                    SUM(CASE WHEN outcome IN ('success', 'implicit_success') THEN 1 ELSE 0 END) as good
                FROM request_log
                WHERE model_used = ?
                  AND outcome != 'pending'
                  AND timestamp >= ?
                GROUP BY DATE(timestamp)
                ORDER BY day
            """, (model_version, cutoff)).fetchall()

            return [
                {
                    "date": row["day"],
                    "accuracy": round(row["good"] / row["total"] * 100, 2) if row["total"] > 0 else 0.0,
                    "total_requests": row["total"],
                }
                for row in rows
            ]
        finally:
            conn.close()

    def get_comparison_report(self, model_a: str, model_b: str) -> dict:
        """Side-by-side comparison of two model versions."""
        acc_a = self.get_accuracy_by_category(model_a)
        acc_b = self.get_accuracy_by_category(model_b)
        overall_a = self.get_overall_accuracy(model_a)
        overall_b = self.get_overall_accuracy(model_b)

        comparison = {}
        for cat in CATEGORIES:
            a_val = acc_a.get(cat, 0.0)
            b_val = acc_b.get(cat, 0.0)
            comparison[cat] = {
                model_a: a_val,
                model_b: b_val,
                "delta": round(b_val - a_val, 2),
                "winner": model_b if b_val > a_val else model_a if a_val > b_val else "tie",
            }

        return {
            "overall": {
                model_a: overall_a,
                model_b: overall_b,
                "delta": round(overall_b - overall_a, 2),
            },
            "by_category": comparison,
        }

    def generate_dashboard_data(self) -> dict:
        """Complete JSON payload for the UI dashboard."""
        conn = self._conn()
        try:
            # Find all model versions
            models = [
                row["model_used"]
                for row in conn.execute(
                    "SELECT DISTINCT model_used FROM request_log WHERE model_used IS NOT NULL"
                ).fetchall()
            ]
        finally:
            conn.close()

        model_data = {}
        for model in models:
            model_data[model] = {
                "overall_accuracy": self.get_overall_accuracy(model),
                "by_category": self.get_accuracy_by_category(model),
                "weak_areas": self.get_weak_areas(model),
                "trend": self.get_improvement_trend(model, days=30),
            }

        return {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "categories": CATEGORIES,
            "training_stats": self.get_training_data_stats(),
            "models": model_data,
        }
