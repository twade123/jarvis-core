# Failure Recovery for Master Orchestrator

Comprehensive failure detection and recovery system enabling Master Orchestrator to handle orchestrator failures, task failures, cross-domain coordination failures, and communication breakdowns.

## 1. Failure Detection Mechanisms

Master Orchestrator continuously monitors for four types of failures:

### Orchestrator Unresponsive

**Indicators:**
- Domain orchestrator doesn't respond to status query within 60 seconds
- No activity in domain workspace for 5+ minutes with active tasks assigned
- Orchestrator process crashed or hung

**Detection Method:**
```python
function detect_unresponsive_orchestrator():
  """
  Poll each domain orchestrator every 30 seconds.
  Mark as unresponsive if no response within 60 seconds.
  """
  for domain_type in ["mcp", "frontend", "backend", "infrastructure", "quality"]:
    for workspace_id in get_active_domain_workspaces(domain_type):
      # Send status query
      response = query_orchestrator_status(workspace_id, timeout=60)

      if response is None:
        # No response - orchestrator may be unresponsive
        mark_unresponsive(workspace_id)
        trigger_recovery_protocol("orchestrator_failure", workspace_id)

      # Also check for activity timeout
      last_activity = workspace_registry[workspace_id]["last_activity_timestamp"]
      active_tasks = workspace_registry[workspace_id]["active_task_count"]

      if active_tasks > 0 and (current_time() - last_activity) > 300:
        # 5+ minutes with no activity but tasks assigned - likely hung
        mark_hung(workspace_id)
        trigger_recovery_protocol("orchestrator_failure", workspace_id)
```

### Task Failure

**Indicators:**
- Domain orchestrator reports task failed with error details
- Worker agent returned error to domain orchestrator
- Task exceeded timeout threshold (default: 30 minutes)

**Detection Method:**
```python
function detect_task_failure():
  """
  Domain orchestrators escalate task failures to Master.
  Master determines recovery action based on error type.
  """
  # Domain orchestrator sends failure notification
  notification = {
    "type": "task_failure",
    "workspace_id": "mcp-domain-1",
    "task_id": "task-123",
    "error_details": {
      "error_type": "worker_error",  # or "timeout", "invalid_input"
      "error_message": "API authentication failed",
      "is_transient": False,
      "requires_research": True
    }
  }

  # Master handles based on error type
  handle_task_failure(
    notification["task_id"],
    notification["workspace_id"],
    notification["error_details"]
  )
```

### Cross-Domain Dependency Failure

**Indicators:**
- Domain B waiting for Domain A output, but Domain A failed or doesn't produce required output
- Task dependency chain broken (upstream task failed)
- Dependency timeout exceeded (task blocked for 10+ minutes)

**Detection Method:**
```python
function detect_cross_domain_failure():
  """
  Monitor task dependency graph for broken dependencies.
  """
  for task in get_all_active_tasks():
    if task.status == "blocked":
      # Check if blocked by dependency
      blocking_task = get_blocking_task(task.id)

      if blocking_task:
        # Check how long blocked
        blocked_duration = current_time() - task.blocked_since

        if blocked_duration > 600:  # 10 minutes
          # Dependency timeout - investigate
          if blocking_task.status == "failed":
            # Upstream failure - propagate or find alternate path
            trigger_recovery_protocol("cross_domain_failure", task.id, blocking_task.id)
          elif blocking_task.status == "stuck":
            # Upstream orchestrator may be hung
            investigate_orchestrator(blocking_task.workspace_id)
```

### Workspace Communication Failure

**Indicators:**
- Master cannot access domain workspace (sharing broken)
- Workspace queries return errors or timeout
- Workspace data corrupted or inaccessible

**Detection Method:**
```python
function detect_workspace_communication_failure():
  """
  Test workspace access during status aggregation.
  """
  for workspace_id in get_all_active_workspaces():
    try:
      # Attempt to access workspace
      workspace_data = access_workspace(workspace_id)

      if workspace_data is None:
        # Access failed - communication issue
        trigger_recovery_protocol("workspace_communication_failure", workspace_id)

    except WorkspaceAccessError as e:
      # Sharing broken or workspace corrupted
      log_error(f"Workspace communication failure: {workspace_id} - {e}")
      trigger_recovery_protocol("workspace_communication_failure", workspace_id)
```

