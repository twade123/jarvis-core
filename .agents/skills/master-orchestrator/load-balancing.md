# Load Balancing Strategies

Distribute tasks across multiple domain orchestrator instances to maximize throughput, minimize wait time, and balance load evenly.

---

## 1. Load Balancing Overview

### Purpose

When multiple instances of a domain orchestrator exist (spawned via @./dynamic-spawning.md), distribute incoming tasks across instances to:
- **Maximize throughput**: All instances working efficiently
- **Minimize wait time**: Tasks assigned to available instances
- **Balance load evenly**: No instance overloaded while others idle
- **Optimize resource usage**: Even distribution across capacity

### Operating Scope

**Per domain type**: Each domain has its own load balancer.
- MCP domain has MCP load balancer (balances across mcp-orchestrator-1, mcp-orchestrator-2, etc.)
- Frontend domain has Frontend load balancer
- Backend domain has Backend load balancer
- Infrastructure domain has Infrastructure load balancer
- Quality domain has Quality load balancer

**No cross-domain balancing**: Load balancers operate independently per domain.

### Strategy Selection

Master Orchestrator selects load balancing strategy based on:
- Task characteristics (complexity, duration, affinity)
- Domain type (different domains have different patterns)
- Current load patterns (uniform vs. variable)
- User hints in task metadata (affinity keys)

### Goals

**Primary**: Minimize task wait time (time from submission to delegation)

**Secondary**: Balance load evenly across instances (prevent hotspots)

**Tertiary**: Optimize for cache locality and context reuse (when applicable)

---

## 2. Round-Robin Strategy

### Algorithm

Distribute tasks evenly across instances in rotating fashion:

```python
function round_robin(domain_type, task):
    """
    Select instance using round-robin rotation.

    Args:
        domain_type: Domain to balance (e.g., "mcp")
        task: Task to assign

    Returns:
        selected_instance: Instance to receive task
    """
    # Get all active instances for domain
    instances = get_active_instances(domain_type)

    # Single instance - no balancing needed
    if len(instances) == 1:
        return instances[0]

    # Get current round-robin index for this domain
    current_index = get_round_robin_index(domain_type)

    # Select instance at current index
    selected_instance = instances[current_index]

    # Increment index for next task (wrap around at end)
    next_index = (current_index + 1) % len(instances)
    set_round_robin_index(domain_type, next_index)

    return selected_instance
```

### Example Execution

**Scenario**: 3 MCP orchestrator instances, 9 tasks arrive

| Task | Current Index | Selected Instance | Next Index |
|------|---------------|-------------------|------------|
| 1    | 0             | mcp-orchestrator-1 | 1 |
| 2    | 1             | mcp-orchestrator-2 | 2 |
| 3    | 2             | mcp-orchestrator-3 | 0 |
| 4    | 0             | mcp-orchestrator-1 | 1 |
| 5    | 1             | mcp-orchestrator-2 | 2 |
| 6    | 2             | mcp-orchestrator-3 | 0 |
| 7    | 0             | mcp-orchestrator-1 | 1 |
| 8    | 1             | mcp-orchestrator-2 | 2 |
| 9    | 2             | mcp-orchestrator-3 | 0 |

**Result**: Each instance receives exactly 3 tasks (perfect distribution)

### Use Case

**Best for**: Tasks of similar complexity and duration
- All tasks take approximately same time to complete
- No significant variance in resource requirements
- Example: MCP domain with mixed email, calendar, weather tasks (all roughly equal complexity)

### Advantages

- **Simple**: Minimal logic, easy to implement
- **Predictable**: Always know which instance gets next task
- **No overhead**: No real-time metrics required
- **Fair**: Every instance gets equal share over time

### Disadvantages

- **Ignores load**: Doesn't account for instance load differences
- **No adaptation**: Doesn't adjust for varying task complexity
- **Potential imbalance**: If tasks have different durations, instances finish at different times

---

## 3. Least-Loaded Strategy

