"""
Jarvis Orchestrator - Comprehensive Version

This module provides a unified orchestration layer using the OpenAI Agents SDK.
It connects to all existing agent systems without modifying them:
- Handler agents (including BoardRoom and Swarm)
- Structured Agent System
- Structured Outputs Multi-Agent
- Code Analysis and Optimization Tools

The orchestrator intelligently routes tasks to the appropriate system based on the query.
"""

import os
import sys
import re
import json
import uuid
import hashlib
import sqlite3
import traceback
import asyncio
import inspect
import importlib
import importlib.util
import threading
import concurrent.futures
import time
from typing import Dict, List, Any, Optional, Awaitable, Union, Callable, Tuple
from datetime import datetime, timedelta
import logging
import subprocess
import time
import ast
from functools import wraps
from pathlib import Path
import base64

from Database.v2.db_helper import connection as v2_connection, DB_PATHS as _V2_PATHS

import openai
from openai import AsyncOpenAI

# Import direct from boardroom_connector to avoid circular imports
try:
    from .boardroom_connector import (
        get_boardroom,
        register_boardroom,
        track_request_journey,
        track_journey_step,
        track_journey_step_sync,
        update_journey_state,
        complete_journey,
        request_feedback,
        process_feedback
    )
except ImportError:
    # Fallback for direct execution - use absolute import
    from boardroom_connector import (
        get_boardroom,
        register_boardroom,
        track_request_journey,
        track_journey_step,
        track_journey_step_sync,
        update_journey_state,
        complete_journey,
        request_feedback,
        process_feedback
    )

# MCP decorators were removed - using official SDK now

# Global singleton instance
_ORCHESTRATOR_INSTANCE = None
_ORCHESTRATOR_LOCK = threading.RLock()

# Workspace sharing for MCP integration imported below with other import_helper functions

# Orchestrator Agent System Prompt - Provides detailed guidance for the orchestrator agent
ORCHESTRATOR_SYSTEM_PROMPT = """
You are Jarvis, an advanced AI orchestrator agent that coordinates various handlers and tools to assist users.

SYSTEM ARCHITECTURE:
1. Trevor Core: 
   - Front-end audio processing system that handles speech-to-text via Whisper models
   - Contains built-in neural network model for intent classification
   - Performs task complexity analysis to determine routing
   - Has direct bidirectional communication with you (Jarvis Orchestrator)
   - Maintains conversation context across interactions
   - Handles simple tasks directly when appropriate

2. Jarvis Orchestrator (you):
   - Acts as the "brain" for Trevor Core's operations
   - Uses pre-trained tokenized model with 98.03% accuracy for classification
   - Leverages semantic relationship data from docstrings
   - Maintains learning systems for improving handler selection
   - Routes complex tasks to specialized systems (Boardroom, agents, etc.)

3. BoardRoom:
   - Sophisticated multi-agent collaboration framework
   - Manages conversations between Claude and GPT models
   - Conducts complex reasoning and strategic planning
   - Produces execution plans for the orchestrator to implement
   - Includes journey tracking and analytics capabilities
 
4. Handler Systems:
   - Specialized modules for specific domains (email, browser, terminal, etc.)
   - Each handler exposes domain-specific actions and capabilities
   - Some handlers have dedicated specialized agents with expertise

5. Agent Systems:
   - Agent Builder: Creates specialized AI agents for specific tasks
   - Structured Agent System: Schema-enforced multi-agent framework
   - Handler Swarm: Collaborative agent network for complex operations
   - Data Validator: Ensures data quality and schema compliance

CAPABILITIES:
1. You have access to various application handlers including: email, browser, calendar, terminal, finder, calculator, and more.
2. You can execute direct commands through these handlers or use the Boardroom system for complex tasks.
3. You can process terminal commands, search files, execute scripts, and perform system operations.
4. You can maintain conversation history and track objects across sessions for continuity.
5. You have access to specialized agents for each handler that can provide expert-level assistance in their domain.
6. You work with Trevor Core for audio processing, intent classification, and complexity analysis.
7. You integrate with BoardRoom for complex reasoning using multi-agent collaboration.

TREVOR CORE INTEGRATION:
1. Bidirectional Communication:
   - Trevor Core sends you task requests after processing user voice input
   - Trevor Core decides whether to route requests to BoardRoom based on complexity analysis
   - You execute tasks and plans based on Trevor Core's routing decisions
   - Results are sent back to Trevor Core for response to the user

2. Complexity Analysis and Routing Flow:
   - Trevor Core performs task complexity analysis (analyze_task_complexity method)
   - Trevor Core routes complex tasks directly to BoardRoom
   - Trevor Core may route simpler tasks to you for direct handler execution
   - Trevor Core also uses BoardRoom as a fallback when other methods fail
   - You do NOT decide when to use BoardRoom - Trevor Core makes this decision

3. Your Role in the Workflow:
   - Execute plans created by BoardRoom, not decide when to use BoardRoom
   - Process requests that Trevor Core sends directly to you
   - Provide results back to Trevor Core or BoardRoom as appropriate
   - Focus on execution rather than routing decisions

4. Shared Intelligence:
   - Trevor Core and you share access to the tokenized model
   - Pattern matching and intent classification are handled by Trevor Core
   - Context is preserved between Trevor Core, BoardRoom, and you

5. Responsibilities:
   - Trevor Core: Audio processing, task complexity analysis, routing decisions
   - BoardRoom: Complex reasoning, Claude-GPT collaboration, plan creation
   - You (Orchestrator): Plan execution, handler coordination, result reporting
   - Information flows seamlessly between all three systems
   - The user experiences a single unified assistant

WORKFLOW OPTIONS:
1. Direct Handler Execution: When a user request maps clearly to a specific handler action (like opening an app or executing a terminal command), you can directly route this to the appropriate handler using execute_handler_action().
2. Boardroom Processing: For complex or ambiguous requests, you can route them through the Boardroom system which provides additional reasoning using process_with_boardroom().
3. Handler Swarm: For tasks that require coordination between multiple handlers, you can use the handler swarm approach with use_handler_swarm().
4. Specialized Agent Processing: For domain-specific tasks that benefit from expert agents, use the use_handler_specialized_agent() to leverage specialized agents for each handler.

HANDLING TERMINAL COMMANDS:
1. For terminal commands, use the terminal handler with the appropriate action:
   - "execute_command" for running shell commands
   - "search_files" for finding files
   - "search_content" for searching within files
   - "run_script" for executing scripts
2. Always capture and report the full output back to the user
3. Examine terminal responses for errors and explain them to the user

CONVERSATION HISTORY AND CONTEXT:
1. You have access to tools for retrieving conversation history:
   - get_conversation_history(): Retrieve past messages for the current session
   - query_conversation_database(): Search across conversation history
2. Use these tools when context from previous conversations is needed
3. The system automatically maintains conversation history for you
4. You should actively use this history to understand user requests in context of previous interactions
5. When a user refers to previous requests or objects created in earlier interactions, use these tools to refresh your memory

SPECIALIZED AGENT INTEGRATION:
1. Each handler has a specialized agent tailored to its specific domain.
2. Terminal Agent: Expert in executing terminal commands and file operations.
3. Email Agent: Expert in communication, email composition and management.
4. Browser Agent: Expert at web searching, navigation, and information gathering.
5. Calendar Agent: Expert at scheduling, planning, and time management.
6. Finder Agent: Expert at file management and organization.
7. Coding Agent: Expert at software development and code analysis.

BOARDROOM SYSTEM INTEGRATION:
1. The BoardRoom system is a sophisticated multi-agent framework using Claude and GPT models together:
   - Implements a turn-based conversation protocol where Claude and GPT collaborate
   - Claude speaks first with an initial analysis of the task
   - GPT responds to Claude's analysis
   - Models alternate in conversation until reaching consensus (up to 20 exchanges each)
   - The consensus leads to an execution plan specifying handlers and tools to use

2. For complex tasks requiring deep reasoning or collaborative AI thinking:
   - Delegate to the BoardRoom using process_with_boardroom(query)
   - The BoardRoom manages the collaboration between Claude and GPT models
   - The models analyze the task, discuss approaches, and reach consensus
   - BoardRoom extracts an execution plan with specific handlers and actions
   - Your responsibility is to execute the plan returned by BoardRoom

3. When to use the BoardRoom system:
   - For complex tasks requiring multi-step reasoning
   - For tasks that need to synthesize multiple information sources
   - For strategic planning or open-ended problem solving
   - For any task where a single AI model might miss important perspectives
   - When the user request is ambiguous and needs thorough analysis

4. Your role with BoardRoom:
   - Act as the executor of plans developed by the BoardRoom
   - Provide the BoardRoom with relevant context for analysis
   - Monitor and report on the execution of BoardRoom plans
   - Recognize when a task exceeds your capabilities and delegate to BoardRoom
   - Maintain awareness of ongoing BoardRoom conversations and their outcomes

5. AI Model Integration in BoardRoom:
   - Claude 3.7 Sonnet: Primary analytical model that speaks first
   - GPT-4.5 Turbo: Secondary model that responds to Claude
   - Both models have specific system prompts and roles
   - Claude tends to excel at detailed analysis and planning
   - GPT tends to excel at creative solutions and coding
   - Together they form a more capable system than either alone

6. BoardRoom's Trevor Core Integration:
   - BoardRoom can directly access Trevor Core's complexity analysis
   - It can break down complex tasks into manageable steps
   - It can create execution plans for Trevor Core to implement
   - This creates a seamless workflow between all systems

AGENT SYSTEM COMPONENTS:
1. Agent Builder (handler_agent_builder.py):
   - Creates specialized AI agents with customizable capabilities
   - Supports multiple agent types: Specialist, Generalist, Coordinator, etc.
   - Configures agent specialization with domain expertise levels
   - Uses type-safe creation through enumerations (AgentType, AgentCapability)
   - Integrates specialized tools for different agent capabilities

2. Swarm Handler (handler_swarm.py):
   - Manages collaborative multi-agent system for complex problems
   - Handles agent registration and lifecycle management
   - Coordinates multi-agent conversation routing
   - Tracks team performance and optimizes workload balance
   - Supports agent handoff between specialists

3. Data Validator (handler_data_validator.py):
   - Provides comprehensive data validation
   - Validates against JSON schemas and business rules
   - Checks pattern matching for various data types
   - Performs statistical validation and time series analysis
   - Uses AI-powered reasoning for complex validations

4. Structured Outputs Multi-Agent:
   - Enforces strict schema validation using OpenAI's strict mode
   - Deploys specialized agents for triaging, processing, and analysis
   - Provides data cleaning, transformation, and aggregation
   - Supports statistical analysis with visualization capabilities
   - Ensures type safety and required field validation

5. Structured Agent System:
   - Implements hierarchical task coordination
   - Creates dynamic agent teams with domain specialization
   - Assigns role-based responsibilities (Coordinator, Analyst, etc.)
   - Ensures schema enforcement and type safety
   - Handles asynchronous tasks with priority-based routing

WHEN TO USE SPECIALIZED AGENTS:
1. Use specialized agents for complex domain-specific tasks requiring expertise.
2. Use the terminal agent for detailed file operations, complex commands, or when explaining terminal output.
3. Use the email agent for crafting professional emails or managing complex communications.
4. Use browser agents for detailed web research or information synthesis.

DETAILED EXECUTION PATHS:
1. For direct handler execution:
   - Identify the handler name (e.g., "terminal", "browser", "email")
   - Determine the specific action to perform
   - Prepare any necessary parameters
   - Call execute_handler_action(handler, action, parameters)
   - Capture the result and report it to the user

2. For specialized agent processing:
   - Identify the appropriate handler domain
   - Call use_handler_specialized_agent(handler_name, task)
   - The specialized agent will suggest and execute the best action
   - Report both the agent's reasoning and result to the user

3. For boardroom processing:
   - Use process_with_boardroom(query) for complex reasoning
   - The BoardRoom will manage Claude-GPT collaboration to analyze the task
   - Execute the resulting plan returned by BoardRoom
   - Report both the reasoning from BoardRoom and the execution results to the user

4. For handler swarm:
   - Define the objective and subtasks
   - Call use_handler_swarm(objective, handlers) 
   - Report the coordinated result to the user

5. For Trevor Core integration:
   - Respect task complexity analysis from Trevor Core
   - Execute the appropriate handler based on intent classification
   - Send results back through Trevor Core's response pipeline
   - Maintain shared context between systems

IMPORTANT BEHAVIOR REQUIREMENTS:
1. Always monitor and report outcomes of actions to the user - whether success or failure.
2. When handling terminal commands or system operations, explain what you're doing and report results.
3. Maintain context and continuity across conversations by using the session tracking system.
4. For errors, provide detailed information and suggest potential solutions when possible.
5. Provide detailed logging information when operations fail to help the user understand what went wrong.
6. Never silently fail - always capture outcomes and report them.
7. Actively use conversation history to understand requests in context and remember previous user interactions.

When deciding which workflow to use:
- For simple, clear requests like "open Safari" or "ls -la" - use direct handler execution
- For requests where domain expertise is helpful, like complex terminal operations - use specialized agents
- For complex requests requiring reasoning like "help me plan my day" - use Boardroom
- For multi-step tasks across different domains - consider using the handler swarm
- When context from previous conversations is needed - use history retrieval tools

IMPORTANT: Always respond to users with:
1. What action you're taking
2. Which handler/system/agent you're using
3. The outcome of the operation (success or detailed error)
4. Any relevant output or results
"""

def load_orchestrator_prompt_from_json() -> str:
    """
    Load the orchestrator system prompt from the JSON prompt registry.
    Falls back to hardcoded prompt if JSON file is not found or invalid.
    
    Returns:
        The system prompt content from JSON or fallback hardcoded prompt
    """
    try:
        # Path to the MCP enhanced JSON prompt
        json_prompt_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "Prompts", "orchestrator", "jarvis_orchestrator_agent_mcp_enhanced.json"
        )
        
        if os.path.exists(json_prompt_path):
            with open(json_prompt_path, 'r', encoding='utf-8') as f:
                prompt_data = json.load(f)
                content = prompt_data.get('content', '')
                if content:
                    logging.info("Successfully loaded orchestrator prompt from JSON registry")
                    return content
                else:
                    logging.warning("JSON prompt file exists but content is empty, using hardcoded fallback")
        else:
            logging.warning(f"JSON prompt file not found at {json_prompt_path}, using hardcoded fallback")
            
    except Exception as e:
        logging.error(f"Error loading orchestrator prompt from JSON: {str(e)}")
        logging.error(f"Falling back to hardcoded prompt")
    
    # Fallback to hardcoded prompt
    return ORCHESTRATOR_SYSTEM_PROMPT

# Import workspace reference cache
try:
    from .workspace_reference_cache import get_workspace_reference_cache
except ImportError:
    # Fallback for direct execution
    from workspace_reference_cache import get_workspace_reference_cache

# Import task registry for task status tracking and journey management

async def generate_orchestrator_instructions() -> str:
    """
    Generate instructions for the orchestrator agent.
    Loads from JSON prompt registry with fallback to hardcoded prompt.
    
    Returns:
        Comprehensive instructions for the orchestrator agent
    """
    try:
        # Load from JSON prompt registry with fallback to hardcoded
        return load_orchestrator_prompt_from_json()
    except Exception as e:
        logging.error(f"Error generating orchestrator instructions: {str(e)}")
        logging.error(traceback.format_exc())
        return "You are Jarvis, an AI assistant that connects to various systems."

def generate_orchestrator_instructions_sync() -> str:
    """
    Synchronous version of generate_orchestrator_instructions.
    Loads from JSON prompt registry with fallback to hardcoded prompt.
    
    Returns:
        Comprehensive instructions for the orchestrator agent
    """
    try:
        # Load from JSON prompt registry with fallback to hardcoded
        return load_orchestrator_prompt_from_json()
    except Exception as e:
        logging.error(f"Error generating orchestrator instructions: {str(e)}")
        logging.error(traceback.format_exc())
        return "You are Jarvis, an AI assistant that connects to various systems."
try:
    from .task_status_registry import get_task_registry, TaskStatus
except ImportError:
    # Fallback for direct execution
    from task_status_registry import get_task_registry, TaskStatus

# Import orchestrator registry for agent registration
try:
    from .orchestrator_registry import register_orchestrator_agent
except ImportError:
    # Fallback for direct execution
    from orchestrator_registry import register_orchestrator_agent

# Import common utilities for tracking and analysis
try:
    from .common_utils import (
        analyze_handler_capabilities
    )
except ImportError:
    # Fallback for direct execution
    from common_utils import (
        analyze_handler_capabilities
    )

# Import helper functions for safe imports
try:
    from .import_helper import (
        get_handler_all,
        get_agent_builder,
        get_analyze_task_capabilities,
        get_execute_handler_action,
        get_execute_handler_action_async,
        get_workspace_sharing,
        get_handler_system,
        get_agent_loader,
        _safe_import,
        generate_request_id
    )
except ImportError:
    # Fallback for direct execution
    from import_helper import (
        get_handler_all,
        get_agent_builder,
        get_analyze_task_capabilities,
        get_execute_handler_action,
        get_execute_handler_action_async,
        get_workspace_sharing,
        get_handler_system,
        get_agent_loader,
        _safe_import,
        generate_request_id
    )

# MCP wrapper removed - using official SDK direct import approach now

# Import from orchestrator_intelligence
try:
    from .orchestrator_intelligence import (
        OrchestratorIntelligence,
        init_orchestrator_intelligence
    )
except ImportError:
    # Fallback for direct execution
    from orchestrator_intelligence import (
        OrchestratorIntelligence,
        init_orchestrator_intelligence
    )

# Import from Handler.agents module for OpenAI key management
try:
    from Handler.agents import set_default_openai_key, function_tool
except ImportError:
    # Fallback implementation if not available
    def set_default_openai_key(key):
        """Fallback implementation of set_default_openai_key"""
        openai.api_key = key
        logging.info("Set OpenAI API key using fallback implementation")
    
    # Fallback implementation of function_tool decorator
    def function_tool(func):
        """Fallback implementation of the function_tool decorator"""
        @wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)
        wrapper.is_tool = True
        wrapper.tool_schema = getattr(func, "tool_schema", {})
        return wrapper

# Get handler components through import_helper
handler_all = get_handler_all()
if handler_all:
    execute_handler = handler_all.execute_handler
    # For simplicity, just set handler_system to None for now and access directly when needed
    handler_system = None  
    # Remove references to other handler_all attributes that might not exist in our stub
    # These will be directly imported when needed

# Use boardroom_connector directly for tracking functionality
# This eliminates circular dependencies and centralizes BoardRoom access
try:
    from Jarvis_Agent_SDK.boardroom_connector import (
        track_request_journey as track_request_journey_interface,
        track_journey_step as track_journey_step_interface,
        track_journey_step_async as track_journey_step_async_interface,
        update_journey_state as update_journey_state_interface,
        complete_journey as complete_journey_interface
    )
    logging.info("Successfully imported tracking functions from boardroom_connector")
except ImportError as e:
    logging.warning(f"Could not import tracking functions from boardroom_connector: {e}")
    # Provide minimal tracking interfaces that just log
    def track_request_journey_interface(request_id, task, system_id="default", journey_type="default"):
        logging.info(f"Journey tracking: {request_id} - {task}")
        return request_id
    
    def track_journey_step_interface(journey_id, step_name, description=None, **kwargs):
        logging.info(f"Step tracking: {journey_id} - {step_name}")
        return True
        
    track_journey_step_async_interface = track_journey_step_interface
    
    def update_journey_state_interface(journey_id, state, metadata=None):
        logging.info(f"State update: {journey_id} - {state}")
        return True
        
    def complete_journey_interface(journey_id, status="completed", metadata=None):
        logging.info(f"Journey completed: {journey_id} - {status}")
        return True

# Add project root to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import config utilities safely
config_module = _safe_import("Core.config")
load_api_key = getattr(config_module, "load_api_key", None) if config_module else None

if not load_api_key:
    def load_api_key(key_name):
        """Fallback implementation of load_api_key"""
        logging.warning(f"Using fallback load_api_key implementation for {key_name}")
        return os.environ.get(f"{key_name}_API_KEY")

# Import handler adapter tools safely
jarvis_hybrid_adapter = _safe_import("Jarvis_Agent_SDK.jarvis_hybrid_agents.handler_adapter")
if jarvis_hybrid_adapter:
    process_with_boardroom = getattr(jarvis_hybrid_adapter, "process_with_boardroom", None)
    use_handler_agent = getattr(jarvis_hybrid_adapter, "use_handler_agent", None)
    use_handler_swarm = getattr(jarvis_hybrid_adapter, "use_handler_swarm", None)
    print(f"✅ Imported process_with_boardroom: {type(process_with_boardroom)}")
else:
    # Ensure these variables are always defined even if import fails
    process_with_boardroom = None
    use_handler_agent = None  
    use_handler_swarm = None
    print("❌ jarvis_hybrid_adapter import failed - process_with_boardroom set to None")

# Import bridge tools safely
bridge_tools = _safe_import("Jarvis_Agent_SDK.jarvis_hybrid_agents.bridge_tools")
if bridge_tools:
    invoke_structured_agent_system = getattr(bridge_tools, "invoke_structured_agent_system", None)
    invoke_structured_outputs_system = getattr(bridge_tools, "invoke_structured_outputs_system", None)
    read_file = getattr(bridge_tools, "read_file", None)
    search_codebase = getattr(bridge_tools, "search_codebase", None)
    analyze_architecture = getattr(bridge_tools, "analyze_architecture", None)

# Import code tools safely
code_tools = _safe_import("Jarvis_Agent_SDK.jarvis_sdk_agents.tools")
if code_tools:
    execute_code = getattr(code_tools, "execute_code", None)
    review_code = getattr(code_tools, "review_code", None)
    optimize_code = getattr(code_tools, "optimize_code", None)

# Global variables for module-level agents and systems
# The orchestrator_agent will be created on first use or reset
orchestrator_agent = None

# Cached BoardRoom instance
_boardroom_instance = None

def get_boardroom_instance():
    """
    Get the BoardRoom instance directly from the boardroom_connector.
    
    Returns:
        The BoardRoom instance or None if it cannot be initialized
    """
    global _boardroom_instance
    
    if _boardroom_instance is not None:
        return _boardroom_instance
    
    try:
        # Get BoardRoom directly from the connector
        _boardroom_instance = get_boardroom()
        if _boardroom_instance:
            logging.info("Successfully got BoardRoom instance from boardroom_connector")
            return _boardroom_instance
            
    except Exception as e:
        logging.error(f"Error getting BoardRoom: {str(e)}")
        return None
        
    return None

# Patch for OpenAI schema validation
def patch_openai_schemas():
    """
    Apply patches to function_tool schemas to ensure compatibility with OpenAI API validation.
    This function should be called after all function_tools are defined.
    """
    try:
        import requests
        
        # Get global variables
        global_vars = globals()
        
        # Get the OpenAI API key for direct validation
        openai_api_key = load_api_key('OPENAI')
        
        print("Starting schema validation and patching process...")
        
        # Direct validation with OpenAI API function
        def validate_schema_with_openai_api(schema):
            """
            Directly validate a schema with the OpenAI API
            
            Args:
                schema: The schema to validate
                
            Returns:
                tuple: (is_valid, error_message)
            """
            # Create a minimal request with just this tool
            request_body = {
                "model": "gpt-4-turbo",
                "messages": [{"role": "user", "content": "Test"}],
                "tools": [
                    {
                        "type": "function",
                        "function": schema
                    }
                ]
            }
            
            # Test the schema directly against the API
            try:
                response = requests.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {openai_api_key}",
                        "Content-Type": "application/json"
                    },
                    json=request_body,
                    timeout=10
                )
                
                if response.status_code == 200:
                    return True, None
                else:
                    error_data = response.json()
                    error_message = error_data.get('error', {}).get('message', 'Unknown error')
                    return False, error_message
            except Exception as e:
                return False, str(e)
        
        # First handle the execute_handler_sequence function which has been causing issues
        sequence_func = global_vars.get('execute_handler_sequence')
        if sequence_func and hasattr(sequence_func, '_tool_schema'):
            sequence_schema = sequence_func._tool_schema
            
            print(f"Testing schema for execute_handler_sequence...")
            is_valid, error = validate_schema_with_openai_api(sequence_schema)
            
            if not is_valid:
                print(f"Schema for execute_handler_sequence is invalid: {error}")
                
                # Create a known-valid schema for execute_handler_sequence
                print("Creating corrected schema for execute_handler_sequence")
                valid_schema = {
                    "name": "execute_handler_sequence",
                    "description": "Execute a sequence of handler requests in order.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "requests_json": {
                                "type": "string",
                                "description": "JSON string containing an array of handler requests to execute"
                            }
                        },
                        "required": ["requests_json"]
                    }
                }
                
                # Test if the new schema is valid
                is_valid, error = validate_schema_with_openai_api(valid_schema)
                if is_valid:
                    print("Corrected schema for execute_handler_sequence is valid!")
                    sequence_func._tool_schema = valid_schema
                else:
                    print(f"Corrected schema is still invalid: {error}")
        
        # Process all other function_tool decorated functions
        for name, func in global_vars.items():
            if name == 'execute_handler_sequence' or not callable(func) or not hasattr(func, '_tool_schema'):
                continue
                
            schema = func._tool_schema
            print(f"Testing schema for {name}...")
            is_valid, error = validate_schema_with_openai_api(schema)
            
            if not is_valid:
                print(f"Schema for {name} is invalid: {error}")
                
                # Apply fixes based on the specific error
                if 'parameters' in schema and 'properties' in schema['parameters']:
                    properties = schema['parameters']['properties']
                    
                    # Fix 1: Ensure required only contains properties that exist
                    if 'required' in schema['parameters']:
                        valid_property_names = list(properties.keys())
                        schema['parameters']['required'] = [
                            prop for prop in schema['parameters']['required'] 
                            if prop in valid_property_names
                        ]
                    
                    # Fix 2: Add items to array properties
                    for prop_name, prop_schema in properties.items():
                        if prop_schema.get('type') == 'array' and 'items' not in prop_schema:
                            # Default to string items which is simplest
                            prop_schema['items'] = {"type": "string"}
                
                # Test if the fixed schema is valid
                is_valid, error = validate_schema_with_openai_api(schema)
                if is_valid:
                    print(f"Corrected schema for {name} is now valid!")
                    func._tool_schema = schema
                else:
                    print(f"Corrected schema for {name} is still invalid: {error}")
                    
                    # Make more radical changes if needed
                    if 'parameters' in schema and 'properties' in schema['parameters']:
                        properties = schema['parameters']['properties']
                        
                        # Make required empty if still having issues
                        schema['parameters']['required'] = []
                        
                        # Test again
                        is_valid, error = validate_schema_with_openai_api(schema)
                        if is_valid:
                            print(f"Schema for {name} is now valid with empty required array")
                            func._tool_schema = schema
                        else:
                            print(f"Schema for {name} still invalid after empty required: {error}")
            else:
                print(f"Schema for {name} is already valid!")
                
        print("Schema validation and patching complete.")
        
    except Exception as e:
        print(f"Error in patch_openai_schemas: {str(e)}")
        traceback.print_exc()

# Add project root to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import from Core for API key
from Core.config import load_api_key

# Import adapter functions
from Jarvis_Agent_SDK.jarvis_hybrid_agents.handler_adapter import (
    process_with_boardroom,
    use_handler_agent,
    use_handler_swarm
)

# Import handler base for HandlerResult
from Handler.handler_base import HandlerResult

# Import handler_all for unified handler execution - moved to functions to avoid circular import

# Import handler execution tracking for better monitoring
from Jarvis_Agent_SDK.handler_execution_tracking import execute_any_handler_async

# Import bridge functions for structured systems
from Jarvis_Agent_SDK.jarvis_hybrid_agents.bridge_tools import (
    invoke_structured_agent_system,
    invoke_structured_outputs_system,
    read_file,
    search_codebase,
    analyze_architecture
)

# Import code tools
from Jarvis_Agent_SDK.jarvis_sdk_agents.tools import (
    execute_code,
    review_code,
    optimize_code
)

# Set the OpenAI API key
api_key = load_api_key('OPENAI')
set_default_openai_key(api_key)

# Conversation History Manager for context persistence
class ConversationHistoryManager:
    """
    Manager for persisting and retrieving conversation history, session metadata, and object tracking.
    """
    
    def __init__(self, db_path=None):
        """
        Initialize the ConversationHistoryManager with a connection to the V2 conversations database.

        Args:
            db_path: Ignored (kept for API compat). Always uses V2 conversations DB.
        """
        self.db_path = _V2_PATHS["conversations"]
        self.initialize_database()

    def initialize_database(self):
        """Initialize the database with required tables if they don't exist."""
        with v2_connection("conversations") as conn:
            conn.execute('''
            CREATE TABLE IF NOT EXISTS sessions (
                session_id TEXT PRIMARY KEY,
                user_id TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                metadata TEXT
            )
            ''')
            conn.execute('''
            CREATE TABLE IF NOT EXISTS messages (
                message_id TEXT PRIMARY KEY,
                session_id TEXT,
                role TEXT,
                content TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                metadata TEXT,
                FOREIGN KEY (session_id) REFERENCES sessions(session_id)
            )
            ''')
            conn.execute('''
            CREATE TABLE IF NOT EXISTS session_objects (
                object_id TEXT PRIMARY KEY,
                session_id TEXT,
                object_name TEXT,
                object_type TEXT,
                app_name TEXT,
                status TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                metadata TEXT,
                FOREIGN KEY (session_id) REFERENCES sessions(session_id)
            )
            ''')

    def _get_connection(self):
        """Get a connection to the V2 conversations database.

        Returns a bare connection (not a context manager) for backward
        compatibility with existing callers that call conn.close().
        """
        from Database.v2.db_helper import get_connection
        return get_connection("conversations")
        
    def create_session(self, user_id, metadata=None):
        """
        Create a new conversation session.
        
        Args:
            user_id: Identifier for the user
            metadata: Optional metadata to store with the session
            
        Returns:
            The session_id of the created session
        """
        session_id = str(uuid.uuid4())
        
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            metadata_json = json.dumps(metadata or {})
            
            cursor.execute(
                "INSERT INTO sessions (session_id, user_id, metadata) VALUES (?, ?, ?)",
                (session_id, user_id, metadata_json)
            )
            
            conn.commit()
            conn.close()
            
            print(f"[HISTORY] Created new session: {session_id}")
            return session_id
            
        except Exception as e:
            print(f"[HISTORY] Error creating session: {str(e)}")
            return session_id  # Return the generated ID even if we failed to save it
    
    def add_message(self, session_id: str, role: str, content: str, metadata: dict = None, message_id: str = None) -> bool:
        """
        Add a message to a conversation session.
        
        Args:
            session_id: The session ID
            role: Message role (e.g., "user", "assistant", "system")
            content: The message content
            metadata: Optional metadata about the message
            message_id: Optional message ID (will be generated if not provided)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # Generate a message ID if not provided
            if message_id is None:
                # Use microsecond precision in timestamp for better uniqueness
                timestamp_ms = int(time.time() * 1000)
                message_id = f"{role}_{timestamp_ms}_{uuid.uuid4().hex[:8]}"
            
            # Check if message ID already exists
            cursor.execute("SELECT 1 FROM messages WHERE message_id = ? LIMIT 1", (message_id,))
            if cursor.fetchone():
                # If it exists, generate a new truly unique ID
                logging.warning(f"[HISTORY] Message ID {message_id} already exists, generating new unique ID")
                message_id = f"{role}_{int(time.time() * 1000000)}_{uuid.uuid4().hex}"
            
            try:
                cursor.execute("""
                    INSERT INTO messages (message_id, conversation_id, role, content, metadata, timestamp)
                    VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                """, (message_id, session_id, role, content, json.dumps(metadata or {})))
            except sqlite3.IntegrityError as e:
                logging.error(f"[HISTORY] Error adding message: {e}")
                return False
            
            # Update session's updated_at timestamp
            cursor.execute("UPDATE sessions SET updated_at = ? WHERE session_id = ?", 
                         (time.time(), session_id))
            
            conn.commit()
            conn.close()
            
            print(f"[HISTORY] Added {role} message to session {session_id}")
            return True
        except Exception as e:
            print(f"[HISTORY] Error adding message: {e}")
            traceback.print_exc()
            return False
    
    def get_session_history(self, session_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get the message history for a session.
    
    Args:
            session_id: The session identifier
            limit: Maximum number of messages to retrieve (most recent first)
        
    Returns:
            List of message dictionaries (role, content, timestamp, metadata)
        """
        try:
            # Check if we have this session cached in memory
            if session_id in self.session_histories:
                return self.session_histories[session_id][-limit:]
                
            conn = self._get_connection()
            if not conn:
                print("Failed to connect to database, returning empty history")
                return []
                
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT role, content, timestamp, metadata
                FROM messages
                WHERE session_id = ?
                ORDER BY timestamp DESC
                LIMIT ?
            """, (session_id, limit))
            
            messages = []
            for row in cursor.fetchall():
                messages.append({
                    "role": row["role"],
                    "content": row["content"],
                    "timestamp": row["timestamp"],
                    "metadata": json.loads(row["metadata"]) if row["metadata"] else {}
                })
            
            # Reverse to get chronological order (oldest first)
            messages.reverse()
            
            # Cache in memory for future requests
            self.session_histories[session_id] = messages
            
            conn.close()
            return messages
            
        except Exception as e:
            print(f"Error getting session history: {str(e)}")
            traceback.print_exc()
            return []
    
    def format_history_for_context(self, session_id: str, limit: int = 5) -> str:
        """
        Format the session history as a string for context inclusion.
    
    Args:
            session_id: The session identifier
            limit: Maximum number of messages to include
        
    Returns:
            Formatted history string
        """
        try:
            messages = self.get_session_history(session_id, limit)
            
            if not messages:
                return "No previous conversation history."
                
            history_str = "Previous conversation:\n\n"
            
            for msg in messages:
                role_display = "User" if msg["role"] == "user" else "Assistant"
                timestamp = msg.get("timestamp", "unknown time")
                history_str += f"{role_display} ({timestamp}): {msg['content']}\n\n"
                
            return history_str
            
        except Exception as e:
            print(f"Error formatting history: {str(e)}")
            traceback.print_exc()
            return "Error retrieving conversation history."
    
    def get_session_metadata(self, session_id: str) -> Dict[str, Any]:
        """
        Get metadata for a session.
        
        Args:
            session_id: The session identifier
            
        Returns:
            Session metadata dictionary
        """
        try:
            conn = self._get_connection()
            if not conn:
                print("Failed to connect to database, returning empty metadata")
                return {}
                
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT metadata
                FROM sessions
                WHERE session_id = ?
            """, (session_id,))
            
            row = cursor.fetchone()
            conn.close()
            
            if row and row["metadata"]:
                return json.loads(row["metadata"])
                
            return {}
            
        except Exception as e:
            print(f"Error getting session metadata: {str(e)}")
            traceback.print_exc()
            return {}
    
    def update_session_metadata(self, session_id: str, metadata: Dict[str, Any]) -> bool:
        """
        Update metadata for a session.
        
        Args:
            session_id: The session identifier
            metadata: New metadata dictionary
            
        Returns:
            True if successful, False otherwise
        """
        try:
            conn = self._get_connection()
            if not conn:
                print("Failed to connect to database, cannot update metadata")
                return False
                
            cursor = conn.cursor()
            
            # Get existing metadata
            cursor.execute("""
                SELECT metadata
                FROM sessions
                WHERE session_id = ?
            """, (session_id,))
            
            row = cursor.fetchone()
            
            if row and row["metadata"]:
                existing_metadata = json.loads(row["metadata"])
                # Merge with new metadata
                existing_metadata.update(metadata)
                metadata_json = json.dumps(existing_metadata)
            else:
                metadata_json = json.dumps(metadata)
            
            # Update the metadata
            cursor.execute("""
                UPDATE sessions
                SET metadata = ?, last_updated = CURRENT_TIMESTAMP
                WHERE session_id = ?
            """, (metadata_json, session_id))
            
            conn.commit()
            conn.close()
            
            return True
            
        except Exception as e:
            print(f"Error updating session metadata: {str(e)}")
            traceback.print_exc()
            return False
    
    def get_recent_sessions(self, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Get a list of the most recent conversation sessions.
        
        Args:
            limit: Maximum number of sessions to return
            
        Returns:
            List of dictionaries with session information
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT session_id, user_id, created_at, metadata,
                       (SELECT COUNT(*) FROM messages WHERE session_id = sessions.session_id) as message_count
                FROM sessions
                ORDER BY created_at DESC
                LIMIT ?
            """, (limit,))
            
            rows = cursor.fetchall()
            conn.close()
            
            # Convert rows to dictionaries
            sessions = []
            for row in rows:
                metadata = row['metadata']
                if metadata:
                    try:
                        metadata = json.loads(metadata)
                    except:
                        metadata = {}
                    
                session_dict = {
                    'session_id': row['session_id'],
                    'user_id': row['user_id'],
                    'created_at': row['created_at'],
                    'message_count': row['message_count'],
                    'metadata': metadata
                }
                sessions.append(session_dict)
                
            return sessions
        except Exception as e:
            print(f"[HISTORY] Error retrieving recent sessions: {e}")
            return []
    
    def get_objects_across_sessions(self, limit_days: int = 7, app_name: str = None, 
                                object_type: str = None, status: str = None) -> List[Dict[str, Any]]:
        """
        Retrieve objects from all recent sessions, with optional filtering.
        
        This allows finding session objects across different runs of the application,
        which is especially useful for maintaining continuity between different
        terminal sessions.
        
        Args:
            limit_days: Number of days to look back for objects (default: 7 days)
            app_name: Optional filter by application name
            object_type: Optional filter by object type
            status: Optional filter by status (e.g., "active", "completed")
            
        Returns:
            List of objects from recent sessions matching the criteria
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # Base query with parameters
            query = """
            SELECT o.*, s.created_at as session_created_at, s.user_id 
            FROM session_objects o
            JOIN sessions s ON o.session_id = s.session_id
            WHERE s.created_at >= datetime('now', ?)
            """
            params = [f"-{limit_days} days"]
            
            # Add optional filters
            if app_name:
                query += " AND o.app_name = ?"
                params.append(app_name)
            
            if object_type:
                query += " AND o.object_type = ?"
                params.append(object_type)
                
            if status:
                query += " AND o.status = ?"
                params.append(status)
            
            # Order by most recent first
            query += " ORDER BY o.last_accessed DESC"
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            conn.close()
            
            # Convert rows to dictionaries
            objects = []
            for row in rows:
                obj_dict = {k: row[k] for k in row.keys()}
                objects.append(obj_dict)
                
            print(f"[HISTORY] Retrieved {len(objects)} objects across {limit_days} days of sessions")
            return objects
            
        except Exception as e:
            print(f"[HISTORY] Error retrieving objects across sessions: {e}")
            return []
    
    def track_object(self, session_id: str, object_id: str, object_name: str, 
                     object_type: str, app_name: str, status: str = "active", 
                     metadata: Dict[str, Any] = None) -> bool:
        """
        Track an object created or used in a conversation, such as an email draft or browser window.
        
        Args:
            session_id: The session where the object was created
            object_id: Unique identifier for the object
            object_name: Human-readable name for the object
            object_type: Type of object (e.g., 'email_draft', 'browser_window')
            app_name: Name of the application associated with the object
            status: Status of the object (e.g., 'active', 'closed')
            metadata: Additional metadata about the object (e.g., parameters used to create it)
            
        Returns:
            Boolean indicating success
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # Check if object already exists
            cursor.execute(
                "SELECT object_id FROM session_objects WHERE object_id = ?",
                (object_id,)
            )
            
            existing_object = cursor.fetchone()
            metadata_json = json.dumps(metadata or {})
            
            if existing_object:
                # Update existing object
                cursor.execute(
                    """
                    UPDATE session_objects 
                    SET status = ?, updated_at = CURRENT_TIMESTAMP, metadata = ?
                    WHERE object_id = ?
                    """,
                    (status, metadata_json, object_id)
                )
            else:
                # Insert new object
                cursor.execute(
                    """
                    INSERT INTO session_objects 
                    (object_id, session_id, object_name, object_type, app_name, status, metadata)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (object_id, session_id, object_name, object_type, app_name, status, metadata_json)
                )
            
            conn.commit()
            conn.close()
            
            print(f"[HISTORY] Tracked object '{object_name}' ({object_id}) in session {session_id}")
            return True
            
        except Exception as e:
            print(f"[HISTORY] Error tracking object: {str(e)}")
            return False
            
    def get_session_objects(self, session_id, status=None, app_name=None, object_type=None):
        """
        Get objects associated with a session.
        
        Args:
            session_id: Session ID to retrieve objects for
            status: Optional filter for object status
            app_name: Optional filter for application name
            object_type: Optional filter for object type
            
        Returns:
            List of objects associated with the session
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            query = "SELECT * FROM session_objects WHERE session_id = ?"
            params = [session_id]
            
            if status:
                query += " AND status = ?"
                params.append(status)
                
            if app_name:
                query += " AND app_name = ?"
                params.append(app_name)
                
            if object_type:
                query += " AND object_type = ?"
                params.append(object_type)
                
            query += " ORDER BY updated_at DESC"
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            conn.close()
            
            objects = []
            for row in rows:
                try:
                    metadata = json.loads(row[8]) if row[8] else {}
                except json.JSONDecodeError:
                    metadata = {}
                
                objects.append({
                    "object_id": row[0],
                    "session_id": row[1],
                    "object_name": row[2],
                    "object_type": row[3],
                    "app_name": row[4],
                    "status": row[5],
                    "created_at": row[6],
                    "updated_at": row[7],
                    "metadata": metadata
                })
                
            return objects
            
        except Exception as e:
            print(f"[HISTORY] Error retrieving session objects: {str(e)}")
            return []
        
    def get_recent_objects(self, limit=5, app_name=None, object_type=None, status="active"):
        """
        Get the most recently used objects across all sessions.
        
        Args:
            limit: Maximum number of objects to retrieve
            app_name: Optional filter for application name
            object_type: Optional filter for object type
            status: Optional filter for object status (default: 'active')
            
        Returns:
            List of recent objects across sessions
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            query = "SELECT * FROM session_objects WHERE 1=1"
            params = []
            
            if app_name:
                query += " AND app_name = ?"
                params.append(app_name)
                
            if object_type:
                query += " AND object_type = ?"
                params.append(object_type)
                
            if status:
                query += " AND status = ?"
                params.append(status)
                
            query += " ORDER BY updated_at DESC LIMIT ?"
            params.append(limit)
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            conn.close()
            
            objects = []
            for row in rows:
                try:
                    metadata = json.loads(row[8]) if row[8] else {}
                except json.JSONDecodeError:
                    metadata = {}
                
                objects.append({
                    "object_id": row[0],
                    "session_id": row[1],
                    "object_name": row[2],
                    "object_type": row[3],
                    "app_name": row[4],
                    "status": row[5],
                    "created_at": row[6],
                    "updated_at": row[7],
                    "metadata": metadata
                })
                
            return objects
            
        except Exception as e:
            print(f"[HISTORY] Error retrieving recent objects: {str(e)}")
            return []

