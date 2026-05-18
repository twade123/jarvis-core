#!/usr/bin/env python3
"""
Unit Tests for MCP Method Discovery

This module contains tests to ensure that all handler methods are properly
exposed via the Model Context Protocol (MCP). These tests verify:

1. All handler wrappers have the expected methods with MCP decorators
2. Method descriptions and parameter metadata are correctly set
3. Both standard and async methods are properly decorated
4. Public and private methods are handled appropriately
5. All required methods are exposed while internal methods remain hidden
"""

import os
import sys
import unittest
import inspect
import importlib.util
from typing import Dict, List, Any, Callable, Type

# Add the parent directory to the path so we can import our modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import MCP decorators for testing
from Jarvis_Agent_SDK.mcp_decorators import is_mcp_exposed, get_mcp_methods
from Jarvis_Agent_SDK.mcp_wrapper import create_handler_wrapper, wrap_function

# Import handler wrappers (adjust imports as needed)
from Handler.mcp_wrappers import (
    EmailHandler, 
    GHLHandler, 
    CalendarHandler, 
    FinderHandler,
    WeatherHandler,
    NewsInfoHandler,
    WolframHandler,
    TerminalHandler,
    SpreadsheetHandler,
    DocumentCreationHandler,
    BrowserHandler,
    FileShareHandler,
    TVMoviesHandler,
    <healthcare-platform>Handler,
    <healthcare-platform>SDK2Handler,
    ClaudeHandler,
    DataValidatorHandler,
    SwarmHandler,
    AgentBuilderHandler,
    AgentExecutionManagerHandler,
    AgentRegistryHandler,
    AgentSIntegrationHandler,
    WorkspaceSharingHandler,
    StructuredAgentSystemHandler,
    StructuredOutputMultiAgentHandler
)


