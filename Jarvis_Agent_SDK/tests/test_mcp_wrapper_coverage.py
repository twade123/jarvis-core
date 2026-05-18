#!/usr/bin/env python3
"""
Unit Tests for MCP Wrapper Coverage

This module contains tests to ensure that all relevant handlers in the Handler
directory have corresponding MCP wrappers. These tests verify:

1. All handler files (handler_*.py) have corresponding wrapper files
2. All wrappers properly extend or wrap the original handler classes
3. Excluded handlers (like placeholders) are properly skipped
4. Handler registry includes all wrapped handler classes
"""

import os
import sys
import unittest
import importlib
import importlib.util
import inspect
import glob
from typing import Dict, List, Any, Type

# Add the parent directory to the path so we can import our modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import MCP decorators and wrapper utilities
from Jarvis_Agent_SDK.mcp_decorators import is_mcp_exposed, get_mcp_methods
from Jarvis_Agent_SDK.mcp_wrapper import create_handler_wrapper


class TestMCPWrapperCoverage(unittest.TestCase):
    """Test case for MCP wrapper coverage."""
    
    def setUp(self):
        """Set up test environment."""
        # Path to Handler directory
        self.handler_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../Handler'))
        # Path to MCP wrappers directory
        self.wrapper_dir = os.path.abspath(os.path.join(self.handler_dir, 'mcp_wrappers'))
        
        # Handlers to exclude (placeholders, deprecated, etc.)
        self.excluded_handlers = [
            "handler_handler_creative.py",  # Placeholder
            "handler_handler_travel.py",    # Placeholder
            "handler_coding.py",           # Deprecated
            "handler_code_execution_utils.py", # Deprecated
            "handler_base.py",              # Base class, not a handler
            "handler_template.py",          # Template, not a handler
            "__init__.py",                  # Not a handler
            "handler_analyzer.py",          # Analyzer, not a handler
            "handler_analyzer2.py",         # Analyzer, not a handler
            "handler_analyzer_database.py", # Analyzer, not a handler
            "handler_data_validator.py",    # Should have a wrapper but lives elsewhere
            "handler_all.py",               # Composite handler, not directly wrapped
            "pattern_intent_mapper.py",     # Utility, not a handler
            "cache.py",                     # Utility, not a handler
            "intents.py",                   # Utility, not a handler
            "structured_agent_system.py",   # Multi-agent system, wrapped separately
            "Structured_outputs_multi_agent.py", # Multi-agent system, wrapped separately
            "database_utils.py",            # Utility, not a handler
            "endpoint_discovery.py",        # Utility, not a handler
            "execute_email_task.py",        # Utility function, not a handler
            "code_execution_utils.py",      # Utility, not a handler
            "check_agent_s_env.py",         # Utility, not a handler
            "check_agent_s_imports.py",     # Utility, not a handler
            "terminal_schema_definitions.py", # Schema definitions, not a handler
            "terminal_test.py",             # Test file, not a handler
            "revert_changes.patch",         # Patch file, not a handler
            "run_agent_s_cli_test.py",      # Test file, not a handler
            "verify_agent_s_impl.py",       # Verification script, not a handler
            "articles.json",                # Data file, not a handler
            "finder_capabilities.json",     # Data file, not a handler
            "intent_data.db",               # Database file, not a handler
            "last_handler_maintenance.txt", # Text file, not a handler
            "last_maintenance.txt",         # Text file, not a handler
            "model_trainer_debug.log",      # Log file, not a handler
            "patterns.db",                  # Database file, not a handler
            "weather_data.json",            # Data file, not a handler
            "error.log",                    # Log file, not a handler
            "info.log"                      # Log file, not a handler
        ]
        
        # Test files are excluded
        self.excluded_handlers.extend([f for f in os.listdir(self.handler_dir) if f.startswith('test_')])
        
    def test_all_handlers_have_wrappers(self):
        """Test that all handler files have corresponding wrapper files."""
        # Get all handler files
        handler_files = [f for f in os.listdir(self.handler_dir) 
                        if f.startswith('handler_') and f.endswith('.py') 
                        and f not in self.excluded_handlers]
        
        # Get all wrapper files
        wrapper_files = [f for f in os.listdir(self.wrapper_dir) 
                        if f.endswith('_wrapper.py')]
        
        # Check each handler has a wrapper
        missing_wrappers = []
        for handler_file in handler_files:
            # Convert handler_name.py to name_wrapper.py
            handler_name = handler_file.replace('handler_', '').replace('.py', '')
            expected_wrapper = f"{handler_name}_wrapper.py"
            
            if expected_wrapper not in wrapper_files:
                missing_wrappers.append(handler_file)
        
        # Check that there are no missing wrappers
        self.assertEqual(
            len(missing_wrappers),
            0,
            f"The following handlers are missing wrappers: {missing_wrappers}"
        )
    
    def test_wrappers_import_original_handlers(self):
        """Test that wrapper files import their corresponding original handlers."""
        # Get all wrapper files
        wrapper_files = [f for f in os.listdir(self.wrapper_dir) 
                        if f.endswith('_wrapper.py')]
        
        for wrapper_file in wrapper_files:
            # Read the wrapper file to check import statements
            with open(os.path.join(self.wrapper_dir, wrapper_file), 'r') as f:
                content = f.read()
            
            # Convert name_wrapper.py to handler_name.py
            handler_name = wrapper_file.replace('_wrapper.py', '')
            expected_import = f"from Handler.handler_{handler_name}"
            
            # Check that the import statement exists
            self.assertIn(
                expected_import,
                content,
                f"Wrapper {wrapper_file} does not import the original handler"
            )
    
    def test_wrapper_classes_extend_original_handlers(self):
        """Test that wrapper classes extend or wrap original handler classes."""
        # Get all wrapper files (excluding __init__.py)
        wrapper_files = [f for f in os.listdir(self.wrapper_dir) 
                        if f.endswith('_wrapper.py') and f != '__init__.py']
        
        for wrapper_file in wrapper_files:
            try:
                # Convert file name to module name
                module_name = wrapper_file.replace('.py', '')
                
                # Import the module
                spec = importlib.util.spec_from_file_location(
                    module_name, 
                    os.path.join(self.wrapper_dir, wrapper_file)
                )
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                
                # Find the wrapper class (should be named XxxHandler)
                wrapper_class = None
                for name, obj in inspect.getmembers(module):
                    if inspect.isclass(obj) and name.endswith('Handler'):
                        wrapper_class = obj
                        break
                
                # If no wrapper class was found, fail the test
                if wrapper_class is None:
                    self.fail(f"No handler class found in {wrapper_file}")
                
                # Check that the wrapper class has at least one MCP-exposed method
                instance = wrapper_class()
                mcp_methods = get_mcp_methods(instance)
                
                self.assertGreater(
                    len(mcp_methods),
                    0,
                    f"Wrapper class in {wrapper_file} has no MCP-exposed methods"
                )
                
                # Check that it has an execute method
                self.assertTrue(
                    hasattr(instance, 'execute'),
                    f"Wrapper class in {wrapper_file} does not have an execute method"
                )
                
                # Check that execute method is MCP-exposed
                execute_method = getattr(instance, 'execute')
                self.assertTrue(
                    is_mcp_exposed(execute_method),
                    f"Execute method in {wrapper_file} is not MCP-exposed"
                )
                
            except (ImportError, AttributeError) as e:
                self.fail(f"Error importing wrapper {wrapper_file}: {e}")
    
    def test_handler_registry_includes_all_wrappers(self):
        """Test that the handler registry includes all wrapper classes."""
        # Import the handler registry
        try:
            from Handler.mcp_wrappers import WRAPPER_MAP
            
            # Get all wrapper files (excluding __init__.py)
            wrapper_files = [f for f in os.listdir(self.wrapper_dir) 
                           if f.endswith('_wrapper.py') and f != '__init__.py']
            
            # Check that each wrapper is in the registry
            for wrapper_file in wrapper_files:
                # Import the module to get the class name
                module_name = wrapper_file.replace('.py', '')
                spec = importlib.util.spec_from_file_location(
                    module_name, 
                    os.path.join(self.wrapper_dir, wrapper_file)
                )
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                
                # Find the wrapper class
                wrapper_class = None
                for name, obj in inspect.getmembers(module):
                    if inspect.isclass(obj) and name.endswith('Handler'):
                        wrapper_class = obj
                        break
                
                if wrapper_class is None:
                    self.fail(f"No handler class found in {wrapper_file}")
                
                # Check that the class name is in the registry values
                registry_contains_class = False
                for registry_key, registry_class in WRAPPER_MAP.items():
                    if registry_class.__name__ == wrapper_class.__name__:
                        registry_contains_class = True
                        break
                
                self.assertTrue(
                    registry_contains_class,
                    f"Wrapper class {wrapper_class.__name__} from {wrapper_file} is missing from the registry"
                )
                
        except ImportError:
            self.fail("Could not import the WRAPPER_MAP from Handler.mcp_wrappers")


if __name__ == '__main__':
    unittest.main()