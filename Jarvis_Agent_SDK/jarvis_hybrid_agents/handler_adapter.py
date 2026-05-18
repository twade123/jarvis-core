"""
Handler System Adapter

This module provides adapter functions that allow the OpenAI Agents SDK to work with
the existing Handler system without modifying any of its code. These functions adapt
the SDK's function_tool interface to the existing Handler API.
"""

import os
import re
import datetime
import json
import logging
import asyncio
import time
import inspect
from typing import Dict, List, Any, Optional, Callable, Union
import traceback
import sys
import functools
from openai import OpenAI
from pathlib import Path
import random
import importlib.util

# Add the project root to Python path to enable absolute imports
project_root = str(Path(__file__).parent.parent.parent.absolute())
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Import SDK components using absolute imports
try:
    from Jarvis_Agent_SDK.jarvis_sdk_agents.sdk_agents import function_tool
    from Jarvis_Agent_SDK.import_helper import get_unified_database
    from Jarvis_Agent_SDK.boardroom_connector import get_boardroom, track_request_journey_sync as track_request_journey, track_journey_step_sync, get_direct_tracking_interface
    from Jarvis_Agent_SDK.base import BaseHandler
except ImportError as e:
    logging.warning(f"Could not import SDK components: {e}")
    function_tool = lambda x: x
    get_unified_database = None
    get_boardroom = None
    
    # Create stub functions to prevent NoneType callable errors
    def track_request_journey_stub(request_id: str, task: any, system_id: str = "boardroom", journey_type: str = "conversation") -> str:
        """Stub function when tracking is not available"""
        return f"journey_{request_id}_{int(time.time())}"
    
    def track_journey_step_sync_stub(journey_id: str, step_name: str, description: str = None, step_type: str = None, error: str = None) -> bool:
        """Stub function when tracking is not available"""
        logging.info(f"Journey step [{step_name}]: {description}")
        return True
    
    track_request_journey = track_request_journey_stub
    track_journey_step_sync = track_journey_step_sync_stub
    get_direct_tracking_interface = None
    BaseHandler = object

# Import Core components using absolute imports
try:
    # Import config first to avoid circular imports
    from Core import config
    CONFIG = config.CONFIG
    load_api_key = config.load_api_key
    PATHS = config.PATHS
    API_KEYS = config.API_KEYS
    
    # Defer TrevorCore import to avoid circular import
    TrevorCore = None
except ImportError as e:
    logging.warning(f"Could not import Core components directly: {e}")
    TrevorCore = None
    CONFIG = {}
    load_api_key = None
    PATHS = {}
    API_KEYS = {}

# Use lazy imports to avoid circular dependencies
def get_handler_imports():
    """Get handler-related imports lazily to avoid circular dependencies."""
    try:
        # Import handler components using absolute imports
        from Handler import handler_board_room
        from Handler import handler_agent_builder
        from Handler import handler_swarm
        
        BoardRoom = handler_board_room.BoardRoom
        DialogueManager = handler_board_room.DialogueManager
        ClaudeHandler = handler_board_room.ClaudeHandler
        CodeExecutionHandler = handler_board_room.CodeExecutionHandler
        try:
            ConversationLogger = handler_board_room.ConversationLogger
        except AttributeError:
            # Create a simple stub if not available
            ConversationLogger = None
        ConversationControl = handler_board_room.ConversationControl
        
        return {
            'BoardRoom': BoardRoom,
            'DialogueManager': DialogueManager,
            'ClaudeHandler': ClaudeHandler,
            'CodeExecutionHandler': CodeExecutionHandler,
            'ConversationLogger': ConversationLogger,
            'ConversationControl': ConversationControl,
            'TrevorCore': TrevorCore,
            'CONFIG': CONFIG,
            'load_api_key': load_api_key,
            'PATHS': PATHS,
            'API_KEYS': API_KEYS,
            'agent_builder_module': handler_agent_builder,
            'swarm_module': handler_swarm
        }
    except Exception as e:
        logging.warning(f"Could not import handler components: {e}")
        return {}

def serialize_handler_response(obj):
    """Helper function to serialize Handler system responses"""
    if hasattr(obj, 'to_dict'):
        return obj.to_dict()
    if hasattr(obj, '__dict__'):
        return obj.__dict__
    return str(obj)

