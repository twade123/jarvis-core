"""
boardroom_agent_context.py — Resource awareness and hybrid agent launcher.

ARCHITECTURE
────────────
Each board member's team is a COMBINATION of agent runtimes — the composition
is determined at runtime based on task needs, not design time:

  ┌─ Board Member Division Workspace (915-919) ──────────────────────────────┐
  │                                                                           │
  │  PERSISTENT AGENTS (swarm)          ON-DEMAND AGENTS                     │
  │  ─────────────────────────          ──────────────────                   │
  │  • DB agents (sqlite MCP)           • Claude via gateway (research)       │
  │  • Code auditors (bash MCP)         • Skill agents (Claude + skill.md)   │
  │  • Data pipeline agents             • ACP sessions (Trevor spawns these) │
  │  • Cron-scheduled agents            • Sub-agents (Trevor spawns these)   │
  │                                                                           │
  │  All results → workspace_tasks  ← board member reads next round          │
  └───────────────────────────────────────────────────────────────────────────┘

EXECUTION ROUTING
─────────────────
  RESEARCH: query
    → Claude via gateway (fast, parallel, no GPU overhead)

  DELEGATE: skill_agent_name | task
    → Read skill .md from vault → inject as Claude system context via gateway
    → Result written to workspace_tasks

  DELEGATE: swarm_agent_name | task
    → swarm.execute_agent_task() → existing Jarvis infrastructure
    → Result written to workspace_tasks

  SPAWN_AGENT: name | type | domain | caps | knowledge
    → Build agent with agent_builder → register in registry
    → Create workspace_task for Trevor to spawn as ACP session
    → Trevor's session picks it up and calls sessions_spawn

ACP SESSION SPONSORSHIP
───────────────────────
  Python code cannot call sessions_spawn directly — only OpenClaw agents can.
  serve_ui.py exposes /api/boardroom/spawn_task which Trevor (main session)
  monitors for pending ACP requests and spawns via sessions_spawn tool.
  Results come back as workspace_tasks updates.

DATA FLOW
─────────
  Every agent result → workspace_tasks(workspace_id=division_ws, status=completed)
  Board member prompt pulls recent completed tasks → context for next round
"""

import sqlite3
import json
import logging
import os
import time
from pathlib import Path
from typing import Optional, List, Dict

logger = logging.getLogger("BoardroomAgentContext")

BOARDROOM_DB   = Path.home() / "Jarvis" / "Database" / "v2" / "workspaces.db"
SKILLS_VAULT   = Path.home() / "jarvis" / "knowledge" / "skills"

# Fallback division workspaces (template boardroom 914).
# Overridden at runtime by _get_division_workspace() which looks up the
# actual divisions of whatever boardroom workspace is currently active.
_DIVISION_WORKSPACES_FALLBACK = {
    # Original 5 seats (template boardroom 914)
    'CTO':   915,
    'CSO':   916,
    'CRO':   917,
    'CDO':   918,
    'Opus':  919,
    'Trevor': 919,
    'CEO':   919,  # CEO = Chair = Trevor's division
    # V2 seats — created dynamically by provision_boardroom() on first use.
    # Placeholder None values trigger dynamic lookup via workspace_relationships.
    'CMO':   None,
    'CFO':   None,
    'CPO':   None,
    'COO':   None,
    'CCO':   None,
    'CHRO':  None,
    'CISO':  None,
    'CXO':   None,
    'CRvO':  None,
    'VPE':   None,
    'CDS':   None,
    'GC':    None,
}

# Cache: boardroom_workspace_id → {seat_name: division_ws_id}
_division_cache: dict = {}


