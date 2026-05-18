"""
Common Utilities for Jarvis Agent SDK

This module provides common utility functions used across multiple modules
to prevent circular imports.
"""

import time
import hashlib
import logging
import importlib
import inspect
import os
import ast
import sys
import json
import asyncio
from typing import Dict, Any, Union, Optional, List

# Import base classes directly to avoid circular dependencies
try:
    from .base import (
        MultiAgentSystemBase, 
        generate_request_id, 
        generate_simple_id
    )
except ImportError:
    # Fallback for direct execution
    from base import (
        MultiAgentSystemBase, 
        generate_request_id, 
        generate_simple_id
    )

# Note: BoardRoom-related functions have been removed
# All modules should use boardroom_connector.py directly for BoardRoom functionality
# This eliminates circular dependencies and centralizes BoardRoom access

def analyze_handler_capabilities(handler_name):
    """
    Analyze a handler file to extract its capabilities, methods, and documentation.
    
    Args:
        handler_name: Name of the handler to analyze
        
    Returns:
        Dictionary containing handler capabilities information
    """
    
    handler_capabilities = {
        "methods": {},
        "description": "",
        "examples": [],
        "parameters": {},
        "return_values": {},
        "special_notes": [],
    }
    
    try:
        # Try to find the handler module path
        possible_handler_paths = [
            f"Handler.handler_{handler_name}",
            f"Handler.{handler_name}"
        ]
        
        handler_module = None
        module_path = None
        
        for path in possible_handler_paths:
            try:
                handler_module = importlib.import_module(path)
                module_path = path
                break
            except ImportError:
                continue
        
        if not handler_module:
            logging.warning(f"Could not find handler module for {handler_name}")
            return handler_capabilities
            
        # First extract module-level docstring for description
        if handler_module.__doc__:
            handler_capabilities["description"] = handler_module.__doc__.strip()
            
        # Find handler class and its methods
        handler_class = None
        for name, obj in inspect.getmembers(handler_module):
            if inspect.isclass(obj) and name.lower().endswith(handler_name.lower()) or name.lower() == handler_name.lower():
                handler_class = obj
                break
        
        # If we found a handler class, extract its methods and docstrings
        if handler_class:
            if handler_class.__doc__:
                handler_capabilities["description"] = handler_class.__doc__.strip()
                
            for method_name, method in inspect.getmembers(handler_class, inspect.isfunction):
                if not method_name.startswith("_"):  # Skip private methods
                    method_info = {
                        "description": "",
                        "parameters": {},
                        "returns": "",
                        "examples": []
                    }
                    
                    if method.__doc__:
                        method_info["description"] = method.__doc__.strip()
                        
                    # Get parameter info
                    signature = inspect.signature(method)
                    for param_name, param in signature.parameters.items():
                        if param_name != "self":
                            method_info["parameters"][param_name] = {
                                "type": str(param.annotation) if param.annotation is not inspect.Parameter.empty else "any",
                                "default": str(param.default) if param.default is not inspect.Parameter.empty else None
                            }
                    
                    handler_capabilities["methods"][method_name] = method_info
        
        # Also look for module-level functions
        for name, obj in inspect.getmembers(handler_module):
            if inspect.isfunction(obj) and not name.startswith("_"):
                method_info = {
                    "description": "",
                    "parameters": {},
                    "returns": "",
                    "examples": []
                }
                
                if obj.__doc__:
                    method_info["description"] = obj.__doc__.strip()
                    
                # Get parameter info
                signature = inspect.signature(obj)
                for param_name, param in signature.parameters.items():
                    method_info["parameters"][param_name] = {
                        "type": str(param.annotation) if param.annotation is not inspect.Parameter.empty else "any",
                        "default": str(param.default) if param.default is not inspect.Parameter.empty else None
                    }
                
                handler_capabilities["methods"][name] = method_info
        
        return handler_capabilities
            
    except Exception as e:
        logging.error(f"Error analyzing handler capabilities: {str(e)}")
        return handler_capabilities

# Note: register_system_in_boardroom function has been removed
# All modules should use boardroom_connector.py directly for BoardRoom functionality
# For system registration, use boardroom_connector.get_boardroom() and then use the
# appropriate methods on the BoardRoom instance

def analyze_task_capabilities(task_data):
    """
    Analyze task data to identify required agent capabilities.
    
    This function analyzes the task structure, content, and metadata to determine
    what agent capabilities would be best suited for handling the task.
    
    Args:
        task_data: Dictionary containing task information
        
    Returns:
        List of required capabilities (strings matching AgentCapability enum values)
    """
    required_capabilities = []
    
    # Analyze explicit requirements if specified
    if isinstance(task_data, dict) and "required_capabilities" in task_data:
        return task_data["required_capabilities"]
    
    # Analyze based on task structure and content
    if isinstance(task_data, dict):
        # Check for data analysis tasks
        if any(key in task_data for key in ["data", "dataset", "analysis", "analytics", "metrics"]):
            required_capabilities.append("ANALYTICAL")
            required_capabilities.append("DATA_ANALYSIS")
            
        # Check for visualization tasks
        if any(key in task_data for key in ["chart", "graph", "visualization", "plot", "display"]):
            required_capabilities.append("DATA_VISUALIZATION")
            
        # Check for statistical analysis
        if any(key in task_data for key in ["statistics", "correlation", "regression", "model"]):
            required_capabilities.append("STATISTICAL_ANALYSIS")
            
        # Check for code tasks
        if any(key in task_data for key in ["code", "function", "script", "program"]):
            required_capabilities.append("TECHNICAL")
            
        # Check for coordination tasks
        if any(key in task_data for key in ["orchestrate", "coordinate", "manage", "delegate"]):
            required_capabilities.append("MANAGEMENT")
            
        # Check for communication tasks
        if any(key in task_data for key in ["report", "explain", "summarize", "document"]):
            required_capabilities.append("COMMUNICATION")
            
        # Check for creative tasks
        if any(key in task_data for key in ["design", "create", "innovative", "novel"]):
            required_capabilities.append("CREATIVE")
    
    # If analyzing a simple string, check keywords
    elif isinstance(task_data, str):
        task_lower = task_data.lower()
        
        # Data analysis keywords
        if any(keyword in task_lower for keyword in ["analyze", "data", "dataset", "extract", "insights"]):
            required_capabilities.append("ANALYTICAL")
            required_capabilities.append("DATA_ANALYSIS")
            
        # Visualization keywords
        if any(keyword in task_lower for keyword in ["visualize", "chart", "graph", "plot", "display"]):
            required_capabilities.append("DATA_VISUALIZATION")
            
        # Statistical keywords
        if any(keyword in task_lower for keyword in ["statistics", "correlation", "predict", "model"]):
            required_capabilities.append("STATISTICAL_ANALYSIS")
            
        # Technical keywords
        if any(keyword in task_lower for keyword in ["code", "program", "script", "function", "develop"]):
            required_capabilities.append("TECHNICAL")
            
        # Management keywords
        if any(keyword in task_lower for keyword in ["manage", "coordinate", "organize", "delegate"]):
            required_capabilities.append("MANAGEMENT")
            
        # Communication keywords
        if any(keyword in task_lower for keyword in ["explain", "report", "document", "summarize"]):
            required_capabilities.append("COMMUNICATION")
            
        # Creative keywords
        if any(keyword in task_lower for keyword in ["design", "create", "innovation", "novel"]):
            required_capabilities.append("CREATIVE")
    
    # Ensure unique capabilities
    return list(set(required_capabilities)) 