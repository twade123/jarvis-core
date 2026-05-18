"""
Database Directory Service for Jarvis Orchestrator Intelligence

This module provides a unified interface for the orchestrator intelligence to discover
and access data across multiple databases without having to search through everything.
It creates a directory of available databases, tables, and their schemas to allow
efficient data access and querying.
"""

import os
import sqlite3
import logging
import json
import time
import hashlib
import io
import types
import traceback
import threading
from typing import Dict, List, Any, Optional, Union, Tuple
from Database.v2.db_helper import connection as v2_connection
from datetime import datetime

# Lazy imports for heavy libraries — only loaded when actually needed
# torch and numpy are only used in load_pytorch_model() and import_best_model_to_trevor()
_torch = None
_np = None

def _get_torch():
    global _torch
    if _torch is None:
        import torch
        _torch = torch
    return _torch

def _get_numpy():
    global _np
    if _np is None:
        import numpy as np
        _np = np
    return _np

# Initialize logger
logger = logging.getLogger(__name__)

# Default paths to key databases
DEFAULT_DB_PATHS = {
    "handler_analysis": "~/Jarvis/Handler/handler_analysis.db",
    "handler_tracking": "~/Jarvis/Database/handler_tracking.db",
    "trevor_database": "~/Jarvis/Database/v2/trading_forex.db",
    "intelligence": "~/Jarvis/Database/v2/intelligence.db",
    "docstrings": "~/Jarvis/docstrings.db",
    "boardroom": "~/Jarvis/Database/v2/agents.db",
    "journey_tracking": "~/Jarvis/Database/v2/journeys.db"
}

# Map important tables to their primary database locations
PRIORITY_TABLE_LOCATIONS = {
    # Handler-related tables
    "handlers": "handler_analysis",
    "handler_patterns": "handler_analysis",
    "intent_mappings": "handler_analysis",
    "handler_performance": "handler_tracking",
    "handler_execution_tracking": "handler_tracking",
    "handler_error_patterns": "boardroom",
    "handler_parameter_patterns": "boardroom",
    "handler_related_actions": "boardroom",
    "handler_data": "boardroom",
    
    # Agent registry tables
    "agent_registry": "boardroom",
    "agent_performance": "boardroom",
    "orchestrator_agent_performance": "boardroom",
    "agent_version_history": "boardroom",
    
    # Handler analysis tables in trevor_database
    "handler_analysis": "trevor_database",
    "handler_analyzer": "trevor_database",
    "handler_processing_history": "trevor_database",
    "handler_training_data": "trevor_database",
    
    # Intelligence-related tables
    "request_mapping": "intelligence",
    "agent_capabilities": "intelligence",
    "agent_performance": "intelligence",
    "intent_patterns": "intelligence",
    
    # Trevor-related tables
    "model_storage": "trevor_database",
    "pattern_data": "trevor_database",
    "training_data": "trevor_database",
    
    # Docstring-related tables
    "docstrings": "docstrings",
    "semantic_relationships": "docstrings",
    "method_similarities": "docstrings",
    
    # Journey tracking tables
    "request_journeys": "journey_tracking",
    "journey_steps": "journey_tracking"
}

