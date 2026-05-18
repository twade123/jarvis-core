"""
Resource Manager — Container management, cost tracking, and system health.

Extracted from handler_claude.py. Contains:
- Code execution container lifecycle (Anthropic SDK feature)
- Cost estimation and budget compliance
- System performance monitoring
- Health checks and cache management
- Agent performance tracking

NOTE: 38 MCP server memory management methods from handler_claude are NOT extracted here.
Those were Jarvis-specific infrastructure for managing spaCy/NLP server memory on a 65MB device.
OpenClaw replaces that functionality. They remain in handler_claude.py as legacy until removed.

Standalone — no ClaudeHandler dependency.
"""

import logging
import os
import time
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Container Management (Anthropic Code Execution - Phase 3)
# ---------------------------------------------------------------------------

class ContainerManager:
    """Manages Anthropic code execution containers.
    
    Containers allow stateful code execution across multiple API calls.
    The SDK handles the container lifecycle; this tracks metadata.
    """
    
    def __init__(self, cleanup_interval: int = 300):
        self.active_containers: Dict[str, Dict] = {}  # container_id -> metadata
        self.cleanup_interval = cleanup_interval
        self.last_cleanup = time.time()
    
    def extract_metadata(self, response, session_id: str) -> Optional[Dict]:
        """Extract container metadata from API response.
        
        Extracted from ClaudeHandler._extract_container_metadata (lines 2629-2664).
        """
        try:
            container_id = None
            
            # Check response for container info
            if hasattr(response, 'container'):
                container_id = response.container
            elif hasattr(response, 'content'):
                for block in response.content:
                    if hasattr(block, 'container') and block.container:
                        container_id = block.container
            
            if container_id:
                metadata = {
                    'container_id': container_id,
                    'session_id': session_id,
                    'created_at': time.time(),
                    'expires_at': time.time() + 3600,  # 1 hour default
                    'last_used': time.time(),
                }
                self.active_containers[container_id] = metadata
                logger.info(f"Tracked container: {container_id[:16]}... for session {session_id[:8]}")
                return metadata
            
            return None
        except Exception as e:
            logger.error(f"Error extracting container metadata: {e}")
            return None
    
    def cleanup_expired(self):
        """Remove expired containers from tracking."""
        if time.time() - self.last_cleanup < self.cleanup_interval:
            return
        
        now = time.time()
        expired = [cid for cid, meta in self.active_containers.items()
                   if meta.get('expires_at', 0) < now]
        
        for cid in expired:
            del self.active_containers[cid]
            logger.info(f"Cleaned up expired container: {cid[:16]}...")
        
        self.last_cleanup = now
    
    def get_active_container(self, session_id: str) -> Optional[str]:
        """Get active container for a session."""
        self.cleanup_expired()
        for cid, meta in self.active_containers.items():
            if meta.get('session_id') == session_id:
                meta['last_used'] = time.time()
                return cid
        return None


# ---------------------------------------------------------------------------
# Cost Tracking
# ---------------------------------------------------------------------------

class CostTracker:
    """Track and estimate API costs across all backends.
    
    Works with Anthropic, OpenAI, and local models (local = $0).
    Extracted from ClaudeHandler cost optimization methods.
    """
    
    # Cost per 1M tokens (as of 2026)
    PRICING = {
        # Anthropic
        'claude-sonnet-4-5-20250929': {'input': 3.0, 'output': 15.0},
        'claude-sonnet-4-20250514': {'input': 3.0, 'output': 15.0},
        'claude-opus-4-20250514': {'input': 15.0, 'output': 75.0},
        'claude-opus-4-1-20260601': {'input': 15.0, 'output': 75.0},
        # OpenAI
        'gpt-4o': {'input': 2.5, 'output': 10.0},
        'gpt-4o-mini': {'input': 0.15, 'output': 0.6},
        # Local models = free
        'default_local': {'input': 0.0, 'output': 0.0},
    }
    
    def __init__(self, budget_limit: float = None):
        self.budget_limit = budget_limit  # Daily budget in dollars
        self.daily_cost = 0.0
        self.daily_reset_time = time.time()
        self.total_cost = 0.0
        self.request_log: List[Dict] = []
    
    def estimate_cost(self, model: str, input_tokens: int, output_tokens: int) -> float:
        """Estimate cost for a request."""
        # Local models are free
        if any(model.startswith(p) for p in ['ollama/', 'local/', 'trained/']):
            return 0.0
        
        pricing = self.PRICING.get(model, self.PRICING.get('claude-sonnet-4-5-20250929'))
        input_cost = (input_tokens / 1_000_000) * pricing['input']
        output_cost = (output_tokens / 1_000_000) * pricing['output']
        return input_cost + output_cost
    
    def record_request(self, model: str, input_tokens: int, output_tokens: int):
        """Record a completed request for cost tracking."""
        cost = self.estimate_cost(model, input_tokens, output_tokens)
        
        # Reset daily counter if needed
        if time.time() - self.daily_reset_time > 86400:
            self.daily_cost = 0.0
            self.daily_reset_time = time.time()
        
        self.daily_cost += cost
        self.total_cost += cost
        self.request_log.append({
            'model': model,
            'input_tokens': input_tokens,
            'output_tokens': output_tokens,
            'cost': cost,
            'timestamp': time.time(),
        })
    
    def check_budget_compliance(self) -> Dict[str, Any]:
        """Check if current spending is within budget."""
        return {
            'daily_cost': round(self.daily_cost, 4),
            'total_cost': round(self.total_cost, 4),
            'budget_limit': self.budget_limit,
            'within_budget': self.daily_cost <= self.budget_limit if self.budget_limit else True,
            'remaining': round(self.budget_limit - self.daily_cost, 4) if self.budget_limit else None,
            'request_count': len(self.request_log),
        }
    
    def get_cost_summary(self) -> Dict[str, Any]:
        """Get cost breakdown by model."""
        by_model = {}
        for req in self.request_log:
            model = req['model']
            if model not in by_model:
                by_model[model] = {'requests': 0, 'cost': 0.0, 'input_tokens': 0, 'output_tokens': 0}
            by_model[model]['requests'] += 1
            by_model[model]['cost'] += req['cost']
            by_model[model]['input_tokens'] += req['input_tokens']
            by_model[model]['output_tokens'] += req['output_tokens']
        
        return {
            'by_model': by_model,
            'total_cost': round(self.total_cost, 4),
            'daily_cost': round(self.daily_cost, 4),
        }


