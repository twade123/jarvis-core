---
name: agent-registry-specialist
description: Specialized agent skill for expert-level Agent Registry MCP operations including agent cataloging, discovery, performance tracking, version management, and capability-based search.
version: 1.0.0
category: mcp-specialist
author: Claude Code Agent Skills System
created: 2026-02-04
triggers:
  - "agent registration"
  - "agent catalog operations"
  - "agent discovery"
  - "agent performance tracking"
  - "agent version management"
  - "capability-based agent search"
capabilities:
  - agent_registration
  - agent_cataloging
  - agent_discovery
  - performance_tracking
  - version_management
  - capability_search
parent_orchestrator: mcp-domain-orchestrator
domain_type: agent_systems
can_execute: true
requires_human_approval: false
---

# Agent Registry Specialist

Expert-level operations for Agent Registry MCP, enabling comprehensive agent catalog management, discovery, performance tracking, and intelligent version-based execution selection.

## Overview

Agent Registry Handler MCP provides a critical bridge between file-based and database-based agent storage systems:

**Storage Integration:**
- **File System**: Handler/Agents/ directory (AgentBuilder storage)
- **Database**: boardroom.db agent_registry table (tracking and integration)
- **Synchronization**: Ensures agents created in one system are available in the other

**Core Capabilities:**
- Agent registration with semantic versioning
- Performance metric tracking (success rate, response time, request count)
- Capability-based agent discovery
- Version management and history tracking
- Best-performing agent selection
- Intelligent execution routing

## Core Tool Inventory

### Registration Tools

**1. register_module_agent** - Register new agent in registry
```python
# Register agent with full metadata and versioning
result = await register_module_agent(
    agent_id="email_orchestrator_v2",
    agent_name="Email Orchestrator",
    agent_type="orchestrator_bridge",
    module_name="email",
    capabilities=["send_email", "read_inbox", "filter_messages"],
    metadata={"workspace_id": "ws_001", "priority": "high"},
    version="2.1.0",
    compatibility_version="2.0.0"
)
```

**Parameters:**
- `agent_id` (str, required): Unique identifier
- `agent_name` (str, required): Human-readable name
- `agent_type` (str, required): Type classification (e.g., "orchestrator_bridge")
- `module_name` (str, required): Module the agent belongs to
- `capabilities` (list, optional): List of capability strings
- `metadata` (dict, optional): Additional metadata
- `version` (str, default="1.0.0"): Semantic version (X.Y.Z format)
- `compatibility_version` (str, optional): Minimum compatible version

**Returns:**
```python
{
    "agent_id": str,
    "db_saved": bool,
    "boardroom_registered": bool
}
```

**Version Validation:**
- Must follow semantic versioning: `X.Y.Z` (e.g., "1.2.3")
- Major.Minor.Patch format enforced
- Invalid format returns error

### Retrieval Tools

**2. get_agent** - Retrieve agent by ID
```python
# Get agent details from registry
result = await get_agent(agent_id="email_orchestrator_v2")
```

**Returns:** Full agent data including capabilities, metadata, performance metrics

**3. list_agents** - List agents with optional filters
```python
# List all active agents
all_agents = await list_agents()

# Filter by module
email_agents = await list_agents(module_name="email")

# Filter by type
orchestrators = await list_agents(agent_type="orchestrator_bridge")

# Combined filters
email_orchestrators = await list_agents(
    module_name="email",
    agent_type="orchestrator_bridge"
)
```

**Parameters:**
- `module_name` (str, optional): Filter by module
- `agent_type` (str, optional): Filter by type

**Returns:** List of agent data dictionaries

### Capability-Based Discovery Tools

**4. find_agents_by_capability** - Search by single capability
```python
# Find all agents with send_email capability
agents = await find_agents_by_capability(capability="send_email")
```

**5. find_agents_by_capabilities** - Search by multiple capabilities (AND logic)
```python
# Find agents with ALL specified capabilities
agents = await find_agents_by_capabilities(
    capabilities=["send_email", "read_inbox", "filter_messages"]
)
```

**Use Case:** Intelligent agent selection based on required capabilities for a task.

### Status Management Tools

**6. update_agent_status** - Change agent status
```python
# Deactivate agent
result = await update_agent_status(
    agent_id="old_email_agent",
    status="inactive"
)

# Valid statuses: "active", "inactive", "deleted"
```

### Performance Tracking Tools

**7. update_agent_performance** - Record execution metrics
```python
# Update after task execution
result = await update_agent_performance(
    agent_id="email_orchestrator_v2",
    success=True,
    response_time=1.23
)
```

