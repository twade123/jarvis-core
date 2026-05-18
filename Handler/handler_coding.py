#!/usr/bin/env python3

"""
Handler for code generation, execution, and analysis with security measures.

Capabilities:
    - Execute simple and complex code snippets
    - Generate code using GPT-Neo and GPT-4
    - Verify code safety and security
    - Analyze code complexity
    - Manage file operations
    - Handle API endpoints for code operations
    - Monitor system resources
    - Validate code execution

Patterns:
    - "generate code for {task_description}"
    - "execute code {code_block}"
    - "verify code safety"
    - "analyze code complexity"
    - "manage file operations"
    - "handle API requests"

Intents:
    - coding_generate_code
    - coding_execute_code
    - coding_verify_safety
    - coding_analyze
    - coding_file_ops
    - coding_api_handle

Parameters:
    - code_request: string (code or task description)
    - request_type: string ('simple' or 'complex')
    - file_operations: Dict (file operation details)
    - api_key: string (for authentication)
    - model_type: string (GPT-Neo or GPT-4)
    - safety_checks: Dict (verification parameters)
"""

import torch
import logging
import os
import json
import requests
import tempfile
import subprocess
import venv
from pathlib import Path
from transformers import AutoTokenizer, GPTNeoForCausalLM
from typing import Dict, List, Tuple, Optional, Any, Union
from openai import OpenAI
from flask import Flask, request, jsonify
from functools import wraps
import hashlib
import time
import threading
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import re
import ast
import asyncio
import sys
import traceback
import signal
import shutil
import importlib.util
from importlib import import_module
import inspect

from Core.config import PATHS, CONFIG, load_api_key
from Handler.handler_base import BaseHandler, HandlerResult

# Import helper functions for runtime imports - these don't create circular dependencies
from Jarvis_Agent_SDK.import_helper import (
    get_agent_builder,
    get_unified_database
)
from Jarvis_Agent_SDK.boardroom_connector import (
    track_journey_step_sync,
    generate_request_id,
    generate_simple_id
)
from Database.v2.db_helper import connection as v2_connection

# Lazy import for handler_code_execution_utils to avoid circular dependencies
def get_execution_utils():
    """Lazy import for code execution utilities"""
    try:
        from .handler_code_execution_utils import DevelopmentEnvironment, FileOperationManager, CodeAnalyzer
        return {
            "DevelopmentEnvironment": DevelopmentEnvironment,
            "FileOperationManager": FileOperationManager,
            "CodeAnalyzer": CodeAnalyzer
        }
    except ImportError as e:
        logger.error(f"Error importing code execution utilities: {e}")
        return None

logger = logging.getLogger(__name__)

# Use runtime imports to avoid circular dependencies
def get_agent_components():
    """Get agent components only when needed to avoid circular imports"""
    try:
        # Use import_helper for orchestrator functions to avoid circular dependencies
        from Jarvis_Agent_SDK.import_helper import get_orchestrator_functions
        orchestrator_funcs = get_orchestrator_functions()
        analyze_handler_capabilities = orchestrator_funcs.get("analyze_handler_capabilities")
        
        # Import agent builder components directly
        from Handler.handler_agent_builder import (
            AgentBuilder, AgentType, AgentSpecialization, 
            AgentCapability, AgentTool
        )
        
        return {
            "analyze_handler_capabilities": analyze_handler_capabilities,
            "AgentBuilder": AgentBuilder,
            "AgentType": AgentType,
            "AgentSpecialization": AgentSpecialization,
            "AgentCapability": AgentCapability,
            "AgentTool": AgentTool
        }
    except ImportError as e:
        logger.warning(f"Agent components not available - specialized agent features disabled: {e}")
        return None

# Export the CodeExecutionHandler class for other modules
def get_code_execution_handler():
    """Return the CodeExecutionHandler class to avoid circular imports."""
    return CodeExecutionHandler

