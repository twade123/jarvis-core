"""
Base Handler: Foundation Framework for Task Execution Handlers

A comprehensive base system that provides the core functionality and structure for all specialized
task handlers in the application. Implements essential methods for task execution, error handling,
and resource management.

Core Components:
    - HandlerResult: Data structure for execution results
    - BaseHandler: Abstract base class for all handlers
    - Handler Validation: Utility for validating handler implementations
    - DatabaseManager: Centralized database operations management
    - CursorProxy/ConnectionProxy: Database access monitoring

Features:
    - Standardized Result Handling:
        - Success/failure tracking
        - Data encapsulation
        - Error messaging
        - Metadata management
        
    - Execution Framework:
        - Asynchronous task handling
        - Dynamic action dispatch
        - Parameter validation
        - Error recovery
        
    - Resource Management:
        - Initialization checks
        - Cleanup procedures
        - Dependency validation
        - Model requirements
        
    - Error Handling:
        - Exception management
        - Error result creation
        - Cleanup on failure
        - Error reporting
        
    - Validation:
        - Handler implementation checks
        - Method existence validation
        - Inheritance verification
        - Dependency checking
        
    - Database Management:
        - Centralized connection handling
        - Query execution with monitoring
        - Transaction management
        - Workspace context awareness
        - Prepared statement support
        - SQL operation metrics tracking
        - Connection pooling and reuse
        
    - Activity Logging:
        - Agent operation monitoring
        - Performance metrics collection
        - Quality score calculation
        - Automatic action tracking
        - Smart redundancy prevention
        
    - Workspace Context:
        - Multi-workspace support
        - Team collaboration features
        - Context-aware database operations
        - Environment-specific configurations

Methods:
    Core:
        - handle(): Main task processing
        - execute(): Action execution
        - cleanup(): Resource cleanup
        
    Results:
        - create_success_result(): Success response
        - create_error_result(): Error response
        - handle_error(): Error processing
        
    Database:
        - execute_query(): Run SQL queries
        - insert(): Insert records
        - update(): Update records
        - delete(): Delete records
        - execute_transaction(): Run multiple queries atomically
        
    Activity Logging:
        - log_agent_activity(): Log agent operations
        - _calculate_quality_score(): Calculate performance quality
        - _log_db_activity(): Track database operations
        
    Utilities:
        - _get_timestamp(): Timing utilities
        - check_handler_dependencies(): Dependency check
        - validate_handler(): Implementation validation
        - set_workspace_context(): Set workspace context

Usage:
    1. Inherit from BaseHandler
    2. Implement required methods
    3. Define handler-specific actions
    4. Use standard result types
    5. Handle cleanup properly
    6. Leverage centralized database operations
    7. Track activities for performance monitoring
"""

from dataclasses import dataclass
from typing import Optional, Any, Dict, List, Union, Tuple
import datetime
import json
import os
import uuid
import subprocess
import time
import sqlite3
import sys
import re
import inspect
import logging
import traceback
import hashlib

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Import agent-related components through the import helper instead of direct imports
try:
    from Jarvis_Agent_SDK import import_helper
    # These will be imported at runtime as needed, avoiding circular dependencies
except ImportError:
    # Allow the handler to function even if agent components can't be imported
    print("Warning: Agent components not available - specialized agent features disabled")


def osascript(script):
    """
    Execute AppleScript using osascript command.
    
    Args:
        script (str): The AppleScript to execute
        
    Returns:
        dict: A dictionary with the result or error message
    """
    try:
        result = subprocess.run(["osascript", "-e", script], capture_output=True, text=True)
        if result.returncode == 0:
            return {"result": result.stdout.strip()}
        else:
            return {"error": result.stderr.strip()}
    except Exception as e:
        return {"error": str(e)}


# Database proxy classes
class CursorProxy:
    """Proxy for a database cursor that tracks and logs SQL operations."""
    
    def __init__(self, db_manager, cursor=None):
        self.db_manager = db_manager
        self.cursor = cursor
        
    def execute(self, query, params=None):
        """Execute a SQL query and log it."""
        try:
            if params:
                result = self.cursor.execute(query, params)
            else:
                result = self.cursor.execute(query)
            # Log the successful operation
            self.db_manager._log_query("execute", query, params)
            return result
        except Exception as e:
            # Log the failed operation
            self.db_manager._log_query_error("execute", query, params, str(e))
            raise
            
    def executemany(self, query, params_list):
        """Execute a SQL query with multiple parameter sets and log it."""
        try:
            result = self.cursor.executemany(query, params_list)
            # Log the successful operation
            self.db_manager._log_query("executemany", query, f"{len(params_list)} parameter sets")
            return result
        except Exception as e:
            # Log the failed operation
            self.db_manager._log_query_error("executemany", query, f"{len(params_list)} parameter sets", str(e))
            raise
            
    def __getattr__(self, name):
        """Forward all other attributes to the underlying cursor."""
        return getattr(self.cursor, name)