**Metrics Updated:**
- `success_count`: Incremented on success
- `failure_count`: Incremented on failure
- `total_requests`: Incremented every execution
- `avg_response_time`: Weighted average updated
- `last_success_time`: Updated on successful execution

**8. get_agent_performance_report** - Generate performance reports
```python
# Report for specific agent
agent_report = await get_agent_performance_report(
    agent_id="email_orchestrator_v2"
)

# Report for module (top 10 agents)
module_report = await get_agent_performance_report(
    module_name="email",
    top_n=10
)

# Overall system report (top 20 agents)
system_report = await get_agent_performance_report(top_n=20)
```

**Report Structure:**
```python
{
    "timestamp": float,
    "report_type": "agent_performance",
    "agent": {  # If specific agent requested
        "agent_id": str,
        "agent_name": str,
        "version": str,
        "success_count": int,
        "failure_count": int,
        "avg_response_time": float,
        "total_requests": int,
        "success_rate": float,
        "version_history": [...]
    },
    "top_agents": [  # If module/system report
        {...agent_metrics...}
    ],
    "summary": {
        "total_success": int,
        "total_failure": int,
        "total_requests": int,
        "overall_success_rate": float,
        "overall_avg_response_time": float
    }
}
```

### Version Management Tools

**9. find_best_agent_version** - Select best-performing version
```python
# Find best version based on performance
result = await find_best_agent_version(
    base_agent_id="email_agent",
    min_requests=5,
    capability_requirements=["send_email", "read_inbox"]
)
```

**Parameters:**
- `base_agent_id` (str, required): Base agent ID (matches versions with this prefix)
- `min_requests` (int, default=5): Minimum request count for consideration
- `capability_requirements` (list, optional): Required capabilities filter

**Scoring Algorithm:**
- Success rate weight: 70%
- Response time weight: 30%
- Normalized response time: 10 seconds upper bound
- Combined score: `(success_rate * 0.7) + (normalized_time * 0.3)`

**Returns:**
```python
{
    "agent_id": str,
    "agent_name": str,
    "version": str,
    "success_rate": float,
    "avg_response_time": float,
    "total_requests": int,
    "score": float,
    "capabilities": list,
    "comparison": {
        "total_versions_analyzed": int,
        "score_components": {...}
    }
}
```

**10. execute_with_best_agent** - Intelligent execution routing
```python
# Automatically select and execute with best agent version
result = await execute_with_best_agent(
    base_agent_id="email_agent",
    task_parameters={
        "action": "send_email",
        "to": "user@example.com",
        "subject": "Test",
        "body": "Hello World"
    },
    min_requests=5,
    capability_requirements=["send_email"],
    fallback_to_latest=True
)
```

**Parameters:**
- `base_agent_id` (str, required): Base agent ID
- `task_parameters` (dict, required): Task parameters for agent
- `min_requests` (int, default=5): Minimum requests for best version selection
- `capability_requirements` (list, optional): Required capabilities
- `fallback_to_latest` (bool, default=True): Use latest version if no qualified version found

**Selection Logic:**
1. Find best-performing version meeting criteria
2. If none found and fallback enabled, use latest version
3. Execute task with selected agent
4. Update performance metrics automatically
5. Return result with metadata

**Returns:**
```python
{
    "success": bool,
    "result": {...task_result...},
    "__meta": {
        "agent_id": str,
        "version": str,
        "selection_method": str,  # "performance_based" or "latest_version_fallback"
        "response_time": float
    }
}
```

## Execution Workflows

### Workflow 1: Register New Agent

**Use Case:** Agent created by AgentBuilder needs registry entry

```python
# Step 1: Register agent with full metadata
result = await register_module_agent(
    agent_id="calendar_sync_agent",
    agent_name="Calendar Sync Agent",
    agent_type="data_sync",
    module_name="calendar",
    capabilities=["sync_events", "resolve_conflicts", "batch_update"],
    metadata={
        "workspace_id": "ws_calendar_001",
        "sync_interval": 300,
        "priority": "medium"
    },
    version="1.0.0",
    compatibility_version="1.0.0"
)

# Step 2: Verify registration
if result.success:
    print(f"Agent {result.result['agent_id']} registered")
    print(f"Database saved: {result.result['db_saved']}")
    print(f"BoardRoom registered: {result.result['boardroom_registered']}")
```

**When to use:**
- New agent created
- Agent configuration updated
- Re-registering after changes

### Workflow 2: Capability-Based Agent Discovery

**Use Case:** Find agents that can handle a specific task