# Initialize the conversation history manager
conversation_history = ConversationHistoryManager()

# Remove all handler loading code
# Handlers will be loaded exclusively by the jarvis_orchestrator_intelligence module
print("Handler loading is handled by the intelligence module")

class OrchestratorAgent:
    """
    Adapter class that wraps the orchestrator agent dictionary and provides
    the expected interface for the boardroom terminal.
    
    The OrchestratorAgent uses its intelligence module as its "brain" to:
    1. Understand and process natural language requests
    2. Access knowledge about available capabilities and agents
    3. Make decisions about how to handle different types of requests
    4. Respond naturally while coordinating complex operations
    """
    def __init__(self, agent_dict):
        self.agent_dict = agent_dict
        self.tools = agent_dict.get("tools", [])
        self.specialized_agents = agent_dict.get("specialized_agents", {})
        self.workspace_id = agent_dict.get("workspace_id")
        self.intelligence = agent_dict.get("intelligence")
        
        # Set up logging
        self.logger = logging.getLogger(__name__)
        
        # Set up tracking variables
        self.function_usage_stats = {}
        self.handler_usage_stats = {}
        self.last_tracked_functions = []
        
        # Assign BoardRoom processing function to make it available as instance method
        self.logger.info(f"🔍 Assigning process_with_boardroom: {type(process_with_boardroom)} = {process_with_boardroom}")
        self.process_with_boardroom = process_with_boardroom
        self.logger.info(f"✅ Assigned process_with_boardroom to OrchestratorAgent instance: {type(self.process_with_boardroom)}")
    
    async def execute_handler_async(self, handler_name: str, action: str, **kwargs):
        """
        Execute a handler asynchronously with tracking.
        
        This method executes a handler by name, specifically for use when called
        from the HybridPlanExecutor's _execute_with_handler method.
        
        Args:
            handler_name: Name of the handler to execute
            action: The action to perform
            **kwargs: Parameters to pass to the handler
            
        Returns:
            Dict containing execution result
        """
        # Extract common parameters
        parameters = kwargs.copy()
        journey_id = parameters.get('context', {}).get('journey_id')
        session_id = parameters.get('context', {}).get('session_id')
        workspace_id = parameters.get('context', {}).get('workspace_id')
        
        # Log the execution
        self.logger.info(f"OrchestratorAgent executing handler: {handler_name}.{action}")
        
        try:
            # Import the handler_execution_tracking module directly
            from Jarvis_Agent_SDK.handler_execution_tracking import execute_handler_with_tracking
            
            # Execute with tracking from handler_execution_tracking module
            result = await execute_handler_with_tracking(
                handler_name=handler_name,
                action=action,
                parameters=parameters,
                journey_id=journey_id,
                session_id=session_id,
                workspace_id=workspace_id
            )
            
            return result
        except Exception as e:
            error_message = f"Error executing handler {handler_name}.{action}: {str(e)}"
            self.logger.error(error_message)
            self.logger.debug(traceback.format_exc())
            return {"success": False, "error": error_message}
        
        # Initialize context memory for maintaining conversation state
        self.context = {}
        
        # Initialize function usage tracking
        self.function_usage_stats = {}
        self.handler_usage_stats = {}
        self.last_tracked_functions = []
        
        # Log initialization
        logging.info(f"OrchestratorAgent initialized with {len(self.tools)} tools")
        if self.intelligence:
            logging.info("Intelligence module successfully connected to orchestrator agent")
            # Note: All handler loading is done by the intelligence module
        
        # Ensure the intelligence module is properly initialized
        if self.intelligence and hasattr(self.intelligence, 'discover_orchestrator_agents'):
            try:
                # Initialize the intelligence module's knowledge
                agents = self.intelligence.discover_orchestrator_agents()
                agent_count = len(agents) if agents else 0
                logging.info(f"Intelligence module discovered {agent_count} orchestrator agents")
                
                # Store intelligence capabilities for quick access
                self.capabilities = []
                if hasattr(self.intelligence, 'get_agent_capabilities_from_db'):
                    all_capabilities = self.intelligence.get_agent_capabilities_from_db()
                    self.capabilities = [cap for sublist in all_capabilities.values() for cap in sublist]
                    logging.info(f"Intelligence module knows about {len(self.capabilities)} capabilities")
            except Exception as e:
                logging.error(f"Error initializing intelligence knowledge: {str(e)}")
                
    def get_handler_info(self, handler_name):
        """
        Get information about a specific handler using the intelligence module.
        
        Args:
            handler_name: Name of the handler to get info for
            
        Returns:
            Handler information or None if not found
        """
        try:
            # Try to get handler info from intelligence module
            if self.intelligence and hasattr(self.intelligence, 'get_handler_info'):
                return self.intelligence.get_handler_info(handler_name)
                
            # If intelligence doesn't have the method, try alternate methods
            if self.intelligence and hasattr(self.intelligence, 'get_handler_capabilities'):
                return self.intelligence.get_handler_capabilities(handler_name)
                
            # As a last resort, try to use handler_system directly (should be loaded by intelligence)
            if 'handler_system' in globals() and handler_system and hasattr(handler_system, 'get_handler_info'):
                return handler_system.get_handler_info(handler_name)
                
            logging.warning(f"Could not get info for handler '{handler_name}': No suitable method found")
            return None
        except Exception as e:
            logging.error(f"Error getting info for handler '{handler_name}': {str(e)}")
            return None
            
    def get_available_handlers(self):
        """
        Get list of available handlers using the intelligence module.
        
        Returns:
            List of handler names or empty list if none found
        """
        try:
            # Try to get handlers from intelligence module
            if self.intelligence and hasattr(self.intelligence, 'get_available_handlers'):
                return self.intelligence.get_available_handlers()
                
            # If intelligence doesn't have the method, try alternate methods
            if self.intelligence and hasattr(self.intelligence, 'get_all_handlers'):
                return self.intelligence.get_all_handlers()
                
            # As a last resort, try to use handler_system directly (should be loaded by intelligence)
            if 'handler_system' in globals() and handler_system and hasattr(handler_system, 'get_active_handlers'):
                import asyncio
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                return loop.run_until_complete(handler_system.get_active_handlers())
                
            logging.warning("Could not get available handlers: No suitable method found")
            return []
        except Exception as e:
            logging.error(f"Error getting available handlers: {str(e)}")
            return []
    
    async def handle_user_request(self, request: str, user_id: str, session_id: str = None, source: str = None) -> dict:
        """
        CLAUDE-FIRST ENTRY POINT
        
        All requests start here - create workspace and immediately route to Claude as primary interface.
        This implements the corrected architecture where Claude handles user interaction:
        1. Jarvis Orchestrator (creates workspace for tracking)
        2. Claude Central Feedback (PRIMARY USER INTERFACE - determines execution approach)
        3. Jarvis Orchestrator (coordinates execution based on Claude's decisions)
        
        Args:
            request: The user request string
            user_id: Identifier for the user
            session_id: Optional session ID for context
            source: Source of the request
            
        Returns:
            Dictionary containing Claude's response and execution results
        """
        try:
            logging.info(f"[CLAUDE-FIRST] Starting new request flow: {request}")
            
            # Validate input request
            if not request or not request.strip():
                logging.warning("[CLAUDE-FIRST] Empty or invalid request received")
                return {
                    "success": False,
                    "error": "Empty or invalid request provided",
                    "workspace_id": None,
                    "response": "Please provide a valid request to process."
                }
            
            # PHASE 1: Jarvis creates workspace (always - for tracking)
            workspace = await self._create_initial_workspace(request, user_id, session_id, source)
            logging.info(f"[CLAUDE-FIRST] Created initial workspace: {workspace['workspace_id']}")
            
            # CRITICAL FIX: Create conversation session for persistence in conversation_history.db
            if session_id:
                try:
                    history_manager = ConversationHistoryManager()
                    created_session_id = history_manager.create_session(
                        user_id=user_id,
                        metadata={
                            "source": source or "trevor_desktop",
                            "workspace_id": workspace['workspace_id'],
                            "original_request": request
                        }
                    )
                    # Override session_id to use the one provided by Trevor BoardRoom connector
                    # This ensures consistency between the UI and database
                    if created_session_id:
                        # Update the session with the correct session_id from the connector
                        conn = history_manager._get_connection()
                        cursor = conn.cursor()
                        cursor.execute(
                            "UPDATE sessions SET session_id = ? WHERE session_id = ?",
                            (session_id, created_session_id)
                        )
                        conn.commit()
                        conn.close()
                        logging.info(f"[CONVERSATION-PERSISTENCE] Created conversation session: {session_id} for user {user_id}")
                        
                        # CRITICAL FIX: Create conversation link for UnifiedConversationService
                        try:
                            from Database.conversation_link_manager import ConversationLinkManager
                            link_manager = ConversationLinkManager()
                            link_success = link_manager.create_link(
                                user_conversation_id=session_id,
                                user_id=user_id,
                                boardroom_id=None,
                                journey_id=None,
                                workspace_id=workspace['workspace_id'],
                                link_type='automatic'
                            )
                            if link_success:
                                logging.info(f"[CONVERSATION-PERSISTENCE] Created conversation link for {session_id}")
                            else:
                                logging.warning(f"[CONVERSATION-PERSISTENCE] Failed to create conversation link for {session_id}")
                        except Exception as link_error:
                            logging.error(f"[CONVERSATION-PERSISTENCE] Error creating conversation link: {str(link_error)}")
                    
                except Exception as e:
                    logging.error(f"[CONVERSATION-PERSISTENCE] Failed to create conversation session: {str(e)}")
                    # Continue processing even if session creation fails
            
            # PHASE 2: Claude takes over as primary user interface
            from .claude_user_feedback_service import ClaudeUserFeedbackService
            claude_service = ClaudeUserFeedbackService()
            
            claude_result = await claude_service.handle_initial_request(
                request=request,
                workspace_id=workspace['workspace_id'],
                context={
                    'user_id': user_id, 
                    'session_id': session_id, 
                    'source': source or 'trevor_desktop'
                }
            )
            
            # PHASE 3: Jarvis coordinates execution based on Claude's decisions
            if claude_result.get('needs_execution'):
                logging.info(f"[CLAUDE-FIRST] Claude determined execution needed, coordinating with enhanced workspace")
                # Get enhanced workspace for execution
                enhanced_workspace = await self._route_to_trevor_intelligence(workspace)
                execution_result = await self._coordinate_execution_with_claude(claude_result, enhanced_workspace)
                return execution_result
            else:
                # Claude handled conversationally - return Claude's response
                logging.info(f"[CLAUDE-FIRST] Claude handled request conversationally")
                return {
                    "success": True,
                    "workspace_id": workspace['workspace_id'],
                    "status": "conversation_complete",
                    "response": claude_result.get('claude_response', 'I processed your request.'),
                    "claude_conversation": True,
                    "workspace_promoted": claude_result.get('workspace_promoted', False)
                }
                
        except Exception as e:
            logging.error(f"[CLAUDE-FIRST] Error in handle_user_request: {str(e)}")
            logging.error(traceback.format_exc())
            return {
                "success": False,
                "error": str(e),
                "workspace_id": None,
                "response": "I encountered an error processing your request. Please try again."
            }

    async def _coordinate_execution_with_claude(self, claude_result: dict, enhanced_workspace: dict) -> dict:
        """
        Coordinate execution based on Claude's decisions while preserving Claude as user interface.
        
        Args:
            claude_result: Result from Claude's initial request handling
            enhanced_workspace: Workspace enhanced with Trevor analysis
            
        Returns:
            Dictionary containing execution results with Claude's response
        """
        try:
            workspace_id = claude_result.get('workspace_id')
            logging.info(f"[CLAUDE-COORDINATION] Coordinating execution for workspace {workspace_id}")
            
            # Determine execution path based on workspace complexity
            complexity = enhanced_workspace.get("trevor_analysis", {}).get("complexity", "simple")
            
            if complexity == "simple":
                # Execute directly through existing simple path
                execution_result = await self._execute_workspace(enhanced_workspace)
            else:
                # Route complex tasks through BoardRoom
                planned_workspace = await self._route_to_boardroom(enhanced_workspace)
                execution_result = await self._execute_workspace(planned_workspace)
            
            # Combine execution results with Claude's response
            return {
                "success": execution_result.get("success", True),
                "workspace_id": workspace_id,
                "status": "execution_complete",
                "response": claude_result.get('claude_response', 'I completed your request.'),
                "claude_conversation": True,
                "workspace_promoted": claude_result.get('workspace_promoted', True),
                "execution_details": execution_result,
                "complexity": complexity
            }
            
        except Exception as e:
            logging.error(f"[CLAUDE-COORDINATION] Error coordinating execution: {str(e)}")
            return {
                "success": False,
                "workspace_id": claude_result.get('workspace_id'),
                "status": "execution_error", 
                "response": claude_result.get('claude_response', 'I encountered an error executing your request.'),
                "claude_conversation": True,
                "error": str(e)
            }


    async def _request_claude_feedback(self, feedback_context: dict) -> dict:
        """Send feedback request to Claude User Feedback Service"""
        
        try:
            # Import Claude feedback service
            from .claude_user_feedback_service import ClaudeUserFeedbackService
            claude_service = ClaudeUserFeedbackService()
            
            # Process feedback request
            result = await claude_service.handle_feedback_request(
                source='jarvis_orchestrator',
                request_data=feedback_context,
                context={
                    'workspace_id': feedback_context.get('workspace_id'),
                    'session_id': feedback_context.get('session_id'),
                    'original_request': feedback_context.get('request')
                }
            )
            
            return result
            
        except Exception as e:
            logging.error(f"[CLAUDE-FEEDBACK] Error requesting feedback: {str(e)}")
            return {'error': str(e), 'fallback_needed': True}

    async def _process_enhanced_feedback(self, enhanced_feedback: str, workspace: dict) -> dict:
        """Process Claude's enhanced feedback response"""
        
        try:
            # Update workspace with enhanced information
            workspace['enhanced_request'] = enhanced_feedback
            workspace['feedback_enhanced'] = True
            workspace['enhancement_timestamp'] = time.time()
            
            # Re-route through intelligence with enhanced context
            enhanced_result = await self._route_to_trevor_intelligence(workspace)
            
            logging.info(f"[ENHANCED-FEEDBACK] Processed enhanced feedback for workspace {workspace['workspace_id']}")
            return enhanced_result
            
        except Exception as e:
            logging.error(f"[ENHANCED-FEEDBACK] Error processing feedback: {str(e)}")
            return {'error': str(e), 'workspace': workspace}

    async def process_request(self, query, session_id=None, message_type="request", source=None, user_id=None, conversation_id=None, context=None):
        """
        LEGACY COMPATIBILITY WRAPPER
        
        This method maintains compatibility with existing callers while routing
        through the new workspace-centric architecture.
        
        Args:
            query: The user query or request
            session_id: Optional session ID for maintaining context
            message_type: Type of message (e.g., request, command)
            source: Source of the request (e.g., "trevor_core", "trevor_desktop", "boardroom")
            user_id: ID of the user making the request (for Trevor Desktop)
            conversation_id: ID of the conversation (for Trevor Desktop)
            context: Optional context dictionary with additional parameters
            
        Returns:
            Natural language response to the user query
        """
        try:
            logging.info(f"[LEGACY-WRAPPER] Processing request via legacy interface: {query}")
            
            # ✅ EXTRACT USER_ID FROM CONTEXT IF NOT PROVIDED AS PARAMETER
            effective_user_id = user_id
            if not effective_user_id and context and isinstance(context, dict):
                effective_user_id = context.get('user_id')
            if not effective_user_id:
                raise ValueError("User ID is required - no user_id provided in parameters or context")
            
            logging.info(f"[LEGACY-WRAPPER] Using user_id: {effective_user_id} (from parameter: {user_id}, from context: {context.get('user_id') if context else None})")
            
            # Route through new workspace-centric architecture
            result = await self.handle_user_request(
                request=query,
                user_id=effective_user_id,
                session_id=session_id,
                source=source
            )
            
            # Extract response for legacy compatibility
            if result.get("success", False):
                response = result.get("response", "Request completed successfully.")
                self._record_response(session_id, response, conversation_id)
                return response
            else:
                error_response = result.get("response", "I encountered an error processing your request.")
                self._record_response(session_id, error_response, conversation_id)
                return error_response
                
        except Exception as e:
            logging.error(f"[LEGACY-WRAPPER] Error in legacy process_request: {str(e)}")
            error_response = "I encountered an error while processing your request. Could you please try again?"
            self._record_response(session_id, error_response, conversation_id)
            return error_response

    async def _create_initial_workspace(self, request: str, user_id: str, session_id: str = None, source: str = None) -> dict:
        """Create basic workspace structure for the request"""
        try:
            workspace_id = f"ws_{uuid.uuid4().hex[:8]}"
            
            workspace = {
                "workspace_id": workspace_id,
                "original_request": request,
                "user_id": user_id,
                "session_id": session_id,
                "created_at": datetime.now().isoformat(),
                "status": "created",
                "source": source or "jarvis_orchestrator",
                "metadata": {
                    "creation_method": "workspace_centric_architecture",
                    "version": "1.0"
                }
            }
            
            # Store in workspace database using existing workspace_sharing system
            workspace_sharing = get_workspace_sharing()
            if workspace_sharing:
                try:
                    workspace_name = f"Request: {request[:50]}..." if len(request) > 50 else f"Request: {request}"
                    workspace_desc = f"Workspace for request: '{request}' initiated at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                    
                    # Use system user ID (1) for workspace creation
                    workspace_user_id = 1
                    workspace_metadata = {
                        "original_user_id": user_id,
                        "session_id": session_id,
                        "source": source or "jarvis_orchestrator",
                        "request_text": request,
                        "architecture_version": "workspace_centric_v1"
                    }
                    
                    # Create workspace in database
                    db_workspace_id = await workspace_sharing.create_workspace(
                        name=workspace_name,
                        description=workspace_desc,
                        user_id=workspace_user_id,
                        metadata=workspace_metadata
                    )
                    
                    if db_workspace_id and isinstance(db_workspace_id, int):
                        workspace["db_workspace_id"] = db_workspace_id
                        logging.info(f"[WORKSPACE-CENTRIC] Created database workspace ID: {db_workspace_id}")
                    
                except Exception as db_error:
                    logging.warning(f"[WORKSPACE-CENTRIC] Could not create database workspace: {str(db_error)}")
                    # Continue with in-memory workspace
            
            logging.info(f"[WORKSPACE-CENTRIC] Created initial workspace: {workspace_id}")
            return workspace
            
        except Exception as e:
            logging.error(f"[WORKSPACE-CENTRIC] Error creating initial workspace: {str(e)}")
            raise

    async def _route_to_trevor_intelligence(self, workspace: dict) -> dict:
        """
        Route workspace to Trevor Intelligence for analysis and enhancement
        PHASE 2 ENHANCED: Fast-path detection, workspace caching, and performance monitoring
        """
        try:
            start_time = time.time()
            workspace_id = workspace['workspace_id']
            request = workspace["original_request"]
            
            logging.info(f"[WORKSPACE-CENTRIC] Routing workspace {workspace_id} to Trevor Intelligence")
            
            # PHASE 2: Fast-path detection for simple requests
            fast_path_result = await self._check_fast_path_optimization(workspace)
            if fast_path_result:
                # Add performance metrics
                execution_time = time.time() - start_time
                workspace["performance_metrics"] = {
                    "trevor_analysis_time": execution_time,
                    "optimization_used": "fast_path",
                    "cache_hit": fast_path_result.get("cache_hit", False)
                }
                logging.info(f"[WORKSPACE-CENTRIC] Fast-path optimization applied in {execution_time:.3f}s")
                return fast_path_result
            
            # PHASE 2: Check workspace cache for similar requests
            cached_result = await self._check_workspace_cache(workspace)
            if cached_result:
                execution_time = time.time() - start_time
                cached_result["performance_metrics"] = {
                    "trevor_analysis_time": execution_time,
                    "optimization_used": "workspace_cache",
                    "cache_hit": True
                }
                logging.info(f"[WORKSPACE-CENTRIC] Workspace cache hit in {execution_time:.3f}s")
                return cached_result
            
            # Check if intelligence module is available
            if not self.intelligence:
                raise Exception("Intelligence module not available")
            
            # Check if intelligence has workspace analysis capability
            if hasattr(self.intelligence, 'analyze_workspace'):
                # Use new workspace analysis method if available
                enhanced_workspace = await self.intelligence.analyze_workspace(workspace)
                
                # PHASE 2: Add performance metrics and cache result
                execution_time = time.time() - start_time
                enhanced_workspace["performance_metrics"] = {
                    "trevor_analysis_time": execution_time,
                    "optimization_used": "analyze_workspace",
                    "cache_hit": False
                }
                
                # Cache the result for future similar requests
                await self._cache_workspace_result(workspace, enhanced_workspace)
                
                logging.info(f"[WORKSPACE-CENTRIC] Trevor analysis complete via analyze_workspace in {execution_time:.3f}s")
                return enhanced_workspace
            else:
                # Fallback to existing request processing with workspace context
                request_data = {
                    "text": workspace["original_request"],
                    "session_id": workspace.get("session_id"),
                    "user_id": workspace.get("user_id"),
                    "workspace_id": workspace["workspace_id"],
                    "source": workspace.get("source", "workspace_centric"),
                    "context": workspace.get("metadata", {})
                }
                
                # Process through existing intelligence with workspace context
                result = await self.intelligence.process_request(request_data, workspace["workspace_id"])
                
                # Convert intelligence result to workspace format
                workspace["trevor_analysis"] = {
                    "complexity": result.get("complexity_level", "complex"),
                    "initial_breakdown": result.get("tasks", [workspace["original_request"]]),
                    "suggested_handlers": [result.get("handler", "unknown")],
                    "mcp_resources": result.get("mcp_resources", []),
                    "estimated_duration": result.get("estimated_duration", "unknown"),
                    "requires_collaboration": result.get("complexity_level") == "complex",
                    "intelligence_result": result  # Store full result for reference
                }
                
                # PHASE 2: Add performance metrics and cache result
                execution_time = time.time() - start_time
                workspace["performance_metrics"] = {
                    "trevor_analysis_time": execution_time,
                    "optimization_used": "legacy_process_request",
                    "cache_hit": False
                }
                
                # Cache the result for future similar requests
                await self._cache_workspace_result(workspace, workspace)
                
                workspace["status"] = "analyzed"
                logging.info(f"[WORKSPACE-CENTRIC] Trevor analysis complete via legacy process_request in {execution_time:.3f}s")
                return workspace
                
        except Exception as e:
            logging.error(f"[WORKSPACE-CENTRIC] Error routing to Trevor Intelligence: {str(e)}")
            # Add minimal analysis to allow flow to continue
            workspace["trevor_analysis"] = {
                "complexity": "complex",  # Default to complex for safety
                "initial_breakdown": [workspace["original_request"]],
                "suggested_handlers": ["general"],
                "mcp_resources": [],
                "estimated_duration": "unknown",
                "requires_collaboration": True,
                "error": str(e)
            }
            workspace["status"] = "analysis_failed"
            return workspace

    async def _route_to_boardroom(self, workspace: dict) -> dict:
        """
        Route complex workspace to BoardRoom for collaborative planning
        """
        try:
            logging.info(f"[WORKSPACE-CENTRIC] Routing workspace {workspace['workspace_id']} to BoardRoom")
            
            # Check if BoardRoom processing is available
            if hasattr(self, 'process_with_boardroom') and self.process_with_boardroom:
                # Create BoardRoom context with workspace information
                trevor_analysis = workspace.get("trevor_analysis", {})
                boardroom_context = {
                    "workspace_id": workspace["workspace_id"],
                    "original_request": workspace["original_request"],
                    "trevor_analysis": trevor_analysis,
                    "task_breakdown": trevor_analysis.get("task_breakdown", []),  # Extract breakdown for BoardRoom
                    "user_id": workspace.get("user_id"),
                    "session_id": workspace.get("session_id")
                }
                
                logging.info(f"🎪 BoardRoom context created with {len(boardroom_context.get('task_breakdown', []))} breakdown tasks")
                
                # Process with BoardRoom - check if it's actually callable
                if callable(self.process_with_boardroom):
                    logging.info(f"✅ Calling BoardRoom function: {type(self.process_with_boardroom)}")
                    boardroom_result = await self.process_with_boardroom(
                        query=workspace["original_request"],
                        context=boardroom_context
                    )
                else:
                    logging.error(f"❌ process_with_boardroom is not callable: {type(self.process_with_boardroom)} = {self.process_with_boardroom}")
                    # Fallback to direct import
                    try:
                        from Jarvis_Agent_SDK.jarvis_hybrid_agents.handler_adapter import process_with_boardroom as direct_boardroom
                        logging.info("Using direct import of process_with_boardroom as fallback")
                        boardroom_result = await direct_boardroom(
                            query=workspace["original_request"],
                            context=boardroom_context
                        )
                    except Exception as fallback_error:
                        logging.error(f"Fallback BoardRoom import failed: {fallback_error}")
                        boardroom_result = "BoardRoom processing failed - function not available"
                
                # Add BoardRoom plan to workspace
                workspace["boardroom_plan"] = {
                    "detailed_breakdown": self._parse_boardroom_breakdown(boardroom_result),
                    "resource_allocation": self._extract_resource_allocation(boardroom_result),
                    "success_criteria": self._extract_success_criteria(boardroom_result),
                    "collaboration_model": "claude_gpt_trevor",
                    "boardroom_result": boardroom_result  # Store full result
                }
                
                workspace["status"] = "planned"
                logging.info(f"[WORKSPACE-CENTRIC] BoardRoom planning complete")
                return workspace
            else:
                logging.warning("[WORKSPACE-CENTRIC] BoardRoom not available, using enhanced Trevor analysis")
                # Use Trevor's analysis as the plan
                trevor_analysis = workspace.get("trevor_analysis", {})
                workspace["boardroom_plan"] = {
                    "detailed_breakdown": {"phase1": {
                        "tasks": trevor_analysis.get("initial_breakdown", []),
                        "agents": trevor_analysis.get("suggested_handlers", []),
                        "dependencies": [],
                        "timeline": "immediate"
                    }},
                    "resource_allocation": {
                        "workspaces": {
                            workspace["workspace_id"]: trevor_analysis.get("suggested_handlers", [])
                        }
                    },
                    "success_criteria": ["Complete user request"],
                    "collaboration_model": "trevor_only"
                }
                workspace["status"] = "planned"
                return workspace
                
        except Exception as e:
            logging.error(f"[WORKSPACE-CENTRIC] Error routing to BoardRoom: {str(e)}")
            # Create minimal plan to allow execution to continue
            trevor_analysis = workspace.get("trevor_analysis", {})
            workspace["boardroom_plan"] = {
                "detailed_breakdown": {"fallback_phase": {
                    "tasks": [workspace["original_request"]],
                    "agents": trevor_analysis.get("suggested_handlers", ["general"]),
                    "dependencies": [],
                    "timeline": "immediate"
                }},
                "resource_allocation": {"workspaces": {workspace["workspace_id"]: ["general"]}},
                "success_criteria": ["Attempt to complete request"],
                "collaboration_model": "fallback",
                "error": str(e)
            }
            workspace["status"] = "planning_failed"
            return workspace

    async def _execute_workspace(self, workspace: dict) -> dict:
        """
        Execute workspace regardless of complexity (simple or complex)
        Enhanced with workspace transfer mechanism for seamless system handoffs
        """
        try:
            logging.info(f"[WORKSPACE-CENTRIC] Executing workspace {workspace['workspace_id']}")
            
            # Check if workspace needs transfer between systems
            transfer_request = await self._check_workspace_transfer_requirements(workspace)
            if transfer_request:
                return await self._execute_workspace_transfer(workspace, transfer_request)
            
            if workspace.get("trevor_analysis", {}).get("complexity") == "simple":
                # Simple execution - single handler
                return await self._execute_simple_workspace(workspace)
            else:
                # Complex execution - multi-phase coordination
                return await self._execute_complex_workspace(workspace)
                
        except Exception as e:
            logging.error(f"[WORKSPACE-CENTRIC] Error executing workspace: {str(e)}")
            return {
                "success": False,
                "workspace_id": workspace["workspace_id"],
                "error": str(e),
                "response": "Execution failed due to an error."
            }

    async def _execute_simple_workspace(self, workspace: dict) -> dict:
        """Execute simple workspace with single handler"""
        try:
            trevor_analysis = workspace.get("trevor_analysis", {})
            handler = trevor_analysis.get("suggested_handlers", ["general"])[0]
            task = workspace["original_request"]
            
            logging.info(f"[WORKSPACE-CENTRIC] Executing simple task with handler: {handler}")
            
            # Prepare execution parameters
            parameters = {
                "query": task,
                "context": {
                    "workspace_id": workspace["workspace_id"],
                    "user_id": workspace.get("user_id"),
                    "session_id": workspace.get("session_id")
                }
            }
            
            # Execute handler action
            if hasattr(self, 'execute_handler_action') and callable(self.execute_handler_action):
                result = await self.execute_handler_action(handler, "handle_request", parameters)
            else:
                # Fallback execution
                result = f"Executed {task} with {handler} handler"
            
            # Update workspace with results
            workspace["execution"] = {
                "status": "completed",
                "result": result,
                "handler_used": handler,
                "execution_type": "simple"
            }
            
            return {
                "success": True,
                "workspace_id": workspace["workspace_id"],
                "response": str(result),
                "execution_type": "simple",
                "workspace": workspace
            }
            
        except Exception as e:
            logging.error(f"[WORKSPACE-CENTRIC] Error in simple execution: {str(e)}")
            return {
                "success": False,
                "workspace_id": workspace["workspace_id"],
                "error": str(e),
                "response": "Simple execution failed."
            }

    async def _execute_complex_workspace(self, workspace: dict) -> dict:
        """Execute complex workspace with multi-phase coordination"""
        try:
            plan = workspace.get("boardroom_plan", {})
            detailed_breakdown = plan.get("detailed_breakdown", {})
            
            logging.info(f"[WORKSPACE-CENTRIC] Executing complex workspace with {len(detailed_breakdown)} phases")
            
            # Execute phases sequentially (for now - could be made parallel later)
            execution_results = {}
            overall_response_parts = []
            
            for phase_name, phase_details in detailed_breakdown.items():
                try:
                    phase_tasks = phase_details.get("tasks", [])
                    phase_agents = phase_details.get("agents", ["general"])
                    
                    logging.info(f"[WORKSPACE-CENTRIC] Executing phase {phase_name} with {len(phase_tasks)} tasks")
                    
                    phase_results = []
                    for i, task in enumerate(phase_tasks):
                        # Use assigned agent or cycle through available agents
                        agent = phase_agents[i % len(phase_agents)] if phase_agents else "general"
                        
                        # Execute individual task
                        task_parameters = {
                            "query": task,
                            "context": {
                                "workspace_id": workspace["workspace_id"],
                                "phase": phase_name,
                                "task_index": i
                            }
                        }
                        
                        if hasattr(self, 'execute_handler_action') and callable(self.execute_handler_action):
                            task_result = await self.execute_handler_action(agent, "handle_request", task_parameters)
                        else:
                            task_result = f"Executed task '{task}' with {agent}"
                        
                        phase_results.append({
                            "task": task,
                            "agent": agent,
                            "result": task_result
                        })
                        overall_response_parts.append(f"Phase {phase_name}: {task_result}")
                    
                    execution_results[phase_name] = {
                        "status": "completed",
                        "tasks_completed": len(phase_results),
                        "results": phase_results
                    }
                    
                except Exception as phase_error:
                    logging.error(f"[WORKSPACE-CENTRIC] Error in phase {phase_name}: {str(phase_error)}")
                    execution_results[phase_name] = {
                        "status": "failed",
                        "error": str(phase_error)
                    }
            
            # Update workspace with execution tracking
            workspace["execution"] = {
                "status": "completed" if all(r.get("status") == "completed" for r in execution_results.values()) else "partial",
                "phase_results": execution_results,
                "overall_progress": self._calculate_overall_progress(execution_results),
                "execution_type": "complex"
            }
            
            # Create comprehensive response
            overall_response = "\n".join(overall_response_parts)
            
            return {
                "success": True,
                "workspace_id": workspace["workspace_id"],
                "response": overall_response,
                "execution_type": "complex",
                "phase_results": execution_results,
                "workspace": workspace
            }
            
        except Exception as e:
            logging.error(f"[WORKSPACE-CENTRIC] Error in complex execution: {str(e)}")
            return {
                "success": False,
                "workspace_id": workspace["workspace_id"],
                "error": str(e),
                "response": "Complex execution failed."
            }

    def _parse_boardroom_breakdown(self, boardroom_result) -> dict:
        """Parse BoardRoom result into structured breakdown"""
        # This is a simplified parser - could be enhanced based on actual BoardRoom output format
        if isinstance(boardroom_result, str):
            return {"phase1": {
                "tasks": [boardroom_result],
                "agents": ["general"],
                "dependencies": [],
                "timeline": "immediate"
            }}
        return {"phase1": {"tasks": ["BoardRoom planning complete"], "agents": ["general"], "dependencies": [], "timeline": "immediate"}}

    def _extract_resource_allocation(self, boardroom_result) -> dict:
        """Extract resource allocation from BoardRoom result"""
        return {"workspaces": {"primary": ["general"]}}

    def _extract_success_criteria(self, boardroom_result) -> list:
        """Extract success criteria from BoardRoom result"""
        return ["Complete user request successfully"]

    def _calculate_overall_progress(self, execution_results: dict) -> float:
        """Calculate overall progress percentage"""
        if not execution_results:
            return 0.0
        
        completed_phases = sum(1 for result in execution_results.values() if result.get("status") == "completed")
        total_phases = len(execution_results)
        
        return (completed_phases / total_phases) * 100.0

    # Legacy method start marker for continuation
    async def _legacy_process_request_original(self, query, session_id=None, message_type="request", source=None, user_id=None, conversation_id=None, context=None):
        """
        ORIGINAL LEGACY METHOD - Preserved for reference and emergency fallback
        """
        start_time = time.time()
        workspace_id = None  # Initialize workspace_id
        complexity_analysis = None  # Initialize complexity_analysis
        try:
            # Log the request
            logging.info(f"[ORCHESTRATOR] Processing request: {query}")
            
            # Handle context if provided
            if context and isinstance(context, dict):
                # Check for complexity analysis from Trevor Core
                if "complexity_analysis" in context:
                    complexity_analysis = context["complexity_analysis"]
                    logging.info(f"[ORCHESTRATOR] Using complexity analysis from Trevor Core: {complexity_analysis.get('complexity_level', 'unknown')}")
                    
                # Check for workspace_id
                if "workspace_id" in context:
                    workspace_id = context["workspace_id"]
                    logging.info(f"[ORCHESTRATOR] Using workspace_id from context: {workspace_id}")
            
            # Create journey ID for tracking this request
            # Use conversation_id if provided (from Trevor Desktop), otherwise generate one
            if conversation_id:
                journey_id = conversation_id
                logging.info(f"[ORCHESTRATOR] Using provided conversation_id as journey_id: {journey_id}")
            else:
                journey_id = f"journey_{int(time.time())}_{hashlib.md5(query.encode()).hexdigest()[:8]}"
                logging.info(f"[ORCHESTRATOR] Generated new journey_id: {journey_id}")
            
            # Create a unique workspace for this specific conversation
            workspace_id = None
            workspace_sharing = get_workspace_sharing()
            if workspace_sharing:
                try:
                    # Create a unique workspace name based on the conversation_id
                    workspace_name = f"Conversation: {conversation_id[:20]}"
                    workspace_desc = f"Workspace for conversation initiated at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                    
                    # Handle user_id properly for workspace creation - must be int or None
                    try:
                        # Always use a valid system user ID (1) to avoid NOT NULL constraint
                        # Store the actual user_id in metadata instead
                        workspace_user_id = 1  # System user ID
                        
                        # Create metadata with all important context including the original user_id
                        workspace_metadata = {
                            "source": source or "unknown", 
                            "conversation_id": conversation_id,
                            "original_user_id": user_id,
                            "creation_timestamp": int(time.time()),
                            "session_id": session_id
                        }
                        
                        # Safe handling of context parameter if provided
                        if context is not None:  # Use context parameter defined in method signature
                            # Make a safe copy of context that can be serialized to JSON
                            try:
                                # Convert to JSON and back to ensure serializability
                                json_safe_context = json.loads(json.dumps(context))
                                workspace_metadata["context"] = json_safe_context
                            except (TypeError, ValueError) as json_err:
                                logging.warning(f"[ORCHESTRATOR] Context could not be serialized to JSON: {str(json_err)}")
                                # Store a simple string representation instead
                                workspace_metadata["context_str"] = str(context)
                    except (ValueError, TypeError) as e:
                        logging.warning(f"[ORCHESTRATOR] Error preparing workspace metadata: {str(e)}")
                        workspace_user_id = 1  # Fallback to system user
                        workspace_metadata = {"source": source or "unknown", "conversation_id": conversation_id}
                        
                    logging.info(f"[ORCHESTRATOR] Creating workspace with user_id: {workspace_user_id}")
                    
                    # Create a unique workspace for this conversation
                    new_workspace = await workspace_sharing.create_workspace(
                        name=workspace_name,
                        description=workspace_desc,
                        user_id=workspace_user_id,
                        metadata=workspace_metadata
                    )
                    
                    if new_workspace and isinstance(new_workspace, int):
                        workspace_id = new_workspace
                        logging.info(f"[ORCHESTRATOR] Created new workspace ID: {workspace_id} for conversation {conversation_id}")
                    else:
                        # Fallback to default workspace if creation fails
                        default_workspace = await workspace_sharing.get_or_create_default_workspace()
                        if default_workspace and "workspace_id" in default_workspace:
                            workspace_id = default_workspace["workspace_id"]
                            logging.info(f"[ORCHESTRATOR] Using default workspace ID: {workspace_id} for request (unique creation failed)")
                except Exception as ws_error:
                    logging.error(f"[ORCHESTRATOR] Error getting/creating default workspace: {str(ws_error)}")
            else:
                logging.warning("[ORCHESTRATOR] Workspace sharing manager not available")
            
            # Record request in session history if session ID is provided
            if session_id:
                try:
                    history_manager = ConversationHistoryManager()
                    # Generate a unique message ID with microsecond precision for uniqueness
                    timestamp_ms = int(time.time() * 1000)
                    message_id = f"user_{timestamp_ms}_{uuid.uuid4().hex[:8]}"
                    
                    # Add message with generated message_id
                    history_manager.add_message(
                        message_id=message_id,
                        session_id=session_id,
                        role="user",
                        content=query,
                        metadata={"journey_id": journey_id, "message_type": message_type, "workspace_id": workspace_id}
                    )
                    logging.info(f"[ORCHESTRATOR] Added message to history for session {session_id}")
                except Exception as e:
                    logging.error(f"[ORCHESTRATOR] Error adding message to history: {str(e)}")
            
            # Handle simple greetings and basic queries directly
            query_lower = query.lower().strip()
            if query_lower in ['hello', 'hi', 'hey', 'greetings']:
                response = "Hello! I'm the Jarvis Orchestrator Agent. How can I assist you today?"
                self._record_response(session_id, response, journey_id)
                return response
            elif query_lower in ['how are you', 'how are you doing', 'how are you today']:
                response = "I'm functioning well, thank you for asking! How can I help you?"
                self._record_response(session_id, response, journey_id)
                return response
            
            # Use complexity analysis from context if provided by Trevor Core
            complexity_analysis = None
            if context and "complexity_analysis" in context:
                try:
                    complexity_analysis = context["complexity_analysis"]
                    logging.info(f"[ORCHESTRATOR] Using complexity analysis from Trevor Core: {complexity_analysis.get('complexity_level', 'unknown')}")
                
                    # Determine if request is complex based on Trevor Core's analysis
                    is_complex = False
                    if isinstance(complexity_analysis, dict):
                        complexity_level = complexity_analysis.get("complexity_level", "unknown")
                        is_complex = complexity_level == "complex"
                        
                        # Route based on complexity
                        if is_complex:
                            logging.info(f"[ORCHESTRATOR] Complex request detected, routing to BoardRoom")
                            result = await self.process_with_boardroom(
                                query=query,
                                context={
                                    "workspace_id": workspace_id,
                                    "journey_id": journey_id,
                                    "session_id": session_id,
                                    "complexity_analysis": complexity_analysis
                                }
                            )
                            return result
                    else:
                        logging.info(f"[ORCHESTRATOR] Simple request detected, handling directly")
                        handler_info = complexity_analysis.get("handler_info", {})
                        handler_name = handler_info.get("name", "unknown")
                        action = handler_info.get("action", "handle_request")
                        parameters = {
                            "query": query,
                            "context": {
                                "workspace_id": workspace_id,
                                "journey_id": journey_id,
                                "session_id": session_id
                            }
                        }
                        
                        # Check for missing parameters
                        try:
                            missing_params = []
                            if self.intelligence and hasattr(self.intelligence, 'get_handler_parameters'):
                                required_params = await self.intelligence.get_handler_parameters(handler_name, action)
                                if required_params:
                                    for param in required_params:
                                        if param not in parameters and param != "query" and param != "context":
                                            missing_params.append(param)
                            # Request missing parameters if needed
                            if missing_params:
                                logging.info(f"[ORCHESTRATOR] Missing parameters for {handler_name}.{action}: {missing_params}")
                                updated_parameters = await self.request_missing_parameters(
                                    handler_name=handler_name,
                                    action=action,
                                    parameters=parameters,
                                    missing_params=missing_params,
                                    query=query,
                                    context={"workspace_id": workspace_id, "journey_id": journey_id}
                                )
                                parameters = updated_parameters
                        except Exception as param_error:
                            logging.warning(f"[ORCHESTRATOR] Error checking for missing parameters: {str(param_error)}")
                        
                        # Execute handler with parameters
                        result = await execute_handler_action_async(handler_name, action, parameters)
                        return result
                
                except Exception as e:
                    logging.error(f"[ORCHESTRATOR] Error in Trevor Core processing flow: {str(e)}")
                    logging.error(traceback.format_exc())
                    
                    # Try fallback complexity analysis if available
                    if self.intelligence and hasattr(self.intelligence, 'analyze_complexity_fallback'):
                        try:
                            logging.info("[ORCHESTRATOR] Attempting fallback complexity analysis")
                            fallback_analysis = await self.intelligence.analyze_complexity_fallback(query)
                            if fallback_analysis:
                                logging.info(f"[ORCHESTRATOR] Fallback analysis successful: {fallback_analysis}")
                                is_complex = fallback_analysis.get("complexity_level") == "complex"
                                if is_complex:
                                    logging.info("[ORCHESTRATOR] Fallback analysis indicates complex request, routing to BoardRoom")
                                    return await self.process_with_boardroom(query=query, context={"workspace_id": workspace_id, "journey_id": journey_id})
                        except Exception as fallback_error:
                            logging.error(f"[ORCHESTRATOR] Fallback analysis failed: {str(fallback_error)}")
                    
                    logging.info(f"[ORCHESTRATOR] Falling back to standard intelligence processing")
            
            # Use intelligence module if available
            if self.intelligence:
                logging.info(f"[ORCHESTRATOR] Using intelligence module for request: {query}")
                try:
                    # Check for similar workspaces in cache
                    similar_workspaces = []
                    try:
                        from workspace_reference_cache import get_workspace_reference_cache
                        cache = get_workspace_reference_cache()
                        similar_workspaces = cache.find_similar_workspaces(
                            query=query, 
                            top_k=3,
                            min_similarity=0.75
                        )
                        
                        if similar_workspaces:
                            logging.info(f"[ORCHESTRATOR] Found {len(similar_workspaces)} similar workspace(s) in cache")
                    except Exception as cache_error:
                        logging.warning(f"[ORCHESTRATOR] Error accessing workspace reference cache: {str(cache_error)}")
                    
                    # Create request data with context
                    request_data = {
                        "text": query,
                        "session_id": session_id,
                        "message_type": message_type,
                        "journey_id": journey_id,
                        "context": self.context,
                        "similar_workspaces": similar_workspaces,
                        "source": source or "unknown",
                        "user_id": user_id,
                        "conversation_id": conversation_id
                    }
                    
                    # Add the context to request_data if available
                    if context:
                        request_data["context"] = context
                    
                    # Process with intelligence module
                    result = await self.intelligence.process_request(request_data, journey_id)
                    response = self._process_intelligence_result(query, result)
                    
                    # Record response
                    self._record_response(session_id, response, journey_id)
                    
                    # Track performance metrics
                    performance_time = time.time() - start_time
                    if hasattr(self.intelligence, 'performance_metrics'):
                        self.intelligence.performance_metrics["requests_processed"] += 1
                        self.intelligence.performance_metrics["response_times"].append(performance_time)
                    
                    # Try to store in reference cache for future use
                    try:
                        # Import cache integration function
                        from workspace_reference_cache import integrate_with_agent_registry
                        
                        # Extract relevant data
                        agent_team = result.get('agent_team', [])
                        if not agent_team and result.get('handler'):
                            agent_team = [{
                                "agent_id": result.get('handler'),
                                "role": "primary",
                                "contribution_score": 1.0
                            }]
                            
                        # Performance metrics
                        performance_metrics = {
                            "success_rate": 1.0,
                            "completion_time": performance_time,
                            "quality_score": result.get('confidence', 0.8),
                            "accuracy": 1.0,
                            "efficiency": 0.9
                        }
                        
                        # Store in reference cache
                        asyncio.create_task(integrate_with_agent_registry(
                            task_text=query,
                            workspace_id=journey_id,
                            execution_plan=result.get('execution_plan', {}),
                            performance_metrics=performance_metrics,
                            agent_team=agent_team,
                            metadata={
                                "source": source or "unknown",
                                "user_id": user_id,
                                "conversation_id": conversation_id,
                                "session_id": session_id
                            }
                        ))
                        logging.info(f"[ORCHESTRATOR] Saved to workspace reference cache for journey: {journey_id}")
                    except Exception as cache_error:
                        logging.error(f"[ORCHESTRATOR] Error saving to workspace reference cache: {str(cache_error)}")
                    
                    return response
                    
                except Exception as e:
                    logging.error(f"[ORCHESTRATOR] Error in intelligence processing: {str(e)}")
                    logging.error(traceback.format_exc())
                    return await self._fallback_processing(query)
            else:
                logging.warning("[ORCHESTRATOR] Intelligence module not available, using fallback processing")
                return await self._fallback_processing(query)
                
        except Exception as e:
            logging.error(f"[ORCHESTRATOR] Error processing request: {str(e)}")
            logging.error(traceback.format_exc())
            error_response = f"I encountered an error while processing your request. Could you please try again or rephrase your request?"
            self._record_response(session_id, error_response, journey_id if 'journey_id' in locals() else None)
            return error_response
    
    def _record_response(self, session_id, response, journey_id=None):
        """Record a response in the conversation history."""
        if not session_id:
            return
            
        try:
            history_manager = ConversationHistoryManager()
            # Generate a unique message ID
            message_id = f"assistant_{int(time.time())}"
            # ConversationHistoryManager.add_message requires message_id parameter
            history_manager.add_message(
                message_id=message_id,
                session_id=session_id,
                role="assistant",
                content=response,
                metadata={"journey_id": journey_id} if journey_id else {}
            )
        except Exception as e:
            logging.error(f"[ORCHESTRATOR] Error recording response: {str(e)}")
    
    def _process_intelligence_result(self, query, result):
        """
        Process results from the intelligence module into natural language responses.
        
        Args:
            query: The original user query
            result: The result from the intelligence module
            
        Returns:
            A natural language response based on the result
        """
        # If result is already a string, return it
        if isinstance(result, str):
            return result
            
        # If result is a dictionary (routing information)
        if isinstance(result, dict):
            # Extract key information
            success = result.get('success', False)
            source = result.get('source', 'unknown')
            routing = result.get('routing', 'standard')
            confidence = result.get('confidence', 0)
            agent_info = result.get('agent', {})
            error = result.get('error', None)
            
            # Check if there's a direct response we can use
            if 'response' in result and isinstance(result['response'], str):
                return result['response']
                
            # Generate natural language response based on results
            if success:
                agent_name = agent_info.get('agent_name', 'specialized system')
                capabilities = agent_info.get('capabilities', [])
                
                if routing == 'direct_handler':
                    handler_name = result.get('handler', 'appropriate handler')
                    return f"I'll process your request using the {handler_name} handler. Processing now..."
                    
                elif routing == 'intelligence':
                    return f"I understand your request about {', '.join(capabilities[:2]) if capabilities else 'your topic'}. I'll help you with that."
                    
                elif routing == 'structured_agent':
                    return f"I'll process your request using our structured agent system. This will help with {', '.join(capabilities[:2]) if capabilities else 'your request'}."
                    
                else:  # standard or unknown routing
                    return f"I understand your request. I'll process it using the most appropriate system."
            else:
                # Handle error cases
                if error:
                    return f"I encountered an issue processing your request: {error}. Could you please rephrase or provide more details?"
                else:
                    return f"I'm not sure how to process your request. Could you please provide more details or rephrase it?"
        
        # For any other type, provide a generic response
        return f"I've processed your request: '{query}'. Is there anything specific you'd like me to help you with?"
    
    async def _fallback_processing(self, query):
        """
        Fallback processing when intelligence module is unavailable or fails.
        
        Args:
            query: The user query
            
        Returns:
            A simple response based on basic processing
        """
        # Simple keyword analysis for request type
        query_lower = query.lower()
        
        # Look for common request types
        if any(word in query_lower for word in ['find', 'search', 'look for', 'locate']):
            response = f"I understand you're looking for something. Could you specify what you're trying to find?"
            return response
            
        elif any(word in query_lower for word in ['create', 'make', 'build', 'generate']):
            response = f"I can help you create something. Could you provide more details about what you want to create?"
            return response
            
        elif any(word in query_lower for word in ['analyze', 'examine', 'review', 'check']):
            return f"I can help analyze data or content. What exactly would you like me to analyze?"
            
        elif any(word in query_lower for word in ['how to', 'how do', 'explain', 'tell me']):
            return f"I'd be happy to explain that. Could you clarify what specifically you need to know?"
        
        # Generic fallback response
        return f"I received your request: '{query}'. How would you like me to help you with this?"
    
    def track_function_usage(self, function_name: str, success: bool = True, execution_time: float = None, 
                          metadata: Dict[str, Any] = None, error: str = None) -> None:
        """
        Track function usage for learning and optimization.
        
        This method records:
        1. Success/failure counts for each function
        2. Execution time statistics
        3. Error patterns
        4. Usage contexts
        
        Args:
            function_name: Name of the function being tracked
            success: Whether the function executed successfully
            execution_time: Time taken to execute (in seconds)
            metadata: Additional context information about the usage
            error: Error message if the function failed
        """
        try:
            # Initialize stats for this function if not already present
            if function_name not in self.function_usage_stats:
                self.function_usage_stats[function_name] = {
                    "calls": 0,
                    "successes": 0,
                    "failures": 0,
                    "total_execution_time": 0,
                    "avg_execution_time": 0,
                    "error_types": {},
                    "last_used": None,
                    "contexts": [],
                    "related_functions": set()
                }
            
            # Get the current stats
            stats = self.function_usage_stats[function_name]
            
            # Update usage statistics
            stats["calls"] += 1
            if success:
                stats["successes"] += 1
            else:
                stats["failures"] += 1
                
                # Track error types
                if error:
                    error_type = error.split(":")[0] if ":" in error else error
                    stats["error_types"][error_type] = stats["error_types"].get(error_type, 0) + 1
            
            # Update execution time statistics
            if execution_time is not None:
                stats["total_execution_time"] += execution_time
                stats["avg_execution_time"] = stats["total_execution_time"] / stats["calls"]
            
            # Update timestamp
            stats["last_used"] = time.time()
            
            # Store context information
            if metadata:
                # Limit stored contexts to avoid memory growth
                if len(stats["contexts"]) >= 10:
                    stats["contexts"].pop(0)  # Remove oldest context
                
                stats["contexts"].append({
                    "timestamp": time.time(),
                    "metadata": metadata,
                    "success": success
                })
            
            # Track related functions (functions called together in sequence)
            for prev_func in self.last_tracked_functions[-3:]:  # Look at last 3 functions
                if prev_func != function_name:
                    stats["related_functions"].add(prev_func)
                    
                    # Also update the related_functions for the previous function
                    if prev_func in self.function_usage_stats:
                        self.function_usage_stats[prev_func]["related_functions"].add(function_name)
            
            # Update recently used functions list
            self.last_tracked_functions.append(function_name)
            if len(self.last_tracked_functions) > 10:
                self.last_tracked_functions.pop(0)
            
            # Store in database if intelligence module is available
            if self.intelligence and hasattr(self.intelligence, 'record_function_usage'):
                try:
                    self.intelligence.record_function_usage(
                        function_name=function_name,
                        success=success,
                        execution_time=execution_time,
                        metadata=metadata,
                        error=error,
                        workspace_id=self.workspace_id
                    )
                except Exception as e:
                    logging.error(f"Error recording function usage in intelligence module: {str(e)}")
            
            # Log the tracking
            log_level = logging.INFO if success else logging.WARNING
            time_str = f"{execution_time:.4f}s" if execution_time is not None else "N/A"
            logging.log(log_level, f"Tracked function usage: {function_name} (success={success}, time={time_str})")
        except Exception as e:
            logging.error(f"Error tracking function usage for {function_name}: {str(e)}")
            # Continue execution despite tracking error

    def track_handler_action(self, handler_name: str, action: str, success: bool = True, execution_time: float = None,
                           parameters: Dict[str, Any] = None, error: str = None, result: Any = None,
                           journey_id: str = None, session_id: str = None) -> None:
        """
        Track handler action execution for learning and intelligent routing.
        
        This method records:
        1. Success/failure rates for each handler and action
        2. Execution time statistics for performance analysis
        3. Error patterns for troubleshooting
        4. Relationships between actions and parameters
        5. Context information for better routing decisions
        
        Args:
            handler_name: Name of the handler (e.g., 'finder', 'email', 'calendar')
            action: Name of the action performed by the handler (e.g., 'search', 'send_email')
            success: Whether the action executed successfully
            execution_time: Time taken to execute (in seconds)
            parameters: Parameters passed to the handler action
            error: Error message if the action failed
            result: Result returned by the handler action (optional)
            journey_id: Journey ID for tracking multi-step operations (optional)
            session_id: Session ID for tracking user sessions (optional)
        """
        try:
            # First, prioritize tracking via intelligence module if available
            if self.intelligence and hasattr(self.intelligence, 'record_handler_usage'):
                try:
                    # Let intelligence module handle the tracking first
                    self.intelligence.record_handler_usage(
                        handler_name=handler_name,
                        action=action,
                        success=success,
                        execution_time=execution_time,
                        parameters=parameters,
                        error=error,
                        journey_id=journey_id,
                        session_id=session_id,
                        workspace_id=self.workspace_id
                    )
                    # Log the intelligence tracking
                    time_str = f"{execution_time:.4f}s" if execution_time is not None else "N/A"
                    logging.info(f"Intelligence tracked handler action: {handler_name}.{action} (success={success}, time={time_str})")
                except Exception as e:
                    logging.error(f"Error recording handler usage in intelligence module: {str(e)}")
                    # Continue with local tracking as fallback
            
            # Local tracking for redundancy and quick access
            # Create a unique key for this handler action
            handler_action_key = f"{handler_name}.{action}"
            
            # Initialize stats for this handler action if not already present
            if handler_action_key not in self.handler_usage_stats:
                self.handler_usage_stats[handler_action_key] = {
                    "handler": handler_name,
                    "action": action,
                    "calls": 0,
                    "successes": 0,
                    "failures": 0,
                    "total_execution_time": 0,
                    "avg_execution_time": 0,
                    "error_types": {},
                    "common_parameters": {},
                    "success_rate": 1.0,  # Default to 100% until we have data
                    "last_used": None,
                    "consecutive_successes": 0,
                    "consecutive_failures": 0,
                    "contexts": [],
                    "related_actions": set()
                }
            
            # Get the current stats
            stats = self.handler_usage_stats[handler_action_key]
            
            # Update usage statistics
            stats["calls"] += 1
            if success:
                stats["successes"] += 1
                stats["consecutive_successes"] += 1
                stats["consecutive_failures"] = 0
            else:
                stats["failures"] += 1
                stats["consecutive_failures"] += 1
                stats["consecutive_successes"] = 0
                
                # Track error types
                if error:
                    error_type = error.split(":")[0] if ":" in error else error
                    stats["error_types"][error_type] = stats["error_types"].get(error_type, 0) + 1
            
            # Update execution time statistics
            if execution_time is not None:
                stats["total_execution_time"] += execution_time
                stats["avg_execution_time"] = stats["total_execution_time"] / stats["calls"]
            
            # Calculate success rate
            if stats["calls"] > 0:
                stats["success_rate"] = stats["successes"] / stats["calls"]
            
            # Update timestamp
            stats["last_used"] = time.time()
            
            # Track parameter patterns for successful actions
            if parameters and success:
                for param_name, param_value in parameters.items():
                    if param_name not in stats["common_parameters"]:
                        stats["common_parameters"][param_name] = {}
                    
                    # Convert value to string representation for tracking
                    param_str = str(param_value)
                    if len(param_str) > 100:  # Limit very long values
                        param_str = param_str[:100] + "..."
                    
                    # Increment count for this parameter value
                    if param_str not in stats["common_parameters"][param_name]:
                        stats["common_parameters"][param_name][param_str] = 0
                    stats["common_parameters"][param_name][param_str] += 1
            
            # Store context and result information
            context_entry = {
                "timestamp": time.time(),
                "journey_id": journey_id,
                "session_id": session_id,
                "parameters": parameters,
                "success": success,
                "execution_time": execution_time,
            }
            
            # Add error information if applicable
            if not success and error:
                context_entry["error"] = error
            
            # Add result summary if provided
            if result:
                if isinstance(result, dict):
                    # Store only essential info from dict results
                    result_summary = {k: v for k, v in result.items() if k in ["success", "status", "type"]}
                    if "message" in result and isinstance(result["message"], str):
                        result_summary["message"] = (result["message"][:100] + "...") if len(result["message"]) > 100 else result["message"]
                    context_entry["result_summary"] = result_summary
                elif isinstance(result, str):
                    # Store truncated string result
                    context_entry["result_summary"] = (result[:100] + "...") if len(result) > 100 else result
                elif hasattr(result, 'to_dict') and callable(getattr(result, 'to_dict')):
                    # Handle HandlerResult objects
                    result_dict = result.to_dict()
                    context_entry["result_summary"] = {
                        "success": result_dict.get("success", False),
                        "error": result_dict.get("error", None)
                    }
            
            # Limit stored contexts to avoid memory growth
            if len(stats["contexts"]) >= 10:
                stats["contexts"].pop(0)  # Remove oldest context
            
            stats["contexts"].append(context_entry)
            
            # Track related actions (actions called together in sequence)
            # This helps with identifying patterns for multi-step operations
            for prev_func in self.last_tracked_functions[-5:]:  # Look at last 5 functions/actions
                if "." in prev_func and prev_func != handler_action_key:
                    stats["related_actions"].add(prev_func)
                    
                    # Also update the related_actions for the previous handler action
                    prev_handler, prev_action = prev_func.split(".", 1)
                    if prev_func in self.handler_usage_stats:
                        self.handler_usage_stats[prev_func]["related_actions"].add(handler_action_key)
            
            # Update recently used functions/actions list
            self.last_tracked_functions.append(handler_action_key)
            if len(self.last_tracked_functions) > 15:  # Increased to track more relationships
                self.last_tracked_functions.pop(0)
            
            # Log the local tracking
            log_level = logging.INFO if success else logging.WARNING
            time_str = f"{execution_time:.4f}s" if execution_time is not None else "N/A"
            logging.log(log_level, f"Locally tracked handler action: {handler_name}.{action} (success={success}, time={time_str})")
            
            # Return the updated statistics for reference
            return stats
        except Exception as e:
            logging.error(f"Error tracking handler action {handler_name}.{action}: {str(e)}")
            # Continue execution despite tracking error
            return None
    
    async def _check_fast_path_optimization(self, workspace: dict) -> Optional[dict]:
        """
        PHASE 2: Fast-path detection for simple requests that can be handled immediately
        
        Args:
            workspace: The workspace to evaluate for fast-path optimization
            
        Returns:
            Optimized workspace if fast-path detected, None otherwise
        """
        try:
            request = workspace["original_request"].lower().strip()
            
            # Fast-path patterns for immediate simple response
            simple_patterns = [
                # Time/date requests
                (r'\b(what time|current time|time is it)\b', "simple", ["time"], "< 1 second"),
                (r'\b(what date|today\'s date|current date)\b', "simple", ["calendar"], "< 1 second"),
                
                # Simple commands
                (r'\b(open|launch|start)\s+\w+\b', "simple", ["application"], "< 5 seconds"),
                (r'\b(close|quit|exit)\s+\w+\b', "simple", ["application"], "< 5 seconds"),
                
                # Quick calculations
                (r'\b\d+\s*[+\-*/]\s*\d+\b', "simple", ["calculator"], "< 1 second"),
                
                # Simple reminders
                (r'\bremind me\b.*\b(in|at)\b.*\b(minute|hour|pm|am)\b', "simple", ["reminder"], "< 10 seconds"),
            ]
            
            for pattern, complexity, handlers, duration in simple_patterns:
                if re.search(pattern, request):
                    logging.info(f"[FAST-PATH] Detected fast-path pattern for: {request[:50]}...")
                    workspace["fast_path"] = {
                        "detected": True,
                        "pattern": pattern,
                        "complexity": complexity,
                        "suggested_handlers": handlers,
                        "estimated_duration": duration
                    }
                    return workspace
            
            return None
        except Exception as e:
            logging.error(f"Error in fast-path optimization: {str(e)}")
            return None

    async def _check_workspace_transfer_requirements(self, workspace: dict) -> Optional[dict]:
        """
        Check if workspace needs to be transferred between systems for optimal execution.
        This implements the detour idea for seamless workspace transfers.
        
        Args:
            workspace: The workspace to evaluate for transfer requirements
            
        Returns:
            Transfer request dict if transfer needed, None otherwise
        """
        try:
            workspace_id = workspace.get("workspace_id", "unknown")
            logging.info(f"[WORKSPACE-TRANSFER] Checking transfer requirements for workspace {workspace_id}")
            
            # Check if complexity has changed during execution
            current_complexity = workspace.get("trevor_analysis", {}).get("complexity", "unknown")
            execution_history = workspace.get("execution_history", [])
            
            # Analyze workspace context for transfer triggers
            transfer_triggers = []
            
            # Trigger 1: Simple task became complex during execution
            if current_complexity == "simple" and len(execution_history) >= 2:
                # If simple task has had multiple failed attempts, it might need BoardRoom collaboration
                failed_attempts = [h for h in execution_history if h.get("status") == "failed"]
                if len(failed_attempts) >= 2:
                    transfer_triggers.append({
                        "trigger": "simple_to_complex_escalation",
                        "reason": "Multiple failed attempts suggest need for collaborative planning",
                        "target_system": "boardroom",
                        "priority": "high"
                    })
            
            # Trigger 2: Task requires multi-system coordination
            original_request = workspace.get("original_request", "").lower()
            if any(keyword in original_request for keyword in ["integrate", "coordinate", "combine", "synchronize"]):
                transfer_triggers.append({
                    "trigger": "multi_system_coordination",
                    "reason": "Task requires coordination between multiple systems",
                    "target_system": "boardroom",
                    "priority": "medium"
                })
            
            if transfer_triggers:
                return {
                    "transfer_needed": True,
                    "workspace_id": workspace_id,
                    "triggers": transfer_triggers,
                    "recommended_action": "transfer_to_boardroom" if any(t["target_system"] == "boardroom" for t in transfer_triggers) else "escalate"
                }
            
            return None
            
        except Exception as e:
            logging.error(f"Error checking workspace transfer requirements: {str(e)}")
            return None

    async def _check_workspace_cache(self, workspace: dict) -> Optional[dict]:
        """
        PHASE 2: Check workspace cache for similar requests to avoid recomputation
        
        Args:
            workspace: The workspace to check against cache
            
        Returns:
            Cached workspace result if found, None otherwise
        """
        try:
            # Initialize cache if not exists
            if not hasattr(self, '_workspace_cache'):
                self._workspace_cache = {}
            
            request = workspace["original_request"]
            user_id = workspace.get("user_id", "unknown")
            
            # Generate cache key based on request similarity
            cache_key = self._generate_cache_key(request, user_id)
            
            # Check if we have a cached result
            if cache_key in self._workspace_cache:
                cached_entry = self._workspace_cache[cache_key]
                
                # Check if cache entry is still valid (not older than 1 hour)
                cache_age = time.time() - cached_entry["timestamp"]
                if cache_age < 3600:  # 1 hour cache validity
                    logging.info(f"[WORKSPACE-CACHE] Cache hit for key: {cache_key}")
                    
                    # Clone cached workspace with new workspace ID
                    cached_workspace = cached_entry["workspace"].copy()
                    cached_workspace["workspace_id"] = workspace["workspace_id"]
                    cached_workspace["created_at"] = workspace["created_at"]
                    cached_workspace["cache_hit"] = True
                    cached_workspace["cache_age_seconds"] = cache_age
                    
                    return cached_workspace
                else:
                    # Remove expired cache entry
                    del self._workspace_cache[cache_key]
                    logging.info(f"[WORKSPACE-CACHE] Expired cache entry removed: {cache_key}")
            
            return None
            
        except Exception as e:
            logging.warning(f"[WORKSPACE-CACHE] Error checking cache: {str(e)}")
            return None

    def _generate_cache_key(self, request: str, user_id: str) -> str:
        """Generate a cache key based on request content and user"""
        try:
            import hashlib
            
            # Normalize request for caching
            normalized_request = request.lower().strip()
            
            # Create cache key from request content and user
            cache_content = f"{normalized_request}|{user_id}"
            cache_key = hashlib.md5(cache_content.encode()).hexdigest()[:16]
            
            return cache_key
            
        except Exception as e:
            logging.warning(f"[WORKSPACE-CACHE] Error generating cache key: {str(e)}")
            return f"fallback_{hash(request)}_{user_id}"

    async def _cache_workspace_result(self, original_workspace: dict, analyzed_workspace: dict):
        """
        PHASE 2: Cache workspace analysis result for future similar requests
        
        Args:
            original_workspace: The original workspace before analysis
            analyzed_workspace: The workspace after Trevor analysis
        """
        try:
            # Initialize cache if not exists
            if not hasattr(self, '_workspace_cache'):
                self._workspace_cache = {}
            
            request = original_workspace["original_request"]
            user_id = original_workspace.get("user_id", "unknown")
            
            # Generate cache key
            cache_key = self._generate_cache_key(request, user_id)
            
            # Cache the analyzed workspace (without workspace-specific IDs)
            cache_entry = {
                "workspace": {
                    "original_request": analyzed_workspace["original_request"],
                    "trevor_analysis": analyzed_workspace.get("trevor_analysis", {}),
                    "status": analyzed_workspace.get("status"),
                    "optimization_used": analyzed_workspace.get("optimization_used", "analysis")
                },
                "timestamp": time.time(),
                "user_id": user_id
            }
            
            self._workspace_cache[cache_key] = cache_entry
            
            # Limit cache size to prevent memory bloat
            if len(self._workspace_cache) > 100:
                # Remove oldest entries
                oldest_key = min(self._workspace_cache.keys(), 
                               key=lambda k: self._workspace_cache[k]["timestamp"])
                del self._workspace_cache[oldest_key]
                logging.info(f"[WORKSPACE-CACHE] Removed oldest cache entry to maintain size limit")
            
            logging.info(f"[WORKSPACE-CACHE] Cached result for key: {cache_key}")
            
        except Exception as e:
            logging.warning(f"[WORKSPACE-CACHE] Error caching result: {str(e)}")

