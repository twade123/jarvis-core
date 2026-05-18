from typing import Dict, List, Optional
from dataclasses import dataclass
from enum import Enum

class AgentType(str, Enum):
    CODE_DEVELOPER = "code_developer"

@dataclass
class AgentSpecialization:
    domain: str
    expertise_level: int
    capabilities: List[str]
    tools: List[Dict]
    knowledge_base: List[str]

class AgentBuilder:
    def create_agent(
        self,
        name: str,
        agent_type: AgentType,
        specialization: Optional[AgentSpecialization] = None
    ) -> Dict:
        if specialization is None:
            specialization = AgentSpecialization(
                domain=agent_type.value,
                expertise_level=9,
                capabilities=[],
                tools=[],
                knowledge_base=[]
            )

        system_prompt = f"You are {name}, an expert {agent_type.value} agent."

        agent_config = {
            "name": name,
            "type": agent_type,
            "system_prompt": system_prompt,
            "tools": specialization.tools,
            "capabilities": specialization.capabilities,
            "knowledge_base": specialization.knowledge_base
        }

        return agent_config 