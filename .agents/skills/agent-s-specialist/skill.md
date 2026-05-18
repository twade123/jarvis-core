---
name: agent-s-specialist
description: Specialized agent skill for expert-level Agent S Handler MCP operations including UI automation, desktop control, lifecycle management, and conversation mode capabilities.
version: 1.0.0
category: mcp-specialist
author: Claude Code Agent Skills System
created: 2026-02-04
triggers:
  - "agent s operations"
  - "ui automation task"
  - "desktop control automation"
  - "agent s lifecycle"
  - "conversation mode agent"
  - "screen interaction task"
capabilities:
  - ui_automation_execution
  - desktop_control_management
  - agent_lifecycle_control
  - conversation_mode_operations
  - screenshot_based_ui_understanding
  - accessibility_tree_integration
parent_orchestrator: mcp-domain-orchestrator
domain_type: agent_systems
can_execute: true
requires_human_approval: true
---

# Agent S Specialist

Expert-level operations for Agent S Handler MCP, enabling sophisticated UI automation, desktop control, and multi-turn conversation workflows through hierarchical task execution.

## Overview

Agent S Handler MCP provides comprehensive UI automation capabilities through a hierarchical framework:

**Architecture Components:**
- **Manager (Planner)**: Creates Directed Acyclic Graph (DAG) of subtasks
- **Worker (Executor)**: Executes individual subtasks through direct UI interaction
- **ACI (Application Control Interface)**: Platform-specific UI interaction layer
- **Knowledge Base**: Stores experiences from previous tasks for continuous improvement

**Key Capabilities:**
- Hierarchical task planning with DAG-based execution
- Cross-platform support (macOS via S1, Windows/Linux via S2)
- Screenshot-based UI understanding and navigation
- Accessibility tree integration for macOS
- Memory systems (narrative and episodic) for performance improvement
- Conversation mode for extended multi-turn interactions

## Core Tool Inventory

### Primary Execution Tools

**1. execute_ui_task** - Main execution entry point
```python
# Execute UI automation task with full lifecycle control
result = await execute_ui_task(
    task_description="Open Safari and search for AI news",
    execute_action=True,
    total_timeout=600,
    max_steps=15,
    execution_preference="auto"  # or "ui", "hotkey", "handler"
)
```

**Parameters:**
- `task_description` (str, required): Natural language task description
- `execute_action` (bool, default=True): Whether to actually execute actions
- `total_timeout` (int, default=600): Maximum execution time in seconds
- `max_steps` (int, default=15): Maximum number of execution steps
- `analysis_result` (dict, optional): Pre-computed task analysis
- `execution_preference` (str, default="auto"): Execution method preference
- `app_name` (str, optional): Target application name for focus

**Returns:**
```python
{
    "success": bool,
    "task": str,
    "execution_time": float,
    "execution_method": str,  # "ui", "hotkey", or "handler"
    "action_code": str,
    "info": dict,
    "conversation_active": bool,
    "conversation_id": str
}
```

**2. run_agent_s** - Direct Agent S execution
```python
# Run Agent S with hierarchical execution system
success, info, action = run_agent_s(
    task_description="Download sales report and create summary",
    max_steps=15
)
```

**Parameters:**
- `task_description` (str, required): Task to perform
- `max_steps` (int, default=15): Maximum execution steps

**Returns:** Tuple of (success: bool, info: dict, action: str)

### Conversation Mode Tools

**3. start_conversation** - Initialize conversation session
```python
# Start continuous conversation mode
result = start_conversation()
# Returns: {"success": bool, "conversation_id": str, "message": str}
```

**4. continue_conversation** - Add task to ongoing conversation
```python
# Continue with new task while maintaining context
result = await continue_conversation(
    task_description="Calculate 123 plus 456",
    execute_action=True,
    total_timeout=600,
    max_steps=15
)
```

**5. continue_with_new_task** - Direct continuation without reset
```python
# Continue conversation with preserved agent state
success, info, action = continue_with_new_task(
    new_task_description="What's the result?",
    max_steps=15
)
```

**6. end_conversation** - Terminate conversation session
```python
# End conversation and get summary
result = end_conversation()
# Returns: {"success": bool, "summary": dict, "message": str}
```

**7. get_conversation_state** - Query current conversation status
```python
# Get conversation state and history
state = get_conversation_state()
# Returns: {"active": bool, "conversation_id": str, "exchanges": int, ...}
```

### Lifecycle Management Tools

**8. is_waiting_for_next_task** - Check agent readiness
```python
# Check if agent completed task and waiting for next
waiting = is_waiting_for_next_task()
# Returns: bool
```

**9. prompt_for_next_task** - Prompt for continuation
```python
# Get prompt information for next task
prompt = prompt_for_next_task(prompt_message="What next?")
# Returns: {"success": bool, "prompt_message": str, "awaiting_input": bool}
```