# ---------------------------------------------------------------------------
# Performance Monitoring
# ---------------------------------------------------------------------------

class PerformanceMonitor:
    """Monitor system and agent performance.
    
    Tracks response times, error rates, and agent effectiveness.
    """
    
    def __init__(self):
        self.metrics: List[Dict] = []
        self.agent_performance: Dict[str, Dict] = {}  # agent_name -> {wins, losses, ...}
    
    def record_request(self, model: str, duration_ms: float, success: bool,
                      input_tokens: int = 0, output_tokens: int = 0):
        """Record a request metric."""
        self.metrics.append({
            'model': model,
            'duration_ms': duration_ms,
            'success': success,
            'input_tokens': input_tokens,
            'output_tokens': output_tokens,
            'timestamp': time.time(),
        })
    
    def track_agent_performance(self, agent_name: str, task_result: Dict):
        """Track agent task performance for optimization.
        
        Extracted from ClaudeHandler._track_agent_performance (lines 14197-14251).
        """
        if agent_name not in self.agent_performance:
            self.agent_performance[agent_name] = {
                'total_tasks': 0, 'successful': 0, 'failed': 0,
                'avg_duration_ms': 0, 'total_duration_ms': 0,
            }
        
        perf = self.agent_performance[agent_name]
        perf['total_tasks'] += 1
        
        if task_result.get('success', False):
            perf['successful'] += 1
        else:
            perf['failed'] += 1
        
        duration = task_result.get('duration_ms', 0)
        perf['total_duration_ms'] += duration
        perf['avg_duration_ms'] = perf['total_duration_ms'] / perf['total_tasks']
    
    def get_summary(self, last_n: int = 100) -> Dict[str, Any]:
        """Get performance summary."""
        recent = self.metrics[-last_n:]
        if not recent:
            return {'status': 'no data'}
        
        durations = [m['duration_ms'] for m in recent]
        successes = sum(1 for m in recent if m['success'])
        
        return {
            'requests': len(recent),
            'success_rate': round(successes / len(recent), 3),
            'avg_duration_ms': round(sum(durations) / len(durations), 1),
            'p95_duration_ms': round(sorted(durations)[int(len(durations) * 0.95)], 1) if len(durations) >= 20 else None,
            'agent_performance': self.agent_performance,
        }
    
    def filter_agents_by_performance(self, agents: List[Dict], 
                                      min_success_rate: float = 0.7) -> List[Dict]:
        """Filter agents by their performance history.
        
        Extracted from ClaudeHandler._filter_agents_by_performance (lines 14143-14196).
        """
        filtered = []
        for agent in agents:
            name = agent.get('name', '')
            perf = self.agent_performance.get(name)
            
            if perf is None:
                # No history — include by default
                filtered.append(agent)
                continue
            
            if perf['total_tasks'] == 0:
                filtered.append(agent)
                continue
            
            success_rate = perf['successful'] / perf['total_tasks']
            if success_rate >= min_success_rate:
                filtered.append(agent)
            else:
                logger.info(f"Filtered out agent '{name}' — success rate {success_rate:.1%} < {min_success_rate:.0%}")
        
        return filtered


# ---------------------------------------------------------------------------
# Health Check
# ---------------------------------------------------------------------------

def perform_health_check() -> Dict[str, Any]:
    """Perform system health check.
    
    Returns status of key subsystems.
    """
    import shutil
    
    disk = shutil.disk_usage(os.path.expanduser("~"))
    
    return {
        'status': 'healthy',
        'timestamp': time.time(),
        'disk_free_gb': round(disk.free / (1024**3), 1),
        'disk_total_gb': round(disk.total / (1024**3), 1),
        'disk_used_pct': round((disk.used / disk.total) * 100, 1),
    }
