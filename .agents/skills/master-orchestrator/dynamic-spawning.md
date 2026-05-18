# Dynamic Orchestrator Spawning

Enable Master Orchestrator to create additional domain orchestrator instances dynamically when bottlenecks are detected, preventing task queuing and maintaining system responsiveness.

---

## 1. Spawning Trigger (from bottleneck-detection.md)

### Detection Input

Master Orchestrator receives bottleneck detection output from @./bottleneck-detection.md:
- **Boolean decision**: Spawn required (true/false)
- **Severity score**: 1-10 scale indicating bottleneck urgency
- **Bottleneck metrics**: Which thresholds exceeded (queue, response time, agents)
- **Domain type**: Which domain orchestrator is bottlenecked

### Trigger Criteria

Spawning triggered when:
- Bottleneck detected (at least 2 of 3 metrics exceed thresholds)
- Severity score ≥ 4 (moderate to critical bottleneck)
- Sustained threshold (3 of 4 measurements over 2 minutes)
- Worsening trend confirmed (recent metrics 10%+ above baseline)

### Validation Before Spawn

Master Orchestrator validates spawn decision before proceeding:

```python
function validate_spawn_decision(domain_type, severity):
    """
    Validate that spawning is appropriate before proceeding.

    Args:
        domain_type: Domain requiring additional instance (e.g., "mcp")
        severity: Bottleneck severity score 1-10

    Returns:
        (spawn_approved: bool, reason: str)
    """
    # Check 1: Cooldown period active?
    if in_cooldown(domain_type) and severity < 10:
        # Severity 10 bypasses cooldown for critical bottlenecks
        return False, "Spawn blocked: cooldown period active"

    # Check 2: At maximum instances?
    current_count = get_instance_count(domain_type)
    max_allowed = get_max_instances(domain_type)  # Default: 5

    if current_count >= max_allowed:
        return False, f"Spawn blocked: at maximum instances ({max_allowed})"

    # Check 3: Bottleneck still present?
    # Re-check metrics to avoid spawning for already-resolved bottleneck
    current_metrics = get_current_metrics(domain_type)
    if not is_bottlenecked(current_metrics):
        return False, "Spawn cancelled: bottleneck resolved"

    # All checks passed
    return True, f"Spawn approved: severity {severity}"
```

---

## 2. Spawning Process Algorithm

### Complete Spawning Flow

```python
function spawn_domain_orchestrator(domain_type, severity):
    """
    Create new domain orchestrator instance with dedicated workspace.

    Args:
        domain_type: Domain to spawn (mcp, frontend, backend, infrastructure, quality)
        severity: Bottleneck severity score 1-10

    Returns:
        bool: True if spawn successful, False if blocked
    """
    # Step 1: Validate spawn decision
    if in_cooldown(domain_type) and severity < 10:
        log("Spawn blocked: cooldown period active")
        return False

    if at_max_instances(domain_type):
        log("Spawn blocked: max instances reached")
        alert_administrators(domain_type, "maximum capacity reached")
        return False

    # Step 2: Generate unique instance ID
    instance_number = get_next_instance_number(domain_type)
    instance_id = f"{domain_type}-orchestrator-{instance_number}"

    # Step 3: Create dedicated workspace for new instance
    workspace_id = create_workspace(
        name=f"{domain_type.title()} Domain Orchestrator #{instance_number}",
        type="domain-orchestrator",
        parent_workspace=master_workspace_id,
        metadata={
            "domain": domain_type,
            "instance_number": instance_number,
            "spawn_timestamp": get_current_timestamp(),
            "spawned_due_to": "bottleneck_detection",
            "severity": severity
        }
    )

    # Step 4: Initialize domain orchestrator agent
    # Agent receives:
    #   - Instance ID for tracking and identification
    #   - Workspace ID for communication and isolation
    #   - Domain type (determines capabilities and responsibilities)
    #   - Initial context from master orchestrator
    orchestrator = initialize_domain_orchestrator(
        instance_id=instance_id,
        workspace_id=workspace_id,
        domain_type=domain_type,
        context={
            "capabilities": get_domain_capabilities(domain_type),
            "available_agents": get_domain_worker_agents(domain_type),
            "master_workspace": master_workspace_id,
            "communication_protocol": "hierarchical",
            "skill_reference": get_domain_skill_path(domain_type)
        }
    )

    # Step 5: Register instance in master's tracking
    register_instance(
        domain_type=domain_type,
        instance_id=instance_id,
        workspace_id=workspace_id,
        orchestrator=orchestrator,
        state="initializing",
        spawn_time=get_current_timestamp(),
        spawn_severity=severity
    )

    # Step 6: Add instance to load balancer pool
    load_balancer.add_instance(domain_type, instance_id, orchestrator)

    # Step 7: Set cooldown period (5 minutes)
    # Prevents cascade spawning before new instance stabilizes load
    set_cooldown(domain_type, duration=300)

    # Step 8: Update instance state to active
    update_instance_state(instance_id, "active")

    # Step 9: Log successful spawn
    log(f"Spawned {instance_id} in workspace {workspace_id} (severity {severity})")

    # Step 10: Notify domain orchestrator to begin accepting tasks
    notify_orchestrator_ready(orchestrator, instance_id)

    return True
```

