#!/usr/bin/env python3
"""
Handler Template with Agent Integration Support

This template includes the necessary imports and structure for handlers to support
specialized agent integration with the orchestrator and bidirectional communication
with the BoardRoom system.

INSTRUCTIONS FOR HANDLER CREATORS:
---------------------------------
1. Use this template as a starting point for creating new handlers
2. Add descriptive docstrings to the handler class and all methods
3. Implement comprehensive get_info() method that returns all capabilities
4. Ensure all methods have type hints and detailed documentation
5. Include examples in docstrings where appropriate
6. Implement receive_message_from_boardroom method to enable bidirectional communication
"""

import os
import sys
import json
import time
import asyncio
import logging
import traceback
from typing import Dict, List, Any, Optional, Union

# Ensure Handler base can be imported
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from Handler.handler_base import BaseHandler, HandlerResult

# Import agent-related components for specialized agent integration
try:
    from Jarvis_Agent_SDK.jarvis_orchestrator import analyze_handler_capabilities
    from Handler.handler_agent_builder import AgentBuilder, AgentType, AgentSpecialization, AgentCapability, AgentTool
    from Jarvis_Agent_SDK.boardroom_connector import track_journey_step_sync
except ImportError:
    # Allow the handler to function even if agent components can't be imported
    print("Warning: Agent components not available - specialized agent features disabled")