### Desktop Control Tools

**10. run_agent_s_with_control_handoff** - Desktop control with user permission
```python
# Execute with proper desktop control handoff (currently disabled for testing)
result = await run_agent_s_with_control_handoff(
    task_description="Edit presentation slide",
    max_steps=15
)
```

**Note:** Desktop control handoff temporarily disabled - uses regular execution.

## Execution Workflows

### Workflow 1: Simple UI Automation

**Use Case:** Single UI task execution

```python
# Execute simple UI automation task
result = await execute_ui_task(
    task_description="Open calculator and compute 25 * 4",
    execute_action=True,
    max_steps=10
)

if result["success"]:
    print(f"Task completed in {result['execution_time']:.2f}s")
    print(f"Method used: {result['execution_method']}")
```

**When to use:**
- Single-step UI operations
- Quick automation tasks
- Testing UI automation capabilities

### Workflow 2: Multi-Turn Conversation

**Use Case:** Extended interaction with context preservation

```python
# Start conversation
session = start_conversation()
conversation_id = session["conversation_id"]

# First task
result1 = await continue_conversation(
    task_description="Open text editor and create new file"
)

# Check if agent is ready for next task
if is_waiting_for_next_task():
    # Second task (context preserved)
    result2 = await continue_conversation(
        task_description="Type 'Hello World' and save as hello.txt"
    )

    # Third task (still in context)
    result3 = await continue_conversation(
        task_description="Close the editor"
    )

# End conversation
summary = end_conversation()
print(f"Completed {summary['summary']['exchanges']} exchanges")
```

**When to use:**
- Complex multi-step workflows
- Tasks requiring context between steps
- Interactive automation scenarios

### Workflow 3: Execution with Preference

**Use Case:** Control execution method selection

```python
# Try hotkey shortcuts first, fallback to UI
result = await execute_ui_task(
    task_description="Open system preferences",
    execution_preference="hotkey",  # Prefer hotkeys
    max_steps=5
)

# Always use UI automation
result = await execute_ui_task(
    task_description="Configure network settings",
    execution_preference="ui",  # Force UI automation
    max_steps=20
)

# Prefer handler-based execution
result = await execute_ui_task(
    task_description="Send email to team",
    execution_preference="handler",  # Bypass UI when possible
    max_steps=10
)
```

**When to use:**
- Performance-critical operations (prefer hotkeys)
- Complex UI interactions (force UI)
- API-accessible operations (prefer handlers)

### Workflow 4: Direct Agent S Execution

**Use Case:** Low-level Agent S control

```python
# Direct execution with Agent S hierarchical system
success, info, action = run_agent_s(
    task_description="Find file in Downloads and move to Desktop",
    max_steps=25
)

if success:
    print("Task completed successfully")
    print(f"Final action: {action}")
    if info.get("subtask"):
        print(f"Subtask: {info['subtask']}")
```

**When to use:**
- Need raw Agent S capabilities
- Custom execution flow control
- Performance monitoring requirements

## Best Practices

### 1. Task Description Quality

**Good descriptions:**
- "Open Safari, navigate to news.google.com, and search for 'AI developments'"
- "Create new folder on Desktop named 'Reports' and move all PDFs from Downloads"
- "Open calculator, compute 123 * 456, and take screenshot of result"

**Avoid:**
- Vague instructions: "Do something with files"
- Missing context: "Click the button" (which button?)
- Ambiguous targets: "Open app" (which app?)

### 2. Step Limit Configuration

- **Simple tasks (1-3 actions)**: max_steps=5-10
- **Medium tasks (4-8 actions)**: max_steps=15-20
- **Complex tasks (9+ actions)**: max_steps=25-30
- **Avoid excessive limits**: Over-allocation wastes resources

### 3. Timeout Management

- **Quick operations**: total_timeout=60-120 seconds
- **Standard workflows**: total_timeout=300-600 seconds (default)
- **Complex automation**: total_timeout=900-1200 seconds
- **Always set timeouts**: Prevent infinite execution

### 4. Conversation Mode Usage

**Enable when:**
- Multi-step workflows with dependencies
- User needs to provide input between steps
- Context preservation improves accuracy
- Extended interaction sessions

**Disable when:**
- Single isolated tasks
- No inter-task dependencies
- Performance is critical
- Simpler execution model preferred

### 5. Error Handling

```python
# Robust error handling pattern
try:
    result = await execute_ui_task(
        task_description=user_task,
        total_timeout=600
    )

    if result["success"]:
        # Process successful result
        process_success(result)
    else:
        # Handle execution failure
        log_error(f"Task failed: {result.get('error')}")

except TimeoutError:
    # Handle timeout specifically
    notify_user("Task timed out - try simpler steps")

except Exception as e:
    # Catch-all for unexpected errors
    log_critical(f"Unexpected error: {e}")
```

