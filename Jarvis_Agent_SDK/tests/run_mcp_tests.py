#!/usr/bin/env python3
"""
Run MCP Tests

This script runs all the MCP-related tests in the tests directory.
It handles environment setup and provides detailed output for debugging.

Usage:
    python run_mcp_tests.py
"""

import os
import sys
import unittest
import importlib.util
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("mcp_tests.log"),
        logging.StreamHandler()
    ]
)

# Add the parent directory to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# Import the test modules
import test_mcp_method_discovery
import test_mcp_wrapper_coverage
import test_mcp_server_discovery


def run_tests():
    """Run all MCP-related tests."""
    # Create a test suite
    test_suite = unittest.TestSuite()
    
    # Add tests from each module
    test_suite.addTest(unittest.makeSuite(test_mcp_method_discovery.TestMCPMethodDiscovery))
    test_suite.addTest(unittest.makeSuite(test_mcp_wrapper_coverage.TestMCPWrapperCoverage))
    test_suite.addTest(unittest.makeSuite(test_mcp_server_discovery.TestMCPServerDiscovery))
    
    # Run the tests
    test_runner = unittest.TextTestRunner(verbosity=2)
    result = test_runner.run(test_suite)
    
    # Print summary
    print("\nTest Summary:")
    print(f"  Run: {result.testsRun}")
    print(f"  Errors: {len(result.errors)}")
    print(f"  Failures: {len(result.failures)}")
    
    # Return exit code based on test results
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    print("Running MCP Tests...")
    sys.exit(run_tests())