### Key Implementation Details

**Workspace Hierarchy**:
```
Master Workspace (master-001)
└── MCP Domain Workspace #1 (mcp-domain-001) [original]
└── MCP Domain Workspace #2 (mcp-domain-002) [spawned - this function creates]
└── MCP Domain Workspace #3 (mcp-domain-003) [spawned]
```

**Context Provision**: New instance receives all information needed to coordinate domain tasks:
- Domain capabilities (what this domain handles)
- Available worker agents (specialists this instance can delegate to)
- Communication protocols (how to report to Master)
- Skill reference (domain-specific orchestration patterns)

**State Transition**: New instance starts in "initializing" state, transitions to "active" when ready to accept tasks.

---

## 3. Instance Identification Patterns

### Instance ID Format

**Pattern**: `{domain}-orchestrator-{number}`

**Domain Types**:
- `mcp` - MCP domain orchestrator
- `frontend` - Frontend domain orchestrator
- `backend` - Backend domain orchestrator
- `infrastructure` - Infrastructure domain orchestrator
- `quality` - Quality domain orchestrator

### Instance ID Examples

| Domain | Instance | ID |
|--------|----------|-----|
| MCP | First (original) | `mcp-orchestrator-1` |
| MCP | Second (spawned) | `mcp-orchestrator-2` |
| MCP | Third (spawned) | `mcp-orchestrator-3` |
| Frontend | First | `frontend-orchestrator-1` |
| Frontend | Second (spawned) | `frontend-orchestrator-2` |
| Backend | First | `backend-orchestrator-1` |
| Infrastructure | First | `infrastructure-orchestrator-1` |
| Quality | First | `quality-orchestrator-1` |

### Numbering Rules

**Sequential numbering**: Start at 1, increment for each spawn within domain.

**No ID reuse**: Instance IDs never reused, even after instance shutdown.
- If `mcp-orchestrator-2` shuts down, next spawn is `mcp-orchestrator-4` (not 2)
- Prevents confusion and enables historical tracking

**Per-domain sequences**: Each domain has independent numbering.
- MCP can have instances 1, 2, 3
- Frontend can have instances 1, 2, 3
- No collision between domains

### Instance Number Tracking

```python
function get_next_instance_number(domain_type):
    """Get next sequential instance number for domain."""
    # Query historical spawn records (including shutdown instances)
    all_instances = get_all_instances_ever_spawned(domain_type)

    if not all_instances:
        return 1  # First instance

    # Extract highest instance number used
    max_number = max(inst.instance_number for inst in all_instances)

    return max_number + 1
```

---

