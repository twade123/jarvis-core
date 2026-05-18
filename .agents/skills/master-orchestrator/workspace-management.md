# Workspace Management for Master Orchestrator

Comprehensive workspace management system that mirrors orchestrator hierarchy and enables Master to track all orchestrator instances and their activities.

## 1. Workspace Hierarchy Architecture

The workspace hierarchy mirrors the orchestrator hierarchy, providing clean separation and tracking for all orchestrator instances:

```
Master Workspace (ID: master-orchestrator-primary)
├── MCP Domain Workspace #1 (ID: mcp-domain-1)
│   ├── Email Agent Workspace (managed by MCP orchestrator)
│   ├── Calendar Agent Workspace (managed by MCP orchestrator)
│   └── [Additional worker agent workspaces]
├── MCP Domain Workspace #2 (ID: mcp-domain-2) [spawned instance]
│   └── [Worker agent workspaces]
├── Frontend Domain Workspace #1 (ID: frontend-domain-1)
│   ├── React Agent Workspace (managed by Frontend orchestrator)
│   ├── Styling Agent Workspace (managed by Frontend orchestrator)
│   └── [Additional worker agent workspaces]
├── Backend Domain Workspace #1 (ID: backend-domain-1)
│   ├── API Agent Workspace (managed by Backend orchestrator)
│   ├── Database Agent Workspace (managed by Backend orchestrator)
│   └── [Additional worker agent workspaces]
├── Infrastructure Domain Workspace #1 (ID: infrastructure-domain-1)
│   └── [Worker agent workspaces]
├── Quality Domain Workspace #1 (ID: quality-domain-1)
│   └── [Worker agent workspaces]
└── [Additional domain workspaces as spawned]
```

### Hierarchy Principles

1. **Master Workspace is root**: Only one Master workspace exists (`master-orchestrator-primary`), serving as the single parent for all domain orchestrator workspaces
2. **Each domain orchestrator instance has dedicated child workspace**: When Master spawns a domain orchestrator, it simultaneously creates a dedicated workspace
3. **Worker agents create workspaces under their domain orchestrator parent**: Domain orchestrators manage their worker agent workspaces, not Master
4. **Communication flows along hierarchy edges only**: Master ↔ Domain orchestrator, Domain orchestrator ↔ Worker agents (no cross-domain direct communication)

This hierarchical structure enables:
- Clean tracking of all orchestrator instances
- Isolation between domain orchestrators (no interference)
- Unified monitoring through Master's view of all child workspaces
- Scalable architecture (each domain can spawn multiple instances)

## 2. Workspace Creation Protocol

When Master Orchestrator spawns a new domain orchestrator instance, it must create the corresponding workspace:

```python
function create_domain_workspace(domain_type, instance_number):
  """
  Create a workspace for a newly spawned domain orchestrator instance.

  Args:
    domain_type: One of "mcp", "frontend", "backend", "infrastructure", "quality"
    instance_number: Sequential instance number (1, 2, 3, ...)

  Returns:
    workspace_id: Unique identifier for the created workspace
  """
  # Generate workspace ID using standard naming convention
  workspace_id = f"{domain_type}-domain-{instance_number}"

  # Create workspace with comprehensive metadata
  workspace = create_workspace(
    id=workspace_id,
    name=f"{domain_type.title()} Domain Orchestrator #{instance_number}",
    type="domain-orchestrator",
    parent_id="master-orchestrator-primary",
    metadata={
      "domain_type": domain_type,
      "instance_number": instance_number,
      "spawn_timestamp": current_timestamp(),
      "orchestrator_version": get_skill_version(),
      "status": "active",
      "spawned_due_to": "bottleneck_detection",  # or "initial_request"
      "load_balancer_strategy": get_load_balancer_strategy(domain_type)
    }
  )

  # Register workspace in master's tracking registry
  register_workspace(workspace_id, workspace)

  # Set up workspace sharing with master (enables monitoring)
  configure_workspace_sharing(
    workspace_id=workspace_id,
    parent_id="master-orchestrator-primary",
    sharing_level="full"  # Master sees all domain orchestrator communication
  )

  # Initialize task tracking for this workspace
  initialize_task_tracking(workspace_id)

  # Log workspace creation for audit trail
  log_workspace_event(
    workspace_id=workspace_id,
    event="created",
    details={"domain": domain_type, "instance": instance_number}
  )

  return workspace_id
```