```python
# Step 1: Determine required capabilities
required = ["send_email", "attach_files", "schedule_send"]

# Step 2: Search for capable agents
agents = await find_agents_by_capabilities(capabilities=required)

# Step 3: Filter by performance if needed
if len(agents) > 1:
    # Get performance reports for each
    reports = []
    for agent in agents:
        report = await get_agent_performance_report(
            agent_id=agent["agent_id"]
        )
        reports.append(report)

    # Select best performer
    best = max(reports, key=lambda r: r.result["agent"]["success_rate"])
    selected_agent_id = best.result["agent"]["agent_id"]
else:
    selected_agent_id = agents[0]["agent_id"]

# Step 4: Execute with selected agent
# (Use selected_agent_id for task execution)
```

**When to use:**
- Task routing based on capabilities
- Load balancing across capable agents
- Fallback selection when primary unavailable

### Workflow 3: Performance-Based Execution

**Use Case:** Automatically route to best-performing agent version

```python
# Single call handles everything
result = await execute_with_best_agent(
    base_agent_id="data_processor",
    task_parameters={
        "action": "process_dataset",
        "dataset_id": "ds_12345",
        "transformations": ["normalize", "deduplicate", "validate"]
    },
    min_requests=10,  # Only consider versions with 10+ executions
    capability_requirements=["normalize", "deduplicate", "validate"],
    fallback_to_latest=True
)

# Result includes execution outcome + metadata
if result.success:
    print(f"Processed by {result.result['__meta']['agent_id']}")
    print(f"Version: {result.result['__meta']['version']}")
    print(f"Selection: {result.result['__meta']['selection_method']}")
    print(f"Response time: {result.result['__meta']['response_time']:.2f}s")
```

**When to use:**
- Production task execution
- Performance-critical operations
- A/B testing between versions
- Gradual rollout of new versions

### Workflow 4: Version Management and Rollback

**Use Case:** Track version performance and rollback if needed

```python
# Step 1: Deploy new version
await register_module_agent(
    agent_id="email_agent_v3",
    agent_name="Email Agent",
    agent_type="email_handler",
    module_name="email",
    capabilities=["send_email", "read_inbox"],
    version="3.0.0",
    compatibility_version="2.0.0"
)

# Step 2: Monitor performance over time
import time
time.sleep(3600)  # Wait 1 hour

report = await get_agent_performance_report(
    agent_id="email_agent_v3"
)

# Step 3: Compare with previous version
v2_report = await get_agent_performance_report(
    agent_id="email_agent_v2"
)

v3_success_rate = report.result["agent"]["success_rate"]
v2_success_rate = v2_report.result["agent"]["success_rate"]

# Step 4: Rollback if new version underperforming
if v3_success_rate < v2_success_rate - 0.1:  # 10% threshold
    # Deactivate v3
    await update_agent_status(
        agent_id="email_agent_v3",
        status="inactive"
    )

    # Reactivate v2
    await update_agent_status(
        agent_id="email_agent_v2",
        status="active"
    )

    print("Rolled back to v2 due to performance degradation")
```

**When to use:**
- Version deployments
- Performance regression detection
- Gradual version migration
- Production incident response

### Workflow 5: Module Performance Audit

**Use Case:** Analyze all agents in a module

```python
# Step 1: Get module performance report
report = await get_agent_performance_report(
    module_name="email",
    top_n=20
)

# Step 2: Analyze summary metrics
summary = report.result["summary"]
print(f"Module Success Rate: {summary['overall_success_rate']:.2%}")
print(f"Average Response Time: {summary['overall_avg_response_time']:.2f}s")
print(f"Total Requests: {summary['total_requests']}")

# Step 3: Identify underperformers
threshold = 0.9  # 90% success rate
top_agents = report.result["top_agents"]

underperformers = [
    agent for agent in top_agents
    if agent["success_rate"] < threshold
]

# Step 4: Flag for review or replacement
for agent in underperformers:
    print(f"⚠️ {agent['agent_name']} (v{agent['version']})")
    print(f"   Success rate: {agent['success_rate']:.2%}")
    print(f"   Requests: {agent['total_requests']}")
```

**When to use:**
- Regular performance audits
- Capacity planning
- Quality assurance
- System health monitoring

## Best Practices

### 1. Semantic Versioning

**Always use semantic versioning for agents:**

- **MAJOR** (X.0.0): Breaking changes, incompatible API changes
- **MINOR** (X.Y.0): New features, backward-compatible
- **PATCH** (X.Y.Z): Bug fixes, backward-compatible

