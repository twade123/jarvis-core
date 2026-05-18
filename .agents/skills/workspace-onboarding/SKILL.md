---
name: workspace-onboarding
description: >
  End-to-end playbook for standing up a new Jarvis workspace from scratch — workspace hierarchy creation,
  agent team assembly via AgentBuilder + Swarm, UI dashboard bootstrapping (dark theme, SSE, vanilla JS),
  Flask API server wiring, MCP tool registration, task management, boardroom integration, and orchestrator
  agent assignment. Use when: (1) creating a new project workspace ("set up a workspace for X"),
  (2) onboarding a team of agents to a workspace, (3) building a dashboard UI for a workspace,
  (4) wiring API endpoints and SSE streams for a workspace, (5) configuring swarm coordination patterns
  for agent teams, (6) connecting boardroom to a workspace, (7) any mention of "workspace setup",
  "new project workspace", "workspace onboarding", "build a workspace", "agent team for a workspace",
  or "workspace dashboard". Reference implementation: Forex Trading Team workspace.
---

# Workspace Onboarding

Stand up a fully operational Jarvis workspace — from empty directory to running agent teams with
a live dashboard. Every workspace gets a dedicated orchestrator agent, a boardroom connection
(active or dormant), and a customizable UI.

## The 7-Layer Process

| Layer | What | When to Skip |
|-------|------|-------------|
| 1. Discovery | Scope the workspace purpose, agents, data sources, MCP needs | Never |
| 2. Scaffolding | Create workspace hierarchy, directories, database entries | Never |
| 3. Agent Team | Build agents via AgentBuilder, register in Swarm, assign skills | Never |
| 4. UI Bootstrap | Dark-theme dashboard from base template, customize views | If headless/API-only |
| 5. API Server | Flask endpoints, SSE streams, database reads | If headless/API-only |
| 6. Orchestration | Wire orchestrator agent, boardroom, task management | Never |
| 7. Lifecycle | Monitoring, health checks, archival strategy | After MVP is running |

---

## Layer 1: Discovery

Before building anything, answer these questions with the user:

### Required Inputs
- **Workspace name and purpose** — What problem does this workspace solve?
- **Agent roster** — What specialist agents are needed? (minimum: 1 orchestrator + 1 specialist)
- **Data sources** — What databases, APIs, or MCP servers does the workspace need?
- **UI needs** — Dashboard? Chat interface? Both? Headless?
- **Boardroom mode** — Active (complex decisions routed to multi-model collaboration) or Dormant (available but not auto-invoked)?

### Discovery Outputs
- Agent specification list (name, role, model, MCP tools, skills)
- Workspace hierarchy plan (parent workspace + child domains)
- MCP server list per agent
- UI view list (what panels/tabs the dashboard needs)

---

## Layer 2: Scaffolding

### Directory Structure
Every workspace follows this layout:
```
{Workspace Name}/
  Config/                    # workspace_config.json, credentials
  Data/                      # workspace-specific data stores
  Source/
    agents/
      team_setup.py          # Agent specs + team creation
      wrappers.py            # Python callable wrappers for agent skills
      __init__.py
    scripts/                 # Utility scripts
    config.py                # Workspace constants
  Skills/                    # Skill reference docs loaded into agent prompts
  Knowledge/                 # Workspace-specific knowledge files
  dashboard/
    index.html               # UI dashboard
    api_server.py            # Flask API
    cycle_state/             # Runtime state files
  .workspace_config.json     # Workspace ID persistence for restart recovery
```

### Database Registration
```python
from Database.workspace_sharing import get_workspace_sharing

ws = get_workspace_sharing()

# Create parent workspace
parent = await ws.create_workspace(
    name="My Project",
    description="Purpose of this workspace",
    created_by="tim"
)
parent_id = parent["id"]

# Create child workspaces for each domain
for domain in ["Data Collection", "Analysis", "Execution"]:
    child = await ws.create_workspace(
        name=domain,
        description=f"{domain} domain workspace",
        created_by="tim",
        parent_workspace_id=parent_id
    )
```