# Function tool to process a query using BoardRoom
@function_tool
async def process_with_boardroom(query: str, context: Optional[Dict[str, Any]] = None, 
                         task_breakdown: Optional[List[str]] = None) -> str:
    """
    Process a query using the existing BoardRoom Handler without modification.
    
    Args:
        query: The task or query to process
        context: Additional context information (optional)
        task_breakdown: Optional list of subtasks from Trevor Core's task breakdown
        
    Returns:
        str: The result from the BoardRoom Handler
    """
    try:
        # Enhance context with task breakdown if available
        enhanced_context = context or {}
        if task_breakdown and isinstance(task_breakdown, list):
            enhanced_context['task_breakdown'] = task_breakdown
            logging.info(f"Added Trevor Core's task breakdown ({len(task_breakdown)} subtasks) to BoardRoom context")
        
        # Run the synchronous call_boardroom in an executor to make it awaitable
        loop = asyncio.get_event_loop()
        boardroom_response = await loop.run_in_executor(None, call_boardroom, query, enhanced_context)
        return boardroom_response
    except Exception as e:
        error_message = str(e)
        if "api_key" in error_message.lower() or "openai" in error_message.lower():
            # Handle OpenAI API key error specifically
            return "I'm unable to access the BoardRoom planning system due to missing API configuration. " + \
                   "Using fallback planning capabilities instead. " + \
                   "I'll process this query using my built-in knowledge to provide strategic guidance."
        else:
            # General error fallback
            logging.error(f"Error calling BoardRoom: {e}")
            return f"I'll process this query using my built-in knowledge since the BoardRoom system is currently unavailable."

@function_tool
def use_handler_agent(agent_type: str, query: str, additional_context: Optional[Dict[str, Any]] = None) -> str:
    """
    Use a specific agent from the Handler system without modifying its implementation.
    
    Args:
        agent_type: The type of agent to use (e.g., "code_developer", "data_analyst")
        query: The query to process
        additional_context: Additional context information (optional)
        
    Returns:
        Results from the handler agent as a JSON string
    """
    try:
        # Call the helper function directly
        return call_agent(agent_type, query, additional_context)
    except Exception as e:
        error_msg = f"Error in use_handler_agent: {str(e)}"
        print(f"ERROR [Internal Tool Error]: An error occurred with the 'use_handler_agent' when attempting to use the {agent_type} agent. {error_msg}")
        traceback.print_exc()
        return f"I'll help you with your query using my built-in knowledge since there was an issue with the {agent_type} agent."

@function_tool
def use_handler_swarm(query: str, agents: Optional[List[str]] = None, context: Optional[Dict[str, Any]] = None) -> str:
    """
    Use the Handler swarm system without modifying its implementation.
    
    Args:
        query: The query to process
        agents: List of agent types to include in the swarm (optional)
        context: Additional context information (optional)
        
    Returns:
        Results from the handler swarm as a JSON string
    """
    try:
        # Call the helper function directly
        return call_swarm(query, agents, context)
    except Exception as e:
        error_msg = f"Error in use_handler_swarm: {str(e)}"
        print(f"ERROR [Internal Tool Error]: An error occurred with the 'use_handler_swarm'. {error_msg}")
        traceback.print_exc()
        return f"I'll help you with your query using my built-in knowledge since there was an issue with the agent swarm."

