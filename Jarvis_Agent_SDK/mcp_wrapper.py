#!/usr/bin/env python3
"""
MCP Wrapper Module

This module provides direct handler access for OpenAI agents in workspaces.
Unlike mcp_server_launcher.py which manages MCP server processes, this wrapper
provides direct handler instance access for method calls within workspace sharing.

Purpose:
    - Bridge between MCP server system and direct handler access
    - Enable OpenAI agents to call handler methods directly
    - Provide same capabilities to OpenAI agents that Claude has via self.active_mcp_servers
    
Usage:
    from Jarvis_Agent_SDK.mcp_wrapper import get_handler_wrapper
    handler_wrapper = get_handler_wrapper("terminal")
    result = handler_wrapper.execute_command(cmd="echo 'test'")
"""

import os
import sys
import logging
import importlib
import inspect
from typing import Dict, Any, Optional, Union, Callable, List

# Add Jarvis root to path for handler imports
sys.path.insert(0, '~/Jarvis')

# Configure logging
logger = logging.getLogger(__name__)

# Handler wrapper cache to avoid repeated imports
_wrapper_cache: Dict[str, Any] = {}

# Handler registry mapping handler names to their module paths and classes
# This mirrors the HANDLER_REGISTRY from mcp_server_launcher but for direct access
HANDLER_WRAPPER_REGISTRY = {
    # Core handlers
    "email": ("Handler.handler_email", "HandlerEmail"),
    "calendar": ("Handler.handler_calendar", "HandlerCalendar"),
    "finder": ("Handler.handler_finder", "HandlerFinder"),
    "weather": ("Handler.handler_weather", "weather"),  # Function-based
    "news": ("Handler.handler_news_info", "NewsMCPHandler"),  # Class wrapper for MCP layer
    "wolfram": ("Handler.handler_wolfram", "WolframHandler"),
    "terminal": ("Handler.handler_terminal", "TerminalHandler"),
    "spreadsheet": ("Handler.handler_spreadsheet", "handle_spreadsheet_intent"),  # Function-based
    "document": ("Handler.handler_document_creation", "handle_document_creation_intent"),  # Function-based
    "browser": ("Handler.handler_browser", "handle_browser_intent"),  # Function-based
    "file_sharing": ("Handler.handler_file_sharing", "handle_file_sharing_intent"),  # Function-based
    "tv_movies": ("Handler.handler_tv_movies", "handle_tmdb_intent"),  # Function-based
    "<healthcare>_sdk2": ("Handler.handler_<healthcare>_sdk2", "<healthcare-platform>SDKHandler"),
    "data_validator": ("Handler.handler_data_validator", "DataValidatorHandler"),
    "oanda": ("Handler.handler_oanda", "OandaHandler"),
    "prompt_registry": ("Handler.handler_prompt_registry", "PromptRegistryHandler"),
    
    # AI & Agent Systems  
    "swarm": ("Handler.handler_swarm", "SwarmHandler"),
    "agent_builder": ("Handler.handler_agent_builder", "AgentBuilderHandler"),
    "agent_s_handler": ("Handler.handler_agent_s", "AgentSHandler"),
    "agent_registry": ("Handler.handler_agent_registry", "AgentRegistryHandler"),
    "structured_agent": ("structured_agent_system", "MultiAgentSystem"),
    "multi_agent": ("Structured_outputs_multi_agent", "route_to_appropriate_system_tool"),  # Function-based
    
    # Workspace and database systems
    "workspace": ("Database.workspace_sharing", "WorkspaceSharing"),
    "task_comments": ("Database.workspace_task_comments", "WorkspaceTaskCommentManager"),
}

