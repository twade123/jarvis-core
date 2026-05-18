#!/usr/bin/env python3

import os
import sys
import json
import asyncio
import traceback
import logging
import datetime
from typing import Dict, List, Any, Optional, Union, Tuple
from dataclasses import dataclass
from enum import Enum
import re
import textwrap
import inspect
import anthropic
import time
import hashlib
from Handler.handler_base import BaseHandler, HandlerResult
import uuid

# Anthropic client singleton (lazy-initialized)
_anthropic_client = None

def _get_anthropic_client():
    """Get or create shared Anthropic client."""
    global _anthropic_client
    if _anthropic_client is None:
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            try:
                from Core.config import CONFIG, load_api_key
                api_key = CONFIG.get('ANTHROPIC_API_KEY') or load_api_key('ANTHROPIC')
            except ImportError:
                pass
        if not api_key:
            logging.warning("No ANTHROPIC_API_KEY found in environment or config")
            return None
        _anthropic_client = anthropic.Anthropic(api_key=api_key)
    return _anthropic_client

ANTHROPIC_MODEL = "claude-sonnet-4-5-20250929"
import random
import string

# Import from Core.config for API key loading
try:
    from Core.config import CONFIG, load_api_key
except ImportError:
    print("Warning: Could not import CONFIG and load_api_key from Core.config")
    CONFIG = {}

# Import shared MCP configuration manager
try:
    from shared_mcp_config_manager import SharedMCPConfigManager
except ImportError:
    print("Warning: Could not import SharedMCPConfigManager")
    SharedMCPConfigManager = None

# Import from Handler.handler_claude only if specifically needed
try:
    from Handler.handler_claude import ClaudeHandler, Message, MessageRole
except ImportError:
    # Define minimal versions if needed
    class MessageRole:
        SYSTEM = "system"
        USER = "user"
        ASSISTANT = "assistant"
    
    class Message:
        def __init__(self, role, content):
            self.role = role
            self.content = content

    class ClaudeHandler:
        pass

# Import boardroom connector functions for BoardRoom functionality
from Jarvis_Agent_SDK.boardroom_connector import (
    get_boardroom,
    track_request_journey,
    track_journey_step,
    update_journey_state,
    complete_journey
)

# Import generate_request_id from Jarvis_Agent_SDK.base
try:
    from Jarvis_Agent_SDK.base import generate_request_id
except ImportError:
    # Fallback implementation
    def generate_request_id(task=None):
        """Generate a unique request ID"""
        return str(uuid.uuid4())

# Import Prompt Registry for agent-prompt integration
try:
    from Jarvis_Agent_SDK.prompt_registry import PromptRegistry, get_prompt_registry
except ImportError:
    logging.warning("Could not import PromptRegistry - agent-prompt integration disabled")
    PromptRegistry = None

# Define which classes and functions are publicly exposed from this module
__all__ = ['AgentType', 'AgentCapability',
           'AgentTool', 'AgentBuilder', 'AgentSpecialization', 'AgentBuilderHandler',
           ]

class AgentType(str):
    """
    Dynamic agent type class that allows for flexible agent type creation.
    Inherits from str to allow for string-based comparison while maintaining type safety.
    """
    # Define class attributes for common types
    SPECIALIST = "specialist"
    GENERALIST = "generalist"
    COORDINATOR = "coordinator"
    EXECUTOR = "executor"
    ANALYST = "analyst"
    CREATOR = "creator"
    REVIEWER = "reviewer"
    RESEARCHER = "researcher"
    CODE_DEVELOPER = "code_developer"
    DOCUMENT_MANAGER = "document_manager"
    COMMUNICATOR = "communicator"
    DATA_ANALYST = "data_analyst"
    INFO_GATHERER = "info_gatherer"
    FILE_MANAGER = "file_manager"
    SCHEDULER = "scheduler"
    HEALTH_ADVISOR = "health_advisor"
    WEATHER_ANALYST = "weather_analyst"

    def __new__(cls, value):
        return str.__new__(cls, value.lower())

    @classmethod
    def from_str(cls, value: str) -> 'AgentType':
        """Create an AgentType from a string value"""
        return cls(value)

    def __eq__(self, other):
        if isinstance(other, str):
            return str(self).lower() == other.lower()
        return super().__eq__(other)

    @staticmethod
    def get_common_types():
        """
        Returns commonly used agent types, but does not limit to only these types.
        These are just suggestions/examples of possible agent types.
        """
        return [
            AgentType.SPECIALIST,
            AgentType.GENERALIST,
            AgentType.COORDINATOR,
            AgentType.EXECUTOR,
            AgentType.ANALYST,
            AgentType.CREATOR,
            AgentType.REVIEWER,
            AgentType.RESEARCHER,
            AgentType.CODE_DEVELOPER,
            AgentType.DOCUMENT_MANAGER,
            AgentType.COMMUNICATOR,
            AgentType.DATA_ANALYST,
            AgentType.INFO_GATHERER,
            AgentType.FILE_MANAGER,
            AgentType.SCHEDULER,
            AgentType.HEALTH_ADVISOR,
            AgentType.WEATHER_ANALYST
        ]


class AgentCapability(str, Enum):
    TECHNICAL = "technical"
    CREATIVE = "creative"
    ANALYTICAL = "analytical"
    RESEARCH = "research"
    MANAGEMENT = "management"
    COMMUNICATION = "communication"
    PROBLEM_SOLVING = "problem_solving"
    DOMAIN_SPECIFIC = "domain_specific"
    CODE_GENERATION = "code_generation"
    CODE_REVIEW = "code_review"
    DEBUGGING = "debugging"
    TESTING = "testing"
    DOCUMENT_CREATION = "document_creation"
    DOCUMENT_EDITING = "document_editing"
    TEMPLATE_MANAGEMENT = "template_management"
    EMAIL_COMPOSITION = "email_composition"
    MEETING_SCHEDULING = "meeting_scheduling"
    COMMUNICATION_MANAGEMENT = "communication_management"
    DATA_ANALYSIS = "data_analysis"
    DATA_VISUALIZATION = "data_visualization"
    STATISTICAL_ANALYSIS = "statistical_analysis"
    WEB_RESEARCH = "web_research"
    NEWS_ANALYSIS = "news_analysis"
    INFORMATION_SYNTHESIS = "information_synthesis"
    FILE_ORGANIZATION = "file_organization"
    FILE_SEARCH = "file_search"
    FILE_SHARING = "file_sharing"
    CALENDAR_MANAGEMENT = "calendar_management"
    TIME_OPTIMIZATION = "time_optimization"
    EVENT_COORDINATION = "event_coordination"
    HEALTH_TRACKING = "health_tracking"
    WELLNESS_PLANNING = "wellness_planning"
    HEALTH_ANALYSIS = "health_analysis"
    CONTENT_ANALYSIS = "content_analysis"
    RECOMMENDATION_GENERATION = "recommendation_generation"
    MEDIA_TRACKING = "media_tracking"
    WEATHER_FORECASTING = "weather_forecasting"
    CLIMATE_ANALYSIS = "climate_analysis"
    WEATHER_DATA_PROCESSING = "weather_data_processing"


@dataclass
class AgentTool:
    name: str
    description: str
    parameters: Dict
    strict: bool = True
    required: List[str] = None

    def to_dict(self) -> Dict:
        """Convert AgentTool to a dictionary format for JSON serialization."""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters,
            "strict": self.strict,
            "required": self.required or []
        }


@dataclass
class AgentSpecialization:
    domain: str
    expertise_level: int  # 1-10
    capabilities: List[AgentCapability]
    tools: List[AgentTool]
    knowledge_base: List[str]

    def to_dict(self) -> Dict:
        """Convert AgentSpecialization to a dictionary format for JSON serialization."""
        return {
            "domain": self.domain,
            "expertise_level": self.expertise_level,
            "capabilities": [cap.value for cap in self.capabilities],
            "tools": [tool.to_dict() if isinstance(tool, AgentTool) else tool for tool in self.tools],
            "knowledge_base": self.knowledge_base
        }


@dataclass
class AgentPattern:
    intent: str
    pattern: str
    action: str
    parameters: Dict


# Add predefined agent configurations
AGENT_CONFIGS = {
    "code_developer": {
        "base_capabilities": [
            # Core Development
            AgentCapability.CODE_GENERATION,
            AgentCapability.CODE_REVIEW,
            AgentCapability.DEBUGGING,
            AgentCapability.TESTING,
            AgentCapability.TECHNICAL,
            AgentCapability.ANALYTICAL,
            AgentCapability.PROBLEM_SOLVING,

            # Project Management
            AgentCapability.MANAGEMENT,
            AgentCapability.TIME_OPTIMIZATION,
            AgentCapability.COMMUNICATION,

            # Documentation
            AgentCapability.DOCUMENT_CREATION,
            AgentCapability.TEMPLATE_MANAGEMENT
        ],
        "default_tools": [
            # Core Development Tools
            AgentTool(
                name="execute_code",
                description="Execute and test code snippets with advanced error handling and performance optimization",
                parameters={
                    "type": "object",
                    "properties": {
                        "code": {"type": "string", "description": "Code to execute"},
                        "language": {"type": "string", "description": "Programming language"},
                        "test_cases": {"type": "array", "description": "Test cases to run"},
                        "performance_metrics": {"type": "boolean", "description": "Whether to include performance analysis"},
                        "security_check": {"type": "boolean", "description": "Whether to perform security analysis"},
                        "environment": {"type": "string", "description": "Execution environment (dev, test, prod)"}
                    },
                    "required": ["code", "language"]
                }
            ),
            AgentTool(
                name="review_code",
                description="Perform comprehensive code review including architecture, security, and performance analysis",
                parameters={
                    "type": "object",
                    "properties": {
                        "code": {"type": "string", "description": "Code to review"},
                        "review_type": {"type": "string", "description": "Type of review (security, performance, style, architecture)"},
                        "depth": {"type": "string", "enum": ["basic", "detailed", "comprehensive"]},
                        "include_metrics": {"type": "boolean", "description": "Include code quality metrics"},
                        "framework": {"type": "string", "description": "Framework or technology stack"},
                        "best_practices": {"type": "array", "description": "Specific best practices to check"}
                    },
                    "required": ["code"]
                }
            ),
            AgentTool(
                name="optimize_code",
                description="Optimize code for performance, memory usage, and efficiency",
                parameters={
                    "type": "object",
                    "properties": {
                        "code": {"type": "string", "description": "Code to optimize"},
                        "optimization_target": {"type": "string", "enum": ["speed", "memory", "both"]},
                        "architecture": {"type": "string", "description": "Target architecture"},
                        "constraints": {"type": "object", "description": "Resource constraints"},
                        "scalability": {"type": "boolean", "description": "Consider scalability in optimization"},
                        "cloud_platform": {"type": "string", "description": "Target cloud platform if applicable"}
                    },
                    "required": ["code", "optimization_target"]
                }
            ),
            # Database Tools
            AgentTool(
                name="database_operations",
                description="Design, optimize, and manage database operations",
                parameters={
                    "type": "object",
                    "properties": {
                        "operation_type": {"type": "string", "enum": ["design", "query", "optimize", "migrate"]},
                        "database_type": {"type": "string", "description": "Type of database (SQL, NoSQL, etc.)"},
                        "schema": {"type": "object", "description": "Database schema"},
                        "query": {"type": "string", "description": "SQL/NoSQL query"},
                        "optimization_params": {"type": "object", "description": "Optimization parameters"},
                        "security_level": {"type": "string", "description": "Security requirements"}
                    },
                    "required": ["operation_type", "database_type"]
                }
            ),
            # Project Management Tools
            AgentTool(
                name="project_management",
                description="Manage software development projects and workflows",
                parameters={
                    "type": "object",
                    "properties": {
                        "project_type": {"type": "string", "description": "Type of project"},
                        "methodology": {"type": "string", "enum": ["agile", "waterfall", "hybrid"]},
                        "timeline": {"type": "object", "description": "Project timeline"},
                        "resources": {"type": "array", "description": "Required resources"},
                        "deliverables": {"type": "array", "description": "Project deliverables"},
                        "stakeholders": {"type": "array", "description": "Project stakeholders"}
                    },
                    "required": ["project_type", "methodology"]
                }
            ),
            # API Development Tools
            AgentTool(
                name="api_development",
                description="Design and implement APIs with best practices",
                parameters={
                    "type": "object",
                    "properties": {
                        "api_type": {"type": "string", "enum": ["REST", "GraphQL", "gRPC", "WebSocket"]},
                        "endpoints": {"type": "array", "description": "API endpoints"},
                        "authentication": {"type": "string", "description": "Authentication method"},
                        "documentation": {"type": "boolean", "description": "Generate API documentation"},
                        "versioning": {"type": "string", "description": "API versioning strategy"},
                        "security_measures": {"type": "array", "description": "Security requirements"}
                    },
                    "required": ["api_type"]
                }
            ),
            # Frontend Development Tools
            AgentTool(
                name="frontend_development",
                description="Design and implement frontend applications",
                parameters={
                    "type": "object",
                    "properties": {
                        "framework": {"type": "string", "description": "Frontend framework"},
                        "components": {"type": "array", "description": "UI components"},
                        "state_management": {"type": "string", "description": "State management approach"},
                        "responsive_design": {"type": "boolean", "description": "Include responsive design"},
                        "accessibility": {"type": "boolean", "description": "Include accessibility features"},
                        "performance_optimization": {"type": "boolean", "description": "Include performance optimization"}
                    },
                    "required": ["framework"]
                }
            )
        ],
        "knowledge_base": [
            # Architecture & Design
            "Advanced Software Architecture",
            "Design Patterns and Best Practices",
            "Microservices Architecture",
            "Cloud-Native Development",
            "Serverless Architecture",
            "System Design Principles"
        ]
    },

    "specialist": {
        "base_capabilities": [
            AgentCapability.DOMAIN_SPECIFIC,
            AgentCapability.TECHNICAL,
            AgentCapability.ANALYTICAL,
            AgentCapability.RESEARCH
        ],
        "default_tools": [],
        "knowledge_base": "Specialized domain knowledge for specific tasks"
    },

    "generalist": {
        "base_capabilities": [
            AgentCapability.PROBLEM_SOLVING,
            AgentCapability.COMMUNICATION,
            AgentCapability.RESEARCH,
            AgentCapability.ANALYTICAL
        ],
        "default_tools": [],
        "knowledge_base": "Broad knowledge across multiple domains"
    }
}