# Helper functions for the interface to use tools manually
def call_boardroom(query: str, context: Optional[Dict[str, Any]] = None) -> str:
    """Call the BoardRoom with appropriate error handling.
    
    Args:
        query: The query to process
        context: Additional context information (optional) - can include
                Trevor Core's task_breakdown or other enhancing metadata
        
    Returns:
        str: The response from BoardRoom
    """
    try:
        # Check for special handler-related queries
        if _is_handler_info_request(query):
            return _handle_handler_info_request(query)
        
        # Get handler imports
        handler_imports = get_handler_imports()
        
        # Set up API key variable so it's available for imports
        api_key = None
        
        # Use Core/config.py to configure OpenAI API key
        try:
            CONFIG = handler_imports.get('CONFIG', {})
            load_api_key = handler_imports.get('load_api_key')
            
            # Try to load the API key if not already set
            if not CONFIG.get('OPENAI_API_KEY'):
                api_key = load_api_key('OPENAI') if load_api_key else None
                if api_key:
                    CONFIG['OPENAI_API_KEY'] = api_key
                    # Set the environment variable for OpenAI library to use
                    import os
                    os.environ["OPENAI_API_KEY"] = api_key
                else:
                    api_key = CONFIG.get('OPENAI_API_KEY')
            else:
                api_key = CONFIG.get('OPENAI_API_KEY')
                
        except Exception as e:
            logging.warning(f"Could not configure API key: {e}")
            # Try to get API key from environment variable as fallback
            import os
            api_key = os.environ.get("OPENAI_API_KEY")

        # Get BoardRoom and DialogueManager classes
        BoardRoom = handler_imports.get('BoardRoom')
        DialogueManager = handler_imports.get('DialogueManager')
        TrevorCore = handler_imports.get('TrevorCore')
        
        if not BoardRoom:
            # Define a stub BoardRoom class if import failed
            class BoardRoom:
                def __init__(self, orchestrator_bridge=None, orchestrated_intelligence=None):
                    self.orchestrator_bridge = orchestrator_bridge
                    self.orchestrated_intelligence = orchestrated_intelligence
                
                def process_query(self, query, context=None):
                    return "BoardRoom not available"
        
        if not DialogueManager:
            class DialogueManager:
                def __init__(self):
                    self.required_consensus = 0.8
        
        # Use orchestrator bridge pattern instead of direct Trevor Core access
        try:
            # Import orchestrator bridge and intelligence
            from .. import boardroom_orchestrator_bridge
            from ..jarvis_orchestrated_intelligence import get_orchestrator_intelligence_instance
            
            orchestrator_bridge = boardroom_orchestrator_bridge
            orchestrated_intelligence = get_orchestrator_intelligence_instance()
            
            if orchestrated_intelligence is None:
                raise Exception("No orchestrated intelligence instance available")
        except Exception:
            # Create a stub for orchestrator bridge if not available
            class OrchestratorBridgeStub:
                def __init__(self):
                    self.logger = logging.getLogger("OrchestratorBridgeStub")
                
                async def get_task_complexity_analysis(self, orchestrated_intelligence, query):
                    return f"Orchestrator bridge stub processing: {query}"
                
                async def get_task_breakdown(self, orchestrated_intelligence, query):
                    return f"Orchestrator bridge stub breakdown: {query}"
            
            orchestrator_bridge = OrchestratorBridgeStub()
            orchestrated_intelligence = None
        
        # Create a subclass of BoardRoom that fixes the OpenAI client initialization
        if api_key:
            from openai import OpenAI
            import os  # Make sure os is imported here too to avoid scope issues
            
            # Create a patched version of AgentBuilder
            try:
                from Handler.handler_agent_builder import AgentBuilder as OriginalAgentBuilder
                
                class FixedAgentBuilder(OriginalAgentBuilder):
                    def __init__(self):
                        # Skip the parent's __init__ which creates OpenAI client without API key
                        # And initialize everything we need manually
                        self.agents = {}
                        self.gpt_handler = OpenAI(api_key=api_key)
                        # Add any other initialization needed here
            except ImportError:
                FixedAgentBuilder = None
            
            class FixedBoardRoom(BoardRoom):
                def __init__(self, orchestrator_bridge=None, orchestrated_intelligence=None):
                    """Initialize the BoardRoom with proper API key and orchestrator bridge."""
                    self.client = OpenAI(api_key=api_key)
                    self.orchestrator_bridge = orchestrator_bridge
                    self.orchestrated_intelligence = orchestrated_intelligence
                    # Initialize without passing required_consensus
                    self.dialogue_manager = DialogueManager()
                    # Set required_consensus after initialization if needed
                    self.dialogue_manager.required_consensus = 0.9
                    
                    # Get handler imports
                    handler_components = get_handler_imports()
                    ClaudeHandler = handler_components.get('ClaudeHandler')
                    CodeExecutionHandler = handler_components.get('CodeExecutionHandler')
                    ConversationLogger = handler_components.get('ConversationLogger')
                    ConversationControl = handler_components.get('ConversationControl')
                    
                    self.claude_handler = ClaudeHandler() if ClaudeHandler else None
                    # Fix the OpenAI client initialization by directly providing the API key
                    self.gpt_handler = OpenAI(api_key=api_key)
                    
                    # Add analyze_request method to OpenAI client
                    if not hasattr(self.gpt_handler, 'analyze_request'):
                        setattr(self.gpt_handler, 'analyze_request', self._openai_analyze_request)
                    
                    self.code_handler = CodeExecutionHandler() if CodeExecutionHandler else None
                    # Use our fixed AgentBuilder if available
                    self.agent_builder = FixedAgentBuilder() if FixedAgentBuilder else None
                    self.active_agents = {}
                    
                    # Initialize other attributes that might be set in the parent class
                    # Use the correct parameter for ConversationLogger (db_path instead of storage_dir)
                    import os  # Add os import here to ensure it's available in this scope
                    boardroom_db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                                                    "Database", "v2", "conversations.db")
                    self.conversation_logger = ConversationLogger(db_path=boardroom_db_path) if ConversationLogger else None
                    self.conversation_control = ConversationControl() if ConversationControl else None
                    self.max_thread_size = 10000
                    
                    # Add complexity patterns for request complexity detection
                    self.complexity_patterns = {
                        'code_generation': r'(write|create|generate|implement|develop)\s+(code|script|function|program|class)',
                        'data_analysis': r'(analyze|examine|study|investigate|explore)\s+(data|information|results|patterns)',
                        'research': r'(research|find|search|look\s+up|investigate|explore)',
                        'simple_query': r'(what\s+is|how\s+to|tell\s+me|explain|define|show)'
                    }
                    
                    # Complexity thresholds for time and token limits
                    self.complexity_thresholds = {
                        'low': {'max_time': 10, 'token_limit': 2000},
                        'medium': {'max_time': 15, 'token_limit': 3000},
                        'high': {'max_time': 25, 'token_limit': 4000},
                        'very_high': {'max_time': 40, 'token_limit': 8000}
                    }
                    
                def process_query(self, query, context=None):
                    """
                    Process a query using the BoardRoom's capabilities.
                    
                    This implementation fixes the missing method that was causing the
                    'FixedBoardRoom' object has no attribute 'process_query' error.
                    
                    Args:
                        query: The query to process
                        context: Additional context information (optional)
                        
                    Returns:
                        The response from the BoardRoom
                    """
                    try:
                        # Initialize tracking for this query (now using sync version)
                        journey_id = track_request_journey(
                            request_id=f"query_{int(time.time())}",
                            task={"query": query, "context": context},
                            system_id="boardroom",
                            journey_type="boardroom_query"
                        )
                        
                        # Log the start of processing
                        track_journey_step_sync(
                            journey_id=journey_id,
                            step_name="start_processing",
                            description=f"Starting to process query: {query[:50]}...",
                            step_type="processing"
                        )
                        
                        # Get query complexity
                        complexity = self._determine_complexity(query)
                        
                        # Track complexity analysis
                        track_journey_step_sync(
                            journey_id=journey_id,
                            step_name="complexity_analysis",
                            description=f"Query complexity: {complexity}",
                            step_type="analysis"
                        )
                        
                        # Check for Trevor's breakdown data - THIS IS THE CRITICAL FIX!
                        trevor_breakdown = context.get("task_breakdown") if context else None
                        trevor_analysis = context.get("trevor_analysis") if context else None
                        workspace_id = context.get("workspace_id") if context else None
                        
                        if trevor_breakdown and len(trevor_breakdown) > 0:
                            # TREVOR BREAKDOWN MODE - Use Trevor's detailed analysis!
                            logging.info(f"🎪 BOARDROOM USING TREVOR BREAKDOWN: {len(trevor_breakdown)} subtasks")
                            
                            system_prompt = (
                                "You are Claude, working with GPT-4 in a BoardRoom collaboration. "
                                "Trevor Core has already broken down this complex task into subtasks. "
                                "Your job is to create a comprehensive execution plan using Trevor's analysis. "
                                "\n\nTrevor's Task Breakdown:\n" + 
                                "\n".join([f"- {task}" for task in trevor_breakdown]) +
                                f"\n\nTrevor's Analysis: {trevor_analysis}" +
                                f"\n\nWorkspace ID: {workspace_id}" +
                                "\n\nCreate a detailed execution strategy incorporating Trevor's breakdown."
                            )
                            
                            track_journey_step_sync(
                                journey_id=journey_id,
                                step_name="processing_approach",
                                description=f"Using Trevor breakdown mode with {len(trevor_breakdown)} subtasks",
                                step_type="processing"
                            )
                            
                            # Enhanced prompt with Trevor's breakdown
                            enhanced_query = f"Original Request: {query}\n\nTrevor Core Analysis Available:\n- Subtasks: {len(trevor_breakdown)}\n- Complexity Analysis: {trevor_analysis.get('complexity', 'complex') if trevor_analysis else 'complex'}\n\nPlease create a comprehensive plan using this analysis."
                            
                        elif context and context.get("query_type") == "strategic_planning":
                            # Planning mode with GPT-4
                            system_prompt = (
                                "You are a strategic planning assistant specialized in creating structured plans. "
                                "Create a clear, actionable plan for this request. Include specific steps, timelines, "
                                "and considerations for successful implementation."
                            )
                            enhanced_query = query
                            
                            track_journey_step_sync(
                                journey_id=journey_id,
                                step_name="processing_approach",
                                description="Using strategic planning mode",
                                step_type="processing"
                            )
                            
                        else:
                            # Standard mode
                            system_prompt = (
                                "You are a helpful assistant that provides clear, accurate, and concise answers."
                            )
                            enhanced_query = query
                            
                            track_journey_step_sync(
                                journey_id=journey_id,
                                step_name="processing_approach",
                                description="Using standard processing mode",
                                step_type="processing"
                            )
                        
                        # Make the API call with enhanced context
                        response = self.gpt_handler.chat.completions.create(
                            model="gpt-4",
                            messages=[
                                {"role": "system", "content": system_prompt},
                                {"role": "user", "content": enhanced_query}
                            ],
                        )
                        
                        result = response.choices[0].message.content
                        
                        # Track completion
                        track_journey_step_sync(
                            journey_id=journey_id,
                            step_name="completion",
                            description="Processing completed successfully",
                            step_type="completion"
                        )
                        
                        return result
                        
                    except Exception as e:
                        error_msg = f"Error in BoardRoom processing: {str(e)}"
                        logging.error(error_msg)
                        
                        # Track error if journey_id is defined
                        if 'journey_id' in locals():
                            track_journey_step_sync(
                                journey_id=journey_id,
                                step_name="error",
                                description=error_msg,
                                step_type="error",
                                error=str(e)
                            )
                        
                        # Provide a fallback response
                        return f"I apologize, but I encountered an error while processing your request. Error: {str(e)}"
                
                def _determine_complexity(self, query):
                    """Analyze the complexity of a query using pattern matching."""
                    query_lower = query.lower()
                    
                    # Check patterns for complexity indicators
                    complexity_score = 0
                    
                    # Check for code generation (high complexity)
                    if re.search(self.complexity_patterns['code_generation'], query_lower):
                        complexity_score += 3
                    
                    # Check for data analysis (medium-high complexity)
                    if re.search(self.complexity_patterns['data_analysis'], query_lower):
                        complexity_score += 2
                    
                    # Check for research (medium complexity)
                    if re.search(self.complexity_patterns['research'], query_lower):
                        complexity_score += 1.5
                    
                    # Check for simple queries (low complexity)
                    if re.search(self.complexity_patterns['simple_query'], query_lower):
                        complexity_score += 0.5
                    
                    # Adjust based on query length (longer queries tend to be more complex)
                    words = query.split()
                    if len(words) > 50:
                        complexity_score += 1
                    elif len(words) > 20:
                        complexity_score += 0.5
                    
                    # Determine complexity level based on score
                    if complexity_score >= 3:
                        return "high"
                    elif complexity_score >= 1.5:
                        return "medium"
                    else:
                        return "low"
                
                async def _openai_analyze_request(self, request: str) -> dict:
                    """Analyze a request using OpenAI and provide structured insights."""
                    try:
                        system_prompt = (
                            "Analyze this request thoroughly. Identify key tasks, required knowledge, "
                            "complexity factors, and the best approach to handling it. "
                            "Return a JSON with the following structure: "
                            "{'insights': [], 'complexity': 'low|medium|high', 'approach': '', 'steps': [], 'criteria': []}"
                        )
                        
                        response = self.gpt_handler.chat.completions.create(
                            model="gpt-4",
                            messages=[
                                {"role": "system", "content": system_prompt},
                                {"role": "user", "content": request}
                            ],
                            response_format={"type": "json_object"}
                        )
                        
                        analysis_text = response.choices[0].message.content
                        try:
                            analysis = json.loads(analysis_text)
                        except json.JSONDecodeError:
                            # Fallback if response isn't valid JSON
                            analysis = {
                                "insights": ["Unable to parse analysis"],
                                "complexity": "medium",
                                "approach": "Standard processing",
                                "steps": ["Process the request directly"],
                                "criteria": ["Clear response"]
                            }
                            
                        return analysis
                        
                    except Exception as e:
                        logging.error(f"Error in OpenAI analysis: {str(e)}")
                        return {
                            "insights": ["Analysis failed"],
                            "complexity": "medium",
                            "approach": "Fallback processing",
                            "steps": ["Process the request directly"],
                            "criteria": ["Provide available information"]
                        }
            
            # Use our fixed BoardRoom instead of the original
            boardroom = FixedBoardRoom(orchestrator_bridge, orchestrated_intelligence)
        else:
            # If we can't get an API key, use the original BoardRoom and let it fail
            # This will be caught by our exception handler
            boardroom = BoardRoom(orchestrator_bridge, orchestrated_intelligence)
        
        # Default context if not provided
        if context is None:
            context = {}
            
        result = boardroom.process_query(query, context)
        return result
    except Exception as e:
        logging.error(f"Error calling BoardRoom: {e}")
        raise  # Re-raise to let process_with_boardroom handle it with appropriate fallback

