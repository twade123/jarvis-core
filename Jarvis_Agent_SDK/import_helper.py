#!/usr/bin/env python3
"""
Import Helper Module

This module provides helper functions to handle circular dependencies in the Jarvis Agent SDK.
It uses runtime imports instead of module-level imports to avoid circular dependencies.

Usage:
    Instead of importing directly, use the helper functions like:
    
    agent_builder = import_helper.get_agent_builder()
    analyze_handler_capabilities = import_helper.get_analyze_handler_capabilities()
"""

import logging
import importlib
import sys
import traceback
from importlib.util import find_spec
import time
import inspect
import os
from typing import Union, Optional, Dict, Any, Callable

# Import only the essential function needed for existing code
# For boardroom functionality, modules should import directly from boardroom_connector
try:
    from .boardroom_connector import generate_simple_id
except ImportError:
    # Fallback for direct execution
    from boardroom_connector import generate_simple_id

# Create a module-level logger
logger = logging.getLogger(__name__)

# Global variables
_unified_database = None
_database_path = None
_direct_import_attempted = False
_handler_all_cache = None
# Note: BoardRoom-related cache variables have been removed

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Cache for imported modules and attributes
_cache = {}

# Individual caches for specific functions to avoid looking them up repeatedly
_register_system_in_boardroom_cache = None
_analyze_task_capabilities_cache = None
_process_with_agent_cache = None
_agent_components_cache = None
_track_request_journey_cache = None
_track_journey_step_cache = None
_get_track_journey_step_cache = None

# Add cache variables for new components
_structured_agent_system_cache = None
_structured_outputs_multi_agent_cache = None
_swarm_handler_cache = None

# Add direct component cache variables
# Structured agent system caches
_structured_agent_type_cache = None
_structured_agent_specialization_cache = None
_structured_agent_capability_cache = None
_structured_agent_builder_cache = None
_structured_multi_agent_system_cache = None
_structured_process_task_cache = None

# Structured outputs caches
_process_structured_task_cache = None
_handle_data_processing_agent_cache = None
_handle_analysis_agent_cache = None
_handle_visualization_agent_cache = None

# Swarm handler caches
_swarm_handler_class_cache = None
_swarm_agent_cache = None
_handle_swarm_intent_cache = None
_boardroom_instance_cache = None

# Add cache variables for execute handler functions
_execute_handler_action_async_cache = None
_execute_handler_action_cache = None

# Workspace sharing manager
_workspace_sharing_manager = None

# Handler system
_handler_system = None

# Agent loader
_agent_loader = None

# Unified database global cache
_unified_database_cache = None

# Function to get HandlerAll module from handler_all.py
def get_handler_all():
    """
    Get the HandlerAll module or class from Handler.handler_all.
    Uses lazy loading to avoid circular imports.
    
    Returns:
        HandlerAll module or class, or None if not available
    """
    global _handler_all_cache
    
    if _handler_all_cache is not None:
        return _handler_all_cache
    
    try:
        # Use dynamic import instead of direct import to avoid circular dependencies
        # This approach prevents Python from loading the module at import time
        import importlib.util
        import sys
        import os
        
        # Get the path to handler_all.py
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        handler_all_path = os.path.join(base_dir, "Handler", "handler_all.py")
        
        # Create a stub class with placeholders
        # This avoids the circular imports by not directly accessing module attributes
        class HandlerAll:
            @staticmethod
            def execute_handler(*args, **kwargs):
                """Stub for execute_handler that dynamically imports when needed"""
                # Dynamically import the function only when called
                try:
                    handler_all_spec = importlib.util.spec_from_file_location("Handler.handler_all", handler_all_path)
                    handler_all_module = importlib.util.module_from_spec(handler_all_spec)
                    handler_all_spec.loader.exec_module(handler_all_module)
                    # Call the real function
                    return handler_all_module.execute_handler(*args, **kwargs)
                except Exception as e:
                    logging.error(f"Error in execute_handler stub: {e}")
                    return None
                
            @staticmethod
            def get_all_handlers():
                """
                Get information about all available handlers.
                
                Returns:
                    Dictionary mapping handler names to their capabilities and metadata
                """
                # Try to get handler info from database directly first
                try:
                    from Jarvis_Agent_SDK.database_directory import get_database_directory
                    db = get_database_directory()
                    if db and hasattr(db, 'get_all_handlers'):
                        return db.get_all_handlers()
                except Exception as e:
                    logging.warning(f"Error getting handlers from database: {str(e)}")
                
                # Create a basic handlers dictionary
                handlers = {}
                
                # Fallback to reading the handler directory directly
                try:
                    # Get all handler files
                    handler_dir = os.path.join(base_dir, "Handler")
                    import glob
                    handler_files = glob.glob(os.path.join(handler_dir, "handler_*.py"))
                    for handler_file in handler_files:
                        if os.path.basename(handler_file) in ['handler_all.py', 'handler_base.py']:
                            continue
                        # Extract handler name from filename
                        handler_name = os.path.basename(handler_file).replace("handler_", "").replace(".py", "")
                        handlers[handler_name] = {
                            'name': handler_name,
                            'type': 'unknown',
                            'category': 'general',
                            'capabilities': []
                        }
                except Exception as e:
                    logging.warning(f"Error reading handler directory: {str(e)}")
                
                return handlers
        
        # Access system object via property to lazy load it
        @property
        def handler_system(self):
            """Lazy-load handler_system only when needed"""
            try:
                # Import using importlib to avoid circular dependencies
                spec = importlib.util.spec_from_file_location("Handler.handler_all", handler_all_path)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                return getattr(module, "handler_system", None)
            except Exception as e:
                logging.warning(f"Error lazy-loading handler_system: {str(e)}")
                return None
                
        # Add property to class
        HandlerAll.handler_system = property(handler_system)
        
        # Store in cache and return
        _handler_all_cache = HandlerAll()
        logging.info("Successfully loaded HandlerAll components with dynamic imports")
        return _handler_all_cache
    except ImportError as e:
        logging.warning(f"Could not import HandlerAll - circular import detected: {e}")
    except Exception as e:
        logging.error(f"Error loading HandlerAll components: {e}")
        traceback.print_exc()
    
    return None

