"""
Task Status Registry for tracking the status of long-running tasks.

This module provides a centralized registry for tracking task status and progress.
It allows the Orchestrator to maintain a persistent connection to long-running tasks
and enables status queries through the terminal interface.
"""

import time
import json
import logging
import threading
from typing import Dict, List, Any, Optional
from enum import Enum, auto
from collections import deque

class TaskStatus(Enum):
    """Enumeration of possible task statuses."""
    PENDING = auto()
    STARTED = auto()
    ANALYZING = auto()
    PROCESSING = auto()
    WAITING_FOR_INPUT = auto()
    COMPLETING = auto()
    COMPLETED = auto()
    FAILED = auto()
    CANCELLED = auto()

class TaskStatusRegistry:
    """
    A registry for tracking the status of long-running tasks.

    This class maintains an in-memory registry of all active and recently completed
    tasks, along with their current status and progress information.
    Optionally bridges to workspace_task_history for persistence across restarts.
    """

    def __init__(self, max_history: int = 100):
        """
        Initialize the task status registry.

        Args:
            max_history: Maximum number of completed tasks to keep in history
        """
        self._active_tasks: Dict[str, Dict[str, Any]] = {}
        self._completed_tasks: deque = deque(maxlen=max_history)
        self._lock = threading.RLock()
        self._listeners: Dict[str, List[callable]] = {}
        self._request_response_metrics: Dict[str, List[Dict[str, Any]]] = {}
        self._db_available = False
        self._workspace_sharing = None
        self._init_db_bridge()
        self._load_incomplete_tasks()
        logging.info("TaskStatusRegistry initialized")

    def _init_db_bridge(self):
        """Try to connect to workspace DB for persistence. Non-fatal if unavailable."""
        try:
            from Jarvis_Agent_SDK.import_helper import get_workspace_sharing
            ws = get_workspace_sharing()
            if ws and hasattr(ws, '_get_db_connection'):
                self._workspace_sharing = ws
                self._db_available = True
        except Exception:
            pass

    def _load_incomplete_tasks(self):
        """Restore active tasks from DB on startup."""
        if not self._db_available:
            return
        try:
            conn = self._workspace_sharing._get_db_connection()
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id, workspace_id, title, description, status, priority, "
                "assigned_agent_id, created_at, updated_at, metadata "
                "FROM workspace_tasks WHERE status NOT IN ('completed', 'failed', 'cancelled')"
            )
            for row in cursor.fetchall():
                task_id = str(row[0])
                if task_id not in self._active_tasks:
                    status_map = {
                        'pending': TaskStatus.PENDING,
                        'in_progress': TaskStatus.PROCESSING,
                        'blocked': TaskStatus.WAITING_FOR_INPUT,
                    }
                    self._active_tasks[task_id] = {
                        "task_id": task_id,
                        "description": row[3] or row[2],
                        "session_id": None,
                        "status": status_map.get(row[4], TaskStatus.PENDING),
                        "status_message": f"Restored from DB (status={row[4]})",
                        "progress": 50 if row[4] == 'in_progress' else 0,
                        "created_at": row[7] if isinstance(row[7], (int, float)) else time.time(),
                        "updated_at": row[8] if isinstance(row[8], (int, float)) else time.time(),
                        "updates": [],
                        "metadata": json.loads(row[9]) if row[9] else {},
                        "tracking_points": [],
                        "status_updates": [],
                        "request_response_pairs": [],
                        "_db_task_id": row[0],
                        "_workspace_id": row[1],
                    }
            logging.info(f"TaskStatusRegistry restored {len(self._active_tasks)} incomplete tasks from DB")
        except Exception as e:
            logging.debug(f"TaskStatusRegistry DB restore skipped: {e}")

    def _persist_update(self, task_id: str, status: 'TaskStatus', message: str):
        """Write status update to workspace_task_history. Non-fatal on failure."""
        if not self._db_available:
            return
        try:
            conn = self._workspace_sharing._get_db_connection()
            cursor = conn.cursor()
            # Map TaskStatus enum to DB status string
            status_str = status.name.lower()
            cursor.execute(
                "INSERT INTO workspace_task_history (task_id, action, new_status, performed_by, details) "
                "VALUES (?, ?, ?, ?, ?)",
                (int(task_id) if task_id.isdigit() else 0, "status_update", status_str,
                 "TaskStatusRegistry", message)
            )
            conn.commit()
        except Exception as e:
            logging.debug(f"TaskStatusRegistry persist skipped: {e}")
    
    def register_task(self, task_id: str, description: str, session_id: Optional[str] = None,
                     metadata: Optional[Dict[str, Any]] = None) -> str:
        """
        Register a new task in the registry.
        
        Args:
            task_id: Unique ID for the task
            description: Human-readable description of the task
            session_id: Optional session ID associated with the task
            metadata: Optional additional metadata for the task
            
        Returns:
            The task ID
        """
        with self._lock:
            timestamp = time.time()
            task_data = {
                "task_id": task_id,
                "description": description,
                "session_id": session_id,
                "status": TaskStatus.PENDING,
                "status_message": "Task registered",
                "progress": 0,  # 0-100
                "created_at": timestamp,
                "updated_at": timestamp,
                "updates": [],
                "metadata": metadata or {},
                "tracking_points": [],
                "status_updates": [],
                "request_response_pairs": []
            }
            
            self._active_tasks[task_id] = task_data
            logging.info(f"Task registered: {task_id} - {description}")
            
            # Add initial status update
            self.update_status(
                task_id=task_id,
                status=TaskStatus.PENDING,
                message="Task registered and pending execution",
                progress=0
            )
            
            return task_id
    
    def update_status(self, task_id: str, status: TaskStatus, message: str,
                     progress: Optional[int] = None,
                     metadata: Optional[Dict[str, Any]] = None) -> bool:
        """
        Update the status of an existing task.
        
        Args:
            task_id: ID of the task to update
            status: New status
            message: Message explaining the status update
            progress: Optional progress percentage (0-100)
            metadata: Optional additional metadata for the update
            
        Returns:
            True if the update was successful, False otherwise
        """
        with self._lock:
            if task_id not in self._active_tasks:
                logging.warning(f"Cannot update status for unknown task: {task_id}")
                return False
            
            task = self._active_tasks[task_id]
            timestamp = time.time()
            
            # Create update record
            update = {
                "timestamp": timestamp,
                "status": status,
                "previous_status": task["status"],
                "message": message,
                "progress": progress if progress is not None else task["progress"]
            }
            
            if metadata:
                update["metadata"] = metadata
            
            # Update task data
            task["status"] = status
            task["status_message"] = message
            task["updated_at"] = timestamp
            if progress is not None:
                task["progress"] = progress
            if metadata:
                task["metadata"].update(metadata)
            
            # Add to update history
            task["updates"].append(update)
            
            # If task is complete or failed, move to completed list
            if status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]:
                task["completed_at"] = timestamp
                self._completed_tasks.append(task.copy())  # Make a copy for history
                # Keep in active tasks for a short period before cleanup
                
            logging.info(f"Task {task_id} updated: {status.name} - {message}")
            self._notify_listeners(task_id, task)

            # Persist to DB (non-blocking, non-fatal)
            self._persist_update(task_id, status, message)

            return True
    
    def mark_task_completed(self, task_id: str, success: bool = True, 
                         message: str = None, result: Any = None) -> bool:
        """
        Mark a task as completed or failed.
        
        Args:
            task_id: ID of the task to mark as completed
            success: Whether the task completed successfully
            message: Optional completion message
            result: Optional result data from the task
            
        Returns:
            True if the update was successful, False otherwise
        """
        if not message:
            message = "Task completed successfully" if success else "Task failed"
            
        status = TaskStatus.COMPLETED if success else TaskStatus.FAILED
        
        metadata = {}
        if result is not None:
            metadata["result"] = result
            
        return self.update_status(
            task_id=task_id,
            status=status,
            message=message,
            progress=100 if success else None,
            metadata=metadata
        )
    
    def add_tracking_point(self, task_id: str, stage: str, description: str = None, 
                        extra_data: Dict[str, Any] = None) -> bool:
        """
        Add a tracking point to a task.
        
        Args:
            task_id: ID of the task to update
            stage: The stage of execution
            description: Optional description of the tracking point
            extra_data: Optional additional data
            
        Returns:
            True if the update was successful, False otherwise
        """
        with self._lock:
            if task_id not in self._active_tasks:
                logging.warning(f"Cannot add tracking point for unknown task: {task_id}")
                return False
            
            task = self._active_tasks[task_id]
            timestamp = time.time()
            
            # Create tracking point
            tracking_point = {
                "stage": stage,
                "timestamp": timestamp,
                "elapsed": timestamp - task["created_at"]
            }
            
            if description:
                tracking_point["description"] = description
            if extra_data:
                tracking_point["data"] = extra_data
                
            # Add to tracking points
            task["tracking_points"].append(tracking_point)
            task["updated_at"] = timestamp
            
            return True
    
    def add_status_update(self, task_id: str, status: str, message: str, 
                        percentage: Optional[int] = None) -> bool:
        """
        Add a detailed status update to a task.
        
        Args:
            task_id: ID of the task to update
            status: Status keyword
            message: Status message
            percentage: Optional completion percentage
            
        Returns:
            True if the update was successful, False otherwise
        """
        with self._lock:
            if task_id not in self._active_tasks:
                logging.warning(f"Cannot add status update for unknown task: {task_id}")
                return False
            
            task = self._active_tasks[task_id]
            timestamp = time.time()
            
            # Create status update
            status_update = {
                "status": status,
                "message": message,
                "timestamp": timestamp,
                "elapsed": timestamp - task["created_at"]
            }
            
            if percentage is not None:
                status_update["percentage"] = percentage
                # Also update the main task progress
                task["progress"] = percentage
                
            # Add to status updates
            task["status_updates"].append(status_update)
            task["updated_at"] = timestamp
            
            # Also update the main task status message
            task["status_message"] = message
            
            return True
    
    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        Get the current status of a task.
        
        Args:
            task_id: ID of the task to get status for
            
        Returns:
            Dictionary with task status information, or None if task not found
        """
        with self._lock:
            if task_id in self._active_tasks:
                return self._active_tasks[task_id].copy()
            
            # Search in completed tasks
            for task in self._completed_tasks:
                if task["task_id"] == task_id:
                    return task.copy()
            
            return None
    
    def get_active_tasks(self, session_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get all active tasks, optionally filtered by session ID.
        
        Args:
            session_id: Optional session ID to filter by
            
        Returns:
            List of task dictionaries
        """
        with self._lock:
            if session_id:
                return [
                    task.copy() for task in self._active_tasks.values()
                    if task["session_id"] == session_id
                ]
            else:
                return [task.copy() for task in self._active_tasks.values()]
    
    def get_recent_tasks(self, limit: int = 10, session_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get recently completed tasks, optionally filtered by session ID.
        
        Args:
            limit: Maximum number of tasks to return
            session_id: Optional session ID to filter by
            
        Returns:
            List of task dictionaries
        """
        with self._lock:
            if session_id:
                filtered = [
                    task for task in self._completed_tasks
                    if task["session_id"] == session_id
                ]
            else:
                filtered = list(self._completed_tasks)
            
            return [task.copy() for task in filtered[-limit:]]
    
    def cancel_task(self, task_id: str, reason: str = "Task cancelled by user") -> bool:
        """
        Cancel an active task.
        
        Args:
            task_id: ID of the task to cancel
            reason: Reason for cancellation
            
        Returns:
            True if the task was cancelled, False otherwise
        """
        return self.update_status(
            task_id=task_id,
            status=TaskStatus.CANCELLED,
            message=reason,
            progress=None
        )
    
    def cleanup_old_tasks(self, max_age_seconds: int = 3600) -> int:
        """
        Remove completed tasks that are older than the specified age.
        
        Args:
            max_age_seconds: Maximum age in seconds for tasks to keep
            
        Returns:
            Number of tasks removed
        """
        with self._lock:
            now = time.time()
            to_remove = []
            
            # Find completed tasks in active tasks that are old enough to remove
            for task_id, task in self._active_tasks.items():
                if task["status"] in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]:
                    if "completed_at" in task and now - task["completed_at"] > max_age_seconds:
                        to_remove.append(task_id)
            
            # Remove tasks
            for task_id in to_remove:
                del self._active_tasks[task_id]
                
            return len(to_remove)
    
    def register_listener(self, task_id: str, callback: callable) -> bool:
        """
        Register a callback function to be called when a task's status is updated.
        
        Args:
            task_id: ID of the task to listen for updates
            callback: Function to call with task data when updated
            
        Returns:
            True if the listener was registered, False otherwise
        """
        with self._lock:
            if task_id not in self._listeners:
                self._listeners[task_id] = []
            
            self._listeners[task_id].append(callback)
            return True
    
    def unregister_listener(self, task_id: str, callback: callable) -> bool:
        """
        Unregister a previously registered callback function.
        
        Args:
            task_id: ID of the task
            callback: Function to unregister
            
        Returns:
            True if the listener was unregistered, False otherwise
        """
        with self._lock:
            if task_id not in self._listeners:
                return False
            
            try:
                self._listeners[task_id].remove(callback)
                if not self._listeners[task_id]:
                    del self._listeners[task_id]
                return True
            except ValueError:
                return False
    
    def _notify_listeners(self, task_id: str, task_data: Dict[str, Any]) -> None:
        """
        Notify all listeners for a task of a status update.
        
        Args:
            task_id: ID of the task
            task_data: Current task data
        """
        if task_id in self._listeners:
            for callback in self._listeners[task_id]:
                try:
                    callback(task_data.copy())
                except Exception as e:
                    logging.error(f"Error in task status listener callback: {e}")
    
    def get_task_summary(self, task_id: str) -> str:
        """
        Get a summary of a task's status as a human-readable string.
        
        Args:
            task_id: ID of the task
            
        Returns:
            Status summary string
        """
        task = self.get_task_status(task_id)
        if not task:
            return f"Task {task_id} not found"
        
        # Create a summary
        status_str = task["status"].name if isinstance(task["status"], TaskStatus) else str(task["status"])
        progress_str = f"{task['progress']}%" if task.get("progress") is not None else "N/A"
        
        # Add timing information
        created = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(task["created_at"]))
        
        if task["status"] in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]:
            if "completed_at" in task:
                completed = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(task["completed_at"]))
                duration = task["completed_at"] - task["created_at"]
                timing = f"Started: {created}, Completed: {completed}, Duration: {duration:.2f}s"
            else:
                timing = f"Started: {created}"
        else:
            duration = time.time() - task["created_at"]
            timing = f"Started: {created}, Running for: {duration:.2f}s"
        
        # Build summary string
        summary = [
            f"Task: {task['description']}",
            f"ID: {task['task_id']}",
            f"Status: {status_str}",
            f"Progress: {progress_str}",
            f"Message: {task['status_message']}",
            timing
        ]
        
        # Add session ID if present
        if task.get("session_id"):
            summary.append(f"Session: {task['session_id']}")
        
        return "\n".join(summary)
    
    def get_task_progress_visualization(self, task_id: str) -> str:
        """
        Generate a visual representation of task progress.
        
        Args:
            task_id: ID of the task
            
        Returns:
            ASCII progress visualization
        """
        task = self.get_task_status(task_id)
        if not task:
            return f"Task {task_id} not found"
        
        # Get progress percentage
        progress = task.get("progress", 0)
        if progress is None:
            progress = 0
        
        # Create progress bar
        bar_width = 50
        filled_width = int(bar_width * progress / 100)
        bar = f"[{'#' * filled_width}{'-' * (bar_width - filled_width)}]"
        
        # Get status updates for timeline
        updates = task.get("status_updates", [])
        if not updates:
            return f"{bar} {progress}%"
        
        # Create timeline
        timeline = []
        for update in updates:
            timestamp = time.strftime("%H:%M:%S", time.localtime(update["timestamp"]))
            percentage = update.get("percentage", "")
            if percentage:
                percentage = f" ({percentage}%)"
            timeline.append(f"{timestamp} - {update['status']}{percentage}: {update['message']}")
        
        # Limit timeline length
        if len(timeline) > 10:
            timeline = timeline[-10:]
            timeline.insert(0, "... (earlier updates omitted)")
        
        # Combine progress bar and timeline
        return f"{bar} {progress}%\n\nTimeline:\n" + "\n".join(timeline)
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the registry to a dictionary for serialization.
        
        Returns:
            Dictionary representation of the registry
        """
        with self._lock:
            return {
                "active_tasks": {k: self._task_dict_to_serializable(v) for k, v in self._active_tasks.items()},
                "completed_tasks": [self._task_dict_to_serializable(t) for t in self._completed_tasks],
                "timestamp": time.time()
            }
    
    def _task_dict_to_serializable(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Convert a task dictionary to a JSON-serializable format."""
        serialized = {}
        for k, v in task.items():
            if isinstance(v, TaskStatus):
                serialized[k] = v.name
            elif isinstance(v, (dict, list, str, int, float, bool, type(None))):
                serialized[k] = v
            else:
                serialized[k] = str(v)
        return serialized
    
    def track_request_response_pair(self, task_id: str, request_data: Dict[str, Any], 
                                  response_data: Dict[str, Any], 
                                  effectiveness_metrics: Optional[Dict[str, Any]] = None) -> bool:
        """
        Track a request/response pair for effectiveness measurement.
        
        Args:
            task_id: ID of the task associated with this request/response pair
            request_data: Data about the request (query, parameters, etc.)
            response_data: Data about the response (result, timing, etc.)
            effectiveness_metrics: Optional metrics about effectiveness
                This can include:
                - execution_time: Time taken to process the request
                - quality_score: Estimated quality of the response
                - tokens_used: Number of tokens used in processing
                - user_feedback: User feedback about the response
                - system_used: Which system generated the response
            
        Returns:
            True if tracking was successful, False otherwise
        """
        with self._lock:
            if task_id not in self._active_tasks and not any(t.get("task_id") == task_id for t in self._completed_tasks):
                logging.warning(f"Cannot track request/response for unknown task: {task_id}")
                return False
            
            timestamp = time.time()
            
            # Create request/response record
            record = {
                "task_id": task_id,
                "timestamp": timestamp,
                "request": request_data,
                "response": response_data,
                "metrics": effectiveness_metrics or {}
            }
            
            # Add task type classification if available
            if "detected_task_type" in effectiveness_metrics or (
                "metadata" in self._active_tasks.get(task_id, {}) and 
                "detected_task_type" in self._active_tasks[task_id]["metadata"]
            ):
                task_type = (effectiveness_metrics and effectiveness_metrics.get("detected_task_type")) or (
                    self._active_tasks.get(task_id, {}).get("metadata", {}).get("detected_task_type")
                )
                if task_type:
                    if task_type not in self._request_response_metrics:
                        self._request_response_metrics[task_type] = []
                    
                    self._request_response_metrics[task_type].append(record)
            
            # Always add to "all" category
            if "all" not in self._request_response_metrics:
                self._request_response_metrics["all"] = []
            self._request_response_metrics["all"].append(record)
            
            # Also update the task's metadata
            task = self._active_tasks.get(task_id)
            if task:
                if "request_response_pairs" not in task["metadata"]:
                    task["metadata"]["request_response_pairs"] = []
                
                task["metadata"]["request_response_pairs"].append({
                    "timestamp": timestamp,
                    "request": request_data,
                    "response": response_data,
                    "metrics": effectiveness_metrics or {}
                })
            
            logging.info(f"Tracked request/response pair for task {task_id}")
            return True
    
    def get_effectiveness_metrics(self, task_type: Optional[str] = None, 
                                time_period: Optional[int] = None) -> Dict[str, Any]:
        """
        Get effectiveness metrics for request/response pairs.
        
        Args:
            task_type: Optional task type to filter by
            time_period: Optional time period in seconds to limit to
            
        Returns:
            Dictionary with effectiveness metrics
        """
        with self._lock:
            # Determine which records to analyze
            if task_type and task_type in self._request_response_metrics:
                records = self._request_response_metrics[task_type]
            else:
                records = self._request_response_metrics.get("all", [])
                
            # Filter by time period if specified
            if time_period:
                now = time.time()
                records = [r for r in records if now - r["timestamp"] <= time_period]
                
            if not records:
                return {
                    "count": 0,
                    "message": "No records found for the specified criteria"
                }
                
            # Calculate basic metrics
            count = len(records)
            
            # Extract execution times
            execution_times = [
                r["metrics"].get("execution_time") 
                for r in records 
                if r["metrics"] and "execution_time" in r["metrics"]
            ]
            execution_times = [t for t in execution_times if t is not None]
            
            # Extract quality scores
            quality_scores = [
                r["metrics"].get("quality_score") 
                for r in records 
                if r["metrics"] and "quality_score" in r["metrics"]
            ]
            quality_scores = [s for s in quality_scores if s is not None]
            
            # Count by system used
            systems_used = {}
            for record in records:
                if record["metrics"] and "system_used" in record["metrics"]:
                    system = record["metrics"]["system_used"]
                    systems_used[system] = systems_used.get(system, 0) + 1
            
            # Calculate averages and distributions
            avg_execution_time = sum(execution_times) / len(execution_times) if execution_times else None
            avg_quality_score = sum(quality_scores) / len(quality_scores) if quality_scores else None
            
            # Return metrics
            return {
                "count": count,
                "systems_used": systems_used,
                "avg_execution_time": avg_execution_time,
                "avg_quality_score": avg_quality_score,
                "time_period": time_period,
                "task_type": task_type or "all"
            }
    
    def get_task_effectiveness(self, task_id: str) -> Dict[str, Any]:
        """
        Get effectiveness metrics for a specific task.
        
        Args:
            task_id: ID of the task
            
        Returns:
            Dictionary with effectiveness metrics for the task
        """
        task = self.get_task_status(task_id)
        if not task:
            return {"error": f"Task {task_id} not found"}
        
        # Extract request/response pairs
        pairs = task.get("metadata", {}).get("request_response_pairs", [])
        if not pairs:
            return {
                "task_id": task_id,
                "message": "No request/response pairs recorded for this task"
            }
        
        # Calculate metrics
        execution_times = [
            p["metrics"].get("execution_time") 
            for p in pairs 
            if p["metrics"] and "execution_time" in p["metrics"]
        ]
        execution_times = [t for t in execution_times if t is not None]
        
        quality_scores = [
            p["metrics"].get("quality_score") 
            for p in pairs 
            if p["metrics"] and "quality_score" in p["metrics"]
        ]
        quality_scores = [s for s in quality_scores if s is not None]
        
        return {
            "task_id": task_id,
            "description": task["description"],
            "status": task["status"].name if isinstance(task["status"], TaskStatus) else str(task["status"]),
            "request_response_count": len(pairs),
            "avg_execution_time": sum(execution_times) / len(execution_times) if execution_times else None,
            "avg_quality_score": sum(quality_scores) / len(quality_scores) if quality_scores else None,
            "created_at": task["created_at"],
            "completed_at": task.get("completed_at")
        }
    
    def generate_effectiveness_report(self, time_period: Optional[int] = None) -> str:
        """
        Generate a human-readable report on system effectiveness.
        
        Args:
            time_period: Optional time period in seconds to limit to
            
        Returns:
            String with human-readable report
        """
        # Get overall metrics
        metrics = self.get_effectiveness_metrics(time_period=time_period)
        
        # Get metrics by task type
        task_type_metrics = {}
        for task_type in self._request_response_metrics.keys():
            if task_type != "all":
                task_type_metrics[task_type] = self.get_effectiveness_metrics(
                    task_type=task_type, 
                    time_period=time_period
                )
        
        # Format time period for display
        if time_period:
            if time_period < 3600:
                time_str = f"{time_period // 60} minutes"
            elif time_period < 86400:
                time_str = f"{time_period // 3600} hours"
            else:
                time_str = f"{time_period // 86400} days"
        else:
            time_str = "all time"
        
        # Build report
        report = [
            f"System Effectiveness Report ({time_str})",
            f"----------------------------------------",
            f"Total requests: {metrics['count']}",
        ]
        
        if metrics["avg_execution_time"] is not None:
            report.append(f"Average execution time: {metrics['avg_execution_time']:.2f}s")
        if metrics["avg_quality_score"] is not None:
            report.append(f"Average quality score: {metrics['avg_quality_score']:.2f}")
        
        # Add systems used
        if metrics["systems_used"]:
            report.append("\nSystems Used:")
            for system, count in sorted(metrics["systems_used"].items(), key=lambda x: x[1], reverse=True):
                percentage = 100 * count / metrics["count"]
                report.append(f"  {system}: {count} ({percentage:.1f}%)")
        
        # Add metrics by task type
        if task_type_metrics:
            report.append("\nMetrics by Task Type:")
            for task_type, type_metrics in sorted(task_type_metrics.items(), key=lambda x: x[1]["count"], reverse=True):
                if type_metrics["count"] == 0:
                    continue
                report.append(f"\n  {task_type}:")
                report.append(f"    Requests: {type_metrics['count']}")
                if type_metrics["avg_execution_time"] is not None:
                    report.append(f"    Average execution time: {type_metrics['avg_execution_time']:.2f}s")
                if type_metrics["avg_quality_score"] is not None:
                    report.append(f"    Average quality score: {type_metrics['avg_quality_score']:.2f}")
        
        return "\n".join(report)

# Create a global instance of the registry
_GLOBAL_REGISTRY = None

def get_task_registry() -> TaskStatusRegistry:
    """
    Get the global task status registry instance.
    
    Returns:
        The global TaskStatusRegistry instance
    """
    global _GLOBAL_REGISTRY
    if _GLOBAL_REGISTRY is None:
        _GLOBAL_REGISTRY = TaskStatusRegistry()
    return _GLOBAL_REGISTRY 