### 6. Platform Considerations

**macOS Specific:**
- Accessibility tree integration available
- S1 implementation optimized for macOS
- AppleScript execution supported

**Windows/Linux:**
- S2 cross-platform implementation used
- Screenshot-based UI understanding
- No accessibility tree (uses vision only)

## Performance Optimization

### Memory Systems

Agent S learns from experience through:

1. **Narrative Memory** - Task-level learning
   - Stores complete task execution trajectories
   - Improves high-level planning
   - Updates after successful completion

2. **Episodic Memory** - Subtask-level learning
   - Records individual subtask executions
   - Improves low-level action selection
   - Updates continuously during execution

**Optimization tip:** Let Agent S complete tasks to accumulate memory - performance improves over time.

### Execution Preference Selection

- **auto**: System decides best method (default, recommended)
- **hotkey**: 2-5x faster for common operations
- **handler**: Bypasses UI entirely (fastest when available)
- **ui**: Most reliable but slowest

**Strategy:** Start with "auto", use "hotkey"/"handler" for repeated operations.

### Perplexica Integration

Agent S can use Perplexica for web search enhancement:
- Improves knowledge-based task execution
- Falls back to local knowledge if unavailable
- Configure via `PERPLEXICA_URL` environment variable

## Common Patterns

### Pattern 1: File Management Automation

```python
result = await execute_ui_task(
    task_description="""
    1. Open Finder
    2. Navigate to Downloads folder
    3. Create new folder named 'Archive_2024'
    4. Move all files older than 30 days to Archive_2024
    5. Close Finder
    """,
    max_steps=25,
    total_timeout=600
)
```

### Pattern 2: Application Workflow

```python
# Start conversation for multi-app workflow
start_conversation()

# Step 1: Data retrieval
await continue_conversation(
    "Open Excel and export data as CSV"
)

# Step 2: Processing
await continue_conversation(
    "Open Python IDE and run data_processor.py on the CSV"
)

# Step 3: Reporting
await continue_conversation(
    "Create summary report in Word with processed results"
)

end_conversation()
```

### Pattern 3: Screenshot-Based Verification

```python
# Execute task
result = await execute_ui_task(
    task_description="Configure network settings for VPN",
    max_steps=20
)

# Agent S automatically captures screenshots during execution
# Screenshots used for UI understanding and verification
if result["success"]:
    # Execution history contains screenshot-based verification
    print("Task verified through screenshot analysis")
```

## Integration with MCP Domain Orchestrator

Agent S Specialist reports to MCP Domain Orchestrator for:

1. **Task Assignment**: Receives UI automation tasks
2. **Progress Updates**: Reports execution progress
3. **Result Delivery**: Returns execution results
4. **Error Escalation**: Escalates unrecoverable errors

**Communication Pattern:**
```
MCP Domain Orchestrator
    ↓ (assigns UI automation task)
Agent S Specialist
    ↓ (executes with Agent S Handler MCP)
Agent S Handler MCP (agent_s_handler)
    ↓ (performs UI automation)
Desktop Applications (UI control)
```

## Success Criteria

Task successfully handled when:

- ✅ Task description properly interpreted
- ✅ Appropriate execution method selected
- ✅ UI interactions completed successfully
- ✅ Results captured and returned
- ✅ Error handling and recovery applied
- ✅ Performance metrics recorded
- ✅ Memory systems updated (when applicable)
- ✅ User notifications provided (when required)

## Troubleshooting

**Issue: Task times out**
- Increase `total_timeout` parameter
- Break task into smaller subtasks
- Reduce `max_steps` to prevent overrun

**Issue: UI elements not found**
- Improve task description specificity
- Verify application is accessible
- Check screen resolution compatibility

**Issue: Conversation mode not working**
- Ensure conversation_mode=True during initialization
- Call start_conversation() before first task
- Check is_waiting_for_next_task() between tasks

**Issue: Desktop control permission denied**
- Grant accessibility permissions to Python
- Enable system-wide UI automation access
- Check macOS Security & Privacy settings

## Version Compatibility

- **Agent S Version**: Compatible with S1 (macOS) and S2 (cross-platform)
- **Python Version**: Requires Python 3.8+
- **Platform Support**: macOS (full features), Windows/Linux (S2 only)
- **LLM Providers**: Anthropic Claude, OpenAI GPT-4

## References

- **Parent Orchestrator**: MCP Domain Orchestrator coordinates all MCP operations
- **Handler File**: `~/Jarvis/Handler/handler_agent_s.py`
- **MCP Registry**: Registered as `agent_s_handler` in MCP infrastructure
- **Related Skills**: agent-builder-specialist, swarm-specialist, multi-agent-specialist
