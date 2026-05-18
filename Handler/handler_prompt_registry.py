"""
Prompt Registry Handler for Jarvis MCP

This module implements a comprehensive prompt registry handler that provides MCP tools
for accessing, managing, and tracking prompts across the Jarvis ecosystem.

Key Features:
- Prompt retrieval and searching
- Performance tracking and metrics
- Prompt suggestions based on context
- Integration with agent registry for compatibility
- Version management and optimization

MCP Tools Provided:
- get_prompt: Retrieve prompt by ID with optional version
- search_prompts: Search prompts by criteria (tags, models, performance)
- track_performance: Record usage metrics for optimization
- suggest_prompts: Get prompt recommendations for specific tasks
- list_prompt_families: Get organized prompt categories
"""

import time
import json
import logging
import traceback
import asyncio
import hashlib
import os
from typing import Dict, Any, List, Optional, Union
import sys
from pathlib import Path
from datetime import datetime
import uuid

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Add project root to Python path for absolute imports
project_root = Path(__file__).parent.parent.absolute()
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Base imports
from Handler.handler_base import BaseHandler, HandlerResult
from Jarvis_Agent_SDK.boardroom_connector import (
    generate_request_id,
    generate_simple_id,
    track_journey_step_sync
)
from Database.v2.db_helper import connection as v2_connection
from Jarvis_Agent_SDK.prompt_registry import PromptRegistry, get_prompt_registry

