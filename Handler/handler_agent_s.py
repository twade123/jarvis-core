#!/usr/bin/env python3

"""
Agent-S Handler - Comprehensive Integration Framework for Agent-S with Jarvis

This module provides a seamless integration between the Agent-S UI automation framework
and the Jarvis ecosystem, enabling natural language-driven control of desktop applications
and user interface interactions. It implements the official Agent-S architecture with
enhanced integration for Jarvis.

Agent-S Architecture Overview:
Agent-S is a hierarchical framework for UI automation consisting of:
1. Manager (Planner) - Creates a DAG (Directed Acyclic Graph) of subtasks needed to complete a task
2. Worker (Executor) - Executes individual subtasks through direct UI interaction
3. ACI (Application Control Interface) - Platform-specific interface for UI interaction
4. Knowledge Base - Stores experiences from previous tasks to improve future performance

Key Features:
- Hierarchical task planning and execution via Agent-S2 or platform-specific implementations
- Automatic selection between S1 (macOS-specific) and S2 (cross-platform) implementations
- Seamless handling of complex multi-step UI interactions
- Screenshot-based UI understanding and navigation
- Accessibility tree integration for improved UI element recognition
- Perplexica web search integration for knowledge retrieval
- Memory systems for improving performance over time:
  - Narrative memory - Task-level learning
  - Episodic memory - Subtask-level learning

Integration Capabilities:
- Streamlined execution of UI automation tasks via natural language commands
- Automatic detection and configuration of platform-specific Agent-S components
- Cross-platform support (macOS, Windows, Linux) with optimized implementations
- Integration with Agent-S enhancement package for improved performance via:
  - Intelligence-driven task analysis and execution path selection
  - Hotkey shortcuts for common operations to improve efficiency
  - Handler-based shortcuts for specialized domain-specific tasks
- Multi-step UI task execution with appropriate failure handling and timeouts
- Support for AppleScript execution on macOS for enhanced system integration
- Timeout protection and failure recovery to prevent hung processes

Usage Examples:
- Control desktop applications: "Open Safari and search for news about AI"
- Perform complex workflows: "Download the latest sales report, create a summary in Excel"
- Automate repetitive tasks: "Check my email and respond to any messages from my boss"
- Handle cross-application workflows: "Find the image in my downloads and add it to my presentation"
"""

import os
import sys
import time
import json
import logging
import pyautogui
import io
import signal
import traceback
import platform
import asyncio
import concurrent.futures
from datetime import datetime
from typing import Dict, List, Any, Optional, Union, Tuple
from PIL import Image

# Check if agent_s_enhancement package is available
try:
    from agent_s_enhancement import (
        get_intelligence_connector,
        get_hotkey_registry,
        get_handler_shortcuts,
        get_intelligent_execution_manager
    )
    ENHANCEMENTS_AVAILABLE = True
    print("Agent-S enhancements are available and will be used for improved performance")
except ImportError:
    ENHANCEMENTS_AVAILABLE = False
    print("Agent-S enhancements are not available (agent_s_enhancement package not found)")
    pass

# Import from your configuration system
try:
    from Core.config import CONFIG, load_api_key, PATHS, API_KEYS
    from pathlib import Path, PurePath
except ImportError as e:
    print(f"Error importing config module: {e}")
    print("Will use environment variables or directly provided API keys")
    from pathlib import Path, PurePath

# Import Agent-S components with lazy loading for problematic imports
try:
    from gui_agents.s2.agents.agent_s import AgentS2
    print("Successfully imported AgentS2")
    
    # Use lazy import for OSWorldACI to avoid hanging during module import
    # OSWorldACI will be imported when actually needed in _initialize_agent_s_components()
    OSWorldACI = None
    _osworld_aci_import_error = None
    
    print("Successfully imported Agent-S2 components (OSWorldACI will be lazy-loaded)")
    
    # Also import S1 components if we're on macOS for accessibility tree support
    if platform.system() == "Darwin":
        try:
            from gui_agents.s1.aci.MacOSACI import UIElement
            print("Successfully imported macOS UIElement support")
        except ImportError:
            print("Note: macOS UIElement support not available - this is optional")
except ImportError as e:
    print(f"Error importing Agent-S components: {e}")
    print("Make sure gui-agents is installed correctly")
    print("Current sys.path:", sys.path)
    sys.exit(1)

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(name)s - %(message)s'
)
logger = logging.getLogger("AgentSHandler")