def _get_division_workspace(member_name: str, boardroom_ws_id: int = None) -> Optional[int]:
    """
    Dynamically resolve a board member's division workspace ID.

    Priority:
    1. Live lookup via workspace_relationships WHERE parent=boardroom_ws_id
    2. Fallback to hardcoded template IDs (workspace 914)

    Division names contain the seat name, e.g. "CTO Division (User 2)".
    """
    global _division_cache

    # Normalise: Trevor/CEO → Opus (same division for chair)
    seat = member_name
    if member_name in ('Trevor', 'trevor', 'CEO', 'ceo'):
        seat = 'Opus'

    if boardroom_ws_id:
        if boardroom_ws_id not in _division_cache:
            _division_cache[boardroom_ws_id] = {}
        cached = _division_cache[boardroom_ws_id].get(seat)
        if cached:
            return cached

        try:
            conn = sqlite3.connect(str(BOARDROOM_DB))
            rows = conn.execute("""
                SELECT w.id, w.name
                FROM workspace_relationships r
                JOIN workspaces w ON w.id = r.child_workspace_id
                WHERE r.parent_workspace_id = ?
                  AND r.relationship_type = 'division'
            """, (boardroom_ws_id,)).fetchall()
            conn.close()
            for ws_id, ws_name in rows:
                ws_name_upper = (ws_name or '').upper()
                for s in ('CTO', 'CSO', 'CRO', 'CDO', 'OPUS'):
                    if s in ws_name_upper:
                        _division_cache[boardroom_ws_id][s] = ws_id
                        if s == 'OPUS':
                            _division_cache[boardroom_ws_id]['Trevor'] = ws_id
            result = _division_cache[boardroom_ws_id].get(seat)
            if result:
                return result
        except Exception as e:
            logger.debug(f"_get_division_workspace dynamic lookup failed: {e}")

    # Fallback to template IDs
    return _DIVISION_WORKSPACES_FALLBACK.get(seat)


# Active boardroom workspace ID — set by trevor_escalation when a session starts
_active_boardroom_ws_id: Optional[int] = None


def set_active_boardroom_workspace(ws_id: int):
    """Called by trevor_escalation at the start of each boardroom session."""
    global _active_boardroom_ws_id
    _active_boardroom_ws_id = ws_id
    logger.info(f"[boardroom_agent_context] Active boardroom workspace: {ws_id}")


def _resolve_division(member_name: str) -> Optional[int]:
    """Resolve member → division workspace using the active boardroom session."""
    return _get_division_workspace(member_name, _active_boardroom_ws_id)


# Legacy alias so existing code using DIVISION_WORKSPACES.get() still works
# during the transition. New code should use _resolve_division().
DIVISION_WORKSPACES = _DIVISION_WORKSPACES_FALLBACK


# ── Registry helpers ──────────────────────────────────────────────────────────

def get_member_skill_agents(member_name: str, limit: int = 12) -> list:
    """Skill agents assigned to this seat (knowledge.agent_factory created them)."""
    if not BOARDROOM_DB.exists():
        return []
    try:
        conn = sqlite3.connect(str(BOARDROOM_DB))
        rows = conn.execute("""
            SELECT agent_id, agent_name,
                   json_extract(capabilities, '$.skill_name') as skill_name,
                   success_count, total_requests, metadata
            FROM agent_registry
            WHERE agent_type = 'skill_agent'
              AND capabilities LIKE ?
              AND status IN ('active', 'available')
            ORDER BY total_requests DESC
            LIMIT ?
        """, (f'%"{member_name}"%', limit)).fetchall()
        conn.close()
        result = []
        for r in rows:
            total = r[4] or 0
            meta  = {}
            try: meta = json.loads(r[5] or '{}')
            except: pass
            result.append({
                'agent_id':    r[0],
                'agent_name':  r[1],
                'skill_name':  r[2] or r[1],
                'vault_path':  meta.get('vault_path', ''),
                'total_tasks': total,
                'success_rate': round(r[3] / total * 100, 1) if total > 0 else None,
            })
        return result
    except Exception as e:
        logger.debug(f"get_member_skill_agents: {e}")
        return []