# Note: BoardRoom access has been completely removed
# All modules should use boardroom_connector.py directly for all BoardRoom functionality
# This eliminates circular dependencies and centralizes BoardRoom access

# Agent Builder related imports
def get_agent_builder():
    """
    Get the AgentBuilder class from Handler.handler_agent_builder
    
    Returns:
        The AgentBuilder class
    """
    module_path = "Handler.handler_agent_builder"
    attribute = "AgentBuilder"
    
    # Return cached version if available
    cache_key = f"{module_path}.{attribute}"
    if cache_key in _cache:
        return _cache[cache_key]
    
    # Try direct import
    try:
        module = importlib.import_module(module_path)
        if hasattr(module, attribute):
            result = getattr(module, attribute)
            _cache[cache_key] = result
            return result
    except (ImportError, AttributeError) as e:
        logger.warning(f"Direct import failed for {attribute} from {module_path}: {str(e)}")
        # Fall back to safe import
        return _safe_import(module_path, attribute)
    
    # If we get here, try safe import as a fallback
    return _safe_import(module_path, attribute)

def get_agent_type():
    """
    Get the AgentType class from Handler.handler_agent_builder
    
    Returns:
        The AgentType class
    """
    module_path = "Handler.handler_agent_builder"
    attribute = "AgentType"
    
    # Return cached version if available
    cache_key = f"{module_path}.{attribute}"
    if cache_key in _cache:
        return _cache[cache_key]
    
    # Try direct import
    try:
        module = importlib.import_module(module_path)
        if hasattr(module, attribute):
            result = getattr(module, attribute)
            _cache[cache_key] = result
            return result
    except (ImportError, AttributeError) as e:
        logger.warning(f"Direct import failed for {attribute} from {module_path}: {str(e)}")
        # Fall back to safe import
        return _safe_import(module_path, attribute)
    
    # If we get here, try safe import as a fallback
    return _safe_import(module_path, attribute)
    
def get_agent_specialization():
    """
    Get the AgentSpecialization class from Handler.handler_agent_builder
    
    Returns:
        The AgentSpecialization class
    """
    module_path = "Handler.handler_agent_builder"
    attribute = "AgentSpecialization"
    
    # Return cached version if available
    cache_key = f"{module_path}.{attribute}"
    if cache_key in _cache:
        return _cache[cache_key]
    
    # Try direct import
    try:
        module = importlib.import_module(module_path)
        if hasattr(module, attribute):
            result = getattr(module, attribute)
            _cache[cache_key] = result
            return result
    except (ImportError, AttributeError) as e:
        logger.warning(f"Direct import failed for {attribute} from {module_path}: {str(e)}")
        # Fall back to safe import
        return _safe_import(module_path, attribute)
    
    # If we get here, try safe import as a fallback
    return _safe_import(module_path, attribute)
    
def get_agent_capability():
    """
    Get the AgentCapability class from Handler.handler_agent_builder
    
    Returns:
        The AgentCapability class
    """
    module_path = "Handler.handler_agent_builder"
    attribute = "AgentCapability"
    
    # Return cached version if available
    cache_key = f"{module_path}.{attribute}"
    if cache_key in _cache:
        return _cache[cache_key]
    
    # Try direct import
    try:
        module = importlib.import_module(module_path)
        if hasattr(module, attribute):
            result = getattr(module, attribute)
            _cache[cache_key] = result
            return result
    except (ImportError, AttributeError) as e:
        logger.warning(f"Direct import failed for {attribute} from {module_path}: {str(e)}")
        # Fall back to safe import
        return _safe_import(module_path, attribute)
    
    # If we get here, try safe import as a fallback
    return _safe_import(module_path, attribute)
    
def get_agent_tool():
    """
    Get the AgentTool class from Handler.handler_agent_builder
    
    Returns:
        The AgentTool class
    """
    module_path = "Handler.handler_agent_builder"
    attribute = "AgentTool"
    
    # Return cached version if available
    cache_key = f"{module_path}.{attribute}"
    if cache_key in _cache:
        return _cache[cache_key]
    
    # Try direct import
    try:
        module = importlib.import_module(module_path)
        if hasattr(module, attribute):
            result = getattr(module, attribute)
            _cache[cache_key] = result
            return result
    except (ImportError, AttributeError) as e:
        logger.warning(f"Direct import failed for {attribute} from {module_path}: {str(e)}")
        # Fall back to safe import
        return _safe_import(module_path, attribute)
    
    # If we get here, try safe import as a fallback
    return _safe_import(module_path, attribute)

# Orchestrator related imports
# Note: BoardRoom tracking functions have been removed
# All modules should use boardroom_connector.py directly for tracking functions
# This eliminates circular dependencies and centralizes BoardRoom functionality

# Note: get_register_system_in_boardroom has been removed
# All modules should use boardroom_connector.py directly for BoardRoom system registration
# This eliminates circular dependencies and centralizes BoardRoom functionality

