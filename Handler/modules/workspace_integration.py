"""
Workspace Integration — Workspace operations, complexity analysis, and agent workspace creation.

Extracted from handler_claude.py. Handles:
- Multi-agent workspace requirement detection
- Workspace complexity analysis
- Agent workspace creation with orchestrators
- System profile detection and transitions
- Task completion detection

Standalone — no ClaudeHandler dependency.
"""

import logging
import os
import re
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


def requires_multi_agent_workspace(prompt: str, parameters: Dict = None) -> bool:
    """Determine if a request requires multi-agent workspace orchestration.
    
    Extracted from ClaudeHandler._requires_multi_agent_workspace (lines 4322-4393).
    """
    if not prompt:
        return False
    
    prompt_lower = prompt.lower()
    
    # Explicit multi-agent keywords
    multi_agent_keywords = [
        'multi-agent', 'multi agent', 'multiple agents', 'agent team',
        'collaborate', 'coordination', 'orchestrate', 'swarm',
        'divide the work', 'parallel agents', 'agent pool',
    ]
    if any(kw in prompt_lower for kw in multi_agent_keywords):
        return True
    
    # Complex task indicators that benefit from multi-agent
    complexity_indicators = [
        'full stack', 'entire system', 'comprehensive audit',
        'redesign everything', 'build a complete', 'end to end',
        'all components', 'the whole', 'from scratch',
    ]
    indicator_count = sum(1 for kw in complexity_indicators if kw in prompt_lower)
    if indicator_count >= 2:
        return True
    
    # Check parameters for explicit multi-agent request
    if parameters:
        execution_guidance = parameters.get('execution_guidance', {})
        intent = execution_guidance.get('intent_classification', {}).get('intent_type', '')
        if intent == 'multi_agent_coordination':
            return True
    
    return False


def analyze_workspace_complexity(prompt: str) -> Dict[str, Any]:
    """Analyze the complexity of a workspace request.
    
    Extracted from ClaudeHandler._analyze_workspace_complexity (lines 4394-4458).
    
    Returns:
        {
            "complexity": "simple"|"moderate"|"complex",
            "estimated_agents": int,
            "recommended_tools": list,
            "domains": list,
        }
    """
    prompt_lower = prompt.lower()
    
    domains = []
    domain_keywords = {
        'frontend': ['html', 'css', 'react', 'vue', 'angular', 'ui', 'frontend', 'front-end'],
        'backend': ['api', 'server', 'backend', 'back-end', 'endpoint', 'rest', 'graphql'],
        'database': ['database', 'sql', 'schema', 'migration', 'table', 'query'],
        'devops': ['deploy', 'docker', 'ci/cd', 'kubernetes', 'infrastructure'],
        'security': ['security', 'auth', 'authentication', 'encryption', 'vulnerability'],
        'testing': ['test', 'testing', 'spec', 'coverage', 'assertion'],
        'data': ['data', 'analytics', 'pipeline', 'etl', 'transform'],
    }
    
    for domain, keywords in domain_keywords.items():
        if any(kw in prompt_lower for kw in keywords):
            domains.append(domain)
    
    # Determine complexity
    if len(domains) >= 3:
        complexity = "complex"
        agents = min(len(domains) + 1, 8)  # Max 8 agents
    elif len(domains) >= 2:
        complexity = "moderate"
        agents = len(domains) + 1
    else:
        complexity = "simple"
        agents = 1
    
    return {
        "complexity": complexity,
        "estimated_agents": agents,
        "recommended_tools": ["Read", "Write", "Edit", "Bash", "Grep"],
        "domains": domains,
    }


def detect_system_profile(parameters: Dict) -> str:
    """Detect the appropriate system profile for a request.
    
    Extracted from ClaudeHandler._detect_system_profile (lines 11840-11887).
    Returns: "research" | "execution" | "creative" | "analysis" | "default"
    """
    prompt = parameters.get('prompt', '').lower()
    
    profiles = {
        'research': ['research', 'investigate', 'find out', 'look into', 'explore', 'analyze'],
        'execution': ['create', 'build', 'make', 'implement', 'deploy', 'set up', 'configure'],
        'creative': ['design', 'write', 'draft', 'compose', 'brainstorm', 'imagine'],
        'analysis': ['audit', 'review', 'evaluate', 'assess', 'compare', 'benchmark'],
    }
    
    scores = {}
    for profile, keywords in profiles.items():
        scores[profile] = sum(1 for kw in keywords if kw in prompt)
    
    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else "default"


def workspace_task_appears_complete(messages: List[Dict], tool_results: List = None) -> bool:
    """Heuristic check if a workspace task appears to be complete.
    
    Extracted from ClaudeHandler._workspace_task_appears_complete (lines 15755-15770).
    """
    if not messages:
        return False
    
    # Check last assistant message for completion indicators
    last_assistant = None
    for msg in reversed(messages):
        if msg.get('role') == 'assistant':
            last_assistant = msg.get('content', '')
            break
    
    if not last_assistant:
        return False
    
    completion_indicators = [
        'completed', 'finished', 'done', 'all set', 'ready',
        'here\'s the result', 'summary:', 'final result',
    ]
    
    return any(ind in last_assistant.lower() for ind in completion_indicators)


def generate_workspace_partial_summary(messages: List[Dict], max_length: int = 500) -> str:
    """Generate a partial summary of workspace progress.
    
    Extracted from ClaudeHandler._generate_workspace_partial_summary (lines 15771-15793).
    """
    if not messages:
        return "No progress yet."
    
    # Get last few assistant messages
    assistant_msgs = [m['content'] for m in messages if m.get('role') == 'assistant']
    if not assistant_msgs:
        return "Work in progress, no results yet."
    
    # Take the last message as summary
    last = assistant_msgs[-1]
    if len(last) > max_length:
        return last[:max_length] + "..."
    return last