def _is_handler_info_request(query: str) -> bool:
    """Check if the query is asking for information about handlers."""
    query_lower = query.lower()
    
    # Check for queries about listing handlers
    if any(pattern in query_lower for pattern in [
        'what handlers', 'list handlers', 'show handlers', 'available handlers',
        'handler list', 'handlers available', 'which handlers'
    ]):
        return True
    
    # Check for queries about specific handler capabilities
    if 'handler' in query_lower and any(word in query_lower for word in [
        'capabilities', 'can do', 'functions', 'methods', 'actions', 'operations',
        'what can', 'how to use', 'tell me about', 'explain'
    ]):
        return True
    
    return False

def _handle_handler_info_request(query: str) -> str:
    """Handle requests for information about handlers."""
    query_lower = query.lower()
    
    try:
        # Import necessary modules
        import os
        import inspect
        from pathlib import Path
        import importlib.util
        
        # Get the Handler directory
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        handler_dir = Path(os.path.join(project_root, 'Handler'))
        
        # Find all handler files
        handler_files = [
            f for f in handler_dir.glob("handler_*.py")
            if f.name not in ['handler_all.py', 'handler_base.py']
        ]
        
        # Check if asking about a specific handler
        specific_handler = None
        for handler_file in handler_files:
            handler_name = handler_file.stem.split('_')[1]
            if handler_name in query_lower:
                specific_handler = handler_name
                break
        
        if specific_handler:
            # Provide information about the specific handler
            return _get_specific_handler_info(specific_handler, handler_dir)
        else:
            # Provide a list of all available handlers
            return _get_all_handlers_info(handler_files)
    
    except Exception as e:
        logging.error(f"Error handling handler info request: {e}")
        return f"I encountered an error while retrieving handler information: {str(e)}"