## 4. Workspace Creation for Instances

### Workspace ID Format

**Pattern**: `{domain}-domain-{instance-number}`

**Examples**:
- `mcp-domain-001` (first MCP instance)
- `mcp-domain-002` (second MCP instance, spawned)
- `frontend-domain-001` (first frontend instance)
- `backend-domain-003` (third backend instance)

### Workspace Hierarchy

```
Master Workspace (master-001)
├── MCP Domain Workspace #1 (mcp-domain-001)
│   └── MCP Worker Agents
├── MCP Domain Workspace #2 (mcp-domain-002) [spawned instance]
│   └── MCP Worker Agents
├── Frontend Domain Workspace (frontend-domain-001)
│   └── Frontend Worker Agents
└── Backend Domain Workspace (backend-domain-001)
    └── Backend Worker Agents
```

### Workspace Properties

Each spawned instance workspace includes:

**Identification**:
- Workspace ID: Unique identifier (e.g., `mcp-domain-002`)
- Instance ID: Associated orchestrator instance (e.g., `mcp-orchestrator-2`)
- Domain type: Domain category (e.g., `mcp`)

**Hierarchy**:
- Parent workspace: Master Orchestrator workspace (e.g., `master-001`)
- Child workspaces: Worker agent workspaces (created on demand)

**Metadata**:
```json
{
    "workspace_id": "mcp-domain-002",
    "instance_id": "mcp-orchestrator-2",
    "domain_type": "mcp",
    "instance_number": 2,
    "spawn_timestamp": "2026-02-04T14:30:00Z",
    "spawn_severity": 7,
    "parent_workspace": "master-001",
    "active_task_count": 0,
    "state": "initializing"
}
```

**Isolation**:
- No shared state with other instances
- Independent task queue
- Separate context and memory
- Communication only through defined protocols

---

## 5. Instance Lifecycle States

### State Definitions

**INITIALIZING**:
- Just spawned, setting up context
- Loading domain capabilities and worker agent registry
- Establishing communication with Master Orchestrator
- Not yet accepting tasks
- Typical duration: 5-15 seconds

**ACTIVE**:
- Accepting and delegating tasks
- Reporting metrics to Master Orchestrator
- Coordinating worker agents
- Normal operational state
- Can transition to DRAINING when load decreases

**DRAINING**:
- No new tasks accepted
- Completing existing tasks
- Preparing for graceful shutdown
- Continues reporting metrics until all tasks complete
- Transition to SHUTDOWN when task queue empty

**SHUTDOWN**:
- All tasks complete
- Workspace archived for debugging/analysis
- Instance terminated and removed from load balancer
- Resources released
- State recorded in historical logs

### State Transitions

```
INITIALIZING → ACTIVE
    Trigger: Initialization complete, ready to accept tasks

ACTIVE → DRAINING
    Trigger: Load decreased, instance selected for shutdown

DRAINING → SHUTDOWN
    Trigger: All active tasks completed

ACTIVE → SHUTDOWN (emergency)
    Trigger: Instance failure or manual shutdown request
```

### State Tracking

Master Orchestrator maintains state for each instance:

```python
instance_registry = {
    "mcp-orchestrator-1": {
        "state": "active",
        "workspace_id": "mcp-domain-001",
        "spawn_time": "2026-02-04T14:00:00Z",
        "active_tasks": 12,
        "last_update": "2026-02-04T14:35:00Z"
    },
    "mcp-orchestrator-2": {
        "state": "active",
        "workspace_id": "mcp-domain-002",
        "spawn_time": "2026-02-04T14:30:00Z",
        "active_tasks": 8,
        "last_update": "2026-02-04T14:35:00Z"
    },
    "frontend-orchestrator-1": {
        "state": "draining",
        "workspace_id": "frontend-domain-001",
        "spawn_time": "2026-02-04T13:00:00Z",
        "active_tasks": 2,
        "last_update": "2026-02-04T14:35:00Z"
    }
}
```