def get_analyze_task_capabilities():
    """
    Returns the analyze_task_capabilities function from common_utils.
    
    This function is now imported from common_utils to avoid circular imports.
    
    Returns:
        function: A function that analyzes task capabilities
    """
    global _analyze_task_capabilities_cache

    if _analyze_task_capabilities_cache is not None:
        return _analyze_task_capabilities_cache

    try:
        # Try direct import from common_utils, which is the new location
        from Jarvis_Agent_SDK.common_utils import analyze_task_capabilities
        _analyze_task_capabilities_cache = analyze_task_capabilities
        return analyze_task_capabilities
    except (ImportError, AttributeError) as e:
        # Fallback to safe import method
        logging.warning(f"Import error for analyze_task_capabilities: {str(e)}")
        
        try:
            # Try dynamic import from common_utils
            common_utils = _safe_import("Jarvis_Agent_SDK.common_utils")
            if hasattr(common_utils, "analyze_task_capabilities"):
                analyze_task_capabilities = getattr(common_utils, "analyze_task_capabilities")
                _analyze_task_capabilities_cache = analyze_task_capabilities
                return analyze_task_capabilities
            else:
                raise ImportError(f"analyze_task_capabilities not found in common_utils")
        except Exception as e:
            logging.warning(f"Failed to import analyze_task_capabilities: {str(e)}")
            raise ImportError(f"Could not import analyze_task_capabilities: {str(e)}")

def get_process_with_agent():
    """
    Get the process_with_agent function safely from Handler.handler_agent_builder.
    
    This function processes a task with a specialized agent.
    
    Returns:
        The process_with_agent function from the AgentBuilder class
    """
    # Direct import is avoided to prevent circular dependencies
    module_path = "Handler.handler_agent_builder"
    attribute = "process_with_agent"
    
    # Return cached version if available
    cache_key = f"{module_path}.{attribute}"
    if cache_key in _cache:
        return _cache[cache_key]
    
    # Import the AgentBuilder class using our own helper function
    try:
        agent_builder_class = get_agent_builder()
        if agent_builder_class:
            # Create a wrapper function that instantiates AgentBuilder and calls its process_with_agent method
            def process_with_agent_wrapper(agent_config, task, extra_context=None):
                builder_instance = agent_builder_class()
                return builder_instance.process_with_agent(agent_config, task, extra_context)
            
            _cache[cache_key] = process_with_agent_wrapper
            return process_with_agent_wrapper
    except (ImportError, AttributeError, TypeError) as e:
        logger.warning(f"Could not create process_with_agent wrapper: {str(e)}")
        # Fall back to direct import
        
    # Direct import if AgentBuilder import fails
    try:
        module = importlib.import_module(module_path)
        if hasattr(module, attribute):
            result = getattr(module, attribute)
            _cache[cache_key] = result
            return result
    except (ImportError, AttributeError) as e:
        logger.warning(f"Direct import failed for {attribute} from {module_path}: {str(e)}")
        # Fall back to safe import
        return _safe_import(module_path, attribute)
    
    # If we get here, try safe import as a fallback
    return _safe_import(module_path, attribute)

# Note: BoardRoom access removed
# All modules should use boardroom_connector directly
# This function has been removed to eliminate circular dependencies

# Structured agent system related imports
def get_structured_agent_system():
    """
    Get components from the structured_agent_system module.
    
    Returns:
        Dict with AgentType, AgentSpecialization, AgentCapability, etc.
    """
    global _structured_agent_system_cache
    
    if _structured_agent_system_cache is not None:
        return _structured_agent_system_cache
    
    try:
        # Try multiple possible import paths for the structured_agent_system module
        try:
            # First try direct import from root directory
            import structured_agent_system as sas
        except ImportError:
            try:
                # Then try from Handler package
                import Handler.structured_agent_system as sas
            except ImportError:
                # As a last resort, try as a relative import
                from .. import structured_agent_system as sas
        
        components = {
            "AgentType": getattr(sas, "AgentType", None),
            "AgentSpecialization": getattr(sas, "AgentSpecialization", None),
            "AgentCapability": getattr(sas, "AgentCapability", None),
            "AgentBuilder": getattr(sas, "AgentBuilder", None),
            "MultiAgentSystem": getattr(sas, "MultiAgentSystem", None),
            "process_task": getattr(sas, "process_task", None),
            "invoke_structured_agent_system": getattr(sas, "invoke_structured_agent_system", None)
        }
        
        _structured_agent_system_cache = components
        return components
        
    except (ImportError, AttributeError) as e:
        logger.warning(f"Cannot import structured_agent_system components: {str(e)}")
        
        # Try individual safe imports
        components = {}
        
        # Try multiple import paths
        module_paths = ["structured_agent_system", "Handler.structured_agent_system"]
        
        for module_path in module_paths:
            for attr in ["AgentType", "AgentSpecialization", "AgentCapability", "AgentBuilder", 
                        "MultiAgentSystem", "process_task", "invoke_structured_agent_system"]:
                component = _safe_import(module_path, attr)
                if component is not None:
                    components[attr] = component
                    break
            
        _structured_agent_system_cache = components
        return components

