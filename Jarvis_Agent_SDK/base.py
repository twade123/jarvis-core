"""
Jarvis Agent SDK Base Module

This module provides essential interfaces and base classes that other modules can depend on
without creating circular dependencies. It contains no imports from other Jarvis_Agent_SDK
modules, making it safe to import anywhere.
"""

import time
import hashlib
import logging
import json
import uuid
from typing import Dict, List, Any, Optional, Union, Callable

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Core base classes

class MultiAgentSystemBase:
    """
    Base class for MultiAgentSystem to prevent circular imports.
    
    This class provides the common interface that any MultiAgentSystem implementation
    should follow, allowing for dependency injection and avoiding circular imports.
    """
    
    def __init__(self):
        self.agents = {}
        self.agent_groups = {}
        self.conversations = {}
        
    async def create_agent_group(self, group_name: str, agents_config: List[Dict]) -> Dict:
        """
        Create a group of agents for collaborative task processing.
        
        Args:
            group_name: Name of the agent group
            agents_config: List of agent configurations
            
        Returns:
            Dict with group information
        """
        raise NotImplementedError("Subclasses must implement create_agent_group")
        
    async def register_with_boardroom(self, boardroom=None) -> bool:
        """
        Register the system and its agents with the BoardRoom.
        
        Args:
            boardroom: Optional BoardRoom instance
            
        Returns:
            True if registration was successful
        """
        raise NotImplementedError("Subclasses must implement register_with_boardroom")
        
    async def process_task(self, group_name: str, task: str) -> Dict:
        """
        Process a task using the specified agent group.
        
        Args:
            group_name: Name of the agent group to use
            task: Task description or data
            
        Returns:
            Dict with task processing results
        """
        raise NotImplementedError("Subclasses must implement process_task")

class BoardRoomBase:
    """Base class for BoardRoom implementations with essential tracking functions"""
    
    def __init__(self):
        self.journey_steps = []
        self.requests = {}
        
    def track_request_journey(self, request_id, task, system_id="default", journey_type="default"):
        """
        Track a request journey
        
        Args:
            request_id: ID of the request
            task: Task description or data
            system_id: ID of the system handling the task
            journey_type: Type of journey being tracked
            
        Returns:
            Journey ID
        """
        raise NotImplementedError("Subclasses must implement track_request_journey")
    
    def update_journey_state(self, journey_id, state, metadata=None):
        """
        Update journey state
        
        Args:
            journey_id: ID of the journey
            state: New state
            metadata: Additional metadata
            
        Returns:
            True if successful
        """
        raise NotImplementedError("Subclasses must implement update_journey_state")
    
    def complete_journey(self, journey_id, status="completed", metadata=None):
        """
        Mark a journey as complete
        
        Args:
            journey_id: ID of the journey
            status: Completion status
            metadata: Additional metadata
            
        Returns:
            True if successful
        """
        raise NotImplementedError("Subclasses must implement complete_journey")
    
    async def track_journey_step(self, journey_id, step_name=None, description=None, 
                               step_type=None, input_data=None, output_data=None, error=None):
        """
        Track a journey step (async version)
        
        Args:
            journey_id: ID of the journey
            step_name: Name of the step
            description: Description of the step
            step_type: Type of step
            input_data: Input data for the step
            output_data: Output data from the step
            error: Error information if applicable
            
        Returns:
            True if successful
        """
        raise NotImplementedError("Subclasses must implement track_journey_step")
    
    def track_journey_step(self, journey_id, step_name=None, description=None, 
                          step_type=None, input_data=None, output_data=None, error=None):
        """
        Track a journey step (sync version)
        
        Args:
            journey_id: ID of the journey
            step_name: Name of the step
            description: Description of the step
            step_type: Type of step
            input_data: Input data for the step
            output_data: Output data from the step
            error: Error information if applicable
            
        Returns:
            True if successful
        """
        raise NotImplementedError("Subclasses must implement track_journey_step")

