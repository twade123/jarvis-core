"""
BoardRoom Connector Module

This module serves as a lightweight connector between the OrchestratorIntelligence
and the BoardRoom system, breaking circular dependencies. It provides:

1. A simple registry for storing global BoardRoom instances
2. Functions for tracking requests, journeys, and performance data
3. No direct imports from either system
4. Core utility functions needed by multiple modules (like load_api_key)
5. Registration interfaces for external systems and agents

This module should be imported by both OrchestratorIntelligence and BoardRoom
or any other module that needs to access the BoardRoom functionality.
"""

import logging
import time
import hashlib
import asyncio
import os
import json
import traceback
import sys
import inspect
import copy
import sqlite3
from pathlib import Path
from typing import Dict, Any, Optional, Union, List, Callable, Tuple
from dataclasses import dataclass
import uuid
import importlib
import threading
from contextlib import contextmanager
from Jarvis_Agent_SDK.database_directory import get_database_directory
from Database.v2.db_helper import connection as v2_connection

# Legacy DatabaseConnectionPool removed — all connections now via Database.v2.db_helper

def get_dedicated_connection(db_path: str, timeout_ms: int = 15000):
    """Legacy shim — callers should migrate to v2_connection(db_name).

    Returns a context-manager that yields a bare sqlite3 connection.
    Kept only so that any remaining callers don't crash immediately.
    """
    @contextmanager
    def _legacy_cm():
        conn = sqlite3.connect(db_path, timeout=timeout_ms / 1000, isolation_level=None)
        conn.execute("PRAGMA journal_mode=DELETE")
        conn.execute(f"PRAGMA busy_timeout={timeout_ms}")
        try:
            yield conn
        finally:
            conn.close()
    return _legacy_cm()

# Stub implementations to break circular imports
class IntentPrediction:
    """Stub implementation of IntentPrediction to break circular imports."""
    
    def __init__(self, text="", intent="", confidence=0.0, predicted=None):
        """Initialize the intent prediction stub."""
        self.text = text
        self.intent = intent
        self.confidence = confidence
        self.predicted = predicted or intent
        
    def to_dict(self):
        """Convert to dictionary."""
        return {
            "text": self.text,
            "intent": self.intent,
            "confidence": self.confidence,
            "predicted": self.predicted
        }

class MetricsCollector:
    """Stub implementation of MetricsCollector to break circular imports."""
    
    def __init__(self):
        """Initialize the metrics collector stub."""
        self.metrics = {
            "system": {},
            "model": {},
            "handler": {},
            "pain_points": {}
        }
        
    def update_system_metrics(self, cpu_usage=0.0, memory_usage=0.0, disk_usage=0.0, gpu_usage=0.0):
        """Stub update_system_metrics method."""
        self.metrics["system"] = {
            "cpu_usage": cpu_usage,
            "memory_usage": memory_usage,
            "disk_usage": disk_usage,
            "gpu_usage": gpu_usage
        }
        
    def update_model_metrics(self, **kwargs):
        """Stub update_model_metrics method."""
        self.metrics["model"].update(kwargs)
        
    def update_handler_metrics(self, **kwargs):
        """Stub update_handler_metrics method."""
        self.metrics["handler"].update(kwargs)
        
    def update_pain_points(self, pain_points):
        """Stub update_pain_points method."""
        self.metrics["pain_points"] = pain_points

class ModelAnalyzer:
    """Stub implementation of ModelAnalyzer to break circular imports."""
    
    def __init__(self, model_name="stub", device=None, config=None, analysis_dir="analysis"):
        """Initialize the model analyzer stub."""
        self.model_name = model_name
        self.device = device
        self.config = config or {}
        self.analysis_dir = analysis_dir
        self.metrics_collector = None
        self.intent_manager = None
        self.model_trainer = None
        self._is_initialized = False
        
    async def initialize(self) -> bool:
        """Stub initialize method."""
        self._is_initialized = True
        return True
        
    async def initialize_intent_manager(self, model_trainer=None) -> bool:
        """Stub initialize_intent_manager method."""
        return True
        
    async def start_monitoring(self, model_trainer=None) -> bool:
        """Stub start_monitoring method."""
        return True
        
    def stop_monitoring(self):
        """Stub stop_monitoring method."""
        pass
        
    async def analyze_pain_points(self, patterns) -> dict:
        """Stub analyze_pain_points method."""
        return {
            "success": True,
            "message": "Stub implementation - ModelAnalyzer.analyze_pain_points",
            "recommendations": []
        }
        
    def create_pain_point_report(self, analysis) -> str:
        """Stub create_pain_point_report method."""
        return "Stub pain point report - ModelAnalyzer.create_pain_point_report"

# Configure logging
logger = logging.getLogger(__name__)

def safe_json_dumps(obj, max_depth=10, current_depth=0):
    """
    Safely convert object to JSON string, handling circular references and deep nesting.
    
    Args:
        obj: The object to convert to JSON
        max_depth: Maximum nesting depth to allow
        current_depth: Current depth (used internally for recursion)
        
    Returns:
        JSON string or None if serialization failed
    """
    if current_depth > max_depth:
        return json.dumps(str(obj)[:100] + "...")  # Convert to string and truncate
        
    if obj is None:
        return 'null'
    
    try:
        # Try simple serialization first
        if isinstance(obj, (str, int, float, bool)):
            return json.dumps(obj)
            
        # Handle sequences
        if isinstance(obj, (list, tuple, set)):
            items = []
            try:
                for item in obj:
                    items.append(safe_json_dumps(item, max_depth, current_depth + 1))
                return f"[{','.join(items)}]"
            except:
                # Fall back to string representation on error
                return json.dumps(str(obj)[:100] + "...")
                
        # Handle dictionaries
        if isinstance(obj, dict):
            pairs = []
            try:
                # Make a shallow copy to avoid modifying the original
                copy_obj = {}
                for k, v in obj.items():
                    # Skip known problematic keys
                    if k in ('self', 'board_room', 'boardroom', '_boardroom_instance', 'workspace_cache'):
                        continue
                    # Ensure key is a string
                    k_str = str(k)
                    # Process value safely
                    copy_obj[k_str] = v
                    
                # Serialize the copied dict
                for k, v in copy_obj.items():
                    if isinstance(k, str):
                        k_json = json.dumps(k)
                        v_json = safe_json_dumps(v, max_depth, current_depth + 1)
                        pairs.append(f"{k_json}:{v_json}")
                return f"{{{','.join(pairs)}}}"
            except:
                # Fall back to string representation on error
                return json.dumps(str(obj)[:100] + "...")
        
        # Other objects - convert to string representation
        return json.dumps(str(obj)[:100] + "...")
    except Exception as e:
        logger.warning(f"JSON serialization error: {str(e)}")
        # Fall back to simple string
        return json.dumps("Object could not be serialized")

# Global variables for storing instances

# Feedback mechanism
_feedback_requests = {}

async def request_feedback(message, needed_params=None, required_for_execution=True, timeout=300):
    """
    Request feedback from the user for the specified parameters.
    
    Args:
        message: The message requesting feedback from the user
        needed_params: List of parameter names that need values from the user
        required_for_execution: Whether this feedback is required before execution
        timeout: How long to wait for feedback in seconds
        
    Returns:
        Dict with success status and journey_id for tracking
    """
    try:
        # Generate a unique ID for this feedback request
        feedback_id = str(uuid.uuid4())
        
        # Get BoardRoom instance for journey tracking
        boardroom = get_boardroom()
        if not boardroom:
            logger.error("Cannot request feedback: No BoardRoom instance available")
            return {"success": False, "error": "No BoardRoom instance available"}
        
        # Get or create a journey ID
        journey_id = getattr(boardroom, 'journey_id', None)
        if not journey_id:
            # Create a new journey
            journey_id = str(uuid.uuid4())
            ensure_journey_exists(journey_id)
            
        # Store feedback request details
        _feedback_requests[feedback_id] = {
            "message": message,
            "needed_params": needed_params or [],
            "required_for_execution": required_for_execution,
            "timeout": timeout,
            "timestamp": time.time(),
            "journey_id": journey_id,
            "response": None,
            "status": "pending"
        }
        
        # Request user feedback using BoardRoom's method
        if hasattr(boardroom, 'request_user_feedback') and callable(boardroom.request_user_feedback):
            feedback_result = await boardroom.request_user_feedback(
                feedback_prompt=message,
                required_for_execution=required_for_execution,
                timeout=timeout
            )
        else:
            # Fall back to journey state update if request_user_feedback is not available
            metrics = {
                'waiting_for_user_feedback': True,
                'feedback_prompt': message,
                'feedback_required_for_execution': required_for_execution,
                'feedback_timeout': timeout,
                'user_feedback_received': False,
                'feedback_id': feedback_id
            }
            
            # Update journey state
            update_journey_state(
                journey_id=journey_id,
                state='waiting_for_user_feedback',
                metrics=metrics
            )
            
            # Track the feedback request
            track_journey_step_sync(
                journey_id=journey_id,
                step_name="feedback_requested",
                description=f"Requested user feedback: {message[:100]}..." if len(message) > 100 else message,
                step_type="user_interaction",
                metadata={
                    "feedback_id": feedback_id,
                    "needed_params": needed_params,
                    "required_for_execution": required_for_execution
                }
            )
            
            feedback_result = True
        
        return {
            "success": feedback_result is True,
            "feedback_id": feedback_id,
            "journey_id": journey_id,
            "message": "Feedback requested successfully"
        }
    except Exception as e:
        logger.error(f"Error requesting feedback: {str(e)}")
        logger.error(traceback.format_exc())
        return {"success": False, "error": str(e)}

async def process_feedback(feedback_content, feedback_id=None, journey_id=None):
    """
    Process user feedback and update the journey state.
    
    Args:
        feedback_content: The feedback content from the user
        feedback_id: Optional feedback request ID to match with the request
        journey_id: Optional journey ID if different from the one in the feedback request
        
    Returns:
        Dict with success status and processed feedback
    """
    try:
        # If feedback_id is provided, get the request details
        if feedback_id and feedback_id in _feedback_requests:
            request_info = _feedback_requests[feedback_id]
            target_journey_id = journey_id or request_info.get("journey_id")
            needed_params = request_info.get("needed_params", [])
        else:
            # Otherwise use provided journey_id or try to get from BoardRoom
            target_journey_id = journey_id
            needed_params = []
            
        # Default journey ID if none provided
        if not target_journey_id:
            boardroom = get_boardroom()
            if boardroom:
                target_journey_id = getattr(boardroom, 'journey_id', None)
            
        if not target_journey_id:
            logger.warning("No journey ID available for processing feedback")
            return {"success": False, "error": "No journey ID available"}
            
        # Get BoardRoom instance
        boardroom = get_boardroom()
        if not boardroom:
            logger.error("Cannot process feedback: No BoardRoom instance available")
            return {"success": False, "error": "No BoardRoom instance available"}
        
        # Process the feedback
        if hasattr(boardroom, 'process_user_feedback') and callable(boardroom.process_user_feedback):
            feedback_result = await boardroom.process_user_feedback(
                feedback=feedback_content,
                journey_id=target_journey_id
            )
        else:
            # Fall back to updating journey state directly
            metrics = {
                'user_feedback_received': True,
                'user_feedback_content': feedback_content,
                'feedback_processed_at': time.time(),
                'feedback_id': feedback_id
            }
            
            # Update journey state
            update_journey_state(
                journey_id=target_journey_id,
                state='processing_after_feedback',
                metrics=metrics
            )
            
            # Track the feedback processing
            track_journey_step_sync(
                journey_id=target_journey_id,
                step_name="feedback_processed",
                description=f"Processed user feedback: {feedback_content[:100]}..." if len(feedback_content) > 100 else feedback_content,
                step_type="user_interaction",
                metadata={
                    "feedback_id": feedback_id,
                    "needed_params": needed_params
                }
            )
            
            feedback_result = {"success": True, "message": "Feedback processed"}
            
        # Update feedback request status
        if feedback_id in _feedback_requests:
            _feedback_requests[feedback_id]["response"] = feedback_content
            _feedback_requests[feedback_id]["status"] = "completed"
            _feedback_requests[feedback_id]["completed_at"] = time.time()
        
        return {
            "success": True,
            "feedback_id": feedback_id,
            "journey_id": target_journey_id,
            "processed_feedback": feedback_content,
            "needed_params": needed_params,
            "result": feedback_result
        }
    except Exception as e:
        logger.error(f"Error processing feedback: {str(e)}")
        logger.error(traceback.format_exc())
        return {"success": False, "error": str(e)}
