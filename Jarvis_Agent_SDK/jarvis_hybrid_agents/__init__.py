"""
Jarvis Hybrid Agents Package

This package provides adapter functions that allow the OpenAI Agents SDK to work with
the existing Handler system without modifying any of its code.
"""

from Jarvis_Agent_SDK.jarvis_hybrid_agents.handler_adapter import (
    process_with_boardroom,
    use_handler_agent,
    use_handler_swarm,
    call_boardroom,
    call_agent,
    call_swarm
)
from Jarvis_Agent_SDK.jarvis_hybrid_agents.bridge_tools import *

__all__ = [
    'process_with_boardroom',
    'use_handler_agent',
    'use_handler_swarm',
    'call_boardroom',
    'call_agent',
    'call_swarm'
] 