# Add BaseHandler class for compatibility with handler_adapter module
class BaseHandler:
    """
    Base class for handler implementations to prevent circular imports.
    This is a minimal implementation just enough to satisfy imports.
    """
    
    def __init__(self, app_name=None, app_version=None, db_path=None):
        """
        Initialize the base handler with common functionality.
        
        Args:
            app_name: Name of the app/handler
            app_version: Version of the app/handler
            db_path: Path to the database file
        """
        self.app_name = app_name or self.__class__.__name__
        self.app_version = app_version
        self.db_path = db_path
        
    async def handle(self, task_description: Dict) -> Dict:
        """
        Handle a task (async version).
        
        Args:
            task_description: Task description or data
            
        Returns:
            Dict with task processing results
        """
        raise NotImplementedError("Subclasses must implement handle")
        
    def create_success_result(self, data=None, metadata=None) -> Dict:
        """
        Create a success result.
        
        Args:
            data: Result data
            metadata: Additional metadata
            
        Returns:
            Dict with success result
        """
        return {
            "success": True,
            "data": data,
            "metadata": metadata or {}
        }
        
    def create_error_result(self, error: str, metadata=None) -> Dict:
        """
        Create an error result.
        
        Args:
            error: Error message
            metadata: Additional metadata
            
        Returns:
            Dict with error result
        """
        return {
            "success": False,
            "error": error,
            "metadata": metadata or {}
        }

# Utility functions without dependencies

def generate_request_id(task: Union[str, Dict[str, Any]]) -> str:
    """
    Generate a unique request ID based on the task and current timestamp.
    
    Args:
        task: The task for which to generate a request ID
        
    Returns:
        A unique string identifier
    """
    timestamp = str(time.time())
    
    if isinstance(task, dict):
        # Use the task content or ID if available
        task_str = task.get('content', '') or task.get('id', '') or str(task)
    else:
        task_str = str(task)
    
    # Create a hash from the task string and timestamp
    hash_input = f"{task_str}_{timestamp}"
    request_hash = hashlib.md5(hash_input.encode()).hexdigest()
    
    # Return a shortened version of the hash
    return request_hash[:12]

def generate_simple_id(prefix="id"):
    """Generate a simple unique ID with the given prefix"""
    return f"{prefix}_{int(time.time())}_{uuid.uuid4().hex[:8]}"

class DatabaseBase:
    """
    Base class for unified database connections across the system.
    
    This class provides a common interface for database operations that can be
    implemented by different database backends, allowing for unified connectivity
    across modules without circular dependencies.
    """
    
    def __init__(self, db_path=None, connection=None):
        """
        Initialize the database base with optional path or connection.
        
        Args:
            db_path: Path to the database file
            connection: Existing database connection
        """
        self.db_path = db_path
        self.connection = connection
        self.is_connected = connection is not None
        
    def connect(self):
        """
        Establish a database connection if not already connected.
        
        Returns:
            True if connected successfully, False otherwise
        """
        raise NotImplementedError("Subclasses must implement connect")
    
    def disconnect(self):
        """
        Close the database connection if open.
        
        Returns:
            True if disconnected successfully, False otherwise
        """
        raise NotImplementedError("Subclasses must implement disconnect")
    
    def execute_query(self, query, params=None):
        """
        Execute a database query.
        
        Args:
            query: SQL query to execute
            params: Optional parameters for the query
            
        Returns:
            Query result cursor
        """
        raise NotImplementedError("Subclasses must implement execute_query")
    
    def commit(self):
        """
        Commit pending transactions.
        
        Returns:
            True if committed successfully, False otherwise
        """
        raise NotImplementedError("Subclasses must implement commit")
    
    def rollback(self):
        """
        Roll back pending transactions.
        
        Returns:
            True if rolled back successfully, False otherwise
        """
        raise NotImplementedError("Subclasses must implement rollback")
    
    def get_connection(self):
        """
        Get the underlying database connection.
        
        Returns:
            The connection object
        """
        raise NotImplementedError("Subclasses must implement get_connection")
    
    def execute_transaction(self, queries):
        """
        Execute multiple queries as a transaction.
        
        Args:
            queries: List of query/params tuples
            
        Returns:
            True if transaction completed successfully, False otherwise
        """
        raise NotImplementedError("Subclasses must implement execute_transaction") 