# Structured outputs multi-agent related imports
def get_structured_outputs_multi_agent():
    """
    Get components from the Structured_outputs_multi_agent module.
    
    Returns:
        Dict with process_task, handle_data_processing_agent, etc.
    """
    global _structured_outputs_multi_agent_cache
    
    if _structured_outputs_multi_agent_cache is not None:
        return _structured_outputs_multi_agent_cache
    
    try:
        # Try multiple possible import paths
        try:
            # First try direct import from root directory
            import Structured_outputs_multi_agent as soma
        except ImportError:
            try:
                # Then try from Handler package
                import Handler.Structured_outputs_multi_agent as soma
            except ImportError:
                # As a last resort, try as a relative import
                from .. import Structured_outputs_multi_agent as soma
        
        components = {
            "process_structured_task": getattr(soma, "process_structured_task", None),
            "handle_data_processing_agent": getattr(soma, "handle_data_processing_agent", None),
            "handle_analysis_agent": getattr(soma, "handle_analysis_agent", None),
            "handle_visualization_agent": getattr(soma, "handle_visualization_agent", None),
            "clean_data": getattr(soma, "clean_data", None),
            "stat_analysis": getattr(soma, "stat_analysis", None),
            "plot_line_chart": getattr(soma, "plot_line_chart", None)
        }
        
        _structured_outputs_multi_agent_cache = components
        return components
        
    except (ImportError, AttributeError) as e:
        logger.warning(f"Cannot import Structured_outputs_multi_agent components: {str(e)}")
        
        # Try individual safe imports
        components = {}
        
        # Try multiple import paths
        module_paths = ["Structured_outputs_multi_agent", "Handler.Structured_outputs_multi_agent"]
        
        for module_path in module_paths:
            for attr in ["process_structured_task", "handle_data_processing_agent", "handle_analysis_agent",
                        "handle_visualization_agent", "clean_data", "stat_analysis", "plot_line_chart"]:
                component = _safe_import(module_path, attr)
                if component is not None:
                    components[attr] = component
                    break
            
        _structured_outputs_multi_agent_cache = components
        return components

# Swarm handler related imports
def get_swarm_handler():
    """
    Get components from the handler_swarm module.
    
    Returns:
        Dict with SwarmHandler, SwarmAgent, etc.
    """
    global _swarm_handler_cache
    
    if _swarm_handler_cache is not None:
        return _swarm_handler_cache
    
    try:
        # Try to directly import the components
        import Handler.handler_swarm as swarm
        
        components = {
            "SwarmHandler": getattr(swarm, "SwarmHandler", None),
            "SwarmAgent": getattr(swarm, "SwarmAgent", None),
            "handle_swarm_intent": getattr(swarm, "handle_swarm_intent", None)
        }
        
        _swarm_handler_cache = components
        return components
        
    except (ImportError, AttributeError) as e:
        logger.warning(f"Cannot import handler_swarm components: {str(e)}")
        
        # Try individual safe imports
        components = {}
        module_path = "Handler.handler_swarm"
        
        for attr in ["SwarmHandler", "SwarmAgent", "handle_swarm_intent"]:
            components[attr] = _safe_import(module_path, attr)
            
        _swarm_handler_cache = components
        return components

# Direct structured_agent_system component imports
def get_structured_agent_type():
    """
    Get the AgentType enum from structured_agent_system.
    
    Returns:
        AgentType enum or None if not available
    """
    global _structured_agent_type_cache
    
    if _structured_agent_type_cache is not None:
        return _structured_agent_type_cache
    
    try:
        # Try multiple possible import paths
        try:
            # First try direct import from root directory
            from structured_agent_system import AgentType
        except ImportError:
            try:
                # Then try from Handler package
                from Handler.structured_agent_system import AgentType
            except ImportError:
                # Try getting it from the components cache
                components = get_structured_agent_system()
                AgentType = components.get("AgentType")
        
        _structured_agent_type_cache = AgentType
        return AgentType
    except (ImportError, AttributeError) as e:
        logger.warning(f"Import error for structured_agent_system.AgentType: {e}")
        return None

def get_structured_agent_specialization():
    """
    Get the AgentSpecialization class from structured_agent_system.
    
    Returns:
        AgentSpecialization class or None if not available
    """
    global _structured_agent_specialization_cache
    
    if _structured_agent_specialization_cache is not None:
        return _structured_agent_specialization_cache
    
    try:
        # Try multiple possible import paths
        try:
            # First try direct import from root directory
            from structured_agent_system import AgentSpecialization
        except ImportError:
            try:
                # Then try from Handler package
                from Handler.structured_agent_system import AgentSpecialization
            except ImportError:
                # Try getting it from the components cache
                components = get_structured_agent_system()
                AgentSpecialization = components.get("AgentSpecialization")
        
        _structured_agent_specialization_cache = AgentSpecialization
        return AgentSpecialization
    except (ImportError, AttributeError) as e:
        logger.warning(f"Import error for structured_agent_system.AgentSpecialization: {e}")
        return None

def get_structured_agent_capability():
    """
    Get the AgentCapability enum from structured_agent_system.
    
    Returns:
        AgentCapability enum or None if not available
    """
    global _structured_agent_capability_cache
    
    if _structured_agent_capability_cache is not None:
        return _structured_agent_capability_cache
    
    try:
        # Try multiple possible import paths
        try:
            # First try direct import from root directory
            from structured_agent_system import AgentCapability
        except ImportError:
            try:
                # Then try from Handler package
                from Handler.structured_agent_system import AgentCapability
            except ImportError:
                # Try getting it from the components cache
                components = get_structured_agent_system()
                AgentCapability = components.get("AgentCapability")
        
        _structured_agent_capability_cache = AgentCapability
        return AgentCapability
    except (ImportError, AttributeError) as e:
        logger.warning(f"Import error for structured_agent_system.AgentCapability: {e}")
        return None