---

## 6. Context Provision to New Instance

### Context Package

New instance receives comprehensive context to begin coordination immediately:

**1. Domain Type and Responsibilities**:
```json
{
    "domain": "mcp",
    "responsibilities": [
        "Coordinate MCP specialist agents",
        "Handle external integration requests",
        "Manage API connections and authentication",
        "Delegate to email, calendar, database specialists"
    ],
    "scope": "External system integrations and data operations"
}
```

**2. Available Worker Agents**:
```json
{
    "available_agents": [
        {"id": "email-agent", "capabilities": ["send_email", "read_email", "search_email"]},
        {"id": "calendar-agent", "capabilities": ["create_event", "list_events", "update_event"]},
        {"id": "database-agent", "capabilities": ["query", "insert", "update", "delete"]},
        {"id": "weather-agent", "capabilities": ["current_weather", "forecast"]}
    ]
}
```

**3. Current Domain-Wide State**:
```json
{
    "other_instances": [
        {
            "id": "mcp-orchestrator-1",
            "active_tasks": 12,
            "state": "active",
            "load": 0.8
        }
    ],
    "aggregate_load": 0.8,
    "recent_task_types": ["email_operations", "calendar_events", "database_queries"]
}
```

**4. Master Orchestrator Communication Protocols**:
```json
{
    "master_workspace": "master-001",
    "communication_channels": {
        "status_updates": "report every 30 seconds or on task completion",
        "task_delegation": "receive tasks via workspace queue",
        "results": "report to Master via workspace result channel"
    },
    "reporting_requirements": {
        "metrics": ["queue_depth", "response_time", "active_agents"],
        "frequency": "30 seconds"
    }
}
```

**5. Workspace Sharing and Task Management**:
- Integration with workspace task comments system
- Shared workspace metadata access
- Task state synchronization across instances
- Result aggregation protocols

**6. Domain-Specific Skill Reference**:
```json
{
    "skill_path": ".claude/skills/mcp-domain-orchestrator/skill.md",
    "resources": [
        "mcp-coordination-patterns.md",
        "specialist-selection.md",
        "error-handling.md"
    ]
}
```

### Context Usage

New instance uses context to:
- Understand its role and responsibilities
- Know which worker agents it can delegate to
- Coordinate with other instances of same domain
- Report status to Master Orchestrator correctly
- Follow established communication protocols
- Access domain-specific orchestration patterns

---

## 7. Max Instances & Resource Limits

### Default Maximum Instances

**Per domain**: 5 instances maximum

**Rationale**:
- Balance scalability with coordination overhead
- Beyond 5 instances, marginal benefit diminishes
- Coordination complexity increases with instance count
- Hard limit prevents runaway spawning

### Domain-Specific Limits

Configurable per domain if workload characteristics differ:

```python
max_instances_config = {
    "mcp": 5,           # High variability, many specialists
    "frontend": 3,      # Lower parallelism, more interdependencies
    "backend": 5,       # High parallelism for API requests
    "infrastructure": 2,  # Fewer concurrent ops tasks
    "quality": 3        # Testing can parallelize moderately
}
```

### Maximum Capacity Handling

When domain reaches maximum instances:

**Detection**:
```python
if get_instance_count(domain_type) >= get_max_instances(domain_type):
    # At capacity - cannot spawn
    log_warning(f"Domain {domain_type} at maximum capacity")
```

**Actions**:
1. Log warning with severity level
2. Alert system administrators for manual intervention
3. Continue monitoring (bottleneck persists in metrics)
4. Consider graceful degradation:
   - Reject low-priority tasks
   - Queue tasks with longer timeouts
   - Notify user of capacity constraints

### Resource Considerations

Maximum instances limited by:
- **Workspace overhead**: Each instance requires dedicated workspace
- **Communication overhead**: More instances = more status updates to aggregate
- **Context switching**: Master must track and coordinate multiple instances
- **Load balancer complexity**: More instances = more routing decisions