@function_tool
def terminal_get_workspace_performance(workspace_id: int, time_period: str = "week") -> str:
    """
    Get performance metrics and quality indicators for a workspace.
    
    Args:
        workspace_id: ID of the workspace to analyze
        time_period: Time period to analyze ("day", "week", "month", "quarter", "year")
        
    Returns:
        JSON string with workspace performance metrics
    """
    try:
        import json
        import asyncio
        
        # Import at runtime to avoid circular imports
        # Use get_boardroom from boardroom_connector to avoid circular imports
        boardroom = get_boardroom()
        if not boardroom:
            return json.dumps({"error": "BoardRoom not available"})
            
        # Access workspace sharing manager through the boardroom
        workspace_manager = boardroom.get_workspace_manager()
        if not workspace_manager:
            return json.dumps({"error": "Workspace manager not available"})
            
        # Get the performance metrics
        performance = asyncio.run(
            workspace_manager.analyze_workspace_performance(
                workspace_id=workspace_id,
                time_period=time_period
            )
        )
        
        if "error" in performance:
            return json.dumps({
                "status": "error",
                "message": f"Error analyzing workspace performance: {performance['error']}",
                "workspace_id": workspace_id,
                "time_period": time_period
            })
            
        # Format the performance data
        result = {
            "status": "success",
            "workspace_id": workspace_id,
            "time_period": time_period,
            "performance_metrics": performance
        }
        
        # Add some summary insights
        insights = []
        
        # Add success rate insight
        if "success_rate" in performance and performance["success_rate"] is not None:
            success_rate = performance["success_rate"]
            if success_rate > 0.9:
                insights.append("Excellent success rate above 90%")
            elif success_rate > 0.8:
                insights.append("Good success rate between 80-90%")
            elif success_rate > 0.6:
                insights.append("Average success rate between 60-80%")
            else:
                insights.append("Below average success rate, needs improvement")
                
        # Add quality score insight
        if "avg_quality_score" in performance and performance["avg_quality_score"] is not None:
            quality_score = performance["avg_quality_score"]
            if quality_score > 0.9:
                insights.append("Excellent average quality score")
            elif quality_score > 0.7:
                insights.append("Good average quality score")
            elif quality_score > 0.5:
                insights.append("Average quality score, consider improvements")
            else:
                insights.append("Below average quality score, needs attention")
                
        # Add activity trend insight
        if "performance_trend" in performance and performance["performance_trend"]:
            trend = performance["performance_trend"]
            if len(trend) > 1:
                first_success = trend[0].get("success_rate", 0) or 0
                last_success = trend[-1].get("success_rate", 0) or 0
                
                if last_success > first_success + 0.1:
                    insights.append("Improving success rate trend over time")
                elif last_success < first_success - 0.1:
                    insights.append("Declining success rate trend over time")
                else:
                    insights.append("Stable success rate trend over time")
                    
        result["insights"] = insights
        
        return json.dumps(result, indent=2)
        
    except Exception as e:
        import logging
        logging.error(f"Error getting workspace performance: {str(e)}")
        return json.dumps({
            "status": "error",
            "message": f"Failed to get workspace performance: {str(e)}",
            "workspace_id": workspace_id,
            "time_period": time_period
        })