# Standalone MCP Server Registry - these run as separate processes
# We can't directly import them, but we can provide access via process spawning
STANDALONE_MCP_REGISTRY = {
    "canva_mcp": {
        "description": "Canva design automation MCP server with OAuth integration",
        "tools": ["create_design", "search_templates", "export_design", "upload_asset", "add_text_element"]
    },
    "google_workspace": {
        "description": "Google Workspace MCP server with OAuth integration for Gmail, Drive, Calendar, Docs, Sheets, Chat, Forms, Slides",
        "tools": ["start_google_auth", "gmail_send_message", "gmail_search_messages", "drive_list_files", "calendar_create_event"]
    },
    "microsoft_365": {
        "description": "Official Microsoft 365 Agents Toolkit MCP server with Teams, Outlook, OneDrive, Office apps integration",
        "tools": ["create_teams_app", "build_copilot_agent", "manage_adaptive_cards", "access_graph_api"]
    },
    "gohighlevel": {
        "description": "GoHighLevel MCP server - comprehensive CRM platform with 200+ tools across 20 categories",
        "tools": ["contact_management", "messaging_conversations", "opportunity_management", "calendar_appointments"]
    },
    "video_editing_mcp": {
        "description": "Professional video editing MCP server with VideoJungle integration",
        "tools": ["add_video", "search_local_videos", "generate_edit_from_videos", "create_videojungle_project"]
    },
    "video_digest_mcp": {
        "description": "Video transcription and content analysis MCP server",
        "tools": ["get_video_content"]
    },
    "meta_business_sdk": {
        "description": "Official Meta Business SDK MCP server - comprehensive Facebook/Instagram advertising platform with 18 tools",
        "tools": ["get_campaigns", "create_campaign", "get_adsets", "create_ad", "get_ad_insights"]
    },
    "github_mcp": {
        "description": "Official GitHub MCP server with OAuth and Personal Access Token authentication",
        "tools": ["repository_management", "issues_discussions", "actions_workflows", "code_security"]
    },
    "railway_mcp": {
        "description": "Official Railway MCP server - comprehensive Railway.app infrastructure management",
        "tools": ["project_management", "service_deployment", "environment_management", "log_retrieval"]
    },
    "aws_cloud_control": {
        "description": "Official AWS Cloud Control API MCP server - comprehensive AWS infrastructure management with 1,100+ resources",
        "tools": ["ec2_management", "database_services", "container_orchestration", "storage_services"]
    }
}


