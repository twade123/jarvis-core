#!/usr/bin/env python3

"""
Handler package initialization
"""

import os
import sys
import logging
from pathlib import Path

# Add the project root to Python path
ROOT_DIR = Path(__file__).parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

# Import only the lightweight base — heavy handlers loaded on demand
from Handler.handler_base import BaseHandler

# Lazy imports for heavy handlers to avoid loading the entire chain
# (SwarmHandler → BoardRoom → intelligence → spaCy etc.) on every handler import
def __getattr__(name):
    """Lazy-load heavy handlers only when explicitly requested."""
    if name == 'SwarmHandler':
        from Handler.handler_swarm import SwarmHandler
        return SwarmHandler
    elif name == 'SwarmAgent':
        from Handler.handler_swarm import SwarmAgent
        return SwarmAgent
    elif name in ('execute_handler', 'HandlerSystem'):
        from Handler.handler_all import execute_handler, HandlerSystem
        return execute_handler if name == 'execute_handler' else HandlerSystem
    raise AttributeError(f"module 'Handler' has no attribute {name!r}")

__all__ = [
    'BaseHandler',
    'SwarmHandler',
    'SwarmAgent'
]