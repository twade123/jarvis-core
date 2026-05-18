# Agent Team Patterns

How to assemble agent teams for Jarvis workspaces. Extracted from the Forex Trading Team
(8 agents, production since Feb 2026) and Marketing Team (8 agents).

## Table of Contents
- [Agent Specification Format](#agent-specification-format)
- [Model Selection Guide](#model-selection-guide)
- [The Orchestrator Agent](#the-orchestrator-agent)
- [Specialist Agent Types](#specialist-agent-types)
- [Skill Registration](#skill-registration)
- [Prompt Architecture](#prompt-architecture)
- [Team Setup File Pattern](#team-setup-file-pattern)
- [Reference: Forex Trading Team Roster](#reference-forex-trading-team-roster)

---

## Agent Specification Format

Every agent is defined as a dictionary with these fields:

```python
{
    "name": "agent_name",                    # Unique identifier, snake_case
    "model": "claude-sonnet-4-6",            # Model to use (see selection guide)
    "role": "One-line description of role",  # Human-readable role
    "agent_type": "analysis",                # Category (see types below)
    "workspace": "Domain Name",              # Child workspace assignment
    "expertise_level": 8,                    # 1-10, used for task routing
    "capabilities": ["analytical", "data_analysis"],  # From AgentCapability enum
    "mcp_tools": ["handler_name"],           # MCP handlers this agent can use
    "prompt_file": "agent_name.md",          # Legacy prompt file (fallback)
    "skill_files": ["SKILL_NAME.md"],        # Skill docs appended to prompt
    "knowledge_base": [                      # Domain knowledge bullets
        "Key fact 1",
        "Key fact 2",
    ],
    "skills": [                              # Python callables and MCP tools
        {
            "name": "skill_name",
            "type": "python_callable",       # or "mcp_tool"
            "definition": {
                "module": "Source.agents.wrappers",
                "function": "function_name"
            }
        },
    ],
}
```

---

## Model Selection Guide

| Use Case | Model | Why |
|----------|-------|-----|
| Orchestration, complex reasoning | `claude-sonnet-4-6` | Needs planning + multi-step coordination |
| Vision, chart reading, complex validation | `claude-sonnet-4-6` | Vision capabilities required |
| Simple tool calling, data fetch | `claude-haiku-4-5-20251001` | Fast, cheap, reliable for structured ops |
| Local inference, no tool calls needed | `mlx/CRO` (port 11500) | Zero cost, sufficient for data description |
| High-stakes decisions | `claude-opus-4-6` | Maximum reasoning for critical paths |

**Rule of thumb**: Orchestrator = Sonnet. Tool callers = Haiku. Reasoners = Sonnet/Opus. Data describers = local MLX.

---

## The Orchestrator Agent

Every workspace gets exactly one orchestrator. This is a non-negotiable pattern.

### Orchestrator Responsibilities
1. **Task intake** — Receives work from boardroom, user, or scheduler
2. **Decomposition** — Breaks complex tasks into specialist subtasks
3. **Routing** — Assigns subtasks to appropriate specialist agents
4. **Coordination** — Sequences parallel and dependent work
5. **Communication** — Reports progress to user via dashboard/SSE
6. **Escalation** — Routes unresolvable issues to boardroom
7. **Learning** — Logs decisions and outcomes to knowledge vault

### Orchestrator Spec Template
```python
{
    "name": "orchestrator",
    "model": "claude-sonnet-4-6",
    "role": "Workspace orchestrator — coordinates all agents, communicates with user and boardroom",
    "agent_type": "coordinator",
    "workspace": "Orchestration",
    "expertise_level": 10,
    "capabilities": ["coordination", "planning", "communication", "analytical"],
    "mcp_tools": [],           # Orchestrator delegates; does NOT call tools directly
    "prompt_file": "orchestrator.md",
    "skill_files": [],
    "knowledge_base": [
        "You coordinate a team of N specialist agents in the [Project Name] workspace",
        "Task flow: receive -> decompose -> assign -> monitor -> aggregate -> report",
        "Use @mentions in task comments to direct specialist agents",
        "Escalate to boardroom when: consensus fails, risk threshold exceeded, user input needed",
        "Report status to user via SSE broadcast after each major step",
        "Log all decisions to knowledge vault with reasoning",
    ],
    "skills": [],
}
```

---

## Specialist Agent Types

From the `AgentType` enum in `handler_agent_builder.py`:

| Type | Use For | Example |
|------|---------|---------|
| `data_collection` | Fetching data from APIs/DBs | oanda_data, news fetcher |
| `analysis` | Processing and interpreting data | technical_analyst, sentiment analyzer |
| `validation` | Quality checks and decision gates | validator, data_validator |
| `execution` | Taking actions based on decisions | trade executor, email sender |
| `monitoring` | Watching for state changes | position_monitor, alert watcher |
| `coordinator` | Orchestrating other agents | orchestrator (exactly 1 per workspace) |
| `reporting` | Generating summaries and reports | reporter, dashboard updater |
| `research` | Deep investigation and learning | researcher, knowledge builder |

---

## Skill Registration

Agents can have two types of skills:

### Python Callables
Functions the agent can invoke directly:
```python
{
    "name": "fetch_data",
    "type": "python_callable",
    "definition": {
        "module": "Source.agents.wrappers",
        "function": "fetch_data"
    }
}
```

### MCP Tools
Handler-based tools accessed through MCP:
```python
{
    "name": "send_notification",
    "type": "mcp_tool",
    "definition": {
        "handler": "handler_email",
        "action": "send_email"
    }
}
```

### Wrappers Pattern
Create a `wrappers.py` file that wraps workspace-specific logic into simple callable functions:

```python
# Source/agents/wrappers.py
"""Thin wrappers around workspace modules for agent skill registration."""

def fetch_data(pair: str, timeframe: str = "H1") -> dict:
    """Fetch data for the given parameters."""
    from Source.data_fetcher import DataFetcher
    fetcher = DataFetcher()
    return fetcher.fetch(pair, timeframe)
```

---

## Prompt Architecture

### Loading Priority (vault-first)

```python
def _load_agent_prompt(spec):
    parts = []

    # 1. Canonical: knowledge vault
    vault_prompt = f"knowledge/agents/{spec['name']}/prompt.md"
    if Path(vault_prompt).exists():
        parts.append(Path(vault_prompt).read_text())

    # 2. Institutional memory: accumulated learnings
    learnings = f"knowledge/agents/{spec['name']}/learnings.md"
    if Path(learnings).exists():
        text = Path(learnings).read_text()
        if len(text) > 200 and "No learnings yet" not in text:
            parts.append(f"\n---\n## YOUR INSTITUTIONAL MEMORY\n\n{text}")

    # 3. Skill reference docs
    for skill_file in spec.get("skill_files", []):
        path = SKILLS_DIR / skill_file
        if path.exists():
            parts.append(f"\n---\n# Skill Reference: {skill_file}\n\n{path.read_text()}")

    # 4. Fallback: knowledge_base bullets
    if not parts:
        kb = spec.get("knowledge_base", [])
        if kb:
            parts.append("## Domain Knowledge\n\n" + "\n".join(f"- {item}" for item in kb))

    return "\n\n".join(parts) if parts else spec.get("role", "You are an agent.")
```

### Vault Prompt Structure
```markdown
# Agent Name — Role Description

## Your Mission
One paragraph describing the agent's core purpose.

## Your Tools
- Tool 1: what it does
- Tool 2: what it does

## Your Workflow
1. Step one
2. Step two
3. Step three

## Rules
- Hard rules that must never be violated
- Domain-specific constraints

## Communication Protocol
- How to post results to task comments
- Who to @mention for handoffs
- When to escalate to orchestrator
```

---

## Team Setup File Pattern

The complete `team_setup.py` pattern extracted from Forex Trading Team:

```python
"""
{Project Name} Team Setup -- dynamic agent creation via AgentBuilder.

Creates agents through Jarvis AgentBuilder, registers skills,
and forms the team via SwarmHandler.
Workspace IDs persist to .workspace_config.json for restart recovery.
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Any

logger = logging.getLogger("workspace.team_setup")

PARENT_WORKSPACE_NAME = "My Project"
PARENT_WORKSPACE_DESC = "Description of what this workspace does"

_WORKSPACE_ROOT = Path(__file__).parent.parent.parent
_SKILLS_DIR = _WORKSPACE_ROOT / "Skills"
_VAULT_DIR = Path(__file__).parent.parent.parent.parent / "knowledge"
_CONFIG_FILE = _WORKSPACE_ROOT / ".workspace_config.json"

AGENT_SPECS: List[Dict[str, Any]] = [
    # Define your agents here (see spec format above)
]


def _load_agent_prompt(spec: Dict[str, Any]) -> str:
    """Build full system prompt — vault-first loading."""
    # (Use the prompt loading pattern from above)
    ...


async def setup_team():
    """Create workspace, build agents, form swarm team."""
    from Handler.handler_agent_builder import AgentBuilder
    from Handler.handler_swarm import SwarmHandler
    from Database.workspace_sharing import get_workspace_sharing

    ws = get_workspace_sharing()
    builder = AgentBuilder()
    swarm = SwarmHandler()

    # Load or create workspace
    config = _load_config()
    if config.get("workspace_id"):
        parent_id = config["workspace_id"]
        logger.info("Resuming workspace %s", parent_id)
    else:
        parent = await ws.create_workspace(
            name=PARENT_WORKSPACE_NAME,
            description=PARENT_WORKSPACE_DESC,
            created_by="tim"
        )
        parent_id = parent["id"]
        config["workspace_id"] = parent_id
        _save_config(config)

    # Create agents
    for spec in AGENT_SPECS:
        prompt = _load_agent_prompt(spec)
        agent = builder.create_agent_simple(
            name=spec["name"],
            agent_type=spec["agent_type"],
            capabilities=spec["capabilities"],
            system_prompt=prompt,
        )
        logger.info("Created agent: %s (%s)", spec["name"], spec["agent_type"])

    # Form team in swarm
    swarm.set_workspace(parent_id)
    team = swarm.create_team(
        name=f"{PARENT_WORKSPACE_NAME.lower().replace(' ', '-')}-team",
        agents=[s["name"] for s in AGENT_SPECS],
    )
    logger.info("Team formed with %d agents", len(AGENT_SPECS))

    return parent_id


def _load_config() -> dict:
    if _CONFIG_FILE.exists():
        return json.loads(_CONFIG_FILE.read_text())
    return {"workspace_name": PARENT_WORKSPACE_NAME, "workspace_id": None}


def _save_config(config: dict):
    _CONFIG_FILE.write_text(json.dumps(config, indent=2))
```

---

## Reference: Forex Trading Team Roster

Production team with 8 agents — the reference implementation:

| Agent | Model | Type | MCP Tools | Role |
|-------|-------|------|-----------|------|
| oanda_data | Haiku | data_collection | handler_oanda | Market data fetch |
| intelligence | MLX/CRO | data_collection | news, weather, wolfram | Currency-aware intel |
| technical_analyst | MLX/CRO | analysis | (none) | TA with indicators and patterns |
| validator | Sonnet | validation | handler_data_validator | Vision-based trade decisions |
| execution | Haiku | execution | handler_oanda | Order placement and management |
| trade_monitor | Sonnet | monitoring | handler_oanda | Position guardian and snipe watcher |
| reporter | Sonnet | reporting | (none) | EOD analysis and reporting |
| cycle_orchestrator | Sonnet | coordinator | (none) | Coordinates the trading cycle |
