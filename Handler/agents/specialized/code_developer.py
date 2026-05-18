from typing import Dict, List, Optional
from ..base_agent import BaseAgent
from ...configs.agent_types import AgentType
from ...configs.capabilities import AgentCapability, CAPABILITY_CATEGORIES
from ...tools.code_tools import get_all_code_tools, get_code_tool

class CodeDeveloperAgent(BaseAgent):
    """Specialized agent for software development and code review"""
    
    def __init__(self, name: str):
        # Get all code-related capabilities
        capabilities = list(CAPABILITY_CATEGORIES["core"].union(CAPABILITY_CATEGORIES["code"]))
        
        # Get all code tools
        tools = get_all_code_tools()
        
        # Define knowledge base
        knowledge_base = [
            # Architecture & Design
            "Advanced Software Architecture",
            "Design Patterns and Best Practices",
            "Microservices Architecture",
            "Cloud-Native Development",
            "Serverless Architecture",
            "System Design Principles",
            
            # Development Skills
            "Full-Stack Development",
            "Frontend Frameworks",
            "Backend Development",
            "Database Design",
            "API Development",
            "Security Best Practices",
            
            # Project Management
            "Agile Methodologies",
            "Project Planning",
            "Team Collaboration",
            "Version Control",
            "CI/CD Practices",
            
            # Quality Assurance
            "Testing Strategies",
            "Code Review Practices",
            "Performance Optimization",
            "Security Testing",
            "Documentation Standards"
        ]
        
        super().__init__(
            name=name,
            agent_type=AgentType.CODE_DEVELOPER.value,
            capabilities=capabilities,
            tools=tools,
            knowledge_base=knowledge_base
        )
    
    def get_system_prompt(self) -> str:
        """Generate a specialized system prompt for code development"""
        base_prompt = super().get_system_prompt()
        
        code_specific_prompt = """
Development Principles:
1. Write clean, maintainable, and efficient code
2. Follow language-specific best practices
3. Implement proper error handling
4. Include comprehensive documentation
5. Write testable code
6. Consider performance implications
7. Follow SOLID principles
8. Use appropriate design patterns
9. Consider security implications
10. Plan for scalability

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
10. Plan for maintenance

Additional Expertise:
- Full-stack development
- Database design and optimization
- API development and integration
- Security implementation
- Performance optimization
- DevOps practices
- Quality assurance
- Technical documentation
- Project management
- Team collaboration"""

        return f"{base_prompt}\n{code_specific_prompt}"
    
    def review_code(self, code: str, review_type: str = "comprehensive") -> Dict:
        """Perform code review with specified depth"""
        review_tool = get_code_tool("review_code")
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
        optimize_tool = get_code_tool("optimize_code")
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
    
    def debug_code(self, code: str, error_message: Optional[str] = None) -> Dict:
        """Debug code with provided error information"""
        debug_tool = get_code_tool("debug_code")
        return {
            "type": "function",
            "function": {
                "name": debug_tool.name,
                "arguments": {
                    "code": code,
                    "error_message": error_message,
                    "environment": "development"
                }
            }
        }
    
    def generate_tests(self, code: str, framework: str) -> Dict:
        """Generate comprehensive tests for the code"""
        test_tool = get_code_tool("generate_tests")
        return {
            "type": "function",
            "function": {
                "name": test_tool.name,
                "arguments": {
                    "code": code,
                    "test_framework": framework,
                    "coverage_target": 90,
                    "include_edge_cases": True
                }
            }
        } 