class CodeExecutionHandlerOrchestratorAgent:
    """
    Orchestrator agent for the Code Execution Handler System.
    
    This agent serves as a bridge between the code execution handler system and the Jarvis orchestrator,
    managing code verification, execution, and facilitating bidirectional communication with Jarvis.
    
    Core Responsibilities:
    1. Code Execution Management
       - Verify code safety and security
       - Execute code in isolated environments
       - Track code execution and results
       
    2. Flask Server Lifecycle Management
       - Start and stop the Flask server as needed
       - Track server status and health
       - Manage API access and authentication
       
    3. System Communication
       - Bidirectional communication with Jarvis
       - Integration with BoardRoom tracking
       - Error reporting and recovery
       
    4. Performance Monitoring
       - Track metrics and KPIs
       - Monitor system health
       
    5. Database Management
       - Schema creation and migration
       - Query optimization
       - Data modeling and relationships
       - Transaction management
       
    6. Full-Stack Development
       - Frontend framework implementation (React, Vue, Angular)
       - Backend API development (REST, GraphQL)
       - Database design and optimization
       - Deployment configuration (Docker, Kubernetes)
       - CI/CD pipeline integration
    """
    
    # System prompt for the agent to understand its role and capabilities
    SYSTEM_PROMPT = """
    You are the Code Execution Handler Orchestrator Agent, responsible for managing the Flask server
    that provides secure code execution services. Your primary responsibilities include:

    1. SERVER LIFECYCLE MANAGEMENT:
       - Starting the Flask server when requested
       - Monitoring server health and status
       - Gracefully shutting down the server when needed
       - Restarting the server if it crashes or becomes unresponsive

    2. REQUEST HANDLING:
       - Processing code verification requests
       - Managing execution of verified code
       - Ensuring proper API key validation
       - Tracking all requests and responses

    3. SECURITY ENFORCEMENT:
       - Validating all incoming requests
       - Ensuring proper authentication
       - Monitoring for suspicious activity
       - Reporting security incidents

    4. PERFORMANCE OPTIMIZATION:
       - Tracking server response times
       - Monitoring resource usage
       - Balancing concurrent requests
       - Optimizing server configuration

    5. COMMUNICATION:
       - Maintaining bidirectional communication with Jarvis
       - Providing regular status updates
       - Reporting errors and exceptions
       - Requesting assistance when needed

    6. KNOWLEDGE MANAGEMENT:
       - Maintaining comprehensive understanding of all modules
       - Tracking code structure and documentation
       - Understanding API endpoints and their purposes
       - Following security protocols and best practices
       
    7. DATABASE MANAGEMENT:
       - Schema design and optimization
       - Migration management
       - Query performance optimization
       - Data modeling and relationships
       - Transaction handling and isolation levels
       - Index creation and maintenance
       
    8. FULL-STACK DEVELOPMENT:
       - Frontend development (React, Vue, Angular, etc.)
       - Backend architecture (REST, GraphQL APIs)
       - Container deployment (Docker, Kubernetes)
       - Serverless architectures
       - CI/CD pipeline implementation
       - Microservices architecture design
       - Testing strategies and frameworks

    You should maintain complete awareness of all server activities while following
    a minimal intervention approach. Only engage actively when specific conditions
    require your attention, such as server failures, security concerns, or explicit
    requests from Jarvis.
    """
    
    def __init__(self, handler=None, system_name="CodeExecutionHandlerSystem"):
        # Handle case where system_name is actually a handler object
        if hasattr(handler, 'name'):
            self.handler = handler
            self.system_name = "CodeExecutionHandlerSystem"
        else:
            self.system_name = system_name
            self.handler = None
            
        self.conversation_history = []
        self.active = True
        self.current_journey_id = None
        self.flask_server_thread = None
        self.flask_server_active = False
        self.server_metrics = {
            "start_time": None,
            "request_count": 0,
            "error_count": 0,
            "average_response_time": 0,
            "uptime": 0
        }
        
        # Knowledge base of docstrings and module information
        self.knowledge_base = {
            "modules": {},
            "endpoints": {},
            "code_examples": {},
            "security_protocols": {},
            "database_schemas": {},
            "frontend_frameworks": {},
            "deployment_platforms": {},
            "api_patterns": {}
        }
        
        # Initialize unified database
        self._init_database()
        
        # BoardRoom was archived (Phase 3). Tracking uses V2 databases directly.
        self.boardroom = None
            
        # Initialize knowledge base
        self.initialize_knowledge_base()
    
    def _init_database(self):
        """Initialize V2 intelligence database for code execution tracking."""
        try:
            self._init_database_schema()
            logger.info(f"{self.system_name}: V2 intelligence database initialized")
        except Exception as e:
            logger.error(f"{self.system_name}: Error initializing database: {str(e)}")

    def _init_database_schema(self):
        """Initialize database schema for code execution tracking in V2 intelligence DB."""
        try:
            with v2_connection("intelligence") as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS code_execution_history (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        request_id TEXT NOT NULL,
                        code_hash TEXT NOT NULL,
                        execution_time REAL,
                        success BOOLEAN,
                        output TEXT,
                        error TEXT,
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS api_request_metrics (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        endpoint TEXT NOT NULL,
                        method TEXT NOT NULL,
                        response_time REAL,
                        status_code INTEGER,
                        client_ip TEXT,
                        request_size INTEGER,
                        response_size INTEGER,
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS server_health_metrics (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        cpu_usage REAL,
                        memory_usage REAL,
                        active_connections INTEGER,
                        requests_per_minute INTEGER,
                        errors_per_minute INTEGER,
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS security_events (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        event_type TEXT NOT NULL,
                        description TEXT,
                        severity TEXT,
                        client_ip TEXT,
                        request_path TEXT,
                        resolved BOOLEAN DEFAULT FALSE,
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS package_usage (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        package_name TEXT NOT NULL,
                        version TEXT,
                        frequency INTEGER DEFAULT 1,
                        last_used TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
            logger.info(f"{self.system_name}: Database schema initialized successfully")
        except Exception as e:
            logger.error(f"{self.system_name}: Error initializing database schema: {str(e)}")
    
    def initialize_knowledge_base(self):
        """
        Initialize the knowledge base with documentation and code from key modules.
        This ensures the agent has comprehensive understanding of its components.
        """
        try:
            # Add handler documentation
            if self.handler:
                self.knowledge_base["modules"]["handler"] = {
                    "docstring": inspect.getdoc(self.handler.__class__),
                    "capabilities": self.handler.capabilities if hasattr(self.handler, "capabilities") else {},
                    "methods": self._get_methods_info(self.handler.__class__)
                }
                
                # Add file manager information
                if hasattr(self.handler, "file_manager"):
                    self.knowledge_base["modules"]["file_manager"] = {
                        "docstring": inspect.getdoc(self.handler.file_manager.__class__),
                        "methods": self._get_methods_info(self.handler.file_manager.__class__)
                    }
                
                # Add Flask app endpoints
                if hasattr(self.handler, "app") and self.handler.app:
                    self.knowledge_base["endpoints"] = self._extract_flask_endpoints(self.handler.app)
            
            # Add this class's documentation
            self.knowledge_base["modules"]["orchestrator_agent"] = {
                "docstring": inspect.getdoc(self.__class__),
                "system_prompt": self.SYSTEM_PROMPT,
                "methods": self._get_methods_info(self.__class__)
            }
            
            # Add security protocols
            self.knowledge_base["security_protocols"] = {
                "api_key_validation": "All endpoints require API key validation using the FLASK API key",
                "code_verification": "All code is verified for syntax, security vulnerabilities, and dependencies before execution",
                "isolated_execution": "Code is executed in isolated environments to prevent system compromise",
                "resource_limits": "Execution has time and memory limits to prevent resource exhaustion"
            }
            
            # Add code examples
            self.knowledge_base["code_examples"] = {
                "start_server": "handler.orchestrator.start_flask_server(port=5000)",
                "stop_server": "handler.orchestrator.stop_flask_server()",
                "verify_code": "verification = handler.file_manager.verify_operation(operation_id, code)",
                "execute_code": "result = handler.file_manager.execute_operation(operation_id, code, file_path)"
            }
            
            # Add database schemas
            self.knowledge_base["database_schemas"] = {
                "code_execution_history": """
                    CREATE TABLE code_execution_history (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        request_id TEXT NOT NULL,
                        code_hash TEXT NOT NULL,
                        execution_time REAL,
                        success BOOLEAN,
                        output TEXT,
                        error TEXT,
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """,
                "api_request_metrics": """
                    CREATE TABLE api_request_metrics (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        endpoint TEXT NOT NULL,
                        method TEXT NOT NULL,
                        response_time REAL,
                        status_code INTEGER,
                        client_ip TEXT,
                        request_size INTEGER,
                        response_size INTEGER,
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """
            }
            
            # Add frontend frameworks
            self.knowledge_base["frontend_frameworks"] = {
                "react": "Component-based UI library with JSX syntax and virtual DOM",
                "vue": "Progressive framework for building UIs with a template-based syntax",
                "angular": "Full-featured framework with TypeScript integration and dependency injection",
                "svelte": "Compiler-based framework that builds highly optimized vanilla JavaScript",
                "next.js": "React framework with server-side rendering, static site generation, and API routes"
            }
            
            # Add deployment platforms
            self.knowledge_base["deployment_platforms"] = {
                "docker": "Containerization platform for packaging applications and dependencies",
                "kubernetes": "Container orchestration system for automated deployment and scaling",
                "aws": "Cloud provider with services like EC2, Lambda, S3, and RDS",
                "azure": "Microsoft's cloud platform with services for compute, databases, and AI",
                "google_cloud": "Google's cloud platform with services like GCE, GKE, and BigQuery",
                "vercel": "Platform optimized for frontend frameworks with automatic deployments",
                "heroku": "PaaS for building, running, and operating applications in the cloud"
            }
            
            # Add API patterns
            self.knowledge_base["api_patterns"] = {
                "rest": {
                    "description": "Representational State Transfer architecture style",
                    "methods": ["GET", "POST", "PUT", "DELETE", "PATCH"],
                    "status_codes": {
                        "200": "OK - Request successful",
                        "201": "Created - Resource created successfully",
                        "400": "Bad Request - Invalid input",
                        "401": "Unauthorized - Authentication required",
                        "403": "Forbidden - Insufficient permissions",
                        "404": "Not Found - Resource not found",
                        "500": "Internal Server Error - Server failure"
                    }
                },
                "graphql": {
                    "description": "Query language for APIs with a single endpoint",
                    "operations": ["query", "mutation", "subscription"],
                    "benefits": [
                        "Eliminates over-fetching and under-fetching",
                        "Strongly typed schema",
                        "Introspection for self-documentation"
                    ]
                }
            }
            
            logger.info(f"Successfully initialized knowledge base with {len(self.knowledge_base['modules'])} modules")
        except Exception as e:
            logger.error(f"Error initializing knowledge base: {str(e)}")
    
    def _get_methods_info(self, cls):
        """Extract method information from a class"""
        methods_info = {}
        for name, method in inspect.getmembers(cls, predicate=inspect.isfunction):
            if not name.startswith('_') or name == '__init__':  # Include init but exclude other private methods
                methods_info[name] = {
                    "docstring": inspect.getdoc(method),
                    "signature": str(inspect.signature(method))
                }
        return methods_info
    
    def _extract_flask_endpoints(self, app):
        """Extract endpoint information from Flask app"""
        endpoints = {}
        if not app or not hasattr(app, 'url_map'):
            return endpoints
            
        for rule in app.url_map.iter_rules():
            endpoints[rule.endpoint] = {
                "url": str(rule),
                "methods": list(rule.methods),
                "handler": rule.endpoint
            }
        return endpoints
    
    def update_knowledge_base(self):
        """Update the knowledge base with current information"""
        self.initialize_knowledge_base()
        logger.info("Knowledge base updated")
    
    def get_knowledge_base_summary(self):
        """
        Get a summary of the knowledge base.
        
        Returns:
            dict: Summary of the knowledge base
        """
        return {
            "module_count": len(self.knowledge_base["modules"]),
            "endpoint_count": len(self.knowledge_base["endpoints"]),
            "modules": list(self.knowledge_base["modules"].keys()),
            "endpoints": list(self.knowledge_base["endpoints"].keys()),
            "security_protocols": list(self.knowledge_base["security_protocols"].keys()),
            "code_examples": list(self.knowledge_base["code_examples"].keys())
        }
    
    def _track_jarvis_communication(self, direction, message, journey_id=None, _prevent_recursion=False):
        """
        Track communication with the Jarvis orchestrator
        
        Args:
            direction: 'input' or 'output'
            message: The message being tracked
            journey_id: Optional journey ID
            _prevent_recursion: Flag to prevent infinite recursion
        """
        if not journey_id:
            journey_id = self.current_journey_id or f"code_exec_comm_{int(time.time())}"
        
        # Create tracking data with timestamp and message metadata
        tracking_data = {
            "timestamp": time.time(),
            "direction": direction,
            "message_type": str(type(message).__name__),
            "system": "CodeExecutionHandlerOrchestratorAgent"
        }
        
        # Prepare step data with appropriate input/output fields based on direction
        step_data = {"description": f"Jarvis communication: {direction}"}
        
        # Handle message based on direction
        try:
            # Create safe message representation
            safe_message = None
            
            if isinstance(message, dict):
                # Try to serialize to JSON first
                try:
                    import json
                    safe_message = json.dumps(message)[:500] + "..." if len(json.dumps(message)) > 500 else json.dumps(message)
                except Exception as e:
                    # If serialization fails, create simple string representation
                    safe_message = str(message)[:500] + "..." if len(str(message)) > 500 else str(message)
            else:
                # For non-dictionary messages, convert to string directly
                safe_message = str(message)[:500] + "..." if len(str(message)) > 500 else str(message)
            
            # Assign to proper field based on direction
            if direction == "input":
                step_data["input_data"] = safe_message
            else:
                step_data["output_data"] = safe_message
            
        except Exception as e:
            logger.error(f"Error preparing message data: {str(e)}")
            # Fallback to simple string
            step_data["description"] = f"Error tracking message: {str(e)}"
            safe_message = str(message)[:100] + "..." if len(str(message)) > 100 else str(message)
            step_data[direction == "input" and "input_data" or "output_data"] = safe_message
        
        if self.boardroom and not _prevent_recursion:
            try:
                track_journey_step_sync(
                    journey_id=journey_id,
                    step_name=f"jarvis_communication_{direction}",
                    description=step_data["description"],
                    step_type="communication",
                    input_data=step_data.get("input_data"),
                    output_data=step_data.get("output_data")
                )
            except Exception as e:
                logger.error(f"Error tracking Jarvis communication: {str(e)}")
        
        # Add to conversation history regardless of BoardRoom availability
        self.conversation_history.append({
            "timestamp": time.time(),
            "direction": direction,
            "message": safe_message,
            "journey_id": journey_id
        })
        
        return True
    
    def send_message_to_jarvis(self, message, context=None, handler_params=None, message_type="update", request_id=None, journey_id=None):
        """Send a message to the Jarvis orchestrator"""
        if not request_id:
            request_id = generate_request_id({"message": message, "timestamp": time.time()})
        
        if not journey_id:
            journey_id = f"code_exec_handler_{request_id}_{int(time.time())}"
            self.current_journey_id = journey_id
        
        message_payload = {
            "message": message,
            "context": context or {},
            "request_id": request_id,
            "journey_id": journey_id,
            "handler_params": handler_params or {},
            "timestamp": time.time(),
            "system": self.system_name,
            "message_type": message_type
        }
        
        # Track outgoing message
        self._track_jarvis_communication("outgoing", message_payload, journey_id)
        
        try:
            # Logic to communicate with Jarvis would go here
            # This is a placeholder - actual implementation depends on Jarvis API
            logger.info(f"Message sent to Jarvis: {message[:100]}...")
            return True, journey_id
        except Exception as e:
            logger.error(f"Error sending message to Jarvis: {str(e)}")
            return False, journey_id

    def start_flask_server(self, port=5000):
        """
        Start the Flask server in a background thread
        
        Args:
            port: Port to run the server on (default: 5000)
            
        Returns:
            bool: True if server started successfully
        """
        if self.flask_server_active:
            logger.info("Flask server is already running")
            return True
            
        if not self.handler:
            logger.error("Cannot start Flask server - handler not initialized")
            return False
            
        try:
            # First ensure the Flask app is initialized
            app = self.handler._init_flask_app()
            
            # Make sure knowledge base is up to date
            self.update_knowledge_base()
            
            # Update metrics
            self.server_metrics["start_time"] = time.time()
            self.server_metrics["request_count"] = 0
            self.server_metrics["error_count"] = 0
            self.server_metrics["average_response_time"] = 0
            
            # Add shutdown endpoint if not already present
            if not hasattr(app, 'shutdown_added') or not app.shutdown_added:
                @app.route('/shutdown', methods=['POST'])
                def shutdown():
                    if request.headers.get('x-api-key') != load_api_key('FLASK'):
                        return jsonify({'error': 'Unauthorized'}), 401
                        
                    func = request.environ.get('werkzeug.server.shutdown')
                    if func is None:
                        raise RuntimeError('Not running with the Werkzeug Server')
                    func()
                    self.flask_server_active = False
                    return 'Server shutting down...'
                    
                app.shutdown_added = True
                
            # Add knowledge base endpoint if not already present
            if not hasattr(app, 'knowledge_endpoint_added') or not app.knowledge_endpoint_added:
                @app.route('/knowledge', methods=['GET'])
                def get_knowledge():
                    api_key = request.headers.get('x-api-key')
                    if api_key != load_api_key('FLASK'):
                        return jsonify({'error': 'Unauthorized'}), 401
                        
                    # Return a summary rather than the full knowledge base for security
                    return jsonify(self.get_knowledge_base_summary())
                    
                app.knowledge_endpoint_added = True
                
            # Define function to run in thread
            def run_flask_server():
                try:
                    # Store the start time for tracking
                    start_time = time.time()
                    logger.info(f"Starting Flask server on port {port}")
                    
                    # Track server start
                    journey_id = f"flask_server_{int(time.time())}"
                    track_journey_step_sync(
                        journey_id=journey_id,
                        step_name="flask_server_start",
                        description=f"Started Flask server on port {port}",
                        step_type="server_lifecycle",
                        input_data={"port": port}
                    )
                    
                    # Run the Flask app
                    app.run(host='localhost', port=port, debug=False, use_reloader=False)
                    
                    # Track server stop (if it gets here naturally)
                    track_journey_step_sync(
                        journey_id=journey_id,
                        step_name="flask_server_stop",
                        description=f"Flask server stopped after {time.time() - start_time:.2f} seconds",
                        step_type="server_lifecycle"
                    )
                    
                    logger.info("Flask server has stopped")
                except Exception as e:
                    logger.error(f"Error in Flask server thread: {str(e)}")
                    self.flask_server_active = False
            
            # Start the thread
            self.flask_server_thread = threading.Thread(target=run_flask_server, daemon=True)
            self.flask_server_thread.start()
            self.flask_server_active = True
            
            # Give the server a moment to start
            time.sleep(1)
            
            # Report status to Jarvis
            self.send_message_to_jarvis(
                message=f"Flask server started on port {port}",
                context={
                    "server_status": "started", 
                    "port": port,
                    "knowledge_base": self.get_knowledge_base_summary()
                },
                message_type="server_status"
            )
            
            return True
        except Exception as e:
            logger.error(f"Error starting Flask server: {str(e)}")
            return False
            
    def stop_flask_server(self):
        """
        Stop the Flask server if it's running
        
        Returns:
            bool: True if server stopped successfully or wasn't running
        """
        if not self.flask_server_active:
            logger.info("Flask server is not running")
            return True
            
        try:
            # Try to send shutdown request
            try:
                api_key = load_api_key('FLASK')
                requests.post('http://localhost:5000/shutdown', 
                             headers={'X-API-KEY': api_key},
                             timeout=5)
                logger.info("Shutdown request sent to Flask server")
            except Exception as e:
                logger.error(f"Error sending shutdown request: {str(e)}")
                # If we can't shut down gracefully, we'll mark it as inactive anyway
                
            # Mark server as inactive
            self.flask_server_active = False
            
            # Report status to Jarvis
            self.send_message_to_jarvis(
                message="Flask server stopped",
                context={"server_status": "stopped"},
                message_type="server_status"
            )
            
            return True
        except Exception as e:
            logger.error(f"Error stopping Flask server: {str(e)}")
            return False
            
    def is_flask_server_running(self):
        """
        Check if the Flask server is running
        
        Returns:
            bool: True if server is running
        """
        if not self.flask_server_active:
            return False
            
        # Additional check - try to connect to the server
        try:
            response = requests.get('http://localhost:5000', timeout=1)
            # If we get any response, the server is running
            return True
        except requests.RequestException:
            # If we can't connect, server is not running
            self.flask_server_active = False
            return False

    def get_capabilities(self):
        """
        Return the capabilities of this orchestrator agent.
        This method is used by the Jarvis orchestrator to discover what this agent can do.
        
        Returns:
            List[str]: List of capabilities
        """
        return [
            "flask_server_management",
            "code_execution_verification",
            "security_enforcement",
            "performance_monitoring",
            "bidirectional_communication",
            "error_handling_recovery",
            "api_endpoint_management",
            "knowledge_base_maintenance",
            "database_management",
            "full_stack_development"
        ]
    
    def get_status(self):
        """
        Get the current status of the Flask server and the orchestrator agent.
        
        Returns:
            Dict: Status information
        """
        current_time = time.time()
        uptime = current_time - self.server_metrics["start_time"] if self.server_metrics["start_time"] else 0
        
        return {
            "server_active": self.flask_server_active,
            "agent_active": self.active,
            "server_metrics": {
                **self.server_metrics,
                "uptime": uptime
            },
            "journey_id": self.current_journey_id,
            "system_name": self.system_name,
            "timestamp": current_time
        }
    
    def restart_flask_server(self, port=5000):
        """
        Restart the Flask server - stop it if running, then start it again.
        
        Args:
            port: Port to run the server on (default: 5000)
            
        Returns:
            bool: True if server was successfully restarted
        """
        # First stop the server if it's running
        if self.flask_server_active:
            logger.info("Restarting Flask server - stopping current instance...")
            stop_success = self.stop_flask_server()
            if not stop_success:
                logger.error("Failed to stop the Flask server for restart")
                return False
            
            # Wait a moment for the server to fully stop
            time.sleep(2)
        
        # Now start the server again
        logger.info("Starting new Flask server instance...")
        return self.start_flask_server(port=port)
    
    def record_request(self, endpoint, response_time, was_successful):
        """
        Record metrics for a request to the Flask server.
        
        Args:
            endpoint: The endpoint that was requested
            response_time: Time taken to process the request in seconds
            was_successful: Whether the request was successful
            
        Returns:
            None
        """
        # Update request count
        self.server_metrics["request_count"] += 1
        
        # Update error count if request failed
        if not was_successful:
            self.server_metrics["error_count"] += 1
        
        # Update average response time
        current_avg = self.server_metrics["average_response_time"]
        current_count = self.server_metrics["request_count"]
        self.server_metrics["average_response_time"] = ((current_avg * (current_count - 1)) + response_time) / current_count

    def get_knowledge_for_jarvis(self, detail_level="summary"):
        """
        Get knowledge base information formatted for Jarvis orchestrator.
        
        Args:
            detail_level: Level of detail to provide ("summary", "medium", "full")
            
        Returns:
            Dict: Knowledge base information at the requested detail level
        """
        if detail_level == "summary":
            return self.get_knowledge_base_summary()
        elif detail_level == "medium":
            # Medium detail provides more information about endpoints and capabilities
            return {
                "modules": {name: {"docstring": info.get("docstring", "")} 
                           for name, info in self.knowledge_base["modules"].items()},
                "endpoints": self.knowledge_base["endpoints"],
                "security_protocols": self.knowledge_base["security_protocols"],
                "capabilities": self.get_capabilities()
            }
        else:  # full detail
            # Full knowledge base including all method details
            # But filter out any sensitive information
            knowledge = dict(self.knowledge_base)
            # Remove any potentially sensitive internal implementation details
            if "system_prompt" in knowledge["modules"].get("orchestrator_agent", {}):
                knowledge["modules"]["orchestrator_agent"].pop("system_prompt", None)
            return knowledge

class CodeExecutionHandler(BaseHandler):
    """Handler for code execution and development tasks"""
    
    def __init__(self):
        """Initialize the handler with necessary components"""
        # Set the handler_name attribute required by BaseHandler
        self.handler_name = "coding"
        self.app_name = "CodeExecutionHandler"
        
        # Initialize LLM for simple code generation
        from transformers import GPTNeoForCausalLM, GPT2Tokenizer
        
        self.tokenizer = GPT2Tokenizer.from_pretrained("EleutherAI/gpt-neo-1.3B")
        self.model = GPTNeoForCausalLM.from_pretrained("EleutherAI/gpt-neo-1.3B")
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model.to(self.device)
        
        # Initialize OpenAI client for complex tasks
        api_key_path = os.path.join(PATHS["API_DIR"], "OPENAI_API_KEY.txt")
        try:
            with open(api_key_path, 'r') as f:
                api_key = f.read().strip()
                self.openai_client = OpenAI(api_key=api_key)
        except Exception as e:
            logger.error(f"Failed to load OpenAI API key: {e}")
            self.openai_client = None
        
        # Lazily initialize Flask app to avoid request context errors during import
        self.app = None
        self._flask_initialized = False
        
        # Lazily import utilities to avoid circular dependencies
        utils = get_execution_utils()
        if utils:
            # Initialize development environment and managers
            self.dev_env = utils["DevelopmentEnvironment"](PATHS["BASE_DIR"])
            self.file_manager = utils["FileOperationManager"](self.dev_env, self.openai_client)
            self.code_analyzer = utils["CodeAnalyzer"]()
        else:
            logger.error("Failed to import code execution utilities")
            raise ImportError("Required code execution utilities not available")
        
        # Initialize unified database access
        self.init_database()
        
        # Initialize orchestrator agent
        self.orchestrator = CodeExecutionHandlerOrchestratorAgent(self)
        
        # Register capabilities
        self.register_capabilities()

    def init_database(self):
        """Initialize V2 intelligence database for code execution tracking."""
        try:
            # Verify intelligence DB is accessible
            with v2_connection("intelligence") as conn:
                conn.execute("SELECT 1")
            logger.info("Connected to V2 intelligence database")
        except Exception as e:
            logger.error(f"Error connecting to V2 intelligence database: {e}")

    def register_capabilities(self):
        """Register handler capabilities"""
        self.capabilities = {
            "execute_simple_code": {
                "description": "Execute simple code snippets using GPT-Neo",
                "parameters": ["code_request"],
                "example": "Write a function to calculate factorial"
            },
            "execute_complex_code": {
                "description": "Execute complex code operations with safety measures",
                "parameters": ["code_request", "file_operations"],
                "example": "Create a class for handling database operations"
            },
            "verify_code": {
                "description": "Verify code changes in isolated environment",
                "parameters": ["code", "operation_type"],
                "example": "Verify this database connection code"
            }
        }

    def _init_flask_app(self):
        """Lazily initialize Flask app only when needed"""
        if not self._flask_initialized:
            self.app = Flask(__name__)
            self.setup_flask_app()
            self._flask_initialized = True
        return self.app

    def setup_flask_app(self):
        """Set up Flask routes and configuration"""
        # If app isn't initialized yet, do nothing - this will be called by _init_flask_app
        if self.app is None:
            return
            
        # Add route decorators and handlers here
        self.app.route('/verify_file_operation', methods=['POST'])(self.require_api_key(self.verify_file_operation_endpoint))
        self.app.route('/execute_file_operation', methods=['POST'])(self.require_api_key(self.execute_file_operation_endpoint))
        self.app.route('/assistant_request', methods=['POST'])(self.require_api_key(self.assistant_request_endpoint))
        
    def verify_file_operation_endpoint(self):
        """Flask endpoint for file operation verification"""
        data = request.get_json()
        return self.file_manager.verify_operation_endpoint(data)
        
    def execute_file_operation_endpoint(self):
        """Flask endpoint for file operation execution"""
        data = request.get_json()
        return self.file_manager.execute_operation_endpoint(data)
        
    def assistant_request_endpoint(self):
        """Flask endpoint for assistant requests"""
        data = request.get_json()
        return self.handle_assistant_request(data)

    def require_api_key(self, f):
        """Decorator to require API key for endpoints"""
        @wraps(f)
        def decorated(*args, **kwargs):
            api_key = request.headers.get('x-api-key')
            if api_key != load_api_key('FLASK'):
                return jsonify({'error': 'Unauthorized'}), 401
            return f(*args, **kwargs)
        return decorated

    def handle_request(self, request_data: Dict) -> Dict:
        """Main entry point for handling requests"""
        try:
            request_type = request_data.get('type', 'simple')
            code_request = request_data.get('code_request')
            
            if not code_request:
                return {"error": "No code request provided", "status": "failed"}
            
            if request_type == 'simple':
                return self.handle_simple_request(code_request)
            else:
                return self.handle_complex_request(code_request, request_data.get('file_operations', {}))
                
        except Exception as e:
            logger.error(f"Error handling request: {e}")
            return {"error": str(e), "status": "failed"}

    def handle_simple_request(self, code_request: str) -> Dict:
        """Handle simple code requests using GPT-Neo"""
        try:
            # Generate code
            inputs = self.tokenizer(code_request, return_tensors="pt").to(self.device)
            with torch.no_grad():
                outputs = self.model.generate(
                    inputs.input_ids,
                    max_length=500,
                    num_return_sequences=1,
                    temperature=0.7,
                    pad_token_id=self.tokenizer.eos_token_id
                )
            
            code = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
            
            # Verify code
            verification = self.file_manager.verify_operation(
                hashlib.md5(code_request.encode()).hexdigest(),
                code
            )
            
            return {
                "code": code,
                "verification": verification,
                "status": "success"
            }
            
        except Exception as e:
            logger.error(f"Error in simple request: {e}")
            return {"error": str(e), "status": "failed"}

    def handle_complex_request(self, code_request: str, file_operations: Dict) -> Dict:
        """Handle complex code requests using OpenAI and safety measures"""
        try:
            # Analyze complexity
            complexity_analysis = self.analyze_complexity(code_request)
            
            # Generate and verify code
            response = self.openai_client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are a secure coding assistant."},
                    {"role": "user", "content": code_request}
                ],
                temperature=0.7,
                max_tokens=500
            )
            
            code = response.choices[0].message.content.strip()
            
            # Verify code
            verification = self.file_manager.verify_operation(
                hashlib.md5(code_request.encode()).hexdigest(),
                code
            )
            
            return {
                "code": code,
                "verification": verification,
                "complexity_analysis": complexity_analysis,
                "status": "success"
            }
            
        except Exception as e:
            logger.error(f"Error in complex request: {e}")
            return {"error": str(e), "status": "failed"}

    def analyze_complexity(self, request_text: str) -> Dict[str, List[str]]:
        """Analyze request complexity"""
        # Implementation from previous CodeAnalyzer class
        return {}

    def start(self):
        """Start the handler and Flask server"""
        # Use the orchestrator agent to start the server
        self.orchestrator.start_flask_server(port=5000)

    def stop(self):
        """Stop the handler and clean up resources"""
        # Stop the Flask server through the orchestrator
        self.orchestrator.stop_flask_server()
        
        # Clean up other resources
        self.dev_env.cleanup()
        
    @property
    def orchestrator_agent(self):
        """Get the orchestrator agent for this handler"""
        return self.orchestrator

# Lazy initialization to avoid circular imports
handler = None

def get_handler():
    """Get the code execution handler instance, creating it if needed."""
    global handler
    if handler is None:
        handler = CodeExecutionHandler()
    return handler

if __name__ == "__main__":
    get_handler().start()