def get_structured_agent_builder():
    """
    Get the AgentBuilder class from structured_agent_system.
    
    Returns:
        AgentBuilder class or None if not available
    """
    global _structured_agent_builder_cache
    
    if _structured_agent_builder_cache is not None:
        return _structured_agent_builder_cache
    
    try:
        # Try multiple possible import paths
        try:
            # First try direct import from root directory
            from structured_agent_system import AgentBuilder
        except ImportError:
            try:
                # Then try from Handler package
                from Handler.structured_agent_system import AgentBuilder
            except ImportError:
                # Try getting it from the components cache
                components = get_structured_agent_system()
                AgentBuilder = components.get("AgentBuilder")
        
        _structured_agent_builder_cache = AgentBuilder
        return AgentBuilder
    except (ImportError, AttributeError) as e:
        logger.warning(f"Import error for structured_agent_system.AgentBuilder: {e}")
        return None

def get_structured_multi_agent_system():
    """
    Get the MultiAgentSystem class from structured_agent_system.
    
    Returns:
        The MultiAgentSystem class from structured_agent_system
    """
    global _structured_multi_agent_system_cache
    
    if _structured_multi_agent_system_cache is not None:
        return _structured_multi_agent_system_cache
    
    # Ensure root directory is in path
    import os
    import sys
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if root_dir not in sys.path:
        sys.path.insert(0, root_dir)
    
    # Direct import from root module
    from structured_agent_system import MultiAgentSystem
    _structured_multi_agent_system_cache = MultiAgentSystem
    return MultiAgentSystem

def get_structured_process_task():
    """
    Get the process_task function from structured_agent_system.
    
    Returns:
        The process_task function from structured_agent_system
    """
    global _structured_process_task_cache
    
    if _structured_process_task_cache is not None:
        return _structured_process_task_cache
    
    # Ensure root directory is in path
    import os
    import sys
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if root_dir not in sys.path:
        sys.path.insert(0, root_dir)
    
    # Direct import from root module
    from structured_agent_system import process_task
    _structured_process_task_cache = process_task
    return process_task

# Structured outputs multi-agent component imports
def get_process_structured_task():
    """
    Get the process_structured_task function from Structured_outputs_multi_agent.
    
    Returns:
        process_structured_task function or None if not available
    """
    global _process_structured_task_cache
    
    if _process_structured_task_cache is not None:
        return _process_structured_task_cache
    
    # Ensure root directory is in path
    import os
    import sys
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if root_dir not in sys.path:
        sys.path.insert(0, root_dir)
    
    # Direct import from root module
    from Structured_outputs_multi_agent import process_structured_task
    _process_structured_task_cache = process_structured_task
    return process_structured_task

def get_handle_data_processing_agent():
    """
    Get the handle_data_processing_agent function from Structured_outputs_multi_agent.
    
    Returns:
        handle_data_processing_agent function or None if not available
    """
    global _handle_data_processing_agent_cache
    
    if _handle_data_processing_agent_cache is not None:
        return _handle_data_processing_agent_cache
    
    # Ensure root directory is in path
    import os
    import sys
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if root_dir not in sys.path:
        sys.path.insert(0, root_dir)
    
    # Direct import from root module
    from Structured_outputs_multi_agent import handle_data_processing_agent
    _handle_data_processing_agent_cache = handle_data_processing_agent
    return handle_data_processing_agent

def get_handle_analysis_agent():
    """
    Get the handle_analysis_agent function from Structured_outputs_multi_agent.
    
    Returns:
        handle_analysis_agent function or None if not available
    """
    global _handle_analysis_agent_cache
    
    if _handle_analysis_agent_cache is not None:
        return _handle_analysis_agent_cache
    
    # Ensure root directory is in path
    import os
    import sys
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if root_dir not in sys.path:
        sys.path.insert(0, root_dir)
    
    # Direct import from root module
    from Structured_outputs_multi_agent import handle_analysis_agent
    _handle_analysis_agent_cache = handle_analysis_agent
    return handle_analysis_agent

def get_handle_visualization_agent():
    """
    Get the handle_visualization_agent function from Structured_outputs_multi_agent.
    
    Returns:
        handle_visualization_agent function or None if not available
    """
    global _handle_visualization_agent_cache
    
    if _handle_visualization_agent_cache is not None:
        return _handle_visualization_agent_cache
    
    # Ensure root directory is in path
    import os
    import sys
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if root_dir not in sys.path:
        sys.path.insert(0, root_dir)
    
    # Direct import from root module
    from Structured_outputs_multi_agent import handle_visualization_agent
    _handle_visualization_agent_cache = handle_visualization_agent
    return handle_visualization_agent

# Swarm handler component imports
def get_swarm_handler_class():
    """
    Get the SwarmHandler class from handler_swarm.
    
    Returns:
        The SwarmHandler class
    """
    module_path = "Handler.handler_swarm"
    attribute = "SwarmHandler"
    
    # Return cached version if available
    cache_key = f"{module_path}.{attribute}"
    if cache_key in _cache:
        return _cache[cache_key]
    
    try:
        module = importlib.import_module(module_path)
        if hasattr(module, attribute):
            result = getattr(module, attribute)
            _cache[cache_key] = result
            return result
    except (ImportError, AttributeError) as e:
        logger.warning(f"Direct import failed for {attribute} from {module_path}: {str(e)}")
        
    # Fall back to safe import
    return _safe_import(module_path, attribute)

