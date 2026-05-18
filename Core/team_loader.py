"""
Universal Team/Agent Loader — Registry-First Architecture.

The agent_registry is the SINGLE SOURCE OF TRUTH for all agents.
Any system (boardroom, trading, future teams) uses this to:

1. Load agents from registry → workspace + swarm
2. Spawn new agents via AgentBuilder if not found → register → load
3. Sync performance data back to registry
4. Clone agents/teams to other workspaces

Flow:
    Need agent? → check registry → found? → load into swarm
                                  → not found? → AgentBuilder creates → registers → load into swarm
    
    Agent does work → swarm tracks performance → sync_performance_to_registry() → registry updated
    
    Need to reuse? → registry knows performance → boardroom picks best agents → clone to new workspace
"""

import json
import logging
import sqlite3
import time
import os
from pathlib import Path
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)

DEFAULT_DB_PATH = str(Path(__file__).parent.parent / "Database" / "v2" / "agents.db")
PROMPTS_DIR = str(Path(__file__).parent.parent / "Trading Bot" / "Prompts")


def get_db(db_path: str = None) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path or DEFAULT_DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


# ---------------------------------------------------------------------------
# 1. Load agents from registry
# ---------------------------------------------------------------------------

def load_agent_from_registry(agent_id: str, db_path: str = None) -> Optional[Dict[str, Any]]:
    """Load a single agent's full config from the registry.
    
    Returns dict with: agent_id, agent_name, model, system_prompt, mcp_tools,
    skills, capabilities, performance, metadata — everything needed to create
    a SwarmAgent and assign it to a workspace.
    """
    conn = get_db(db_path)
    row = conn.execute(
        """SELECT agent_id, agent_name, agent_type, model, system_prompt_path,
                  capabilities, metadata, team_id, workspace_id, board_seat,
                  success_count, failure_count, avg_response_time, total_requests
           FROM agent_registry WHERE agent_id = ? AND status = 'active'""",
        (agent_id,)
    ).fetchone()
    
    if not row:
        conn.close()
        return None
    
    agent = dict(row)
    
    # Parse JSON fields
    if agent.get("capabilities"):
        try:
            agent["capabilities"] = json.loads(agent["capabilities"])
        except (json.JSONDecodeError, TypeError):
            agent["capabilities"] = []
    
    if agent.get("metadata"):
        try:
            agent["metadata"] = json.loads(agent["metadata"])
        except (json.JSONDecodeError, TypeError):
            agent["metadata"] = {}
    else:
        agent["metadata"] = {}
    
    # Load system prompt: metadata blob > prompt file > empty
    agent["system_prompt"] = agent["metadata"].get("system_prompt", "")
    if not agent["system_prompt"] and agent.get("system_prompt_path"):
        agent["system_prompt"] = _load_prompt_file(agent["system_prompt_path"])
    
    # MCP tools from metadata
    agent["mcp_tools"] = agent["metadata"].get("mcp_tools", [])
    
    # Load skills
    skills = conn.execute(
        "SELECT skill_name, skill_type, definition_json, performance_score FROM agent_skills WHERE agent_id = ?",
        (agent_id,)
    ).fetchall()
    agent["skills"] = [dict(s) for s in skills]
    
    # Performance summary
    agent["performance"] = {
        "success_count": agent.get("success_count", 0) or 0,
        "failure_count": agent.get("failure_count", 0) or 0,
        "avg_response_time": agent.get("avg_response_time", 0) or 0,
        "total_requests": agent.get("total_requests", 0) or 0,
        "win_rate": _calc_win_rate(agent.get("success_count", 0), agent.get("failure_count", 0)),
    }
    
    conn.close()
    logger.info("Loaded agent %s (%s) from registry — model=%s, skills=%d, win_rate=%.1f%%",
                agent["agent_name"], agent_id[:12], agent.get("model"), len(agent["skills"]),
                agent["performance"]["win_rate"])
    return agent


def load_team_from_registry(team_id: str, db_path: str = None) -> Optional[Dict[str, Any]]:
    """Load an entire team from registry. Returns dict of agent_name → agent config."""
    conn = get_db(db_path)
    rows = conn.execute(
        "SELECT agent_id FROM agent_registry WHERE team_id = ? AND status = 'active'",
        (team_id,)
    ).fetchall()
    conn.close()
    
    if not rows:
        return None
    
    team = {}
    for row in rows:
        agent = load_agent_from_registry(row["agent_id"], db_path)
        if agent:
            team[agent["agent_name"]] = agent
    
    logger.info("Loaded team %s: %d agents", team_id[:12], len(team))
    return team


