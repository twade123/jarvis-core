from typing import Dict, List, Optional
from dataclasses import dataclass
from enum import Enum
from ..configs.capabilities import AgentCapability

@dataclass
class AgentTool:
    name: str
    description: str
    parameters: Dict
    strict: bool = True
    required: List[str] = None

class BaseAgent:
    """Base class for all specialized agents"""
    
    def __init__(
        self,
        name: str,
        agent_type: str,
        capabilities: List[AgentCapability],
        tools: List[AgentTool],
        knowledge_base: List[str],
        expertise_level: int = 9
    ):
        self.name = name
        self.agent_type = agent_type
        self.capabilities = capabilities
        self.tools = tools
        self.knowledge_base = knowledge_base
        self.expertise_level = expertise_level
        
    def get_system_prompt(self) -> str:
        """Generate the system prompt for this agent"""
        return f"""You are {self.name}, a PhD-level expert {self.agent_type} AI agent.

Expertise Level: {self.expertise_level}/10 (PhD with extensive research and practical experience)

Your core capabilities include:
{self._format_capabilities()}

Your knowledge base covers:
{self._format_knowledge_base()}

You have access to the following specialized tools:
{self._format_tools()}"""

    def get_tools(self) -> List[Dict]:
        """Get the agent's tools in a format ready for API calls"""
        return [
            {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.parameters
                },
                "strict": tool.strict
            }
            for tool in self.tools
        ]

    def get_function_schema(self) -> Dict:
        """Get the function calling schema for this agent"""
        schema = {
            "type": "object",
            "properties": {},
            "required": []
        }
        
        for tool in self.tools:
            schema["properties"][tool.name] = {
                "type": "object",
                "properties": tool.parameters,
                "required": tool.required or []
            }
            
        return schema

    def _format_capabilities(self) -> str:
        """Format capabilities for the prompt"""
        return "\n".join([f"- {cap.value.title()}: Expert-level capability in {cap.value}" 
                         for cap in self.capabilities])
    
    def _format_knowledge_base(self) -> str:
        """Format knowledge base for the prompt"""
        return "\n".join([f"- {knowledge}" for knowledge in self.knowledge_base])
    
    def _format_tools(self) -> str:
        """Format tools for the prompt"""
        return "\n".join([f"- {tool.name}: {tool.description}" for tool in self.tools]) 