def get_member_team_agents(member_name: str, limit: int = 10) -> list:
    """Persistent agents assigned to this member's division workspace."""
    division_ws = _resolve_division(member_name)
    if not division_ws or not BOARDROOM_DB.exists():
        return []
    try:
        conn = sqlite3.connect(str(BOARDROOM_DB))
        rows = conn.execute("""
            SELECT waa.agent_id, waa.agent_name, waa.agent_type, waa.role,
                   COALESCE(ar.success_count,0), COALESCE(ar.total_requests,0)
            FROM workspace_agent_assignments waa
            LEFT JOIN agent_registry ar ON ar.agent_id = waa.agent_id
            WHERE waa.workspace_id = ? AND waa.status = 'active'
            LIMIT ?
        """, (division_ws, limit)).fetchall()
        conn.close()
        result = []
        for r in rows:
            total = r[5]
            result.append({
                'agent_id': r[0], 'agent_name': r[1],
                'agent_type': r[2], 'role': r[3],
                'total_tasks': total,
                'success_rate': round(r[4]/total*100, 1) if total > 0 else None,
            })
        return result
    except Exception as e:
        logger.debug(f"get_member_team_agents: {e}")
        return []


def get_division_tasks(member_name: str, limit: int = 5) -> list:
    """Recent completed + active tasks in this member's division workspace."""
    division_ws = _resolve_division(member_name)
    if not division_ws or not BOARDROOM_DB.exists():
        return []
    try:
        conn = sqlite3.connect(str(BOARDROOM_DB))
        rows = conn.execute("""
            SELECT id, title, status, priority, assigned_agent_id, description
            FROM workspace_tasks
            WHERE workspace_id = ? AND status NOT IN ('archived')
            ORDER BY CASE status WHEN 'completed' THEN 0 WHEN 'in_progress' THEN 1
                                 WHEN 'pending' THEN 2 ELSE 3 END,
                     updated_at DESC
            LIMIT ?
        """, (division_ws, limit)).fetchall()
        conn.close()
        return [{'id': r[0], 'title': r[1], 'status': r[2],
                 'priority': r[3], 'agent': r[4],
                 'result': (r[5] or '')[:200]} for r in rows]
    except Exception as e:
        logger.debug(f"get_division_tasks: {e}")
        return []


def write_task_result(member_name: str, title: str, result: str,
                      agent_name: str = None, status: str = 'completed') -> int:
    """Write an agent result to the division workspace_tasks table."""
    division_ws = _resolve_division(member_name)
    if not division_ws or not BOARDROOM_DB.exists():
        return -1
    try:
        conn = sqlite3.connect(str(BOARDROOM_DB))
        cursor = conn.execute("""
            INSERT INTO workspace_tasks
              (workspace_id, title, description, status, priority,
               assigned_agent_id, created_at, updated_at)
            VALUES (?, ?, ?, ?, 'medium', ?, datetime('now'), datetime('now'))
        """, (division_ws, title[:200], result[:2000], status, agent_name))
        conn.commit()
        task_id = cursor.lastrowid
        conn.close()
        return task_id
    except Exception as e:
        logger.debug(f"write_task_result: {e}")
        return -1


def write_pending_acp_spawn(member_name: str, agent_spec: dict, task: str) -> int:
    """
    Write a pending ACP spawn request to workspace_tasks with status='pending_acp'.
    Trevor's main session polls for these and calls sessions_spawn on our behalf.
    The task description contains the full ACP spawn spec as JSON.
    """
    division_ws = _resolve_division(member_name)
    if not division_ws or not BOARDROOM_DB.exists():
        return -1
    try:
        conn = sqlite3.connect(str(BOARDROOM_DB))
        spec_json = json.dumps({
            'spawn_type': 'acp',
            'member': member_name,
            'agent_spec': agent_spec,
            'task': task,
            'requested_at': time.time(),
        })
        cursor = conn.execute("""
            INSERT INTO workspace_tasks
              (workspace_id, title, description, status, priority,
               assigned_agent_id, created_at, updated_at)
            VALUES (?, ?, ?, 'pending_acp', 'high', 'trevor_acp_sponsor',
                    datetime('now'), datetime('now'))
        """, (division_ws, f"[ACP] {agent_spec.get('name','agent')}: {task[:100]}", spec_json))
        conn.commit()
        task_id = cursor.lastrowid
        conn.close()
        logger.info(f"[boardroom] ACP spawn request queued: task_id={task_id} for {member_name}")
        return task_id
    except Exception as e:
        logger.debug(f"write_pending_acp_spawn: {e}")
        return -1