def load_team_into_swarm(team_id: str, swarm_handler, db_path: str = None) -> Dict[str, str]:
    """Load a team from registry directly into a SwarmHandler.
    
    - Creates SwarmAgents with model, prompt, mcp_tools from registry
    - Records agent → workspace assignment in workspace_agent_assignments
    - Swarm must already be bound to a workspace via set_workspace()
    
    Returns dict of agent_name → agent_id for all loaded agents.
    """
    from Handler.handler_swarm import SwarmAgent
    
    team = load_team_from_registry(team_id, db_path)
    if not team:
        logger.warning("No team found for %s", team_id[:12])
        return {}
    
    workspace_id = getattr(swarm_handler, '_workspace_id', None)
    
    loaded = {}
    for agent_name, agent_data in team.items():
        try:
            agent = SwarmAgent(
                name=agent_name,
                instructions=agent_data.get("system_prompt", agent_data.get("agent_type", "")),
                tools=[],  # Python callables resolved by caller if needed
                mcp_tools=agent_data.get("mcp_tools", []),
                model=agent_data.get("model", ""),
            )
            swarm_handler.agents[agent_name] = agent
            loaded[agent_name] = agent_data["agent_id"]
            
            # Record workspace assignment so workspace_sharing tracks this agent
            if workspace_id:
                _assign_agent_to_workspace_sync(
                    agent_data["agent_id"], agent_name,
                    agent_data.get("agent_type", "system"),
                    workspace_id, db_path,
                )
            
            logger.info("Loaded %s into swarm (ws=%s): model=%s, mcps=%s",
                        agent_name, workspace_id, agent_data.get("model"), agent_data.get("mcp_tools"))
        except Exception as e:
            logger.warning("Failed to load %s into swarm: %s", agent_name, e)
    
    return loaded


def _assign_agent_to_workspace_sync(agent_id: str, agent_name: str, agent_type: str,
                                      workspace_id: int, db_path: str = None):
    """Record agent → workspace assignment in workspace_agent_assignments table.
    
    This is the sync version for use during team loading. The workspace_sharing
    module tracks all agent activity per workspace through this table.
    """
    try:
        conn = get_db(db_path)
        conn.execute("""
            INSERT INTO workspace_agent_assignments 
                (workspace_id, agent_id, agent_name, agent_type, role, assigned_by, status)
            VALUES (?, ?, ?, ?, 'contributor', 'team_loader', 'active')
            ON CONFLICT(workspace_id, agent_id) DO UPDATE SET
                status = 'active', assigned_at = CURRENT_TIMESTAMP
        """, (workspace_id, agent_id, agent_name, agent_type))
        conn.commit()
        conn.close()
    except Exception as e:
        logger.debug("workspace assignment for %s: %s", agent_name, e)


# ---------------------------------------------------------------------------
# 2. Find or spawn agents
# ---------------------------------------------------------------------------

def find_or_spawn_agent(
    task_description: str,
    team_id: str = None,
    board_seat: str = None,
    model: str = None,
    db_path: str = None,
) -> Dict[str, Any]:
    """Registry-first agent resolution.
    
    1. Search registry for an agent matching the task/capabilities
    2. If found → return it (with full config)
    3. If not found → AgentBuilder creates it → registers → return it
    
    This is what the boardroom should call when it needs an agent.
    """
    # Step 1: Search registry
    existing = _search_registry(task_description, team_id, board_seat, db_path)
    if existing:
        agent = load_agent_from_registry(existing["agent_id"], db_path)
        if agent:
            return {"action": "existing", "agent": agent}
    
    # Step 2: Build new agent
    logger.info("No existing agent for '%s' — building via AgentBuilder", task_description[:60])
    try:
        from Handler.handler_agent_builder import AgentBuilder
        builder = AgentBuilder()
        result = builder.find_or_build_agent(task_description, board_seat)
        
        if result.get("agent"):
            agent_data = result["agent"]
            agent_id = agent_data.get("agent_id")
            
            # Ensure it's in the registry with full config
            if agent_id:
                _ensure_registered(agent_data, team_id, model, db_path)
                # Reload from registry to get clean data
                agent = load_agent_from_registry(agent_id, db_path)
                if agent:
                    return {"action": result.get("action", "created"), "agent": agent}
            
            return {"action": result.get("action", "created"), "agent": agent_data}
    except Exception as e:
        logger.error("AgentBuilder failed: %s", e)
    
    return {"action": "failed", "agent": None}


# ---------------------------------------------------------------------------
# 3. Performance sync: swarm/workspace → registry
# ---------------------------------------------------------------------------

