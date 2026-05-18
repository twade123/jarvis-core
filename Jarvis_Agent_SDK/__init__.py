"""
Jarvis Agent SDK

This package provides the core functionality for the Jarvis agent system,
including hybrid agents, orchestration, and integration with various handlers.
"""

# Lazy imports — heavy modules (boardroom, orchestrator, intelligence) 
# are loaded on demand, not on package import.
# This prevents importing one lightweight module (e.g. http_utils) 
# from triggering the entire intelligence/spaCy/BoardRoom init chain.

_LAZY_MODULES = {
    'base', 'common_utils', 'jarvis_orchestrator', 'import_helper',
    'workflow_tools', 'boardroom_connector', 'database',
    'error_monitor', 'task_status_registry', 'response_format',
}

def __getattr__(name):
    """Lazy-load submodules on first access."""
    if name in _LAZY_MODULES:
        import importlib
        mod = importlib.import_module(f'.{name}', __name__)
        globals()[name] = mod
        return mod
    raise AttributeError(f"module 'Jarvis_Agent_SDK' has no attribute {name!r}")

__all__ = list(_LAZY_MODULES) 