"""
Tests for Learning Dashboard and Active Teacher.
Uses a temporary in-memory DB with mock data.
"""

import sqlite3
import tempfile
import os
from pathlib import Path
from datetime import datetime, timezone, timedelta

# --- Setup temp DB ---
_tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
TEST_DB = Path(_tmp.name)
_tmp.close()


def setup_db():
    """Create schema and insert mock data."""
    conn = sqlite3.connect(str(TEST_DB), isolation_level=None)
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
        CREATE TABLE IF NOT EXISTS teaching_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            category TEXT NOT NULL,
            difficulty TEXT,
            query TEXT NOT NULL,
            expert_response TEXT,
            shadow_response TEXT,
            expert_model TEXT,
            shadow_model TEXT,
            quality_gap REAL,
            notes TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        );
    """)

    now = datetime.now(timezone.utc)
    mock_data = [
        # Trading — 50% accuracy (weak)
        (now.isoformat(), "user1", "analyze AAPL setup", "trading", "trading_handler", "local", "buy it", None, "success", 100, 50, 100, 0.0, None),
        (now.isoformat(), "user1", "what's the market regime?", "trading", "trading_handler", "local", "bullish", None, "failure", 120, 60, 80, 0.0, None),
        (now.isoformat(), "user1", "risk assessment for my portfolio", "trade", "trading_handler", "local", "looks fine", None, "failure", 90, 40, 60, 0.0, None),
        (now.isoformat(), "user1", "SPY analysis", "market", "trading_handler", "local", "going up", None, "success", 110, 55, 90, 0.0, None),
        # Code — 100% accuracy (strong)
        (now.isoformat(), "user1", "write a python function", "code", "code_handler", "local", "def foo(): pass", None, "success", 200, 100, 500, 0.0, None),
        (now.isoformat(), "user1", "debug this script", "debug", "code_handler", "local", "found the bug", None, "success", 150, 80, 300, 0.0, None),
        # User interaction — 66% accuracy (borderline)
        (now.isoformat(), "user1", "hello how are you", "chat", "chat_handler", "local", "I'm good!", None, "success", 50, 20, 30, 0.0, None),
        (now.isoformat(), "user1", "can you help me?", "help", "chat_handler", "local", "sure", None, "success", 60, 25, 40, 0.0, None),
        (now.isoformat(), "user1", "that's not what I meant", "chat", "chat_handler", "local", "sorry", None, "failure", 70, 30, 50, 0.0, None),
        # Complex reasoning — 0% (very weak)
        (now.isoformat(), "user1", "plan a migration strategy", "plan", "planning_handler", "local", "just do it", None, "failure", 300, 200, 800, 0.0, None),
        (now.isoformat(), "user1", "analyze the tradeoffs", "analyze", "planning_handler", "local", "there are some", None, "failure", 250, 180, 700, 0.0, None),
        # Tool selection — with tool calls
        (now.isoformat(), "user1", "what time is it", "question", "general", "local", "3pm", '[{"tool": "clock"}]', "success", 40, 15, 20, 0.0, None),
        # Also add some "anthropic" model entries for comparison
        (now.isoformat(), "user1", "analyze AAPL setup", "trading", "trading_handler", "anthropic", "detailed analysis here", None, "success", 500, 100, 800, 0.01, None),
        (now.isoformat(), "user1", "plan a migration", "plan", "planning_handler", "anthropic", "step by step plan", None, "success", 600, 200, 1000, 0.02, None),
        # Add data across multiple days for trend
        ((now - timedelta(days=1)).isoformat(), "user1", "trading q", "trading", "trading_handler", "local", "resp", None, "success", 100, 50, 100, 0.0, None),
        ((now - timedelta(days=2)).isoformat(), "user1", "trading q2", "trading", "trading_handler", "local", "resp", None, "failure", 100, 50, 100, 0.0, None),
    ]

    conn.executemany("""
        INSERT INTO request_log
        (timestamp, user_id, request_text, intent_classified, handler_routed,
         model_used, response_text, tool_calls, outcome, latency_ms,
         tokens_in, tokens_out, cost_estimate, trade_id)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, mock_data)
    conn.commit()
    conn.close()


def test_dashboard():
    from .learning_dashboard import LearningDashboard

    db = LearningDashboard(db_path=TEST_DB)

    # Overall accuracy
    acc = db.get_overall_accuracy("local")
    print(f"Overall accuracy (local): {acc}%")
    assert 0 < acc < 100, f"Expected partial accuracy, got {acc}"

    # By category
    by_cat = db.get_accuracy_by_category("local")
    print(f"By category: {by_cat}")
    assert by_cat["code_generation"] == 100.0, f"Code should be 100%, got {by_cat['code_generation']}"
    assert by_cat["complex_reasoning"] == 0.0, f"Reasoning should be 0%, got {by_cat['complex_reasoning']}"

    # Weak areas
    weak = db.get_weak_areas("local", threshold=75.0)
    print(f"Weak areas: {weak}")
    weak_cats = [w["category"] for w in weak]
    assert "complex_reasoning" in weak_cats
    assert "trading_analysis" in weak_cats
    assert "code_generation" not in weak_cats

    # Training data stats
    stats = db.get_training_data_stats()
    print(f"Training stats: total={stats['total_examples']}")
    assert stats["total_examples"] == 16

    # Trend
    trend = db.get_improvement_trend("local", days=7)
    print(f"Trend ({len(trend)} days): {trend}")
    assert len(trend) >= 1

    # Comparison
    comp = db.get_comparison_report("local", "anthropic")
    print(f"Comparison overall: local={comp['overall']['local']}% anthropic={comp['overall']['anthropic']}%")
    assert comp["overall"]["anthropic"] == 100.0

    # Full dashboard
    dashboard = db.generate_dashboard_data()
    print(f"Dashboard keys: {list(dashboard.keys())}")
    assert "models" in dashboard
    assert "local" in dashboard["models"]

    print("\n✅ All dashboard tests passed!")


def test_active_teacher():
    from .learning_dashboard import LearningDashboard
    from .active_teacher import ActiveTeacher, TeachingCurriculum

    db = LearningDashboard(db_path=TEST_DB)
    teacher = ActiveTeacher(dashboard=db, llm_router=None)
    teacher.db_path = TEST_DB  # point to test DB

    # Identify weak areas
    weak = teacher.identify_weak_areas("local", threshold=75.0)
    print(f"\nWeak areas: {[w['category'] for w in weak]}")
    assert len(weak) > 0

    # Generate curriculum
    curricula = teacher.generate_curriculum(weak)
    print(f"Generated {len(curricula)} curricula:")
    for c in curricula:
        print(f"  {c.category}: {c.difficulty}, {len(c.queries)} queries, priority={c.priority}")
    assert len(curricula) > 0
    # Highest priority should be the weakest area
    assert curricula[0].priority >= curricula[-1].priority

    # Schedule teaching
    plan = teacher.schedule_teaching("local", max_queries=10, threshold=75.0)
    print(f"\nTeaching plan: {plan['total_queries']} queries, est ${plan['estimated_cost_usd']}")
    assert plan["total_queries"] <= 10

    # Teaching report (starts empty)
    report = teacher.get_teaching_report()
    print(f"Teaching report: {report['total_sessions']} sessions")

    print("\n✅ All active teacher tests passed!")


def run_all():
    setup_db()
    try:
        test_dashboard()
        test_active_teacher()
        print("\n🎉 All learning system tests passed!")
    finally:
        os.unlink(TEST_DB)


if __name__ == "__main__":
    # Allow running as: python -m Handler.modules.test_learning_system
    run_all()
