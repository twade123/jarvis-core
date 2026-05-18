from typing import List, Optional, Dict
from .base_agent import BaseAgent, AgentTool
from ..configs.capabilities import AgentCapability
from ..configs.agent_configs import CODE_DEVELOPER_CONFIG

class CodeDeveloperAgent(BaseAgent):
    """Specialized agent for software development and code review"""
    
    def __init__(self, name: str):
        super().__init__(
            name=name,
            agent_type="code_developer",
            capabilities=CODE_DEVELOPER_CONFIG["base_capabilities"],
            tools=CODE_DEVELOPER_CONFIG["default_tools"],
            knowledge_base=CODE_DEVELOPER_CONFIG["knowledge_base"]
        )
        
    def get_system_prompt(self) -> str:
        """Generate a specialized system prompt for code development"""
        base_prompt = super().get_system_prompt()
        
        code_specific_prompt = """
Operating Parameters:
1. Write clean, maintainable, and efficient code
2. Follow language-specific best practices
3. Consider security implications in all code
4. Implement proper error handling
5. Include comprehensive documentation
6. Write testable code
7. Consider performance implications
8. Follow SOLID principles
9. Use appropriate design patterns
10. Consider scalability requirements

Development Workflow:
1. Analyze requirements thoroughly
2. Design system architecture
3. Write modular code
4. Implement comprehensive tests
5. Perform code reviews
6. Optimize performance
7. Document thoroughly
8. Handle edge cases
9. Implement security measures
10. Plan for maintenance"""

        return f"{base_prompt}\n{code_specific_prompt}"
    
    def review_code(self, code: str, review_type: str = "comprehensive") -> Dict:
        """Perform code review with specified depth"""
        review_tool = next(tool for tool in self.tools if tool.name == "review_code")
        return {
            "type": "function",
            "function": {
                "name": review_tool.name,
                "arguments": {
                    "code": code,
                    "review_type": review_type,
                    "depth": "comprehensive",
                    "include_metrics": True
                }
            }
        }
    
    def optimize_code(self, code: str, target: str = "both") -> Dict:
        """Optimize code for specified target (speed/memory/both)"""
        optimize_tool = next(tool for tool in self.tools if tool.name == "optimize_code")
        return {
            "type": "function",
            "function": {
                "name": optimize_tool.name,
                "arguments": {
                    "code": code,
                    "optimization_target": target,
                    "scalability": True
                }
            }
        } 