**Examples:**
- `1.0.0` → `1.0.1`: Bug fix (patch)
- `1.0.1` → `1.1.0`: New feature added (minor)
- `1.1.0` → `2.0.0`: Breaking API change (major)

### 2. Capability Naming Conventions

**Use verb_noun format for capabilities:**

Good:
- `send_email`
- `read_inbox`
- `filter_messages`
- `sync_calendar`
- `validate_data`

Avoid:
- `email` (too vague)
- `EmailSending` (wrong casing)
- `can_send_email` (redundant "can")
- `emails` (not a capability, just a resource)

### 3. Performance Tracking

**Update performance after every execution:**

```python
import time

start_time = time.time()
try:
    # Execute agent task
    result = execute_agent_task(...)
    success = True
except Exception:
    success = False
finally:
    response_time = time.time() - start_time
    await update_agent_performance(
        agent_id=agent_id,
        success=success,
        response_time=response_time
    )
```

**Don't:**
- Skip performance updates
- Only update on success
- Use incorrect response times

### 4. Version Selection Strategy

**Use `execute_with_best_agent` for production:**

```python
# Production execution
result = await execute_with_best_agent(
    base_agent_id="critical_agent",
    task_parameters={...},
    min_requests=10,  # Require statistical significance
    fallback_to_latest=True
)
```

**Use specific version for testing:**

```python
# Testing/development
result = await execute_agent_task(
    agent_id="critical_agent_v2_beta",
    parameters={...}
)
```

### 5. Capability Requirements

**Be specific but not over-constrained:**

Good:
```python
# Core capabilities only
capability_requirements=["send_email", "attach_files"]
```

Avoid:
```python
# Over-specified - may exclude valid agents
capability_requirements=[
    "send_email", "attach_files", "validate_email",
    "check_spam", "retry_failed", "log_activity"
]
```

### 6. Metadata Usage

**Store operational context in metadata:**

```python
metadata = {
    "workspace_id": "ws_001",
    "deployment_env": "production",
    "owner_team": "platform-team",
    "cost_center": "engineering",
    "priority": "high",
    "sla_target_ms": 500,
    "max_retries": 3
}
```

**Useful for:**
- Workspace isolation
- Environment tracking
- Organizational mapping
- Performance targets
- Operational policies

## Performance Optimization

### Agent Selection Caching

Cache capability lookups to reduce database queries:

```python
# Cache agents by capability for 5 minutes
capability_cache = {}
cache_ttl = 300

def get_cached_agents(capability):
    if capability in capability_cache:
        cached_time, agents = capability_cache[capability]
        if time.time() - cached_time < cache_ttl:
            return agents

    # Cache miss - query database
    agents = await find_agents_by_capability(capability)
    capability_cache[capability] = (time.time(), agents)
    return agents
```

### Batch Performance Updates

For high-throughput systems, batch performance updates:

```python
# Accumulate metrics
pending_updates = []

async def queue_performance_update(agent_id, success, response_time):
    pending_updates.append((agent_id, success, response_time))

    # Flush every 100 updates or every 60 seconds
    if len(pending_updates) >= 100:
        await flush_performance_updates()

async def flush_performance_updates():
    for agent_id, success, response_time in pending_updates:
        await update_agent_performance(agent_id, success, response_time)
    pending_updates.clear()
```

### Version Comparison Optimization

Pre-calculate scores during registration:

```python
# Include performance targets in metadata
metadata = {
    "target_success_rate": 0.95,
    "target_response_time_ms": 500,
    "performance_tier": "premium"
}
```

Use tiers for quick filtering before detailed comparison.

## Common Patterns

### Pattern 1: Agent Health Check

```python
async def check_agent_health(agent_id, min_success_rate=0.9):
    report = await get_agent_performance_report(agent_id=agent_id)

    if not report.success:
        return {"healthy": False, "error": "Agent not found"}

    agent = report.result["agent"]
    success_rate = agent["success_rate"]
    total_requests = agent["total_requests"]

    # Require minimum sample size
    if total_requests < 10:
        return {"healthy": "insufficient_data", "requests": total_requests}

    # Check success rate
    healthy = success_rate >= min_success_rate

    return {
        "healthy": healthy,
        "success_rate": success_rate,
        "total_requests": total_requests,
        "avg_response_time": agent["avg_response_time"]
    }
```

### Pattern 2: Progressive Version Rollout

