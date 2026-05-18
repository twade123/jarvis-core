#!/usr/bin/env python3
"""
Graduation System — Self-regulating Opus dependency.

Tracks per-category match rate between local models and Opus QC.
As categories graduate (90%+ match sustained for 2 weeks), Opus QC 
becomes spot-check only, then consultant-only.

Three phases:
  Phase A (Training):   Opus QCs EVERYTHING — mandatory during ramp-up
  Phase B (Selective):  Categories at 90%+ get spot-checked (10% sample)
  Phase C (Consultant): Category fully graduated — Opus only on explicit request

The cost curve is self-regulating:
  - Worse local performance → more Opus calls → more training data → better performance
  - Better performance → fewer Opus calls → lower cost → sustain

Usage:
    from knowledge.graduation import GraduationTracker
    tracker = GraduationTracker()
    
    # After Opus reviews local output
    tracker.record_comparison(
        category="boardroom_deliberation",
        agent="CTO",
        local_output="...",
        opus_output="...",
        match_score=0.85  # 0-1, how well local matched Opus quality
    )
    
    # Before calling Opus — should we?
    phase = tracker.get_phase("boardroom_deliberation")
    # Returns "A", "B", or "C"
    should_qc = tracker.should_opus_qc("boardroom_deliberation")
    # True/False based on phase + sampling
"""

import json
import os
import random
import sqlite3
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger("Graduation")

# Default DB in the knowledge vault
DEFAULT_DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_index.db")

# Graduation thresholds
PHASE_B_THRESHOLD = 0.90    # 90% match rate to enter Phase B
PHASE_C_THRESHOLD = 0.95    # 95% match rate to enter Phase C
SUSTAIN_WINDOW_DAYS = 14    # Must sustain for 2 weeks
SPOT_CHECK_RATE = 0.10      # 10% spot-check in Phase B
MIN_SAMPLES = 20            # Minimum comparisons before graduation eligible
REGRESSION_THRESHOLD = 0.85 # Drop below this → demote back to Phase A