## 2. Failure Classification

Different failure types require different recovery strategies:

### Transient Failures (Network hiccups, temporary overload)

**Characteristics:**
- Short duration (~1-30 seconds)
- Intermittent occurrence
- External causes (network, service availability)

**Recovery Strategy:**
- **Immediate retry** (up to 3 attempts)
- Exponential backoff between retries (1s, 2s, 4s)
- If retry succeeds, continue normally
- If all retries fail, escalate to task-level failure

### Task-Level Failures (Worker agent error, invalid input)

**Characteristics:**
- Worker agent encountered error it cannot handle
- Invalid user input or missing information
- Knowledge gap (worker doesn't know how to perform task)

**Recovery Strategy:**
- Domain orchestrator handles recovery
- If knowledge gap: Trigger research → skill update → retry flow (LEARN-05)
- If invalid input: Master requests clarification from user
- If unrecoverable: Mark task failed, notify user

### Orchestrator-Level Failures (Domain orchestrator crashed/hung)

**Characteristics:**
- Orchestrator process unresponsive
- Workspace activity stopped with active tasks
- Critical failure requiring intervention

**Recovery Strategy:**
- Master spawns replacement orchestrator instance
- Reassign orphaned tasks to replacement or other instances
- Archive failed orchestrator workspace
- Notify user of recovery in progress

### Cross-Domain Failures (Dependency deadlock, coordination failure)

**Characteristics:**
- Multiple domains blocked waiting for each other
- Task dependency chain broken by upstream failure
- Cross-domain communication breakdown

**Recovery Strategy:**
- Master intervenes as coordinator
- Reorder tasks to break deadlock
- Provide alternate path if available
- Propagate failure if unrecoverable

## 3. Recovery Protocol - Orchestrator Failure

When domain orchestrator becomes unresponsive or crashes, Master must recover quickly to minimize disruption:

```python
function handle_orchestrator_failure(failed_instance_id, domain_type):
  """
  Recover from domain orchestrator failure by spawning replacement
  and reassigning orphaned tasks.

  Args:
    failed_instance_id: ID of failed orchestrator instance
    domain_type: Domain of failed orchestrator (mcp, frontend, etc.)

  Returns:
    replacement_id: ID of replacement orchestrator (or None if max instances reached)
  """
  # Step 1: Mark instance as failed
  mark_instance_failed(failed_instance_id)
  failed_workspace_id = get_workspace_id(failed_instance_id)
  workspace_registry[failed_workspace_id]["status"] = "failed"
  workspace_registry[failed_workspace_id]["orchestrator_status"] = "crashed"

  # Step 2: Get tasks that were assigned to failed instance
  orphaned_tasks = get_tasks_for_instance(failed_instance_id)
  log_warning(f"Orchestrator {failed_instance_id} failed - {len(orphaned_tasks)} tasks orphaned")

  # Step 3: Spawn replacement instance (if under max instances)
  replacement_id = spawn_domain_orchestrator(
    domain_type=domain_type,
    severity=10,  # Critical - bypass cooldown
    reason="orchestrator_failure"
  )

  # Step 4: Reassign orphaned tasks
  if replacement_id:
    # Replacement spawned - assign all orphaned tasks to it
    log_info(f"Reassigning {len(orphaned_tasks)} tasks to replacement {replacement_id}")

    for task in orphaned_tasks:
      # Reset task state for retry
      task.status = "pending"
      task.assigned_to = replacement_id
      task.retry_count += 1
      task.retry_reason = "orchestrator_failure"

      assign_task(replacement_id, task)

  else:
    # Max instances reached - distribute across existing instances
    log_warning(f"Max instances reached for {domain_type} - distributing orphaned tasks")

    for task in orphaned_tasks:
      # Use load balancer to select best instance
      instance = load_balancer.select_instance(domain_type, task)

      task.status = "pending"
      task.assigned_to = instance
      task.retry_count += 1
      task.retry_reason = "orchestrator_failure"

      assign_task(instance, task)

  # Step 5: Archive failed workspace (preserve for debugging)
  archive_workspace(failed_workspace_id)

  # Step 6: Notify user through Master → user communication
  notify_user(
    message=f"{domain_type.title()} coordination encountered an issue - recovering now",
    details={
      "failed_instance": failed_instance_id,
      "orphaned_tasks": len(orphaned_tasks),
      "replacement_spawned": replacement_id is not None,
      "recovery_status": "in_progress"
    }
  )

  # Step 7: Monitor replacement for successful startup
  if replacement_id:
    monitor_orchestrator_startup(replacement_id, timeout=60)

  return replacement_id
```

### Orchestrator Failure Edge Cases

**Cascading Failures**: Multiple orchestrators fail simultaneously
- Spawn replacements in priority order (based on task criticality)
- Rate-limit spawning to avoid resource exhaustion
- Notify user of widespread issue if affecting multiple domains

**Repeated Failures**: Replacement orchestrator also fails
- Investigate root cause (system-level issue?)
- Pause domain processing temporarily
- Escalate to user for intervention

## 4. Recovery Protocol - Task Failure

When task fails, Master determines appropriate recovery action based on error type:

```python
function handle_task_failure(task_id, domain_type, error_details):
  """
  Recover from task failure using appropriate strategy for error type.

  Args:
    task_id: ID of failed task
    domain_type: Domain where task was executing
    error_details: Error information from domain orchestrator

  Returns:
    recovery_action: Action taken (retried, learning, clarification_needed, failed)
  """
  task = get_task(task_id)

  # Strategy 1: Retry for transient errors
  if error_details.is_transient():
    # Network error, timeout, temporary service unavailable
    log_info(f"Task {task_id} failed with transient error - retrying")

    task.retry_count += 1

    if task.retry_count <= 3:
      # Retry with exponential backoff
      backoff_seconds = 2 ** task.retry_count  # 2s, 4s, 8s
      schedule_retry(task_id, domain_type, delay=backoff_seconds)
      return "retried"
    else:
      # Exceeded retry limit - mark as failed
      mark_task_failed(task_id, "max_retries_exceeded")
      notify_user(f"Task failed after 3 retries: {error_details.message}")
      return "failed"

  # Strategy 2: Trigger learning flow for knowledge gaps
  if error_details.requires_research():
    # Worker agent doesn't know how to handle this situation
    # Trigger research → skill update → retry flow (LEARN-05)
    log_info(f"Task {task_id} failed due to knowledge gap - triggering learning flow")

    trigger_learning_flow(
      task_id=task_id,
      domain_type=domain_type,
      error_details=error_details
    )

    return "learning"

  # Strategy 3: Request clarification for invalid input
  if error_details.is_invalid_input():
    # User input was invalid or missing required information
    log_info(f"Task {task_id} failed due to invalid input - requesting clarification")

    clarification_request = generate_clarification_request(task, error_details)

    request_user_clarification(
      task=task,
      question=clarification_request,
      error_context=error_details
    )

    # Pause task until clarification received
    task.status = "awaiting_clarification"
    return "clarification_needed"

  # Strategy 4: Mark as failed for unrecoverable errors
  log_error(f"Task {task_id} failed with unrecoverable error: {error_details.message}")
  mark_task_failed(task_id, error_details)
  notify_user(f"Task failed: {error_details.message}")
  return "failed"
```

### Task Failure Recovery with Learning (LEARN-05 Integration)

When task fails due to knowledge gap, trigger automated learning flow:

```python
function trigger_learning_flow(task_id, domain_type, error_details):
  """
  Trigger research → skill update → retry flow for knowledge gaps.

  This implements LEARN-05 requirement: failures trigger learning.
  """
  task = get_task(task_id)

  # Step 1: Capture failure context
  failure_context = {
    "task_id": task_id,
    "task_description": task.description,
    "error_type": error_details.error_type,
    "error_message": error_details.error_message,
    "worker_agent": task.assigned_worker,
    "attempt_number": task.retry_count,
    "timestamp": current_timestamp()
  }

  # Step 2: Master requests domain orchestrator to research solution
  research_request = f"""
  Research how to handle this error:
  - Task: {task.description}
  - Error: {error_details.error_message}
  - Context: {error_details.context}

  Analyze:
  1. What knowledge is missing?
  2. What skill update would prevent this error?
  3. How should the task be completed?
  """

  # Send to domain orchestrator for research
  research_task_id = delegate_to_domain_orchestrator(
    domain_type=domain_type,
    task_type="research",
    request=research_request,
    priority="high"
  )

  # Step 3: Wait for research results
  research_results = wait_for_task_completion(research_task_id, timeout=600)  # 10 minutes

  if research_results.status == "completed":
    # Step 4: Validate proposed skill update
    skill_update = research_results.proposed_skill_update

    if validate_skill_update(skill_update, additive_only=True):
      # Step 5: Apply skill update to domain orchestrator
      apply_skill_update(domain_type, skill_update)

      log_info(f"Applied skill update to {domain_type} orchestrator based on task {task_id} failure")

      # Step 6: Retry original task with updated skill
      task.retry_count += 1
      task.retry_reason = "skill_updated"
      retry_task(task_id, domain_type)

      # Step 7: Monitor retry for success
      retry_result = monitor_task_retry(task_id, timeout=600)

      if retry_result.status == "completed":
        # Success! Learning flow complete
        log_success(f"Task {task_id} succeeded after skill update")
        return "learning_success"
      else:
        # Still failing - escalate to user
        escalate_to_user(task, "skill_update_insufficient")
        return "learning_failed"

    else:
      # Skill update invalid (not additive or overwrites existing)
      log_error(f"Skill update rejected - not additive only")
      escalate_to_user(task, "invalid_skill_update")
      return "learning_failed"

  else:
    # Research failed or timed out
    escalate_to_user(task, "research_failed")
    return "learning_failed"
```

## 5. Recovery Protocol - Cross-Domain Dependency Failure

When cross-domain dependencies fail, Master intervenes as coordinator:

```python
function handle_cross_domain_failure(blocked_task_id, blocking_domain):
  """
  Resolve cross-domain dependency failure through Master coordination.

  Args:
    blocked_task_id: Task that is blocked waiting for dependency
    blocking_domain: Domain that was supposed to provide dependency output

  Returns:
    resolution: How failure was resolved
  """
  blocked_task = get_task(blocked_task_id)
  blocking_task = get_blocking_task(blocked_task_id)

  log_warning(f"Cross-domain failure: Task {blocked_task_id} blocked by {blocking_task.id}")

  # Scenario 1: Blocking task failed
  if blocking_task.status == "failed":
    log_info(f"Blocking task {blocking_task.id} failed - checking for alternate path")

    # Check if alternate path exists
    if alternate_path_exists(blocked_task):
      # Reroute to alternate path
      alternate_path = find_alternate_path(blocked_task)
      reroute_task(blocked_task, alternate_path)

      notify_user(
        message=f"Adjusted plan - using alternate approach for {blocked_task.description}",
        details={"reason": "dependency_failed"}
      )

      return "rerouted"

    else:
      # No alternate path - propagate failure
      propagate_failure(
        task=blocked_task,
        reason="dependency_failed",
        upstream_failure=blocking_task.id
      )

      notify_user(
        message=f"Unable to complete {blocked_task.description} due to dependency failure",
        details={"failed_dependency": blocking_task.description}
      )

      return "propagated_failure"

  # Scenario 2: Blocking orchestrator may be hung
  elif blocking_task.status == "stuck":
    log_warning(f"Blocking orchestrator {blocking_domain} may be hung - investigating")

    # Investigate orchestrator health
    orchestrator_status = investigate_orchestrator(blocking_domain)

    if orchestrator_status == "hung":
      # Trigger orchestrator recovery
      handle_orchestrator_failure(
        failed_instance_id=blocking_task.assigned_to,
        domain_type=blocking_domain
      )

      notify_user(
        message=f"Coordinating {blocked_task.domain} and {blocking_domain} - slight delay",
        details={"reason": "orchestrator_recovery"}
      )

      return "orchestrator_recovered"

  # Scenario 3: Blocking task still in progress, just slow
  elif blocking_task.status == "in_progress":
    blocked_duration = current_time() - blocked_task.blocked_since

    if blocked_duration < 600:
      # Less than 10 minutes - extend timeout
      log_info(f"Extending timeout for blocked task {blocked_task_id}")
      extend_timeout(blocked_task, additional_minutes=10)

      return "timeout_extended"

    else:
      # More than 10 minutes - investigate why so slow
      investigate_slow_task(blocking_task)

      notify_user(
        message=f"Coordinating {blocked_task.domain} and {blocking_domain} - taking longer than expected",
        details={"blocked_duration": f"{blocked_duration // 60} minutes"}
      )

      return "investigating_slowness"

  # Scenario 4: Deadlock detection
  if detect_circular_dependency(blocked_task, blocking_task):
    log_error(f"Circular dependency detected: {blocked_task_id} <-> {blocking_task.id}")

    # Break deadlock by reordering tasks
    break_deadlock(blocked_task, blocking_task)

    notify_user(
      message="Adjusted task order to resolve coordination deadlock",
      details={"tasks": [blocked_task_id, blocking_task.id]}
    )

    return "deadlock_broken"
```

### Cross-Domain Communication Breakdown

When domains cannot communicate, Master acts as intermediary:

```python
function handle_communication_breakdown(domain_a, domain_b):
  """
  Master relays data between domains when direct communication broken.
  """
  # Get data from domain A
  data = query_domain_output(domain_a, task_id)

  # Relay to domain B
  provide_input_to_domain(domain_b, data, source=domain_a)

  log_info(f"Master relaying data from {domain_a} to {domain_b}")
```

## 6. Learning Trigger from Failures (LEARN-05 Requirement)

Master Orchestrator enables continuous improvement by triggering learning from failures:

### Learning Flow Steps

1. **Capture Failure Context**
   - Task details (what was being attempted)
   - Error details (what went wrong)
   - Attempt history (how many retries, what was tried)
   - Environment context (domain, orchestrator instance, timing)

2. **Trigger Orchestrator Research**
   - Master delegates research task to domain orchestrator
   - Domain orchestrator consults:
     - Documentation resources
     - Pattern databases
     - Previous successful similar tasks
     - External references (if available)

3. **Propose Skill Update**
   - Domain orchestrator identifies knowledge gap
   - Proposes specific skill addition or enhancement
   - Skill update must be **additive only** (no overwrites)
   - Includes rationale and expected behavior change

4. **Validate Skill Update**
   - Master validates proposal against rules:
     - Must be additive (no deletion of existing skills)
     - Must not overwrite existing functionality
     - Must be relevant to the failure
     - Must follow Anthropic skills format
   - Reject invalid proposals

5. **Apply Skill Update**
   - Master applies validated skill to domain orchestrator
   - Skill becomes available to all instances of that domain
   - Versioning tracks skill additions over time

6. **Retry Original Task**
   - Master retries original task with updated orchestrator
   - Monitor for success
   - If successful: Learning flow complete, log success
   - If still failing: Escalate to user for guidance

7. **Track Learning Metrics**
   - Success rate of learning flow
   - Common failure patterns that trigger learning
   - Skill additions over time
   - Impact on future task success rates

### Learning Integration Benefits

- **Automated improvement**: System learns without manual intervention
- **Reduced user burden**: Fewer escalations for common issues
- **Knowledge accumulation**: Skills grow more comprehensive over time
- **Failure resilience**: Same error handled automatically next time

## 7. Coordination Failure Resolution

Master resolves coordination failures between domains:

### Deadlock Detection and Resolution

```python
function detect_circular_dependency(task_a, task_b):
  """
  Check if tasks are waiting for each other (deadlock).
  """
  # Task A blocked by Task B
  # Task B blocked by Task A
  # = Circular dependency

  if (task_a.blocked_by == task_b.id and
      task_b.blocked_by == task_a.id):
    return True

  return False

function break_deadlock(task_a, task_b):
  """
  Break deadlock by reordering tasks or providing intermediate data.
  """
  # Strategy 1: Reorder tasks (make one independent)
  if can_make_independent(task_a):
    remove_dependency(task_a, task_b)
    log_info(f"Broke deadlock by making {task_a.id} independent")

  # Strategy 2: Provide intermediate data
  elif can_provide_intermediate(task_b):
    intermediate_data = generate_intermediate_data(task_b)
    provide_to_task(task_a, intermediate_data)
    log_info(f"Broke deadlock by providing intermediate data from {task_b.id}")

  # Strategy 3: Refactor task dependency graph
  else:
    refactor_dependencies(task_a, task_b)
```

### Resource Contention

```python
function handle_resource_contention(resource_id, requesting_domains):
  """
  Arbitrate access when multiple domains need same resource.
  """
  # Strategy: First-come-first-served with queue
  queue = resource_queues.get(resource_id, [])

  for domain in requesting_domains:
    if domain not in queue:
      queue.append(domain)

  # Grant access to first in queue
  granted_domain = queue[0]
  grant_resource_access(resource_id, granted_domain)

  # Notify others they're queued
  for domain in queue[1:]:
    notify_domain_queued(domain, resource_id, position=queue.index(domain))
```

### Communication Breakdown

```python
function handle_workspace_communication_failure(workspace_id):
  """
  Fix broken workspace sharing or corrupted workspace.
  """
  log_error(f"Workspace communication failure: {workspace_id}")

  # Strategy 1: Rebuild workspace sharing
  try:
    rebuild_workspace_sharing(workspace_id, "master-orchestrator-primary")
    log_info(f"Rebuilt workspace sharing for {workspace_id}")
    return "sharing_rebuilt"

  except Exception as e:
    log_error(f"Failed to rebuild sharing: {e}")

  # Strategy 2: Create new workspace and migrate
  try:
    new_workspace_id = create_replacement_workspace(workspace_id)
    migrate_tasks(workspace_id, new_workspace_id)
    archive_workspace(workspace_id)
    log_info(f"Migrated to new workspace: {new_workspace_id}")
    return "workspace_migrated"

  except Exception as e:
    log_error(f"Failed to migrate workspace: {e}")
    return "unrecoverable"
```

## 8. Failure Notification & Transparency

Master maintains user-friendly failure notifications:

### User-Friendly Messages

**❌ BAD** (Technical jargon):
- "Backend orchestrator process 1234 segfaulted at address 0x7fff..."
- "Workspace sharing manager threw NullPointerException"
- "Task execution failed with exit code 137"

**✅ GOOD** (User-friendly):
- "Backend coordination encountered an issue - recovering now"
- "Coordinating systems experienced a delay - adjusting plan"
- "Task needs additional information - can you clarify [specific question]?"

### Notification Levels

```python
function notify_user(message, details=None, level="info"):
  """
  Send user notification through Master → user communication channel.

  Levels:
  - "info": Normal progress update
  - "warning": Minor issue, already handling
  - "error": Significant issue, user may want to know
  - "critical": Major failure, requires user attention
  """
  notification = {
    "timestamp": current_timestamp(),
    "level": level,
    "message": message,
    "details": details  # Optional technical details if user requests
  }

  send_to_user(notification)

  # Log for audit trail
  log_user_notification(notification)
```

### Progress Updates Include Recovery Status

When recovering from failures, keep user informed:

```python
# During recovery
notify_user(
  message="Backend coordination encountered an issue - recovering now",
  details={"recovery_progress": "spawning_replacement"},
  level="warning"
)

# After recovery complete
notify_user(
  message="Backend recovery complete - resuming API development",
  details={"tasks_resumed": 5},
  level="info"
)
```

### User Can Request Details

If user wants more information:

```python
# User asks: "What happened with the backend?"

def provide_failure_details(failure_id):
  failure = get_failure_record(failure_id)

  summary = f"""
  Backend orchestrator instance #2 became unresponsive at {failure.timestamp}.

  What happened:
  - Instance stopped responding to status queries
  - 5 tasks were in progress when it failed
  - Cause: {failure.root_cause}

  What we did:
  - Spawned replacement instance #3
  - Reassigned 5 tasks to replacement
  - Recovery completed in 45 seconds

  Current status:
  - All tasks resumed successfully
  - Backend domain operating normally
  """

  return summary
```

## 9. Failure Metrics & Learning

Track failure patterns to improve system reliability:

### Failure Metrics Collection

```python
failure_metrics = {
  "by_domain": {
    "mcp": {
      "orchestrator_failures": 2,
      "task_failures": 15,
      "avg_recovery_time_seconds": 45
    },
    "frontend": {
      "orchestrator_failures": 0,
      "task_failures": 8,
      "avg_recovery_time_seconds": 30
    },
    "backend": {
      "orchestrator_failures": 3,
      "task_failures": 22,
      "avg_recovery_time_seconds": 60
    }
  },
  "by_type": {
    "transient_errors": 30,
    "knowledge_gaps": 10,
    "invalid_input": 5,
    "orchestrator_crashes": 5
  },
  "learning_flow": {
    "triggered": 10,
    "successful": 8,
    "failed": 2,
    "skill_updates_applied": 8
  }
}
```

### Pattern Identification

Analyze metrics to identify patterns:

```python
function analyze_failure_patterns():
  """
  Identify patterns in failures to improve system.
  """
  # Pattern 1: Domain failure rates
  if failure_metrics["by_domain"]["backend"]["orchestrator_failures"] > 3:
    recommendation = "Backend orchestrators failing frequently - investigate root cause"

  # Pattern 2: Common error types
  common_errors = get_most_common_errors()
  if "authentication_error" in common_errors:
    recommendation = "Authentication errors common - improve auth error handling"

  # Pattern 3: Learning flow success rate
  learning_success_rate = (failure_metrics["learning_flow"]["successful"] /
                            failure_metrics["learning_flow"]["triggered"])
  if learning_success_rate < 0.7:
    recommendation = "Learning flow success rate low - improve research capabilities"

  return recommendations
```

### System Improvements from Metrics

Use metrics to drive improvements:

1. **Adjust spawn thresholds**: If domain failure-prone, spawn additional instances sooner
2. **Update worker agent skills**: Based on common failure patterns, enhance skills proactively
3. **Improve task routing**: Avoid routing complex tasks to unstable instances
4. **Enhance error handling**: Add specific error handlers for common error types
5. **Optimize resource allocation**: Allocate more resources to failure-prone domains

### Metrics Storage

Store metrics in workspace metadata for analysis:

```python
workspace_metadata = {
  # ... other metadata
  "failure_statistics": {
    "total_failures": 5,
    "orchestrator_crashes": 1,
    "task_failures": 4,
    "recovery_times": [45, 30, 60, 40, 50],  # seconds
    "failure_types": {
      "transient": 2,
      "knowledge_gap": 1,
      "invalid_input": 1,
      "crash": 1
    }
  }
}
```

Master aggregates metrics across all workspaces for system-wide analysis.

## Summary

Comprehensive failure recovery system enables Master Orchestrator to:

1. **Detect failures** across all orchestrator instances and task executions
2. **Classify failures** by type to apply appropriate recovery strategy
3. **Recover orchestrator failures** by spawning replacements and reassigning tasks
4. **Recover task failures** through retry, learning, or clarification
5. **Resolve cross-domain failures** through coordination and alternate paths
6. **Trigger learning** from failures to continuously improve
7. **Resolve coordination issues** like deadlocks and resource contention
8. **Communicate transparently** with user using friendly language
9. **Track and analyze metrics** to drive system improvements

This creates a resilient system that handles failures gracefully and learns from experience.