class PromptRegistryOrchestratorAgent:
    """Agent responsible for orchestrating communication between PromptRegistry and Jarvis system"""
    
    def __init__(self, system_name="PromptRegistrySystem"):
        # Handle case where system_name is actually a PromptRegistryHandler object
        if hasattr(system_name, 'name'):
            self.prompt_registry_handler = system_name
            self.system_name = "PromptRegistryOrchestratorAgent"
        else:
            self.system_name = system_name
            self.prompt_registry_handler = None
            
        self.conversation_history = []
        self.active = True
        self.current_journey_id = None
        
        # Initialize prompt registry
        self.prompt_registry = get_prompt_registry()
        
        # BoardRoom was archived (Phase 3). Tracking uses V2 databases directly.
        self.boardroom = None
        logger.info(f"PromptRegistryOrchestratorAgent initialized for {self.system_name}")
    
    def _track_jarvis_communication(self, direction, message, journey_id=None, _prevent_recursion=False):
        """
        Track communication with the Jarvis orchestrator
        
        Args:
            direction: 'incoming' or 'outgoing'
            message: The message being tracked
            journey_id: Optional journey ID
            _prevent_recursion: Flag to prevent infinite recursion
        """
        import time as time_module
        
        if not journey_id:
            journey_id = self.current_journey_id or f"jarvis_comm_{int(time_module.time())}"
        
        # Create tracking data with timestamp and message metadata
        tracking_data = {
            "timestamp": time_module.time(),
            "direction": direction,
            "message_type": str(type(message).__name__),
            "system": "PromptRegistryOrchestratorAgent",
            "message_preview": str(message)[:200] if isinstance(message, str) else str(type(message).__name__)
        }
        
        try:
            # Track the communication step
            track_journey_step_sync(
                journey_id=journey_id,
                step_name=f"{direction}_prompt_registry_communication",
                description=f"PromptRegistry {direction} communication",
                step_type="orchestrator_communication",
                metadata=tracking_data
            )
        except Exception as e:
            logger.debug(f"Could not track communication: {e}")
    
    async def get_prompt_by_id(self, prompt_id: str, version: str = None, journey_id: str = None) -> Dict[str, Any]:
        """
        Retrieve a prompt by ID with optional version specification.
        
        Args:
            prompt_id: Unique identifier for the prompt
            version: Optional specific version to retrieve
            journey_id: Optional journey ID for tracking
            
        Returns:
            Dict containing prompt data or error information
        """
        try:
            self._track_jarvis_communication("incoming", f"get_prompt_by_id: {prompt_id}", journey_id)
            
            prompt = self.prompt_registry.load_prompt(prompt_id, version)
            if prompt:
                result = {
                    "success": True,
                    "prompt": prompt,
                    "metadata": {
                        "retrieved_at": time.time(),
                        "version_requested": version,
                        "actual_version": prompt.get("version")
                    }
                }
            else:
                result = {
                    "success": False,
                    "error": f"Prompt not found: {prompt_id}",
                    "available_prompts": self.prompt_registry.get_all_prompt_ids()[:10]  # First 10 for reference
                }
            
            self._track_jarvis_communication("outgoing", f"get_prompt result: {result['success']}", journey_id)
            return result
            
        except Exception as e:
            logger.error(f"Error retrieving prompt {prompt_id}: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "traceback": traceback.format_exc()
            }
    
    async def search_prompts(self, criteria: Dict[str, Any], journey_id: str = None) -> Dict[str, Any]:
        """
        Search prompts based on various criteria.
        
        Args:
            criteria: Search criteria dict with optional fields:
                - tags: List of tags to match
                - models: List of compatible models
                - prompt_family: Prompt family name
                - min_performance: Minimum performance score
                - content_search: Search in prompt content
            journey_id: Optional journey ID for tracking
            
        Returns:
            Dict containing search results
        """
        try:
            self._track_jarvis_communication("incoming", f"search_prompts: {criteria}", journey_id)
            
            # Extract search parameters
            tags = criteria.get("tags", [])
            models = criteria.get("models", [])
            prompt_family = criteria.get("prompt_family")
            min_performance = criteria.get("min_performance", 0.0)
            content_search = criteria.get("content_search")
            
            # Perform search using PromptRegistry methods
            results = self.prompt_registry.search_prompts(
                tags=tags if tags else None,
                models=models if models else None,
                prompt_family=prompt_family,
                min_performance_score=min_performance
            )
            
            # Additional content search if specified
            if content_search and results:
                content_filtered = []
                for prompt in results:
                    if content_search.lower() in prompt.get("content", "").lower():
                        content_filtered.append(prompt)
                results = content_filtered
            
            result = {
                "success": True,
                "prompts": results,
                "search_criteria": criteria,
                "count": len(results),
                "metadata": {
                    "searched_at": time.time(),
                    "total_available": len(self.prompt_registry.get_all_prompt_ids())
                }
            }
            
            self._track_jarvis_communication("outgoing", f"search found {len(results)} prompts", journey_id)
            return result
            
        except Exception as e:
            logger.error(f"Error searching prompts: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "traceback": traceback.format_exc()
            }
    
    async def track_prompt_performance(self, prompt_id: str, success: bool, response_time: float = None, 
                                     quality_score: float = None, journey_id: str = None) -> Dict[str, Any]:
        """
        Track performance metrics for a prompt.
        
        Args:
            prompt_id: Unique identifier for the prompt
            success: Whether the prompt execution was successful
            response_time: Optional response time in seconds
            quality_score: Optional quality score (0.0 to 1.0)
            journey_id: Optional journey ID for tracking
            
        Returns:
            Dict containing tracking result
        """
        try:
            self._track_jarvis_communication("incoming", f"track_performance: {prompt_id}", journey_id)
            
            # Track performance using PromptRegistry
            result = self.prompt_registry.track_performance(
                prompt_id=prompt_id,
                success=success,
                response_time=response_time,
                quality_score=quality_score
            )
            
            if result:
                tracking_result = {
                    "success": True,
                    "prompt_id": prompt_id,
                    "tracked_metrics": {
                        "success": success,
                        "response_time": response_time,
                        "quality_score": quality_score
                    },
                    "metadata": {
                        "tracked_at": time.time(),
                        "journey_id": journey_id
                    }
                }
            else:
                tracking_result = {
                    "success": False,
                    "error": f"Failed to track performance for prompt: {prompt_id}"
                }
            
            self._track_jarvis_communication("outgoing", f"tracking result: {tracking_result['success']}", journey_id)
            return tracking_result
            
        except Exception as e:
            logger.error(f"Error tracking performance for {prompt_id}: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "traceback": traceback.format_exc()
            }
    
    async def suggest_prompts(self, context: Dict[str, Any], journey_id: str = None) -> Dict[str, Any]:
        """
        Get prompt suggestions based on context and requirements.
        
        Args:
            context: Context dict with optional fields:
                - task_type: Type of task (e.g., "code_analysis", "data_validation")
                - model_preference: Preferred model
                - required_capabilities: List of required capabilities
                - performance_threshold: Minimum performance requirement
            journey_id: Optional journey ID for tracking
            
        Returns:
            Dict containing suggested prompts
        """
        try:
            self._track_jarvis_communication("incoming", f"suggest_prompts: {context}", journey_id)
            
            task_type = context.get("task_type")
            model_preference = context.get("model_preference", "claude")
            required_capabilities = context.get("required_capabilities", [])
            performance_threshold = context.get("performance_threshold", 0.7)
            
            # Get high-performing prompts
            high_performance_prompts = self.prompt_registry.search_prompts(
                min_performance_score=performance_threshold,
                models=[model_preference] if model_preference else None
            )
            
            # Filter by task type if specified
            if task_type:
                task_filtered = []
                for prompt in high_performance_prompts:
                    tags = prompt.get("tags", [])
                    content = prompt.get("content", "").lower()
                    name = prompt.get("name", "").lower()
                    
                    # Check if task type matches tags, content, or name
                    if (task_type.lower() in [tag.lower() for tag in tags] or
                        task_type.lower() in content or
                        task_type.lower() in name):
                        task_filtered.append(prompt)
                high_performance_prompts = task_filtered
            
            # Sort by performance score
            suggestions = sorted(
                high_performance_prompts,
                key=lambda p: p.get("performance", {}).get("success_rate", 0),
                reverse=True
            )[:10]  # Top 10 suggestions
            
            result = {
                "success": True,
                "suggestions": suggestions,
                "context": context,
                "count": len(suggestions),
                "metadata": {
                    "suggested_at": time.time(),
                    "criteria_used": {
                        "task_type": task_type,
                        "model_preference": model_preference,
                        "performance_threshold": performance_threshold
                    }
                }
            }
            
            self._track_jarvis_communication("outgoing", f"suggested {len(suggestions)} prompts", journey_id)
            return result
            
        except Exception as e:
            logger.error(f"Error suggesting prompts: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "traceback": traceback.format_exc()
            }
    
    async def list_prompt_families(self, journey_id: str = None) -> Dict[str, Any]:
        """
        Get a list of prompt families/categories.
        
        Args:
            journey_id: Optional journey ID for tracking
            
        Returns:
            Dict containing prompt families and their prompts
        """
        try:
            self._track_jarvis_communication("incoming", "list_prompt_families", journey_id)
            
            # Get all prompts and organize by family
            all_prompts = self.prompt_registry.get_all_prompt_ids()
            families = {}
            
            for prompt_id in all_prompts:
                prompt = self.prompt_registry.load_prompt(prompt_id)
                if prompt:
                    family = prompt.get("prompt_family", "uncategorized")
                    if family not in families:
                        families[family] = []
                    families[family].append({
                        "prompt_id": prompt_id,
                        "name": prompt.get("name"),
                        "description": prompt.get("description", "")[:100] + "..." if len(prompt.get("description", "")) > 100 else prompt.get("description", ""),
                        "tags": prompt.get("tags", [])
                    })
            
            result = {
                "success": True,
                "families": families,
                "total_families": len(families),
                "total_prompts": len(all_prompts),
                "metadata": {
                    "listed_at": time.time()
                }
            }
            
            self._track_jarvis_communication("outgoing", f"listed {len(families)} families", journey_id)
            return result
            
        except Exception as e:
            logger.error(f"Error listing prompt families: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "traceback": traceback.format_exc()
            }

