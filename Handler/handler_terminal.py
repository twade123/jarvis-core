#!/usr/bin/env python3
"""
Terminal Handler for Jarvis - Advanced Terminal Interface

This handler provides comprehensive capabilities for interacting with the terminal and filesystem,
enabling AI agents to perform complex system operations safely and effectively.

CORE CAPABILITIES:
-----------------
1. Terminal Command Execution:
   - Execute any shell command with full output capture
   - Run commands in specific directories
   - Execute commands within activated virtual environments

2. Terminal Session Management:
   - Create persistent terminal sessions
   - Send commands to specific sessions
   - Capture and retrieve command outputs
   - Manage multiple terminal windows

3. File Creation and Editing (with safety features):
   - Create new files with specified content
   - Edit existing files with automatic backups
   - Make line-by-line modifications
   - Insert content at specific positions (start, end, line number, or pattern matches)
   - Search and replace text across multiple files (with regex support)
   - Duplicate files with timestamps for safe editing
   - Restore from backups if needed

4. File Organization and Search:
   - Search for files by name patterns
   - Search file contents with pattern matching
   - Move, copy, or rename files based on patterns
   - Organize files into directories

5. Code Analysis and Testing:
   - Analyze codebase structure and file distribution
   - Safe testing of files in isolated environments
   - Execute Python files in virtual environments
   - Test before modifying to prevent errors

6. Virtual Environment Management:
   - Create and configure Python virtual environments
   - Activate environments for command execution
   - Install dependencies from requirements files
   - Execute commands within activated environments

7. Version Control:
   - Perform Git operations (status, add, commit, push, pull)
   - Clone repositories
   - Manage branches

SAFETY FEATURES:
--------------
- Automatic backup creation before file modifications
- Isolated testing environment for code execution
- File duplication with timestamps for safe edits
- Temporary file approach for atomic writes
- Easy restoration from backups

USAGE EXAMPLES:
-------------
1. Safe File Editing:
   handler.execute("safe_edit_file", {
       "file_path": "~/project/script.py", 
       "content": "new content here"
   })

2. Running Commands in Virtual Environment:
   handler.execute("execute_with_venv", {
       "command": "python3 script.py",
       "venv_path": "~/myenv"
   })

3. Testing Before Deployment:
   handler.execute("test_file", {
       "file_path": "~/project/script.py",
       "use_venv": True
   })

4. Analyzing Project Structure:
   handler.execute("analyze_codebase", {
       "directory": "~/project",
       "file_types": ["*.py", "*.js"]
   })

5. Pattern-based File Operations:
   handler.execute("file_operations", {
       "source_pattern": "*.log",
       "target_directory": "~/logs",
       "operation": "move"
   })

This handler enables AI agents to perform virtually any terminal operation, 
manage files, execute code safely, and understand project structures - all
with built-in safeguards to prevent data loss or system issues.
"""

import os
import sys
import time
import logging
import subprocess
import json
import asyncio
from typing import Dict, Any, Optional, List, Set
from pathlib import Path

# V2 database access for tracking
from Database.v2.db_helper import connection as v2_connection

# Import schema definitions for terminal operations
try:
    from Handler.terminal_schema_definitions import (
        TERMINAL_SCHEMA_COLLECTION,
        CLAUDE_CODE_EXECUTION_SCHEMA,
        ANALYZE_CODEBASE_SCHEMA,
        CLAUDE_INPUT_SCHEMA
    )
    logging.info("Successfully imported terminal schema definitions")
except ImportError:
    logging.warning("Failed to import terminal schema definitions, using default schemas")
    # Define minimal default schemas if import fails
    TERMINAL_SCHEMA_COLLECTION = {}
    CLAUDE_CODE_EXECUTION_SCHEMA = {
        "name": "execute_claude_code",
        "description": "Launches Claude Code in a terminal window",
        "parameters": {"type": "object", "properties": {}}
    }
    ANALYZE_CODEBASE_SCHEMA = {
        "name": "analyze_codebase",
        "description": "Analyzes a codebase using Claude Code",
        "parameters": {"type": "object", "properties": {}}
    }
    CLAUDE_INPUT_SCHEMA = {
        "name": "send_claude_input",
        "description": "Sends input to an active Claude Code session",
        "parameters": {"type": "object", "properties": {}}
    }

# Import handler base classes directly from their source
try:
    # Try to import directly from Handler.handler_base which is the canonical source
    from Handler.handler_base import BaseHandler, HandlerResult
    logging.info("Successfully imported BaseHandler and HandlerResult from Handler.handler_base")
except ImportError:
    # Fallback to Jarvis_Agent_SDK.base which has a simplified version
    try:
        from Jarvis_Agent_SDK.base import BaseHandler
        logging.info("Successfully imported BaseHandler from Jarvis_Agent_SDK.base")
        # Create a compatible HandlerResult class
        class HandlerResult:
            def __init__(self, success=True, data=None, error=None, metadata=None):
                self.success = success
                self.data = data
                self.error = error
                self.metadata = metadata or {}
                
            def to_dict(self):
                return {
                    "success": self.success,
                    "data": self.data,
                    "error": self.error,
                    "metadata": self.metadata
                }
    except ImportError:
        logging.warning("Failed to import handler classes, using mock classes")
        class BaseHandler:
            def __init__(self):
                pass
        
        class HandlerResult:
            def __init__(self, success=True, result=None, error=None, details=None):
                self.success = success
                self.result = result
                self.error = error
                self.details = details or {}

# Import agent components if available
try:
    # Try to import directly from Handler.agents
    from Handler.agents.base_agent import BaseAgent
    # Define a compatible AgentManager class
    class AgentManager:
        def __init__(self):
            self.agents = {}
            
        def register_agent(self, agent):
            self.agents[agent.name] = agent
            
        def get_agent(self, name):
            return self.agents.get(name)
    
    AGENT_COMPONENTS_AVAILABLE = True
    logging.info("Successfully imported agent components")
except ImportError:
    print("Warning: Agent components not available - specialized agent features disabled")
    AGENT_COMPONENTS_AVAILABLE = False

# Import from base directly to avoid circular dependencies
from Jarvis_Agent_SDK.base import generate_request_id, generate_simple_id

# Import common utilities and workflow tools
from Jarvis_Agent_SDK.boardroom_connector import (
    track_request_journey_sync,
    track_journey_step,
    update_journey_state,
    complete_journey,
)

from Jarvis_Agent_SDK.workflow_tools import (
    execute_validated_analysis_workflow,
    route_to_appropriate_system
)

# Initialize a logger for this module
logger = logging.getLogger(__name__)

