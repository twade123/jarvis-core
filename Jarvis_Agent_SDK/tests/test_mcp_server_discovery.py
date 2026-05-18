#!/usr/bin/env python3
"""
Unit Tests for MCP Server Discovery

This module tests the discovery mechanism for MCP servers to ensure they can be
properly discovered and accessed by the Claude MCP connector. It verifies:

1. Proper URL configuration for the /sse endpoint
2. Authentication token handling
3. Tool discovery and introspection
4. Configuration generation for Claude's MCP connector
"""

import os
import sys
import json
import unittest
import tempfile
from unittest.mock import patch, MagicMock

# Add the parent directory to the path so we can import our modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import server components
from Jarvis_Agent_SDK.mcp_server_template import HandlerMCPServer, MCPRegistry, get_registry
from Jarvis_Agent_SDK.mcp_server_launcher import start_server, HANDLER_REGISTRY

# Import a test handler for our mock server
from Handler.mcp_wrappers import ClaudeHandler


class TestMCPServerDiscovery(unittest.TestCase):
    """Test case for MCP server discovery and configuration."""
    
    def setUp(self):
        """Set up test environment."""
        # Create a mock handler class
        self.mock_handler_class = MagicMock()
        self.mock_handler_class.__name__ = "MockHandler"
        
        # Create a mock server instance
        self.server = HandlerMCPServer(
            self.mock_handler_class, 
            "test_server",
            url_path="/sse"
        )
        
        # Register a test tool
        self.server.tools = {
            "test_tool": {
                "method_name": "test_method",
                "description": "Test tool for discovery",
                "parameters": {
                    "param1": {
                        "description": "First parameter",
                        "required": True
                    }
                }
            }
        }
        
        # Create a clean registry for testing
        self.test_registry = MCPRegistry()
        self.test_registry.register_server("test_server", self.server)
    
    def test_server_url_configuration(self):
        """Test that the server URL is properly configured."""
        # Verify the server URL path
        self.assertEqual(self.server.url_path, "/sse")
        
        # Test with a custom URL path
        custom_server = HandlerMCPServer(
            self.mock_handler_class, 
            "custom_server",
            url_path="/custom"
        )
        self.assertEqual(custom_server.url_path, "/custom")
    
    def test_auth_token_verification(self):
        """Test authentication token verification."""
        # Test with no auth config (should allow all)
        self.assertTrue(self.server.verify_auth_token("any_token"))
        
        # Test with auth config
        self.server.auth_config = MagicMock()
        self.server.auth_config.valid_tokens = ["valid_token"]
        self.assertTrue(self.server.verify_auth_token("valid_token"))
        self.assertFalse(self.server.verify_auth_token("invalid_token"))
    
    def test_tool_discovery(self):
        """Test tool discovery in the server."""
        # Get tools for the server
        tools = self.test_registry.list_tools("test_server")
        
        # Check that our test tool is properly registered
        expected_tool_name = "mcp__test_server__test_tool"
        self.assertIn(expected_tool_name, tools)
        
        # Check tool information
        tool_info = self.test_registry.get_tool_info(expected_tool_name)
        self.assertEqual(tool_info["server"], "test_server")
        self.assertEqual(tool_info["tool"], "test_tool")
        self.assertEqual(tool_info["method"], "test_method")
        self.assertEqual(tool_info["description"], "Test tool for discovery")
    
    def test_mcp_config_generation(self):
        """Test generation of MCP configuration for Claude."""
        # Create a temp file for the config
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as temp:
            temp_path = temp.name
        
        try:
            # Set environment variables for testing
            os.environ["MCP_HOST"] = "test.example.com"
            os.environ["MCP_PORT"] = "9000"
            
            # Generate config
            config = self.test_registry.create_mcp_config(
                allowed_tools=["test_tool"],
                output_path=temp_path
            )
            
            # Check standard server config
            self.assertIn("mcpServers", config)
            self.assertIn("test_server", config["mcpServers"])
            
            # Check Claude MCP connector config
            claude_config_key = "claude_test_server_config"
            self.assertIn(claude_config_key, config)
            
            # Verify Claude config format
            claude_config = config[claude_config_key]
            self.assertIn("mcp_servers", claude_config)
            self.assertEqual(len(claude_config["mcp_servers"]), 1)
            
            # Check server properties
            server_config = claude_config["mcp_servers"][0]
            self.assertEqual(server_config["type"], "url")
            self.assertEqual(server_config["url"], "https://test.example.com:9000/sse")
            self.assertEqual(server_config["name"], "test_server")
            
            # Check tool configuration
            self.assertIn("tool_configuration", server_config)
            self.assertTrue(server_config["tool_configuration"]["enabled"])
            self.assertEqual(server_config["tool_configuration"]["allowed_tools"], ["test_tool"])
            
            # Verify file was written correctly
            with open(temp_path, 'r') as f:
                file_config = json.load(f)
                self.assertEqual(config, file_config)
                
        finally:
            # Clean up temp file
            if os.path.exists(temp_path):
                os.unlink(temp_path)
    
    @patch('Jarvis_Agent_SDK.mcp_server_launcher.import_handler_class')
    def test_server_start_with_discovery(self, mock_import):
        """Test that server startup includes discovery information."""
        # Mock the handler class import
        mock_import.return_value = ClaudeHandler
        
        # Mock the registry
        mock_registry = MagicMock()
        
        # Test server startup with discovery
        with patch('Jarvis_Agent_SDK.mcp_server_launcher.get_registry', return_value=mock_registry):
            # Add a test entry to the registry
            HANDLER_REGISTRY["test"] = ("Handler.mcp_wrappers", "ClaudeHandler")
            
            # Start the server
            server = start_server("test", url_path="/test")
            
            # Verify the server was registered
            mock_registry.register_server.assert_called_once()
            
            # Clean up
            HANDLER_REGISTRY.pop("test")


if __name__ == '__main__':
    unittest.main()