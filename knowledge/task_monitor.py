#!/usr/bin/env python3
"""
Task Monitor — Boardroom oversight of child workspaces.

Periodically checks workspace tasks for:
- Stale tasks (no progress in N hours)
- Failed tasks (error state)
- Completed tasks (need boardroom review)
- Blocked tasks (dependency issues)

Designed to be called from OpenClaw cron or heartbeat.
Reports back to the boardroom for escalation.

Usage:
    from knowledge.task_monitor import TaskMonitor
    monitor = TaskMonitor()
    
    # Check all active workspace tasks
    report = monitor.check_all()
    # Returns: {"stale": [...], "failed": [...], "completed": [...], "blocked": [...]}
    
    # Record task outcome for learning
    monitor.record_outcome(task_id=123, outcome="success", 
                           learnings="RSI divergence detection works better with 21-period")
"""

import os
import json
import sqlite3
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional

logger = logging.getLogger("TaskMonitor")

# boardroom.db has workspace_tasks table
BOARDROOM_DB = os.path.expanduser("~/jarvis/Database/boardroom.db")

# Thresholds
STALE_HOURS = 4        # No update in 4 hours = stale
OVERDUE_HOURS = 24     # Past deadline by 24h = escalate


class TaskMonitor:
    """Monitor workspace tasks and escalate issues to boardroom."""

    def __init__(self, db_path: str = None):
        self.db_path = db_path or BOARDROOM_DB
        self._workspace_sharing = None
        try:
            from Jarvis_Agent_SDK.import_helper import get_workspace_sharing
            self._workspace_sharing = get_workspace_sharing()
        except Exception:
            pass

    def _get_conn(self) -> sqlite3.Connection:
        if self._workspace_sharing and hasattr(self._workspace_sharing, '_get_db_connection'):
            try:
                conn = self._workspace_sharing._get_db_connection()
                conn.row_factory = sqlite3.Row
                return conn
            except Exception:
                pass
        conn = sqlite3.connect(self.db_path, isolation_level=None)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=DELETE")
        return conn
    
    def check_all(self) -> Dict[str, List[Dict]]:
        """
        Check all active workspace tasks and categorize issues.
        
        Returns dict with keys: stale, failed, completed_unreviewed, 
        overdue, active_healthy, summary.
        """
        conn = self._get_conn()
        now = datetime.utcnow()
        stale_cutoff = (now - timedelta(hours=STALE_HOURS)).isoformat()
        
        report = {
            "stale": [],
            "failed": [],
            "completed_unreviewed": [],
            "overdue": [],
            "active_healthy": 0,
            "total_active": 0,
        }
        
        # Get all non-archived tasks
        try:
            tasks = conn.execute("""
                SELECT id, workspace_id, title, description, status, priority,
                       assigned_agent_id, created_at, updated_at, due_date,
                       assigned_user_id, completed_at
                FROM workspace_tasks 
                WHERE status NOT IN ('archived', 'cancelled')
                ORDER BY priority DESC, created_at ASC
            """).fetchall()
        except sqlite3.OperationalError as e:
            logger.warning(f"Could not query workspace_tasks: {e}")
            conn.close()
            return report
        
        for task in tasks:
            task_dict = dict(task)
            status = task_dict.get("status", "")
            updated = task_dict.get("updated_at", "")
            
            if status in ("completed", "done"):
                # Check if reviewed by boardroom
                report["completed_unreviewed"].append(task_dict)
            elif status in ("failed", "error"):
                report["failed"].append(task_dict)
            elif status in ("in_progress", "pending", "assigned"):
                report["total_active"] += 1
                
                # Check staleness
                if updated and updated < stale_cutoff:
                    task_dict["stale_hours"] = round(
                        (now - datetime.fromisoformat(updated.replace("Z", ""))).total_seconds() / 3600, 1
                    )
                    report["stale"].append(task_dict)
                else:
                    report["active_healthy"] += 1
                
                # Check overdue
                due = task_dict.get("due_date")
                if due and due < now.isoformat():
                    overdue_hours = (now - datetime.fromisoformat(due.replace("Z", ""))).total_seconds() / 3600
                    if overdue_hours >= OVERDUE_HOURS:
                        task_dict["overdue_hours"] = round(overdue_hours, 1)
                        report["overdue"].append(task_dict)
        
        conn.close()
        
        # Summary
        report["summary"] = (
            f"Active: {report['total_active']} ({report['active_healthy']} healthy), "
            f"Stale: {len(report['stale'])}, Failed: {len(report['failed'])}, "
            f"Completed (unreviewed): {len(report['completed_unreviewed'])}, "
            f"Overdue: {len(report['overdue'])}"
        )
        
        if report["stale"] or report["failed"] or report["overdue"]:
            logger.warning(f"Task issues found: {report['summary']}")
        else:
            logger.info(f"Task monitor: all clear — {report['summary']}")
        
        return report
    
    def record_outcome(self, task_id: int, outcome: str, 
                        learnings: str = None, quality_score: float = None) -> bool:
        """
        Record task outcome and optionally write learnings to vault.
        
        Args:
            task_id: workspace_tasks.id
            outcome: "success" | "partial" | "failed"
            learnings: What was learned from this task
            quality_score: 0-1 quality rating
        """
        conn = self._get_conn()
        
        try:
            # Update task status
            conn.execute("""
                UPDATE workspace_tasks SET status=?, updated_at=datetime('now')
                WHERE id=?
            """, ("completed" if outcome == "success" else "failed", task_id))
            
            # Get task details for vault writing
            task = conn.execute(
                "SELECT * FROM workspace_tasks WHERE id=?", (task_id,)
            ).fetchone()
            
            conn.commit()
            conn.close()
            
            # Write learnings to vault if provided
            if learnings and task:
                try:
                    from knowledge.vault_writer import VaultWriter
                    vault = VaultWriter()
                    agent_name = task["assigned_agent_id"] or "unknown"
                    vault.record_agent_learning(agent_name, {
                        "type": "discovery" if outcome == "success" else "failure",
                        "summary": f"Task outcome ({outcome}): {task['title'][:60]}",
                        "context": f"**Task:** {task['title']}\n\n{learnings}",
                        "evidence": f"Quality: {quality_score:.0%}" if quality_score else None,
                        "tags": ["task_outcome", outcome],
                    })
                except Exception as e:
                    logger.warning(f"Could not write task learnings to vault: {e}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to record outcome for task {task_id}: {e}")
            conn.close()
            return False
    
    def get_agent_workload(self) -> Dict[str, Dict]:
        """Get current task count and status breakdown per agent."""
        conn = self._get_conn()
        try:
            rows = conn.execute("""
                SELECT assigned_agent_id, status, COUNT(*) as cnt
                FROM workspace_tasks 
                WHERE status NOT IN ('archived', 'cancelled') AND assigned_agent_id IS NOT NULL
                GROUP BY assigned_agent_id, status
            """).fetchall()
        except sqlite3.OperationalError:
            conn.close()
            return {}
        
        conn.close()
        
        workload = {}
        for row in rows:
            agent = row["assigned_agent_id"]
            if agent not in workload:
                workload[agent] = {"total": 0}
            workload[agent][row["status"]] = row["cnt"]
            workload[agent]["total"] += row["cnt"]
        
        return workload
    
    def needs_escalation(self) -> List[Dict]:
        """
        Quick check: anything that needs boardroom attention RIGHT NOW?
        Returns list of issues, empty if all clear.
        """
        report = self.check_all()
        escalations = []
        
        for task in report["failed"]:
            escalations.append({
                "severity": "high",
                "type": "task_failed",
                "task_id": task["id"],
                "title": task.get("title", "Unknown"),
                "agent": task.get("assigned_agent_id"),
                "message": f"Task failed: {task.get('title', 'Unknown')}",
            })
        
        for task in report["stale"]:
            if task.get("stale_hours", 0) > 8:  # only escalate very stale
                escalations.append({
                    "severity": "medium",
                    "type": "task_stale",
                    "task_id": task["id"],
                    "title": task.get("title", "Unknown"),
                    "agent": task.get("assigned_agent_id"),
                    "message": f"Task stale ({task['stale_hours']}h): {task.get('title', 'Unknown')}",
                })
        
        for task in report["overdue"]:
            escalations.append({
                "severity": "high",
                "type": "task_overdue",
                "task_id": task["id"],
                "title": task.get("title", "Unknown"),
                "agent": task.get("assigned_agent_id"),
                "message": f"Task overdue ({task['overdue_hours']}h): {task.get('title', 'Unknown')}",
            })
        
        return escalations