### Algorithm

Route tasks to instance with lowest current load:

```python
function least_loaded(domain_type, task):
    """
    Select instance with lowest current load.

    Args:
        domain_type: Domain to balance (e.g., "backend")
        task: Task to assign

    Returns:
        selected_instance: Instance with lowest load
    """
    # Get all active instances for domain
    instances = get_active_instances(domain_type)

    # Single instance - no balancing needed
    if len(instances) == 1:
        return instances[0]

    # Calculate current load for each instance
    instance_loads = [(inst, get_current_load(inst)) for inst in instances]

    # Sort by load (lowest first)
    instance_loads.sort(key=lambda x: x[1])

    # Select instance with lowest load
    selected_instance = instance_loads[0][0]

    return selected_instance
```

### Load Calculation

**Formula**: `current_load = (active_agents / max_agents) + (queue_depth / 10)`

**Components**:
- **active_agents / max_agents**: Agent utilization ratio (0.0 to 1.0)
- **queue_depth / 10**: Normalized queue pressure (0.0 to 2.0+)

**Range**:
- **0.0**: Idle (no agents active, no queue)
- **1.0**: Moderate load (100% agent utilization OR queue of 10)
- **2.0+**: Overloaded (full agent utilization + significant queue)

**Lower is better**: Instance with lowest score receives task

### Load Calculation Examples

| Active Agents | Max Agents | Queue Depth | Load Score | Interpretation |
|---------------|------------|-------------|------------|----------------|
| 0 | 15 | 0 | 0.0 | Idle |
| 5 | 15 | 2 | 0.53 | Low load |
| 10 | 15 | 5 | 1.17 | Moderate load |
| 15 | 15 | 8 | 1.80 | High load |
| 15 | 15 | 15 | 2.50 | Overloaded |

### Example Execution

**Scenario**: 3 backend instances with varying loads

| Instance | Active Agents | Queue | Load Score |
|----------|---------------|-------|------------|
| backend-orchestrator-1 | 12 | 3 | 1.10 |
| backend-orchestrator-2 | 5 | 1 | 0.43 |
| backend-orchestrator-3 | 10 | 7 | 1.37 |

**Task arrives**: Algorithm selects `backend-orchestrator-2` (lowest load 0.43)

**After assignment**: Backend-2 load increases to 0.50, next task may go elsewhere

### Use Case

**Best for**: Tasks with varying complexity and duration
- Some tasks complete in seconds, others take minutes
- Resource requirements vary significantly
- Example: Backend domain with mix of simple queries and complex migrations

### Advantages

- **Balances actual load**: Accounts for real-time instance capacity
- **Adaptive**: Automatically adjusts to varying task complexity
- **Prevents hotspots**: Avoids overloading busy instances
- **Optimizes throughput**: Keeps all instances working efficiently

### Disadvantages

- **Requires real-time tracking**: Must maintain load metrics for each instance
- **Overhead**: Load calculation on every task assignment
- **Metric lag**: Load metrics may be slightly out of sync

---

## 4. Task Affinity Strategy

### Algorithm

Route related tasks to same instance for context reuse:

```python
function task_affinity(domain_type, task):
    """
    Select instance using task affinity (route related tasks together).

    Args:
        domain_type: Domain to balance
        task: Task to assign (may include affinity_key)

    Returns:
        selected_instance: Instance for this task
    """
    # Get all active instances for domain
    instances = get_active_instances(domain_type)

    # Single instance - no balancing needed
    if len(instances) == 1:
        return instances[0]

    # Check if task has affinity hint (related to previous task)
    if task.affinity_key:
        # Route to same instance as previous related task
        previous_instance = get_affinity_mapping(task.affinity_key)

        if previous_instance and previous_instance.is_active():
            # Check if instance is not overloaded
            if get_current_load(previous_instance) < 1.5:
                # Use previous instance (context locality)
                return previous_instance

            # Previous instance overloaded - reassign affinity

    # No affinity or previous instance unavailable
    # Fall back to round-robin for fair distribution
    return round_robin(domain_type, task)
```