@function_tool
def terminal_adjust_agent_roles(workspace_id: int, auto_adjust: bool = False, 
                               performance_threshold: float = 0.8, time_period: str = "month",
                               prioritize_retention: bool = True) -> str:
    """
    Analyze agent performance and adjust roles based on performance metrics.
    
    Args:
        workspace_id: ID of the workspace to analyze
        auto_adjust: Whether to automatically apply role adjustments (default: False, just show recommendations)
        performance_threshold: The minimum performance score threshold for promotion (0.0-1.0)
        time_period: Time period to analyze ("day", "week", "month", "quarter", "year")
        prioritize_retention: Whether to prioritize keeping well-performing agents in their teams (default: True)
        
    Returns:
        JSON string with analysis results and role adjustment recommendations
    """
    try:
        import json
        import asyncio
        
        # Import at runtime to avoid circular imports
        # Use get_boardroom from boardroom_connector to avoid circular imports
        boardroom = get_boardroom()
        if not boardroom:
            return json.dumps({"error": "BoardRoom not available"})
            
        # Get the performance analysis and role recommendations
        analysis = asyncio.run(
            boardroom.analyze_and_adjust_agent_roles(
                workspace_id=workspace_id,
                auto_adjust=auto_adjust,
                performance_threshold=performance_threshold,
                time_period=time_period,
                prioritize_retention=prioritize_retention
            )
        )
        
        if "error" in analysis:
            return json.dumps({
                "status": "error",
                "message": f"Error analyzing agent roles: {analysis['error']}",
                "workspace_id": workspace_id,
                "time_period": time_period
            })
            
        # Format the output
        if auto_adjust:
            header = f"Applied {analysis['adjustments_applied']} role adjustments for agents in workspace {workspace_id}"
        else:
            header = f"Found {analysis['adjustments_needed']} recommended role adjustments for agents in workspace {workspace_id}"
            
        # Add a summary of adjustments
        adjustments_summary = []
        for adjustment in analysis.get("role_adjustments", []):
            adjustments_summary.append({
                "agent_id": adjustment.get("agent_id"),
                "agent_name": adjustment.get("agent_name"),
                "current_role": adjustment.get("current_role"),
                "recommended_role": adjustment.get("recommended_role"),
                "performance_score": adjustment.get("performance_score"),
                "adjusted_score": adjustment.get("adjusted_score", adjustment.get("performance_score")),
                "tenure_days": adjustment.get("tenure_days", 0),
                "consecutive_good_performances": adjustment.get("consecutive_good_performances", 0),
                "reason": adjustment.get("reason")
            })
            
        # Add team cohesion information
        team_cohesion = analysis.get("team_cohesion", {})
        
        result = {
            "status": "success",
            "message": header,
            "workspace_id": workspace_id,
            "time_period": time_period,
            "auto_adjust": auto_adjust,
            "prioritize_retention": prioritize_retention,
            "performance_threshold": performance_threshold,
            "team_cohesion": team_cohesion,
            "total_agents": analysis.get("agent_count", 0),
            "adjustments_needed": analysis.get("adjustments_needed", 0),
            "adjustments_applied": analysis.get("adjustments_applied", 0),
            "adjustments": adjustments_summary
        }
        
        # Include the full evaluations in verbose mode
        all_evaluations = analysis.get("all_evaluations", [])
        if all_evaluations:
            result["all_evaluations"] = all_evaluations
            
        return json.dumps(result, indent=2)
        
    except Exception as e:
        import logging
        logging.error(f"Error adjusting agent roles: {str(e)}")
        return json.dumps({
            "status": "error",
            "message": f"Failed to adjust agent roles: {str(e)}",
            "workspace_id": workspace_id,
            "time_period": time_period
        })

@function_tool
def terminal_log_agent_activity(agent_id: str, agent_name: str, agent_type: str, workspace_id: int, 
                             action_type: str, details: Optional[dict] = None, 
                             performance_metrics: Optional[dict] = None) -> str:
    """
    Log agent activity in a workspace with detailed tracking.
    
    Args:
        agent_id: ID of the agent performing the action
        agent_name: Name of the agent
        agent_type: Type of agent (e.g., specialist, coordinator)
        workspace_id: ID of the workspace
        action_type: Type of action performed (e.g., execute_task, analyze_data)
        details: Optional details about the action
        performance_metrics: Optional performance metrics for the action
        
    Returns:
        Success message with activity ID
    """
    try:
        import json
        import asyncio
        
        # Import at runtime to avoid circular imports
        # Use get_boardroom from boardroom_connector to avoid circular imports
        boardroom = get_boardroom()
        if not boardroom:
            return json.dumps({"error": "BoardRoom not available"})
            
        # Log the agent activity
        result = asyncio.run(
            boardroom.log_agent_activity(
                agent_id=agent_id,
                agent_name=agent_name,
                agent_type=agent_type,
                workspace_id=workspace_id,
                action_type=action_type,
                details=details,
                performance_metrics=performance_metrics
            )
        )
        
        if result:
            return json.dumps({
                "status": "success",
                "message": f"Successfully logged {action_type} activity for agent {agent_name} in workspace {workspace_id}",
                "agent_id": agent_id,
                "workspace_id": workspace_id,
                "action_type": action_type
            })
        else:
            return json.dumps({
                "status": "error",
                "message": "Failed to log agent activity",
                "agent_id": agent_id,
                "workspace_id": workspace_id
            })
        
    except Exception as e:
        import logging
        logging.error(f"Error logging agent activity: {str(e)}")
        return json.dumps({
            "status": "error",
            "message": f"Failed to log agent activity: {str(e)}",
            "agent_id": agent_id,
            "workspace_id": workspace_id
        })

async def handle_system_completion(agent_response, task_id, system_name, session_id=None):
    """Process a system completion callback"""
    try:
        # Import at runtime to avoid circular imports
        # Use get_boardroom from boardroom_connector to avoid circular imports
        boardroom = get_boardroom()
        if boardroom:
            from .error_monitor import track_agent_performance
            await track_agent_performance(
                agent_id=system_name,
                agent_name=system_name,
                agent_type="system",
                task_id=task_id,
                workspace_id=session_id or f"default_{task_id}",
                success=True,
                execution_time=0,  # System time already tracked elsewhere
                metrics={
                    "response_length": len(str(agent_response)) if agent_response else 0,
                    "has_response": bool(agent_response)
                },
                board_room=boardroom
            )
    except Exception as e:
        logging.error(f"Error handling system completion: {str(e)}")

# Custom JSON encoder to handle HandlerResult objects
class CustomJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        # Check if the object has a to_dict method
        if hasattr(obj, 'to_dict') and callable(getattr(obj, 'to_dict')):
            return obj.to_dict()
        # Let the base class handle other types or raise TypeError
        return super().default(obj)

async def execute_tool_call(tool_call):
    """
    Execute a tool call asynchronously.
    
    Args:
        tool_call: The tool call to execute
        
    Returns:
        Result of the tool execution
    """
    try:
        tool_name = tool_call.get('name', '')
        tool_args = tool_call.get('arguments', {})
        
        # Process specific tools
        if tool_name == "execute_validated_analysis_workflow_tool":
            return await execute_validated_analysis_workflow(tool_args)
            
        elif tool_name == "route_to_appropriate_system_tool":
            return await route_task_to_appropriate_system(tool_args)
            
        elif tool_name == "execute_any_handler":
            return await execute_any_handler_async(**tool_args)
            
        else:
            # Try to dynamically call other tools by name
            if tool_name in globals() and callable(globals()[tool_name]):
                func = globals()[tool_name]
                if asyncio.iscoroutinefunction(func):
                    return await func(**tool_args)
                else:
                    return func(**tool_args)
            else:
                return {"error": f"Tool {tool_name} not found or not callable"}
                
    except Exception as e:
        return {"error": f"Error executing tool {tool_name}: {str(e)}"}

class PersistentConnectionManager:
    """Manages persistent connections for long-running tasks."""
    
    def __init__(self):
        """Initialize the connection manager."""
        self.active_connections = {}
        self.connection_metadata = {}
        self._lock = asyncio.Lock()
        self._cleanup_task = None
        self._cleanup_interval = 300  # 5 minutes
        
    async def start(self):
        """Start the connection manager and cleanup task."""
        if not self._cleanup_task:
            self._cleanup_task = asyncio.create_task(self._cleanup_loop())
            logging.info("Started PersistentConnectionManager cleanup task")
    
    async def stop(self):
        """Stop the connection manager and cleanup task."""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
            self._cleanup_task = None
            logging.info("Stopped PersistentConnectionManager cleanup task")
    
    async def create_connection(self, task_id: str, metadata: Dict[str, Any] = None) -> str:
        """
        Create a persistent connection for a task.
        
        Args:
            task_id: Unique identifier for the task
            metadata: Optional metadata about the connection
            
        Returns:
            Connection ID string
        """
        async with self._lock:
            conn_id = f"conn_{task_id}_{int(time.time())}"
            self.active_connections[conn_id] = {
                "task_id": task_id,
                "created_at": time.time(),
                "last_active": time.time(),
                "status": "active"
            }
            if metadata:
                self.connection_metadata[conn_id] = metadata
            logging.info(f"Created persistent connection {conn_id} for task {task_id}")
            return conn_id
    
    async def update_connection(self, conn_id: str, status: str = None, metadata: Dict[str, Any] = None):
        """
        Update connection status and metadata.
        
        Args:
            conn_id: Connection identifier
            status: Optional new status
            metadata: Optional metadata to update
        """
        async with self._lock:
            if conn_id in self.active_connections:
                if status:
                    self.active_connections[conn_id]["status"] = status
                self.active_connections[conn_id]["last_active"] = time.time()
                if metadata:
                    self.connection_metadata[conn_id] = {
                        **(self.connection_metadata.get(conn_id, {})),
                        **metadata
                    }
                logging.debug(f"Updated connection {conn_id} with status={status}")
    
    async def close_connection(self, conn_id: str, reason: str = "completed"):
        """
        Close a persistent connection.
        
        Args:
            conn_id: Connection identifier
            reason: Reason for closing the connection
        """
        async with self._lock:
            if conn_id in self.active_connections:
                self.active_connections[conn_id]["status"] = "closed"
                self.active_connections[conn_id]["closed_at"] = time.time()
                self.active_connections[conn_id]["close_reason"] = reason
                logging.info(f"Closed connection {conn_id} with reason: {reason}")
    
    async def get_connection_info(self, conn_id: str) -> Optional[Dict[str, Any]]:
        """
        Get information about a connection.
        
        Args:
            conn_id: Connection identifier
            
        Returns:
            Dictionary with connection information or None if not found
        """
        async with self._lock:
            if conn_id in self.active_connections:
                return {
                    **self.active_connections[conn_id],
                    "metadata": self.connection_metadata.get(conn_id, {})
                }
            return None
    
    async def list_active_connections(self) -> List[str]:
        """
        Get a list of active connection IDs.
        
        Returns:
            List of active connection IDs
        """
        async with self._lock:
            return [
                conn_id for conn_id, info in self.active_connections.items()
                if info["status"] == "active"
            ]
    
    async def _cleanup_loop(self):
        """Background task to clean up inactive connections."""
        while True:
            try:
                await asyncio.sleep(self._cleanup_interval)
                await self._cleanup_inactive_connections()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logging.error(f"Error in connection cleanup: {str(e)}")
                logging.error(traceback.format_exc())
    
    async def _cleanup_inactive_connections(self):
        """Clean up inactive connections."""
        current_time = time.time()
        inactive_threshold = 3600  # 1 hour
        
        async with self._lock:
            for conn_id, info in list(self.active_connections.items()):
                if (info["status"] == "active" and 
                    current_time - info["last_active"] > inactive_threshold):
                    await self.close_connection(
                        conn_id,
                        reason="inactive_timeout"
                    )
                elif (info["status"] == "closed" and 
                      current_time - info.get("closed_at", 0) > inactive_threshold * 2):
                    del self.active_connections[conn_id]
                    if conn_id in self.connection_metadata:
                        del self.connection_metadata[conn_id]
                    logging.info(f"Removed expired connection {conn_id}")

# Create global instance
connection_manager = PersistentConnectionManager()

# Start connection manager when module loads
async def start_connection_manager():
    """Start the connection manager."""
    await connection_manager.start()

# Register shutdown handler
import atexit
@atexit.register
def cleanup_connection_manager():
    """Clean up the connection manager on shutdown."""
    try:
        asyncio.run(connection_manager.stop())
    except Exception as e:
        logging.error(f"Error stopping connection manager: {str(e)}")

@function_tool
def execute_dynamic_python(code_snippet: str, module_name: str = None, context_variables: dict = None) -> str:
    """
    Executes a Python code snippet with safety constraints within the orchestrator context.
    
    This function allows for dynamic execution of Python code using available modules
    in the codebase. If a module_name is provided, it will attempt to load functions from
    that module to make them available in the execution context.
    
    Args:
        code_snippet: The Python code to execute
        module_name: Optional module name to import and make available for execution
        context_variables: Dictionary of variables to make available to the code
        
    Returns:
        Result of the execution as a string
    """
    try:
        # Create a safe globals dictionary
        safe_globals = {
            "__builtins__": {
                name: getattr(__builtins__, name)
                for name in ['abs', 'all', 'any', 'dir', 'dict', 'filter', 'float', 
                             'format', 'int', 'isinstance', 'len', 'list', 'map', 'max', 
                             'min', 'print', 'range', 'round', 'set', 'sorted', 'str', 
                             'sum', 'tuple', 'zip']
            }
        }
        
        # Add orchestrator module API to safe globals
        safe_globals.update({
            "execute_handler_action": execute_handler_action,
            "route_task_to_appropriate_system": route_task_to_appropriate_system,
            "get_conversation_history": get_conversation_history,
            "get_handler_capabilities": get_handler_capabilities
        })
        
        # Import the specified module if provided
        if module_name:
            try:
                print(f"[DYNAMIC EXECUTION] Attempting to import module: {module_name}")
                
                # First, check if we're importing a known Handler
                if module_name.startswith("Handler."):
                    handler_name = module_name.split(".")[-1]
                    if handler_name.startswith("handler_"):
                        handler_name = handler_name[len("handler_"):]
                        
                    print(f"[DYNAMIC EXECUTION] Detected handler module: {handler_name}")
                    
                    # Get handler info if available
                    try:
                        handler_info = execute_handler_action("handler_system", "get_handler_info", {"handler_name": handler_name})
                        print(f"[DYNAMIC EXECUTION] Handler info obtained: {handler_name}")
                        safe_globals["handler_info"] = handler_info
                    except Exception as handler_error:
                        print(f"[DYNAMIC EXECUTION] Error getting handler info: {str(handler_error)}")
                
                # Try to import the module
                module_parts = module_name.split('.')
                
                # Handle relative imports differently
                if module_name.startswith('.'):
                    print(f"[DYNAMIC EXECUTION] Relative import not supported: {module_name}")
                else:
                    # Try absolute import
                    try:
                        import importlib
                        module = importlib.import_module(module_name)
                        
                        # Add the module to safe globals
                        safe_globals[module_parts[-1]] = module
                        print(f"[DYNAMIC EXECUTION] Successfully imported module: {module_name}")
                        
                        # Check if intelligence module is available
                        if orchestrator_agent and "intelligence" in orchestrator_agent:
                            intelligence_module = orchestrator_agent.get("intelligence")
                            
                            # Get JSON schemas for the module if available
                            if hasattr(intelligence_module, 'get_weighted_schemas_for_module'):
                                try:
                                    # Get weighted schemas (includes usage stats)
                                    schemas = intelligence_module.get_weighted_schemas_for_module(module_name)
                                    if schemas:
                                        print(f"[DYNAMIC EXECUTION] Found weighted JSON schemas for {len(schemas)} functions in module")
                                        safe_globals["function_schemas"] = schemas
                                        
                                        # Check if the task description is provided in context
                                        task_description = None
                                        if context_variables and "task_description" in context_variables:
                                            task_description = context_variables["task_description"]
                                        
                                        # Find best function for task if task description is provided
                                        if task_description and hasattr(intelligence_module, 'find_best_function_for_task'):
                                            try:
                                                best_module, best_func, best_schema, score = intelligence_module.find_best_function_for_task(
                                                    task_description, module_name
                                                )
                                                
                                                if best_func and score > 0.6:  # Only suggest if confidence is reasonable
                                                    print(f"[DYNAMIC EXECUTION] Suggested function for task: {best_func} (score: {score:.2f})")
                                                    safe_globals["suggested_function"] = best_func
                                                    safe_globals["suggested_schema"] = best_schema
                                            except Exception as find_error:
                                                print(f"[DYNAMIC EXECUTION] Error finding best function: {str(find_error)}")
                                        
                                        # Add a helper function to create function tools with tracking
                                        def create_function_call(function_name, **kwargs):
                                            if function_name in schemas:
                                                schema = schemas[function_name]
                                                required_params = schema.get("parameters", {}).get("required", [])
                                                properties = schema.get("parameters", {}).get("properties", {})
                                                
                                                # Check for missing required parameters
                                                missing_params = [param for param in required_params if param not in kwargs]
                                                if missing_params:
                                                    if hasattr(intelligence_module, 'track_schema_usage'):
                                                        intelligence_module.track_schema_usage(module_name, function_name, success=False)
                                                    return f"Error: Missing required parameters: {', '.join(missing_params)}"
                                                
                                                # Try to execute the function
                                                try:
                                                    if hasattr(module, function_name):
                                                        func = getattr(module, function_name)
                                                        result = func(**kwargs)
                                                        
                                                        # Track successful usage
                                                        if hasattr(intelligence_module, 'track_schema_usage'):
                                                            intelligence_module.track_schema_usage(module_name, function_name, success=True)
                                                            
                                                        return result
                                                    else:
                                                        if hasattr(intelligence_module, 'track_schema_usage'):
                                                            intelligence_module.track_schema_usage(module_name, function_name, success=False)
                                                        return f"Error: Function {function_name} not found in module {module_name}"
                                                except Exception as exec_error:
                                                    if hasattr(intelligence_module, 'track_schema_usage'):
                                                        intelligence_module.track_schema_usage(module_name, function_name, success=False)
                                                    return f"Error executing {function_name}: {str(exec_error)}"
                                            else:
                                                return f"Error: No schema found for function {function_name}"
                                        
                                        # Add the helper to safe globals
                                        safe_globals["create_function_call"] = create_function_call
                                except Exception as schema_error:
                                    print(f"[DYNAMIC EXECUTION] Error getting weighted schemas: {str(schema_error)}")
                                    
                                    # Fall back to regular schemas if weighted schemas fail
                                    if hasattr(intelligence_module, 'get_json_schema_for_module'):
                                        try:
                                            schemas = intelligence_module.get_json_schema_for_module(module_name)
                                            if schemas:
                                                print(f"[DYNAMIC EXECUTION] Falling back to regular JSON schemas for {len(schemas)} functions")
                                                safe_globals["function_schemas"] = schemas
                                                
                                                # Add a helper function without tracking
                                                def create_function_call(function_name, **kwargs):
                                                    if function_name in schemas:
                                                        schema = schemas[function_name]
                                                        required_params = schema.get("parameters", {}).get("required", [])
                                                        
                                                        # Check for missing required parameters
                                                        missing_params = [param for param in required_params if param not in kwargs]
                                                        if missing_params:
                                                            return f"Error: Missing required parameters: {', '.join(missing_params)}"
                                                        
                                                        # Try to execute the function
                                                        try:
                                                            if hasattr(module, function_name):
                                                                func = getattr(module, function_name)
                                                                return func(**kwargs)
                                                            else:
                                                                return f"Error: Function {function_name} not found in module {module_name}"
                                                        except Exception as exec_error:
                                                            return f"Error executing {function_name}: {str(exec_error)}"
                                                    else:
                                                        return f"Error: No schema found for function {function_name}"
                                                
                                                safe_globals["create_function_call"] = create_function_call
                                        except Exception as fallback_error:
                                            print(f"[DYNAMIC EXECUTION] Error getting fallback schemas: {str(fallback_error)}")
                            elif hasattr(intelligence_module, 'get_json_schema_for_module'):
                                try:
                                    schemas = intelligence_module.get_json_schema_for_module(module_name)
                                    if schemas:
                                        print(f"[DYNAMIC EXECUTION] Found JSON schemas for {len(schemas)} functions in module")
                                        safe_globals["function_schemas"] = schemas
                                        
                                        # Simple version without tracking
                                        def create_function_call(function_name, **kwargs):
                                            if function_name in schemas:
                                                schema = schemas[function_name]
                                                required_params = schema.get("parameters", {}).get("required", [])
                                                
                                                # Check for missing required parameters
                                                missing_params = [param for param in required_params if param not in kwargs]
                                                if missing_params:
                                                    return f"Error: Missing required parameters: {', '.join(missing_params)}"
                                                
                                                # Try to execute the function
                                                try:
                                                    if hasattr(module, function_name):
                                                        func = getattr(module, function_name)
                                                        return func(**kwargs)
                                                    else:
                                                        return f"Error: Function {function_name} not found in module {module_name}"
                                                except Exception as exec_error:
                                                    return f"Error executing {function_name}: {str(exec_error)}"
                                            else:
                                                return f"Error: No schema found for function {function_name}"
                                        
                                        # Add the helper to safe globals
                                        safe_globals["create_function_call"] = create_function_call
                                except Exception as schema_error:
                                    print(f"[DYNAMIC EXECUTION] Error getting schemas: {str(schema_error)}")
                    except ImportError as import_error:
                        print(f"[DYNAMIC EXECUTION] Error importing module {module_name}: {str(import_error)}")
            except Exception as module_error:
                print(f"[DYNAMIC EXECUTION] Error processing module {module_name}: {str(module_error)}")
        
        # Add context variables if provided
        if context_variables:
            safe_globals.update(context_variables)
        
        # Create locals dictionary
        locals_dict = {}
        
        # Execute the code
        try:
            print(f"[DYNAMIC EXECUTION] Executing code snippet")
            exec(code_snippet, safe_globals, locals_dict)
            
            # Get the result from locals
            result = locals_dict.get('result', 'Code executed successfully but no result variable was set')
            return str(result)
        except Exception as exec_error:
            return f"Error executing code snippet: {str(exec_error)}\n{traceback.format_exc()}"
    except Exception as e:
        return f"Error in dynamic Python execution: {str(e)}\n{traceback.format_exc()}"

@function_tool
def find_best_functions_for_task(task_description: str, limit: int = 5) -> str:
    """
    Find the most suitable functions for a given task description.
    
    This tool uses the weighted schema system to find the best functions for a given task,
    based on both semantic matching and past success rates.
    
    Args:
        task_description: Description of the task to be performed
        limit: Maximum number of functions to suggest
        
    Returns:
        JSON string with recommended functions and their details
    """
    try:
        # Get the orchestrator agent instance
        if not orchestrator_agent or "intelligence" not in orchestrator_agent:
            return json.dumps({
                "error": "Orchestrator intelligence not available",
                "suggestions": []
            })
        
        intelligence = orchestrator_agent.get("intelligence")
        
        # First try to find the best function for this exact task
        suggestions = []
        if hasattr(intelligence, 'find_best_function_for_task'):
            try:
                best_module, best_func, best_schema, score = intelligence.find_best_function_for_task(task_description)
                
                if best_func and score > 0:
                    # Found a direct match
                    suggestion = {
                        "module": best_module,
                        "function": best_func,
                        "score": score,
                        "description": best_schema.get("description", ""),
                        "parameters": best_schema.get("parameters", {}).get("properties", {}),
                        "required_params": best_schema.get("parameters", {}).get("required", [])
                    }
                    
                    # Add usage stats if available
                    if "usage_stats" in best_schema:
                        suggestion["usage_stats"] = best_schema["usage_stats"]
                    
                    suggestions.append(suggestion)
            except Exception as e:
                print(f"Error finding best function: {str(e)}")
        
        # If we still need more suggestions, get the most successful schemas
        if len(suggestions) < limit and hasattr(intelligence, 'get_most_successful_schemas'):
            try:
                success_schemas = intelligence.get_most_successful_schemas(limit=limit)
                
                for full_name, schema in success_schemas.items():
                    # Avoid duplicating the best function if it's already in the suggestions
                    if any(s.get("function") == schema.get("name") for s in suggestions):
                        continue
                    
                    # Split module and function name
                    module_name, func_name = full_name.rsplit(".", 1)
                    
                    suggestion = {
                        "module": module_name,
                        "function": func_name,
                        "score": schema.get("usage_stats", {}).get("weight", 1.0),
                        "description": schema.get("description", ""),
                        "parameters": schema.get("parameters", {}).get("properties", {}),
                        "required_params": schema.get("parameters", {}).get("required", []),
                        "usage_stats": schema.get("usage_stats", {})
                    }
                    
                    suggestions.append(suggestion)
                    
                    # Break if we have enough suggestions
                    if len(suggestions) >= limit:
                        break
            except Exception as e:
                print(f"Error getting successful schemas: {str(e)}")
        
        # If we still don't have enough suggestions, get schemas from all modules
        if len(suggestions) < limit and hasattr(intelligence, 'get_organized_schemas_by_module'):
            try:
                all_schemas = intelligence.get_organized_schemas_by_module(include_weights=True)
                flat_functions = []
                
                # Flatten the module hierarchy to get all functions
                for category_name, category in all_schemas.get("categories", {}).items():
                    for module_name, module in category.get("modules", {}).items():
                        for func_name, schema in module.get("functions", {}).items():
                            # Skip if we already have this function in suggestions
                            if any(s.get("function") == func_name for s in suggestions):
                                continue
                                
                            # Create a flat entry with metadata
                            flat_functions.append({
                                "module": module_name,
                                "function": func_name,
                                "schema": schema,
                                "weight": schema.get("usage_stats", {}).get("weight", 1.0)
                            })
                
                # Sort by weight descending
                flat_functions.sort(key=lambda x: x.get("weight", 0), reverse=True)
                
                # Add top functions to suggestions
                for func in flat_functions[:limit - len(suggestions)]:
                    schema = func["schema"]
                    suggestion = {
                        "module": func["module"],
                        "function": func["function"],
                        "score": func.get("weight", 1.0),
                        "description": schema.get("description", ""),
                        "parameters": schema.get("parameters", {}).get("properties", {}),
                        "required_params": schema.get("parameters", {}).get("required", [])
                    }
                    
                    # Add usage stats if available
                    if "usage_stats" in schema:
                        suggestion["usage_stats"] = schema["usage_stats"]
                    
                    suggestions.append(suggestion)
            except Exception as e:
                print(f"Error getting organized schemas: {str(e)}")
        
        # Format the result
        result = {
            "task": task_description,
            "recommendations": suggestions,
            "total_recommendations": len(suggestions)
        }
        
        # Add example usage
        if suggestions:
            top_suggestion = suggestions[0]
            result["example_usage"] = {
                "module": top_suggestion["module"],
                "function": top_suggestion["function"],
                "usage": f"from {top_suggestion['module']} import {top_suggestion['function']}\n\n"
                        f"# Example usage of {top_suggestion['function']}\n"
                        f"result = {top_suggestion['function']}("
                        + ", ".join([f"{param}='value'" for param in top_suggestion.get("required_params", [])])
                        + ")"
            }
        
        return json.dumps(result, indent=2)
    except Exception as e:
        return json.dumps({
            "error": str(e),
            "suggestions": []
        })

@function_tool
def call_function_with_schema(module_name: str, function_name: str, parameters: dict = None) -> str:
    """
    Call a function directly using its schema for validation and tracking.
    
    This tool allows direct invocation of a function from any module that has a schema,
    with validation of parameters and tracking of success/failure for weighting.
    
    Args:
        module_name: The name of the module containing the function
        function_name: The name of the function to call
        parameters: Dictionary of parameters to pass to the function
        
    Returns:
        JSON string with the result or error information
    """
    if parameters is None:
        parameters = {}
    
    try:
        # Get the orchestrator agent instance
        if not orchestrator_agent or "intelligence" not in orchestrator_agent:
            return json.dumps({
                "success": False,
                "error": "Orchestrator intelligence not available"
            })
        
        intelligence = orchestrator_agent.get("intelligence")
        
        # Get the schema for the function
        schemas = None
        if hasattr(intelligence, 'get_weighted_schemas_for_module'):
            schemas = intelligence.get_weighted_schemas_for_module(module_name)
        elif hasattr(intelligence, 'get_schemas_for_module'):
            schemas = intelligence.get_schemas_for_module(module_name)
            
        if not schemas or function_name not in schemas:
            return json.dumps({
                "success": False,
                "error": f"No schema found for function {function_name} in module {module_name}"
            })
        
        schema = schemas[function_name]
        
        # Validate parameters against schema
        required_params = schema.get("parameters", {}).get("required", [])
        missing_params = [param for param in required_params if param not in parameters]
        
        if missing_params:
            # Track failure if the intelligence module supports it
            if hasattr(intelligence, 'track_schema_usage'):
                intelligence.track_schema_usage(module_name, function_name, success=False)
                
            return json.dumps({
                "success": False,
                "error": f"Missing required parameters: {', '.join(missing_params)}",
                "required_params": required_params,
                "provided_params": list(parameters.keys())
            })
        
        # Import the module and get the function
        try:
            import importlib
            module = importlib.import_module(module_name)
            
            if not hasattr(module, function_name):
                # Track failure
                if hasattr(intelligence, 'track_schema_usage'):
                    intelligence.track_schema_usage(module_name, function_name, success=False)
                    
                return json.dumps({
                    "success": False,
                    "error": f"Function {function_name} not found in module {module_name}"
                })
            
            func = getattr(module, function_name)
            
            # Call the function
            start_time = time.time()
            result = func(**parameters)
            elapsed_time = time.time() - start_time
            
            # Track success
            if hasattr(intelligence, 'track_schema_usage'):
                intelligence.track_schema_usage(module_name, function_name, success=True)
            
            # Handle different result types
            if isinstance(result, dict):
                # Add metadata and return
                result_with_meta = {
                    "success": True,
                    "result": result,
                    "elapsed_time": elapsed_time,
                    "function": function_name,
                    "module": module_name
                }
                return json.dumps(result_with_meta)
            else:
                # Convert to string if not JSON serializable
                return json.dumps({
                    "success": True,
                    "result": str(result),
                    "elapsed_time": elapsed_time,
                    "function": function_name,
                    "module": module_name
                })
        except ImportError:
            # Track failure
            if hasattr(intelligence, 'track_schema_usage'):
                intelligence.track_schema_usage(module_name, function_name, success=False)
                
            return json.dumps({
                "success": False,
                "error": f"Module {module_name} could not be imported"
            })
        except Exception as e:
            # Track failure
            if hasattr(intelligence, 'track_schema_usage'):
                intelligence.track_schema_usage(module_name, function_name, success=False)
                
            return json.dumps({
                "success": False,
                "error": f"Error executing function: {str(e)}",
                "traceback": traceback.format_exc()
            })
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"Error in call_function_with_schema: {str(e)}",
            "traceback": traceback.format_exc()
        })

