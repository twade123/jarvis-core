"""
Unified Database Implementation for Jarvis Agent SDK

This module provides a concrete implementation of the DatabaseBase interface
for SQLite databases, enabling unified database access across different
components of the system without circular dependencies.
"""

import os
import sqlite3
import logging
import time
import json
from typing import List, Dict, Any, Optional, Tuple, Union
from contextlib import contextmanager

from .base import DatabaseBase

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class SQLiteDatabase(DatabaseBase):
    """
    SQLite implementation of the unified database interface.
    
    This class provides concrete implementations of all the methods defined in
    DatabaseBase for SQLite databases, allowing for a unified database access
    pattern across the system.
    """
    
    def __init__(self, db_path=None, connection=None, row_factory=sqlite3.Row, create_new_connection=False):
        """
        Initialize the SQLite database.
        
        Args:
            db_path: Path to the SQLite database file
            connection: Existing SQLite connection
            row_factory: Row factory for query results
            create_new_connection: Force creation of a new connection even if one is provided
        """
        super().__init__(db_path, connection)
        self.row_factory = row_factory
        self._last_error = None
        self._query_count = 0
        
        # If create_new_connection is True, ignore any existing connection
        if create_new_connection and self.db_path:
            self.connection = None
            self.is_connected = False
            logger.info(f"Creating new thread-specific connection to {db_path}")
        
        # Connect if we have a db_path and no connection
        if self.db_path and not self.connection:
            self.connect()
    
    def connect(self):
        """
        Establish a connection to the SQLite database.
        
        Returns:
            True if connected successfully, False otherwise
        """
        try:
            if not self.db_path:
                raise ValueError("Database path not provided")
            
            # Skip for in-memory databases
            if self.db_path != ":memory:":    
                # Create the directory if it doesn't exist
                db_dir = os.path.dirname(self.db_path)
                os.makedirs(db_dir, exist_ok=True)
                
                # Check directory permissions
                if not os.access(db_dir, os.W_OK):
                    self._last_error = f"Database directory {db_dir} is not writable"
                    logger.error(self._last_error)
                    return False
            
            # Connect to the database with timeout and retries
            max_retries = 3
            retry_count = 0
            while retry_count < max_retries:
                try:
                    if self.db_path == ":memory:":
                        logger.info("Connecting to in-memory SQLite database")
                    else:
                        logger.info(f"Connecting to SQLite database at {self.db_path}")
                    
                    self.connection = sqlite3.connect(self.db_path, timeout=20.0, isolation_level=None)
                    
                    # Set the row factory if provided
                    if self.row_factory:
                        self.connection.row_factory = self.row_factory
                    
                    # Enable foreign keys
                    self.connection.execute("PRAGMA foreign_keys = ON")
                    
                    # Set journal mode to WAL for better concurrency
                    if self.db_path != ":memory:":
                        self.connection.execute("PRAGMA journal_mode=DELETE")
                    
                    # Test the connection
                    test_cursor = self.connection.cursor()
                    test_cursor.execute("SELECT 1")
                    test_cursor.fetchone()
                    
                    self.is_connected = True
                    logger.info(f"Successfully connected to SQLite database at {self.db_path}")
                    
                    return True
                except sqlite3.OperationalError as oe:
                    retry_count += 1
                    wait_time = retry_count * 2  # Exponential backoff
                    
                    if "database is locked" in str(oe) and retry_count < max_retries:
                        logger.warning(f"Database locked, retrying in {wait_time} seconds (attempt {retry_count}/{max_retries})")
                        time.sleep(wait_time)
                    else:
                        self._last_error = str(oe)
                        logger.error(f"Error connecting to database: {str(oe)}")
                        return False
                except Exception as e:
                    self._last_error = str(e)
                    logger.error(f"Error connecting to database: {str(e)}")
                    return False
            
            return False
        except Exception as e:
            self._last_error = str(e)
            logger.error(f"Error connecting to database: {str(e)}")
            return False
    
    def disconnect(self):
        """
        Close the database connection.
        
        Returns:
            True if disconnected successfully, False otherwise
        """
        try:
            if self.connection:
                self.connection.close()
                self.is_connected = False
                self.connection = None
                logger.info("Disconnected from SQLite database")
                return True
            return True  # Already disconnected
        except Exception as e:
            self._last_error = str(e)
            logger.error(f"Error disconnecting from database: {str(e)}")
            return False
    
    def execute_query(self, query, params=None):
        """
        Execute an SQL query on the database.
        
        Args:
            query: SQL query to execute
            params: Optional parameters for the query
            
        Returns:
            Cursor object for the query result
        """
        try:
            if not self.is_connected:
                self.connect()
                
            if not self.connection:
                raise RuntimeError("No database connection available")
                
            cursor = self.connection.cursor()
            
            # Log query for debugging (sanitized)
            query_start = time.time()
            
            # Execute the query
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
                
            # Log execution time for performance monitoring
            query_time = time.time() - query_start
            self._query_count += 1
            
            if query_time > 1.0:  # Log slow queries
                logger.warning(f"Slow query ({query_time:.2f}s): {query[:100]}...")
            
            return cursor
        except Exception as e:
            self._last_error = str(e)
            logger.error(f"Error executing query: {str(e)}")
            raise
    
    def commit(self):
        """
        Commit pending transactions.
        
        Returns:
            True if committed successfully, False otherwise
        """
        try:
            if self.connection:
                self.connection.commit()
                return True
            return False
        except Exception as e:
            self._last_error = str(e)
            logger.error(f"Error committing transaction: {str(e)}")
            return False
    
    def rollback(self):
        """
        Rollback pending transactions.
        
        Returns:
            True if rolled back successfully, False otherwise
        """
        try:
            if self.connection:
                self.connection.rollback()
                return True
            return False
        except Exception as e:
            self._last_error = str(e)
            logger.error(f"Error rolling back transaction: {str(e)}")
            return False
    
    def get_connection(self):
        """
        Get the underlying database connection.
        
        Returns:
            SQLite connection object
        """
        if not self.is_connected:
            self.connect()
        return self.connection
    
    def execute_transaction(self, queries):
        """
        Execute multiple queries as a single transaction.
        
        Args:
            queries: List of (query, params) tuples
            
        Returns:
            True if transaction completed successfully, False otherwise
        """
        try:
            if not self.is_connected:
                self.connect()
                
            if not self.connection:
                raise RuntimeError("No database connection available")
                
            # Start transaction
            self.connection.execute("BEGIN TRANSACTION")
            
            for query, params in queries:
                if params:
                    self.connection.execute(query, params)
                else:
                    self.connection.execute(query)
                    
            # Commit the transaction
            self.connection.commit()
            return True
        except Exception as e:
            # Rollback on error
            if self.connection:
                self.connection.rollback()
                
            self._last_error = str(e)
            logger.error(f"Transaction failed: {str(e)}")
            return False
    
    @contextmanager
    def transaction(self):
        """
        Context manager for database transactions.
        
        Usage:
            with db.transaction():
                db.execute_query("INSERT INTO ...", params)
                db.execute_query("UPDATE ...", params)
        """
        try:
            self.connection.execute("BEGIN TRANSACTION")
            yield
            self.connection.commit()
        except Exception as e:
            self.connection.rollback()
            self._last_error = str(e)
            logger.error(f"Transaction failed: {str(e)}")
            raise
    
    def get_last_error(self):
        """
        Get the last error message.
        
        Returns:
            Last error message or None if no error occurred
        """
        return self._last_error
    
    def get_query_count(self):
        """Get the number of queries executed."""
        return self._query_count
    
    def reset_query_count(self):
        """Reset the query counter to zero."""
        self._query_count = 0
        return True
        
    def execute_query_with_result(self, query, params=None):
        """
        Execute a query and fetch all results.
        
        Args:
            query: SQL query to execute
            params: Optional parameters for the query
            
        Returns:
            List of rows from the query result
        """
        cursor = self.execute_query(query, params)
        return cursor.fetchall()
    
    def execute_query_with_single_result(self, query, params=None):
        """
        Execute a query and fetch a single result.
        
        Args:
            query: SQL query to execute
            params: Optional parameters for the query
            
        Returns:
            Single row from the query result or None
        """
        cursor = self.execute_query(query, params)
        return cursor.fetchone()
    
    def table_exists(self, table_name):
        """
        Check if a table exists in the database.
        
        Args:
            table_name: Name of the table to check
            
        Returns:
            True if table exists, False otherwise
        """
        try:
            if not self.is_connected:
                self.connect()
                
            if not self.connection:
                return False
                
            cursor = self.connection.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table_name,))
            return cursor.fetchone() is not None
        except Exception as e:
            self._last_error = str(e)
            logger.error(f"Error checking if table exists: {str(e)}")
            return False
    
    def get_tables(self):
        """
        Get a list of all tables in the database.
        
        Returns:
            List of table names
        """
        try:
            if not self.is_connected:
                self.connect()
                
            if not self.connection:
                return []
                
            cursor = self.connection.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]
            return tables
        except Exception as e:
            self._last_error = str(e)
            logger.error(f"Error getting tables: {str(e)}")
            return []
        
# Global singleton instance
_unified_database = None

def get_unified_database(db_path=None):
    """
    Get or create the unified database instance.
    
    Args:
        db_path: Optional database path
        
    Returns:
        SQLiteDatabase instance
    """
    global _unified_database
    
    if _unified_database is None and db_path:
        _unified_database = SQLiteDatabase(db_path)
        # Ensure connection is initialized
        if not _unified_database.is_connected:
            _unified_database.connect()
    
    return _unified_database 