class AgentSHandler:
    """
    Comprehensive handler for executing UI automation tasks using Agent-S.
    
    This handler implements the official Agent-S integration approach while
    providing enhanced functionality for Jarvis ecosystem integration. It supports
    both direct UI automation and intelligence-driven execution strategies.
    
    The handler operates in three main phases:
    1. Initialization - Detects platform, configures environment, and initializes the appropriate
       Agent-S implementation (S1 for macOS, S2 for cross-platform)
    2. Task Planning - Analyzes the task using hierarchical decomposition to create a directed
       acyclic graph (DAG) of subtasks
    3. Task Execution - Executes subtasks sequentially with feedback loops and recovery mechanisms
    
    Enhanced features include:
    - Automatic API key management for LLM providers (Anthropic Claude, OpenAI)
    - Platform-specific optimizations for macOS, Windows, and Linux
    - Unrestricted mode for full system access capabilities
    - Integration with Perplexica for enhanced web search capabilities
    - Timeout protection to prevent hung processes during execution
    - Detailed execution history tracking for analytics and debugging
    - Intelligent execution optimization through the agent_s_enhancement package
    - Hotkey shortcut detection for efficient UI navigation
    - Handler-based shortcuts for bypassing UI when appropriate
    - Continuous conversation mode for extended interactions
    
    This implementation preserves the hierarchical design of Agent-S while adding
    robustness features needed for production use in the Jarvis ecosystem.
    """
    
    def __init__(
        self,
        api_key_env: Dict[str, str] = None,
        model: str = None,
        provider: str = None,
        use_enhancements: bool = True,
        execution_preference: str = "auto",  # "auto", "ui", "hotkey", or "handler"
        conversation_mode: bool = False      # Enable continuous conversation mode
    ):
        """
        Initialize the Agent-S handler with appropriate configuration.
        
        This handler provides seamless integration with the Agent-S UI automation
        framework, enabling natural language control of desktop applications. It
        automatically configures the appropriate components based on the platform
        and available resources.
        
        Args:
            api_key_env: Dictionary of API keys to set as environment variables
            model: LLM model to use (defaults to claude-3-7-sonnet-20250219 for Anthropic
                  or gpt-4o for OpenAI)
            provider: LLM provider ('anthropic' or 'openai')
            use_enhancements: Whether to use agent_s_enhancement package for improved
                            performance through intelligence, hotkeys, and handler shortcuts
            execution_preference: Preferred execution method:
                                - "auto": Automatically select the best method
                                - "ui": Always use UI automation
                                - "hotkey": Prefer hotkey shortcuts when available
                                - "handler": Prefer handler shortcuts when available
            conversation_mode: Whether to enable continuous conversation mode, which
                             maintains agent state between requests for extended interactions
        """
        logger.info("Initializing AgentSHandler")
        
        # Conversation mode attributes
        self.conversation_mode = conversation_mode
        self.conversation_active = False
        self.conversation_history = []
        self.last_observation = None
        self.last_task_description = None
        self.last_agent_response = None
        self.conversation_id = None
        
        # Detect platform using standard approach
        self.platform = platform.system().lower()
        logger.info(f"Detected platform: {self.platform}")
        
        # Setup API keys
        self._setup_api_keys(api_key_env)
        
        # Configure Perplexica for web search capability
        self._configure_perplexica()
        
        # Enable unrestricted mode (preserving valuable functionality)
        self._enable_unrestricted_mode()
        
        # Configure engine parameters with proper model and provider
        self.provider, self.model = self._select_provider_and_model(provider, model)
        self.engine_params = {
            "engine_type": self.provider,
            "model": self.model,
        }
        logger.info(f"Using provider: {self.provider} with model: {self.model}")
        
        # Initialize Agent-S components
        self._initialize_agent_s_components()
        
        # Keep track of execution history (valuable from original implementation)
        self.execution_history = []
        
        # Configure for enhanced execution if available
        self.enhanced_manager = None
        self.use_enhancements = use_enhancements and ENHANCEMENTS_AVAILABLE
        
        # Store parameters for lazy loading the enhanced manager later
        self._api_key_env = api_key_env
        self._execution_preference = execution_preference
        
        # We'll initialize the enhanced manager on first use (lazy loading)
        # This avoids the overhead of loading all components during initialization
        if self.use_enhancements:
            logger.info("Enhanced execution capability is available (will load on first use)")
        else:
            logger.info("Enhanced execution is not available or disabled")
        
        logger.info("AgentSHandler initialized successfully")
    
    def _select_provider_and_model(self, provider=None, model=None):
        """Select the provider and model based on available API keys"""
        available_keys = {
            "openai": "OPENAI_API_KEY" in os.environ,
            "anthropic": "ANTHROPIC_API_KEY" in os.environ,
        }
        
        # Select provider based on available API keys if not specified
        if provider is None:
            if available_keys["anthropic"]:
                provider = "anthropic"
                logger.info("Using Anthropic provider (API key available)")
            elif available_keys["openai"]:
                provider = "openai"
                logger.info("Using OpenAI provider (API key available)")
            else:
                raise ValueError("No API keys found. Cannot initialize Agent-S.")
        
        # Determine model based on provider if not specified
        if model is None:
            provider_default_models = {
                "openai": "gpt-4o",
                "anthropic": "claude-3-7-sonnet-20250219",
            }
            model = provider_default_models.get(provider, "gpt-4o")
        
        return provider, model
    
    def _configure_perplexica(self):
        """Configure Perplexica search service following the Agent-S README"""
        # Set Perplexica URL as per documentation
        if "PERPLEXICA_URL" not in os.environ:
            perplexica_url = "http://localhost:3000/api/search"
            os.environ["PERPLEXICA_URL"] = perplexica_url
            logger.info(f"Set Perplexica URL: {perplexica_url}")
        else:
            logger.info(f"Using existing Perplexica URL: {os.environ['PERPLEXICA_URL']}")
            
        # For compatibility with the original implementation, check connectivity
        try:
            import requests
            health_url = os.environ["PERPLEXICA_URL"].replace("/search", "/health")
            response = requests.get(health_url, timeout=2)
            if response.status_code == 200:
                logger.info("Perplexica is running and accessible")
            else:
                logger.warning(f"Perplexica health check failed: {response.status_code}")
                logger.warning("Disabling Perplexica - using local knowledge fallback")
                os.environ["PERPLEXICA_URL"] = "disabled"
        except Exception as e:
            logger.warning(f"Could not connect to Perplexica: {e}")
            logger.warning("Disabling Perplexica - using local knowledge fallback")
            os.environ["PERPLEXICA_URL"] = "disabled"
    
    def _enable_unrestricted_mode(self):
        """Enable unrestricted mode for Agent-S (preserving functionality)"""
        # Enable full AppleScript functionality - valuable from original implementation
        os.environ["AGENT_S_ENABLE_APPLESCRIPT"] = "1"
        os.environ["AGENT_S_UNRESTRICTED"] = "1"
        os.environ["AGENT_S_HOST_SYSTEM"] = "JARVIS"
        
        logger.info("Unrestricted mode enabled for Agent-S")
    
    def _setup_api_keys(self, api_key_env: Dict[str, str] = None):
        """
        Set up API keys for Anthropic and OpenAI.
        
        Args:
            api_key_env: Dictionary of API keys to set as environment variables directly
        """
        # Set up API keys if provided directly
        if api_key_env:
            for key, value in api_key_env.items():
                os.environ[key] = value
                logger.info(f"Set environment variable: {key}")
        
        # Load API keys from configuration
        try:
            anthropic_key = load_api_key('CLAUDE')
            if anthropic_key:
                os.environ["ANTHROPIC_API_KEY"] = anthropic_key
                logger.info("Loaded Anthropic API key from config")
        except Exception as e:
            logger.warning(f"Could not load Anthropic API key: {str(e)}")
        
        try:
            openai_key = load_api_key('OPENAI')
            if openai_key:
                os.environ["OPENAI_API_KEY"] = openai_key
                logger.info("Loaded OpenAI API key from config")
        except Exception as e:
            logger.warning(f"Could not load OpenAI API key: {str(e)}")
    
    def _initialize_agent_s_components(self):
        """Initialize Agent-S components following the official documentation"""
        logger.info("Starting Agent-S component initialization...")
        
        # Get screen dimensions for grounding
        screen_width, screen_height = pyautogui.size()
        logger.info(f"Screen dimensions: {screen_width}x{screen_height}")
        
        grounding_width = 1366  # Anthropic's default resize width
        grounding_height = screen_height * grounding_width / screen_width
        logger.info(f"Grounding dimensions: {grounding_width}x{grounding_height}")
        
        # Set up grounding parameters
        grounding_params = self.engine_params.copy()
        grounding_params.update({
            "grounding_width": grounding_width,
            "grounding_height": grounding_height
        })
        
        # Create the grounding agent using the simplified approach from documentation
        # Import OSWorldACI lazily to avoid hanging during module import
        global OSWorldACI, _osworld_aci_import_error
        if OSWorldACI is None and _osworld_aci_import_error is None:
            try:
                logger.info("Lazy importing OSWorldACI...")
                from gui_agents.s2.agents.grounding import OSWorldACI
                logger.info("OSWorldACI lazy import successful")
            except Exception as e:
                _osworld_aci_import_error = e
                logger.error(f"Failed to lazy import OSWorldACI: {str(e)}")
                raise ImportError(f"Could not import OSWorldACI: {str(e)}") from e
        elif _osworld_aci_import_error is not None:
            raise ImportError(f"OSWorldACI import failed previously: {str(_osworld_aci_import_error)}") from _osworld_aci_import_error
        
        logger.info("Initializing OSWorldACI grounding agent...")
        self.grounding_agent = OSWorldACI(
            platform=self.platform,
            engine_params_for_generation=self.engine_params,
            engine_params_for_grounding=grounding_params,
            width=screen_width,
            height=screen_height
        )
        logger.info("OSWorldACI grounding agent initialized successfully")
        
        # Create the agent using the simplified approach from documentation
        logger.info("Initializing AgentS2 with Perplexica search engine...")
        self.agent = AgentS2(
            engine_params=self.engine_params,
            grounding_agent=self.grounding_agent,
            platform=self.platform,
            action_space="pyautogui",
            observation_type="mixed",
            search_engine="Perplexica"
        )
        logger.info("AgentS2 initialized successfully")
        
        logger.info("Agent-S components initialized successfully")
    
    def _scale_screen_dimensions(self, width, height, max_dim_size=2400):
        """Scale screen dimensions to fit within max_dim_size while preserving aspect ratio"""
        scale_factor = min(max_dim_size / width, max_dim_size / height, 1)
        scaled_width = int(width * scale_factor)
        scaled_height = int(height * scale_factor)
        return scaled_width, scaled_height
        
    def start_conversation(self):
        """
        Start a continuous conversation with Agent-S.
        
        This method initializes a new conversation session, enabling Agent-S to maintain
        context between multiple task executions. It sets up the necessary state tracking
        and prepares the agent for a series of related interactions.
        
        Returns:
            Dict: Information about the new conversation session
        """
        if not self.conversation_mode:
            logger.warning("Conversation mode is not enabled. Enable it during initialization.")
            return {"success": False, "error": "Conversation mode not enabled"}
            
        # Generate a unique conversation ID
        import uuid
        self.conversation_id = str(uuid.uuid4())
        
        # Reset conversation state
        self.conversation_active = True
        self.conversation_history = []
        self.last_observation = None
        self.last_task_description = None
        self.last_agent_response = None
        
        # Reset the agent's memory for a fresh conversation
        if hasattr(self, 'agent'):
            self.agent.reset()
        
        logger.info(f"Started new conversation with ID: {self.conversation_id}")
        
        return {
            "success": True,
            "conversation_id": self.conversation_id,
            "message": "Conversation started. You can now interact with Agent-S in a continuous session."
        }
        
    def end_conversation(self):
        """
        End the current continuous conversation with Agent-S.
        
        This method cleanly terminates the active conversation session, saving any
        relevant state if needed and releasing resources.
        
        Returns:
            Dict: Summary information about the ended conversation
        """
        if not self.conversation_active:
            return {"success": False, "error": "No active conversation to end"}
            
        # Summarize the conversation
        conversation_summary = {
            "conversation_id": self.conversation_id,
            "exchanges": len(self.conversation_history),
            "duration": time.time() - self.conversation_history[0]["timestamp"] if self.conversation_history else 0
        }
        
        # Reset conversation state
        self.conversation_active = False
        self.conversation_id = None
        
        # Keep the history for reference but mark it as inactive
        logger.info(f"Ended conversation with {conversation_summary['exchanges']} exchanges")
        
        return {
            "success": True,
            "summary": conversation_summary,
            "message": "Conversation ended successfully."
        }
        
    def prompt_for_next_task(self, prompt_message=None):
        """
        Prompt the user for the next task in the conversation.
        
        This method is useful when Agent-S has completed a task and is waiting
        for further instructions. It displays a prompt message (which can be
        the last response from the agent) and returns a structure that can be
        used by client applications to prompt for input.
        
        Args:
            prompt_message: Optional custom prompt message
            
        Returns:
            Dict: Prompt information for client applications
        """
        if not self.conversation_active:
            return {"success": False, "error": "No active conversation"}
            
        # Use provided message, last agent response, or default
        message = prompt_message or self.last_agent_response or "What would you like to do next?"
            
        return {
            "success": True,
            "conversation_id": self.conversation_id,
            "prompt_message": message,
            "exchanges_so_far": len(self.conversation_history),
            "awaiting_input": True,
            "waiting_for_next_task": getattr(self, '_waiting_for_next_task', False)
        }
    
    def continue_with_new_task(self, new_task_description, max_steps=15):
        """
        Continue the conversation with a new task without resetting the agent.
        
        This method allows seamless continuation of a conversation by providing
        a new task to the agent while maintaining all previous context and state.
        It's designed to work when the agent has completed a previous task and
        is waiting for new instructions.
        
        Args:
            new_task_description: The new task to execute
            max_steps: Maximum number of steps for the new task
            
        Returns:
            Tuple of (success, info, action) from the new task execution
        """
        if not self.conversation_active:
            logger.error("Cannot continue conversation - no active conversation")
            return False, {"error": "No active conversation"}, "No action taken"
            
        logger.info(f"Continuing conversation with new task: {new_task_description}")
        
        # Clear the waiting flags
        if hasattr(self, '_task_completed'):
            delattr(self, '_task_completed')
        if hasattr(self, '_waiting_for_next_task'):
            delattr(self, '_waiting_for_next_task')
        
        # Update last task description for context
        self.last_task_description = new_task_description
        
        # Continue with the agent in its current state (don't reset)
        # The agent should maintain its memory and context
        logger.info("Agent continuing with preserved state and context")
        
        # Run the new task with the existing agent state
        return self.run_agent_s(new_task_description, max_steps)
    
    def is_waiting_for_next_task(self):
        """
        Check if the agent has completed a task and is waiting for the next one.
        
        Returns:
            bool: True if agent is waiting for next task, False otherwise
        """
        return getattr(self, '_waiting_for_next_task', False)
    
    def get_conversation_state(self):
        """
        Get the current state of the active conversation.
        
        Returns information about the current conversation including its history,
        active status, and metadata.
        
        Returns:
            Dict: Current conversation state
        """
        if not self.conversation_active:
            return {"active": False, "message": "No active conversation"}
            
        return {
            "active": True,
            "conversation_id": self.conversation_id,
            "exchanges": len(self.conversation_history),
            "last_task": self.last_task_description,
            "last_response": self.last_agent_response,
            "history_summary": [
                {"task": entry["task"], "timestamp": entry["timestamp"]}
                for entry in self.conversation_history
            ]
        }
    
    async def run_agent_s_with_control_handoff(self, task_description, max_steps=15):
        """
        Run Agent-S with proper desktop control handoff for workspace integration.
        
        TEMPORARILY DISABLED: Desktop control handoff is currently disabled for testing.
        This method now just calls the regular run_agent_s method without desktop takeover.
        
        Args:
            task_description: Natural language description of the task
            max_steps: Maximum number of execution steps
            
        Returns:
            Dict containing execution results and captured data for workspace integration
        """
        logger.info(f"[AGENT-S-HANDLER] Desktop control handoff DISABLED - using regular execution: {task_description}")
        
        # Call the regular method without desktop control
        execution_result = self.run_agent_s(task_description, max_steps)
        
        return {
            "status": "success",
            "task_description": task_description,
            "execution_result": execution_result,
            "workspace_data": None,
            "desktop_control_used": False,
            "note": "Desktop control handoff was disabled for testing"
        }
        
        # Original implementation is commented out below:
        """
        try:
            # Import the control manager
            from agent_s_enhancement.agent_s_control_manager import AgentSControlManager
            
            logger.info(f"[AGENT-S-HANDLER] Starting controlled execution: {task_description}")
            
            # Initialize control manager
            control_manager = AgentSControlManager()
            
            # Request user permission (no duration estimate - Agent-S learns as needed)
            permission_granted = await control_manager.request_user_control_handoff(task_description)
            
            if not permission_granted:
                logger.info("[AGENT-S-HANDLER] User denied desktop control")
                return {
                    "status": "cancelled",
                    "reason": "user_denied_control",
                    "task_description": task_description
                }
            
            # Prepare desktop
            desktop_state = await control_manager.prepare_desktop_for_agent_s()
            
            try:
                # Execute Agent-S with progress tracking
                logger.info("[AGENT-S-HANDLER] Starting Agent-S execution with desktop control")
                
                # Show execution notification
                await control_manager._show_notification(
                    "Agent-S Active",
                    f"Executing: {task_description}"
                )
                
                # Run the actual Agent-S task (existing method)
                execution_result = self.run_agent_s(task_description, max_steps)
                
                # Capture workspace data from execution
                workspace_data = self._extract_workspace_data_from_execution(
                    execution_result, task_description
                )
                
                # Show completion notification
                await control_manager._show_notification(
                    "Agent-S Complete",
                    "Task completed successfully"
                )
                
                logger.info("[AGENT-S-HANDLER] Agent-S execution completed successfully")
                
                return {
                    "status": "success",
                    "task_description": task_description,
                    "execution_result": execution_result,
                    "workspace_data": workspace_data,
                    "desktop_control_used": True
                }
                
            finally:
                # Always restore desktop state
                await control_manager.restore_desktop_state(desktop_state)
                await control_manager._notify_control_returned()
                logger.info("[AGENT-S-HANDLER] Desktop control returned to user")
                
        except Exception as e:
            logger.error(f"[AGENT-S-HANDLER] Error in controlled execution: {e}")
            
            # Emergency notification
            try:
                await control_manager._notify_control_returned(error=str(e))
            except:
                pass
            
            return {
                "status": "error",
                "error": str(e),
                "task_description": task_description,
                "desktop_control_used": True
            }
        """
    
    def _extract_workspace_data_from_execution(self, execution_result, task_description):
        """
        Extract relevant data from Agent-S execution for workspace integration.
        
        This method processes the Agent-S execution results and extracts data
        that should be stored in the workspace reference cache for future use.
        """
        try:
            workspace_data = {
                "data_captured": [],
                "ui_patterns_learned": [],
                "application_insights": [],
                "workspace_context_updated": False,
                "gaps_filled": [task_description]
            }
            
            # Extract data from execution result
            if isinstance(execution_result, tuple) and len(execution_result) >= 2:
                success, info, action = execution_result
                
                if success:
                    workspace_data["workspace_context_updated"] = True
                    
                    # Extract UI patterns if available
                    if info and isinstance(info, dict):
                        # Look for UI element information
                        if "ui_elements" in info:
                            for element in info["ui_elements"]:
                                pattern = {
                                    "application": element.get("application", "unknown"),
                                    "ui_element": element.get("element_type", "unknown"),
                                    "action_type": element.get("action", "click"),
                                    "success_rate": 1.0 if success else 0.0,
                                    "workspace_context": task_description
                                }
                                workspace_data["ui_patterns_learned"].append(pattern)
                        
                        # Extract application insights
                        if "application_state" in info:
                            insight = {
                                "application": info.get("application", "unknown"),
                                "insight": info.get("application_state", "State captured"),
                                "confidence": 0.9,
                                "task_context": task_description
                            }
                            workspace_data["application_insights"].append(insight)
                    
                    # Add screenshot data capture info
                    workspace_data["data_captured"].append({
                        "type": "ui_automation_execution",
                        "timestamp": time.time(),
                        "task": task_description,
                        "success": success
                    })
            
            logger.info(f"[AGENT-S-HANDLER] Extracted workspace data: {len(workspace_data['ui_patterns_learned'])} patterns, "
                       f"{len(workspace_data['application_insights'])} insights")
            
            return workspace_data
            
        except Exception as e:
            logger.error(f"[AGENT-S-HANDLER] Error extracting workspace data: {e}")
            return {
                "data_captured": [],
                "ui_patterns_learned": [],
                "application_insights": [],
                "workspace_context_updated": False,
                "gaps_filled": [task_description],
                "extraction_error": str(e)
            }
    
    def run_agent_s(self, task_description, max_steps=15):
        """
        Run Agent-S with the given task description using its hierarchical execution system.
        
        This method implements the core Agent-S execution flow, leveraging its DAG-based
        task planning and step-by-step execution model. It handles the complete lifecycle
        of a UI automation task:
        
        1. Task Initialization - Prepares the agent and captures initial screen state
        2. Plan Generation - The Manager component creates a directed acyclic graph (DAG) of subtasks
        3. Sequential Execution - The Worker component executes each subtask in sequence
        4. Progress Monitoring - Tracks execution progress and handles completion/failure states
        5. Memory Updates - Updates narrative and episodic memory for future improvement
        
        The execution process is designed to be robust with:
        - Appropriate timeouts to prevent hanging
        - Step limits to prevent excessive execution
        - Error handling for recovery from failures
        - Screenshot-based environment understanding
        - Accessibility tree integration when available
        
        Args:
            task_description: Natural language description of the task to perform
            max_steps: Maximum number of execution steps to run (default: 15)
            
        Returns:
            Tuple of (success, info, action) where:
                - success: Boolean indicating whether execution succeeded
                - info: Dictionary containing execution metadata and state information
                - action: Final action code or description that was executed
                
        Note:
            This method follows the official Agent-S documentation and preserves
            its execution flow while adding necessary error handling and timeouts.
            It automatically adjusts screenshot resolution to optimize for LLM processing.
        """
        logger.info(f"Running Agent-S for task: {task_description}")
        print(f"\n===== USING AGENT-S FOR TASK: {task_description} =====\n")
        
        # Get screen dimensions and scale
        screen_width, screen_height = pyautogui.size()
        scaled_width, scaled_height = self._scale_screen_dimensions(screen_width, screen_height)
        
        # Reset the agent for a fresh start, but preserve state in conversation mode
        if not (self.conversation_mode and self.conversation_active):
            self.agent.reset()
        else:
            logger.info("Conversation mode active - Preserving agent state between tasks")
        
        # Track execution for history
        all_infos = []
        all_actions = []
        success = False
        traj = "Task:\n" + task_description
        subtask_traj = ""
        
        # Run the agent for max_steps
        for step in range(max_steps):
            logger.info(f"Executing step {step+1}/{max_steps}")
            
            # Capture screenshot
            screenshot = pyautogui.screenshot()
            screenshot = screenshot.resize((scaled_width, scaled_height), Image.LANCZOS)
            
            # Convert to bytes
            buffered = io.BytesIO()
            screenshot.save(buffered, format="PNG")
            screenshot_bytes = buffered.getvalue()
            
            # Create observation object
            obs = {
                "screenshot": screenshot_bytes
            }
            
            # Add accessibility tree for macOS if available (from original implementation)
            if self.platform == "darwin" and 'UIElement' in globals():
                try:
                    obs["accessibility_tree"] = UIElement.systemWideElement()
                except Exception:
                    pass
            
            # Get next action from the agent
            try:
                info, code = self.agent.predict(instruction=task_description, observation=obs)
            except AttributeError as e:
                if "'NoneType' object has no attribute 'name'" in str(e):
                    logger.info("Agent determined task is already complete - no further action needed")
                    success = True
                    final_info = {
                        "message": "Task already completed",
                        "steps_executed": step + 1,
                        "final_status": "completed_already"
                    }
                    return (success, final_info, "Task was already complete")
                else:
                    raise e
            
            # Record for tracking
            if info:
                all_infos.append(info)
            
            # Handle empty code
            if not code or len(code) == 0:
                logger.info("No action received, waiting...")
                time.sleep(1)
                continue
                
            action = code[0]
            all_actions.append(action)
            
            # Log for debugging
            print(f"\nAGENT ACTION (step {step+1}):")
            print(action)
            
            # Check for task completion
            if "done" in action.lower() or "fail" in action.lower():
                logger.info(f"Task completed: {action}")
                success = True
                if hasattr(self.agent, 'update_narrative_memory'):
                    self.agent.update_narrative_memory(traj)
                
                # In conversation mode, handle completion differently
                if self.conversation_mode and self.conversation_active:
                    logger.info("Conversation mode active - Task completed but keeping session alive")
                    
                    # Extract any response message from the DONE action
                    if "done(" in action.lower() and ")" in action:
                        try:
                            # Extract the message from done("message")
                            import re
                            message_match = re.search(r'done\s*\(\s*["\'](.+?)["\']\s*\)', action.lower())
                            if message_match:
                                response_message = message_match.group(1)
                                logger.info(f"Extracted response message: {response_message}")
                                self.last_agent_response = response_message
                        except Exception as e:
                            logger.warning(f"Error extracting message from DONE action: {e}")
                    
                    # Don't break from the loop in conversation mode - instead, wait for next task
                    # Set a flag indicating task completion but agent ready for more
                    if not hasattr(self, '_task_completed'):
                        self._task_completed = True
                        self._waiting_for_next_task = True
                        logger.info("Task completed - Agent waiting for next instruction in conversation")
                        
                        # Return success but indicate conversation is still active
                        break
                else:
                    # Not in conversation mode - normal completion behavior
                    break
                
            # Handle special actions
            if "next" in action.lower():
                logger.info("Agent requested 'next' action, continuing...")
                continue
                
            if "wait" in action.lower():
                logger.info("Agent requested 'wait' action, waiting 5 seconds...")
                time.sleep(5)
                continue
                
            # Execute normal action
            logger.info(f"Executing action: {action[:100]}..." if len(action) > 100 else f"Executing action: {action}")
            try:
                # Fix potential AppleScript formatting issues (valuable from original)
                if "apple_script" in action and "{" in action:
                    # Fix common AppleScript formatting errors
                    logger.info("Fixing AppleScript formatting in action...")
                    
                    # Extract the AppleScript portion
                    script_start = action.find("apple_script = f'''")
                    script_end = action.find("'''", script_start + 20)
                    
                    if script_start >= 0 and script_end >= 0:
                        script_text = action[script_start + 20:script_end]
                        fixed_script = script_text.replace('{Mail}', 'Mail')
                        
                        # Replace the script in the action
                        action = action[:script_start + 20] + fixed_script + action[script_end:]
                        
                        logger.info("Applied AppleScript formatting fix")
                
                # Execute the agent's action
                exec(action)
                time.sleep(1.0)
                
                # Update memories if available (from the original implementation)
                if isinstance(info, dict):
                    # Update narrative with reflection and plan
                    if "reflection" in info and "executor_plan" in info:
                        traj += (
                            "\n\nReflection:\n"
                            + str(info["reflection"])
                            + "\n\n----------------------\n\nPlan:\n"
                            + info["executor_plan"]
                        )
                    
                    # Update episodic memory
                    if hasattr(self.agent, 'update_episodic_memory'):
                        subtask_traj = self.agent.update_episodic_memory(info, subtask_traj)
            except Exception as e:
                logger.error(f"Error executing action: {e}")
                logger.error(traceback.format_exc())
        
        # Return final results
        final_info = all_infos[-1] if all_infos else {}
        final_action = all_actions[-1] if all_actions else "No action taken"
        
        return success, final_info, final_action
    
    async def continue_conversation(
        self,
        task_description: str,
        execute_action: bool = True,
        total_timeout: int = 600,
        max_steps: int = 15
    ):
        """
        Continue an existing conversation with a new task.
        
        This method adds a new task to an ongoing conversation, maintaining context
        from previous exchanges. It's a simpler interface to execute_ui_task that
        ensures conversation mode is properly maintained.
        
        Args:
            task_description: Description of the new task to perform
            execute_action: Whether to actually execute actions
            total_timeout: Maximum timeout in seconds
            max_steps: Maximum number of steps to execute
            
        Returns:
            Dict with execution results and conversation state
        """
        if not self.conversation_mode:
            return {"success": False, "error": "Conversation mode is not enabled"}
            
        if not self.conversation_active:
            return {"success": False, "error": "No active conversation. Call start_conversation() first."}
            
        # If agent is waiting for next task, use direct continuation
        if self.is_waiting_for_next_task():
            logger.info("Agent is waiting for next task - using direct continuation")
            
            # Record start time
            start_time = time.time()
            
            try:
                # Continue with the new task directly
                if execute_action:
                    success, info, action = self.continue_with_new_task(task_description, max_steps)
                else:
                    logger.info("Execute action is False, skipping actual execution")
                    success = False
                    info = {"status": "skipped", "reason": "execute_action is False"}
                    action = "Action execution skipped due to execute_action=False"
                
                # Create execution record
                execution_record = {
                    "task": task_description,
                    "timestamp": time.time(),
                    "human_readable_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "execution_time": time.time() - start_time,
                    "action_code": action if isinstance(action, str) else str(action),
                    "success": success,
                    "execution_method": "ui_continuation",  # Indicate this was a conversation continuation
                    "conversation_id": self.conversation_id
                }
                
                # Add to histories
                self.execution_history.append(execution_record)
                self.conversation_history.append(execution_record)
                
                # Update conversation state
                self.last_task_description = task_description
                
                # Take new screenshot for next potential task
                import io
                screenshot = pyautogui.screenshot()
                buffered = io.BytesIO()
                screenshot.save(buffered, format="PNG")
                screenshot_bytes = buffered.getvalue()
                self.last_observation = {"screenshot": screenshot_bytes}
                
                return {
                    "success": success,
                    "task": task_description,
                    "execution_time": time.time() - start_time,
                    "action_code": action if isinstance(action, str) else str(action),
                    "info": info,
                    "execution_method": "ui_continuation",
                    "conversation_active": True,
                    "conversation_id": self.conversation_id,
                    "conversation_exchanges": len(self.conversation_history)
                }
                
            except Exception as e:
                logger.error(f"Error in conversation continuation: {e}")
                return {
                    "success": False,
                    "task": task_description,
                    "execution_time": time.time() - start_time,
                    "error": str(e),
                    "conversation_active": True,
                    "conversation_id": self.conversation_id
                }
        else:
            # Use the standard execution path
            result = await self.execute_ui_task(
                task_description=task_description,
                execute_action=execute_action,
                total_timeout=total_timeout,
                max_steps=max_steps
            )
            
            # Add conversation details
            result["conversation_id"] = self.conversation_id
            result["conversation_exchanges"] = len(self.conversation_history)
            
            return result
    
    async def execute_ui_task(
        self, 
        task_description: str, 
        execute_action: bool = True,
        total_timeout: int = 600, 
        max_steps: int = 15,
        analysis_result: Dict[str, Any] = None,
        execution_preference: str = None,  # Override the default preference for this task
        app_name: str = None, # Optional target application name to improve execution
        in_conversation: bool = None  # Override conversation mode for this task
    ):
        """
        Execute a UI automation task using Agent-S's hierarchical execution system.
        
        This method serves as the primary entry point for UI automation tasks, providing
        an asynchronous interface that supports both the core Agent-S execution flow and
        enhanced execution paths when available.
        
        The execution process follows these steps:
        1. Task Analysis - If enhancements are available, analyzes the task to determine
           the optimal execution strategy (UI automation, hotkeys, or handler shortcuts)
        2. Execution Strategy Selection - Chooses between direct UI automation, hotkey shortcuts,
           or handler-based execution based on analysis and preferences
        3. Execution - Performs the selected execution strategy with appropriate timeout handling
        4. Result Processing - Standardizes the execution results for consistent return format
        
        The method supports several execution methods:
        - UI Automation: Direct control of UI elements through Agent-S's DAG-based execution
        - Hotkey Shortcuts: Using system hotkeys for faster execution of common operations
        - Handler Shortcuts: Bypassing UI entirely when appropriate handlers are available
        
        When running in conversation mode, the method maintains context between executions:
        - Preserves screenshot and UI state between requests
        - Includes previous exchanges as context for the current task
        - Updates an ongoing conversation history
        - Provides richer context for multi-step interactions
        
        Args:
            task_description: Natural language description of the task to perform
            execute_action: Whether to actually execute actions (false for simulation/safety)
            total_timeout: Maximum execution time in seconds before forced termination
            max_steps: Maximum number of execution steps to perform
            analysis_result: Optional pre-computed task analysis results
            execution_preference: Preferred execution method, overriding the default:
                - "auto": Automatically select best method based on analysis
                - "ui": Always use direct UI automation
                - "hotkey": Prefer hotkey shortcuts when available
                - "handler": Prefer handler-based execution when available
            app_name: Optional target application name to improve execution focus
            in_conversation: Override conversation mode for this specific task
            
        Returns:
            Dict containing execution results with the following keys:
                - success: Boolean indicating whether execution succeeded
                - task: Original task description
                - execution_time: Total execution time in seconds
                - execution_method: Method used for execution (ui, hotkey, handler)
                - action_code: Code or description of final action performed
                - info: Additional information about the execution
                - error: Error message if execution failed
                - conversation_active: Whether this task was part of a conversation
                - conversation_id: ID of the active conversation (if any)
        
        Raises:
            TimeoutError: If execution exceeds the specified timeout
            Exception: For other execution errors
        """
        logger.info(f"Executing UI task: {task_description}")
        
        # Use enhanced execution if available, but with better fallback handling
        if self.use_enhancements and ENHANCEMENTS_AVAILABLE:
            # Add global timeout for the entire enhanced execution path
            enhanced_execution_start = time.time()
            enhanced_execution_timeout = 8  # Reduced from 15 to 8 seconds total timeout for enhancement path
            
            try:
                # Initialize enhanced manager if not done yet (lazy loading)
                # Use a specific flag to prevent multiple initialization attempts
                is_initializing = getattr(self, '_initializing_enhanced_manager', False)
                
                # Check if we're already over the timeout before even starting
                if time.time() - enhanced_execution_start > enhanced_execution_timeout:
                    logger.warning("Enhanced execution timeout before initialization - falling back to standard")
                    raise TimeoutError("Enhanced execution path timed out")
                
                # Initialize the enhanced manager if needed
                if (not hasattr(self, 'enhanced_manager') or self.enhanced_manager is None) and not is_initializing:
                    # Set flag to prevent reentrancy
                    self._initializing_enhanced_manager = True
                    
                    try:
                        logger.info("Initializing enhanced execution manager (lazy loading)")
                        
                        # Gather parameters with safe checks
                        api_key_env = getattr(self, '_api_key_env', None)
                        model = getattr(self, 'model', None)
                        provider = getattr(self, 'provider', None)
                        pref = execution_preference or getattr(self, '_execution_preference', "auto")
                        
                        # Calculate remaining timeout - max 5 seconds for initialization
                        remaining_timeout = min(5, max(1, enhanced_execution_timeout - (time.time() - enhanced_execution_start)))
                        
                        # Use the get_intelligent_execution_manager with built-in timeout
                        logger.info(f"Getting intelligent execution manager with {remaining_timeout}s timeout")
                        self.enhanced_manager = get_intelligent_execution_manager(
                            api_key_env=api_key_env,
                            model=model,
                            provider=provider,
                            execution_preference=pref,
                            enable_intelligence=True,  # Explicitly enable intelligence
                            enable_hotkeys=True,       # Explicitly enable hotkeys
                            enable_handler_shortcuts=True,  # Explicitly enable handler shortcuts
                            timeout=remaining_timeout  # Pass timeout directly
                        )
                        
                        # Check if we got a valid manager back
                        if self.enhanced_manager is None:
                            logger.warning("Enhanced manager initialization returned None")
                            raise TimeoutError("Enhanced manager initialization failed or timed out")
                        
                        # Connect the enhanced manager to this base manager
                        if hasattr(self.enhanced_manager, 'connect_to_base_manager'):
                            self.enhanced_manager.connect_to_base_manager(self)
                            
                        logger.info("Enhanced execution manager initialized successfully")
                    except concurrent.futures.TimeoutError:
                        logger.error("Timeout initializing enhanced manager")
                        self.enhanced_manager = None
                        self.use_enhancements = False
                        raise TimeoutError("Enhanced manager initialization timed out")
                    except Exception as load_error:
                        logger.error(f"Error lazy-loading enhanced manager: {load_error}")
                        logger.error(traceback.format_exc())
                        self.enhanced_manager = None
                        self.use_enhancements = False
                        logger.warning("Falling back to standard execution due to initialization error")
                        raise
                    finally:
                        # Always clear the initialization flag
                        self._initializing_enhanced_manager = False
                
                # Check timeout again before proceeding
                if time.time() - enhanced_execution_start > enhanced_execution_timeout:
                    logger.warning("Enhanced execution timeout after initialization - falling back to standard")
                    raise TimeoutError("Enhanced execution path timed out after initialization")
                
                # Only proceed if we have a valid enhanced manager
                if self.enhanced_manager:
                    logger.info("Using enhanced execution manager")
                    print(f"\n=== EXECUTING TASK WITH ENHANCED AGENT-S: {task_description} ===\n")
                    
                    # Calculate remaining timeout
                    remaining_timeout = max(1, enhanced_execution_timeout - (time.time() - enhanced_execution_start))
                    
                    # Execute with enhanced manager and timeout
                    try:
                        # Use asyncio.wait_for to prevent hanging in the enhanced manager
                        result = await asyncio.wait_for(
                            self.enhanced_manager.execute_ui_task(
                                task_description=task_description,
                                execute_action=execute_action,
                                total_timeout=total_timeout,
                                max_steps=max_steps,
                                analysis_result=analysis_result,
                                _direct_execution=True  # Add a flag to prevent recursion
                            ),
                            timeout=remaining_timeout
                        )
                        
                        # Enhanced manager handles execution history internally
                        return result
                    except asyncio.TimeoutError:
                        logger.error(f"Timeout in enhanced manager execution after {remaining_timeout}s")
                        raise TimeoutError("Enhanced execution timed out")
                else:
                    logger.warning("Enhanced manager not available, falling back to standard")
                    raise ValueError("Enhanced manager not available")
                
            except (TimeoutError, asyncio.TimeoutError, ValueError) as timeout_err:
                # Handle timeout or initialization failures - log but don't propagate the error
                logger.warning(f"Enhanced execution unavailable: {str(timeout_err)}")
                logger.info("Falling back to standard execution")
                # Continue to standard execution
            except Exception as e:
                logger.error(f"Error using enhanced execution manager: {e}")
                logger.error(traceback.format_exc())
                logger.warning("Falling back to standard execution due to error")
        
        # Standard execution (fallback or if enhancements aren't available)
        print(f"\n=== EXECUTING TASK WITH AGENT-S: {task_description} ===\n")
        
        # Record start time
        start_time = time.time()
        
        # Set a timeout handler to prevent hanging (Unix systems only)
        use_alarm = hasattr(signal, 'SIGALRM')
        if use_alarm:
            def timeout_handler(signum, frame):
                raise TimeoutError(f"Task execution timed out after {total_timeout} seconds")
            
            # Set the timeout
            signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(total_timeout)
        
        try:
            # Create initial observation for conversation mode
            initial_observation = None
            
            # If in conversation mode, use the last observation if available
            if self.conversation_mode and self.conversation_active and self.last_observation:
                logger.info("Using saved observation from ongoing conversation")
                initial_observation = self.last_observation
                # Append conversation context to task if needed
                if not task_description.startswith("CONVERSATION CONTEXT:"):
                    # Create a context summary from recent history
                    context_entries = []
                    for entry in self.conversation_history[-3:]:  # Last 3 exchanges
                        context_entries.append(f"Previous task: {entry['task']}")
                        if entry.get('action_code'):
                            context_entries.append(f"Action: {entry['action_code'][:100]}...")
                    
                    # Include last agent response if available
                    if self.last_agent_response:
                        context_entries.append(f"Your last response: {self.last_agent_response}")
                    
                    if context_entries:
                        conversation_context = "\n".join(context_entries)
                        task_description = f"CONVERSATION CONTEXT:\n{conversation_context}\n\nCURRENT TASK:\n{task_description}"
            
            # Run Agent-S with task description
            if execute_action:
                success, info, action = self.run_agent_s(task_description, max_steps)
            else:
                logger.info("Execute action is False, skipping actual execution")
                success = False
                info = {"status": "skipped", "reason": "execute_action is False"}
                action = "Action execution skipped due to execute_action=False"
            
            # Create detailed execution record for tracking
            execution_record = {
                "task": task_description,
                "timestamp": time.time(),
                "human_readable_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "execution_time": time.time() - start_time,
                "action_code": action if isinstance(action, str) else str(action),
                "success": success,
                "execution_method": "ui",  # Standard UI execution
                "conversation_id": self.conversation_id if self.conversation_active else None
            }
            
            # Add subtask info if available
            if isinstance(info, dict):
                if "subtask" in info:
                    execution_record["subtask"] = info["subtask"]
                if "subtask_status" in info:
                    execution_record["subtask_status"] = info["subtask_status"]
                if "reflection" in info:
                    execution_record["reflection"] = info["reflection"]
            
            # Add to execution history
            self.execution_history.append(execution_record)
            
            # Update conversation history if in conversation mode
            if self.conversation_mode and self.conversation_active:
                self.conversation_history.append(execution_record)
                self.last_task_description = task_description
                
                # Take a new screenshot to update observation for next exchange
                import io
                screenshot = pyautogui.screenshot()
                buffered = io.BytesIO()
                screenshot.save(buffered, format="PNG")
                screenshot_bytes = buffered.getvalue()
                
                # Create new observation with screenshot
                self.last_observation = {"screenshot": screenshot_bytes}
                
                # Add accessibility tree for macOS if available
                if self.platform == "darwin":
                    try:
                        from gui_agents.s1.aci.MacOSACI import UIElement
                        self.last_observation["accessibility_tree"] = UIElement.systemWideElement()
                    except Exception as e:
                        logger.warning(f"Could not get accessibility tree: {e}")
            
            # Return execution results
            result = {
                "success": success,
                "task": task_description,
                "execution_time": time.time() - start_time,
                "action_code": action if isinstance(action, str) else str(action),
                "info": info,
                "execution_method": "ui",  # Standard UI execution
                "conversation_active": self.conversation_active,
                "conversation_id": self.conversation_id if self.conversation_active else None
            }
            
            return result
            
        except TimeoutError as e:
            logger.error(f"Task execution timed out: {e}")
            return {
                "success": False,
                "task": task_description,
                "execution_time": time.time() - start_time,
                "error": f"Timeout: {str(e)}"
            }
        except Exception as e:
            logger.error(f"Error in execute_ui_task: {e}")
            logger.error(traceback.format_exc())
            
            return {
                "success": False,
                "task": task_description,
                "execution_time": time.time() - start_time,
                "error": str(e)
            }
        finally:
            # Cancel the alarm if it was set
            if use_alarm:
                signal.alarm(0)