_boardroom_instance = None
_track_functions = {}
_initialized = False
_boardroom_class = None  # Store the BoardRoom class itself
_boardroom_import_attempted = False  # Flag to track if we've tried to import BoardRoom

# Global references for important shared resources
# Note: Agent registry caching is handled directly by BoardRoom, not in this connector

# Global reference for ModelCommunicationManager
_communication_manager = None

# Direct tracking interface
_direct_tracking_interface = None 

# Get base directory for relative imports
BASE_DIR = Path(__file__).resolve().parent.parent

# Define the ModelMessage class for structured model communication
@dataclass
class ModelMessage:
    """
    A structured message sent between models for communication and consensus building.
    
    Attributes:
        model_id: The ID of the model sending the message
        content: The text content of the message
        message_type: The type of message (e.g., analysis, question, answer)
        context: Optional context information
        message_id: Unique ID for the message
        in_response_to: Optional ID of message this responds to
        timestamp: When the message was created
    """
    model_id: str
    content: str
    message_type: str
    context: Optional[Dict[str, Any]] = None
    message_id: str = None
    in_response_to: Optional[str] = None
    timestamp: float = None
    
    def __post_init__(self):
        # Initialize default values if not provided
        if self.message_id is None:
            self.message_id = f"msg_{uuid.uuid4().hex[:8]}"
        if self.timestamp is None:
            self.timestamp = time.time()
        if self.context is None:
            self.context = {}

def generate_simple_id(prefix="id", length=8):
    """
    Generate a simple ID with prefix and random alphanumeric characters.
    
    Args:
        prefix: The prefix to use for the ID
        length: The length of the random part
        
    Returns:
        A string containing the prefix and random characters
    """
    random_part = uuid.uuid4().hex[:length]
    return f"{prefix}_{random_part}"
    
def generate_request_id():
    """
    Generate a unique request ID for tracking.
    
    Returns:
        A string containing a unique ID for a request
    """
    return f"req_{uuid.uuid4().hex[:12]}"
    
def get_direct_tracking_interface():
    """
    Get the direct tracking interface for journey tracking.
    
    Returns:
        The tracking interface or None
    """
    return _direct_tracking_interface

def _dynamic_import(module_path, class_name=None):
    """
    Dynamically import a module and optionally a specific class from it.
    
    This function avoids circular imports by loading modules at runtime.
    
    Args:
        module_path: Path to the module (e.g., 'Handler.handler_board_room')
        class_name: Optional class name to import from the module
        
    Returns:
        Module or class object if successful, None otherwise
    """
    try:
        module = importlib.import_module(module_path)
        if class_name:
            return getattr(module, class_name, None)
        return module
    except Exception as e:
        logger.warning(f"Error dynamically importing {module_path}: {str(e)}")
        return None

def register_boardroom(boardroom_instance):
    """
    Register a BoardRoom instance globally for the Jarvis system.
    
    Args:
        boardroom_instance: BoardRoom class instance to register
        
    Returns:
        Boolean indicating success
    """
    global _boardroom_instance, _initialized, _track_functions
    
    # Store the instance, but make sure we don't create circular references
    try:
        # To avoid direct reference that might create circular dependencies
        # we discard some attributes that might cause issues
        # This weakened reference prevents deep circular dependencies
        logger.info("Registering BoardRoom instance with protection from circular references")
        _boardroom_instance = boardroom_instance
        
        # Do NOT register the direct track_journey_step method
        # Instead we'll use the database directly for these operations
        
        # Register other functions that are less likely to cause issues
        safe_functions = [
            # AI context management only
            ('add_context', getattr(boardroom_instance, 'add_context', None)),
            ('get_context', getattr(boardroom_instance, 'get_context', None)), 
            ('clear_context', getattr(boardroom_instance, 'clear_context', None)),
            
            # Tool and agent registry functions
            ('register_agent', getattr(boardroom_instance, 'register_agent', None)),
            ('register_tool', getattr(boardroom_instance, 'register_tool', None))
        ]
        
        for name, func in safe_functions:
            if func and callable(func):
                _track_functions[name] = func
                logger.info(f"Registered safe BoardRoom function: {name}")
        
        _initialized = True
        return True
    except Exception as e:
        logger.error(f"Error registering BoardRoom: {str(e)}")
        return False

def _import_boardroom_class():
    """
    Import the BoardRoom class dynamically.
    
    As of Phase 3 refactor (Mar 2026), handler_board_room.py was archived.
    The new boardroom is implemented via Handler.boardroom_template which uses
    the workspace + swarm infrastructure. This function now imports from the
    new location.
    
    Returns:
        BoardRoom class if successful, None otherwise
    """
    global _boardroom_class, _boardroom_import_attempted
    
    # If we've already tried to import, return the cached result
    if _boardroom_import_attempted:
        return _boardroom_class
        
    try:
        # Mark that we've attempted the import
        _boardroom_import_attempted = True
        
        # First ensure BASE_DIR is in the path
        if str(BASE_DIR) not in sys.path:
            sys.path.insert(0, str(BASE_DIR))
            logger.info(f"Added {BASE_DIR} to sys.path")
        
        # Try new boardroom_template first (Phase 3+ architecture)
        new_handler_path = os.path.join(BASE_DIR, "Handler", "boardroom_template.py")
        if os.path.exists(new_handler_path):
            logger.info("Loading boardroom from Handler.boardroom_template (Phase 3+)")
            import importlib.util
            spec = importlib.util.spec_from_file_location("Handler.boardroom_template", new_handler_path)
            if spec:
                handler_module = importlib.util.module_from_spec(spec)
                sys.modules["Handler.boardroom_template"] = handler_module
                handler_module.__package__ = "Handler"
                try:
                    spec.loader.exec_module(handler_module)
                    # Look for a BoardRoom-compatible class
                    for class_name in ['BoardRoom', 'BoardroomTemplate', 'Boardroom']:
                        boardroom_class = getattr(handler_module, class_name, None)
                        if boardroom_class:
                            logger.info(f"Successfully imported {class_name} from boardroom_template")
                            _boardroom_class = boardroom_class
                            return boardroom_class
                    logger.warning("boardroom_template loaded but no BoardRoom class found")
                except Exception as exec_error:
                    logger.error(f"Error loading boardroom_template: {str(exec_error)}")
                    logger.debug(f"Details: {traceback.format_exc()}")
        
        # Fallback: check for legacy handler_board_room.py (should not exist post-Phase 3)
        legacy_path = os.path.join(BASE_DIR, "Handler", "handler_board_room.py")
        if os.path.exists(legacy_path):
            logger.warning("Found legacy handler_board_room.py — using it as fallback")
            import importlib.util
            spec = importlib.util.spec_from_file_location("Handler.handler_board_room", legacy_path)
            if spec:
                handler_module = importlib.util.module_from_spec(spec)
                sys.modules["Handler.handler_board_room"] = handler_module
                handler_module.__package__ = "Handler"
                try:
                    spec.loader.exec_module(handler_module)
                    boardroom_class = getattr(handler_module, 'BoardRoom', None)
                    if boardroom_class:
                        logger.info("Successfully imported legacy BoardRoom class")
                        _boardroom_class = boardroom_class
                        return boardroom_class
                except Exception as exec_error:
                    logger.error(f"Error loading legacy boardroom: {str(exec_error)}")
        
        logger.info("No boardroom implementation found — boardroom features unavailable")
        return None
    except Exception as e:
        logger.error(f"Error importing BoardRoom class: {str(e)}")
        logger.debug(f"Import error details: {traceback.format_exc()}")
        return None
        
def get_boardroom():
    """
    Get an instance of BoardRoom, creating it if necessary.
    
    This function returns the globally registered BoardRoom instance if available,
    otherwise it creates a new instance using dynamic import to avoid circular dependencies.
    
    Note: This function returns the basic BoardRoom instance, which may not be fully initialized.
    For operations requiring full initialization (like spaCy embeddings), use get_initialized_boardroom.
    
    Returns:
        BoardRoom instance if successful, None otherwise
    """
    global _boardroom_instance
    
    # Return cached instance if available
    if _boardroom_instance:
        return _boardroom_instance
    
    # handler_board_room.py was archived (Phase 3 refactor, Mar 2026).
    # Tracking now lives in handler_swarm.py. Direct DB tracking functions
    # in this file (track_journey_step_sync, etc.) still work independently.
    # Return None — callers handle this gracefully.
    return None

    # --- DEAD CODE BELOW (kept for reference) ---
    try:
        # Try using the register_with_connector function from handler_board_room.py
        try:
            # Add the base directory to the path to ensure proper imports
            if str(BASE_DIR) not in sys.path:
                sys.path.insert(0, str(BASE_DIR))
            
            # Use a runtime import to avoid circular imports
            import importlib.util
            
            # Get the path to handler_board_room.py
            handler_board_room_path = os.path.join(BASE_DIR, "Handler", "handler_board_room.py")
            
            # Load the module
            spec = importlib.util.spec_from_file_location("Handler.handler_board_room_temp", handler_board_room_path)
            boardroom_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(boardroom_module)
            
            # Get the register_with_connector function
            register_with_connector = getattr(boardroom_module, "register_with_connector", None)
            
            # Let the handler create and register its own BoardRoom instance if the function exists
            if register_with_connector and callable(register_with_connector):
                if register_with_connector(register_boardroom):
                    logger.info("BoardRoom successfully registered through register_with_connector")
                    return _boardroom_instance
        except Exception as reg_error:
            logger.warning(f"Could not use register_with_connector: {str(reg_error)}")
        
        # Fallback to direct import if registration function failed
        logger.info("Falling back to direct BoardRoom import")
        boardroom_class = _import_boardroom_class()
        
        if not boardroom_class:
            logger.warning("Could not import BoardRoom class")
            return None
        
        # Create a new instance
        boardroom_instance = boardroom_class()
        
        # Register the instance globally to avoid creating multiple instances
        register_boardroom(boardroom_instance)
        
        return boardroom_instance
    except Exception as e:
        logger.error(f"Error getting BoardRoom instance: {str(e)}")
        logger.debug(f"Stack trace: {traceback.format_exc()}")
        return None