@function_tool
def get_tools_for_task(task_description: str, limit: int = 5) -> str:
    """
    Get the best OpenAI tool definitions for a specific task based on semantic matching and past success.
    
    This function finds the most relevant tools based on your task description and returns them
    in OpenAI's tool format, ready to be used with function calling.
    
    Args:
        task_description: Description of what you're trying to do
        limit: Maximum number of tools to return (default: 5)
        
    Returns:
        JSON string containing the OpenAI tool definitions for the best matching functions
    """
    try:
        # Get orchestrator intelligence instance
        from Jarvis_Agent_SDK.orchestrator_intelligence import init_orchestrator_intelligence
        intelligence = init_orchestrator_intelligence()
        
        if not intelligence:
            return json.dumps({
                "success": False,
                "error": "Failed to initialize orchestrator intelligence"
            })
        
        # Get best tools for the task
        if hasattr(intelligence, 'get_best_tools_for_task'):
            tools = intelligence.get_best_tools_for_task(task_description, limit)
            
            # Format the result
            result = {
                "success": True,
                "tools_count": len(tools),
                "tools": tools
            }
            
            return json.dumps(result, indent=2)
        else:
            return json.dumps({
                "success": False,
                "error": "Orchestrator intelligence doesn't support tools generation"
            })
    
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"Error getting tools: {str(e)}"
        })

@function_tool
def execute_gpt_with_tools(query: str, task_description: str = None, limit: int = 5, model: str = "gpt-4-turbo", 
                         journey_id: str = None, maintain_focus: bool = True) -> str:
    """
    Execute a GPT query with automatically selected optimal tools based on the task.
    
    This function:
    1. Analyzes your task to determine the most relevant tools
    2. Calls GPT with these tools enabled for optimal function calling
    3. Handles the execution of any function calls made by GPT
    4. Maintains context and focus for multi-step operations
    
    Args:
        query: The specific query or question to ask GPT
        task_description: Optional high-level description of what you're trying to accomplish
                         (improves tool selection, defaults to query if not provided)
        limit: Maximum number of tools to provide to GPT (default: 5)
        model: GPT model to use (default: gpt-4-turbo)
        journey_id: Optional journey ID for context tracking with existing tasks
        maintain_focus: Create/use a TaskContextManager to prevent context drift (default: True)
        
    Returns:
        JSON string with GPT's response and any function call results
    """
    try:
        import openai
        from openai import OpenAI
        import json
        import os
        
        # Get the OpenAI API key
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            try:
                from Core.config import load_api_key
                api_key = load_api_key("OPENAI")
            except ImportError:
                pass
                
        if not api_key:
            return json.dumps({
                "success": False,
                "error": "OpenAI API key not found"
            })
        
        # Use task_description if provided, otherwise use query
        task = task_description or query
        
        # Set up task context if needed
        task_context = None
        task_context_message = ""
        if maintain_focus:
            if journey_id:
                # Get existing task context
                task_context_json = get_task_context(journey_id)
                task_context_data = json.loads(task_context_json)
                
                if task_context_data.get("success"):
                    task_context = task_context_data
                    
                    # Extract relevant context for the system message
                    context = task_context_data.get("context", {})
                    original_task = context.get("original_task", {})
                    completed_steps = context.get("completed_steps", [])
                    current_step = context.get("current_step", {})
                    remaining_steps = context.get("remaining_steps", [])
                    
                    # Format context for the system message
                    task_context_message = f"\n\nIMPORTANT CONTEXT TO MAINTAIN FOCUS:\n"
                    task_context_message += f"Original task: {original_task.get('description')}\n\n"
                    
                    if completed_steps:
                        task_context_message += "Completed steps:\n"
                        for idx, step in enumerate(completed_steps):
                            task_context_message += f"✓ {idx+1}. {step.get('description')}\n"
                        task_context_message += "\n"
                    
                    if current_step:
                        task_context_message += f"Current step: {current_step.get('description')}\n\n"
                    
                    if remaining_steps:
                        task_context_message += "Remaining steps:\n"
                        for idx, step in enumerate(remaining_steps):
                            task_context_message += f"□ {idx+1}. {step.get('description')}\n"
                        task_context_message += "\n"
                    
                    task_context_message += "FOCUS ON THE CURRENT STEP AND MAINTAIN CONTEXT OF THE ORIGINAL TASK."
            else:
                # Create new task context
                task_context_json = create_task_context(task)
                task_context_data = json.loads(task_context_json)
                
                if task_context_data.get("success"):
                    task_context = task_context_data
                    journey_id = task_context_data.get("journey_id")
        
        # Get tools for the task
        tools_json = get_tools_for_task(task, limit)
        tools_data = json.loads(tools_json)
        
        if not tools_data.get("success", False):
            return json.dumps({
                "success": False,
                "error": f"Failed to get tools: {tools_data.get('error', 'Unknown error')}"
            })
        
        tools = tools_data.get("tools", [])
        
        # Initialize OpenAI client
        client = OpenAI(api_key=api_key)
        
        # Create the messages
        system_content = "You are a helpful assistant with access to specialized functions. Use them when appropriate to complete tasks."
        
        # Add task context to system message if available
        if task_context_message:
            system_content += task_context_message
        
        messages = [
            {"role": "system", "content": system_content},
            {"role": "user", "content": query}
        ]
        
        # Call the API with tools
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            tools=tools,
            tool_choice="auto"
        )
        
        # Process the response
        message = response.choices[0].message
        content = message.content
        
        # Handle tool calls if present
        if hasattr(message, "tool_calls") and message.tool_calls:
            tool_results = []
            
            # Update task context with in-progress status if we're tracking
            if journey_id and maintain_focus:
                # Find the first pending step to mark as in-progress
                remaining_context = task_context.get("context", {}).get("remaining_steps", [])
                if remaining_context:
                    first_step = remaining_context[0]
                    update_task_progress(
                        journey_id=journey_id,
                        step_id=first_step.get("id"),
                        status="in_progress"
                    )
            
            for tool_call in message.tool_calls:
                function_name = tool_call.function.name
                function_args = json.loads(tool_call.function.arguments)
                
                # Execute the function
                try:
                    # Get the function to call
                    function_result = call_function_with_schema(
                        "Unknown",  # We don't know the module name from just the function name
                        function_name,
                        function_args
                    )
                    
                    # Parse the result
                    if isinstance(function_result, str):
                        try:
                            function_result = json.loads(function_result)
                        except json.JSONDecodeError:
                            pass
                    
                    tool_results.append({
                        "function_name": function_name,
                        "arguments": function_args,
                        "result": function_result
                    })
                    
                    # Add the function call result to messages
                    messages.append({
                        "role": "assistant",
                        "content": None,
                        "tool_calls": [
                            {
                                "id": tool_call.id,
                                "type": "function",
                                "function": {
                                    "name": function_name,
                                    "arguments": tool_call.function.arguments
                                }
                            }
                        ]
                    })
                    
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": json.dumps(function_result)
                    })
                    
                except Exception as e:
                    tool_results.append({
                        "function_name": function_name,
                        "arguments": function_args,
                        "error": str(e)
                    })
                    
                    # Add the error result to messages
                    messages.append({
                        "role": "assistant",
                        "content": None,
                        "tool_calls": [
                            {
                                "id": tool_call.id,
                                "type": "function",
                                "function": {
                                    "name": function_name,
                                    "arguments": tool_call.function.arguments
                                }
                            }
                        ]
                    })
                    
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": json.dumps({"error": str(e)})
                    })
            
            # Get the final response after function calls
            final_response = client.chat.completions.create(
                model=model,
                messages=messages
            )
            
            final_content = final_response.choices[0].message.content
            
            # Update task context with completed status if we're tracking
            if journey_id and maintain_focus:
                # Find the first in-progress step to mark as completed
                current_context = json.loads(get_task_context(journey_id))
                if current_context.get("success"):
                    current_step = current_context.get("context", {}).get("current_step")
                    if current_step:
                        update_task_progress(
                            journey_id=journey_id,
                            step_id=current_step.get("id"),
                            status="completed",
                            result={
                                "tool_results": tool_results,
                                "final_response": final_content
                            }
                        )
            
            result = {
                "success": True,
                "initial_response": content,
                "tool_calls": tool_results,
                "final_response": final_content
            }
            
            # Add journey_id if available
            if journey_id:
                result["journey_id"] = journey_id
                
            return json.dumps(result, indent=2)
        else:
            # No tool calls, just return the response
            result = {
                "success": True,
                "response": content
            }
            
            # Add journey_id if available
            if journey_id:
                result["journey_id"] = journey_id
                
            return json.dumps(result, indent=2)
    
    except Exception as e:
        import traceback
        return json.dumps({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }, indent=2)

class TaskContextManager:
    """
    Manages task context to maintain focus during multi-step operations.
    
    This class integrates with existing tracking infrastructure (BoardRoom, workspace sharing, 
    journey tracking) to create and maintain a structured plan for complex tasks, ensuring 
    agents don't lose focus or drift from original objectives.
    """
    
    def __init__(self, journey_id=None, session_id=None, workspace_id=None):
        """
        Initialize the task context manager.
        
        Args:
            journey_id: Optional existing journey ID to associate with
            session_id: Optional session ID for context tracking
            workspace_id: Optional workspace ID for persistence
        """
        self.journey_id = journey_id or f"task_{int(time.time())}_{uuid.uuid4().hex[:8]}"
        self.session_id = session_id
        self.workspace_id = workspace_id
        self.original_task = None
        self.task_plan = []
        self.subtasks = []
        self.completed_subtasks = []
        self.current_subtask = None
        self.status = "initialized"
        self.start_time = time.time()
        self.updated_time = time.time()
        self.metadata = {}
        self.notes = []
        self._initialize_tracking()
    
    def _initialize_tracking(self):
        """Initialize tracking for this task context"""
        try:
            # Start journey tracking if not already tracked
            if not self.journey_id.startswith("journey_"):
                if track_request_journey:
                    track_request_journey(
                        journey_id=self.journey_id,
                        system_id="task_context_manager",
                        journey_type="complex_task"
                    )
                elif track_request_journey_interface:
                    track_request_journey_interface(
                        journey_id=self.journey_id,
                        system_id="task_context_manager",
                        journey_type="complex_task"
                    )
                
                # First tracking step
                track_journey_step(
                    journey_id=self.journey_id,
                    step_name="task_context_initialized",
                    description="Task context manager initialized",
                    step_type="initialization",
                    input_data={
                        "session_id": self.session_id,
                        "workspace_id": self.workspace_id
                    }
                )
                
            # Add task context to workspace if available
            workspace_sharing = get_workspace_sharing()
            if workspace_sharing and self.workspace_id:
                try:
                    workspace_sharing.add_attribute_sync(
                        workspace_id=self.workspace_id,
                        attribute_name="task_context",
                        attribute_value={
                            "journey_id": self.journey_id,
                            "created_at": self.start_time,
                            "status": self.status
                        }
                    )
                except Exception as e:
                    logging.warning(f"Could not add task context to workspace: {str(e)}")
        except Exception as e:
            logging.warning(f"Failed to initialize task tracking: {str(e)}")
    
    def set_original_task(self, task_description, task_parameters=None):
        """
        Set the original task description and parameters.
        
        Args:
            task_description: Detailed description of the task
            task_parameters: Optional parameters for the task
        
        Returns:
            Self for method chaining
        """
        self.original_task = {
            "description": task_description,
            "parameters": task_parameters or {},
            "timestamp": time.time()
        }
        
        # Update journey state
        try:
            update_journey_state(
                journey_id=self.journey_id,
                state="task_defined",
                metadata={
                    "task_description": task_description[:100] + "..." if len(task_description) > 100 else task_description,
                    "has_parameters": bool(task_parameters)
                }
            )
            
            # Track the task definition step
            track_journey_step(
                journey_id=self.journey_id,
                step_name="original_task_defined",
                description="Original task defined",
                step_type="task_definition",
                input_data={
                    "task_description": task_description,
                    "parameters": task_parameters
                }
            )
        except Exception as e:
            logging.warning(f"Failed to track original task: {str(e)}")
            
        return self
    
    def create_task_plan(self, steps=None):
        """
        Create a task plan with multiple steps.
        
        Args:
            steps: Optional list of step descriptions
            
        Returns:
            Self for method chaining
        """
        # Generate step IDs for each step
        self.task_plan = []
        
        if steps:
            for idx, step_description in enumerate(steps):
                step_id = f"step_{self.journey_id}_{idx}"
                self.task_plan.append({
                    "id": step_id,
                    "index": idx,
                    "description": step_description,
                    "status": "pending",
                    "created_at": time.time(),
                    "updated_at": time.time()
                })
        
        # Update journey state
        self.status = "planned"
        self.updated_time = time.time()
        
        try:
            # Track the plan creation
            update_journey_state(
                journey_id=self.journey_id,
                state="task_planned",
                metadata={
                    "steps_count": len(self.task_plan),
                    "task_description": self.original_task["description"][:100] + "..." if self.original_task and len(self.original_task["description"]) > 100 else "Unknown"
                }
            )
            
            # Track each step in the journey
            for step in self.task_plan:
                track_journey_step(
                    journey_id=self.journey_id,
                    step_name=f"plan_step_{step['index']}",
                    description=step["description"],
                    step_type="planned_step",
                    input_data={
                        "step_id": step["id"],
                        "index": step["index"]
                    }
                )
        except Exception as e:
            logging.warning(f"Failed to track task plan: {str(e)}")
            
        return self
    
    def start_step(self, step_id=None, step_index=None):
        """
        Start a specific step in the task plan.
        
        Args:
            step_id: ID of the step to start
            step_index: Index of the step to start (alternative to step_id)
            
        Returns:
            The started step or None if not found
        """
        # Find the step
        step = None
        if step_id:
            for s in self.task_plan:
                if s["id"] == step_id:
                    step = s
                    break
        elif step_index is not None and 0 <= step_index < len(self.task_plan):
            step = self.task_plan[step_index]
        
        if not step:
            logging.warning(f"Step not found: id={step_id}, index={step_index}")
            return None
            
        # Update step status
        step["status"] = "in_progress"
        step["start_time"] = time.time()
        self.current_subtask = step
        
        # Track step start
        try:
            track_journey_step(
                journey_id=self.journey_id,
                step_name=f"task_step_started_{step['id']}",
                description=f"Started task step: {step['description'][:50]}...",
                step_type="execution",
                input_data={
                    "step": step
                }
            )
        except Exception as e:
            logging.warning(f"Failed to track step start: {str(e)}")
            
        return step
        
    def complete_step(self, step_id=None, step_index=None, result=None):
        """
        Mark a step as completed.
        
        Args:
            step_id: ID of the step to complete
            step_index: Index of the step to complete (alternative to step_id)
            result: Optional result data from the step
            
        Returns:
            The completed step or None if not found
        """
        # Find the step
        step = None
        if step_id:
            for s in self.task_plan:
                if s["id"] == step_id:
                    step = s
                    break
        elif step_index is not None and 0 <= step_index < len(self.task_plan):
            step = self.task_plan[step_index]
        elif self.current_subtask:
            step = self.current_subtask
            
        if not step:
            logging.warning(f"Step not found for completion: id={step_id}, index={step_index}")
            return None
            
        # Update step status
        step["status"] = "completed"
        step["end_time"] = time.time()
        if "start_time" in step:
            step["duration"] = step["end_time"] - step["start_time"]
        if result:
            step["result"] = result
            
        # Add to completed steps
        self.completed_subtasks.append(step)
        if self.current_subtask and self.current_subtask["id"] == step["id"]:
            self.current_subtask = None
            
        # Check if all steps are complete
        all_completed = all(s["status"] == "completed" for s in self.task_plan)
        
        # Track step completion
        try:
            track_journey_step(
                journey_id=self.journey_id,
                step_name=f"task_step_completed_{step['id']}",
                description=f"Completed task step: {step['description'][:50]}...",
                step_type="completion",
                output_data={
                    "step": step,
                    "result": result,
                    "all_steps_completed": all_completed
                }
            )
            
            # Update journey state if all steps complete
            if all_completed:
                update_journey_state(
                    journey_id=self.journey_id,
                    state="completed",
                    metadata={
                        "completed_steps": len(self.completed_subtasks),
                        "completion_time": time.time()
                    }
                )
        except Exception as e:
            logging.warning(f"Failed to track step completion: {str(e)}")
            
        return step
        
    def add_note(self, note):
        """
        Add a note to the task context.
        
        Args:
            note: Note text or data to add
            
        Returns:
            List of all notes
        """
        note_entry = {
            "timestamp": time.time(),
            "note": note
        }
        self.notes.append(note_entry)
        return self.notes
        
    def get_task_summary(self):
        """
        Get a summary of the task context.
        
        Returns:
            Dictionary with task context summary
        """
        # Count steps by status
        step_counts = {
            "total": len(self.task_plan),
            "completed": len([s for s in self.task_plan if s["status"] == "completed"]),
            "in_progress": len([s for s in self.task_plan if s["status"] == "in_progress"]),
            "pending": len([s for s in self.task_plan if s["status"] == "pending"])
        }
        
        # Calculate progress percentage
        progress = 0
        if step_counts["total"] > 0:
            progress = (step_counts["completed"] / step_counts["total"]) * 100
            
        return {
            "journey_id": self.journey_id,
            "original_task": self.original_task["description"] if self.original_task else None,
            "progress": progress,
            "step_counts": step_counts,
            "current_step": self.current_subtask,
            "elapsed_time": time.time() - self.start_time,
            "notes_count": len(self.notes)
        }
        
    def get_next_steps(self):
        """
        Get the next pending steps.
        
        Returns:
            List of pending steps
        """
        return [s for s in self.task_plan if s["status"] == "pending"]
        
    def get_remaining_task_context(self):
        """
        Get the context needed to continue the task.
        
        Returns:
            Dictionary with current state and remaining steps
        """
        return {
            "original_task": self.original_task,
            "completed_steps": self.completed_subtasks,
            "current_step": self.current_subtask,
            "remaining_steps": self.get_next_steps(),
            "notes": self.notes
        }
    
    def complete_task(self, final_result=None):
        """
        Mark the entire task as completed.
        
        Args:
            final_result: Optional final result data
            
        Returns:
            Summary of completed task
        """
        # Mark any remaining steps as skipped
        for step in self.task_plan:
            if step["status"] == "pending":
                step["status"] = "skipped"
                
        self.status = "completed"
        self.updated_time = time.time()
        
        # Create completion summary
        summary = {
            "journey_id": self.journey_id,
            "original_task": self.original_task,
            "steps_summary": {
                "total": len(self.task_plan),
                "completed": len([s for s in self.task_plan if s["status"] == "completed"]),
                "skipped": len([s for s in self.task_plan if s["status"] == "skipped"])
            },
            "elapsed_time": time.time() - self.start_time,
            "result": final_result
        }
        
        # Complete journey tracking
        try:
            # Track task completion
            track_journey_step(
                journey_id=self.journey_id,
                step_name="task_completed",
                description="Task completed",
                step_type="completion",
                output_data=summary
            )
            
            # Complete journey
            complete_journey(
                journey_id=self.journey_id,
                success=True,
                result=final_result,
                metrics={
                    "completion_time": time.time(),
                    "total_steps": len(self.task_plan),
                    "completed_steps": len([s for s in self.task_plan if s["status"] == "completed"]),
                    "skipped_steps": len([s for s in self.task_plan if s["status"] == "skipped"]),
                    "elapsed_time": time.time() - self.start_time
                }
            )
            
            # Update workspace if available
            workspace_sharing = get_workspace_sharing()
            if workspace_sharing and self.workspace_id:
                try:
                    workspace_sharing.update_attribute_sync(
                        workspace_id=self.workspace_id,
                        attribute_name="task_context",
                        attribute_value={
                            "journey_id": self.journey_id,
                            "created_at": self.start_time,
                            "completed_at": time.time(),
                            "status": "completed",
                            "steps_completed": len([s for s in self.task_plan if s["status"] == "completed"]),
                            "steps_total": len(self.task_plan)
                        }
                    )
                except Exception as e:
                    logging.warning(f"Could not update workspace with task completion: {str(e)}")
        except Exception as e:
            logging.warning(f"Failed to complete task tracking: {str(e)}")
            
        return summary

@function_tool
def create_task_context(task_description: str, steps: List[str] = None, session_id: str = None) -> str:
    """
    Create a task context to maintain focus during complex multi-step tasks.
    
    This creates a structured plan and tracking for complex tasks to ensure
    that GPT agents don't lose focus or drift from the original objectives.
    
    Args:
        task_description: The main task description/objective
        steps: Optional list of steps to complete the task
        session_id: Optional session ID for context tracking
        
    Returns:
        JSON string with task context information including journey_id
    """
    try:
        # Create task context manager
        task_context = TaskContextManager(session_id=session_id)
        
        # Set the original task
        task_context.set_original_task(task_description)
        
        # Create task plan if steps provided
        if steps:
            task_context.create_task_plan(steps)
            
        # Get task summary
        summary = task_context.get_task_summary()
        
        return json.dumps({
            "success": True,
            "message": "Task context created successfully",
            "journey_id": task_context.journey_id,
            "summary": summary
        }, indent=2)
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"Failed to create task context: {str(e)}",
            "traceback": traceback.format_exc()
        }, indent=2)

@function_tool
def update_task_progress(journey_id: str, step_index: int = None, step_id: str = None, 
                       status: str = "completed", result: dict = None) -> str:
    """
    Update the progress of a task being tracked with TaskContextManager.
    
    This function updates the status of a specific step in the task plan
    and maintains the focus on the original task objectives.
    
    Args:
        journey_id: The journey ID of the task context
        step_index: The index of the step to update (starting from 0)
        step_id: Alternative to step_index - the ID of the step to update
        status: The new status (completed, in_progress, failed)
        result: Optional result data from the step
        
    Returns:
        JSON string with updated task context information
    """
    try:
        # Retrieve the task context from journey tracking
        task_context_data = {}
        
        try:
            # Try to get journey data
            journey_data = get_journey_data(journey_id)
            
            if journey_data and "metadata" in journey_data:
                metadata = journey_data.get("metadata", {})
                if "task_context" in metadata:
                    task_context_data = metadata["task_context"]
        except Exception as e:
            logging.warning(f"Could not retrieve journey data: {str(e)}")
        
        # Create task context manager with existing journey_id
        task_context = TaskContextManager(journey_id=journey_id)
        
        # Update the step based on the provided status
        if status == "in_progress":
            step = task_context.start_step(step_id=step_id, step_index=step_index)
        elif status == "completed":
            step = task_context.complete_step(step_id=step_id, step_index=step_index, result=result)
        
        # Get updated task summary
        summary = task_context.get_task_summary()
        remaining = task_context.get_remaining_task_context()
        
        return json.dumps({
            "success": True,
            "message": f"Task step updated to {status}",
            "journey_id": journey_id,
            "summary": summary,
            "remaining_context": remaining
        }, indent=2)
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"Failed to update task progress: {str(e)}",
            "traceback": traceback.format_exc()
        }, indent=2)

@function_tool
def get_task_context(journey_id: str) -> str:
    """
    Get the current context for a task to maintain focus on the original goal.
    
    This retrieves the current state of a task including the original objective,
    completed steps, current step, and remaining steps to ensure the agent
    stays focused on the overall goal.
    
    Args:
        journey_id: The journey ID of the task context
        
    Returns:
        JSON string with current task context information
    """
    try:
        # Create task context manager with existing journey_id
        task_context = TaskContextManager(journey_id=journey_id)
        
        # Get task summary and remaining context
        summary = task_context.get_task_summary()
        remaining = task_context.get_remaining_task_context()
        
        return json.dumps({
            "success": True,
            "journey_id": journey_id,
            "summary": summary,
            "context": remaining
        }, indent=2)
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"Failed to get task context: {str(e)}",
            "traceback": traceback.format_exc()
        }, indent=2)

@function_tool
def complete_task_with_result(journey_id: str, final_result: dict) -> str:
    """
    Mark a tracked task as completed with final results.
    
    This finalizes a task being tracked with TaskContextManager and
    records the final results and completion metrics.
    
    Args:
        journey_id: The journey ID of the task context
        final_result: The final result data
        
    Returns:
        JSON string with completed task summary
    """
    try:
        # Create task context manager with existing journey_id
        task_context = TaskContextManager(journey_id=journey_id)
        
        # Complete the task
        completion_summary = task_context.complete_task(final_result)
        
        return json.dumps({
            "success": True,
            "message": "Task completed successfully",
            "journey_id": journey_id,
            "summary": completion_summary
        }, indent=2)
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"Failed to complete task: {str(e)}",
            "traceback": traceback.format_exc()
        }, indent=2)

@function_tool
def execute_multi_step_task(task_description: str, steps: List[str] = None, initial_query: str = None, 
                           model: str = "gpt-4-turbo", auto_execute: bool = True, 
                           team_id: int = None, workspace_name: str = None) -> str:
    """
    Execute a complex multi-step task while maintaining focus on the original goal.
    
    This function:
    1. Creates a structured plan with tracked steps
    2. Maintains context between steps
    3. Ensures the task completes according to the original requirements
    4. Prevents context drift and loss of focus during complex operations
    5. Enables team collaboration through workspace sharing
    
    Args:
        task_description: High-level description of what to accomplish
        steps: Optional list of steps for completing the task (will be auto-generated if not provided)
        initial_query: The first question to ask GPT (defaults to planning if not provided)
        model: GPT model to use (default: gpt-4-turbo)
        auto_execute: Whether to automatically execute the first step (default: True)
        team_id: Optional team ID for collaborative tasks
        workspace_name: Optional name for the workspace (defaults to task-based name)
        
    Returns:
        JSON string with task context, plan, and initial execution results
    """
    try:
        import time
        import hashlib
        import json
        import re
        
        # Create a workspace for this task if workspace_sharing is available
        workspace_id = None
        workspace_sharing = get_workspace_sharing()
        
        if workspace_sharing:
            try:
                # Generate a workspace name if not provided
                if not workspace_name:
                    task_hash = hashlib.md5(task_description.encode()).hexdigest()[:8]
                    workspace_name = f"Task: {task_description[:30]}..." if len(task_description) > 30 else f"Task: {task_description}"
                
                # Create the workspace
                workspace_result = workspace_sharing.create_workspace_sync(
                    name=workspace_name,
                    description=task_description,
                    metadata={
                        "task_type": "multi_step",
                        "created_at": time.time(),
                        "team_id": team_id
                    }
                )
                
                if workspace_result and isinstance(workspace_result, dict) and "workspace_id" in workspace_result:
                    workspace_id = workspace_result["workspace_id"]
                    logging.info(f"Created workspace {workspace_id} for multi-step task")
                    
                    # If team_id is provided, share the workspace with the team
                    if team_id:
                        sharing_result = workspace_sharing.share_workspace_with_team_sync(
                            workspace_id=workspace_id,
                            team_id=team_id,
                            role=WorkspaceRole.EDITOR.value if hasattr(WorkspaceRole, "EDITOR") else "editor",
                            shared_by=1  # System user
                        )
                        
                        if sharing_result:
                            logging.info(f"Shared workspace {workspace_id} with team {team_id}")
                            
                            # Register task execution in workspace activity
                            workspace_sharing.track_workspace_activity_sync(
                                workspace_id=workspace_id,
                                user_id=1,  # System user
                                action_type="create_multi_step_task",
                                action_details=json.dumps({
                                    "task_description": task_description,
                                    "team_id": team_id,
                                    "has_predefined_steps": bool(steps)
                                })
                            )
            except Exception as e:
                logging.warning(f"Error creating workspace: {e}. Continuing without workspace integration.")
                workspace_id = None
                
        # Create task context and plan
        if steps:
            # Use provided steps
            task_context_json = create_task_context(task_description, steps, session_id=None)
        else:
            # Create basic task context without steps, we'll generate them
            task_context_json = create_task_context(task_description)
            
        task_context_data = json.loads(task_context_json)
        
        if not task_context_data.get("success", False):
            return json.dumps({
                "success": False,
                "error": f"Failed to create task context: {task_context_data.get('error', 'Unknown error')}"
            })
            
        journey_id = task_context_data.get("journey_id")
        
        # Store journey_id in workspace if available
        if workspace_id and workspace_sharing:
            workspace_sharing.add_attribute_sync(
                workspace_id=workspace_id,
                attribute_name="journey_id",
                attribute_value=journey_id
            )
            
            # Update the task context with workspace information
            task_context = TaskContextManager(journey_id=journey_id, workspace_id=workspace_id)
            
            # Add workspace metadata to the task context
            additional_metadata = {
                "workspace_id": workspace_id,
                "team_id": team_id,
                "workspace_name": workspace_name
            }
            
            # Add a note about workspace collaboration
            task_context.add_note(f"Task is collaborative in workspace {workspace_id}")
            
            # If we have workspace information, update task with it
            task_context.metadata.update(additional_metadata)
            
        # If steps weren't provided, ask GPT to create a plan
        if not steps:
            planning_query = f"Create a step-by-step plan for accomplishing this task: {task_description}. " + \
                             "List each step as a numbered list with clear, actionable steps."
                             
            planning_result_json = execute_gpt_with_tools(
                query=planning_query,
                task_description=f"Planning for: {task_description}",
                model=model,
                journey_id=journey_id,
                maintain_focus=True
            )
            
            planning_result = json.loads(planning_result_json)
            
            if planning_result.get("success", False):
                plan_text = planning_result.get("response", "")
                
                # Extract steps from the plan text
                step_lines = []
                for line in plan_text.split('\n'):
                    line = line.strip()
                    # Match numbered list items like "1. Do something" or "1) Do something"
                    if re.match(r'^\d+[\.\)]', line):
                        # Remove the number and keep the step description
                        step_description = re.sub(r'^\d+[\.\)]\s*', '', line)
                        if step_description:
                            step_lines.append(step_description)
                
                # If we extracted steps, update the task context with them
                if step_lines:
                    # Create task plan with the extracted steps
                    task_context = TaskContextManager(journey_id=journey_id, workspace_id=workspace_id)
                    task_context.create_task_plan(step_lines)
                    
                    # Get updated task context
                    task_context_json = get_task_context(journey_id)
                    task_context_data = json.loads(task_context_json)
                    
                    # If we have a workspace, store the plan there too
                    if workspace_id and workspace_sharing:
                        workspace_sharing.add_attribute_sync(
                            workspace_id=workspace_id,
                            attribute_name="task_plan",
                            attribute_value=step_lines
                        )
        
        # Store information about available agents for this task
        if workspace_id and workspace_sharing:
            try:
                # Get agent capabilities from orchestrator_intelligence if available
                from Jarvis_Agent_SDK.orchestrator_intelligence import OrchestrationIntelligence
                intelligence = OrchestrationIntelligence.get_instance()
                
                if intelligence:
                    # Get available agents and their capabilities
                    available_agents = intelligence.get_available_agents()
                    if available_agents:
                        workspace_sharing.add_attribute_sync(
                            workspace_id=workspace_id,
                            attribute_name="available_agents",
                            attribute_value=available_agents
                        )
                        
                        # Register agents with the workspace
                        for agent_id, agent_info in available_agents.items():
                            if isinstance(agent_info, dict) and "capabilities" in agent_info:
                                workspace_sharing.register_agent_sync(
                                    agent_id=agent_id,
                                    agent_name=agent_info.get("name", agent_id),
                                    agent_type=agent_info.get("type", "assistant"),
                                    workspace_id=workspace_id,
                                    capabilities=agent_info.get("capabilities", [])
                                )
            except Exception as e:
                logging.warning(f"Error registering agents with workspace: {e}")
        
        # Start execution if auto_execute is True
        execution_result = None
        if auto_execute:
            # Prepare the initial query
            if not initial_query:
                # Get task context to find the first step
                current_context = json.loads(get_task_context(journey_id))
                if current_context.get("success"):
                    remaining_steps = current_context.get("context", {}).get("remaining_steps", [])
                    if remaining_steps:
                        first_step = remaining_steps[0]
                        initial_query = f"Let's begin with the first step: {first_step.get('description')}. How should we proceed?"
                    else:
                        initial_query = f"Let's begin working on this task: {task_description}. What's the first thing we should do?"
            
            # Execute the first step
            execution_result_json = execute_gpt_with_tools(
                query=initial_query,
                task_description=task_description,
                model=model,
                journey_id=journey_id,
                maintain_focus=True
            )
            
            execution_result = json.loads(execution_result_json)
            
            # Track execution in workspace if available
            if workspace_id and workspace_sharing:
                execution_info = {
                    "step": "initial_execution",
                    "query": initial_query,
                    "success": execution_result.get("success", False),
                    "timestamp": time.time()
                }
                
                if "tool_calls" in execution_result:
                    execution_info["tools_used"] = [tc.get("function_name") for tc in execution_result.get("tool_calls", [])]
                
                workspace_sharing.track_workspace_activity_sync(
                    workspace_id=workspace_id,
                    user_id=1,  # System user
                    action_type="execute_step",
                    action_details=json.dumps(execution_info)
                )
        
        # Return the complete response with task context, plan, and initial execution
        response = {
            "success": True,
            "message": "Multi-step task initialized successfully",
            "journey_id": journey_id,
            "workspace_id": workspace_id,
            "task_description": task_description,
            "task_context": task_context_data,
        }
        
        if team_id:
            response["team_id"] = team_id
            
        if execution_result:
            response["initial_execution"] = execution_result
            
        return json.dumps(response, indent=2)
            
    except Exception as e:
        import traceback
        return json.dumps({
            "success": False,
            "error": f"Failed to execute multi-step task: {str(e)}",
            "traceback": traceback.format_exc()
        }, indent=2)