class ConnectionProxy:
    """
    A proxy for database connection that intercepts operations.
    """
    def __init__(self, db_manager, connection=None):
        self.db_manager = db_manager
        self._connection = connection
        
    @property
    def connection(self):
        """Ensures connection is available before use."""
        if self._connection is None:
            # Initialize connection if not already done
            self._connection = self.db_manager.get_connection()
        return self._connection
        
    def cursor(self):
        """Create a cursor proxied for tracking SQL operations."""
        cursor = self.connection.cursor()
        return CursorProxy(self.db_manager, cursor)
        
    def __getattr__(self, name):
        """Forward all other attributes to the underlying connection."""
        return getattr(self.connection, name)


class DatabaseManager:
    """
    Manages database connections and operations with workspace-awareness
    and standardized logging. Uses delegation pattern to singleton DatabaseDirectory.
    """
    def __init__(self, handler, connection=None, db_path=None):
        self.handler = handler
        self.connection = connection
        self.db_path = db_path
        self.workspace_id = None

        # Database directory loaded lazily on first access to avoid triggering
        # the full init chain (spaCy, 80 DBs, etc.) during handler import
        self._db_directory = None
        self._db_directory_loaded = False

        # Initialize connection if we have a db_path
        if self.db_path and not self.connection:
            try:
                self.connection = self.get_connection()
                # Reduced logging - singleton handles initialization messages
            except Exception as e:
                print(f"Database initialization error: {str(e)}")

    def _get_db_name_from_path(self, db_path):
        """
        Map file paths to database names for singleton delegation.

        Args:
            db_path: File path to database

        Returns:
            Database name for singleton, or None if unmapped
        """
        if not db_path:
            return None

        # Normalize path and extract database name
        import os
        db_filename = os.path.basename(db_path)

        # Map common database files to singleton names
        path_mappings = {
            'trading_forex.db': 'trevor',
            'agents.db': 'boardroom',
            'handler_analysis.db': 'handler_analysis',
            'docstrings.db': 'docstrings',
            'intelligence.db': 'intelligence',
            'journeys.db': 'journey_tracking',
            'patterns.db': 'patterns',
            'conversation_archive.db': 'conversation_archive',
            'core.db': 'core',
            'workspaces.db': 'workspaces',
            'conversations.db': 'conversations',
        }

        return path_mappings.get(db_filename)
        
    def set_workspace_id(self, workspace_id):
        """Set the workspace ID for context-aware operations."""
        self.workspace_id = workspace_id
        
    def get_connection(self):
        """Get or create a database connection, delegating to singleton when possible."""
        try:
            if not self.db_path:
                raise ValueError("Database path not set")

            # Return existing connection if available
            if self.connection:
                return self.connection

            # Try to delegate to singleton first (lazy load)
            if not self._db_directory_loaded:
                self._db_directory_loaded = True
                try:
                    from Jarvis_Agent_SDK.database_directory import get_database_directory
                    self._db_directory = get_database_directory()
                except ImportError as e:
                    pass
            if self._db_directory:
                db_name = self._get_db_name_from_path(self.db_path)
                if db_name:
                    try:
                        # Use singleton connection (no duplicate logging)
                        connection = self._db_directory.get_connection(db_name)
                        if connection:
                            return connection
                    except Exception as singleton_error:
                        print(f"Singleton delegation failed for {db_name}: {singleton_error}")

            # Fallback to direct SQLite connection for unmapped databases
            connection = sqlite3.connect(self.db_path, check_same_thread=False, timeout=30, isolation_level=None)
            connection.row_factory = sqlite3.Row
            connection.execute("PRAGMA busy_timeout = 30000")
            connection.execute("PRAGMA journal_mode=DELETE")
            # Only log for unmapped databases
            db_name = self._get_db_name_from_path(self.db_path)
            if not db_name:
                print(f"Direct connection to unmapped database: {self.db_path}")

            return connection
        except Exception as e:
            print(f"Error connecting to database: {str(e)}")
            # Handle unmapped database paths
            if not self._get_db_name_from_path(self.db_path):
                print(f"Warning: Unmapped database path: {self.db_path}")
            # Try in-memory database as fallback
            try:
                print("Attempting in-memory database fallback")
                connection = sqlite3.connect(":memory:", check_same_thread=False, isolation_level=None)
                connection.row_factory = sqlite3.Row
                print("Successfully created in-memory database fallback")
                return connection
            except Exception as fallback_error:
                print(f"Even in-memory database failed: {fallback_error}")
                return None
        
    def execute_query(self, sql, params=None, workspace_id=None):
        """
        Execute an SQL query with workspace context.
        
        Args:
            sql: SQL query to execute
            params: Query parameters
            workspace_id: Optional workspace ID context
            
        Returns:
            Cursor object for the query
        """
        conn = self.get_connection()
        if not conn:
            # Try to reinitialize connection before giving up
            try:
                if self.db_path:
                    self.connection = sqlite3.connect(self.db_path, check_same_thread=False, isolation_level=None)
                    self.connection.row_factory = sqlite3.Row
                    conn = self.connection
                    print(f"Successfully reinitialized database connection to {self.db_path}")
                else:
                    self.connection = sqlite3.connect(":memory:", check_same_thread=False, isolation_level=None)
                    self.connection.row_factory = sqlite3.Row
                    conn = self.connection
                    print("Successfully reinitialized in-memory database connection")
            except Exception as e:
                print(f"Failed to reinitialize database connection: {e}")
                raise Exception("No database connection available and failed to reinitialize")
            
        # Use provided workspace ID or default
        workspace = workspace_id or self.workspace_id
        
        # Apply workspace filtering for SELECT queries if workspace is specified
        if workspace and sql.strip().upper().startswith("SELECT"):
            # Check if workspace filtering is applicable
            if any(table in sql.lower() for table in [
                "workspace_", "team_", "user_", "agent_performance", 
                "agent_metrics", "workspace_activity"
            ]):
                # Add workspace filter if not already present
                if "WHERE" in sql.upper():
                    if f"workspace_id = {workspace}" not in sql and "workspace_id = ?" not in sql:
                        sql = sql.replace("WHERE", f"WHERE workspace_id = {workspace} AND ", 1)
                else:
                    # Add WHERE clause if not present
                    sql = f"{sql} WHERE workspace_id = {workspace}"
        
        # Set a longer timeout for the SQLite connection to handle locks
        conn.execute("PRAGMA busy_timeout = 30000")  # 30 second timeout
        
        cursor = conn.cursor()
        max_retries = 3
        retry_delay = 0.5  # seconds
        
        for retry in range(max_retries):
            try:
                if params:
                    result = cursor.execute(sql, params)
                else:
                    result = cursor.execute(sql)
                return result
            except sqlite3.OperationalError as e:
                # Handle database lock errors with retries
                if "database is locked" in str(e) and retry < max_retries - 1:
                    import time
                    print(f"Database locked, retry {retry+1}/{max_retries}")
                    time.sleep(retry_delay * (retry + 1))  # Exponential backoff
                    continue
                else:
                    print(f"Error executing query: {str(e)}")
                    raise
            except Exception as e:
                print(f"Error executing query: {str(e)}")
                raise
            
    def query_with_result(self, sql, params=None, workspace_id=None):
        """
        Execute a query and return the result rows.
        
        Args:
            sql: SQL query to execute
            params: Query parameters
            workspace_id: Optional workspace ID context
            
        Returns:
            List of result rows
        """
        cursor = self.execute_query(sql, params, workspace_id)
        return cursor.fetchall()
        
    def insert(self, table, data, workspace_id=None):
        """
        Insert data into a table.
        
        Args:
            table: Table name
            data: Dictionary of column:value pairs
            workspace_id: Optional workspace ID context
            
        Returns:
            ID of the inserted row
        """
        # Add workspace_id if applicable and not already in data
        if workspace_id and "workspace_id" not in data and any(table.startswith(prefix) for prefix in [
            "workspace_", "team_", "agent_", "activity"
        ]):
            data["workspace_id"] = workspace_id
            
        columns = ", ".join(data.keys())
        placeholders = ", ".join(["?"] * len(data))
        values = list(data.values())
        
        sql = f"INSERT INTO {table} ({columns}) VALUES ({placeholders})"
        
        cursor = self.execute_query(sql, values)
        self.get_connection().commit()
        
        return cursor.lastrowid
        
    def update(self, table, data, condition, params=None, workspace_id=None):
        """
        Update data in a table.
        
        Args:
            table: Table name
            data: Dictionary of column:value pairs to update
            condition: WHERE condition string
            params: Parameters for the condition
            workspace_id: Optional workspace ID context
            
        Returns:
            Number of rows affected
        """
        set_clause = ", ".join([f"{column} = ?" for column in data.keys()])
        values = list(data.values())
        
        # Add workspace context to condition if applicable
        if workspace_id and "workspace_id" not in condition:
            if condition:
                condition = f"workspace_id = {workspace_id} AND ({condition})"
            else:
                condition = f"workspace_id = {workspace_id}"
                
        sql = f"UPDATE {table} SET {set_clause} WHERE {condition}"
        
        if params:
            values.extend(params)
            
        cursor = self.execute_query(sql, values)
        self.get_connection().commit()
        
        return cursor.rowcount
        
    def delete(self, table, condition, params=None, workspace_id=None):
        """
        Delete data from a table.
        
        Args:
            table: Table name
            condition: WHERE condition string
            params: Parameters for the condition
            workspace_id: Optional workspace ID context
            
        Returns:
            Number of rows affected
        """
        # Add workspace context to condition if applicable
        if workspace_id and "workspace_id" not in condition:
            if condition:
                condition = f"workspace_id = {workspace_id} AND ({condition})"
            else:
                condition = f"workspace_id = {workspace_id}"
                
        sql = f"DELETE FROM {table} WHERE {condition}"
            
        cursor = self.execute_query(sql, params)
        self.get_connection().commit()
        
        return cursor.rowcount
        
    def execute_transaction(self, queries):
        """
        Execute multiple queries in a transaction.
        
        Args:
            queries: List of (sql, params) tuples
            
        Returns:
            True if successful, False otherwise
        """
        conn = self.get_connection()
        if not conn:
            # Try to reinitialize connection before giving up
            try:
                if self.db_path:
                    self.connection = sqlite3.connect(self.db_path, check_same_thread=False, isolation_level=None)
                    self.connection.row_factory = sqlite3.Row
                    conn = self.connection
                    print(f"Successfully reinitialized database connection to {self.db_path}")
                else:
                    self.connection = sqlite3.connect(":memory:", check_same_thread=False, isolation_level=None)
                    self.connection.row_factory = sqlite3.Row
                    conn = self.connection
                    print("Successfully reinitialized in-memory database connection")
            except Exception as e:
                print(f"Failed to reinitialize database connection: {e}")
                raise Exception("No database connection available and failed to reinitialize")
            
        try:
            conn.execute("BEGIN TRANSACTION")
            
            for sql, params in queries:
                if params:
                    conn.execute(sql, params)
                else:
                    conn.execute(sql)
                    
            conn.commit()
            return True
        except Exception as e:
            conn.rollback()
            print(f"Transaction failed: {str(e)}")
            return False

    def _log_query(self, operation, query, params=None):
        """Log successful database operations."""
        if self.handler:
            # Create a standardized log entry
            log_entry = {
                "operation": operation,
                "query": query,
                "params": str(params) if params else None,
                "status": "success",
                "timestamp": datetime.datetime.now().isoformat()
            }
            
            # Skip DB activity logging to avoid circular imports
            # Just log to terminal for debugging
            if operation in ["insert", "update", "delete", "transaction"]:
                print(f"DB {operation.upper()}: {query[:100]}{'...' if len(query) > 100 else ''}")
    
    def _log_query_error(self, operation, query, params=None, error=None):
        """Log failed database operations."""
        if self.handler:
            # Create a standardized error log entry
            log_entry = {
                "operation": operation,
                "query": query,
                "params": str(params) if params else None,
                "status": "error",
                "error": str(error),
                "timestamp": datetime.datetime.now().isoformat()
            }
            
            # Skip DB activity logging to avoid circular imports
            # Just log to terminal for debugging
            print(f"DB ERROR ({operation.upper()}): {error} - {query[:100]}{'...' if len(query) > 100 else ''}")