async def get_initialized_boardroom() -> Any:
    """
    Get a fully initialized BoardRoom instance with all components loaded.
    
    This async function ensures that the BoardRoom instance has all its
    asynchronous components properly initialized, including:
    - spaCy models for embeddings via workspace_reference_cache
    - Database connections
    - External system registrations
    - Docstrings and other reference data
    
    Returns:
        A fully initialized BoardRoom instance, or None if initialization fails
    """
    # Get the basic instance first
    boardroom = get_boardroom()
    if not boardroom:
        return None
    
    # Track initialization steps for better debugging
    init_steps = []
    start_time = time.time()
    
    try:
        # 1. First check if it's already fully initialized to avoid redundant work
        if hasattr(boardroom, 'fully_initialized') and boardroom.fully_initialized:
            logger.info("BoardRoom instance already fully initialized")
            return boardroom
            
        # 2. Import and initialize the workspace reference cache first 
        # This loads spaCy and database entries which takes the most time
        logger.info("Initializing workspace reference cache...")
        init_steps.append(("workspace_cache_start", time.time() - start_time))
        
        try:
            # Import directly to avoid circular reference issues
            from Jarvis_Agent_SDK.workspace_reference_cache import (
                initialize_workspace_reference_cache, 
                get_workspace_reference_cache,
                _cache_initializer  # Access to the global initializer for resource status
            )
            
            # First check if the cache is already initialized to avoid unnecessary work
            cache_instance = get_workspace_reference_cache()
            if hasattr(cache_instance, 'initialized') and cache_instance.initialized:
                init_steps.append(("workspace_cache_already_initialized", time.time() - start_time))
                logger.info("Workspace reference cache already initialized")
                
                # Get the status for logging
                if hasattr(_cache_initializer, 'get_initialization_status'):
                    status = _cache_initializer.get_initialization_status()
                    logger.info(f"Cache status: {status['state']} with {status['resources_loaded']} resources loaded")
                    
                # Set the cache instance
                workspace_cache = cache_instance
            else:
                # Initialize the cache with a timeout
                # This loads spaCy models and database entries
                workspace_cache = await initialize_workspace_reference_cache()
                
                if workspace_cache and hasattr(workspace_cache, 'initialized') and workspace_cache.initialized:
                    init_steps.append(("workspace_cache_success", time.time() - start_time))
                    logger.info("Successfully initialized workspace reference cache")
                else:
                    init_steps.append(("workspace_cache_partial", time.time() - start_time))
                    logger.warning("Workspace reference cache initialization incomplete or failed")
            
            # Always update the BoardRoom's reference to the cache
            if hasattr(boardroom, 'workspace_cache') and workspace_cache:
                # Update the reference to ensure it's using the initialized instance
                boardroom.workspace_cache = workspace_cache
                logger.info("Updated BoardRoom workspace_cache reference")
            
            # Always check for critical resources - even if "initialized", they might be partially initialized
            # This ensures we report accurate status about what's available for Claude/GPT
            if hasattr(_cache_initializer, 'dependency_graph'):
                graph = _cache_initializer.dependency_graph
                critical_resources = graph.get_critical_resources()
                
                # Get status of critical resources for logging
                status = []
                for resource_name in critical_resources:
                    resource = graph.get_resource(resource_name)
                    if resource:
                        status.append(f"{resource_name}: {resource.status}")
                
                logger.info(f"Critical resources status: {', '.join(status)}")
                
                # We need at least database for minimal functionality
                database_resource = graph.get_resource("database")
                if database_resource and not database_resource.is_loaded():
                    logger.warning("Critical resource 'database' is not loaded, functionality will be limited")
                    
                # Report on model-specific resources
                spacy_resource = graph.get_resource("spacy_model")
                if spacy_resource and spacy_resource.is_loaded():
                    logger.info("spaCy model is loaded - full embedding functionality available")
                else:
                    logger.warning("spaCy model is not loaded - using fallback embeddings")
                    
                # Check for agent registry and docstrings which enhance model capabilities
                agent_registry = graph.get_resource("agent_registry")
                docstrings = graph.get_resource("docstrings")
                
                # Report on enhancement capabilities status
                enhancements = []
                if agent_registry and agent_registry.is_loaded():
                    enhancements.append("agent performance tracking")
                if docstrings and docstrings.is_loaded():
                    enhancements.append("semantic docstring search")
                    
                if enhancements:
                    logger.info(f"Available enhancements for models: {', '.join(enhancements)}")
                else:
                    logger.warning("No enhancement resources available for models")
            
        except Exception as cache_e:
            init_steps.append(("workspace_cache_failed", time.time() - start_time))
            logger.warning(f"Error initializing workspace cache: {str(cache_e)}")
            logger.debug(traceback.format_exc())
            # Continue with initialization even if cache fails
        
        # 3. Now initialize the BoardRoom instance itself
        if hasattr(boardroom, 'initialize') and callable(boardroom.initialize):
            logger.info("Initializing BoardRoom instance asynchronously")
            init_steps.append(("boardroom_init_start", time.time() - start_time))
            
            # Initialize with timeout to avoid blocking indefinitely
            try:
                # Create a task with timeout
                initialize_task = asyncio.create_task(boardroom.initialize())
                # Wait with timeout (30 seconds)
                await asyncio.wait_for(initialize_task, timeout=30)
                init_steps.append(("boardroom_init_success", time.time() - start_time))
                logger.info("BoardRoom initialization completed successfully")
            except asyncio.TimeoutError:
                init_steps.append(("boardroom_init_timeout", time.time() - start_time))
                logger.warning("BoardRoom initialization timed out, continuing with partial initialization")
            except Exception as init_e:
                init_steps.append(("boardroom_init_error", time.time() - start_time))
                logger.error(f"Error in BoardRoom.initialize(): {str(init_e)}")
                logger.debug(traceback.format_exc())
        else:
            # If it has no initialize method, it's likely an older version
            init_steps.append(("boardroom_no_init_method", time.time() - start_time))
            logger.warning("BoardRoom instance does not have initialize method")
        
        # Log all initialization steps for debugging
        init_time = time.time() - start_time
        logger.info(f"BoardRoom initialization completed in {init_time:.2f}s with steps: {init_steps}")
        
        # Return the instance, which may be partially initialized
        return boardroom
    except Exception as e:
        logger.error(f"Error initializing BoardRoom: {str(e)}")
        logger.debug(traceback.format_exc())
        
        # Log init steps for debugging failed initializations
        logger.info(f"BoardRoom initialization failed with steps: {init_steps}")
        
        # Return the partially initialized instance as fallback
        return boardroom

# REMOVED: Competing singleton implementation replaced with official singleton
# Use: from Jarvis_Agent_SDK.database_directory import get_database_directory

def register_tracking_function(function_name: str, function_impl: Callable):
    """
    Register a tracking function to be used by the BoardRoom connector.
    
    Args:
        function_name: Name of the tracking function (e.g., 'track_request_journey')
        function_impl: Function implementation to call when the tracking function is invoked
        
    Returns:
        Boolean indicating success
    """
    global _track_functions
    
    if not function_name or not function_impl or not callable(function_impl):
        return False
        
    _track_functions[function_name] = function_impl
    logger.info(f"Registered external tracking function: {function_name}")
    return True

def register_core_tracking_functions(
    track_request_journey_fn=None,
    track_journey_step_fn=None,
    update_journey_state_fn=None,
    complete_journey_fn=None
):
    """
    Register core tracking functions used by the system.
    
    Args:
        track_request_journey_fn: Function to track the start of a request journey
        track_journey_step_fn: Function to track a step in a journey
        update_journey_state_fn: Function to update the state of a journey
        complete_journey_fn: Function to mark a journey as complete
        
    Returns:
        Boolean indicating success
    """
    success = True
    
    # Register each function if provided
    if track_request_journey_fn and callable(track_request_journey_fn):
        success = register_tracking_function("track_request_journey", track_request_journey_fn) and success
        
    if track_journey_step_fn and callable(track_journey_step_fn):
        success = register_tracking_function("track_journey_step", track_journey_step_fn) and success
        
    if update_journey_state_fn and callable(update_journey_state_fn):
        success = register_tracking_function("update_journey_state", update_journey_state_fn) and success
        
    if complete_journey_fn and callable(complete_journey_fn):
        success = register_tracking_function("complete_journey", complete_journey_fn) and success
        
    return success

async def track_request_journey(request_id=None, task=None, system_id="default", journey_type="default") -> str:
    """
    Track a new request journey.
    IMPORTANT: Always use track_request_journey_sync in non-async contexts to avoid coroutine warnings.
    
    Args:
        request_id: Unique identifier for the request (generated if None)
        task: Task description or data
        system_id: System handling the request
        journey_type: Type of journey (normal, complex, etc.)
        
    Returns:
        Journey ID for the tracked request
    """
    # Generate a request_id if not provided
    if not request_id:
        request_id = f"req_{uuid.uuid4().hex[:12]}"
        
    # Create journey_id with timestamp for better tracking
    journey_id = f"{system_id}_{int(time.time())}_{request_id}"
    
    # Try with registered tracking function
    if 'track_request_journey' in _track_functions:
        try:
            result = _track_functions['track_request_journey'](
                request_id=request_id,
                task=task,
                system_id=system_id,
                journey_type=journey_type
            )
            
            # If the function returns a journey_id, use it instead
            if result and isinstance(result, str):
                return result
                
            # If function returns True, it was successful but we'll use our journey_id
            if result is True:
                return journey_id
                
            # If function returns False, fall through to default behavior
        except Exception as e:
            logger.warning(f"Error calling track_request_journey: {str(e)}")
    
    # Check if this journey already exists, then insert if not
    try:
        with v2_connection("journeys") as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT COUNT(*) FROM request_journeys WHERE journey_id = ?",
                (journey_id,)
            )
            count = cursor.fetchone()[0]
            if count > 0:
                logger.info(f"Journey {journey_id} already exists in database")
                return journey_id

            # Create a timestamp
            timestamp = time.time()

            # Insert the journey record
            cursor.execute(
                """
                INSERT INTO request_journeys
                (journey_id, request_id, system_id, journey_type, task, start_time, current_state, last_updated)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    journey_id,
                    request_id,
                    system_id,
                    journey_type,
                    json.dumps(task) if task else None,
                    timestamp,
                    "initialized",
                    timestamp
                )
            )
            logger.info(f"Journey tracked: {journey_id} - Request: {request_id}")
            return journey_id
    except sqlite3.IntegrityError as ie:
        if "UNIQUE constraint failed" in str(ie):
            logger.info(f"Journey {journey_id} already exists - concurrent creation attempt detected")
            return journey_id
        else:
            logger.error(f"Database integrity error tracking journey: {str(ie)}")
            logger.debug(traceback.format_exc())
            ensure_journey_exists(journey_id, "initialized")
            return journey_id
    except Exception as e:
        logger.error(f"Error tracking journey: {str(e)}")
        logger.debug(traceback.format_exc())
        ensure_journey_exists(journey_id, "initialized")
        return journey_id

def track_request_journey_sync(request_id=None, task=None, system_id="default", journey_type="default") -> str:
    """
    Synchronous version of track_request_journey.
    
    This function MUST be used in synchronous contexts where async/await is not available.
    It provides the same functionality as track_request_journey but in a synchronous way.
    
    WARNING: Using the async version (track_request_journey) without await will cause
    "coroutine was never awaited" warnings. Always use this sync version in non-async contexts.
    
    Args:
        request_id: Unique identifier for the request (generated if None)
        task: Task description or data
        system_id: System handling the request
        journey_type: Type of journey (normal, complex, etc.)
        
    Returns:
        Journey ID for the tracked request
    """
    # Generate a request_id if not provided
    if not request_id:
        request_id = f"req_{uuid.uuid4().hex[:12]}"
        
    # Create journey_id with timestamp for better tracking
    journey_id = f"{system_id}_{int(time.time())}_{request_id}"
    
    # Check if this journey already exists, then insert if not
    try:
        with v2_connection("journeys") as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT COUNT(*) FROM request_journeys WHERE journey_id = ?",
                (journey_id,)
            )
            count = cursor.fetchone()[0]
            if count > 0:
                logger.info(f"Journey {journey_id} already exists in database")
                return journey_id

            timestamp = time.time()
            cursor.execute(
                """
                INSERT INTO request_journeys
                (journey_id, request_id, system_id, journey_type, task, start_time, current_state, last_updated)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    journey_id,
                    request_id,
                    system_id,
                    journey_type,
                    json.dumps(task) if task else None,
                    timestamp,
                    "initialized",
                    timestamp
                )
            )
            logger.info(f"Journey tracked synchronously: {journey_id} - Request: {request_id}")
            return journey_id
    except sqlite3.IntegrityError as ie:
        if "UNIQUE constraint failed" in str(ie):
            logger.info(f"Journey {journey_id} already exists - concurrent creation attempt detected")
            return journey_id
        else:
            logger.error(f"Database integrity error tracking journey: {str(ie)}")
            logger.debug(traceback.format_exc())
            ensure_journey_exists(journey_id, "initialized")
            return journey_id
    except Exception as e:
        logger.error(f"Error tracking journey synchronously: {str(e)}")
        logger.debug(traceback.format_exc())
        ensure_journey_exists(journey_id, "initialized")
        return journey_id
    finally:
        # Don't close singleton database connections - they're managed by DatabaseDirectory
        pass

