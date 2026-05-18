# Swarm Integration Guide

How swarm, workspace sharing, task comments, and boardroom wire together as
the communication fabric for Jarvis workspaces.

## Table of Contents
- [Architecture Overview](#architecture-overview)
- [Swarm + Workspace Binding](#swarm--workspace-binding)
- [Task Comment Communication](#task-comment-communication)
- [Coordination Patterns](#coordination-patterns)
- [Boardroom Integration](#boardroom-integration)
- [Agent Health and Recovery](#agent-health-and-recovery)
- [Cross-Workspace Communication](#cross-workspace-communication)

---

## Architecture Overview

```
User / Boardroom
      |
      v
[Workspace Orchestrator Agent]
      |
      +-- SwarmHandler (team coordination)
      |     +-- Agent A (specialist)
      |     +-- Agent B (specialist)
      |     +-- Agent C (specialist)
      |
      +-- WorkspaceTaskCommentManager (communication)
      |     +-- Task threads with @mentions
      |     +-- Status updates
      |     +-- Technical detail attachments
      |
      +-- WorkspaceSharingManager (access control)
      |     +-- Role-based permissions
      |     +-- Team membership
      |     +-- Workspace hierarchy
      |
      +-- BoardroomConnector (escalation)
            +-- Multi-model collaboration
            +-- Journey tracking
            +-- Decision logging
```

---

## Swarm + Workspace Binding

### Setting Up a Swarm in a Workspace

```python
from Handler.handler_swarm import SwarmHandler

swarm = SwarmHandler()

# Bind swarm to workspace
swarm.set_workspace(workspace_id)

# Load workspace's MCP configuration (what tools are available)
await swarm.load_workspace_mcp()

# Create team
team = swarm.create_team(
    name="project-team",
    agents=["orchestrator", "analyst", "executor"],
)

# Assign agents to workspace with roles
for agent_name in ["orchestrator", "analyst", "executor"]:
    await swarm._assign_agent_to_workspace(
        agent_name=agent_name,
        workspace_id=workspace_id,
        role="contributor"
    )
```

### SwarmAgent Model
Each agent in the swarm has:
```python
SwarmAgent(
    name="analyst",
    instructions="System prompt / role description",
    tools=[callable_function_1, callable_function_2],
    mcp_tools=["handler_data_validator", "handler_terminal"],
)
```

### MCP Tool Access
Agents access MCP tools through the swarm's workspace configuration:
- `swarm._workspace_mcp_config` maps handler_name -> mcp_server_name
- When an agent needs an MCP tool, swarm routes through the correct handler
- MCP tools are loaded lazily when first accessed

---

## Task Comment Communication

### The Communication Pattern
Agents communicate through task comment threads — NOT direct messages.
This creates an auditable, searchable record of all agent interactions.

### Creating a Task Thread
```python
from Database.workspace_task_comments import WorkspaceTaskCommentManager

comments = WorkspaceTaskCommentManager()

# Orchestrator creates the task (defines the work unit)
task_id = comments.create_task(
    title="Analyze EUR_USD for trading signals",
    workspace_id=workspace_id,
    assigned_agent_id="technical_analyst",
    description="Run full TA pipeline on H1 + H4 timeframes",
    priority="high"
)
```

### Agent Communication Flow
```
1. Orchestrator creates task, assigns to Agent A
2. Agent A posts analysis results as comment
3. Agent A @mentions Agent B for next step
4. Agent B reads thread, posts its results
5. Orchestrator reads all comments, makes routing decision
6. Orchestrator posts summary, closes task or escalates
```

### Comment Types by author_type
- `"agent"` — Agent posting results or requests
- `"user"` — Human posting instructions or feedback
- `"system"` — Automated status updates (task created, status changed)

### Technical Details Attachment
```python
# Attach structured data alongside human-readable comment
comments.add_comment(
    task_id=task_id,
    author_id="technical_analyst",
    author_type="agent",
    content="EUR_USD H1: RSI oversold (28.5), MACD bullish crossover forming. Setup S15 detected.",
    technical_details={
        "pair": "EUR_USD",
        "timeframe": "H1",
        "rsi": 28.5,
        "macd_signal": "bullish_crossover",
        "setup": "S15",
        "confluence_score": 78,
        "regime": "ranging"
    }
)
```

### @Mention Routing
```python
# Direct handoff to specific agent
comments.add_comment(
    task_id=task_id,
    author_id="orchestrator",
    author_type="agent",
    content="@validator Signal detected. Please validate with DB evidence and vision check."
)

# Broadcast to team
comments.add_comment(
    task_id=task_id,
    author_id="orchestrator",
    author_type="agent",
    content="@all Cycle complete. Results: 2 signals approved, 1 rejected."
)
```

---

## Coordination Patterns

### Pattern 1: Sequential Pipeline
```
Orchestrator -> Data Agent -> Analyst -> Validator -> Executor
                   |              |           |           |
                   v              v           v           v
              [task comment] [task comment] [task comment] [task comment]
```
Each agent reads the task thread, adds its analysis, and @mentions the next agent.

### Pattern 2: Parallel Fan-Out
```
              +-- Analyst A (posts results) --+
              |                               |
Orchestrator -+-- Analyst B (posts results) --+-- Orchestrator (aggregates)
              |                               |
              +-- Analyst C (posts results) --+
```
Orchestrator creates one task, assigns to multiple agents. Reads all comments when
all agents have posted.

### Pattern 3: Competitive Consensus
```
Orchestrator creates same task for 3 agents
  -> Agent A: "BUY, confidence 0.8"
  -> Agent B: "HOLD, confidence 0.6"
  -> Agent C: "BUY, confidence 0.7"
  -> Orchestrator: "Consensus BUY (2/3, avg confidence 0.75)"
```

### Pattern 4: Escalation Chain
```
Specialist: "I can't determine the correct action. Confidence below threshold."
  -> Orchestrator: Reviews, attempts resolution
    -> Boardroom: Multi-model collaboration for complex decision
      -> Back to Orchestrator: Execute boardroom's plan
```

### Pattern 5: Cyclic/Scheduled Pipeline
```
Scheduler triggers every N minutes:
  -> Orchestrator: Start cycle
    -> Data Agent: Fetch latest data
      -> Analyst: Analyze
        -> Validator: Validate
          -> Executor: Execute (if approved)
            -> Reporter: Log results
              -> Orchestrator: Cycle complete, wait for next trigger
```
This is the Forex Trading Team pattern — a continuous analysis-decision-execution loop.

---

## Boardroom Integration

### Active Mode
```python
# In workspace config
{"boardroom_mode": "active"}

# Orchestrator auto-escalates complex tasks
async def handle_complex_task(task):
    if task.complexity > THRESHOLD:
        # Route to boardroom for multi-model planning
        from Jarvis_Agent_SDK.boardroom_connector import request_boardroom_session
        plan = await request_boardroom_session(
            task=task,
            workspace_id=workspace_id,
            context=gather_context_from_task_thread(task.id)
        )
        # Execute boardroom's plan
        await execute_plan(plan)
```

### Dormant Mode
```python
# In workspace config
{"boardroom_mode": "dormant"}

# Boardroom only invoked on explicit request
async def escalate_to_boardroom(task, reason):
    """Only called when orchestrator or user explicitly requests boardroom."""
    logger.info("Escalating to boardroom: %s — reason: %s", task.title, reason)
    # ... invoke boardroom ...
```

### Journey Tracking
Every significant operation is tracked through the boardroom connector:
```python
from Jarvis_Agent_SDK.boardroom_connector import track_journey_step_sync

track_journey_step_sync(
    journey_id=journey_id,
    step_name="analysis_complete",
    step_data={"agents_participated": 3, "signals_found": 2},
    status="completed"
)
```

---

## Agent Health and Recovery

### Health Monitoring
```python
# Swarm provides health_check()
health = swarm.health_check()
# Returns: {agent_name: {status, last_activity, tasks_completed, error_count}}
```

### Recovery Patterns

**Agent unresponsive** (no activity for >5 minutes):
1. Orchestrator detects via health check
2. Reassign pending tasks to backup agent or self
3. Log failure to vault
4. Broadcast status update via SSE

**Consensus failure** (agents disagree, can't resolve):
1. Orchestrator collects all positions
2. If any agent has >0.8 confidence, use that
3. Otherwise, escalate to boardroom
4. Log disagreement pattern for learning

**MCP tool failure** (handler unavailable):
1. Agent reports error in task comment
2. Orchestrator checks if alternative tool exists
3. If no alternative, degrade gracefully (skip that analysis step)
4. Report to user via SSE

---

## Cross-Workspace Communication

### When Workspaces Need to Talk
- Parent workspace needs results from child workspace
- Shared resource (database, API) needs coordination
- User request spans multiple workspace domains

### Pattern: Workspace Bridge via Orchestrator
```python
# Parent orchestrator creates task in child workspace
from Database.workspace_task_comments import WorkspaceTaskCommentManager

comments = WorkspaceTaskCommentManager()

# Create task in child workspace
child_task = comments.create_task(
    title="Provide analysis for parent workspace request",
    workspace_id=child_workspace_id,
    assigned_agent_id="child_orchestrator",
    description=f"Parent workspace {parent_id} needs: {request_details}"
)

# Child orchestrator picks up, processes, posts results
# Parent orchestrator polls for completion
```

### Pattern: Shared Shard Database
All workspaces in the same shard can read each other's conversations and activities.
Use `workspace_id` filtering to scope queries.