### Workspace Config File
```json
{
  "workspace_name": "My Project",
  "workspace_id": null,
  "parent_workspace_id": null,
  "environment": "development",
  "agents": {},
  "mcp_servers": [],
  "boardroom_mode": "dormant",
  "created_at": null
}
```

---

## Layer 3: Agent Team Assembly

Every workspace gets exactly ONE orchestrator agent. All other agents are specialists
reporting to that orchestrator.

### The Orchestrator Pattern
The workspace orchestrator:
- Receives tasks from boardroom or user
- Breaks work into subtasks for specialist agents
- Coordinates via task comments (@mentions)
- Reports status back to user/boardroom
- Is the ONLY agent that talks to the user directly

### Agent Spec Format
See [references/agent-team-patterns.md](references/agent-team-patterns.md) for the complete pattern with examples from the Forex Trading Team.

```python
AGENT_SPECS = [
    {
        "name": "orchestrator",
        "model": "claude-sonnet-4-6",       # Orchestrator needs reasoning
        "role": "Workspace orchestrator — coordinates all agents, talks to user",
        "agent_type": "coordinator",
        "workspace": "Orchestration",
        "expertise_level": 10,
        "capabilities": ["coordination", "planning", "communication"],
        "mcp_tools": [],                     # Orchestrator delegates, doesn't use tools
        "prompt_file": "orchestrator.md",
        "skill_files": [],
        "knowledge_base": ["...domain-specific coordination knowledge..."],
        "skills": [],
    },
    # ... specialist agents follow same format ...
]
```

### Team Creation Flow
```python
from Handler.handler_agent_builder import AgentBuilder
from Handler.handler_swarm import SwarmHandler

builder = AgentBuilder()
swarm = SwarmHandler()

# 1. Create agents via builder
for spec in AGENT_SPECS:
    prompt = _load_agent_prompt(spec)  # Vault-first loading
    agent = builder.create_agent_simple(
        name=spec["name"],
        agent_type=spec["agent_type"],
        capabilities=spec["capabilities"],
        system_prompt=prompt,
    )

# 2. Register team in swarm
swarm.set_workspace(parent_workspace_id)
team = swarm.create_team(
    name="my-project-team",
    agents=[s["name"] for s in AGENT_SPECS],
)
```

### Prompt Loading Priority
1. Knowledge vault: `knowledge/agents/{name}/prompt.md` (canonical)
2. Vault learnings: `knowledge/agents/{name}/learnings.md` (appended)
3. Skill files from workspace `Skills/` directory (appended as reference sections)
4. Legacy `Prompts/` directory (fallback only)
5. `knowledge_base` list from spec (last resort)

---

## Layer 4: UI Bootstrap

Use the Jarvis dark-theme UI system. See [references/ui-brand-guide.md](references/ui-brand-guide.md) for the complete brand book with CSS variables, component patterns, and layout system.

Start from the base template in [assets/base-ui-template/](assets/base-ui-template/) and customize.

### Quick Start
1. Copy `assets/base-ui-template/index.html` to `{workspace}/dashboard/index.html`
2. Copy `assets/base-ui-template/api_server.py` to `{workspace}/dashboard/api_server.py`
3. Update title, header text, and workspace name
4. Add workspace-specific views/panels
5. Wire SSE event handlers for your agent events

### View Architecture
```
Loading View -> Login View -> Setup View (optional) -> Main App View
                                                        |-- Sidebar (nav)
                                                        |-- Main Content (panels)
                                                        +-- Status Bar
```

### Key UI Patterns
- **Global state**: Single `const S = { token, user, ... }` object
- **View switching**: `.view` class with `.active` toggle
- **Real-time**: SSE via `EventSource` — never WebSockets
- **Auth**: Auto-login on localhost, token-based otherwise
- **Theme**: CSS variables — customize by overriding `:root` values

---

## Layer 5: API Server

See [references/api-server-guide.md](references/api-server-guide.md) for the complete Flask pattern with SSE streaming.