async def track_journey_step_async(
    journey_id: str,
    step_type: str,
    step_name: str,
    description: str = None,
    input_data: Dict[str, Any] = None,
    output_data: Dict[str, Any] = None,
    error: str = None,
    status: str = "completed",
    metadata: Dict[str, Any] = None,
    duration: float = None
) -> bool:
    """
    Track a step in a journey asynchronously.
    
    This completely rewritten function creates a dedicated connection for journey tracking to avoid
    database locks. It bypasses the shared connection pooling mechanisms that can cause locks
    and instead directly manages its own connection with proper timeouts and cleanup.
    
    Args:
        journey_id: The journey ID to track the step for
        step_type: Type of step (e.g., 'api_call', 'processing', 'error')
        step_name: Name of the step
        description: Description of the step
        input_data: Input data for the step
        output_data: Output data from the step
        error: Error message if the step failed
        status: Status of the step (e.g., 'completed', 'failed', 'in_progress')
        metadata: Additional metadata
        duration: Duration of the step in seconds
        
    Returns:
        True if successful, False otherwise
    """
    # Use the existing connection pool to eliminate repeated database initialization
            
    # Utility function to safely convert Python objects to JSON
    def safe_serialize(obj):
        """Safely convert an object to JSON, handling potential circular references."""
        if obj is None:
            return None
            
        try:
            # Handle basic types directly
            if isinstance(obj, (str, int, float, bool, type(None))):
                return json.dumps(obj)
                
            # Simplify dictionaries to avoid potential circular references
            if isinstance(obj, dict):
                # Create a safe copy without potentially problematic references
                safe_obj = {k: str(v)[:100] for k, v in obj.items() 
                           if k not in ('self', 'board_room', 'boardroom', '_boardroom_instance', 
                                       'workspace_cache', 'nlp', 'external_systems')}
                return json.dumps(safe_obj)
                
            # For other types, convert to string representation
            return json.dumps(str(obj)[:100])
        except Exception as e:
            logger.warning(f"Error serializing object: {str(e)}")
            return json.dumps({"error": "Object could not be serialized"})
            
    # Make sure journey_id is valid
    if not journey_id:
        logger.warning("Invalid journey_id provided to track_journey_step_async")
        return False
        
    # First, simplify the data to avoid serialization issues
    # These are the main issues that cause problems in the first place
    try:
        # Limit and safely serialize input data
        safe_input = None
        if input_data is not None:
            safe_input = safe_serialize(input_data)
            
        # Limit and safely serialize output data
        safe_output = None
        if output_data is not None:
            safe_output = safe_serialize(output_data)
            
        # Limit and safely serialize metadata
        safe_metadata = None
        if metadata is not None:
            safe_metadata = safe_serialize(metadata)
    except Exception as e:
        logger.warning(f"Error simplifying data for journey step: {str(e)}")
        safe_input = json.dumps({"simplified": True})
        safe_output = json.dumps({"simplified": True})
        safe_metadata = json.dumps({"simplified": True})
    
    # Use retries with exponential backoff
    max_retries = 5
    base_delay = 0.1

    for retry in range(max_retries):
        try:
            with v2_connection("journeys") as conn:
                cursor = conn.cursor()
                conn.execute("BEGIN IMMEDIATE")

                # Check if journey exists and create it if needed
                cursor.execute(
                    "SELECT COUNT(*) FROM request_journeys WHERE journey_id = ?",
                    (journey_id,)
                )
                exists = cursor.fetchone()[0] > 0

                if not exists:
                    timestamp = time.time()
                    logger.info(f"Creating journey record for {journey_id}")
                    cursor.execute(
                        """
                        INSERT INTO request_journeys
                        (journey_id, request_id, system_id, journey_type, task, start_time, current_state, last_updated)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            journey_id,
                            f"auto_{journey_id}",
                            "system",
                            "auto_created",
                            json.dumps({"description": f"Auto-created for step {step_name}"}),
                            timestamp,
                            "active",
                            timestamp
                        )
                    )

                timestamp = time.time()
                cursor.execute(
                    """
                    INSERT INTO journey_steps
                    (journey_id, step_type, step_name, description, input_data, output_data,
                    error, timestamp, duration, status, metadata)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        journey_id, step_type, step_name, description,
                        safe_input, safe_output, error, timestamp,
                        duration, status, safe_metadata
                    )
                )
                cursor.execute(
                    "UPDATE request_journeys SET last_updated = ? WHERE journey_id = ?",
                    (timestamp, journey_id)
                )
                conn.execute("COMMIT")
                logger.info(f"Journey step tracked: {journey_id} - {step_name}")
                return True

        except sqlite3.OperationalError as oe:
            if "database is locked" in str(oe) and retry < max_retries - 1:
                retry_delay = base_delay * (2 ** retry)
                logger.warning(f"Database locked, retry {retry+1}/{max_retries} in {retry_delay:.2f}s: {step_name}")
                await asyncio.sleep(retry_delay)
            else:
                logger.warning(f"SQLite error tracking journey step: {str(oe)}")
                if retry >= max_retries - 1:
                    logger.info(f"Journey step logged minimally (after SQLite error): {journey_id} - {step_name}")
                    return True
                await asyncio.sleep(base_delay * (2 ** retry))
        except Exception as e:
            logger.warning(f"Error tracking journey step (attempt {retry+1}): {str(e)}")
            logger.debug(traceback.format_exc())
            if retry >= max_retries - 1:
                logger.info(f"Journey step logged minimally (after general error): {journey_id} - {step_name}")
                return True
            await asyncio.sleep(base_delay * (2 ** retry))

    logger.warning(f"Exhausted all retries for journey step: {journey_id} - {step_name}")
    return True

def track_journey_step_sync(
    journey_id: str,
    step_type: str,
    step_name: str,
    description: str = None,
    input_data: Dict[str, Any] = None,
    output_data: Dict[str, Any] = None,
    error: str = None,
    status: str = "completed",
    metadata: Dict[str, Any] = None,
    duration: float = None
) -> bool:
    """
    Track a step in a journey synchronously.
    
    Args:
        journey_id: The journey ID to track the step for
        step_type: Type of step (e.g., 'api_call', 'processing', 'error')
        step_name: Name of the step
        description: Description of the step
        input_data: Input data for the step
        output_data: Output data from the step
        error: Error message if the step failed
        status: Status of the step (e.g., 'completed', 'failed', 'in_progress')
        metadata: Additional metadata
        duration: Duration of the step in seconds
        
    Returns:
        True if successful, False otherwise
    """
    # IMPORTANT: We no longer attempt to use the BoardRoom instance directly
    # This avoids circular references that cause recursion errors
    
    # Always use direct database access for journey steps
    logger.debug(f"Tracking journey step directly via database: {step_name}")
    
    # Make sure journey exists first - this is a simple direct function call
    if not ensure_journey_exists(journey_id, state="active"):
        # Create journey entry if needed
        try:
            logger.info(f"Creating journey tracking entry for {journey_id}")
            track_request_journey(journey_id, {"description": f"Auto-created journey for {step_name}"})
        except Exception as e:
            logger.warning(f"Error creating journey: {str(e)}")
    
    # Clean any complex data structures to prevent recursion
    try:
        # Simplify input data if present
        if input_data:
            # For dictionaries, remove known problematic keys and limit depth
            if isinstance(input_data, dict):
                safe_input = {k: str(v)[:100] for k, v in input_data.items() 
                             if k not in ('self', 'board_room', 'boardroom', '_boardroom_instance', 
                                         'workspace_cache', 'nlp', 'external_systems')}
            else:
                # For other types, convert to string
                safe_input = str(input_data)[:100]
        else:
            safe_input = None
            
        # Simplify output data if present
        if output_data:
            # For dictionaries, remove known problematic keys and limit depth
            if isinstance(output_data, dict):
                safe_output = {k: str(v)[:100] for k, v in output_data.items()
                              if k not in ('self', 'board_room', 'boardroom', '_boardroom_instance',
                                          'workspace_cache', 'nlp', 'external_systems')}
            else:
                # For other types, convert to string
                safe_output = str(output_data)[:100]
        else:
            safe_output = None
            
        # Simplify metadata if present
        if metadata:
            # For dictionaries, remove known problematic keys and limit depth
            if isinstance(metadata, dict):
                safe_metadata = {k: str(v)[:100] for k, v in metadata.items()
                                if k not in ('self', 'board_room', 'boardroom', '_boardroom_instance',
                                            'workspace_cache', 'nlp', 'external_systems')}
            else:
                # For other types, convert to string
                safe_metadata = str(metadata)[:100]
        else:
            safe_metadata = None
    except Exception as clean_err:
        logger.warning(f"Error cleaning data structures: {str(clean_err)}")
        safe_input = None
        safe_output = None 
        safe_metadata = None
    
    try:
        # Serialize data safely
        try:
            input_json = json.dumps(safe_input) if safe_input is not None else None
            output_json = json.dumps(safe_output) if safe_output is not None else None
            metadata_json = json.dumps(safe_metadata) if safe_metadata is not None else None
        except Exception as json_err:
            logger.warning(f"Error serializing journey data, using minimal fallbacks: {str(json_err)}")
            input_json = '{"type": "simplified"}'
            output_json = '{"type": "simplified"}'
            metadata_json = '{"type": "simplified"}'

        with v2_connection("journeys") as conn:
            timestamp = time.time()
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO journey_steps
                (journey_id, step_type, step_name, description, input_data, output_data,
                error, timestamp, duration, status, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    journey_id, step_type, step_name, description,
                    input_json, output_json, error, timestamp,
                    duration, status, metadata_json
                )
            )
            cursor.execute(
                "UPDATE request_journeys SET last_updated = ? WHERE journey_id = ?",
                (timestamp, journey_id)
            )
            logger.info(f"Journey step tracked: {journey_id} - {step_name}")
            return True
    except Exception as e:
        logger.error(f"Error tracking journey step: {str(e)}")
        logger.debug(traceback.format_exc())
        return False