### Creation Triggers

Workspaces are created in these scenarios:

1. **Initial request processing**: User request requires a domain orchestrator - create first instance (e.g., `mcp-domain-1`)
2. **Bottleneck detection**: Existing orchestrator overloaded - spawn additional instance (e.g., `mcp-domain-2`)
3. **Manual spawn request**: User or system explicitly requests additional capacity

Workspace creation happens **atomically** with orchestrator spawning to ensure every orchestrator has a corresponding workspace.

## 3. Workspace ID Naming Conventions

Consistent naming conventions enable predictable workspace identification and tracking:

### Master Workspace
- **ID**: `master-orchestrator-primary` (fixed, always exists)
- **Purpose**: Root workspace for Master Orchestrator coordination activities

### Domain Orchestrator Workspaces
- **Format**: `{domain}-domain-{number}`
- **Domain types**: `mcp`, `frontend`, `backend`, `infrastructure`, `quality`
- **Number**: Sequential starting from 1 (increments with each spawn)

### Examples
- `mcp-domain-1` - First MCP orchestrator instance
- `mcp-domain-2` - Second MCP orchestrator instance (spawned due to bottleneck)
- `frontend-domain-1` - First frontend orchestrator
- `frontend-domain-3` - Third frontend orchestrator (if spawned)
- `backend-domain-1` - First backend orchestrator
- `infrastructure-domain-2` - Second infrastructure orchestrator
- `quality-domain-1` - First quality orchestrator

### Worker Agent Workspaces
- **Managed by domain orchestrators** (not Master)
- **Format**: Domain orchestrators choose their own naming convention
- **Examples**: `mcp-domain-1-email-agent`, `frontend-domain-1-react-agent`
- Master does not directly track worker agent workspace IDs

## 4. Workspace Tracking & Registry

Master Orchestrator maintains comprehensive registry of all domain orchestrator workspaces for efficient lookup and monitoring.

### Primary Registry Structure

```python
workspace_registry = {
  "master-orchestrator-primary": {
    "workspace_object": workspace_ref,
    "status": "active",
    "created_at": "2026-02-04T10:00:00Z"
  },
  "mcp-domain-1": {
    "workspace_object": workspace_ref,
    "status": "active",
    "spawn_time": "2026-02-04T10:05:00Z",
    "domain_type": "mcp",
    "instance_number": 1,
    "last_activity": "2026-02-04T10:30:00Z",
    "active_task_count": 5,
    "orchestrator_status": "healthy"
  },
  "mcp-domain-2": {
    "workspace_object": workspace_ref,
    "status": "active",
    "spawn_time": "2026-02-04T10:25:00Z",
    "domain_type": "mcp",
    "instance_number": 2,
    "last_activity": "2026-02-04T10:29:00Z",
    "active_task_count": 3,
    "orchestrator_status": "healthy"
  },
  "frontend-domain-1": {
    "workspace_object": workspace_ref,
    "status": "active",
    "spawn_time": "2026-02-04T10:10:00Z",
    "domain_type": "frontend",
    "instance_number": 1,
    "last_activity": "2026-02-04T10:28:00Z",
    "active_task_count": 2,
    "orchestrator_status": "healthy"
  }
  # ... additional workspaces
}
```

### Domain-Indexed Lookup

For efficient domain-level operations, maintain secondary index:

```python
domain_workspaces = {
  "mcp": ["mcp-domain-1", "mcp-domain-2"],
  "frontend": ["frontend-domain-1"],
  "backend": ["backend-domain-1"],
  "infrastructure": [],  # No instances spawned yet
  "quality": []  # No instances spawned yet
}
```

### Registry Operations