def _get_all_handlers_info(handler_files) -> str:
    """Get information about all available handlers."""
    try:
        handlers_info = []
        
        for handler_file in handler_files:
            try:
                # Extract handler name from filename
                handler_name = handler_file.stem.split('_')[1]
                
                # Load the module
                spec = importlib.util.spec_from_file_location(f"Handler.{handler_file.stem}", handler_file)
                if spec is None or spec.loader is None:
                    continue
                    
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                
                # Get the handler class
                handler_class_name = f"{handler_name.capitalize()}Handler"
                if not hasattr(module, handler_class_name):
                    continue
                
                handler_class = getattr(module, handler_class_name)
                
                # Get handler docstring
                doc = handler_class.__doc__ or "No documentation available"
                
                # Add to the list
                handlers_info.append({
                    "name": handler_name,
                    "description": doc.strip().split('\n')[0]  # First line of docstring
                })
                
            except Exception as e:
                logging.error(f"Error loading handler from {handler_file}: {e}")
                continue
        
        # Format the output
        if not handlers_info:
            return "No handlers found in the system."
        
        output = "Available Handlers:\n\n"
        
        for info in sorted(handlers_info, key=lambda x: x["name"]):
            output += f"- {info['name']}: {info['description']}\n"
        
        output += "\nFor more information about a specific handler, ask about it by name."
        
        return output
    
    except Exception as e:
        logging.error(f"Error getting all handlers info: {e}")
        return f"I encountered an error while retrieving handler information: {str(e)}"