# ── Resource context block ────────────────────────────────────────────────────

def build_member_resource_context(member_name: str) -> str:
    """
    Inject the full resource context into a board member's prompt.
    Covers: skill agents, persistent team, active tasks, delegation interface.
    """
    division_ws = _resolve_division(member_name)
    skill_agents = get_member_skill_agents(member_name, limit=10)
    team_agents  = get_member_team_agents(member_name, limit=6)
    tasks        = get_division_tasks(member_name, limit=4)

    lines = [f"\n### {member_name} Division (workspace {division_ws}) — Your Resources"]

    # Skill agents
    if skill_agents:
        lines.append(f"\n**Skill agents on your roster ({len(skill_agents)}):**")
        for a in skill_agents[:8]:
            perf = f" [{a['success_rate']}% / {a['total_tasks']} tasks]" if a['total_tasks'] else ""
            lines.append(f"  - `{a['skill_name']}`{perf}")
    else:
        lines.append("\n**Skill agents:** none yet — use BUILD_AGENT: to add them")

    # Persistent team agents
    if team_agents:
        lines.append(f"\n**Your standing team ({len(team_agents)} agents):**")
        for a in team_agents[:5]:
            perf = f" [{a['success_rate']}% / {a['total_tasks']} tasks]" if a['total_tasks'] else ""
            lines.append(f"  - `{a['agent_name']}` ({a['role']}){perf}")

    # Recent task results (what your team has already done)
    completed = [t for t in tasks if t['status'] == 'completed']
    if completed:
        lines.append(f"\n**Recent team results:**")
        for t in completed[:3]:
            lines.append(f"  - [{t['agent'] or 'agent'}] {t['title']}")
            if t['result']:
                lines.append(f"    → {t['result'][:120]}")

    active = [t for t in tasks if t['status'] in ('in_progress', 'pending')]
    if active:
        lines.append(f"\n**Tasks in progress:**")
        for t in active[:3]:
            lines.append(f"  - [{t['status']}] {t['title']} → {t['agent'] or 'unassigned'}")

    # Delegation interface
    lines.append("""
**Delegation — use these tags anywhere in your response:**

RESEARCH: [question]
  → Claude researches immediately, result injected before your contribution
  → Best for: quick lookups, web data, vault queries, code reads

DELEGATE: [agent_name] | [task description]
  → Routes to a skill agent (Claude + skill knowledge) or swarm agent
  → Result written to your division workspace and injected back

SPAWN_AGENT: [name] | [type] | [domain] | [capabilities] | [what it knows]
  → Builds agent with agent_builder, registers it, requests ACP session via Trevor
  → Agent runs as full Claude Code instance, manages its own sub-team
  → Use for: complex long-running tasks, multi-step plans, any task needing /plan or /gsd
  → Example: SPAWN_AGENT: VaultAuditor | analysis | obsidian_vault | research,file_read | Obsidian API feature comparison

BUILD_AGENT: [name] | [type] | [domain] | [capabilities] | [knowledge]
  → Builds and registers a new agent — adds it to your roster immediately
  → Unlike SPAWN_AGENT, does NOT auto-run — you call it with DELEGATE: later

FIND_AGENTS: [capability keyword]
  → Searches the full agent registry across all divisions""")

    return "\n".join(lines)


# ── Tag parser ────────────────────────────────────────────────────────────────

