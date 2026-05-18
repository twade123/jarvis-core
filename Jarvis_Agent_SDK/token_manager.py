"""
Token and Resource Management System for Jarvis

This module provides centralized tracking and management of API usage, tokens,
and costs across all integrated services. It focuses on monitoring and reporting
rather than decision making, providing data to the Jarvis orchestrator.
"""

import tiktoken
import logging
import json
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple, Union
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
import asyncio
from concurrent.futures import ThreadPoolExecutor
import sys
import os
import openai
from .boardroom_connector import (
    get_boardroom,
    track_request_journey,
    update_journey_state,
    complete_journey,
    track_journey_step
)
from .common_utils import generate_request_id

# Add parent directory to path for direct execution
if __name__ == "__main__":
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from Jarvis_Agent_SDK.import_helper import get_unified_database
    from Core.config import load_api_key
else:
    # Normal module imports
    from .import_helper import get_unified_database

# Global instance holder
_resource_manager_instance = None

def get_or_create_resource_manager(workspace_id: Optional[str] = None):
    """
    Get or create a singleton ResourceManager instance.
    
    Args:
        workspace_id: Optional workspace ID for context
    
    Returns:
        ResourceManager: The singleton instance
    """
    global _resource_manager_instance
    
    if _resource_manager_instance is not None:
        return _resource_manager_instance
        
    try:
        _resource_manager_instance = ResourceManager(workspace_id=workspace_id)
        return _resource_manager_instance
    except Exception as e:
        logging.error(f"Error creating ResourceManager: {str(e)}")
        return None

@dataclass
class BatchConfig:
    """Configuration for batch processing"""
    max_batch_size: int = 50  # Maximum requests in a batch
    max_wait_time: float = 0.5  # Maximum seconds to wait for batch completion
    min_batch_size: int = 5  # Minimum requests to trigger a batch
    dynamic_sizing: bool = True  # Adjust batch size based on performance

@dataclass
class ResourceConfig:
    """Configuration for different resource types (AI models, APIs, etc.)"""
    name: str
    type: str  # 'llm', 'api', 'compute', etc.
    metrics: Dict[str, Any]  # Configurable metrics (tokens, calls, compute units, etc.)
    cost_config: Dict[str, float]  # Cost per unit configurations
    limits: Dict[str, int]  # Rate limits, quotas, etc.
    features: Dict[str, Any]  # Special features or capabilities
    workspace_id: Optional[str] = None  # Associated workspace ID
    batch_config: Optional[BatchConfig] = None  # Batch processing configuration
    fallback_models: List[str] = None  # Ordered list of fallback models
    performance_metrics: Dict[str, float] = None  # Historical performance data