class HandlerTemplate(BaseHandler):
    """Template for creating handlers with agent integration support and BoardRoom communication"""
    
    def __init__(self):
        super().__init__()
        self.handler_name = "template"
        self.system_name = "TemplateHandlerSystem"  # For orchestrator agent identification
        self.logger = logging.getLogger(__name__)
        
        # Initialize boardroom connectivity
        try:
            from Jarvis_Agent_SDK.boardroom_connector import get_boardroom
            self.boardroom = get_boardroom()
            if self.boardroom:
                self.logger.info(f"Successfully connected to BoardRoom from {self.handler_name}")
        except ImportError:
            self.boardroom = None
            self.logger.warning(f"BoardRoom connectivity not available for {self.handler_name}")
        
        # Initialize orchestrator agent - add this if your handler needs an orchestrator agent
        try:
            from YourHandlerOrchestratorAgentClass import YourHandlerOrchestratorAgent
            self.orchestrator = YourHandlerOrchestratorAgent(system_name=self.system_name)
            self.orchestrator.handler = self  # Link back to this handler instance
            self.logger.info(f"Initialized orchestrator agent for {self.handler_name}")
        except ImportError:
            self.orchestrator = None
            self.logger.warning(f"Orchestrator agent not available for {self.handler_name}")
            
        # Additional initialization here
        
    def get_info(self) -> Dict[str, Any]:
        """
        Get information about this handler's capabilities.
        
        Returns:
            Dict[str, Any]: Dictionary containing handler information including:
                - name: Handler name
                - description: Handler description
                - version: Handler version
                - author: Handler author
                - actions: List of actions supported by this handler
        """
        return {
            "name": self.handler_name,
            "description": "Template handler with agent integration support",
            "version": "1.0.0",
            "author": "Your Name",
            "actions": [
                {
                    "name": "example_action",
                    "description": "Example action for demonstration purposes",
                    "parameters": [
                        {
                            "name": "param1",
                            "type": "string",
                            "description": "Example parameter",
                            "required": True
                        },
                        {
                            "name": "param2",
                            "type": "integer",
                            "description": "Another example parameter",
                            "required": False
                        }
                    ]
                }
                # Add more actions here
            ]
        }
        
    def execute(self, action: str, parameters: Dict[str, Any]) -> HandlerResult:
        """
        Execute an action with the specified parameters.
        
        Args:
            action: Name of the action to execute
            parameters: Parameters for the action
            
        Returns:
            HandlerResult: Result of the action execution
        """
        # Implement action routing logic here
        if action == "example_action":
            return self.example_action(parameters)
        else:
            return HandlerResult(
                success=False,
                error=f"Action '{action}' not supported by {self.handler_name}"
            )
    
    def example_action(self, parameters: Dict[str, Any]) -> HandlerResult:
        """
        Example action implementation.
        
        Args:
            parameters: Dictionary of parameters including:
                - param1 (str): Example parameter
                - param2 (int, optional): Another example parameter
                
        Returns:
            HandlerResult: Result of the action execution
            
        Example:
            handler.execute("example_action", {
                "param1": "example value", 
                "param2": 42
            })
        """
        try:
            # Validate required parameters
            if "param1" not in parameters:
                return HandlerResult(
                    success=False,
                    error="Missing required parameter 'param1'"
                )
                
            # Implement action logic here
            param1 = parameters["param1"]
            param2 = parameters.get("param2", 0)  # Default value if not provided
            
            # Return successful result
            return HandlerResult(
                success=True,
                data={
                    "message": f"Successfully executed example_action with param1={param1} and param2={param2}"
                }
            )
            
        except Exception as e:
            # Handle any exceptions and return an error result
            return HandlerResult(
                success=False,
                error=f"Error executing example_action: {str(e)}"
            )
            
    async def receive_message_from_boardroom(self, message: str, context: Optional[Dict[str, Any]] = None, 
                                         message_type: str = "query") -> Dict[str, Any]:
        """
        Process a message received from the BoardRoom via the orchestrator bridge.
        
        This method enables bidirectional communication with the BoardRoom,
        allowing it to directly query this handler's orchestrator agent for 
        capabilities, status, and handler-specific information to enhance planning context.
        
        Args:
            message: The message content from BoardRoom
            context: Additional context for the message
            message_type: Type of message (query, instruction, etc.)
            
        Returns:
            Dict: Response to the message
        """
        # Generate journey ID for tracking
        journey_id = f"boardroom_to_{self.handler_name}_{int(time.time())}_{hash(str(message))}"
        
        # Initialize context if needed
        if context is None:
            context = {}
            
        # Add message source information
        context["message_from_boardroom"] = message
        context["source"] = "boardroom_orchestrator_bridge"
        
        # Ensure message is properly truncated for the description
        message_preview = message[:100] + "..." if len(message) > 100 else message
        
        # Track the incoming message if tracking is available
        try:
            # Use track_journey_step_sync if available
            if 'track_journey_step_sync' in globals():
                track_journey_step_sync(
                    journey_id=journey_id,
                    step_name="incoming_boardroom_message",
                    description=f"Received message from BoardRoom: {message_preview}",
                    step_type="inbound_communication",
                    input_data={
                        "message": message,
                        "message_type": message_type,
                        "context": context
                    },
                    output_data={}
                )
            else:
                self.logger.info(f"Received message from BoardRoom: {message_preview}")
        except Exception as e:
            self.logger.warning(f"Error tracking message from BoardRoom: {str(e)}")
        
        try:
            # Process the message based on type and context
            response = None
            
            # Check for query_type in context for specialized handling
            query_type = context.get("query_type")
            
            if query_type == "capabilities":
                # Return capabilities of this handler
                handler_info = self.get_info()
                response = {
                    "success": True,
                    "capabilities": handler_info.get("actions", []),
                    "handler_name": self.handler_name,
                    "system_name": self.system_name,
                    "description": handler_info.get("description", "Handler template")
                }
                
            elif query_type == "status":
                # Return current status of this handler
                response = {
                    "success": True,
                    "status": "active",  # Or determine status dynamically
                    "handler_name": self.handler_name,
                    "system_name": self.system_name
                }
                
            elif query_type == "module_info":
                # Return information about this handler
                handler_info = self.get_info()
                response = {
                    "success": True,
                    "module_name": context.get("module_name", self.handler_name),
                    "description": handler_info.get("description", "Handler template"),
                    "version": handler_info.get("version", "1.0.0"),
                    "author": handler_info.get("author", "Unknown"),
                    "capabilities": [
                        action.get("description", "Unknown action") 
                        for action in handler_info.get("actions", [])
                    ]
                }
                    
            else:
                # Default handling for other message types
                response = {
                    "success": True,
                    "status": "received",
                    "message": f"Message of type {message_type} received from BoardRoom",
                    "handler_name": self.handler_name,
                    "system_name": self.system_name,
                    "journey_id": journey_id,
                    "timestamp": time.time()
                }
            
            # Track the response if tracking is available
            try:
                if 'track_journey_step_sync' in globals():
                    track_journey_step_sync(
                        journey_id=journey_id,
                        step_name="boardroom_response_sent",
                        description=f"Sending response to BoardRoom",
                        step_type="outbound_communication",
                        input_data={},
                        output_data=response
                    )
                else:
                    self.logger.info(f"Sending response to BoardRoom: {str(response)[:100]}...")
            except Exception as e:
                self.logger.warning(f"Error tracking response to BoardRoom: {str(e)}")
            
            return response
            
        except Exception as e:
            error_msg = f"Error processing message from BoardRoom: {str(e)}"
            self.logger.error(error_msg)
            self.logger.debug(traceback.format_exc())
            
            # Track the error if tracking is available
            try:
                if 'track_journey_step_sync' in globals():
                    track_journey_step_sync(
                        journey_id=journey_id,
                        step_name="boardroom_processing_error",
                        description=error_msg,
                        step_type="error",
                        input_data={},
                        output_data={
                            "error": error_msg,
                            "traceback": traceback.format_exc()
                        }
                    )
            except Exception as track_err:
                self.logger.warning(f"Error tracking BoardRoom processing error: {str(track_err)}")
            
            return {
                "success": False,
                "status": "error",
                "message": error_msg,
                "handler_name": self.handler_name,
                "system_name": self.system_name,
                "journey_id": journey_id,
                "timestamp": time.time()
            }