class TestMCPMethodDiscovery(unittest.TestCase):
    """Test case for MCP method discovery and decoration."""
    
    def test_all_handlers_have_mcp_methods(self):
        """Test that all handlers have at least one MCP-exposed method."""
        handlers = [
            EmailHandler, 
            GHLHandler, 
            CalendarHandler, 
            FinderHandler,
            WeatherHandler,
            NewsInfoHandler,
            WolframHandler,
            TerminalHandler,
            SpreadsheetHandler,
            DocumentCreationHandler,
            BrowserHandler,
            FileShareHandler,
            TVMoviesHandler,
            <healthcare-platform>Handler,
            <healthcare-platform>SDK2Handler,
            ClaudeHandler,
            DataValidatorHandler,
            SwarmHandler,
            AgentBuilderHandler,
            AgentExecutionManagerHandler,
            AgentRegistryHandler,
            AgentSIntegrationHandler,
            WorkspaceSharingHandler,
            StructuredAgentSystemHandler,
            StructuredOutputMultiAgentHandler
        ]
        
        for handler_class in handlers:
            # Create an instance for inspection
            handler = handler_class()
            
            # Get all MCP-exposed methods
            mcp_methods = get_mcp_methods(handler)
            
            # Check that at least one method is exposed
            self.assertGreater(
                len(mcp_methods), 
                0, 
                f"Handler {handler_class.__name__} has no MCP-exposed methods"
            )
            
            # For each method, check if it has the required attributes
            for method_name, metadata in mcp_methods.items():
                # Get the method object
                method = getattr(handler, method_name)
                
                # Check that the method is callable
                self.assertTrue(
                    callable(method), 
                    f"Method {method_name} in {handler_class.__name__} is not callable"
                )
                
                # Check that the method has the required MCP attributes
                self.assertTrue(
                    hasattr(method, '_mcp_exposed'),
                    f"Method {method_name} in {handler_class.__name__} is missing _mcp_exposed attribute"
                )
                
                # Check that the method has a description
                self.assertTrue(
                    'description' in metadata,
                    f"Method {method_name} in {handler_class.__name__} is missing description"
                )
                
                # Check that parameters metadata exists
                self.assertTrue(
                    'parameters' in metadata,
                    f"Method {method_name} in {handler_class.__name__} is missing parameters metadata"
                )
    
    def test_execute_method_present(self):
        """Test that all handlers have an execute method."""
        handlers = [
            EmailHandler, 
            GHLHandler, 
            CalendarHandler, 
            FinderHandler,
            WeatherHandler,
            NewsInfoHandler,
            WolframHandler,
            TerminalHandler,
            SpreadsheetHandler,
            DocumentCreationHandler,
            BrowserHandler,
            FileShareHandler,
            TVMoviesHandler,
            <healthcare-platform>Handler,
            <healthcare-platform>SDK2Handler,
            ClaudeHandler,
            DataValidatorHandler,
            SwarmHandler,
            AgentBuilderHandler,
            AgentExecutionManagerHandler,
            AgentRegistryHandler,
            AgentSIntegrationHandler,
            WorkspaceSharingHandler,
            StructuredAgentSystemHandler,
            StructuredOutputMultiAgentHandler
        ]
        
        for handler_class in handlers:
            # Create an instance for inspection
            handler = handler_class()
            
            # Check that execute method exists
            self.assertTrue(
                hasattr(handler, 'execute'),
                f"Handler {handler_class.__name__} is missing execute method"
            )
            
            # Check that execute method is callable
            self.assertTrue(
                callable(getattr(handler, 'execute')),
                f"Execute method in {handler_class.__name__} is not callable"
            )
            
            # Check that execute method is MCP-exposed
            execute_method = getattr(handler, 'execute')
            self.assertTrue(
                is_mcp_exposed(execute_method),
                f"Execute method in {handler_class.__name__} is not MCP-exposed"
            )
    
    def test_async_methods_properly_exposed(self):
        """Test that async methods are properly exposed via MCP."""
        # Handlers known to have async methods
        async_handlers = [
            ClaudeHandler,  # Has agenerate_response and other async methods
            TerminalHandler,  # Likely has async execute_command
            StructuredOutputMultiAgentHandler  # Likely has async processing methods
        ]
        
        for handler_class in async_handlers:
            # Create an instance for inspection
            handler = handler_class()
            
            # Get all MCP-exposed methods
            mcp_methods = get_mcp_methods(handler)
            
            # Filter for async methods
            async_methods = []
            for method_name, metadata in mcp_methods.items():
                method = getattr(handler, method_name)
                if inspect.iscoroutinefunction(method):
                    async_methods.append(method_name)
            
            # Should have at least one async method
            self.assertGreater(
                len(async_methods),
                0,
                f"Handler {handler_class.__name__} should have async methods but none were found"
            )
            
            # Check that each async method has MCP decoration
            for method_name in async_methods:
                method = getattr(handler, method_name)
                self.assertTrue(
                    is_mcp_exposed(method),
                    f"Async method {method_name} in {handler_class.__name__} is not MCP-exposed"
                )
    
    def test_private_methods_not_exposed(self):
        """Test that private methods are not exposed via MCP."""
        handlers = [
            EmailHandler, 
            ClaudeHandler,  # Has several private helper methods
            TerminalHandler
        ]
        
        for handler_class in handlers:
            # Create an instance for inspection
            handler = handler_class()
            
            # Get all methods
            all_methods = [method for method in dir(handler) 
                          if callable(getattr(handler, method))]
            
            # Get private methods (starting with _)
            private_methods = [method for method in all_methods 
                              if method.startswith('_') and not method.startswith('__')]
            
            # There should be some private methods
            self.assertGreater(
                len(private_methods),
                0,
                f"Handler {handler_class.__name__} has no private methods to test"
            )
            
            # Get MCP-exposed methods
            mcp_methods = get_mcp_methods(handler)
            mcp_method_names = list(mcp_methods.keys())
            
            # Check that no private methods are exposed
            for method_name in private_methods:
                self.assertNotIn(
                    method_name,
                    mcp_method_names,
                    f"Private method {method_name} in {handler_class.__name__} is incorrectly exposed via MCP"
                )
    
    def test_claude_wrapper_specific_methods(self):
        """Test specific methods in the ClaudeHandler wrapper."""
        # Create a Claude handler instance
        handler = ClaudeHandler()
        
        # List of methods that should be exposed
        expected_methods = [
            'create_message',
            'create_message_with_thinking',
            'count_tokens',
            'create_message_batch',
            'get_message_batch',
            'get_message_batch_results',
            'cancel_message_batch',
            'list_message_batches',
            'encode_image',
            'select_appropriate_model',
            'generate_response',
            'agenerate_response',
            'analyze_request',
            'is_claude4',
            'supports_thinking',
            'get_prompt_library',
            'execute'
        ]
        
        # Get all MCP-exposed methods
        mcp_methods = get_mcp_methods(handler)
        
        # Check that all expected methods are exposed
        for method_name in expected_methods:
            self.assertIn(
                method_name,
                mcp_methods,
                f"Expected method {method_name} is not exposed in ClaudeHandler"
            )
            
            # Check that the method has a description
            self.assertIn(
                'description',
                mcp_methods[method_name],
                f"Method {method_name} in ClaudeHandler is missing description"
            )
    
    def test_email_wrapper_specific_methods(self):
        """Test specific methods in the EmailHandler wrapper."""
        # Create an Email handler instance
        handler = EmailHandler()
        
        # List of methods that should be exposed
        expected_methods = [
            'open_application',
            'compose_email',
            'send_email',
            'get_unread_emails',
            'search_emails',
            'execute'
        ]
        
        # Get all MCP-exposed methods
        mcp_methods = get_mcp_methods(handler)
        
        # Check that all expected methods are exposed
        for method_name in expected_methods:
            self.assertIn(
                method_name,
                mcp_methods,
                f"Expected method {method_name} is not exposed in EmailHandler"
            )
            
            # Check that the method has a description
            self.assertIn(
                'description',
                mcp_methods[method_name],
                f"Method {method_name} in EmailHandler is missing description"
            )
    
    def test_structured_output_wrapper_methods(self):
        """Test methods in the StructuredOutputMultiAgentHandler wrapper."""
        # Create a handler instance
        handler = StructuredOutputMultiAgentHandler()
        
        # List of methods that should be exposed
        expected_methods = [
            'process_request',
            'get_schema',
            'validate_data',
            'execute'
        ]
        
        # Get all MCP-exposed methods
        mcp_methods = get_mcp_methods(handler)
        
        # Check that all expected methods are exposed
        for method_name in expected_methods:
            self.assertIn(
                method_name,
                mcp_methods,
                f"Expected method {method_name} is not exposed in StructuredOutputMultiAgentHandler"
            )
            
            # Check that the method has a description
            self.assertIn(
                'description',
                mcp_methods[method_name],
                f"Method {method_name} in StructuredOutputMultiAgentHandler is missing description"
            )


if __name__ == '__main__':
    unittest.main()