def _get_specific_handler_info(handler_name: str, handler_dir: Path) -> str:
    """Get detailed information about a specific handler."""
    try:
        # Find the handler file
        handler_file = handler_dir / f"handler_{handler_name}.py"
        
        if not handler_file.exists():
            return f"Handler '{handler_name}' not found."
        
        # Load the module
        spec = importlib.util.spec_from_file_location(f"Handler.handler_{handler_name}", handler_file)
        if spec is None or spec.loader is None:
            return f"Could not load handler '{handler_name}'."
            
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        # Get the handler class
        handler_class_name = f"{handler_name.capitalize()}Handler"
        if not hasattr(module, handler_class_name):
            return f"Handler class '{handler_class_name}' not found in module."
        
        handler_class = getattr(module, handler_class_name)
        
        # Get handler docstring
        doc = handler_class.__doc__ or "No documentation available"
        
        # Get handler methods (actions)
        actions = []
        for attr_name, attr_value in inspect.getmembers(handler_class, predicate=inspect.isfunction):
            if not attr_name.startswith('_'):
                action_doc = attr_value.__doc__ or "No documentation available"
                actions.append({
                    "name": attr_name,
                    "description": action_doc.strip().split('\n')[0]  # First line of docstring
                })
        
        # Format the output
        output = f"Handler: {handler_name}\n\n"
        output += f"Description:\n{doc.strip()}\n\n"
        
        if actions:
            output += "Available Actions:\n\n"
            
            for action in sorted(actions, key=lambda x: x["name"]):
                output += f"- {action['name']}: {action['description']}\n"
        else:
            output += "No actions found for this handler."
        
        return output
    
    except Exception as e:
        logging.error(f"Error getting specific handler info: {e}")
        return f"I encountered an error while retrieving information about handler '{handler_name}': {str(e)}"