def parse_member_requests(member_name: str, response_text: str) -> list:
    """
    Parse structured delegation tags from a board member's response.
    Returns list of request dicts for parallel execution.
    """
    import re
    requests = []

    for m in re.finditer(r'RESEARCH:\s*([^\n]+)', response_text, re.IGNORECASE):
        requests.append({'type': 'research', 'query': m.group(1).strip(), 'member': member_name})

    for m in re.finditer(r'DELEGATE:\s*([^|\n]+)\|([^\n]+)', response_text, re.IGNORECASE):
        requests.append({'type': 'delegate', 'agent_name': m.group(1).strip(),
                         'task': m.group(2).strip(), 'member': member_name})

    for m in re.finditer(
        r'SPAWN_AGENT:\s*([^|]+)\|([^|]+)\|([^|]+)\|([^|]+)\|([^\n]+)',
        response_text, re.IGNORECASE
    ):
        requests.append({'type': 'spawn_agent', 'name': m.group(1).strip(),
                         'agent_type': m.group(2).strip(), 'domain': m.group(3).strip(),
                         'capabilities': [c.strip() for c in m.group(4).split(',')],
                         'knowledge': m.group(5).strip(), 'member': member_name})

    for m in re.finditer(
        r'BUILD_AGENT:\s*([^|]+)\|([^|]+)\|([^|]+)\|([^|]+)\|([^\n]+)',
        response_text, re.IGNORECASE
    ):
        requests.append({'type': 'build_agent', 'name': m.group(1).strip(),
                         'agent_type': m.group(2).strip(), 'domain': m.group(3).strip(),
                         'capabilities': [c.strip() for c in m.group(4).split(',')],
                         'knowledge': m.group(5).strip(), 'member': member_name})

    for m in re.finditer(r'FIND_AGENTS:\s*([^\n]+)', response_text, re.IGNORECASE):
        requests.append({'type': 'find_agents', 'capability': m.group(1).strip(),
                         'member': member_name})

    return requests


# ── Execution router ──────────────────────────────────────────────────────────

async def execute_member_request(req: dict, swarm=None) -> str:
    """
    Execute a parsed delegation request and return result string.
    All results are also written to workspace_tasks for persistence.
    """
    t = req.get('type')
    if   t == 'research':    return await _do_research(req)
    elif t == 'delegate':    return await _do_delegate(req, swarm)
    elif t == 'spawn_agent': return await _do_spawn_agent(req)
    elif t == 'build_agent': return await _do_build_agent(req)
    elif t == 'find_agents': return await _do_find_agents(req)
    return f"*(unknown request type: {t})*"


# ── RESEARCH ──────────────────────────────────────────────────────────────────

async def _do_research(req: dict) -> str:
    """
    Fast research via Claude (gateway chat/completions).
    No ACP spawn needed — Claude running here IS the research capability.
    Results written to workspace_tasks.
    """
    query  = req['query']
    member = req['member']
    try:
        import httpx
        token, gateway = _get_gateway_creds()
        if not token:
            return "*(Research: gateway token unavailable)*"

        payload = {
            "model": "openclaw:main",
            "messages": [{
                "role": "user",
                "content": (
                    f"You are a research agent for the {member} board member.\n"
                    f"Research this concisely — key facts only, be specific:\n\n"
                    f"{query}\n\n"
                    f"Check ~/jarvis files if relevant. Return 3-5 bullet points."
                )
            }],
            "max_tokens": 500,
        }
        async with httpx.AsyncClient(timeout=50.0) as client:
            r = await client.post(f"{gateway}/v1/chat/completions",
                                  headers={"Authorization": f"Bearer {token}"}, json=payload)
            if r.status_code != 200:
                logger.error(f"_do_research: gateway HTTP {r.status_code} — {r.text[:200]}")
                return f"*(Research failed: HTTP {r.status_code})*"
            d = r.json()
            if "choices" not in d:
                logger.error(f"_do_research: no choices in response — {str(d)[:200]}")
                return f"*(Research failed: {str(d)[:80]})*"
            result = d["choices"][0]["message"]["content"].strip()

        write_task_result(member, f"Research: {query[:80]}", result, agent_name="research_claude")
        logger.info(f"_do_research [{member}]: '{query[:60]}' → {len(result)} chars")
        return f"**Research** ({query[:60]}):\n{result}"
    except Exception as e:
        logger.error(f"_do_research [{member}] exception: {type(e).__name__}: {e}", exc_info=True)
        return f"*(Research error: {type(e).__name__}: {str(e)[:80]})*"