# Example usage
if __name__ == "__main__":
    import asyncio
    
    async def conversation_example():
        """Example of using Agent-S in continuous conversation mode"""
        print("=== Agent-S Continuous Conversation Example ===")
        
        # Create the Agent-S handler with conversation mode enabled
        manager = AgentSHandler(
            conversation_mode=True,  # Enable conversation mode
            use_enhancements=False   # Keep it simple for the example
        )
        print(f"Initialized Agent-S with {manager.provider} provider")
        
        # Start a conversation
        conversation_result = manager.start_conversation()
        print(f"Started conversation: {conversation_result['conversation_id']}")
        
        # First task
        print("\n--- First Task ---")
        task1 = "open calculator"
        result1 = await manager.continue_conversation(task1)
        print(f"Task 1 completed: {result1['success']}")
        
        # Check if agent is waiting for next task
        if manager.is_waiting_for_next_task():
            print("✅ Agent is waiting for next task - conversation still active!")
            
            # Second task
            print("\n--- Second Task ---")
            task2 = "calculate 123 plus 456"
            result2 = await manager.continue_conversation(task2)
            print(f"Task 2 completed: {result2['success']}")
            
            # Third task
            print("\n--- Third Task ---")
            task3 = "what's the result?"
            result3 = await manager.continue_conversation(task3)
            print(f"Task 3 completed: {result3['success']}")
        
        # End the conversation
        end_result = manager.end_conversation()
        print(f"\nConversation ended. Total exchanges: {end_result['summary']['exchanges']}")
    
    async def main():
        try:
            # Parse command line arguments
            import argparse
            parser = argparse.ArgumentParser(description="Agent-S Handler")
            parser.add_argument("task", nargs="*", default=[], help="The task to execute")
            parser.add_argument("--no-enhancements", action="store_true", help="Disable enhancements")
            parser.add_argument("--preference", choices=["auto", "ui", "hotkey", "handler"], 
                               default="auto", help="Execution preference")
            parser.add_argument("--conversation-example", action="store_true", 
                               help="Run the conversation mode example")
            args = parser.parse_args()
            
            # Run conversation example if requested
            if args.conversation_example:
                await conversation_example()
                return
            
            # Create the Agent-S handler
            manager = AgentSHandler(
                use_enhancements=not args.no_enhancements,
                execution_preference=args.preference
            )
            print(f"Successfully initialized Agent-S with {manager.provider} provider")
            
            if manager.use_enhancements:
                print("Agent-S enhancements are ENABLED")
                print(f"Execution preference: {args.preference}")
            else:
                print("Agent-S enhancements are DISABLED")
            
            # Get task from command line or use default
            if args.task:
                task = " ".join(args.task)
            else:
                task = input("Enter the task you want to execute (e.g., 'open safari and search for news'): ")
            
            print(f"\nExecuting task: {task}")
            
            # Analyze the task first if enhancements are available
            if manager.use_enhancements and manager.enhanced_manager:
                try:
                    analysis = await manager.enhanced_manager.analyze_task(task)
                    print(f"\nTask Analysis:")
                    print(f"- Recommended execution method: {analysis.get('execution_method', 'ui')}")
                    
                    if analysis.get("hotkey_options"):
                        print(f"- Hotkey options available: {len(analysis['hotkey_options'])}")
                        for option in analysis["hotkey_options"][:2]:  # Show top 2
                            confidence = option.get("confidence", 0) * 100
                            print(f"  - {option.get('operation')}: {'+'.join(option.get('shortcut', []))} ({confidence:.1f}%)")
                    
                    if analysis.get("handler_options"):
                        handler_opt = analysis["handler_options"]
                        confidence = handler_opt.get("confidence", 0) * 100
                        print(f"- Handler option available: {handler_opt.get('domain')}/{handler_opt.get('action')} ({confidence:.1f}%)")
                    
                    # Send to Agent-S with the analysis
                    result = await manager.execute_ui_task(
                        task_description=task,
                        analysis_result=analysis,
                        execution_preference=args.preference
                    )
                except Exception as e:
                    print(f"Error during task analysis: {e}")
                    print("Continuing without analysis...")
                    result = await manager.execute_ui_task(task_description=task)
            else:
                # Send to Agent-S without analysis
                result = await manager.execute_ui_task(task_description=task)
            
            # Show results
            print("\nTask execution completed!")
            print(f"Success: {result.get('success', False)}")
            print(f"Execution method: {result.get('execution_method', 'ui')}")
            print(f"Execution time: {result.get('execution_time', 0):.2f} seconds")
            
            if result.get("error"):
                print(f"Error: {result['error']}")
                
            # Show action if available
            if result.get("action_code"):
                action_code = result["action_code"]
                print(f"\nAction: {action_code[:100] + '...' if len(action_code) > 100 else action_code}")
                
        except Exception as e:
            print(f"Error in main: {e}")
            traceback.print_exc()
    
if __name__ == "__main__":
    # Run the async main function only if this file is executed directly
    asyncio.run(main())