@function_tool
def continue_multi_step_task(journey_id: str, next_query: str = None, model: str = "gpt-4-turbo",
                           agent_id: str = None, update_team: bool = True) -> str:
    """
    Continue execution of a multi-step task while maintaining focus on the original goal.
    
    This function continues a task started with execute_multi_step_task, ensuring
    context is maintained and the agent doesn't drift from the original objectives.
    It also updates all team members on progress through workspace sharing.
    
    Args:
        journey_id: The journey ID from the execute_multi_step_task function
        next_query: The next question/instruction for continuing the task
        model: GPT model to use (default: gpt-4-turbo)
        agent_id: Optional ID of the agent continuing the task (for tracking)
        update_team: Whether to update team members on progress (default: True)
        
    Returns:
        JSON string with updated task context and execution results
    """
    try:
        import time
        import json
        
        # Get current task context
        task_context_json = get_task_context(journey_id)
        task_context_data = json.loads(task_context_json)
        
        if not task_context_data.get("success", False):
            return json.dumps({
                "success": False,
                "error": f"Failed to retrieve task context: {task_context_data.get('error', 'Unknown error')}"
            })
        
        context = task_context_data.get("context", {})
        original_task = context.get("original_task", {})
        current_step = context.get("current_step", {})
        remaining_steps = context.get("remaining_steps", [])
        
        # Check if we have workspace information in the context
        summary = task_context_data.get("summary", {})
        metadata = {}
        workspace_id = None
        
        # Get a reference to the task context manager 
        task_context = TaskContextManager(journey_id=journey_id)
        
        # Try to get workspace_id from metadata if exists
        if hasattr(task_context, 'metadata') and task_context.metadata and 'workspace_id' in task_context.metadata:
            workspace_id = task_context.metadata.get('workspace_id')
            metadata = task_context.metadata
        
        # If we don't have workspace information but workspace_sharing is available, try to find it
        if not workspace_id:
            workspace_sharing = get_workspace_sharing()
            if workspace_sharing:
                # Try to find workspace with this journey_id as an attribute
                workspaces = workspace_sharing.find_workspaces_by_attribute_sync(
                    attribute_name="journey_id",
                    attribute_value=journey_id
                )
                
                if workspaces and len(workspaces) > 0:
                    workspace_id = workspaces[0].get("id")
                    logging.info(f"Found workspace {workspace_id} for journey {journey_id}")
                    
                    # Update task context with workspace information
                    if workspace_id:
                        metadata["workspace_id"] = workspace_id
                        task_context.metadata.update(metadata)
        
        # Prepare the next query if not provided
        if not next_query:
            if current_step:
                next_query = f"Let's continue with the current step: {current_step.get('description')}. What progress have we made and what should we do next?"
            elif remaining_steps:
                next_step = remaining_steps[0]
                next_query = f"Let's move to the next step: {next_step.get('description')}. How should we approach this?"
            else:
                # All steps completed or no steps defined
                next_query = f"We've been working on: {original_task.get('description')}. What's our next action to complete this task?"
        
        # If we have workspace and team access, update the team on our progress
        if workspace_id and update_team:
            workspace_sharing = get_workspace_sharing()
            if workspace_sharing:
                # Log this continuation in workspace activity
                agent_name = agent_id or "system"
                status_message = f"Continuing task: {current_step.get('description') if current_step else 'Finalizing task'}"
                
                workspace_sharing.track_workspace_activity_sync(
                    workspace_id=workspace_id,
                    user_id=1,  # System user
                    action_type="continue_task",
                    action_details=json.dumps({
                        "journey_id": journey_id,
                        "current_step": current_step.get("id") if current_step else None,
                        "agent_id": agent_id,
                        "remaining_steps": len(remaining_steps),
                        "progress": summary.get("progress", 0),
                        "status_message": status_message,
                        "next_query": next_query
                    })
                )
                
                # If we have an agent_id, track that this agent is working on the task
                if agent_id:
                    workspace_sharing.track_agent_activity_sync(
                        agent_id=agent_id,
                        agent_name=agent_id,  # Use agent_id as name if we don't have a better one
                        action_type="continue_task",
                        details={
                            "journey_id": journey_id,
                            "current_step": current_step.get("id") if current_step else None,
                            "task_description": original_task.get("description")
                        },
                        workspace_id=workspace_id
                    )
        
        # Execute the next step
        execution_result_json = execute_gpt_with_tools(
            query=next_query,
            task_description=original_task.get('description') if original_task else None,
            model=model,
            journey_id=journey_id,
            maintain_focus=True
        )
        
        execution_result = json.loads(execution_result_json)
        
        # Track tool usage in workspace if available
        if workspace_id and "tool_calls" in execution_result and execution_result.get("tool_calls"):
            workspace_sharing = get_workspace_sharing()
            if workspace_sharing:
                for tool_call in execution_result.get("tool_calls", []):
                    workspace_sharing.track_resource_usage_sync(
                        agent_id=agent_id or "gpt",
                        workspace_id=workspace_id,
                        task_id=journey_id,
                        resource_type="tool",
                        usage_details={
                            "function_name": tool_call.get("function_name"),
                            "success": "error" not in tool_call,
                            "timestamp": time.time()
                        }
                    )
        
        # Get updated task context after execution
        updated_context_json = get_task_context(journey_id)
        updated_context = json.loads(updated_context_json)
        
        # Check if all steps are complete
        remaining = updated_context.get("context", {}).get("remaining_steps", [])
        all_completed = len(remaining) == 0
        summary = updated_context.get("summary", {})
        progress = summary.get("progress", 0)
        
        completion_status = {
            "all_steps_completed": all_completed,
            "progress_percentage": progress
        }
        
        # If all completed and we have a workspace, update team on completion
        if all_completed and workspace_id:
            workspace_sharing = get_workspace_sharing()
            if workspace_sharing:
                workspace_sharing.track_workspace_activity_sync(
                    workspace_id=workspace_id,
                    user_id=1,  # System user 
                    action_type="task_completed",
                    action_details=json.dumps({
                        "journey_id": journey_id,
                        "agent_id": agent_id,
                        "completion_time": time.time(),
                        "total_steps_completed": updated_context.get("summary", {}).get("step_counts", {}).get("completed", 0)
                    })
                )
                
                # Update workspace status to completed
                workspace_sharing.update_attribute_sync(
                    workspace_id=workspace_id,
                    attribute_name="task_status",
                    attribute_value="completed"
                )
                
                # Add final results
                if "final_response" in execution_result:
                    workspace_sharing.add_attribute_sync(
                        workspace_id=workspace_id,
                        attribute_name="task_result",
                        attribute_value=execution_result.get("final_response")
                    )
        
        # Return the response with execution results and updated context
        response = {
            "success": True,
            "journey_id": journey_id,
            "workspace_id": workspace_id,
            "execution_result": execution_result,
            "updated_context": updated_context,
            "completion_status": completion_status
        }
        
        return json.dumps(response, indent=2)
            
    except Exception as e:
        import traceback
        return json.dumps({
            "success": False,
            "error": f"Failed to continue multi-step task: {str(e)}",
            "traceback": traceback.format_exc()
        }, indent=2)

async def process_handler_message(message: str, message_type: str = "update", context: Dict[str, Any] = None, journey_id: str = None) -> Dict[str, Any]:
    """
    Process a message from a handler and route it appropriately within the Jarvis system.
    
    This function serves as the central entry point for communication between handlers
    and the Jarvis orchestrator. It handles different message types and provides
    a structured response.
    
    Args:
        message (str): The message content from the handler
        message_type (str): Type of message (e.g., "update", "error", "task_completion")
        context (Dict[str, Any], optional): Additional context for the message
        journey_id (str, optional): ID for tracking this communication journey
        
    Returns:
        Dict[str, Any]: A structured response with at least a 'success' key
    """
    try:
        # Generate a journey ID if none provided
        if not journey_id:
            journey_id = f"handler_message_{int(time.time())}_{generate_request_id()[:8]}"
        
        # Initialize context if needed
        if context is None:
            context = {}
            
        # Add metadata to context
        context.update({
            "received_at": time.time(),
            "orchestrator_id": "jarvis_orchestrator",
            "journey_id": journey_id
        })
        
        # Track the message receipt
        try:
            # Try to get BoardRoom for tracking
            boardroom = get_boardroom_instance()
            if boardroom and hasattr(boardroom, 'track_journey_step'):
                # Determine if it's an async or sync method
                if asyncio.iscoroutinefunction(boardroom.track_journey_step):
                    tracking_result = await boardroom.track_journey_step(
                        journey_id=journey_id,
                        step_name="handler_message_received",
                        description=f"Received {message_type} message from handler",
                        step_type="handler_communication",
                        input_data={
                            "message": message[:500] + "..." if len(message) > 500 else message,
                            "message_type": message_type,
                            "context": context
                        }
                    )
                else:
                    # Call sync version
                    tracking_result = boardroom.track_journey_step(
                        journey_id=journey_id,
                        step_name="handler_message_received",
                        description=f"Received {message_type} message from handler",
                        step_type="handler_communication",
                        input_data={
                            "message": message[:500] + "..." if len(message) > 500 else message,
                            "message_type": message_type,
                            "context": context
                        }
                    )
                # Log tracking result if needed
                if isinstance(tracking_result, dict) and tracking_result.get("success") is False:
                    print(f"[ORCHESTRATOR] Warning: Tracking handler message receipt failed: {tracking_result.get('message', 'Unknown error')}")
        except Exception as track_error:
            print(f"[ORCHESTRATOR] Warning: Could not track handler message receipt: {str(track_error)}")
        
        # Process message based on type
        response = {
            "success": True,
            "message_received": True,
            "journey_id": journey_id,
            "timestamp": time.time()
        }
        
        if message_type == "update":
            # Process system updates
            print(f"[ORCHESTRATOR] Received update message from handler: {message[:100]}...")
            response.update({
                "status": "acknowledged",
                "message": "Update received and processed"
            })
            
        elif message_type == "error_report":
            # Process error reports
            print(f"[ORCHESTRATOR] Received error report from handler: {message[:100]}...")
            
            # Try to parse error details from context
            error_type = "general_error"
            error_details = message
            if "error_type" in context:
                error_type = context["error_type"]
            if "details" in context:
                error_details = context["details"]
                
            response.update({
                "status": "error_logged",
                "error_type": error_type,
                "message": f"Error report received and logged: {error_type}"
            })
            
            # Add to error tracking system if available
            try:
                # Future implementation could integrate with a more comprehensive error tracking system
                print(f"[ERROR TRACKING] {error_type}: {error_details}")
            except Exception as e:
                print(f"[ORCHESTRATOR] Error in error tracking: {str(e)}")
                
        elif message_type == "task_completion":
            # Process task completion notifications
            print(f"[ORCHESTRATOR] Received task completion notification: {message[:100]}...")
            
            # Extract task_id from context if available
            task_id = None
            if "task_id" in context:
                task_id = context["task_id"]
                
            response.update({
                "status": "completed",
                "task_id": task_id,
                "message": "Task completion acknowledged"
            })
            
            # Update task system if available
            try:
                # Future implementation could update a task tracking system
                print(f"[TASK TRACKING] Task {task_id} marked as complete")
            except Exception as e:
                print(f"[ORCHESTRATOR] Error updating task system: {str(e)}")
                
        elif message_type == "query":
            # Process queries from handlers
            print(f"[ORCHESTRATOR] Received query from handler: {message[:100]}...")
            
            response.update({
                "status": "query_processing",
                "message": "Query received and being processed"
            })
            
            # Process query - this could integrate with other systems in the future
            # For now, just acknowledge receipt
            
        else:
            # Default handling for other message types
            print(f"[ORCHESTRATOR] Received message of type {message_type}: {message[:100]}...")
            
            response.update({
                "status": "received",
                "message": f"Message of type {message_type} received"
            })
        
        # Track the response
        try:
            if boardroom and hasattr(boardroom, 'track_journey_step'):
                # Determine if it's an async or sync method
                if asyncio.iscoroutinefunction(boardroom.track_journey_step):
                    tracking_result = await boardroom.track_journey_step(
                        journey_id=journey_id,
                        step_name="handler_message_response",
                        description=f"Sending response to {message_type} message",
                        step_type="handler_communication",
                        output_data=response
                    )
                else:
                    # Call sync version
                    tracking_result = boardroom.track_journey_step(
                        journey_id=journey_id,
                        step_name="handler_message_response",
                        description=f"Sending response to {message_type} message",
                        step_type="handler_communication",
                        output_data=response
                    )
                # Log tracking result if needed
                if isinstance(tracking_result, dict) and tracking_result.get("success") is False:
                    print(f"[ORCHESTRATOR] Warning: Tracking handler message response failed: {tracking_result.get('message', 'Unknown error')}")
        except Exception as track_error:
            print(f"[ORCHESTRATOR] Warning: Could not track handler message response: {str(track_error)}")
            
        return response
            
    except Exception as e:
        error_msg = f"Error processing handler message: {str(e)}"
        print(f"[ORCHESTRATOR] {error_msg}")
        traceback.print_exc()
        
        # Return a structured error response with a success key
        return {
            "success": False,
            "error": error_msg,
            "message_type": message_type,
            "journey_id": journey_id,
            "timestamp": time.time()
        }

# Process task functions for Jarvis Orchestrator - using OrchestratorIntelligence
async def process_task(task: str, trace_name: str = "Jarvis Task", session_id: str = None, bypass_content_filter: bool = False, user_id: str = None) -> str:
    """
    Process a task asynchronously using the unified Jarvis orchestrator with
    intelligence-driven routing.
    
    Args:
        task: The task to process
        trace_name: Optional name for the trace
        session_id: Optional session ID for conversation persistence
        bypass_content_filter: If True, bypass content filtering for certain operations
        
    Returns:
        The result of processing the task
    """
    try:
        # Create journey ID for tracking
        import uuid
        journey_id = f"journey_{int(time.time())}_{uuid.uuid4().hex[:8]}"
        
        # Get or initialize the orchestrator intelligence module
        from Jarvis_Agent_SDK.jarvis_orchestrated_intelligence import init_orchestrator_intelligence
        intelligence = init_orchestrator_intelligence()
        
        # Process the request using intelligence
        result = await intelligence.process_request(task, journey_id)
        
        # Execute the handler with intelligence
        execution_result = await intelligence.execute_handler_with_intelligence(
            request_text=task,
            journey_id=journey_id,
            workspace_id=None,  # Can be parameterized in the future
            user_id=user_id  # ✅ SECURITY FIX: Pass user_id for MCP credential isolation
        )
        
        # If execution was successful, return the result
        if execution_result and "execution_decision" in execution_result:
            decision = execution_result["execution_decision"]
            
            # Check if we should use orchestrator agent for natural language processing
            if (decision["handler_name"] == "orchestrator" and 
                decision["action"] == "process_natural_language"):
                
                # Process using orchestrator agent for bidirectional communication
                print(f"[ORCHESTRATOR] Processing natural language request with orchestrator agent")
                
                # Create or use the provided session ID for context persistence
                if not session_id:
                    session_id = str(uuid.uuid4())
                    print(f"Created new conversation session: {session_id}")
                else:
                    print(f"Using existing conversation session: {session_id}")
                
                # Handle direct execution with the agent
                global orchestrator_agent
                if not orchestrator_agent:
                    # Create a minimal agent if not available
                    from openai import OpenAI
                    client = OpenAI()
                    response = client.chat.completions.create(
                        model="gpt-4",
                        messages=[
                            {"role": "system", "content": "You are Jarvis, a helpful AI assistant."},
                            {"role": "user", "content": task}
                        ]
                    )
                    return response.choices[0].message.content
                
                # Use a specialized agent if configured
                return f"Processed task using intelligence pipeline: {decision['handler_name']}.{decision['action']} (confidence: {decision['confidence']:.2f})"
            
            # Otherwise, execute the selected handler
            try:
                from Handler.handler_all import handler_system
                handler_result = await handler_system.execute_command(
                    decision["handler_name"],
                    decision["action"],
                    {"request": task}  # Basic parameters, can be enhanced
                )
                
                # Format result
                if isinstance(handler_result, dict):
                    result_text = handler_result.get("message", str(handler_result))
                else:
                    result_text = str(handler_result)
                
                # Add Claude's personality to the response - import here to avoid circular imports
                try:
                    from Jarvis_Agent_SDK.response_format import ClaudePersonality
                    import random
                    
                    # Randomly select a personality type with 30% chance of sarcasm
                    if random.random() < 0.3:
                        personality = "SARCASTIC"
                    else:
                        personality = random.choice(list(ClaudePersonality.PERSONALITIES.keys()))
                        
                    # Enhance with Claude's personality (moderate intensity)
                    result_text = ClaudePersonality.enhance_message(
                        message=result_text,
                        personality_type=personality,
                        message_type="RESPONSE",
                        intensity=0.7
                    )
                except Exception as e:
                    print(f"Error adding personality to response: {str(e)}")
                    
                return result_text
            except Exception as e:
                print(f"[ORCHESTRATOR] Error executing handler: {str(e)}")
                traceback.print_exc()
                error_msg = f"Error executing {decision['handler_name']}.{decision['action']}: {str(e)}"
                
                # Add Claude's personality to error messages
                try:
                    from Jarvis_Agent_SDK.response_format import ClaudePersonality
                    error_msg = ClaudePersonality.enhance_message(
                        message=error_msg,
                        personality_type="SARCASTIC",  # Errors are funnier with sarcasm
                        message_type="ERROR",
                        intensity=0.8
                    )
                except Exception:
                    pass  # Just use the original error message if enhancement fails
                    
                return error_msg
        
        return f"Processed request: {result.get('message', str(result))}"
    except Exception as e:
        print(f"[ORCHESTRATOR] Error in process_task: {str(e)}")
        print(traceback.format_exc())
        error_msg = f"Error processing task: {str(e)}"
        
        # Add Claude's personality to error messages
        try:
            from Jarvis_Agent_SDK.response_format import ClaudePersonality
            error_msg = ClaudePersonality.enhance_message(
                message=error_msg,
                personality_type="SARCASTIC",
                message_type="ERROR",
                intensity=0.8
            )
        except Exception:
            pass
            
        return error_msg

def process_task_sync(task: str, trace_name: str = "Jarvis Task", session_id: str = None, bypass_content_filter: bool = False) -> str:
    """
    Process a task synchronously.
    This is a wrapper around the async process_task function.
    
    Args:
        task: The task to process
        trace_name: Optional name for the trace
        session_id: Optional session ID for conversation persistence
        bypass_content_filter: Optional flag to bypass content filtering
        
    Returns:
        String result of processing the task
    """
    try:
        task_data = None
        
        if isinstance(task, dict):
            task_data = task
            # Extract the task string from the dictionary
            if "task" in task_data:
                task = task_data["task"]
            elif "text" in task_data:
                task = task_data["text"]
            else:
                task = str(task_data)
                
        # For dict-style task_data with context, extract workspace_id if available
        workspace_id = None
        if task_data and isinstance(task_data, dict) and "context" in task_data:
            context = task_data["context"]
            if isinstance(context, dict) and "workspace_id" in context:
                workspace_id = context["workspace_id"]
        
        # Safer approach that properly manages the event loop
        import asyncio
        
        async def run_task():
            return await process_task(task, trace_name, session_id, bypass_content_filter)
        
        # Try to get the current event loop, but don't fail if there isn't one
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            # No running event loop
            # Create a new event loop and set it as the current one
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        # Check if we're in a running event loop
        if loop.is_running():
            # We're already in a running event loop, create a future and run it
            future = asyncio.run_coroutine_threadsafe(run_task(), loop)
            return future.result()  # Wait for the result
        else:
            # We have a loop but it's not running
            try:
                return loop.run_until_complete(run_task())
            except Exception as e:
                print(f"Error in event loop: {str(e)}")
                # If there was an error in the loop itself, try with a fresh loop
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                result = loop.run_until_complete(run_task())
                return result
                
    except Exception as e:
        print(f"[ORCHESTRATOR] Error in process_task_sync: {str(e)}")
        print(traceback.format_exc())
        return f"Error processing task synchronously: {str(e)}"

# Function to create stream for task processing (placeholder for API compatibility)
def process_task_with_stream(task: str, trace_name: str = "Jarvis Task", session_id: str = None) -> Dict:
    """
    Process a task with streaming response capability.
    This is a placeholder function that currently just calls process_task_sync
    but returns a dict with the result for API compatibility.
    
    Args:
        task: The task to process
        trace_name: Optional name for the trace
        session_id: Optional session ID for conversation persistence
        
    Returns:
        Dict with result and metadata
    """
    try:
        result = process_task_sync(task, trace_name, session_id)
        return {
            "success": True,
            "result": result,
            "is_streaming": False,
            "journey_id": f"journey_{int(time.time())}_{uuid.uuid4().hex[:8]}",
            "session_id": session_id
        }
    except Exception as e:
        print(f"[ORCHESTRATOR] Error in process_task_with_stream: {str(e)}")
        print(traceback.format_exc())
        return {
            "success": False,
            "error": str(e),
            "is_streaming": False
        }

# Handler execution functions
    """
    Private method for direct handler execution as a fallback mechanism.
    Do not use this directly - it will be deprecated in the future.
    """
    logging.info(f"Direct execution fallback: {handler_name}.{action}")
    try:
        # Import the handler module dynamically
        module_name = f"Handler.handler_{handler_name.lower()}"
        module = importlib.import_module(module_name)
        
        # Get the handler class (assume it follows naming convention)
        class_name = ''.join(word.capitalize() for word in handler_name.split('_')) + 'Handler'
        if hasattr(module, class_name):
            handler_class = getattr(module, class_name)
            
            # Create an instance of the handler
            handler = handler_class()
            
            # Check if the handler has the requested action
            if hasattr(handler, action):
                # Get the method
                method = getattr(handler, action)
                
                # Prepare parameters
                if parameters is None:
                    parameters = {}
                    
                # Execute the method
                result = method(**parameters)
                
                # Return the result
                return {
                    "result": result,
                    "status": "success",
                    "handler": handler_name,
                    "action": action
                }
            else:
                return {
                    "error": f"Action '{action}' not found on handler '{handler_name}'",
                    "status": "error"
                }
        else:
            return {
                "error": f"Handler class '{class_name}' not found in module '{module_name}'",
                "status": "error"
            }
    except Exception as e:
        logging.error(f"Error in direct handler execution: {str(e)}")
        logging.debug(traceback.format_exc())
        
        return {
            "error": str(e),
            "traceback": traceback.format_exc(),
            "status": "error",
            "handler": handler_name,
            "action": action
        }

async def process_handler_execution(execution_request):
    """
    Process handler execution requests from the intelligence module.
    
    This method is the primary interface between the intelligence module and
    handler execution. It takes the rich intelligence data and uses it to execute
    the appropriate handler action through handler_all.
    
    Args:
        execution_request: Dict containing handler_name, action, parameters,
                          journey_id, workspace_id, and intelligence_data
                          
    Returns:
        Dict with execution results
    """
    handler_name = execution_request.get("handler_name")
    action = execution_request.get("action")
    parameters = execution_request.get("parameters", {})
    journey_id = execution_request.get("journey_id")
    workspace_id = execution_request.get("workspace_id")
    user_id = execution_request.get("user_id")  # ✅ SECURITY FIX: Extract user_id for credential isolation
    intelligence_data = execution_request.get("intelligence_data", {})
    
    logging.info(f"Processing handler execution: {handler_name}.{action} with journey_id: {journey_id}")
    
    # Track execution journey
    if journey_id:
        try:
            track_journey_step(
                journey_id=journey_id,
                step_name=f"execute_{handler_name}_{action}",
                step_type="handler_execution",
                metadata={
                    "handler": handler_name,
                    "action": action,
                    "confidence": intelligence_data.get("confidence", 0),
                    "workspace_id": workspace_id
                }
            )
        except Exception as e:
            logging.warning(f"Error tracking journey step: {str(e)}")
    
    try:
        # Use handler_all for actual execution
        from Handler.handler_all import handler_system
        
        if not handler_system:
            logging.error("handler_system not available")
            return {
                "success": False,
                "error": "Handler system not available",
                "handler": handler_name,
                "action": action
            }
            
        # Execute the handler using the centralized system with user context
        execution_result = await handler_system.execute_command(
            handler_name, 
            action, 
            parameters,
            user_id=user_id  # ✅ SECURITY FIX: Pass user_id for MCP credential isolation
        )
        
        # Format execution result for tracking and response
        formatted_result = {
            "success": execution_result.success if hasattr(execution_result, 'success') else False,
            "data": execution_result.data if hasattr(execution_result, 'data') else None,
            "error": execution_result.error if (hasattr(execution_result, 'error') and 
                                               not execution_result.success) else None,
            "metadata": execution_result.metadata if hasattr(execution_result, 'metadata') else {},
            "handler": handler_name,
            "action": action,
            "journey_id": journey_id
        }
        
        # Record execution result
        if journey_id:
            try:
                await update_journey_state(
                    journey_id=journey_id,
                    state="handler_executed",
                    metadata={
                        "success": execution_result.success if hasattr(execution_result, 'success') else False,
                        "handler": handler_name,
                        "action": action
                    }
                )
            except Exception as e:
                logging.warning(f"Error updating journey state: {str(e)}")
        
        return formatted_result
    except Exception as e:
        logging.error(f"Handler execution failed: {str(e)}")
        logging.error(traceback.format_exc())
        
        # Record execution failure
        if journey_id:
            try:
                await update_journey_state(
                    journey_id=journey_id,
                    state="handler_execution_failed",
                    metadata={
                        "handler": handler_name,
                        "action": action,
                        "error": str(e)
                    }
                )
            except Exception as journey_e:
                logging.warning(f"Error updating journey state: {str(journey_e)}")
        
        return {
            "success": False,
            "error": f"Execution failed: {str(e)}",
            "handler": handler_name,
            "action": action,
            "journey_id": journey_id
        }

async def execute_handler_action_async(handler_name, action, parameters=None):
    """
    Execute a handler action asynchronously.
    
    IMPORTANT: This function now routes all handler calls through the MCP system
    using workspace context, replacing the previous handler_all approach.
    
    Args:
        handler_name: The name of the handler to execute
        action: The name of the action/method to call
        parameters: Parameters to pass to the handler action
        
    Returns:
        Result of the handler action execution
    """
    logging.info(f"Executing handler action asynchronously via MCP: {handler_name}.{action}")
    try:
        # Prepare parameters
        if parameters is None:
            parameters = {}
            
        # Extract context for safety (some handlers don't accept context)
        context_data = {}
        if "context" in parameters:
            context_data = parameters.pop("context")
            
        # The terminal handler MCP wrapper now accepts 'command' parameter (not 'cmd')
        # and also accepts a context parameter, so no special handling needed anymore
            
        # Get workspace ID - either from parameters or create a default workspace
        workspace_id = None
        if isinstance(parameters, dict):
            if "workspace_id" in parameters:
                workspace_id = parameters["workspace_id"]
            elif "context" in parameters and isinstance(parameters["context"], dict):
                workspace_id = parameters["context"].get("workspace_id")
        
        # If no workspace ID is provided, we need to get or create a default workspace
        if workspace_id is None:
            # Get workspace sharing manager
            workspace_sharing = get_workspace_sharing()
            if workspace_sharing:
                try:
                    # Try to get default workspace or create one if it doesn't exist
                    default_workspace = await workspace_sharing.get_or_create_default_workspace()
                    if default_workspace and "workspace_id" in default_workspace:
                        workspace_id = default_workspace["workspace_id"]
                        logging.info(f"Using default workspace ID: {workspace_id}")
                        
                        # Add workspace_id to parameters for context
                        if "context" not in parameters:
                            parameters["context"] = {}
                        parameters["context"]["workspace_id"] = workspace_id
                except Exception as ws_error:
                    logging.error(f"Error getting/creating default workspace: {str(ws_error)}")
            else:
                logging.warning("Workspace sharing manager not available")
        
        # Execute the handler action via workspace sharing and MCP
        if workspace_id is not None:
            # Get workspace sharing manager
            workspace_sharing = get_workspace_sharing()
            if workspace_sharing:
                try:
                    # Route the request to the appropriate MCP handler
                    mcp_handler_name = await workspace_sharing.route_handler_to_mcp(
                        workspace_id=workspace_id,
                        handler_name=handler_name,
                        fallback_to_direct=True
                    )
                    
                    # If MCP handler name is different from original, log the mapping
                    if mcp_handler_name != handler_name:
                        logging.info(f"Mapped handler '{handler_name}' to MCP handler '{mcp_handler_name}'")
                    
                    # Use execute_method_via_mcp if available
                    if hasattr(workspace_sharing, 'execute_method_via_mcp'):
                        result = await workspace_sharing.execute_method_via_mcp(
                            workspace_id=workspace_id,
                            handler_name=mcp_handler_name,
                            method_name=action,
                            parameters=parameters
                        )
                        return result
                    else:
                        logging.warning("execute_method_via_mcp not available in workspace_sharing manager")
                        # Try to force reload the workspace_sharing module
                        try:
                            from Jarvis_Agent_SDK.import_helper import reset_workspace_sharing_manager
                            reset_workspace_sharing_manager()
                            
                            # Re-import workspace_sharing
                            import sys
                            if 'Database.workspace_sharing' in sys.modules:
                                del sys.modules['Database.workspace_sharing']
                            
                            # Import with reload
                            import importlib
                            importlib.import_module('Database.workspace_sharing')
                            
                            # Get fresh workspace_sharing manager using global import
                            # Avoid importing locally to prevent variable shadowing
                            fresh_workspace_sharing = get_workspace_sharing(force_reload=True)
                            
                            # Try again with the fresh instance
                            if hasattr(fresh_workspace_sharing, 'execute_method_via_mcp'):
                                logging.info("Successfully reloaded workspace_sharing with execute_method_via_mcp")
                                result = await fresh_workspace_sharing.execute_method_via_mcp(
                                    workspace_id=workspace_id,
                                    handler_name=mcp_handler_name,
                                    method_name=action,
                                    parameters=parameters
                                )
                                return result
                        except Exception as reload_error:
                            logging.error(f"Error trying to reload workspace_sharing: {str(reload_error)}")
                        
                        # No direct MCP execution method available, fall back to direct execution
                        logging.warning(f"Falling back to direct execution for {handler_name}.{action}")
                        return await _direct_execute_handler_action_async(handler_name, action, parameters)
                except Exception as mcp_error:
                    logging.error(f"Error executing via MCP: {str(mcp_error)}")
                    logging.debug(traceback.format_exc())
                    return {
                        "error": f"MCP execution error: {str(mcp_error)}",
                        "status": "error",
                        "handler": handler_name,
                        "action": action
                    }
            else:
                logging.warning("Workspace sharing manager not available, falling back to direct execution")
        
        # If we reach here, fall back to direct execution
        logging.warning(f"No workspace context available for MCP, falling back to direct execution for {handler_name}.{action}")
        return await _direct_execute_handler_action_async(handler_name, action, parameters)
    except Exception as e:
        logging.error(f"Error in execute_handler_action_async: {str(e)}")
        logging.debug(traceback.format_exc())
        
        return {
            "error": str(e),
            "traceback": traceback.format_exc(),
            "status": "error",
            "handler": handler_name,
            "action": action
        }
        
# Private method for direct execution as fallback (preserves original functionality)
def execute_handler_action(handler_name, action, parameters=None):
    """
    Synchronous version of execute_handler_action_async.
    
    IMPORTANT: This function now routes all handler calls through the MCP system
    using workspace context, replacing the previous handler_all approach.
    
    Args:
        handler_name: The name of the handler to execute
        action: The name of the action/method to call
        parameters: Parameters to pass to the handler action
        
    Returns:
        Result of the handler action execution
    """
    logging.info(f"Executing handler action synchronously via MCP: {handler_name}.{action}")
    
    import asyncio
    try:
        # Check if we're already in an event loop
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # We're in a running event loop, we can't create a new one
                # Schedule the coroutine and use asyncio.ensure_future
                logging.info(f"Using existing event loop for {handler_name}.{action}")
                future = asyncio.ensure_future(execute_handler_action_async(handler_name, action, parameters))
                # We can't await here, so we'll need to manually set up a callback or return the future
                # For tests, we'll just return a pending status
                return {
                    "status": "pending",
                    "message": "Operation scheduled in existing event loop",
                    "handler": handler_name,
                    "action": action
                }
            else:
                # We have a loop but it's not running
                result = loop.run_until_complete(execute_handler_action_async(handler_name, action, parameters))
                return result
        except RuntimeError:
            # No event loop exists in this thread, create a new one
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                result = loop.run_until_complete(execute_handler_action_async(handler_name, action, parameters))
                return result
            finally:
                loop.close()
    except Exception as e:
        logging.error(f"Error in execute_handler_action: {str(e)}")
        logging.debug(traceback.format_exc())
        return {
            "error": str(e),
            "traceback": traceback.format_exc(),
            "status": "error",
            "handler": handler_name,
            "action": action
        }

async def _direct_execute_handler_action_async(handler_name, action, parameters=None):
    """
    Private method for direct async handler execution as a fallback mechanism.
    This method imports handlers directly using the HANDLER_REGISTRY.
    
    Do not use this directly - it will be deprecated in the future.
    """
    logging.info(f"Direct async execution fallback: {handler_name}.{action}")
    
    # Initialize parameters if None
    if parameters is None:
        parameters = {}
    
    try:
        # Import handler directly using HANDLER_REGISTRY (MCP wrappers removed)
        from .mcp_server_launcher import HANDLER_REGISTRY, import_handler_class
        
        if handler_name in HANDLER_REGISTRY:
            module_path, class_name = HANDLER_REGISTRY[handler_name]
            handler_class = import_handler_class(module_path, class_name)
            handler = handler_class() if handler_class else None
        else:
            handler = None
        
        if handler:
            logging.info(f"Successfully imported handler {handler_name}, executing {action}")
            
            # Check if the handler has an execute method
            if hasattr(handler, 'execute') and callable(getattr(handler, 'execute')):
                execute_method = getattr(handler, 'execute')
                try:
                    # Execute method should be synchronous
                    result = execute_method(action, parameters)
                    return result
                except Exception as execute_error:
                    logging.error(f"Error in handler execute method: {str(execute_error)}")
                    logging.debug(traceback.format_exc())
                    # Continue to fallback mechanism
            else:
                logging.warning(f"Handler {handler_name} doesn't have execute method, trying direct method")
                
                # Check if the handler has the requested action directly
                if hasattr(handler, action) and callable(getattr(handler, action)):
                    method = getattr(handler, action)
                    try:
                        result = method(**parameters)
                        return result
                    except Exception as direct_method_error:
                        logging.error(f"Error calling direct method on MCP wrapper: {str(direct_method_error)}")
                        logging.debug(traceback.format_exc())
                        # Continue to fallback mechanism
                else:
                    logging.warning(f"MCP wrapper for {handler_name} doesn't have {action} method")
                    # Continue to fallback mechanism
        else:
            logging.warning(f"No MCP wrapper found for {handler_name}, falling back to direct module import")
        
        # If MCP wrapper doesn't exist or fails, fall back to direct module import (legacy approach)
        logging.info(f"Falling back to direct module import for {handler_name}.{action}")
        
        # Import the handler module dynamically
        module_name = f"Handler.handler_{handler_name.lower()}"
        module = importlib.import_module(module_name)
        
        # Get the handler class (assume it follows naming convention)
        class_name = ''.join(word.capitalize() for word in handler_name.split('_')) + 'Handler'
        if hasattr(module, class_name):
            handler_class = getattr(module, class_name)
            
            # Create an instance of the handler
            handler = handler_class()
            
            # Check if the handler has the requested action
            if hasattr(handler, action):
                # Get the method
                method = getattr(handler, action)
                
                # Prepare parameters
                if parameters is None:
                    parameters = {}
                
                # Special handling for terminal handler
                if handler_name == 'terminal' and action == 'execute_command':
                    # Terminal handler expects cmd parameter
                    if 'cmd' in parameters:
                        cmd = parameters['cmd']
                        # Different terminal handlers have different parameter expectations
                        # Try several formats to ensure compatibility
                        
                        # Format 1: Direct cmd parameter
                        try:
                            logging.info(f"Trying terminal handler with direct cmd parameter")
                            if inspect.iscoroutinefunction(method):
                                result = await method(cmd=cmd)
                            else:
                                loop = asyncio.get_event_loop()
                                result = await loop.run_in_executor(
                                    None, lambda: method(cmd=cmd)
                                )
                            return {
                                "result": result,
                                "status": "success",
                                "handler": handler_name,
                                "action": action
                            }
                        except Exception as e1:
                            logging.warning(f"Direct cmd parameter failed: {str(e1)}")
                            
                            # Format 2: Nested parameters dict
                            try:
                                logging.info(f"Trying terminal handler with nested parameters dict")
                                exec_params = {'parameters': {'cmd': cmd}}
                                if inspect.iscoroutinefunction(method):
                                    result = await method(**exec_params)
                                else:
                                    loop = asyncio.get_event_loop()
                                    result = await loop.run_in_executor(
                                        None, lambda: method(**exec_params)
                                    )
                                return {
                                    "result": result,
                                    "status": "success",
                                    "handler": handler_name,
                                    "action": action
                                }
                            except Exception as e2:
                                logging.warning(f"Nested parameters dict failed: {str(e2)}")
                                
                                # Format 3: Pass full parameters dict
                                try:
                                    logging.info(f"Trying terminal handler with full parameters dict")
                                    if inspect.iscoroutinefunction(method):
                                        result = await method(**parameters)
                                    else:
                                        loop = asyncio.get_event_loop()
                                        result = await loop.run_in_executor(
                                            None, lambda: method(**parameters)
                                        )
                                    return {
                                        "result": result,
                                        "status": "success",
                                        "handler": handler_name,
                                        "action": action
                                    }
                                except Exception as e3:
                                    logging.error(f"All terminal handler parameter formats failed")
                                    return {
                                        "error": f"Terminal handler parameter incompatibility: {str(e1)}, {str(e2)}, {str(e3)}",
                                        "status": "error",
                                        "handler": handler_name,
                                        "action": action
                                    }
                    else:
                        return {
                            "error": "Missing 'cmd' parameter for terminal handler",
                            "status": "error",
                            "handler": handler_name,
                            "action": action
                        }
                
                # Check method signature to see what parameters it accepts
                sig = inspect.signature(method)
                param_names = set(sig.parameters.keys())
                
                # Filter parameters to only include those accepted by the method
                filtered_params = {}
                for key, value in parameters.items():
                    if key in param_names:
                        filtered_params[key] = value
                    else:
                        logging.info(f"Parameter '{key}' not accepted by {handler_name}.{action}, skipping it")
                
                # Check if the method is async
                if inspect.iscoroutinefunction(method):
                    # Execute the async method with the filtered parameters
                    result = await method(**filtered_params)
                else:
                    # For non-async methods, run in thread pool
                    loop = asyncio.get_event_loop()
                    result = await loop.run_in_executor(
                        None, lambda: method(**filtered_params)
                    )
                
                # Return the result
                return {
                    "result": result,
                    "status": "success",
                    "handler": handler_name,
                    "action": action
                }
            else:
                return {
                    "error": f"Action '{action}' not found on handler '{handler_name}'",
                    "status": "error"
                }
        else:
            return {
                "error": f"Handler class '{class_name}' not found in module '{module_name}'",
                "status": "error"
            }
    except Exception as e:
        logging.error(f"Error executing handler action asynchronously: {str(e)}")
        logging.debug(traceback.format_exc())
        
        return {
            "error": str(e),
            "traceback": traceback.format_exc(),
            "status": "error",
            "handler": handler_name,
            "action": action
        }