# ── DELEGATE ─────────────────────────────────────────────────────────────────

async def _do_delegate(req: dict, swarm) -> str:
    """
    Hybrid routing:
      skill_agent  → Claude via gateway with full skill.md injected as context
      swarm_agent  → swarm.execute_agent_task()
      unknown      → Claude research fallback
    """
    agent_name = req['agent_name']
    task       = req['task']
    member     = req['member']

    # Look up agent in registry
    agent_info = _get_agent_from_db(agent_name)

    if agent_info and agent_info.get('agent_type') in ('skill_agent', 'available'):
        result = await _run_skill_agent(agent_info, task, member)
    elif swarm:
        result = await _run_swarm_agent(swarm, agent_name, task, member)
    else:
        # Fallback to Claude research
        result = await _do_research({'query': task, 'member': member})

    write_task_result(member, f"[{agent_name}] {task[:80]}", result, agent_name=agent_name)
    return f"**{agent_name}** result:\n{result}"


async def _run_skill_agent(agent_info: dict, task: str, member: str) -> str:
    """
    Run a skill agent by injecting its SKILL.md into a Claude gateway call.
    This gives Claude full skill knowledge — effectively is the skill agent running.
    """
    # Read skill content from vault
    skill_content = ""
    vault_path = agent_info.get('vault_path', '')
    if vault_path and Path(vault_path).exists():
        try:
            skill_content = Path(vault_path).read_text(encoding='utf-8')[:3000]
        except Exception:
            pass
    else:
        # Try by skill_name
        try:
            caps = json.loads(agent_info.get('capabilities', '{}'))
            skill_name = caps.get('skill_name', '')
            if skill_name:
                skill_file = SKILLS_VAULT / f"{skill_name}.md"
                if skill_file.exists():
                    skill_content = skill_file.read_text(encoding='utf-8')[:3000]
        except Exception:
            pass

    try:
        import httpx
        token, gateway = _get_gateway_creds()
        if not token:
            return "*(Skill agent: gateway unavailable)*"

        system = (
            f"You are the {agent_info.get('agent_name', 'agent')} agent on the {member}'s team.\n"
            f"You have this specialized skill:\n\n{skill_content}\n\n"
            f"Execute the task given. Be specific and actionable. Return findings only."
        ) if skill_content else (
            f"You are the {agent_info.get('agent_name', 'agent')} agent. "
            f"Execute the task and return findings."
        )

        payload = {
            "model": "openclaw:main",
            "messages": [
                {"role": "system", "content": system},
                {"role": "user",   "content": task},
            ],
            "max_tokens": 600,
        }
        async with httpx.AsyncClient(timeout=60.0) as client:
            r = await client.post(f"{gateway}/v1/chat/completions",
                                  headers={"Authorization": f"Bearer {token}"}, json=payload)
            d = r.json()
            if "choices" in d:
                return d["choices"][0]["message"]["content"].strip()
            return f"*(Skill agent call failed: {str(d)[:80]})*"
    except Exception as e:
        logger.error(f"_run_skill_agent: {e}")
        return f"*(Skill agent error: {str(e)[:80]})*"


async def _run_swarm_agent(swarm, agent_name: str, task: str, member: str) -> str:
    """Run a swarm agent via execute_agent_task."""
    try:
        result = await swarm.execute_agent_task(
            agent_name=agent_name,
            task=task,
            context={"delegated_by": member, "boardroom": True},
        )
        if hasattr(result, 'response'):
            return result.response[:500]
        return str(result)[:500]
    except Exception as e:
        logger.error(f"_run_swarm_agent [{member}] agent={agent_name}: {type(e).__name__}: {e}", exc_info=True)
        write_task_result(member, f"SWARM FAIL: {agent_name}", str(e)[:500],
                          agent_name=agent_name, status='failed')
        return f"*(Swarm agent {agent_name} error: {type(e).__name__}: {str(e)[:80]})*"