def get_swarm_agent_class():
    """
    Get the SwarmAgent class from handler_swarm.
    
    Returns:
        The SwarmAgent class
    """
    module_path = "Handler.handler_swarm"
    attribute = "SwarmAgent"
    
    # Return cached version if available
    cache_key = f"{module_path}.{attribute}"
    if cache_key in _cache:
        return _cache[cache_key]
    
    try:
        module = importlib.import_module(module_path)
        if hasattr(module, attribute):
            result = getattr(module, attribute)
            _cache[cache_key] = result
            return result
    except (ImportError, AttributeError) as e:
        logger.warning(f"Direct import failed for {attribute} from {module_path}: {str(e)}")
        
    # Fall back to safe import
    return _safe_import(module_path, attribute)

def get_handle_swarm_intent():
    """
    Get the handle_swarm_intent function from handler_swarm.
    
    Returns:
        The handle_swarm_intent function
    """
    module_path = "Handler.handler_swarm"
    attribute = "handle_swarm_intent"
    
    # Return cached version if available
    cache_key = f"{module_path}.{attribute}"
    if cache_key in _cache:
        return _cache[cache_key]
    
    try:
        module = importlib.import_module(module_path)
        if hasattr(module, attribute):
            result = getattr(module, attribute)
            _cache[cache_key] = result
            return result
    except (ImportError, AttributeError) as e:
        logger.warning(f"Direct import failed for {attribute} from {module_path}: {str(e)}")
        
    # Fall back to safe import
    return _safe_import(module_path, attribute)

# Update get_agent_components to also include the new direct imports
def get_agent_components():
    """
    Returns a dictionary of agent components functions.
    
    This function tries to import all agent component functions and returns
    them in a dictionary. If a function cannot be imported due to circular imports
    or other errors, it will log a warning and continue with the other functions.
    
    Returns:
        dict: A dictionary containing all available agent component functions
    """
    global _agent_components_cache
    
    if _agent_components_cache is not None:
        return _agent_components_cache
    
    components = {}
    
    # Define component getters
    component_getters = {
        # Core agent builder components
        "AgentBuilder": get_agent_builder,
        "AgentType": get_agent_type,
        "AgentSpecialization": get_agent_specialization,
        "AgentCapability": get_agent_capability,
        "AgentTool": get_agent_tool,
        
        # Orchestrator functions
        # Note: BoardRoom-related functions have been removed, use boardroom_connector directly
        'analyze_task_capabilities': get_analyze_task_capabilities,
        'process_with_agent': get_process_with_agent,
        
        # Direct structured_agent_system components
        'structured_AgentType': get_structured_agent_type,
        'structured_AgentSpecialization': get_structured_agent_specialization,
        'structured_AgentCapability': get_structured_agent_capability,
        'structured_AgentBuilder': get_structured_agent_builder,
        'structured_MultiAgentSystem': get_structured_multi_agent_system,
        'structured_process_task': get_structured_process_task,
        
        # Direct Structured_outputs_multi_agent components
        'process_structured_task': get_process_structured_task,
        'handle_data_processing_agent': get_handle_data_processing_agent,
        'handle_analysis_agent': get_handle_analysis_agent,
        'handle_visualization_agent': get_handle_visualization_agent,
        
        # Direct handler_swarm components
        'SwarmHandler': get_swarm_handler_class,
        'SwarmAgent': get_swarm_agent_class,
        'handle_swarm_intent': get_handle_swarm_intent,
    }
    
    # Try to import each component
    for name, getter in component_getters.items():
        try:
            components[name] = getter()
        except ImportError as e:
            logging.warning(f"Could not import {name}: {str(e)}")
            components[name] = None
    
    # Get bulk components (maintain backward compatibility)
    structured_components = get_structured_agent_system()
    for name, component in structured_components.items():
        if f"structured_{name}" not in components:
            components[f"structured_{name}"] = component
    
    soma_components = get_structured_outputs_multi_agent()
    for name, component in soma_components.items():
        if name not in components:
            components[f"soma_{name}"] = component
    
    swarm_components = get_swarm_handler()
    for name, component in swarm_components.items():
        if name not in components:
            components[f"swarm_{name}"] = component
    
    _agent_components_cache = components
    return components 

def _safe_import(module_path, attribute=None, default=None):
    """
    Safely import a module or an attribute from a module with proper error handling.
    
    Args:
        module_path: The path to the module to import
        attribute: Optional attribute to import from the module
        default: Default value to return if import fails
        
    Returns:
        The imported module/attribute or the default value if import fails
    """
    cache_key = f"{module_path}.{attribute}" if attribute else module_path
    
    # Return from cache if available
    if cache_key in _cache:
        return _cache[cache_key]
    
    try:
        module = importlib.import_module(module_path)
        
        if attribute:
            result = getattr(module, attribute)
        else:
            result = module
            
        # Cache the result
        _cache[cache_key] = result
        return result
        
    except (ImportError, AttributeError) as e:
        if 'circular' in str(e).lower():
            logger.warning(f"Circular import detected: {str(e)}")
        else:
            logger.warning(f"Import error for {module_path}.{attribute if attribute else ''}: {str(e)}")
        return default
    except Exception as e:
        logger.error(f"Unexpected error importing {module_path}.{attribute if attribute else ''}: {str(e)}")
        logger.debug(traceback.format_exc())
        return default 

# Note: get_direct_tracking_interface has been removed.
# All modules should use boardroom_connector.py directly for tracking functionality.
# This removes circular dependencies and centralizes BoardRoom access.