```python
async def progressive_rollout(old_version_id, new_version_id):
    # Start with 10% traffic to new version
    traffic_split = 0.1

    while traffic_split < 1.0:
        # Route traffic
        if random.random() < traffic_split:
            agent_id = new_version_id
        else:
            agent_id = old_version_id

        # Execute task...

        # Check performance after each hour
        time.sleep(3600)

        new_report = await get_agent_performance_report(agent_id=new_version_id)
        old_report = await get_agent_performance_report(agent_id=old_version_id)

        new_rate = new_report.result["agent"]["success_rate"]
        old_rate = old_report.result["agent"]["success_rate"]

        # Increase traffic if performing well
        if new_rate >= old_rate - 0.05:  # Within 5%
            traffic_split += 0.1
        else:
            # Rollback on performance degradation
            print("Rollback triggered")
            break
```

### Pattern 3: Capability-Based Load Balancing

```python
async def route_task_to_agent(task_requirements):
    # Find all capable agents
    agents = await find_agents_by_capabilities(
        capabilities=task_requirements["capabilities"]
    )

    if not agents:
        raise Exception("No capable agents found")

    # Load balance based on recent performance
    agent_loads = []
    for agent in agents:
        report = await get_agent_performance_report(
            agent_id=agent["agent_id"]
        )

        # Calculate load score (lower is better)
        metrics = report.result["agent"]
        load = metrics["avg_response_time"] * (1 + (1 - metrics["success_rate"]))
        agent_loads.append((agent["agent_id"], load))

    # Select agent with lowest load
    selected_agent_id = min(agent_loads, key=lambda x: x[1])[0]

    return selected_agent_id
```

## Integration with MCP Domain Orchestrator

Agent Registry Specialist reports to MCP Domain Orchestrator for:

1. **Agent Cataloging**: Register new MCP agents in central registry
2. **Performance Monitoring**: Track MCP agent execution metrics
3. **Intelligent Routing**: Select best-performing agent for tasks
4. **Version Management**: Coordinate agent version deployments

**Communication Pattern:**
```
MCP Domain Orchestrator
    ↓ (needs agent for task)
Agent Registry Specialist
    ↓ (searches capabilities, evaluates performance)
Agent Registry MCP (agent_registry)
    ↓ (queries database, returns best agent)
Selected Agent (execute task)
    ↓ (reports metrics back)
Agent Registry Specialist (updates performance)
```

## Success Criteria

Task successfully handled when:

- ✅ Agent registered in both database and BoardRoom
- ✅ Capabilities correctly indexed for discovery
- ✅ Performance metrics accurately tracked
- ✅ Version selection algorithm produces optimal results
- ✅ Status updates propagated correctly
- ✅ Reports generated with accurate data
- ✅ Best agent selection meets performance requirements
- ✅ Synchronization maintained between storage systems

## Troubleshooting

**Issue: Agent registration fails**
- Verify semantic version format (X.Y.Z)
- Check database connection
- Ensure agent_id is unique
- Verify module_name exists

**Issue: Capability search returns no results**
- Check capability name spelling
- Verify agents have capabilities registered
- Ensure agents are status="active"
- Check for case sensitivity issues

**Issue: Best agent selection fails**
- Lower min_requests threshold
- Enable fallback_to_latest
- Verify agents have performance data
- Check capability_requirements match

**Issue: Performance metrics not updating**
- Verify agent_id matches registered agent
- Check database write permissions
- Ensure update_agent_performance called after execution
- Verify connection not closed prematurely

## Database Schema

### agent_registry Table

```sql
CREATE TABLE agent_registry (
    id TEXT PRIMARY KEY,
    agent_id TEXT,
    agent_name TEXT,
    agent_type TEXT,
    module_name TEXT,
    capabilities TEXT,  -- JSON array
    status TEXT DEFAULT 'active',
    created_at REAL,
    updated_at REAL,
    metadata TEXT,  -- JSON object
    version TEXT DEFAULT '1.0.0',
    compatibility_version TEXT,
    last_success_time REAL,
    success_count INTEGER DEFAULT 0,
    failure_count INTEGER DEFAULT 0,
    avg_response_time REAL DEFAULT 0,
    total_requests INTEGER DEFAULT 0
)
```

### agent_version_history Table

```sql
CREATE TABLE agent_version_history (
    id TEXT PRIMARY KEY,
    agent_id TEXT,
    version TEXT,
    recorded_at REAL,
    performance_data TEXT  -- JSON snapshot
)
```

## References

- **Parent Orchestrator**: MCP Domain Orchestrator coordinates agent registry operations
- **Handler File**: `~/Jarvis/Handler/handler_agent_registry.py`
- **Database**: `~/Jarvis/Database/boardroom.db`
- **MCP Registry**: Registered as `agent_registry` in MCP infrastructure
- **Related Skills**: agent-builder-specialist, agent-s-specialist, swarm-specialist