```python
# Add workspace when spawning
def register_workspace(workspace_id, workspace):
  workspace_registry[workspace_id] = workspace
  domain_type = extract_domain_from_id(workspace_id)
  domain_workspaces[domain_type].append(workspace_id)

# Remove workspace when shutting down
def unregister_workspace(workspace_id):
  workspace_registry[workspace_id]["status"] = "archived"
  domain_type = extract_domain_from_id(workspace_id)
  domain_workspaces[domain_type].remove(workspace_id)

# Get all active workspaces for a domain
def get_domain_workspaces(domain_type):
  return [wid for wid in domain_workspaces[domain_type]
          if workspace_registry[wid]["status"] == "active"]

# Update activity timestamp
def update_workspace_activity(workspace_id):
  workspace_registry[workspace_id]["last_activity"] = current_timestamp()
```

## 5. Workspace Sharing Configuration

Workspace sharing enables Master to monitor all domain orchestrator activities while maintaining isolation between domains.

### Sharing Hierarchy

```
Master Workspace (master-orchestrator-primary)
  ↓ [FULL ACCESS - observer role]
MCP Domain Workspace #1 (mcp-domain-1)
  ↓ [FULL ACCESS - participant role]
Email Agent Workspace
```

### Access Levels

1. **Master → Domain orchestrator workspaces**: **Observer access**
   - Can read all communication in domain workspace
   - Can view task status and agent activities
   - Cannot directly send messages to domain workspace
   - Used for: Progress aggregation, failure detection, bottleneck monitoring

2. **Domain orchestrator → Worker agent workspaces**: **Participant access**
   - Can read and write in worker workspace
   - Can delegate tasks to workers
   - Can receive status updates from workers
   - Used for: Task delegation, worker coordination

3. **Domain orchestrators → Other domain workspaces**: **No access**
   - Domains are isolated from each other
   - Cross-domain communication flows through Master only
   - Prevents interference and maintains clear boundaries

### Configuration Implementation

```python
function configure_workspace_sharing(workspace_id, parent_id, sharing_level):
  """
  Set up workspace sharing between parent (Master) and child (domain orchestrator).

  Uses WorkspaceSharingManager from workspace_task_systems_analysis.md.
  """
  sharing_manager = WorkspaceSharingManager()

  # Create sharing relationship
  share_id = sharing_manager.create_share(
    workspace_id=workspace_id,
    shared_with_workspace_id=parent_id,
    permission_level=sharing_level,  # "full" for Master
    can_view=True,
    can_comment=True,
    can_edit=False  # Master observes but doesn't interfere
  )

  # Store share ID for future reference
  workspace_registry[workspace_id]["share_id"] = share_id

  return share_id
```

### Monitoring Capabilities

With workspace sharing configured, Master can:

1. **Monitor progress across all domains**: Aggregate status from all domain workspaces
2. **Detect failures in child workspaces**: Identify unresponsive orchestrators or failed tasks
3. **Debug cross-domain issues**: View communication flow between domains (through Master as intermediary)
4. **Collect performance metrics**: Track task completion times, bottleneck indicators
5. **Generate unified reports**: Present coherent updates to user based on all domain activities

## 6. Workspace Lifecycle Management

Each workspace progresses through defined lifecycle states:

### Lifecycle States

1. **Initializing**
   - Workspace created, orchestrator spawning
   - No tasks assigned yet
   - Duration: ~5 seconds

2. **Active**
   - Orchestrator operational and processing tasks
   - Workers communicating with orchestrator
   - Tasks being executed
   - Duration: As long as workload exists

3. **Draining**
   - No new tasks being assigned
   - Completing existing work
   - Preparing for shutdown
   - Duration: Until all tasks complete (~1-10 minutes)

4. **Archived**
   - Orchestrator shutdown complete
   - Workspace preserved for analysis
   - No active processing
   - Duration: Permanent (retained for debugging/metrics)

### State Transitions

```python
# Initial spawn
"initializing" -> "active" (when orchestrator confirms ready)

# Graceful shutdown
"active" -> "draining" (when load balancer stops assigning new tasks)
"draining" -> "archived" (when all tasks complete)

# Emergency shutdown
"active" -> "archived" (when orchestrator crashes/fails)
```