### Affinity Key Examples

**User ID**: All tasks for user X go to same instance
```json
{
    "task": "process_user_data",
    "affinity_key": "user-12345",
    "reason": "Multiple operations on same user account"
}
```

**Project ID**: All tasks for project Y go to same instance
```json
{
    "task": "build_component",
    "affinity_key": "project-dashboard",
    "reason": "All components for dashboard related"
}
```

**Feature ID**: All tasks for feature Z go to same instance
```json
{
    "task": "test_authentication",
    "affinity_key": "feature-auth",
    "reason": "Sequential testing of auth flow"
}
```

### Affinity Mapping Storage

Master Orchestrator maintains affinity mappings:

```python
affinity_mappings = {
    "user-12345": "backend-orchestrator-1",
    "project-dashboard": "frontend-orchestrator-2",
    "feature-auth": "backend-orchestrator-1"
}
```

**Mapping lifecycle**:
- Created on first task with affinity key
- Updated if instance becomes overloaded (reassignment)
- Expired after 10 minutes of inactivity (cleanup)

### Use Case

**Best for**: Tasks that benefit from shared context/state
- Sequential operations on same entity
- Multiple related tasks requiring consistent state
- Example: Frontend domain working on single project (all components related)

### Advantages

- **Reduces context switching**: Same instance handles related tasks
- **Improves cache locality**: Instance may cache data for related tasks
- **Maintains consistency**: Related operations coordinated by same instance
- **Better performance**: Avoid redundant setup for related tasks

### Disadvantages

- **Can create imbalance**: If affinity keys skewed, some instances overloaded
- **Requires affinity hints**: Tasks must include affinity keys (not always available)
- **Complexity**: Tracking affinity mappings adds overhead

### Affinity Overload Handling

If affinity instance becomes overloaded:

```python
# Check if affinity instance is overloaded
if get_current_load(affinity_instance) >= 1.5:
    # Reassign affinity to least-loaded instance
    new_instance = least_loaded(domain_type, task)
    update_affinity_mapping(task.affinity_key, new_instance)
    return new_instance
```

**Rationale**: Preserve system responsiveness over strict affinity

---

## 5. Strategy Selection Algorithm

### Selection Logic

Master Orchestrator chooses strategy per task based on hints and domain characteristics:

```python
function select_load_balancing_strategy(domain_type, task):
    """
    Choose best load balancing strategy for task.

    Args:
        domain_type: Domain to balance
        task: Task to assign (with metadata)

    Returns:
        strategy: ROUND_ROBIN, LEAST_LOADED, or TASK_AFFINITY
    """
    # Priority 1: Check task metadata for explicit affinity hint
    if task.has_affinity_key():
        # Task indicates it's related to previous task
        return TASK_AFFINITY

    # Priority 2: Check domain type default strategy
    if domain_type == "mcp":
        # MCP tasks typically independent (email, calendar, weather)
        return ROUND_ROBIN

    if domain_type in ["frontend", "backend"]:
        # Development tasks may have complex interdependencies
        # Use affinity to group related work
        return TASK_AFFINITY

    if domain_type in ["infrastructure", "quality"]:
        # Ops tasks may vary significantly in duration
        # Use least-loaded to balance varying complexity
        return LEAST_LOADED

    # Default fallback: Round-robin (simplest, most predictable)
    return ROUND_ROBIN
```

### Strategy Selection Table

| Domain | Default Strategy | Rationale |
|--------|------------------|-----------|
| MCP | Round-Robin | Independent tasks (email, calendar, weather) with similar complexity |
| Frontend | Task Affinity | Related components for same project benefit from context locality |
| Backend | Task Affinity | API operations on same entities benefit from shared state |
| Infrastructure | Least-Loaded | Deployment tasks vary significantly in duration |
| Quality | Least-Loaded | Testing complexity varies (unit tests vs. integration tests) |