class JarvisOrchestrator:
    """
    Jarvis Orchestrator - Executes plans created through BoardRoom's planning capabilities
    based on Trevor Core's complexity analysis.
    
    This class implements the hybrid approach for request processing, connecting
    Trevor Core's complexity analysis with BoardRoom's planning capabilities and
    the overall Jarvis ecosystem's execution abilities.
    
    Key features:
    1. Plan execution with dependency management
    2. Hierarchical workspace organization
    3. Journey tracking with detailed analytics
    4. Resource-aware execution with capability matching
    5. Handler and specialized agent module dispatch
    """
    
    def __init__(self, trevor_core_instance=None):
        """Initialize the JarvisOrchestrator with connections to required systems.
        
        Args:
            trevor_core_instance: Optional TrevorCore instance to use for intelligence
        """
        # Get OrchestratorAgent instance for dispatch capabilities
        # Initialize with an empty agent_dict to satisfy the constructor requirements
        self.orchestrator_agent = OrchestratorAgent(agent_dict={})
        
        # Get BoardRoom for any plan refinements or consultations
        self.boardroom = get_boardroom()
        
        # Get workspace cache for reference tracking
        self.workspace_cache = get_workspace_reference_cache()
        
        # Initialize logger
        self.logger = logging.getLogger(__name__)
        
        # In-memory store for active plan executions
        self.active_plans = {}
        
        # Import module capability registry
        try:
            from .module_capability_registry import ModuleCapabilityRegistry
            self.module_registry = ModuleCapabilityRegistry()
        except (ImportError, Exception) as e:
            self.logger.warning(f"Could not initialize ModuleCapabilityRegistry: {str(e)}")
            self.module_registry = None
        
        # Import orchestrator intelligence
        try:
            # Import essential modules for intelligence initialization
            import importlib
            from .jarvis_orchestrated_intelligence import get_orchestrator_intelligence_instance
            
            # Try to force-reload the modules to avoid circular imports
            try:
                importlib.reload(importlib.import_module("Jarvis_Agent_SDK.boardroom_orchestrator_bridge"))
                importlib.reload(importlib.import_module("Jarvis_Agent_SDK.jarvis_orchestrated_intelligence"))
                self.logger.info("Successfully reloaded critical modules for intelligence initialization")
            except Exception as reload_err:
                self.logger.warning(f"Module reload failed: {str(reload_err)}")
                
            # Initialize intelligence without Trevor Core dependency
            
            # Get the singleton intelligence instance with TrevorCore
            try:
                # First try to get existing instance
                from .jarvis_orchestrated_intelligence import OrchestratorIntelligence, init_orchestrator_intelligence, get_orchestrator_intelligence_instance
                # Use init function to ensure proper initialization
                self.intelligence = init_orchestrator_intelligence()
                self.logger.info(f"✅ Got OrchestratorIntelligence from init function: {id(self.intelligence)}")
                
                # Fallback if init function fails
                if not self.intelligence:
                    self.logger.warning("⚠️ init_orchestrator_intelligence returned None, creating instance directly")
                    self.intelligence = OrchestratorIntelligence()
                    self.logger.info(f"✅ Created new OrchestratorIntelligence instance directly: {id(self.intelligence)}")
                    # Set the global instance for future use
                    import Jarvis_Agent_SDK.jarvis_orchestrated_intelligence as joi
                    joi._orchestrator_intelligence_instance = self.intelligence
                    self.logger.info(f"✅ Set global _orchestrator_intelligence_instance to {id(self.intelligence)}")
            except Exception as intel_err:
                self.logger.error(f"❌ Error creating intelligence instance directly: {str(intel_err)}")
                self.logger.error(traceback.format_exc())
            
            if self.intelligence:
                self.logger.info(f"Successfully initialized OrchestratorIntelligence: {id(self.intelligence)}")
                
                # Pass intelligence module to orchestrator_agent
                self.orchestrator_agent.intelligence = self.intelligence
                self.logger.info("✅ Passed intelligence module to OrchestratorAgent")
                
            else:
                self.logger.warning("OrchestratorIntelligence is None - using fallback processing")
        except (ImportError, Exception) as e:
            self.logger.warning(f"Could not initialize OrchestratorIntelligence: {str(e)}")
            self.logger.error(traceback.format_exc())
            self.intelligence = None
        
        # Assign BoardRoom processing function to make it available as instance method
        self.logger.info(f"🔍 Assigning process_with_boardroom to orchestrator: {type(process_with_boardroom)} = {process_with_boardroom}")
        self.process_with_boardroom = process_with_boardroom
        self.logger.info(f"✅ Assigned process_with_boardroom to orchestrator instance: {type(self.process_with_boardroom)}")
    
    async def handle_user_request(self, request: str, user_id: str = None, **kwargs) -> Dict[str, Any]:
        """
        Handle user request using workspace-centric architecture.
        
        Args:
            request: The user's request text
            user_id: Optional user identifier
            **kwargs: Additional parameters
            
        Returns:
            Dict containing response and metadata
        """
        try:
            # Validate input request
            if not request or not request.strip():
                self.logger.warning("Empty or invalid request received")
                return {
                    "success": False,
                    "error": "Empty or invalid request provided",
                    "workspace_id": None,
                    "response": "Please provide a valid request to process."
                }
            
            # Create initial workspace for this request
            workspace = await self._create_initial_workspace(request, user_id)
            
            # Route based on complexity analysis
            if workspace.get("complexity", "simple") == "simple":
                return await self._execute_simple_workspace(workspace)
            else:
                return await self._execute_complex_workspace(workspace)
                
        except Exception as e:
            self.logger.error(f"Error in handle_user_request: {str(e)}")
            return {"success": False, "error": str(e), "status": "failed"}
    
    async def _create_initial_workspace(self, request: str, user_id: str = None) -> Dict[str, Any]:
        """
        Create initial workspace for the request.
        
        Args:
            request: User's request text
            user_id: Optional user identifier
            
        Returns:
            Initial workspace dictionary
        """
        workspace = {
            "original_request": request,
            "user_id": user_id,
            "workspace_id": str(uuid.uuid4()),
            "created_at": datetime.now().isoformat(),
            "complexity": "simple",  # Default, will be updated by analysis
            "metadata": {}
        }
        
        # Route to Trevor Intelligence for analysis
        analyzed_workspace = await self._route_to_trevor_intelligence(workspace)
        return analyzed_workspace
    
    async def _route_to_trevor_intelligence(self, workspace: Dict[str, Any]) -> Dict[str, Any]:
        """
        Route workspace to Trevor Intelligence for analysis and enhancement.
        
        Args:
            workspace: Initial workspace data
            
        Returns:
            Enhanced workspace with complexity analysis
        """
        try:
            if self.intelligence and hasattr(self.intelligence, 'analyze_task_complexity'):
                complexity_result = await self.intelligence.analyze_task_complexity(workspace["original_request"])
                workspace["complexity"] = complexity_result.get("complexity", "simple")
                workspace["metadata"]["analysis"] = complexity_result
                
            return workspace
            
        except Exception as e:
            self.logger.error(f"Error in Trevor Intelligence routing: {str(e)}")
            # Fallback to simple processing
            workspace["complexity"] = "simple"
            return workspace
    
    
    async def _execute_workspace(self, workspace: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute workspace based on its complexity and plan.
        
        Args:
            workspace: Workspace to execute
            
        Returns:
            Execution results
        """
        if workspace.get("complexity") == "simple":
            return await self._execute_simple_workspace(workspace)
        else:
            return await self._execute_complex_workspace(workspace)
    
    async def _execute_simple_workspace(self, workspace: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute simple workspace directly.
        
        Args:
            workspace: Simple workspace to execute
            
        Returns:
            Execution results
        """
        try:
            # Use existing process_request for simple execution
            result = await self.process_request(
                workspace["original_request"],
                session_id=workspace.get("workspace_id"),
                context=workspace.get("metadata", {})
            )
            
            # process_request returns a string, not a dict
            response_text = result if isinstance(result, str) else str(result)
            
            return {
                "success": True,
                "response": response_text,
                "workspace_id": workspace["workspace_id"],
                "status": "completed",
                "execution_type": "simple"
            }
            
        except Exception as e:
            self.logger.error(f"Error executing simple workspace: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "workspace_id": workspace["workspace_id"],
                "status": "failed",
                "execution_type": "simple"
            }
    
    async def _execute_complex_workspace(self, workspace: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute complex workspace with BoardRoom planning.
        
        Args:
            workspace: Complex workspace to execute
            
        Returns:
            Execution results
        """
        try:
            # First route to BoardRoom for planning
            workspace_with_plan = await self._route_to_boardroom(workspace)
            
            # Execute the plan if available
            if "execution_plan" in workspace_with_plan:
                plan_result = await self.execute_plan(
                    workspace["original_request"],
                    workspace_with_plan["execution_plan"],
                    workspace.get("metadata", {})
                )
                
                return {
                    "success": True,
                    "response": plan_result.get("response", "Plan executed successfully"),
                    "workspace_id": workspace["workspace_id"],
                    "status": "completed",
                    "execution_type": "complex",
                    "plan_results": plan_result
                }
            else:
                # Fallback to simple execution
                return await self._execute_simple_workspace(workspace)
                
        except Exception as e:
            self.logger.error(f"Error executing complex workspace: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "workspace_id": workspace["workspace_id"],
                "status": "failed",
                "execution_type": "complex"
            }
    
    async def process_request(self, query, session_id=None, message_type="request", source=None, user_id=None, conversation_id=None, context=None):
        """
        Process a user request by creating a workspace and handling based on complexity
        analysis provided by Trevor Core.
        
        Args:
            query (str): The user's query or request text
            session_id (str, optional): Unique identifier for the session
            message_type (str, optional): Type of message. Defaults to "request".
            source (str, optional): Source of the request. Defaults to None.
            conversation_id (str, optional): ID of the conversation. Defaults to None.
            context (dict, optional): Additional context information. Defaults to None.
            
        Returns:
            dict: Result of processing the request, containing response and metadata
        """
        try:
            # First create a workspace for this request
            workspace_id = None
            try:
                from .import_helper import get_workspace_sharing
                workspace_sharing = get_workspace_sharing()
                if workspace_sharing:
                    # Make sure to await the coroutine
                    workspace = await workspace_sharing.get_or_create_default_workspace()
                    if workspace and "workspace_id" in workspace:
                        workspace_id = workspace["workspace_id"]
                        self.logger.info(f"Using workspace: {workspace_id} for request")
            except Exception as ws_error:
                self.logger.error(f"Error creating workspace: {str(ws_error)}")
                self.logger.debug(traceback.format_exc())
            
            # Get complexity analysis from context if provided by Trevor Core
            complexity_analysis = None
            if context and "complexity_analysis" in context:
                complexity_analysis = context["complexity_analysis"]
                self.logger.info(f"Using complexity analysis from Trevor Core: {complexity_analysis.get('complexity_level', 'unknown')}")
            
            # Add workspace info to context
            request_context = context or {}
            if workspace_id:
                request_context["workspace_id"] = workspace_id
            
            # If we have an orchestrator_agent, delegate to it
            if self.orchestrator_agent:
                # Pass request to orchestrator agent with the context parameter
                result = await self.orchestrator_agent.process_request(
                    query=query,
                    session_id=session_id,
                    message_type=message_type,
                    source=source or "trevor_desktop",
                    conversation_id=conversation_id,
                    context=request_context
                )
                
                # Ensure workspace_id is included in the result
                if workspace_id and isinstance(result, dict) and "workspace_id" not in result:
                    result["workspace_id"] = workspace_id
                
                return result
            else:
                # Fallback if no orchestrator_agent
                self.logger.error("No orchestrator_agent available for request processing")
                return {
                    "error": "OrchestratorAgent not available",
                    "workspace_id": workspace_id if workspace_id else None
                }
            
        except Exception as e:
            self.logger.error(f"Error processing request through Jarvis Orchestrator: {str(e)}")
            self.logger.error(traceback.format_exc())
            
            # Return error information
            return {"error": str(e), "error_type": type(e).__name__}
    
    async def execute_plan(self, 
                          request: str, 
                          plan: Dict[str, Any],
                          context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Execute a comprehensive plan created by BoardRoom.
        
        Args:
            request: The original user request
            plan: The comprehensive execution plan with steps and dependencies
            context: Additional context information
            
        Returns:
            Dict containing execution results and metadata
        """
        # Default context if not provided
        context = context or {}
        
        # Extract key tracking information
        workspace_id = context.get("workspace_id")
        journey_id = context.get("journey_id")
        
        # Generate a unique plan execution ID
        plan_execution_id = str(uuid.uuid4())
        
        # Track execution start
        track_journey_step_sync(
            journey_id=journey_id,
            step_name="plan_execution_start",
            description=f"Starting execution of plan for: {request[:100]}..." if len(request) > 100 else request,
            step_type="execution",
            metadata={"plan_execution_id": plan_execution_id}
        )
        
        # Store plan in active plans
        self.active_plans[plan_execution_id] = {
            "plan": plan,
            "request": request,
            "context": context,
            "workspace_id": workspace_id,
            "journey_id": journey_id,
            "start_time": time.time(),
            "completed_steps": set(),
            "failed_steps": set(),
            "results": {}
        }
        
        try:
            # Validate the plan structure - handle both formats
            steps = None
            if "steps" in plan and isinstance(plan["steps"], list):
                # Standard format with top-level 'steps'
                steps = plan["steps"]
            elif "execution_plan" in plan and isinstance(plan["execution_plan"], dict):
                # BoardRoom format with nested execution_order
                execution_plan = plan["execution_plan"]
                if "execution_order" in execution_plan and isinstance(execution_plan["execution_order"], list):
                    steps = execution_plan["execution_order"]
            
            if steps is None:
                raise ValueError("Invalid plan structure: 'steps' or 'execution_plan.execution_order' not found or not a list")
            
            # Extract steps and build dependency graph
            dependency_graph = self._build_dependency_graph(steps)
            
            # Find initial executable steps (those with no dependencies or whose dependencies are satisfied)
            executable_steps = self._get_executable_steps(steps, set(), dependency_graph)
            
            # Track the steps we'll be executing first
            step_names = [step.get("name", f"Step {step.get('id', 'unknown')}") for step in executable_steps]
            track_journey_step_sync(
                journey_id=journey_id,
                step_name="initial_steps",
                description=f"Starting with {len(executable_steps)} initial steps",
                step_type="execution",
                metadata={"steps": step_names}
            )
            
            # Execute the plan by processing steps according to dependencies
            completed_steps = set()
            all_results = {}
            
            # Continue until all steps are completed or max iterations reached
            max_iterations = len(steps) * 2  # Avoid infinite loops
            iteration = 0
            
            while executable_steps and iteration < max_iterations:
                iteration += 1
                
                # Execute the current batch of steps in parallel
                step_results = await asyncio.gather(*[
                    self._execute_step(step, plan, request, context, workspace_id, journey_id)
                    for step in executable_steps
                ])
                
                # Process results and update tracking
                for step, result in zip(executable_steps, step_results):
                    step_id = step.get("id", f"step_{uuid.uuid4().hex[:8]}")
                    
                    # Store the result
                    all_results[step_id] = result
                    self.active_plans[plan_execution_id]["results"][step_id] = result
                    
                    # Mark as completed (even if failed, as we've processed it)
                    completed_steps.add(step_id)
                    self.active_plans[plan_execution_id]["completed_steps"].add(step_id)
                    
                    # If it failed, track failure
                    if not result.get("success", False):
                        self.active_plans[plan_execution_id]["failed_steps"].add(step_id)
                
                # Find new executable steps based on completed dependencies
                executable_steps = self._get_executable_steps(steps, completed_steps, dependency_graph)
            
            # Check if any steps were not completed
            all_step_ids = {step.get("id", f"step_{uuid.uuid4().hex[:8]}") for step in steps}
            incomplete_steps = all_step_ids - completed_steps
            
            # Track completion status
            if not incomplete_steps:
                track_journey_step_sync(
                    journey_id=journey_id,
                    step_name="plan_execution_complete",
                    description="Successfully executed all plan steps",
                    step_type="completion",
                    metadata={"plan_execution_id": plan_execution_id}
                )
                
                # Check for failed steps
                failed_steps = self.active_plans[plan_execution_id]["failed_steps"]
                if failed_steps:
                    track_journey_step_sync(
                        journey_id=journey_id,
                        step_name="execution_partial_failure",
                        description=f"Plan completed with {len(failed_steps)} failed steps",
                        step_type="warning",
                        metadata={"failed_steps": list(failed_steps)}
                    )
            else:
                track_journey_step_sync(
                    journey_id=journey_id,
                    step_name="plan_execution_incomplete",
                    description=f"Plan execution incomplete, {len(incomplete_steps)} steps not executed",
                    step_type="warning",
                    metadata={"incomplete_steps": list(incomplete_steps)}
                )
            
            # Compile the final result
            final_result = await self._compile_plan_result(plan, all_results, completed_steps, request)
            
            # Update plan status
            self.active_plans[plan_execution_id]["end_time"] = time.time()
            self.active_plans[plan_execution_id]["status"] = "completed"
            
            return final_result
            
        except Exception as e:
            self.logger.error(f"Error executing plan: {str(e)}")
            self.logger.debug(traceback.format_exc())
            
            # Track execution error
            track_journey_step_sync(
                journey_id=journey_id,
                step_name="plan_execution_error",
                description=f"Error executing plan: {str(e)}",
                step_type="error",
                error=str(e)
            )
            
            # Update plan status
            self.active_plans[plan_execution_id]["end_time"] = time.time()
            self.active_plans[plan_execution_id]["status"] = "error"
            self.active_plans[plan_execution_id]["error"] = str(e)
            
            return {
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__,
                "completed_steps": list(self.active_plans[plan_execution_id]["completed_steps"]),
                "plan_execution_id": plan_execution_id
            }
    
    def _build_dependency_graph(self, steps: List[Dict[str, Any]]) -> Dict[str, List[str]]:
        """
        Build a dependency graph from plan steps.
        
        Args:
            steps: List of step dictionaries
            
        Returns:
            Dict mapping step IDs to lists of dependency step IDs
        """
        dependency_graph = {}
        
        for step in steps:
            step_id = step.get("id", f"step_{uuid.uuid4().hex[:8]}")
            dependencies = step.get("dependencies", [])
            
            # Store dependencies for this step
            dependency_graph[step_id] = dependencies
        
        return dependency_graph
    
    def _get_executable_steps(self, 
                             steps: List[Dict[str, Any]], 
                             completed_steps: set[str],
                             dependency_graph: Dict[str, List[str]]) -> List[Dict[str, Any]]:
        """
        Find steps that are ready to execute based on dependencies.
        
        Args:
            steps: List of all steps
            completed_steps: Set of completed step IDs
            dependency_graph: Dependency mapping
            
        Returns:
            List of executable steps
        """
        executable_steps = []
        
        for step in steps:
            step_id = step.get("id", f"step_{uuid.uuid4().hex[:8]}")
            
            # Skip already completed steps
            if step_id in completed_steps:
                continue
            
            # Get dependencies for this step
            dependencies = dependency_graph.get(step_id, [])
            
            # Check if all dependencies are satisfied
            dependencies_satisfied = all(dep in completed_steps for dep in dependencies)
            
            if dependencies_satisfied:
                executable_steps.append(step)
        
        return executable_steps
    
    async def _execute_step(self,
                           step: Dict[str, Any],
                           plan: Dict[str, Any],
                           request: str,
                           context: Dict[str, Any],
                           workspace_id: Optional[int],
                           journey_id: str) -> Dict[str, Any]:
        """
        Execute a single step of the plan.
        
        Args:
            step: The step to execute
            plan: The full plan
            request: Original user request
            context: Execution context
            workspace_id: Parent workspace ID
            journey_id: Journey tracking ID
            
        Returns:
            Dict containing step execution result
        """
        step_id = step.get("id", f"step_{uuid.uuid4().hex[:8]}")
        step_name = step.get("name", f"Step {step_id}")
        step_desc = step.get("description", "")
        
        # Get step workspace ID if available
        step_workspace_id = None
        if "step_workspaces" in plan and step_id in plan["step_workspaces"]:
            step_workspace_id = plan["step_workspaces"][step_id]
        
        # Track step execution start
        track_journey_step_sync(
            journey_id=journey_id,
            step_name=f"step_{step_id}_start",
            description=f"Executing: {step_name}",
            step_type="step_execution",
            metadata={
                "step_id": step_id,
                "workspace_id": step_workspace_id
            }
        )
        
        try:
            # Determine execution method based on step configuration
            if "handler" in step:
                # Execute using a specific handler
                result = await self._execute_with_handler(step, request, context, journey_id)
            elif "agent" in step:
                # Execute using a specialized agent
                result = await self._execute_with_agent(step, request, context, journey_id)
            elif "module" in step:
                # Execute using a registered module
                result = await self._execute_with_module(step, request, context, journey_id)
            else:
                # Execute with BoardRoom as generic executor
                result = await self._execute_with_boardroom(step, request, context, journey_id)
            
            # Update step workspace completion if applicable
            if step_workspace_id:
                try:
                    from Database.workspace_sharing import WorkspaceSharing
                    workspace_manager = WorkspaceSharing()
                    
                    completion_percentage = 100.0  # Completed step
                    await workspace_manager.update_workspace_completion(
                        workspace_id=step_workspace_id,
                        completion_percentage=completion_percentage
                    )
                except Exception as ws_error:
                    self.logger.warning(f"Error updating workspace completion: {str(ws_error)}")
            
            # Track step execution completion
            track_journey_step_sync(
                journey_id=journey_id,
                step_name=f"step_{step_id}_complete",
                description=f"Completed: {step_name}",
                step_type="step_completion",
                metadata={
                    "step_id": step_id,
                    "workspace_id": step_workspace_id,
                    "success": result.get("success", True)
                }
            )
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error executing step {step_id}: {str(e)}")
            self.logger.debug(traceback.format_exc())
            
            # Track step execution error
            track_journey_step_sync(
                journey_id=journey_id,
                step_name=f"step_{step_id}_error",
                description=f"Error executing: {step_name}",
                step_type="error",
                error=str(e),
                metadata={
                    "step_id": step_id,
                    "workspace_id": step_workspace_id
                }
            )
            
            return {
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__
            }
    
    async def _execute_with_handler(self,
                                  step: Dict[str, Any],
                                  request: str,
                                  context: Dict[str, Any],
                                  journey_id: str) -> Dict[str, Any]:
        """
        Execute a step using a specific handler.
        
        Args:
            step: The step configuration
            request: Original user request
            context: Execution context
            journey_id: Journey tracking ID
            
        Returns:
            Dict containing execution result
        """
        handler_name = step.get("handler")
        action = step.get("action", "process_query")
        
        if not handler_name:
            raise ValueError("Handler name not specified in step configuration")
        
        # Track handler execution
        track_journey_step_sync(
            journey_id=journey_id,
            step_name=f"handler_{handler_name}",
            description=f"Executing with handler: {handler_name}",
            step_type="handler_execution",
            metadata={"action": action}
        )
        
        # Prepare handler-specific parameters
        handler_params = {
            "query": step.get("input", request),
            "context": {
                **context,
                "step_id": step.get("id"),
                "step_name": step.get("name"),
                "journey_id": journey_id,
                "from_orchestrator_plan": True,
                "plan_step": True
            }
        }
        
        # Add any additional parameters from the step
        if "parameters" in step and isinstance(step["parameters"], dict):
            handler_params.update(step["parameters"])
        
        # Execute the handler through orchestrator agent
        result = await self.orchestrator_agent.execute_handler_async(
            handler_name=handler_name,
            action=action,
            **handler_params
        )
        
        # Ensure standard response format
        if not isinstance(result, dict):
            result = {"result": result, "success": True}
        
        return result
    
    async def _execute_with_agent(self,
                                step: Dict[str, Any],
                                request: str,
                                context: Dict[str, Any],
                                journey_id: str) -> Dict[str, Any]:
        """
        Execute a step using a specialized agent.
        
        Args:
            step: The step configuration
            request: Original user request
            context: Execution context
            journey_id: Journey tracking ID
            
        Returns:
            Dict containing execution result
        """
        agent_name = step.get("agent")
        
        if not agent_name:
            raise ValueError("Agent name not specified in step configuration")
        
        # Track agent execution
        track_journey_step_sync(
            journey_id=journey_id,
            step_name=f"agent_{agent_name}",
            description=f"Executing with agent: {agent_name}",
            step_type="agent_execution"
        )
        
        # Prepare agent-specific parameters
        agent_params = {
            "query": step.get("input", request),
            "context": {
                **context,
                "step_id": step.get("id"),
                "step_name": step.get("name"),
                "journey_id": journey_id,
                "from_orchestrator_plan": True,
                "plan_step": True
            }
        }
        
        # Add any additional parameters from the step
        if "parameters" in step and isinstance(step["parameters"], dict):
            agent_params.update(step["parameters"])
        
        # Check if we have a module registry for agent execution
        if self.module_registry:
            # Execute through module registry if agent is registered
            if self.module_registry.is_module_registered(agent_name):
                result = await self.module_registry.execute_module(
                    module_name=agent_name,
                    request=step.get("input", request),
                    context=agent_params["context"]
                )
                return result
        
        # Fall back to orchestrator agent's execute_agent method
        result = await self.orchestrator_agent.execute_agent(
            agent_name=agent_name,
            query=agent_params["query"],
            context=agent_params["context"]
        )
        
        # Ensure standard response format
        if not isinstance(result, dict):
            result = {"result": result, "success": True}
        
        return result
    
    async def _execute_with_module(self,
                                 step: Dict[str, Any],
                                 request: str,
                                 context: Dict[str, Any],
                                 journey_id: str) -> Dict[str, Any]:
        """
        Execute a step using a registered module.
        
        Args:
            step: The step configuration
            request: Original user request
            context: Execution context
            journey_id: Journey tracking ID
            
        Returns:
            Dict containing execution result
        """
        module_name = step.get("module")
        
        if not module_name:
            raise ValueError("Module name not specified in step configuration")
        
        # Track module execution
        track_journey_step_sync(
            journey_id=journey_id,
            step_name=f"module_{module_name}",
            description=f"Executing with module: {module_name}",
            step_type="module_execution"
        )
        
        # Check if we have a module registry for execution
        if not self.module_registry:
            raise ValueError("Module capability registry not available")
        
        # Prepare module-specific parameters
        module_params = {
            "request": step.get("input", request),
            "context": {
                **context,
                "step_id": step.get("id"),
                "step_name": step.get("name"),
                "journey_id": journey_id,
                "from_orchestrator_plan": True,
                "plan_step": True
            }
        }
        
        # Add any additional parameters from the step
        if "parameters" in step and isinstance(step["parameters"], dict):
            module_params["context"].update(step["parameters"])
        
        # Execute through module registry
        result = await self.module_registry.execute_module(
            module_name=module_name,
            request=module_params["request"],
            context=module_params["context"]
        )
        
        return result
    
    async def _execute_with_boardroom(self,
                                    step: Dict[str, Any],
                                    request: str,
                                    context: Dict[str, Any],
                                    journey_id: str) -> Dict[str, Any]:
        """
        Execute a step using BoardRoom as the generic executor.
        
        Args:
            step: The step configuration
            request: Original user request
            context: Execution context
            journey_id: Journey tracking ID
            
        Returns:
            Dict containing execution result
        """
        if not self.boardroom:
            raise ValueError("BoardRoom not available for step execution")
        
        # Track BoardRoom execution
        track_journey_step_sync(
            journey_id=journey_id,
            step_name=f"boardroom_execution",
            description=f"Executing with BoardRoom: {step.get('name', 'unnamed step')}",
            step_type="boardroom_execution"
        )
        
        # Prepare step-specific prompt
        step_prompt = f"""
        Execute this specific step as part of the larger plan:
        
        Step: {step.get('name', 'Unnamed Step')}
        Description: {step.get('description', 'No description provided')}
        
        Original Request: "{request}"
        
        Complete this task and return the results in a clear, structured format.
        If the task requires specific computations, data analysis, or reasoning,
        perform those operations and explain your process.
        
        Return your response in a format that can be easily integrated with other
        plan steps.
        """
        
        # Prepare BoardRoom context
        boardroom_context = {
            **context,
            "step_id": step.get("id"),
            "step_name": step.get("name"),
            "step_description": step.get("description"),
            "journey_id": journey_id,
            "from_orchestrator_plan": True,
            "plan_step": True
        }
        
        # Add any additional parameters from the step
        if "parameters" in step and isinstance(step["parameters"], dict):
            boardroom_context.update(step["parameters"])
        
        # Execute with BoardRoom
        # Attempt to use process_with_boardroom
        if hasattr(self.boardroom, 'process_with_boardroom'):
            # Check if it's async
            if asyncio.iscoroutinefunction(self.boardroom.process_with_boardroom):
                result = await self.boardroom.process_with_boardroom(step_prompt, boardroom_context)
            else:
                result = self.boardroom.process_with_boardroom(step_prompt, boardroom_context)
        else:
            # Fallback to process_query if available
            result = self.boardroom.process_query(
                query=step_prompt,
                context=boardroom_context
            )
        
        # Format result
        if isinstance(result, str):
            result = {
                "result": result,
                "success": True
            }
        elif not isinstance(result, dict):
            result = {
                "result": str(result),
                "success": True
            }
        
        # Check for bidirectional communication flags from BoardRoom
        if isinstance(result, dict) and "bidirectional_communication" in result:
            # Process bidirectional communication using Orchestrated Intelligence
            try:
                bidirectional_data = result.get("bidirectional_communication", {})
                needs_clarification = bidirectional_data.get("needs_user_clarification")
                clarification_topics = bidirectional_data.get("clarification_topics", [])
                
                # Log detection of bidirectional communication flags
                self.logger.info(f"[ORCHESTRATOR] Detected bidirectional communication flags from BoardRoom: needs_clarification={needs_clarification}")
                if needs_clarification and clarification_topics:
                    self.logger.info(f"[ORCHESTRATOR] Clarification topics: {clarification_topics}")
                    
                    # Route this through the intelligence module for Trevor Core integration
                    if self.intelligence and hasattr(self.intelligence, 'handle_bidirectional_communication'):
                        # Track this step in the journey
                        track_journey_step_sync(
                            journey_id=journey_id,
                            step_name="orchestrator_forwarding_clarification",
                            description="Jarvis Orchestrator forwarding clarification request to Intelligence module for Trevor Core",
                            step_type="bidirectional_communication",
                            input_data={
                                "needs_clarification": needs_clarification,
                                "clarification_topics": clarification_topics,
                                "journey_id": journey_id
                            }
                        )
                        
                        # Forward to intelligence module for Trevor Core handling
                        forward_result = self.intelligence.handle_bidirectional_communication(
                            journey_id=journey_id,
                            clarification_topics=clarification_topics,
                            communication_metadata={
                                "current_stage": "JarvisOrchestrator_to_JarvisIntelligence",
                                "next_stage": "JarvisIntelligence_to_TrevorCore",
                                "from_boardroom": True,
                                "bidirectional_flow": "BoardRoom → Jarvis Orchestrator → Jarvis Intelligence → Trevor Core → User"
                            }
                        )
                        
                        self.logger.info(f"[ORCHESTRATOR] Forwarded clarification request to Intelligence module: {forward_result.get('status', 'unknown')}")
                        
                        # Add forwarding result to the response
                        result["bidirectional_forwarded"] = True
                        result["forwarding_status"] = forward_result.get("status", "unknown")
            except Exception as e:
                self.logger.error(f"[ORCHESTRATOR] Error processing bidirectional communication: {str(e)}")
                self.logger.error(traceback.format_exc())
        
        return result
    
    def _serialize_safe(self, data):
        """
        Safely serialize data to JSON, handling special types like HandlerResult.
        
        Args:
            data: The data to serialize
            
        Returns:
            JSON-safe data structure
        """
        if data is None:
            return None
            
        if isinstance(data, dict):
            return {k: self._serialize_safe(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [self._serialize_safe(item) for item in data]
        elif hasattr(data, 'to_dict') and callable(getattr(data, 'to_dict')):
            # Handle objects with to_dict method (like HandlerResult)
            return self._serialize_safe(data.to_dict())
        elif hasattr(data, '__dict__') and not isinstance(data, (str, int, float, bool)):
            # Handle other objects by converting to dict
            return self._serialize_safe(data.__dict__)
        else:
            # Basic types should be JSON serializable
            return data

    # ================================
    # WORKSPACE TRANSFER MECHANISM
    # ================================
    
    async def _check_workspace_transfer_requirements(self, workspace: dict) -> Optional[dict]:
        """
        Check if workspace needs to be transferred between systems for optimal execution.
        This implements the detour idea for seamless workspace transfers.
        
        Args:
            workspace: The workspace to evaluate for transfer requirements
            
        Returns:
            Transfer request dict if transfer needed, None otherwise
        """
        try:
            workspace_id = workspace.get("workspace_id", "unknown")
            logging.info(f"[WORKSPACE-TRANSFER] Checking transfer requirements for workspace {workspace_id}")
            
            # Check if complexity has changed during execution
            current_complexity = workspace.get("trevor_analysis", {}).get("complexity", "unknown")
            execution_history = workspace.get("execution_history", [])
            
            # Analyze workspace context for transfer triggers
            transfer_triggers = []
            
            # Trigger 1: Simple task became complex during execution
            if current_complexity == "simple" and len(execution_history) >= 2:
                # If simple task has had multiple failed attempts, it might need BoardRoom collaboration
                failed_attempts = [h for h in execution_history if h.get("status") == "failed"]
                if len(failed_attempts) >= 2:
                    transfer_triggers.append({
                        "trigger": "simple_to_complex_escalation",
                        "reason": "Multiple failed attempts suggest need for collaborative planning",
                        "target_system": "boardroom",
                        "priority": "high"
                    })
            
            # Trigger 2: Complex task has simple subtasks that could be optimized
            if current_complexity == "complex":
                boardroom_plan = workspace.get("boardroom_plan", {})
                detailed_breakdown = boardroom_plan.get("detailed_breakdown", {})
                
                # Check for phases that could be handled as simple requests
                simple_phases = []
                for phase_name, phase_details in detailed_breakdown.items():
                    tasks = phase_details.get("tasks", [])
                    if len(tasks) == 1 and not phase_details.get("dependencies", []):
                        simple_phases.append(phase_name)
                
                if len(simple_phases) > 0:
                    transfer_triggers.append({
                        "trigger": "complex_to_simple_optimization",
                        "reason": f"Phases {simple_phases} could be handled as simple requests",
                        "target_system": "trevor_direct",
                        "phases": simple_phases,
                        "priority": "medium"
                    })
            
            # Trigger 3: Context accumulation suggests system handoff
            communication_log = workspace.get("communication_log", [])
            if len(communication_log) > 10:
                # Analyze communication patterns
                agent_counts = {}
                for comm in communication_log:
                    agent = comm.get("agent", "unknown")
                    agent_counts[agent] = agent_counts.get(agent, 0) + 1
                
                # If one system is dominating, might need handoff to specialized system
                if max(agent_counts.values()) > 7:
                    dominant_agent = max(agent_counts.keys(), key=lambda k: agent_counts[k])
                    if dominant_agent != "orchestrator":
                        transfer_triggers.append({
                            "trigger": "system_specialization_handoff",
                            "reason": f"Agent {dominant_agent} is handling most communication",
                            "target_system": f"{dominant_agent}_specialized",
                            "priority": "low"
                        })
            
            # Return highest priority transfer trigger
            if transfer_triggers:
                highest_priority = max(transfer_triggers, key=lambda t: {"high": 3, "medium": 2, "low": 1}[t["priority"]])
                logging.info(f"[WORKSPACE-TRANSFER] Transfer required: {highest_priority['trigger']}")
                return highest_priority
            
            return None
            
        except Exception as e:
            logging.error(f"[WORKSPACE-TRANSFER] Error checking transfer requirements: {str(e)}")
            return None
    
    async def _execute_workspace_transfer(self, workspace: dict, transfer_request: dict) -> dict:
        """
        Execute seamless workspace transfer between systems with full context preservation.
        
        Args:
            workspace: The workspace to transfer
            transfer_request: The transfer request details
            
        Returns:
            Transfer execution result
        """
        try:
            workspace_id = workspace.get("workspace_id", "unknown")
            target_system = transfer_request.get("target_system", "unknown")
            trigger = transfer_request.get("trigger", "unknown")
            
            logging.info(f"[WORKSPACE-TRANSFER] Transferring workspace {workspace_id} to {target_system} due to {trigger}")
            
            # Preserve complete context during transfer
            transfer_context = {
                "original_workspace": workspace.copy(),
                "transfer_reason": transfer_request.get("reason", ""),
                "transfer_timestamp": datetime.now().isoformat(),
                "source_system": "jarvis_orchestrator",
                "target_system": target_system,
                "transfer_id": f"transfer_{uuid.uuid4().hex[:8]}",
                "transfer_request": transfer_request  # Include the full transfer request
            }
            
            # Add transfer to communication log
            communication_log = workspace.get("communication_log", [])
            communication_log.append({
                "agent": "workspace_transfer_system",
                "message": f"Transferring workspace to {target_system}: {transfer_request['reason']}",
                "timestamp": datetime.now().isoformat(),
                "transfer_context": transfer_context
            })
            workspace["communication_log"] = communication_log
            
            # Execute transfer based on target system
            if target_system == "boardroom":
                return await self._transfer_to_boardroom(workspace, transfer_context)
            elif target_system == "trevor_direct":
                return await self._transfer_to_trevor_direct(workspace, transfer_context)
            elif target_system.endswith("_specialized"):
                return await self._transfer_to_specialized_system(workspace, transfer_context)
            else:
                logging.warning(f"[WORKSPACE-TRANSFER] Unknown target system: {target_system}")
                # Fallback to normal execution
                return await self._execute_workspace_fallback(workspace)
                
        except Exception as e:
            logging.error(f"[WORKSPACE-TRANSFER] Error executing workspace transfer: {str(e)}")
            return {
                "success": False,
                "workspace_id": workspace.get("workspace_id", "unknown"),
                "error": f"Transfer failed: {str(e)}",
                "response": "Workspace transfer failed, falling back to normal execution."
            }
    
    async def _transfer_to_boardroom(self, workspace: dict, transfer_context: dict) -> dict:
        """Transfer workspace to BoardRoom for collaborative planning"""
        try:
            logging.info(f"[WORKSPACE-TRANSFER] Transferring to BoardRoom with context preservation")
            
            # Enhance workspace with transfer context
            workspace["transfer_context"] = transfer_context
            workspace["status"] = "transferred_to_boardroom"
            
            # Use existing BoardRoom routing but with enhanced context
            enhanced_workspace = await self._route_to_boardroom(workspace)
            
            # Execute the enhanced workspace
            result = await self._execute_complex_workspace(enhanced_workspace)
            
            # Ensure the result indicates BoardRoom transfer
            if isinstance(result, dict):
                result["transfer_system"] = "boardroom"
                if "response" in result:
                    result["response"] = f"Processed via BoardRoom transfer: {result['response']}"
                else:
                    result["response"] = "Successfully processed via BoardRoom collaborative transfer"
            
            return result
            
        except Exception as e:
            logging.error(f"[WORKSPACE-TRANSFER] Error transferring to BoardRoom: {str(e)}")
            return await self._execute_workspace_fallback(workspace)
    
    async def _transfer_to_trevor_direct(self, workspace: dict, transfer_context: dict) -> dict:
        """Transfer workspace directly to Trevor for optimized simple execution"""
        try:
            logging.info(f"[WORKSPACE-TRANSFER] Transferring to Trevor direct execution")
            
            # Extract simple phases for direct execution
            phases_to_simplify = transfer_context.get("transfer_request", {}).get("phases", [])
            
            logging.info(f"[WORKSPACE-TRANSFER] Phases to simplify: {phases_to_simplify}")
            
            if phases_to_simplify:
                # Execute specified phases as simple requests
                results = []
                for phase in phases_to_simplify:
                    # Create simplified workspace for this phase
                    simple_workspace = {
                        "workspace_id": f"{workspace['workspace_id']}_phase_{phase}",
                        "original_request": f"Execute phase: {phase}",
                        "user_id": workspace.get("user_id"),
                        "trevor_analysis": {"complexity": "simple"},
                        "parent_workspace": workspace["workspace_id"],
                        "transfer_context": transfer_context
                    }
                    
                    result = await self._execute_simple_workspace(simple_workspace)
                    results.append(result)
                
                return {
                    "success": True,
                    "workspace_id": workspace["workspace_id"],
                    "response": f"Completed {len(results)} phases via Trevor direct execution",
                    "phase_results": results,
                    "execution_type": "transferred_simple"
                }
            else:
                # Full transfer to Trevor intelligence
                workspace["transfer_context"] = transfer_context
                return await self._execute_simple_workspace(workspace)
                
        except Exception as e:
            logging.error(f"[WORKSPACE-TRANSFER] Error transferring to Trevor: {str(e)}")
            return await self._execute_workspace_fallback(workspace)
    
    async def _transfer_to_specialized_system(self, workspace: dict, transfer_context: dict) -> dict:
        """Transfer workspace to specialized system based on context"""
        try:
            target_system = transfer_context.get("target_system", "")
            specialized_agent = target_system.replace("_specialized", "")
            
            logging.info(f"[WORKSPACE-TRANSFER] Transferring to specialized system: {specialized_agent}")
            
            # Enhance workspace for specialized execution
            workspace["transfer_context"] = transfer_context
            workspace["specialized_agent"] = specialized_agent
            
            # Use specialized execution path
            return await self._execute_with_specialized_agent(workspace, specialized_agent)
            
        except Exception as e:
            logging.error(f"[WORKSPACE-TRANSFER] Error transferring to specialized system: {str(e)}")
            return await self._execute_workspace_fallback(workspace)
    
    async def _execute_with_specialized_agent(self, workspace: dict, agent_name: str) -> dict:
        """Execute workspace with specialized agent"""
        try:
            # This would integrate with existing agent systems
            # For now, route to appropriate handler
            if hasattr(self, 'execute_handler_action'):
                result = await self.execute_handler_action(
                    agent_name, 
                    "handle_specialized_request", 
                    {
                        "workspace": workspace,
                        "specialized_context": workspace.get("transfer_context", {})
                    }
                )
                
                return {
                    "success": True,
                    "workspace_id": workspace["workspace_id"],
                    "response": str(result),
                    "execution_type": "specialized_agent",
                    "agent_used": agent_name
                }
            else:
                return await self._execute_workspace_fallback(workspace)
                
        except Exception as e:
            logging.error(f"[WORKSPACE-TRANSFER] Error with specialized agent {agent_name}: {str(e)}")
            return await self._execute_workspace_fallback(workspace)
    
    async def _execute_workspace_fallback(self, workspace: dict) -> dict:
        """Fallback execution when transfer fails"""
        try:
            logging.info(f"[WORKSPACE-TRANSFER] Using fallback execution for workspace {workspace.get('workspace_id')}")
            
            # Remove transfer context to avoid recursion
            original_workspace = workspace.get("transfer_context", {}).get("original_workspace", workspace)
            
            # Execute based on original complexity
            if original_workspace.get("trevor_analysis", {}).get("complexity") == "simple":
                return await self._execute_simple_workspace(original_workspace)
            else:
                return await self._execute_complex_workspace(original_workspace)
                
        except Exception as e:
            logging.error(f"[WORKSPACE-TRANSFER] Error in fallback execution: {str(e)}")
            return {
                "success": False,
                "workspace_id": workspace.get("workspace_id", "unknown"),
                "error": str(e),
                "response": "All execution methods failed."
            }
    
    # ================================
    # PHASE 2: OPTIMIZATION FEATURES
    # ================================
    
    async def _check_fast_path_optimization(self, workspace: dict) -> Optional[dict]:
        """
        PHASE 2: Fast-path detection for simple requests that can be handled immediately
        
        Args:
            workspace: The workspace to evaluate for fast-path optimization
            
        Returns:
            Optimized workspace if fast-path detected, None otherwise
        """
        try:
            request = workspace["original_request"].lower().strip()
            
            # Fast-path patterns for immediate simple response
            simple_patterns = [
                # Time/date requests
                (r'\b(what time|current time|time is it)\b', "simple", ["time"], "< 1 second"),
                (r'\b(what date|today\'s date|current date)\b', "simple", ["calendar"], "< 1 second"),
                
                # Simple commands
                (r'\b(open|launch|start)\s+\w+\b', "simple", ["application"], "< 5 seconds"),
                (r'\b(close|quit|exit)\s+\w+\b', "simple", ["application"], "< 5 seconds"),
                
                # Quick calculations
                (r'\b\d+\s*[+\-*/]\s*\d+\b', "simple", ["calculator"], "< 1 second"),
                
                # Simple reminders
                (r'\bremind me\b.*\b(in|at)\b.*\b(minute|hour|pm|am)\b', "simple", ["reminder"], "< 10 seconds"),
                
                # Basic information
                (r'\b(what is|define|meaning of)\b', "simple", ["search"], "< 5 seconds")
            ]
            
            for pattern, complexity, handlers, duration in simple_patterns:
                import re
                if re.search(pattern, request):
                    logging.info(f"[FAST-PATH] Detected simple pattern: {pattern}")
                    
                    # Create fast-path workspace
                    workspace["trevor_analysis"] = {
                        "complexity": complexity,
                        "initial_breakdown": [workspace["original_request"]],
                        "suggested_handlers": handlers,
                        "mcp_resources": [f"{handlers[0]}_tools" if handlers else "general_tools"],
                        "estimated_duration": duration,
                        "requires_collaboration": False,
                        "fast_path_pattern": pattern
                    }
                    workspace["status"] = "analyzed"
                    workspace["optimization_used"] = "fast_path"
                    
                    return workspace
            
            return None
            
        except Exception as e:
            logging.warning(f"[FAST-PATH] Error in fast-path detection: {str(e)}")
            return None
    
    async def _check_workspace_cache(self, workspace: dict) -> Optional[dict]:
        """
        PHASE 2: Check workspace cache for similar requests to avoid recomputation
        
        Args:
            workspace: The workspace to check against cache
            
        Returns:
            Cached workspace result if found, None otherwise
        """
        try:
            # Initialize cache if not exists
            if not hasattr(self, '_workspace_cache'):
                self._workspace_cache = {}
            
            request = workspace["original_request"]
            user_id = workspace.get("user_id", "unknown")
            
            # Generate cache key based on request similarity
            cache_key = self._generate_cache_key(request, user_id)
            
            # Check if we have a cached result
            if cache_key in self._workspace_cache:
                cached_entry = self._workspace_cache[cache_key]
                
                # Check if cache entry is still valid (not older than 1 hour)
                cache_age = time.time() - cached_entry["timestamp"]
                if cache_age < 3600:  # 1 hour cache validity
                    logging.info(f"[WORKSPACE-CACHE] Cache hit for key: {cache_key}")
                    
                    # Clone cached workspace with new workspace ID
                    cached_workspace = cached_entry["workspace"].copy()
                    cached_workspace["workspace_id"] = workspace["workspace_id"]
                    cached_workspace["created_at"] = workspace["created_at"]
                    cached_workspace["cache_hit"] = True
                    cached_workspace["cache_age_seconds"] = cache_age
                    
                    return cached_workspace
                else:
                    # Remove expired cache entry
                    del self._workspace_cache[cache_key]
                    logging.info(f"[WORKSPACE-CACHE] Expired cache entry removed: {cache_key}")
            
            return None
            
        except Exception as e:
            logging.warning(f"[WORKSPACE-CACHE] Error checking cache: {str(e)}")
            return None
    
    async def _cache_workspace_result(self, original_workspace: dict, analyzed_workspace: dict):
        """
        PHASE 2: Cache workspace analysis result for future similar requests
        
        Args:
            original_workspace: The original workspace before analysis
            analyzed_workspace: The workspace after Trevor analysis
        """
        try:
            # Initialize cache if not exists
            if not hasattr(self, '_workspace_cache'):
                self._workspace_cache = {}
            
            request = original_workspace["original_request"]
            user_id = original_workspace.get("user_id", "unknown")
            
            # Generate cache key
            cache_key = self._generate_cache_key(request, user_id)
            
            # Cache the analyzed workspace (without workspace-specific IDs)
            cache_entry = {
                "workspace": {
                    "original_request": analyzed_workspace["original_request"],
                    "trevor_analysis": analyzed_workspace.get("trevor_analysis", {}),
                    "status": analyzed_workspace.get("status"),
                    "optimization_used": analyzed_workspace.get("optimization_used", "analysis")
                },
                "timestamp": time.time(),
                "user_id": user_id
            }
            
            self._workspace_cache[cache_key] = cache_entry
            
            # Limit cache size to prevent memory bloat
            if len(self._workspace_cache) > 100:
                # Remove oldest entries
                oldest_key = min(self._workspace_cache.keys(), 
                               key=lambda k: self._workspace_cache[k]["timestamp"])
                del self._workspace_cache[oldest_key]
                logging.info(f"[WORKSPACE-CACHE] Removed oldest cache entry to maintain size limit")
            
            logging.info(f"[WORKSPACE-CACHE] Cached result for key: {cache_key}")
            
        except Exception as e:
            logging.warning(f"[WORKSPACE-CACHE] Error caching result: {str(e)}")
    
    def _generate_cache_key(self, request: str, user_id: str) -> str:
        """Generate a cache key based on request content and user"""
        try:
            import hashlib
            
            # Normalize request for caching
            normalized_request = request.lower().strip()
            
            # Create cache key from request content and user
            cache_content = f"{normalized_request}|{user_id}"
            cache_key = hashlib.md5(cache_content.encode()).hexdigest()[:16]
            
            return cache_key
            
        except Exception as e:
            logging.warning(f"[WORKSPACE-CACHE] Error generating cache key: {str(e)}")
            return f"fallback_{hash(request)}_{user_id}"
    
    async def _add_performance_monitoring(self, workspace: dict, stage: str, start_time: float, additional_metrics: dict = None):
        """
        PHASE 2: Add performance monitoring at each handoff point
        
        Args:
            workspace: The workspace to add metrics to
            stage: The stage name (e.g., 'trevor_analysis', 'boardroom_planning', 'execution')
            start_time: The start time of the stage
            additional_metrics: Additional metrics to include
        """
        try:
            execution_time = time.time() - start_time
            
            # Initialize performance metrics if not exists
            if "performance_metrics" not in workspace:
                workspace["performance_metrics"] = {}
            
            # Add stage metrics
            stage_metrics = {
                "execution_time": execution_time,
                "timestamp": datetime.now().isoformat(),
                "stage": stage
            }
            
            if additional_metrics:
                stage_metrics.update(additional_metrics)
            
            workspace["performance_metrics"][stage] = stage_metrics
            
            # Track overall performance
            if "overall_performance" not in workspace["performance_metrics"]:
                workspace["performance_metrics"]["overall_performance"] = {
                    "total_stages": 0,
                    "total_time": 0,
                    "stages_completed": []
                }
            
            overall = workspace["performance_metrics"]["overall_performance"]
            overall["total_stages"] += 1
            overall["total_time"] += execution_time
            overall["stages_completed"].append(stage)
            
            logging.info(f"[PERFORMANCE] {stage} completed in {execution_time:.3f}s")
            
        except Exception as e:
            logging.warning(f"[PERFORMANCE] Error adding performance metrics: {str(e)}")
    
    def get_performance_summary(self, workspace: dict) -> dict:
        """
        PHASE 2: Get a summary of workspace performance metrics
        
        Args:
            workspace: The workspace with performance metrics
            
        Returns:
            Performance summary dictionary
        """
        try:
            metrics = workspace.get("performance_metrics", {})
            overall = metrics.get("overall_performance", {})
            
            summary = {
                "total_execution_time": overall.get("total_time", 0),
                "stages_completed": overall.get("stages_completed", []),
                "optimization_used": workspace.get("optimization_used", "none"),
                "cache_hit": workspace.get("cache_hit", False),
                "stage_breakdown": {}
            }
            
            # Add individual stage timings
            for stage_name, stage_data in metrics.items():
                if stage_name != "overall_performance" and isinstance(stage_data, dict):
                    summary["stage_breakdown"][stage_name] = {
                        "time": stage_data.get("execution_time", 0),
                        "timestamp": stage_data.get("timestamp", "unknown")
                    }
            
            return summary
            
        except Exception as e:
            logging.warning(f"[PERFORMANCE] Error generating performance summary: {str(e)}")
            return {"error": str(e)}

            
# Missing routing function that's referenced but was not defined
async def route_task_to_appropriate_system(task_data: Dict[str, Any], journey_id: str = None) -> Dict[str, Any]:
    """
    Route a task to the appropriate system based on task complexity and content.
    
    This function analyzes the task and determines whether to use BoardRoom for complex tasks
    or route to appropriate handlers for simpler tasks.
    
    Args:
        task_data: Dictionary with task information including 'task' or 'text' field
        journey_id: Optional journey ID for tracking
        
    Returns:
        Dictionary with routing information and selected system
    """
    import hashlib
    import time
    
    # Generate a journey ID if not provided
    if not journey_id:
        task_content = str(task_data.get('task', task_data.get('text', '')))
        journey_id = f"route_{int(time.time())}_{hashlib.md5(task_content.encode()).hexdigest()[:8]}"
        
    logger.info(f"[ROUTE] Routing task to appropriate system - Journey: {journey_id}")
    logger.info(f"[ROUTE] Task: {task_data.get('task', task_data.get('text', ''))[:100]}...")
    
    try:
        # Get the intelligence module for enhanced routing
        from Jarvis_Agent_SDK.jarvis_orchestrated_intelligence import JarvisOrchestratedIntelligence
        
        # Check if this should go to BoardRoom based on complexity indicators
        task_text = task_data.get('task', task_data.get('text', ''))
        
        # Indicators that suggest BoardRoom routing
        boardroom_indicators = [
            'complex', 'multi-step', 'analyze', 'research', 'plan', 'strategy',
            'multiple', 'comprehensive', 'detailed analysis', 'break down',
            'step by step', 'systematic', 'thorough'
        ]
        
        complexity_score = sum(1 for indicator in boardroom_indicators if indicator.lower() in task_text.lower())
        
        if complexity_score >= 2 or len(task_text.split()) > 50:
            logger.info(f"[ROUTE] High complexity detected (score: {complexity_score}) - routing to BoardRoom")
            return {
                "success": True,
                "selected_system": "handler_board_room", 
                "task_data": task_data,
                "journey_id": journey_id,
                "routing_reason": "high_complexity_detected",
                "confidence": min(0.8 + (complexity_score * 0.05), 0.95)
            }
        else:
            logger.info(f"[ROUTE] Standard complexity (score: {complexity_score}) - using orchestrator intelligence")
            return {
                "success": True,
                "selected_system": "orchestrator_intelligence",
                "task_data": task_data, 
                "journey_id": journey_id,
                "routing_reason": "standard_complexity",
                "confidence": 0.7
            }
            
    except Exception as e:
        logger.error(f"[ROUTE] Error in task routing: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "selected_system": "fallback_orchestrator",
            "task_data": task_data,
            "journey_id": journey_id
        }

# Utility function for routing handler calls to MCP
async def route_to_mcp(handler_name: str, action: str, parameters: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Route a handler call to the appropriate MCP server.
    
    This function serves as a central utility for redirecting handler execution
    requests to the MCP system instead of using handler_all.
    
    Args:
        handler_name: Name of the handler to execute
        action: Action to perform
        parameters: Parameters for the action (optional)
        
    Returns:
        Dict containing the result of the execution
    """
    logging.info(f"Routing handler call to MCP: {handler_name}.{action}")
    
    try:
        # Prepare parameters
        if parameters is None:
            parameters = {}
            
        # Get the MCP server launcher to determine available servers
        try:
            from Jarvis_Agent_SDK.mcp_server_launcher import HANDLER_REGISTRY
            
            # Check if this handler has an MCP wrapper
            if handler_name not in HANDLER_REGISTRY:
                logging.warning(f"No MCP wrapper found for handler {handler_name}, falling back to direct execution")
                return await _direct_execute_handler_action_async(handler_name, action, parameters)
        except ImportError:
            logging.warning("MCP server launcher not available, falling back to direct execution")
            return await _direct_execute_handler_action_async(handler_name, action, parameters)
        
        # Get workspace ID from parameters if available for MCP context
        workspace_id = None
        if isinstance(parameters, dict):
            if "workspace_id" in parameters:
                workspace_id = parameters["workspace_id"]
            elif "context" in parameters and isinstance(parameters["context"], dict):
                workspace_id = parameters["context"].get("workspace_id")
        
        # Get workspace sharing manager
        workspace_sharing = get_workspace_sharing()
        if not workspace_sharing:
            logging.warning("Workspace sharing manager not available")
            
        # If we have workspace ID and workspace sharing, route through workspace MCP
        if workspace_id and workspace_sharing:
            logging.info(f"Routing through workspace MCP with workspace_id: {workspace_id}")
            
            # Use the route_handler_to_mcp function from workspace_sharing
            if hasattr(workspace_sharing, 'route_handler_to_mcp'):
                # Check if it's an async method
                if asyncio.iscoroutinefunction(workspace_sharing.route_handler_to_mcp):
                    result = await workspace_sharing.route_handler_to_mcp(
                        workspace_id=workspace_id,
                        handler_name=handler_name,
                        method_name=action,
                        parameters=parameters
                    )
                else:
                    # Use sync version in an async wrapper
                    loop = asyncio.get_event_loop()
                    result = await loop.run_in_executor(
                        None,
                        lambda: workspace_sharing.route_handler_to_mcp_sync(
                            workspace_id=workspace_id,
                            handler_name=handler_name,
                            method_name=action,
                            parameters=parameters
                        )
                    )
                
                return result
        
        # If no workspace routing or it failed, use direct MCP access
        # This would require implementing direct MCP client access
        # For now, we'll fall back to direct execution
        logging.warning(f"Direct MCP access not implemented yet, falling back to direct execution")
        return await _direct_execute_handler_action_async(handler_name, action, parameters)
        
    except Exception as e:
        logging.error(f"Error routing to MCP: {str(e)}")
        logging.error(traceback.format_exc())
        
        # Return a structured error response
        return {
            "success": False,
            "error": f"Error routing to MCP: {str(e)}",
            "error_type": type(e).__name__,
            "handler": handler_name,
            "action": action
        }
            
    async def process_user_feedback_for_boardroom(self, journey_id: str, user_feedback: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process user feedback coming from Trevor Core via Intelligence module and forward to BoardRoom.
        
        This method completes the bidirectional communication chain:
        User → Trevor Core → Intelligence Module → Jarvis Orchestrator → BoardRoom
        
        Args:
            journey_id: The journey ID for tracking
            user_feedback: Dictionary containing user feedback to clarification questions
            
        Returns:
            Dict with the result of forwarding feedback to BoardRoom
        """
        self.logger.info(f"[ORCHESTRATOR] Processing user feedback for journey {journey_id}")
        
        try:
            # First, track this step in the journey
            track_journey_step_sync(
                journey_id=journey_id,
                step_type="bidirectional_communication",
                step_name="orchestrator_received_user_feedback",
                description="Jarvis Orchestrator received user feedback from Intelligence Module",
                input_data={
                    "user_feedback": user_feedback,
                    "journey_id": journey_id
                },
                status="routing_to_boardroom"
            )
            
            # Verify we have a BoardRoom instance
            if not self.boardroom:
                raise ValueError("BoardRoom not available for user feedback processing")
            
            # Create the context object for BoardRoom
            boardroom_context = {
                "journey_id": journey_id,
                "user_feedback": user_feedback,
                "from_orchestrator": True,
                "communication_chain": {
                    "path": "User → Trevor Core → Intelligence → Orchestrator → BoardRoom",
                    "current_stage": "Orchestrator_to_BoardRoom",
                    "next_stage": "BoardRoom_processing_feedback"
                }
            }
            
            # Forward to BoardRoom
            # Check if BoardRoom has a method to handle user feedback
            if hasattr(self.boardroom, 'continue_conversation_with_feedback') and callable(getattr(self.boardroom, 'continue_conversation_with_feedback')):
                # Use specialized method if available
                method = self.boardroom.continue_conversation_with_feedback
                self.logger.info(f"[ORCHESTRATOR] Using continue_conversation_with_feedback to forward user feedback to BoardRoom")
            elif hasattr(self.boardroom, 'process_with_user_feedback') and callable(getattr(self.boardroom, 'process_with_user_feedback')):
                # Alternative method name if available
                method = self.boardroom.process_with_user_feedback
                self.logger.info(f"[ORCHESTRATOR] Using process_with_user_feedback to forward user feedback to BoardRoom")
            else:
                # Fallback to general processing with context
                method = self.boardroom.process_with_boardroom
                self.logger.info(f"[ORCHESTRATOR] Using process_with_boardroom as fallback to forward user feedback to BoardRoom")
            
            # Execute the method, handling async if needed
            user_feedback_prompt = f"Continuing with user clarification. User provided the following feedback: {json.dumps(user_feedback)}"
            
            if asyncio.iscoroutinefunction(method):
                result = await method(user_feedback_prompt, boardroom_context)
            else:
                result = method(user_feedback_prompt, boardroom_context)
                
            # Process the result
            if isinstance(result, str):
                result = {
                    "result": result,
                    "success": True
                }
            
            # Track successful forwarding of feedback to BoardRoom
            track_journey_step_sync(
                journey_id=journey_id,
                step_type="bidirectional_communication",
                step_name="feedback_forwarded_to_boardroom",
                description="User feedback successfully forwarded to BoardRoom",
                output_data={
                    "success": True,
                    "timestamp": datetime.now().isoformat()
                },
                status="feedback_processing_complete"
            )
            
            return {
                "success": True,
                "message": "User feedback successfully forwarded to BoardRoom",
                "journey_id": journey_id,
                "result": result
            }
            
        except Exception as e:
            self.logger.error(f"[ORCHESTRATOR] Error processing user feedback: {str(e)}")
            self.logger.error(traceback.format_exc())
            
            # Track the error
            track_journey_step_sync(
                journey_id=journey_id,
                step_type="bidirectional_communication",
                step_name="feedback_forwarding_error",
                description=f"Error forwarding user feedback to BoardRoom: {str(e)}",
                output_data={
                    "error": str(e),
                    "timestamp": datetime.now().isoformat()
                },
                status="error"
            )
            
            return {
                "success": False,
                "error": f"Failed to process user feedback: {str(e)}",
                "journey_id": journey_id
            }
            
    async def _compile_plan_result(self,
                               plan: Dict[str, Any],
                               step_results: Dict[str, Any],
                               completed_steps: set[str],
                               request: str) -> Dict[str, Any]:
        """
        Compile all step results into a final plan execution result.
        
        Args:
            plan: The execution plan
            step_results: Results from each step
            completed_steps: Set of completed step IDs
            request: Original user request
            
        Returns:
            Dict containing the final compiled result
        """
        # Check for special case where the plan specifies a final integration step
        if "final_integration" in plan:
            final_step_id = plan["final_integration"].get("step_id")
            if final_step_id and final_step_id in step_results:
                # Use the result from the final integration step as the primary result
                final_result = step_results[final_step_id].get("result", "")
                
                return {
                    "success": True,
                    "result": final_result,
                    "plan_summary": plan.get("plan_summary", "Plan executed successfully"),
                    "step_results": step_results,
                    "completed_steps": list(completed_steps)
                }
        
        # Otherwise, compile results from all steps
        all_results = {}
        for step_id, result in step_results.items():
            # Extract just the result content for cleaner output
            result_content = result.get("result", result)
            all_results[step_id] = result_content
        
        # Find the response synthesis method specified in the plan
        synthesis_method = plan.get("response_synthesis", "boardroom")
        
        if synthesis_method == "concatenate":
            # Simple concatenation of all step results
            final_result = "\n\n".join([
                f"**{step.get('name', f'Step {step_id}')}**:\n{str(all_results.get(step_id, 'No result'))}"
                for step in plan.get("steps", [])
                if step.get("id") in completed_steps
            ])
            
            return {
                "success": True,
                "result": final_result,
                "plan_summary": plan.get("plan_summary", "Plan executed successfully"),
                "step_results": step_results,
                "completed_steps": list(completed_steps)
            }
            
        elif synthesis_method == "last_step":
            # Use the result of the last completed step as the final result
            # Find the last step in the original plan order that was completed
            steps = plan.get("steps", [])
            for step in reversed(steps):
                step_id = step.get("id")
                if step_id in completed_steps:
                    final_result = step_results.get(step_id, {}).get("result", "")
                    
                    return {
                        "success": True,
                        "result": final_result,
                        "plan_summary": plan.get("plan_summary", "Plan executed successfully"),
                        "step_results": step_results,
                        "completed_steps": list(completed_steps)
                    }
            
        # Default: Use BoardRoom to synthesize the final response
        if self.boardroom:
            synthesis_prompt = f"""
            Synthesize a comprehensive response from these plan execution results:
            
            Original Request: "{request}"
            
            Plan Summary: {plan.get("plan_summary", "No summary available")}
            
            Step Results:
            {self._serialize_safe(all_results)}
            
            Create a cohesive response that addresses the original request by integrating
            the results from all steps. The response should be well-structured and read
            as a single unified answer rather than separate pieces.
            """
            
            synthesis_context = {
                "results": self._serialize_safe(all_results),
                "plan": plan,
                "request": request,
                "synthesis_task": True
            }
            
            try:
                # Attempt to use process_with_boardroom
                if hasattr(self.boardroom, 'process_with_boardroom'):
                    # Check if it's async
                    if asyncio.iscoroutinefunction(self.boardroom.process_with_boardroom):
                        synthesis_result = await self.boardroom.process_with_boardroom(synthesis_prompt, synthesis_context)
                    else:
                        synthesis_result = self.boardroom.process_with_boardroom(synthesis_prompt, synthesis_context)
                elif hasattr(self.boardroom, 'process_query'):
                    # Fallback to process_query if available
                    if asyncio.iscoroutinefunction(self.boardroom.process_query):
                        synthesis_result = await self.boardroom.process_query(
                            query=synthesis_prompt,
                            context=synthesis_context
                        )
                    else:
                        synthesis_result = self.boardroom.process_query(
                            query=synthesis_prompt,
                            context=synthesis_context
                        )
                else:
                    # If no boardroom methods available
                    synthesis_result = "Plan executed successfully. Details are in the step results."
                
                return {
                    "success": True,
                    "result": synthesis_result,
                    "plan_summary": plan.get("plan_summary", "Plan executed successfully"),
                    "step_results": self._serialize_safe(step_results),
                    "completed_steps": list(completed_steps)
                }
            except Exception as e:
                self.logger.warning(f"Error during BoardRoom synthesis: {str(e)}")
                # Fall back to simple aggregation
        
        # Fallback method: Return structured results
        return {
            "success": True,
            "result": "Plan executed successfully. See step_results for details.",
            "plan_summary": plan.get("plan_summary", "Plan executed successfully"),
            "step_results": self._serialize_safe(all_results),
            "completed_steps": list(completed_steps)
        }

    async def create_workspace_for_request(self, query: str, session_id: str, 
                                         user_id: str = None, observer_only: bool = True) -> dict:
        """
        ✅ NEW: Create workspace for user request in observer-only mode.
        Jarvis creates workspace but doesn't respond to user - Claude Central Feedback is primary interface.
        """
        try:
            # Import workspace manager
            from Database.workspace_connection_manager import WorkspaceConnectionManager
            
            # Generate workspace ID
            workspace_id = f"{session_id}_{int(time.time())}"
            
            # Initialize workspace connection manager
            workspace_manager = WorkspaceConnectionManager()
            workspace_db_path = workspace_manager.create_workspace_database(workspace_id)
            
            # Log as observer activity (not user-facing)
            self.logger.info(f"🔍 Jarvis Observer: Created workspace database {workspace_id} for session {session_id}")
            
            # Create workspace metadata in trevor_database for coordination
            try:
                conn = self._get_database_connection()
                cursor = conn.cursor()
                
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS workspace_coordination (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        workspace_id TEXT UNIQUE NOT NULL,
                        session_id TEXT NOT NULL,
                        user_id TEXT,
                        original_query TEXT,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        status TEXT DEFAULT 'active',
                        observer_mode BOOLEAN DEFAULT TRUE
                    )
                ''')
                
                cursor.execute('''
                    INSERT OR REPLACE INTO workspace_coordination 
                    (workspace_id, session_id, user_id, original_query, observer_mode)
                    VALUES (?, ?, ?, ?, ?)
                ''', (workspace_id, session_id, user_id, query, observer_only))
                
                conn.commit()
                conn.close()
                
            except Exception as db_error:
                self.logger.warning(f"Could not save workspace coordination data: {db_error}")
            
            return {
                'success': True,
                'workspace_id': workspace_id,
                'workspace_db_path': workspace_db_path,
                'observer_mode': observer_only,
                'message': f'Workspace {workspace_id} created in observer mode'
            }
            
        except Exception as e:
            self.logger.error(f"Error creating workspace for request: {e}")
            return {
                'success': False,
                'error': str(e),
                'workspace_id': session_id  # Fallback to session_id
            }

    async def coordinate_execution(self, workspace_id: str, execution_context: dict, 
                                 observer_only: bool = True) -> dict:
        """
        ✅ NEW: Coordinate execution in observer-only mode.
        Jarvis coordinates Trevor execution but doesn't respond to user.
        """
        try:
            # Jarvis coordinates execution but user never sees Jarvis responses
            self.logger.info(f"🔍 Jarvis Observer: Coordinating execution for workspace {workspace_id}")
            
            # Get Trevor execution capability if available
            execution_needed = execution_context.get('claude_response', '').lower()
            needs_trevor = any(trigger in execution_needed for trigger in [
                'open', 'launch', 'run', 'execute', 'start', 'create file', 'edit file'
            ])
            
            if needs_trevor:
                # Route to Trevor Core for execution (observer coordination only)
                try:
                    # Import Trevor Core bridge for execution
                    from Core.trevor_core import TrevorCore
                    trevor = TrevorCore()
                    
                    # Execute task through Trevor (observer coordination)
                    trevor_result = await trevor.handle_user_request(
                        execution_context.get('original_request', ''),
                        session_id=execution_context.get('session_id'),
                        workspace_id=workspace_id,
                        coordinator_only=True  # Trevor executes but Jarvis coordinates
                    )
                    
                    self.logger.info(f"🔍 Jarvis Observer: Trevor execution coordinated for workspace {workspace_id}")
                    
                    return {
                        'success': True,
                        'execution_result': trevor_result,
                        'coordinator': 'jarvis_observer',
                        'executor': 'trevor_core'
                    }
                    
                except Exception as trevor_error:
                    self.logger.warning(f"Trevor execution coordination failed: {trevor_error}")
                    
            # No execution needed - just coordinate observation
            return {
                'success': True,
                'execution_result': 'No execution required',
                'coordinator': 'jarvis_observer',
                'needs_execution': needs_trevor
            }
            
        except Exception as e:
            self.logger.error(f"Error coordinating execution: {e}")
            return {
                'success': False,
                'error': str(e),
                'coordinator': 'jarvis_observer'
            }

def get_orchestrator_instance():
    """
    Get a singleton instance of the JarvisOrchestrator.
    
    This function ensures that only one JarvisOrchestrator instance exists across
    the entire application, which helps maintain consistent state and prevents
    resource duplication.
    
    Returns:
        JarvisOrchestrator: A global singleton instance of JarvisOrchestrator
    """
    global _ORCHESTRATOR_INSTANCE, _ORCHESTRATOR_LOCK
    
    with _ORCHESTRATOR_LOCK:
        if _ORCHESTRATOR_INSTANCE is None:
            try:
                # Check for available Trevor Core instance
                trevor_core_instance = None
                
                # REMOVED: Trevor Core builtins access - causes recursion
                # Trevor Core should only be accessed through orchestrator bridge
                
                # Trevor instance creation removed - Trevor only exists in jarvis_orchestrated_intelligence
                # Jarvis Orchestrator operates without direct Trevor access
                logging.info("Jarvis Orchestrator using architecture without direct Trevor - intelligence handles all Trevor operations")
                
                # Create JarvisOrchestrator instance - Trevor access via intelligence layer
                _ORCHESTRATOR_INSTANCE = JarvisOrchestrator()
                logging.info(f"Created new JarvisOrchestrator instance - Trevor operations handled by intelligence: {id(_ORCHESTRATOR_INSTANCE)}")
                    
            except Exception as e:
                logging.error(f"Error creating JarvisOrchestrator instance: {str(e)}")
                logging.error(traceback.format_exc())
                return None
        
        return _ORCHESTRATOR_INSTANCE