# Add direct tracking functions for execute handler
def get_execute_handler_action_async():
    """
    Get the execute_handler_action_async function from jarvis_orchestrator.
    
    Returns:
        The execute_handler_action_async function
    """
    global _execute_handler_action_async_cache

    if _execute_handler_action_async_cache is not None:
        return _execute_handler_action_async_cache

    try:
        # Try direct import first
        from Jarvis_Agent_SDK.jarvis_orchestrator import execute_handler_action_async
        _execute_handler_action_async_cache = execute_handler_action_async
        return execute_handler_action_async
    except (ImportError, AttributeError) as e:
        # Fallback to safe import method
        logging.warning(f"Import error for execute_handler_action_async: {str(e)}")
        
        try:
            # Try dynamic import to avoid circular imports
            jarvis_orchestrator = _safe_import("Jarvis_Agent_SDK.jarvis_orchestrator")
            if hasattr(jarvis_orchestrator, "execute_handler_action_async"):
                execute_handler_action_async = getattr(jarvis_orchestrator, "execute_handler_action_async")
                _execute_handler_action_async_cache = execute_handler_action_async
                return execute_handler_action_async
            else:
                raise ImportError("execute_handler_action_async not found in jarvis_orchestrator")
        except Exception as e:
            logging.warning(f"Failed to import execute_handler_action_async: {str(e)}")
            return None

def get_execute_handler_action():
    """
    Get the execute_handler_action function from jarvis_orchestrator.
    
    Returns:
        The execute_handler_action function
    """
    global _execute_handler_action_cache

    if _execute_handler_action_cache is not None:
        return _execute_handler_action_cache

    try:
        # Try direct import first
        from Jarvis_Agent_SDK.jarvis_orchestrator import execute_handler_action
        _execute_handler_action_cache = execute_handler_action
        return execute_handler_action
    except (ImportError, AttributeError) as e:
        # Fallback to safe import method
        logging.warning(f"Import error for execute_handler_action: {str(e)}")
        
        try:
            # Try dynamic import to avoid circular imports
            jarvis_orchestrator = _safe_import("Jarvis_Agent_SDK.jarvis_orchestrator")
            if hasattr(jarvis_orchestrator, "execute_handler_action"):
                execute_handler_action = getattr(jarvis_orchestrator, "execute_handler_action")
                _execute_handler_action_cache = execute_handler_action
                return execute_handler_action
            else:
                raise ImportError("execute_handler_action not found in jarvis_orchestrator")
        except Exception as e:
            logging.warning(f"Failed to import execute_handler_action: {str(e)}")
            return None 

def get_unified_database(db_path: Optional[str] = None) -> Any:
    """
    Get or create the unified database instance.
    
    Args:
        db_path: Optional database path. If not provided, will use existing connection
                or default to v2/agents.db
        
    Returns:
        SQLiteDatabase instance
    """
    global _unified_database, _database_path, _unified_database_cache
    
    # Check if thread-local storage is enabled in environment
    use_thread_local = os.environ.get('TREVOR_THREAD_SAFE_DB', '1') == '1'
    force_new_db_conn = os.environ.get('FORCE_NEW_DB_CONNECTIONS', '0') == '1'
    
    if use_thread_local:
        # Import thread module at function call time to avoid circular imports
        import threading
        thread_id = threading.get_ident()
        
        # Initialize thread_local if not already done
        if not hasattr(threading, 'thread_local_db'):
            threading.thread_local_db = threading.local()
            
        if not hasattr(threading.thread_local_db, 'connections'):
            threading.thread_local_db.connections = {}
            
        # Use a thread-specific connection if available
        if not force_new_db_conn and db_path and db_path in threading.thread_local_db.connections:
            # Reuse existing thread-local connection
            return threading.thread_local_db.connections[db_path]
            
        # If we don't have a path but have default connection for this thread
        if not db_path and hasattr(threading.thread_local_db, 'default_connection'):
            return threading.thread_local_db.default_connection
    
    # If we're not using thread-local storage or don't have a thread-specific connection
    # First check if we have a cached instance when not forcing new connections
    if not force_new_db_conn and _unified_database_cache is not None:
        return _unified_database_cache
        
    # Then check if we have a standard instance when not forcing new connections
    if not force_new_db_conn and _unified_database is not None:
        _unified_database_cache = _unified_database
        return _unified_database
    
    # If db_path is provided, try to create a new instance
    if db_path:
        try:
            # Try import using importlib to avoid circular imports
            import importlib.util
            spec = importlib.util.find_spec("Jarvis_Agent_SDK.database")
            if spec:
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                
                if hasattr(module, "SQLiteDatabase"):
                    SQLiteDatabase = module.SQLiteDatabase
                    db_instance = SQLiteDatabase(db_path)
                    
                    # Store in thread-local storage if enabled
                    if use_thread_local:
                        import threading
                        threading.thread_local_db.connections[db_path] = db_instance
                        if not hasattr(threading.thread_local_db, 'default_connection'):
                            threading.thread_local_db.default_connection = db_instance
                    else:
                        # Use global variables as fallback
                        _unified_database = db_instance
                        _unified_database_cache = db_instance
                        
                    logger.info(f"Created fallback SQLite connection to {db_path}")
                    return db_instance
            
            # Fallback to direct import if the above fails
            from Jarvis_Agent_SDK.database import SQLiteDatabase
            db_instance = SQLiteDatabase(db_path)
            
            # Store in thread-local storage if enabled
            if use_thread_local:
                import threading
                threading.thread_local_db.connections[db_path] = db_instance
                if not hasattr(threading.thread_local_db, 'default_connection'):
                    threading.thread_local_db.default_connection = db_instance
            else:
                # Use global variables as fallback
                _unified_database = db_instance
                _unified_database_cache = db_instance
                
            logger.info(f"Created fallback SQLite connection to {db_path}")
            return db_instance
            
        except sqlite3.ProgrammingError as e:
            # Handle specific SQLite thread error by creating a new connection
            if "thread" in str(e).lower():
                logger.error(f"Error verifying database connection: {e}")
                
                try:
                    # Retry with a brand new connection
                    from Jarvis_Agent_SDK.database import SQLiteDatabase
                    db_instance = SQLiteDatabase(db_path, create_new_connection=True)
                    
                    # Store in thread-local storage if enabled
                    if use_thread_local:
                        import threading
                        threading.thread_local_db.connections[db_path] = db_instance
                        if not hasattr(threading.thread_local_db, 'default_connection'):
                            threading.thread_local_db.default_connection = db_instance
                            
                    logger.info(f"Created fallback SQLite connection to {db_path}")
                    return db_instance
                except Exception as retry_error:
                    logger.error(f"Error creating fallback database connection: {str(retry_error)}")
                    return None
            else:
                # Re-raise other database errors
                raise
        except Exception as e:
            logger.error(f"Error creating unified database connection: {str(e)}")
            return None
    
    # If we get here and using thread-local storage, try to get default connection
    if use_thread_local:
        import threading
        if hasattr(threading.thread_local_db, 'default_connection'):
            return threading.thread_local_db.default_connection
    
    return _unified_database_cache