class ResourceManager:
    """Manages resource usage, tracking, and reporting across all integrated services"""
    
    def __init__(self, workspace_id: Optional[str] = None):
        """
        Initialize the resource manager
        
        Args:
            workspace_id: Optional workspace ID for context
        """
        self.workspace_id = workspace_id
        self.configs: Dict[str, ResourceConfig] = {}
        self.usage_cache = {}
        self.executor = ThreadPoolExecutor(max_workers=4)
        self.batch_queues: Dict[str, List[Dict]] = {}
        self.batch_events: Dict[str, asyncio.Event] = {}
        
        # Get unified database instance
        self.db = get_unified_database()
        if not self.db:
            raise RuntimeError("Failed to initialize unified database")
            
        # Get BoardRoom instance for tracking
        self.boardroom = get_boardroom()
        
        # Initialize database tables
        self._initialize_db()
        self._load_cached_configs()
        
        # Start batch processing tasks
        self._start_batch_processors()
        
    def _initialize_db(self):
        """Initialize the database tables for persistent tracking"""
        # Use transaction for table creation
        with self.db.transaction():
            self.db.execute_query("""
                CREATE TABLE IF NOT EXISTS usage_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    resource_name TEXT,
                    resource_type TEXT,
                    metric_type TEXT,
                    metric_value REAL,
                    cost REAL,
                    metadata TEXT,
                    workspace_id TEXT
                )
            """)
            
            self.db.execute_query("""
                CREATE TABLE IF NOT EXISTS resource_configs (
                    resource_name TEXT PRIMARY KEY,
                    config_data TEXT,
                    last_updated DATETIME DEFAULT CURRENT_TIMESTAMP,
                    workspace_id TEXT
                )
            """)
            
            # Create indexes for better query performance
            self.db.execute_query("CREATE INDEX IF NOT EXISTS idx_resource_name ON usage_logs(resource_name)")
            self.db.execute_query("CREATE INDEX IF NOT EXISTS idx_timestamp ON usage_logs(timestamp)")
            self.db.execute_query("CREATE INDEX IF NOT EXISTS idx_workspace ON usage_logs(workspace_id)")
    
    def _load_cached_configs(self):
        """Load cached resource configurations from database"""
        try:
            # Build query with workspace context
            query = "SELECT resource_name, config_data FROM resource_configs"
            params = []
            
            if self.workspace_id:
                query += " WHERE workspace_id = ? OR workspace_id IS NULL"
                params.append(self.workspace_id)
                
            cursor = self.db.execute_query(query, tuple(params))
            for row in cursor.fetchall():
                config_data = json.loads(row[1])
                self.configs[row[0]] = ResourceConfig(**config_data)
        except Exception as e:
            logging.error(f"Error loading cached configs: {e}")

    def _start_batch_processors(self):
        """Start background tasks for batch processing"""
        for resource_name, config in self.configs.items():
            if config.batch_config:
                self.batch_queues[resource_name] = []
                self.batch_events[resource_name] = asyncio.Event()
                asyncio.create_task(self._batch_processor(resource_name))

    async def _batch_processor(self, resource_name: str):
        """Background task to process batched requests"""
        config = self.configs[resource_name]
        batch_config = config.batch_config
        
        while True:
            try:
                # Wait for either enough requests or timeout
                batch_queue = self.batch_queues[resource_name]
                batch_event = self.batch_events[resource_name]
                
                if len(batch_queue) < batch_config.min_batch_size:
                    try:
                        await asyncio.wait_for(batch_event.wait(), batch_config.max_wait_time)
                    except asyncio.TimeoutError:
                        pass
                
                if not batch_queue:
                    continue
                
                # Process current batch
                current_batch = batch_queue[:batch_config.max_batch_size]
                self.batch_queues[resource_name] = batch_queue[batch_config.max_batch_size:]
                
                # Clear event if queue is empty
                if not self.batch_queues[resource_name]:
                    batch_event.clear()
                
                # Process batch and measure performance
                start_time = time.time()
                results = await self._process_batch(resource_name, current_batch)
                processing_time = time.time() - start_time
                
                # Update performance metrics
                await self._update_performance_metrics(
                    resource_name,
                    processing_time,
                    len(current_batch),
                    results
                )
                
                # Adjust batch size if dynamic sizing is enabled
                if batch_config.dynamic_sizing:
                    self._adjust_batch_size(resource_name, processing_time, len(current_batch))
                
            except Exception as e:
                logging.error(f"Error in batch processor for {resource_name}: {e}")
                await asyncio.sleep(1)  # Prevent tight error loops

    async def _process_batch(self, resource_name: str, batch: List[Dict]) -> List[Dict]:
        """Process a batch of requests"""
        try:
            # Combine requests efficiently based on model type
            config = self.configs[resource_name]
            
            if config.type == "llm":
                # Special handling for language models
                combined_prompt = self._combine_llm_requests(batch)
                response = await self._send_to_model(resource_name, combined_prompt)
                return self._split_llm_response(response, batch)
            else:
                # Generic batch processing
                results = []
                for request in batch:
                    result = await self._process_single_request(resource_name, request)
                    results.append(result)
                return results
                
        except Exception as e:
            logging.error(f"Batch processing error for {resource_name}: {e}")
            # Try fallback models if available
            return await self._try_fallback_models(resource_name, batch)

    async def submit_request(
        self,
        resource_name: str,
        request_data: Dict[str, Any],
        batch: bool = True
    ) -> Dict[str, Any]:
        """
        Submit a request for processing, optionally batching it
        
        Args:
            resource_name: Name of the resource to use
            request_data: The request data
            batch: Whether to allow batch processing
            
        Returns:
            Dict containing the response and metrics
        """
        config = self.configs[resource_name]
        
        if batch and config.batch_config:
            # Add to batch queue
            future = asyncio.Future()
            self.batch_queues[resource_name].append({
                "data": request_data,
                "future": future
            })
            self.batch_events[resource_name].set()
            
            # Wait for result
            return await future
        else:
            # Process immediately
            return await self._process_single_request(resource_name, request_data)

    async def _update_performance_metrics(
        self,
        resource_name: str,
        processing_time: float,
        batch_size: int,
        results: List[Dict]
    ):
        """Update performance metrics for a resource"""
        config = self.configs[resource_name]
        if not config.performance_metrics:
            config.performance_metrics = {}
            
        metrics = config.performance_metrics
        metrics["avg_processing_time"] = (
            metrics.get("avg_processing_time", processing_time) * 0.9 +
            processing_time * 0.1
        )
        metrics["avg_batch_size"] = (
            metrics.get("avg_batch_size", batch_size) * 0.9 +
            batch_size * 0.1
        )
        metrics["success_rate"] = (
            metrics.get("success_rate", 1.0) * 0.9 +
            (sum(1 for r in results if not r.get("error")) / len(results)) * 0.1
        )
        
        # Save metrics to database
        await self._save_performance_metrics(resource_name, metrics)

    def _adjust_batch_size(self, resource_name: str, processing_time: float, batch_size: int):
        """Dynamically adjust batch size based on performance"""
        config = self.configs[resource_name]
        batch_config = config.batch_config
        
        # Calculate optimal batch size based on processing time and success rate
        metrics = config.performance_metrics or {}
        success_rate = metrics.get("success_rate", 1.0)
        avg_processing_time = metrics.get("avg_processing_time", processing_time)
        
        if processing_time > batch_config.max_wait_time and batch_size > batch_config.min_batch_size:
            # Reduce batch size if processing is too slow
            batch_config.max_batch_size = max(
                batch_config.min_batch_size,
                int(batch_config.max_batch_size * 0.8)
            )
        elif (processing_time < batch_config.max_wait_time * 0.8 and 
              success_rate > 0.95 and 
              batch_size >= batch_config.max_batch_size):
            # Increase batch size if processing is fast and reliable
            batch_config.max_batch_size = min(
                batch_config.max_batch_size * 1.2,
                100  # Hard upper limit
            )

    async def _try_fallback_models(self, resource_name: str, batch: List[Dict]) -> List[Dict]:
        """Try fallback models when primary model fails"""
        config = self.configs[resource_name]
        if not config.fallback_models:
            raise ValueError(f"No fallback models configured for {resource_name}")
            
        for fallback_model in config.fallback_models:
            try:
                return await self._process_batch(fallback_model, batch)
            except Exception as e:
                logging.warning(f"Fallback {fallback_model} failed: {e}")
                continue
                
        raise ValueError("All fallback models failed")

    async def register_resource(
        self,
        config: ResourceConfig
    ) -> Dict[str, Any]:
        """
        Register a new resource for tracking
        
        Args:
            config: ResourceConfig instance with resource details
            
        Returns:
            Dict containing registration status and resource details
        """
        request_id = generate_request_id()
        journey_id = track_request_journey(
            request_id=request_id,
            action_type="register_resource",
            resource_name=config.name,
            workspace_id=self.workspace_id
        )
        
        try:
            # Set workspace ID if not provided
            if not config.workspace_id:
                config.workspace_id = self.workspace_id
                
            update_journey_state(journey_id, "Validating configuration")
            
            # Validate configuration
            if not config.name or not config.type:
                raise ValueError("Resource name and type are required")
                
            if config.name in self.configs:
                raise ValueError(f"Resource {config.name} already registered")
                
            # Save to database
            update_journey_state(journey_id, "Saving configuration")
            await asyncio.get_event_loop().run_in_executor(
                self.executor,
                self._save_config_to_db,
                config
            )
            
            # Update cache
            self.configs[config.name] = config
            self.usage_cache[config.name] = {
                "current_period": {
                    "metrics": {},
                    "cost": 0.0
                },
                "rate_limits": {
                    "current_usage": {},
                    "last_reset": datetime.now()
                }
            }
            
            result = {
                "resource_name": config.name,
                "type": config.type,
                "metrics": config.metrics,
                "workspace_id": config.workspace_id
            }
            
            complete_journey(journey_id, "success", result)
            return result
            
        except Exception as e:
            error_details = {"error": str(e), "resource_name": config.name}
            complete_journey(journey_id, "error", error_details)
            raise
            
    def _save_config_to_db(self, config: ResourceConfig):
        """Save resource configuration to database"""
        with self.db.transaction():
            self.db.execute_query(
                "INSERT OR REPLACE INTO resource_configs (resource_name, config_data, workspace_id) VALUES (?, ?, ?)",
                (config.name, json.dumps(config.__dict__), config.workspace_id)
            )

    async def track_usage(
        self,
        resource_name: str,
        metrics: Dict[str, Union[int, float]],
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Track resource usage and calculate costs
        
        Args:
            resource_name: Name of the resource being used
            metrics: Dictionary of metric types and values
            metadata: Optional metadata about the usage
            
        Returns:
            Dict containing tracking results, costs, current usage, and rate limits
        """
        request_id = generate_request_id()
        journey_id = track_request_journey(
            request_id=request_id,
            action_type="track_resource_usage",
            resource_name=resource_name,
            workspace_id=self.workspace_id
        )
        
        try:
            # Validate resource exists
            if resource_name not in self.configs:
                raise ValueError(f"Resource {resource_name} not registered")
                
            config = self.configs[resource_name]
            update_journey_state(journey_id, "Calculating costs")
            
            # Calculate costs based on metrics
            total_cost = 0.0
            for metric_type, value in metrics.items():
                if metric_type in config.cost_config:
                    total_cost += value * config.cost_config[metric_type]
                    
            # Check rate limits
            current_usage = await self.get_current_usage(resource_name)
            update_journey_state(journey_id, "Checking rate limits")
            
            warnings = []
            for limit_type, limit in config.limits.items():
                if limit_type in current_usage and current_usage[limit_type] > limit:
                    warning = f"Rate limit exceeded for {limit_type}"
                    warnings.append(warning)
                    self.boardroom.log_event(
                        event_type="rate_limit_exceeded",
                        resource_name=resource_name,
                        limit_type=limit_type,
                        current_usage=current_usage[limit_type],
                        limit=limit,
                        workspace_id=self.workspace_id
                    )
            
            # Save usage data
            update_journey_state(journey_id, "Saving usage data")
            await asyncio.get_event_loop().run_in_executor(
                self.executor,
                self._save_usage_data,
                resource_name,
                config.type,
                metrics,
                total_cost,
                metadata
            )
            
            result = {
                "resource_name": resource_name,
                "metrics_tracked": metrics,
                "total_cost": total_cost,
                "current_usage": current_usage,
                "warnings": warnings
            }
            
            complete_journey(journey_id, "success", result)
            return result
            
        except Exception as e:
            error_details = {"error": str(e), "resource_name": resource_name}
            complete_journey(journey_id, "error", error_details)
            raise
        
    def _save_usage_data(
        self,
        resource_name: str,
        resource_type: str,
        metrics: Dict[str, Union[int, float]],
        cost: float,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Save usage data to database"""
        with self.db.transaction():
            for metric_type, value in metrics.items():
                self.db.execute_query(
                    """
                    INSERT INTO usage_logs 
                    (resource_name, resource_type, metric_type, metric_value, cost, metadata, workspace_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        resource_name,
                        resource_type,
                        metric_type,
                        value,
                        cost,
                        json.dumps(metadata) if metadata else None,
                        self.workspace_id
                    )
                )

    async def get_usage_report(
        self,
        resource_names: Optional[List[str]] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        group_by: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate a usage report for specified resources and time period
        
        Args:
            resource_names: Optional list of resources to include (all if None)
            start_time: Start of reporting period (30 days ago if None)
            end_time: End of reporting period (now if None)
            group_by: Optional grouping ('day', 'hour', 'resource', etc.)
            
        Returns:
            Dict containing usage statistics, costs, and resource details
        """
        request_id = generate_request_id()
        journey_id = track_request_journey(
            request_id=request_id,
            action_type="generate_usage_report",
            resource_names=resource_names,
            workspace_id=self.workspace_id
        )
        
        try:
            # Set default time range if not provided
            if not start_time:
                start_time = datetime.now() - timedelta(days=30)
            if not end_time:
                end_time = datetime.now()
                
            update_journey_state(journey_id, "Building query")
            
            # Build base query
            query = """
                SELECT 
                    resource_name,
                    resource_type,
                    metric_type,
                    SUM(metric_value) as total_value,
                    SUM(cost) as total_cost,
                    COUNT(*) as usage_count
                FROM usage_logs
                WHERE timestamp BETWEEN ? AND ?
            """
            params = [start_time, end_time]
            
            # Add resource filter if specified
            if resource_names:
                placeholders = ','.join('?' * len(resource_names))
                query += f" AND resource_name IN ({placeholders})"
                params.extend(resource_names)
                
            # Add workspace filter if specified
            if self.workspace_id:
                query += " AND (workspace_id = ? OR workspace_id IS NULL)"
                params.append(self.workspace_id)
                
            # Add grouping
            group_clause = "resource_name, resource_type, metric_type"
            if group_by == "day":
                group_clause = "DATE(timestamp), " + group_clause
            elif group_by == "hour":
                group_clause = "strftime('%Y-%m-%d %H:00:00', timestamp), " + group_clause
                
            query += f" GROUP BY {group_clause}"
            
            update_journey_state(journey_id, "Executing query")
            
            # Execute query
            results = await asyncio.get_event_loop().run_in_executor(
                self.executor,
                self._execute_report_query,
                query,
                params
            )
            
            # Process results
            update_journey_state(journey_id, "Processing results")
            
            report = {
                "period": {
                    "start": start_time.isoformat(),
                    "end": end_time.isoformat()
                },
                "total_cost": 0.0,
                "resources": {},
                "workspace_id": self.workspace_id
            }
            
            for row in results:
                resource_name = row[0]
                if resource_name not in report["resources"]:
                    report["resources"][resource_name] = {
                        "type": row[1],
                        "metrics": {},
                        "total_cost": 0.0,
                        "usage_count": 0
                    }
                    
                resource = report["resources"][resource_name]
                metric_type = row[2]
                resource["metrics"][metric_type] = row[3]
                resource["total_cost"] += row[4]
                resource["usage_count"] += row[5]
                report["total_cost"] += row[4]
            
            complete_journey(journey_id, "success", report)
            return report
            
        except Exception as e:
            error_details = {
                "error": str(e),
                "resource_names": resource_names,
                "period": {"start": start_time, "end": end_time}
            }
            complete_journey(journey_id, "error", error_details)
            raise

    def _execute_report_query(self, query: str, params: List[Any]) -> List[Tuple]:
        """Execute a report query and return results"""
        cursor = self.db.execute_query(query, params)
        return cursor.fetchall()

    async def get_current_usage(self, resource_name: str) -> Dict[str, Any]:
        """
        Get current usage statistics for a resource
        
        Args:
            resource_name: Name of the resource
            
        Returns:
            Dict containing current usage metrics and rate limits
        """
        # Get usage for last hour
        hour_query = """
            SELECT 
                metric_type,
                SUM(metric_value) as total_value,
                SUM(cost) as total_cost
            FROM usage_logs
            WHERE 
                resource_name = ?
                AND timestamp >= datetime('now', '-1 hour')
                AND (workspace_id = ? OR workspace_id IS NULL)
            GROUP BY metric_type
        """
        
        # Get usage for last day
        day_query = """
            SELECT 
                metric_type,
                SUM(metric_value) as total_value,
                SUM(cost) as total_cost
            FROM usage_logs
            WHERE 
                resource_name = ?
                AND timestamp >= datetime('now', '-1 day')
                AND (workspace_id = ? OR workspace_id IS NULL)
            GROUP BY metric_type
        """
        
        try:
            # Execute queries asynchronously
            params = (resource_name, self.workspace_id)
            
            hour_results = await asyncio.get_event_loop().run_in_executor(
                self.executor,
                self._execute_report_query,
                hour_query,
                params
            )
            
            day_results = await asyncio.get_event_loop().run_in_executor(
                self.executor,
                self._execute_report_query,
                day_query,
                params
            )
            
            # Process results
            usage = {
                "last_hour": {
                    "metrics": {},
                    "total_cost": 0.0
                },
                "last_day": {
                    "metrics": {},
                    "total_cost": 0.0
                }
            }
            
            for row in hour_results:
                usage["last_hour"]["metrics"][row[0]] = row[1]
                usage["last_hour"]["total_cost"] += row[2]
                
            for row in day_results:
                usage["last_day"]["metrics"][row[0]] = row[1]
                usage["last_day"]["total_cost"] += row[2]
                
            return usage
            
        except Exception as e:
            logging.error(f"Error getting current usage for {resource_name}: {e}")
            raise

    async def reset_rate_limits(self, resource_name: str) -> Dict[str, Any]:
        """
        Reset rate limits for a resource
        
        Args:
            resource_name: Name of the resource
            
        Returns:
            Dict containing reset status and details
        """
        request_id = generate_request_id()
        journey_id = track_request_journey(
            request_id=request_id,
            action_type="reset_rate_limits",
            resource_name=resource_name,
            workspace_id=self.workspace_id
        )
        
        try:
            update_journey_state(journey_id, "Resetting rate limits")
            
            if resource_name not in self.configs:
                raise ValueError(f"Resource {resource_name} not registered")
                
            # Reset rate limits in cache
            self.usage_cache[resource_name]["rate_limits"] = {
                "current_usage": {},
                "last_reset": datetime.now()
            }
            
            # Log reset event
            self.boardroom.log_event(
                event_type="rate_limits_reset",
                resource_name=resource_name,
                workspace_id=self.workspace_id
            )
            
            result = {
                "resource_name": resource_name,
                "reset_time": datetime.now().isoformat(),
                "workspace_id": self.workspace_id
            }
            
            complete_journey(journey_id, "success", result)
            return result
            
        except Exception as e:
            error_details = {"error": str(e), "resource_name": resource_name}
            complete_journey(journey_id, "error", error_details)
            raise
            
    async def get_resource_config(self, resource_name: str) -> Dict[str, Any]:
        """
        Get configuration for a resource
        
        Args:
            resource_name: Name of the resource
            
        Returns:
            Dict containing resource configuration
        """
        request_id = generate_request_id()
        journey_id = track_request_journey(
            request_id=request_id,
            action_type="get_resource_config",
            resource_name=resource_name,
            workspace_id=self.workspace_id
        )
        
        try:
            update_journey_state(journey_id, "Retrieving configuration")
            
            if resource_name not in self.configs:
                raise ValueError(f"Resource {resource_name} not registered")
                
            config = self.configs[resource_name]
            result = {
                "resource_name": config.name,
                "type": config.type,
                "metrics": config.metrics,
                "cost_config": config.cost_config,
                "limits": config.limits,
                "features": config.features,
                "workspace_id": config.workspace_id
            }
            
            complete_journey(journey_id, "success", result)
            return result
            
        except Exception as e:
            error_details = {"error": str(e), "resource_name": resource_name}
            complete_journey(journey_id, "error", error_details)
            raise
            
    async def update_resource_config(
        self,
        resource_name: str,
        updates: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Update configuration for a resource
        
        Args:
            resource_name: Name of the resource
            updates: Dictionary of configuration updates
            
        Returns:
            Dict containing updated resource configuration
        """
        request_id = generate_request_id()
        journey_id = track_request_journey(
            request_id=request_id,
            action_type="update_resource_config",
            resource_name=resource_name,
            workspace_id=self.workspace_id
        )
        
        try:
            update_journey_state(journey_id, "Updating configuration")
            
            if resource_name not in self.configs:
                raise ValueError(f"Resource {resource_name} not registered")
                
            config = self.configs[resource_name]
            
            # Update configuration fields
            for key, value in updates.items():
                if hasattr(config, key):
                    setattr(config, key, value)
                    
            # Save updated configuration
            await asyncio.get_event_loop().run_in_executor(
                self.executor,
                self._save_config_to_db,
                config
            )
            
            result = {
                "resource_name": config.name,
                "type": config.type,
                "metrics": config.metrics,
                "cost_config": config.cost_config,
                "limits": config.limits,
                "features": config.features,
                "workspace_id": config.workspace_id,
                "updated_fields": list(updates.keys())
            }
            
            complete_journey(journey_id, "success", result)
            return result
            
        except Exception as e:
            error_details = {
                "error": str(e),
                "resource_name": resource_name,
                "updates": updates
            }
            complete_journey(journey_id, "error", error_details)
            raise

    async def cleanup_old_data(self, days_to_keep: int = 90) -> Dict[str, Any]:
        """
        Clean up old usage data
        
        Args:
            days_to_keep: Number of days of data to retain
            
        Returns:
            Dict containing cleanup status and details
        """
        request_id = generate_request_id()
        journey_id = track_request_journey(
            request_id=request_id,
            action_type="cleanup_old_data",
            days_to_keep=days_to_keep,
            workspace_id=self.workspace_id
        )
        
        try:
            update_journey_state(journey_id, "Cleaning up old data")
            
            # Execute cleanup
            await asyncio.get_event_loop().run_in_executor(
                self.executor,
                self._cleanup_old_data_sync,
                days_to_keep
            )
            
            result = {
                "days_kept": days_to_keep,
                "cleanup_time": datetime.now().isoformat(),
                "workspace_id": self.workspace_id
            }
            
            complete_journey(journey_id, "success", result)
            return result
            
        except Exception as e:
            error_details = {"error": str(e), "days_to_keep": days_to_keep}
            complete_journey(journey_id, "error", error_details)
            raise
        
    def _cleanup_old_data_sync(self, days_to_keep: int):
        """Synchronous cleanup of old data"""
        with self.db.transaction():
            self.db.execute_query(
                "DELETE FROM usage_logs WHERE timestamp < datetime('now', ?)",
                (f'-{days_to_keep} days',)
            )

# Create a global instance
resource_manager = ResourceManager()

# Example usage:
"""
# Register GPT-4 as a resource
gpt4_config = ResourceConfig(
    name="gpt-4",
    type="llm",
    metrics={
        "input_tokens": 0,
        "output_tokens": 0,
        "requests": 0
    },
    cost_config={
        "input_tokens": 0.03/1000,  # Cost per 1K input tokens
        "output_tokens": 0.06/1000  # Cost per 1K output tokens
    },
    limits={
        "tokens_per_minute": 90000,
        "requests_per_minute": 500
    },
    features={
        "max_tokens": 128000,
        "supports_functions": True
    }
)

# Register Wolfram Alpha as a resource
wolfram_config = ResourceConfig(
    name="wolfram-alpha",
    type="api",
    metrics={
        "queries": 0,
        "compute_time": 0
    },
    cost_config={
        "queries": 0.50  # Cost per query
    },
    limits={
        "queries_per_month": 2000
    },
    features={
        "supports_math": True,
        "supports_plots": True
    }
)

# Track usage
await resource_manager.track_usage(
    "gpt-4",
    {
        "input_tokens": 100,
        "output_tokens": 50,
        "requests": 1
    },
    metadata={"task_id": "123", "purpose": "code_analysis"}
)

# Get usage report
report = await resource_manager.get_usage_report(
    resource_names=["gpt-4", "wolfram-alpha"],
    start_time=datetime.now() - timedelta(days=7),
    group_by="day"
)
""" 

if __name__ == "__main__":
    import asyncio
    import openai
    from datetime import datetime, timedelta
    import logging
    import sys
    import json
    
    # Import config module
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from Core.config import load_api_key
    
    # Set up detailed logging
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s [%(levelname)s] %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )
    logger = logging.getLogger("TokenManagerTest")
    
    async def run_real_batch_test():
        """Test batch processing with real GPT-4 API calls"""
        logger.info("\n=== Starting Token Manager Real API Test ===\n")
        
        # Initialize OpenAI client with API key from config
        api_key = load_api_key('OPENAI')
        if not api_key:
            raise ValueError("Failed to load OpenAI API key from config")
        openai.api_key = api_key
        logger.info("OpenAI API key loaded successfully from config")
        
        # Initialize resource manager with test workspace
        logger.info("Initializing ResourceManager with test workspace...")
        manager = ResourceManager(workspace_id="test_workspace")
        logger.debug("Database initialized with tables: usage_logs, resource_configs")
        
        # Register GPT-4 with real costs and limits
        logger.info("Preparing GPT-4 configuration...")
        gpt4_config = ResourceConfig(
            name="gpt-4",
            type="llm",
            metrics={
                "input_tokens": 0,
                "output_tokens": 0,
                "requests": 0
            },
            cost_config={
                "input_tokens": 0.03/1000,  # Real GPT-4 input token cost
                "output_tokens": 0.06/1000  # Real GPT-4 output token cost
            },
            limits={
                "tokens_per_minute": 90000,
                "requests_per_minute": 500
            },
            features={
                "max_tokens": 8192,  # Real GPT-4 token limit
                "supports_functions": True
            },
            batch_config=BatchConfig(
                max_batch_size=20,
                max_wait_time=1.0,
                min_batch_size=3,
                dynamic_sizing=True
            ),
            fallback_models=["gpt-3.5-turbo"]
        )
        
        logger.info("1. Registering GPT-4 with real API configuration...")
        try:
            registration_result = await manager.register_resource(gpt4_config)
            logger.debug("Registration result: %s", registration_result)
            logger.info("GPT-4 registered successfully")
        except Exception as e:
            logger.error("Failed to register GPT-4: %s", str(e))
            raise
        
        # Log database state after registration
        logger.debug("Current database state:")
        cursor = manager.db.execute_query("SELECT * FROM resource_configs")
        for row in cursor.fetchall():
            logger.debug("Resource config: %s", row)
        
        # Prepare real test requests with varying complexity
        logger.info("Preparing test requests...")
        test_requests = [
            {
                "prompt": "Explain the concept of quantum entanglement in simple terms.",
                "max_tokens": 100
            },
            {
                "prompt": "Write a haiku about artificial intelligence.",
                "max_tokens": 50
            },
            {
                "prompt": "What are the key principles of clean code?",
                "max_tokens": 150
            },
            {
                "prompt": "Describe the process of photosynthesis.",
                "max_tokens": 120
            },
            {
                "prompt": "Compare and contrast REST and GraphQL.",
                "max_tokens": 200
            }
        ]
        
        logger.info("\n2. Submitting real API requests...")
        # Submit requests concurrently
        tasks = []
        for i, req in enumerate(test_requests):
            logger.debug("Queuing request %d: %s", i+1, req["prompt"][:50] + "...")
            task = asyncio.create_task(manager.submit_request(
                "gpt-4",
                request_data=req,
                batch=True
            ))
            tasks.append(task)
        
        # Wait for all requests to complete
        logger.info("3. Processing real API requests...")
        try:
            results = await asyncio.gather(*tasks)
            logger.info("\nAPI Responses:")
            total_tokens = 0
            total_cost = 0
            
            for i, result in enumerate(results):
                logger.info("\nRequest %d:", i+1)
                logger.info("Prompt: %s", test_requests[i]["prompt"])
                logger.info("Response: %s...", result.get('response', 'No response')[:100])
                
                usage = result.get('usage', {})
                tokens = usage.get('total_tokens', 0)
                total_tokens += tokens
                
                # Calculate cost
                input_tokens = usage.get('prompt_tokens', 0)
                output_tokens = usage.get('completion_tokens', 0)
                cost = (input_tokens * 0.03 + output_tokens * 0.06) / 1000
                total_cost += cost
                
                logger.info("Tokens used: %d (Input: %d, Output: %d)", 
                           tokens, input_tokens, output_tokens)
                logger.info("Request cost: $%.4f", cost)
                
                # Log database entry for this request
                cursor = manager.db.execute_query(
                    "SELECT * FROM usage_logs WHERE resource_name = ? ORDER BY timestamp DESC LIMIT 1",
                    ("gpt-4",)
                )
                log_entry = cursor.fetchone()
                logger.debug("Usage log entry: %s", log_entry)
                
            logger.info("\nBatch Summary:")
            logger.info("Total tokens used: %d", total_tokens)
            logger.info("Total cost: $%.4f", total_cost)
            
        except Exception as e:
            logger.error("Error processing requests: %s", str(e))
            raise
        
        # Get real performance metrics
        logger.info("\n4. Checking actual performance metrics...")
        config = manager.configs["gpt-4"]
        metrics = config.performance_metrics or {}
        
        logger.info("\nPerformance Metrics:")
        logger.info("- Average processing time: %.3fs", metrics.get('avg_processing_time', 0))
        logger.info("- Average batch size: %.1f", metrics.get('avg_batch_size', 0))
        logger.info("- Success rate: %.1f%%", metrics.get('success_rate', 0)*100)
        
        # Log batch processing details
        logger.debug("Batch processing configuration:")
        logger.debug("- Max batch size: %d", config.batch_config.max_batch_size)
        logger.debug("- Min batch size: %d", config.batch_config.min_batch_size)
        logger.debug("- Wait time: %.2fs", config.batch_config.max_wait_time)
        
        # Get real usage report
        logger.info("\n5. Generating actual usage report...")
        report = await manager.get_usage_report(
            resource_names=["gpt-4"],
            start_time=datetime.now() - timedelta(minutes=5)
        )
        
        logger.info("\nUsage Report:")
        logger.info("- Total cost: $%.4f", report['total_cost'])
        if "gpt-4" in report["resources"]:
            gpt4_stats = report["resources"]["gpt-4"]
            logger.info("- Total requests: %d", gpt4_stats['usage_count'])
            logger.info("- Metrics: %s", json.dumps(gpt4_stats['metrics'], indent=2))
            
            # Log detailed database metrics
            cursor = manager.db.execute_query("""
                SELECT metric_type, COUNT(*) as count, SUM(metric_value) as total, AVG(cost) as avg_cost
                FROM usage_logs 
                WHERE resource_name = 'gpt-4'
                GROUP BY metric_type
            """)
            logger.debug("\nDetailed database metrics:")
            for row in cursor.fetchall():
                logger.debug("- %s: count=%d, total=%.2f, avg_cost=%.4f", 
                           row[0], row[1], row[2], row[3])
        
        # Test real fallback to GPT-3.5
        logger.info("\n6. Testing real fallback to GPT-3.5...")
        try:
            # Create a request that might trigger fallback
            large_request = {
                "prompt": "Write a comprehensive essay about the history of artificial intelligence, " * 10,  # Intentionally large prompt
                "max_tokens": 4000
            }
            logger.debug("Submitting large request to test fallback...")
            result = await manager.submit_request("gpt-4", large_request)
            logger.info("Request handled by model: %s", result.get('model', 'unknown'))
            
            # Log fallback details
            logger.debug("Fallback request details:")
            logger.debug("- Prompt length: %d characters", len(large_request["prompt"]))
            logger.debug("- Requested tokens: %d", large_request["max_tokens"])
            logger.debug("- Response length: %d characters", 
                        len(result.get('response', '')))
            
        except Exception as e:
            logger.error("Fallback handling error: %s", str(e))
            # Log error details
            logger.debug("Error context:", exc_info=True)
        
        # Final database state
        logger.debug("\nFinal database state:")
        cursor = manager.db.execute_query("""
            SELECT 
                COUNT(*) as total_logs,
                COUNT(DISTINCT resource_name) as unique_resources,
                SUM(cost) as total_cost
            FROM usage_logs
        """)
        stats = cursor.fetchone()
        logger.debug("- Total log entries: %d", stats[0])
        logger.debug("- Unique resources: %d", stats[1])
        logger.debug("- Total recorded cost: $%.4f", stats[2])
        
        logger.info("\n=== Test Complete ===")

    # Run the real API test
    logger.info("Starting token manager tests with real API calls...")
    asyncio.run(run_real_batch_test()) 