import uuid
import re
import json
import logging
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
from enum import Enum, auto

from Jarvis_Agent_SDK.boardroom_connector import get_boardroom
from Jarvis_Agent_SDK.config import CONFIG, load_api_key

from Handler.handler_agent_registry import AgentRegistryHandler

class AgentBuilder:
    """Agent builder for creating specialized AI agents"""

    def __init__(self):
        """Initialize the agent builder"""
        self.logger = logging.getLogger(__name__)
        self.anthropic_client = None
        self.mcp_config_manager = None
        self.patterns = self._initialize_patterns()
        self.boardroom = None
        # Initialize BoardRoom connection if available
        self._initialize_boardroom()
        
        # Initialize database connection
        try:
            from Jarvis_Agent_SDK.import_helper import get_unified_database
            self.unified_db = get_unified_database()
            if self.unified_db and self.unified_db.is_connected:
                self.logger.info("Successfully connected to unified database")
            else:
                self.logger.warning("Could not connect to unified database")
                self.unified_db = None
        except Exception as e:
            self.logger.error(f"Error initializing database connection: {str(e)}")
            self.unified_db = None

        # Initialize client after database setup
        self._initialize_client()
        
        # Initialize Prompt Registry for agent-prompt integration
        if PromptRegistry:
            try:
                self.prompt_registry = get_prompt_registry(
                    db_path="~/Jarvis/Database/v2/prompts.db",
                    prompts_dir="~/Jarvis/Prompts"
                )
                self.logger.info("AgentBuilder: Prompt Registry integration enabled (singleton)")
            except Exception as e:
                self.logger.warning(f"AgentBuilder: Could not initialize Prompt Registry: {e}")
                self.prompt_registry = None
        else:
            self.prompt_registry = None

    def _initialize_client(self):
        """Initialize the LLM client for agent building capabilities.
        
        Uses LLMRouter when available (supports Anthropic + Ollama + any OpenAI-compatible).
        Falls back to direct Anthropic client for backward compatibility.
        """
        # Try LLMRouter first (THE swap point for cloud ↔ local)
        try:
            from Handler.modules.claude_client import LLMRouter, AnthropicClient, OpenAICompatibleClient
            self.llm_router = LLMRouter()
            api_key = os.environ.get("ANTHROPIC_API_KEY")
            if not api_key:
                try:
                    from Core.config import load_api_key
                    api_key = load_api_key('ANTHROPIC') or load_api_key('CLAUDE')
                except ImportError:
                    pass
            if api_key:
                _anthropic = AnthropicClient(api_key=api_key)
                self.llm_router.register_client("anthropic/", _anthropic, is_default=True)
                self.llm_router.register_client("claude-", _anthropic)
                # Keep backward-compat self.anthropic_client
                self.anthropic_client = _anthropic.client
            _ollama = OpenAICompatibleClient(
                base_url="http://localhost:11434/v1", api_key="none",
                default_model="qwen3.5:latest",
            )
            self.llm_router.register_client("ollama/", _ollama)
            logging.info("✅ AgentBuilder LLMRouter initialized (Anthropic + Ollama)")
            return
        except Exception as e:
            logging.warning(f"LLMRouter init failed, falling back to direct Anthropic: {e}")
            self.llm_router = None

        # Fallback: direct Anthropic client
        try:
            self.anthropic_client = _get_anthropic_client()
            if self.anthropic_client:
                logging.info("Initialized Agent Builder with Anthropic SDK (focused on agent creation, not MCP connections)")
            else:
                logging.warning("Anthropic client not available - Agent Builder will use basic functionality")
        except Exception as e:
            logging.error(f"Error initializing Agent Builder: {str(e)}")
            logging.warning("Agent Builder will operate in basic mode without Anthropic client")
            self.anthropic_client = None

    def _initialize_patterns(self) -> Dict[AgentType, List[AgentPattern]]:
        """Initialize patterns for matching user requests to agent actions"""
        patterns = {}

        # Code Developer Patterns
        patterns[AgentType.CODE_DEVELOPER] = [
            AgentPattern(
                intent="write_code",
                pattern="write|create|generate|implement|develop|code",
                action="execute_code",
                parameters={"language": "", "code": "", "test_cases": []}
            ),
            AgentPattern(
                intent="review_code",
                pattern="review|check|analyze|examine|assess|evaluate",
                action="review_code",
                parameters={"code": "", "review_type": "comprehensive"}
            ),
            AgentPattern(
                intent="optimize_code",
                pattern="optimize|improve|enhance|speed up|make faster|efficient",
                action="optimize_code",
                parameters={"code": "", "optimization_target": "both"}
            ),
            AgentPattern(
                intent="debug_code",
                pattern="debug|fix|solve|troubleshoot|resolve issue",
                action="execute_code",
                parameters={"code": "", "language": "", "test_cases": []}
            )
        ]

        # Document Manager Patterns
        patterns[AgentType.DOCUMENT_MANAGER] = [
            AgentPattern(
                intent="create_document",
                pattern="create|write|generate|draft|compose|make document",
                action="create_document",
                parameters={"document_type": "", "content": ""}
            ),
            AgentPattern(
                intent="edit_document",
                pattern="edit|modify|update|revise|change|improve document",
                action="edit_document",
                parameters={"document": "", "edit_type": "all"}
            ),
            AgentPattern(
                intent="manage_template",
                pattern="template|create template|manage template|update template",
                action="manage_templates",
                parameters={"template_name": "", "template_type": ""}
            )
        ]

        # Communicator Patterns
        patterns[AgentType.COMMUNICATOR] = [
            AgentPattern(
                intent="send_email",
                pattern="send|write|compose|draft email|message",
                action="compose_email",
                parameters={"subject": "", "content": "", "recipients": []}
            ),
            AgentPattern(
                intent="schedule_meeting",
                pattern="schedule|arrange|set up|organize|plan meeting",
                action="schedule_meeting",
                parameters={"participants": [], "duration": ""}
            ),
            AgentPattern(
                intent="manage_communication",
                pattern="manage|handle|coordinate|organize communication",
                action="manage_communications",
                parameters={"channel": "", "priority": "medium"}
            )
        ]

        # Data Analyst Patterns
        patterns[AgentType.DATA_ANALYST] = [
            AgentPattern(
                intent="analyze_data",
                pattern="analyze|examine|study|investigate|process data",
                action="analyze_data",
                parameters={"data": "", "analysis_type": ""}
            ),
            AgentPattern(
                intent="visualize_data",
                pattern="visualize|plot|chart|graph|display data",
                action="create_visualization",
                parameters={"data": "", "chart_type": ""}
            ),
            AgentPattern(
                intent="predict_data",
                pattern="predict|forecast|model|estimate|project data",
                action="predictive_modeling",
                parameters={"data": "", "target": "", "model_type": ""}
            )
        ]

        # Health Advisor Patterns
        patterns[AgentType.HEALTH_ADVISOR] = [
            AgentPattern(
                intent="health_analysis",
                pattern="analyze health|check health|assess health|evaluate health",
                action="analyze_health_data",
                parameters={"data": "", "analysis_type": ""}
            ),
            AgentPattern(
                intent="wellness_plan",
                pattern="plan wellness|create health plan|design program",
                action="create_wellness_plan",
                parameters={"goals": [], "preferences": {}}
            )
        ]

        # Weather Analyst Patterns
        patterns[AgentType.WEATHER_ANALYST] = [
            AgentPattern(
                intent="weather_forecast",
                pattern="forecast|predict|check weather|weather report",
                action="analyze_weather",
                parameters={"location": "", "timeframe": ""}
            ),
            AgentPattern(
                intent="climate_analysis",
                pattern="analyze climate|study weather patterns|climate trends",
                action="analyze_climate",
                parameters={"region": "", "time_period": ""}
            )
        ]

        return patterns

    def _initialize_boardroom(self):
        """Initialize connection to BoardRoom for tracking agent performance"""
        try:
            self.boardroom = get_boardroom()
            if self.boardroom:
                logging.info(
                    "Successfully connected to BoardRoom for agent performance tracking")
            else:
                logging.warning(
                    "Could not connect to BoardRoom - agent performance tracking limited")
        except ImportError:
            logging.info(
                "BoardRoom utilities not available - agent performance tracking disabled")
            self.boardroom = None

    def match_user_request(self, request: str, agent_type: AgentType) -> Optional[Tuple[str, Dict]]:
        """Match user request to appropriate agent action"""
        if agent_type not in self.patterns:
            return None

        for pattern in self.patterns[agent_type]:
            if re.search(pattern.pattern, request.lower()):
                return pattern.action, pattern.parameters

        return None

    async def create_agent(
        self,
        specialization: AgentSpecialization,
        agent_name: str,
        agent_type: AgentType,
        module_name: str,
        team_name: str
    ) -> str:
        """Create a new agent with the given specialization."""
        
        # Generate journey ID for tracking
        journey_id = self._generate_journey_id("agent_creation")
        
        try:
            # Track journey start
            await self._track_journey_step(
                journey_id=journey_id,
                step_name="start_agent_creation",
                status="in_progress",
                description=f"Starting creation of agent {agent_name}",
                parameters={
                    "agent_name": agent_name,
                    "agent_type": str(agent_type),
                    "module_name": module_name
                }
            )
            
            # Select optimal model
            model = self._select_optimal_model(specialization)
            
            # Generate system prompt
            system_prompt = self._generate_system_prompt(agent_name, agent_type, specialization)
            
            # Create tools configuration
            tools = self._create_agent_tools(specialization)
            
            # Generate function schema
            function_schema = self._generate_function_schema(specialization)
            
            # Generate unique agent ID
            agent_id = str(uuid.uuid4())
            
            # Create agent configuration
            agent_config = {
                "agent_id": agent_id,
                "agent_name": agent_name,
                "agent_type": str(agent_type),
                "module_name": module_name,
                "model": model,
                "system_prompt": system_prompt,
                "tools": tools,
                "function_schema": function_schema,
                "specialization": specialization.to_dict(),
                "metadata": {
                    "team_name": team_name,
                    "created_at": time.time(),
                    "created_by": "agent_builder"
                }
            }
            
            # Track configuration generation
            await self._track_journey_step(
                journey_id=journey_id,
                step_name="configuration_generated",
                status="success",
                description="Generated agent configuration",
                parameters=agent_config
            )
            
            # Register the agent
            try:
                registry = AgentRegistryHandler()
                result = await registry.register_module_agent(
                    agent_id=agent_id,
                    agent_name=agent_name,
                    agent_type=str(agent_type),
                    module_name=module_name,
                    capabilities=[str(cap) for cap in specialization.capabilities],
                    metadata={
                        "team_name": team_name,
                        "model": model,
                        "tools": tools,
                        "specialization": specialization.to_dict()
                    }
                )
                
                if not result.success:
                    raise Exception(f"Agent registration failed: {result.error}")
                
                # Track successful registration
                await self._track_journey_step(
                    journey_id=journey_id,
                    step_name="agent_registered",
                    status="success",
                    description=f"Successfully registered agent {agent_name}",
                    parameters={"agent_id": agent_id}
                )
                
                return agent_id
                
            except Exception as e:
                error_msg = f"Error registering agent: {str(e)}"
                await self._track_journey_step(
                    journey_id=journey_id,
                    step_name="registration_failed",
                    status="error",
                    description=error_msg,
                    error=str(e)
                )
                raise Exception(error_msg)
                
        except Exception as e:
            error_msg = f"Error creating agent: {str(e)}"
            await self._track_journey_step(
                journey_id=journey_id,
                step_name="creation_failed",
                status="error",
                description=error_msg,
                error=str(e)
            )
            raise Exception(error_msg)

    def create_agent_simple(self, name: str, agent_type: str,
                            specialization: Optional[AgentSpecialization] = None,
                            skills: Optional[List[Dict]] = None) -> Dict:
        """
        Complete agent creation: prompt + skills + registry integration.
        
        Creates the full agent package in one call:
        1. Generates domain-specific system prompt from knowledge_base
        2. Saves prompt to prompt_registry + tracks agent-prompt pairing
        3. Registers all skills (python_callable, mcp_tool, prompt_template)
           in AgentRegistry so the agent is fully operational and clonable
        
        Parameters
        ----------
        name : str
            Agent name (e.g. "intelligence", "technical_analyst")
        agent_type : str
            Agent type string (e.g. "data_collection", "analysis")
        specialization : AgentSpecialization | None
            Domain, expertise, capabilities, knowledge_base.
            knowledge_base drives prompt content.
        skills : list[dict] | None
            Skill definitions to register. Each dict has:
            - name: skill name
            - type: "python_callable" | "mcp_tool" | "prompt_template"
            - definition: dict with module/function or handler/action or template data
            If None, no skills registered (caller can do it separately).
        
        Returns
        -------
        dict
            agent_id, name, type, system_prompt, prompt_id, tools,
            capabilities, knowledge_base, skills_registered, metadata.
        """
        try:
            # Create default specialization if none provided
            if specialization is None:
                specialization = AgentSpecialization(
                    domain=agent_type,
                    expertise_level=8,
                    capabilities=[AgentCapability.ANALYTICAL, AgentCapability.PROBLEM_SOLVING],
                    tools=[],
                    knowledge_base=[]
                )
            
            # Generate system prompt (uses knowledge_base via all generation paths)
            system_prompt = self._generate_system_prompt(name, AgentType(agent_type), specialization)
            
            # Create basic tools configuration
            tools = self._create_agent_tools(specialization)
            
            # Generate unique agent ID
            agent_id = str(uuid.uuid4())
            
            # --- Save prompt to registry and track pairing ---
            prompt_id = None
            try:
                prompt_id = self._save_to_prompt_registry(
                    prompt=system_prompt,
                    agent_type=str(agent_type),
                    specialization=specialization.domain
                )
                if prompt_id:
                    self.logger.info(f"Saved prompt to registry for {name}: {prompt_id}")
                    compatibility_key = self._create_compatibility_key(
                        {"prompt_id": prompt_id},
                        {
                            "type": str(agent_type),
                            "domain": specialization.domain,
                            "capabilities": [str(cap) for cap in specialization.capabilities]
                        }
                    )
                    self._track_agent_prompt_pairing(agent_id, prompt_id, compatibility_key)
                    self.logger.info(f"Tracked agent-prompt pairing for {name}: {agent_id} -> {prompt_id}")
            except Exception as prompt_exc:
                self.logger.warning(f"Prompt registry operations failed for {name}: {prompt_exc}")
            
            # --- Register skills in AgentRegistry ---
            skills_registered = []
            if skills:
                try:
                    from Handler.handler_agent_registry import AgentRegistryHandler
                    registry = AgentRegistryHandler()
                    import asyncio
                    
                    for skill_def in skills:
                        skill_name = skill_def.get("name", "unnamed")
                        skill_type = skill_def.get("type", "python_callable")
                        definition = skill_def.get("definition", {})
                        try:
                            asyncio.run(
                                registry.register_skill(
                                    agent_id=agent_id,
                                    skill_name=skill_name,
                                    skill_type=skill_type,
                                    definition_json=json.dumps(definition),
                                )
                            )
                            skills_registered.append(skill_name)
                            self.logger.info(f"Registered skill {skill_name} ({skill_type}) for {name}")
                        except Exception as skill_exc:
                            self.logger.warning(f"Skill {skill_name} registration failed: {skill_exc}")
                    
                    # Also register knowledge_base as a consolidated prompt_template skill
                    if specialization.knowledge_base:
                        kb_definition = {
                            "agent_name": name,
                            "domain": specialization.domain,
                            "expertise_level": specialization.expertise_level,
                            "knowledge_items": specialization.knowledge_base,
                            "item_count": len(specialization.knowledge_base),
                        }
                        try:
                            asyncio.run(
                                registry.register_skill(
                                    agent_id=agent_id,
                                    skill_name=f"{name}_domain_knowledge",
                                    skill_type="prompt_template",
                                    definition_json=json.dumps(kb_definition),
                                )
                            )
                            skills_registered.append(f"{name}_domain_knowledge")
                            self.logger.info(
                                f"Registered domain knowledge skill for {name} ({len(specialization.knowledge_base)} items)"
                            )
                        except Exception as kb_exc:
                            self.logger.warning(f"Knowledge base skill for {name} failed: {kb_exc}")
                            
                except ImportError:
                    self.logger.warning("AgentRegistryHandler not available — skills not registered")
            
            # Create agent configuration with full metadata
            agent_config = {
                "agent_id": agent_id,
                "name": name,
                "type": agent_type,
                "system_prompt": system_prompt,
                "prompt_id": prompt_id,
                "tools": tools,
                "capabilities": [str(cap) for cap in specialization.capabilities],
                "knowledge_base": specialization.knowledge_base,
                "skills_registered": skills_registered,
                "specialization": specialization.to_dict(),
                "metadata": {
                    "created_at": time.time(),
                    "created_by": "agent_builder",
                    "prompt_id": prompt_id,
                    "domain": specialization.domain,
                    "expertise_level": specialization.expertise_level,
                    "skills_count": len(skills_registered),
                }
            }
            
            return agent_config
            
        except Exception as e:
            self.logger.error(f"Error in create_agent_simple: {str(e)}")
            return {"error": str(e)}

    # ── Vault-Aware Agent Creation ───────────────────────────────

    def find_or_build_agent(self, task_description: str, board_seat: str = None) -> Dict:
        """Registry-first agent resolution. Boardroom calls this.
        
        1. Search registry for an agent whose skill matches the task
        2. If found → return existing agent (with vault prompt)
        3. If not found → create new agent + skill paired in vault
        
        This is what the boardroom uses: never build what you already have.
        """
        import sqlite3
        db_path = "~/Jarvis/Database/v2/agents.db"

        # Step 1: Search existing agents by skill match
        match = self._search_registry_for_task(task_description, board_seat)
        if match:
            self.logger.info(f"Found existing agent for task: {match['agent_name']} ({match['agent_id']})")
            # Load prompt from vault
            try:
                from knowledge.agent_factory import get_agent_prompt
                prompt = get_agent_prompt(match["agent_id"])
                if prompt:
                    match["system_prompt"] = prompt
            except Exception:
                pass
            return {"action": "existing", "agent": match}
        
        # Step 2: No match — build new agent + skill
        self.logger.info(f"No existing agent for task, building new one (seat={board_seat})")
        result = self.create_from_skill(
            task_description=task_description,
            board_seat=board_seat or "CDO",
        )
        return {"action": "created", "agent": result}

    def _search_registry_for_task(self, task: str, board_seat: str = None) -> Optional[Dict]:
        """Search agent registry for best match to a task description."""
        import sqlite3
        conn = sqlite3.connect("~/Jarvis/Database/v2/agents.db", isolation_level=None)
        conn.row_factory = sqlite3.Row

        # Build query — filter by seat if provided
        query = """
            SELECT agent_id, agent_name, agent_type, board_seat,
                   prompt_focus, system_prompt_path, capabilities
            FROM agent_registry
            WHERE status = 'available'
        """
        params = []
        if board_seat:
            query += " AND board_seat = ?"
            params.append(board_seat)
        
        rows = conn.execute(query, params).fetchall()
        conn.close()
        
        if not rows:
            return None
        
        # Simple keyword matching (upgradeable to embeddings later)
        task_lower = task.lower()
        task_words = set(task_lower.split())
        
        best_match = None
        best_score = 0
        
        for row in rows:
            agent = dict(row)
            # Score based on keyword overlap with prompt_focus + capabilities
            search_text = f"{agent.get('prompt_focus', '')} {agent.get('agent_name', '')} {agent.get('capabilities', '')}".lower()
            search_words = set(search_text.split())
            
            overlap = len(task_words & search_words)
            if overlap > best_score:
                best_score = overlap
                best_match = agent
        
        # Require minimum relevance
        if best_score >= 2:
            return best_match
        return None

    def create_from_skill(self, task_description: str, board_seat: str = "CDO",
                          skill_name: str = None) -> Dict:
        """Create a new agent + skill paired together in the vault.
        
        Uses the skill-development methodology (Anthropic's official process)
        to generate both a proper SKILL.md-style reference AND an agent prompt,
        stored as a single file in knowledge/skills/.
        """
        import re as _re
        from pathlib import Path
        
        vault_skills = Path("~/Jarvis/knowledge/skills")
        vault_skills.mkdir(parents=True, exist_ok=True)
        
        # Generate skill name from task if not provided
        if not skill_name:
            # Clean task into a kebab-case name
            words = _re.sub(r'[^a-zA-Z0-9\s]', '', task_description.lower()).split()[:4]
            skill_name = "-".join(words) if words else "custom-agent"
        
        agent_id = f"skill_{_re.sub(r'[^a-zA-Z0-9]', '_', skill_name).lower()}"
        agent_name = _re.sub(r'[-_.]', ' ', skill_name).strip().title().replace(' ', '')
        
        team_name = {
            "CTO": "Engineering & Technology",
            "CSO": "Strategy & Intelligence",
            "CRO": "Risk & Compliance",
            "CDO": "Data & Analytics",
        }.get(board_seat, "General")
        
        # Generate prompt + skill content
        # If we have an LLM client, use it for high-quality generation
        prompt = ""
        skill_body = ""
        
        if self.anthropic_client:
            try:
                # Load skill-creator guide for quality principles
                guide_path = "~/Jarvis/.agents/skills/skill-creator/SKILL.md"
                guide = ""
                if os.path.exists(guide_path):
                    with open(guide_path) as f:
                        guide = f.read()[:4000]

                generation_prompt = (
                    f"Create a specialized agent for this task:\n"
                    f"Task: {task_description}\n"
                    f"Team: {team_name} (managed by {board_seat})\n"
                    f"Agent Name: {agent_name}\n\n"
                    f"Generate TWO sections:\n\n"
                    f"1. AGENT PROMPT — A system prompt that gives the agent:\n"
                    f"   - Clear identity and expertise domain\n"
                    f"   - Specific methodologies and frameworks to apply\n"
                    f"   - Communication protocol (report to team lead, collaborate with peers)\n"
                    f"   - Quality standards\n\n"
                    f"2. SKILL REFERENCE — Practitioner-level domain knowledge. CRITICAL QUALITY RULES:\n"
                    f"   - Claude is already smart. Only include knowledge Claude does NOT already have.\n"
                    f"   - Prefer concise examples over verbose explanations.\n"
                    f"   - Include 3+ CONCRETE before/after examples using Weak/Strong or BAD/GOOD format.\n"
                    f"     Example: Weak: 'Submit' / Strong: 'Start Free Trial' — with WHY it's better.\n"
                    f"   - Use the language practitioners actually use in this domain, not generic corporate.\n"
                    f"   - Include specific anti-patterns with explanations of WHY they fail.\n"
                    f"   - Prioritize actionable checklists over abstract framework names.\n"
                    f"   - Each section should advance one specific idea. No filler paragraphs.\n"
                    f"   - Write in imperative form: 'Check for X' not 'It is important to check for X'.\n\n"
                    f"Quality reference — match this writing style:\n"
                    f"```\n"
                    f"### Value Proposition Clarity (Highest Impact)\n"
                    f"**Check for:**\n"
                    f"- Can a visitor understand what this is within 5 seconds?\n"
                    f"- Is the primary benefit clear, specific, and differentiated?\n"
                    f"**Common issues:**\n"
                    f"- Feature-focused instead of benefit-focused\n"
                    f"- Too vague or too clever (sacrificing clarity)\n\n"
                    f"### CTA Copy\n"
                    f"  Weak: 'Submit,' 'Sign Up,' 'Learn More'\n"
                    f"  Strong: 'Start Free Trial,' 'Get My Report,' 'See Pricing'\n"
                    f"```\n\n"
                    f"Skill writing methodology:\n{guide[:3000]}\n\n"
                    f"Output format:\n"
                    f"## Agent Prompt\n[prompt here]\n\n"
                    f"## Skill Reference\n[reference here]"
                )

                response = self.anthropic_client.messages.create(
                    model="claude-sonnet-4-20250514",  # Use Sonnet for generation (cost effective)
                    max_tokens=6000,
                    messages=[{"role": "user", "content": generation_prompt}]
                )
                
                content = response.content[0].text if response.content else ""
                
                # Split into sections
                if "## Skill Reference" in content:
                    parts = content.split("## Skill Reference", 1)
                    prompt = parts[0].replace("## Agent Prompt", "").strip()
                    skill_body = parts[1].strip()
                else:
                    prompt = content[:len(content)//2]
                    skill_body = content[len(content)//2:]
                    
            except Exception as e:
                self.logger.warning(f"LLM generation failed: {e}, using template")
        
        # Fallback: template-based generation
        if not prompt:
            prompt = (
                f"# {agent_name}\n\n"
                f"You are a specialized agent on the **{team_name} Team** (managed by the {board_seat}).\n\n"
                f"## Your Expertise\n{task_description}\n\n"
                f"## Your Role\n"
                f"- Execute tasks in your domain when assigned by your team lead ({board_seat})\n"
                f"- Collaborate with other workspace agents\n"
                f"- Report progress through workspace communication\n"
                f"- Escalate to team lead when uncertain\n"
            )
            skill_body = f"Task domain: {task_description}\n\n*Skill content will be refined through use and Opus corrections.*"
        
        # Write merged skill+prompt to vault
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc).isoformat()
        vault_content = (
            f"---\n"
            f"type: skill_agent\n"
            f"source: agent_builder\n"
            f"skill_name: {skill_name}\n"
            f"agent_id: {agent_id}\n"
            f"agent_name: {agent_name}\n"
            f"board_seats: [{board_seat}]\n"
            f"generated_at: {now}Z\n"
            f"refinement_count: 0\n"
            f"---\n\n"
            f"# {agent_name}\n\n"
            f"## Agent Prompt\n{prompt}\n\n"
            f"## Skill Reference\n{skill_body}\n\n"
            f"## Learnings\n*No learnings yet.*\n"
        )
        
        vault_path = vault_skills / f"{skill_name}.md"
        vault_path.write_text(vault_content, encoding="utf-8")
        
        # Register in agent_registry
        import sqlite3
        conn = sqlite3.connect("~/Jarvis/Database/v2/agents.db", isolation_level=None)
        conn.execute("""
            INSERT OR REPLACE INTO agent_registry (
                agent_id, agent_name, agent_type, module_name,
                capabilities, status, created_at, updated_at,
                metadata, system_prompt_path, board_seat, prompt_focus
            ) VALUES (?, ?, 'skill_agent', 'handler_agent_builder',
                ?, 'available', ?, ?,
                ?, ?, ?, ?)
        """, (
            agent_id, agent_name,
            json.dumps({"task": task_description, "seat": board_seat}),
            now, now,
            json.dumps({"source": "agent_builder", "vault_path": str(vault_path)}),
            str(vault_path),
            board_seat, skill_name,
        ))
        conn.commit()
        conn.close()
        
        self.logger.info(f"Created agent {agent_name} ({agent_id}) in vault + registry")
        
        return {
            "agent_id": agent_id,
            "agent_name": agent_name,
            "board_seat": board_seat,
            "skill_name": skill_name,
            "vault_path": str(vault_path),
            "system_prompt": prompt,
        }

    def _select_optimal_model(self, specialization: AgentSpecialization) -> str:
        """Select the best model based on specialization requirements"""

        # Score models based on specialization needs
        claude_score = 0
        gpt_score = 0

        # Technical capabilities
        if AgentCapability.TECHNICAL in specialization.capabilities:
            claude_score += 8
            gpt_score += 9

        # Creative capabilities
        if AgentCapability.CREATIVE in specialization.capabilities:
            claude_score += 9
            gpt_score += 8

        # Analytical capabilities
        if AgentCapability.ANALYTICAL in specialization.capabilities:
            claude_score += 9
            gpt_score += 9

        # Research capabilities
        if AgentCapability.RESEARCH in specialization.capabilities:
            claude_score += 9
            gpt_score += 8

        # Communication capabilities
        if AgentCapability.COMMUNICATION in specialization.capabilities:
            claude_score += 9
            gpt_score += 8

        return "claude" if claude_score >= gpt_score else "gpt"

    def _search_prompt_registry(self, agent_type: str, specialization: str) -> List[Dict]:
        """
        Search Prompt Registry for suitable existing prompts.
        
        Args:
            agent_type: Type of agent (e.g., 'code_developer', 'analyst')
            specialization: Domain specialization (e.g., 'python', 'data_analysis')
            
        Returns:
            List of suitable prompts from the registry
        """
        if not self.prompt_registry:
            return []
            
        try:
            # Search by agent type and specialization tags
            search_tags = [agent_type.lower(), specialization.lower(), 'agent_builder']
            
            suitable_prompts = self.prompt_registry.search_prompts(
                agent_type='agent',
                tags=search_tags,
                min_performance_score=0.7,
                limit=5
            )
            
            self.logger.info(f"Found {len(suitable_prompts)} suitable prompts for {agent_type}/{specialization}")
            return suitable_prompts
            
        except Exception as e:
            self.logger.error(f"Error searching prompt registry: {str(e)}")
            return []

    async def _verify_prompt_compatibility(self, prompt: Dict, agent_config: Dict) -> Dict:
        """
        Verify prompt-agent compatibility using orchestrator validation.
        
        Args:
            prompt: Prompt data from registry
            agent_config: Agent configuration details
            
        Returns:
            Dict with compatibility assessment
        """
        try:
            # Create compatibility assessment
            compatibility = {
                'compatible': False,
                'compatibility_score': 0.0,
                'reasons': [],
                'recommended_modifications': [],
                'approval_required': False
            }
            
            # Basic compatibility checks
            agent_type = agent_config.get('type', '').lower()
            agent_domain = agent_config.get('domain', '').lower()
            
            # Check if prompt tags match agent requirements
            prompt_tags = prompt.get('tags', [])
            score = 0.0
            
            # Agent type matching (40% weight)
            if agent_type in [tag.lower() for tag in prompt_tags]:
                score += 0.4
                compatibility['reasons'].append(f"Agent type '{agent_type}' matches prompt tags")
            
            # Domain specialization (30% weight)
            if agent_domain in [tag.lower() for tag in prompt_tags]:
                score += 0.3
                compatibility['reasons'].append(f"Domain '{agent_domain}' matches prompt specialization")
            
            # Performance history (20% weight)
            performance_metrics = prompt.get('metadata', {}).get('performance_metrics', {})
            success_rate = performance_metrics.get('success_rate', 0.0)
            if success_rate > 0.8:
                score += 0.2
                compatibility['reasons'].append(f"High success rate: {success_rate:.1%}")
            elif success_rate > 0.6:
                score += 0.1
                
            # Model compatibility (10% weight)
            models = prompt.get('models', {})
            if isinstance(models, dict):
                compatible_models = models.get('compatible', [])
                if 'claude' in compatible_models or 'gpt' in compatible_models:
                    score += 0.1
                    compatibility['reasons'].append("Compatible with required models")
            
            compatibility['compatibility_score'] = score
            compatibility['compatible'] = score >= 0.7
            compatibility['approval_required'] = 0.6 <= score < 0.9
            
            if score < 0.7:
                compatibility['reasons'].append("Score below compatibility threshold")
                
            self.logger.info(f"Prompt compatibility score: {score:.2f} for {agent_type}/{agent_domain}")
            return compatibility
            
        except Exception as e:
            self.logger.error(f"Error verifying prompt compatibility: {str(e)}")
            return {
                'compatible': False,
                'compatibility_score': 0.0,
                'reasons': [f"Verification error: {str(e)}"],
                'recommended_modifications': [],
                'approval_required': False
            }

    def _adapt_prompt_for_agent(self, prompt: Dict, agent_name: str) -> str:
        """
        Customize existing prompt for specific agent requirements.
        
        Args:
            prompt: Prompt data from registry
            agent_name: Name of the agent being created
            
        Returns:
            Adapted prompt content
        """
        try:
            prompt_content = prompt.get('content', {})
            system_prompt = prompt_content.get('system_prompt', '')
            
            if not system_prompt:
                system_prompt = prompt_content.get('content', '')
                
            # Adapt the prompt for the specific agent
            adapted_prompt = system_prompt.replace(
                "{agent_name}", agent_name
            ).replace(
                "You are an AI", f"You are {agent_name}, an AI"
            ).replace(
                "You are a", f"You are {agent_name}, a"
            )
            
            self.logger.info(f"Adapted prompt for agent: {agent_name}")
            return adapted_prompt
            
        except Exception as e:
            self.logger.error(f"Error adapting prompt for agent: {str(e)}")
            return prompt.get('content', {}).get('system_prompt', '')

    def _save_to_prompt_registry(self, prompt: str, agent_type: str, specialization: str) -> str:
        """
        Store newly generated prompt in registry with metadata.
        
        Args:
            prompt: Generated prompt content
            agent_type: Type of agent
            specialization: Domain specialization
            
        Returns:
            Prompt ID in registry
        """
        if not self.prompt_registry:
            return None
            
        try:
            # Generate unique prompt ID
            prompt_id = f"agent_builder_{agent_type}_{specialization}_{uuid.uuid4().hex[:8]}"
            
            # Create prompt data structure
            prompt_data = {
                "prompt_id": prompt_id,
                "name": f"Agent Builder - {agent_type.title()} ({specialization.title()})",
                "description": f"Auto-generated prompt for {agent_type} agents specializing in {specialization}",
                "content": {
                    "system_prompt": prompt,
                    "user_prefix": "Please analyze the following request:",
                    "parameters": {
                        "temperature": 0.7,
                        "max_tokens": 2000
                    }
                },
                "models": {
                    "compatible": ["claude", "gpt"],
                    "preferred": "claude"
                },
                "agent_type": "agent",
                "tags": [agent_type.lower(), specialization.lower(), "agent_builder", "auto_generated"],
                "metadata": {
                    "created_at": datetime.datetime.now().isoformat(),
                    "author": "AgentBuilder",
                    "created_by": "agent_builder",
                    "performance_metrics": {
                        "success_rate": 0.8,  # Default for new prompts
                        "avg_response_time": 2.0
                    }
                },
                "version": "1.0"
            }
            
            # Register the prompt
            if self.prompt_registry.register_prompt(prompt_data):
                self.logger.info(f"Saved new prompt to registry: {prompt_id}")
                return prompt_id
            else:
                self.logger.error("Failed to register prompt in registry")
                return None
                
        except Exception as e:
            self.logger.error(f"Error saving prompt to registry: {str(e)}")
            return None

    def _track_agent_prompt_pairing(self, agent_id: str, prompt_id: str, compatibility_key: str = None) -> None:
        """
        Track agent-prompt association for performance monitoring.
        
        Args:
            agent_id: Unique identifier for the agent
            prompt_id: Prompt ID from registry
            compatibility_key: Compatibility verification key
        """
        if not self.prompt_registry:
            return
            
        try:
            # Connect to database to store pairing
            import sqlite3
            conn = sqlite3.connect("~/Jarvis/Database/v2/prompts.db", isolation_level=None)
            cursor = conn.cursor()

            # Generate pairing ID and compatibility key if needed
            pairing_id = str(uuid.uuid4())
            if not compatibility_key:
                compatibility_key = str(uuid.uuid4())

            # Insert pairing record
            cursor.execute("""
                INSERT INTO agent_prompt_pairings 
                (pairing_id, agent_id, prompt_id, compatibility_key, assignment_timestamp, is_active)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (pairing_id, agent_id, prompt_id, compatibility_key, 
                  datetime.datetime.now().isoformat(), 1))
            
            conn.commit()
            conn.close()
            
            self.logger.info(f"Tracked agent-prompt pairing: {agent_id} -> {prompt_id}")
            
        except Exception as e:
            self.logger.error(f"Error tracking agent-prompt pairing: {str(e)}")

    def _create_compatibility_key(self, prompt: Dict, agent_config: Dict) -> str:
        """
        Generate unique compatibility identifier for agent-prompt pairing.
        
        Args:
            prompt: Prompt data
            agent_config: Agent configuration
            
        Returns:
            Unique compatibility key
        """
        try:
            # Create hash of key compatibility factors
            compatibility_data = {
                'prompt_id': prompt.get('prompt_id', ''),
                'agent_type': agent_config.get('type', ''),
                'domain': agent_config.get('domain', ''),
                'capabilities': sorted(agent_config.get('capabilities', []))
            }
            
            compatibility_str = json.dumps(compatibility_data, sort_keys=True)
            compatibility_hash = hashlib.md5(compatibility_str.encode()).hexdigest()
            
            return f"compat_{compatibility_hash[:16]}"
            
        except Exception as e:
            self.logger.error(f"Error creating compatibility key: {str(e)}")
            return str(uuid.uuid4())

    def _generate_system_prompt(
        self,
        name: str,
        agent_type: AgentType,
        specialization: AgentSpecialization
    ) -> str:
        """
        Generate a dynamic, specialized system prompt with full Prompt Registry integration.
        
        INTEGRATED WORKFLOW:
        1. Search Prompt Registry for compatible existing prompts
        2. Verify compatibility using orchestrator validation
        3. Adapt existing prompt or generate new specialized prompt
        4. Save new prompts to registry for future reuse
        5. Track agent-prompt pairing for performance monitoring
        
        Args:
            name: Agent name
            agent_type: Type of agent being created
            specialization: Agent specialization details
            
        Returns:
            Optimized system prompt string
        """
        self.logger.info(f"🔄 Starting integrated prompt generation for {name} ({agent_type}/{specialization.domain})")
        
        # PHASE 1: Search existing prompts in registry
        suitable_prompts = []
        generated_prompt = None
        prompt_id = None
        agent_id = str(uuid.uuid4())  # Generate agent ID for tracking
        
        if self.prompt_registry:
            try:
                self.logger.info("🔍 Searching Prompt Registry for compatible prompts...")
                suitable_prompts = self._search_prompt_registry(
                    agent_type=str(agent_type),
                    domain=specialization.domain
                )
                self.logger.info(f"Found {len(suitable_prompts)} potentially suitable prompts")
            except Exception as e:
                self.logger.warning(f"Error searching prompt registry: {str(e)}")
        
        # PHASE 2: Verify compatibility for existing prompts
        best_prompt = None
        best_compatibility = None
        
        if suitable_prompts:
            agent_config = {
                'type': str(agent_type),
                'domain': specialization.domain,
                'capabilities': [str(cap) for cap in specialization.capabilities],
                'expertise_level': specialization.expertise_level,
                'name': name
            }
            
            self.logger.info("🧠 Verifying prompt compatibility with orchestrator...")
            
            for prompt in suitable_prompts:
                try:
                    # Async compatibility verification
                    import asyncio
                    compatibility = asyncio.run(self._verify_prompt_compatibility(prompt, agent_config))
                    
                    if compatibility['compatibility_score'] > 0.7:  # High compatibility threshold
                        if not best_compatibility or compatibility['compatibility_score'] > best_compatibility['compatibility_score']:
                            best_prompt = prompt
                            best_compatibility = compatibility
                            
                except Exception as e:
                    self.logger.warning(f"Error verifying compatibility for prompt {prompt.get('prompt_id', 'unknown')}: {str(e)}")
        
        # PHASE 3: Use best existing prompt or generate new one
        if best_prompt and best_compatibility['compatibility_score'] > 0.8:
            # High compatibility - adapt existing prompt
            self.logger.info(f"✅ Using compatible existing prompt (score: {best_compatibility['compatibility_score']:.2f})")
            
            generated_prompt = self._adapt_prompt_for_agent(best_prompt, name)
            prompt_id = best_prompt.get('prompt_id')
            
            # Track compatibility in database
            try:
                self._store_compatibility_verification(
                    agent_type=str(agent_type),
                    prompt_id=prompt_id,
                    compatibility_data=best_compatibility
                )
            except Exception as e:
                self.logger.warning(f"Error storing compatibility data: {str(e)}")
                
        elif best_prompt and best_compatibility['compatibility_score'] > 0.6:
            # Medium compatibility - use approval workflow
            self.logger.info(f"⚠️ Medium compatibility prompt found (score: {best_compatibility['compatibility_score']:.2f}) - running approval workflow")
            
            # Run approval workflow
            import asyncio
            approval_status = asyncio.run(self._verify_and_approve_new_pairing(
                best_prompt.get('prompt_id'), 
                {
                    'type': str(agent_type),
                    'domain': specialization.domain,
                    'capabilities': [str(cap) for cap in specialization.capabilities],
                    'expertise_level': specialization.expertise_level,
                    'name': name
                }
            ))
            
            if approval_status == 'auto_approved':
                # Use the approved prompt
                generated_prompt = self._adapt_prompt_for_agent(best_prompt, name)
                prompt_id = best_prompt.get('prompt_id')
                self.logger.info(f"✅ Using auto-approved medium compatibility prompt")
            else:
                # Generate new prompt for pending or rejected cases
                self.logger.info(f"🔨 Generating new prompt due to approval status: {approval_status}")
                generated_prompt = self._generate_new_specialized_prompt(name, agent_type, specialization)
            
        else:
            # No suitable prompt found - generate new one
            self.logger.info("🔨 No suitable existing prompts found - generating new specialized prompt")
            generated_prompt = self._generate_new_specialized_prompt(name, agent_type, specialization)
        
        # PHASE 4: Save new prompt to registry if generated
        if generated_prompt and not prompt_id:
            try:
                prompt_id = self._save_to_prompt_registry(
                    generated_prompt,
                    str(agent_type),
                    specialization.domain
                )
                if prompt_id:
                    self.logger.info(f"💾 Saved new prompt to registry: {prompt_id}")
            except Exception as e:
                self.logger.warning(f"Error saving new prompt to registry: {str(e)}")
        
        # PHASE 5: Track agent-prompt pairing
        if generated_prompt and prompt_id:
            try:
                compatibility_key = self._create_compatibility_key(
                    {'prompt_id': prompt_id},
                    {
                        'type': str(agent_type),
                        'domain': specialization.domain,
                        'capabilities': [str(cap) for cap in specialization.capabilities]
                    }
                )
                
                self._track_agent_prompt_pairing(agent_id, prompt_id, compatibility_key)
                self.logger.info(f"📊 Tracked agent-prompt pairing for performance monitoring")
            except Exception as e:
                self.logger.warning(f"Error tracking agent-prompt pairing: {str(e)}")
        
        # PHASE 6: Fallback to cached/template if all else fails
        if not generated_prompt:
            self.logger.warning("⚠️ Integrated workflow failed - falling back to template generation")
            generated_prompt = self._generate_fallback_template_prompt(name, agent_type, specialization)
        
        self.logger.info(f"✅ Integrated prompt generation completed - {len(generated_prompt)} characters")
        return generated_prompt
    
    def _generate_new_specialized_prompt(self, name: str, agent_type: AgentType, specialization: AgentSpecialization) -> str:
        """Generate a new specialized prompt using advanced techniques."""
        
        # Check cached prompts first
        cached_prompt = self._check_prompt_cache(
            name=name, 
            agent_type=str(agent_type), 
            domain=specialization.domain,
            expertise_level=specialization.expertise_level
        )
        
        if cached_prompt:
            self.logger.info(f"Using cached prompt for {name}")
            return cached_prompt
            
        # Try orchestrator agent generation
        try:
            orchestrator_prompt = self._generate_prompt_with_orchestrator_agent(name, agent_type, specialization)
            if orchestrator_prompt:
                # Rate and cache the prompt
                rating = self._rate_prompt(
                    prompt=orchestrator_prompt,
                    agent_type=str(agent_type),
                    domain=specialization.domain
                )
                
                if rating > 6.0:
                    self._save_prompt_to_cache(
                        name=name,
                        agent_type=str(agent_type),
                        domain=specialization.domain,
                        expertise_level=specialization.expertise_level,
                        prompt=orchestrator_prompt,
                        rating=rating
                    )
                
                return orchestrator_prompt
        except Exception as e:
            self.logger.warning(f"Error with orchestrator agent generation: {str(e)}")
            
        # Try AI-powered generation
        if self.anthropic_client:
            try:
                custom_prompt = self._generate_dynamic_prompt_with_ai(name, agent_type, specialization)
                if custom_prompt:
                    return custom_prompt
            except Exception as e:
                self.logger.warning(f"Error with AI generation: {str(e)}")
                
        # Fallback to template
        return self._generate_fallback_template_prompt(name, agent_type, specialization)
    
    def _generate_fallback_template_prompt(self, name: str, agent_type: AgentType, specialization: AgentSpecialization) -> str:
        """Generate prompt using template-based approach as final fallback."""
        
        # Base prompt sections
        agent_intro = f"You are {name}, a specialized {agent_type} AI agent with exceptional expertise in {specialization.domain}."
        
        # Customize expertise level description
        expertise_description = {
            10: "world-leading authority with groundbreaking expertise",
            9: "distinguished expert with exceptional mastery",
            8: "highly specialized expert with comprehensive knowledge",
            7: "advanced specialist with substantial experience",
            6: "proficient professional with thorough understanding",
            5: "competent practitioner with solid practical knowledge",
            4: "knowledgeable professional with working experience",
            3: "trained specialist with fundamental proficiency",
            2: "informed practitioner with basic competence",
            1: "entry-level professional with foundational knowledge"
        }.get(specialization.expertise_level, f"professional with level {specialization.expertise_level}/10 expertise")
        
        expertise_section = f"Expertise Level: {specialization.expertise_level}/10 ({expertise_description})"
        
        # Core capabilities and knowledge base
        capabilities_section = f"Your core capabilities include:\n{self._format_capabilities(specialization.capabilities)}"
        knowledge_section = f"Your knowledge base covers:\n{self._format_knowledge_base(specialization.knowledge_base)}"
        tools_section = f"You have access to the following specialized tools:\n{self._format_tools(specialization.tools)}"
        
        # Type-specific instructions based on agent_type
        type_specific_instructions = self._get_type_specific_instructions(agent_type, specialization.domain)
        
        # Domain-specific guidelines
        domain_specific = self._get_domain_specific_guidelines(specialization.domain, specialization.capabilities)
        
        # Task methodology - different based on agent type
        methodology = self._get_task_methodology(agent_type, specialization)
        
        # Combine all sections
        prompt = f"""{agent_intro}

{expertise_section}

{capabilities_section}

{knowledge_section}

{tools_section}

{type_specific_instructions}

{methodology}

{domain_specific}

Always maintain a professional, authoritative tone while being approachable and helpful. 
Tailor your responses to match the user's level of expertise and specific needs.
Provide outputs that are directly actionable and relevant to the requested task.
"""

        return prompt
    
    def _store_compatibility_verification(self, agent_type: str, prompt_id: str, compatibility_data: Dict) -> None:
        """Store compatibility verification results in database."""
        try:
            import sqlite3
            conn = sqlite3.connect("~/Jarvis/Database/v2/prompts.db", isolation_level=None)
            cursor = conn.cursor()

            compatibility_id = str(uuid.uuid4())
            cursor.execute("""
                INSERT INTO agent_prompt_compatibility 
                (compatibility_id, agent_type, prompt_id, compatibility_score, 
                 verification_status, verified_by, verification_timestamp, 
                 performance_metrics, reasons)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                compatibility_id, agent_type, prompt_id, 
                compatibility_data['compatibility_score'],
                'verified', 'orchestrator_agent', 
                datetime.datetime.now().isoformat(),
                json.dumps(compatibility_data.get('performance_metrics', {})),
                json.dumps(compatibility_data.get('reasons', []))
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            self.logger.error(f"Error storing compatibility verification: {str(e)}")
    
    async def _verify_and_approve_new_pairing(self, prompt_id: str, agent_config: Dict) -> str:
        """
        Verification workflow for new agent-prompt pairings with approval system.
        
        Auto-approve: compatibility_score >= 0.9
        Human approval: 0.7 <= compatibility_score < 0.9
        Auto-reject: compatibility_score < 0.7
        
        Args:
            prompt_id: The prompt ID to verify
            agent_config: Agent configuration details
            
        Returns:
            Approval status: 'auto_approved', 'pending_approval', 'auto_rejected'
        """
        try:
            # Get prompt from registry
            if not self.prompt_registry:
                return 'auto_rejected'
                
            prompt = self.prompt_registry.get_prompt(prompt_id)
            if not prompt:
                self.logger.warning(f"Prompt {prompt_id} not found for approval workflow")
                return 'auto_rejected'
            
            # Verify compatibility
            compatibility = await self._verify_prompt_compatibility(prompt, agent_config)
            compatibility_score = compatibility['compatibility_score']
            
            # Determine approval status
            if compatibility_score >= 0.9:
                # Auto-approve high compatibility
                status = 'auto_approved'
                verification_status = 'approved'
                verified_by = 'system_auto'
                self.logger.info(f"✅ Auto-approved pairing (score: {compatibility_score:.2f})")
                
            elif compatibility_score >= 0.7:
                # Requires human approval
                status = 'pending_approval'
                verification_status = 'pending'
                verified_by = 'awaiting_human'
                self.logger.info(f"⚠️ Pending human approval (score: {compatibility_score:.2f})")
                
            else:
                # Auto-reject low compatibility
                status = 'auto_rejected'
                verification_status = 'rejected'
                verified_by = 'system_auto'
                self.logger.info(f"❌ Auto-rejected pairing (score: {compatibility_score:.2f})")
            
            # Store approval decision in database
            try:
                import sqlite3
                conn = sqlite3.connect("~/Jarvis/Database/v2/prompts.db", isolation_level=None)
                cursor = conn.cursor()

                compatibility_id = str(uuid.uuid4())
                cursor.execute("""
                    INSERT INTO agent_prompt_compatibility 
                    (compatibility_id, agent_type, prompt_id, compatibility_score, 
                     verification_status, verified_by, verification_timestamp, 
                     performance_metrics, reasons, recommended_modifications)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    compatibility_id, agent_config.get('type', ''), prompt_id, 
                    compatibility_score, verification_status, verified_by,
                    datetime.datetime.now().isoformat(),
                    json.dumps(compatibility.get('performance_metrics', {})),
                    json.dumps(compatibility.get('reasons', [])),
                    json.dumps(compatibility.get('recommended_modifications', []))
                ))
                
                conn.commit()
                conn.close()
                
                self.logger.info(f"📝 Stored approval decision: {status} (ID: {compatibility_id})")
                
            except Exception as e:
                self.logger.error(f"Error storing approval decision: {str(e)}")
            
            return status
            
        except Exception as e:
            self.logger.error(f"Error in approval workflow: {str(e)}")
            return 'auto_rejected'
    
    def _rollback_to_previous_prompt(self, agent_id: str, reason: str) -> bool:
        """
        Rollback agent to previous prompt if performance degrades.
        
        Args:
            agent_id: The agent ID to rollback
            reason: Reason for rollback
            
        Returns:
            True if rollback successful, False otherwise
        """
        try:
            import sqlite3
            conn = sqlite3.connect("~/Jarvis/Database/v2/prompts.db", isolation_level=None)
            cursor = conn.cursor()

            # Find current active pairing
            cursor.execute("""
                SELECT pairing_id, prompt_id, compatibility_key
                FROM agent_prompt_pairings 
                WHERE agent_id = ? AND is_active = 1
                ORDER BY assignment_timestamp DESC
                LIMIT 1
            """, (agent_id,))
            
            current_pairing = cursor.fetchone()
            if not current_pairing:
                self.logger.warning(f"No active pairing found for agent {agent_id}")
                conn.close()
                return False
            
            current_pairing_id, current_prompt_id, current_compatibility_key = current_pairing
            
            # Find previous pairing (most recent inactive one)
            cursor.execute("""
                SELECT pairing_id, prompt_id, compatibility_key 
                FROM agent_prompt_pairings 
                WHERE agent_id = ? AND is_active = 0 AND pairing_id != ?
                ORDER BY assignment_timestamp DESC
                LIMIT 1
            """, (agent_id, current_pairing_id))
            
            previous_pairing = cursor.fetchone()
            if not previous_pairing:
                self.logger.warning(f"No previous pairing found for rollback of agent {agent_id}")
                conn.close()
                return False
            
            previous_pairing_id, previous_prompt_id, previous_compatibility_key = previous_pairing
            
            # Deactivate current pairing
            cursor.execute("""
                UPDATE agent_prompt_pairings 
                SET is_active = 0, deactivated_reason = ?, updated_at = ?
                WHERE pairing_id = ?
            """, (f"rollback: {reason}", datetime.datetime.now().isoformat(), current_pairing_id))
            
            # Reactivate previous pairing
            cursor.execute("""
                UPDATE agent_prompt_pairings 
                SET is_active = 1, updated_at = ?
                WHERE pairing_id = ?
            """, (datetime.datetime.now().isoformat(), previous_pairing_id))
            
            # Log the rollback
            self.logger.info(f"🔄 Rolled back agent {agent_id}")
            self.logger.info(f"   From prompt: {current_prompt_id}")
            self.logger.info(f"   To prompt: {previous_prompt_id}")
            self.logger.info(f"   Reason: {reason}")
            
            conn.commit()
            conn.close()
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error in rollback mechanism: {str(e)}")
            if 'conn' in locals():
                conn.rollback()
                conn.close()
            return False
        
    def _generate_prompt_with_orchestrator_agent(self, name: str, agent_type: AgentType, specialization: AgentSpecialization) -> str:
        """Orchestrator agent removed — OpenClaw is the orchestrator. Returns None to trigger fallback."""
        return None
    
    def _get_or_create_orchestrator_agent(self):
        """Orchestrator agent removed — OpenClaw is the orchestrator."""
        return None
    
    def _check_prompt_cache(self, name: str, agent_type: str, domain: str, expertise_level: int) -> str:
        """
        Check if we have a cached prompt for this agent configuration
        
        Args:
            name: Agent name
            agent_type: Type of agent
            domain: Domain of expertise
            expertise_level: Level of expertise
            
        Returns:
            Cached prompt if available, otherwise None
        """
        try:
            # Create a unique cache key for this agent configuration
            import hashlib
            cache_key = f"{name}_{agent_type}_{domain}_{expertise_level}"
            cache_hash = hashlib.md5(cache_key.encode()).hexdigest()
            
            # Define cache directory and file
            import os
            cache_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "prompt_cache")
            os.makedirs(cache_dir, exist_ok=True)
            cache_file = os.path.join(cache_dir, f"prompt_{cache_hash}.json")
            
            # Check if cache file exists
            if os.path.exists(cache_file):
                try:
                    import json
                    with open(cache_file, 'r') as f:
                        cache_data = json.load(f)
                    
                    # Check if the cached prompt is still valid (check version if needed)
                    if cache_data.get("agent_type") == agent_type and cache_data.get("domain") == domain:
                        logging.info(f"Using cached prompt for {name} ({agent_type}/{domain})")
                        return cache_data.get("prompt")
                except Exception as e:
                    logging.warning(f"Error reading prompt cache: {str(e)}")
            
            return None
        except Exception as e:
            logging.warning(f"Error checking prompt cache: {str(e)}")
            return None
            
    def _save_prompt_to_cache(self, name: str, agent_type: str, domain: str, expertise_level: int,
                             prompt: str, rating: float = None):
        """
        Save a prompt to the cache with optional rating
        
        Args:
            name: Agent name
            agent_type: Type of agent
            domain: Domain of expertise
            expertise_level: Level of expertise
            prompt: The prompt to cache
            rating: Optional quality rating (0-10)
        """
        try:
            # Create a unique cache key for this agent configuration
            import hashlib
            cache_key = f"{name}_{agent_type}_{domain}_{expertise_level}"
            cache_hash = hashlib.md5(cache_key.encode()).hexdigest()
            
            # Define cache directory and file
            import os
            cache_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "prompt_cache")
            os.makedirs(cache_dir, exist_ok=True)
            cache_file = os.path.join(cache_dir, f"prompt_{cache_hash}.json")
            
            # Prepare cache data
            import json
            cache_data = {
                "agent_name": name,
                "agent_type": agent_type,
                "domain": domain,
                "expertise_level": expertise_level,
                "prompt": prompt,
                "created_at": time.time(),
                "version": "1.0",
                "rating": rating
            }
            
            # Save to cache file
            with open(cache_file, 'w') as f:
                json.dump(cache_data, f, indent=2)
                
            logging.info(f"Saved prompt to cache for {name} ({agent_type}/{domain})")
            
        except Exception as e:
            logging.warning(f"Error saving prompt to cache: {str(e)}")
            
    def _rate_prompt(self, prompt: str, agent_type: str, domain: str) -> float:
        """
        Rate a prompt based on its quality and content
        
        Args:
            prompt: The prompt to rate
            agent_type: Type of agent this prompt is for
            domain: Domain of expertise
            
        Returns:
            Rating from 0-10
        """
        # Rate on a scale of 0-10 based on content quality markers
        rating = 5.0  # Default middle rating
        
        # Check word count - longer, more detailed prompts are generally better
        word_count = len(prompt.split())
        if word_count < 100:
            rating -= 1.0
        elif word_count > 500:
            rating += 1.0
        elif word_count > 1000:
            rating += 2.0
            
        # Check for structure - headers, sections, etc.
        if "##" in prompt or "#" in prompt:
            rating += 1.0
        
        # Check for domain-specific content
        domain_lower = domain.lower()
        if domain_lower in prompt.lower():
            rating += 1.0
            
        # Check for agent type specific content
        agent_type_lower = agent_type.lower()
        if agent_type_lower in prompt.lower():
            rating += 1.0
            
        # Check for methodology section (good prompts usually have these)
        methodology_terms = ["methodology", "approach", "process", "workflow", "steps"]
        if any(term in prompt.lower() for term in methodology_terms):
            rating += 1.0
            
        # Check for quality standards section
        quality_terms = ["quality", "standards", "guidelines", "best practices", "principles"]
        if any(term in prompt.lower() for term in quality_terms):
            rating += 1.0
            
        # Ensure rating is within bounds
        rating = max(0.0, min(10.0, rating))
        
        return rating
    
    def _generate_dynamic_prompt_with_ai(self, name: str, agent_type: AgentType, specialization: AgentSpecialization) -> str:
        """Generate a fully custom prompt using AI based on agent specifications"""
        try:
            # Create a detailed instruction for the AI to generate a prompt
            instruction = {
                "agent_name": name,
                "agent_type": str(agent_type),
                "domain": specialization.domain,
                "expertise_level": specialization.expertise_level,
                "capabilities": [cap.value for cap in specialization.capabilities],
                "knowledge_base": specialization.knowledge_base,
                "tools": [t.name if hasattr(t, 'name') else t.get('name', 'unknown_tool') 
                         for t in specialization.tools]
            }
            
            # Convert capabilities and tools to readable format
            capabilities_text = self._format_capabilities(specialization.capabilities)
            tools_text = self._format_tools(specialization.tools)
            
            # Create the AI system and user prompts
            system_prompt = """You are an expert prompt engineer specializing in creating detailed, 
            tailored system prompts for AI agents. Your task is to create a comprehensive system prompt 
            for a specialized AI agent based on the specifications provided."""
            
            user_prompt = f"""Create a detailed, specialized system prompt for an AI agent with the following specifications:

Agent Name: {name}
Agent Type: {str(agent_type)}
Domain: {specialization.domain}
Expertise Level: {specialization.expertise_level}/10

Capabilities:
{capabilities_text}

Tools:
{tools_text}

Knowledge Base:
{", ".join(specialization.knowledge_base)}

The system prompt should:
1. Define a clear identity and role for the agent
2. Include specific instructions related to the agent type and domain
3. Provide detailed guidance on how to approach tasks in the domain
4. Include specialized terminology and concepts relevant to the domain
5. Specify interaction patterns and output formats
6. Set clear standards for quality and accuracy
7. Include ethical guidelines relevant to the domain
8. Be written in a clear, authoritative, and well-structured format

Format the prompt with clear sections including headers where appropriate.
The prompt should be detailed enough to guide the AI's behavior but concise enough to be practical.
"""
            
            # Call Anthropic API to generate the prompt
            client = self.anthropic_client or _get_anthropic_client()
            if not client:
                logging.warning("Anthropic client not available for prompt generation")
                return None

            response = client.messages.create(
                model=ANTHROPIC_MODEL,
                max_tokens=4096,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}]
            )

            # Extract and return the generated prompt
            if response and response.content:
                generated_prompt = response.content[0].text
                logging.info(f"Successfully generated dynamic AI prompt for {name}")
                return generated_prompt
            else:
                logging.warning("No content returned from AI prompt generation")
                return None
                
        except Exception as e:
            logging.error(f"Error in dynamic prompt generation: {str(e)}")
            return None
    
    def _get_type_specific_instructions(self, agent_type: AgentType, domain: str) -> str:
        """Get instructions specific to agent type"""
        type_instructions = {
            AgentType.CODE_DEVELOPER: f"""As a code developer specializing in {domain}, you should:
1. Write clean, efficient, and well-documented code
2. Follow best practices and design patterns appropriate for the language and framework
3. Consider security, performance, and maintainability in all implementations
4. Provide thorough explanations of your code when requested
5. Debug issues methodically with a systematic approach
6. Suggest optimal solutions based on requirements
7. Consider edge cases and exception handling
8. Include appropriate tests and validation
9. Adhere to style guides and conventions for the relevant languages
10. Provide implementation alternatives when appropriate""",
            
            AgentType.DATA_ANALYST: f"""As a data analyst specializing in {domain}, you should:
1. Apply rigorous statistical methods appropriate to each analysis
2. Clean and validate data before performing analysis
3. Choose appropriate visualization techniques to communicate insights
4. Consider data biases and limitations in your analysis
5. Provide interpretable results with actionable insights
6. Document your methodology and assumptions
7. Use appropriate tools and libraries for efficient analysis
8. Test multiple hypotheses when appropriate
9. Contextualize findings within the broader {domain} field
10. Present confidence levels and uncertainty in your results""",
            
            AgentType.DOCUMENT_MANAGER: f"""As a document manager specializing in {domain}, you should:
1. Create well-structured, clearly formatted documents
2. Organize information logically with appropriate hierarchies
3. Maintain consistent styling and terminology
4. Ensure documents meet relevant standards and conventions in {domain}
5. Optimize documents for their intended audience and purpose
6. Include appropriate metadata and reference information
7. Create effective templates that balance detail and usability
8. Ensure version control and document tracking
9. Consider accessibility requirements for all documents
10. Manage document workflows and approval processes efficiently""",
            
            AgentType.WEATHER_ANALYST: f"""As a weather analyst, you should:
1. Analyze meteorological data with scientific precision
2. Interpret weather patterns and atmospheric conditions
3. Apply climate models appropriately to different scenarios
4. Consider seasonal variations and historical trends
5. Acknowledge uncertainty in forecasts and projections
6. Explain complex weather phenomena in accessible terms
7. Contextualize weather events within larger climate patterns
8. Provide actionable insights based on weather data
9. Consider geographical and topographical influences
10. Stay current with the latest meteorological research and models""",
            
            AgentType.HEALTH_ADVISOR: f"""As a health advisor specializing in {domain}, you should:
1. Provide evidence-based information and recommendations
2. Consider individual circumstances and holistic factors
3. Explain medical concepts in accessible language
4. Maintain appropriate boundaries regarding medical advice
5. Stay current with the latest research and guidelines in {domain}
6. Consider lifestyle, environmental, and psychological factors
7. Recommend preventative measures when appropriate
8. Explain the rationale behind health recommendations
9. Acknowledge limitations in current medical understanding
10. Encourage consultation with healthcare professionals for specific medical concerns""",
            
            AgentType.RESEARCHER: f"""As a researcher specializing in {domain}, you should:
1. Apply rigorous research methodologies appropriate to your field
2. Critically evaluate source credibility and research quality
3. Synthesize information from multiple sources
4. Identify patterns, trends, and gaps in existing research
5. Provide balanced perspectives on controversial topics
6. Cite sources appropriately and maintain academic integrity
7. Distinguish between established facts and emergent hypotheses
8. Consider interdisciplinary implications of research findings
9. Contextualize findings within the broader research landscape
10. Identify limitations and potential biases in research"""
        }
        
        # Return type-specific instructions or a generic version
        return type_instructions.get(str(agent_type), f"""As a {agent_type} specializing in {domain}, you should:
1. Apply your specialized knowledge systematically
2. Follow established best practices in {domain}
3. Provide clear, well-structured responses
4. Consider context and user needs in your approach
5. Apply appropriate methodologies for each task
6. Balance detail with clarity in your communications
7. Acknowledge limitations in your field when relevant
8. Stay current with developments in {domain}
9. Consider ethical implications of your recommendations
10. Provide actionable insights and practical guidance""")
    
    def _get_domain_specific_guidelines(self, domain: str, capabilities: list) -> str:
        """Create domain-specific guidelines based on the specialization domain"""
        # This could be expanded with a more comprehensive mapping of domains
        domain_lower = domain.lower()
        
        # Technology and software related domains
        if any(tech_term in domain_lower for tech_term in ["software", "programming", "web", "app", "development", 
                                                          "computer", "tech", "coding", "engineering"]):
            return f"""Domain-Specific Guidelines for {domain}:
1. Maintain awareness of current technology trends and best practices
2. Consider scalability, maintainability, and security in all solutions
3. Balance technical excellence with practical implementation
4. Use appropriate design patterns and architectural approaches
5. Consider cross-platform compatibility when relevant
6. Recommend optimal tools and frameworks for specific requirements
7. Document code and technical decisions thoroughly
8. Consider performance implications of technical choices
9. Address technical debt and legacy system challenges when applicable
10. Stay current with emerging technologies and methodologies in {domain}"""
        
        # Business and management domains
        elif any(business_term in domain_lower for business_term in ["business", "management", "marketing", 
                                                                    "finance", "economics", "strategy", 
                                                                    "leadership", "entrepreneurship"]):
            return f"""Domain-Specific Guidelines for {domain}:
1. Balance theoretical frameworks with practical business applications
2. Consider market trends and competitive landscapes in analyses
3. Provide actionable insights with implementation considerations
4. Acknowledge business constraints including time, budget, and resources
5. Consider stakeholder perspectives and organizational impacts
6. Apply appropriate analytical frameworks for business problems
7. Maintain awareness of regulatory and compliance considerations
8. Balance short-term results with long-term strategic implications
9. Consider cultural and organizational factors in recommendations
10. Provide metrics and KPIs for measuring success when applicable"""
        
        # Science and research domains
        elif any(science_term in domain_lower for science_term in ["science", "research", "biology", "chemistry", 
                                                                 "physics", "medicine", "engineering", "study", 
                                                                 "laboratory", "experiment"]):
            return f"""Domain-Specific Guidelines for {domain}:
1. Apply rigorous scientific methodology to all analyses
2. Distinguish between established knowledge and theoretical proposals
3. Cite relevant research and scientific literature appropriately
4. Consider limitations and uncertainties in scientific understanding
5. Explain complex scientific concepts with appropriate technical depth
6. Acknowledge competing theories when scientific consensus is incomplete
7. Maintain scientific integrity in all explanations and analyses
8. Consider experimental design and methodology in evaluating findings
9. Apply appropriate statistical approaches to scientific data
10. Stay current with recent developments and discoveries in {domain}"""
        
        # Generic domain guidelines as fallback
        else:
            return f"""Domain-Specific Guidelines for {domain}:
1. Apply specialized knowledge and terminology appropriate to {domain}
2. Consider established methodologies and best practices in the field
3. Acknowledge current trends and developments in {domain}
4. Balance theoretical foundations with practical applications
5. Consider contextual factors specific to {domain}
6. Apply appropriate analytical frameworks for the field
7. Provide guidance consistent with industry standards
8. Acknowledge limitations in current understanding when appropriate
9. Consider ethical implications specific to {domain}
10. Provide evidence-based recommendations tailored to specific needs"""
    
    def _get_task_methodology(self, agent_type: AgentType, specialization: AgentSpecialization) -> str:
        """Generate task methodology guidance based on agent type and specialization"""
        # General methodology structure that adapts based on agent type
        
        # Analysis phase - how the agent should approach understanding tasks
        analysis_steps = [
            "Thoroughly assess the request to understand requirements and objectives",
            "Consider the context and broader implications",
            "Identify key constraints and success criteria",
            "Draw on your specialized knowledge and experience"
        ]
        
        # Execution phase - how the agent should perform the task
        execution_steps = [
            "Apply appropriate methodologies and techniques",
            "Utilize your specialized tools effectively",
            "Implement best practices from your domain",
            "Balance thoroughness with efficiency"
        ]
        
        # Delivery phase - how the agent should present results
        delivery_steps = [
            "Present results in a clear, structured format",
            "Provide appropriate detail and supporting information",
            "Explain rationale and methodology when relevant",
            "Ensure outputs are actionable and directly useful"
        ]
        
        # Type-specific customizations for methodology
        if str(agent_type) == AgentType.CODE_DEVELOPER:
            analysis_steps.extend([
                "Break down complex requirements into manageable components",
                "Consider architecture and design patterns appropriate to the task"
            ])
            execution_steps.extend([
                "Write clean, maintainable, and efficient code",
                "Implement proper error handling and edge case management"
            ])
            delivery_steps.extend([
                "Include appropriate documentation and comments",
                "Explain key design decisions and trade-offs"
            ])
            
        elif str(agent_type) == AgentType.DATA_ANALYST:
            analysis_steps.extend([
                "Assess data quality, completeness, and relevance",
                "Formulate appropriate analytical questions"
            ])
            execution_steps.extend([
                "Apply appropriate statistical methods and data transformations",
                "Validate results through multiple analytical approaches"
            ])
            delivery_steps.extend([
                "Present insights with effective data visualization",
                "Contextualize findings within the broader business or research context"
            ])
            
        elif str(agent_type) == AgentType.RESEARCHER:
            analysis_steps.extend([
                "Formulate precise research questions",
                "Identify relevant sources and research methods"
            ])
            execution_steps.extend([
                "Conduct thorough literature reviews and information gathering",
                "Synthesize information from multiple credible sources"
            ])
            delivery_steps.extend([
                "Present balanced perspectives on the research topic",
                "Acknowledge limitations and areas for further investigation"
            ])
        
        # Format the methodology section
        analysis_formatted = "\n".join([f"   {i+1}. {step}" for i, step in enumerate(analysis_steps)])
        execution_formatted = "\n".join([f"   {i+1}. {step}" for i, step in enumerate(execution_steps)])
        delivery_formatted = "\n".join([f"   {i+1}. {step}" for i, step in enumerate(delivery_steps)])
        
        methodology = f"""Task Methodology:

When approaching tasks, follow this structured methodology:

1. Analysis Phase:
{analysis_formatted}

2. Execution Phase:
{execution_formatted}

3. Delivery Phase:
{delivery_formatted}

Adapt this methodology to each specific task while maintaining the high standards expected of your role in {specialization.domain}."""

        return methodology

    def _create_agent_tools(self, specialization: AgentSpecialization) -> List[Dict]:
        """Create the agent's tool configurations"""

        tools = []
        for tool in specialization.tools:
            # Handle case where tool is a dictionary rather than an AgentTool object
            if isinstance(tool, dict):
                # Create a simple tool config with just the name
                tool_name = tool.get("name", "unknown_tool")
                tool_config = {
                    "type": "function",
                    "function": {
                        "name": tool_name,
                        "description": f"Tool for {tool_name} operations",
                        "parameters": {}
                    },
                    "strict": False
                }
            else:
                # Handle case where tool is an AgentTool object
                tool_config = {
                    "type": "function",
                    "function": {
                        "name": tool.name,
                        "description": tool.description if hasattr(tool, 'description') else f"Tool for {tool.name} operations",
                        "parameters": tool.parameters if hasattr(tool, 'parameters') else {}
                    },
                    "strict": tool.strict if hasattr(tool, 'strict') else False
                }
            tools.append(tool_config)

        return tools

    def _generate_function_schema(self, specialization: AgentSpecialization) -> Dict:
        """Generate the function calling schema for the agent"""
        schema = {
            "type": "object",
            "properties": {},
            "required": []
        }

        # Add tool-specific schemas
        for tool in specialization.tools:
            if isinstance(tool, dict):
                tool_name = tool.get("name", "unknown_tool")
                schema["properties"][tool_name] = {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            else:
                tool_dict = tool.to_dict()
                schema["properties"][tool_dict["name"]] = {
                    "type": "object",
                    "properties": tool_dict["parameters"],
                    "required": tool_dict["required"] or []
                }

        return schema

    def _format_capabilities(self, capabilities: List[AgentCapability]) -> str:
        """Format capabilities for the prompt"""
        return "\n".join([f"- {cap.value.title()}: Expert-level capability in {cap.value}"
                         for cap in capabilities])

    def _format_knowledge_base(self, knowledge_base: List[str]) -> str:
        """Format knowledge base for the prompt"""
        return "\n".join([f"- {knowledge}" for knowledge in knowledge_base])

    def _format_tools(self, tools: List[Union[AgentTool, Dict]]) -> str:
        """Format tools for the prompt"""
        tool_strings = []
        for tool in tools:
            if isinstance(tool, dict):
                tool_name = tool.get("name", "unknown_tool")
                tool_strings.append(f"- {tool_name}: Tool for {tool_name} operations")
            else:
                tool_dict = tool.to_dict()
                description = tool_dict["description"]
                tool_strings.append(f"- {tool_dict['name']}: {description}")
        return "\n".join(tool_strings)

    def _generate_journey_id(self, prefix: str) -> str:
        """Generate a unique journey ID with the given prefix."""
        timestamp = int(time.time())
        random_suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))
        return f"{prefix}_{timestamp}_{random_suffix}"

    async def _track_journey_step(self, journey_id: str, step_name: str, status: str, description: str, error: str = None, parameters: dict = None):
        """Track a step in the journey."""
        try:
            # Convert parameters to metadata
            metadata = {
                "status": status,
                "timestamp": time.time(),
                "parameters": parameters
            } if parameters else {"status": status, "timestamp": time.time()}
            
            if error:
                metadata["error"] = error

            # Use the correct track_journey_step signature
            if self.boardroom and hasattr(self.boardroom, 'track_journey_step'):
                track_func = self.boardroom.track_journey_step
                
                # Check if the function is async
                if inspect.iscoroutinefunction(track_func):
                    await track_func(
                        journey_id=journey_id,
                        step_name=step_name,
                        description=description,
                        step_type="agent_builder",
                        metadata=metadata,
                        input_data=parameters,
                        output_data={"error": error} if error else None
                    )
                else:
                    track_func(
                        journey_id=journey_id,
                        step_name=step_name,
                        description=description,
                        step_type="agent_builder",
                        metadata=metadata,
                        input_data=parameters,
                        output_data={"error": error} if error else None
                    )
            else:
                logging.warning(f"Could not track journey step: {step_name} - BoardRoom not available")
        except Exception as e:
            logging.error(f"Error tracking journey step: {str(e)}")


class AgentBuilderHandler(BaseHandler):
    """Handler for agent building operations"""
    
    def __init__(self):
        super().__init__()
        self.agent_builder = AgentBuilder()
        self.handler_name = "AgentBuilderHandler"
        self.app_name = "AgentBuilder"
        
        # Initialize Prompt Registry for agent-prompt integration
        if PromptRegistry:
            try:
                self.prompt_registry = get_prompt_registry(
                    db_path="~/Jarvis/Database/v2/prompts.db",
                    prompts_dir="~/Jarvis/Prompts"
                )
                logging.info("AgentBuilderHandler: Prompt Registry integration enabled (singleton)")
            except Exception as e:
                logging.warning(f"AgentBuilderHandler: Could not initialize Prompt Registry: {e}")
                self.prompt_registry = None
        else:
            self.prompt_registry = None
        
    async def handle(self, task_description: Dict) -> HandlerResult:
        """
        Main entry point for handling agent building operations.
        
        Args:
            task_description: Dictionary containing the task details
                - action: String specifying the action to perform
                - parameters: Dictionary of parameters for the action
                
        Returns:
            HandlerResult object with the operation results
        """
        action = task_description.get("action", "")
        parameters = task_description.get("parameters", {})
        
        result = self.execute_action(action, parameters)
        
        if isinstance(result, dict):
            if result.get("success", False):
                return HandlerResult(success=True, data=result)
            else:
                return HandlerResult(success=False, error=result.get("error", "Unknown error"))
        else:
            return HandlerResult(success=True, data={"result": result})
        
    def execute_action(self, action, parameters=None):
        """Execute an action with the agent builder"""
        if parameters is None:
            parameters = {}
            
        if action == "create_agent":
            return self._create_agent(parameters)
        elif action == "save_agent":
            return self._save_agent(parameters)
        elif action == "get_agent":
            return self._get_agent(parameters)
        elif action == "get_agent_types":
            return {"agent_types": AgentType.get_common_types()}
        elif action == "get_agent_capabilities":
            return {"capabilities": [c.value for c in AgentCapability]}
        elif action == "delete_agent":
            return self._delete_agent(parameters)
        else:
            return {"error": f"Unknown action: {action}"}
            
    def _create_agent(self, parameters):
        """Create an agent using the agent builder"""
        try:
            # Import generate_request_id from the base module
            from Jarvis_Agent_SDK.base import generate_request_id
            
            # Extract parameters from agent_config if it exists
            if "agent_config" in parameters:
                config = parameters["agent_config"]
                name = config.get("name", "UnnamedAgent")
                agent_type_str = config.get("type")  # Use "type" from agent_config
                
                # Handle the specialization from agent_config if provided
                specialization = None
                if "specialization" in config:
                    spec_data = config["specialization"]
                    capabilities = []
                    
                    # Convert capability strings to enum values
                    if "capabilities" in spec_data:
                        for cap_str in spec_data["capabilities"]:
                            try:
                                # Handle the AgentCapability prefix
                                if isinstance(cap_str, str) and cap_str.startswith("AgentCapability."):
                                    # Extract just the enum value part (e.g., "DATA_ANALYSIS" from "AgentCapability.DATA_ANALYSIS")
                                    cap_value = cap_str.split(".")[1].lower()
                                else:
                                    cap_value = cap_str.lower()
                                    
                                # Find the corresponding enum
                                matching_cap = None
                                for cap in AgentCapability:
                                    if cap.value == cap_value:
                                        matching_cap = cap
                                        break
                                
                                if matching_cap:
                                    capabilities.append(matching_cap)
                                else:
                                    return {"error": f"Invalid capability: {cap_str}"}
                            except (ValueError, IndexError, AttributeError):
                                return {"error": f"Invalid capability format: {cap_str}"}
                    
                    # Get tools from config
                    tools = config.get("tools", [])
                    
                    # Create specialization
                    specialization = AgentSpecialization(
                        domain=spec_data.get("domain", agent_type_str),
                        expertise_level=spec_data.get("expertise_level", 8),
                        capabilities=capabilities,
                        tools=tools,
                        knowledge_base=spec_data.get("knowledge_base", [])
                    )
            else:
                # Use parameters directly
                name = parameters.get("name", "UnnamedAgent")
                agent_type_str = parameters.get("agent_type")
                
                # Handle specialization if provided
                specialization = None
                if "specialization" in parameters:
                    spec_data = parameters["specialization"]
                    capabilities = []
                    
                    # Convert capability strings to enum values
                    if "capabilities" in spec_data:
                        for cap_str in spec_data["capabilities"]:
                            try:
                                # Handle the AgentCapability prefix
                                if isinstance(cap_str, str) and cap_str.startswith("AgentCapability."):
                                    # Extract just the enum value part
                                    cap_value = cap_str.split(".")[1].lower()
                                else:
                                    cap_value = cap_str.lower()
                                    
                                # Find the corresponding enum
                                matching_cap = None
                                for cap in AgentCapability:
                                    if cap.value == cap_value:
                                        matching_cap = cap
                                        break
                                
                                if matching_cap:
                                    capabilities.append(matching_cap)
                                else:
                                    return {"error": f"Invalid capability: {cap_str}"}
                            except (ValueError, IndexError, AttributeError):
                                return {"error": f"Invalid capability format: {cap_str}"}
                    
                    # Create specialization
                    specialization = AgentSpecialization(
                        domain=spec_data.get("domain", agent_type_str),
                        expertise_level=spec_data.get("expertise_level", 8),
                        capabilities=capabilities,
                        tools=spec_data.get("tools", []),
                        knowledge_base=spec_data.get("knowledge_base", [])
                    )
                
            if not agent_type_str:
                return {"error": "agent_type is required"}
                
            # Extract skills list if provided
            skills = parameters.get("skills", None)
            
            # Create the agent using the simple synchronous method
            agent_config = self.agent_builder.create_agent_simple(
                name=name,
                agent_type=agent_type_str,
                specialization=specialization,
                skills=skills,
            )
            
            return {"success": True, "agent_config": agent_config}
            
        except Exception as e:
            return {"error": str(e)}
            
    def _save_agent(self, parameters):
        """Save an agent configuration using AgentRegistryHandler"""
        try:
            agent_config = parameters.get("agent_config")
            if not agent_config:
                return {"error": "agent_config is required"}
                
            persist = parameters.get("persist", True)
            team_name = parameters.get("team_name")
            
            # Save using the agent builder which now uses AgentRegistryHandler
            agent_id = self.agent_builder.save_agent(
                agent_config=agent_config,
                persist=persist,
                team_name=team_name
            )
            
            return {"success": True, "agent_id": agent_id}
            
        except Exception as e:
            return {"error": str(e)}
            
    def _get_agent(self, parameters):
        """Retrieve an existing agent using AgentRegistryHandler"""
        try:
            agent_name = parameters.get("agent_name")
            agent_type_str = parameters.get("agent_type")
            
            if not agent_name:
                return {"error": "agent_name is required"}
                
            # Initialize AgentRegistryHandler
            from Handler.handler_agent_registry import AgentRegistryHandler
            registry = AgentRegistryHandler()
            
            # If agent_type is provided, use it to narrow the search
            if agent_type_str:
                try:
                    agent_type = AgentType(agent_type_str)
                    # Search for agent with specific type
                    result = asyncio.run(registry.list_agents(agent_type=agent_type.value))
                    if result.success:
                        agents = result.result
                        # Find agent with matching name
                        for agent in agents:
                            if agent["agent_name"].lower() == agent_name.lower():
                                # Get full agent details
                                agent_result = asyncio.run(registry.get_agent(agent["agent_id"]))
                                if agent_result.success:
                                    return {"success": True, "agent_config": agent_result.result}
                except ValueError:
                    return {"error": f"Invalid agent_type: {agent_type_str}"}
            
            # If no type specified or not found with type, search all agents
            result = asyncio.run(registry.list_agents())
            if result.success:
                agents = result.result
                # Find agent with matching name
                for agent in agents:
                    if agent["agent_name"].lower() == agent_name.lower():
                        # Get full agent details
                        agent_result = asyncio.run(registry.get_agent(agent["agent_id"]))
                        if agent_result.success:
                            return {"success": True, "agent_config": agent_result.result}
            
            return {"error": f"Agent {agent_name} not found"}
            
        except Exception as e:
            return {"error": f"Error retrieving agent: {str(e)}"}

    def _list_agents(self, parameters):
        """List all available agents using AgentRegistryHandler"""
        try:
            agent_type_str = parameters.get("agent_type")
            
            # Initialize AgentRegistryHandler
            from Handler.handler_agent_registry import AgentRegistryHandler
            registry = AgentRegistryHandler()
            
            # If agent_type is provided, filter by type
            if agent_type_str:
                try:
                    agent_type = AgentType(agent_type_str)
                    result = asyncio.run(registry.list_agents(agent_type=agent_type.value))
                    if result.success:
                        return {"success": True, "agents": result.result}
                    return {"error": "Failed to retrieve agents"}
                except ValueError:
                    return {"error": f"Invalid agent_type: {agent_type_str}"}
            
            # List all agents if no type specified
            result = asyncio.run(registry.list_agents())
            if result.success:
                return {"success": True, "agents": result.result}
            return {"error": "Failed to retrieve agents"}
            
        except Exception as e:
            return {"error": f"Error listing agents: {str(e)}"}

    def _delete_agent(self, parameters):
        """Delete an existing agent using AgentRegistryHandler"""
        try:
            agent_name = parameters.get("agent_name")
            agent_type_str = parameters.get("agent_type")
            
            if not agent_name:
                return {"error": "agent_name is required"}
                
            # Initialize AgentRegistryHandler
            from Handler.handler_agent_registry import AgentRegistryHandler
            registry = AgentRegistryHandler()
            
            # First, find the agent to get its ID
            if agent_type_str:
                try:
                    agent_type = AgentType(agent_type_str)
                    result = asyncio.run(registry.list_agents(agent_type=agent_type.value))
                    if result.success:
                        agents = result.result
                        # Find agent with matching name and type
                        for agent in agents:
                            if agent["agent_name"].lower() == agent_name.lower():
                                # Delete the agent
                                delete_result = asyncio.run(registry.delete_agent(agent["agent_id"]))
                                if delete_result.success:
                                    return {"success": True, "message": f"Agent {agent_name} deleted successfully"}
                                return {"error": "Failed to delete agent"}
                except ValueError:
                    return {"error": f"Invalid agent_type: {agent_type_str}"}
            
            # If no type specified or not found with type, search all agents
            result = asyncio.run(registry.list_agents())
            if result.success:
                agents = result.result
                # Find agent with matching name
                for agent in agents:
                    if agent["agent_name"].lower() == agent_name.lower():
                        # Delete the agent
                        delete_result = asyncio.run(registry.delete_agent(agent["agent_id"]))
                        if delete_result.success:
                            return {"success": True, "message": f"Agent {agent_name} deleted successfully"}
                        return {"error": "Failed to delete agent"}
            
            return {"error": f"Agent {agent_name} not found"}
            
        except Exception as e:
            return {"error": f"Error deleting agent: {str(e)}"}

# Lazy global instance — only created on first use (not at import time)

# Removed: _LazyAgentBuilderProxy, AgentBuilderOrchestratorAgent (2,486 lines)
# March 1, 2026 — OpenClaw is the orchestrator now