def ensure_journey_exists(journey_id: str, state: str = "initialized", existing_conn=None, in_transaction=False) -> bool:
    """
    Ensure that a journey with the given ID exists in the database.
    If it doesn't exist, create it with sensible defaults.
    
    Args:
        journey_id: The journey ID to check/create
        state: The initial state for the journey if created
        existing_conn: An existing database connection (for transaction support)
        in_transaction: Whether this is being called from within a transaction
        
    Returns:
        bool: True if the journey exists or was created, False otherwise
    """
    def _do_ensure(conn, need_txn):
        """Inner logic — works with any connection (passed-in or freshly opened)."""
        cursor = conn.cursor()
        if need_txn:
            conn.execute("BEGIN IMMEDIATE")

        cursor.execute(
            "SELECT COUNT(*) FROM request_journeys WHERE journey_id = ?",
            (journey_id,)
        )
        if cursor.fetchone()[0] > 0:
            if need_txn:
                conn.execute("COMMIT")
            return True

        logger.info(f"Journey {journey_id} not found - creating it automatically")
        timestamp = time.time()

        # Extract request_id, system_id, journey_type from journey_id pattern
        extracted_request_id = journey_id
        system_id = "system"
        journey_type = "auto_created"

        if "boardroom_conversation_" in journey_id:
            parts = journey_id.split('_')
            if len(parts) >= 3:
                try:
                    timestamp_part = parts[-2]
                    if timestamp_part.isdigit():
                        extracted_request_id = f"test_req_{timestamp_part}"
                        parsed_timestamp = float(timestamp_part)
                        if parsed_timestamp > 1000000000:
                            timestamp = parsed_timestamp
                except Exception:
                    pass
                system_id = "boardroom"
                journey_type = "boardroom_conversation"
            else:
                system_id = "boardroom"
                journey_type = "auto_created_conversation"
        elif "test_req_" in journey_id:
            extracted_request_id = journey_id
            system_id = "boardroom"
            journey_type = "boardroom_request"

        try:
            cursor.execute(
                """
                INSERT INTO request_journeys
                (journey_id, request_id, system_id, journey_type, task, start_time, current_state, last_updated)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    journey_id, extracted_request_id, system_id, journey_type,
                    json.dumps({"description": f"Auto-created journey for {system_id}"}),
                    timestamp, state, timestamp
                )
            )
            cursor.execute(
                """
                INSERT INTO journey_steps
                (journey_id, step_type, step_name, description, timestamp, status)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (journey_id, "auto_creation", "journey_created",
                 "Journey auto-created during ensure_journey_exists", timestamp, "completed")
            )
            if need_txn:
                conn.execute("COMMIT")
            logger.info(f"Successfully created journey {journey_id} with request_id {extracted_request_id}")
            return True
        except sqlite3.IntegrityError as ie:
            if "UNIQUE constraint failed" in str(ie):
                logger.info(f"Journey {journey_id} was created by another process (concurrent creation)")
                if need_txn:
                    conn.execute("COMMIT")
                return True
            raise

    # If caller passed an existing connection (inside their own txn), use it directly
    if existing_conn:
        try:
            return _do_ensure(existing_conn, need_txn=not in_transaction)
        except Exception as e:
            logger.error(f"Error in ensure_journey_exists: {str(e)}")
            return False

    # Otherwise open our own v2 connection
    try:
        with v2_connection("journeys") as conn:
            return _do_ensure(conn, need_txn=True)
    except Exception as e:
        logger.error(f"Error in ensure_journey_exists: {str(e)}")
        logger.warning(f"Journey {journey_id} not found and could not be created: {str(e)}")
        return False

def track_journey_step(
    journey_id: str,
    step_type: str,
    step_name: str,
    description: str = None,
    input_data: Dict[str, Any] = None,
    output_data: Dict[str, Any] = None,
    error: str = None,
    status: str = "completed",
    metadata: Dict[str, Any] = None,
    duration: float = None
) -> bool:
    """
    Track a step in a journey.
    
    Args:
        journey_id: The journey ID to track the step for
        step_type: Type of step (e.g., 'api_call', 'processing', 'error')
        step_name: Name of the step
        description: Description of the step
        input_data: Input data for the step
        output_data: Output data from the step
        error: Error message if the step failed
        status: Status of the step (e.g., 'completed', 'failed', 'in_progress')
        metadata: Additional metadata
        duration: Duration of the step in seconds
        
    Returns:
        True if successful, False otherwise
    """
    # Make sure we have a valid journey_id
    if not journey_id:
        logger.warning("Invalid journey_id provided to track_journey_step")
        return False
    
    # Try with registered tracking function
    if 'track_journey_step' in _track_functions:
        try:
            logger.info(f"Using registered tracking function for step: {step_name}")
            # Get the function and check its signature
            func = _track_functions['track_journey_step']
            # Get the parameters the function accepts
            sig = inspect.signature(func)
            param_names = list(sig.parameters.keys())
            
            # Create base kwargs with required parameters
            kwargs = {
                'journey_id': journey_id,
                'step_name': step_name
            }
            
            # Only add optional parameters if they are in the function signature
            if 'step_type' in param_names and step_type is not None:
                kwargs['step_type'] = step_type
            if 'description' in param_names and description is not None:
                kwargs['description'] = description
            if 'input_data' in param_names and input_data is not None:
                kwargs['input_data'] = input_data
            if 'output_data' in param_names and output_data is not None:
                kwargs['output_data'] = output_data
            if 'error' in param_names and error is not None:
                kwargs['error'] = error
            if 'metadata' in param_names and metadata is not None:
                kwargs['metadata'] = metadata
                
            # Status and duration parameters are conditionally added
            if 'status' in param_names and status is not None:
                kwargs['status'] = status
            if 'duration' in param_names and duration is not None:
                kwargs['duration'] = duration
                
            # Log which parameters were excluded for debugging
            if 'status' not in param_names and status != "completed":
                logger.debug(f"Status parameter '{status}' not supported by registered function, using defaults")
            if 'duration' not in param_names and duration is not None:
                logger.debug(f"Duration parameter '{duration}' not supported by registered function, using defaults")
                
            # Call the function with only the parameters it accepts
            return func(**kwargs)
        except Exception as e:
            logger.warning(f"Error calling track_journey_step function: {str(e)}")
    
    # Skip the BoardRoom instance method to avoid async/sync issues
    # Instead, rely on the direct database implementation below
    logger.info(f"Using direct database implementation for step: {step_name}")
    
    # Ensure the journey exists before tracking a step
    journey_exists = ensure_journey_exists(journey_id, state="initialized")
    if not journey_exists:
        logger.warning(f"Cannot track step for journey {journey_id}: Journey does not exist and could not be created")
        return False
    
    # Direct database implementation as fallback
    try:
        # Clean complex data structures to prevent recursion
        _bad_keys = ('self', 'board_room', 'boardroom', '_boardroom_instance',
                     'workspace_cache', 'nlp', 'external_systems', 'steps')
        try:
            safe_input = ({k: str(v)[:100] for k, v in input_data.items() if k not in _bad_keys}
                          if isinstance(input_data, dict) else (str(input_data)[:100] if input_data else None))
            safe_output = ({k: str(v)[:100] for k, v in output_data.items() if k not in _bad_keys}
                           if isinstance(output_data, dict) else (str(output_data)[:100] if output_data else None))
            safe_metadata = ({k: str(v)[:100] for k, v in metadata.items() if k not in _bad_keys}
                             if isinstance(metadata, dict) else (str(metadata)[:100] if metadata else None))
        except Exception:
            safe_input = safe_output = safe_metadata = None

        input_json = json.dumps(safe_input) if safe_input is not None else None
        output_json = json.dumps(safe_output) if safe_output is not None else None
        metadata_json = json.dumps(safe_metadata) if safe_metadata is not None else None

        with v2_connection("journeys") as conn:
            timestamp = time.time()
            conn.execute(
                """
                INSERT INTO journey_steps
                (journey_id, step_type, step_name, description, input_data, output_data,
                error, timestamp, duration, status, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (journey_id, step_type, step_name, description,
                 input_json, output_json, error, timestamp,
                 duration, status, metadata_json)
            )
            logger.info(f"Journey step tracked directly: {journey_id} - {step_name}")
            return True
    except Exception as e:
        logger.error(f"Error tracking journey step: {str(e)}")
        logger.debug(traceback.format_exc())

    logger.info(f"Journey step logged minimally: {journey_id} - {step_name}")
    return True

def get_all_journey_states(limit: int = 10) -> Dict[str, Dict[str, Any]]:
    """
    Get the current state of all recent active journeys.
    
    This function is used by the terminal to check for pending feedback requests
    across all journeys without needing to know specific journey IDs.
    
    Args:
        limit: Maximum number of journeys to return (most recent first)
        
    Returns:
        Dict mapping journey_id to state information
    """
    try:
        with v2_connection("journeys") as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT journey_id, current_state, start_time
                FROM request_journeys
                WHERE completed = 0 OR completed IS NULL
                ORDER BY start_time DESC
                LIMIT ?
                """,
                (limit,)
            )
            journeys = cursor.fetchall()

        results = {}
        for journey in journeys:
            jid = journey[0] if isinstance(journey, (tuple, list)) else journey["journey_id"]
            journey_state = get_journey_state(jid)
            if journey_state:
                results[jid] = journey_state
        return results
    except Exception as e:
        logging.error(f"Error in get_all_journey_states: {str(e)}")
        return {}

def get_journey_state(journey_id: str) -> Dict[str, Any]:
    """
    Get the current state and metrics of a journey.
    
    Args:
        journey_id: ID of the journey to check
        
    Returns:
        Dict with journey state information or None if not found
    """
    if not journey_id:
        return None
        
    try:
        with v2_connection("journeys") as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT journey_id, current_state FROM request_journeys WHERE journey_id = ?",
                (journey_id,)
            )
            journey_row = cursor.fetchone()

            if not journey_row:
                logging.warning(f"No journey found with ID: {journey_id}")
                return None

            metrics = {}
            feedback_required = False

            try:
                cursor.execute(
                    """
                    SELECT step_type, description, metadata
                    FROM journey_steps
                    WHERE journey_id = ?
                    ORDER BY timestamp DESC
                    LIMIT 10
                    """,
                    (journey_id,)
                )
                steps = cursor.fetchall()

                for step in steps:
                    s_type = step[0] if isinstance(step, (tuple, list)) else step["step_type"]
                    s_desc = step[1] if isinstance(step, (tuple, list)) else step["description"]
                    s_meta = step[2] if isinstance(step, (tuple, list)) else step["metadata"]

                    if s_type and ('feedback' in s_type.lower() or 'user_input' in s_type.lower()):
                        feedback_required = True
                    if s_desc and 'feedback' in s_desc.lower() and ('request' in s_desc.lower() or 'waiting' in s_desc.lower()):
                        feedback_required = True
                    if s_meta:
                        try:
                            meta = json.loads(s_meta)
                            if isinstance(meta, dict):
                                if meta.get('request_feedback') or meta.get('waiting_for_user_feedback') or meta.get('feedback_request_visible'):
                                    feedback_required = True
                                    metrics.update({
                                        'waiting_for_user_feedback': True,
                                        'feedback_request_visible': True,
                                        'feedback_requested_timestamp': meta.get('timestamp', time.time())
                                    })
                        except Exception:
                            pass
            except Exception as steps_error:
                logging.warning(f"Error checking steps for feedback indicators: {str(steps_error)}")

            state = journey_row[1] if isinstance(journey_row, (tuple, list)) else journey_row["current_state"]
            jid = journey_row[0] if isinstance(journey_row, (tuple, list)) else journey_row["journey_id"]
            if feedback_required and state != 'user_feedback_received':
                state = 'waiting_for_user_feedback'
                metrics.update({'waiting_for_user_feedback': True, 'feedback_request_visible': True})

            return {"journey_id": jid, "state": state, "metrics": metrics}
    except Exception as e:
        logging.error(f"Error in get_journey_state: {str(e)}")
        return None