def sync_performance_to_registry(db_path: str = None):
    """Sync performance data from agent_performance table → agent_registry.
    
    Aggregates success/failure/timing from agent_performance (where swarm logs it)
    and writes summary stats to agent_registry columns.
    
    Call this periodically (e.g., after each cycle, or via cron).
    """
    conn = get_db(db_path)
    
    # Aggregate from agent_performance
    rows = conn.execute("""
        SELECT agent_id, agent_name,
               SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as wins,
               SUM(CASE WHEN success = 0 THEN 1 ELSE 0 END) as losses,
               AVG(completion_time) as avg_time,
               COUNT(*) as total,
               AVG(quality_score) as avg_quality
        FROM agent_performance
        GROUP BY agent_id
    """).fetchall()
    
    updated = 0
    for row in rows:
        conn.execute("""
            UPDATE agent_registry 
            SET success_count = ?, failure_count = ?, avg_response_time = ?,
                total_requests = ?, updated_at = ?
            WHERE agent_id = ?
        """, (row["wins"], row["losses"], row["avg_time"], row["total"], time.time(), row["agent_id"]))
        updated += 1
    
    conn.commit()
    conn.close()
    
    if updated:
        logger.info("Synced performance for %d agents to registry", updated)
    return updated


def get_top_agents(capability: str = None, min_requests: int = 5, limit: int = 10, db_path: str = None) -> List[Dict]:
    """Get top-performing agents from registry, sorted by win rate.
    
    Boardroom uses this to find the best agents to reuse or clone.
    """
    conn = get_db(db_path)
    
    query = """
        SELECT agent_id, agent_name, model, team_id, board_seat,
               success_count, failure_count, avg_response_time, total_requests,
               capabilities
        FROM agent_registry
        WHERE status = 'active' AND total_requests >= ?
    """
    params: list = [min_requests]
    
    if capability:
        query += " AND capabilities LIKE ?"
        params.append(f"%{capability}%")
    
    query += " ORDER BY CAST(success_count AS FLOAT) / MAX(total_requests, 1) DESC LIMIT ?"
    params.append(limit)
    
    rows = conn.execute(query, params).fetchall()
    conn.close()
    
    results = []
    for row in rows:
        agent = dict(row)
        agent["win_rate"] = _calc_win_rate(agent.get("success_count", 0), agent.get("failure_count", 0))
        results.append(agent)
    
    return results


def get_team_performance(team_id: str, db_path: str = None) -> Dict[str, Any]:
    """Get aggregated performance for an entire team."""
    conn = get_db(db_path)
    
    rows = conn.execute("""
        SELECT agent_name, success_count, failure_count, avg_response_time, total_requests
        FROM agent_registry
        WHERE team_id = ? AND status = 'active'
    """, (team_id,)).fetchall()
    conn.close()
    
    agents = {}
    total_wins = 0
    total_losses = 0
    total_requests = 0
    
    for row in rows:
        agent = dict(row)
        agent["win_rate"] = _calc_win_rate(agent.get("success_count", 0), agent.get("failure_count", 0))
        agents[agent["agent_name"]] = agent
        total_wins += agent.get("success_count", 0) or 0
        total_losses += agent.get("failure_count", 0) or 0
        total_requests += agent.get("total_requests", 0) or 0
    
    return {
        "team_id": team_id,
        "agents": agents,
        "team_win_rate": _calc_win_rate(total_wins, total_losses),
        "total_requests": total_requests,
    }


# ---------------------------------------------------------------------------
# 4. Clone agents/teams to other workspaces
# ---------------------------------------------------------------------------

def clone_agent_to_workspace(agent_id: str, target_workspace_id: int, target_team_id: str = None, db_path: str = None) -> Optional[str]:
    """Clone an agent from registry into a different workspace/team.
    
    Creates a new agent_registry entry with same config but new IDs.
    Copies all skills. Returns new agent_id.
    """
    import uuid
    source = load_agent_from_registry(agent_id, db_path)
    if not source:
        logger.error("Cannot clone — agent %s not found", agent_id)
        return None
    
    new_agent_id = f"{source['agent_name']}_{int(time.time())}"
    new_db_id = str(uuid.uuid4())
    
    conn = get_db(db_path)
    
    # Insert cloned agent
    conn.execute("""
        INSERT INTO agent_registry 
        (id, agent_id, agent_name, agent_type, module_name, capabilities,
         created_at, updated_at, status, metadata, model, system_prompt_path,
         team_id, workspace_id, board_seat, prompt_focus)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'active', ?, ?, ?, ?, ?, ?, ?)
    """, (
        new_db_id, new_agent_id, source["agent_name"], source.get("agent_type"),
        source.get("module_name", "cloned"), json.dumps(source.get("capabilities", [])),
        time.time(), time.time(), json.dumps(source.get("metadata", {})),
        source.get("model"), source.get("system_prompt_path"),
        target_team_id, target_workspace_id,
        source.get("board_seat"), source.get("prompt_focus"),
    ))
    
    # Clone skills
    for skill in source.get("skills", []):
        skill_id = str(uuid.uuid4())
        conn.execute("""
            INSERT INTO agent_skills (id, agent_id, skill_name, skill_type, definition_json)
            VALUES (?, ?, ?, ?, ?)
        """, (skill_id, new_agent_id, skill["skill_name"], skill["skill_type"], skill.get("definition_json", "{}")))
    
    conn.commit()
    conn.close()
    
    logger.info("Cloned agent %s → %s (workspace=%s, team=%s)", 
                agent_id[:12], new_agent_id[:12], target_workspace_id, target_team_id)
    return new_agent_id