### Lifecycle Management Operations

```python
def transition_workspace_state(workspace_id, new_state):
  """Update workspace state and log transition."""
  old_state = workspace_registry[workspace_id]["status"]
  workspace_registry[workspace_id]["status"] = new_state

  log_workspace_event(
    workspace_id=workspace_id,
    event="state_transition",
    details={"from": old_state, "to": new_state}
  )

  # Handle state-specific actions
  if new_state == "draining":
    stop_assigning_tasks(workspace_id)
  elif new_state == "archived":
    cleanup_workspace_resources(workspace_id)
```

## 7. Workspace Metadata Tracking

Each workspace maintains comprehensive metadata for monitoring, debugging, and analysis:

```python
workspace_metadata = {
  # Identity
  "workspace_id": "mcp-domain-2",
  "instance_id": "mcp-orchestrator-instance-2",
  "domain_type": "mcp",
  "instance_number": 2,

  # Timestamps
  "spawn_timestamp": "2026-02-04T10:25:00Z",
  "last_activity_timestamp": "2026-02-04T10:29:00Z",
  "drain_started": None,
  "archived_at": None,

  # Status tracking
  "status": "active",  # initializing, active, draining, archived
  "orchestrator_status": "healthy",  # healthy, degraded, unresponsive
  "active_task_count": 3,
  "completed_task_count": 12,
  "failed_task_count": 1,

  # Performance metrics
  "avg_response_time_ms": 450,
  "queue_depth": 2,
  "throughput_tasks_per_minute": 2.5,

  # Hierarchy
  "parent_workspace_id": "master-orchestrator-primary",
  "child_workspace_ids": ["mcp-domain-2-email-agent", "mcp-domain-2-calendar-agent"],

  # Configuration
  "orchestrator_version": "1.0.0",
  "load_balancer_strategy": "least-loaded",
  "spawned_due_to": "bottleneck_detection",
  "bottleneck_severity_at_spawn": 7
}
```

### Metadata Updates

Master Orchestrator updates metadata continuously:

- **Every 30 seconds**: Collect performance metrics (response time, queue depth, task counts)
- **On task assignment**: Increment `active_task_count`
- **On task completion**: Decrement `active_task_count`, increment `completed_task_count`
- **On task failure**: Increment `failed_task_count`
- **On communication**: Update `last_activity_timestamp`

## 8. Task Integration with Workspace System

Workspaces and tasks are tightly integrated for comprehensive tracking and coordination.

### Task Creation in Domain Workspace

```python
function create_task_in_workspace(workspace_id, task_details):
  """
  Create task in domain orchestrator workspace for tracking.

  Uses TaskManager from workspace_task_systems_analysis.md.
  """
  task_manager = TaskManager()

  task_id = task_manager.create_task(
    workspace_id=workspace_id,
    title=task_details["title"],
    description=task_details["description"],
    assigned_to=task_details["orchestrator_id"],
    priority=task_details["priority"],
    metadata={
      "domain_type": extract_domain_from_id(workspace_id),
      "delegated_by": "master-orchestrator",
      "requires_domains": task_details.get("dependencies", [])
    }
  )

  # Update workspace task count
  workspace_registry[workspace_id]["active_task_count"] += 1

  return task_id
```

### Task Status Aggregation

Master aggregates task status across all domain workspaces:

```python
function aggregate_task_status():
  """
  Collect task status from all active domain workspaces.

  Returns unified view of progress across all domains.
  """
  aggregated_status = {
    "total_tasks": 0,
    "completed_tasks": 0,
    "in_progress_tasks": 0,
    "failed_tasks": 0,
    "by_domain": {}
  }

  for domain_type in domain_workspaces:
    domain_status = {"total": 0, "completed": 0, "in_progress": 0, "failed": 0}

    for workspace_id in get_domain_workspaces(domain_type):
      workspace_meta = workspace_registry[workspace_id]
      domain_status["in_progress"] += workspace_meta["active_task_count"]
      domain_status["completed"] += workspace_meta["completed_task_count"]
      domain_status["failed"] += workspace_meta["failed_task_count"]
      domain_status["total"] += (domain_status["in_progress"] +
                                  domain_status["completed"] +
                                  domain_status["failed"])

    aggregated_status["by_domain"][domain_type] = domain_status
    aggregated_status["total_tasks"] += domain_status["total"]
    aggregated_status["completed_tasks"] += domain_status["completed"]
    aggregated_status["in_progress_tasks"] += domain_status["in_progress"]
    aggregated_status["failed_tasks"] += domain_status["failed"]

  return aggregated_status
```

### Task Comments for Communication

Domain orchestrators communicate with Master through task comments:

```python
function post_domain_update(workspace_id, task_id, message):
  """
  Domain orchestrator posts update to task in its workspace.
  Master reads these updates through workspace sharing.

  Uses WorkspaceTaskCommentManager from workspace_task_systems_analysis.md.
  """
  comment_manager = WorkspaceTaskCommentManager()

  comment_manager.add_comment(
    task_id=task_id,
    workspace_id=workspace_id,
    author=f"{extract_domain_from_id(workspace_id)}-orchestrator",
    content=message,
    metadata={
      "for_master": True,
      "update_type": "progress",  # or "blocker", "question", "completion"
      "timestamp": current_timestamp()
    }
  )
```

Master monitors task comments to detect:
- Progress updates ("API endpoint completed")
- Blockers ("Waiting for Backend data")
- Questions ("Need clarification on requirement")
- Completions ("All tasks finished")

## 9. Workspace Cleanup & Archival

When orchestrator instance is no longer needed, graceful shutdown preserves workspace for analysis.

### Graceful Shutdown Process

```python
function graceful_shutdown_workspace(workspace_id):
  """
  Shut down orchestrator instance and archive its workspace.

  Steps:
  1. Stop accepting new tasks (transition to draining)
  2. Wait for active tasks to complete
  3. Archive workspace (preserve data)
  4. Cleanup resources
  """
  # Step 1: Mark as draining
  transition_workspace_state(workspace_id, "draining")

  # Step 2: Wait for completion (up to 10 minutes)
  timeout = 10 * 60  # 10 minutes in seconds
  start_time = current_time()

  while workspace_registry[workspace_id]["active_task_count"] > 0:
    if (current_time() - start_time) > timeout:
      # Force shutdown if taking too long
      log_warning(f"Workspace {workspace_id} shutdown timed out - forcing")
      break

    sleep(5)  # Check every 5 seconds

  # Step 3: Archive workspace
  transition_workspace_state(workspace_id, "archived")
  workspace_registry[workspace_id]["archived_at"] = current_timestamp()

  # Step 4: Cleanup (remove from active lists)
  domain_type = extract_domain_from_id(workspace_id)
  domain_workspaces[domain_type].remove(workspace_id)

  # Preserve metadata and data (don't delete)
  log_workspace_event(
    workspace_id=workspace_id,
    event="archived",
    details={"reason": "load_decreased", "tasks_completed": workspace_registry[workspace_id]["completed_task_count"]}
  )
```

### Archival Retention

Archived workspaces are retained permanently for:

1. **Performance analysis**: Was this instance efficient? Did it handle load well?
2. **Failure investigation**: If tasks failed, what happened in this workspace?
3. **Historical metrics**: Track load patterns over time for capacity planning
4. **Debugging**: Investigate issues by replaying workspace communication history
5. **Learning**: Analyze successful patterns for future optimization

### Archival Storage

```python
archived_workspaces = {
  "mcp-domain-2": {
    "archived_at": "2026-02-04T11:00:00Z",
    "lifetime": "35 minutes",
    "tasks_completed": 12,
    "tasks_failed": 1,
    "avg_response_time": 450,
    "reason_for_shutdown": "load_decreased",
    "data_snapshot": {...}  # Full workspace state at archival
  }
}
```

Master can query archived workspaces for analysis but does not actively monitor them.