### Core Endpoints Every Workspace Needs
```
GET  /api/config              -> workspace configuration
GET  /api/conversations       -> agent messages from shard DB
GET  /api/activities          -> workspace activity log
GET  /api/agents              -> agent roster with status
GET  /api/health              -> workspace health check
POST /api/task                -> submit task to orchestrator
GET  /api/stream              -> SSE event stream
```

### SSE Event Types
```javascript
// Standard events every workspace dashboard handles
event: agent_activity     // Agent did something
event: task_update        // Task status changed
event: conversation       // New agent message
event: boardroom_update   // Boardroom session activity
event: workspace_status   // Workspace health/state change
```

---

## Layer 6: Orchestration Wiring

### Boardroom Integration
Every workspace has boardroom access. Configure the mode in workspace config:

- **Active**: Complex requests auto-route to boardroom for multi-model planning (Claude + GPT collaboration). Use for workspaces where decisions are high-stakes or require diverse reasoning.
- **Dormant**: Boardroom available but only invoked explicitly via user request or orchestrator escalation. Use for workspaces with well-defined automated workflows.

### Task Management via Comments
Agents communicate through task comments with @mentions. See [references/swarm-integration-guide.md](references/swarm-integration-guide.md) for the full communication fabric pattern.

```python
from Database.workspace_task_comments import WorkspaceTaskCommentManager

comments = WorkspaceTaskCommentManager()

# Orchestrator creates task and assigns to specialist
task_id = comments.create_task(
    title="Analyze data for X",
    workspace_id=workspace_id,
    assigned_agent_id="analyst"
)

# Specialist posts results
comments.add_comment(
    task_id=task_id,
    author_id="analyst",
    author_type="agent",
    content="Analysis complete. Key findings: ...",
    technical_details={"metric": 42.5}
)

# Orchestrator routes to next agent
comments.add_comment(
    task_id=task_id,
    author_id="orchestrator",
    author_type="agent",
    content="@validator Please validate these findings."
)
```

### Swarm Coordination Patterns
- **Sequential pipeline**: Agent A -> Agent B -> Agent C (data flows linearly)
- **Parallel fan-out**: Orchestrator sends same task to multiple agents, collects results
- **Competitive consensus**: Multiple agents analyze independently, orchestrator picks best
- **Escalation chain**: Specialist -> Orchestrator -> Boardroom (increasing complexity)

---

## Layer 7: Lifecycle Operations

### Health Monitoring
```python
def workspace_health_check():
    return {
        "workspace_id": WORKSPACE_ID,
        "agents_active": len(active_agents),
        "tasks_pending": count_pending_tasks(),
        "last_activity": get_last_activity_timestamp(),
        "boardroom_mode": config["boardroom_mode"],
        "database_ok": check_db_connections(),
        "mcp_servers_ok": check_mcp_health(),
    }
```

### Learning Extraction
After significant workspace operations, write to the knowledge vault:
```bash
python3 ~/jarvis/knowledge/vault_cli.py \
    --agent "workspace-orchestrator" \
    --type "improvement" \
    --summary "One-line summary of what was learned" \
    --context "Full context" \
    --tags "workspace,project-name"
```

---

## Checklist: New Workspace MVP

- [ ] Discovery complete — purpose, agents, data sources defined
- [ ] Directory structure created
- [ ] Workspace registered in database (parent + child workspaces)
- [ ] workspace_config.json written
- [ ] Orchestrator agent spec defined
- [ ] Specialist agent specs defined (at least 1)
- [ ] Agent prompts written to knowledge vault
- [ ] team_setup.py written with AGENT_SPECS
- [ ] Agents registered in AgentBuilder + Swarm
- [ ] Dashboard UI customized from base template (if UI needed)
- [ ] API server running with core endpoints (if UI needed)
- [ ] SSE stream wired for real-time updates (if UI needed)
- [ ] Boardroom mode configured (active/dormant)
- [ ] Task management wired (create tasks, comment routing)
- [ ] Health check endpoint working
- [ ] Workspace config persisted for restart recovery
