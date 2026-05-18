"""Shared database utilities for handler analysis."""

import sqlite3
import logging
from typing import Dict, List, Set, Tuple, Any, Union

# Import agent-related components for specialized agent integration
try:
    from Jarvis_Agent_SDK.jarvis_orchestrator import analyze_handler_capabilities
    from Handler.handler_agent_builder import AgentBuilder, AgentType, AgentSpecialization, AgentCapability, AgentTool
except ImportError:
    # Allow the handler to function even if agent components can't be imported
    print("Warning: Agent components not available - specialized agent features disabled")

class DatabaseConnection:
    """Base class for database connections."""
    
    def __init__(self, db_connection):
        """Initialize with an existing database connection."""
        self.conn = db_connection
        self.cursor = self.conn.cursor()
        self._keep_alive = True  # Flag to control connection lifetime
        
    def init_database(self):
        """Initialize database tables."""
        try:
            # Create all necessary tables in one place
            tables = {
                'handlers': '''
                    CREATE TABLE IF NOT EXISTS handlers (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        handler_name TEXT NOT NULL,
                        handler_type TEXT NOT NULL,
                        handler_category TEXT NOT NULL,
                        file_path TEXT NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''',
                'patterns': '''
                    CREATE TABLE IF NOT EXISTS handler_patterns (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        handler_id INTEGER NOT NULL,
                        pattern_type TEXT NOT NULL,
                        pattern_text TEXT NOT NULL,
                        pattern_category TEXT NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (handler_id) REFERENCES handlers(id)
                    )
                ''',
                'pattern_mapping': '''
                    CREATE TABLE IF NOT EXISTS pattern_mapping (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        handler_id INTEGER NOT NULL,
                        pattern_type TEXT NOT NULL,
                        pattern_value TEXT NOT NULL,
                        similarity_score REAL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (handler_id) REFERENCES handlers(id)
                    )
                ''',
                'intents': '''
                    CREATE TABLE IF NOT EXISTS intents (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT NOT NULL,
                        category TEXT NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''',
                'examples': '''
                    CREATE TABLE IF NOT EXISTS examples (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        intent_id INTEGER NOT NULL,
                        text TEXT NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (intent_id) REFERENCES intents(id)
                    )
                ''',
                'actions': '''
                    CREATE TABLE IF NOT EXISTS actions (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        intent_id INTEGER NOT NULL,
                        name TEXT NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (intent_id) REFERENCES intents(id)
                    )
                ''',
                'intent_mappings': '''
                    CREATE TABLE IF NOT EXISTS intent_mappings (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        intent_id INTEGER NOT NULL,
                        pattern_id INTEGER NOT NULL,
                        handler_id INTEGER NOT NULL,
                        score REAL NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (intent_id) REFERENCES intents(id),
                        FOREIGN KEY (pattern_id) REFERENCES pattern_mapping(id),
                        FOREIGN KEY (handler_id) REFERENCES handlers(id)
                    )
                '''
            }
            
            for table_name, create_sql in tables.items():
                self.cursor.execute(create_sql)
                
            self.conn.commit()
            logging.info("Database initialized successfully.")
            
        except Exception as e:
            logging.error(f"Error initializing database: {e}")
            raise
            
    def close(self):
        """Explicitly close the database connection."""
        if hasattr(self, 'conn') and self.conn and not self._keep_alive:
            try:
                self.conn.close()
            except Exception as e:
                logging.error(f"Error closing database connection: {str(e)}")
            
    def __del__(self):
        """Clean up database connection if not kept alive."""
        self.close() 