---

## 8. Graceful Instance Shutdown

### Shutdown Triggers

Instances shut down when:
- **Load decreased**: Domain no longer requires multiple instances
- **Instance idle**: No tasks for 10+ minutes
- **Low aggregate load**: Domain aggregate load below threshold
- **Manual shutdown**: Administrator-initiated shutdown

### Shutdown Threshold

Shutdown candidate criteria:
- Instance has been idle for 10+ minutes (no active tasks)
- Domain aggregate load is low (below 50% of capacity)
- At least 2 instances of domain type exist (never shutdown last instance)

### Shutdown Process

```python
function graceful_instance_shutdown(instance_id):
    """
    Gracefully shut down domain orchestrator instance.

    Args:
        instance_id: Instance to shutdown (e.g., "mcp-orchestrator-2")
    """
    # Step 1: Mark instance as "draining" (no new tasks)
    update_instance_state(instance_id, "draining")
    log(f"Instance {instance_id} entering drain state")

    # Step 2: Remove from load balancer pool
    # No new tasks will be routed to this instance
    load_balancer.remove_instance(instance_id)

    # Step 3: Wait for active tasks to complete
    while has_active_tasks(instance_id):
        # Check every 5 seconds
        time.sleep(5)

        # Timeout after 5 minutes (force shutdown if tasks hung)
        if time_in_drain_state(instance_id) > 300:
            log_warning(f"Instance {instance_id} drain timeout - forcing shutdown")
            break

    # Step 4: Collect final metrics and results
    final_metrics = collect_final_metrics(instance_id)
    task_results = collect_remaining_results(instance_id)

    # Step 5: Archive workspace (for debugging/analysis)
    workspace_id = get_workspace_id(instance_id)
    archive_workspace(
        workspace_id=workspace_id,
        final_metrics=final_metrics,
        task_results=task_results,
        shutdown_reason="load_decreased",
        shutdown_time=get_current_timestamp()
    )

    # Step 6: Terminate instance
    terminate_instance(instance_id)

    # Step 7: Remove from instance registry
    unregister_instance(instance_id)

    # Step 8: Update instance state to shutdown
    update_instance_state(instance_id, "shutdown")

    # Step 9: Log successful shutdown
    log(f"Instance {instance_id} shutdown complete")
```

### Shutdown Selection Algorithm

When multiple instances exist and load allows shutdown:

```python
function select_instance_for_shutdown(domain_type):
    """Select best instance to shutdown when load decreased."""
    instances = get_active_instances(domain_type)

    # Must have at least 2 instances (never shutdown last one)
    if len(instances) < 2:
        return None

    # Find instance with lowest current load
    instance_loads = [(inst, get_current_load(inst)) for inst in instances]
    instance_loads.sort(key=lambda x: x[1])  # Sort by load (lowest first)

    # Select lowest load instance as shutdown candidate
    candidate = instance_loads[0][0]

    # Verify candidate is truly idle (< 10% capacity)
    if get_current_load(candidate) < 0.1:
        return candidate

    return None  # No idle instances found
```

### Preservation of Results

**Critical**: Before shutdown, preserve all task results and metrics:
- Final metric snapshot (queue depth, response time, agents)
- Completed task results not yet reported to Master
- Partial results from draining tasks
- Workspace state for historical analysis

**Archive Structure**:
```json
{
    "instance_id": "mcp-orchestrator-2",
    "workspace_id": "mcp-domain-002",
    "shutdown_time": "2026-02-04T15:00:00Z",
    "shutdown_reason": "load_decreased",
    "lifetime": "30 minutes",
    "tasks_completed": 45,
    "final_metrics": {
        "queue_depth": 0,
        "avg_response_time": 12,
        "active_agents": 0
    }
}
```

---

*Spawning triggered by @./bottleneck-detection.md severity scores*

*Load balancing across spawned instances handled by @./load-balancing.md*