def call_agent(agent_type: str, query: str, additional_context: Optional[Dict[str, Any]] = None) -> str:
    """Helper function to call a specific agent directly"""
    try:
        # Import AgentBuilder lazily using import_helper
        agent_builder_module = get_handler_imports().get('agent_builder_module')
        if not agent_builder_module:
            logging.error("Could not import AgentBuilder")
            return f"I'll help you with your query using my built-in knowledge since there was an issue loading the {agent_type} agent."
        
        AgentBuilder = agent_builder_module.AgentBuilder
        
        # Initialize the agent builder
        builder = AgentBuilder()
        
        # Create the agent using the existing implementation
        agent = builder.create_agent(agent_type)
        
        # Default context if not provided
        if additional_context is None:
            additional_context = {}
        
        # Process the query with the agent
        response = agent.process_query(query, additional_context)
        
        # Format the response for the SDK
        return json.dumps(response, default=serialize_handler_response, indent=2)
    except Exception as e:
        error_msg = f"Error calling agent {agent_type}: {str(e)}"
        print(f"ERROR: {error_msg}")
        traceback.print_exc()
        return f"I'll help you with your query using my built-in knowledge since there was an issue with the {agent_type} agent."

def call_swarm(query: str, agents: Optional[List[str]] = None, context: Optional[Dict[str, Any]] = None) -> str:
    """Helper function to call the swarm directly"""
    try:
        # Import SwarmHandler lazily using import_helper
        swarm_module = get_handler_imports().get('swarm_module')
        if not swarm_module:
            logging.error("Could not import SwarmHandler")
            return f"I'll help you with your query using my built-in knowledge since there was an issue loading the agent swarm."
        
        SwarmHandler = swarm_module.SwarmHandler
        
        # Initialize the swarm handler
        swarm = SwarmHandler()
        
        # Default values if not provided
        if agents is None:
            agents = ["coordinator", "code_developer", "data_analyst"]
        
        if context is None:
            context = {}
        
        # Set up the swarm with specified agents - handling async properly
        loop = asyncio.get_event_loop()
        for agent_type in agents:
            # Run the async method in the event loop
            loop.run_until_complete(swarm.register_agent(agent_type))
        
        # Process the query with the swarm (handling async if needed)
        try:
            response = swarm.process_query(query, context)
        except AttributeError:
            # If process_query is also async, try running it in the event loop
            try:
                response = loop.run_until_complete(swarm.process_query(query, context))
            except Exception as e:
                return json.dumps({"error": f"Error processing with swarm: {str(e)}"}, indent=2)
        
        # Format the response for the SDK
        return json.dumps(response, default=serialize_handler_response, indent=2)
    except Exception as e:
        error_msg = f"Error calling swarm: {str(e)}"
        print(f"ERROR: {error_msg}")
        traceback.print_exc()
        return f"I'll help you with your query using my built-in knowledge since there was an issue with the agent swarm."

