"""
Handler Execution Tracking Module

This module provides enhanced handler action tracking functionality for the Jarvis Orchestrator,
enabling tracking of success/failure rates for all handler actions, which allows for:

1. Better intelligence-based routing
2. Improved success rate monitoring
3. Error pattern identification
4. Parameter pattern learning
"""

import time
import json
import logging
import traceback
import importlib
import asyncio
from typing import Dict, Any, Optional, Union
import os
import hashlib

# Import needed functions 
try:
    # Import unified database helper
    from Jarvis_Agent_SDK.import_helper import get_unified_database
    # We will log errors but continue if these imports fail, as they're optional
    from Jarvis_Agent_SDK.jarvis_orchestrator import orchestrator_agent
except ImportError as e:
    logging.warning(f"Import error in handler_execution_tracking: {str(e)}")
    orchestrator_agent = None
    get_unified_database = None
    logging.warning("Could not import required modules, tracking will be limited")

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("handler_execution_tracking")

# Database constants
HANDLER_TRACKING_DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
                                     "Database", "handler_tracking.db")

class HandlerTrackingDatabase:
    """
    Database manager for handler execution tracking.
    
    Provides methods to store and retrieve handler execution metrics using the unified database system.
    """
    
    def __init__(self, db_path=None):
        """
        Initialize the database manager.
        
        Args:
            db_path: Optional path to the database file
        """
        self.db = None
        self.db_path = db_path or HANDLER_TRACKING_DB_PATH
        self.connected = False
        self._initialize_database()
        
    def _initialize_database(self):
        """Initialize the database connection using the unified database approach."""
        try:
            # Ensure the Database directory exists
            db_dir = os.path.dirname(self.db_path)
            os.makedirs(db_dir, exist_ok=True)
            
            # Check if the database directory is writable
            if not os.access(db_dir, os.W_OK):
                logger.error(f"Database directory {db_dir} is not writable")
                return
                
            # Try to get the unified database instance
            if get_unified_database:
                logger.info(f"Attempting to connect to unified database at {self.db_path}")
                self.db = get_unified_database(self.db_path)
                if self.db:
                    logger.info(f"Connected to unified database at {self.db_path}")
                    self.connected = True
                    self._ensure_tables_exist()
                else:
                    logger.error(f"Failed to connect to unified database at {self.db_path}")
                    
                    # Try with a more specific fallback path
                    fallback_path = os.path.join(os.path.expanduser("~"), "Jarvis", "Database", "handler_tracking.db")
                    logger.info(f"Trying fallback database path: {fallback_path}")
                    os.makedirs(os.path.dirname(fallback_path), exist_ok=True)
                    self.db = get_unified_database(fallback_path)
                    if self.db:
                        logger.info(f"Connected to fallback database at {fallback_path}")
                        self.db_path = fallback_path
                        self.connected = True
            else:
                logger.error("Unified database helper not available")
        except Exception as e:
            logger.error(f"Error initializing database: {str(e)}")
            logger.error(traceback.format_exc())
            
    def _ensure_tables_exist(self):
        """Ensure that all required tables exist in the database."""
        if not self.connected or not self.db:
            logger.error("Cannot create tables - not connected to database")
            return False
            
        try:
            with self.db.transaction():
                # Create handler execution tracking table
                self.db.execute_query("""
                    CREATE TABLE IF NOT EXISTS handler_execution_tracking (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        handler_name TEXT NOT NULL,
                        action TEXT NOT NULL,
                        timestamp REAL NOT NULL,
                        journey_id TEXT,
                        session_id TEXT,
                        success INTEGER NOT NULL,
                        execution_time REAL,
                        workspace_id TEXT,
                        error TEXT,
                        parameters TEXT
                    )
                """)
                
                # Create handler performance table
                self.db.execute_query("""
                    CREATE TABLE IF NOT EXISTS handler_performance (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        handler_name TEXT NOT NULL,
                        action TEXT NOT NULL,
                        success_count INTEGER DEFAULT 0,
                        failure_count INTEGER DEFAULT 0,
                        avg_execution_time REAL DEFAULT 0,
                        total_execution_time REAL DEFAULT 0,
                        total_calls INTEGER DEFAULT 0,
                        last_updated REAL NOT NULL,
                        workspace_id TEXT,
                        UNIQUE(handler_name, action, workspace_id)
                    )
                """)
                
                # Create handler error patterns table
                self.db.execute_query("""
                    CREATE TABLE IF NOT EXISTS handler_error_patterns (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        handler_name TEXT NOT NULL,
                        action TEXT NOT NULL,
                        error_type TEXT NOT NULL,
                        count INTEGER DEFAULT 0,
                        last_occurred REAL NOT NULL,
                        workspace_id TEXT,
                        UNIQUE(handler_name, action, error_type, workspace_id)
                    )
                """)
                
                # Create parameter patterns table
                self.db.execute_query("""
                    CREATE TABLE IF NOT EXISTS handler_parameter_patterns (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        handler_name TEXT NOT NULL,
                        action TEXT NOT NULL,
                        param_name TEXT NOT NULL,
                        param_value TEXT NOT NULL,
                        count INTEGER DEFAULT 0,
                        success_count INTEGER DEFAULT 0,
                        last_used REAL NOT NULL,
                        workspace_id TEXT,
                        UNIQUE(handler_name, action, param_name, param_value, workspace_id)
                    )
                """)
                
                # Create related actions table
                self.db.execute_query("""
                    CREATE TABLE IF NOT EXISTS handler_related_actions (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        handler_action TEXT NOT NULL,
                        related_action TEXT NOT NULL,
                        count INTEGER DEFAULT 0,
                        last_updated REAL NOT NULL,
                        workspace_id TEXT,
                        UNIQUE(handler_action, related_action, workspace_id)
                    )
                """)
                
                logger.info("Handler tracking database tables initialized")
                return True
        except Exception as e:
            logger.error(f"Error ensuring handler tracking tables: {str(e)}")
            logger.error(traceback.format_exc())
            return False
    
    def record_handler_execution(self, 
                                handler_name: str, 
                                action: str, 
                                success: bool, 
                                execution_time: float = None,
                                parameters: Dict[str, Any] = None,
                                error: str = None,
                                journey_id: str = None,
                                session_id: str = None,
                                workspace_id: str = None) -> bool:
        """
        Record a handler execution in the database.
        
        Args:
            handler_name: Name of the handler
            action: Action performed
            success: Whether execution was successful
            execution_time: Time taken to execute
            parameters: Parameters used in the execution
            error: Error message if execution failed
            journey_id: Journey ID for tracking
            session_id: Session ID for tracking
            workspace_id: Workspace ID for context
            
        Returns:
            True if recorded successfully, False otherwise
        """
        if not self.connected or not self.db:
            logger.error("Cannot record handler execution - not connected to database")
            return False
            
        try:
            timestamp = time.time()
            
            # Convert parameters to JSON string if needed
            params_json = None
            if parameters:
                try:
                    # Filter out any sensitive parameters
                    filtered_params = {k: v for k, v in parameters.items() 
                                     if not any(sensitive in k.lower() for sensitive in 
                                              ['password', 'token', 'key', 'secret', 'credential'])}
                    
                    # Truncate very long values to avoid DB issues
                    for k, v in filtered_params.items():
                        if isinstance(v, str) and len(v) > 500:
                            filtered_params[k] = v[:500] + "..."
                    
                    params_json = json.dumps(filtered_params)
                except Exception as json_error:
                    logger.error(f"Error converting parameters to JSON: {str(json_error)}")
                    params_json = json.dumps({"error": "Could not serialize parameters"})
            
            # Insert execution record
            with self.db.transaction():
                self.db.execute_query(
                    """
                    INSERT INTO handler_execution_tracking 
                    (handler_name, action, timestamp, journey_id, session_id, success, 
                     execution_time, workspace_id, error, parameters)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        handler_name,
                        action,
                        timestamp,
                        journey_id,
                        session_id,
                        1 if success else 0,
                        execution_time,
                        workspace_id,
                        error,
                        params_json
                    )
                )
                
                # Update performance metrics
                handler_action_key = f"{handler_name}.{action}"
                
                # Update performance table
                self.db.execute_query(
                    """
                    INSERT INTO handler_performance
                    (handler_name, action, success_count, failure_count, 
                     avg_execution_time, total_execution_time, total_calls, last_updated, workspace_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(handler_name, action, workspace_id) DO UPDATE SET
                    success_count = success_count + ?,
                    failure_count = failure_count + ?,
                    total_execution_time = total_execution_time + ?,
                    total_calls = total_calls + 1,
                    avg_execution_time = (total_execution_time + ?) / (total_calls + 1),
                    last_updated = ?
                    """,
                    (
                        handler_name,
                        action,
                        1 if success else 0,
                        0 if success else 1,
                        execution_time if execution_time else 0,
                        execution_time if execution_time else 0,
                        1,
                        timestamp,
                        workspace_id,
                        
                        # Values for the ON CONFLICT UPDATE
                        1 if success else 0,
                        0 if success else 1,
                        execution_time if execution_time else 0,
                        execution_time if execution_time else 0,
                        timestamp
                    )
                )
                
                # Update error patterns if execution failed
                if not success and error:
                    error_type = error.split(":")[0] if ":" in error else error
                    self.db.execute_query(
                        """
                        INSERT INTO handler_error_patterns
                        (handler_name, action, error_type, count, last_occurred, workspace_id)
                        VALUES (?, ?, ?, 1, ?, ?)
                        ON CONFLICT(handler_name, action, error_type, workspace_id) DO UPDATE SET
                        count = count + 1,
                        last_occurred = ?
                        """,
                        (
                            handler_name,
                            action,
                            error_type,
                            timestamp,
                            workspace_id,
                            timestamp
                        )
                    )
                
                # Update parameter patterns if execution succeeded
                if success and parameters and params_json:
                    for param_name, param_value in parameters.items():
                        # Skip sensitive parameters
                        if any(sensitive in param_name.lower() for sensitive in 
                              ['password', 'token', 'key', 'secret', 'credential']):
                            continue
                        
                        # Convert value to string and limit size
                        param_str = str(param_value)
                        if len(param_str) > 500:
                            param_str = param_str[:500] + "..."
                        
                        self.db.execute_query(
                            """
                            INSERT INTO handler_parameter_patterns
                            (handler_name, action, param_name, param_value, count, success_count, last_used, workspace_id)
                            VALUES (?, ?, ?, ?, 1, 1, ?, ?)
                            ON CONFLICT(handler_name, action, param_name, param_value, workspace_id) DO UPDATE SET
                            count = count + 1,
                            success_count = success_count + 1,
                            last_used = ?
                            """,
                            (
                                handler_name,
                                action,
                                param_name,
                                param_str,
                                timestamp,
                                workspace_id,
                                timestamp
                            )
                        )
            
            return True
        
        except Exception as e:
            logger.error(f"Error recording handler execution: {str(e)}")
            logger.error(traceback.format_exc())
            return False
    
    def get_handler_performance(self, handler_name=None, action=None, workspace_id=None) -> Dict[str, Any]:
        """
        Get performance metrics for a handler action or all handlers.
        
        Args:
            handler_name: Optional name of the handler to get metrics for
            action: Optional action to get metrics for (requires handler_name)
            workspace_id: Optional workspace ID
            
        Returns:
            Dictionary of performance metrics
        """
        if not self.connected or not self.db:
            logger.error("Cannot get handler performance - not connected to database")
            return {"error": "Not connected to database"}
            
        try:
            query = "SELECT * FROM handler_performance"
            params = []
            
            where_clauses = []
            if handler_name:
                where_clauses.append("handler_name = ?")
                params.append(handler_name)
                
                if action:
                    where_clauses.append("action = ?")
                    params.append(action)
            
            if workspace_id:
                where_clauses.append("workspace_id = ?")
                params.append(workspace_id)
                
            if where_clauses:
                query += " WHERE " + " AND ".join(where_clauses)
                
            cursor = self.db.execute_query(query, tuple(params))
            
            results = []
            for row in cursor.fetchall():
                success_rate = 0
                if row["total_calls"] > 0:
                    success_rate = row["success_count"] / row["total_calls"]
                    
                results.append({
                    "handler_name": row["handler_name"],
                    "action": row["action"],
                    "success_count": row["success_count"],
                    "failure_count": row["failure_count"],
                    "avg_execution_time": row["avg_execution_time"],
                    "total_calls": row["total_calls"],
                    "success_rate": success_rate,
                    "last_updated": row["last_updated"],
                    "workspace_id": row["workspace_id"]
                })
            
            return {
                "success": True,
                "results": results
            }
            
        except Exception as e:
            logger.error(f"Error getting handler performance: {str(e)}")
            logger.error(traceback.format_exc())
            return {"error": str(e)}

# Initialize the database
_handler_tracking_db = None

def get_handler_tracking_db(db_path=None) -> HandlerTrackingDatabase:
    """Get or create the handler tracking database instance."""
    global _handler_tracking_db
    
    if _handler_tracking_db is None:
        _handler_tracking_db = HandlerTrackingDatabase(db_path)
        
    return _handler_tracking_db

# Handler execution with tracking
async def execute_handler_with_tracking(
    handler_name: str, 
    action: str, 
    parameters: Dict[str, Any] = None,
    journey_id: str = None,
    session_id: str = None,
    workspace_id: str = None
) -> Dict[str, Any]:
    """
    Execute a handler action with success/failure tracking.
    
    This function extends the standard handler execution with detailed tracking of:
    - Success/failure rates
    - Execution times
    - Error patterns
    - Parameter patterns
    
    Args:
        handler_name: The name of the handler to execute
        action: The action to perform
        parameters: Parameters for the action
        journey_id: Optional journey ID for tracking multi-step operations
        session_id: Optional session ID for tracking user sessions
        workspace_id: Optional workspace ID for context
        
    Returns:
        Result of the handler execution
    """
    if parameters is None:
        parameters = {}
        
    # Add tracking IDs to parameters if provided
    if journey_id and 'journey_id' not in parameters:
        parameters['journey_id'] = journey_id
    if session_id and 'session_id' not in parameters:
        parameters['session_id'] = session_id
    
    # Record the start time for tracking execution duration
    start_time = time.time()
    success = False
    error = None
    result = None
    
    try:
        # Log execution attempt
        logging.info(f"Executing handler: {handler_name}.{action}")
        
        # First, try to import the handler module directly
        try:
            # Construct potential import paths
            module_paths = [
                f"Handler.handler_{handler_name}",
                f"Handler.{handler_name}"
            ]
            
            handler_module = None
            for module_path in module_paths:
                try:
                    logging.debug(f"Attempting to import {module_path}")
                    handler_module = importlib.import_module(module_path)
                    break
                except ImportError:
                    continue
            
            if handler_module:
                logging.info(f"Successfully imported {module_path}")
                
                # Check for execute_action function
                if hasattr(handler_module, 'execute_action') and callable(getattr(handler_module, 'execute_action')):
                    logging.debug(f"Using {module_path}.execute_action")
                    execute_action_fn = getattr(handler_module, 'execute_action')
                    
                    # Check if execute_action is a coroutine function
                    if asyncio.iscoroutinefunction(execute_action_fn):
                        result = await execute_action_fn(action, parameters)
                    else:
                        result = execute_action_fn(action, parameters)
                    
                    # Determine success based on result
                    if isinstance(result, dict):
                        success = result.get('success', False)
                        if not success and 'error' in result:
                            error = result['error']
                        elif not success and 'message' in result and 'error' in result['message'].lower():
                            error = result['message']
                    elif hasattr(result, 'success'):
                        success = result.success
                        if hasattr(result, 'error') and not success:
                            error = result.error
                            
                    return result
                    
                # Check for handler instance
                if hasattr(handler_module, 'handler'):
                    handler_instance = getattr(handler_module, 'handler')
                    if hasattr(handler_instance, 'execute_action') and callable(getattr(handler_instance, 'execute_action')):
                        logging.debug(f"Using {module_path}.handler.execute_action")
                        execute_method = getattr(handler_instance, 'execute_action')
                        
                        # Check if the execute_action method is a coroutine function
                        if asyncio.iscoroutinefunction(execute_method):
                            result = await execute_method(action, parameters)
                        else:
                            result = execute_method(action, parameters)
                        
                        # Determine success based on result
                        if isinstance(result, dict):
                            success = result.get('success', False)
                            if not success and 'error' in result:
                                error = result['error']
                            elif not success and 'message' in result and 'error' in result['message'].lower():
                                error = result['message']
                        elif hasattr(result, 'success'):
                            success = result.success
                            if hasattr(result, 'error') and not success:
                                error = result.error
                                
                        return result
                
                # Try fallback to execute method if it exists
                if hasattr(handler_module, 'execute') and callable(getattr(handler_module, 'execute')):
                    logging.debug(f"Using {module_path}.execute")
                    execute_fn = getattr(handler_module, 'execute')
                    
                    # Check if execute is a coroutine function
                    if asyncio.iscoroutinefunction(execute_fn):
                        result = await execute_fn(action, parameters)
                    else:
                        result = execute_fn(action, parameters)
                    
                    # Determine success based on result
                    if isinstance(result, dict):
                        success = result.get('success', False)
                        if not success and 'error' in result:
                            error = result['error'] 
                    elif hasattr(result, 'success'):
                        success = result.success
                        if hasattr(result, 'error') and not success:
                            error = result.error
                            
                    return result
            
            # If no direct methods found, try using our MCP-based approach
            logging.debug("Direct module methods not found, trying MCP-based execution")
            
            # Add workspace context to parameters if not present
            if workspace_id and 'context' not in parameters:
                parameters['context'] = {}
            if workspace_id and 'workspace_id' not in parameters.get('context', {}):
                parameters.setdefault('context', {})['workspace_id'] = workspace_id
            
            try:
                # Import from jarvis_orchestrator
                from Jarvis_Agent_SDK.jarvis_orchestrator import execute_handler_action_async
                
                # Execute via MCP
                logging.debug(f"Using execute_handler_action_async for {handler_name}.{action}")
                result = await execute_handler_action_async(handler_name, action, parameters)
                
                # Determine success based on result
                if isinstance(result, dict):
                    success = result.get('success', False) or result.get('status') == 'success'
                    if not success and 'error' in result:
                        error = result['error']
                elif hasattr(result, 'success'):
                    success = result.success
                    if hasattr(result, 'error') and not success:
                        error = result.error
                        
                return result
                
            except ImportError:
                # Fallback to handler_all if MCP execution is not available
                logging.debug("MCP execution not available, trying Handler.handler_all")
                try:
                    from Handler.handler_all import handler_system
                    
                    if handler_system:
                        logging.debug(f"Using handler_system.execute_command for {handler_name}.{action}")
                        result = await handler_system.execute_command(handler_name, action, parameters)
                        
                        # Determine success based on result
                        if hasattr(result, 'success'):
                            success = result.success
                            if hasattr(result, 'error') and not success:
                                error = result.error
                                
                        return result
                except ImportError:
                    logging.error("Both MCP and handler_all execution methods are unavailable")
                    error = "Both MCP and handler_all execution methods are unavailable"
                    return {"success": False, "error": error}
            
            # If we got here, we couldn't find a way to execute the handler
            error = f"No callable method found for {handler_name}.{action}"
            logging.error(error)
            return {"success": False, "error": error}
            
        except Exception as import_ex:
            error = f"Error importing or executing handler: {str(import_ex)}"
            logging.error(error)
            logging.debug(traceback.format_exc())
            return {"success": False, "error": error}
            
    except Exception as e:
        error = f"Error executing handler {handler_name}.{action}: {str(e)}"
        logging.error(error)
        logging.debug(traceback.format_exc())
        return {"success": False, "error": error}
    finally:
        # Calculate execution time
        execution_time = time.time() - start_time
        
        # Track handler action in the database
        db = get_handler_tracking_db()
        if db:
            try:
                db.record_handler_execution(
                    handler_name=handler_name,
                    action=action,
                    success=success,
                    execution_time=execution_time,
                    parameters=parameters,
                    error=error,
                    journey_id=journey_id,
                    session_id=session_id,
                    workspace_id=workspace_id
                )
            except Exception as db_error:
                logging.error(f"Error recording handler execution in database: {str(db_error)}")
                logging.debug(traceback.format_exc())
        
        # Track handler action execution using the orchestrator agent if available
        if orchestrator_agent and hasattr(orchestrator_agent, 'track_handler_action'):
            try:
                # Get the agent instance to access tracker
                if isinstance(orchestrator_agent, dict) and "agent" in orchestrator_agent:
                    agent = orchestrator_agent["agent"]
                else:
                    agent = orchestrator_agent
                
                # Track the handler action
                if hasattr(agent, 'track_handler_action'):
                    agent.track_handler_action(
                        handler_name=handler_name,
                        action=action,
                        success=success,
                        execution_time=execution_time,
                        parameters=parameters,
                        error=error,
                        result=result,
                        journey_id=journey_id,
                        session_id=session_id
                    )
            except Exception as tracking_error:
                logging.error(f"Error tracking handler action: {str(tracking_error)}")
                logging.debug(traceback.format_exc())

# For backward compatibility, provide the execute_any_handler_async function
async def execute_any_handler_async(handler_name=None, action=None, parameters=None):
    """
    Asynchronous function to execute any handler by name with tracking.
    
    This is a replacement for the original function that adds tracking capabilities.
    
    Args:
        handler_name (str, optional): Name of the handler to execute.
        action (str, optional): The action to perform on the handler.
        parameters (dict, optional): Parameters to pass to the handler action.
        
    Returns:
        dict: Result of handler execution.
    """
    # Extract journey_id and session_id if present in parameters
    journey_id = None
    session_id = None
    workspace_id = None
    
    if parameters:
        journey_id = parameters.get('journey_id')
        session_id = parameters.get('session_id')
        workspace_id = parameters.get('workspace_id')
    
    # Execute with tracking
    return await execute_handler_with_tracking(
        handler_name=handler_name,
        action=action,
        parameters=parameters,
        journey_id=journey_id,
        session_id=session_id,
        workspace_id=workspace_id
    ) 