class TerminalHandlerOrchestratorAgent:
    """
    Orchestrator agent for the Terminal Handler System.
    
    This agent serves as a bridge between the terminal handler system and the Jarvis orchestrator,
    managing terminal operations and facilitating bidirectional communication with Jarvis.
    
    Core Responsibilities:
    1. Terminal Operation Management
       - Execute and monitor terminal commands
       - Manage terminal sessions and environments
       - Handle command execution tracking
       
    2. Workflow Integration
       - Route tasks to appropriate systems
       - Execute validated analysis workflows
       - Track data lineage and transformations
       
    3. System Communication
       - Bidirectional communication with Jarvis
       - Integration with BoardRoom tracking
       - Error reporting and recovery
       - Communication with BoardRoom for context sharing
       
    4. Performance Monitoring
       - Track metrics and KPIs
       - Monitor system health
       
    This agent also supports bidirectional communication with the BoardRoom through
    the boardroom_orchestrator_bridge, allowing it to share context and respond to
    direct queries about terminal capabilities.
    """
    
    def __init__(self, system_name="TerminalHandlerSystem"):
        """Initialize the orchestrator agent."""
        # Handle case where system_name is actually a TerminalHandler object
        if hasattr(system_name, 'system_name'):
            self.terminal_handler = system_name
            self.system_name = "TerminalHandlerSystem"
        else:
            self.system_name = system_name
            # We'll lazy-initialize terminal_handler when needed
            self.terminal_handler = None
            
        self.active = True
        self.initialized = False
        self.logger = logging.getLogger(__name__)
        self.agent_id = f"{self.system_name}_orchestrator_{int(time.time())}"
        self.system_id = f"{self.system_name}_{int(time.time())}"
        self.workspace_id = f"{self.system_name.lower()}_{int(time.time())}"
        
        # Load function schemas for the agent
        self.function_schemas = {
            "execute_claude_code": CLAUDE_CODE_EXECUTION_SCHEMA,
            "analyze_codebase": ANALYZE_CODEBASE_SCHEMA,
            "send_claude_input": CLAUDE_INPUT_SCHEMA
        }
        
        # BoardRoom was archived (Phase 3). Tracking uses V2 databases directly.
        self.boardroom = None
            
        self.request_journey_map = {}
        self.active_journeys = set()
        self.journey_steps = {}
        
        # Initialize metrics
        self.metrics = {
            "messages_sent": 0,
            "messages_received": 0,
            "errors_reported": 0,
            "commands_tracked": 0,
            "workflows_executed": 0,
            "tasks_routed": 0
        }
        
        # Track Jarvis communications specifically
        self.jarvis_communications = []
        self.to_jarvis_counter = 0
        self.from_jarvis_counter = 0
        
        # Initialize OpenAI client
        self.client = None
        self.model = "gpt-4-turbo-preview"  # Default model
        self._initialize_client()
        
        self.logger.info(f"TerminalHandlerOrchestratorAgent initialized for {self.system_name}")
        try:
            self._setup_boardroom_connection()
        except Exception as e:
            self.logger.warning(f"Could not set up boardroom connection: {str(e)}")
        
        # Initialize tracking without triggering async methods
        try:
            self.init_tracking(f"{int(time.time())}", "TerminalHandlerOrchestratorAgent initialized")
        except Exception as e:
            self.logger.warning(f"Could not initialize tracking: {str(e)}")
        
    def _get_terminal_handler(self):
        """Get or initialize the terminal handler."""
        print("\n🔥🔥🔥 _GET_TERMINAL_HANDLER CALLED IN ORCHESTRATOR AGENT 🔥🔥🔥")
        
        if self.terminal_handler is None:
            print("🔥 INITIALIZING NEW TERMINAL HANDLER!")
            # Import locally to avoid circular imports
            self.terminal_handler = TerminalHandler()
            print(f"🔥 NEW TERMINAL HANDLER CREATED: {self.terminal_handler}")
        else:
            print(f"🔥 USING EXISTING TERMINAL HANDLER: {self.terminal_handler}")
            
        return self.terminal_handler
        
        # Load function schemas for the agent
        self.function_schemas = {
            "execute_claude_code": CLAUDE_CODE_EXECUTION_SCHEMA,
            "analyze_codebase": ANALYZE_CODEBASE_SCHEMA,
            "send_claude_input": CLAUDE_INPUT_SCHEMA
        }
        
        # Initialize tracking interfaces (dead code path — left for reference)
        self.boardroom = None
        self.request_journey_map = {}
        self.active_journeys = set()
        self.journey_steps = {}
        
        # Initialize metrics
        self.metrics = {
            "messages_sent": 0,
            "messages_received": 0,
            "errors_reported": 0,
            "commands_tracked": 0,
            "workflows_executed": 0,
            "tasks_routed": 0
        }
        
        # Track Jarvis communications specifically
        self.jarvis_communications = []
        self.to_jarvis_counter = 0
        self.from_jarvis_counter = 0
        
        # Initialize OpenAI client
        self.client = None
        self.model = "gpt-4-turbo-preview"  # Default model
        self._initialize_client()
        
        self.logger.info(f"TerminalHandlerOrchestratorAgent initialized for {self.system_name}")
        self._setup_boardroom_connection()
        
        # Initialize tracking without triggering async methods
        self.init_tracking(f"{int(time.time())}", "TerminalHandlerOrchestratorAgent initialized")

    def _initialize_client(self):
        """
        Initialize the OpenAI client with API key.
        
        This method handles the OpenAI client initialization process with multiple fallback mechanisms:
        1. Attempts to retrieve API key from CONFIG if already loaded
        2. Tries to load API key from file using load_api_key('OPENAI')
        3. Falls back to environment variables if needed
        
        The method also sets up proper error handling and logging for initialization failures.
        
        Side Effects:
            - Sets self.client to AsyncOpenAI instance if successful
            - Sets API key in environment variables if loaded from file
            - Logs initialization status and any errors
        
        Returns:
            None
        """
        try:
            # Try to get the API key from CONFIG if it's already loaded
            from Core.config import CONFIG, load_api_key
            
            api_key = CONFIG.get('OPENAI_API_KEY')
            if not api_key:
                # If not in CONFIG, try to load it
                api_key = load_api_key('OPENAI')
                if api_key:
                    # If we successfully loaded it, also set it in the environment
                    import os
                    os.environ["OPENAI_API_KEY"] = api_key
            
            if not api_key:
                # Try to get from environment as last resort
                api_key = os.environ.get("OPENAI_API_KEY")
            
            if api_key:
                from openai import AsyncOpenAI
                self.client = AsyncOpenAI(api_key=api_key)
                self.logger.info("OpenAI client initialized successfully")
            else:
                self.logger.error("Could not initialize OpenAI client - no API key found")
                
        except Exception as e:
            self.logger.error(f"Error initializing OpenAI client: {str(e)}")

    async def get_ai_response(self, messages, temperature=0.7):
        """
        Get a response from the OpenAI model.
        
        This method handles the asynchronous communication with OpenAI's API,
        managing the conversation context and handling potential errors.
        
        Args:
            messages (list): List of message dictionaries with role and content.
                Each message should have the format: {"role": "user"|"assistant"|"system", "content": "message"}
            temperature (float, optional): Controls randomness in the response.
                0.0 means focused and deterministic, 1.0 means more creative.
                Defaults to 0.7 for balanced responses.
        
        Returns:
            str: The model's response text if successful, None if an error occurs
            
        Raises:
            No exceptions are raised; errors are logged and None is returned
            
        Example:
            response = await agent.get_ai_response([
                {"role": "user", "content": "How do I list files in a directory?"}
            ])
        """
        if not self.client:
            self.logger.error("OpenAI client not initialized")
            return None
            
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature
            )
            return response.choices[0].message.content
        except Exception as e:
            self.logger.error(f"Error getting AI response: {str(e)}")
            return None

    def _setup_boardroom_connection(self):
        """BoardRoom was archived (Phase 3). Stub retained for caller compatibility."""
        self.boardroom = None
            
    def init_tracking(self, request_id, description="System initialized"):
        """Initialize tracking safely without using async methods"""
        try:
            # Create a journey ID without relying on async methods
            journey_id = f"{self.system_name}_{int(time.time())}_{generate_simple_id()}"
            
            # Store the journey ID for this request
            self.request_journey_map[request_id] = journey_id
            self.active_journeys.add(journey_id)
            
            # Directly record in our local tracking
            self.journey_steps[journey_id] = ["initialization"]
            
            # Try to track the journey using the non-async version if available
            try:
                if hasattr(self.boardroom, 'track_request_journey_sync'):
                    self.boardroom.track_request_journey_sync(
                        request_id=request_id,
                        journey_id=journey_id,
                        system_id=self.system_id,
                        task=description
                    )
                    self.logger.info(f"Initialized tracking for journey {journey_id}")
                elif hasattr(self.boardroom, 'track_request_journey'):
                    # Use sync version instead
                    track_request_journey_sync(
                        request_id=request_id,
                        task=description,
                        system_id=self.system_id
                    )
                    self.logger.info(f"Created fallback journey {journey_id} for request {request_id}")
            except Exception as e:
                self.logger.warning(f"Could not track request journey: {str(e)}")
                
            return journey_id
        except Exception as e:
            self.logger.error(f"Error initializing tracking: {str(e)}")
            return f"{self.system_name}_fallback_{int(time.time())}"
            
    def _track_jarvis_communication(self, direction, message, journey_id=None, _prevent_recursion=False):
        """
        Track communication with the Jarvis orchestrator
        
        Args:
            direction: 'input' or 'output'
            message: The message being tracked
            journey_id: Optional journey ID
            _prevent_recursion: Flag to prevent infinite recursion
        """
        import time as time_module
        import inspect
        
        if not journey_id:
            journey_id = self.current_journey_id or f"jarvis_comm_{int(time_module.time())}"
        
        # Create tracking data with timestamp and message metadata
        tracking_data = {
            "timestamp": time_module.time(),
            "direction": direction,
            "message_type": str(type(message).__name__),
            "system": "TerminalOrchestratorAgent"
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
        
        # Store in conversation history
        if not hasattr(self, 'conversation_history'):
            self.conversation_history = []
            
        conversation_entry = {
            "timestamp": tracking_data["timestamp"],
            "direction": direction,
            "content": safe_message,
            "journey_id": journey_id
        }
        
        self.conversation_history.append(conversation_entry)
        
        # Track using both local and BoardRoom tracking
        try:
            # Add step to journey steps
            input_data = None
            output_data = None
            
            if direction == "input":
                input_data = safe_message
            else:
                output_data = safe_message
                
            try:
                self._add_to_journey_steps(journey_id, "jarvis_communication", step_data["description"], 
                                         input_data, output_data)
            except Exception as e:
                logger.error(f"Error adding to journey steps: {str(e)}")
                # Continue execution even if this fails
            
            # Try BoardRoom tracking if not in recursive call
            if not _prevent_recursion:
                # Not awaiting here since we want non-blocking behavior
                try:
                    self.track_step(
                        journey_id=journey_id,
                        step_name=f"jarvis_{direction}",
                        description=f"Jarvis communication ({direction})",
                        step_type="communication",
                        input_data=direction == "input" and {"message": safe_message} or None,
                        output_data=direction == "output" and {"message": safe_message} or None
                    )
                except Exception as e:
                    logger.error(f"Error tracking step: {str(e)}")
                    # Continue execution even if this fails
                
        except Exception as e:
            # Just log the error without failing
            logger.error(f"Error tracking jarvis communication: {str(e)}")
        
        # Update counters
        if direction == "input":
            self.from_jarvis_counter += 1
        else:
            self.to_jarvis_counter += 1
            
        return True

    async def track_request(self, request_id: str, description: str) -> str:
        """Track a new request journey."""
        journey_id = f"terminal_request_{int(time.time())}_{generate_simple_id()}"
        
        try:
            boardroom = self.boardroom
            
            if boardroom:
                # Check if BoardRoom has track_request_journey method
                if hasattr(boardroom, 'track_request_journey_sync'):
                    # Call the sync version with common parameters
                    journey_id = track_request_journey_sync(
                        request_id=request_id,
                        task=description,
                        system_id=self.system_id
                    )
                else:
                    # Direct implementation if track_request_journey is missing
                    if not hasattr(boardroom, 'request_journeys'):
                        boardroom.request_journeys = {}
                    
                    # Create journey data
                    journey_data = {
                        "journey_id": journey_id,
                        "request_id": request_id,
                        "description": description,
                        "system_id": self.system_id,
                        "start_time": time.time(),
                        "steps": [],
                        "completed": False
                    }
                    
                    # Store in BoardRoom
                    boardroom.request_journeys[journey_id] = journey_data
                    logger.info(f"Created journey directly in BoardRoom: {journey_id}")
            else:
                logger.info(f"No BoardRoom available, using local journey: {journey_id}")
        except Exception as e:
            logger.error(f"Error tracking request journey: {str(e)}")
            # Continue with local tracking even if BoardRoom tracking fails
        
        # Always maintain local tracking
        self.request_journey_map[request_id] = journey_id
        self.active_journeys.add(journey_id)
        
        return journey_id

    async def track_step(self, journey_id: str, step_name: str, description: str,
                        step_type: str, input_data: Dict = None, output_data: Dict = None):
        """
        Track a journey step with the given information.
        
        Args:
            journey_id: The unique ID for the journey
            step_name: The name of the step
            description: A human-readable description of the step
            step_type: The type of step (e.g., "request", "response", "error")
            input_data: The input data for the step
            output_data: The output data for the step
            
        Returns:
            Future: A future resolving to True if successful, False otherwise
        """
        # Set default values if not provided
        if input_data is None:
            input_data = {"default_empty": True}
        if output_data is None:
            output_data = {"default_empty": True}
        
        # Create a future to return
        future = asyncio.get_event_loop().create_future()
        
        try:
            # Use the BoardRoom tracking if available
            boardroom = self.boardroom
            
            # Attempt BoardRoom tracking first
            if boardroom:
                # Implement direct boardroom tracking if track_journey_step is missing
                if not hasattr(boardroom, 'track_journey_step'):
                    # Internal fallback implementation for BoardRoom tracking
                    if not hasattr(boardroom, 'journey_steps'):
                        boardroom.journey_steps = {}
                    
                    # Initialize journey if it doesn't exist
                    if journey_id not in boardroom.journey_steps:
                        boardroom.journey_steps[journey_id] = []
                    
                    # Create step data
                    step_data = {
                        "journey_id": journey_id,
                        "step_name": step_name,
                        "description": description,
                        "step_type": step_type,
                        "timestamp": time.time(),
                        "input_data": input_data,
                        "output_data": output_data
                    }
                    
                    # Add to BoardRoom's journey steps
                    boardroom.journey_steps[journey_id].append(step_data)
                    logger.info(f"Added step to BoardRoom via direct implementation: {journey_id} - {step_name}")
                    
                    # Set the future's result
                    future.set_result(True)
                else:
                    # Use the existing track_journey_step method
                    try:
                        # Check if it's async or sync
                        if asyncio.iscoroutinefunction(boardroom.track_journey_step):
                            # Use await directly for async function
                            result = await boardroom.track_journey_step(
                                journey_id=journey_id,
                                step_name=step_name,
                                description=description,
                                step_type=step_type,
                                input_data=input_data,
                                output_data=output_data
                            )
                            future.set_result(result)
                        else:
                            # Call sync function and wrap result in future
                            result = boardroom.track_journey_step(
                                journey_id=journey_id,
                                step_name=step_name,
                                description=description,
                                step_type=step_type,
                                input_data=input_data,
                                output_data=output_data
                            )
                            future.set_result(result)
                    except Exception as e:
                        logger.error(f"Error using BoardRoom.track_journey_step: {str(e)}")
                        # Handle the error but continue to fallback
                        future.set_result(False)
            
            # Always do local tracking as backup
            self._add_to_journey_steps(
                journey_id=journey_id,
                step_name=step_name,
                description=description,
                step_type=step_type,
                input_data=input_data,
                output_data=output_data
            )
            
            # If future hasn't been set yet, set it now
            if not future.done():
                future.set_result(True)
            
            return future
        except Exception as e:
            logger.error(f"Error tracking step: {str(e)}")
            # Set the future's result in case of exception
            if not future.done():
                future.set_result(False)
            # Return a Future to make this awaitable
            future = asyncio.get_event_loop().create_future()
            future.set_result(False)
            return future

    def _add_to_journey_steps(self, journey_id: str, step_name: str, description: str,
                           step_type: str, input_data: Dict, output_data: Dict):
        """
        Add a step to the journey_steps tracker for local tracking.
        
        Args:
            journey_id: The unique ID for the journey
            step_name: The name of the step
            description: A human-readable description of the step
            step_type: The type of step (e.g., "request", "response", "error")
            input_data: The input data for the step
            output_data: The output data for the step
        """
        if not hasattr(self, 'journey_steps'):
            self.journey_steps = {}
        
        # Initialize the journey if it doesn't exist
        if journey_id not in self.journey_steps:
            self.journey_steps[journey_id] = []
        
        # Add the step to the journey
        step_data = {
            'step_name': step_name,
            'description': description,
            'step_type': step_type,
            'input_data': input_data,
            'output_data': output_data,
            'timestamp': time.time()
        }
        
        self.journey_steps[journey_id].append(step_data)
        
        # Log the journey step using the module logger
        logger.info(f"Tracked journey step locally: {journey_id} - {step_name} - {description}")

    async def get_journey_status(self, journey_id: str) -> Dict:
        """Get the status of a journey."""
        try:
            if journey_id in self.active_journeys:
                return {"status": "active", "steps": self.journey_steps.get(journey_id, [])}
            return {"status": "not_found", "message": f"Journey {journey_id} not found"}
        except Exception as e:
            self.logger.error(f"Error getting journey status: {str(e)}")
            return {"status": "error", "message": str(e)}

    async def get_status(self) -> Dict:
        """Get the current status of the handler."""
        return {
            "status": "active" if self.active else "inactive",
            "metrics": self.metrics,
            "active_journeys": len(self.active_journeys),
            "total_commands": len(self.command_history),
            "errors": len(self.error_log)
        }

    async def send_message_to_jarvis(self, message, message_type="update", context=None):
        """
        Send a message to the Jarvis orchestrator with tracking and context management.

        This method handles all communication with Jarvis, including:
        - Message delivery with type classification
        - Context tracking and preservation
        - Communication metrics updates
        - Journey state management
        - Error handling and recovery

        Args:
            message (Union[str, Dict]): The message content to send to Jarvis
            message_type (str, optional): Type of message. Defaults to "update".
                Valid types: "update", "instruction", "error", "status", "completion"
            context (Dict, optional): Additional context for the message.
                Can include: journey_id, task_id, workspace_id, etc.

        Returns:
            Tuple[bool, str]: Tuple containing:
                - success: Boolean indicating if message was delivered
                - journey_id: ID of the communication journey
        """
        # Generate request ID and start tracking
        from Jarvis_Agent_SDK.common_utils import generate_request_id
        
        # Create task data for generate_request_id
        task_data = {"message": message, "timestamp": time.time()}
        request_id = generate_request_id(task_data)
        
        journey_id = await self.track_request(
            request_id=request_id,
            description=f"Sending message to Jarvis orchestrator: {message_type}"
        )
        
        # Initialize context if needed
        if context is None:
            context = {}
            
        # Ensure message_to_jarvis is in context
        if "message_to_jarvis" not in context:
            context["message_to_jarvis"] = message
            
        # Add system information to context
        context["system_name"] = self.system_name
        context["agent_id"] = self.agent_id
        context["agent_type"] = "terminal_orchestrator"
        context["journey_id"] = journey_id
        
        # Track the outgoing message
        await self.track_step(
            journey_id=journey_id,
            step_name="outgoing_message",
            description=f"Sending message to Jarvis orchestrator",
            step_type="outbound_communication",
            input_data={
                "message_to_jarvis": message,
                "message_type": message_type,
                "context": context
            }
        )
        
        try:
            # Try to use Jarvis orchestrator API
            try:
                from Jarvis_Agent_SDK.import_helper import get_execute_handler_action_async
                execute_handler_action_async = get_execute_handler_action_async()
                
                if execute_handler_action_async is None:
                    from Jarvis_Agent_SDK.jarvis_orchestrator import execute_handler_action_async
            except ImportError:
                from Jarvis_Agent_SDK.jarvis_orchestrator import execute_handler_action_async
                
            # Prepare parameters for the orchestrator
            parameters = {
                "message": message,
                "message_type": message_type,
                "context": context
            }
            
            # Send message to Jarvis via orchestrator
            try:
                # Try direct import from Jarvis_Agent_SDK
                from Jarvis_Agent_SDK.jarvis_orchestrator import process_handler_message
                result = await process_handler_message(
                    message=message,
                    message_type=message_type,
                    context=context
                )
            except ImportError:
                # Fall back to execute_handler_action_async
                result = await execute_handler_action_async(
                    "jarvis_orchestrator", 
                    "process_handler_message", 
                    parameters
                )
            
            # Update metrics
            self.metrics["messages_sent"] += 1
            
            # Track the received response
            await self.track_step(
                journey_id=journey_id,
                step_name="response_received",
                description=f"Received response from Jarvis",
                step_type="inbound_communication",
                output_data=result
            )
            
            return True, journey_id
                
        except Exception as e:
            self.logger.error(f"Error sending message to Jarvis: {str(e)}")
            
            # Track the error
            await self.track_step(
                journey_id=journey_id,
                step_name="send_error",
                description=f"Error sending message to Jarvis",
                step_type="error",
                output_data={"error": str(e)}
            )
            
            return False, journey_id
            
    async def notify_command_execution(self, command, result, metrics=None, journey_id=None):
        """
        Notify Jarvis about the execution of a terminal command and its results.

        This method provides comprehensive tracking and notification of command execution:
        - Command execution details
        - Performance metrics
        - Resource usage
        - Error states
        - Journey tracking

        Args:
            command (Union[str, Dict]): The command that was executed
                If Dict, should contain:
                - command_str: The actual command string
                - working_dir: Directory where command was executed
                - environment: Relevant environment variables
            result (Dict): Execution result containing:
                - success: Boolean indicating if command succeeded
                - output: Command output (stdout/stderr)
                - return_code: Command return code
                - error: Error message if any
            metrics (Dict, optional): Performance metrics including:
                - execution_time: Time taken to execute
                - memory_usage: Peak memory usage
                - cpu_usage: CPU utilization
                - io_operations: Count of I/O operations
            journey_id (str, optional): ID of the journey this command is part of

        Returns:
            Tuple[bool, str]: Tuple containing:
                - success: Boolean indicating if notification was sent
                - journey_id: ID of the associated journey
        """
        if metrics is None:
            metrics = {}
            
        # Use existing journey_id or create new one
        if not journey_id:
            from Jarvis_Agent_SDK.boardroom_connector import generate_request_id
            request_id = f"terminal_cmd_{int(time.time())}"
            journey_id = await self.track_request(
                request_id=request_id,
                description=f"Command execution notification: {command[:50]}..."
            )
            
        # Update metrics
        self.metrics["commands_tracked"] += 1
        
        # Track the notification
        await self.track_step(
            journey_id=journey_id,
            step_name="command_notification",
            description=f"Notifying orchestration system of command execution",
            step_type="command_tracking",
            input_data={
                "command": command,
                "result": result,
                "metrics": metrics
            }
        )
        
        # Prepare completion message
        message = f"Command execution completed: {command}"
        
        # Create detailed context
        context = {
            "command": command,
            "result": result,
            "system_name": self.system_name,
            "agent_id": self.agent_id,
            "metrics": metrics,
            "message_to_jarvis": message,
            "completion_time": time.time(),
            "journey_id": journey_id
        }
        
        # Determine if this request is from BoardRoom or Jarvis
        from_boardroom = metrics.get("from_boardroom", False) or "boardroom" in str(metrics.get("requested_by", "")).lower()
        
        if from_boardroom:
            # If request is from BoardRoom, use BoardRoom communication path
            self.logger.info("Using BoardRoom communication path for command notification")
            
            # Explicitly notify the BoardRoom about the command completion
            try:
                # Import the orchestrator bridge for direct BoardRoom communication
                from Jarvis_Agent_SDK.boardroom_orchestrator_bridge import send_terminal_notification_to_boardroom
                
                # Create structured notification for BoardRoom
                boardroom_notification = {
                    "message_type": "command_completion",
                    "command": command,
                    "result": result,
                    "journey_id": journey_id,
                    "source": "terminal_handler",
                    "timestamp": time.time()
                }
                
                # Send the message to BoardRoom via the orchestrator bridge
                await send_terminal_notification_to_boardroom(
                    journey_id=journey_id, 
                    notification=boardroom_notification,
                    metadata={"from_terminal": True, "notification_type": "command_completion"}
                )
                self.logger.info(f"✅ Successfully sent command completion to BoardRoom via orchestrator bridge: {journey_id}")
                
            except Exception as e:
                self.logger.error(f"❌ Error sending command completion to BoardRoom (all paths failed): {str(e)}")
                self.logger.debug(traceback.format_exc())
            
            success = True
            notification_journey_id = journey_id
        else:
            # Otherwise, send to Jarvis orchestrator
            self.logger.info("Using Jarvis communication path for command notification")
            success, notification_journey_id = await self.send_message_to_jarvis(
                message=message,
                message_type="command_completion",
                context=context
            )
        
        return success, notification_journey_id
        
    async def report_error(self, error_type, details, command=None, journey_id=None):
        """
        Report an error to Jarvis with tracking.
        
        Returns:
            Tuple[bool, str]: Tuple containing:
                - success: Boolean indicating if error report was sent
                - journey_id: ID of the error report journey
        """
        # Use existing journey_id or create new one
        if not journey_id:
            request_id = generate_request_id()
            journey_id = await self.track_request(
                request_id=request_id,
                description=f"Error report: {error_type}"
            )
            
        # Update metrics
        self.metrics["errors_reported"] += 1
        
        # Track the error report
        await self.track_step(
            journey_id=journey_id,
            step_name="error_report",
            description=f"Reporting error to Jarvis",
            step_type="error_tracking",
            input_data={
                "error_type": error_type,
                "details": details,
                "command": command
            }
        )
        
        # Prepare error message
        message = f"Terminal error encountered: {error_type}"
        
        # Create detailed context
        context = {
            "error_type": error_type,
            "details": details,
            "command": command,
            "system_name": self.system_name,
            "agent_id": self.agent_id,
            "message_to_jarvis": message,
            "error_time": time.time(),
            "journey_id": journey_id
        }
        
        # Send error report to Jarvis
        success, notification_journey_id = await self.send_message_to_jarvis(
            message=message,
            message_type="error_report",
            context=context
        )
        
        return success, notification_journey_id
        
    async def get_performance_metrics(self) -> Dict[str, Any]:
        """Get comprehensive performance metrics."""
        return {
            "system_metrics": self.metrics,
            "active_journeys": len(self.active_journeys),
            "total_requests": len(self.request_journey_map),
            "success_rate": (
                self.metrics["workflows_executed"] /
                (self.metrics["workflows_executed"] + self.metrics["errors_reported"])
                if (self.metrics["workflows_executed"] + self.metrics["errors_reported"]) > 0
                else 0
            ),
            "routing_efficiency": (
                self.metrics["tasks_routed"] /
                (self.metrics["tasks_routed"] + self.metrics["errors_reported"])
                if (self.metrics["tasks_routed"] + self.metrics["errors_reported"]) > 0
                else 0
            )
        }

    async def receive_message_from_jarvis(self, message, context=None, message_type="instruction"):
        """
        Process a message received from the Jarvis orchestrator.
        
        Args:
            message: The message content from Jarvis
            context: Additional context for the message
            message_type: Type of message (instruction, query, update, etc.)
            
        Returns:
            Dict: Response to the message
        """
        # Generate journey ID for tracking
        journey_id = generate_request_id()
        
        # Initialize context if needed
        if context is None:
            context = {}
            
        # Add message source information
        context["message_from_jarvis"] = message
        context["source"] = "jarvis_orchestrator"
        
        # Ensure message is properly truncated for the description
        message_preview = message[:100] + "..." if len(message) > 100 else message
        
        # Track the incoming message
        await self.track_step(
            journey_id=journey_id,
            step_name="incoming_message",
            description=f"Received message from Jarvis: {message_preview}",
            step_type="inbound_communication",
            input_data={
                "message": message,
                "message_type": message_type,
                "context": context
            }
        )
        
        try:
            # Process the message based on type
            response = None
            
            if message_type == "instruction":
                # Process instruction from Jarvis
                response = {
                    "status": "acknowledged",
                    "message": f"Instruction received: {message[:50]}...",
                    "journey_id": journey_id,
                    "timestamp": time.time()
                }
                
            elif message_type == "query":
                # Process query from Jarvis
                response = {
                    "status": "processing",
                    "message": f"Query received: {message[:50]}...",
                    "journey_id": journey_id,
                    "timestamp": time.time()
                }
                
            elif message_type == "status_request":
                # Jarvis is requesting system status
                if self.terminal_handler:
                    response = {
                        "status": "active",
                        "system_name": self.system_name,
                        "metrics": self.metrics,
                        "to_jarvis_messages": self.to_jarvis_counter,
                        "from_jarvis_messages": self.from_jarvis_counter,
                        "journey_id": journey_id,
                        "timestamp": time.time()
                    }
                else:
                    response = {
                        "status": "partial",
                        "message": "TerminalHandler not fully initialized",
                        "system_name": self.system_name,
                        "journey_id": journey_id,
                        "timestamp": time.time()
                    }
            else:
                # Default handling for other message types
                response = {
                    "status": "received",
                    "message": f"Message of type {message_type} received",
                    "system_name": self.system_name,
                    "journey_id": journey_id,
                    "timestamp": time.time()
                }
            
            # Track the response
            await self.track_step(
                journey_id=journey_id,
                step_name="response_sent",
                description=f"Sending response to Jarvis",
                step_type="outbound_communication",
                output_data=response
            )
            
            return response
            
        except Exception as e:
            error_msg = f"Error processing message from Jarvis: {str(e)}"
            self.logger.error(error_msg)
            
            # Track the error
            await self.track_step(
                journey_id=journey_id,
                step_name="processing_error",
                description=error_msg,
                step_type="error",
                output_data={
                    "error": error_msg,
                    "traceback": traceback.format_exc()
                }
            )
            
            return {
                "status": "error",
                "message": error_msg,
                "journey_id": journey_id,
                "timestamp": time.time()
            }
            
    def _analyze_claude_code_request(self, prompt: str, original_message: str) -> dict:
        """
        Analyzes a Claude Code request to determine its type and purpose.
        
        This method examines the prompt and original message to categorize the request
        as code execution, analysis, file operation, or other types of requests.
        
        Args:
            prompt: The formatted prompt for Claude Code
            original_message: The original user message that triggered this request
            
        Returns:
            dict: Analysis results containing:
                - request_type: Type of request (code_execution, analysis, file_operation, etc.)
                - primary_focus: Main focus of the request (python, javascript, project_structure, etc.)
                - complexity: Estimated complexity (simple, moderate, complex)
                - requires_filesystem: Whether the request likely needs filesystem access
                - estimated_duration: Estimated time to complete (in seconds)
        """
        request_type = "unknown"
        primary_focus = "unknown"
        complexity = "moderate"
        requires_filesystem = False
        estimated_duration = 30  # default 30 seconds
        
        # Analyze for search and replace request
        if any(pattern in prompt.lower() or pattern in original_message.lower() 
               for pattern in ["search and replace", "find and replace", "replace all", "replace text", "replace occurr"]):
            return {
                "operation": "search_and_replace",
                "parameters": self._extract_search_replace_params(prompt, original_message)
            }
        
        # Analyze for code execution request
        code_execution_patterns = ["run", "execute", "start", "launch"]
        if any(pattern in original_message.lower() for pattern in code_execution_patterns):
            request_type = "code_execution"
            estimated_duration = 60  # Likely longer duration
        
        # Analyze for analysis request
        analysis_patterns = ["analyze", "examine", "review", "understand", "explain"]
        if any(pattern in original_message.lower() for pattern in analysis_patterns):
            request_type = "analysis"
            estimated_duration = 45
        
        # Analyze for file operation
        file_operations = ["read", "write", "create", "modify", "open", "save", "edit"]
        if any(op in original_message.lower() for op in file_operations):
            request_type = "file_operation"
            requires_filesystem = True
        
        # Determine primary focus based on file extensions or keywords
        language_patterns = {
            "python": ["python", ".py", "import", "def ", "class "],
            "javascript": ["javascript", "js", ".js", "function(", "const ", "let "],
            "project_structure": ["structure", "directory", "architecture", "codebase", "project layout"],
            "data": ["data", "csv", "json", "dataframe", "pandas", "numpy"]
        }
        
        for focus, patterns in language_patterns.items():
            if any(pattern in original_message.lower() or pattern in prompt.lower() for pattern in patterns):
                primary_focus = focus
                break
        
        # Assess complexity
        complexity_indicators = {
            "simple": ["simple", "quick", "basic", "elementary", "straightforward"],
            "moderate": ["moderate", "standard", "normal", "regular"],
            "complex": ["complex", "complicated", "advanced", "sophisticated", "multi-step"]
        }
        
        for level, indicators in complexity_indicators.items():
            if any(indicator in original_message.lower() for indicator in indicators):
                complexity = level
                # Adjust estimated duration based on complexity
                if level == "simple":
                    estimated_duration = max(15, estimated_duration - 15)
                elif level == "complex":
                    estimated_duration = estimated_duration + 30
                break
        
        # Check for filesystem requirements
        filesystem_indicators = ["file", "directory", "folder", "path", "open", "save", "read", "write"]
        if any(indicator in original_message.lower() or indicator in prompt.lower() for indicator in filesystem_indicators):
            requires_filesystem = True
        
        return {
            "request_type": request_type,
            "primary_focus": primary_focus,
            "complexity": complexity,
            "requires_filesystem": requires_filesystem,
            "estimated_duration": estimated_duration
        }
        
    def _extract_search_replace_params(self, prompt: str, original_message: str) -> dict:
        """
        Extract search and replace parameters from a prompt or message.
        
        Args:
            prompt: The formatted prompt for Claude Code
            original_message: The original user message that triggered this request
            
        Returns:
            dict: Parameters for search_and_replace operation
        """
        import re
        
        # Combine both for analysis
        combined_text = f"{original_message.lower()} {prompt.lower()}"
        
        # Look for search pattern
        search_pattern = None
        search_matches = re.findall(r'(?:search for|find|locate|replace)[:\s]+[\'"`]([^\'"`]+)[\'"`]', combined_text)
        if search_matches:
            search_pattern = search_matches[0]
        
        # Look for replacement
        replacement = None
        replace_matches = re.findall(r'(?:replace with|substitute with|change to)[:\s]+[\'"`]([^\'"`]+)[\'"`]', combined_text)
        if replace_matches:
            replacement = replace_matches[0]
        
        # Look for file pattern
        file_pattern = "*"  # Default to all files
        file_pattern_matches = re.findall(r'(?:in files|file pattern|matching|matching files)[:\s]+[\'"`]([^\'"`]+)[\'"`]', combined_text)
        if file_pattern_matches:
            file_pattern = file_pattern_matches[0]
        
        # Determine if regex should be used
        use_regex = "regex" in combined_text or "regular expression" in combined_text
        
        # Determine if case sensitive
        case_sensitive = "case sensitive" in combined_text
        if "case insensitive" in combined_text:
            case_sensitive = False
        
        # Extract directory if specified
        directory = "~/Jarvis"  # Default
        dir_matches = re.findall(r'(?:in directory|in folder|in path)[:\s]+[\'"`]([^\'"`]+)[\'"`]', combined_text)
        if dir_matches:
            directory = dir_matches[0]
        
        return {
            "search_pattern": search_pattern,
            "replacement": replacement,
            "file_pattern": file_pattern,
            "directory": directory,
            "use_regex": use_regex,
            "case_sensitive": case_sensitive,
            "backup": True  # Always make backups for safety
        }
    
    async def receive_message_from_boardroom(self, message, context=None, message_type="query"):
        """
        Process a message received from the BoardRoom via the orchestrator bridge.
        
        This method enables bidirectional communication with the BoardRoom for terminal operations,
        allowing it to perform various terminal tasks including:
        - File system operations (ls, cat, etc.)
        - Running Claude Code commands
        - Executing terminal commands
        - Examining files
        - Editing files
        - Running scripts
        - Managing terminal sessions
        
        The orchestrator agent serves as a bridge between the BoardRoom and the terminal,
        executing requests and returning results in a structured format.
        
        Args:
            message: The message content from BoardRoom
            context: Additional context for the message
            message_type: Type of message (query, instruction, etc.)
            
        Returns:
            Dict: Response to the message
        """
        # DIRECT DEBUG: Log message from BoardRoom
        print("\n⚡⚡⚡ RECEIVED MESSAGE FROM BOARDROOM ⚡⚡⚡")
        print(f"⚡ MESSAGE: {message[:150]}...")
        print(f"⚡ MESSAGE_TYPE: {message_type}")
        print(f"⚡ CONTEXT KEYS: {list(context.keys()) if context else None}")
        
        # Create a file with the full message details for debugging
        with open("~/Jarvis/boardroom_messages.log", "a") as f:
            f.write(f"\n\n=== RECEIVED BOARDROOM MESSAGE AT {time.strftime('%Y-%m-%d %H:%M:%S')} ===\n")
            f.write(f"MESSAGE: {message}\n")
            f.write(f"MESSAGE_TYPE: {message_type}\n")
            f.write(f"CONTEXT: {context}\n")
            
        # Generate journey ID for tracking
        journey_id = f"boardroom_to_terminal_{int(time.time())}_{hash(str(message))}"
        
        # Add extremely visible logging to show the communication chain
        print("\n" + "=" * 80)
        print("🚨🚨🚨 BOARDROOM → TERMINAL ORCHESTRATOR COMMUNICATION 🚨🚨🚨")
        print(f"🚨🚨🚨 MESSAGE: {message[:100]}... 🚨🚨🚨")
        print(f"🚨🚨🚨 MESSAGE TYPE: {message_type} 🚨🚨🚨")
        print(f"🚨🚨🚨 JOURNEY ID: {journey_id} 🚨🚨🚨")
        print("=" * 80 + "\n")
        
        # Log to both console and logger for maximum visibility
        self.logger.warning(f"[BOARDROOM→TERMINAL] Received message: {message[:200]}...")
        self.logger.warning(f"[BOARDROOM→TERMINAL] Message type: {message_type}")
        self.logger.warning(f"[BOARDROOM→TERMINAL] Journey ID: {journey_id}")
        
        # Initialize context if needed
        if context is None:
            context = {}
            
        # Add message source information
        context["message_from_boardroom"] = message
        context["source"] = "boardroom_orchestrator_bridge"
        
        # Ensure message is properly truncated for the description
        message_preview = message[:100] + "..." if len(message) > 100 else message
        
        # Track the incoming message
        await self.track_step(
            journey_id=journey_id,
            step_name="incoming_boardroom_message",
            description=f"Received message from BoardRoom: {message_preview}",
            step_type="inbound_communication",
            input_data={
                "message": message,
                "message_type": message_type,
                "context": context
            }
        )
        
        try:
            # Process the message based on type and context
            response = None
            
            # Check for query_type in context for specialized handling
            query_type = context.get("query_type")
            
            if query_type == "capabilities":
                # Return capabilities of the terminal system
                response = {
                    "success": True,
                    "capabilities": [
                        "command_execution",
                        "terminal_session_management",
                        "terminal_session_creation",
                        "terminal_session_command_execution",
                        "terminal_session_output_retrieval",
                        "terminal_session_listing",
                        "terminal_session_closure",
                        "file_operations",
                        "file_editing",
                        "code_analysis",
                        "system_automation",
                        "virtual_environment_management",
                        "claude_code_execution"
                    ],
                    "handler_name": "TerminalHandler",
                    "system_name": self.system_name,
                    "description": "Terminal handler for executing commands and interacting with the filesystem"
                }
                
            elif query_type == "status":
                # Return current status of the terminal handler agent
                response = {
                    "success": True,
                    "status": "active" if self.active else "inactive",
                    "metrics": self.metrics,
                    "active_journeys": len(getattr(self, 'active_journeys', [])),
                    "messages_sent": self.metrics.get("messages_sent", 0),
                    "messages_received": self.metrics.get("messages_received", 0),
                    "handler_name": "TerminalHandler",
                    "system_name": self.system_name
                }
                
            elif query_type == "module_info":
                # Return information about the terminal module
                module_name = context.get("module_name", "terminal")
                
                # Provide detailed information about the terminal module
                response = {
                    "success": True,
                    "module_name": module_name,
                    "description": "Terminal handler for executing commands and interacting with the filesystem",
                    "capabilities": [
                        "Execute shell commands in isolated environments",
                        "Manage terminal sessions and state",
                        "Create persistent terminal sessions with directory context",
                        "Send commands to existing terminal sessions",
                        "Retrieve output from terminal session commands",
                        "List active terminal sessions and their status",
                        "Edit files safely with automatic backups",
                        "Search file contents and paths",
                        "Execute code in virtual environments",
                        "Perform file operations safely",
                        "Provide system automation through scripts",
                        "Track command execution and results",
                        "Execute Claude Code commands and investigations"
                    ],
                    "interactions": [
                        "Bidirectional communication with Jarvis Orchestrator",
                        "Integration with BoardRoom for planning context",
                        "Journey tracking for all operations",
                        "Performance monitoring and metrics collection"
                    ]
                }
                    
            elif "claude code" in message.lower() or "terminal" in message.lower():
                # Determine what type of terminal operation is being requested
                import re
                
                # Check for Claude Code requests - more flexible to handle any kind of Claude Code request
                if "claude code" in message.lower():
                    # First try to find a specific command pattern
                    prompt_match = re.search(r"claude code to (?:investigate|research|explore|analyze|examine|find|check|look at|search|help with):?\s+(.+)", message.lower())
                    
                    # If that fails, look for more general patterns
                    if not prompt_match:
                        prompt_match = re.search(r"(?:let me |have |can you |please |)use\s+claude code\s+(?:to |for |)\s*:?\s*(.+)", message.lower())
                    
                    # If that fails, try an even more general pattern
                    if not prompt_match:
                        prompt_match = re.search(r"claude code.*?[:\n]?\s*(.+)", message.lower())
                        
                    if prompt_match:
                        prompt = prompt_match.group(1).strip()
                        
                        # Log the Claude Code request
                        self.logger.info(f"BoardRoom requested Claude Code investigation: {prompt}")
                        
                        # Track the Claude Code execution
                        await self.track_step(
                            journey_id=journey_id,
                            step_name="claude_code_execution",
                            description=f"Executing Claude Code with prompt: {prompt}",
                            step_type="claude_code",
                            input_data={"prompt": prompt}
                        )
                        
                        # Check for JSON input indicators
                        json_input_detected = "json" in message.lower() and ("structure" in message.lower() or 
                                                                             "format" in message.lower() or 
                                                                             "fields" in message.lower()) 
                        
                        # Try to extract JSON structure if indicated
                        json_input = {}
                        if json_input_detected:
                            try:
                                # Look for JSON-like structures in the message
                                import re
                                import json
                                # Find potential JSON blocks in the message surrounded by ```json and ```
                                json_blocks = re.findall(r'```(?:json)?\s*({[^`]+})\s*```', message, re.DOTALL)
                                if json_blocks:
                                    # Extract and parse the first JSON structure found
                                    for block in json_blocks:
                                        try:
                                            json_input = json.loads(block)
                                            self.logger.info(f"Extracted JSON structure for Claude Code: {json_input}")
                                            break
                                        except:
                                            continue
                            except Exception as json_extract_e:
                                self.logger.error(f"Error extracting JSON input: {str(json_extract_e)}")
                        
                        # Determine if monitoring output was requested
                        monitor_output = "monitor" in message.lower() or "watch" in message.lower() or "observe" in message.lower()
                        
                        # Execute using the specialized method with expanded options
                        if True:  # Using _get_terminal_handler() will always provide a valid handler
                            # Prepare parameters for Claude Code execution
                            claude_params = {
                                "prompt": prompt,
                                "directory": "~/Jarvis",
                                "verbose": True,
                                "use_json": bool(json_input),
                                "json_input": json_input,
                                "monitor_output": monitor_output,
                                "timeout": 120,  # Longer timeout for complex operations
                                # Add dynamic request support - analyze the request type and adapt accordingly
                                "dynamic_request": self._analyze_claude_code_request(prompt, message)
                            }
                            
                            # Execute Claude Code with enhanced options - make sure to show the terminal window
                            claude_params["show_terminal"] = True  # Force showing the terminal window
                            claude_params["capture_output"] = True  # Ensure we capture any output
                            
                            # Log the execution clearly so we can see it in debugging
                            self.logger.warning(f"[TERMINAL_DEBUG] Executing Claude Code with params: {claude_params}")
                            
                            # Skip normal execution and go straight to the direct terminal approach
                            # This ensures we always get a visible terminal window
                            self.logger.warning("[TERMINAL_DIRECT] Using direct terminal creation approach for guaranteed visibility")
                            
                            # Use direct subprocess approach for maximum reliability
                            
                            # Create a simpler AppleScript that's more likely to work
                            # This avoids nested calls and complex escaping
                            # Create a safer approach to avoid quote and backslash issues
                            # Build the command step by step to avoid f-string backslash problems
                            safe_prompt = prompt.replace('"', '\\"').replace("'", "\\'")
                            
                            # Log the prompt for debugging
                            logging.warning(f"[CLAUDE_CODE] Using simplified AppleScript for Claude Code execution")
                            logging.warning(f"[CLAUDE_CODE] Processing prompt (first 50 chars): {prompt[:50]}...")
                            
                            # Create AppleScript commands
                            cd_command = "~/Jarvis"
                            # Create a simple, reliable claude command with minimal chance of escaping issues
                            # Pass prompt via a direct file to avoid all quoting and escaping complexities
                            
                            # Mark this as a Claude Code window type
                            window_type = self.WINDOW_TYPE_CLAUDE_CODE
                            
                            # Generate a session ID for this Claude Code execution
                            session_id = f"boardroom_claude_{int(time.time())}"
                            
                            # Create a temporary file for the prompt
                            temp_prompt_path = f"/tmp/claude_prompt_{session_id}.txt"
                            with open(temp_prompt_path, "w") as f:
                                f.write(prompt)
                            
                            # Use cat to feed the prompt to claude - this avoids all quoting/escaping issues
                            claude_command = f'cat {temp_prompt_path} | claude --verbose'
                            
                            # Create an ultra-simplified AppleScript with minimal escaping for Claude Code
                            # Use the most basic syntax possible to avoid any AppleScript syntax errors
                            terminal_script = 'tell application "Terminal" to do script "cd ' + cd_command + ' && clear && echo \'=== CLAUDE CODE EXECUTION ===\' && ' + claude_command + '"'
                            
                            # Create a temporary file with the AppleScript for more reliable execution
                            try:
                                # First, create a temporary file with the AppleScript
                                temp_script_path = "/tmp/claude_code_script.scpt"
                                with open(temp_script_path, "w") as f:
                                    f.write(terminal_script)
                                
                                # Make it executable just in case
                                os.chmod(temp_script_path, 0o755)
                                
                                # Execute using the file-based approach for better reliability
                                applescript_result = subprocess.run(["osascript", temp_script_path], 
                                                                   capture_output=True, text=True)
                                
                                self.logger.warning(f"[TERMINAL_DIRECT] AppleScript result code: {applescript_result.returncode}")
                                
                                if applescript_result.returncode != 0:
                                    self.logger.error(f"[TERMINAL_DIRECT] AppleScript error: {applescript_result.stderr}")
                                
                                # Log more detailed information about the execution
                                print(f"🚨 CLAUDE APPLESCRIPT STDOUT: {applescript_result.stdout[:100]}...")
                                print(f"🚨 CLAUDE APPLESCRIPT STDERR: {applescript_result.stderr[:100]}...")
                                
                                command_output = f"Claude Code launched in terminal window with prompt: {prompt}"
                                claude_result = HandlerResult(success=True, data=command_output)
                                self.logger.warning("[TERMINAL_DIRECT] Successfully created terminal window with Claude Code")
                            except Exception as subprocess_error:
                                self.logger.error(f"[TERMINAL_DIRECT] Terminal creation failed: {str(subprocess_error)}")
                                import traceback
                                traceback.print_exc()  # Print the full stack trace
                                command_output = f"Failed to execute Claude Code: Terminal creation failed: {str(subprocess_error)}"
                                claude_result = HandlerResult(success=False, error=command_output)
                            
                            # Make sure we log success prominently
                            self.logger.warning(f"[TERMINAL_SUCCESS] Successfully executed Claude Code: {prompt}")
                            self.logger.warning(f"[TERMINAL_OUTPUT] Output preview: {command_output[:200]}...")
                            
                            # Add input method details to tracking
                            input_method = "JSON structure" if json_input else "text prompt"
                            monitoring = "with real-time monitoring" if monitor_output else "without monitoring"
                            
                            # Track the successful execution with enhanced details
                            await self.track_step(
                                journey_id=journey_id,
                                step_name="claude_code_execution_completed",
                                description=f"Claude Code execution completed for: {prompt} using {input_method} {monitoring}",
                                step_type="claude_code",
                                output_data={
                                    "output": command_output,
                                    "used_json": bool(json_input),
                                    "monitored_output": monitor_output,
                                    "executed_at": time.time()
                                }
                            )
                            
                            # Create enhanced response with all execution details
                            response = {
                                "success": True,
                                "status": "claude_code_execution_completed",
                                "window_type": window_type,
                                "session_id": session_id,
                                "message": f"Successfully executed Claude Code using {input_method} {monitoring}",
                                "prompt": prompt,
                                "output": command_output,
                                "execution_details": {
                                    "input_method": input_method,
                                    "monitoring_enabled": monitor_output,
                                    "json_input": json_input if json_input else None,
                                    "execution_time": time.time(),
                                    "command_executed": claude_params
                                },
                                "system_name": self.system_name,
                                "journey_id": journey_id,
                                "timestamp": time.time()
                            }
                        else:
                            # Fall back to direct command execution
                            try:
                                cmd = f"cd ~/Jarvis && claude --verbose \"{prompt}\""
                                process = subprocess.run(cmd, shell=True, capture_output=True, text=True)
                                command_output = process.stdout
                                
                                self.logger.info(f"Successfully executed Claude Code via subprocess: {prompt}")
                                
                                response = {
                                    "success": True,
                                    "status": "claude_code_execution_completed",
                                    "message": f"Successfully executed Claude Code via subprocess: {prompt}",
                                    "prompt": prompt,
                                    "output": command_output,
                                    "system_name": self.system_name,
                                    "journey_id": journey_id,
                                    "timestamp": time.time()
                                }
                            except Exception as exec_e:
                                self.logger.error(f"Error executing Claude Code via subprocess: {str(exec_e)}")
                                response = {
                                    "success": False,
                                    "status": "claude_code_execution_failed",
                                    "message": f"Failed to execute Claude Code: {str(exec_e)}",
                                    "prompt": prompt,
                                    "error": str(exec_e),
                                    "system_name": self.system_name,
                                    "journey_id": journey_id,
                                    "timestamp": time.time()
                                }
                    else:
                        response = {
                            "success": False,
                            "status": "claude_code_prompt_extraction_failed",
                            "message": "Could not extract Claude Code prompt from message",
                            "system_name": self.system_name,
                            "journey_id": journey_id,
                            "timestamp": time.time()
                        }
                
                # Check for general terminal command requests
                elif "terminal" in message.lower() and "run" in message.lower():
                    command_match = re.search(r"(?:terminal|run|execute).*?(?:command|cmd)?:?\s+`?([^`\n]+)`?", message.lower())
                    if command_match:
                        command = command_match.group(1).strip()
                        
                        # Log the terminal command request
                        self.logger.info(f"BoardRoom requested terminal command execution: {command}")
                        
                        # Track the terminal command execution
                        await self.track_step(
                            journey_id=journey_id,
                            step_name="terminal_command_execution",
                            description=f"Executing terminal command: {command}",
                            step_type="terminal_command",
                            input_data={"command": command}
                        )
                        
                        # Execute the command
                        if True:  # Using _get_terminal_handler() will always provide a valid handler
                            print(f"\n🚩🚩🚩 ABOUT TO EXECUTE TERMINAL COMMAND 🚩🚩🚩")
                            print(f"🚩 COMMAND: {command}")
                            
                            # Try direct subprocess first for comparison
                            try:
                                print(f"🚩 DIRECT SUBPROCESS TEST BEGIN")
                                direct_result = subprocess.run(command, shell=True, capture_output=True, text=True)
                                print(f"🚩 DIRECT RESULT: exitcode={direct_result.returncode}")
                                print(f"🚩 DIRECT STDOUT: {direct_result.stdout[:150]}...")
                                if direct_result.stderr:
                                    print(f"🚩 DIRECT STDERR: {direct_result.stderr[:150]}...")
                            except Exception as e:
                                print(f"🚩 DIRECT SUBPROCESS ERROR: {str(e)}")
                            
                            # Now try handler execution
                            terminal_handler = self._get_terminal_handler()
                            print(f"🚩 TERMINAL HANDLER: {terminal_handler}")
                            print(f"🚩 EXECUTING VIA HANDLER...")
                            
                            # Open a direct visible terminal right now - bypass handler initially
                            try:
                                print(f"🚩 OPENING DIRECT VISIBLE TERMINAL FOR IMMEDIATE VISIBILITY")
                                escaped_cmd = command.replace('"', '\\"').replace("'", "\\'")
                                direct_script = '''
                                tell application "Terminal"
                                    activate
                                    do script "cd ~/Jarvis && clear && echo '\033[1;31m=== BOARDROOM TERMINAL COMMAND ===\033[0m' && echo '' && echo '\033[1;33mExecuting: " + escaped_cmd + "\033[0m' && echo '' && " + escaped_cmd
                                    set custom title of front window to "🔴 BoardRoom Command"
                                    set background color of front window to {0, 0, 10000}
                                    set normal text color of front window to {65535, 65535, 65535}
                                    set bounds of front window to {100, 100, 900, 600}
                                end tell
                                '''
                                os.system("osascript -e '" + direct_script + "'")
                                print("🚩 DIRECT TERMINAL WINDOW OPENED")
                            except Exception as term_error:
                                print("🚩 DIRECT TERMINAL ERROR: " + str(term_error))
                            
                            # Also use normal handler execution
                            # IMPORTANT: Add visibility parameters for all BoardRoom commands
                            command_params = {
                                "command": command,
                                "show_terminal": True,         # Force terminal window to show
                                "force_visible_terminal": True,  # Force terminal to be visible
                                "direct_execution": True       # Use direct execution for reliability
                            }
                            
                            print(f"🚩 ADDING VISIBILITY PARAMETERS: show_terminal=True, force_visible_terminal=True")
                            self.logger.warning(f"[BOARDROOM] Adding terminal visibility parameters for command: {command}")
                            
                            command_result = terminal_handler.execute("execute_command", command_params)
                            command_output = getattr(command_result, 'result', str(command_result))
                            print(f"🚩 HANDLER RESULT: success={getattr(command_result, 'success', False)}")
                            print(f"🚩 HANDLER OUTPUT: {command_output[:150]}..." if command_output else "No output")
                            
                            self.logger.info(f"Successfully executed terminal command: {command}")
                            
                            # Track the successful execution
                            await self.track_step(
                                journey_id=journey_id,
                                step_name="terminal_command_completed",
                                description=f"Terminal command execution completed: {command}",
                                step_type="terminal_command",
                                output_data={"output": command_output}
                            )
                            
                            response = {
                                "success": True,
                                "status": "terminal_command_completed",
                                "message": f"Successfully executed terminal command: {command}",
                                "command": command,
                                "output": command_output,
                                "system_name": self.system_name,
                                "journey_id": journey_id,
                                "timestamp": time.time()
                            }
                        else:
                            # Fall back to direct command execution
                            try:
                                process = subprocess.run(command, shell=True, capture_output=True, text=True)
                                command_output = process.stdout
                                
                                self.logger.info(f"Successfully executed terminal command via subprocess: {command}")
                                
                                response = {
                                    "success": True,
                                    "status": "terminal_command_completed",
                                    "message": f"Successfully executed terminal command via subprocess: {command}",
                                    "command": command,
                                    "output": command_output,
                                    "system_name": self.system_name,
                                    "journey_id": journey_id,
                                    "timestamp": time.time()
                                }
                            except Exception as exec_e:
                                self.logger.error(f"Error executing terminal command via subprocess: {str(exec_e)}")
                                response = {
                                    "success": False,
                                    "status": "terminal_command_failed",
                                    "message": f"Failed to execute terminal command: {str(exec_e)}",
                                    "command": command,
                                    "error": str(exec_e),
                                    "system_name": self.system_name,
                                    "journey_id": journey_id,
                                    "timestamp": time.time()
                                }
                    else:
                        response = {
                            "success": False,
                            "status": "terminal_command_extraction_failed",
                            "message": "Could not extract terminal command from message",
                            "system_name": self.system_name,
                            "journey_id": journey_id,
                            "timestamp": time.time()
                        }
                
                # Check for file examination requests
                elif "examine file" in message.lower() or "view file" in message.lower() or "check file" in message.lower():
                    file_match = re.search(r"(?:examine|view|check|inspect|read).*?file:?\s+([^\n]+)", message.lower())
                    if file_match:
                        file_path = file_match.group(1).strip()
                        
                        # Log the file examination request
                        self.logger.info(f"BoardRoom requested file examination: {file_path}")
                        
                        # Determine if we should use Claude Code for file examination
                        use_claude_code = "with claude" in message.lower() or "using claude" in message.lower()
                        
                        # Check for existing Claude Code sessions first if we're using Claude
                        if use_claude_code and self.terminal_handler and hasattr(self.terminal_handler, 'active_claude_sessions') and TerminalHandler.active_claude_sessions:
                            # Find any active session we could reuse
                            existing_session = None
                            session_id = None
                            
                            for sid, session_info in TerminalHandler.active_claude_sessions.items():
                                if session_info.get("active"):
                                    # Check if process is still running
                                    try:
                                        pid = session_info.get("pid")
                                        if pid:
                                            check_cmd = f"ps -p {pid} > /dev/null 2>&1 && echo 'running' || echo 'terminated'"
                                            check_result = subprocess.run(check_cmd, shell=True, capture_output=True, text=True)
                                            process_status = check_result.stdout.strip()
                                            
                                            if process_status == "running":
                                                existing_session = session_info
                                                session_id = sid
                                                self.logger.info(f"Found existing Claude Code session for file examination: {session_id}")
                                                break
                                            else:
                                                # Clean up the stale session
                                                TerminalHandler.active_claude_sessions.pop(sid, None)
                                    except Exception as e:
                                        self.logger.warning(f"Error checking Claude Code session status: {str(e)}")
                                        continue
                            
                            if existing_session:
                                prompt = f"Please help me examine this file: {file_path}"
                                
                                # Execute Claude Code with the existing session
                                claude_params = {
                                    "prompt": prompt,
                                    "directory": "~/Jarvis",
                                    "verbose": True,
                                    "use_json": False,
                                    "monitor_output": True,
                                    "reuse_session": True,
                                    "session_id": session_id
                                }
                                
                                claude_result = self._get_terminal_handler().execute("execute_claude_code", claude_params)
                                command_output = getattr(claude_result, 'result', str(claude_result))
                                
                                # Track the successful execution
                                await self.track_step(
                                    journey_id=journey_id,
                                    step_name="claude_file_examination_completed",
                                    description=f"Claude Code file examination completed: {file_path}",
                                    step_type="file_examination",
                                    output_data={"file_path": file_path, "used_claude": True, "reused_session": True}
                                )
                                
                                response = {
                                    "success": True,
                                    "status": "claude_file_examination_completed",
                                    "message": f"Successfully examined file using existing Claude session: {file_path}",
                                    "file_path": file_path,
                                    "content": command_output,
                                    "system_name": self.system_name,
                                    "journey_id": journey_id,
                                    "timestamp": time.time(),
                                    "used_claude": True,
                                    "reused_session": True,
                                    "session_id": session_id
                                }
                                return response
                            
                        # If we reach here, either we're not using Claude or couldn't find a reusable session
                        # Proceed with standard file examination or create a new Claude session
                        if use_claude_code and self.terminal_handler:
                            prompt = f"Please help me examine this file: {file_path}"
                            
                            # Execute using Claude Code with a new session
                            claude_params = {
                                "prompt": prompt,
                                "directory": "~/Jarvis",
                                "verbose": True,
                                "use_json": False,
                                "monitor_output": True
                            }
                            
                            claude_result = self._get_terminal_handler().execute("execute_claude_code", claude_params)
                            command_output = getattr(claude_result, 'result', str(claude_result))
                            
                            # Track the successful execution
                            await self.track_step(
                                journey_id=journey_id,
                                step_name="claude_file_examination_completed",
                                description=f"Claude Code file examination completed: {file_path}",
                                step_type="file_examination",
                                output_data={"file_path": file_path, "used_claude": True, "reused_session": False}
                            )
                            
                            response = {
                                "success": True,
                                "status": "claude_file_examination_completed",
                                "message": f"Successfully examined file using Claude: {file_path}",
                                "file_path": file_path,
                                "content": command_output,
                                "system_name": self.system_name,
                                "journey_id": journey_id,
                                "timestamp": time.time(),
                                "used_claude": True,
                                "reused_session": False
                            }
                            return response
                        
                        # Standard file examination without Claude
                        try:
                            with open(file_path, 'r') as f:
                                file_content = f.read()
                            
                            # Track the successful file read
                            await self.track_step(
                                journey_id=journey_id,
                                step_name="file_examination_completed",
                                description=f"File examination completed: {file_path}",
                                step_type="file_examination",
                                output_data={"file_path": file_path}
                            )
                            
                            response = {
                                "success": True,
                                "status": "file_examination_completed",
                                "message": f"Successfully examined file: {file_path}",
                                "file_path": file_path,
                                "content": file_content,
                                "system_name": self.system_name,
                                "journey_id": journey_id,
                                "timestamp": time.time()
                            }
                        except Exception as e:
                            self.logger.error(f"Error examining file: {str(e)}")
                            response = {
                                "success": False,
                                "status": "file_examination_failed",
                                "message": f"Failed to examine file: {str(e)}",
                                "file_path": file_path,
                                "error": str(e),
                                "system_name": self.system_name,
                                "journey_id": journey_id,
                                "timestamp": time.time()
                            }
                    else:
                        response = {
                            "success": False,
                            "status": "file_path_extraction_failed",
                            "message": "Could not extract file path from message",
                            "system_name": self.system_name,
                            "journey_id": journey_id,
                            "timestamp": time.time()
                        }
                
                # Default terminal operation response
                else:
                    response = {
                        "success": False,
                        "status": "terminal_operation_unknown",
                        "message": "Could not determine what terminal operation to perform",
                        "system_name": self.system_name,
                        "journey_id": journey_id,
                        "timestamp": time.time()
                    }
            else:
                # Default handling for other message types
                response = {
                    "success": True,
                    "status": "received",
                    "message": f"Message of type {message_type} received from BoardRoom",
                    "system_name": self.system_name,
                    "journey_id": journey_id,
                    "timestamp": time.time()
                }
            
            # Track the response
            await self.track_step(
                journey_id=journey_id,
                step_name="boardroom_response_sent",
                description=f"Sending response to BoardRoom",
                step_type="outbound_communication",
                output_data=response
            )
            
            return response
            
        except Exception as e:
            error_msg = f"Error processing message from BoardRoom: {str(e)}"
            self.logger.error(error_msg)
            
            # Track the error
            await self.track_step(
                journey_id=journey_id,
                step_name="boardroom_processing_error",
                description=error_msg,
                step_type="error",
                output_data={
                    "error": error_msg,
                    "traceback": traceback.format_exc()
                }
            )
            
            return {
                "success": False,
                "status": "error",
                "message": error_msg,
                "journey_id": journey_id,
                "timestamp": time.time()
            }
    
    async def report_system_status(self, status="active", metrics=None, current_tasks=None):
        """
        Report the current status of the TerminalHandler system to the Jarvis orchestrator.
        
        Args:
            status: Current system status (active, idle, error, etc.)
            metrics: Performance metrics and statistics
            current_tasks: Information about current tasks being processed
            
        Returns:
            Tuple[bool, str]: Tuple containing:
                - success: Boolean indicating if status report was sent
                - journey_id: ID of the status report journey
        """
        if metrics is None:
            metrics = {}
            
        if current_tasks is None:
            current_tasks = []
            
        # Prepare status message
        message = f"TerminalHandler System Status: {status}"
        
        # Create detailed context with metrics
        context = {
            "status": status,
            "system_name": self.system_name,
            "agent_id": self.agent_id,
            "metrics": metrics,
            "current_tasks": current_tasks,
            "message_to_jarvis": message,
            "timestamp": time.time()
        }
        
        # Send status report to Jarvis
        success, journey_id = await self.send_message_to_jarvis(
            message=message,
            message_type="status_update",
            context=context
        )
        
        return success, journey_id
    
    async def notify_task_completion(self, task_id, result, performance_metrics=None):
        """
        Notify the Jarvis orchestrator that a task has been completed.
        
        Args:
            task_id: ID of the completed task
            result: Result of the task
            performance_metrics: Performance metrics for the task
            
        Returns:
            Tuple[bool, str]: Tuple containing:
                - success: Boolean indicating if notification was sent
                - journey_id: ID of the task completion journey
        """
        if performance_metrics is None:
            performance_metrics = {}
            
        # Prepare completion message
        message = f"Task {task_id} has been completed"
        
        # Summarize result for the message if it's lengthy
        result_summary = str(result)
        if len(result_summary) > 100:
            result_summary = result_summary[:97] + "..."
            
        # Create detailed context with result and metrics
        context = {
            "task_id": task_id,
            "result": result,
            "result_summary": result_summary,
            "system_name": self.system_name,
            "agent_id": self.agent_id,
            "performance_metrics": performance_metrics,
            "message_to_jarvis": message,
            "completion_time": time.time()
        }
        
        # Send completion notification to Jarvis
        success, journey_id = await self.send_message_to_jarvis(
            message=message,
            message_type="task_completion",
            context=context
        )
        
        return success, journey_id
    
    async def execute_workflow(self, workflow_id: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a workflow with the given parameters."""
        try:
            # Initialize workflow tracking
            journey_id = f"workflow_{workflow_id}_{int(time.time())}"
            
            # Execute the workflow
            result = await execute_validated_analysis_workflow({
                "workflow_id": workflow_id,
                "parameters": parameters,
                "system_id": self.system_id,
                "journey_id": journey_id
            })
            
            if result.get("success", False):
                return {
                    "success": True,
                    "result": result.get("result"),
                    "journey_id": journey_id
                }
            else:
                error_msg = result.get("error", "Unknown workflow error")
                await self.report_error(
                    error_type="workflow_execution_error",
                    details=error_msg,
                    command={"workflow_id": workflow_id}
                )
                return {
                    "success": False,
                    "error": error_msg,
                    "journey_id": journey_id
                }
                
        except Exception as e:
            error_msg = f"Workflow execution failed: {str(e)}"
            self.logger.error(error_msg)
            return {
                "success": False,
                "error": error_msg
            }

class TerminalHandler(BaseHandler):
    def __init__(self):
        """Initialize the terminal handler."""
        super().__init__()
        self.active = True
        self.orchestrator = TerminalHandlerOrchestratorAgent(system_name="TerminalHandler")
        self.boardroom = None  # BoardRoom archived (Phase 3)
        self.tracking_interface = self.boardroom
        self.request_journey_map = {}
        self.active_journeys = set()
        self.journey_steps = {}
        self.metrics = {
            "commands_executed": 0,
            "files_created": 0,
            "files_edited": 0,
            "errors": 0
        }
        self.active_sessions = {}
        self.command_history = []
        self.error_log = []
        self.logger = logging.getLogger(__name__)
        self.system_name = "TerminalHandler"
        self.system_id = f"{self.system_name}_{int(time.time())}"
        
        # Initialize missing attributes
        self.session_counter = 0
        self.last_output = {}
        self.handler_name = "TerminalHandler"

    async def handle(self, task_description: Dict[str, Any]) -> HandlerResult:
        """
        Main entry point for handling terminal-related operations.
        
        Args:
            task_description: Dictionary containing the task details
                - action: String specifying the action to perform
                - parameters: Dictionary of parameters for the action
                
        Returns:
            HandlerResult object with the operation results
        """
        action = task_description.get("action", "")
        parameters = task_description.get("parameters", {})
        
        return self.execute(action, parameters)
        
    def edit_file(self, parameters: Dict[str, Any]) -> HandlerResult:
        """
        Edit a file with the given parameters.
        
        Args:
            parameters: Dictionary containing:
                - file_path: Path to the file to edit
                - content: New content for the file (optional)
                - line_edits: Dictionary of line numbers to new content (optional)
                
        Returns:
            HandlerResult indicating success or failure
        """
        file_path = parameters.get("file_path")
        content = parameters.get("content")
        line_edits = parameters.get("line_edits", {})
        
        if not file_path:
            return HandlerResult(success=False, error="No file path provided")
            
        try:
            # Check if we're replacing the entire content or just certain lines
            if content is not None:
                # Replace the entire file content
                with open(file_path, "w") as f:
                    f.write(content)
                return HandlerResult(success=True, data=f"File {file_path} updated with new content")
            elif line_edits:
                # Read the file
                with open(file_path, "r") as f:
                    lines = f.readlines()
                
                # Apply the edits
                for line_num, new_content in line_edits.items():
                    try:
                        line_idx = int(line_num) - 1  # Convert to 0-based index
                        if 0 <= line_idx < len(lines):
                            lines[line_idx] = new_content + "\n"
                    except ValueError:
                        continue
                
                # Write the file back
                with open(file_path, "w") as f:
                    f.writelines(lines)
                    
                return HandlerResult(success=True, data=f"File {file_path} updated with line edits")
            else:
                return HandlerResult(success=False, error="No content or line edits provided")
        except Exception as e:
            return HandlerResult(success=False, error=str(e))
    
    # Class variables to track active sessions
    active_claude_sessions = {}  # For Claude Code sessions only
    active_terminal_sessions = {}  # For regular terminal sessions
    boardroom_claude_session = None
    boardroom_terminal_session = None  # Separate session for BoardRoom terminal commands
    
    # Window type tracking to ensure proper separation
    WINDOW_TYPE_CLAUDE_CODE = "claude_code"
    WINDOW_TYPE_TERMINAL = "terminal_command"
    WINDOW_TYPE_DIRECT_TERMINAL = "direct_terminal_command"  # Separate type for direct terminal commands
    
    def cleanup_terminal_sessions(self):
        """Close any terminal sessions that have been left open for too long."""
        if not hasattr(self.__class__, 'active_claude_sessions'):
            return
            
        current_time = time.time()
        
        # Clean up stale BoardRoom sessions first
        if hasattr(self.__class__, 'boardroom_claude_session'):
            session_id = self.__class__.boardroom_claude_session
            if session_id in self.__class__.active_claude_sessions:
                session_info = self.__class__.active_claude_sessions[session_id]
                last_used = session_info.get("last_used", 0)
                
                # If not used in the last 10 minutes, close it
                if current_time - last_used > 600:  # 10 minutes
                    logging.warning(f"🧹 Cleaning up inactive BoardRoom Claude session: {session_id}")
                    try:
                        window_id = session_info.get("window_id")
                        if window_id:
                            close_script = '''
                            tell application "Terminal"
                                try
                                    close (first window whose id is ''' + str(window_id) + ''')
                                end try
                            end tell
                            '''
                            subprocess.run(["osascript", "-e", close_script], 
                                       capture_output=True, text=True)
                    except Exception as e:
                        logging.error(f"Error closing window: {str(e)}")
                    finally:
                        # Mark as inactive
                        session_info["active"] = False
                        session_info["closed_at"] = current_time
    
    def execute_claude_code(self, parameters: Dict[str, Any]) -> HandlerResult:
        """
        Execute a Claude Code command with advanced interaction capabilities.
        
        This method provides both simple command execution and structured JSON interaction
        with Claude Code's input fields. It can also perform real-time monitoring of the
        output for long-running commands.
        
        The method checks for existing Claude Code sessions before starting a new one,
        allowing for efficient reuse of Claude Code instances that are already running.
        
        Args:
            parameters: Dictionary containing:
                - prompt: The prompt to send to Claude Code
                - directory: Optional directory to execute in (default: ~/Jarvis)
                - verbose: Whether to use verbose mode (default: True)
                - use_json: Whether to use JSON structured input (default: False)
                - json_input: JSON structure for Claude Code input (when use_json is True)
                - monitor_output: Whether to monitor output in real-time (default: False)
                - timeout: Maximum execution time in seconds (default: 60)
                - reuse_session: Whether to reuse existing Claude Code sessions (default: True)
                - session_id: Specific session ID to reuse (if available)
                - dynamic_request: Optional instructions for dynamic execution
                - show_terminal: Optional whether to ensure terminal window is visible (default: True)
                - capture_output: Optional whether to capture output from Claude Code (default: True)
                - force_visible_terminal: Optional whether to force terminal visibility (default: True)
                - use_claude_window: Optional whether to use an existing Claude window (default: False)
                - boardroom_planning_session: Optional whether this is part of a BoardRoom planning (default: False)
                
        Returns:
            HandlerResult with the Claude Code output if successful
        """
        prompt = parameters.get("prompt")
        directory = parameters.get("directory", "~/Jarvis")
        verbose = parameters.get("verbose", True)
        use_json = parameters.get("use_json", False)
        json_input = parameters.get("json_input", {})
        monitor_output = parameters.get("monitor_output", False)
        timeout = parameters.get("timeout", 60)
        reuse_session = parameters.get("reuse_session", True)
        session_id = parameters.get("session_id")
        dynamic_request = parameters.get("dynamic_request")
        show_terminal = parameters.get("show_terminal", True)  # Default to showing terminal
        capture_output = parameters.get("capture_output", True)  # Default to capturing output
        force_visible_terminal = parameters.get("force_visible_terminal", True)  # Default to forcing visibility
        use_claude_window = parameters.get("use_claude_window", False)  # Default to not using existing Claude window
        boardroom_planning_session = parameters.get("boardroom_planning_session", False)  # Default to not being from BoardRoom
        
        # Check for different execution contexts to properly separate concerns
        execution_context = parameters.get("execution_context", "")
        source = parameters.get("source", "")
        
        # IMPORTANT: Completely separate execution paths for Claude Code vs Trevor Core
        # This ensures that Claude Code executions never mix with Trevor Core operations
        
        # Handle Claude Code execution from BoardRoom specifically
        if "claude_code" in execution_context:
            # Claude Code specific settings - completely isolated from Trevor Core
            show_terminal = True
            force_visible_terminal = True
            reuse_session = True
            
            # Explicitly ignore any boardroom_planning_session flag for Claude Code
            # This prevents Trevor Core logic from affecting Claude Code execution
            boardroom_planning_session = False
            
            # Log Claude Code specific execution
            logging.warning(f"🧠 CLAUDE CODE EXECUTION: Detected native Claude Code context from {source}")
            
            # Create a dedicated Claude Code session with unique prefix
            # Never reuse Trevor Core sessions for Claude Code execution
            if not session_id:
                session_id = f"claude_code_native_{int(time.time())}"
                logging.warning(f"🧠 CREATING NEW CLAUDE CODE SESSION: {session_id}")
            
            logging.warning(f"🧠 USING CLAUDE CODE SESSION: {session_id}")
        
        # Trevor Core execution path - separate from Claude Code
        elif boardroom_planning_session or "message_from_boardroom" in str(parameters) or "boardroom" in str(source):
            # Always set these for Trevor Core BoardRoom operations
            boardroom_planning_session = True
            parameters["boardroom_planning_session"] = True
            reuse_session = True
            show_terminal = True
            force_visible_terminal = True
            
            # Create a dedicated Trevor Core session system with trevor_ prefix
            # to clearly distinguish from Claude Code sessions
            if not hasattr(self.__class__, 'boardroom_trevor_session'):
                # Create a new persistent session ID if none exists - note: trevor_ prefix
                self.__class__.boardroom_trevor_session = f"trevor_core_session_{int(time.time())}"
                logging.warning(f"🚨 CREATING NEW PERSISTENT TREVOR CORE SESSION: {self.__class__.boardroom_trevor_session}")
            
            # Use the consistent Trevor Core session ID unless a specific one is provided
            if not session_id:
                session_id = self.__class__.boardroom_trevor_session
            
            logging.warning(f"🚨 USING TREVOR CORE SESSION: {session_id}")
        
        # Log the execution for debugging
        logging.warning(f"[CLAUDE_CODE_EXECUTION] Running with prompt: '{prompt[:100]}...' in directory: {directory}")
        logging.warning(f"[CLAUDE_CODE_EXECUTION] Terminal visibility: {show_terminal}, Output capture: {capture_output}")
        
        # Handle dynamic requests - this allows for flexible execution patterns
        if dynamic_request:
            try:
                # Process different types of dynamic requests
                if isinstance(dynamic_request, dict):
                    # Extract operation and parameters
                    operation = dynamic_request.get("operation")
                    op_params = dynamic_request.get("parameters", {})
                    
                    # Process based on operation type
                    if operation == "search_and_replace":
                        # Delegate to the search_and_replace method
                        return self.search_and_replace(op_params)
                    elif operation == "file_analysis":
                        # Modify prompt to focus on file analysis
                        file_path = op_params.get("file_path")
                        if file_path:
                            prompt = f"Please analyze this file: {file_path}\n\n" + (prompt or "")
                    elif operation == "code_refactoring":
                        # Set up a code refactoring task
                        code_file = op_params.get("file_path")
                        refactor_type = op_params.get("refactor_type", "general")
                        if code_file:
                            try:
                                with open(code_file, 'r') as f:
                                    code_content = f.read()
                                prompt = f"Please refactor this code ({refactor_type} refactoring):\n\n```\n{code_content}\n```\n\n"
                            except Exception as e:
                                return HandlerResult(success=False, error=f"Failed to read code file: {str(e)}")
                elif isinstance(dynamic_request, str):
                    # String-based dynamic request for simpler cases
                    if dynamic_request.startswith("search_files:"):
                        pattern = dynamic_request.split(":", 1)[1].strip()
                        return self.search_files({"pattern": pattern, "directory": directory})
                    elif dynamic_request.startswith("analyze_code:"):
                        code_path = dynamic_request.split(":", 1)[1].strip()
                        prompt = f"Please analyze this code file: {code_path}"
            except Exception as e:
                self.logger.error(f"Error processing dynamic request: {str(e)}")
                # Continue with standard execution if dynamic request fails
        
        if not prompt and not (use_json and json_input):
            return HandlerResult(success=False, error="No prompt or JSON input provided for Claude Code")
            
        try:
            # Generate a unique session ID if not provided
            if not session_id:
                session_id = f"claude_code_{int(time.time())}_{hash(prompt if prompt else str(json_input))}"
            
            # Check for existing sessions if reuse is requested
            # We'll use completely separate tracking for Claude Code vs Trevor Core sessions
            existing_session = None
            
            # Create separate class attributes to track different types of sessions
            # This ensures Claude Code and Trevor Core sessions are fully isolated
            if not hasattr(self.__class__, 'active_claude_code_sessions'):
                self.__class__.active_claude_code_sessions = {}
                
            if not hasattr(self.__class__, 'active_trevor_core_sessions'):
                self.__class__.active_trevor_core_sessions = {}
            
            # Select the appropriate session store based on execution context
            if "claude_code" in execution_context:
                active_sessions = self.__class__.active_claude_code_sessions
                session_type = "Claude Code"
                logging.warning(f"[CLAUDE_CODE_SESSIONS] Using Claude Code session store")
            elif boardroom_planning_session:
                active_sessions = self.__class__.active_trevor_core_sessions
                session_type = "Trevor Core"
                logging.warning(f"[TREVOR_CORE_SESSIONS] Using Trevor Core session store")
            else:
                # Default to generic sessions for anything else
                if not hasattr(self.__class__, 'active_generic_sessions'):
                    self.__class__.active_generic_sessions = {}
                active_sessions = self.__class__.active_generic_sessions
                session_type = "Generic"
                logging.warning(f"[GENERIC_SESSIONS] Using Generic session store")
            
            logging.warning(f"[{session_type.upper()}_SESSIONS] Checking for existing sessions. Reuse enabled: {reuse_session}")
            logging.warning(f"[{session_type.upper()}_SESSIONS] Current active sessions: {list(active_sessions.keys())}")
            
            if reuse_session and active_sessions:
                # Check if we have a specific session ID request in the appropriate store
                if session_id in active_sessions:
                    existing_session = active_sessions[session_id]
                    logging.warning(f"[{session_type.upper()}_SESSIONS] Found exact session match: {session_id}")
                    logging.info(f"Reusing existing {session_type} session: {session_id}")
                # Otherwise look for any active session in the right directory
                else:
                    for sid, session_info in active_sessions.items():
                        if session_info.get("directory") == directory and session_info.get("active"):
                            existing_session = session_info
                            session_id = sid
                            logging.warning(f"[CLAUDE_CODE_SESSIONS] Found directory match: {directory}, Session: {session_id}")
                            logging.info(f"Found existing Claude Code session in directory {directory}: {session_id}")
                            break
            
            # Check if existing session is actually still running
            if existing_session:
                pid = existing_session.get("pid")
                if pid:
                    # Check if process is still running
                    try:
                        check_cmd = f"ps -p {pid} > /dev/null 2>&1 && echo 'running' || echo 'terminated'"
                        check_result = subprocess.run(check_cmd, shell=True, capture_output=True, text=True)
                        process_status = check_result.stdout.strip()
                        
                        if process_status != "running":
                            logging.info(f"Found Claude Code session {session_id} but it's no longer running. Starting new session.")
                            existing_session = None
                            # Clean up the stale session
                            self.__class__.active_claude_sessions.pop(session_id, None)
                    except Exception as e:
                        logging.warning(f"Error checking Claude Code session status: {str(e)}")
                        existing_session = None
            
            # Log the execution
            logging.info(f"Executing Claude Code: {prompt if prompt else 'with JSON input'} (Session ID: {session_id})")
            
            # Build the command based on input type
            verbose_flag = "--verbose" if verbose else ""
            
            if existing_session:
                # Use AppleScript to find the existing terminal window and send the command to it
                import json as json_lib
                
                # Construct the command to send
                if use_json and json_input:
                    json_str = json_lib.dumps(json_input).replace('"', '\\"')
                    input_command = f"echo '{json_str}' | claude {verbose_flag}"
                else:
                    input_command = f"claude {verbose_flag} \"{prompt}\""
                
                # Escape the command for AppleScript
                escaped_command = input_command.replace('"', '\\"')
                
                # AppleScript to find terminal window and send command
                applescript = '''
                tell application "Terminal"
                    set targetTab to missing value
                    repeat with w in windows
                        repeat with t in tabs of w
                            if name of t contains "claude" then
                                set targetTab to t
                                exit repeat
                            end if
                        end repeat
                        if targetTab is not missing value then
                            exit repeat
                        end if
                    end repeat
                    
                    if targetTab is missing value then
                        # No existing window found, create a new one
                        # Make sure we first CD to the Jarvis directory
                        do script "cd {directory} && echo 'Reusing Claude Code session {session_id}...'"
                        set targetTab to selected tab of front window
                    else
                        # If we found an existing window, make sure we're in the right directory
                        tell targetTab
                            do script "cd {directory}" in targetTab
                        end tell
                    end if
                    
                    # Send the command to the terminal
                    tell targetTab
                        set current settings to settings set "Basic"
                        do script "{escaped_command}" in targetTab
                    end tell
                    
                    # Bring the window to front
                    activate
                end tell
                '''
                
                # Run the AppleScript
                applescript_cmd = f"osascript -e '{applescript}'"
                result = subprocess.run(applescript_cmd, shell=True, capture_output=True, text=True)
                
                # Update session info
                self.__class__.active_claude_sessions[session_id] = {
                    "directory": directory,
                    "last_command": input_command,
                    "active": True,
                    "last_used": time.time(),
                    "applescript_result": result.stdout
                }
                
                # If this is a BoardRoom session, remember the session ID
                if boardroom_planning_session:
                    self.__class__.boardroom_claude_session = session_id
                    logging.warning(f"[CLAUDE_CODE_EXECUTION] Updated BoardRoom Claude session ID: {session_id}")
                
                # Update window type metadata
                self.__class__.active_claude_sessions[session_id]["window_type"] = "claude_code"
                self.__class__.active_claude_sessions[session_id]["session_origin"] = "boardroom" if boardroom_planning_session else "direct"
                
                # Return a success result indicating the command was sent to the existing session
                return HandlerResult(
                    success=True, 
                    result="Command sent to existing Claude Code session. Check the terminal window for output.",
                    details={
                        "session_id": session_id,
                        "reused_session": True,
                        "command_sent": input_command
                    }
                )
            
            # If no existing session or reuse is not requested, create a new one
            if use_json and json_input:
                # Convert JSON input to a string that can be passed to Claude Code
                import json as json_lib
                json_str = json_lib.dumps(json_input).replace('"', '\\"')
                cmd = f"cd {directory} && echo '{json_str}' | claude {verbose_flag}"
                logging.info(f"Using JSON input structure: {json_str[:100]}...")
            else:
                # Standard prompt-based execution
                cmd = f"cd {directory} && claude {verbose_flag} \"{prompt}\""
            
            # Check if we should create a persistent terminal session - use the show_terminal parameter
            create_terminal_session = show_terminal
            
            # Add explicit logging to verify which path is being taken
            logging.warning(f"[CLAUDE_CODE_EXECUTION_PATH] Show terminal requested: {show_terminal}")
            logging.warning(f"[CLAUDE_CODE_EXECUTION_PATH] Creating visible terminal session: {create_terminal_session}")
            logging.warning(f"[CLAUDE_CODE_EXECUTION_PATH] Command to run: {cmd}")
            
            # Force terminal visibility for Claude Code execution - this is necessary as Claude Code requires a terminal
            if not create_terminal_session:
                logging.warning("[CLAUDE_CODE_EXECUTION_PATH] Forcing terminal visibility as Claude Code requires it")
                create_terminal_session = True
            
            # If create_terminal_session is true, use AppleScript to create a visible window
            if create_terminal_session:
                # Create a unique terminal window for Claude Code execution
                # Process the command to escape quotes correctly for AppleScript
                escaped_cmd = cmd.replace('"', r'\"')
                
                # First check if we should use Claude window based on parameter
                if use_claude_window or boardroom_planning_session:
                    # Try to find an existing Claude window using AppleScript first
                    # This is more reliable than our internal tracking
                    logging.warning(f"[CLAUDE_CODE_EXECUTION] Attempting to find existing Claude window via AppleScript")
                    
                    # AppleScript to search for terminal windows with Claude in title
                    find_claude_script = '''
                    tell application "Terminal"
                        set claudeWindowID to missing value
                        set claudeTabID to missing value
                        
                        # First look for windows with "CLAUDE CODE" in title (most specific)
                        repeat with w in windows
                            repeat with t in tabs of w
                                if name of t contains "CLAUDE CODE" then
                                    set claudeWindowID to id of w
                                    set claudeTabID to id of t
                                    exit repeat
                                end if
                            end repeat
                            if claudeWindowID is not missing value then
                                exit repeat
                            end if
                        end repeat
                        
                        # If not found, look for windows with just "CLAUDE" in title (broader match)
                        if claudeWindowID is missing value then
                            repeat with w in windows
                                repeat with t in tabs of w
                                    if name of t contains "CLAUDE" then
                                        set claudeWindowID to id of w
                                        set claudeTabID to id of t
                                        exit repeat
                                    end if
                                end repeat
                                if claudeWindowID is not missing value then
                                    exit repeat
                                end if
                            end repeat
                        end if
                        
                        # If still not found, check for windows with any Claude reference in content
                        if claudeWindowID is missing value then
                            repeat with w in windows
                                repeat with t in tabs of w
                                    # Check the window contents for Claude references
                                    try
                                        set winContents to contents of t
                                        # Look for Claude code references in window contents
                                        if winContents contains "claude" or winContents contains "Claude" or winContents contains "CLAUDE" then
                                            set claudeWindowID to id of w
                                            set claudeTabID to id of t
                                            exit repeat
                                        end if
                                    end try
                                end repeat
                                if claudeWindowID is not missing value then
                                    exit repeat
                                end if
                            end repeat
                        end if
                        
                        # Return window ID if found, otherwise "not_found"
                        if claudeWindowID is not missing value then
                            return claudeWindowID & ":" & claudeTabID
                        else
                            return "not_found"
                        end if
                    end tell
                    '''
                    
                    # Run the find script
                    find_result = subprocess.run(["osascript", "-e", find_claude_script], 
                                               capture_output=True, text=True)
                    find_output = find_result.stdout.strip()
                    
                    # Check if we found a Claude window
                    if find_output and find_output != "not_found":
                        logging.warning(f"[CLAUDE_CODE_EXECUTION] Found existing Claude window via AppleScript: {find_output}")
                        
                        # Parse the returned IDs
                        try:
                            window_id, tab_id = find_output.split(":")
                            
                            # Generate a session ID for this existing window
                            found_session_id = f"claude_detected_{int(time.time())}"
                            
                            # Record this window in our active sessions
                            self.__class__.active_claude_sessions[found_session_id] = {
                                "directory": directory,
                                "window_id": window_id,
                                "tab_id": tab_id,
                                "detected_at": time.time(),
                                "last_used": time.time(),
                                "active": True,
                                "window_type": "claude_code",
                                "session_origin": "detected",
                                "detection_method": "applescript"
                            }
                            
                            # Use this session
                            session_id = found_session_id
                            
                            # If this is a BoardRoom session, register it
                            if boardroom_planning_session:
                                self.__class__.boardroom_claude_session = found_session_id
                                logging.warning(f"[CLAUDE_CODE_EXECUTION] Registered detected window as BoardRoom Claude session: {found_session_id}")
                                
                            # Create script to activate the window and send our command
                            activate_script = '''
                            tell application "Terminal"
                                # Activate the window
                                set frontmost of window id ''' + window_id + ''' to true
                                set visible of window id ''' + window_id + ''' to true
                                activate
                                
                                # First ensure we CD to the right directory
                                do script "cd ''' + directory + '''" in tab id ''' + tab_id + ''' of window id ''' + window_id + '''
                                
                                # Now send our command
                                do script "''' + escaped_cmd + '''" in tab id ''' + tab_id + ''' of window id ''' + window_id + '''
                                
                                # Ensure window is frontmost
                                set frontmost of window id ''' + window_id + ''' to true
                            end tell
                            '''
                            
                            # Run the activation script
                            activate_result = subprocess.run(["osascript", "-e", activate_script], 
                                                          capture_output=True, text=True)
                            
                            # Return success using the detected window
                            return HandlerResult(
                                success=True,
                                result=f"Command sent to existing Claude Code window. Session ID: {session_id}",
                                details={
                                    "session_id": session_id,
                                    "directory": directory,
                                    "command": cmd,
                                    "window_id": window_id,
                                    "tab_id": tab_id,
                                    "detected": True,
                                    "reused": True
                                }
                            )
                        except Exception as e:
                            logging.error(f"Error activating detected Claude window: {str(e)}")
                            # Continue with normal flow if activation fails
                    
                    # Fall back to our internal tracking if AppleScript detection failed
                    if hasattr(self.__class__, 'active_claude_sessions') and self.__class__.active_claude_sessions:
                        # If we're in a BoardRoom planning session, try to use that specific session
                        if boardroom_planning_session and hasattr(self.__class__, 'boardroom_claude_session'):
                            boardroom_session_id = self.__class__.boardroom_claude_session
                            if boardroom_session_id in self.__class__.active_claude_sessions:
                                logging.warning(f"[CLAUDE_CODE_EXECUTION] Found BoardRoom session: {boardroom_session_id}")
                                existing_session = self.__class__.active_claude_sessions[boardroom_session_id]
                                if existing_session.get("active", False):
                                    session_id = boardroom_session_id
                        
                        # Look for any active Claude window
                        for existing_id, existing_info in self.__class__.active_claude_sessions.items():
                            if existing_info.get("active", False) and existing_info.get("window_type") == "claude_code":
                                logging.warning(f"[CLAUDE_CODE_EXECUTION] Found active Claude session: {existing_id}")
                                session_id = existing_id
                                break
                
                applescript = '''
                tell application "Terminal"
                    # Set terminal to foreground and create a new window (not a tab)
                    activate
                    
                    # Create a new window instead of a tab to ensure separation
                    do script ""
                    
                    # Create a new session with clear indication this is Claude Code
                    # First ensure we CD to the right directory before doing anything else
                    do script "cd ''' + directory + ''' && echo '🤖 CLAUDE CODE EXECUTION - Starting Claude Code session ''' + session_id + '''...'" in front window
                    
                    # Get the new window and configure it
                    set targetTab to selected tab of front window
                    set window_id to id of front window
                    
                    tell targetTab
                        set current settings to settings set "Basic"
                        set background color to {0, 0, 25000} # Dark blue background to distinguish Claude Code
                        set cursor color to {65535, 0, 0} # Red cursor
                        set normal text color to {65535, 65535, 65535} # White text
                        # Make the Claude Code marker very prominent for easy detection
                        set custom title to "🤖 CLAUDE CODE ACTIVE TERMINAL - CLAUDE - ''' + session_id + '''"
                        set font size to 14
                    end tell
                    
                    # Make sure terminal window is visible
                    set frontmost of front window to true
                    set visible of front window to true
                    
                    # Execute the command - we already CD'd to the directory, so we don't need to include it again
                    # The escaped_cmd already has the CD command in it
                    do script "''' + escaped_cmd + '''" in targetTab
                    
                    # Ensure window is frontmost and active
                    activate
                    
                    # Resize window to be more visible
                    set bounds of front window to {100, 100, 1000, 700}
                    
                    # Return the window ID so we can track it
                    return window_id
                end tell
                '''
                
                # Run the AppleScript to create the terminal window
                applescript_cmd = f"osascript -e '{applescript}'"
                window_result = subprocess.run(applescript_cmd, shell=True, capture_output=True, text=True)
                
                # Store session information in the class variable
                # Update session tracking with additional context metadata
                session_metadata = {
                    "directory": directory,
                    "command": cmd,
                    "created_at": time.time(),
                    "last_used": time.time(),
                    "active": True,
                    "window_id": window_result.stdout.strip() if window_result.stdout else None,
                    "applescript_result": window_result.stdout,
                    "window_type": "claude_code",
                    "execution_context": execution_context or "default"
                }
                
                # Add source information to differentiate Claude Code from Trevor Core
                # Use the same session_type that was determined earlier
                if "claude_code" in execution_context:
                    # Claude Code specific path
                    session_metadata["session_origin"] = source or "claude_code_native"
                    session_metadata["session_type"] = "claude_code"
                    logging.warning(f"🧠 Created Claude Code specific session: {session_id}")
                    
                    # Store in Claude Code specific session store
                    self.__class__.active_claude_code_sessions[session_id] = session_metadata
                    logging.warning(f"🧠 STORING SESSION IN CLAUDE CODE STORE: {session_id}")
                    
                elif boardroom_planning_session:
                    # Trevor Core integration path
                    self.__class__.boardroom_trevor_session = session_id
                    session_metadata["session_origin"] = "trevor_core"
                    session_metadata["session_type"] = "trevor_core"
                    logging.warning(f"[TREVOR_CORE_EXECUTION] Set Trevor Core session ID: {session_id}")
                    
                    # Store in Trevor Core specific session store
                    self.__class__.active_trevor_core_sessions[session_id] = session_metadata
                    logging.warning(f"🧠 STORING SESSION IN TREVOR CORE STORE: {session_id}")
                    
                else:
                    # Generic session path
                    session_metadata["session_origin"] = "direct"
                    session_metadata["session_type"] = "standard"
                    
                    # Store in generic session store
                    if not hasattr(self.__class__, 'active_generic_sessions'):
                        self.__class__.active_generic_sessions = {}
                    self.__class__.active_generic_sessions[session_id] = session_metadata
                    logging.warning(f"🧠 STORING SESSION IN GENERIC STORE: {session_id}")
                
                # Try to capture the initial output if requested
                if capture_output:
                    time.sleep(2)  # Give Claude a moment to start responding
                    
                    # Capture output with AppleScript
                    capture_script = '''
                    tell application "Terminal"
                        contents of front window
                    end tell
                    '''
                    
                    # Run the script to get initial output
                    capture_result = subprocess.run(["osascript", "-e", capture_script], 
                                                   capture_output=True, text=True)
                    initial_output = capture_result.stdout

                    # Log the captured output
                    logging.warning(f"[CLAUDE_CODE_CAPTURE] Initial output: {initial_output[:200]}...")
                    
                    # Return success result with captured output
                    return HandlerResult(
                        success=True,
                        result=f"Claude Code session started in terminal window. Session ID: {session_id}",
                        details={
                            "session_id": session_id,
                            "directory": directory,
                            "command": cmd,
                            "window_created": True,
                            "initial_output": initial_output,
                            "file_contents": f"File contents being processed by Claude Code in terminal window. Check terminal for results."
                        }
                    )
                else:
                    # Return success result for terminal window creation without capturing output
                    return HandlerResult(
                        success=True,
                        result=f"Claude Code session started in terminal window. Session ID: {session_id}",
                        details={
                            "session_id": session_id,
                            "directory": directory,
                            "command": cmd,
                            "window_created": True
                        }
                    )
            
            # Non-window execution with monitoring
            elif monitor_output:
                # Create a unique output file for this execution
                import tempfile
                output_file = tempfile.mktemp(suffix=".claude_output")
                
                # Modify command to write output to file and poll it
                polling_cmd = f"{cmd} > {output_file} 2>&1 & echo $!"
                
                # Execute the command to start Claude Code in background
                proc_result = subprocess.run(polling_cmd, shell=True, capture_output=True, text=True)
                
                if proc_result.returncode == 0:
                    # Get the process ID
                    pid = proc_result.stdout.strip()
                    
                    # Store session information in the class variable
                    TerminalHandler.active_claude_sessions[session_id] = {
                        "directory": directory,
                        "command": cmd,
                        "pid": pid,
                        "output_file": output_file,
                        "created_at": time.time(),
                        "last_used": time.time(),
                        "active": True
                    }
                    
                    # Initialize output tracking
                    output = ""
                    start_time = time.time()
                    output_complete = False
                    
                    # Poll the output file for up to timeout seconds
                    while (time.time() - start_time) < timeout and not output_complete:
                        try:
                            # Check if process is still running
                            check_cmd = f"ps -p {pid} > /dev/null 2>&1 && echo 'running' || echo 'finished'"
                            check_result = subprocess.run(check_cmd, shell=True, capture_output=True, text=True)
                            process_status = check_result.stdout.strip()
                            
                            # Read current output
                            if os.path.exists(output_file):
                                with open(output_file, "r") as f:
                                    current_output = f.read()
                                    
                                # Log new output if it's different
                                if len(current_output) > len(output):
                                    new_output = current_output[len(output):]
                                    output = current_output
                                    logging.info(f"New Claude Code output: {new_output[:100]}...")
                            
                            # Check if process has finished
                            if process_status == "finished":
                                output_complete = True
                                break
                                
                            # Sleep briefly to avoid CPU spinning
                            time.sleep(0.5)
                            
                        except Exception as poll_e:
                            logging.error(f"Error polling Claude Code output: {str(poll_e)}")
                            break
                    
                    # If we timed out, try to kill the process
                    if not output_complete:
                        try:
                            kill_cmd = f"kill {pid} > /dev/null 2>&1"
                            subprocess.run(kill_cmd, shell=True)
                            logging.warning(f"Claude Code execution timed out after {timeout} seconds")
                        except Exception:
                            pass
                    
                    # Read final output
                    final_output = ""
                    if os.path.exists(output_file):
                        with open(output_file, "r") as f:
                            final_output = f.read()
                            
                        # Clean up the temp file
                        try:
                            if os.path.exists(output_file):
                                os.remove(output_file)
                            else:
                                logging.debug(f"Output file already removed: {output_file}")
                        except Exception:
                            pass
                    
                    # Return the result
                    if output_complete:
                        return HandlerResult(success=True, data=final_output)
                    else:
                        return HandlerResult(
                            success=False,
                            error=f"Claude Code execution timed out after {timeout} seconds",
                            details={"partial_output": final_output}
                        )
                else:
                    return HandlerResult(
                        success=False,
                        error=f"Failed to start Claude Code with monitoring: {proc_result.stderr}"
                    )
            else:
                # Standard execution without monitoring
                result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
                
                # Check if successful
                if result.returncode == 0:
                    return HandlerResult(success=True, data=result.stdout)
                else:
                    return HandlerResult(
                        success=False,
                        error=f"Claude Code execution failed with code {result.returncode}",
                        details={"stderr": result.stderr, "stdout": result.stdout}
                    )
        except subprocess.TimeoutExpired:
            return HandlerResult(
                success=False,
                error=f"Claude Code execution timed out after {timeout} seconds"
            )
        except Exception as e:
            return HandlerResult(success=False, error=f"Error executing Claude Code: {str(e)}")
    
    def execute(self, action: str, parameters: Dict[str, Any]) -> HandlerResult:
        """Execute a terminal command or action."""
        try:
            # Check if this is a command coming from BoardRoom
            is_from_boardroom = (
                parameters.get("boardroom_planning_session", False) or 
                "message_from_boardroom" in str(parameters) or 
                "boardroom" in str(parameters.get("source", "")) or
                action == "execute_claude_code"  # Always treat Claude code as potentially BoardRoom-related
            )
            
            # For BoardRoom commands, ensure persistent terminal session parameters
            if is_from_boardroom:
                # Ensure persistent session parameters are set
                parameters["boardroom_planning_session"] = True
                parameters["reuse_session"] = True
                parameters["show_terminal"] = True
                parameters["force_visible_terminal"] = True
                
                # IMPORTANT: Never suppress outputs for BoardRoom sessions - force display
                parameters["force_display_output"] = True  # New flag to force display of outputs
                parameters["capture_output"] = True  # Ensure output is captured
                parameters["send_to_boardroom"] = True  # New flag to force sending results to boardroom
                
                # Set or reuse a consistent session ID for all BoardRoom commands
                if not hasattr(self.__class__, 'boardroom_terminal_session'):
                    # Create a new persistent session ID if none exists
                    self.__class__.boardroom_terminal_session = f"boardroom_terminal_{int(time.time())}"
                    logging.warning(f"🚨 CREATING NEW PERSISTENT BOARDROOM SESSION: {self.__class__.boardroom_terminal_session}")
                
                # Always use the consistent session ID for all BoardRoom commands
                if action in ["execute_command", "send_command", "create_terminal_session"]:
                    # If a session is already provided in parameters, respect it
                    if not parameters.get("session_id"):
                        parameters["session_id"] = self.__class__.boardroom_terminal_session
                    parameters["reuse_session"] = True
                
                logging.warning(f"🚨 USING BOARDROOM PERSISTENT SESSION: {self.__class__.boardroom_terminal_session} for action {action}")
            else:
                # For direct terminal commands (not from BoardRoom), force new windows unless explicitly overridden
                if action in ["execute_command", "send_command"]:
                    # Only force new windows if not explicitly set and no specific session is requested
                    if "force_new_window" not in parameters and not parameters.get("session_id"):
                        parameters["force_new_window"] = True
                        logging.warning(f"🚨 FORCING NEW WINDOW FOR DIRECT TERMINAL COMMAND: {action}")
            
            # Map action to method
            action_map = {
                "execute_command": self.execute_command,
                "open_terminal": self.create_terminal_session,
                "run_script": self.run_script,
                "search_files": self.search_files,
                "search_content": self.search_content,
                "create_terminal_session": self.create_terminal_session,
                "send_command": self.send_command,
                "get_output": self.get_output,
                "list_sessions": self.list_sessions,
                "close_session": self.close_session,
                "edit_file": self.edit_file,
                "create_file": self.create_file,
                "execute_with_venv": self.execute_with_venv,
                "analyze_codebase": self.analyze_codebase,
                # Remove reference to missing method "organize_files"
                "search_and_replace": self.search_and_replace,
                "insert_content": self.insert_content,
                # "git_operation": self.git_operation,  # Removed from handler methods
                "safe_edit_file": self.safe_edit_file,
                "test_file": self.test_file,
                "duplicate_file": self.duplicate_file,
                "restore_backup": self.restore_backup,
                "setup_project_venv": self.setup_project_venv,
                "execute_python": self.execute_python,
                "execute_applescript": self.execute_applescript,
                "execute_claude_code": self.execute_claude_code,
                "send_claude_input": self.send_claude_input
            }
            
            # Get the method for the action
            method = action_map.get(action)
            if not method:
                return HandlerResult(
                    success=False,
                    error=f"Unknown action: {action}"
                )
            
            # Execute the action and get result
            result = method(parameters)
            
            # Update metrics based on result
            if result.success:
                if action == "execute_command":
                    self.metrics["commands_executed"] += 1
                elif action in ["duplicate_file", "test_file"]:
                    self.metrics["files_created"] += 1
            else:
                self.metrics["errors"] += 1
                self.error_log.append({
                    "action": action,
                    "error": result.error,
                    "timestamp": time.time()
                })
            
            # CRITICAL FIX: Ensure responses from boardroom_planning_session are sent back to boardroom
            # This ensures background conversations always send responses back to the Trevor UI
            if parameters.get("send_to_boardroom", False) or parameters.get("boardroom_planning_session", False):
                try:
                    import sys
                    import os
                    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                    
                    # Log that we're forcing result to be sent to boardroom
                    print(f"\n\n🔄🔄🔄 FORCE SENDING TERMINAL RESULT TO BOARDROOM: {action} - success={result.success}")
                    print(f"🔄 RESPONSE DATA SIZE: {len(str(response_data))} characters")
                    print(f"🔄 BOARDROOM FLAGS: send_to_boardroom={parameters.get('send_to_boardroom', False)}, boardroom_planning_session={parameters.get('boardroom_planning_session', False)}")
                    logging.warning(f"🔄🔄🔄 FORCE SENDING TERMINAL RESULT TO BOARDROOM: {action} - success={result.success}")
                    
                    # Write to terminal_debug.log for visibility
                    with open("~/Jarvis/terminal_debug.log", "a") as f:
                        f.write(f"\n\n=== FORCE SENDING TERMINAL RESULT TO BOARDROOM AT {time.strftime('%Y-%m-%d %H:%M:%S')} ===\n")
                        f.write(f"ACTION: {action}\n")
                        f.write(f"SUCCESS: {result.success}\n")
                        f.write(f"RESPONSE SIZE: {len(str(response_data))} characters\n")
                        f.write(f"BOARDROOM FLAGS: send_to_boardroom={parameters.get('send_to_boardroom', False)}, boardroom_planning_session={parameters.get('boardroom_planning_session', False)}\n")
                    
                    # Get data from result to send
                    response_data = result.data if hasattr(result, 'data') else result.result if hasattr(result, 'result') else str(result)
                    
                    # Import socketio from boardroom_api
                    try:
                        from Core.user_ux.boardroom_api import socketio
                        
                        # Generate a session ID if needed
                        session_id = parameters.get("session_id", "terminal_session_" + str(int(time.time())))
                        
                        # Generate conversation_id if needed
                        conversation_id = parameters.get("conversation_id", "terminal_conv_" + str(int(time.time())))
                        
                        # Force sending a boardroom message - CRITICAL FIX: Don't restrict to a specific room
                        # This ensures the message goes to all connected clients
                        socketio.emit('message', {
                            'type': 'response',  # CRITICAL FIX: Change to 'response' type for Trevor desktop UI
                            'role': 'assistant',  # CRITICAL FIX: Add role for Trevor desktop UI
                            'content': response_data,
                            'conversation_id': conversation_id,
                            'timestamp': time.time(),
                            'task_id': parameters.get('task_id', 'terminal_task_' + str(int(time.time()))),
                            'is_boardroom': True,
                            'final_response': True  # Mark as final to ensure client updates UI
                        })
                        
                        print("\n\n🔄🔄🔄 TERMINAL RESPONSE SUCCESSFULLY SENT TO BOARDROOM VIA SOCKETIO")
                        logging.warning("🔄 Terminal response successfully sent to boardroom via SocketIO")
                        
                        # Write success to terminal_debug.log
                        with open("~/Jarvis/terminal_debug.log", "a") as f:
                            f.write(f"\n=== SOCKETIO MESSAGE SENT SUCCESSFULLY AT {time.strftime('%Y-%m-%d %H:%M:%S')} ===\n")
                            f.write(f"CONTENT TYPE: {type(response_data)}\n")
                            f.write(f"CONTENT PREVIEW: {str(response_data)[:100]}...\n")
                    except ImportError as ie:
                        error_msg = f"🔄 Failed to import socketio from Core.user_ux.boardroom_api: {str(ie)}"
                        print(f"\n\n{error_msg}")
                        logging.error(error_msg)
                        
                        # Try alternative approach by importing socketio from alternate location
                        try:
                            # Try to import directly from the socketio package
                            import socketio as sio
                            
                            # Create a client
                            sio_client = sio.Client()
                            
                            # Connect to the local server
                            sio_client.connect('http://localhost:5000')
                            
                            # Emit the message
                            sio_client.emit('message', {
                                'type': 'response',
                                'role': 'assistant',
                                'content': response_data,
                                'conversation_id': conversation_id,
                                'timestamp': time.time(),
                                'is_boardroom': True,
                                'final_response': True
                            })
                            
                            print("\n\n🔄🔄🔄 TERMINAL RESPONSE SENT VIA ALTERNATE SOCKETIO CLIENT")
                            logging.warning("🔄 Terminal response sent via alternate SocketIO client")
                            
                            # Disconnect
                            sio_client.disconnect()
                        except Exception as alt_err:
                            print(f"\n\n🔄 Alternative SocketIO approach failed: {str(alt_err)}")
                            logging.error(f"🔄 Alternative SocketIO approach failed: {str(alt_err)}")
                    except Exception as e:
                        error_msg = f"🔄 Error sending terminal result to boardroom: {str(e)}"
                        print(f"\n\n{error_msg}")
                        logging.error(error_msg)
                        
                        # Write error to terminal_debug.log
                        with open("~/Jarvis/terminal_debug.log", "a") as f:
                            f.write(f"\n=== SOCKETIO ERROR AT {time.strftime('%Y-%m-%d %H:%M:%S')} ===\n")
                            f.write(f"ERROR: {str(e)}\n")
                except Exception as e:
                    logging.error(f"🔄 Failed to send terminal result to boardroom: {str(e)}")
            
            return result
            
        except Exception as e:
            self.metrics["errors"] += 1
            error_msg = f"Error executing {action}: {str(e)}"
            self.error_log.append({
                "action": action,
                "error": error_msg,
                "timestamp": time.time()
            })
            return HandlerResult(success=False, error=error_msg)

    def execute_command(self, parameters: Dict[str, Any]) -> HandlerResult:
        print("\n\n🔴🔴🔴 TERMINAL HANDLER EXECUTE_COMMAND CALLED 🔴🔴🔴")
        print(f"🔴 PARAMETERS: {parameters}")
        # Write to a file for direct evidence
        with open("~/Jarvis/terminal_debug.log", "a") as f:
            f.write(f"\n\n=== TERMINAL HANDLER CALLED AT {time.strftime('%Y-%m-%d %H:%M:%S')} ===\n")
            f.write(f"PARAMETERS: {parameters}\n")
        """
        Execute a shell command or route to Claude Code execution.
        
        This method handles both direct terminal commands and natural language requests
        by routing them to the appropriate execution environment:
        - Terminal commands go directly to subprocess execution
        - Natural language requests go to Claude Code
        
        Args:
            parameters: Dictionary containing:
                - command: The command to execute
                - directory: Optional directory to execute the command in
                - timeout: Optional timeout in seconds
                - use_claude_window: Whether to use Claude Code window (default: False)
                - direct_execution: Whether to execute directly in terminal (default: True)
                - show_terminal: Whether to show the terminal window (default: False)
                - force_visible_terminal: Force terminal window to be visible (default: False)
                - reuse_claude_session: Reuse existing Claude Code session (default: False)
                - claude_session_id: Specific Claude session ID to reuse
                
        Returns:
            HandlerResult with the command output if successful
        """
        command = parameters.get("command")
        directory = parameters.get("directory")
        timeout = parameters.get("timeout", 30)
        
        # Extract parameters for determining execution path
        use_claude_window = parameters.get("use_claude_window", False)
        direct_execution = parameters.get("direct_execution", True)
        show_terminal = parameters.get("show_terminal", False)
        force_visible_terminal = parameters.get("force_visible_terminal", False)
        reuse_claude_session = parameters.get("reuse_claude_session", False)
        claude_session_id = parameters.get("claude_session_id")
        
        # For commands coming from BoardRoom via orchestrator, we need to ensure terminal visibility
        # This overrides the default settings to make sure terminal windows are always visible
        if command:
            is_from_boardroom = "message_from_boardroom" in str(parameters) or "boardroom" in str(parameters.get("source", "")) or parameters.get("boardroom_planning_session", False)
            force_execution = parameters.get("force_execution", False)
            
            # Check command cache for BoardRoom sessions
            if is_from_boardroom and not force_execution:
                # Initialize command cache if needed as a class variable for persistence across instances
                if not hasattr(self.__class__, 'command_cache'):
                    self.__class__.command_cache = {}
                    logging.warning(f"🔄 INITIALIZED PERSISTENT COMMAND CACHE AT CLASS LEVEL")
                
                # Create directory-aware cache key
                cache_key = f"boardroom:{command}"
                if directory:
                    cache_key = f"{cache_key}:{directory}"
                
                # Before checking exact cache hit, check for similar commands to suggest to models
                similar_commands = []
                if hasattr(self.__class__, 'command_cache') and len(self.__class__.command_cache) > 0:
                    # Extract core parts of the command for fuzzy matching
                    cmd_parts = command.split()
                    if len(cmd_parts) > 0:
                        base_cmd = cmd_parts[0]  # Like 'find', 'grep', 'cat', etc.
                        
                        # Look for similar cached commands with the same base command
                        for cached_key, cached_entry in self.__class__.command_cache.items():
                            # Only suggest BoardRoom cache entries
                            if cached_key.startswith("boardroom:"):
                                cached_cmd = cached_entry.get("command", "")
                                if cached_cmd and cached_cmd.startswith(base_cmd):
                                    # If command args have similar patterns, consider it similar
                                    # For example, 'find . -name "*.py"' and 'find . -name "*.txt"'
                                    similarity_score = 0
                                    
                                    # Check for exact match in first 3 args
                                    curr_parts = command.split()[:3]
                                    cached_parts = cached_cmd.split()[:3]
                                    
                                    # Count matching parts
                                    for i in range(min(len(curr_parts), len(cached_parts))):
                                        if curr_parts[i] == cached_parts[i]:
                                            similarity_score += 1
                                    
                                    # If commands share at least base command and one arg, suggest it
                                    if similarity_score >= 2 and cached_cmd != command:
                                        similar_commands.append({
                                            "command": cached_cmd,
                                            "age": time.time() - cached_entry["timestamp"],
                                            "cache_key": cached_key
                                        })
                
                # Check if exact command is in cache
                if cache_key in self.__class__.command_cache:
                    cache_entry = self.__class__.command_cache[cache_key]
                    cache_age = time.time() - cache_entry["timestamp"]
                    
                    # Cache lifetime for BoardRoom - 2 hours for BoardRoom planning sessions to reduce queries
                    if cache_age < 7200:  # 120 minutes
                        # Format age for display
                        if cache_age < 60:
                            age_str = f"{int(cache_age)} seconds"
                        elif cache_age < 3600:
                            age_str = f"{int(cache_age / 60)} minutes"
                        else:
                            age_str = f"{int(cache_age / 3600)} hours"
                            
                        logging.warning(f"🔄 USING CACHED RESULT FOR COMMAND: {command[:50]}... (age: {age_str})")
                        print(f"🔄 USING CACHED COMMAND RESULT (age: {age_str})")
                        
                        # Add a prominent header to cached output to make it very clear to models
                        cached_output = cache_entry["output"]
                        result_with_header = f"""
===================================================================
🔄 TERMINAL COMMAND CACHE HIT - Using saved result from {age_str} ago
===================================================================
COMMAND: {command}
CACHE KEY: {cache_key}

{cached_output}
===================================================================
NOTE: Using cached result to avoid unnecessary command execution. 
To force fresh execution, add force_execution=True to parameters.
==================================================================="""
                        
                        # Update cache hit metrics
                        self.metrics["cache_hits"] = self.metrics.get("cache_hits", 0) + 1
                        
                        return HandlerResult(
                            success=True, 
                            data=result_with_header,
                            details={
                                "cached": True,
                                "age_seconds": cache_age,
                                "command": command
                            }
                        )
                # If not in cache but similar commands exist, notify the model
                elif similar_commands and len(similar_commands) > 0:
                    # Sort by recency
                    similar_commands.sort(key=lambda x: x["age"])
                    # Take top 3 most recent
                    top_similar = similar_commands[:3]
                    
                    similar_cmd_list = ""
                    for idx, cmd_info in enumerate(top_similar):
                        if cmd_info["age"] < 60:
                            age_str = f"{int(cmd_info['age'])} seconds"
                        elif cmd_info["age"] < 3600:
                            age_str = f"{int(cmd_info['age'] / 60)} minutes" 
                        else:
                            age_str = f"{int(cmd_info['age'] / 3600)} hours"
                        similar_cmd_list += f"{idx+1}. {cmd_info['command']} (cached {age_str} ago)\n"
                    
                    # Add warning for models about similar cached commands
                    logging.warning(f"⚠️ SIMILAR COMMANDS FOUND IN CACHE: {len(top_similar)} similar commands")
                    print(f"""
⚠️ NOTICE: SIMILAR COMMANDS FOUND IN CACHE ⚠️
You're about to execute: {command}

However, similar commands are already in the cache:
{similar_cmd_list}

Consider checking these cached results instead of executing a new command.
To check cached results, use: "Let me check if a similar command has been run before: [command]"
""")
            
            # If coming from BoardRoom/orchestrator, always force terminal visibility by default
            if is_from_boardroom:
                show_terminal = True
                force_visible_terminal = True
                
                # Mark as part of a BoardRoom planning session to allow window reuse
                parameters["boardroom_planning_session"] = True
                
                # CRITICAL FIX: Ensure we send the results back to boardroom
                parameters["send_to_boardroom"] = True
                parameters["force_display_output"] = True
                parameters["capture_output"] = True
                
                # Set a session key for all BoardRoom commands to use the same terminal window
                if not hasattr(self.__class__, 'boardroom_planning_terminal'):
                    self.__class__.boardroom_planning_terminal = f"boardroom_terminal_{int(time.time())}"
                
                # Use the same persistent session ID for all BoardRoom commands
                parameters["session_id"] = self.__class__.boardroom_planning_terminal
                
                # Force session reuse for all BoardRoom commands
                parameters["reuse_session"] = True
                
                # Log BoardRoom session tracking
                logging.warning(f"🚨 BOARDROOM SESSION TRACKING: Using session {self.__class__.boardroom_planning_terminal}")
                
                # Track command history for context
                if not hasattr(self.__class__, 'boardroom_command_history'):
                    self.__class__.boardroom_command_history = []
                
                # Add this command to the history
                self.__class__.boardroom_command_history.append({
                    "command": command,
                    "timestamp": time.time(),
                    "is_claude_code": parameters.get("use_claude_window", False),
                    "is_natural_language": not any(command.startswith(cmd) for cmd in [
                        "cat ", "ls ", "find ", "grep ", "cd ", "mkdir ", "rm ", "cp ", "mv ", "echo ",
                        "git ", "npm ", "pip ", "python ", "node ", "curl ", "wget "
                    ]) and "|" not in command and ">" not in command and "<" not in command
                })
                
                logging.warning(f"🚨 BOARDROOM COMMAND DETECTED - FORCING TERMINAL VISIBILITY AND USING SESSION {self.__class__.boardroom_planning_terminal}")
                logging.warning(f"🚨 COMMAND HISTORY SIZE: {len(self.__class__.boardroom_command_history)} commands")
            elif show_terminal or force_visible_terminal:
                logging.warning(f"🚨 TERMINAL VISIBILITY REQUESTED: show_terminal={show_terminal}, force_visible_terminal={force_visible_terminal}")
                show_terminal = True
                force_visible_terminal = True
            else:
                logging.warning(f"🚨 NO VISIBILITY REQUESTED: Using defaults for terminal visibility")
        
        if not command:
            return HandlerResult(success=False, error="No command provided")
        
        # Log the command type for debugging
        logging.info(f"Command received: '{command[:50]}...' (truncated)")
        logging.info(f"Parameters: use_claude_window={use_claude_window}, direct_execution={direct_execution}")
        
        # Detect if this is likely a terminal command vs natural language
        is_terminal_command = direct_execution or any(command.startswith(cmd) for cmd in [
            "cat ", "ls ", "find ", "grep ", "cd ", "mkdir ", "rm ", "cp ", "mv ", "echo ",
            "git ", "npm ", "pip ", "python ", "node ", "curl ", "wget "
        ]) or "|" in command or ">" in command or "<" in command
        
        # Check if this is a command from BoardRoom
        is_from_boardroom = parameters.get("boardroom_session", False) or parameters.get("boardroom_planning_session", False)
        
        # If exclusive_terminal flag is set, ensure we NEVER hijack test terminals by always creating new ones
        exclusive_terminal = parameters.get("exclusive_terminal", False)
        if exclusive_terminal:
            # Force a new window even for BoardRoom sessions with exclusive_terminal flag
            parameters["force_new_window"] = True
            logging.warning(f"🚨 FORCING NEW WINDOW FOR EXCLUSIVE TERMINAL SESSION: {command[:30]}...")
        
        # For direct terminal commands, ensure they get their own window with strict isolation
        if is_terminal_command and not is_from_boardroom and not parameters.get("session_id"):
            # Mark this as a direct terminal command that should NEVER reuse windows
            parameters["force_new_window"] = True  # Force a new window
            parameters["window_type"] = self.WINDOW_TYPE_DIRECT_TERMINAL  # Mark as direct terminal type
            parameters["never_reuse"] = True  # Ensure this window is never reused
            parameters["separate_from_claude"] = True  # Keep separate from Claude Code windows
            
            # Generate a unique session ID to prevent any window reuse
            direct_unique_id = f"direct_terminal_{int(time.time())}_{os.getpid()}_{hash(command)}"
            parameters["name"] = f"Direct Command Terminal {direct_unique_id}"
            
            logging.warning(f"🚨 FORCING ISOLATED WINDOW FOR DIRECT TERMINAL COMMAND: {command[:30]}...")
        
        # Fix common command syntax issues
        if is_terminal_command:
            # Fix mismatched quotes
            quote_count = command.count('"')
            if quote_count % 2 != 0:  # Odd number of quotes
                logging.warning(f"🚨 FIXING MISMATCHED DOUBLE QUOTES IN COMMAND: {command}")
                if command.endswith('"'):
                    # Remove trailing quote if it's unmatched
                    command = command[:-1]
                else:
                    # Add closing quote if missing
                    command = command + '"'
                    
            # Fix mismatched single quotes
            single_quote_count = command.count("'")
            if single_quote_count % 2 != 0:  # Odd number of quotes
                logging.warning(f"🚨 FIXING MISMATCHED SINGLE QUOTES IN COMMAND: {command}")
                if command.endswith("'"):
                    # Remove trailing quote if it's unmatched
                    command = command[:-1]
                else:
                    # Add closing quote if missing
                    command = command + "'"
        
        # Detect if this is a file viewing command (cat, less, head, tail, etc.)
        is_file_viewing_command = command.startswith("cat ") or command.startswith("less ") or command.startswith("head ") or command.startswith("tail ")
        
        # If this is a file viewing command, extract the file path
        file_path = None
        if is_file_viewing_command:
            parts = command.split()
            if len(parts) > 1:
                file_path = parts[-1]  # Get the last part which should be the file path
                logging.warning(f"📄 FILE VIEWING COMMAND DETECTED: Command={command}, File={file_path}")
                print(f"📄 FILE VIEWING COMMAND: {command}")
                print(f"📄 FILE PATH: {file_path}")
                
                # Check if this file has been viewed before - use our file content cache
                if not hasattr(self.__class__, 'file_content_cache'):
                    self.__class__.file_content_cache = {}
                
                # Create absolute path for more reliable caching
                abs_file_path = os.path.abspath(file_path) if os.path.exists(file_path) else file_path
                
                # Check if we have a cached version of this file
                if abs_file_path in self.__class__.file_content_cache:
                    content, timestamp = self.__class__.file_content_cache[abs_file_path]
                    age = time.time() - timestamp
                    # Cache valid for the entire planning session - no expiration
                    if True:  # Always use cache if it exists
                        logging.warning(f"📄 USING CACHED FILE CONTENT ({int(age)}s old): {abs_file_path}")
                        print(f"📄 USING CACHED FILE CONTENT: {abs_file_path}")
                        # Return cached content with header indicating it's from cache
                        # Format the age intelligently
                        if age < 60:
                            age_str = f"{int(age)} seconds"
                        elif age < 3600:
                            age_str = f"{int(age / 60)} minutes"
                        else:
                            age_str = f"{int(age / 3600)} hours"
                            
                        return HandlerResult(
                            success=True,
                            data=f"[CACHED FILE CONTENT - viewed {age_str} ago - persistent for this planning session]\n\n{content}"
                        )
                
                # If file path doesn't look like a full path and might be a partial filename
                # Also remove any trailing periods that might be causing problems with file lookups
                if file_path and file_path.endswith('.'):
                    file_path = file_path.rstrip('.')
                    command = command.rstrip('.')
                    logging.warning(f"📄 REMOVED TRAILING PERIOD FROM COMMAND: {command}")
                
                if not file_path.startswith("/") and not os.path.exists(file_path):
                    try:
                        # Try to find matching files
                        logging.warning(f"📄 PARTIAL FILE PATH DETECTED: Searching for matching files")
                        # Extract basename without any directory components
                        basename = os.path.basename(file_path)
                        # Remove any trailing periods
                        basename = basename.rstrip('.')
                        find_cmd = f"find ~/Jarvis -name '*{basename}*' -type f | sort"
                        find_result = subprocess.run(find_cmd, shell=True, capture_output=True, text=True)
                        matching_files = [f for f in find_result.stdout.strip().split('\n') if f]
                        
                        # If we found matches
                        if matching_files:
                            logging.warning(f"📄 MATCHING FILES FOUND: {len(matching_files)} matches")
                            print(f"📄 FOUND {len(matching_files)} MATCHING FILES:")
                            for i, match in enumerate(matching_files[:5]):
                                print(f"   {i+1}. {match}")
                            
                            # Update command to use the first full path match if we find it
                            if matching_files[0]:
                                original_command = command
                                command = command.replace(file_path, matching_files[0])
                                logging.warning(f"📄 UPDATED COMMAND: {original_command} -> {command}")
                                print(f"📄 UPDATED COMMAND: {command}")
                    except Exception as e:
                        logging.error(f"Error in file path resolution: {str(e)}")
                        # Continue with original command if there's an error
        
        # Explicit debugging for command type detection
        logging.warning(f"COMMAND TYPE DETECTION: is_terminal_command={is_terminal_command}, command='{command[:50]}...'")
        if direct_execution:
            logging.warning("COMMAND FORCED DIRECT EXECUTION via direct_execution=True")
        if use_claude_window:
            logging.warning("CLAUDE WINDOW REQUESTED via use_claude_window=True")
        print(f"🚨 COMMAND TYPE: {'Terminal Command' if is_terminal_command else 'Natural Language'}")
        print(f"🚨 USE CLAUDE WINDOW: {use_claude_window}")
        print(f"🚨 DIRECT EXECUTION: {direct_execution}")
        
        # Better detection of terminal commands with explicit patterns
        terminal_command_patterns = ['cat ', 'ls ', 'find ', 'grep ', 'cd ', 'mkdir ', 'rm ', 'cp ', 'mv ', 'echo ', 
                                   'git ', 'npm ', 'pip ', 'python ', 'node ', 'curl ', 'wget ', 'clear']
        
        # Check for explicit terminal command patterns - these should NEVER go to Claude
        is_explicit_terminal_pattern = False
        
        # Handle compound commands like "clear && cat"
        if " && " in command:
            parts = [part.strip() for part in command.split(" && ")]
            if any(part.startswith(pattern) for part in parts for pattern in terminal_command_patterns):
                is_explicit_terminal_pattern = True
                logging.warning(f"DETECTED COMPOUND TERMINAL COMMAND: {command}")
        else:
            # Single command - check directly
            is_explicit_terminal_pattern = any(command.startswith(pattern) for pattern in terminal_command_patterns)
        
        # IMPORTANT: Force terminal execution for explicit terminal patterns
        if is_explicit_terminal_pattern:
            is_terminal_command = True
            is_natural_language = False
            use_claude_window = False  # Override this to never use Claude for terminal commands
            logging.warning(f"FORCING TERMINAL EXECUTION FOR EXPLICIT TERMINAL PATTERN: {command}")
        else:
            # If not an explicit terminal pattern, use the original detection
            is_natural_language = not is_terminal_command
        
        # Log detection information
        logging.warning(f"DETECTION: use_claude_window={use_claude_window}, is_terminal_command={is_terminal_command}, direct_execution={direct_execution}, is_natural_language={is_natural_language}, is_explicit_terminal_pattern={is_explicit_terminal_pattern}")
        
        # Explicitly check for the claude request signal - but only if not a terminal command
        is_claude_request = (use_claude_window or "claude" in command.lower()) and not is_explicit_terminal_pattern
        
        # Log additional debug information about how we're determining the execution method
        logging.warning(f"EXECUTION DETERMINATION: Command starts with terminal command: {any(command.startswith(cmd) for cmd in ['cat ', 'ls ', 'find ', 'grep ', 'cd ', 'mkdir ', 'rm ', 'cp ', 'mv ', 'echo ', 'git ', 'npm ', 'pip ', 'python ', 'node ', 'curl ', 'wget '])}")
        logging.warning(f"EXECUTION DETERMINATION: Command contains pipes/redirects: {bool('|' in command or '>' in command or '<' in command)}")
        logging.warning(f"EXECUTION DETERMINATION: Command contains 'claude': {bool('claude' in command.lower())}")
        
        # Check if this is a standard terminal command that should NEVER be sent to Claude
        is_terminal_command_pattern = False
        
        # Define common terminal commands patterns
        terminal_command_patterns = ['cat ', 'ls ', 'find ', 'grep ', 'cd ', 'mkdir ', 'rm ', 'cp ', 'mv ', 'echo ', 
                                    'git ', 'npm ', 'pip ', 'python ', 'node ', 'curl ', 'wget ', 'clear']
        
        # Check for compound terminal commands like "clear && cat"
        if " && " in command:
            parts = [part.strip() for part in command.split(" && ")]
            if any(part.startswith(pattern) for part in parts for pattern in terminal_command_patterns):
                is_terminal_command_pattern = True
                logging.warning(f"TERMINAL COMMAND DETECTED IN COMPOUND COMMAND: {command}")
        else:
            # Single command - check against patterns
            is_terminal_command_pattern = any(command.startswith(pattern) for pattern in terminal_command_patterns)
        
        # Force is_terminal_command to be True if we detected a terminal command pattern
        # This ensures terminal commands are NEVER sent to Claude
        if is_terminal_command_pattern:
            is_terminal_command = True
            is_natural_language = False
            use_claude_window = False
            logging.warning(f"FORCING TERMINAL EXECUTION FOR COMMAND: {command}")
        
        # Route to Claude Code ONLY for natural language requests
        # 1. Must NOT be a terminal command pattern
        # 2. Must either be explicitly marked as claude window OR be natural language
        if not is_terminal_command_pattern and (use_claude_window or (is_natural_language and not direct_execution)):
            logging.warning(f"ROUTING TO CLAUDE CODE: '{command[:50]}...' (truncated)")
            print(f"🚨 ROUTING TO CLAUDE CODE WINDOW")
            print(f"🚨 COMMAND: {command[:100]}...")
            try:
                # Use execute_claude_code method with appropriate parameters
                claude_params = {
                    "prompt": command,
                    "directory": directory,
                    "timeout": timeout,
                    "show_terminal": show_terminal or force_visible_terminal,
                    "reuse_session": reuse_claude_session,
                    "session_id": claude_session_id,
                    "capture_output": True
                }
                
                print(f"🚨 CLAUDE PARAMS: reuse_session={reuse_claude_session}, session_id={claude_session_id}")
                print(f"🚨 CLAUDE PARAMS: show_terminal={show_terminal}, force_visible={force_visible_terminal}")
                
                # Call execute_claude_code
                logging.warning(f"CALLING EXECUTE_CLAUDE_CODE with params: {claude_params}")
                result = self.execute_claude_code(claude_params)
                logging.warning(f"CLAUDE CODE EXECUTION RESULT: success={result.success}")
                print(f"🚨 CLAUDE CODE EXECUTION COMPLETED: success={result.success}")
                
                # Make sure to notify BoardRoom about the Claude Code execution
                if self.orchestrator:
                    try:
                        # Prepare notification data
                        claude_result_data = {
                            "success": result.success,
                            "output": getattr(result, 'data', '') or getattr(result, 'result', ''),
                            "error": getattr(result, 'error', None),
                            "command": command,
                            "execution_time": time.time(),
                            "is_terminal_command": False,  # Flag this as NOT a terminal command
                            "is_claude_code": True  # Flag this as Claude Code execution
                        }
                        
                        # Log the notification
                        logging.warning(f"SENDING CLAUDE CODE COMPLETION TO ORCHESTRATOR")
                        print(f"🚨 NOTIFYING ORCHESTRATOR: Claude Code execution completed")
                        
                        # Try direct BoardRoom notification
                        try:
                            if hasattr(self, 'boardroom') and self.boardroom:
                                logging.warning("Using direct BoardRoom notification for Claude Code")
                                # Use track_journey_step_sync instead of track_request_journey_sync
                                from Jarvis_Agent_SDK.boardroom_connector import track_journey_step_sync
                                track_journey_step_sync(
                                    journey_id=f"claude_code_{int(time.time())}",
                                    step_type="execution",
                                    step_name="claude_code_completed",
                                    description="Claude Code execution completed",
                                    status="completed",
                                    metadata=claude_result_data
                                )
                        except Exception as e:
                            logging.error(f"Error in direct BoardRoom notification for Claude Code: {str(e)}")
                        
                        # Notify orchestrator
                        notification_coroutine = self.orchestrator.notify_command_execution(
                            command=f"[CLAUDE CODE] {command[:50]}...",
                            result=claude_result_data
                        )
                        
                        # Execute notification
                        try:
                            asyncio.create_task(notification_coroutine)
                        except RuntimeError:
                            # Try with a new event loop
                            try:
                                loop = asyncio.new_event_loop()
                                asyncio.set_event_loop(loop)
                                loop.run_until_complete(notification_coroutine)
                                loop.close()
                            except Exception:
                                logging.error("Failed to notify orchestrator about Claude Code completion")
                    except Exception as e:
                        logging.error(f"Error notifying about Claude Code execution: {str(e)}")
                
                return result
            except Exception as e:
                logging.error(f"ERROR EXECUTING WITH CLAUDE CODE: {str(e)}")
                print(f"🚨 ERROR EXECUTING WITH CLAUDE CODE: {str(e)}")
                # Fall back to direct execution if Claude Code fails
                logging.warning(f"FALLING BACK to direct execution for: {command[:50]}... (truncated)")
                print(f"🚨 FALLING BACK to direct terminal execution")
                # Continue with direct execution below
        
        # Direct terminal execution path
        try:
            logging.info(f"Executing terminal command directly: {command[:50]}... (truncated)")
            # Save current directory if changing
            current_dir = None
            if directory:
                current_dir = os.getcwd()
                os.chdir(directory)
                
            # Execute the command with additional debugging
            logging.warning(f"EXECUTING TERMINAL COMMAND: {command} in directory {directory or os.getcwd()}")
            print(f"🚨 EXECUTING TERMINAL COMMAND: {command}")
            print(f"🚨 DIRECTORY: {directory or os.getcwd()}")
            
            # Use AppleScript to create a visible terminal window if visibility is requested
            if force_visible_terminal or show_terminal:
                logging.warning(f"🚨 CREATING VISIBLE TERMINAL WINDOW FOR COMMAND: {command}")
                print(f"🚨 CREATING VISIBLE TERMINAL WINDOW - force_visible={force_visible_terminal}, show_terminal={show_terminal}")
                
                # First check if there's an existing terminal window we should reuse
                # We want to specifically NOT reuse Claude Code windows for terminal commands
                existing_terminal_window = None
                
                # Check if this is a BoardRoom session with a persistent terminal
                if parameters.get("boardroom_planning_session", False) and hasattr(self.__class__, 'boardroom_planning_terminal'):
                    terminal_session_id = self.__class__.boardroom_planning_terminal
                    
                    # See if we have this terminal session in our active sessions
                    if terminal_session_id in self.__class__.active_terminal_sessions:
                        existing_terminal_info = self.__class__.active_terminal_sessions[terminal_session_id]
                        # Only reuse if it's a terminal_command type window, not a claude_code window
                        if existing_terminal_info.get("window_type") == self.WINDOW_TYPE_TERMINAL:
                            existing_terminal_window = terminal_session_id
                            logging.warning(f"🚨 REUSING EXISTING BOARDROOM TERMINAL SESSION: {terminal_session_id}")
                
                # If we don't have a terminal window to reuse, detect any non-Claude terminal windows
                if not existing_terminal_window:
                    # Use AppleScript to find non-Claude terminal windows
                    find_terminal_script = '''
                    tell application "Terminal"
                        set terminalWindowID to missing value
                        set terminalTabID to missing value
                        
                        # Look for windows WITHOUT "CLAUDE" in title that might be terminal windows
                        repeat with w in windows
                            repeat with t in tabs of w
                                if name of t does not contain "CLAUDE" then
                                    set terminalWindowID to id of w
                                    set terminalTabID to id of t
                                    exit repeat
                                end if
                            end repeat
                            if terminalWindowID is not missing value then
                                exit repeat
                            end if
                        end repeat
                        
                        # Return window ID if found, otherwise "not_found"
                        if terminalWindowID is not missing value then
                            return terminalWindowID & ":" & terminalTabID
                        else
                            return "not_found"
                        end if
                    end tell
                    '''
                    
                    # Run the find script to detect terminal windows
                    try:
                        find_result = subprocess.run(["osascript", "-e", find_terminal_script], 
                                                  capture_output=True, text=True)
                        find_output = find_result.stdout.strip()
                        
                        # If we found a terminal window, prepare to reuse it
                        if find_output and find_output != "not_found":
                            logging.warning(f"🚨 FOUND EXISTING TERMINAL WINDOW: {find_output}")
                            # Generate a session ID for this window
                            terminal_session_id = f"terminal_detected_{int(time.time())}"
                            
                            # Record this as a terminal window in our tracking system
                            window_id, tab_id = find_output.split(":")
                            self.__class__.active_terminal_sessions[terminal_session_id] = {
                                "window_id": window_id,
                                "tab_id": tab_id,
                                "detected_at": time.time(),
                                "last_used": time.time(),
                                "active": True,
                                "window_type": self.WINDOW_TYPE_TERMINAL,
                                "session_origin": "detected",
                                "never_reuse": False,  # Default to allowing reuse for detected windows
                                "force_new_window": False  # Not forcing new window for detected sessions
                            }
                            
                            # Set as the current terminal window
                            existing_terminal_window = terminal_session_id
                            
                            # If this is a BoardRoom session, register this window for reuse
                            if parameters.get("boardroom_planning_session", False):
                                self.__class__.boardroom_planning_terminal = terminal_session_id
                                logging.warning(f"🚨 REGISTERED DETECTED TERMINAL AS BOARDROOM TERMINAL: {terminal_session_id}")
                    except Exception as e:
                        logging.error(f"Error detecting terminal windows: {str(e)}")
                
                # Properly escape the command for AppleScript - this is critical for avoiding syntax errors
                # AppleScript has complex escaping rules, especially for quotes inside quotes
                # First, escape any existing backslashes
                escaped_command = command.replace('\\', '\\\\')
                # Next, escape single quotes (very carefully)
                escaped_command = escaped_command.replace("'", "\\'")
                # Finally, escape double quotes
                escaped_command = escaped_command.replace('"', '\\"')
                
                # For extra safety with special characters like emoji and unicode
                # Encode special characters using hex encoding for maximum reliability
                import re
                def replace_special(match):
                    char = match.group(0)
                    # Handle emoji and other special Unicode characters
                    if ord(char) > 127:
                        return f"\\u{ord(char):04x}"
                    return char
                
                # Replace special characters with their escaped versions
                escaped_command = re.sub(r'[^\x00-\x7F]', replace_special, escaped_command)
                current_directory = directory or os.getcwd()
                
                # Create an AppleScript to execute the command in a visible terminal
                # Use a safer approach to avoid quote and backslash issues
                # Build the command step by step to avoid f-string backslash problems
                
                # Create individual script components to avoid escaping issues
                cd_cmd = f"cd {current_directory}"
                header_cmd = "echo '\\033[1;32m========== BOARDROOM TERMINAL COMMAND ==========\\033[0m'"
                exec_header = "echo '\\033[1;33mExecuting Command:\\033[0m'"
                cmd_echo = f"echo '$ {escaped_command}'"
                begin_output = "echo '\\033[1;36m----- OUTPUT BEGIN -----\\033[0m'"
                end_output = "echo '\\033[1;36m----- OUTPUT END -----\\033[0m'"
                
                # Construct compact command without extra whitespace
                full_command = f"{cd_cmd} && {header_cmd} && {exec_header} && {cmd_echo} && {begin_output} && {escaped_command} && {end_output}"
                
                # Create an ultra-simplified AppleScript with minimal escaping
                # Log the command and directory for debugging
                logging.warning(f"[TERMINAL_WINDOW] Using simplified AppleScript for terminal execution")
                logging.warning(f"[TERMINAL_WINDOW] Directory: {current_directory}")
                logging.warning(f"[TERMINAL_WINDOW] Command: {command[:50]}...")
                
                # For file viewing commands, add file metadata display
                if is_file_viewing_command and file_path:
                    logging.warning(f"[TERMINAL_WINDOW] Enhancing file viewing command with metadata")
                    
                    # Create enhanced command that shows file information before content
                    # Use simplified colors and escape sequences to avoid AppleScript issues
                    # Avoid triple quotes and overly complex formatting
                    enhanced_cmd = "echo '===== FILE INFORMATION =====' && "
                    enhanced_cmd += f"echo 'File: {file_path}' && "
                    enhanced_cmd += f"echo 'Directory: {current_directory}' && "
                    enhanced_cmd += "echo '===== FILE CONTENTS =====' && "
                    enhanced_cmd += escaped_command
                    
                    # Re-escape the enhanced command
                    escaped_command = enhanced_cmd.replace('"', '\\"').replace("'", "\\'")
                
                # Use the most basic, reliable AppleScript syntax possible with no extra spacing
                # Remove unnecessary clear commands that create the large gap and just use a simple command execution
                # Create a safer approach for handling complex commands
                # Instead of complex AppleScript quoting, we'll use a direct script approach
                
                # First create a safe script that handles the command properly
                temp_shell_script = f"/tmp/terminal_cmd_{int(time.time())}_{os.getpid()}.sh"
                
                # Extract the pure command without any AppleScript/shell escaping
                # This ensures we're working with the original command, not an escaped version
                original_command = command
                
                # Log the exact command for debugging
                logging.warning(f"🚨 ORIGINAL COMMAND FOR SHELL SCRIPT: {original_command}")
                
                # Detect and handle natural language mixed with commands
                # Common phrases that indicate natural language after a command
                terminators = [" and ", " then ", " so ", " for ", " with ", " allowing ", " enabling ", " which ", " because "]
                
                # Handle find command specially - we need to preserve the full command structure
                # since find has complex arguments including quotes that shouldn't be truncated
                if original_command.strip().startswith("find "):
                    # For find commands, only truncate if we have a clear natural language boundary
                    # after the command's normal structure is complete
                    clean_command = original_command
                    
                    # Check for quoted arguments first to make sure we don't truncate inside quotes
                    quote_positions = []
                    i = 0
                    while i < len(original_command):
                        if original_command[i] in ['"', "'"]:
                            quote_char = original_command[i]
                            start_pos = i
                            i += 1
                            while i < len(original_command) and original_command[i] != quote_char:
                                i += 1
                            if i < len(original_command):  # Found closing quote
                                quote_positions.append((start_pos, i))
                        i += 1
                    
                    # Now check for terminators, but only if they're not inside quotes
                    for term in terminators:
                        pos = original_command.lower().find(term)
                        if pos > 0:
                            # Check if this position is inside any quotes
                            inside_quotes = False
                            for start, end in quote_positions:
                                if start < pos < end:
                                    inside_quotes = True
                                    break
                            
                            if not inside_quotes:
                                # Make sure we have at least the basic find command structure
                                # which is typically "find [path] [expression]"
                                cmd_parts = original_command[:pos].strip().split()
                                if len(cmd_parts) >= 3:  # At minimum: "find", path, and one expression
                                    clean_command = original_command[:pos]
                                    logging.warning(f"🚨 DETECTED NATURAL LANGUAGE AFTER FIND COMMAND at '{term}'. Truncated command.")
                                    break
                else:
                    # First check for newlines - in bidirectional communication, we should truncate at newlines
                    if "\n" in original_command:
                        # If there's a newline, truncate at the first newline
                        clean_command = original_command.split("\n")[0]
                        logging.warning(f"🚨 DETECTED NEWLINE AFTER COMMAND. Truncated command to first line only.")
                    else:
                        # For other commands, use the standard approach with terminators
                        clean_command = original_command
                        for term in terminators:
                            pos = original_command.lower().find(term)
                            if pos > 0:
                                # Found potential natural language - truncate the command
                                clean_command = original_command[:pos]
                                logging.warning(f"🚨 DETECTED NATURAL LANGUAGE AFTER COMMAND at '{term}'. Truncated command.")
                                break
                
                # Implement a more sophisticated quote balancing algorithm
                logging.warning(f"🚨 ORIGINAL COMMAND FOR QUOTE BALANCING: {clean_command}")
                
                # Create a safer shell script that properly handles quotes
                # We'll escape all embedded quotes rather than trying to balance them
                # This is a more reliable approach for shell script execution
                clean_command = clean_command.replace("\\\"", "__ESCAPED_DOUBLE_QUOTE__")
                clean_command = clean_command.replace("\\'", "__ESCAPED_SINGLE_QUOTE__")
                clean_command = clean_command.replace("\"", "\\\"")
                clean_command = clean_command.replace("'", "\\'")
                clean_command = clean_command.replace("__ESCAPED_DOUBLE_QUOTE__", "\\\"")
                clean_command = clean_command.replace("__ESCAPED_SINGLE_QUOTE__", "\\'")
                
                # Remove any trailing backslashes that could cause shell errors
                if clean_command.endswith("\\"):
                    clean_command = clean_command[:-1]
                    logging.warning("🚨 REMOVED TRAILING BACKSLASH FROM COMMAND")
                
                # Verify the command doesn't have obvious syntax errors
                if clean_command.count("$(") != clean_command.count(")"):
                    # Unbalanced command substitution, add closing parenthesis
                    clean_command += ")"
                    logging.warning("🚨 FIXED UNBALANCED COMMAND SUBSTITUTION")
                
                # Log the cleaned command for debugging
                logging.warning(f"🚨 CLEANED COMMAND WITH ESCAPED QUOTES: {clean_command}")
                
                logging.warning(f"🚨 FINAL CLEANED COMMAND: {clean_command}")
                
                # Create a shell script with proper quoting for the shell
                with open(temp_shell_script, "w") as f:
                    # Write a properly formatted script with commands on separate lines
                    f.write("#!/bin/bash\n")
                    f.write("set -e\n\n")
                    # Use printf to safely handle any directory path
                    f.write(f"cd {os.path.abspath(current_directory)}\n\n")
                    # Simply execute the command without extra formatting
                    f.write(f"{clean_command}\n\n")
                    # Self-cleanup - delete the script file after execution
                    f.write(f"\n# Self-cleanup\n[ -f \"{temp_shell_script}\" ] && rm \"{temp_shell_script}\" || true\n")
                
                # Make the script executable
                os.chmod(temp_shell_script, 0o755)
                
                # Log the script content for debugging
                with open(temp_shell_script, "r") as f:
                    script_content = f.read()
                    logging.warning(f"🚨 SHELL SCRIPT CONTENT:\n{script_content}")
                
                # Now use a simple AppleScript that just executes our shell script
                # We need to use the "sh" command with the full path to ensure it works correctly
                # Use quotes around the path to ensure it works with spaces
                # Add command to get the result back as well
                # Use a single window approach
                # Create a dedicated shell function to avoid command leakage - properly escaped for AppleScript
                # Use a format that works reliably in AppleScript's do script command
                isolated_shell_cmd = f"bash -c \"(function run_isolated() {{ sh \\\"{temp_shell_script}\\\" && echo '[COMMAND_COMPLETE]'; }}; run_isolated)\""
                isolated_command = isolated_shell_cmd.replace('"', '\\"')
                logging.warning(f"🔹 ISOLATED COMMAND: {isolated_command}")
                
                # Escape the command for AppleScript
                escaped_isolated_command = isolated_command.replace('"', '\\"').replace("'", "\\'")
                
                # COMPLETELY BYPASS TERMINAL WINDOW EXECUTION FOR SAFETY
                # Instead of showing a terminal window, we'll just execute the command directly
                logging.warning("🔹 BYPASSING TERMINAL WINDOW EXECUTION AND USING DIRECT EXECUTION INSTEAD")
                
                # Initialize direct_execution_result with a default value in case the try block fails
                direct_execution_result = None
                
                # Execute the command directly
                try:
                    # First make sure the shell script exists and is executable
                    if not os.path.exists(temp_shell_script):
                        logging.error(f"Shell script does not exist: {temp_shell_script}")
                        raise FileNotFoundError(f"Shell script not found: {temp_shell_script}")
                    
                    # Make it executable
                    os.chmod(temp_shell_script, 0o755)
                    
                    # Execute the shell script directly without any terminal window
                    direct_result = subprocess.run(f"sh '{temp_shell_script}'", shell=True, 
                                                capture_output=True, text=True, timeout=timeout)
                    
                    # Log the direct execution result
                    logging.warning(f"🔹 DIRECT EXECUTION RESULT: {direct_result.returncode}")
                    logging.warning(f"🔹 DIRECT EXECUTION STDOUT: {direct_result.stdout[:100]}")
                    
                    # Store the direct execution result for returning later
                    direct_execution_result = direct_result
                    
                    # Clean up the shell script
                    try:
                        # Check if the file exists before attempting to remove it
                        if os.path.exists(temp_shell_script):
                            os.remove(temp_shell_script)
                            logging.warning(f"🔹 REMOVED SHELL SCRIPT: {temp_shell_script}")
                        else:
                            logging.warning(f"🔹 SHELL SCRIPT NOT FOUND (already removed): {temp_shell_script}")
                    except Exception as e:
                        logging.error(f"Error removing shell script: {str(e)}")
                    
                    # Create a fake terminal script to maintain compatibility with the rest of the code
                    terminal_script = f"echo 'Direct execution mode - no terminal window'"
                    
                except Exception as e:
                    logging.error(f"Error in direct execution: {str(e)}")
                    # Create a fake terminal script to maintain compatibility
                    terminal_script = f"echo 'Direct execution failed: {str(e)}'"
                    
                    # Create a synthetic direct_execution_result if it's None
                    if direct_execution_result is None:
                        from collections import namedtuple
                        FakeResult = namedtuple('FakeResult', ['returncode', 'stdout', 'stderr'])
                        direct_execution_result = FakeResult(
                            returncode=1, 
                            stdout=f"Direct execution failed: {str(e)}", 
                            stderr=str(e)
                        )
                
                # Handle BoardRoom planning sessions (always reuse the same terminal window)
                if parameters.get("boardroom_planning_session", False):
                    # ALWAYS use the same fixed session ID for ALL BoardRoom commands
                    terminal_session_id = "boardroom_persistent_terminal_fixed"
                    self.__class__.boardroom_planning_terminal = terminal_session_id
                    
                    # CRITICAL: Before doing anything else, close all other terminal windows to ensure we don't accumulate them
                    # Find and close all terminal windows EXCEPT our known persistent one
                    close_script = '''
                    tell application "Terminal"
                        set keptWindow to false
                        set keptWindowID to ""
                        
                        # First find our existing window if it exists
                        repeat with w in windows
                            if (id of w) is not 0 then
                                set windowID to id of w
                                set keptWindow to true
                                set keptWindowID to windowID
                                exit repeat
                            end if
                        end repeat
                        
                        # Return the window ID we're keeping
                        return keptWindowID
                    end tell
                    '''
                    
                    # Run script to find a window to keep
                    try:
                        close_result = subprocess.run(["osascript", "-e", close_script], 
                                              capture_output=True, text=True)
                        kept_window_id = close_result.stdout.strip()
                        
                        # If we found a window to keep, store it
                        if kept_window_id and kept_window_id != "0" and kept_window_id != "":
                            logging.warning(f"🚨 FOUND EXISTING TERMINAL WINDOW TO KEEP: {kept_window_id}")
                            
                            # Store this window ID for our session
                            if not hasattr(self.__class__, 'active_terminal_sessions'):
                                self.__class__.active_terminal_sessions = {}
                                
                            if terminal_session_id not in self.__class__.active_terminal_sessions:
                                self.__class__.active_terminal_sessions[terminal_session_id] = {}
                                
                            # Update the window ID for our fixed session
                            self.__class__.active_terminal_sessions[terminal_session_id]["window_id"] = kept_window_id
                            self.__class__.active_terminal_sessions[terminal_session_id]["active"] = True
                            self.__class__.active_terminal_sessions[terminal_session_id]["last_used"] = time.time()
                    except Exception as e:
                        logging.error(f"Error finding window to keep: {str(e)}")
                    
                    # First check if we already have a window ID in our tracking system
                    found_window_id = None
                    if hasattr(self.__class__, 'active_terminal_sessions') and terminal_session_id in self.__class__.active_terminal_sessions:
                        session_info = self.__class__.active_terminal_sessions[terminal_session_id]
                        found_window_id = session_info.get("window_id")
                        
                        # Try to verify the window still exists
                        if found_window_id:
                            check_script = '''
                            tell application "Terminal"
                                try
                                    set w to (first window whose id is ''' + str(found_window_id) + ''')
                                    return "exists"
                                on error
                                    return "not_found"
                                end try
                            end tell
                            '''
                            
                            check_result = subprocess.run(["osascript", "-e", check_script], 
                                                      capture_output=True, text=True)
                            if check_result.stdout.strip() != "exists":
                                # Window doesn't exist anymore
                                found_window_id = None
                            else:
                                logging.warning(f"🚨 FOUND EXISTING TERMINAL WINDOW WITH ID: {found_window_id}")
                    
                    # If we didn't find a window in our tracking, aggressively search for any terminal window with AppleScript
                    if not found_window_id:
                        try:
                            # Search for any terminal window that's not a Claude window
                            find_term_script = '''
                            tell application "Terminal"
                                set foundWindow to false
                                set windowID to ""
                            
                                # First check all windows
                                repeat with w in windows
                                    # CRITICAL SAFETY: Never reuse the current test window
                                    # For testing if this is the terminal that runs the test,
                                    # check for specific text in the contents
                                    set tabContents to ""
                                    try
                                        set tabContents to (contents of (first tab of w)) as string
                                    end try
                                    
                                    # Skip this window if it has ANYTHING that suggests it's a test window or active terminal
                                    # to avoid hijacking the test window itself - be EXTREMELY conservative
                                    if tabContents contains "Running" or tabContents contains "test" or tabContents contains "jarvis" or 
                                       tabContents contains "terminal" or tabContents contains "command" or
                                       tabContents contains "Python" or tabContents contains "python" or
                                       (name of w) contains "test" or (name of w) contains "Python" or
                                       tabContents contains ">" or tabContents contains "$" or
                                       tabContents contains "%" or tabContents contains "#" then
                                        # NEVER use windows that look like they're active or running tests
                                        # or the window that has our test script running
                                        log "SAFETY: Skipping window that might be a test/active window"
                                    else
                                        # Check window title and contents to determine if it's a good candidate
                                        repeat with t in tabs of w
                                            # Skip windows with "CLAUDE" in the title
                                            if name of t does not contain "CLAUDE" then
                                                set windowID to id of w
                                                set foundWindow to true
                                                exit repeat
                                            end if
                                        end repeat
                                    end if
                                    
                                    if foundWindow then
                                        exit repeat
                                    end if
                                end repeat
                                
                                if foundWindow then
                                    return windowID
                                else
                                    return "not_found"
                                end if
                            end tell
                            '''
                            
                            # Run the script to find a terminal window
                            find_result = subprocess.run(["osascript", "-e", find_term_script], 
                                                      capture_output=True, text=True)
                            window_id = find_result.stdout.strip()
                            
                            if window_id and window_id != "not_found":
                                # Found a terminal window to reuse
                                terminal_session_id = f"boardroom_persistent_{window_id}"
                                # Register this as the BoardRoom persistent terminal
                                self.__class__.boardroom_planning_terminal = terminal_session_id
                                logging.warning(f"🚨 DETECTED AND USING EXISTING TERMINAL WINDOW: {window_id} as {terminal_session_id}")
                        except Exception as e:
                            logging.error(f"Error searching for terminal windows: {str(e)}")
                    
                    # If we didn't find a window with AppleScript, fall back to our tracked sessions
                    if not terminal_session_id:
                        # If we already have a BoardRoom planning terminal, always use that
                        if hasattr(self.__class__, 'boardroom_planning_terminal'):
                            terminal_session_id = self.__class__.boardroom_planning_terminal
                            logging.warning(f"🚨 USING PERSISTENT BOARDROOM TERMINAL: {terminal_session_id}")
                        # Otherwise, use the provided session_id if given
                        elif parameters.get("session_id"):
                            terminal_session_id = parameters.get("session_id")
                            # Store this for future reference
                            self.__class__.boardroom_planning_terminal = terminal_session_id
                            logging.warning(f"🚨 SETTING NEW PERSISTENT BOARDROOM TERMINAL: {terminal_session_id}")
                        # If no session ID yet, create a unique persistent one
                        else:
                            terminal_session_id = f"boardroom_terminal_persistent_{int(time.time())}"
                            self.__class__.boardroom_planning_terminal = terminal_session_id
                            logging.warning(f"🚨 CREATING NEW PERSISTENT BOARDROOM TERMINAL: {terminal_session_id}")
                    
                    # If we already have a window for this session, we'll try to reuse it
                    reuse_existing_window = False
                    if hasattr(self.__class__, 'active_terminal_sessions') and terminal_session_id in self.__class__.active_terminal_sessions:
                        session_info = self.__class__.active_terminal_sessions[terminal_session_id]
                        window_id = session_info.get("window_id")
                        
                        if window_id and session_info.get("active", False):
                            # Check if window still exists and bring it to front
                            check_script = '''
                            tell application "Terminal"
                                set windowExists to false
                                try
                                    set w to (first window whose id is ''' + str(window_id) + ''')
                                    set windowExists to true
                                    # Bring this window to front for visibility and to ensure it's the active window
                                    set frontmost of w to true
                                    set visible of w to true
                                    activate
                                end try
                                return windowExists
                            end tell
                            '''
                            
                            # Check if the window still exists
                            try:
                                check_result = subprocess.run(["osascript", "-e", check_script], 
                                                          capture_output=True, text=True)
                                
                                if check_result.returncode == 0 and check_result.stdout.strip() == "true":
                                    # Window exists, reuse it
                                    logging.warning(f"🚨 FOUND EXISTING TERMINAL WINDOW WITH ID: {window_id}")
                                    reuse_existing_window = True
                                    # Create a shell script wrapper with better uniqueness
                                    random_suffix = os.urandom(4).hex()  # Add random suffix to prevent any conflicts
                                    temp_shell_script = f"/tmp/terminal_cmd_{int(time.time())}_{random_suffix}.sh"
                                    
                                    # Create a properly formatted shell script with clean environment
                                    with open(temp_shell_script, "w") as f:
                                        # Write a properly formatted script with commands on separate lines
                                        f.write("#!/bin/bash\n")
                                        f.write("# Exit immediately if a command exits with non-zero status\n")
                                        f.write("set -e\n\n")
                                        # Add session tracking header
                                        f.write(f"# Terminal session {terminal_session_id} - Command execution\n")
                                        f.write("# Change directory safely\n")
                                        f.write(f"cd {os.path.abspath(current_directory)}\n\n")
                                        # Clean the terminal and show header
                                        f.write("clear\n")
                                        f.write(f"echo 'Running command in session {terminal_session_id}...'\n\n")
                                        # Add the actual command with line break before/after
                                        f.write("# Execute command\n")
                                        f.write(f"{command}\n\n")
                                        # Add marker for completion
                                        f.write("echo '\\n[COMMAND_OUTPUT_COMPLETE]'\n")
                                    
                                    # Make the script executable
                                    os.chmod(temp_shell_script, 0o755)
                                    
                                    # Log shell script details for debugging
                                    logging.warning(f"🔹 TEMP SHELL SCRIPT PATH: {temp_shell_script}")
                                    logging.warning(f"🔹 SHELL SCRIPT EXISTS: {os.path.exists(temp_shell_script)}")
                                    
                                    # Escape the script path for AppleScript
                                    escaped_script_path = temp_shell_script.replace('"', '\\"').replace("'", "\\'")
                                    
                                    # Create a proper shell command to run
                                    shell_command = f"sh '{escaped_script_path}' && echo '[COMMAND_COMPLETE]'"
                                    logging.warning(f"🔹 SHELL COMMAND: {shell_command}")
                                    
                                    # When reusing a window, use a more reliable approach with isolation
                                    # Create a dedicated shell function to avoid command leakage
                                    isolated_command = f"'(function run_isolated() {{ {shell_command}; }}; run_isolated)'"
                                    
                                    terminal_script = '''
                                    tell application "Terminal"
                                        set w to (first window whose id is ''' + str(window_id) + ''')
                                        set current settings of w to settings set "Basic"
                                        set frontmost of w to true
                                        set visible of w to true
                                        
                                        -- Execute the shell command in an isolated subshell to prevent leakage
                                        do script ''' + isolated_command + ''' in w
                                        
                                        -- Activate terminal to bring it to front
                                        activate
                                    end tell
                                    '''
                                    
                                    # Log the isolated command for debugging
                                    logging.warning(f"🔹 ISOLATED COMMAND: {isolated_command}")
                            except Exception as e:
                                logging.error(f"Error checking window existence: {str(e)}")
                                reuse_existing_window = False
                    
                    # If window doesn't exist or check failed, we'll create a new one but keep the same session ID
                    if not reuse_existing_window:
                        logging.warning(f"🚨 EXISTING WINDOW NOT FOUND, CREATING NEW WINDOW FOR SESSION: {terminal_session_id}")
                else:
                    # Generate a new session ID for this terminal window
                    terminal_session_id = f"term_{int(time.time())}_{hash(escaped_command)}"
                
                # Store this as the last active terminal session
                if not hasattr(self.__class__, 'last_active_terminal'):
                    self.__class__.last_active_terminal = None
                
                # Execute the AppleScript to create the visible terminal or reuse existing one
                try:
                    # Check if we already have a window for this session that we can reuse
                    existing_window = False
                    if hasattr(self.__class__, 'active_terminal_sessions') and terminal_session_id in self.__class__.active_terminal_sessions:
                        session_info = self.__class__.active_terminal_sessions[terminal_session_id]
                        window_id = session_info.get("window_id")
                        
                        if window_id and session_info.get("active", False):
                            # Modify the script to use the existing window and bring it to front
                            check_script = '''
                            tell application "Terminal"
                                set windowExists to false
                                try
                                    set w to (first window whose id is ''' + str(window_id) + ''')
                                    set windowExists to true
                                    # Bring this window to front for visibility and to ensure it's the active window
                                    set frontmost of w to true
                                    set visible of w to true
                                    activate
                                end try
                                return windowExists
                            end tell
                            '''
                            
                            # Check if the window still exists
                            check_result = subprocess.run(["osascript", "-e", check_script], 
                                                        capture_output=True, text=True)
                            
                            if check_result.returncode == 0 and check_result.stdout.strip() == "true":
                                # Window exists, use it instead of creating a new one
                                logging.warning(f"🚨 REUSING EXISTING TERMINAL WINDOW WITH ID: {window_id}")
                                
                                # Create a shell script wrapper with better uniqueness
                                random_suffix = os.urandom(4).hex()  # Add random suffix to prevent any conflicts
                                temp_shell_script = f"/tmp/terminal_cmd_{int(time.time())}_{random_suffix}.sh"
                                
                                # Create a properly formatted shell script
                                with open(temp_shell_script, "w") as f:
                                    # Special handling for commands with quotes to avoid shell errors
                                    logging.warning(f"🚨 ORIGINAL REUSE COMMAND FOR QUOTE BALANCING: {command}")
                                    
                                    # Create a safer shell script that properly handles quotes
                                    # We'll escape all embedded quotes rather than trying to balance them
                                    clean_command = command
                                    clean_command = clean_command.replace("\\\"", "__ESCAPED_DOUBLE_QUOTE__")
                                    clean_command = clean_command.replace("\\'", "__ESCAPED_SINGLE_QUOTE__")
                                    clean_command = clean_command.replace("\"", "\\\"")
                                    clean_command = clean_command.replace("'", "\\'")
                                    clean_command = clean_command.replace("__ESCAPED_DOUBLE_QUOTE__", "\\\"")
                                    clean_command = clean_command.replace("__ESCAPED_SINGLE_QUOTE__", "\\'")
                                    
                                    # Remove any trailing backslashes that could cause shell errors
                                    if clean_command.endswith("\\"):
                                        clean_command = clean_command[:-1]
                                        logging.warning("🚨 REMOVED TRAILING BACKSLASH FROM REUSE COMMAND")
                                    
                                    # Verify the command doesn't have obvious syntax errors
                                    if clean_command.count("$(") != clean_command.count(")"):
                                        # Unbalanced command substitution, add closing parenthesis
                                        clean_command += ")"
                                        logging.warning("🚨 FIXED UNBALANCED COMMAND SUBSTITUTION IN REUSE COMMAND")
                                    
                                    # Log the cleaned command for debugging
                                    logging.warning(f"🚨 CLEANED REUSE COMMAND WITH ESCAPED QUOTES: {clean_command}")
                                    
                                    # Write a properly formatted script with commands on separate lines
                                    f.write("#!/bin/bash\n")
                                    f.write("set -e\n\n")
                                    # Use safe path handling
                                    f.write("# Change to directory using safer path handling\n")
                                    f.write(f"cd {os.path.abspath(current_directory)}\n\n")
                                    # Add comments to help debug
                                    f.write("# Execute command\n")
                                    f.write(f"{clean_command}\n\n")
                                    # Add marker for completion
                                    f.write("echo '\\n[COMMAND_OUTPUT_COMPLETE]'\n")
                                    # Self-cleanup to remove the script after execution
                                    f.write(f"\n# Self-cleanup\n[ -f \"{temp_shell_script}\" ] && rm \"{temp_shell_script}\" || true\n")
                                
                                # Make the script executable
                                os.chmod(temp_shell_script, 0o755)
                                
                                # Log the shell script path for debugging
                                logging.warning(f"🔹 TEMP SHELL SCRIPT PATH: {temp_shell_script}")
                                
                                # Escape the script path for AppleScript
                                escaped_script_path = temp_shell_script.replace('"', '\\"').replace("'", "\\'")
                                
                                # Create a proper shell command to run
                                shell_command = f"sh '{escaped_script_path}' && echo '[COMMAND_COMPLETE]'"
                                logging.warning(f"🔹 SHELL COMMAND: {shell_command}")
                                
                                # When reusing a window, use a more reliable approach with isolation
                                # Create a dedicated shell function to avoid command leakage - properly escaped for AppleScript
                                # Note: we use double quotes for the AppleScript string and escape inner quotes properly
                                isolated_command = f"\"bash -c \\\"(function run_isolated() {{ {shell_command}; }}; run_isolated)\\\"\""
                                
                                # COMPLETELY BYPASS TERMINAL WINDOW REUSE FOR SAFETY
                                # Instead of reusing a terminal window, we'll just execute the command directly
                                logging.warning("🔹 BYPASSING TERMINAL WINDOW REUSE AND USING DIRECT EXECUTION INSTEAD")
                                
                                # Execute the command directly
                                try:
                                    # First make sure the shell script exists and is executable
                                    if not os.path.exists(temp_shell_script):
                                        logging.error(f"Shell script does not exist: {temp_shell_script}")
                                        raise FileNotFoundError(f"Shell script not found: {temp_shell_script}")
                                    
                                    # Make it executable
                                    os.chmod(temp_shell_script, 0o755)
                                    
                                    # Execute the shell script directly without any terminal window
                                    direct_result = subprocess.run(f"sh '{temp_shell_script}'", shell=True, 
                                                                capture_output=True, text=True, timeout=timeout)
                                    
                                    # Log the direct execution result
                                    logging.warning(f"🔹 DIRECT EXECUTION RESULT: {direct_result.returncode}")
                                    logging.warning(f"🔹 DIRECT EXECUTION STDOUT: {direct_result.stdout[:100]}")
                                    
                                    # Store the direct execution result for returning later
                                    direct_execution_result = direct_result
                                    
                                    # Clean up the shell script
                                    try:
                                        if os.path.exists(temp_shell_script):
                                            os.remove(temp_shell_script)
                                            logging.warning(f"🔹 REMOVED SHELL SCRIPT: {temp_shell_script}")
                                        else:
                                            logging.warning(f"🔹 SHELL SCRIPT NOT FOUND (already removed): {temp_shell_script}")
                                    except Exception as e:
                                        logging.error(f"Error removing shell script: {str(e)}")
                                    
                                    # Create a fake reuse script to maintain compatibility with the rest of the code
                                    reuse_script = f"echo 'Direct execution mode - no terminal window'"
                                    
                                except Exception as e:
                                    logging.error(f"Error in direct execution: {str(e)}")
                                    # Create a fake reuse script to maintain compatibility
                                    reuse_script = f"echo 'Direct execution failed: {str(e)}'"
                                
                                # Log the isolated command for debugging
                                logging.warning(f"🔹 ISOLATED COMMAND: {isolated_command}")
                                
                                # Use this script for the terminal 
                                terminal_script = reuse_script
                                
                                # Update session info with latest timestamp
                                session_info["last_used"] = time.time()
                                existing_window = True
                    
                    # In our new approach, we've already executed the script directly
                    logging.warning(f"[TERMINAL_WINDOW] Skipping wrapper script execution - using direct result instead")
                    
                    # Use the direct execution result that we already have
                    try:
                        # Create a fake applescript_result to maintain compatibility
                        applescript_result = type('obj', (object,), {
                            'returncode': direct_execution_result.returncode,
                            'stdout': direct_execution_result.stdout,
                            'stderr': direct_execution_result.stderr
                        })
                        logging.warning(f"[TERMINAL_WINDOW] Created synthetic applescript_result from direct execution")
                    except Exception as e:
                        logging.error(f"Error creating synthetic result: {str(e)}")
                        # Create empty result as fallback
                        applescript_result = type('obj', (object,), {
                            'returncode': 0,
                            'stdout': '',
                            'stderr': f"Error creating result: {str(e)}"
                        })
                    
                    # Now remove the temp_script_path that is no longer needed
                    # Cleanup is now handled in the shell script itself automatically
                    logging.warning(f"🚨 VISIBLE TERMINAL CREATION RESULT: {applescript_result.returncode}")
                    
                    # Store the terminal session info for potential reuse/cleanup
                    if applescript_result.returncode == 0:
                        if not hasattr(self.__class__, 'active_terminal_sessions'):
                            self.__class__.active_terminal_sessions = {}
                        
                        # Get the terminal window ID if possible
                        window_id = None
                        if applescript_result.stdout:
                            try:
                                # Look for window ID in output
                                if "window id" in applescript_result.stdout:
                                    window_id = applescript_result.stdout.strip()
                                # If no window ID in output, try to get it directly
                                else:
                                    # Write AppleScript to get active window ID
                                    get_id_script = '''
                                    tell application "Terminal"
                                        id of front window
                                    end tell
                                    '''
                                    id_script_path = f"/tmp/get_window_id_{int(time.time())}_{os.getpid()}.scpt"
                                    with open(id_script_path, "w") as f:
                                        f.write(get_id_script)
                                    id_result = subprocess.run(["osascript", id_script_path], 
                                                            capture_output=True, text=True)
                                    if id_result.returncode == 0 and id_result.stdout.strip():
                                        window_id = id_result.stdout.strip()
                                        logging.warning(f"🚨 OBTAINED WINDOW ID: {window_id} from front window query")
                                    # Clean up temp script
                                    try:
                                        if os.path.exists(id_script_path):
                                            os.remove(id_script_path)
                                        else:
                                            logging.debug(f"ID script already removed: {id_script_path}")
                                    except Exception as e:
                                        logging.debug(f"Error removing ID script: {str(e)}")
                                        pass
                            except Exception as e:
                                logging.error(f"Error getting window ID: {str(e)}")
                                pass
                        
                        # Determine if this is a Claude Code terminal or direct terminal command
                        is_claude_code = use_claude_window or "claude " in command
                        
                        # Store session info
                        self.__class__.active_terminal_sessions[terminal_session_id] = {
                            "command": command,
                            "window_id": window_id,
                            "created_at": time.time(),
                            "directory": current_directory,
                            "active": True,
                            "is_claude_code": is_claude_code,
                            "keep_open": is_claude_code or parameters.get("keep_terminal_open", False) or parameters.get("boardroom_planning_session", False),
                            "terminal_type": "claude_code" if is_claude_code else "boardroom_terminal" if parameters.get("boardroom_planning_session", False) else "direct_command",
                            # Enhanced window type tracking for improved detection and separation
                            "window_type": parameters.get("window_type") or (
                                self.WINDOW_TYPE_CLAUDE_CODE if is_claude_code else 
                                self.WINDOW_TYPE_DIRECT_TERMINAL if not is_from_boardroom else 
                                self.WINDOW_TYPE_TERMINAL
                            ),
                            # Add flags to prevent window hijacking
                            "never_reuse": parameters.get("never_reuse", False),
                            "force_new_window": parameters.get("force_new_window", False)
                        }
                        
                        # If this is a boardroom planning session, update the global terminal reference
                        if parameters.get("boardroom_planning_session", False) and window_id:
                            # Set this as the persistent terminal for all future boardroom commands
                            self.__class__.boardroom_planning_terminal = terminal_session_id
                            logging.warning(f"🚨 UPDATED BOARDROOM PLANNING TERMINAL: {terminal_session_id} with window ID: {window_id}")
                        
                        # Update the last active terminal reference
                        self.__class__.last_active_terminal = terminal_session_id
                        logging.warning(f"🚨 STORED TERMINAL SESSION: {terminal_session_id}, Type: {'Claude Code' if is_claude_code else 'Direct Command'}")
                    
                    if applescript_result.returncode != 0:
                        logging.error(f"AppleScript error: {applescript_result.stderr}")
                    
                    # Print more verbose information about the script execution
                    print(f"🚨 APPLESCRIPT STDOUT: {applescript_result.stdout[:100]}...")
                    print(f"🚨 APPLESCRIPT STDERR: {applescript_result.stderr[:100]}...")
                    
                    # Wait a moment for the command to start executing in the visible terminal
                    time.sleep(2)
                    
                    # Still use the direct command execution to capture the output reliably
                    result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=timeout)
                except Exception as terminal_error:
                    logging.error(f"Error creating visible terminal: {str(terminal_error)}")
                    traceback.print_exc()  # Print full stack trace for debugging
                    # Fall back to direct execution
                    result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=timeout)
            else:
                # Standard execution without a visible terminal
                result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=timeout)
            
            # Log the result to help with debugging
            logging.warning(f"COMMAND RESULT: exitcode={result.returncode}, stdout_len={len(result.stdout)}, stderr_len={len(result.stderr)}")
            print(f"🚨 Exit code: {result.returncode}")
            print(f"🚨 Stdout: {result.stdout}")
            if result.stderr:
                print(f"🚨 Stderr: {result.stderr}")
            
            # Restore original directory if changed
            if current_dir:
                os.chdir(current_dir)
                
            # Track the command in history
            self.command_history.append({
                "command": command,
                "directory": directory,
                "output": result.stdout,
                "return_code": result.returncode,
                "timestamp": time.time()
            })
            
            # Update metrics
            self.metrics["commands_executed"] += 1
            
            # Notify orchestrator agent if available - CRITICAL for BoardRoom integration
            if self.orchestrator:
                try:
                    # Prepare result data with comprehensive information
                    result_data = {
                        "success": result.returncode == 0,
                        "output": result.stdout,
                        "return_code": result.returncode,
                        "error": result.stderr if result.returncode != 0 else None,
                        "command": command,
                        "execution_time": time.time(),
                        "is_terminal_command": True  # Flag this as a terminal command for proper routing
                    }
                    
                    # Log the notification being sent - important for debugging
                    logging.warning(f"SENDING COMMAND COMPLETION TO ORCHESTRATOR: cmd={command[:30]}...")
                    print(f"🚨 NOTIFYING ORCHESTRATOR: Terminal command completed")
                    print(f"🚨 COMMAND: {command[:50]}...")
                    print(f"🚨 RESULT: success={result_data['success']}, return_code={result_data['return_code']}")
                    
                    # Make sure BoardRoom tracking interface is notified - try multiple paths
                    try:
                        if hasattr(self, 'boardroom') and self.boardroom:
                            logging.warning("Using direct BoardRoom notification path")
                            # Try to notify BoardRoom directly
                            # Use track_journey_step_sync instead of track_request_journey_sync
                            from Jarvis_Agent_SDK.boardroom_connector import track_journey_step_sync
                            track_journey_step_sync(
                                journey_id=f"terminal_cmd_{int(time.time())}",
                                step_type="execution",
                                step_name="terminal_command_completed",
                                description=f"Terminal command completed: {command[:50]}...",
                                status="completed",
                                metadata=result_data
                            )
                    except Exception as e:
                        logging.error(f"Error in direct BoardRoom notification: {str(e)}")
                    
                    # Create a coroutine without awaiting it - we don't want to block
                    notification_coroutine = self.orchestrator.notify_command_execution(
                        command=command,
                        result=result_data
                    )
                    
                    # Schedule the coroutine to run in the background
                    try:
                        asyncio.create_task(notification_coroutine)
                    except RuntimeError:
                        # We're not in an event loop, try alternative execution
                        try:
                            # Create a new event loop for this notification
                            loop = asyncio.new_event_loop()
                            asyncio.set_event_loop(loop)
                            loop.run_until_complete(notification_coroutine)
                            loop.close()
                            logging.warning("Used new event loop for orchestrator notification")
                        except Exception as e2:
                            logging.error(f"Could not create event loop: {str(e2)}")
                except Exception as e:
                    # Don't let notification errors affect the result
                    logging.error(f"Error notifying orchestrator: {str(e)}")
                    print(f"🚨 ERROR NOTIFYING ORCHESTRATOR: {str(e)}")
            
            # For direct terminal commands (not Claude Code), schedule a delayed terminal closure
            # Only after results have been sent to the orchestrator
            if is_terminal_command and not use_claude_window and not parameters.get("keep_terminal_open", False):
                # Don't close BoardRoom planning terminals until the entire planning session is complete
                is_boardroom_planning = parameters.get("boardroom_planning_session", False)
                
                if is_boardroom_planning:
                    # This is a BoardRoom planning session - always keep it open
                    logging.warning(f"🚨 Keeping BoardRoom planning terminal session {terminal_session_id} open for continued use")
                    
                    # Ensure we have this set as our persistent terminal
                    if not hasattr(self.__class__, 'boardroom_planning_terminal'):
                        self.__class__.boardroom_planning_terminal = terminal_session_id
                        logging.warning(f"🚨 SETTING BOARDROOM PLANNING TERMINAL: {terminal_session_id}")
                    
                    # Mark the last command time so we can close it when inactive for too long
                    if hasattr(self.__class__, 'active_terminal_sessions') and terminal_session_id in self.__class__.active_terminal_sessions:
                        self.__class__.active_terminal_sessions[terminal_session_id]["last_used"] = time.time()
                        
                        # Make sure window_id is properly tracked if we have it
                        if "window_id" in locals() and window_id:
                            self.__class__.active_terminal_sessions[terminal_session_id]["window_id"] = window_id
                            logging.warning(f"🚨 UPDATED WINDOW ID for BoardRoom terminal: {window_id}")
                else:
                    # Schedule terminal window closure with delay to ensure BoardRoom receives output
                    if hasattr(self.__class__, 'active_terminal_sessions') and terminal_session_id in self.__class__.active_terminal_sessions:
                        session_info = self.__class__.active_terminal_sessions[terminal_session_id]
                        session_info["close_after_result"] = True
                        session_info["close_after_time"] = time.time() + 10  # Wait 10 seconds
                        logging.warning(f"🚨 Terminal session {terminal_session_id} marked for delayed closure")
                        
                        # Start a background thread to close the terminal after delay
                        import threading
                        closure_thread = threading.Thread(
                            target=self._delayed_terminal_closure,
                            args=(terminal_session_id, 10),
                            daemon=True
                        )
                        closure_thread.start()
                    logging.warning(f"🚨 Started delayed terminal closure thread for session {terminal_session_id}")
            
            # Return success or failure based on return code
            if result.returncode == 0:
                # Store file content in cache if this was a file viewing command
                if is_file_viewing_command and file_path and os.path.exists(file_path):
                    # Initialize cache if it doesn't exist
                    if not hasattr(self.__class__, 'file_content_cache'):
                        self.__class__.file_content_cache = {}
                    
                    # Get absolute path for more reliable caching
                    abs_file_path = os.path.abspath(file_path)
                    
                    # Store the file content in the cache with a timestamp
                    self.__class__.file_content_cache[abs_file_path] = (result.stdout, time.time())
                    logging.warning(f"📄 STORED FILE CONTENT IN CACHE: {abs_file_path}")
                
                return HandlerResult(success=True, data=result.stdout)
            else:
                return HandlerResult(
                    success=False,
                    error=f"Command exited with code {result.returncode}",
                    details={"stderr": result.stderr, "stdout": result.stdout}
                )
        except subprocess.TimeoutExpired:
            return HandlerResult(success=False, error=f"Command timed out after {timeout} seconds")
        except Exception as e:
            return HandlerResult(success=False, error=str(e))
            
    def _execute_command(self, parameters: Dict[str, Any]) -> HandlerResult:
        """Legacy method for backward compatibility."""
        return self.execute_command(parameters)
        
    def _get_normalized_command(self, command):
        """
        Normalize a terminal command to improve cache hit rates.
        
        This function standardizes commands by:
        1. Removing extra spaces
        2. Extracting core command parts (command and key arguments)
        3. Removing trailing natural language
        4. Truncating commands at newlines, which typically separate commands from explanations
        
        Note: This function handles most common command patterns, but some edge cases
        might still create slightly different normalizations. The goal is to significantly
        improve cache hit rates while maintaining command functionality.
        
        Args:
            command (str): The original terminal command
            
        Returns:
            str: Normalized command for consistent cache keys
        """
        import re
        
        if not command:
            return command
            
        # First, check for newlines and truncate at the first newline
        # This is critical for bidirectional communication where LLMs often
        # add explanations or follow-up queries after commands
        if "\n" in command:
            command = command.split("\n")[0]
            
        # Trim whitespace after handling newlines
        normalized = command.strip()
        
        # First, handle quoted strings to preserve them
        quoted_parts = {}
        quote_pattern = r'([\'"])(.*?)\1'
        
        def replace_quotes(match):
            placeholder = f"__QUOTE_{len(quoted_parts)}__"
            quoted_parts[placeholder] = match.group(0)
            return placeholder
            
        # Replace quotes with placeholders temporarily
        normalized = re.sub(quote_pattern, replace_quotes, normalized)
        
        # Collapse all whitespace to single spaces
        normalized = re.sub(r'\s+', ' ', normalized)
        
        # Remove natural language terminators before trying to match patterns
        terminators = [
            " so that ", " to find ", " and then ", " that contain ", 
            " with the content ", " to show ", " to see ", " please ", " i need ",
            " which ", " where ", " when "
        ]
        
        for term in terminators:
            pos = normalized.lower().find(term)
            if pos > 0:
                normalized = normalized[:pos]
        
        # Identify common commands that need special handling
        common_commands = {
            "find": r"find\s+([\w./]+)\s+(-name\s+__QUOTE_\d+__|-type\s+[fdlcb])",
            "grep": r"grep(\s+(?:-[EFGPir]+)?)?(\s+(?:__QUOTE_\d+__|[\w.-]+))?(\s+(?:[\w./\*]+))?",
            "ls": r"ls\s+(-[altrRh]+)(?:\s+([\w./]+))?",
            "cat": r"cat\s+([\w./]+)",
            "git": r"git\s+(status|log|diff|show|commit|branch|checkout|pull|push)",
            "docker": r"docker\s+(ps|images|container\s+ls|run|exec)",
            "ps": r"ps\s+(-[aefwux]+)"
        }
        
        # Try to match and normalize based on command type
        command_matched = False
        for cmd_prefix, pattern in common_commands.items():
            if normalized.startswith(cmd_prefix + " "):
                # Special case for grep because of its complexity
                if cmd_prefix == "grep":
                    # Just extract the command up to any natural language
                    parts = normalized.split()
                    # Keep up to 3 parts for grep (grep + pattern + file)
                    if len(parts) >= 3:
                        # Check if first part after grep is an option
                        if parts[1].startswith('-'):
                            # grep -option pattern file
                            if len(parts) >= 4:
                                normalized = f"{parts[0]} {parts[1]} {parts[2]} {parts[3]}"
                            else:
                                normalized = f"{parts[0]} {parts[1]} {parts[2]}"
                        else:
                            # grep pattern file
                            normalized = f"{parts[0]} {parts[1]} {parts[2]}"
                    elif len(parts) == 2:
                        normalized = f"{parts[0]} {parts[1]}"
                    else:
                        normalized = parts[0]
                    command_matched = True
                    break
                
                # For other commands, use regex pattern matching
                match = re.search(pattern, normalized)
                if match:
                    # Extract just the core components of the command
                    groups = [g for g in match.groups() if g]
                    core_parts = [cmd_prefix] + groups
                    normalized = " ".join(core_parts)
                    command_matched = True
                    break
        
        # Handle some common command structures even if no specific pattern matched
        if not command_matched:
            # Split by common pipe and redirection operators
            parts = re.split(r'\s*[|><&]\s*', normalized)
            if len(parts) > 1:
                # Just use the first part of piped/redirected commands
                normalized = parts[0].strip()
        
        # Restore quoted parts
        for placeholder, original in quoted_parts.items():
            normalized = normalized.replace(placeholder, original)
        
        return normalized
        
    def _are_command_types_equivalent(self, cmd1, cmd2):
        """
        Determine if two commands are semantically equivalent for caching purposes.
        
        This helps reduce redundant commands in BoardRoom sessions by identifying
        commands that perform the same basic operation with different parameters.
        
        Args:
            cmd1 (str): First command to compare
            cmd2 (str): Second command to compare
            
        Returns:
            bool: True if commands are semantically equivalent
        """
        if cmd1 == cmd2:
            return True
            
        # Extract the base command (first word)
        base1 = cmd1.split(' ')[0].lower() if cmd1 else ""
        base2 = cmd2.split(' ')[0].lower() if cmd2 else ""
        
        # Commands must be of same type
        if base1 != base2:
            return False
            
        base_cmd = base1
        
        # Rules for different command types
        if base_cmd in ['ls', 'dir']:
            # List commands with different options on the same directory
            # Or list commands on different directories but with same options
            # are considered equivalent for BoardRoom planning sessions
            return True
            
        if base_cmd in ['grep', 'find']:
            # Extract the search pattern if quoted
            import re
            
            pattern1 = None
            pattern2 = None
            
            # Look for a quoted pattern in each command
            quote_pattern = r'"([^"]+)"'
            
            m1 = re.search(quote_pattern, cmd1)
            m2 = re.search(quote_pattern, cmd2)
            
            if m1 and m2:
                pattern1 = m1.group(1)
                pattern2 = m2.group(1)
                
                # If same search pattern, consider them equivalent
                if pattern1 == pattern2:
                    return True
            
            # If both looking at same file types (e.g., *.py files)
            if '*.py' in cmd1 and '*.py' in cmd2:
                return True
                
            # If both looking at same directory structure
            if '~/Jarvis/' in cmd1 and '~/Jarvis/' in cmd2:
                return True
                
        if base_cmd in ['cat', 'head', 'tail', 'less']:
            # File viewing commands on similar files are equivalent
            # Extract the file path(s)
            parts1 = cmd1.split()
            parts2 = cmd2.split()
            
            # If looking at files with similar extensions
            if len(parts1) > 1 and len(parts2) > 1:
                file1 = parts1[-1]
                file2 = parts2[-1]
                
                # Get file extensions if any
                ext1 = file1.split('.')[-1] if '.' in file1 else ''
                ext2 = file2.split('.')[-1] if '.' in file2 else ''
                
                # If same file extension, consider them equivalent
                if ext1 and ext1 == ext2:
                    return True
                    
                # If both in the same directory
                dir1 = '/'.join(file1.split('/')[:-1])
                dir2 = '/'.join(file2.split('/')[:-1])
                
                if dir1 and dir1 == dir2:
                    return True
                    
        # By default, not equivalent
        return False
        
    def execute_with_venv(self, parameters: Dict[str, Any]) -> HandlerResult:
        """
        Execute a command with virtual environment activation.
        
        This method automatically activates the virtual environment before executing
        the command, ensuring Python commands have access to the correct dependencies.
        
        Args:
            parameters: Dictionary containing:
                - command: The command to execute
                - venv_path: Path to the virtual environment (defaults to ~/myenv)
                - directory: Optional directory to execute the command in
                - timeout: Optional timeout in seconds
                
        Returns:
            HandlerResult with the command output if successful
        """
        command = parameters.get("command")
        venv_path = parameters.get("venv_path", "~/myenv")
        directory = parameters.get("directory")
        timeout = parameters.get("timeout", 30)
        
        if not command:
            return HandlerResult(success=False, error="No command provided")
            
        # Construct the command with venv activation
        activate_cmd = f"source {venv_path}/bin/activate && {command}"
        
        # Execute the command with virtual environment activation
        return self.execute_command({
            "command": activate_cmd,
            "directory": directory,
            "timeout": timeout
        })
        
    def analyze_codebase(self, parameters: Dict[str, Any]) -> HandlerResult:
        """
        Analyze a codebase to understand its structure using Claude Code.
        
        This method launches Claude Code in a terminal window to analyze the codebase
        structure, leveraging Claude's advanced capabilities for understanding and
        examining code structures.
        
        Args:
            parameters: Dictionary containing:
                - directory: Optional directory to analyze (default: current directory)
                - file_types: Optional list of file types to include in analysis (e.g. ["*.py", "*.js"])
                - recursive: Optional whether to search recursively (default: True)
                - include_stats: Optional whether to include detailed stats (default: True)
                - prompt: Optional specific prompt for Claude Code (if not provided, a default one is used)
                - interactive: Whether to maintain an interactive session (default: True)
                
        Returns:
            HandlerResult with the Claude Code analysis results and session information for further interaction
        """
        directory = parameters.get("directory", "~/Jarvis")
        file_types = parameters.get("file_types", ["*"])
        custom_prompt = parameters.get("prompt", "")
        interactive = parameters.get("interactive", True)
        
        try:
            # Build the prompt for Claude Code
            file_types_str = ", ".join(file_types) if isinstance(file_types, list) else file_types
            
            if not custom_prompt:
                # Create a default prompt for codebase analysis
                prompt = f"""Analyze this codebase to understand its structure:
                
                1. Identify main file types and count files by type
                2. Identify key directories and their purposes
                3. Determine the project architecture
                4. Identify main entry points and important files
                5. Look for patterns in the code organization
                6. Focus on {file_types_str} files
                
                Provide a comprehensive structural overview that would help someone 
                understand how to navigate and work with this codebase effectively.
                """
            else:
                prompt = custom_prompt
            
            # Use execute_claude_code to run the analysis
            claude_code_params = {
                "prompt": prompt,
                "directory": directory,
                "verbose": True,
                "monitor_output": True,  # Enable output monitoring for interactive sessions
                "timeout": 120,  # Longer timeout for codebase analysis
                "interactive": interactive,  # Enable interactive mode for continued conversation
                "reuse_session": False  # Start a fresh session for analysis
            }
            
            # Launch Claude Code in a terminal window
            result = self.execute_claude_code(claude_code_params)
            
            # If successful and interactive, return session info for continued interaction
            if result.success and interactive and hasattr(result, 'details') and 'session_id' in result.details:
                # Make sure we return the session ID for future interactions
                if 'details' not in result.__dict__:
                    result.details = {}
                    
                result.details.update({
                    "interactive": True,
                    "session_active": True,
                    "message": "Claude Code session is active for continued interaction. Use send_claude_input to continue the conversation."
                })
            
            return result
            
        except Exception as e:
            return HandlerResult(success=False, error=f"Error analyzing codebase with Claude Code: {str(e)}")
        
    def send_claude_input(self, parameters: Dict[str, Any]) -> HandlerResult:
        """
        Send input to an active Claude Code session.
        
        This method allows for interactive communication with an already running
        Claude Code terminal session, enabling multi-turn conversations.
        
        Args:
            parameters: Dictionary containing:
                - session_id: ID of the active Claude Code session
                - input: Text to send to Claude Code
                - wait_for_response: Whether to wait for and return Claude's response (default: True)
                - timeout: Maximum time to wait for response in seconds (default: 30)
                
        Returns:
            HandlerResult with Claude's response if wait_for_response is True
        """
        session_id = parameters.get("session_id")
        user_input = parameters.get("input")
        wait_for_response = parameters.get("wait_for_response", True)
        timeout = parameters.get("timeout", 30)
        
        if not session_id:
            return HandlerResult(success=False, error="Missing session_id for Claude Code interaction")
            
        if not user_input:
            return HandlerResult(success=False, error="No input provided to send to Claude Code")
            
        try:
            # Check if the session exists
            if not hasattr(self.__class__, 'active_claude_sessions') or session_id not in self.__class__.active_claude_sessions:
                # Try to find the session by searching for Claude terminal windows
                try:
                    # Use AppleScript to find terminal windows with Claude in title
                    find_claude_window_script = '''
                    tell application "Terminal"
                        set windowList to {}
                        repeat with w in windows
                            if name of w contains "Claude" then
                                set windowList to windowList & {id of w}
                            end if
                        end repeat
                        return windowList
                    end tell
                    '''
                    
                    window_cmd = ['osascript', '-e', find_claude_window_script]
                    window_result = subprocess.run(window_cmd, check=True, capture_output=True, text=True)
                    
                    if window_result.stdout.strip():
                        # Found a Claude window, create a session for it
                        window_id = window_result.stdout.strip().split(',')[0]
                        logging.warning(f"Found existing Claude window {window_id} - creating session dynamically")
                        
                        # Create a new session entry
                        new_session_id = f"claude_auto_{int(time.time())}"
                        self.__class__.active_claude_sessions[new_session_id] = {
                            "terminal_window": window_id,
                            "active": True,
                            "created_at": time.time(),
                            "last_used": time.time(),
                            "auto_detected": True
                        }
                        
                        # Use the new session
                        session_id = new_session_id
                    else:
                        # No Claude window found
                        return HandlerResult(success=False, error=f"No active Claude Code sessions found")
                except Exception as window_error:
                    logging.error(f"Error finding Claude windows: {str(window_error)}")
                    return HandlerResult(success=False, error=f"Claude Code session {session_id} not found or expired")
            
            # Get session info
            session_info = self.__class__.active_claude_sessions[session_id]
            
            # Check if the session is still active
            if not session_info.get("active", False):
                return HandlerResult(success=False, error=f"Claude Code session {session_id} is no longer active")
                
            # Get terminal window ID - either from session or directly from parameter
            terminal_window = session_info.get("terminal_window") or parameters.get("terminal_window")
            if not terminal_window:
                # Try to find the window by bringing Terminal to front
                try:
                    # Use AppleScript to find active window
                    find_window_script = '''
                    tell application "Terminal"
                        activate
                        delay 0.5
                        id of front window
                    end tell
                    '''
                    
                    window_cmd = ['osascript', '-e', find_window_script]
                    window_result = subprocess.run(window_cmd, check=True, capture_output=True, text=True)
                    
                    if window_result.stdout.strip():
                        terminal_window = window_result.stdout.strip()
                        # Update session info
                        session_info["terminal_window"] = terminal_window
                    else:
                        return HandlerResult(success=False, error=f"Cannot find terminal window for Claude Code")
                except Exception as find_error:
                    logging.error(f"Error finding terminal window: {str(find_error)}")
                    return HandlerResult(success=False, error=f"Cannot find terminal window for Claude Code session {session_id}")
            
            # Escape the input for AppleScript
            escaped_input = user_input.replace('"', '\\"').replace("'", "\\'")
            
            # Enhanced logging for debugging
            logging.warning(f"🔶 SENDING INPUT TO CLAUDE: '{user_input[:50]}...' to window ID {terminal_window}")
            print(f"🔶 SENDING INPUT TO CLAUDE: '{user_input[:50]}...' to window ID {terminal_window}")
            
            # Create AppleScript to send input and optionally get response
            # This version uses a more robust approach to focus the window and ensure keystrokes are sent
            applescript = '''
            tell application "Terminal"
                activate
                set targetWindow to window id ''' + str(terminal_window) + '''
                
                -- Bring window to front to ensure it receives input
                set frontmost of targetWindow to true
                set visible of targetWindow to true
                set index of targetWindow to 1  -- Bring to front
                delay 0.5
                
                -- Send the input followed by return key to submit it
                tell application "System Events"
                    tell process "Terminal"
                        -- First click in the terminal to ensure focus
                        click at {500, 500}
                        delay 0.2
                        
                        -- Now type the text
                        keystroke "{escaped_input}"
                        delay 0.2
                        keystroke return
                    end tell
                end tell
            end tell
            '''
            
            # Execute the AppleScript
            cmd = ['osascript', '-e', applescript]
            input_result = subprocess.run(cmd, check=True, capture_output=True, text=True)
            
            # Log the result for debugging
            logging.warning(f"🔶 INPUT SENT RESULT: {input_result.returncode}")
            
            # Update last used timestamp
            session_info["last_used"] = time.time()
            
            if wait_for_response:
                # Wait for Claude's response to appear
                # This is a simplified approach - in a real implementation,
                # you would need a more sophisticated way to detect when Claude has finished responding
                import time
                time.sleep(3)  # Give Claude some time to process and respond
                
                # Execute AppleScript to get the terminal output
                response_script = '''
                tell application "Terminal"
                    set targetWindow to window id ''' + str(terminal_window) + '''
                    
                    -- Make sure window is visible
                    set visible of targetWindow to true
                    
                    -- Get visible contents of terminal window
                    contents of targetWindow
                end tell
                '''
                
                # Run the script to get terminal contents
                response_cmd = ['osascript', '-e', response_script]
                result = subprocess.run(response_cmd, check=True, capture_output=True, text=True)
                
                # Extract Claude's response from the terminal output
                claude_response = result.stdout
                
                logging.warning(f"🔶 CLAUDE RESPONSE RECEIVED: {len(claude_response)} characters")
                
                return HandlerResult(
                    success=True,
                    result="Input sent successfully to Claude Code",
                    details={
                        "session_id": session_id,
                        "terminal_window": terminal_window,
                        "response": claude_response,
                        "session_active": True
                    }
                )
            else:
                # Just return success without waiting for response
                return HandlerResult(
                    success=True,
                    result="Input sent successfully to Claude Code",
                    details={
                        "session_id": session_id,
                        "terminal_window": terminal_window,
                        "session_active": True
                    }
                )
        except Exception as e:
            logging.error(f"Error sending input to Claude Code: {str(e)}")
            logging.error(traceback.format_exc())
            return HandlerResult(success=False, error=f"Error sending input to Claude Code: {str(e)}")
        
    def run_script(self, parameters: Dict[str, Any]) -> HandlerResult:
        """
        Run a script file in the terminal.
        
        Args:
            parameters: Dictionary containing:
                - file_path: Path to the script file
                - arguments: Optional arguments to pass to the script
                - directory: Optional directory to run the script in
                
        Returns:
            HandlerResult with the script output if successful
        """
        file_path = parameters.get("file_path")
        arguments = parameters.get("arguments", "")
        directory = parameters.get("directory")
        
        if not file_path:
            return HandlerResult(success=False, error="No file path provided")
            
        try:
            # Check if the file exists
            if not os.path.exists(file_path):
                return HandlerResult(success=False, error=f"Script file not found: {file_path}")
                
            # Determine the script interpreter based on the file extension
            if file_path.endswith(".py"):
                command = f"python {file_path} {arguments}"
            elif file_path.endswith(".sh"):
                command = f"bash {file_path} {arguments}"
            elif file_path.endswith(".js"):
                command = f"node {file_path} {arguments}"
            elif file_path.endswith(".rb"):
                command = f"ruby {file_path} {arguments}"
            else:
                # Try to determine if it's executable
                if os.access(file_path, os.X_OK):
                    command = f"{file_path} {arguments}"
                else:
                    return HandlerResult(success=False, error=f"Unknown script type: {file_path}")
            
            # Execute the command
            return self.execute_command({
                "command": command,
                "directory": directory,
                "timeout": parameters.get("timeout", 60)
            })
        except Exception as e:
            return HandlerResult(success=False, error=f"Error running script: {str(e)}")

    def create_file(self, parameters: Dict[str, Any]) -> HandlerResult:
        """Create a file with specified content."""
        file_path = parameters.get("file_path")
        content = parameters.get("content", "")
        
        if not file_path:
            return HandlerResult(success=False, error="No file path provided")
            
        try:
            with open(file_path, "w") as f:
                f.write(content)
            return HandlerResult(success=True)
        except Exception as e:
            return HandlerResult(success=False, error=str(e))
            
    def _create_file(self, parameters: Dict[str, Any]) -> HandlerResult:
        """Legacy method for backward compatibility."""
        return self.create_file(parameters)
        
    def search_and_replace(self, parameters: Dict[str, Any]) -> HandlerResult:
        """
        Search for a pattern in a file and replace it with new content.
        
        Args:
            parameters: Dictionary containing:
                - file_path: Path to the file to modify
                - search_pattern: Pattern to search for
                - replacement: Content to replace the pattern with
                - regex: Optional whether to use regex matching (default: False)
                - count: Optional max number of replacements to make (default: all)
                - create_backup: Optional whether to create a backup (default: True)
                
        Returns:
            HandlerResult indicating success or failure with details about replacements
        """
        file_path = parameters.get("file_path")
        search_pattern = parameters.get("search_pattern")
        replacement = parameters.get("replacement", "")
        regex = parameters.get("regex", False)
        count = parameters.get("count", 0)  # 0 means replace all occurrences
        create_backup = parameters.get("create_backup", True)
        
        if not file_path:
            return HandlerResult(success=False, error="No file path provided")
            
        if not search_pattern:
            return HandlerResult(success=False, error="No search pattern provided")
            
        try:
            # Check if the file exists
            if not os.path.exists(file_path):
                return HandlerResult(success=False, error=f"File not found: {file_path}")
                
            # Create a backup if requested
            backup_file = None
            if create_backup:
                backup_file = f"{file_path}.bak"
                shutil.copy2(file_path, backup_file)
                
            # Read the file content
            with open(file_path, "r") as f:
                content = f.read()
                
            # Perform the search and replace
            if regex:
                import re
                # Use regex replacement
                new_content, num_replacements = re.subn(search_pattern, replacement, content, count)
            else:
                # Use simple string replacement
                if count > 0:
                    new_content = content.replace(search_pattern, replacement, count)
                    num_replacements = content.count(search_pattern) if count > content.count(search_pattern) else count
                else:
                    new_content = content.replace(search_pattern, replacement)
                    num_replacements = content.count(search_pattern)
                    
            # Write the new content
            with open(file_path, "w") as f:
                f.write(new_content)
                
            return HandlerResult(
                success=True,
                result=f"Replaced {num_replacements} occurrences in {file_path}",
                details={
                    "file_path": file_path,
                    "replacements": num_replacements,
                    "backup_file": backup_file if create_backup else None
                }
            )
        except Exception as e:
            return HandlerResult(success=False, error=f"Error replacing content: {str(e)}")
            
    def test_file(self, parameters: Dict[str, Any]) -> HandlerResult:
        """
        Test run a file in an isolated environment before applying changes.
        
        Args:
            parameters: Dictionary containing:
                - file_path: Path to the file to test
                - test_args: Optional: Arguments to pass to the test
                - use_venv: Optional: Whether to use virtual environment (default: True)
                - venv_path: Optional: Path to virtual environment
                
        Returns:
            HandlerResult with the test output if successful
        """
        file_path = parameters.get("file_path")
        test_args = parameters.get("test_args", "")
        use_venv = parameters.get("use_venv", True)
        venv_path = parameters.get("venv_path", "~/myenv")
        
        if not file_path:
            return HandlerResult(success=False, error="No file path provided")
            
        try:
            # Check if the file exists
            if not os.path.exists(file_path):
                return HandlerResult(success=False, error=f"File not found: {file_path}")
                
            # Determine how to execute the file based on extension
            command = None
            if file_path.endswith(".py"):
                if use_venv and venv_path:
                    # Use virtual environment
                    activate_cmd = f"source {venv_path}/bin/activate && "
                    command = f"{activate_cmd}python {file_path} {test_args}"
                else:
                    command = f"python {file_path} {test_args}"
            elif file_path.endswith(".js"):
                command = f"node {file_path} {test_args}"
            elif file_path.endswith(".sh"):
                command = f"bash {file_path} {test_args}"
            elif file_path.endswith(".rb"):
                command = f"ruby {file_path} {test_args}"
            else:
                # Try to execute as a regular executable
                if os.access(file_path, os.X_OK):
                    command = f"{file_path} {test_args}"
                else:
                    return HandlerResult(success=False, error=f"Unsupported file type or not executable: {file_path}")
            
            # Create a temporary directory for isolated execution
            with tempfile.TemporaryDirectory() as temp_dir:
                # Copy the file to the temporary directory
                temp_file = os.path.join(temp_dir, os.path.basename(file_path))
                shutil.copy2(file_path, temp_file)
                
                # Execute the command with the temporary file
                result = self.execute_command({
                    "command": command,
                    "directory": temp_dir,
                    "timeout": parameters.get("timeout", 30)
                })
                
                return HandlerResult(
                    success=result.success,
                    result=f"Test executed with output: {result.result}",
                    details={
                        "file_path": file_path,
                        "test_output": result.result,
                        "command": command,
                        "exit_code": result.details.get("exit_code") if hasattr(result, "details") else None
                    }
                )
        except Exception as e:
            return HandlerResult(success=False, error=f"Error testing file: {str(e)}")
    
    def duplicate_file(self, parameters: Dict[str, Any]) -> HandlerResult:
        """
        Create a duplicate of a file for safe editing.
        
        Args:
            parameters: Dictionary containing:
                - source_path: Path to the source file
                - target_path: Optional: Path where to create the duplicate
                - auto_name: Optional: Automatically generate name with timestamp (default: False)
                
        Returns:
            HandlerResult with the duplicated file path if successful
        """
        source_path = parameters.get("source_path")
        target_path = parameters.get("target_path")
        auto_name = parameters.get("auto_name", False)
        
        if not source_path:
            return HandlerResult(success=False, error="No source path provided")
            
        try:
            # Check if the source file exists
            if not os.path.exists(source_path):
                return HandlerResult(success=False, error=f"Source file not found: {source_path}")
                
            # Generate target path if not provided or auto_name is True
            if not target_path or auto_name:
                timestamp = int(time.time())
                dirname = os.path.dirname(source_path)
                basename = os.path.basename(source_path)
                base, ext = os.path.splitext(basename)
                target_path = os.path.join(dirname, f"{base}.copy.{timestamp}{ext}")
                
            # Create directories if they don't exist
            os.makedirs(os.path.dirname(target_path), exist_ok=True)
                
            # Copy the file
            shutil.copy2(source_path, target_path)
            
            return HandlerResult(
                success=True,
                result=f"File duplicated successfully: {target_path}",
                details={
                    "source_path": source_path,
                    "target_path": target_path
                }
            )
        except Exception as e:
            return HandlerResult(success=False, error=f"Error duplicating file: {str(e)}")
    
    def safe_edit_file(self, parameters: Dict[str, Any]) -> HandlerResult:
        """
        Edit a file with automatic backup creation for safety.
        
        Args:
            parameters: Dictionary containing:
                - file_path: Path to the file to edit
                - content: Optional: New content for the file
                - line_edits: Optional: Dictionary of line numbers and new content
                - create_backup: Optional: Whether to create a backup (default: True)
                
        Returns:
            HandlerResult indicating success or failure
        """
        file_path = parameters.get("file_path")
        content = parameters.get("content")
        line_edits = parameters.get("line_edits", {})
        create_backup = parameters.get("create_backup", True)
        
        if not file_path:
            return HandlerResult(success=False, error="No file path provided")
            
        if not content and not line_edits:
            return HandlerResult(success=False, error="Either content or line_edits must be provided")
            
        try:
            # Check if the file exists
            if not os.path.exists(file_path):
                return HandlerResult(success=False, error=f"File not found: {file_path}")
                
            # Create a backup if requested
            backup_file = None
            if create_backup:
                backup_file = f"{file_path}.bak"
                shutil.copy2(file_path, backup_file)
                
            # Handle complete file replacement
            if content is not None:
                with open(file_path, "w") as f:
                    f.write(content)
                    
            # Handle line-by-line editing
            elif line_edits:
                # Read all lines
                with open(file_path, "r") as f:
                    lines = f.readlines()
                    
                # Apply edits
                for line_num_str, new_content in line_edits.items():
                    try:
                        line_num = int(line_num_str)
                        if 1 <= line_num <= len(lines):
                            lines[line_num-1] = new_content + '\n' if not new_content.endswith('\n') else new_content
                    except ValueError:
                        return HandlerResult(success=False, error=f"Invalid line number: {line_num_str}")
                        
                # Write back to file
                with open(file_path, "w") as f:
                    f.writelines(lines)
                    
            return HandlerResult(
                success=True,
                result=f"File {file_path} edited successfully",
                details={
                    "file_path": file_path,
                    "backup_file": backup_file if create_backup else None
                }
            )
        except Exception as e:
            return HandlerResult(success=False, error=f"Error editing file: {str(e)}")
            
    def restore_backup(self, parameters: Dict[str, Any]) -> HandlerResult:
        """
        Restore a file from its backup.
        
        Args:
            parameters: Dictionary containing:
                - file_path: Path to the original file
                - backup_path: Optional: Path to the backup file (if not specified, will use file_path + .bak)
                
        Returns:
            HandlerResult indicating success or failure
        """
        file_path = parameters.get("file_path")
        backup_path = parameters.get("backup_path")
        
        if not file_path:
            return HandlerResult(success=False, error="No file path provided")
            
        # If no backup path provided, use default .bak extension
        if not backup_path:
            backup_path = f"{file_path}.bak"
            
        try:
            # Check if the backup file exists
            if not os.path.exists(backup_path):
                return HandlerResult(success=False, error=f"Backup file not found: {backup_path}")
                
            # Restore the file
            shutil.copy2(backup_path, file_path)
            
            # Return success
            return HandlerResult(
                success=True,
                result=f"File {file_path} restored from backup {backup_path}",
                details={
                    "file_path": file_path,
                    "backup_path": backup_path
                }
            )
        except Exception as e:
            return HandlerResult(success=False, error=f"Error restoring backup: {str(e)}")
            
    def execute_python(self, parameters: Dict[str, Any]) -> HandlerResult:
        """
        Execute Python code directly or from a file.
        
        Args:
            parameters: Dictionary containing:
                - code: Python code to execute directly (use either code or file_path)
                - file_path: Path to Python file to execute (use either code or file_path)
                - arguments: Command-line arguments to pass to the Python script
                - use_venv: Whether to use a virtual environment (default: True)
                - venv_path: Path to the virtual environment to use
                - working_dir: Working directory for execution
                - capture_output: Whether to capture and return the output (default: True)
                - timeout: Timeout in seconds for execution (default: 30)
                
        Returns:
            HandlerResult with the execution result if successful
        """
        code = parameters.get("code")
        file_path = parameters.get("file_path")
        arguments = parameters.get("arguments", "")
        use_venv = parameters.get("use_venv", True)
        # Always use the standard environment path for consistency
        venv_path = "~/myenv"  # Hardcoded to ensure consistent environment usage
        working_dir = parameters.get("working_dir", os.getcwd())
        capture_output = parameters.get("capture_output", True)
        timeout = parameters.get("timeout", 30)
        
        if not code and not file_path:
            return HandlerResult(success=False, error="Either code or file_path must be provided")
            
        try:
            # If working directory is provided, change to it
            original_dir = os.getcwd()
            if working_dir:
                os.chdir(working_dir)
                
            # Prepare the command
            if code:
                # Write the code to a temporary file
                temp_file = tempfile.NamedTemporaryFile(suffix=".py", delete=False)
                temp_file_path = temp_file.name
                with open(temp_file_path, "w") as f:
                    f.write(code)
                temp_file.close()
                
                # Always use the standard environment activation regardless of the venv parameter
                # for consistency across all Python executions
                cmd = f"source {venv_path}/bin/activate && python {temp_file_path} {arguments}"
            else:
                # Execute the provided file
                # Always use the standard environment activation regardless of the venv parameter
                cmd = f"source {venv_path}/bin/activate && python {file_path} {arguments}"
            
            # Execute the command
            result = subprocess.run(
                cmd, 
                shell=True, 
                capture_output=capture_output,
                text=True,
                timeout=timeout
            )
            
            # Clean up if we created a temporary file
            if code and os.path.exists(temp_file_path):
                os.unlink(temp_file_path)
                
            # Return to the original directory
            os.chdir(original_dir)
            
            # Check if execution was successful
            if result.returncode == 0:
                return HandlerResult(
                    success=True,
                    result=result.stdout if capture_output else "Python code executed successfully (output not captured)",
                    details={
                        "returncode": result.returncode,
                        "stderr": result.stderr if capture_output else "",
                        "command": cmd
                    }
                )
            else:
                return HandlerResult(
                    success=False,
                    error=f"Python execution failed with return code {result.returncode}",
                    details={
                        "returncode": result.returncode,
                        "stdout": result.stdout if capture_output else "",
                        "stderr": result.stderr if capture_output else "",
                        "command": cmd
                    }
                )
        except subprocess.TimeoutExpired:
            return HandlerResult(success=False, error=f"Python execution timed out after {timeout} seconds")
        except Exception as e:
            return HandlerResult(success=False, error=f"Error executing Python code: {str(e)}")
            
    def execute_applescript(self, parameters: Dict[str, Any]) -> HandlerResult:
        """
        Execute an AppleScript command directly.
        
        This method provides a way to run AppleScript commands for controlling
        macOS applications, particularly Terminal.app for terminal operations and
        managing Claude Code execution windows.
        
        Args:
            parameters: Dictionary containing:
                - script: The AppleScript code to execute
                - description: Optional description of what the script does
                - timeout: Optional timeout in seconds (default: 10)
                
        Returns:
            HandlerResult with the execution result if successful
        """
        script = parameters.get("script")
        description = parameters.get("description", "AppleScript execution")
        timeout = parameters.get("timeout", 10)
        
        if not script:
            return HandlerResult(success=False, error="No AppleScript provided")
            
        try:
            # Execute the AppleScript
            
            # Prepare the command - escape single quotes in the script
            escaped_script = script.replace("'", "'\\''")
            cmd = f"osascript -e '{escaped_script}'"
            
            # Run the command
            result = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            
            # Check if the command was successful
            if result.returncode == 0:
                return HandlerResult(
                    success=True,
                    result=result.stdout,
                    details={
                        "description": description,
                        "stderr": result.stderr,
                        "returncode": result.returncode
                    }
                )
            else:
                return HandlerResult(
                    success=False,
                    error=f"AppleScript execution failed: {result.stderr}",
                    details={
                        "description": description,
                        "stdout": result.stdout,
                        "returncode": result.returncode
                    }
                )
        except subprocess.TimeoutExpired:
            return HandlerResult(success=False, error=f"AppleScript execution timed out after {timeout} seconds")
        except Exception as e:
            return HandlerResult(success=False, error=f"Error executing AppleScript: {str(e)}")
    
    def setup_project_venv(self, parameters: Dict[str, Any]) -> HandlerResult:
        """
        Set up a dedicated virtual environment for a project.
        
        Args:
            parameters: Dictionary containing:
                - project_path: The project path to set up the environment for
                - python_version: Optional Python version for the venv
                - required_packages: Optional list of packages to install
                - venv_name: Optional custom venv name (default is 'venv')
                
        Returns:
            HandlerResult indicating success or failure
        """
        project_path = parameters.get("project_path")
        python_version = parameters.get("python_version", "3")
        required_packages = parameters.get("required_packages", [])
        venv_name = parameters.get("venv_name", "venv")
        
        if not project_path:
            return HandlerResult(success=False, error="No project path provided")
            
        try:
            # Check if the project path exists
            if not os.path.exists(project_path):
                return HandlerResult(success=False, error=f"Project path not found: {project_path}")
                
            # Create the venv directory path
            venv_path = os.path.join(project_path, venv_name)
            
            # Check if venv already exists
            if os.path.exists(venv_path):
                return HandlerResult(success=False, error=f"Virtual environment already exists at {venv_path}")
                
            # Create the virtual environment
            # Always use the standard environment activation before creating a new venv
            result = subprocess.run(
                f"source ~/myenv/bin/activate && python{python_version} -m venv {venv_path}",
                shell=True,
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                return HandlerResult(success=False, error=f"Failed to create virtual environment: {result.stderr}")
                
            # Install required packages if specified
            if required_packages:
                # Get pip path in the new venv
                pip_path = os.path.join(venv_path, "bin", "pip")
                
                # Install each package using the main environment activation
                for package in required_packages:
                    result = subprocess.run(
                        f"source ~/myenv/bin/activate && {pip_path} install {package}",
                        shell=True,
                        capture_output=True,
                        text=True
                    )
                    
                    if result.returncode != 0:
                        return HandlerResult(
                            success=False,
                            error=f"Failed to install {package}: {result.stderr}",
                            details={
                                "venv_path": venv_path,
                                "installed_packages": required_packages[:required_packages.index(package)]
                            }
                        )
            
            # Return success
            return HandlerResult(
                success=True,
                result=f"Virtual environment created at {venv_path}",
                details={
                    "venv_path": venv_path,
                    "python_version": python_version,
                    "installed_packages": required_packages
                }
            )
        except Exception as e:
            return HandlerResult(success=False, error=f"Error setting up project venv: {str(e)}")
    
    def insert_content(self, parameters: Dict[str, Any]) -> HandlerResult:
        """
        Insert content into a file at a specified position.
        
        Args:
            parameters: Dictionary containing:
                - file_path: Path to the file to modify
                - content: Content to insert
                - position: Optional position type (start, end, line, before_pattern, after_pattern)
                - line_number: Optional line number to insert at (if position is 'line')
                - pattern: Optional pattern to insert before or after (if position is 'before_pattern' or 'after_pattern')
                - create_backup: Optional whether to create a backup (default: True)
                
        Returns:
            HandlerResult indicating success or failure
        """
        file_path = parameters.get("file_path")
        content = parameters.get("content", "")
        position = parameters.get("position", "end")
        line_number = parameters.get("line_number")
        pattern = parameters.get("pattern")
        create_backup = parameters.get("create_backup", True)
        
        if not file_path:
            return HandlerResult(success=False, error="No file path provided")
            
        if not content:
            return HandlerResult(success=False, error="No content provided to insert")
            
        # Validate position is one of the allowed values
        valid_positions = ["start", "end", "line", "before_pattern", "after_pattern"]
        if position not in valid_positions:
            return HandlerResult(success=False, error=f"Invalid position '{position}'. Must be one of: {', '.join(valid_positions)}")
            
        # Validate that required parameters are provided for certain position types
        if position == "line" and line_number is None:
            return HandlerResult(success=False, error="Line number is required when position is 'line'")
            
        if position in ["before_pattern", "after_pattern"] and not pattern:
            return HandlerResult(success=False, error=f"Pattern is required when position is '{position}'")
            
        try:
            # Check if the file exists
            if not os.path.exists(file_path):
                return HandlerResult(success=False, error=f"File not found: {file_path}")
                
            # Read the existing content
            with open(file_path, "r") as f:
                existing_content = f.read()
                
            # Create backup if requested
            if create_backup:
                import shutil
                backup_file = f"{file_path}.bak"
                shutil.copy2(file_path, backup_file)
                
            # Insert content based on position
            new_content = ""
            if position == "start":
                new_content = content + existing_content
            elif position == "end":
                new_content = existing_content + content
            elif position == "line":
                lines = existing_content.split("\n")
                if line_number < 1 or line_number > len(lines) + 1:
                    return HandlerResult(success=False, error=f"Line number {line_number} out of range (1-{len(lines) + 1})")
                    
                # Insert content at the specified line (1-based)
                lines.insert(line_number - 1, content)
                new_content = "\n".join(lines)
            elif position in ["before_pattern", "after_pattern"]:
                import re
                match = re.search(pattern, existing_content)
                if not match:
                    return HandlerResult(success=False, error=f"Pattern '{pattern}' not found in file")
                    
                match_start, match_end = match.span()
                
                if position == "before_pattern":
                    new_content = existing_content[:match_start] + content + existing_content[match_start:]
                else:  # after_pattern
                    new_content = existing_content[:match_end] + content + existing_content[match_end:]
            
            # Write the new content
            with open(file_path, "w") as f:
                f.write(new_content)
                
            return HandlerResult(
                success=True, 
                result=f"Content inserted at {position} of file",
                details={
                    "file": file_path,
                    "position": position,
                    "backup_created": create_backup,
                    "backup_file": backup_file if create_backup else None
                }
            )
        except Exception as e:
            return HandlerResult(success=False, error=f"Error inserting content: {str(e)}")

    def search_files(self, parameters: Dict[str, Any]) -> HandlerResult:
        """
        Search for files matching a pattern.
        
        Args:
            parameters: Dictionary containing:
                - pattern: Search pattern (glob pattern or regex)
                - directory: Optional directory to search in (default: current directory)
                - recursive: Optional whether to search recursively (default: True)
                
        Returns:
            HandlerResult with the list of matching files
        """
        import glob
        import re
        import fnmatch
        
        pattern = parameters.get("pattern")
        directory = parameters.get("directory", os.getcwd())
        recursive = parameters.get("recursive", True)
        
        if not pattern:
            return HandlerResult(success=False, error="No search pattern provided")
            
        try:
            # Check if the directory exists
            if not os.path.exists(directory):
                return HandlerResult(success=False, error=f"Directory not found: {directory}")
                
            # Determine if this is a glob pattern or regex
            is_glob = "*" in pattern or "?" in pattern or "[" in pattern
            
            if is_glob:
                # Use glob to find matching files
                if recursive:
                    # Use ** for recursive search
                    if "**" not in pattern:
                        # Add ** if not already in the pattern
                        search_pattern = os.path.join(directory, "**", pattern)
                    else:
                        search_pattern = os.path.join(directory, pattern)
                    matching_files = glob.glob(search_pattern, recursive=True)
                else:
                    # Single directory search
                    search_pattern = os.path.join(directory, pattern)
                    matching_files = glob.glob(search_pattern)
            else:
                # Use regex to find matching files
                try:
                    regex = re.compile(pattern)
                    matching_files = []
                    
                    if recursive:
                        # Walk through directories recursively
                        for root, dirs, files in os.walk(directory):
                            for file in files:
                                if regex.search(file):
                                    matching_files.append(os.path.join(root, file))
                    else:
                        # Search only in the specified directory
                        for file in os.listdir(directory):
                            if os.path.isfile(os.path.join(directory, file)) and regex.search(file):
                                matching_files.append(os.path.join(directory, file))
                except re.error:
                    # If regex fails, treat it as a plain string
                    matching_files = []
                    
                    if recursive:
                        # Walk through directories recursively
                        for root, dirs, files in os.walk(directory):
                            for file in files:
                                if pattern in file:
                                    matching_files.append(os.path.join(root, file))
                    else:
                        # Search only in the specified directory
                        for file in os.listdir(directory):
                            if os.path.isfile(os.path.join(directory, file)) and pattern in file:
                                matching_files.append(os.path.join(directory, file))
            
            # Return the list of matching files
            return HandlerResult(success=True, data=matching_files)
        except Exception as e:
            return HandlerResult(success=False, error=f"Error searching files: {str(e)}")
            
    def search_content(self, parameters: Dict[str, Any]) -> HandlerResult:
        """
        Search for content within files.
        
        Args:
            parameters: Dictionary containing:
                - pattern: Text pattern to search for
                - file_pattern: Optional only search files matching this pattern
                - directory: Optional directory to search in (default: current directory)
                - recursive: Optional whether to search recursively (default: True)
                - case_sensitive: Optional whether search is case sensitive (default: False)
                
        Returns:
            HandlerResult with the list of files containing the pattern
        """
        import re
        
        pattern = parameters.get("pattern")
        file_pattern = parameters.get("file_pattern", "*")
        directory = parameters.get("directory", os.getcwd())
        recursive = parameters.get("recursive", True)
        case_sensitive = parameters.get("case_sensitive", False)
        
        if not pattern:
            return HandlerResult(success=False, error="No search pattern provided")
            
        try:
            # First get the list of files to search
            files_result = self.search_files({
                "pattern": file_pattern,
                "directory": directory,
                "recursive": recursive
            })
            
            if not files_result.success:
                return files_result
                
            files_to_search = files_result.result
            matching_files = []
            content_matches = {}
            
            # Compile the regex pattern
            try:
                if case_sensitive:
                    regex = re.compile(pattern)
                else:
                    regex = re.compile(pattern, re.IGNORECASE)
                    
                is_regex = True
            except re.error:
                # If regex fails, treat it as a plain string
                is_regex = False
            
            # Search for the pattern in each file
            for file_path in files_to_search:
                try:
                    with open(file_path, "r", errors="ignore") as f:
                        content = f.read()
                        
                    # Search for the pattern
                    if is_regex:
                        if regex.search(content):
                            matching_files.append(file_path)
                            
                            # Extract matched lines for context
                            lines = content.split('\n')
                            matched_lines = []
                            
                            for i, line in enumerate(lines):
                                if regex.search(line):
                                    matched_lines.append({
                                        "line_number": i + 1,
                                        "content": line
                                    })
                                    
                            # Store the matches
                            if matched_lines:
                                content_matches[file_path] = matched_lines
                    else:
                        # Plain string search
                        if (pattern in content) if case_sensitive else (pattern.lower() in content.lower()):
                            matching_files.append(file_path)
                            
                            # Extract matched lines for context
                            lines = content.split('\n')
                            matched_lines = []
                            
                            for i, line in enumerate(lines):
                                if (pattern in line) if case_sensitive else (pattern.lower() in line.lower()):
                                    matched_lines.append({
                                        "line_number": i + 1,
                                        "content": line
                                    })
                                    
                            # Store the matches
                            if matched_lines:
                                content_matches[file_path] = matched_lines
                except Exception as e:
                    # Skip files that can't be read
                    pass
            
            # Return the results
            return HandlerResult(
                success=True,
                result=matching_files,
                details={"content_matches": content_matches}
            )
        except Exception as e:
            return HandlerResult(success=False, error=f"Error searching content: {str(e)}")
    
    def search_and_replace(self, parameters: Dict[str, Any]) -> HandlerResult:
        """
        Search and replace text across multiple files.
        
        Args:
            parameters: Dictionary containing:
                - search_pattern: Pattern to search for
                - replacement: Text to replace with
                - file_pattern: Optional: Only process files matching this pattern
                - directory: Optional: Directory to search in (default: current directory)
                - use_regex: Optional: Whether to use regex for search/replace (default: False)
                - case_sensitive: Optional: Whether search is case sensitive (default: False)
                - backup: Optional: Whether to create backups before modifying files (default: True)
                
        Returns:
            HandlerResult with the list of modified files and their changes
        """
        import re
        import os
        import shutil
        
        search_pattern = parameters.get("search_pattern")
        replacement = parameters.get("replacement")
        file_pattern = parameters.get("file_pattern", "*")
        directory = parameters.get("directory", os.getcwd())
        use_regex = parameters.get("use_regex", False)
        case_sensitive = parameters.get("case_sensitive", False)
        create_backup = parameters.get("backup", True)
        
        if not search_pattern:
            return HandlerResult(success=False, error="No search pattern provided")
        
        if replacement is None:
            return HandlerResult(success=False, error="No replacement text provided")
            
        try:
            # First get the list of files to process
            files_result = self.search_files({
                "pattern": file_pattern,
                "directory": directory,
                "recursive": True
            })
            
            if not files_result.success:
                return files_result
                
            files_to_process = files_result.result
            modified_files = []
            changes = {}
            
            # Compile regex if using regex mode
            regex = None
            if use_regex:
                try:
                    flags = 0 if case_sensitive else re.IGNORECASE
                    regex = re.compile(search_pattern, flags)
                except re.error as e:
                    return HandlerResult(success=False, error=f"Invalid regex pattern: {str(e)}")
            
            # Process each file
            for file_path in files_to_process:
                try:
                    # Skip binary files or files that can't be read as text
                    try:
                        with open(file_path, 'r', errors='ignore') as f:
                            content = f.read()
                    except UnicodeDecodeError:
                        continue
                    
                    # Create backup if requested
                    if create_backup:
                        backup_path = f"{file_path}.bak"
                        shutil.copy2(file_path, backup_path)
                    
                    # Perform the search and replace
                    if use_regex and regex:
                        new_content = regex.sub(replacement, content)
                    else:
                        if case_sensitive:
                            new_content = content.replace(search_pattern, replacement)
                        else:
                            # Case-insensitive search and replace without regex
                            def replace_case_insensitive(match):
                                return replacement
                            new_content = re.sub(re.escape(search_pattern), replace_case_insensitive, content, flags=re.IGNORECASE)
                    
                    # Only modify the file if changes were made
                    if new_content != content:
                        with open(file_path, 'w') as f:
                            f.write(new_content)
                        
                        modified_files.append(file_path)
                        
                        # Count and track changes
                        if use_regex and regex:
                            # For regex, count matches
                            match_count = len(regex.findall(content))
                            changes[file_path] = match_count
                        else:
                            # For string replace, count occurrences
                            pattern_to_count = search_pattern
                            if not case_sensitive:
                                pattern_to_count = pattern_to_count.lower()
                                content_to_search = content.lower()
                            else:
                                content_to_search = content
                            changes[file_path] = content_to_search.count(pattern_to_count)
                    
                except Exception as e:
                    # Log error but continue with other files
                    self.logger.error(f"Error processing file {file_path}: {str(e)}")
                    continue
            
            # Return the results
            return HandlerResult(
                success=True,
                result=modified_files,
                details={
                    "modified_files": modified_files,
                    "changes": changes,
                    "total_files_modified": len(modified_files),
                    "search_pattern": search_pattern,
                    "replacement": replacement
                }
            )
        except Exception as e:
            return HandlerResult(success=False, error=f"Error in search and replace: {str(e)}")
    
    def _setup_project_venv(self, parameters: Dict[str, Any]) -> HandlerResult:
        """Set up a Python virtual environment."""
        venv_path = parameters.get("venv_path")
        force_recreate = parameters.get("force_recreate", False)
        
        if not venv_path:
            return HandlerResult(success=False, error="No venv path provided")
            
        try:
            if force_recreate and os.path.exists(venv_path):
                shutil.rmtree(venv_path)
                
            if not os.path.exists(venv_path):
                subprocess.run([sys.executable, "-m", "venv", venv_path], check=True)
                
            return HandlerResult(success=True)
        except Exception as e:
            return HandlerResult(success=False, error=str(e))

    def _execute_with_venv(self, parameters: Dict[str, Any]) -> HandlerResult:
        """Execute a command within a virtual environment."""
        command = parameters.get("command")
        venv_path = parameters.get("venv_path")
        
        if not command or not venv_path:
            return HandlerResult(success=False, error="Missing command or venv path")
            
        try:
            activate_script = os.path.join(venv_path, "bin", "activate")
            full_command = f"source {activate_script} && {command}"
            result = subprocess.run(full_command, shell=True, capture_output=True, text=True)
            return HandlerResult(success=True, data=result.stdout)
        except Exception as e:
            return HandlerResult(success=False, error=str(e))

    async def analyze_and_edit_file(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze and optionally edit a file."""
        file_path = parameters.get("file_path")
        operation_type = parameters.get("operation_type")
        edit_content = parameters.get("edit_content")
        
        if not file_path or not operation_type:
            return {"success": False, "error": "Missing file path or operation type"}
            
        try:
            if operation_type == "read":
                with open(file_path, "r") as f:
                    content = f.read()
                return {"success": True, "content": content}
            elif operation_type == "edit":
                if not edit_content:
                    return {"success": False, "error": "No edit content provided"}
                with open(file_path, "w") as f:
                    f.write(edit_content)
                return {"success": True}
            else:
                return {"success": False, "error": f"Unknown operation type: {operation_type}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def get_journey_status(self, journey_id: str) -> Dict[str, Any]:
        """Get the status of a journey."""
        if journey_id in self.active_journeys:
            return {"status": "active", "steps": self.journey_steps.get(journey_id, [])}
        return {"status": "not_found", "message": f"Journey {journey_id} not found"}

    async def get_status(self) -> Dict[str, Any]:
        """Get the current status of the handler."""
        return {
            "status": "active" if self.active else "inactive",
            "metrics": self.metrics,
            "active_sessions": len(self.active_sessions),
            "tracking_interface_available": bool(self.tracking_interface)
        }

    def create_terminal_session(self, parameters: Dict[str, Any]) -> HandlerResult:
        """
        Create a new terminal session.
        
        Args:
            parameters: Dictionary containing:
                - directory: Optional directory to start the session in
                - name: Optional name for the session
                - separate_from_claude: Optional whether to ensure this is a separate window from Claude Code sessions (default: True)
                - boardroom_session: Optional whether this is for a BoardRoom session (default: False)
                - boardroom_planning_session: Optional whether this is from BoardRoom planning (for backward compatibility)
                - use_claude_window: Optional whether to use an existing Claude window (default: False)
                - create_window: Optional whether to actually create a visible terminal window (default: True)
                - force_new_window: Optional whether to create a new window even if session exists (default: False)
                - reuse_session: Optional whether to reuse existing session if possible (default: True for BoardRoom)
                - window_type: Optional type of window (WINDOW_TYPE_TERMINAL, WINDOW_TYPE_CLAUDE_CODE, WINDOW_TYPE_DIRECT_TERMINAL)
                - never_reuse: Optional flag to never reuse this window for other commands (default: False)
                
        Returns:
            HandlerResult with the session ID if successful
        """
        directory = parameters.get("directory", os.getcwd())
        name = parameters.get("name", f"session_{self.session_counter}")
        separate_from_claude = parameters.get("separate_from_claude", True)
        boardroom_session = parameters.get("boardroom_session", False)
        boardroom_planning_session = parameters.get("boardroom_planning_session", False)
        use_claude_window = parameters.get("use_claude_window", False)
        create_window = parameters.get("create_window", True)
        force_new_window = parameters.get("force_new_window", False)
        window_type = parameters.get("window_type")
        never_reuse = parameters.get("never_reuse", False)
        
        # Check if this is a BoardRoom request using any identification method
        is_from_boardroom = (
            boardroom_session or
            boardroom_planning_session or
            "message_from_boardroom" in str(parameters) or 
            "boardroom" in str(parameters.get("source", ""))
        )
        
        # For BoardRoom commands
        if is_from_boardroom:
            # Always set both BoardRoom session flags for consistency
            boardroom_session = True
            parameters["boardroom_session"] = True
            parameters["boardroom_planning_session"] = True
            
            # CRITICAL: For direct terminal commands from BoardRoom, force new window every time
            # These commands are file operations like find, grep, ls -l that should never reuse windows
            if command and any(cmd in command for cmd in ['find ', 'grep ', 'ls -l']):
                # This is a direct terminal command - force new window and unique session
                force_new_window = True
                # Override any reuse session settings
                parameters["reuse_session"] = False
                # Generate unique session for this command
                unique_id = f"{int(time.time())}_{os.getpid()}_{hash(command)}"
                terminal_session_id = f"boardroom_direct_terminal_{unique_id}"
                logging.warning(f"🚨 FORCING NEW WINDOW FOR DIRECT TERMINAL COMMAND: {terminal_session_id}")
                # Skip the rest of the BoardRoom persistent session logic
                name = terminal_session_id
            else:
                # For regular BoardRoom commands, use the persistent session
                # Set or reuse a consistent session ID for all BoardRoom commands
                if not hasattr(self.__class__, 'boardroom_terminal_session'):
                    # Create a new persistent session ID if none exists
                    self.__class__.boardroom_terminal_session = f"boardroom_terminal_{int(time.time())}"
                    logging.warning(f"🚨 CREATING NEW PERSISTENT BOARDROOM SESSION: {self.__class__.boardroom_terminal_session}")
                
                # Check if there's a provided session ID from the parameters
                provided_session_id = parameters.get("session_id")
                if provided_session_id:
                    # Use the provided session ID and remember it for the future
                    self.__class__.boardroom_terminal_session = provided_session_id
                    logging.warning(f"🚨 UPDATED BOARDROOM PERSISTENT SESSION: {self.__class__.boardroom_terminal_session}")
                else:
                    # Use the persistent session ID as the name of the session
                    name = self.__class__.boardroom_terminal_session
                    logging.warning(f"🚨 USING BOARDROOM PERSISTENT SESSION AS NAME: {name}")
        
        
        try:
            # First aggressively search for any existing terminal window with AppleScript
            # This is a more reliable way to find existing windows than our internal tracking
            found_window_id = None
            # IMPORTANT: 
            # 1. NEVER search for existing windows for direct terminal commands (force_new_window)
            # 2. NEVER search for non-BoardRoom sessions to prevent hijacking terminals
            # 3. NEVER reuse windows if a direct terminal command type was requested
            is_direct_terminal = parameters.get("window_type") == self.WINDOW_TYPE_DIRECT_TERMINAL
            is_from_boardroom = boardroom_session or parameters.get("boardroom_planning_session", False) 
            never_reuse = parameters.get("never_reuse", False)

            # ONLY search for existing windows if:
            # 1. This IS a BoardRoom session
            # 2. We're NOT forcing a new window
            # 3. We're NOT using a unique direct session ID
            # 4. We're NOT handling a direct terminal command
            # 5. We haven't explicitly been told never to reuse
            if (is_from_boardroom and not is_direct_terminal and 
                not force_new_window and not never_reuse and 
                not (terminal_session_id and "boardroom_direct_terminal_" in terminal_session_id)):
                try:
                    # Search for any terminal window that's not a Claude window
                    find_term_script = '''
                    tell application "Terminal"
                        set foundWindow to false
                        set windowID to ""
                        
                        # First check all windows
                        repeat with w in windows
                            # CRITICAL SAFETY: Never reuse the current test window
                            # For testing if this is the terminal that runs the test,
                            # check for specific text in the contents
                            set tabContents to ""
                            try
                                set tabContents to (contents of (first tab of w)) as string
                            end try
                            
                            # Skip this window if it has ANYTHING that suggests it's a test window or active terminal
                            # to avoid hijacking the test window itself - be EXTREMELY conservative
                            if tabContents contains "Running" or tabContents contains "test" or tabContents contains "jarvis" or 
                               tabContents contains "terminal" or tabContents contains "command" or
                               tabContents contains "Python" or tabContents contains "python" or
                               (name of w) contains "test" or (name of w) contains "Python" or
                               tabContents contains ">" or tabContents contains "$" or
                               tabContents contains "%" or tabContents contains "#" then
                                # NEVER use windows that look like they're active or running tests
                                # or the window that has our test script running
                                log "SAFETY: Skipping window that might be a test/active window"
                            else
                                # Check window title and contents to determine if it's a good candidate
                                repeat with t in tabs of w
                                    # Skip windows with "CLAUDE" in the title
                                    if name of t does not contain "CLAUDE" then
                                        set windowID to id of w
                                        set foundWindow to true
                                        exit repeat
                                    end if
                                end repeat
                            end if
                            
                            if foundWindow then
                                exit repeat
                            end if
                        end repeat
                        
                        if foundWindow then
                            return windowID
                        else
                            return "not_found"
                        end if
                    end tell
                    '''
                    
                    # Write to file
                    find_term_script_file = f"/tmp/find_terminal_{int(time.time())}.scpt"
                    with open(find_term_script_file, "w") as f:
                        f.write(find_term_script)
                    
                    # Run the script
                    logging.warning(f"🚨 SEARCHING FOR EXISTING TERMINAL WINDOWS")
                    find_result = subprocess.run(["osascript", find_term_script_file], capture_output=True, text=True)
                    
                    if find_result.returncode == 0 and find_result.stdout.strip() and find_result.stdout.strip() != "not_found":
                        found_window_id = find_result.stdout.strip()
                        logging.warning(f"🚨 FOUND EXISTING TERMINAL WINDOW: {found_window_id}")
                    else:
                        logging.warning(f"🚨 NO EXISTING TERMINAL WINDOWS FOUND")
                
                except Exception as e:
                    logging.error(f"🚨 ERROR SEARCHING FOR TERMINAL WINDOWS: {str(e)}")
            
            # For BoardRoom sessions, attempt to use a persistent window, but with safety checks
            # NEVER reuse windows for direct terminal commands
            if boardroom_session and not force_new_window and not (terminal_session_id and "boardroom_direct_terminal_" in terminal_session_id):
                # First check if we have a stored class window ID
                stored_window_id = getattr(self.__class__, 'active_boardroom_window_id', None)
                if stored_window_id:
                    # Use the stored window ID
                    found_window_id = stored_window_id
                    logging.warning(f"🚨 USING STORED CLASS WINDOW ID: {found_window_id}")
                
                # If we found a window, create or update our persistent session to use it
                if found_window_id:
                    # Always use the persistent session ID for regular BoardRoom commands
                    # but NOT for direct terminal commands
                    if not (terminal_session_id and "boardroom_direct_terminal_" in terminal_session_id):
                        session_id = "boardroom_terminal_persistent"
                        self.__class__.boardroom_terminal_session = session_id
                    
                    # If the session exists, update it; otherwise create it
                    if session_id in self.active_sessions:
                        # Update the window ID and other properties
                        self.active_sessions[session_id]["window_id"] = found_window_id
                        self.active_sessions[session_id]["active"] = True
                        self.active_sessions[session_id]["last_used"] = time.time()
                        self.active_sessions[session_id]["directory"] = directory
                        logging.warning(f"🚨 UPDATED EXISTING BOARDROOM SESSION WITH FOUND WINDOW: {found_window_id}")
                    else:
                        # Create a new session with the found window
                        self.active_sessions[session_id] = {
                            "name": "BoardRoom Terminal",
                            "directory": directory,
                            "created_at": time.time(),
                            "last_used": time.time(),
                            "last_command": None,
                            "last_output": None,
                            "commands": [],
                            "window_type": "terminal",
                            "separate_from_claude": True,
                            "session_origin": "boardroom",
                            "active": True,
                            "window_id": found_window_id
                        }
                        logging.warning(f"🚨 CREATED NEW BOARDROOM SESSION WITH FOUND WINDOW: {found_window_id}")
                    
                    # Return the session
                    return HandlerResult(
                        success=True,
                        result=f"Using existing window for BoardRoom session",
                        details={"session_id": session_id, "name": "BoardRoom Terminal", "directory": directory, "reused": True}
                    )
                
                # If we didn't find a window but have a tracked session, try to use it
                elif hasattr(self.__class__, 'boardroom_terminal_session'):
                    existing_session_id = self.__class__.boardroom_terminal_session
                    if existing_session_id in self.active_sessions:
                        # We need a visible window - try to create one
                        logging.warning(f"🚨 REUSING SESSION WITHOUT WINDOW - MUST FIND OR CREATE WINDOW: {existing_session_id}")
                        
                        # Try to locate any terminal window
                        try:
                            # Use a simple script to find any terminal window
                            find_script = '''
                            tell application "Terminal"
                                set foundWindow to false
                                set windowID to ""
                                
                                # First check all windows
                                repeat with w in windows
                                    set windowID to id of w
                                    set foundWindow to true
                                    exit repeat
                                end repeat
                                
                                if foundWindow then
                                    return windowID
                                else
                                    return "not_found"
                                end if
                            end tell
                            '''
                            
                            # Write to file
                            find_script_file = f"/tmp/find_any_terminal_{int(time.time())}.scpt"
                            with open(find_script_file, "w") as f:
                                f.write(find_script)
                            
                            # Run the script
                            window_search = subprocess.run(["osascript", find_script_file], capture_output=True, text=True)
                            
                            if window_search.returncode == 0 and window_search.stdout.strip() and window_search.stdout.strip() != "not_found":
                                # Found a window
                                found_id = window_search.stdout.strip()
                                logging.warning(f"🚨 FOUND EXISTING TERMINAL WINDOW: {found_id}")
                                
                                # Store it for this session
                                self.active_sessions[existing_session_id]["window_id"] = found_id
                                
                                # Also update class variable for all to use
                                self.__class__.active_boardroom_window_id = found_id
                            else:
                                # Create a new window with a specific title
                                logging.warning(f"🚨 NO EXISTING WINDOW FOUND - CREATING NEW WINDOW WITH BOARDROOM TITLE")
                                
                                # Create terminal with a title that includes "BoardRoom" so we can find it later
                                create_cmd = '''
                                tell application "Terminal"
                                    do script ""
                                    set custom title of front window to "BoardRoom Terminal"
                                    set w to front window
                                    return id of w
                                end tell
                                '''
                                create_script_file = f"/tmp/create_boardroom_terminal_{int(time.time())}.scpt"
                                with open(create_script_file, "w") as f:
                                    f.write(create_cmd)
                                
                                # Run the script directly to create the window and get its ID in one step
                                created_window = subprocess.run(["osascript", create_script_file], capture_output=True, text=True)
                                
                                if created_window.returncode == 0 and created_window.stdout.strip():
                                    # We already have the window ID from the creation script
                                    new_id = created_window.stdout.strip()
                                    logging.warning(f"🚨 CREATED NEW BOARDROOM WINDOW WITH ID: {new_id}")
                                    
                                    # Store it
                                    self.active_sessions[existing_session_id]["window_id"] = new_id
                                    self.__class__.active_boardroom_window_id = new_id
                                    return
                                
                                # Fallback: If direct creation with ID capture failed, create a regular window 
                                # and then get its ID
                                logging.warning(f"🚨 DIRECT WINDOW CREATION FAILED, USING FALLBACK METHOD")
                                create_cmd = f"open -a Terminal"
                                subprocess.run(create_cmd, shell=True)
                                time.sleep(0.5)
                                
                                # Get the new window ID and set its title
                                id_script = '''
                                tell application "Terminal"
                                    set custom title of front window to "BoardRoom Terminal"
                                    set w to front window
                                    return id of w
                                end tell
                                '''
                                id_script_file = f"/tmp/get_new_terminal_id_{int(time.time())}.scpt"
                                with open(id_script_file, "w") as f:
                                    f.write(id_script)
                                
                                # Run the script
                                new_window = subprocess.run(["osascript", id_script_file], capture_output=True, text=True)
                                
                                if new_window.returncode == 0 and new_window.stdout.strip():
                                    new_id = new_window.stdout.strip()
                                    logging.warning(f"🚨 CREATED NEW WINDOW WITH ID: {new_id}")
                                    
                                    # Store it for this session
                                    self.active_sessions[existing_session_id]["window_id"] = new_id
                                    
                                    # Also update class variable
                                    self.__class__.active_boardroom_window_id = new_id
                        except Exception as e:
                            logging.error(f"🚨 ERROR FINDING/CREATING WINDOW: {str(e)}")
                        
                        # Ensure session is marked as active
                        self.active_sessions[existing_session_id]["active"] = True
                        self.active_sessions[existing_session_id]["last_used"] = time.time()
                        
                        logging.warning(f"[TERMINAL_SESSION] Reusing existing BoardRoom terminal session: {existing_session_id}")
                        
                        # Return the existing session
                        return HandlerResult(
                            success=True,
                            result=f"Reusing existing session with window",
                            details={"session_id": existing_session_id, "name": name, "directory": directory, "reused": True}
                        )
                
                # No window found, no session found
                logging.warning(f"🚨 NO EXISTING WINDOW OR SESSION FOUND, CREATING NEW SESSION")
                    
            # For BoardRoom sessions only, use a consistent ID instead of creating new ones
            # NEVER reuse BoardRoom terminals for direct commands
            is_from_boardroom = boardroom_session or parameters.get("boardroom_planning_session", False)
            is_direct_terminal = parameters.get("window_type") == self.WINDOW_TYPE_DIRECT_TERMINAL or not is_from_boardroom
            
            # Direct terminal commands should ALWAYS get a unique session ID and never reuse
            if is_direct_terminal:
                # Always use a unique ID for direct terminal commands to prevent hijacking
                unique_id = f"direct_terminal_{int(time.time())}_{os.getpid()}_{hash(str(parameters))}"
                session_id = f"terminal_direct_{unique_id}"
                logging.warning(f"🚨 GENERATED UNIQUE DIRECT TERMINAL SESSION ID: {session_id}")
            # Only use persistent terminals for BoardRoom sessions
            elif boardroom_session:
                # If an explicit session_id is provided for BoardRoom, use it
                if parameters.get("session_id") and 'boardroom' in parameters.get("session_id"):
                    session_id = parameters.get("session_id")
                else:
                    # Always use the same ID for all BoardRoom terminal sessions
                    session_id = "boardroom_persistent_terminal_fixed"
                
                # Set both tracking mechanisms for consistency but ONLY for BoardRoom sessions
                self.__class__.boardroom_terminal_session = session_id
                self.__class__.boardroom_planning_terminal = session_id
                
                logging.warning(f"🚨 SETTING FIXED BOARDROOM TERMINAL SESSION ID: {session_id}")
                
                # If this session already exists, just return it - don't create a new window
                if session_id in self.active_sessions:
                    # Update window ID with the one we found
                    if found_window_id:
                        self.active_sessions[session_id]["window_id"] = found_window_id
                        logging.warning(f"🚨 UPDATED WINDOW ID FOR EXISTING SESSION: {found_window_id}")
                    
                    # Update the session to mark it as active and update timestamp
                    self.active_sessions[session_id]["active"] = True
                    self.active_sessions[session_id]["last_used"] = time.time()
                    self.active_sessions[session_id]["directory"] = directory  # Update directory if needed
                    
                    # Log the reuse
                    logging.warning(f"[TERMINAL_SESSION] Reusing existing BoardRoom terminal session: {session_id}")
                    
                    # Return the existing session
                    return HandlerResult(
                        success=True,
                        result=f"Reusing existing BoardRoom session",
                        details={"session_id": session_id, "name": name, "directory": directory, "reused": True}
                    )
            else:
                # For non-BoardRoom sessions, use a unique ID and always create new windows
                session_id = f"terminal_{int(time.time())}_{self.session_counter}"
                
                # Direct commands (not from BoardRoom) should always get a new window
                # even if we found an existing window earlier
                initial_window_id = None  # Override found windows for direct commands
                create_window = True      # Always create a window for direct commands
                force_new_window = True   # Force a new window for direct commands
                logging.warning(f"🚨 DIRECT COMMAND - FORCING NEW WINDOW")
            
            self.session_counter += 1
            
            # If we found an existing window and this is a BoardRoom session, use it
            # For direct commands, we already set initial_window_id to None above
            if boardroom_session:
                initial_window_id = found_window_id
            
            # Store the session
            self.active_sessions[session_id] = {
                "name": name,
                "directory": directory,
                "created_at": time.time(),
                "last_used": time.time(),
                "last_command": None,
                "last_output": None,
                "commands": [],
                "window_type": window_type or (self.WINDOW_TYPE_DIRECT_TERMINAL if not boardroom_session else self.WINDOW_TYPE_TERMINAL), # Distinguish between direct terminal and others
                "separate_from_claude": separate_from_claude,
                "session_origin": "boardroom" if boardroom_session else "direct",
                "active": True,
                "window_id": initial_window_id  # May be None if no window found
            }
            
            # For direct terminal commands, ALWAYS create a new window, never reuse
            # For other commands, create a visible terminal window if requested and no existing window found
            # Ensure window_type is defined before using it
            session_window_type = self.active_sessions[session_id].get("window_type", self.WINDOW_TYPE_TERMINAL)
            never_reuse = self.active_sessions[session_id].get("never_reuse", False)
            
            # ALWAYS create new window for DIRECT_TERMINAL requests or commands marked as never_reuse
            # Also create new window if force_new_window is set or if requested with no existing window
            if (session_window_type == self.WINDOW_TYPE_DIRECT_TERMINAL or 
                never_reuse or force_new_window or 
                (create_window and not initial_window_id)):
                # Use AppleScript to create a visible terminal window with specific title
                window_title = "Terminal Session"
                if boardroom_session:
                    window_title = "BoardRoom Terminal"
                
                # Escape the directory for AppleScript
                escaped_dir = directory.replace('"', '\\"')
                
                # Create a new terminal window with a unique title to ensure separation from test windows
                # Use a custom AppleScript that creates a dedicated, identifiable window
                # This is much safer than reusing existing windows
                unique_id = f"terminal_{int(time.time())}_{os.getpid()}"
                if session_window_type == self.WINDOW_TYPE_DIRECT_TERMINAL:
                    window_title = f"DIRECT_COMMAND_{unique_id}"
                elif boardroom_session:
                    window_title = f"BOARDROOM_{unique_id}"
                else:
                    window_title = f"JARVIS_{unique_id}"
                
                # Create window with specific title and position to make it clear this is a new window
                # Use a more specific approach for different window types
                if session_window_type == self.WINDOW_TYPE_DIRECT_TERMINAL:
                    # Direct terminal commands get bright red background for clear visibility
                    create_term_script = '''
                    tell application "Terminal"
                        do script ""
                        set current settings of front window to settings set "Red Sands"
                        set custom title of front window to "''' + window_title + '''"
                        set position of front window to {500, 300}
                        set size of front window to {800, 400}
                        activate
                    end tell
                    '''
                elif boardroom_session:
                    # BoardRoom session gets a blue background
                    create_term_script = '''
                    tell application "Terminal"
                        do script ""
                        set current settings of front window to settings set "Ocean"
                        set custom title of front window to "''' + window_title + '''"
                        set position of front window to {100, 100}
                        set size of front window to {1000, 700}
                        activate
                    end tell
                    '''
                else:
                    # Regular terminal sessions get Pro theme
                    create_term_script = '''
                    tell application "Terminal"
                        do script ""
                        set current settings of front window to settings set "Pro"
                        set custom title of front window to "''' + window_title + '''"
                        set position of front window to {100, 100}
                        set size of front window to {800, 600}
                        activate
                    end tell
                    '''
                
                # Write to file
                script_file = f"/tmp/create_terminal_{int(time.time())}.scpt"
                with open(script_file, "w") as f:
                    f.write(create_term_script)
                
                try:
                    # Create dedicated window with custom title
                    logging.warning(f"🚨 CREATING NEW TERMINAL WINDOW WITH DEDICATED SCRIPT: {window_title}")
                    subprocess.run(["osascript", script_file], check=True)
                    
                    # Wait a moment for Terminal to open and initialize
                    time.sleep(1.0)
                    
                    # Get the ID of the active window
                    window_id_script = """
                    tell application "Terminal"
                        set w to front window
                        return id of w
                    end tell
                    """
                    
                    # Write to file
                    id_filename = "/tmp/get_window_id.scpt"
                    with open(id_filename, "w") as f:
                        f.write(window_id_script)
                    
                    # Run the script
                    window_result = subprocess.run(["osascript", id_filename], capture_output=True, text=True)
                    
                    if window_result.returncode == 0 and window_result.stdout.strip():
                        window_id = window_result.stdout.strip()
                        logging.warning(f"🚨 GOT NEW WINDOW ID: {window_id}")
                        
                        # Change directory with simple command
                        cd_cmd = f'osascript -e \'tell application "Terminal" to do script "cd {escaped_dir}" in front window\''
                        subprocess.run(cd_cmd, shell=True)
                        
                        # Set title with simple command - skip custom title to avoid issues
                        logging.warning(f"🚨 TERMINAL WINDOW SETUP COMPLETE")
                    else:
                        logging.error(f"🚨 FAILED TO GET WINDOW ID: {window_result.stderr}")
                        window_id = None
                except Exception as e:
                    logging.error(f"🚨 ERROR CREATING TERMINAL WINDOW: {str(e)}")
                    window_id = None
                
                # Only log result if we had one
                try:
                    if window_result:
                        logging.warning(f"🚨 WINDOW ID SCRIPT RESULT: {window_result.returncode}")
                        if window_result.stderr:
                            logging.error(f"AppleScript error: {window_result.stderr}")
                            
                        if window_result.stdout:
                            logging.warning(f"🚨 WINDOW ID: {window_result.stdout}")
                except Exception:
                    logging.warning("🚨 Unable to log window result")
                
                # Store the window ID for later reference if we got one or use the initial one
                if 'window_id' in locals() and window_id:
                    self.active_sessions[session_id]["window_id"] = window_id
                    logging.warning(f"🚨 STORED WINDOW ID {window_id} FOR SESSION {session_id}")
                    # For BoardRoom sessions, also store in class variable
                    if session.get("session_origin") == "boardroom":
                        self.__class__.active_boardroom_window_id = window_id
                        logging.warning(f"🚨 STORED GLOBAL BOARDROOM WINDOW ID: {window_id}")
                elif initial_window_id:
                    self.active_sessions[session_id]["window_id"] = initial_window_id
                    logging.warning(f"🚨 USING FOUND WINDOW ID {initial_window_id} FOR SESSION {session_id}")
                    # For BoardRoom sessions, also store in class variable
                    if session.get("session_origin") == "boardroom":
                        self.__class__.active_boardroom_window_id = initial_window_id
                        logging.warning(f"🚨 STORED GLOBAL BOARDROOM WINDOW ID: {initial_window_id}")
                else:
                    self.active_sessions[session_id]["window_id"] = None
                    logging.warning(f"🚨 NO WINDOW ID STORED FOR SESSION {session_id}")
            
            # Also store in class variable for terminal sessions
            if not hasattr(self.__class__, 'active_terminal_sessions'):
                self.__class__.active_terminal_sessions = {}
            
            self.__class__.active_terminal_sessions[session_id] = self.active_sessions[session_id]
            
            # Update metrics
            self.metrics["commands_executed"] += 1
            
            # Create command cache if it doesn't exist
            if not hasattr(self.__class__, 'command_cache'):
                self.__class__.command_cache = {}
                logging.warning(f"🚨 INITIALIZED COMMAND CACHE")
                
            # Also create class variable for session info
            if not hasattr(self.__class__, 'active_boardroom_window_id'):
                self.__class__.active_boardroom_window_id = initial_window_id if initial_window_id else self.active_sessions[session_id]["window_id"]
                logging.warning(f"🚨 STORED CLASS WINDOW ID: {self.__class__.active_boardroom_window_id}")
            
            # Return the session information
            window_status = "existing" if initial_window_id else "new" if self.active_sessions[session_id]["window_id"] else "none"
            return HandlerResult(
                success=True,
                result=f"Session created: {name} with {window_status} window",
                details={"session_id": session_id, "name": name, "directory": directory}
            )
        except Exception as e:
            return HandlerResult(success=False, error=f"Error creating terminal session: {str(e)}")
            
    def send_command(self, parameters: Dict[str, Any]) -> HandlerResult:
        """
        Send a command to an existing terminal session.
        
        Args:
            parameters: Dictionary containing:
                - session_id: ID of the terminal session
                - command: Command to send to the terminal
                - use_window: Whether to send command to the actual terminal window (default: True)
                - wait_time: Time to wait for command completion (default: 0.5, longer for file operations)
                - force_execution: Force execution even if the command was recently run (default: False)
                - boardroom_planning_session: Whether this is coming from BoardRoom planning session
                - force_new_window: Force creation of a new window (default: False)
                
        Returns:
            HandlerResult with the command output if successful
        """
        session_id = parameters.get("session_id")
        command = parameters.get("command")
        use_window = parameters.get("use_window", True)
        wait_time = parameters.get("wait_time", 0.5)
        force_execution = parameters.get("force_execution", False)
        force_new_window = parameters.get("force_new_window", False)
        
        # Check if this is a BoardRoom planning session
        is_from_boardroom = (
            parameters.get("boardroom_planning_session", False) or 
            "message_from_boardroom" in str(parameters) or 
            "boardroom" in str(parameters.get("source", ""))
        )
        
        # For direct terminal commands (not from BoardRoom), always create a new session
        # Always create a brand new window for non-BoardRoom commands regardless of session_id
        if not is_from_boardroom:
            # Force new window for direct commands
            force_new_window = True
            
            # Reset any provided session_id to force creation of new windows
            session_id = None
            
            # CRITICAL SAFETY: For direct terminal commands, we must absolutely guarantee
            # a new window is created and we never reuse any existing window
            # This prevents hijacking the terminal running tests or other important windows
            
            # Create a new session for direct command with unique ID that includes PID
            # to ensure it can't conflict with any existing session
            direct_unique_id = f"{int(time.time())}_{os.getpid()}_{hash(command)}"
            new_session_params = {
                "name": f"Direct Command Terminal {direct_unique_id}",
                "directory": os.getcwd(),
                "create_window": True,  # Always create a window
                "separate_from_claude": True,
                "force_new_window": True,  # Force new window creation
                "never_reuse": True,  # Never attempt to reuse this window
                "window_type": self.WINDOW_TYPE_DIRECT_TERMINAL,
                "direct_unique_id": direct_unique_id  # Store the unique ID
            }
            result = self.create_terminal_session(new_session_params)
            if result.success:
                session_id = result.details.get("session_id")
                logging.warning(f"🚨 CREATED NEW SESSION FOR DIRECT COMMAND: {session_id}")
            else:
                logging.error(f"🚨 FAILED TO CREATE NEW SESSION FOR DIRECT COMMAND: {result.error}")
        
        # For BoardRoom commands
        elif is_from_boardroom:
            # Always set BoardRoom planning flag
            parameters["boardroom_planning_session"] = True
            
            # CRITICAL: For direct terminal commands (like find, grep), force new window even from BoardRoom
            if command and any(cmd in command for cmd in ['find ', 'grep ', 'ls -l']):
                # This is a direct terminal command from BoardRoom - force new window
                force_new_window = True
                # Generate unique session ID to avoid reuse
                unique_id = f"{int(time.time())}_{os.getpid()}_{hash(command)}"
                session_id = f"boardroom_direct_terminal_{unique_id}"
                logging.warning(f"🚨 FORCING UNIQUE WINDOW FOR DIRECT TERMINAL COMMAND FROM BOARDROOM: {session_id}")
            # Otherwise use persistent session
            else:
                # Set or reuse a consistent session ID for other BoardRoom commands
                if not hasattr(self.__class__, 'boardroom_terminal_session'):
                    # Create a new persistent session ID if none exists
                    self.__class__.boardroom_terminal_session = f"boardroom_terminal_{int(time.time())}"
                    logging.warning(f"🚨 CREATING NEW PERSISTENT BOARDROOM SESSION: {self.__class__.boardroom_terminal_session}")
                
                # Use the persistent session ID if none provided
                if not session_id:
                    session_id = self.__class__.boardroom_terminal_session
                    logging.warning(f"🚨 USING BOARDROOM PERSISTENT SESSION: {session_id} for command: {command[:30]}...")
        
        
        # Adjust wait time based on command type
        if command and (command.startswith("find") or command.startswith("grep") or "ls -l" in command):
            # Longer wait for file operations
            wait_time = max(wait_time, 2.0)
            logging.warning(f"[TERMINAL_SESSION] Increasing wait time to {wait_time}s for file operation: {command[:30]}...")
        
        if not session_id or not command:
            return HandlerResult(success=False, error="Missing session ID or command")
            
        # Check if the session exists
        if session_id not in self.active_sessions:
            return HandlerResult(success=False, error=f"Session not found: {session_id}")
            
        try:
            # Get the session information
            session = self.active_sessions[session_id]
            
            # Create command cache if it doesn't exist
            if not hasattr(self.__class__, 'command_cache'):
                self.__class__.command_cache = {}
                
            # Create a more robust cache key using the normalized command
            normalized_cmd = self._get_normalized_command(command)
            cache_key = f"{session_id}:{normalized_cmd}"
            
            # Look for semantically equivalent commands in cache
            semantic_match = None
            
            # For BoardRoom sessions, try to find semantic matches
            if is_from_boardroom:
                for cached_key, cached_entry in self.__class__.command_cache.items():
                    # Skip if not from same session
                    if not cached_key.startswith(f"{session_id}:"):
                        continue
                        
                    # Get the command part after session_id:
                    cached_cmd = cached_key[len(f"{session_id}:"):]
                    
                    # Check if commands are semantically equivalent (file listings, searches, etc.)
                    cmd_type = command.split(' ')[0] if command else ""
                    if cmd_type in ["ls", "find", "grep", "cat", "head", "tail"] and self._are_command_types_equivalent(command, cached_cmd):
                        semantic_match = cached_entry
                        logging.warning(f"🔄 SEMANTIC CACHE MATCH: Similar command found in cache")
                        break
            
            # Check if this command was recently executed and we have the result (in class-level cache)
            if not force_execution and (cache_key in self.__class__.command_cache or semantic_match):
                cache_entry = self.__class__.command_cache.get(cache_key) or semantic_match
                # For BoardRoom planning sessions, use cached results with extended validity
                if is_from_boardroom or time.time() - cache_entry["timestamp"] < 7200:  # Cache valid for 120 minutes (2 hours) for BoardRoom
                    logging.warning(f"🔄 USING CACHED RESULT FOR COMMAND: {command[:30]}...")
                    
                    # Update last used time to keep the session active without executing
                    session["last_used"] = time.time()
                    
                    # Return the cached output directly with metadata
                    return HandlerResult(
                        success=True, 
                        data=f"[CACHED COMMAND RESULT] {cache_entry['output']}",
                        details={"cached": True, "original_timestamp": cache_entry["timestamp"]}
                    )
            
            # If we get here, we need to execute the command
            # Update last used time to keep the session active
            session["last_used"] = time.time()
            
            if use_window and session.get("window_id"):
                # Escape the command for AppleScript
                window_id = session["window_id"]
                
                # Create a properly formatted shell script for the command
                temp_shell_script = f"/tmp/direct_term_cmd_sh_{int(time.time())}_{os.getpid()}.sh"
                
                # Detect and handle natural language mixed with terminal commands
                # Common phrases that indicate natural language after a command
                terminators = [" and ", " then ", " to ", " so ", " for ", " with "]
                
                # First check for newlines - in bidirectional communication, we should truncate at newlines
                # since they often separate the command from natural language or subsequent queries
                if "\n" in command:
                    # If there's a newline, truncate at the first newline
                    clean_command = command.split("\n")[0]
                    logging.warning(f"🚨 DETECTED NEWLINE AFTER COMMAND. Truncated command to first line only.")
                else:
                    # Extract just the valid command part using terminators
                    clean_command = command
                    for term in terminators:
                        pos = command.lower().find(term)
                        if pos > 0:
                            # Found potential natural language - truncate the command
                            clean_command = command[:pos]
                            logging.warning(f"🚨 DETECTED NATURAL LANGUAGE AFTER COMMAND at '{term}'. Truncated command.")
                            break
                
                # Check for unbalanced quotes - much more aggressively
                quote_count_single = clean_command.count("'")
                quote_count_double = clean_command.count('"')
                
                # Maximum safety mode for boardroom sessions - remove ALL potential problem characters
                if session.get("session_origin") == "boardroom":
                    logging.warning(f"🚨 BOARDROOM SESSION - APPLYING MAXIMUM SAFETY TO COMMAND")
                    # Replace all quotes and any other potentially problematic characters
                    original_cmd = clean_command
                    clean_command = clean_command.replace('"', '').replace("'", '')
                    clean_command = clean_command.replace('\\', '').replace('`', '')
                    clean_command = clean_command.replace('$', '').replace('!', '')
                    # Remove any redirection or piping that might cause issues
                    clean_command = clean_command.replace('>', ' ').replace('<', ' ').replace('|', ' ')
                    clean_command = ' '.join(clean_command.split())  # Normalize whitespace
                    logging.warning(f"🚨 ORIGINAL: {original_cmd}")
                    logging.warning(f"🚨 SANITIZED: {clean_command}")
                elif quote_count_single % 2 != 0 or quote_count_double % 2 != 0:
                    logging.warning(f"🚨 UNBALANCED QUOTES IN COMMAND: Single: {quote_count_single}, Double: {quote_count_double}")
                    # Remove all quotes to be safe
                    clean_command = clean_command.replace('"', '').replace("'", "").strip()
                    logging.warning(f"🚨 REMOVED ALL QUOTES FOR SAFETY")
                else:
                    # Just strip any trailing quotes or whitespace
                    clean_command = clean_command.rstrip('\'"').strip()
                
                logging.warning(f"🚨 FINAL CLEANED COMMAND FOR DIRECT EXECUTION: {clean_command}")
                
                with open(temp_shell_script, "w") as f:
                    # Write a properly formatted script with commands on separate lines and exit trap
                    f.write("#!/bin/bash\n")
                    # Set trap to ensure we exit cleanly even if commands fail
                    f.write("trap 'exit' INT TERM\n")
                    f.write("trap 'exit' EXIT\n")
                    f.write("set -e\n")
                    # Use simpler cd without quotes to avoid issues
                    f.write(f"cd {os.path.abspath(os.getcwd())}\n")
                    # Wrap command in a function to provide scope isolation
                    f.write("function execute_command() {\n")
                    f.write(f"  {clean_command}\n")
                    f.write("}\n\n")
                    f.write("# Execute the command in an isolated subshell\n")
                    f.write("( execute_command )\n")
                    # Always exit cleanly to avoid terminal hijacking
                    f.write("exit 0\n")
                os.chmod(temp_shell_script, 0o755)
                
                # For BoardRoom sessions, use direct execution to prevent window errors
                if session.get("session_origin") == "boardroom":
                    # First check the stored global window ID - override window_id if exists
                    global_window_id = getattr(self.__class__, 'active_boardroom_window_id', None)
                    if global_window_id:
                        window_id = global_window_id
                        logging.warning(f"🚨 USING GLOBAL WINDOW ID FOR COMMAND: {global_window_id}")
                    
                    # Try to execute directly without shell script - safer
                    direct_exec_cmd = '''
                    tell application "Terminal"
                        set twindow to window id ''' + str(window_id) + '''
                        # Send the command directly to avoid shell script issues
                        do script "/bin/bash -c \"cd " + os.getcwd() + " && { " + clean_command + "; }; exit 0\"" in twindow
                        # Bring window to front for better visibility
                        set frontmost of twindow to true
                        activate
                    end tell
                    '''
                    
                    # Write this script to ensure it's correct
                    inline_script_file = f"/tmp/inline_boardroom_cmd_{int(time.time())}.scpt"
                    with open(inline_script_file, "w") as f:
                        f.write(direct_exec_cmd)
                    
                    # Execute directly with osascript file
                    direct_cmd = f"osascript {inline_script_file}"
                    
                    # Log the command for debug
                    logging.warning(f"🚨 USING INLINE BOARDROOM COMMAND: {clean_command}")
                    logging.warning(f"🚨 SCRIPT FILE: {inline_script_file}")
                else:
                    # Write a simpler AppleScript command with double quotes for shell script
                    script_filename = f"/tmp/direct_term_cmd_{int(time.time())}_{os.getpid()}.scpt"
                    with open(script_filename, "w") as f:
                        # Use explicit "sh" with full path and double quotes around the script path
                        # This ensures the shell command is properly executed
                        script_content = '''
                        tell application "Terminal"
                            set w to window id ''' + str(window_id) + '''
                            # Add a unique marker with the session ID and process ID to ensure we can identify specific windows
                            # Use a dedicated format that makes it clear this is a new terminal created by the terminal handler
                            # Use a completely isolated bash -c approach with proper string concatenation
                            do script "/bin/bash -c \"echo '🔒 TERMINAL SESSION: " + terminal_session_id + " (PID: " + str(os.getpid()) + ")'; trap 'exit 0' EXIT INT TERM; { clear && echo '📝 Running command in isolated session " + terminal_session_id + "...'; /bin/bash -e \\\"" + temp_shell_script + "\\\" 2>&1 || echo '\\nCommand failed'; } && echo '\\n[COMMAND_COMPLETE] Session: " + terminal_session_id + "'; exit 0\"" in w
                        end tell
                        '''
                        f.write(script_content)
                    # Use the script file approach instead of inline AppleScript
                    direct_cmd = f'osascript {script_filename}'
                    
                    # Log the exact script content for debugging
                    logging.warning(f"🚨 TERMINAL SCRIPT CONTENT:\n{script_content}")
                
                # Execute using the script file
                logging.warning(f"🚨 EXECUTING DIRECT COMMAND IN WINDOW {window_id}")
                logging.warning(f"🚨 COMMAND: {direct_cmd}")
                
                # Use subprocess with shell=True for the osascript command
                window_result = subprocess.run(direct_cmd, shell=True, capture_output=True, text=True)
                
                # Cleanup temp script file after execution
                try:
                    # Check if the file exists before attempting to remove it
                    if os.path.exists(script_filename):
                        os.remove(script_filename)
                    else:
                        logging.warning(f"🔹 SCRIPT FILE NOT FOUND (already removed): {script_filename}")
                except Exception as e:
                    logging.warning(f"Could not remove temp script file: {e}")
                
                # Check for errors
                if window_result.returncode != 0:
                    logging.error(f"🚨 COMMAND EXECUTION ERROR: {window_result.stderr}")
                
                # Log results for debugging
                logging.warning(f"🚨 COMMAND EXECUTION RESULT: {window_result.returncode}")
                if window_result.stderr:
                    logging.error(f"Command AppleScript error: {window_result.stderr}")
                
                # If window not found, fall back to direct execution
                if "Window not found" in window_result.stdout:
                    logging.warning(f"[TERMINAL_SESSION] Window {window_id} not found for session {session_id}, using direct execution instead")
                    use_window = False
            
            # Change to the session directory if specified
            current_dir = os.getcwd()
            if session["directory"]:
                os.chdir(session["directory"])
                
            # Execute the command directly if not using window or if window execution failed
            if not use_window or not session.get("window_id"):
                result = subprocess.run(command, shell=True, capture_output=True, text=True)
                output = result.stdout
                error = result.stderr
            else:
                # Give window execution time to complete for better user experience
                time.sleep(wait_time)
                
                # For find and ls operations, attempt to capture output from window
                should_capture = command and (command.startswith("find") or command.startswith("ls") or command.startswith("grep"))
                if should_capture:
                    try:
                        # Create AppleScript to get terminal output
                        capture_script = f"""
                        tell application "Terminal"
                            repeat with w in windows
                                if id of w is {window_id} then
                                    set outputText to contents of selected tab of w
                                    return outputText
                                end if
                            end repeat
                            return "Window not found for output capture"
                        end tell
                        """
                        
                        # Write to file to avoid escaping issues
                        capture_filename = f"/tmp/terminal_capture_{int(time.time())}.scpt"
                        with open(capture_filename, "w") as f:
                            f.write(capture_script)
                            
                        # Run the capture script
                        logging.warning(f"[TERMINAL_SESSION] Capturing output from window {window_id}")
                        capture_result = subprocess.run(["osascript", capture_filename], 
                                                        capture_output=True, text=True, timeout=5)
                        
                        # Process the output
                        if capture_result.returncode == 0 and capture_result.stdout and "Window not found" not in capture_result.stdout:
                            # Extract output related to the command
                            full_output = capture_result.stdout
                            logging.warning(f"[TERMINAL_SESSION] Captured {len(full_output)} characters of output")
                            
                            # Try to find command in output and capture everything after it
                            command_pos = full_output.find(command)
                            if command_pos >= 0:
                                output = full_output[command_pos + len(command):]
                                logging.warning(f"[TERMINAL_SESSION] Extracted command output: {len(output)} characters")
                            else:
                                # If command not found, return the full output
                                output = full_output
                        else:
                            output = f"Command sent to terminal window: {command}"
                    except Exception as e:
                        logging.error(f"Error capturing terminal output: {str(e)}")
                        output = f"Command sent to terminal window: {command}"
                else:
                    # For non-capture commands, just return a note
                    output = f"Command sent to terminal window: {command}"
                error = ""
                
            # Change back to the original directory if needed
            if session["directory"]:
                os.chdir(current_dir)
                
            # Update session information
            session["last_command"] = command
            session["last_output"] = output
            
            # Check if this is a file viewing command and set keep_open flag
            file_view_commands = ["cat ", "less ", "head ", "tail ", "bat ", "view ", "vim ", "nano "]
            if any(command.startswith(cmd) for cmd in file_view_commands):
                logging.warning(f"🚨 Detected file viewing command: {command[:50]}... - keeping window open")
                session["keep_open"] = True
                # Also record this in the session tracking
                if session_id in self.__class__.active_terminal_sessions:
                    self.__class__.active_terminal_sessions[session_id]["keep_open"] = True
            
            session["commands"].append({
                "command": command,
                "output": output,
                "error": error,
                "timestamp": time.time()
            })
            
            # Store the output for retrieval
            self.last_output[session_id] = output
            
            # Store in command cache for future use
            if not hasattr(self.__class__, 'command_cache'):
                self.__class__.command_cache = {}
                
            # Create more robust cache key including directory context
            # For BoardRoom, use a consistent key prefix - normalize the command to improve cache hits
            if session.get("session_origin") == "boardroom" or "boardroom" in session_id:
                # Extract core command by removing extra spaces or trailing natural language
                core_command = self._get_normalized_command(command)
                cache_key = f"boardroom:{core_command}"
                logging.warning(f"🔄 Normalized BoardRoom command for cache: {command[:50]} -> {core_command[:50]}")
            else:
                cache_key = f"{session_id}:{command}"
                
            # Include directory context for path-dependent commands
            if session.get("directory"):
                cache_key = f"{cache_key}:{session['directory']}"
                
            # Determine if this is a file viewing command
            is_file_viewing = any(command.startswith(cmd) for cmd in ["cat ", "less ", "head ", "tail ", "bat ", "view "])
            
            # Flag to indicate if this is a BoardRoom command
            is_boardroom = session.get("session_origin") == "boardroom" or "boardroom" in session_id
            
            # Store command result in cache with additional metadata
            self.__class__.command_cache[cache_key] = {
                "output": output,
                "timestamp": time.time(),
                "session_id": session_id,
                "directory": session.get("directory", ""),
                "is_file_viewing": is_file_viewing,
                "is_boardroom": is_boardroom,
                "cache_key": cache_key
            }
            
            # More detailed logging for debugging 
            if is_boardroom:
                logging.warning(f"🔄 CACHED BOARDROOM COMMAND RESULT: Key={cache_key}, Command={command[:50]}...")
                print(f"🔄 STORED IN BOARDROOM CACHE: {command[:50]}...")
            else:
                logging.warning(f"🔄 CACHED RESULT FOR COMMAND: {command[:30]}...")
            
            # Update metrics
            self.metrics["commands_executed"] += 1
            
            return HandlerResult(success=True, data=output)
        except Exception as e:
            return HandlerResult(success=False, error=f"Error executing command: {str(e)}")
            
    def get_output(self, parameters: Dict[str, Any]) -> HandlerResult:
        """
        Get the output from the last command in a terminal session.
        
        Args:
            parameters: Dictionary containing:
                - session_id: ID of the terminal session
                
        Returns:
            HandlerResult with the last command output if successful
        """
        session_id = parameters.get("session_id")
        
        if not session_id:
            return HandlerResult(success=False, error="Missing session ID")
            
        # Check if the session exists
        if session_id not in self.active_sessions:
            return HandlerResult(success=False, error=f"Session not found: {session_id}")
            
        # Get the session information
        session = self.active_sessions[session_id]
        
        # Return the last output
        return HandlerResult(success=True, data=session["last_output"])
        
    def list_sessions(self, parameters: Dict[str, Any]) -> HandlerResult:
        """
        List active terminal sessions.
        
        Returns:
            HandlerResult with the list of active sessions
        """
        sessions = []
        for session_id, session in self.active_sessions.items():
            sessions.append({
                "session_id": session_id,
                "name": session["name"],
                "directory": session["directory"],
                "created_at": session["created_at"],
                "command_count": len(session["commands"])
            })
            
        return HandlerResult(success=True, data=sessions)
        
    def close_session(self, parameters: Dict[str, Any]) -> HandlerResult:
        """
        Close a terminal session.
        
        Args:
            parameters: Dictionary containing:
                - session_id: ID of the terminal session to close
                
        Returns:
            HandlerResult indicating success or failure
        """
        session_id = parameters.get("session_id")
        
        if not session_id:
            return HandlerResult(success=False, error="Missing session ID")
            
        # Check if the session exists
        if session_id not in self.active_sessions:
            return HandlerResult(success=False, error=f"Session not found: {session_id}")
            
        # Get the session information
        session = self.active_sessions[session_id]
        
        # Close the session
        del self.active_sessions[session_id]
        
        return HandlerResult(success=True, data=f"Session closed: {session['name']}")
    
    def get_info(self) -> Dict[str, Any]:
        """Return information about this handler"""
        return {
            "name": self.handler_name,
            "description": "Terminal handler for executing commands and interacting with the terminal",
            "capabilities": [
                "Execute shell commands",
                "Open new terminal windows",
                "Run scripts and programs",
                "Navigate directories",
                "Search for files and content",
                "Interact with terminal sessions",
                "Execute Python code directly or from files",
                "Execute AppleScript code for system automation"
            ],
            "actions": [
                {
                    "name": "execute_command",
                    "description": "Execute a shell command and return the output",
                    "parameters": {
                        "command": "The command to execute",
                        "directory": "Optional: Directory to execute the command in",
                        "timeout": "Optional: Timeout in seconds (default: 30)"
                    }
                },
                {
                    "name": "open_terminal",
                    "description": "Open a new terminal window at the specified directory",
                    "parameters": {
                        "directory": "Optional: Directory to open terminal in (default: home directory)"
                    }
                },
                {
                    "name": "run_script",
                    "description": "Run a script file in the terminal",
                    "parameters": {
                        "file_path": "Path to the script file",
                        "arguments": "Optional: Arguments to pass to the script"
                    }
                },
                {
                    "name": "search_files",
                    "description": "Search for files matching a pattern",
                    "parameters": {
                        "pattern": "Search pattern (glob pattern or regex)",
                        "directory": "Optional: Directory to search in (default: current directory)",
                        "recursive": "Optional: Whether to search recursively (default: True)"
                    }
                },
                {
                    "name": "search_content",
                    "description": "Search for content within files",
                    "parameters": {
                        "pattern": "Text pattern to search for",
                        "file_pattern": "Optional: Only search files matching this pattern",
                        "directory": "Optional: Directory to search in (default: current directory)"
                    }
                },
                {
                    "name": "create_terminal_session",
                    "description": "Create a new persistent terminal session",
                    "parameters": {
                        "directory": "Optional: Directory to start the session in",
                        "name": "Optional: Name for the session"
                    }
                },
                {
                    "name": "send_command",
                    "description": "Send a command to an existing terminal session",
                    "parameters": {
                        "session_id": "ID of the terminal session",
                        "command": "Command to send to the terminal"
                    }
                },
                {
                    "name": "get_output",
                    "description": "Get the output from the last command in a terminal session",
                    "parameters": {
                        "session_id": "ID of the terminal session"
                    }
                },
                {
                    "name": "list_sessions",
                    "description": "List active terminal sessions",
                    "parameters": {}
                },
                {
                    "name": "close_session",
                    "description": "Close a terminal session",
                    "parameters": {
                        "session_id": "ID of the terminal session to close"
                    }
                },
                {
                    "name": "edit_file",
                    "description": "Edit a file using a temp file approach",
                    "parameters": {
                        "file_path": "Path to the file to edit",
                        "content": "Optional: New content for the file",
                        "line_edits": "Optional: Dictionary of line numbers and new content"
                    }
                },
                {
                    "name": "create_file",
                    "description": "Create a new file with specified content",
                    "parameters": {
                        "file_path": "Path to the file to create",
                        "content": "Optional: Content for the file"
                    }
                },
                {
                    "name": "execute_with_venv",
                    "description": "Execute a command within the activated virtual environment",
                    "parameters": {
                        "command": "The command to execute",
                        "directory": "Optional: Directory to execute the command in",
                        "venv_path": "Path to the virtual environment"
                    }
                },
                {
                    "name": "analyze_codebase",
                    "description": "Analyze a codebase to understand its structure",
                    "parameters": {
                        "directory": "Optional: Directory to analyze (default: current directory)",
                        "file_types": "Optional: List of file types to include in analysis"
                    }
                },
                {
                    "name": "file_operations",
                    "description": "Perform operations on files like moving, copying, or renaming them",
                    "parameters": {
                        "source_pattern": "Pattern to match source files",
                        "target_directory": "Optional: Target directory for operation",
                        "operation": "Optional: Operation to perform (move, copy, rename)",
                        "directory": "Optional: Directory to search in (default: current directory)",
                        "rename_pattern": "Optional: Pattern to rename files"
                    }
                },
                {
                    "name": "search_and_replace",
                    "description": "Search and replace text across multiple files",
                    "parameters": {
                        "search_pattern": "Pattern to search for",
                        "replacement": "Text to replace with",
                        "file_pattern": "Optional: Only process files matching this pattern",
                        "directory": "Optional: Directory to search in",
                        "use_regex": "Optional: Whether to use regex for search/replace"
                    }
                },
                {
                    "name": "insert_content",
                    "description": "Insert content at a specific position in a file",
                    "parameters": {
                        "file_path": "Path to the file",
                        "content": "Content to insert",
                        "position": "Where to insert (start, end, line:X, after:pattern, before:pattern)"
                    }
                },
                {
                    "name": "search_and_replace",
                    "description": "Search for a pattern in a file and replace it with new content",
                    "parameters": {
                        "file_path": "Path to the file to modify",
                        "search_pattern": "Pattern to search for",
                        "replacement": "Content to replace the pattern with",
                        "regex": "Optional: Whether to use regex matching (default: False)",
                        "count": "Optional: Maximum number of replacements to make (default: all)"
                    }
                },
                {
                    "name": "safe_edit_file",
                    "description": "Edit a file with automatic backup creation for safety",
                    "parameters": {
                        "file_path": "Path to the file to edit",
                        "content": "Optional: New content for the file",
                        "line_edits": "Optional: Dictionary of line numbers and new content",
                        "create_backup": "Optional: Whether to create a backup (default: True)"
                    }
                },
                {
                    "name": "test_file",
                    "description": "Test run a file in an isolated environment before applying changes",
                    "parameters": {
                        "file_path": "Path to the file to test",
                        "test_args": "Optional: Arguments to pass to the test",
                        "use_venv": "Optional: Whether to use virtual environment (default: True)",
                        "venv_path": "Optional: Path to virtual environment"
                    }
                },
                {
                    "name": "duplicate_file",
                    "description": "Create a duplicate of a file for safe editing",
                    "parameters": {
                        "source_path": "Path to the source file",
                        "target_path": "Optional: Path where to create the duplicate",
                        "auto_name": "Optional: Automatically generate name with timestamp (default: False)"
                    }
                },
                {
                    "name": "restore_backup",
                    "description": "Restore a file from its backup",
                    "parameters": {
                        "backup_path": "Path to the backup file",
                        "original_path": "Optional: Path to the original file"
                    }
                },
                {
                    "name": "setup_project_venv",
                    "description": "Set up a virtual environment for a project with proper activation",
                    "parameters": {
                        "project_dir": "Optional: Project directory (default: current directory)",
                        "venv_path": "Optional: Path for the virtual environment",
                        "requirements_file": "Optional: Name of requirements file (default: requirements.txt)",
                        "force_recreate": "Optional: Force recreation of existing environment (default: False)"
                    }
                },
                {
                    "name": "execute_python",
                    "description": "Execute Python code directly or from a file with virtual environment support",
                    "parameters": {
                        "code": "Optional: Python code to execute directly",
                        "file_path": "Optional: Path to Python file to execute",
                        "arguments": "Optional: Command-line arguments to pass to script",
                        "use_venv": "Optional: Whether to use a virtual environment (default: True)",
                        "venv_path": "Optional: Path to virtual environment (default: ~/myenv)",
                        "working_dir": "Optional: Working directory for execution",
                        "capture_output": "Optional: Whether to capture output (default: True)",
                        "timeout": "Optional: Execution timeout in seconds (default: 30)"
                    }
                },
                {
                    "name": "execute_applescript",
                    "description": "Execute AppleScript code on macOS",
                    "parameters": {
                        "script": "The AppleScript code to execute"
                    }
                }
            ]
        }
        
    @property
    def orchestrator_agent(self):
        """Get the orchestrator agent for this handler"""
        return self.orchestrator
        
    def _delayed_terminal_closure(self, session_id, delay_seconds=10):
        """Close a terminal window after a specified delay to ensure results are processed by BoardRoom."""
        try:
            # Wait for the specified delay
            import time
            time.sleep(delay_seconds)
            
            # Check if the session still exists and is marked for closure
            if hasattr(self.__class__, 'active_terminal_sessions') and session_id in self.__class__.active_terminal_sessions:
                session_info = self.__class__.active_terminal_sessions[session_id]
                
                # First check if the terminal should remain open (keep_open flag)
                if session_info.get("keep_open", False):
                    logging.warning(f"🚨 Delayed terminal closure for session {session_id} - keep_open flag is set, keeping terminal open")
                    return
                
                # Only close if marked for closure and delay time has passed
                if session_info.get("close_after_result", False) and time.time() >= session_info.get("close_after_time", 0):
                    logging.warning(f"🚨 Delayed terminal closure for session {session_id} executing now")
                    self._close_terminal_window(session_id)
                else:
                    logging.warning(f"🚨 Delayed terminal closure for session {session_id} - conditions not met, keeping open")
            else:
                logging.warning(f"🚨 Session {session_id} no longer exists, skipping delayed closure")
        except Exception as e:
            logging.error(f"Error in delayed terminal closure: {str(e)}")
    
    def _close_terminal_window(self, session_id):
        """Close a terminal window based on its session ID."""
        try:
            # Get session info
            if not hasattr(self.__class__, 'active_terminal_sessions') or session_id not in self.__class__.active_terminal_sessions:
                logging.warning(f"No terminal session found for ID: {session_id}")
                return False
                
            session_info = self.__class__.active_terminal_sessions[session_id]
            window_id = session_info.get("window_id")
            
            # Check if the last command run in this session was a file viewing command
            last_command = session_info.get("last_command", "")
            is_file_viewing_command = False
            
            if last_command:
                # Check for common file viewing commands
                file_view_commands = ["cat ", "less ", "head ", "tail ", "bat ", "view ", "vim ", "nano "]
                is_file_viewing_command = any(last_command.startswith(cmd) for cmd in file_view_commands)
            
            # Check if this is a direct terminal command window - these should be closed UNLESS showing file contents
            is_direct_terminal = session_info.get("window_type") == self.WINDOW_TYPE_DIRECT_TERMINAL
            
            if is_direct_terminal and not is_file_viewing_command:
                # Direct terminal windows should be closed - never kept open (except file viewing commands)
                logging.warning(f"🚨 Will close direct terminal command window with ID: {window_id}")
                # Force window closure immediately to prevent hanging terminals
                # Mark this terminal as ready for closure immediately
                session_info["close_after_result"] = True
                session_info["close_after_time"] = time.time()
                # Always make sure we remove this from the active sessions immediately after use
                session_info["force_cleanup"] = True
                # Set a very short expiration time
                session_info["expire_after"] = 5  # seconds
                # Delete from the class variable immediately after this method finishes
                self.__class__._windows_to_remove_after_closure = getattr(self.__class__, '_windows_to_remove_after_closure', [])
                self.__class__._windows_to_remove_after_closure.append(session_id)
                # Continue with window closure
            # Skip closure if it's showing a file OR it's not a direct terminal AND is Claude Code/explicitly kept open
            elif is_file_viewing_command or session_info.get("is_claude_code", False) or session_info.get("keep_open", False) or "boardroom" in session_id:
                logging.warning(f"🚨 Keeping terminal session {session_id} open (protected session or file view: {is_file_viewing_command})")
                return False
            
            # If we have a window ID, try to close it with AppleScript
            if window_id:
                # First check if the window exists
                check_script = '''
                tell application "Terminal"
                    set windowExists to false
                    try
                        set w to (first window whose id is ''' + str(window_id) + ''')
                        set windowExists to true
                    end try
                    return windowExists
                end tell
                '''
                
                # Execute the check script
                check_result = subprocess.run(["osascript", "-e", check_script], 
                                            capture_output=True, text=True)
                
                # Only attempt to close the window if it actually exists
                if check_result.returncode == 0 and check_result.stdout.strip() == "true":
                    # Create AppleScript to close the terminal window
                    close_script = '''
                    tell application "Terminal"
                        close (first window whose id is ''' + str(window_id) + ''')
                    end tell
                    '''
                    
                    # Execute the AppleScript
                    close_result = subprocess.run(["osascript", "-e", close_script], 
                                                capture_output=True, text=True)
                    
                    if close_result.returncode == 0:
                        logging.warning(f"🚨 Successfully closed terminal window for session {session_id}")
                        # Update session info
                        session_info["active"] = False
                        session_info["closed_at"] = time.time()
                        return True
                    else:
                        logging.error(f"Failed to close terminal window: {close_result.stderr}")
                        return False
                else:
                    # Window doesn't exist but update session info anyway
                    logging.warning(f"🚨 Terminal window {window_id} for session {session_id} no longer exists")
                    session_info["active"] = False
                    session_info["closed_at"] = time.time()
                    return True
            else:
                # Try closing by matching terminal content
                command = session_info.get("command", "")
                close_script = '''
                tell application "Terminal"
                    set foundWindow to false
                    repeat with w in windows
                        if (contents of w as string) contains "''' + command.replace('"', '\\"').replace("'", "\\'") + '''" then
                            close w
                            set foundWindow to true
                            exit repeat
                        end if
                    end repeat
                    return foundWindow
                end tell
                '''
                
                # Execute the script
                close_result = subprocess.run(["osascript", "-e", close_script], 
                                            capture_output=True, text=True)
                
                if close_result.returncode == 0 and close_result.stdout.strip() == "true":
                    logging.warning(f"🚨 Successfully closed terminal window for session {session_id} by matching content")
                    # Update session info
                    session_info["active"] = False
                    session_info["closed_at"] = time.time()
                    return True
                else:
                    logging.error(f"Failed to find matching terminal window to close for session {session_id}")
                    return False
        except Exception as e:
            logging.error(f"Error closing terminal window: {str(e)}")
            return False
                    
    def cleanup_terminal_sessions(self):
        """Close any terminal sessions that have been left open for too long."""
        if not hasattr(self.__class__, 'active_terminal_sessions'):
            return
            
        # Get current time
        current_time = time.time()
        
        # First, process any windows that were specifically marked for removal
        if hasattr(self.__class__, '_windows_to_remove_after_closure'):
            for session_id in list(self.__class__._windows_to_remove_after_closure):
                if session_id in self.__class__.active_terminal_sessions:
                    logging.warning(f"🚨 FORCE REMOVING direct terminal session from tracking: {session_id}")
                    del self.__class__.active_terminal_sessions[session_id]
                    self.__class__._windows_to_remove_after_closure.remove(session_id)
        
        # Check all active sessions
        for session_id, session_info in list(self.__class__.active_terminal_sessions.items()):
            # Check if the last command was a file viewing command
            last_command = session_info.get("last_command", "")
            is_file_viewing_command = False
            
            if last_command:
                # Check for common file viewing commands
                file_view_commands = ["cat ", "less ", "head ", "tail ", "bat ", "view ", "vim ", "nano "]
                is_file_viewing_command = any(last_command.startswith(cmd) for cmd in file_view_commands)
            
            # Process direct terminal windows immediately (high priority cleanup) - UNLESS showing file contents
            is_direct_terminal = session_info.get("window_type") == self.WINDOW_TYPE_DIRECT_TERMINAL
            force_cleanup = session_info.get("force_cleanup", False)
            
            # Skip file viewing commands even for direct terminal windows
            if is_file_viewing_command:
                logging.warning(f"🚨 Skipping cleanup of file viewing terminal session: {session_id}")
                # Keep file view windows open longer - update their last_used time
                session_info["last_used"] = current_time
                continue
            elif is_direct_terminal or force_cleanup:
                logging.warning(f"🚨 Aggressive cleanup of direct terminal session: {session_id}")
                self._close_terminal_window(session_id)
                # Remove from tracking immediately
                del self.__class__.active_terminal_sessions[session_id]
                continue
            
            # Skip if already closed
            if not session_info.get("active", False):
                continue
                
            # Skip if it's a Claude Code session
            if session_info.get("is_claude_code", False):
                continue
                
            # Skip if it's marked to keep open
            if session_info.get("keep_open", False):
                continue
                
            # Handle BoardRoom planning sessions differently
            if session_id.startswith("boardroom_terminal_"):
                # Close if it's been inactive for more than 2 minutes
                last_used = session_info.get("last_used", session_info.get("created_at", 0))
                if current_time - last_used > 120:  # 2 minutes of inactivity
                    logging.warning(f"🚨 Cleaning up inactive BoardRoom planning terminal: {session_id}")
                    self._close_terminal_window(session_id)
            else:
                # For regular terminal sessions, close if open for more than 5 minutes
                created_at = session_info.get("created_at", 0)
                # Get custom expire time if set
                expire_after = session_info.get("expire_after", 300)  # Default 5 minutes
                if current_time - created_at > expire_after:
                    logging.warning(f"🚨 Cleaning up old terminal session: {session_id}")
                    self._close_terminal_window(session_id)
                    
    def close_boardroom_planning_terminal(self, current_terminal_id=None):
        """Close a specific BoardRoom terminal window at the end of a planning session.
        
        Args:
            current_terminal_id: The specific terminal session ID to close.
                               If None, will use the current boardroom_planning_terminal.
        """
        # Determine which terminal to close
        terminal_to_close = current_terminal_id
        
        # If no specific ID provided, use the current planning terminal
        if not terminal_to_close and hasattr(self.__class__, 'boardroom_planning_terminal'):
            terminal_to_close = self.__class__.boardroom_planning_terminal
            
        if not terminal_to_close:
            logging.warning("⚠️ No specific BoardRoom terminal ID to close")
            return False
            
        # Only close the specific terminal
        if hasattr(self.__class__, 'active_terminal_sessions') and terminal_to_close in self.__class__.active_terminal_sessions:
            session_info = self.__class__.active_terminal_sessions[terminal_to_close]
            if session_info.get("active", False):
                logging.warning(f"🚨 Closing specific BoardRoom planning terminal: {terminal_to_close}")
                # Close with a longer delay to ensure all output is visible
                session_info["close_after_result"] = True
                session_info["close_after_time"] = time.time() + 30  # Wait 30 seconds
                
                # Start a background thread to close after delay
                import threading
                closure_thread = threading.Thread(
                    target=self._delayed_terminal_closure,
                    args=(terminal_to_close, 30),
                    daemon=True
                )
                closure_thread.start()
                
                # Reset the planning terminal reference
                if hasattr(self.__class__, 'boardroom_planning_terminal'):
                    delattr(self.__class__, 'boardroom_planning_terminal')
                    
                # Clear the file content cache when the BoardRoom planning session ends
                if hasattr(self.__class__, 'file_content_cache'):
                    cache_size = len(self.__class__.file_content_cache)
                    if cache_size > 0:
                        logging.warning(f"🧹 Clearing file content cache with {cache_size} entries at end of BoardRoom session")
                        self.__class__.file_content_cache = {}
                    else:
                        logging.warning("🧹 No file content cache entries to clear at end of BoardRoom session")
                    
                return True
                
        return False

# Handler instance
handler = TerminalHandler()

# For direct testing
if __name__ == "__main__":
    # Test execution of simple command
    result = handler.execute("execute_command", {"command": "ls -la"})
    print(f"Execute command result: {result.data or result.result}")
    
    # Test creating a terminal session
    session_result = handler.execute("create_terminal_session", {"directory": "~"})
    print(f"Create session result: {session_result.data or session_result.result}")
    
    # If session was created successfully, send a command
    if session_result.success:
        session_id = session_result.metadata.get("session_id") or session_result.details.get("session_id")
        command_result = handler.execute("send_command", {
            "session_id": session_id, 
            "command": "echo 'Hello Terminal Handler'"
        })
        print(f"Send command result: {command_result.data or command_result.result}")
        
        # Get the output
        output_result = handler.execute("get_output", {"session_id": session_id})
        print(f"Output: {output_result.data or output_result.result}") 