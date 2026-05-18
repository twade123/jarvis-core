from agents import Agent
from .agent_builder import AgentBuilder, AgentType
from .tools import execute_code, review_code, optimize_code
from .guardrails import validate_code_input, validate_review_input
from functools import wraps

# Import function_tool from Handler.agents if available, otherwise provide our own implementation
try:
    from Handler.agents import function_tool
except ImportError:
    # Fallback implementation of function_tool decorator
    def function_tool(func):
        """
        Decorator for function tools to be used with OpenAI agents.
        This provides compatibility with the Handler.agents function_tool system.
        """
        @wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)
        wrapper.is_tool = True
        wrapper.tool_schema = getattr(func, "tool_schema", {})
        return wrapper

builder = AgentBuilder()

# Code Developer Agent
code_agent_config = builder.create_agent(
    name="CodeExpert",
    agent_type=AgentType.CODE_DEVELOPER
)

code_agent = Agent(
    name=code_agent_config["name"],
    instructions=code_agent_config["system_prompt"],
    tools=[execute_code, review_code, optimize_code],
    input_guardrails=[validate_code_input, validate_review_input]
) 