# ── SPAWN_AGENT ───────────────────────────────────────────────────────────────

async def _do_spawn_agent(req: dict) -> str:
    """
    Build agent + queue ACP spawn for Trevor to execute.

    Flow:
      1. Build agent config with agent_builder (prompt + skills + registry)
      2. Write pending_acp task to workspace — Trevor polls and calls sessions_spawn
      3. Return immediately with confirmation — result arrives asynchronously
    """
    member = req['member']

    # Step 1: build the agent
    build_result = await _do_build_agent(req)

    # Step 2: queue ACP spawn
    agent_spec = {
        'name':         req['name'],
        'type':         req.get('agent_type', 'analysis'),
        'domain':       req.get('domain', ''),
        'capabilities': req.get('capabilities', []),
        'knowledge':    req.get('knowledge', ''),
    }
    task_id = write_pending_acp_spawn(member, agent_spec, task=req.get('knowledge', req['name']))

    return (
        f"**{req['name']} spawned** — {build_result}\n"
        f"ACP session queued (task #{task_id}). "
        f"Trevor will launch it as Claude Code — results flow back to your division workspace."
    )


# ── BUILD_AGENT ───────────────────────────────────────────────────────────────

async def _do_build_agent(req: dict) -> str:
    """Build + register a new agent via agent_builder. Does NOT auto-launch."""
    try:
        from Handler.handler_agent_builder import (
            AgentBuilderHandler, AgentSpecialization,
            AgentCapability, AgentType
        )
        import asyncio

        builder = AgentBuilderHandler()
        cap_map = {c.value: c for c in AgentCapability}
        caps = []
        for c in req.get('capabilities', []):
            norm = c.lower().strip().replace(' ', '_').replace('-', '_')
            caps.append(cap_map.get(norm, AgentCapability.ANALYTICAL))

        spec = AgentSpecialization(
            domain=req.get('domain', 'general'),
            expertise_level=8,
            capabilities=caps or [AgentCapability.ANALYTICAL, AgentCapability.RESEARCH],
            tools=[],
            knowledge_base=[req.get('knowledge', '')]
        )

        try:
            agent_type = AgentType(req.get('agent_type', 'analysis'))
        except ValueError:
            agent_type = AgentType('analysis')

        agent_id = await builder.create_agent(
            specialization=spec,
            agent_name=req['name'],
            agent_type=agent_type,
            module_name=f"boardroom.{req['member'].lower()}",
            team_name=f"{req['member']} Division",
        )
        return (
            f"Agent `{req['name']}` built and registered (id: {agent_id[:8]}…). "
            f"Call via: DELEGATE: {req['name']} | [task]"
        )
    except Exception as e:
        logger.error(f"_do_build_agent: {e}")
        return f"*(Agent build failed: {str(e)[:100]})*"


# ── FIND_AGENTS ───────────────────────────────────────────────────────────────

async def _do_find_agents(req: dict) -> str:
    capability = req['capability']
    try:
        conn = sqlite3.connect(str(BOARDROOM_DB))
        rows = conn.execute("""
            SELECT agent_name, agent_type, module_name, success_count, total_requests
            FROM agent_registry
            WHERE (capabilities LIKE ? OR agent_name LIKE ? OR agent_type LIKE ?)
              AND status IN ('active', 'available')
            ORDER BY total_requests DESC
            LIMIT 12
        """, (f'%{capability}%', f'%{capability}%', f'%{capability}%')).fetchall()
        conn.close()
        if not rows:
            return f"*(No agents found matching: {capability})*"
        lines = [f"**Registry — '{capability}':**"]
        for r in rows:
            total = r[4] or 0
            perf = f" [{round(r[3]/total*100,1)}% / {total} tasks]" if total else ""
            lines.append(f"  - `{r[0]}` ({r[1]}, {r[2]}){perf}")
        return "\n".join(lines)
    except Exception as e:
        return f"*(Registry search error: {str(e)[:80]})*"