class StandaloneMCPWrapper:
    """
    Wrapper for standalone MCP servers that run as separate processes.
    
    This provides a consistent interface for OpenAI agents to interact with
    standalone MCP servers, even though they can't be directly imported.
    """
    
    def __init__(self, mcp_name: str, mcp_info: Dict[str, Any]):
        self.mcp_name = mcp_name
        self.mcp_info = mcp_info
        self.description = mcp_info.get("description", "No description available")
        self.tools = mcp_info.get("tools", [])
        
        logger.debug(f"Created StandaloneMCPWrapper for {mcp_name}")
    
    def get_description(self) -> str:
        """Get description of this MCP server."""
        return self.description
    
    def list_tools(self) -> List[str]:
        """List available tools for this MCP server."""
        return self.tools.copy()
    
    def execute(self, action: str, parameters: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Execute a tool on this standalone MCP server.
        
        Note: This returns information about the MCP rather than actually executing it,
        since standalone MCPs need to be launched as separate processes.
        """
        parameters = parameters or {}
        
        return {
            "status": "info",
            "message": f"Standalone MCP server '{self.mcp_name}' requires process spawning",
            "mcp_name": self.mcp_name,
            "description": self.description,
            "available_tools": self.tools,
            "action_requested": action,
            "parameters": parameters,
            "note": "Use MCP server launcher to start this server as a separate process"
        }
    
    def __getattr__(self, method_name: str):
        """Route any method calls to the execute method."""
        def method_wrapper(*args, **kwargs):
            return self.execute(method_name, kwargs)
        return method_wrapper


class HandlerWrapper:
    """
    Wrapper class that provides a unified interface for both class-based and function-based handlers.
    
    This allows OpenAI agents to call handler methods consistently regardless of the underlying
    implementation type.
    """
    
    def __init__(self, handler_name: str, handler_instance: Union[object, Callable]):
        self.handler_name = handler_name
        self.handler_instance = handler_instance
        self.is_function_based = callable(handler_instance) and not hasattr(handler_instance, '__dict__')
        
        logger.debug(f"Created HandlerWrapper for {handler_name}, function_based={self.is_function_based}")
    
    def __getattr__(self, method_name: str):
        """
        Dynamically route method calls to the underlying handler instance.
        
        Args:
            method_name: Name of the method to call
            
        Returns:
            Callable method or attribute from the handler instance
        """
        if self.is_function_based:
            # For function-based handlers, the instance IS the callable function
            if method_name == 'execute' or method_name == self.handler_name:
                return self.handler_instance
            else:
                raise AttributeError(f"Function-based handler {self.handler_name} does not have method {method_name}")
        else:
            # For class-based handlers, delegate to the instance
            if hasattr(self.handler_instance, method_name):
                return getattr(self.handler_instance, method_name)
            else:
                raise AttributeError(f"Handler {self.handler_name} does not have method {method_name}")
    
    def execute(self, action: str, parameters: Dict[str, Any] = None):
        """
        Generic execute method for consistency with MCP interface.
        
        Args:
            action: Action to perform
            parameters: Parameters for the action
            
        Returns:
            Result of the action execution
        """
        parameters = parameters or {}
        
        if self.is_function_based:
            # For function-based handlers, call directly
            try:
                # Try to call with parameters
                if parameters:
                    return self.handler_instance(**parameters)
                else:
                    return self.handler_instance()
            except TypeError as e:
                logger.warning(f"Function call failed for {self.handler_name}: {e}")
                return {"error": f"Invalid parameters for {self.handler_name}: {e}"}
        else:
            # For class-based handlers, try to find the appropriate method
            if hasattr(self.handler_instance, action):
                method = getattr(self.handler_instance, action)
                try:
                    if parameters:
                        return method(**parameters)
                    else:
                        return method()
                except TypeError as e:
                    logger.warning(f"Method call failed for {self.handler_name}.{action}: {e}")
                    return {"error": f"Invalid parameters for {self.handler_name}.{action}: {e}"}
            else:
                return {"error": f"Method {action} not found in handler {self.handler_name}"}


def get_handler_wrapper(handler_name: str) -> Optional[Union[HandlerWrapper, StandaloneMCPWrapper]]:
    """
    Get a handler wrapper instance for direct method calls.
    
    This function provides OpenAI agents with direct access to handler functionality,
    similar to how Claude accesses handlers through self.active_mcp_servers.
    
    Supports both:
    - Handler-based MCPs (can be directly imported and instantiated)
    - Standalone MCPs (run as separate processes)
    
    Args:
        handler_name: Name of the handler/MCP to get wrapper for
        
    Returns:
        HandlerWrapper or StandaloneMCPWrapper instance, or None if not found
        
    Example:
        # For handlers:
        wrapper = get_handler_wrapper("terminal")
        result = wrapper.execute_command(cmd="ls -la")
        
        # For standalone MCPs:
        wrapper = get_handler_wrapper("canva_mcp")
        result = wrapper.execute("create_design", {"template": "business_card"})
    """
    # Check cache first
    if handler_name in _wrapper_cache:
        return _wrapper_cache[handler_name]
    
    # Check if it's a standalone MCP first
    if handler_name in STANDALONE_MCP_REGISTRY:
        mcp_info = STANDALONE_MCP_REGISTRY[handler_name]
        wrapper = StandaloneMCPWrapper(handler_name, mcp_info)
        
        # Cache the wrapper
        _wrapper_cache[handler_name] = wrapper
        
        logger.info(f"Successfully created standalone MCP wrapper for {handler_name}")
        return wrapper
    
    # Check if handler is in registry
    if handler_name not in HANDLER_WRAPPER_REGISTRY:
        logger.warning(f"Handler/MCP {handler_name} not found in wrapper registry")
        return None
    
    module_path, class_or_function_name = HANDLER_WRAPPER_REGISTRY[handler_name]
    
    try:
        # Import the module
        module = importlib.import_module(module_path)
        logger.debug(f"Successfully imported module {module_path}")
        
        # Get the class or function
        handler_obj = getattr(module, class_or_function_name)
        
        # Determine if this is a class or function
        if inspect.isclass(handler_obj):
            # Instantiate the class
            try:
                handler_instance = handler_obj()
                logger.debug(f"Successfully instantiated class {class_or_function_name}")
            except Exception as e:
                logger.error(f"Failed to instantiate {class_or_function_name}: {e}")
                return None
        elif inspect.isfunction(handler_obj):
            # Use the function directly
            handler_instance = handler_obj
            logger.debug(f"Using function {class_or_function_name} directly")
        else:
            logger.error(f"{class_or_function_name} is neither a class nor a function")
            return None
        
        # Create wrapper
        wrapper = HandlerWrapper(handler_name, handler_instance)
        
        # Cache the wrapper
        _wrapper_cache[handler_name] = wrapper
        
        logger.info(f"Successfully created handler wrapper for {handler_name}")
        return wrapper
        
    except ImportError as e:
        logger.error(f"Failed to import {module_path}: {e}")
        return None
    except AttributeError as e:
        logger.error(f"Failed to get {class_or_function_name} from {module_path}: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error creating wrapper for {handler_name}: {e}")
        return None


def list_available_handlers() -> Dict[str, Dict[str, str]]:
    """
    List all available handlers and standalone MCPs in the wrapper registry.
    
    Returns:
        Dictionary mapping MCP names to their information
    """
    result = {}
    
    # Add handlers
    for handler_name, (module_path, class_name) in HANDLER_WRAPPER_REGISTRY.items():
        result[handler_name] = {
            "type": "handler",
            "module": module_path,
            "class_or_function": class_name,
            "cached": handler_name in _wrapper_cache
        }
    
    # Add standalone MCPs
    for mcp_name, mcp_info in STANDALONE_MCP_REGISTRY.items():
        result[mcp_name] = {
            "type": "standalone_mcp",
            "description": mcp_info["description"],
            "tools_count": len(mcp_info["tools"]),
            "cached": mcp_name in _wrapper_cache
        }
    
    return result


def clear_wrapper_cache():
    """Clear the handler wrapper cache."""
    global _wrapper_cache
    _wrapper_cache.clear()
    logger.info("Handler wrapper cache cleared")


def test_handler_wrapper(handler_name: str) -> Dict[str, Any]:
    """
    Test a handler wrapper to verify it works correctly.
    
    Args:
        handler_name: Name of the handler to test
        
    Returns:
        Dictionary containing test results
    """
    test_results = {
        "handler_name": handler_name,
        "success": False,
        "wrapper_created": False,
        "methods_found": [],
        "test_execution": None,
        "errors": []
    }
    
    try:
        # Try to get the wrapper
        wrapper = get_handler_wrapper(handler_name)
        
        if not wrapper:
            test_results["errors"].append("Failed to create wrapper")
            return test_results
        
        test_results["wrapper_created"] = True
        
        # Try to find available methods
        if wrapper.is_function_based:
            test_results["methods_found"] = ["execute", handler_name]
        else:
            # Get methods from the handler instance
            methods = [method for method in dir(wrapper.handler_instance) 
                      if not method.startswith('_') and callable(getattr(wrapper.handler_instance, method))]
            test_results["methods_found"] = methods
        
        # Try a simple test execution
        try:
            if hasattr(wrapper, 'execute'):
                result = wrapper.execute("test", {})
                test_results["test_execution"] = str(result)
            else:
                test_results["test_execution"] = "No execute method available"
        except Exception as e:
            test_results["test_execution"] = f"Test execution failed: {e}"
        
        test_results["success"] = True
        
    except Exception as e:
        test_results["errors"].append(str(e))
    
    return test_results


if __name__ == "__main__":
    # Basic testing when run directly
    logging.basicConfig(level=logging.DEBUG)
    
    print("MCP Wrapper Module Test")
    print("=" * 50)
    
    # List available handlers
    print("\nAvailable MCPs:")
    mcps = list_available_handlers()
    
    handlers = {k: v for k, v in mcps.items() if v.get('type') == 'handler'}
    standalone_mcps = {k: v for k, v in mcps.items() if v.get('type') == 'standalone_mcp'}
    
    print(f"\nHandlers ({len(handlers)}):")
    for name, info in handlers.items():
        print(f"  {name}: {info['module']}.{info['class_or_function']}")
    
    print(f"\nStandalone MCPs ({len(standalone_mcps)}):")
    for name, info in standalone_mcps.items():
        print(f"  {name}: {info['description'][:60]}... ({info['tools_count']} tools)")
    
    print(f"\nTotal MCPs: {len(mcps)} (matching MCP server launcher)")
    
    # Test a few handlers
    test_handlers = ["terminal", "weather", "canva_mcp"]
    
    for handler_name in test_handlers:
        if handler_name in mcps:
            print(f"\nTesting {handler_name} ({mcps[handler_name]['type']}):")
            results = test_handler_wrapper(handler_name)
            print(f"  Success: {results['success']}")
            print(f"  Wrapper Created: {results['wrapper_created']}")
            print(f"  Methods Found: {results['methods_found']}")
            if results['errors']:
                print(f"  Errors: {results['errors']}")
        else:
            print(f"\nSkipping {handler_name}: not in registry")