### Override Mechanisms

**Explicit task hint**: Task metadata can override domain default
```json
{
    "task": "send_bulk_emails",
    "domain": "mcp",
    "load_balancing_hint": "least_loaded",
    "reason": "Bulk operation - use least loaded to avoid overwhelming single instance"
}
```

**Dynamic adjustment**: Master can change strategy based on observed patterns
```python
# If round-robin causing imbalance, switch to least-loaded
if detect_load_imbalance(domain_type):
    override_strategy(domain_type, LEAST_LOADED)
```

---

## 6. Load Balancer State Management

### State Components

Load balancer maintains per-domain state:

**1. Instance Registry**: Active instances for each domain
```python
instance_registry = {
    "mcp": ["mcp-orchestrator-1", "mcp-orchestrator-2"],
    "frontend": ["frontend-orchestrator-1"],
    "backend": ["backend-orchestrator-1", "backend-orchestrator-2"]
}
```

**2. Round-Robin Indices**: Current index per domain
```python
round_robin_indices = {
    "mcp": 0,
    "frontend": 0,
    "backend": 1
}
```

**3. Affinity Mappings**: Affinity key to instance mappings
```python
affinity_mappings = {
    "user-12345": "backend-orchestrator-1",
    "project-dashboard": "frontend-orchestrator-1"
}
```

**4. Load Metrics**: Current load per instance
```python
load_metrics = {
    "mcp-orchestrator-1": 0.75,
    "mcp-orchestrator-2": 0.45,
    "frontend-orchestrator-1": 0.30
}
```

### State Update Triggers

**Instance spawned**: Add to registry
```python
def on_instance_spawned(domain_type, instance_id):
    instance_registry[domain_type].append(instance_id)
    load_metrics[instance_id] = 0.0
```

**Instance shutdown**: Remove from registry
```python
def on_instance_shutdown(domain_type, instance_id):
    instance_registry[domain_type].remove(instance_id)
    del load_metrics[instance_id]
    # Clean up affinity mappings pointing to this instance
    cleanup_affinity_mappings(instance_id)
```

**Task assigned**: Update load and affinity
```python
def on_task_assigned(instance_id, task):
    # Update load metric
    load_metrics[instance_id] += calculate_task_load(task)
    # Update affinity mapping if task has affinity key
    if task.affinity_key:
        affinity_mappings[task.affinity_key] = instance_id
```

**Task completed**: Update load
```python
def on_task_completed(instance_id, task):
    # Decrease load metric
    load_metrics[instance_id] -= calculate_task_load(task)
    # Ensure non-negative
    load_metrics[instance_id] = max(0.0, load_metrics[instance_id])
```

### State Persistence

**In-memory**: All state maintained in-memory for fast access

**Periodic sync**: State synced to workspace metadata every 30 seconds

**Recovery**: On restart, rebuild state from workspace metadata and active instances

---

## 7. Handling Instance Failures During Load Balancing

### Failure Detection

**Scenario**: Selected instance becomes unavailable (crashed, unresponsive) after selection but before task assignment.

**Detection mechanisms**:
- Task assignment timeout (no acknowledgment within 5 seconds)
- Instance health check failure
- Workspace communication error

### Failure Handling