# ── DB helpers ────────────────────────────────────────────────────────────────

def _get_agent_from_db(agent_name: str) -> Optional[dict]:
    """
    Look up an agent by name in the registry.
    Tries multiple name variants: original, hyphen→underscore, camelCase strip.
    """
    if not BOARDROOM_DB.exists():
        return None
    # Build search variants: 'data-exploration' → also try 'data_exploration', 'dataexploration'
    clean = agent_name.strip().strip('*').strip()  # strip any markdown formatting
    variants = list({
        clean,
        clean.replace('-', '_'),
        clean.replace('-', ''),
        clean.replace('_', '-'),
        clean.replace(' ', '-'),
        clean.replace(' ', '_'),
    })
    try:
        conn = sqlite3.connect(str(BOARDROOM_DB))
        row = None
        for v in variants:
            row = conn.execute("""
                SELECT agent_id, agent_name, agent_type, module_name, capabilities, metadata
                FROM agent_registry
                WHERE agent_name LIKE ? OR agent_id LIKE ?
                  AND status IN ('available','active','running')
                ORDER BY total_requests DESC LIMIT 1
            """, (f'%{v}%', f'%{v}%')).fetchone()
            if row:
                break
        conn.close()
        if not row:
            return None
        meta = {}
        try: meta = json.loads(row[5] or '{}')
        except: pass
        return {'agent_id': row[0], 'agent_name': row[1], 'agent_type': row[2],
                'module_name': row[3], 'capabilities': row[4],
                'vault_path': meta.get('vault_path', '')}
    except Exception as e:
        logger.debug(f"_get_agent_from_db({agent_name}): {e}")
        return None


def _get_gateway_creds():
    """Read OpenClaw gateway token + URL."""
    try:
        config_path = Path.home() / ".openclaw" / "openclaw.json"
        config = json.loads(config_path.read_text())
        token = config.get("gateway", {}).get("auth", {}).get("token", "")
        port  = config.get("gateway", {}).get("port", 18789)
        return token, f"http://127.0.0.1:{port}"
    except Exception:
        return "", "http://127.0.0.1:18789"


# ── ACP sponsor: Trevor polls this and calls sessions_spawn ──────────────────

def get_pending_acp_spawns() -> list:
    """
    Called by Trevor's main session to pick up pending ACP spawn requests.
    Returns list of tasks with status='pending_acp'.
    """
    if not BOARDROOM_DB.exists():
        return []
    try:
        conn = sqlite3.connect(str(BOARDROOM_DB))
        rows = conn.execute("""
            SELECT id, workspace_id, title, description, created_at
            FROM workspace_tasks
            WHERE status = 'pending_acp'
            ORDER BY created_at ASC
            LIMIT 10
        """).fetchall()
        conn.close()
        result = []
        for r in rows:
            spec = {}
            try: spec = json.loads(r[3] or '{}')
            except: pass
            result.append({'task_id': r[0], 'workspace_id': r[1],
                           'title': r[2], 'spec': spec})
        return result
    except Exception as e:
        logger.debug(f"get_pending_acp_spawns: {e}")
        return []


def mark_acp_spawn_launched(task_id: int, session_key: str):
    """Mark a pending_acp task as launched with the session key."""
    if not BOARDROOM_DB.exists():
        return
    try:
        conn = sqlite3.connect(str(BOARDROOM_DB))
        conn.execute("""
            UPDATE workspace_tasks
            SET status = 'in_progress',
                assigned_agent_id = ?,
                updated_at = datetime('now')
            WHERE id = ?
        """, (session_key, task_id))
        conn.commit()
        conn.close()
    except Exception as e:
        logger.debug(f"mark_acp_spawn_launched: {e}")