@dataclass
class HandlerResult:
    """Result data structure for handler operations."""
    success: bool = False
    data: Any = None
    error: Optional[str] = None
    message: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the result to a dictionary for JSON serialization."""
        return {
            "success": self.success,
            "data": self.data,
            "error": self.error,
            "message": self.message,
            "metadata": self.metadata
        }
    
    def __str__(self) -> str:
        """String representation for debugging and logging."""
        return f"HandlerResult(success={self.success}, data={self.data}, error={self.error}, message={self.message})"


class BaseHandler:
    """Base class for all handlers."""
    
    REQUIRED_MODELS = []  # List of required model dependencies
    
    def __init__(self, app_name=None, app_version=None, db_path=None):
        """Initialize the base handler with common functionality.
        
        Args:
            app_name: Name of the app/handler
            app_version: Version of the app/handler
            db_path: Path to the database file
        """
        # Store basic handler info
        self.app_name = app_name
        self.app_version = app_version
        
        # Default to Unknown or empty values if not provided
        if self.app_name is None:
            self.app_name = self.__class__.__name__
        
        # Set board_room and boardroom to None - other components should initialize them
        # We avoid initializing them here to prevent circular imports
        self.board_room = None
        self.boardroom = None
        
        # Initialize error counters
        self.errors = 0
        self.last_error = None
        
        # Initialize database manager
        self.db_manager = DatabaseManager(handler=self, db_path=db_path)
        
        # Initialize connection proxy for direct SQL 
        if hasattr(self, 'db') and self.db is not None:
            # If there's an existing db connection, proxy it
            self.db = ConnectionProxy(self.db_manager, self.db)
        else:
            # Create a new connection proxy
            self.db = ConnectionProxy(self.db_manager)
        
        self.active_objects = []
        self.session_id = None
        self.last_action = None
        self.last_parameters = None
        self.last_result = None
        self.app_objects = {}  # Track objects created within this app
        self.handler_name = self.__class__.__name__
        
        # Database standardization
        self.use_standardized_db = True
            
    def set_session(self, session_id):
        """Set the session ID for this handler."""
        self.session_id = session_id
    
    def get_active_objects(self):
        """Get active objects for this handler."""
        if self.session_id:
            try:
                from Jarvis_Agent_SDK.conversation_history import conversation_history
                return conversation_history.get_objects_for_handler(self.session_id, self.app_name or self.handler_name)
            except Exception as e:
                print(f"Error getting active objects: {e}")
        return []
        
    def _log_db_activity(self, sql, params=None):
        """
        Log database activity for monitoring and debugging.
        
        Args:
            sql: SQL statement being executed
            params: Query parameters
        """
        # Don't log certain common/trivial queries
        if sql in ("COMMIT", "ROLLBACK", "BEGIN TRANSACTION"):
            return
            
        # Mask sensitive information in query params
        safe_params = params
        if params and isinstance(params, (list, tuple)):
            # Only show first few and last few elements if large
            if len(params) > 10:
                safe_params = params[:3] + ["..."] + params[-3:]
                
        # Determine operation type
        op_type = "unknown"
        if sql.strip().upper().startswith("SELECT"):
            op_type = "query"
        elif sql.strip().upper().startswith("INSERT"):
            op_type = "insert"
        elif sql.strip().upper().startswith("UPDATE"):
            op_type = "update" 
        elif sql.strip().upper().startswith("DELETE"):
            op_type = "delete"
        
        # Log the activity if detailed logging enabled
        if hasattr(self, 'verbose_logging') and self.verbose_logging:
            print(f"DB {op_type}: {sql[:100]}{'...' if len(sql) > 100 else ''} - Params: {safe_params}")
            
    def set_workspace_context(self, workspace_id):
        """
        Set the workspace context for database operations.
        
        Args:
            workspace_id: ID of the workspace
        """
        self.db_manager.set_workspace_id(workspace_id)
        
    def execute_action(self, action, parameters=None):
        """
        Execute an action with proper session tracking and continuity support.
        
        Args:
            action: The action to execute
            parameters: Parameters for the action
            
        Returns:
            dict: Result of the operation
        """
        start_time = time.time()
        success = True
        error_count = 0
        error_message = None

        try:
            if not parameters:
                parameters = {}
            
            # Check if this is a continuation
            if parameters.get('continuation'):
                # Get the original object
                object_id = parameters.get('object_id')
                if object_id and self.session_id:
                    try:
                        from Jarvis_Agent_SDK.conversation_history import conversation_history
                        original_object = conversation_history.get_object(self.session_id, object_id)
                        if original_object:
                            # Add original object's metadata to parameters
                            parameters['original_metadata'] = original_object.get('metadata', {})
                    except Exception as e:
                        print(f"Error getting original object: {e}")
            
            # Execute the specific action
            if hasattr(self, action):
                result = getattr(self, action)(**parameters)
                
                # If successful and we have a session, update the object
                if result.get('success') and self.session_id and parameters.get('object_id'):
                    try:
                        from Jarvis_Agent_SDK.conversation_history import conversation_history
                        conversation_history.update_object(
                            self.session_id,
                            parameters['object_id'],
                            {
                                "last_accessed": datetime.datetime.now().isoformat(),
                                "metadata": {
                                    **parameters.get('original_metadata', {}),
                                    "last_action": action,
                                    "last_parameters": parameters
                                }
                            }
                        )
                    except Exception as e:
                        print(f"Error updating object: {e}")
                
                return result
            else:
                success = False
                error_count = 1
                error_message = f"Action {action} not found"
                return {"success": False, "message": error_message}
            
        except Exception as e:
            success = False
            error_count = 1
            error_message = str(e)
            return {"success": False, "message": f"Error executing action: {error_message}"}
        finally:
            # Only log if we're not in a handler that already implements log_agent_activity
            # Check if the class has implemented its own log_agent_activity method
            has_custom_logging = False
            for cls in self.__class__.__mro__:
                if cls.__name__ not in ['BaseHandler', 'object'] and hasattr(cls, 'log_agent_activity') and cls.log_agent_activity.__module__ != BaseHandler.log_agent_activity.__module__:
                    has_custom_logging = True
                    break
                
            # Skip logging for handlers with known custom implementations
            handler_classes_with_custom_logging = [
                'SwarmHandler',
                'DataValidatorHandler',
                'AgentBuilder',
                'BoardRoom',
                'StructuredOutputsSystem'
            ]
            
            if self.__class__.__name__ in handler_classes_with_custom_logging:
                has_custom_logging = True
                
            if not has_custom_logging:
                # Log the activity regardless of success/failure
                completion_time = time.time() - start_time
                
                # Try to get agent info from context or generate it
                try:
                    # Get agent information - either from parameters or generate it
                    agent_id = parameters.get('agent_id', f"{self.handler_name}_{int(time.time())}")
                    agent_name = parameters.get('agent_name', f"{self.handler_name.capitalize()} Handler Agent")
                    agent_type = parameters.get('agent_type', self.handler_name)
                    workspace_id = parameters.get('workspace_id', 1)  # Default workspace
                    
                    # Build activity details
                    details = {
                        "action": action,
                        "handler": self.handler_name,
                        "app_name": self.app_name,
                    }
                    
                    # Add safe parameters (filter out potential sensitive info)
                    safe_params = {}
                    for key, value in parameters.items():
                        if key not in ['password', 'api_key', 'secret', 'token', 'credentials']:
                            # Truncate long values
                            if isinstance(value, str) and len(value) > 100:
                                safe_params[key] = value[:100] + "..."
                            else:
                                safe_params[key] = value
                    
                    details["parameters"] = safe_params
                    
                    # If there was an error, add error details
                    if not success:
                        details["error"] = error_message
                    
                    # Build performance metrics
                    performance_metrics = {
                        "success": success,
                        "completion_time": completion_time,
                        "error_count": error_count
                    }
                    
                    # Try to log the agent activity directly using track_journey_step_sync
                    try:
                        # We don't need BoardRoom for this anymore
                        # Just use the method directly
                        import asyncio
                        asyncio.create_task(self.log_agent_activity(
                            agent_id=agent_id,
                            agent_name=agent_name,
                            agent_type=agent_type,
                            workspace_id=workspace_id,
                            action_type=action,
                            details=details,
                            performance_metrics=performance_metrics
                        ))
                    except Exception as e:
                        # Don't let logging errors affect the main execution flow
                        pass
                except Exception as logging_error:
                    # Don't let logging errors affect the main execution flow
                    pass
    
    def _handle_error(self, action, message, details=None):
        if details is None:
            details = {}
        details["action_name"] = action
        
        error_info = {
            "action": action,
            "timestamp": self._get_timestamp(),
            "message": message,
            "details": details
        }
        
        return {"success": False, "message": message, "error_info": error_info}
    
    def _get_timestamp(self) -> str:
        """Get a formatted timestamp string."""
        return datetime.datetime.now().isoformat()
        
    async def handle(self, task_description: Dict) -> HandlerResult:
        """Base handle method that all handlers should implement."""
        raise NotImplementedError("Handlers must implement handle method")
        
    def create_success_result(self, data: Any = None, metadata: Dict = None) -> HandlerResult:
        """Create a successful result."""
        if metadata is None:
            metadata = {}
            
        # Add handler information to metadata
        metadata.update({
            "handler_name": self.handler_name,
            "app_name": self.app_name,
            "timestamp": self._get_timestamp(),
        })
        
        result = HandlerResult(
            success=True,
            data=data,
            metadata=metadata
        )
        
        # Update the last result
        self.last_result = result
        
        return result
        
    def create_error_result(self, error: str, metadata: Dict = None) -> HandlerResult:
        """Create an error result."""
        if metadata is None:
            metadata = {}
            
        # Add handler information to metadata
        metadata.update({
            "handler_name": self.handler_name,
            "app_name": self.app_name,
            "timestamp": self._get_timestamp(),
        })
        
        result = HandlerResult(
            success=False,
            error=error,
            metadata=metadata
        )
        
        # Update the last result
        self.last_result = result
        
        return result
        
    async def execute(self, action: str, parameters: Dict) -> HandlerResult:
        """Execute a specific action with parameters."""
        start_time = time.time()
        success = True
        error_count = 0
        error_message = None
        
        try:
            # Store the action and parameters
            self.last_action = action
            self.last_parameters = parameters
            
            if hasattr(self, action):
                method = getattr(self, action)
                result = await method(**parameters)
                
                # If this is a successful creation of some object, track it
                if result.success and action.startswith(("create", "compose", "open")):
                    self._track_created_object(action, parameters, result)
                
                # Check if result was successful
                if not result.success:
                    success = False
                    error_count = 1
                    error_message = result.error if hasattr(result, 'error') else "Action failed"
                    
                return result
            else:
                success = False
                error_count = 1
                error_message = f"Action {action} not found"
                return self.create_error_result(error_message)
        except Exception as e:
            success = False
            error_count = 1
            error_message = str(e)
            return self.create_error_result(error_message)
        finally:
            # Only log if we're not in a handler that already implements log_agent_activity
            # Check if the class has implemented its own log_agent_activity method
            has_custom_logging = False
            for cls in self.__class__.__mro__:
                if cls.__name__ not in ['BaseHandler', 'object'] and hasattr(cls, 'log_agent_activity') and cls.log_agent_activity.__module__ != BaseHandler.log_agent_activity.__module__:
                    has_custom_logging = True
                    break
                
            # Skip logging for handlers with known custom implementations
            handler_classes_with_custom_logging = [
                'SwarmHandler',
                'DataValidatorHandler',
                'AgentBuilder',
                'BoardRoom',
                'StructuredOutputsSystem'
            ]
            
            if self.__class__.__name__ in handler_classes_with_custom_logging:
                has_custom_logging = True
                
            if not has_custom_logging:
                # Log the activity regardless of success/failure
                completion_time = time.time() - start_time
                
                # Try to get agent info from context or generate it
                try:
                    # Get agent information - either from parameters or generate it
                    agent_id = parameters.get('agent_id', f"{self.handler_name}_{int(time.time())}")
                    agent_name = parameters.get('agent_name', f"{self.handler_name.capitalize()} Handler Agent")
                    agent_type = parameters.get('agent_type', self.handler_name)
                    workspace_id = parameters.get('workspace_id', 1)  # Default workspace
                    
                    # Build activity details
                    details = {
                        "action": action,
                        "handler": self.handler_name,
                        "app_name": self.app_name,
                    }
                    
                    # Add safe parameters (filter out potential sensitive info)
                    safe_params = {}
                    for key, value in parameters.items():
                        if key not in ['password', 'api_key', 'secret', 'token', 'credentials']:
                            # Truncate long values
                            if isinstance(value, str) and len(value) > 100:
                                safe_params[key] = value[:100] + "..."
                            else:
                                safe_params[key] = value
                    
                    details["parameters"] = safe_params
                    
                    # If there was an error, add error details
                    if not success:
                        details["error"] = error_message
                    
                    # Build performance metrics
                    performance_metrics = {
                        "success": success,
                        "completion_time": completion_time,
                        "error_count": error_count
                    }
                    
                    # Get quality score if available
                    if hasattr(self, '_calculate_quality_score'):
                        try:
                            quality_score = self._calculate_quality_score(success, error_count, completion_time)
                            performance_metrics["quality_score"] = quality_score
                        except:
                            pass
                    
                    # Log the activity directly without relying on boardroom
                    try:
                        import asyncio
                        asyncio.create_task(self.log_agent_activity(
                            agent_id=agent_id,
                            agent_name=agent_name,
                            agent_type=agent_type,
                            workspace_id=workspace_id,
                            action_type=action,
                            details=details,
                            performance_metrics=performance_metrics
                        ))
                    except Exception:
                        # Don't let logging errors affect the main execution flow
                        pass
                except Exception:
                    # Don't let logging errors affect the main execution flow
                    pass
    
    def _track_created_object(self, action: str, parameters: Dict, result: HandlerResult) -> None:
        """
        Track an object that was created by this handler.
        
        Args:
            action: The action that created the object
            parameters: The parameters used to create the object
            result: The result of the creation action
        """
        # Only track successful creations
        if not result.success:
            return
            
        # Skip if app_name isn't set (would be unusual)
        if not self.app_name:
            return
            
        # Generate an object ID based on action and parameters
        import hashlib
        param_str = json.dumps(parameters, sort_keys=True)
        object_id = hashlib.md5(f"{action}:{param_str}:{self._get_timestamp()}".encode()).hexdigest()[:12]
        
        # Determine object type dynamically based on action and app_name
        object_type = action.replace("_", " ")  # Default to the action name
        object_name = f"{self.app_name} {object_type}"
        
        # Extract better object names from parameters when possible
        if parameters:
            # Try to find the most relevant parameter for naming
            name_keys = ['name', 'title', 'subject', 'recipient', 'filename', 'path', 'url', 'id']
            for key in name_keys:
                if key in parameters and parameters[key]:
                    object_name = f"{object_type}: {parameters[key]}"
                    break
        
        # Store in local tracking
        self.app_objects[object_id] = {
            "object_id": object_id,
            "object_type": object_type,
            "object_name": object_name,
            "action": action,
            "parameters": parameters,
            "created_at": self._get_timestamp(),
            "app_name": self.app_name
        }
        
        # Also track in session history if available
        if self.session_id:
            try:
                from Jarvis_Agent_SDK.conversation_history import conversation_history
                conversation_history.track_object(
                    session_id=self.session_id,
                    object_id=object_id,
                    object_name=object_name,
                    object_type=object_type,
                    app_name=self.app_name,
                    status="active",
                    metadata={
                        "action": action,
                        "parameters": parameters,
                        "created_at": self._get_timestamp()
                    }
                )
            except Exception as e:
                print(f"Error tracking object: {e}")
                
    @staticmethod
    def check_handler_dependencies() -> tuple[bool, List[str]]:
        """
        Check if all required dependencies for this handler are available.
        
        Returns:
            (bool, List[str]): Success flag and list of missing dependencies
        """
        try:
            # Check basic Python dependencies
            import sqlite3
            import datetime
            import json
            
            # Success, no missing dependencies
            return True, []
        except ImportError as e:
            module_name = str(e).split("'")[1] if "'" in str(e) else str(e)
            return False, [module_name]
        except Exception:
            return False, ["Error checking dependencies"]
    
    # BoardRoom initialization should be handled by the BoardRoom connector or specific handlers
    # BaseHandler shouldn't be responsible for this to avoid circular dependencies
            
    async def log_agent_activity(self, agent_id: str, agent_name: str, agent_type: str, 
                         workspace_id: int, action_type: str, details: Dict = None,
                         performance_metrics: Dict = None) -> bool:
        """
        Log agent activity - simplified implementation to avoid circular imports.
        
        This method doesn't use BoardRoom directly but tries to use boardroom_connector.
        
        Args:
            agent_id: ID of the agent
            agent_name: Name of the agent
            agent_type: Type of agent
            workspace_id: ID of the workspace
            action_type: Type of action performed
            details: Details about the action
            performance_metrics: Performance metrics of the action
            
        Returns:
            True if logging was successful, False otherwise
        """
        try:
            # Use dynamic import to avoid circular dependencies
            import importlib
            
            # Try to use track_journey_step_sync from boardroom_connector directly
            try:
                connector = importlib.import_module("Jarvis_Agent_SDK.boardroom_connector")
                track_journey_step_sync = getattr(connector, "track_journey_step_sync", None)
                
                if track_journey_step_sync:
                    # Create journey ID based on agent and timestamp
                    journey_id = f"agent_{agent_id}_{int(time.time())}"
                    
                    # Track using the connector's function directly
                    track_journey_step_sync(
                        journey_id=journey_id,
                        step_type="agent_activity",
                        step_name=f"{agent_type}_{action_type}",
                        description=f"Agent {agent_name} performed {action_type}",
                        input_data={"agent_id": agent_id, "agent_type": agent_type},
                        output_data=details,
                        metadata=performance_metrics
                    )
                    return True
            except Exception as e:
                # Just silently fail and return True to avoid disrupting caller
                pass
                
            return True
        except Exception:
            # Don't let errors in logging affect the calling code
            return True
 
    def _calculate_quality_score(self, success: bool, error_count: int, 
                                completion_time: float, 
                                base_score: float = 0.9) -> float:
        """
        Calculate a quality score for an operation based on success, errors, and time.
        
        Args:
            success: Whether the operation was successful
            error_count: Number of errors encountered
            completion_time: Time taken to complete the operation
            base_score: Base quality score for successful operations
            
        Returns:
            float: Quality score between 0.0 and 1.0
        """
        if not success:
            # Failed operations get a quality score based on error count
            # More errors = lower score, but never below 0.1
            return max(0.5 - (error_count * 0.1), 0.1)
            
        # Start with the base score for successful operations
        quality = base_score
        
        # Adjust for completion time - penalize slow operations
        # This is very application-specific and may need tuning
        if completion_time > 10.0:  # More than 10 seconds
            quality -= min((completion_time - 10.0) / 100.0, 0.2)  # Max penalty of 0.2 for time
            
        # Adjust for error count - even successful operations may have recoverable errors
        quality -= min(error_count * 0.05, 0.3)  # Max penalty of 0.3 for errors
        
        # Ensure quality is between 0.0 and 1.0
        return max(min(quality, 1.0), 0.0)

def validate_handler(handler_class) -> tuple[bool, str]:
    """Validate a handler class implementation."""
    try:
        # Special case for BoardRoom which uses bridge pattern, not inheritance
        if handler_class.__name__ == "BoardRoom":
            print("⚠️ BoardRoom uses bridge pattern with TrevorCore, not BaseHandler inheritance")
            print("⚠️ This is by design to avoid circular dependencies")
            return True, "BoardRoom is valid using bridge pattern"
            
        # Check if the class inherits from BaseHandler
        if not issubclass(handler_class, BaseHandler):
            return False, "Handler class must inherit from BaseHandler"
            
        # Check if all required methods are implemented
        instance = handler_class()
        
        # Check if handle method is implemented
        if not hasattr(instance, "handle") or instance.handle.__func__ is BaseHandler.handle:
            return False, "Handler class must implement the handle method"
            
        # Check if app_name is set
        if not instance.app_name:
            return False, "Handler app_name must be set in __init__"
            
        # Check if handler_name is set
        if not instance.handler_name:
            return False, "Handler handler_name must be set in __init__"
            
        # Check dependencies
        deps_ok, missing_deps = instance.check_handler_dependencies()
        if not deps_ok:
            deps_str = ", ".join(missing_deps)
            return False, f"Handler is missing dependencies: {deps_str}"
            
        # All checks passed
        return True, "Handler implementation is valid"
        
    except Exception as e:
        return False, f"Error validating handler: {str(e)}" 