class PromptRegistryHandler(BaseHandler):
    """
    Handler for managing prompts through MCP protocol.
    
    This handler provides comprehensive prompt management capabilities including:
    - Prompt retrieval and caching
    - Performance tracking and analytics
    - Search and recommendation functionality
    - Integration with agent registry for compatibility checks
    """
    
    def __init__(self):
        super().__init__()
        self.name = "handler_prompt_registry"
        self.description = "Comprehensive prompt registry management with MCP integration"
        self.version = "1.0.0"
        
        # Initialize prompt registry
        self.prompt_registry = get_prompt_registry()
        
        # Initialize orchestrator agent
        self._orchestrator_agent = PromptRegistryOrchestratorAgent(self)
        
        # Database: V2 databases used via v2_connection() context manager when needed
        # No persistent connection object required.
        
        # MCP Tools Definition
        self.mcp_tools = [
            {
                "name": "get_prompt",
                "description": "Retrieve a prompt by ID with optional version specification",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "prompt_id": {"type": "string", "description": "Unique identifier for the prompt"},
                        "version": {"type": "string", "description": "Optional specific version to retrieve"},
                        "journey_id": {"type": "string", "description": "Optional journey ID for tracking"}
                    },
                    "required": ["prompt_id"]
                }
            },
            {
                "name": "search_prompts",
                "description": "Search prompts based on various criteria",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "criteria": {
                            "type": "object",
                            "description": "Search criteria",
                            "properties": {
                                "tags": {"type": "array", "items": {"type": "string"}, "description": "Tags to match"},
                                "models": {"type": "array", "items": {"type": "string"}, "description": "Compatible models"},
                                "prompt_family": {"type": "string", "description": "Prompt family name"},
                                "min_performance": {"type": "number", "description": "Minimum performance score"},
                                "content_search": {"type": "string", "description": "Search in prompt content"}
                            }
                        },
                        "journey_id": {"type": "string", "description": "Optional journey ID for tracking"}
                    },
                    "required": ["criteria"]
                }
            },
            {
                "name": "track_performance",
                "description": "Record usage metrics for prompt optimization",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "prompt_id": {"type": "string", "description": "Unique identifier for the prompt"},
                        "success": {"type": "boolean", "description": "Whether the prompt execution was successful"},
                        "response_time": {"type": "number", "description": "Optional response time in seconds"},
                        "quality_score": {"type": "number", "description": "Optional quality score (0.0 to 1.0)"},
                        "journey_id": {"type": "string", "description": "Optional journey ID for tracking"}
                    },
                    "required": ["prompt_id", "success"]
                }
            },
            {
                "name": "suggest_prompts",
                "description": "Get prompt recommendations based on context and requirements",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "context": {
                            "type": "object",
                            "description": "Context for suggestions",
                            "properties": {
                                "task_type": {"type": "string", "description": "Type of task"},
                                "model_preference": {"type": "string", "description": "Preferred model"},
                                "required_capabilities": {"type": "array", "items": {"type": "string"}, "description": "Required capabilities"},
                                "performance_threshold": {"type": "number", "description": "Minimum performance requirement"}
                            }
                        },
                        "journey_id": {"type": "string", "description": "Optional journey ID for tracking"}
                    },
                    "required": ["context"]
                }
            },
            {
                "name": "list_prompt_families",
                "description": "Get organized list of prompt categories and their contents",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "journey_id": {"type": "string", "description": "Optional journey ID for tracking"}
                    }
                }
            }
        ]
        
        logger.info(f"PromptRegistryHandler initialized with {len(self.mcp_tools)} MCP tools")
    
    def initialize(self) -> bool:
        """
        Initialize the PromptRegistryHandler.
        
        Returns:
            bool: True if initialization successful, False otherwise
        """
        try:
            # Test prompt registry connection
            if self.prompt_registry:
                # Try to get all prompt IDs to test the connection
                prompt_ids = self.prompt_registry.get_all_prompt_ids()
                logger.info(f"PromptRegistryHandler: Successfully connected to registry with {len(prompt_ids)} prompts")
                return True
            else:
                logger.error("PromptRegistryHandler: Prompt registry not available")
                return False
                
        except Exception as e:
            logger.error(f"PromptRegistryHandler initialization failed: {str(e)}")
            return False
    
    def list_tools(self) -> List[Dict[str, Any]]:
        """
        Return list of available MCP tools.
        
        Returns:
            List of MCP tool definitions
        """
        return self.mcp_tools
    
    async def handle_task(self, task_data: Dict[str, Any]) -> HandlerResult:
        """
        Handle incoming tasks and route them to appropriate MCP tools.
        
        Args:
            task_data: Dictionary containing task information
            
        Returns:
            HandlerResult: Result of the task execution
        """
        try:
            action = task_data.get("action")
            journey_id = task_data.get("journey_id", generate_simple_id())
            
            if action == "get_prompt":
                result = await self._orchestrator_agent.get_prompt_by_id(
                    prompt_id=task_data.get("prompt_id"),
                    version=task_data.get("version"),
                    journey_id=journey_id
                )
            elif action == "search_prompts":
                result = await self._orchestrator_agent.search_prompts(
                    criteria=task_data.get("criteria", {}),
                    journey_id=journey_id
                )
            elif action == "track_performance":
                result = await self._orchestrator_agent.track_prompt_performance(
                    prompt_id=task_data.get("prompt_id"),
                    success=task_data.get("success"),
                    response_time=task_data.get("response_time"),
                    quality_score=task_data.get("quality_score"),
                    journey_id=journey_id
                )
            elif action == "suggest_prompts":
                result = await self._orchestrator_agent.suggest_prompts(
                    context=task_data.get("context", {}),
                    journey_id=journey_id
                )
            elif action == "list_prompt_families":
                result = await self._orchestrator_agent.list_prompt_families(
                    journey_id=journey_id
                )
            else:
                result = {
                    "success": False,
                    "error": f"Unknown action: {action}",
                    "available_actions": ["get_prompt", "search_prompts", "track_performance", "suggest_prompts", "list_prompt_families"]
                }
            
            return self.create_success_result(result)
            
        except Exception as e:
            logger.error(f"Error in PromptRegistryHandler.handle_task: {str(e)}")
            logger.error(traceback.format_exc())
            return self.create_error_result(f"Error handling task: {str(e)}")
    
    @property
    def orchestrator_agent(self):
        """Get the orchestrator agent for this handler"""
        return self._orchestrator_agent

# Export the handler class for dynamic loading
__all__ = ['PromptRegistryHandler']