class GraduationTracker:
    """Track local model quality vs Opus and manage graduation phases."""
    
    def __init__(self, db_path: str = None):
        self.db_path = db_path or DEFAULT_DB
        self._ensure_tables()
    
    def _ensure_tables(self):
        conn = sqlite3.connect(self.db_path, isolation_level=None)
        conn.execute("PRAGMA journal_mode=DELETE")
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS opus_comparisons (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL DEFAULT (datetime('now')),
                category TEXT NOT NULL,
                agent TEXT,
                match_score REAL NOT NULL,
                local_output_hash TEXT,
                notes TEXT
            );
            
            CREATE TABLE IF NOT EXISTS graduation_status (
                category TEXT PRIMARY KEY,
                phase TEXT NOT NULL DEFAULT 'A',
                current_match_rate REAL DEFAULT 0.0,
                samples INTEGER DEFAULT 0,
                phase_b_since TEXT,
                phase_c_since TEXT,
                last_regression TEXT,
                last_spot_check TEXT,
                updated_at TEXT NOT NULL DEFAULT (datetime('now'))
            );
            
            CREATE INDEX IF NOT EXISTS idx_comparisons_category 
                ON opus_comparisons(category, timestamp);
        """)
        conn.commit()
        conn.close()
    
    def record_comparison(self, category: str, match_score: float,
                           agent: str = None, notes: str = None) -> Dict:
        """
        Record a local-vs-Opus comparison result.
        
        Args:
            category: Task category (e.g., "boardroom_deliberation", "trade_validation")
            match_score: 0.0-1.0, how well local output matched Opus quality
            agent: Which agent produced the local output
            notes: Optional context
            
        Returns:
            Updated graduation status for this category.
        """
        conn = sqlite3.connect(self.db_path, isolation_level=None)
        conn.execute(
            "INSERT INTO opus_comparisons (category, agent, match_score, notes) VALUES (?,?,?,?)",
            (category, agent, max(0.0, min(1.0, match_score)), notes)
        )
        conn.commit()
        conn.close()
        
        # Recalculate and update phase
        return self._update_phase(category)
    
    def _update_phase(self, category: str) -> Dict:
        """Recalculate match rate and update graduation phase."""
        conn = sqlite3.connect(self.db_path, isolation_level=None)
        conn.row_factory = sqlite3.Row
        now = datetime.utcnow().isoformat()
        
        # Get recent match rate (last 14 days)
        window_start = (datetime.utcnow() - timedelta(days=SUSTAIN_WINDOW_DAYS)).isoformat()
        row = conn.execute("""
            SELECT AVG(match_score) as avg_score, COUNT(*) as cnt
            FROM opus_comparisons 
            WHERE category=? AND timestamp >= ?
        """, (category, window_start)).fetchone()
        
        avg_score = row["avg_score"] or 0.0
        sample_count = row["cnt"] or 0
        
        # Get total samples ever
        total = conn.execute(
            "SELECT COUNT(*) FROM opus_comparisons WHERE category=?", (category,)
        ).fetchone()[0]
        
        # Get current status
        status = conn.execute(
            "SELECT * FROM graduation_status WHERE category=?", (category,)
        ).fetchone()
        
        current_phase = status["phase"] if status else "A"
        new_phase = current_phase
        
        # Phase transition logic
        if sample_count >= MIN_SAMPLES:
            if avg_score >= PHASE_C_THRESHOLD and current_phase == "B":
                # Check if sustained
                if status and status["phase_b_since"]:
                    b_since = datetime.fromisoformat(status["phase_b_since"])
                    if (datetime.utcnow() - b_since).days >= SUSTAIN_WINDOW_DAYS:
                        new_phase = "C"
                        logger.info(f"🎓 Category '{category}' GRADUATED to Phase C! "
                                   f"({avg_score:.1%} match rate, {total} total samples)")
            
            elif avg_score >= PHASE_B_THRESHOLD and current_phase == "A":
                new_phase = "B"
                logger.info(f"📈 Category '{category}' promoted to Phase B "
                           f"({avg_score:.1%} match rate, {total} total samples)")
            
            elif avg_score < REGRESSION_THRESHOLD and current_phase in ("B", "C"):
                new_phase = "A"
                logger.warning(f"📉 Category '{category}' REGRESSED to Phase A "
                              f"({avg_score:.1%} match rate)")
        
        # Upsert status
        conn.execute("""
            INSERT INTO graduation_status (category, phase, current_match_rate, samples, updated_at,
                phase_b_since, phase_c_since, last_regression)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(category) DO UPDATE SET
                phase=excluded.phase,
                current_match_rate=excluded.current_match_rate,
                samples=excluded.samples,
                updated_at=excluded.updated_at,
                phase_b_since=CASE 
                    WHEN excluded.phase='B' AND graduation_status.phase='A' THEN excluded.updated_at
                    WHEN excluded.phase='A' THEN NULL
                    ELSE graduation_status.phase_b_since END,
                phase_c_since=CASE 
                    WHEN excluded.phase='C' AND graduation_status.phase='B' THEN excluded.updated_at
                    WHEN excluded.phase IN ('A','B') THEN NULL
                    ELSE graduation_status.phase_c_since END,
                last_regression=CASE
                    WHEN excluded.phase='A' AND graduation_status.phase IN ('B','C') THEN excluded.updated_at
                    ELSE graduation_status.last_regression END
        """, (category, new_phase, avg_score, total, now, 
              now if new_phase == "B" and current_phase == "A" else None,
              now if new_phase == "C" and current_phase == "B" else None,
              now if new_phase == "A" and current_phase in ("B", "C") else None))
        
        conn.commit()
        conn.close()
        
        return {
            "category": category,
            "phase": new_phase,
            "match_rate": round(avg_score, 3),
            "samples_14d": sample_count,
            "samples_total": total,
            "transitioned": new_phase != current_phase,
        }
    
    def get_phase(self, category: str) -> str:
        """Get current graduation phase for a category."""
        conn = sqlite3.connect(self.db_path, isolation_level=None)
        row = conn.execute(
            "SELECT phase FROM graduation_status WHERE category=?", (category,)
        ).fetchone()
        conn.close()
        return row[0] if row else "A"
    
    def should_opus_qc(self, category: str) -> bool:
        """
        Should we send this task to Opus for QC?
        
        Phase A: Always yes
        Phase B: 10% random spot-check
        Phase C: Never (unless explicitly requested)
        """
        phase = self.get_phase(category)
        
        if phase == "A":
            return True
        elif phase == "B":
            should = random.random() < SPOT_CHECK_RATE
            if should:
                # Record spot check timestamp
                conn = sqlite3.connect(self.db_path, isolation_level=None)
                conn.execute(
                    "UPDATE graduation_status SET last_spot_check=datetime('now') WHERE category=?",
                    (category,)
                )
                conn.commit()
                conn.close()
            return should
        else:  # Phase C
            return False
    
    def get_all_status(self) -> List[Dict]:
        """Get graduation status for all tracked categories."""
        conn = sqlite3.connect(self.db_path, isolation_level=None)
        conn.row_factory = sqlite3.Row
        rows = conn.execute("""
            SELECT category, phase, current_match_rate, samples, 
                   phase_b_since, phase_c_since, last_regression, updated_at
            FROM graduation_status ORDER BY phase, current_match_rate DESC
        """).fetchall()
        conn.close()
        
        return [dict(r) for r in rows]
    
    def get_cost_estimate(self) -> Dict:
        """
        Estimate current vs peak Opus cost based on graduation status.
        Shows how much money the self-improving pipeline is saving.
        """
        statuses = self.get_all_status()
        if not statuses:
            return {"phase_a": 0, "phase_b": 0, "phase_c": 0, 
                    "opus_calls_pct": 100, "estimated_savings_pct": 0}
        
        phase_counts = {"A": 0, "B": 0, "C": 0}
        total_samples = 0
        for s in statuses:
            phase_counts[s["phase"]] = phase_counts.get(s["phase"], 0) + 1
            total_samples += s["samples"]
        
        total_cats = len(statuses)
        # Phase A = 100% Opus, Phase B = 10% Opus, Phase C = 0% Opus
        opus_pct = (
            (phase_counts["A"] * 1.0 + phase_counts["B"] * SPOT_CHECK_RATE + phase_counts["C"] * 0.0) 
            / total_cats * 100
        ) if total_cats > 0 else 100
        
        return {
            "categories": total_cats,
            "phase_a": phase_counts["A"],
            "phase_b": phase_counts["B"],
            "phase_c": phase_counts["C"],
            "total_comparisons": total_samples,
            "opus_calls_pct": round(opus_pct, 1),
            "estimated_savings_pct": round(100 - opus_pct, 1),
        }
    
    def get_category_report(self, category: str) -> Dict:
        """Detailed report for a single category — trend, agents, recent scores."""
        conn = sqlite3.connect(self.db_path, isolation_level=None)
        conn.row_factory = sqlite3.Row
        
        # Status
        status = conn.execute(
            "SELECT * FROM graduation_status WHERE category=?", (category,)
        ).fetchone()
        
        # Recent comparisons
        recent = conn.execute("""
            SELECT timestamp, agent, match_score, notes 
            FROM opus_comparisons WHERE category=? 
            ORDER BY timestamp DESC LIMIT 20
        """, (category,)).fetchall()
        
        # Per-agent breakdown
        agents = conn.execute("""
            SELECT agent, AVG(match_score) as avg, COUNT(*) as cnt
            FROM opus_comparisons WHERE category=? AND agent IS NOT NULL
            GROUP BY agent ORDER BY avg DESC
        """, (category,)).fetchall()
        
        # Weekly trend
        trend = conn.execute("""
            SELECT strftime('%Y-W%W', timestamp) as week, 
                   AVG(match_score) as avg, COUNT(*) as cnt
            FROM opus_comparisons WHERE category=?
            GROUP BY week ORDER BY week DESC LIMIT 8
        """, (category,)).fetchall()
        
        conn.close()
        
        return {
            "status": dict(status) if status else None,
            "recent": [dict(r) for r in recent],
            "agents": [dict(a) for a in agents],
            "trend": [dict(t) for t in trend],
        }