def update_journey_state(
    journey_id: str,
    state: str,
    message: str = None,
    metrics: Dict[str, Any] = None
) -> bool:
    """
    Update the state of a journey.
    
    Args:
        journey_id: The journey ID to update
        state: New state for the journey
        message: Optional message describing the state update
        metrics: Optional metrics to store with the state
        
    Returns:
        bool: True if successful
    """
    # Check if journey_id is provided
    if not journey_id:
        logger.warning("No journey_id provided for update_journey_state")
        return False
    
    # Log that we're attempting to update a journey state
    logger.info(f"Updating journey state for {journey_id} to {state}")
        
    # Try with registered tracking function first
    if 'update_journey_state' in _track_functions:
        try:
            return _track_functions['update_journey_state'](
                journey_id=journey_id,
                state=state,
                message=message,
                metrics=metrics
            )
        except TypeError as e:
            # Handle missing positional argument 'self'
            if "'self'" in str(e):
                logger.warning(f"update_journey_state missing 'self' parameter: {str(e)}")
                
                # Try importing the static version if available
                try:
                    from Handler.handler_board_room import update_journey_state_static
                    return update_journey_state_static(
                        journey_id=journey_id,
                        state=state,
                        message=message,
                        metrics=metrics
                    )
                except Exception as import_error:
                    logger.warning(f"Error importing update_journey_state_static: {str(import_error)}")
            else:
                # For other TypeError issues, fallback to default behavior
                logger.warning(f"TypeError in update_journey_state: {str(e)}")
        except Exception as e:
            logger.warning(f"Error calling update_journey_state: {str(e)}")
    
    try:
        with v2_connection("journeys") as conn:
            conn.execute("BEGIN IMMEDIATE")
            cursor = conn.cursor()

            cursor.execute(
                "SELECT COUNT(*) FROM request_journeys WHERE journey_id = ?",
                (journey_id,)
            )
            if cursor.fetchone()[0] == 0:
                # Create inside transaction
                if not ensure_journey_exists(journey_id, state=state, existing_conn=conn, in_transaction=True):
                    logger.warning(f"Journey {journey_id} not found for state update and could not be created")
                    conn.execute("ROLLBACK")
                    return False

            timestamp = time.time()
            cursor.execute(
                "UPDATE request_journeys SET current_state = ?, last_updated = ? WHERE journey_id = ?",
                (state, timestamp, journey_id)
            )

            if message:
                cursor.execute(
                    """
                    INSERT INTO journey_steps
                    (journey_id, step_type, step_name, description, output_data, timestamp, status)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        journey_id, "state_change", f"state_update_{state}", message,
                        json.dumps({"new_state": state, "metrics": metrics}) if metrics else json.dumps({"new_state": state}),
                        timestamp, "completed"
                    )
                )
            conn.execute("COMMIT")
            logger.info(f"Journey state updated: {journey_id} - {state}")
            return True
    except sqlite3.OperationalError as oe:
        if "no such table" in str(oe):
            logger.error(f"Missing journey tracking tables: {str(oe)}")
        else:
            logger.error(f"Database error updating journey state: {str(oe)}")
        logger.debug(traceback.format_exc())
        return False
    except Exception as e:
        logger.error(f"Error updating journey state: {str(e)}")
        logger.debug(traceback.format_exc())
        return False

async def update_journey_state_async(
    journey_id: str,
    state: str,
    message: str = None,
    metrics: Dict[str, Any] = None
) -> bool:
    """
    Asynchronous version of update_journey_state.
    
    This function wraps the synchronous version and adds async compatibility,
    allowing it to be properly awaited in async contexts.
    
    Args:
        journey_id: The journey ID to update
        state: New state for the journey
        message: Optional message describing the state update
        metrics: Optional metrics to store with the state
        
    Returns:
        bool: True if successful
    """
    # Try with registered tracking function first, looking for async versions
    if 'update_journey_state' in _track_functions:
        try:
            func = _track_functions['update_journey_state']
            # Check if it's an async function
            if asyncio.iscoroutinefunction(func):
                # Call the async function with await
                return await func(
                    journey_id=journey_id,
                    state=state,
                    message=message,
                    metrics=metrics
                )
            else:
                # Call the sync function, but wrap the result in a coroutine
                # to ensure we always return an awaitable
                result = func(
                    journey_id=journey_id,
                    state=state,
                    message=message,
                    metrics=metrics
                )
                # Return the result directly without awaiting it since it's already a boolean
                return result
        except TypeError as e:
            # Handle missing positional argument 'self'
            if "'self'" in str(e):
                logger.warning(f"update_journey_state missing 'self' parameter: {str(e)}")
                
                # Try importing the static version if available
                try:
                    # Create a wrapper future for any synchronous result
                    loop = asyncio.get_event_loop()
                    future = loop.create_future()
                    
                    # Try to import BoardRoom's async version first
                    try:
                        from Handler.handler_board_room import update_journey_state as boardroom_update_state
                        if asyncio.iscoroutinefunction(boardroom_update_state):
                            return await boardroom_update_state(
                                journey_id=journey_id,
                                state=state,
                                message=message,
                                metrics=metrics
                            )
                    except Exception:
                        # Fall back to static version
                        from Handler.handler_board_room import update_journey_state_static
                        if asyncio.iscoroutinefunction(update_journey_state_static):
                            return await update_journey_state_static(
                                journey_id=journey_id,
                                state=state,
                                message=message,
                                metrics=metrics
                            )
                        else:
                            # Call the sync function but wrap in a coroutine
                            result = update_journey_state_static(
                                journey_id=journey_id,
                                state=state,
                                message=message,
                                metrics=metrics
                            )
                            future.set_result(result)
                            return await future
                except Exception as import_error:
                    logger.warning(f"Error importing update_journey_state_static: {str(import_error)}")
            else:
                # For other TypeError issues, fallback to default behavior
                logger.warning(f"TypeError in update_journey_state: {str(e)}")
        except Exception as e:
            logger.warning(f"Error calling update_journey_state: {str(e)}")
    
    # Fall back to the synchronous implementation
    # We need to wrap the result in a coroutine to ensure we return an awaitable
    try:
        # Create an event loop and future
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            # No event loop in this thread, create a new one
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
        # Create a future to wrap the synchronous result
        future = loop.create_future()
        
        # Call the synchronous function
        result = update_journey_state(
            journey_id=journey_id,
            state=state,
            message=message,
            metrics=metrics
        )
        
        # Set the result and return the future
        future.set_result(result)
        return await future  # Return the awaitable future, not the raw bool
    except Exception as e:
        logger.error(f"Error wrapping synchronous update_journey_state: {str(e)}")
        # Create a failed future as last resort
        future = asyncio.get_event_loop().create_future()
        future.set_result(False)
        return await future

async def complete_journey(
    journey_id: str,
    success: bool = True,
    result: Dict[str, Any] = None
) -> bool:
    """
    Mark a journey as complete.
    
    IMPORTANT: This is an async function and MUST be awaited when called.
    Use 'await complete_journey(...)' rather than just 'complete_journey(...)'
    
    Args:
        journey_id: The journey ID to complete
        success: Whether the journey was successful
        result: Optional result data
        
    Returns:
        bool: True if successful
    """
    # Check if journey_id is provided
    if not journey_id:
        logger.warning("No journey_id provided for complete_journey")
        return False
    
    # Try with registered tracking function first
    if 'complete_journey' in _track_functions:
        try:
            complete_journey_func = _track_functions['complete_journey']
            if asyncio.iscoroutinefunction(complete_journey_func):
                return await complete_journey_func(
                    journey_id=journey_id,
                    success=success,
                    result=result
                )
            else:
                return complete_journey_func(
                    journey_id=journey_id,
                    success=success,
                    result=result
                )
        except TypeError as e:
            # Handle missing positional argument 'self'
            if "'self'" in str(e):
                logger.warning(f"complete_journey missing 'self' parameter: {str(e)}")
                
                # Try importing the static version if available
                try:
                    from Handler.handler_board_room import complete_journey_static
                    if asyncio.iscoroutinefunction(complete_journey_static):
                        return await complete_journey_static(
                            journey_id=journey_id,
                            success=success,
                            result=result
                        )
                    else:
                        return complete_journey_static(
                            journey_id=journey_id,
                            success=success,
                            result=result
                        )
                except Exception as import_error:
                    logger.warning(f"Error importing complete_journey_static: {str(import_error)}")
            else:
                # For other TypeError issues, fallback to default behavior
                logger.warning(f"TypeError in complete_journey: {str(e)}")
        except Exception as e:
            logger.warning(f"Error calling complete_journey: {str(e)}")
    
    try:
        with v2_connection("journeys") as conn:
            timestamp = time.time()
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE request_journeys
                SET completed = ?, completion_time = ?, success = ?, last_updated = ?
                WHERE journey_id = ?
                """,
                (1, timestamp, 1 if success else 0, timestamp, journey_id)
            )
            if result:
                cursor.execute(
                    """
                    INSERT INTO journey_steps
                    (journey_id, step_type, step_name, description, output_data, timestamp, status)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (journey_id, "completion", "journey_completed",
                     "Journey completed" if success else "Journey failed",
                     json.dumps(result), timestamp, "completed")
                )
            logger.info(f"Journey completed: {journey_id} - Success: {success}")
            return True
    except Exception as e:
        logger.error(f"Error completing journey: {str(e)}")
        logger.debug(traceback.format_exc())
        return False

def get_communication_manager():
    """
    Get the model communication manager instance.
    
    Returns:
        The communication manager or None
    """
    global _communication_manager
    
    # Return cached instance if available
    if _communication_manager:
        return _communication_manager
    
    # Try to get communication manager from BoardRoom if available
    boardroom = get_boardroom()
    if boardroom and hasattr(boardroom, 'get_communication_manager'):
        try:
            _communication_manager = boardroom.get_communication_manager()
            return _communication_manager
        except Exception as e:
            logger.warning(f"Error getting communication manager from BoardRoom: {str(e)}")
    
    return None

async def send_model_message(
    message: Union[ModelMessage, Dict[str, Any], str],
    recipient: str = "all",
    message_type: str = None,
    context: Dict[str, Any] = None,
    journey_id: str = None,
    sender: str = "system"
) -> str:
    """
    Proxy function to forward model messages to the BoardRoom's implementation.
    
    This function ensures resources are properly initialized before 
    communicating with models, then forwards the message to BoardRoom's
    send_model_message implementation.
    
    Args:
        message: The message content, either as a ModelMessage object, dictionary, or string
        recipient: The model to send to (e.g., "gpt", "claude", "all")
        message_type: The type of message (e.g., "question", "analysis") if message is a string
        context: Additional context for the message if message is a string
        journey_id: Optional journey ID for tracking
        sender: The sender of the message if not part of message object
        
    Returns:
        String message ID of the sent message
    """
    # First, ensure that cache resources are initialized for optimal model operation
    try:
        # Check if cache initialization is completed
        # Only import here to avoid circular imports
        from Jarvis_Agent_SDK.workspace_reference_cache import (
            get_workspace_reference_cache,
            _cache_initializer
        )
        
        # Get current cache instance
        cache = get_workspace_reference_cache()
        
        # If the cache isn't initialized, log warning but continue
        if hasattr(cache, 'initialized') and not cache.initialized:
            logger.warning("Cache not fully initialized before model communication - some features may be limited")
            
            # Check if we're about to communicate with a specific model 
            # Specific models may need specific resources
            if recipient in ["claude", "gpt"] or recipient == "all":
                # Try to ensure critical resources are available
                try:
                    if hasattr(_cache_initializer, 'dependency_graph'):
                        # Check database (critical for operation)
                        database_resource = _cache_initializer.dependency_graph.get_resource("database")
                        if database_resource and not database_resource.is_loaded():
                            logger.warning(f"Warning: Database not loaded before {recipient} communication")
                        
                        # Log which model is being used with what resources
                        spacy_available = False
                        spacy_resource = _cache_initializer.dependency_graph.get_resource("spacy_model")
                        if spacy_resource:
                            spacy_available = spacy_resource.is_loaded()
                            
                        # Enhanced warnings for specific models
                        if recipient == "claude" and not spacy_available:
                            logger.warning("Claude communication without spaCy model - semantic search capabilities limited")
                        elif recipient == "gpt" and not spacy_available:
                            logger.warning("GPT communication without spaCy model - semantic search capabilities limited")
                except Exception as res_e:
                    logger.warning(f"Error checking resources before model communication: {str(res_e)}")
    except ImportError:
        # Module not found, just continue
        logger.warning("Could not import workspace_reference_cache to check initialization status")
    except Exception as cache_e:
        # Unexpected error, log and continue
        logger.warning(f"Error checking cache initialization before model communication: {str(cache_e)}")
    
    # Get BoardRoom instance
    boardroom = get_boardroom()
    if boardroom and hasattr(boardroom, 'send_model_message'):
        try:
            # Forward the call to BoardRoom's implementation
            if asyncio.iscoroutinefunction(boardroom.send_model_message):
                return await boardroom.send_model_message(
                    message=message,
                    recipient=recipient,
                    message_type=message_type,
                    context=context,
                    journey_id=journey_id,
                    sender=sender
                )
            else:
                return boardroom.send_model_message(
                    message=message,
                    recipient=recipient,
                    message_type=message_type,
                    context=context,
                    journey_id=journey_id,
                    sender=sender
                )
        except Exception as e:
            logger.warning(f"Error forwarding message to BoardRoom: {str(e)}")
    
    # If BoardRoom not available or method call failed, implement basic functionality here
    message_id = f"msg_{uuid.uuid4().hex[:8]}"
    
    # Log the message for testing purposes
    logger.info(f"[MODEL MESSAGE] To: {recipient} - Type: {message_type}")
    
    # Extract content for consistent format
    content = ""
    if isinstance(message, str):
        content = message
    elif isinstance(message, dict) and 'content' in message:
        content = message['content']
    elif isinstance(message, ModelMessage):
        content = message.content
    
    # Log content snippet
    content_snippet = content[:100] + "..." if len(content) > 100 else content
    logger.info(f"[MODEL MESSAGE] Content: {content_snippet}")
    
    # Store in global registry for testing if available
    try:
        if boardroom and hasattr(boardroom, 'model_messages'):
            model_msg = {
                'id': message_id,
                'message': content,
                'recipient': recipient,
                'message_type': message_type,
                'timestamp': time.time(),
                'direction': 'outgoing',
                'sender': sender
            }
            
            # Check for feature mentions
            feature_mentions = {}
            # Define feature categories we want to track
            feature_categories = {
                "claude_code": [
                    "Claude Code", "claude --verbose", "terminal handler", 
                    "infrastructure coding", "~/Jarvis directory"
                ],
                "boardroom_cache": [
                    "cache access", "BoardRoom cache", "resource cache", "cache contains", 
                    "cache data", "cache includes"
                ],
                "agent_modules": [
                    "handler_agent_builder", "handler_swarm", "handler_data_validator",
                    "structured_agent_system", "specialized agent", "agent module", 
                    "orchestrator agent"
                ],
                "personas": [
                    "specialized personas", "PUN_DIT", "PYTHON_BUG_BUSTER", "SQL_SORCERER",
                    "EXCEL_FORMULA_EXPERT", "HAL_HUMOROUS_HELPER", "COSMIC_KEYSTROKES",
                    "CODE_CONSULTANT", "PromptLibrary"
                ],
                "workspace": [
                    "workspace sharing", "team-based collaboration", "hierarchical workspace",
                    "workspace organization", "share workspaces", "workspace hierarchies"
                ],
                "database_query": [
                    "database information", "I need database information", "query the database",
                    "database for additional information"
                ],
                "resource_creation": [
                    "resource creation", "build custom tools", "build what's needed",
                    "novel requirements", "creating resources", "build new capabilities"
                ],
                "implementation_approach": [
                    "launch from the ~/Jarvis directory", 
                    "handler_terminal to control Claude Code",
                    "full access to the Jarvis directory structure",
                    "modifying codebase files", "adding new modules",
                    "debugging complex code", "running tests",
                    "view, edit, and create files"
                ]
            }
            
            # Loop through feature categories and find mentions
            for category, keywords in feature_categories.items():
                for keyword in keywords:
                    if keyword.lower() in content.lower():
                        if category not in feature_mentions:
                            feature_mentions[category] = []
                        feature_mentions[category].append(keyword)
            
            if feature_mentions:
                model_msg['feature_mentions'] = feature_mentions
                model_msg['any_feature_mentioned'] = True
                
                # Log findings for testing
                logger.info(f"[FEATURE DETECT] Found mentions in categories: {', '.join(feature_mentions.keys())}")
            else:
                model_msg['any_feature_mentioned'] = False
            
            # Add to boardroom's message list
            boardroom.model_messages.append(model_msg)
            
            # If no message registry exists, create one and store the message
            if not hasattr(boardroom, 'model_messages'):
                boardroom.model_messages = [model_msg]
    except Exception as e:
        logger.warning(f"Error processing model message features: {str(e)}")
    
    return message_id

def register_system_in_boardroom(system, system_name=None, capabilities=None, description=None):
    """
    Register an external system with the BoardRoom for collaboration.
    
    This function allows external systems to register themselves with the BoardRoom,
    making their capabilities available for collaborative problem-solving.
    
    Args:
        system: The system instance to register
        system_name: Name to register the system under (defaults to system.__class__.__name__)
        capabilities: List of capabilities this system provides
        description: Detailed description of what this system does
        
    Returns:
        bool: True if registration was successful, False otherwise
    """
    # Get BoardRoom instance
    boardroom = get_boardroom()
    if not boardroom:
        logger.error(f"Cannot register system: BoardRoom instance not available")
        return False
        
    try:
        # Check if the BoardRoom instance has a register_external_system method
        if hasattr(boardroom, 'register_external_system') and callable(boardroom.register_external_system):
            # Get the system name if not provided
            if not system_name:
                system_name = getattr(system, 'system_name', system.__class__.__name__)
                
            # Call the registration method
            result = boardroom.register_external_system(
                system=system,
                system_name=system_name,
                capabilities=capabilities,
                description=description
            )
            
            if result:
                logger.info(f"Successfully registered system '{system_name}' with BoardRoom")
                return True
            else:
                logger.warning(f"BoardRoom returned failure for system registration: {system_name}")
                return False
        else:
            # Try to register through the external_systems dictionary directly
            if hasattr(boardroom, 'external_systems') and isinstance(boardroom.external_systems, dict):
                # Get the system name if not provided
                if not system_name:
                    system_name = getattr(system, 'system_name', system.__class__.__name__)
                    
                # Create system info dict
                system_info = {
                    'instance': system,
                    'capabilities': capabilities or [],
                    'description': description or f"External system: {system_name}"
                }
                
                # Register in the dictionary
                boardroom.external_systems[system_name] = system_info
                logger.info(f"Directly registered system '{system_name}' with BoardRoom through external_systems dict")
                return True
            else:
                logger.error(f"BoardRoom has no registration mechanism available")
                return False
    except Exception as e:
        logger.error(f"Error registering system with BoardRoom: {str(e)}")
        logger.debug(traceback.format_exc())
        return False

async def async_register_system_in_boardroom(system, system_name=None, capabilities=None, description=None) -> bool:
    """
    Async version of register_system_in_boardroom.
    
    This function allows external systems to register themselves with the BoardRoom,
    making their capabilities available for collaborative problem-solving.
    
    Args:
        system: The system instance to register
        system_name: Name to register the system under (defaults to system.__class__.__name__)
        capabilities: List of capabilities this system provides
        description: Detailed description of what this system does
        
    Returns:
        bool: True if registration was successful, False otherwise
    """
    # Use a coroutine function to make it properly awaitable
    try:
        # Get the BoardRoom instance
        boardroom = get_boardroom()
        if not boardroom:
            logger.error("Could not get BoardRoom instance")
            return False
            
        # Use system name from parameter or derive from class
        if system_name is None:
            if hasattr(system, '__class__'):
                system_name = system.__class__.__name__
            else:
                system_name = str(system)
        
        # Check if the BoardRoom has the registration mechanism
        if hasattr(boardroom, 'register_system_in_boardroom'):
            # Register using the BoardRoom's method
            result = await boardroom.register_system_in_boardroom(
                system_name=system_name,
                system_type="external",
                capabilities=capabilities,
                metadata={"description": description} if description else None
            )
            logger.info(f"Registered system '{system_name}' with BoardRoom: {result}")
            return result
        elif hasattr(boardroom, 'external_systems'):
            # Create system info dict
            system_info = {
                'instance': system,
                'capabilities': capabilities or [],
                'description': description or f"External system: {system_name}"
            }
            
            # Register in the dictionary
            boardroom.external_systems[system_name] = system_info
            logger.info(f"Directly registered system '{system_name}' with BoardRoom through external_systems dict")
            return True
        else:
            logger.error(f"BoardRoom has no registration mechanism available")
            return False
    except Exception as e:
        logger.error(f"Error during registration: {str(e)}")
        import traceback
        logger.debug(traceback.format_exc())
        return False
        
def update_journey_with_request(journey_id, request, metadata=None):
    """
    Update a journey with user request details and notify the BoardRoom.
    
    This function allows the terminal to send user request information to an active
    BoardRoom conversation identified by journey_id.
    
    Args:
        journey_id: The journey ID associated with the conversation
        request: The user's request (text or object)
        metadata: Optional metadata about the request
        
    Returns:
        bool: True if the request was successfully processed, False otherwise
    """
    try:
        if not journey_id:
            logger.warning("Cannot update journey with user request: No journey ID provided")
            return False
            
        # Determine request text based on type
        if isinstance(request, dict) and 'text' in request:
            request_text = request['text']
        elif isinstance(request, dict) and 'description' in request:
            request_text = request['description']
        elif isinstance(request, str):
            request_text = request
        else:
            try:
                request_text = str(request)
            except:
                request_text = "Unknown request format"
        
        logger.info(f"Processing user request for journey {journey_id}: {request_text[:100]}...")
        
        # Track the user request as a journey step
        track_journey_step_sync(
            journey_id=journey_id,
            step_name=f"user_request_{int(time.time())}",
            description="User provided request",
            step_type="user_request",
            input_data={"request": request_text},
            metadata=metadata or {}
        )
        
        # Update the journey state to indicate user request was received
        update_journey_state(
            journey_id=journey_id,
            state="user_request_received",
            message="User provided request to the conversation",
            metrics={
                "user_request_received": True, 
                "request_timestamp": time.time(),
                "request_text": request_text,
                "request_object": request if isinstance(request, dict) else {"text": request_text}
            }
        )
        
        # Try to send request to BoardRoom instance if available
        boardroom = get_boardroom()
        if boardroom:
            # Try multiple methods to send the request to the BoardRoom instance
            
            # Method 1: Use process_user_request if available
            if hasattr(boardroom, 'process_user_request') and callable(boardroom.process_user_request):
                try:
                    logger.info(f"Using process_user_request method to send request")
                    if asyncio.iscoroutinefunction(boardroom.process_user_request):
                        # Create a new event loop for async execution if we're not in an async context
                        try:
                            loop = asyncio.get_event_loop()
                        except RuntimeError:
                            loop = asyncio.new_event_loop()
                            asyncio.set_event_loop(loop)
                        
                        # Run the async method
                        loop.run_until_complete(boardroom.process_user_request(
                            journey_id=journey_id,
                            request=request,
                            metadata=metadata or {}
                        ))
                    else:
                        # Call the sync method
                        boardroom.process_user_request(
                            journey_id=journey_id,
                            request=request,
                            metadata=metadata or {}
                        )
                    return True
                except Exception as e:
                    logger.warning(f"Error using process_user_request: {str(e)}")
            
            # Method 2: Use add_user_message if available
            if hasattr(boardroom, 'add_user_message') and callable(boardroom.add_user_message):
                try:
                    logger.info(f"Using add_user_message method to send request")
                    if asyncio.iscoroutinefunction(boardroom.add_user_message):
                        # Create a new event loop for async execution if we're not in an async context
                        try:
                            loop = asyncio.get_event_loop()
                        except RuntimeError:
                            loop = asyncio.new_event_loop()
                            asyncio.set_event_loop(loop)
                        
                        # Run the async method
                        loop.run_until_complete(boardroom.add_user_message(
                            request_text,
                            journey_id=journey_id,
                            metadata=metadata or {}
                        ))
                    else:
                        # Call the sync method
                        boardroom.add_user_message(
                            request_text,
                            journey_id=journey_id,
                            metadata=metadata or {}
                        )
                    return True
                except Exception as e:
                    logger.warning(f"Error using add_user_message: {str(e)}")
        
        # If we get here, we've updated the journey state but couldn't notify BoardRoom directly
        logger.info(f"Updated journey {journey_id} with user request, but no direct BoardRoom notification was possible")
        return True
    except Exception as e:
        logger.error(f"Error updating journey with user request: {str(e)}")
        logger.debug(traceback.format_exc())
        return False

def update_journey_with_user_feedback(journey_id, feedback, metadata=None, send_to_client=True):
    """
    Route BoardRoom feedback through Claude hub instead of direct storage.
    
    This function routes all BoardRoom user feedback through the Claude User Feedback Service
    for consistent user experience and enhanced feedback processing.
    
    Args:
        journey_id: The journey ID associated with the conversation
        feedback: The user's feedback message
        metadata: Optional metadata about the feedback
        send_to_client: Whether to send the feedback back to client UI for display
        
    Returns:
        dict: Result from Claude feedback processing or False if failed
    """
    try:
        if not journey_id:
            logger.warning("Cannot update journey with user feedback: No journey ID provided")
            return False
            
        logger.info(f"Routing BoardRoom feedback through Claude hub for journey {journey_id}: {feedback[:100]}...")
        
        # Route through Claude hub instead of direct storage
        try:
            from .claude_user_feedback_service import ClaudeUserFeedbackService
            claude_service = ClaudeUserFeedbackService()
            
            # Prepare context for Claude
            claude_context = {
                'journey_id': journey_id,
                'session_id': metadata.get('session_id') if metadata else None,
                'workspace_id': metadata.get('workspace_id') if metadata else None,
                'source': 'boardroom_connector'
            }
            
            # Route through Claude hub
            result = asyncio.run(claude_service.handle_feedback_request(
                source='boardroom_connector',
                request_data={'feedback_request': feedback},
                context=claude_context
            ))
            
            logger.info(f"Claude feedback processing complete for journey {journey_id}")
            
            # Log to journey tracking for historical purposes
            track_journey_step_sync(
                journey_id=journey_id,
                step_name=f"claude_feedback_{int(time.time())}",
                description="User feedback processed through Claude hub",
                step_type="claude_feedback",
                metadata={**(metadata or {}), "claude_processing": True, "claude_result": result}
            )
            
            # Update journey state
            update_journey_state(
                journey_id=journey_id,
                state="claude_feedback_processed",
                message="User feedback processed through Claude hub",
                metrics={"claude_feedback_processed": True, "feedback_timestamp": time.time()}
            )
            
            return result
            
        except ImportError as e:
            logger.error(f"Claude feedback service not available: {e}")
            # Fallback to original behavior
            logger.info("Falling back to direct feedback processing")
            
        # Fallback: Track the user feedback as a journey step (original behavior)
        track_journey_step_sync(
            journey_id=journey_id,
            step_name=f"user_feedback_{int(time.time())}",
            description="User provided feedback",
            step_type="user_feedback",
            metadata=metadata or {}
        )
        
        # Update the journey state to indicate user feedback was received
        update_journey_state(
            journey_id=journey_id,
            state="user_feedback_received",
            message="User provided feedback to the conversation",
            metrics={"user_feedback_received": True, "feedback_timestamp": time.time()}
        )
        
        # If send_to_client is enabled, try to send the feedback to the UI
        if send_to_client:
            try:
                # Try to import socketio from the api module
                # This is done conditionally to avoid circular imports
                from Core.user_ux.boardroom_api import socketio
                
                # Get session ID from metadata if available
                session_id = None
                if metadata and isinstance(metadata, dict):
                    session_id = metadata.get('session_id')
                
                # Emit the boardroom_feedback event
                if socketio:
                    logger.info(f"Emitting boardroom_feedback event for journey {journey_id}")
                    socketio.emit('boardroom_feedback', {
                        'journey_id': journey_id,
                        'feedback': feedback,
                        'timestamp': time.time()
                    }, room=session_id)
            except ImportError:
                logger.debug("Could not import socketio from boardroom_api - this is normal during tests")
            except Exception as e:
                logger.debug(f"Could not emit boardroom_feedback event: {str(e)}")
                # This is not a critical error, so we continue
        
        # Try to send feedback to BoardRoom instance if available
        boardroom = get_boardroom()
        if boardroom:
            # Try multiple methods to send feedback to the BoardRoom instance
            
            # Method 1: Use process_user_feedback if available (prioritize the new method)
            if hasattr(boardroom, 'process_user_feedback') and callable(boardroom.process_user_feedback):
                try:
                    logger.info(f"Using process_user_feedback method to send feedback")
                    if asyncio.iscoroutinefunction(boardroom.process_user_feedback):
                        # Create a new event loop for async execution if we're not in an async context
                        try:
                            # Check if we're in an async context already
                            asyncio.get_running_loop()
                            # If no exception, we're in an async context and can create a task
                            asyncio.create_task(boardroom.process_user_feedback(feedback, journey_id))
                            logger.info(f"Created async task to process user feedback")
                        except RuntimeError:
                            # Not in async context, use run_coroutine_threadsafe
                            logger.info(f"Using threadsafe approach to run async feedback processing")
                            loop = asyncio.new_event_loop()
                            asyncio.set_event_loop(loop)
                            try:
                                loop.run_until_complete(boardroom.process_user_feedback(feedback, journey_id))
                            finally:
                                loop.close()
                    else:
                        # Non-async method
                        boardroom.process_user_feedback(feedback, journey_id)
                    logger.info(f"Successfully sent feedback to BoardRoom using process_user_feedback")
                    return True
                except Exception as e:
                    logger.warning(f"Error using process_user_feedback: {str(e)}")
            
            # Method 2: Use add_user_message if available (fallback)
            if hasattr(boardroom, 'add_user_message') and callable(boardroom.add_user_message):
                try:
                    logger.info(f"Using add_user_message method to send feedback")
                    if asyncio.iscoroutinefunction(boardroom.add_user_message):
                        # Create a new event loop for async execution if we're not in an async context
                        try:
                            # Check if we're in an async context already
                            asyncio.get_running_loop()
                            # If no exception, we're in an async context and can create a task
                            asyncio.create_task(boardroom.add_user_message(feedback, journey_id))
                            logger.info(f"Created async task to add user message")
                        except RuntimeError:
                            # Not in async context, use run_coroutine_threadsafe
                            logger.info(f"Using threadsafe approach to run async message processing")
                            loop = asyncio.new_event_loop()
                            asyncio.set_event_loop(loop)
                            try:
                                loop.run_until_complete(boardroom.add_user_message(feedback, journey_id))
                            finally:
                                loop.close()
                    else:
                        # Non-async method
                        boardroom.add_user_message(feedback, journey_id)
                    logger.info(f"Successfully sent feedback to BoardRoom using add_user_message")
                    return True
                except Exception as e:
                    logger.warning(f"Error using add_user_message: {str(e)}")
                    
            # Method 3: Use add_message if available (lowest priority fallback)
            if hasattr(boardroom, 'add_message') and callable(boardroom.add_message):
                try:
                    logger.info(f"Using add_message method to send feedback")
                    if asyncio.iscoroutinefunction(boardroom.add_message):
                        # Create a new event loop for async execution if we're not in an async context
                        try:
                            # Check if we're in an async context already
                            asyncio.get_running_loop()
                            # If no exception, we're in an async context and can create a task
                            asyncio.create_task(boardroom.add_message("user", feedback))
                            logger.info(f"Created async task to add user message")
                        except RuntimeError:
                            # Not in async context, use run_coroutine_threadsafe
                            logger.info(f"Using threadsafe approach to run async message processing")
                            loop = asyncio.new_event_loop()
                            asyncio.set_event_loop(loop)
                            try:
                                loop.run_until_complete(boardroom.add_message("user", feedback))
                            finally:
                                loop.close()
                    else:
                        # Non-async method
                        boardroom.add_message("user", feedback)
                    logger.info(f"Successfully sent feedback to BoardRoom using add_message")
                    return True
                except Exception as e:
                    logger.warning(f"Error using add_message: {str(e)}")
        
        # If we reach here, we couldn't send feedback directly to the BoardRoom instance
        # but we did track it in the journey, so return True
        logger.info(f"Tracked user feedback in journey but couldn't send directly to BoardRoom")
        return True
    except Exception as e:
        logger.error(f"Error updating journey with user feedback: {str(e)}")
        return False