# Note: track_journey_step_sync function has been removed
# All modules should use boardroom_connector.py directly for tracking functions 
# This eliminates circular dependencies and centralizes BoardRoom functionality

def reset_workspace_sharing_manager():
    """
    Reset the workspace sharing manager cache.
    This forces a new instance to be created next time get_workspace_sharing is called.
    
    Returns:
        None
    """
    global _workspace_sharing_manager
    _workspace_sharing_manager = None
    logging.info("Workspace sharing manager cache has been reset")

def get_workspace_sharing(workspace_manager=None, force_reload=False):
    """
    Get or create a WorkspaceSharingManager instance.
    
    Args:
        workspace_manager: Optional workspace manager to use
        force_reload: If True, forces a new instance to be created
        
    Returns:
        WorkspaceSharingManager instance or None if not available
    """
    global _workspace_sharing_manager
    
    # If force_reload is True, reset the cached instance
    if force_reload:
        reset_workspace_sharing_manager()
    
    # If already initialized, return it
    if _workspace_sharing_manager is not None:
        return _workspace_sharing_manager
    
    # Try to create a new instance
    try:
        # NOTE: WorkspaceSharing is the subclass that has all the real methods
        # (create_workspace, assign_agent_to_workspace, _get_db_connection, etc.)
        # WorkspaceSharingManager is the base with only BaseHandler methods.
        from Database.workspace_sharing import WorkspaceSharing
        _workspace_sharing_manager = WorkspaceSharing(workspace_manager)
        
        # Note: BoardRoom connection should be done directly using boardroom_connector
        # For legacy support, application code should call:
        # workspace_manager.set_boardroom(boardroom_connector.get_boardroom())
        
        return _workspace_sharing_manager
    except ImportError:
        logging.warning("Could not import WorkspaceSharingManager - continuing without it")
    except Exception as e:
        logging.error(f"Error initializing workspace sharing manager: {str(e)}")
    
    return None

def get_handler_system():
    """
    Get the handler system for use across components.
    
    Returns:
        Handler system or None if not available
    """
    global _handler_system
    
    # If already initialized, return it
    if _handler_system is not None:
        return _handler_system
    
    # Try to import and access
    try:
        from Core.handler_system import handler_system
        _handler_system = handler_system
        return _handler_system
    except ImportError:
        logging.warning("Could not import handler_system - continuing without it")
    except Exception as e:
        logging.warning(f"Error accessing handler_system: {str(e)}")
    
    return None

def get_agent_loader():
    """
    Get the agent loader for use across components.
    
    Returns:
        Agent loader or None if not available
    """
    global _agent_loader
    
    # If already initialized, return it
    if _agent_loader is not None:
        return _agent_loader
    
    # Try to import and access
    try:
        from Core.agent_loader import agent_loader
        _agent_loader = agent_loader
        return _agent_loader
    except ImportError:
        logging.warning("Could not import agent_loader - continuing without it")
    except Exception as e:
        logging.warning(f"Error accessing agent_loader: {str(e)}")
    
    return None

# Note: All BoardRoom-related functions have been removed.
# Modules should use boardroom_connector.py directly for these functions:
# - task_success
# - task_error
# - system_status
# - system_error
# 
# This eliminates circular dependencies and centralizes BoardRoom functionality.

# Note: All BoardRoom-related tracking functions have been removed.
# Modules should use boardroom_connector.py directly for these functions:
# - track_request_journey
# - track_journey_step (async and sync versions)
# 
# This eliminates circular dependencies and centralizes BoardRoom functionality.

def generate_request_id(task=None):
    """
    Generate a unique request ID
    
    Args:
        task: Optional task data (ignored in this implementation)
        
    Returns:
        A unique request ID string
    """
    import uuid
    return str(uuid.uuid4())

def generate_simple_id():
    """Generate a simple, shorter unique ID"""
    import random
    import string
    import time
    
    # Get current timestamp for uniqueness
    timestamp = int(time.time() * 1000)
    
    # Generate 4 random characters
    random_part = ''.join(random.choices(string.ascii_lowercase + string.digits, k=4))
    
    # Combine for a compact but unique ID
    return f"{timestamp:x}-{random_part}"

# Note: All BoardRoom-related logging and tracking functions have been removed.
# Modules should use boardroom_connector.py directly for:
# - log_agent_activity
# - track_agent_performance
# - update_journey_state
#
# This eliminates circular dependencies and centralizes BoardRoom functionality. 