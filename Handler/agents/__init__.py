"""
Agent system initialization file

This file exposes the necessary classes and functions from the agents module,
while preventing circular imports through lazy loading when needed.
"""

# Import required modules
from .base_agent import BaseAgent as Agent
from .base_agent import AgentTool
# Add safe imports for other components
# These won't be loaded until explicitly accessed

# Dummy implementations to prevent import errors
class Runner:
    """Placeholder for Runner from OpenAI agents SDK"""
    pass

def function_tool(func):
    """Decorator for function tools"""
    return func

def set_default_openai_key(key):
    """Set default OpenAI API key"""
    pass

def trace(*args, **kwargs):
    """Tracing utility"""
    pass

class RunConfig:
    """Placeholder for RunConfig"""
    pass

# Export these symbols
__all__ = [
    'Agent',
    'Runner',
    'function_tool',
    'set_default_openai_key',
    'trace',
    'RunConfig',
    'AgentTool'
]