class DatabaseDirectory:
    """
    Directory service that maps database locations, tables, and schemas
    to provide unified data access for the orchestrator intelligence.
    Thread-safe with per-thread connection pools.
    """

    def __init__(self):
        """Initialize the database directory service."""
        self.directory = {}
        # Thread-local storage for database connections
        self._thread_local = threading.local()
        self.table_mappings = {}
        self.prioritized_sources = {}
        self._cache = {}
        self._cache_timestamps = {}
        self.initialized = False
        self.model_cache = {}
        self.pattern_cache = {}
        self._connection_lock = threading.Lock()

        # Set base directory and primary database paths immediately
        # so they're available even before initialize() is called
        self.base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.primary_db_paths = {
            "trevor": os.path.join(self.base_dir, "Database", "v2", "trading_forex.db"),
            "handler_analysis": os.path.join(self.base_dir, "Handler", "handler_analysis.db"),
            "docstrings": os.path.join(self.base_dir, "docstrings.db"),
            "intelligence": os.path.join(self.base_dir, "Database", "intelligence.db")
        }

    def _get_thread_connections(self):
        """Get database connections for the current thread."""
        if not hasattr(self._thread_local, 'database_connections'):
            self._thread_local.database_connections = {}
            logger.info(f"Created new database connection pool for thread {threading.current_thread().ident}")
        return self._thread_local.database_connections

    def initialize(self):
        """Initialize the database directory with thread-safe connection pools."""
        if self.initialized:
            return

        # Device selection deferred — only needed for model operations
        self._device = None

        # Initialize primary databases (base_dir and primary_db_paths already set in __init__)
        self._initialize_primary_databases()
        self.initialized = True
        
    def _patch_sqlite_connections(self):
        """
        Since we can't directly patch the sqlite3.Connection class (it's immutable),
        we'll create a wrapper class around it and use that for our connections.
        """
        try:
            # Create a connection wrapper class
            class ConnectionWrapper:
                """Wrapper for sqlite3.Connection that adds execute_query method."""
                
                def __init__(self, connection):
                    """Initialize with an existing connection."""
                    self.connection = connection
                    # Copy the row_factory from the original connection
                    if hasattr(connection, 'row_factory'):
                        self.row_factory = connection.row_factory
                
                def __getattr__(self, name):
                    """Delegate attribute access to the wrapped connection."""
                    return getattr(self.connection, name)
                
                def cursor(self):
                    """Get a cursor from the wrapped connection."""
                    return self.connection.cursor()
                
                def commit(self):
                    """Commit changes to the wrapped connection."""
                    return self.connection.commit()
                
                def close(self):
                    """Close the wrapped connection."""
                    return self.connection.close()
                
                def execute_query(self, query, params=None, target_table=None, target_db=None):
                    """
                    Execute a SQL query and return the results.
                    
                    Args:
                        query: SQL query to execute
                        params: Optional query parameters
                        target_table: Ignored (for compatibility)
                        target_db: Ignored (for compatibility)
                        
                    Returns:
                        For SELECT queries: List of dictionaries representing result rows
                        For other queries: None
                    """
                    try:
                        cursor = self.connection.cursor()
                        
                        # Execute the query
                        try:
                            if params:
                                cursor.execute(query, params)
                            else:
                                cursor.execute(query)
                        except sqlite3.IntegrityError as integrity_error:
                            # Specifically for the request_mapping UNIQUE constraint
                            if "UNIQUE constraint failed: request_mapping.request_hash" in str(integrity_error):
                                # Just log the constraint violation and let caller handle it
                                logger.warning("UNIQUE constraint for request_mapping.request_hash - this should be handled by caller")
                            # Let IntegrityError propagate up for handling by caller
                            raise
                        
                        # Get results for SELECT queries
                        if query.strip().upper().startswith("SELECT"):
                            try:
                                # For SELECT queries, fetch all results and convert to a list of dicts
                                rows = cursor.fetchall()
                                results = []
                                
                                for row in rows:
                                    try:
                                        if isinstance(row, sqlite3.Row):
                                            # Convert sqlite3.Row to dict
                                            results.append(dict(row))
                                        else:
                                            # Keep as is if not a sqlite3.Row
                                            results.append(row)
                                    except Exception as row_error:
                                        logger.warning(f"Error converting row to dict: {str(row_error)}")
                                        # Add row as-is if conversion fails
                                        results.append(row)
                                
                                return results  # Always return a list, never a cursor
                            except sqlite3.Error as se:
                                logger.warning(f"SQLite error fetching results: {str(se)}")
                                return []
                            except Exception as fetch_error:
                                logger.warning(f"Error fetching results: {str(fetch_error)}")
                                return []
                        
                        # Commit for non-SELECT queries
                        if query.strip().upper().startswith(("INSERT", "UPDATE", "DELETE", "CREATE", "ALTER", "DROP")):
                            self.connection.commit()
                        
                        # Return empty list for non-SELECT queries to maintain consistent return type
                        return []
                    except Exception as e:
                        logger.error(f"Error in execute_query: {str(e)}")
                        logger.debug(traceback.format_exc())
                        return []  # Return empty list rather than None on error
            
            # Store the wrapper class so we can use it later
            self._connection_wrapper_class = ConnectionWrapper
            logger.info("Created ConnectionWrapper class with execute_query method")
            
        except Exception as e:
            logger.error(f"Error creating connection wrapper: {str(e)}")
            logger.debug(traceback.format_exc())

    def _initialize_primary_databases(self):
        """Initialize connections to primary databases."""
        for db_name, db_path in self.primary_db_paths.items():
            if os.path.exists(db_path):
                try:
                    # Use the _get_db_connection method to get a wrapped connection
                    conn = self._get_db_connection(db_path)
                    
                    self.directory[db_name] = {
                        "path": db_path,
                        "size": os.path.getsize(db_path),
                        "last_modified": os.path.getmtime(db_path),
                        "tables": {},
                        "source": "default"
                    }
                    logger.info(f"Connected to {db_name} database at {db_path}")
                except Exception as e:
                    logger.error(f"Error connecting to {db_name} database: {str(e)}")
            else:
                # If the database doesn't exist, but it's one of our primary databases,
                # create the directory if needed and initialize the database
                if db_name == "intelligence":
                    try:
                        # Ensure directory exists
                        os.makedirs(os.path.dirname(db_path), exist_ok=True)
                        
                        # Create and connect to the database using _get_db_connection
                        conn = self._get_db_connection(db_path)
                        
                        self.directory[db_name] = {
                            "path": db_path,
                            "size": 0,
                            "last_modified": time.time(),
                            "tables": {},
                            "source": "default"
                        }
                        logger.info(f"Created and connected to {db_name} database at {db_path}")
                        
                        # Initialize tables
                        self._initialize_intelligence_tables()
                    except Exception as e:
                        logger.error(f"Error creating {db_name} database: {str(e)}")
        
    def initialize(self):
        """Initialize the directory by discovering databases and mapping tables."""
        global _global_initialized

        # Check global initialization flag to prevent redundant setup across instances
        if self.initialized or _global_initialized:
            return True
            
        try:
            # Only do minimal initialization if we haven't done it yet
            if not self.directory:
                self._initialize_primary_databases()
            
            # Discover additional databases without recursion
            if not hasattr(self, '_discovery_in_progress'):
                self._discovery_in_progress = True
                try:
                    self.discover_databases()
                finally:
                    self._discovery_in_progress = False
            
            # Map tables across all databases
            self.map_database_tables()
            
            # Set up priority sources for important tables
            self._setup_priority_sources()
            
            # Initialize Trevor tables with recursion protection
            if not hasattr(self, '_trevor_init_in_progress'):
                self._trevor_init_in_progress = True
                try:
                    self._initialize_trevor_tables()
                finally:
                    self._trevor_init_in_progress = False
            
            self.initialized = True
            _global_initialized = True
            logger.debug(f"Database directory initialized with {len(self.directory)} databases and {len(self.table_mappings)} mapped tables")
            return True
        except Exception as e:
            logger.error(f"Error initializing database directory: {str(e)}")
            return False
        
    def discover_databases(self):
        """Discover all available SQLite databases in the workspace."""
        try:
            # TRADING MODE OPTIMIZATION: Only load essential databases for trading bot
            # Set JARVIS_TRADING_MODE=1 to skip the expensive discovery of 65+ unused databases
            if os.environ.get('JARVIS_TRADING_MODE') == '1':
                logger.info("Trading mode enabled - loading only essential databases (boardroom, trevor_database, users)")
                
                # Only load the 3 databases actually used by the trading bot
                essential_dbs = {
                    "boardroom": "~/Jarvis/Database/v2/agents.db",
                    "trevor_database": "~/Jarvis/Database/v2/trading_forex.db",
                    "users": "~/Jarvis/Database/v2/core.db"
                }
                
                for db_name, db_path in essential_dbs.items():
                    if os.path.exists(db_path) and os.path.getsize(db_path) > 0:
                        self.directory[db_name] = {
                            "path": db_path,
                            "size": os.path.getsize(db_path),
                            "last_modified": os.path.getmtime(db_path),
                            "tables": {},
                            "source": "trading_essential"
                        }
                        logger.debug(f"Added essential trading database {db_name} at {db_path}")
                
                logger.info(f"Trading mode: loaded {len(self.directory)} essential databases instead of 68")
                return True
            
            # NORMAL MODE: Full discovery (for non-trading use cases)
            # Start with the default paths
            for db_name, db_path in DEFAULT_DB_PATHS.items():
                if os.path.exists(db_path) and os.path.getsize(db_path) > 0:
                    self.directory[db_name] = {
                        "path": db_path,
                        "size": os.path.getsize(db_path),
                        "last_modified": os.path.getmtime(db_path),
                        "tables": {},
                        "source": "default"
                    }
                    logger.debug(f"Added default database {db_name} at {db_path}")
                    
            # Base directory for searching additional databases
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            
            # Find all .db files in the workspace, excluding env directories
            for root, dirs, files in os.walk(base_dir):
                # Skip virtual environments, backups, test data, and already processed paths
                if ('myenv' in root or 'venv' in root or 'env' in root or '.git' in root or
                    'backups' in root or 'backup' in root.lower() or
                    'temp_extract' in root or 'test_data' in root or
                    'mcp-reference' in root or
                    any(path in root for path in DEFAULT_DB_PATHS.values())):
                    continue
                    
                for file in files:
                    if file.endswith('.db'):
                        db_path = os.path.join(root, file)
                        
                        # Skip empty files
                        if os.path.getsize(db_path) == 0:
                            continue
                            
                        # Generate a unique name based on the path
                        db_name = f"{os.path.basename(root)}_{file[:-3]}"
                        
                        # Add to directory if not already present
                        if db_name not in self.directory:
                            self.directory[db_name] = {
                                "path": db_path,
                                "size": os.path.getsize(db_path),
                                "last_modified": os.path.getmtime(db_path),
                                "tables": {},
                                "source": "discovered"
                            }
                            logger.info(f"Discovered additional database {db_name} at {db_path}")
            
            logger.info(f"Discovered {len(self.directory)} databases")
            return True
        except Exception as e:
            logger.error(f"Error discovering databases: {str(e)}")
            return False
            
    def map_database_tables(self):
        """Map all tables and their schemas across all discovered databases."""
        for db_name, db_info in self.directory.items():
            db_path = db_info["path"]
            
            try:
                # Connect to the database using our wrapper
                conn = self._get_db_connection(db_path)
                cursor = conn.cursor()
                
                # Get all tables
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tables = [row[0] for row in cursor.fetchall()]
                
                for table_name in tables:
                    # Get table schema
                    cursor.execute(f"PRAGMA table_info({table_name})")
                    columns = [{"name": row[1], "type": row[2], "notnull": row[3], "pk": row[4]} 
                               for row in cursor.fetchall()]
                    
                    # Get approximate row count (fast)
                    try:
                        cursor.execute(f"SELECT COUNT(*) FROM {table_name} LIMIT 1")
                        row_count = cursor.fetchone()[0]
                    except:
                        row_count = 0
                    
                    # Store table info in the database entry
                    db_info["tables"][table_name] = {
                        "columns": columns,
                        "row_count": row_count
                    }
                    
                    # Update the global table mapping
                    if table_name not in self.table_mappings:
                        self.table_mappings[table_name] = []
                    
                    self.table_mappings[table_name].append({
                        "db_name": db_name,
                        "db_path": db_path,
                        "row_count": row_count
                    })
                
                # No need to close connection, will be kept in our cache
                
                logger.info(f"Mapped {len(tables)} tables in {db_name}")
            except Exception as e:
                logger.error(f"Error mapping tables in {db_name} ({db_path}): {str(e)}")
        
        # Sort table mappings by row count (descending)
        for table_name, locations in self.table_mappings.items():
            self.table_mappings[table_name] = sorted(
                locations, 
                key=lambda x: x["row_count"],
                reverse=True
            )
        
        logger.info(f"Mapped {len(self.table_mappings)} unique tables across all databases")
        return True
    
    def _setup_priority_sources(self):
        """Set up priority sources focusing specifically on V2 trading, agents, and intelligence databases."""
        # Clear any existing priority sources
        self.prioritized_sources = {}
        
        # Explicitly set priorities for the databases we want
        trevor_db_path = "~/Jarvis/Database/v2/trading_forex.db"
        boardroom_db_path = "~/Jarvis/Database/v2/agents.db"
        intelligence_db_path = "~/Jarvis/Jarvis_Agent_SDK/intelligence.db"
        docstring_db_path = "~/Jarvis/docstrings.db"
        
        # Find db_names for these paths
        trevor_db_name = None
        boardroom_db_name = None
        intelligence_db_name = None
        docstring_db_name = None
        
        for db_name, db_info in self.directory.items():
            if db_info["path"] == trevor_db_path:
                trevor_db_name = db_name
            elif db_info["path"] == boardroom_db_path:
                boardroom_db_name = db_name
            elif db_info["path"] == intelligence_db_path:
                intelligence_db_name = db_name
            elif db_info["path"] == docstring_db_path:
                docstring_db_name = db_name
        
        # Set trevor_database tables
        if trevor_db_name:
            tables = ["handler_analysis", "handler_processing_history", "handler_training_data", "pattern_data", "model_storage"]
            for table in tables:
                if table in self.directory[trevor_db_name]["tables"]:
                    self.prioritized_sources[table] = trevor_db_name
                    logger.info(f"Set priority source for {table} to {trevor_db_name}")
        
        # Set boardroom tables
        if boardroom_db_name:
            tables = ["handlers", "handler_execution_tracking", "handler_performance",
                      "handler_error_patterns", "handler_parameter_patterns", 
                      "handler_related_actions", "handler_data", "handler_patterns"]
            for table in tables:
                if table in self.directory[boardroom_db_name]["tables"]:
                    self.prioritized_sources[table] = boardroom_db_name
                    logger.info(f"Set priority source for {table} to {boardroom_db_name}")
        
        # Set intelligence tables
        if intelligence_db_name:
            tables = ["handler_performance", "handler_data", "handler_patterns"]
            for table in tables:
                if table in self.directory[intelligence_db_name]["tables"]:
                    self.prioritized_sources[table] = intelligence_db_name
                    logger.info(f"Set priority source for {table} to {intelligence_db_name}")
        
        # Set docstring tables
        if docstring_db_name:
            tables = ["docstrings", "semantic_relationships", "docstring_versions"]
            for table in tables:
                if table in self.directory[docstring_db_name]["tables"]:
                    self.prioritized_sources[table] = docstring_db_name
                    logger.info(f"Set priority source for {table} to {docstring_db_name}")
        
        logger.info(f"Set up {len(self.prioritized_sources)} priority table sources from specified databases only")
        
    def get_table_location(self, table_name: str) -> List[Dict]:
        """
        Get all database locations containing a specific table.
        
        Args:
            table_name: Name of the table to locate
            
        Returns:
            List of database paths containing the table
        """
        if not self.initialized:
            self.initialize()
            
        # Check if we have this table mapped
        if table_name in self.table_mappings:
            return self.table_mappings[table_name]
        
        return []
        
    def get_priority_database_for_table(self, table_name: str) -> Optional[str]:
        """
        Get the priority database path for a specific table.
        
        Args:
            table_name: Name of the table
            
        Returns:
            Database path or None if not found
        """
        if not self.initialized:
            self.initialize()
            
        # Check priority sources first
        if table_name in self.prioritized_sources:
            db_name = self.prioritized_sources[table_name]
            if db_name in self.directory:
                return self.directory[db_name]["path"]
        
        # Fall back to the first entry in table_mappings (sorted by row count)
        if table_name in self.table_mappings and self.table_mappings[table_name]:
            return self.table_mappings[table_name][0]["db_path"]
        
        return None
        
    def _get_db_connection(self, db_path: str) -> Union[sqlite3.Connection, 'ConnectionWrapper']:
        """
        Get a database connection with thread-safe per-thread connection pools.
        Creates the database and directory if needed.
        """
        try:
            thread_id = threading.current_thread().ident
            thread_connections = self._get_thread_connections()

            # Check if we already have a connection to this database for this thread
            if db_path in thread_connections:
                logger.debug(f"DatabaseDirectory: Reusing connection to {os.path.basename(db_path)} "
                           f"for thread {thread_id}")
                return thread_connections[db_path]

            # Create a new thread-specific connection
            logger.info(f"Creating new SQLite connection for thread {thread_id} to {db_path}")
            os.makedirs(os.path.dirname(db_path), exist_ok=True)

            # Create connection with check_same_thread=False for thread safety
            conn = sqlite3.connect(db_path, check_same_thread=False, isolation_level=None)
            conn.row_factory = sqlite3.Row

            # Enable WAL mode for better concurrent access
            conn.execute("PRAGMA journal_mode=DELETE")
            conn.execute("PRAGMA wal_autocheckpoint=500")  # Checkpoint after ~2MB
            conn.execute("PRAGMA busy_timeout=30000")  # 30 second timeout

            # Wrap the connection with our custom wrapper
            class ConnectionWrapper:
                """Thread-safe wrapper for sqlite3.Connection with execute_query method."""

                def __init__(self, connection):
                    self.connection = connection

                def __getattr__(self, name):
                    return getattr(self.connection, name)

                def cursor(self):
                    return self.connection.cursor()

                def commit(self):
                    return self.connection.commit()

                def close(self):
                    return self.connection.close()

                def execute_query(self, query, params=None, target_table=None, target_db=None):
                    """Execute a SQL query and return results."""
                    try:
                        cursor = self.connection.cursor()
                        if params:
                            cursor.execute(query, params)
                        else:
                            cursor.execute(query)

                        if query.strip().upper().startswith("SELECT"):
                            rows = cursor.fetchall()
                            return [dict(row) for row in rows]
                        else:
                            self.connection.commit()
                            return cursor
                    except Exception as e:
                        logger.error(f"Query execution failed: {e}")
                        raise

            wrapped_conn = ConnectionWrapper(conn)

            # Store in thread-local storage
            thread_connections[db_path] = wrapped_conn

            logger.info(f"Connected to {os.path.basename(db_path)} database at {db_path}")
            return wrapped_conn

        except Exception as e:
            logger.error(f"Error getting database connection for {db_path}: {str(e)}")
            logger.debug(traceback.format_exc())
            return None
            
    def get_connection(self, db_name: str) -> Optional[sqlite3.Connection]:
        """
        Get a database connection by database name (not path).
        
        This method is primarily used by functions that know the database name
        (e.g., 'trevor_database', 'boardroom', 'workspace_sharing') but not the full path.
        
        Args:
            db_name: The name of the database to connect to
            
        Returns:
            A SQLite connection object or None if the database wasn't found
        """
        if not self.initialized:
            self.initialize()
            
        # Check if the database is in our directory
        if db_name in self.directory:
            db_path = self.directory[db_name]["path"]
            return self._get_db_connection(db_path)
            
        # Check for standard database paths
        if db_name in DEFAULT_DB_PATHS:
            db_path = DEFAULT_DB_PATHS[db_name]
            if os.path.exists(db_path):
                return self._get_db_connection(db_path)
                
        # Try to construct a path from the base directory
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        possible_paths = [
            os.path.join(base_dir, "Database", f"{db_name}.db"),
            os.path.join(base_dir, f"{db_name}.db"),
            os.path.join(base_dir, "Handler", f"{db_name}.db")
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                try:
                    conn = self._get_db_connection(path)
                    
                    # Add to directory if not already there
                    if db_name not in self.directory:
                        self.directory[db_name] = {
                            "path": path,
                            "size": os.path.getsize(path),
                            "last_modified": os.path.getmtime(path),
                            "tables": {},
                            "source": "constructed"
                        }
                        
                    return conn
                except Exception as e:
                    logger.error(f"Error connecting to constructed path {path}: {str(e)}")
        
        # Special handling for workspace_sharing
        if db_name == "workspace_sharing":
            workspace_db_path = os.path.join(base_dir, "Database", "workspace_sharing.db")
            try:
                # Create the database if it doesn't exist
                os.makedirs(os.path.dirname(workspace_db_path), exist_ok=True)
                conn = sqlite3.connect(workspace_db_path, isolation_level=None)
                conn.row_factory = sqlite3.Row
                
                # Add to our connection cache
                self.database_connections[workspace_db_path] = conn
                
                # Add to directory
                self.directory[db_name] = {
                    "path": workspace_db_path,
                    "size": 0,
                    "last_modified": time.time(),
                    "tables": {},
                    "source": "created"
                }
                
                logger.info(f"Created new workspace_sharing database at {workspace_db_path}")
                return conn
            except Exception as e:
                logger.error(f"Error creating workspace_sharing database: {str(e)}")
        
        logger.warning(f"Could not find or create database: {db_name}")
        return None

    def execute_query(self, query: str, params: Optional[Tuple] = None,
                     target_table: Optional[str] = None, 
                     target_db: Optional[str] = None,
                     fetch_all: Optional[bool] = True):
        """
        Execute a query against the appropriate database based on the target table.
        
        Args:
            query: SQL query to execute
            params: Query parameters
            target_table: Target table for context
            target_db: Optional specific database to query
            fetch_all: Whether to fetch all results (True) or just the first one (False)
            
        Returns:
            For SELECT queries: List of dictionaries representing result rows
            For other queries: Empty list
        """
        if not self.initialized:
            self.initialize()
            
        db_path = None
        
        # If target_db is provided, use it directly
        if target_db:
            if target_db in self.directory:
                db_path = self.directory[target_db]["path"]
            else:
                # Check if target_db is a direct path
                if os.path.exists(target_db) and os.path.isfile(target_db):
                    db_path = target_db
        
        # If no db_path yet and we have a target_table, find the appropriate database
        if not db_path and target_table:
            db_path = self.get_priority_database_for_table(target_table)
            
        # If still no db_path, try to extract table name from the query
        if not db_path and not target_table:
            # Try to extract the table name from the query
            table_match = self._extract_table_from_query(query)
            if table_match:
                db_path = self.get_priority_database_for_table(table_match)
        
        # If we couldn't determine the database, use the intelligence database as default
        if not db_path:
            if "intelligence" in self.directory:
                db_path = self.directory["intelligence"]["path"]
                logger.warning(f"Could not determine database for query, using intelligence database as default")
            else:
                logger.error(f"Could not determine database for query and no default available")
                return []  # Return empty list instead of None
                
        try:
            # Create a new connection for this thread to avoid SQLite thread errors
            import threading
            thread_id = threading.get_ident()
            
            # Check if we have thread-local connections initialized
            if not hasattr(self._thread_local, 'connections'):
                self._thread_local.connections = {}

            # Get or create thread-local connection
            if db_path not in self._thread_local.connections:
                logger.info(f"Creating new SQLite connection for thread {thread_id} to {db_path}")
                # Create a new SQLite connection for this thread
                conn = sqlite3.connect(db_path, isolation_level=None)
                conn.row_factory = sqlite3.Row
                self._thread_local.connections[db_path] = conn
            else:
                conn = self._thread_local.connections[db_path]
            
            # Check if conn has execute_query method (our wrapper) and use it if available
            if hasattr(conn, 'execute_query'):
                # Use the wrapper's execute_query directly
                results = conn.execute_query(query, params)
                # Always return a list, either the results list or an empty list
                return results if results is not None else []
            
            # Otherwise use the standard approach
            cursor = conn.cursor()
            
            # Execute query
            try:
                if params:
                    cursor.execute(query, params)
                else:
                    cursor.execute(query)
            except sqlite3.IntegrityError as integrity_error:
                # Re-raise IntegrityError so it can be caught by the calling code
                logger.warning(f"IntegrityError executing query: {str(integrity_error)}")
                raise  # Re-raise the IntegrityError for handling upstream
            except Exception as exec_error:
                logger.error(f"Error executing query: {str(exec_error)}")
                # Return empty list for query execution failures
                return []
            
            # Only try to get results for SELECT queries to avoid errors
            if query.strip().upper().startswith("SELECT"):
                try:
                    # Handle case where cursor might already be a list (some DB wrappers return this)
                    if isinstance(cursor, list):
                        raw_results = cursor
                    else:
                        # Handle fetch_all parameter
                        if fetch_all:
                            raw_results = cursor.fetchall()
                        else:
                            row = cursor.fetchone()
                            raw_results = [row] if row else []
                    
                    # Convert sqlite3.Row objects to dictionaries
                    results = []
                    for row in raw_results:
                        try:
                            if isinstance(row, sqlite3.Row):
                                # Convert sqlite3.Row to dict
                                results.append(dict(row))
                            else:
                                # Keep as is if not a sqlite3.Row
                                results.append(row)
                        except Exception as row_error:
                            logger.warning(f"Error converting row to dict: {str(row_error)}")
                            # Add row as-is if conversion fails
                            results.append(row)
                        
                    return results
                except AttributeError as attr_error:
                    # This is specifically for the 'list' object has no attribute 'fetchall' error
                    if isinstance(cursor, list):
                        # If cursor is already a list, return it with dict conversion
                        results = []
                        for row in cursor:
                            try:
                                if isinstance(row, sqlite3.Row):
                                    results.append(dict(row))
                                else:
                                    results.append(row)
                            except Exception:
                                results.append(row)
                        return results
                    else:
                        logger.error(f"AttributeError in execute_query: {str(attr_error)}")
                        return []
                except Exception as fetch_error:
                    logger.warning(f"Error fetching results: {str(fetch_error)}")
                    return []  # Return empty list on error
            else:
                # For non-SELECT queries, commit if necessary
                if query.strip().upper().startswith(("INSERT", "UPDATE", "DELETE", "CREATE", "ALTER", "DROP")):
                    conn.commit()
                
                # Return empty list for non-SELECT queries
                return []
                
        except Exception as e:
            logger.error(f"Error executing query on {db_path}: {str(e)}")
            logger.error(f"Query: {query}")
            if params:
                logger.error(f"Params: {params}")
            return []  # Return empty list instead of None
    
    def _extract_table_from_query(self, query: str) -> Optional[str]:
        """
        Extract the main table name from a SQL query.
        
        Args:
            query: SQL query to analyze
            
        Returns:
            Table name or None if not found
        """
        import re
        
        # Convert to uppercase for case-insensitive matching
        query_upper = query.upper()
        
        # Check for SELECT queries
        if query_upper.startswith("SELECT"):
            # Try to find FROM clause
            from_match = re.search(r"FROM\s+([a-zA-Z0-9_]+)", query_upper)
            if from_match:
                return from_match.group(1).lower()
                
        # Check for INSERT queries
        elif query_upper.startswith("INSERT"):
            # Try to find INTO clause
            into_match = re.search(r"INTO\s+([a-zA-Z0-9_]+)", query_upper)
            if into_match:
                return into_match.group(1).lower()
                
        # Check for UPDATE queries
        elif query_upper.startswith("UPDATE"):
            # Try to find the table name
            update_match = re.search(r"UPDATE\s+([a-zA-Z0-9_]+)", query_upper)
            if update_match:
                return update_match.group(1).lower()
                
        # Check for DELETE queries
        elif query_upper.startswith("DELETE"):
            # Try to find FROM clause
            from_match = re.search(r"FROM\s+([a-zA-Z0-9_]+)", query_upper)
            if from_match:
                return from_match.group(1).lower()
                
        return None
        
    def close_connections(self):
        """Close all database connections."""
        for db_path, conn in self.database_connections.items():
            try:
                conn.close()
                logger.info(f"Closed connection to {db_path}")
            except Exception as e:
                logger.error(f"Error closing connection to {db_path}: {str(e)}")
                
        self.database_connections = {}

    def get_cached_result(self, key: str, max_age_seconds: int = 300) -> Optional[Any]:
        """
        Get a cached result if available and not expired.
        
        Args:
            key: Cache key
            max_age_seconds: Maximum age in seconds
            
        Returns:
            Cached result or None if not found or expired
        """
        if key in self._cache and key in self._cache_timestamps:
            age = time.time() - self._cache_timestamps[key]
            if age < max_age_seconds:
                return self._cache[key]
        
        return None
        
    def set_cached_result(self, key: str, value: Any):
        """
        Cache a result.
        
        Args:
            key: Cache key
            value: Value to cache
        """
        self._cache[key] = value
        self._cache_timestamps[key] = time.time()
        
    def get_table_schema(self, table_name: str) -> Optional[List[Dict]]:
        """
        Get the schema for a table.
        
        Args:
            table_name: Name of the table
            
        Returns:
            List of column definitions or None if not found
        """
        if not self.initialized:
            self.initialize()
            
        # Check cache first
        cache_key = f"schema_{table_name}"
        cached_result = self.get_cached_result(cache_key)
        if cached_result:
            return cached_result
            
        # Find the table in our mappings
        if table_name in self.table_mappings and self.table_mappings[table_name]:
            db_info = self.table_mappings[table_name][0]
            db_name = db_info["db_name"]
            
            if db_name in self.directory and table_name in self.directory[db_name]["tables"]:
                schema = self.directory[db_name]["tables"][table_name]["columns"]
                
                # Cache the result
                self.set_cached_result(cache_key, schema)
                
                return schema
        
        return None
        
    def get_all_tables(self) -> List[str]:
        """
        Get list of all available tables across all databases.
        
        Returns:
            List of table names
        """
        if not self.initialized:
            self.initialize()
            
        return list(self.table_mappings.keys())
        
    def search_tables(self, pattern: str, limit: int = 20) -> List[str]:
        """
        Search for tables matching a pattern.
        
        Args:
            pattern: Search pattern (case-insensitive)
            limit: Maximum number of results
            
        Returns:
            List of matching table names
        """
        if not self.initialized:
            self.initialize()
            
        pattern = pattern.lower()
        matches = []
        
        for table_name in self.table_mappings.keys():
            if pattern in table_name.lower():
                matches.append(table_name)
                
                if len(matches) >= limit:
                    break
        
        return matches
        
    def get_handler_performance_data(self, handler_name: Optional[str] = None, 
                                  action: Optional[str] = None,
                                  workspace_id: Optional[str] = None) -> List[Dict]:
        """
        Get handler performance data from across all databases.
        
        Args:
            handler_name: Optional filter by handler name
            action: Optional filter by action
            workspace_id: Optional filter by workspace ID
            
        Returns:
            List of handler performance records
        """
        if not self.initialized:
            self.initialize()
            
        # Build the cache key
        cache_components = ["handler_performance"]
        if handler_name:
            cache_components.append(f"handler_{handler_name}")
        if action:
            cache_components.append(f"action_{action}")
        if workspace_id:
            cache_components.append(f"workspace_{workspace_id}")
            
        cache_key = "_".join(cache_components)
        
        # Check cache
        cached_result = self.get_cached_result(cache_key, max_age_seconds=60)  # Short cache for performance data
        if cached_result:
            return cached_result
            
        # Build the query
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
            
        # Find all databases with handler_performance table
        all_results = []
        
        # First check priority database
        priority_db = self.get_priority_database_for_table("handler_performance")
        if priority_db:
            try:
                # Use execute_query instead of direct cursor operations
                priority_results = self.execute_query(query, tuple(params), 
                                                     target_db=priority_db)
                if priority_results:
                    all_results.extend(priority_results)
                    logger.info(f"Got {len(priority_results)} handler performance records from priority database")
            except Exception as e:
                logger.error(f"Error querying handler_performance in priority database: {str(e)}")
        
        # Then check other databases with this table
        for table_location in self.get_table_location("handler_performance"):
            db_path = table_location["db_path"]
            
            # Skip priority database which we already queried
            if db_path == priority_db:
                continue
                
            try:
                # Use execute_query instead of direct cursor operations
                db_results = self.execute_query(query, tuple(params), target_db=db_path)
                
                if db_results:
                    # Add source database info
                    for result in db_results:
                        result["source_db"] = db_path
                    
                    all_results.extend(db_results)
                    logger.info(f"Got {len(db_results)} handler performance records from {db_path}")
            except Exception as e:
                logger.error(f"Error querying handler_performance in {db_path}: {str(e)}")
        
        # Cache the results
        self.set_cached_result(cache_key, all_results)
        
        return all_results

    def get_handler_analysis_data(self, handler_name: Optional[str] = None) -> List[Dict]:
        """
        Get handler analysis data from trevor_database's handler_analysis table.
        
        Args:
            handler_name: Optional filter by handler name
            
        Returns:
            List of handler analysis records with complexity scores and metadata
        """
        if not self.initialized:
            self.initialize()
            
        # Build the cache key
        cache_key = "handler_analysis"
        if handler_name:
            cache_key += f"_{handler_name}"
            
        # Check cache
        cached_result = self.get_cached_result(cache_key, max_age_seconds=300)
        if cached_result:
            return cached_result
            
        # Build the query
        query = "SELECT * FROM handler_analysis"
        params = []
        
        if handler_name:
            query += " WHERE handler_name = ?"
            params.append(handler_name)
            
        # Get priority database for handler_analysis table (should be trevor_database)
        priority_db = self.get_priority_database_for_table("handler_analysis")
        if not priority_db:
            logger.warning("No priority database found for handler_analysis table")
            return []
            
        try:
            # Use execute_query instead of direct cursor operations
            results = self.execute_query(query, tuple(params), 
                                      target_db=priority_db)
            
            if not results:
                return []
                
            # Parse any JSON metadata fields
            for row in results:
                for key, value in row.items():
                    if key == 'metadata' and value and isinstance(value, str):
                        try:
                            row[key] = json.loads(value)
                        except json.JSONDecodeError:
                            # Keep as string if not valid JSON
                            pass
            
            # Cache the result
            self.set_cached_result(cache_key, results)
            logger.info(f"Got {len(results)} handler analysis records from {priority_db}")
            
            return results
        except Exception as e:
            logger.error(f"Error querying handler_analysis in {priority_db}: {str(e)}")
            return []

    def get_handler_related_data(self, table_name: str, handler_name: Optional[str] = None) -> List[Dict]:
        """
        Get handler-related data from boardroom database's various handler tables.
        
        Args:
            table_name: Name of the handler-related table (handler_error_patterns, 
                       handler_parameter_patterns, handler_related_actions, etc.)
            handler_name: Optional filter by handler name
            
        Returns:
            List of handler-related records
        """
        if not self.initialized:
            self.initialize()
            
        # Validate table name is a handler-related table
        handler_related_tables = [
            "handler_error_patterns", 
            "handler_parameter_patterns", 
            "handler_related_actions",
            "handler_data"
        ]
        
        if table_name not in handler_related_tables:
            if table_name == "handler_patterns":
                logger.debug(f"Looking for execution patterns in special table '{table_name}' - this will be populated during runtime")
            else:
                logger.warning(f"Invalid handler-related table: {table_name}")
            return []
            
        # Build the cache key
        cache_key = f"{table_name}"
        if handler_name:
            cache_key += f"_{handler_name}"
            
        # Check cache
        cached_result = self.get_cached_result(cache_key, max_age_seconds=120)
        if cached_result:
            return cached_result
            
        # Build the query
        query = f"SELECT * FROM {table_name}"
        params = []
        
        if handler_name:
            query += " WHERE handler_name = ?"
            params.append(handler_name)
            
        # Get priority database for this table (should be boardroom)
        priority_db = self.get_priority_database_for_table(table_name)
        if not priority_db:
            logger.warning(f"No priority database found for {table_name} table")
            return []
            
        try:
            # Use execute_query instead of direct cursor operations
            results = self.execute_query(query, tuple(params), target_db=priority_db)
            
            if not results:
                return []
                
            # Parse any JSON data fields
            for row in results:
                for key, value in row.items():
                    if (key in ['parameters', 'patterns', 'metadata', 'data'] and 
                        value and isinstance(value, str)):
                        try:
                            row[key] = json.loads(value)
                        except json.JSONDecodeError:
                            # Keep as string if not valid JSON
                            pass
            
            # Cache the results
            self.set_cached_result(cache_key, results)
            logger.info(f"Got {len(results)} records from {table_name} in {priority_db}")
            
            return results
        except Exception as e:
            logger.error(f"Error querying {table_name} in {priority_db}: {str(e)}")
            return []

    def get_docstring_semantic_relationships(self, method_name=None, relationship_type=None):
        """
        Get semantic relationships between methods based on docstring analysis.
        
        Args:
            method_name: Optional method name to filter relationships
            relationship_type: Optional relationship type to filter by
            
        Returns:
            Dictionary containing incoming and outgoing relationships
        """
        if not self.initialized:
            self.initialize()
            
        result = {
            "outgoing_relationships": [],
            "incoming_relationships": []
        }
        
        try:
            # Build query with filters
            query = "SELECT * FROM semantic_relationships WHERE 1=1"
            params = []
            
            # Add method filter
            if method_name:
                query += " AND (source = ? OR target = ?)"
                params.extend([method_name, method_name])
                
            # Add relationship type filter
            if relationship_type:
                query += " AND type = ?"
                params.append(relationship_type)
                
            # Execute query
            cursor = self.execute_query(query, tuple(params) if params else None, 
                                     target_table="semantic_relationships")
            
            if not cursor:
                logger.warning("Failed to execute semantic relationships query")
                return result
                
            # Process relationships
            for row in cursor:
                relationship = dict(row)
                
                # Add to appropriate list based on method name
                if method_name:
                    if relationship.get('source') == method_name:
                        result["outgoing_relationships"].append(relationship)
                    elif relationship.get('target') == method_name:
                        result["incoming_relationships"].append(relationship)
                else:
                    # If no method name filter, add to outgoing list
                    result["outgoing_relationships"].append(relationship)
            
            return result
            
        except Exception as e:
            logger.error(f"Error getting semantic relationships: {str(e)}")
            return result
            
    def ensure_journey_tracking_tables(self):
        """
        Ensures that all necessary journey tracking tables exist in the workspace_sharing database.
        
        This includes tables for:
        - Journey steps
        - Journey metrics
        - Workspace activity
        - Cross-handler communication
        
        Returns:
            Boolean indicating if tables were successfully created or verified
        """
        try:
            # Try to connect to workspace_sharing database
            conn = self.get_connection('workspace_sharing')
            if not conn:
                # Try to create the database if it doesn't exist
                workspace_db_path = os.path.join(self.base_dir, "Database", "workspace_sharing.db")
                os.makedirs(os.path.dirname(workspace_db_path), exist_ok=True)
                conn = sqlite3.connect(workspace_db_path, isolation_level=None)
                conn.row_factory = sqlite3.Row
                self.database_connections[workspace_db_path] = conn
                logger.info(f"Created new workspace_sharing database at {workspace_db_path}")
                
                # Add to directory
                self.directory["workspace_sharing"] = {
                    "path": workspace_db_path,
                    "size": 0,
                    "last_modified": time.time(),
                    "tables": {},
                    "source": "created"
                }
                
            cursor = conn.cursor()
            
            # Create journey_steps table if it doesn't exist
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS journey_steps (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                journey_id TEXT NOT NULL,
                step_type TEXT NOT NULL,
                step_data TEXT,
                workspace_id TEXT,
                user_id TEXT,
                timestamp REAL NOT NULL,
                status TEXT DEFAULT 'pending'
            )
            ''')
            
            # Create journey_metrics table if it doesn't exist
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS journey_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                journey_id TEXT NOT NULL,
                metric_name TEXT NOT NULL,
                metric_value REAL,
                workspace_id TEXT,
                user_id TEXT,
                timestamp REAL NOT NULL
            )
            ''')
            
            # Create workspace_activity table if it doesn't exist
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS workspace_activity (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                workspace_id TEXT NOT NULL,
                activity_type TEXT NOT NULL,
                activity_data TEXT,
                user_id TEXT,
                journey_id TEXT,
                timestamp REAL NOT NULL
            )
            ''')
            
            # Create cross_handler_communication table if it doesn't exist
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS cross_handler_communication (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                journey_id TEXT NOT NULL,
                source_handler TEXT NOT NULL,
                target_handler TEXT NOT NULL,
                message_type TEXT NOT NULL,
                message_data TEXT,
                workspace_id TEXT,
                timestamp REAL NOT NULL,
                status TEXT DEFAULT 'sent'
            )
            ''')
            
            # Create indexes for faster querying
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_journey_steps_journey_id ON journey_steps(journey_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_journey_metrics_journey_id ON journey_metrics(journey_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_workspace_activity_workspace_id ON workspace_activity(workspace_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_cross_handler_journey_id ON cross_handler_communication(journey_id)')
            
            conn.commit()
            
            # Update our directory with the new tables
            self.directory["workspace_sharing"]["tables"] = {
                "journey_steps": {"columns": [], "row_count": 0},
                "journey_metrics": {"columns": [], "row_count": 0},
                "workspace_activity": {"columns": [], "row_count": 0},
                "cross_handler_communication": {"columns": [], "row_count": 0}
            }
            
            logger.info("Journey tracking tables created or verified successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error ensuring journey tracking tables: {str(e)}")
            return False
            
    def record_journey_step(self, journey_id, step_type, step_data=None, workspace_id=None, user_id=None, status='pending'):
        """
        Records a step in a user's journey through the system.
        
        Args:
            journey_id: Unique ID for the journey
            step_type: Type of step (e.g., 'request', 'handler_selection', 'response')
            step_data: Optional JSON-serializable data about the step
            workspace_id: Optional workspace ID
            user_id: Optional user ID
            status: Status of the step (default 'pending')
            
        Returns:
            ID of the created step or None if failed
        """
        try:
            # Ensure tables exist
            self.ensure_journey_tracking_tables()
            
            # Connect to workspace_sharing database
            conn = self.get_connection('workspace_sharing')
            if not conn:
                logger.error("Could not connect to workspace_sharing database for recording journey step")
                return None
                
            cursor = conn.cursor()
            
            # Serialize step data if provided
            serialized_data = None
            if step_data:
                if isinstance(step_data, str):
                    serialized_data = step_data
                else:
                    serialized_data = json.dumps(step_data)
            
            # Insert the step
            cursor.execute(
                '''
                INSERT INTO journey_steps 
                (journey_id, step_type, step_data, workspace_id, user_id, timestamp, status)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ''',
                (
                    journey_id,
                    step_type,
                    serialized_data,
                    workspace_id,
                    user_id,
                    time.time(),
                    status
                )
            )
            
            conn.commit()
            step_id = cursor.lastrowid
            logger.info(f"Recorded journey step {step_id} for journey {journey_id}")
            return step_id
            
        except Exception as e:
            logger.error(f"Error recording journey step: {str(e)}")
            return None
    
    def get_docstring_content(self, handler=None, function=None):
        """
        Get docstring content from the docstrings database.
        
        Args:
            handler: Optional handler name to filter by
            function: Optional function name to filter by
            
        Returns:
            List of docstring records with NLP features
        """
        if not self.initialized:
            self.initialize()
            
        try:
            # Build query with filters
            where_clauses = []
            params = []
            
            if handler:
                where_clauses.append("handler_type = ?")
                params.append(handler)
                
            if function:
                where_clauses.append("function_name = ?")
                params.append(function)
            
            # Construct the query
            query = "SELECT * FROM docstrings"
            
            if where_clauses:
                query += " WHERE " + " AND ".join(where_clauses)
                
            # Execute the query
            cursor = self.execute_query(query, tuple(params) if params else None, 
                                     target_table="docstrings")
            
            if not cursor:
                logger.warning("Failed to execute docstring content query")
                return []
                
            # Process results
            results = []
            for row in cursor:
                result = dict(row)
                
                # Parse JSON fields if they exist
                for key in ['nlp_features', 'content']:
                    if key in result and result[key]:
                        try:
                            result[key] = json.loads(result[key])
                        except json.JSONDecodeError:
                            # If it's not valid JSON, keep as is
                            pass
                            
                results.append(result)
                
            return results
            
        except Exception as e:
            logger.error(f"Error getting docstring content: {str(e)}")
            return []
    
    def get_trevor_model_data(self, model_version: Optional[str] = None):
        """
        Load a pre-trained tokenized model from v2/trading_forex.db.
        
        Args:
            model_version: Optional specific model version to load, 
                          defaults to highest accuracy model if not specified
                          
        Returns:
            Dict containing model data, metadata, and accuracy information
        """
        # Ensure we're initialized
        if not self.initialized:
            logger.info("Database directory not initialized, performing minimal initialization")
            self._initialize_primary_databases()
            self.initialized = True
        
        # Build the cache key
        cache_key = "trevor_model"
        if model_version:
            cache_key += f"_{model_version}"
        
        # Check cache - only cache the metadata, not the full model blob which could be large
        cached_result = self.get_cached_result(cache_key, max_age_seconds=3600)  # Cache for 1 hour
        if cached_result:
            # Note: we don't cache the actual model_data blob to save memory
            return cached_result
        
        try:
            with v2_connection("intelligence") as conn:
                cursor = conn.cursor()
                if model_version:
                    query = "SELECT id, version, metadata, accuracy FROM model_storage WHERE version = ? LIMIT 1"
                    params = (model_version,)
                else:
                    query = "SELECT id, version, metadata, accuracy FROM model_storage ORDER BY accuracy DESC LIMIT 1"
                    params = ()

                cursor.execute(query, params)
                model_info = cursor.fetchone()

                if not model_info:
                    logger.warning(f"No model found with version {model_version if model_version else 'any'}")
                    return None

                model_id = model_info["id"]
                version = model_info["version"]
                metadata_str = model_info["metadata"]
                accuracy = model_info["accuracy"]

                metadata = {}
                if metadata_str:
                    try:
                        metadata = json.loads(metadata_str)
                    except json.JSONDecodeError:
                        logger.warning(f"Could not parse metadata for model {version}")

                logger.info(f"Found model version {version} with accuracy {accuracy}%")
                result = {
                    "id": model_id,
                    "version": version,
                    "metadata": metadata,
                    "accuracy": accuracy,
                    "has_model_data": False
                }
                self.set_cached_result(cache_key, result)
                return result
        except Exception as e:
            logger.error(f"Error loading model from database: {str(e)}")
            return None

    def get_model_blob(self, model_id):
        """Get the actual model blob data."""
        try:
            with v2_connection("intelligence") as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT model_data FROM model_storage WHERE id = ?", (model_id,))
                row = cursor.fetchone()
                if row:
                    return row['model_data']
                return None
        except Exception as e:
            logger.error(f"Error getting model blob: {str(e)}")
            return None

    def load_pytorch_model(self, version=None):
        """Load a PyTorch model from the model_metrics table.
        
        Args:
            version (str, optional): Not used, will always load the 99.8% accuracy model.
            
        Returns:
            tuple: (model_state_dict, metadata) where model_state_dict is None and metadata contains model info
        """
        try:
            # Query model_metrics table for the 99.8% accuracy model
            query = "SELECT model_version, accuracy, loss, timestamp FROM model_metrics WHERE accuracy = 99.8 LIMIT 1"
            
            with v2_connection("intelligence") as conn:
                cursor = conn.cursor()
                result = cursor.execute(query).fetchone()

                if not result:
                    logging.warning("Could not find 99.8% accuracy model in model_metrics table")
                    any_models = cursor.execute("SELECT COUNT(*) FROM model_metrics").fetchone()[0]
                    if any_models > 0:
                        logging.info(f"Found {any_models} models in model_metrics table, but none with 99.8% accuracy")
                        best_model = cursor.execute("SELECT model_version, accuracy, loss, timestamp FROM model_metrics ORDER BY accuracy DESC LIMIT 1").fetchone()
                        if best_model:
                            model_version, accuracy, loss, timestamp = best_model
                            logging.info(f"Using best available model with accuracy {accuracy}%: {model_version}")
                            return None, {
                                "version": model_version,
                                "accuracy": accuracy,
                                "loss": loss,
                                "timestamp": timestamp,
                                "source": "model_metrics",
                                "note": "Using best available model instead of 99.8% model"
                            }
                    return None, {}

                model_version, accuracy, loss, timestamp = result
                metadata = {
                    "version": model_version,
                    "accuracy": accuracy,
                    "loss": loss,
                    "timestamp": timestamp,
                    "source": "model_metrics"
                }
                logging.info(f"Found model version {model_version} with accuracy {accuracy}")
                return None, metadata
        
        except Exception as e:
            logging.error(f"Error loading model: {str(e)}")
            return None, {}

    def integrate_with_orchestrator_intelligence(self, intelligence_module):
        """
        Integrate the database directory service with the orchestrator intelligence module.
        This is a one-way integration that avoids circular dependencies.
        """
        if not self.initialized:
            self.initialize()
        
        try:
            # Check if we've already integrated with this module
            if hasattr(intelligence_module, 'db_directory') and intelligence_module.db_directory == self:
                logger.info("Already integrated with this orchestrator intelligence module")
                return True
                
            # Attach self as a property on the intelligence module
            setattr(intelligence_module, 'db_directory', self)
        
            # Add a direct query method that uses our execute_query method
            if not hasattr(intelligence_module, 'directory_query'):
                def directory_query(query, params=None, target_table=None, target_db=None):
                    """Execute a query through the database directory."""
                    return self.execute_query(query, params, target_table, target_db)
            
                setattr(intelligence_module, 'directory_query', directory_query)
            
            # Initialize tables only if necessary and without creating dependencies
            # Skip automatic initialization to prevent loops
            if not hasattr(self, '_tables_initialized'):
                # Perform minimal initialization without dependencies
                self._initialize_primary_databases()
                self._tables_initialized = True
                logger.info("Performed minimal table initialization without unified database")
            
            return True
            
        except Exception as e:
            logger.error(f"Error integrating with orchestrator intelligence: {str(e)}")
            return False

    def _initialize_intelligence_tables(self):
        """Initialize required tables in the intelligence database."""
        intelligence_db_path = "~/Jarvis/Database/intelligence.db"
        conn = self._get_db_connection(intelligence_db_path)
        cursor = conn.cursor()
        
        # Create handlers table - This is crucial for the handler system to work
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS handlers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            handler_name TEXT NOT NULL,
            handler_type TEXT NOT NULL,
            handler_category TEXT NOT NULL DEFAULT 'general',
            file_path TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
        
        # Create handler_performance table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS handler_performance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            handler_name TEXT NOT NULL,
            action TEXT,
            success INTEGER,
            execution_time REAL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            metadata TEXT
        )
        """)
        
        # Create handler_data table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS handler_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            handler_name TEXT NOT NULL,
            capabilities TEXT,
            patterns TEXT,
            metadata TEXT,
            last_updated DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """)
        
        # Create handler_patterns table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS handler_patterns (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            handler_name TEXT NOT NULL,
            pattern TEXT NOT NULL,
            confidence REAL DEFAULT 0.0,
            metadata TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """)
        
        # Create intent_mappings table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS intent_mappings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            intent TEXT NOT NULL,
            handler_name TEXT NOT NULL,
            confidence REAL DEFAULT 0.0,
            success_rate REAL DEFAULT 0.0,
            metadata TEXT,
            last_updated DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """)
        
        # Create feedback_conversations table for Claude dual feedback system
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS feedback_conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            source TEXT NOT NULL, -- 'boardroom' or 'jarvis_orchestrator'
            feedback_request TEXT NOT NULL,
            conversation_history TEXT, -- JSON array of messages
            status TEXT DEFAULT 'active', -- 'active', 'completed', 'failed'
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            completed_at TIMESTAMP
        )
        """)
        
        # Create enhanced_responses table for Claude dual feedback system
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS enhanced_responses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            conversation_id INTEGER,
            original_response TEXT,
            enhanced_response TEXT,
            claude_personality TEXT,
            sentiment_analysis TEXT, -- JSON object
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (conversation_id) REFERENCES feedback_conversations (id)
        )
        """)
        
        # Create feedback_analytics table for Claude dual feedback system
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS feedback_analytics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            source TEXT NOT NULL, -- 'boardroom' or 'jarvis_orchestrator'
            turn_count INTEGER DEFAULT 0,
            completion_time REAL DEFAULT 0,
            user_satisfaction REAL DEFAULT 0,
            claude_personality TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
        
        conn.commit()
        logger.info("Intelligence database tables initialized (including Claude feedback tables)")
        
    def _initialize_boardroom_tables(self):
        """Initialize required tables in the V2 intelligence database."""
        with v2_connection("intelligence") as conn:
            for ddl in [
                """CREATE TABLE IF NOT EXISTS handler_error_patterns (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, handler_name TEXT NOT NULL,
                    error_pattern TEXT NOT NULL, frequency INTEGER DEFAULT 0,
                    last_seen DATETIME, metadata TEXT)""",
                """CREATE TABLE IF NOT EXISTS handler_parameter_patterns (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, handler_name TEXT NOT NULL,
                    parameter_name TEXT NOT NULL, pattern TEXT NOT NULL,
                    frequency INTEGER DEFAULT 0, metadata TEXT)""",
                """CREATE TABLE IF NOT EXISTS handler_related_actions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, handler_name TEXT NOT NULL,
                    related_action TEXT NOT NULL, relationship_type TEXT,
                    confidence REAL DEFAULT 0.0, metadata TEXT)""",
                """CREATE TABLE IF NOT EXISTS handler_data (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, handler_name TEXT NOT NULL,
                    capabilities TEXT, metadata TEXT,
                    last_updated DATETIME DEFAULT CURRENT_TIMESTAMP)""",
                """CREATE TABLE IF NOT EXISTS handler_performance (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, handler_name TEXT NOT NULL,
                    action TEXT, success INTEGER, execution_time REAL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP, metadata TEXT)""",
            ]:
                conn.execute(ddl)
        logger.info("Boardroom/intelligence database tables initialized")
        
    def _initialize_trevor_tables(self):
        """Initialize Trevor database tables."""
        try:
            trevor_db = self.get_priority_database_for_table("handler_analysis")
            if not trevor_db:
                logger.error("Trevor database not found")
                return False
                
            # Create handler_patterns table if it doesn't exist
            create_patterns_table = """
            CREATE TABLE IF NOT EXISTS handler_patterns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                handler_id INTEGER NOT NULL,
                pattern_type TEXT NOT NULL,
                pattern_text TEXT NOT NULL,
                pattern_category TEXT,
                confidence REAL DEFAULT 0.0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
            
            # Create handler_analysis table if it doesn't exist
            create_analysis_table = """
            CREATE TABLE IF NOT EXISTS handler_analysis (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                handler_name TEXT NOT NULL,
                analysis_type TEXT NOT NULL,
                analysis_data TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
            
            # Create handler_training_data table if it doesn't exist
            create_training_table = """
            CREATE TABLE IF NOT EXISTS handler_training_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                handler_name TEXT NOT NULL,
                input_text TEXT NOT NULL,
                output_text TEXT NOT NULL,
                metadata TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
            
            # Execute table creation queries
            self.execute_query(create_patterns_table, target_db=trevor_db)
            self.execute_query(create_analysis_table, target_db=trevor_db)
            self.execute_query(create_training_table, target_db=trevor_db)
            
            logger.info("Trevor database tables initialized")
            return True
            
        except Exception as e:
            logger.error(f"Error initializing Trevor tables: {str(e)}")
            return False

    def import_best_model_to_trevor(self):
        """Import the best model from filesystem into Trevor database."""
        model_path = "~/Jarvis/Core/models/checkpoints/best_model.pt"
        if not os.path.exists(model_path):
            logger.error(f"Model file not found at {model_path}")
            return False
            
        try:
            # Load model checkpoint
            checkpoint = _get_torch().load(model_path)
            model_state = checkpoint['model_state_dict']
            
            # Serialize model state dict
            buffer = io.BytesIO()
            _get_torch().save(model_state, buffer)
            model_data = buffer.getvalue()
            
            # Get metadata
            metadata = {
                'architecture': 'IntentClassifier',
                'input_size': 4000,
                'hidden_size': 2048,
                'output_size': 559,
                'accuracy': 99.8,
                'file_size_mb': os.path.getsize(model_path) / (1024 * 1024),
                'import_date': datetime.now().isoformat()
            }
            
            # Insert model into V2 intelligence database
            with v2_connection("intelligence") as conn:
                conn.execute("BEGIN IMMEDIATE")
                conn.execute("UPDATE model_storage SET is_latest = 0")
                conn.execute("""
                    INSERT INTO model_storage
                    (model_data, version, metadata, accuracy, is_latest)
                    VALUES (?, ?, ?, ?, 1)
                """, (
                    model_data,
                    'best_model_v1',
                    json.dumps(metadata),
                    99.8
                ))
                conn.execute("COMMIT")
            logger.info("Successfully imported best model into V2 intelligence database")
            
            # Clear any cached models
            if hasattr(self, '_cached_models'):
                self._cached_models = {}
                
            return True
            
        except Exception as e:
            logger.error(f"Error importing model: {str(e)}")
            return False
            
    # Agent Registry Methods
    def register_agent(self, agent_id: str, agent_name: str, agent_type: str,
                       module_name: str, capabilities: List[str] = None,
                       metadata: Dict[str, Any] = None) -> bool:
        """
        Register an agent in the agent registry database.
        
        Args:
            agent_id: Unique identifier for the agent
            agent_name: Human-readable name for the agent
            agent_type: Type of agent (e.g., orchestrator_agent, handler_bridge)
            module_name: Module the agent belongs to
            capabilities: List of agent capabilities
            metadata: Additional agent metadata
            
        Returns:
            bool: True if registration was successful
        """
        if not self.initialized:
            self.initialize()
            
        # Serialize capabilities and metadata
        capabilities_json = json.dumps(capabilities or [])
        metadata_json = json.dumps(metadata or {})
        
        # Get current timestamp
        current_time = time.time()
        
        # Check if agent already exists
        query = "SELECT agent_id FROM agent_registry WHERE agent_id = ?"
        existing_agents = self.execute_query(query, (agent_id,), target_table="agent_registry")
        existing_agent = existing_agents[0] if existing_agents else None
        
        if existing_agent:
            # Update existing agent
            query = """
            UPDATE agent_registry
            SET agent_name = ?, agent_type = ?, module_name = ?,
                capabilities = ?, updated_at = ?, metadata = ?
            WHERE agent_id = ?
            """
            params = (agent_name, agent_type, module_name,
                     capabilities_json, current_time, metadata_json, agent_id)
        else:
            # Insert new agent
            query = """
            INSERT INTO agent_registry
            (agent_id, agent_name, agent_type, module_name, capabilities, 
             created_at, updated_at, metadata, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'active')
            """
            params = (agent_id, agent_name, agent_type, module_name, capabilities_json,
                     current_time, current_time, metadata_json)
        
        try:
            cursor = self.execute_query(query, params, target_table="agent_registry")
            if cursor is not None:
                logger.info(f"Agent {agent_id} registered in agent_registry")
                
                # Initialize performance tracking for the agent if it's not already there
                self._initialize_agent_performance_tracking(agent_id, agent_name, agent_type)
                
                return True
            else:
                logger.warning(f"Failed to register agent {agent_id} in agent_registry")
                return False
        except Exception as e:
            logger.error(f"Error registering agent in database: {str(e)}")
            return False
    
    def _initialize_agent_performance_tracking(self, agent_id: str, agent_name: str, agent_type: str) -> bool:
        """
        Initialize performance tracking for an agent in the orchestrator_agent_performance table.
        """
        # Check if entry already exists
        query = "SELECT agent_id FROM orchestrator_agent_performance WHERE agent_id = ?"
        existing_entries = self.execute_query(query, (agent_id,), target_table="orchestrator_agent_performance")
        existing_entry = existing_entries[0] if existing_entries else None
        
        if not existing_entry:
            # Create a new entry with default values
            query = """
            INSERT INTO orchestrator_agent_performance
            (agent_id, requests, successes, failures, total_time, avg_time, success_rate, last_updated)
            VALUES (?, 0, 0, 0, 0.0, 0.0, 0.0, ?)
            """
            try:
                result = self.execute_query(query, (agent_id, time.time()), 
                                          target_table="orchestrator_agent_performance")
                if result is not None:
                    logger.info(f"Initialized performance tracking for agent {agent_id}")
                    return True
            except Exception as e:
                logger.error(f"Error initializing performance tracking: {str(e)}")
                
        return False
    
    def update_agent_performance(self, agent_id: str, success: bool, 
                              response_time: float, metadata: Dict[str, Any] = None) -> bool:
        """
        Update performance metrics for an agent.
        
        Args:
            agent_id: The agent ID to update metrics for
            success: Whether the operation was successful
            response_time: Time taken to respond in seconds
            metadata: Optional additional metadata about the operation
            
        Returns:
            bool: True if update was successful
        """
        if not self.initialized:
            self.initialize()
            
        # Get current timestamp
        current_time = time.time()
        
        # First, update the orchestrator_agent_performance table
        try:
            # Get current metrics
            query = """
            SELECT requests, successes, failures, total_time, avg_time
            FROM orchestrator_agent_performance
            WHERE agent_id = ?
            """
            metrics_list = self.execute_query(query, (agent_id,), target_table="orchestrator_agent_performance")
            metrics = metrics_list[0] if metrics_list else None
            
            if metrics:
                # Update metrics based on current operation
                requests = metrics['requests'] + 1
                successes = metrics['successes'] + (1 if success else 0)
                failures = metrics['failures'] + (0 if success else 1)
                total_time = metrics['total_time'] + response_time
                avg_time = total_time / requests
                success_rate = successes / requests if requests > 0 else 0.0
                
                # Update the table
                query = """
                UPDATE orchestrator_agent_performance
                SET requests = ?, successes = ?, failures = ?,
                    total_time = ?, avg_time = ?, success_rate = ?, last_updated = ?
                WHERE agent_id = ?
                """
                params = (requests, successes, failures, total_time, avg_time, 
                         success_rate, current_time, agent_id)
                
                result = self.execute_query(query, params, target_table="orchestrator_agent_performance")
                if result is None:
                    logger.warning(f"Failed to update performance for agent {agent_id}")
                    
            else:
                # Agent doesn't exist in performance table, try to initialize
                self._initialize_agent_performance_tracking(agent_id, agent_id, "unknown")
                
                # Initialize with first metrics
                query = """
                UPDATE orchestrator_agent_performance
                SET requests = 1, successes = ?, failures = ?,
                    total_time = ?, avg_time = ?, success_rate = ?, last_updated = ?
                WHERE agent_id = ?
                """
                params = (1 if success else 0, 0 if success else 1, response_time, 
                         response_time, 1.0 if success else 0.0, current_time, agent_id)
                
                result = self.execute_query(query, params, target_table="orchestrator_agent_performance")
                if result is None:
                    logger.warning(f"Failed to initialize performance for agent {agent_id}")
            
            # Also add record to agent_performance table for more detailed tracking
            if metadata is None:
                metadata = {}
            
            metadata_json = json.dumps(metadata)
            
            # Insert a new performance record
            query = """
            INSERT INTO agent_performance
            (agent_id, agent_name, agent_type, workspace_id, task_id,
             success, completion_time, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """
            
            # Get agent info to extract name and type
            agent_info = self.get_agent(agent_id)
            agent_name = agent_info.get('agent_name', agent_id) if agent_info else agent_id
            agent_type = agent_info.get('agent_type', 'unknown') if agent_info else 'unknown'
            
            task_id = metadata.get('task_id', f"task_{int(current_time)}")
            workspace_id = metadata.get('workspace_id', 1)
            
            params = (agent_id, agent_name, agent_type, workspace_id, task_id,
                     1 if success else 0, response_time, metadata_json)
            
            self.execute_query(query, params, target_table="agent_performance")
            
            return True
            
        except Exception as e:
            logger.error(f"Error updating agent performance: {str(e)}")
            return False
    
    def get_agent(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """
        Get agent information from the registry.
        
        Args:
            agent_id: Unique identifier for the agent
            
        Returns:
            Dict containing agent information or None if not found
        """
        if not self.initialized:
            self.initialize()
            
        query = "SELECT * FROM agent_registry WHERE agent_id = ?"
        agents = self.execute_query(query, (agent_id,), target_table="agent_registry")
        
        if agents and len(agents) > 0:
            agent_data = agents[0]
            # Convert from database row to dict if needed
            if not isinstance(agent_data, dict):
                try:
                    agent_dict = dict(agent_data)
                except (TypeError, ValueError):
                    logger.warning(f"Could not convert agent data to dict: {agent_data}")
                    return None
            else:
                agent_dict = agent_data
            
            # Parse JSON fields
            try:
                agent_dict['capabilities'] = json.loads(agent_dict['capabilities']) if agent_dict.get('capabilities') else []
                agent_dict['metadata'] = json.loads(agent_dict['metadata']) if agent_dict.get('metadata') else {}
            except Exception as e:
                logger.warning(f"Error parsing JSON fields for agent {agent_id}: {str(e)}")
                
            return agent_dict
            
        return None
    
    def get_all_agents(self, module_name: Optional[str] = None, agent_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get all agents from the registry, optionally filtered by module or type.
        
        Args:
            module_name: Optional filter by module name
            agent_type: Optional filter by agent type
            
        Returns:
            List of agent dictionaries
        """
        if not self.initialized:
            self.initialize()
            
        query = "SELECT * FROM agent_registry WHERE status = 'active'"
        params = []
        
        if module_name:
            query += " AND module_name = ?"
            params.append(module_name)
            
        if agent_type:
            query += " AND agent_type = ?"
            params.append(agent_type)
            
        # Get query results
        cursor = self.execute_query(query, params, target_table="agent_registry")
        
        # Handle different return types from execute_query
        if cursor is None:
            # No cursor returned
            return []
        
        # The cursor is now guaranteed to be a list because of our fixes to execute_query
        # No need to check if it has fetchall() method
        agents = cursor
        
        result = []
        for agent_data in agents:
            # Convert from database row to dict
            try:
                agent_dict = dict(agent_data)
            except (TypeError, ValueError):
                # If agent_data isn't a mapping type
                if isinstance(agent_data, dict):
                    agent_dict = agent_data
                else:
                    logger.warning(f"Could not convert agent data to dict: {agent_data}")
                    continue
            
            # Parse JSON fields
            try:
                agent_dict['capabilities'] = json.loads(agent_dict['capabilities']) if agent_dict.get('capabilities') else []
                agent_dict['metadata'] = json.loads(agent_dict['metadata']) if agent_dict.get('metadata') else {}
            except Exception as e:
                logger.warning(f"Error parsing JSON fields for agent {agent_dict.get('agent_id')}: {str(e)}")
                
            result.append(agent_dict)
            
        return result
    
    def find_agents_by_capability(self, capability: str) -> List[Dict[str, Any]]:
        """
        Find agents with a specific capability.
        
        Args:
            capability: Capability to search for
            
        Returns:
            List of matching agents
        """
        all_agents = self.get_all_agents()
        matching_agents = []
        
        for agent in all_agents:
            capabilities = agent.get('capabilities', [])
            
            # Check for exact match or substring match in capabilities
            if capability in capabilities or any(capability in cap for cap in capabilities):
                matching_agents.append(agent)
                
        return matching_agents
        
    def get_agent_performance(self, agent_id: Optional[str] = None, 
                           top_n: int = 10) -> Dict[str, Any]:
        """
        Get performance metrics for agents.
        
        Args:
            agent_id: Optional specific agent ID
            top_n: Number of top agents to include
            
        Returns:
            Performance metrics dict
        """
        if not self.initialized:
            self.initialize()
            
        result = {
            "success": True,
            "timestamp": time.time()
        }
        
        try:
            if agent_id:
                # Get metrics for specific agent
                query = """
                SELECT agent_id, requests, successes, failures, 
                       total_time, avg_time, success_rate, last_updated
                FROM orchestrator_agent_performance
                WHERE agent_id = ?
                """
                cursor = self.execute_query(query, (agent_id,), target_table="orchestrator_agent_performance")
                metrics = cursor.fetchone() if cursor else None
                
                if metrics:
                    result["agent"] = dict(metrics)
                else:
                    result["success"] = False
                    result["error"] = f"No performance data found for agent {agent_id}"
                    
            else:
                # Get top N agents by success rate
                query = """
                SELECT agent_id, requests, successes, failures, 
                       total_time, avg_time, success_rate, last_updated
                FROM orchestrator_agent_performance
                WHERE requests > 0
                ORDER BY success_rate DESC, requests DESC
                LIMIT ?
                """
                cursor = self.execute_query(query, (top_n,), target_table="orchestrator_agent_performance")
                top_agents = cursor.fetchall() if cursor else []
                
                # Enhance with agent names/types
                enhanced_agents = []
                for agent_metrics in top_agents:
                    agent_info = self.get_agent(agent_metrics["agent_id"])
                    if agent_info:
                        metrics_dict = dict(agent_metrics)
                        metrics_dict["agent_name"] = agent_info.get("agent_name")
                        metrics_dict["agent_type"] = agent_info.get("agent_type")
                        enhanced_agents.append(metrics_dict)
                    else:
                        enhanced_agents.append(dict(agent_metrics))
                
                result["top_agents"] = enhanced_agents
                result["total_agents"] = len(enhanced_agents)
                
                # Add summary statistics
                if enhanced_agents:
                    total_success = sum(a.get("successes", 0) for a in enhanced_agents)
                    total_failure = sum(a.get("failures", 0) for a in enhanced_agents)
                    total_requests = sum(a.get("requests", 0) for a in enhanced_agents)
                    
                    # Calculate weighted average response time
                    weighted_times = sum(a.get("avg_time", 0) * a.get("requests", 0) 
                                      for a in enhanced_agents)
                    overall_avg_time = weighted_times / total_requests if total_requests > 0 else 0
                    
                    result["summary"] = {
                        "total_success": total_success,
                        "total_failure": total_failure,
                        "total_requests": total_requests,
                        "overall_success_rate": total_success / total_requests if total_requests > 0 else 0,
                        "overall_avg_response_time": overall_avg_time
                    }
            
            return result
            
        except Exception as e:
            logger.error(f"Error getting agent performance: {str(e)}")
            return {
                "success": False,
                "error": f"Error retrieving performance data: {str(e)}"
            }
            
    def get_all_tools(self) -> Dict[str, Dict[str, Any]]:
        """
        Get information about all available tools in the system.
        
        This method retrieves tool information from:
        - Predefined tool specifications
        - Tool registry in the database if available
        - Built-in system tools
        
        Returns:
            Dict mapping tool names to their specifications and metadata
        """
        if not self.initialized:
            self.initialize()
            
        # Cache key for tools
        cache_key = "all_tools"
        
        # Check cache first
        if cache_key in self._cache and time.time() - self._cache_timestamps.get(cache_key, 0) < 300:  # 5 minute cache
            return self._cache[cache_key]
            
        tool_info = {}
        
        # Add default system tools (these are always available)
        tool_info.update({
            "code_execution": {
                "name": "code_execution",
                "description": "Executes code in a safe environment",
                "parameters": {
                    "language": {
                        "type": "string",
                        "description": "Programming language (python, javascript, etc.)"
                    },
                    "code": {
                        "type": "string",
                        "description": "Code to execute"
                    }
                },
                "required": ["language", "code"],
                "source": "system"
            },
            "file_operations": {
                "name": "file_operations",
                "description": "Read, write, and manipulate files",
                "parameters": {
                    "operation": {
                        "type": "string",
                        "description": "Operation to perform (read, write, append, delete)",
                        "enum": ["read", "write", "append", "delete"]
                    },
                    "path": {
                        "type": "string",
                        "description": "File path"
                    },
                    "content": {
                        "type": "string",
                        "description": "Content to write (for write/append operations)"
                    }
                },
                "required": ["operation", "path"],
                "source": "system"
            },
            "web_search": {
                "name": "web_search",
                "description": "Search the web for information",
                "parameters": {
                    "query": {
                        "type": "string",
                        "description": "Search query"
                    },
                    "num_results": {
                        "type": "integer",
                        "description": "Number of results to return",
                        "default": 5
                    }
                },
                "required": ["query"],
                "source": "system"
            }
        })
        
        try:
            # Check if tools table exists in boardroom database
            conn = self.get_connection("boardroom")
            if conn:
                cursor = conn.cursor()
                
                # Check if tools table exists
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='tools'")
                if cursor.fetchone():
                    # Get tools from the tools table
                    cursor.execute("SELECT * FROM tools WHERE status = 'active'")
                    rows = cursor.fetchall()
                    
                    for row in rows:
                        row_dict = dict(row)
                        tool_name = row_dict.get('tool_name')
                        
                        if tool_name:
                            # Extract parameters from JSON if stored that way
                            params = row_dict.get('parameters')
                            if isinstance(params, str):
                                try:
                                    params = json.loads(params)
                                except:
                                    params = {}
                                    
                            tool_info[tool_name] = {
                                "name": tool_name,
                                "description": row_dict.get('description', ''),
                                "parameters": params,
                                "required": row_dict.get('required_params', '').split(',') if row_dict.get('required_params') else [],
                                "source": "database"
                            }
        except Exception as e:
            logger.warning(f"Error getting tools from tools table: {str(e)}")
            
        # Try to get tools from other sources
        try:
            # Check for tools in agent_capabilities table
            conn = self.get_connection("intelligence")
            if conn:
                cursor = conn.cursor()
                
                # Check if agent_capabilities table exists
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='agent_capabilities'")
                if cursor.fetchone():
                    # Query for tool capabilities
                    cursor.execute(
                        "SELECT capability_name, capability_type, capability_data " +
                        "FROM agent_capabilities WHERE capability_type = 'tool'"
                    )
                    rows = cursor.fetchall()
                    
                    for row in rows:
                        capability_name = row[0]
                        capability_data = row[2]
                        
                        # Parse capability data if it's JSON
                        if isinstance(capability_data, str):
                            try:
                                tool_data = json.loads(capability_data)
                                
                                tool_info[capability_name] = {
                                    "name": capability_name,
                                    "description": tool_data.get('description', ''),
                                    "parameters": tool_data.get('parameters', {}),
                                    "required": tool_data.get('required', []),
                                    "source": "capabilities"
                                }
                            except:
                                pass
        except Exception as e:
            logger.warning(f"Error getting tools from agent_capabilities: {str(e)}")
            
        # Cache the results
        self._cache[cache_key] = tool_info
        self._cache_timestamps[cache_key] = time.time()
        
        return tool_info
        
    def get_all_handlers(self) -> Dict[str, Dict[str, Any]]:
        """
        Get information about all available handlers in the system.
        
        This method aggregates handler information from multiple sources:
        - The handlers table
        - The handler_data table
        - The handler_performance table
        - Generated from pattern metrics
        
        Returns:
            Dict mapping handler names to their capabilities and metadata
        """
        if not self.initialized:
            self.initialize()
            
        handler_info = {}
        
        try:
            # First, get basic handler info from handlers table
            query = "SELECT * FROM handlers"
            handlers = self.execute_query(query, target_table="handlers")
            
            if handlers:
                for handler in handlers:
                    handler_name = handler.get('handler_name')
                    if handler_name:
                        handler_info[handler_name] = {
                            'name': handler_name,
                            'type': handler.get('handler_type', 'unknown'),
                            'category': handler.get('handler_category', 'general'),
                            'file_path': handler.get('file_path', ''),
                            'created_at': handler.get('created_at', '')
                        }
            
            # Enhance with data from handler_data table
            query = "SELECT * FROM handler_data"
            handler_data = self.execute_query(query, target_table="handler_data")
            
            if handler_data:
                for data in handler_data:
                    handler_name = data.get('handler_name')
                    if handler_name:
                        if handler_name not in handler_info:
                            handler_info[handler_name] = {
                                'name': handler_name,
                                'type': 'unknown',
                                'category': 'general'
                            }
                            
                        # Parse capabilities and metadata
                        try:
                            if data.get('capabilities'):
                                capabilities = json.loads(data.get('capabilities')) if isinstance(data.get('capabilities'), str) else data.get('capabilities')
                                handler_info[handler_name]['capabilities'] = capabilities
                            
                            if data.get('patterns'):
                                patterns = json.loads(data.get('patterns')) if isinstance(data.get('patterns'), str) else data.get('patterns')
                                handler_info[handler_name]['patterns'] = patterns
                                
                            if data.get('metadata'):
                                metadata = json.loads(data.get('metadata')) if isinstance(data.get('metadata'), str) else data.get('metadata')
                                handler_info[handler_name]['metadata'] = metadata
                        except json.JSONDecodeError as e:
                            logger.warning(f"Error parsing JSON for handler {handler_name}: {str(e)}")
            
            # Add performance metrics from handler_performance table
            for handler_name in handler_info.keys():
                performance_data = self.get_handler_performance_data(handler_name=handler_name)
                
                if performance_data:
                    # Aggregate metrics
                    total_requests = len(performance_data)
                    successes = sum(1 for p in performance_data if p.get('success') == 1)
                    avg_time = sum(p.get('execution_time', 0) for p in performance_data) / total_requests if total_requests > 0 else 0
                    
                    handler_info[handler_name]['performance'] = {
                        'total_requests': total_requests,
                        'success_rate': successes / total_requests if total_requests > 0 else 0,
                        'avg_execution_time': avg_time
                    }
            
            logger.info(f"Retrieved information for {len(handler_info)} handlers")
            return handler_info
            
        except Exception as e:
            logger.error(f"Error getting all handlers: {str(e)}")
            logger.debug(traceback.format_exc())
            return {}
            
    def get_all_tools(self) -> Dict[str, Dict[str, Any]]:
        """
        Get information about all available tools in the system.
        
        This method retrieves tool information from:
        - Predefined tool specifications
        - Tool registry in the database if available
        - Built-in system tools
        
        Returns:
            Dict mapping tool names to their specifications and metadata
        """
        if not self.initialized:
            self.initialize()
        
        tools_info = {}
        
        try:
            # First, try to get tools from the tools table if it exists
            try:
                query = "SELECT * FROM tools"
                tools_data = self.execute_query(query, target_table="tools")
                
                if tools_data:
                    for tool in tools_data:
                        tool_name = tool.get('tool_name')
                        if tool_name:
                            tools_info[tool_name] = {
                                'name': tool_name,
                                'type': tool.get('tool_type', 'unknown'),
                                'category': tool.get('tool_category', 'general'),
                                'description': tool.get('description', ''),
                                'created_at': tool.get('created_at', '')
                            }
                            
                            # Parse schema if available
                            if tool.get('schema'):
                                try:
                                    schema = json.loads(tool.get('schema')) if isinstance(tool.get('schema'), str) else tool.get('schema')
                                    tools_info[tool_name]['schema'] = schema
                                except json.JSONDecodeError:
                                    logger.warning(f"Error parsing schema for tool {tool_name}")
            except Exception as e:
                logger.debug(f"Tool table might not exist: {str(e)}")
            
            # If no tools found, check tools_registry table as an alternative
            if not tools_info:
                try:
                    query = "SELECT * FROM tools_registry"
                    registry_data = self.execute_query(query, target_table="tools_registry")
                    
                    if registry_data:
                        for tool in registry_data:
                            tool_name = tool.get('name')
                            if tool_name:
                                tools_info[tool_name] = {
                                    'name': tool_name,
                                    'type': tool.get('type', 'unknown'),
                                    'description': tool.get('description', ''),
                                    'module': tool.get('module', ''),
                                    'version': tool.get('version', '1.0')
                                }
                                
                                # Parse additional fields if available
                                for field in ['parameters', 'metadata', 'schema']:
                                    if tool.get(field):
                                        try:
                                            parsed_value = json.loads(tool.get(field)) if isinstance(tool.get(field), str) else tool.get(field)
                                            tools_info[tool_name][field] = parsed_value
                                        except json.JSONDecodeError:
                                            logger.warning(f"Error parsing {field} for tool {tool_name}")
                except Exception as e:
                    logger.debug(f"Tools registry table might not exist: {str(e)}")
            
            # Add default system tools if no tools found in database
            if not tools_info:
                # Define default system tools
                default_tools = {
                    "web_search": {
                        "name": "web_search",
                        "type": "web",
                        "category": "search",
                        "description": "Search the web for information",
                        "parameters": {
                            "query": {"type": "string", "description": "Search query"}
                        }
                    },
                    "calculator": {
                        "name": "calculator",
                        "type": "math",
                        "category": "utility",
                        "description": "Perform mathematical calculations",
                        "parameters": {
                            "expression": {"type": "string", "description": "Mathematical expression to evaluate"}
                        }
                    },
                    "code_executor": {
                        "name": "code_executor",
                        "type": "code",
                        "category": "development",
                        "description": "Execute code in various languages",
                        "parameters": {
                            "code": {"type": "string", "description": "Code to execute"},
                            "language": {"type": "string", "description": "Programming language"}
                        }
                    }
                }
                
                # Add default tools to result
                tools_info.update(default_tools)
            
            logger.info(f"Retrieved information for {len(tools_info)} tools")
            return tools_info
            
        except Exception as e:
            logger.error(f"Error getting all tools: {str(e)}")
            logger.debug(traceback.format_exc())
            return {}
            
    def find_best_agent_version(self, base_agent_id: str, min_requests: int = 5,
                             capability_requirements: List[str] = None) -> Dict[str, Any]:
        """
        Find the best performing version of an agent.
        
        Args:
            base_agent_id: The base agent ID to find the best version for
            min_requests: Minimum number of requests for consideration
            capability_requirements: Required capabilities
            
        Returns:
            Dict with the best agent version information
        """
        if not self.initialized:
            self.initialize()
            
        try:
            # First find all versions of this agent (using LIKE query)
            pattern = f"{base_agent_id}%"
            
            query = """
            SELECT a.*, p.requests, p.successes, p.failures, p.avg_time, p.success_rate
            FROM agent_registry a
            LEFT JOIN orchestrator_agent_performance p ON a.agent_id = p.agent_id
            WHERE (a.agent_id = ? OR a.agent_id LIKE ?)
            AND a.status = 'active'
            AND (p.requests >= ? OR p.requests IS NULL)
            """
            
            params = (base_agent_id, pattern, min_requests)
            
            cursor = self.execute_query(query, params, target_table="agent_registry")
            rows = cursor.fetchall() if cursor else []
            
            if not rows:
                return {
                    "success": False,
                    "error": f"No agent versions found for {base_agent_id} with at least {min_requests} requests"
                }
                
            # Convert to list of dictionaries
            agent_versions = []
            for row in rows:
                agent_data = dict(row)
                
                # Parse JSON fields
                try:
                    agent_data['capabilities'] = json.loads(agent_data['capabilities']) if agent_data.get('capabilities') else []
                    agent_data['metadata'] = json.loads(agent_data['metadata']) if agent_data.get('metadata') else {}
                except Exception as e:
                    logger.warning(f"Error parsing JSON for agent {agent_data.get('agent_id')}: {str(e)}")
                
                # Check capability requirements if specified
                if capability_requirements:
                    agent_capabilities = agent_data.get('capabilities', [])
                    has_all_capabilities = all(cap in agent_capabilities for cap in capability_requirements)
                    if not has_all_capabilities:
                        continue
                        
                agent_versions.append(agent_data)
                
            if not agent_versions:
                error_message = f"No agent versions found for {base_agent_id}"
                if capability_requirements:
                    error_message += f" with required capabilities: {', '.join(capability_requirements)}"
                return {
                    "success": False,
                    "error": error_message
                }
                
            # Define scoring function that balances success rate and response time
            # This gives 70% weight to success rate and 30% weight to response time
            def calculate_score(agent):
                # Default values if metrics are missing
                success_rate = agent.get("success_rate", 0.0)
                avg_time = agent.get("avg_time", 10.0)  # Assume worst time if missing
                
                # Normalize response time (lower is better)
                # We use an upper bound of 10 seconds for normalization
                normalized_time_score = max(0, 1 - (avg_time / 10))
                
                # Calculate the combined score
                return (success_rate * 0.7) + (normalized_time_score * 0.3)
                
            # Calculate scores and find the best
            for agent in agent_versions:
                agent["score"] = calculate_score(agent)
                
            # Find the best agent
            best_agent = max(agent_versions, key=lambda x: x.get("score", 0))
            
            return {
                "success": True,
                "agent": best_agent,
                "score": best_agent.get("score", 0)
            }
            
        except Exception as e:
            logger.error(f"Error finding best agent version: {str(e)}")
            return {
                "success": False,
                "error": f"Error finding best agent version: {str(e)}"
            }

    def initialize_all_connections(self):
        """
        Initialize all database connections needed for full integration.
        This method ensures that all necessary databases are connected and ready
        for high-performance access by systems like Trevor Core.
        
        Returns:
            Boolean indicating if initialization was successful
        """
        logger.info("Initializing all database connections for complete integration")
        
        # Make sure we're fully initialized
        if not self.initialized:
            self.initialize()
            
        success = True
            
        # Connect to all databases in the default paths
        for db_name, db_path in DEFAULT_DB_PATHS.items():
            try:
                if os.path.exists(db_path):
                    conn = self.get_connection(db_name)
                    if conn:
                        logger.info(f"Connected to {db_name} database for integration")
                    else:
                        logger.warning(f"Failed to connect to {db_name} at {db_path}")
                        success = False
                else:
                    logger.warning(f"Database path doesn't exist: {db_path}")
            except Exception as e:
                logger.error(f"Error connecting to {db_name} database: {str(e)}")
                success = False
        
        # Ensure journey tracking is ready
        try:
            self.ensure_journey_tracking_tables()
            logger.info("Journey tracking tables initialized for integration")
        except Exception as e:
            logger.warning(f"Error ensuring journey tracking tables: {str(e)}")
            
        logger.info(f"Database directory initialization complete with status: {'success' if success else 'partial failure'}")
        return success

    def get_workspace_teams(self):
        """
        Get workspace teams from the database with thread-safe connection.
        
        Returns:
            List of team dictionaries or empty list if none found
        """
        try:
            query = "SELECT * FROM teams"
            results = self.execute_query(query, target_db="boardroom")
            if results:
                logger.info(f"Found {len(results)} workspace teams")
                return results
            else:
                logger.info("No workspace teams found")
                return []
        except Exception as e:
            logger.error(f"Error getting workspace teams: {str(e)}")
            return []

    def get_workspace_tasks(self):
        """
        Get workspace tasks from the database with thread-safe connection.
        
        Returns:
            List of task dictionaries or empty list if none found
        """
        try:
            query = "SELECT * FROM workspace_tasks"
            results = self.execute_query(query, target_db="boardroom")
            if results:
                logger.info(f"Found {len(results)} workspace tasks")
                return results
            else:
                logger.info("No workspace tasks found")
                return []
        except Exception as e:
            logger.error(f"Error getting workspace tasks: {str(e)}")
            return []

    def get_workspace_resources(self):
        """
        Get workspace resources from the database with thread-safe connection.
        
        Returns:
            List of resource dictionaries or empty list if none found
        """
        try:
            # Try multiple potential resource tables
            resource_tables = ["workspaces", "workspace_shares", "workspace_relationships"]
            all_resources = []
            
            for table in resource_tables:
                try:
                    query = f"SELECT * FROM {table}"
                    results = self.execute_query(query, target_db="boardroom")
                    if results:
                        all_resources.extend(results)
                        logger.info(f"Found {len(results)} items in {table}")
                except Exception as table_error:
                    logger.debug(f"Table {table} not found or inaccessible: {str(table_error)}")
                    continue
            
            logger.info(f"Found {len(all_resources)} total workspace resources")
            return all_resources
            
        except Exception as e:
            logger.error(f"Error getting workspace resources: {str(e)}")
            return []
    
    # Claude Dual Feedback System Database Methods
    
    def create_feedback_conversation(self, session_id: str, source: str, request: str) -> int:
        """
        Create new feedback conversation record
        
        Args:
            session_id: Session identifier for the conversation
            source: Source of the feedback request ('boardroom' or 'jarvis_orchestrator')
            request: The feedback request text
            
        Returns:
            conversation_id: ID of the created conversation record
        """
        try:
            query = """
                INSERT INTO feedback_conversations 
                (session_id, source, feedback_request, status, created_at)
                VALUES (?, ?, ?, 'active', CURRENT_TIMESTAMP)
            """
            
            # Execute the insert query
            self.execute_query(query, (session_id, source, request), target_db="intelligence")
            
            # Get the last inserted ID
            id_query = "SELECT last_insert_rowid()"
            result = self.execute_query(id_query, target_db="intelligence")
            
            conversation_id = result[0][0] if result and result[0] else None
            
            if conversation_id:
                logger.info(f"Created feedback conversation {conversation_id} for session {session_id}")
                return conversation_id
            else:
                logger.error(f"Failed to get conversation ID for session {session_id}")
                return None
                
        except Exception as e:
            logger.error(f"Error creating feedback conversation: {str(e)}")
            return None
    
    def update_feedback_conversation(self, conversation_id: int, history: list, status: str = None):
        """
        Update conversation history and status
        
        Args:
            conversation_id: ID of the conversation to update
            history: List of conversation messages
            status: Optional status update ('active', 'completed', 'failed')
        """
        try:
            import json
            
            # Convert history to JSON string
            history_json = json.dumps(history) if history else None
            
            if status:
                # Update both history and status
                query = """
                    UPDATE feedback_conversations 
                    SET conversation_history = ?, status = ?, completed_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """
                self.execute_query(query, (history_json, status, conversation_id), target_db="intelligence")
            else:
                # Update only history
                query = """
                    UPDATE feedback_conversations 
                    SET conversation_history = ?
                    WHERE id = ?
                """
                self.execute_query(query, (history_json, conversation_id), target_db="intelligence")
            
            logger.info(f"Updated feedback conversation {conversation_id}")
            
        except Exception as e:
            logger.error(f"Error updating feedback conversation {conversation_id}: {str(e)}")
    
    def log_enhanced_response(self, conversation_id: int, original: str, enhanced: str, metadata: dict):
        """
        Log Claude's enhanced response
        
        Args:
            conversation_id: ID of the feedback conversation
            original: Original response before enhancement
            enhanced: Enhanced response from Claude
            metadata: Additional metadata (personality, sentiment analysis, etc.)
        """
        try:
            import json
            
            query = """
                INSERT INTO enhanced_responses 
                (conversation_id, original_response, enhanced_response, claude_personality, sentiment_analysis, created_at)
                VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """
            
            claude_personality = metadata.get('personality_type', '')
            sentiment_json = json.dumps(metadata.get('sentiment_analysis', {}))
            
            self.execute_query(
                query, 
                (conversation_id, original, enhanced, claude_personality, sentiment_json),
                target_db="intelligence"
            )
            
            logger.info(f"Logged enhanced response for conversation {conversation_id}")
            
        except Exception as e:
            logger.error(f"Error logging enhanced response for conversation {conversation_id}: {str(e)}")
    
    def get_feedback_conversation(self, session_id: str) -> Optional[dict]:
        """
        Get feedback conversation by session ID
        
        Args:
            session_id: Session identifier
            
        Returns:
            Dictionary with conversation data or None if not found
        """
        try:
            import json
            
            query = """
                SELECT id, session_id, source, feedback_request, conversation_history, 
                       status, created_at, completed_at
                FROM feedback_conversations 
                WHERE session_id = ?
                ORDER BY created_at DESC
                LIMIT 1
            """
            
            result = self.execute_query(query, (session_id,), target_db="intelligence")
            
            if result and result[0]:
                row = result[0]
                conversation = {
                    'id': row[0],
                    'session_id': row[1],
                    'source': row[2],
                    'feedback_request': row[3],
                    'conversation_history': json.loads(row[4]) if row[4] else [],
                    'status': row[5],
                    'created_at': row[6],
                    'completed_at': row[7]
                }
                return conversation
            else:
                return None
                
        except Exception as e:
            logger.error(f"Error getting feedback conversation for session {session_id}: {str(e)}")
            return None
    
    def get_active_feedback_conversations(self) -> list:
        """
        Get all active feedback conversations
        
        Returns:
            List of active conversation dictionaries
        """
        try:
            query = """
                SELECT id, session_id, source, feedback_request, status, created_at
                FROM feedback_conversations 
                WHERE status = 'active'
                ORDER BY created_at DESC
            """
            
            result = self.execute_query(query, target_db="intelligence")
            
            conversations = []
            if result:
                for row in result:
                    conversation = {
                        'id': row[0],
                        'session_id': row[1],
                        'source': row[2],
                        'feedback_request': row[3],
                        'status': row[4],
                        'created_at': row[5]
                    }
                    conversations.append(conversation)
            
            return conversations
            
        except Exception as e:
            logger.error(f"Error getting active feedback conversations: {str(e)}")
            return []

# Global instance for easier access with thread safety
import threading
_directory_instance = None
_directory_lock = threading.Lock()
_global_initialized = False

def get_database_directory():
    """
    Get or create the global database directory instance with thread safety.

    Returns:
        DatabaseDirectory instance
    """
    global _directory_instance, _global_initialized

    if _directory_instance is None:
        with _directory_lock:
            if _directory_instance is None:
                _directory_instance = DatabaseDirectory()
                if not _global_initialized:
                    _directory_instance.initialize()
                    _global_initialized = True

    return _directory_instance 

# Simple test case when module is run directly
if __name__ == "__main__":
    import time
    print("Testing enhanced DatabaseDirectory...")
    
    db = DatabaseDirectory()
    db.initialize()
    
    print("Testing loading model data...")
    model_info = db.get_trevor_model_data()
    if model_info:
        print(f"Model version: {model_info.get('version')}")
        print(f"Model accuracy: {model_info.get('accuracy')}%")
    
    print("Testing loading full tokenized model...")
    try:
        model = db.load_pytorch_model()
        if model:
            print(f"Successfully loaded model {model.get('version')}")
            print(f"Enhanced tokenizer config: {model.get('tokenizer_config')}")
            print(f"Model has vocabulary: {model.get('vocabulary') is not None}")
            print(f"Model has class labels: {model.get('class_labels') is not None}")
    except Exception as e:
        print(f"Error loading model: {str(e)}") 