```python
function handle_instance_failure(failed_instance_id, task, domain_type):
    """
    Handle instance failure during task assignment.

    Args:
        failed_instance_id: Instance that failed
        task: Task that was being assigned
        domain_type: Domain of failed instance
    """
    # Step 1: Remove from load balancer pool
    remove_instance_from_pool(failed_instance_id)
    log_error(f"Instance {failed_instance_id} failed - removing from pool")

    # Step 2: Mark instance as failed in registry
    mark_instance_failed(failed_instance_id)

    # Step 3: Clean up affinity mappings pointing to failed instance
    cleanup_affinity_mappings(failed_instance_id)

    # Step 4: Re-run load balancing algorithm (exclude failed instance)
    instances = get_active_instances(domain_type)
    instances.remove(failed_instance_id)

    if not instances:
        # No instances left - spawn new one immediately
        spawn_domain_orchestrator(domain_type, severity=10)
        # Queue task until new instance ready
        queue_task_for_retry(task)
        return

    # Step 5: Assign task to newly selected instance
    strategy = select_load_balancing_strategy(domain_type, task)
    new_instance = apply_strategy(strategy, domain_type, task, instances)
    assign_task(new_instance, task)

    # Step 6: Log rebalancing event
    log(f"Task reassigned from {failed_instance_id} to {new_instance}")

    # Step 7: Consider spawning replacement instance
    if get_instance_count(domain_type) < get_min_instances(domain_type):
        spawn_domain_orchestrator(domain_type, severity=5)
```

### Failure Recovery

**Automatic recovery**: System automatically handles instance failures without user intervention

**Replacement spawning**: If instance count drops below minimum, spawn replacement

**Task retry**: Failed tasks automatically retried on different instance

**Alerting**: System administrators notified of instance failures for investigation

---

## 8. Performance Optimization

### Optimization Techniques

**1. Cache Instance Lists**

Don't query registry on every task assignment:
```python
# Bad: Query registry every time
def select_instance(domain_type, task):
    instances = query_instance_registry(domain_type)  # Expensive
    return round_robin(instances)

# Good: Cache instance list, refresh periodically
instance_cache = {}
def select_instance(domain_type, task):
    if domain_type not in instance_cache or cache_expired(domain_type):
        instance_cache[domain_type] = query_instance_registry(domain_type)
    return round_robin(instance_cache[domain_type])
```

**Cache invalidation**: Refresh on instance spawn/shutdown events

**2. Lazy Load Calculation**

Only calculate load when using least-loaded strategy:
```python
# Only compute loads if strategy requires it
if strategy == LEAST_LOADED:
    instance_loads = [(inst, get_current_load(inst)) for inst in instances]
else:
    # Round-robin and affinity don't need load calculation
    instance_loads = None
```

**3. Batched Affinity Updates**

Update affinity mappings in bulk rather than per-task:
```python
# Accumulate affinity updates
affinity_update_buffer = []

def on_task_assigned(instance_id, task):
    if task.affinity_key:
        affinity_update_buffer.append((task.affinity_key, instance_id))

# Flush buffer every 1 second
def flush_affinity_updates():
    for key, instance in affinity_update_buffer:
        affinity_mappings[key] = instance
    affinity_update_buffer.clear()
```

**4. Periodic Rebalancing**

Detect and correct load imbalances:
```python
function periodic_rebalancing(domain_type):
    """
    Detect load imbalance and reassign future tasks to balance load.

    Runs every 2 minutes per domain.
    """
    instances = get_active_instances(domain_type)

    # Calculate load variance
    loads = [get_current_load(inst) for inst in instances]
    avg_load = sum(loads) / len(loads)
    variance = sum((load - avg_load) ** 2 for load in loads) / len(loads)

    # If variance high (load imbalanced)
    if variance > 0.3:
        # Switch to least-loaded strategy temporarily
        override_strategy(domain_type, LEAST_LOADED, duration=300)
        log(f"Load imbalance detected in {domain_type} - using least-loaded strategy")
```

### Performance Metrics

**Target metrics**:
- Task assignment latency: < 5ms (time to select instance)
- Load query latency: < 10ms (time to fetch instance loads)
- Affinity lookup latency: < 2ms (dictionary lookup)
- Cache hit rate: > 95% (instance list caching)

### Monitoring

Track load balancer performance:
- Assignment latency per strategy
- Cache hit rates
- Rebalancing frequency
- Instance failure rates

---

*Distributes tasks across instances spawned by @./dynamic-spawning.md*

*Uses metrics from @./monitoring-metrics.md for least-loaded strategy*