def clone_team_to_workspace(source_team_id: str, target_workspace_id: int, target_team_id: str = None, db_path: str = None) -> Dict[str, str]:
    """Clone an entire team to a new workspace. Returns mapping of agent_name → new_agent_id."""
    import uuid
    if not target_team_id:
        target_team_id = str(uuid.uuid4())
    
    team = load_team_from_registry(source_team_id, db_path)
    if not team:
        return {}
    
    cloned = {}
    for agent_name, agent_data in team.items():
        new_id = clone_agent_to_workspace(agent_data["agent_id"], target_workspace_id, target_team_id, db_path)
        if new_id:
            cloned[agent_name] = new_id
    
    logger.info("Cloned team %s → %s: %d agents", source_team_id[:12], target_team_id[:12], len(cloned))
    return cloned


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _calc_win_rate(success: int, failure: int) -> float:
    total = (success or 0) + (failure or 0)
    if total == 0:
        return 0.0
    return ((success or 0) / total) * 100

def _load_prompt_file(prompt_path: str) -> str:
    """Load a prompt file, checking multiple locations."""
    # Try as-is first
    if os.path.exists(prompt_path):
        with open(prompt_path, 'r') as f:
            return f.read()
    
    # Try in Prompts directory
    full_path = os.path.join(PROMPTS_DIR, prompt_path)
    if os.path.exists(full_path):
        with open(full_path, 'r') as f:
            content = f.read()
            # Strip YAML frontmatter if present
            if content.startswith("---"):
                parts = content.split("---", 2)
                return parts[2].strip() if len(parts) > 2 else content
            return content
    
    return ""


def _search_registry(task_description: str, team_id: str = None, board_seat: str = None, db_path: str = None) -> Optional[Dict]:
    """Search registry for best agent match by capability/skill overlap."""
    conn = get_db(db_path)
    
    query = "SELECT agent_id, agent_name, capabilities, metadata, success_count, total_requests FROM agent_registry WHERE status = 'active'"
    params = []
    
    if team_id:
        query += " AND team_id = ?"
        params.append(team_id)
    if board_seat:
        query += " AND board_seat = ?"
        params.append(board_seat)
    
    rows = conn.execute(query, params).fetchall()
    conn.close()
    
    if not rows:
        return None
    
    task_words = set(task_description.lower().split())
    best = None
    best_score = 0
    
    for row in rows:
        search_text = f"{row['agent_name']} {row['capabilities'] or ''}"
        try:
            meta = json.loads(row['metadata'] or '{}')
            search_text += f" {meta.get('domain', '')} {' '.join(meta.get('knowledge_base', []))}"
        except (json.JSONDecodeError, TypeError):
            pass
        
        overlap = len(task_words & set(search_text.lower().split()))
        # Boost by performance
        if row['total_requests'] and row['total_requests'] > 0:
            win_rate = (row['success_count'] or 0) / row['total_requests']
            overlap += win_rate * 2  # Performance bonus
        
        if overlap > best_score:
            best_score = overlap
            best = dict(row)
    
    if best_score >= 2:
        return best
    return None


def _ensure_registered(agent_data: Dict, team_id: str = None, model: str = None, db_path: str = None):
    """Ensure an agent from AgentBuilder is fully registered with model/team."""
    conn = get_db(db_path)
    agent_id = agent_data.get("agent_id")
    if not agent_id:
        conn.close()
        return
    
    updates = []
    params = []
    
    if team_id:
        updates.append("team_id = ?")
        params.append(team_id)
    if model:
        updates.append("model = ?")
        params.append(model)
    
    if updates:
        updates.append("updated_at = ?")
        params.append(time.time())
        params.append(agent_id)
        conn.execute(f"UPDATE agent_registry SET {', '.join(updates)} WHERE agent_id = ?", params)
        conn.commit()
    
    conn.close()