def track_request_journey_local(request_id: str, task: Any, system_id: str = "boardroom", journey_type: str = "conversation") -> str:
    """Track a request journey through the BoardRoom if available"""
    try:
        # Get handler imports
        handler_imports = get_handler_imports()
        BoardRoom = handler_imports.get('BoardRoom')
        
        if BoardRoom:
            # Create BoardRoom instance
            boardroom = BoardRoom()
            
            # Call track_request_journey if available
            if hasattr(boardroom, 'track_request_journey'):
                return boardroom.track_request_journey(
                    request_id=request_id,
                    task=task,
                    system_id=system_id,
                    journey_type=journey_type
                )
        
        # If we got here, it means we either:
        # 1. Couldn't import track_request_journey
        # 2. Or track_request_journey wasn't callable
        # Create journey directly in database
        try:
            from Jarvis_Agent_SDK.database_directory import get_database_directory
            db_directory = get_database_directory()
            if db_directory:
                conn = db_directory.get_connection("journey_tracking")
                if conn:
                    try:
                        journey_id = f"{system_id}_{int(time.time())}_{request_id}"
                        timestamp = time.time()
                        
                        # Insert the journey record
                        cursor = conn.cursor()
                        cursor.execute(
                            """
                            INSERT INTO request_journeys 
                            (journey_id, request_id, system_id, journey_type, task, start_time, current_state, last_updated) 
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                            """,
                            (
                                journey_id,
                                request_id,
                                system_id,
                                journey_type,
                                json.dumps(task) if task else None,
                                timestamp,
                                "initialized",
                                timestamp
                            )
                        )
                        
                        # Commit the changes
                        conn.commit()
                        conn.close()
                        
                        logging.info(f"Created direct database journey {journey_id} for request {request_id}")
                        return journey_id
                    except Exception as db_error:
                        logging.error(f"Error creating direct database journey: {str(db_error)}")
                        conn.close()
            
            # Ultimate fallback if everything else fails
            journey_id = f"{system_id}_{int(time.time())}_{request_id}"
            logging.info(f"Created fallback journey {journey_id} for request {request_id}")
            
            # Make sure the journey is actually tracked in the database
            try:
                from Jarvis_Agent_SDK.boardroom_connector import ensure_journey_exists
                ensure_journey_exists(journey_id, "initialized")
            except Exception as ensure_error:
                logging.warning(f"Could not ensure journey exists: {str(ensure_error)}")
                
            return journey_id
        except Exception as fallback_error:
            logging.error(f"Error in fallback journey creation: {str(fallback_error)}")
            journey_id = f"{system_id}_{int(time.time())}_{request_id}"
            
            # Even after error, try to ensure the journey exists
            try:
                from Jarvis_Agent_SDK.boardroom_connector import ensure_journey_exists
                ensure_journey_exists(journey_id, "initialized")
            except:
                pass
                
            return journey_id
        
    except Exception as e:
        logging.error(f"Error in track_request_journey: {e}")
        # Generate a minimal journey ID as fallback
        journey_id = f"fallback_{system_id}_{int(time.time())}_{request_id}"
        
        # Even after total failure, try to ensure the journey exists
        try:
            from Jarvis_Agent_SDK.boardroom_connector import ensure_journey_exists
            ensure_journey_exists(journey_id, "initialized")
        except:
            pass
            
        return journey_id

def track_journey_step(journey_id: str, step_name: str, description: str = None, step_type: str = None) -> bool:
    """Track a step in a request journey"""
    try:
        # Get handler imports
        handler_imports = get_handler_imports()
        BoardRoom = handler_imports.get('BoardRoom')
        
        if BoardRoom:
            # Create BoardRoom instance
            boardroom = BoardRoom()
            
            # Call track_journey_step if available
            if hasattr(boardroom, 'track_journey_step'):
                # Get the parameters the function accepts
                sig = inspect.signature(boardroom.track_journey_step)
                param_names = [param for param in sig.parameters]
                
                # Prepare basic arguments
                kwargs = {
                    'journey_id': journey_id,
                    'step_name': step_name
                }
                
                # Add optional parameters only if they are in the function signature
                if 'description' in param_names and description is not None:
                    kwargs['description'] = description
                if 'step_type' in param_names and step_type is not None:
                    kwargs['step_type'] = step_type
                    
                # Call the method with only the parameters it accepts
                return boardroom.track_journey_step(**kwargs)
        
        # Fallback if BoardRoom not available
        logging.info(f"Tracked step '{step_name}' in journey {journey_id}")
        return True
        
    except Exception as e:
        logging.error(f"Error in track_journey_step: {e}")
        return False

# Note: The functions above are designed to adapt to the existing Handler API.
# If the actual API signatures are different, these functions should be adjusted
# to match the existing implementation without changing the Handler code. 