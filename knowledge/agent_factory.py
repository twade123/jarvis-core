"""
Agent Factory — Bridge between vault skills and AgentBuilder.

Reads skills from the vault, maps them to board seats, and uses
AgentBuilder.create_agent_simple() to create properly registered agents.

All agent prompts live in knowledge/agents/ (the vault) so they
evolve with the learning loop:
  Skill → AgentBuilder → prompt in vault → agent uses it
    → Opus corrects → vault_writer.refine_learning() updates prompt
    → next task uses improved prompt → training data captured

Workspace model:
  PROJECT WORKSPACE
  ├── Boardroom (CTO, CSO, CRO, CDO, Opus)
  ├── CTO Team → deploys agents from their roster
  ├── CSO Team → deploys agents from their roster  
  ├── CRO Team → deploys agents from their roster
  └── CDO Team → deploys agents from their roster
  All communicate → all progress tracked in workspace
"""

import json
import logging
import os
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

BOARDROOM_DB = Path(__file__).parent.parent / "Database" / "v2" / "agents.db"
VAULT_SKILLS_DIR = Path(__file__).parent / "skills"
VAULT_AGENTS_DIR = Path(__file__).parent / "agents"  # All prompts live here


def _skill_to_agent_name(skill_name: str) -> str:
    """Convert a skill name to a clean agent name."""
    name = skill_name.replace("jarvis-", "").replace("skill_file_", "")
    return re.sub(r"[-_.]", " ", name).strip().title().replace(" ", "")


def _skill_to_agent_id(skill_name: str) -> str:
    """Convert a skill name to a unique agent_id."""
    clean = skill_name.replace("jarvis-", "").replace("skill_file_", "")
    return f"skill_{re.sub(r'[^a-zA-Z0-9]', '_', clean).lower()}"


def _extract_seat_from_frontmatter(content: str) -> List[str]:
    """Extract board_seats from skill file frontmatter."""
    if not content.startswith("---"):
        return ["CDO"]
    end = content.find("---", 3)
    if end < 0:
        return ["CDO"]
    fm = content[3:end]
    match = re.search(r"board_seats:\s*\[([^\]]+)\]", fm)
    if match:
        return [s.strip() for s in match.group(1).split(",")]
    return ["CDO"]


def _extract_skill_body(content: str) -> str:
    """Strip frontmatter, return just the skill content."""
    if content.startswith("---"):
        end = content.find("---", 3)
        if end > 0:
            return content[end + 3:].strip()
    return content.strip()


def generate_agents_from_skills(use_agent_builder: bool = True, dry_run: bool = False) -> Dict:
    """Create agents for every skill in the vault.
    
    When use_agent_builder=True, calls AgentBuilder.create_agent_simple()
    which handles prompt generation, registry, and skill registration.
    
    When use_agent_builder=False, does direct DB insert (faster, simpler).
    """
    if not VAULT_SKILLS_DIR.exists():
        return {"created": 0, "skipped": 0, "errors": 0}

    VAULT_AGENTS_DIR.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(str(BOARDROOM_DB), isolation_level=None)
    existing_ids = set(
        r[0] for r in conn.execute(
            "SELECT agent_id FROM agent_registry WHERE agent_type = 'skill_agent'"
        ).fetchall()
    )

    # Try to load AgentBuilder
    builder = None
    if use_agent_builder:
        try:
            import sys
            sys.path.insert(0, str(Path(__file__).parent.parent))
            from Handler.handler_agent_builder import AgentBuilder, AgentSpecialization, AgentCapability
            builder = AgentBuilder()
            logger.info("Using AgentBuilder for agent creation")
        except Exception as e:
            logger.warning("AgentBuilder unavailable (%s), falling back to direct insert", e)
            builder = None

    stats = {"created": 0, "skipped": 0, "errors": 0, "by_seat": {}}
    agents_by_seat: Dict[str, List[str]] = {"CTO": [], "CSO": [], "CRO": [], "CDO": []}

    for md_file in sorted(VAULT_SKILLS_DIR.glob("*.md")):
        skill_name = md_file.stem
        agent_id = _skill_to_agent_id(skill_name)
        agent_name = _skill_to_agent_name(skill_name)

        if agent_id in existing_ids:
            stats["skipped"] += 1
            content = md_file.read_text(encoding="utf-8", errors="replace")
            for seat in _extract_seat_from_frontmatter(content):
                if seat in agents_by_seat:
                    agents_by_seat[seat].append(agent_id)
            continue

        try:
            content = md_file.read_text(encoding="utf-8", errors="replace")
            seats = _extract_seat_from_frontmatter(content)
            body = _extract_skill_body(content)
            primary_seat = seats[0] if seats else "CDO"

            if builder and not dry_run:
                # Use AgentBuilder — proper prompt generation + registry
                try:
                    specialization = AgentSpecialization(
                        domain=skill_name,
                        expertise_level=8,
                        capabilities=[AgentCapability.ANALYTICAL, AgentCapability.PROBLEM_SOLVING],
                        tools=[],
                        knowledge_base=[body[:2000]]  # Feed skill content as knowledge
                    )
                    result = builder.create_agent_simple(
                        name=agent_name,
                        agent_type="skill_agent",
                        specialization=specialization,
                    )
                    # Update board_seat (AgentBuilder doesn't know about seats)
                    if result.get("agent_id"):
                        conn.execute(
                            "UPDATE agent_registry SET board_seat = ?, prompt_focus = ? WHERE agent_id = ?",
                            (primary_seat, skill_name, result["agent_id"])
                        )
                    # Save prompt to vault
                    prompt = result.get("system_prompt", "")
                    if prompt:
                        prompt_path = VAULT_AGENTS_DIR / f"{agent_id}.md"
                        _write_vault_prompt(prompt_path, agent_name, primary_seat, skill_name, prompt)

                    stats["created"] += 1
                except Exception as e:
                    logger.warning("AgentBuilder failed for %s: %s, using direct insert", skill_name, e)
                    _direct_insert(conn, agent_id, agent_name, skill_name, seats, primary_seat, body, md_file)
                    stats["created"] += 1
            else:
                # Direct insert — simpler, no LLM call needed
                if not dry_run:
                    _direct_insert(conn, agent_id, agent_name, skill_name, seats, primary_seat, body, md_file)
                stats["created"] += 1

            for seat in seats:
                if seat in agents_by_seat:
                    agents_by_seat[seat].append(agent_id)

        except Exception as e:
            logger.error("Failed to create agent for %s: %s", skill_name, e)
            stats["errors"] += 1

    if not dry_run:
        conn.commit()
    conn.close()

    stats["by_seat"] = {k: len(v) for k, v in agents_by_seat.items()}
    return stats


def _write_vault_prompt(path: Path, agent_name: str, seat: str, skill_name: str, prompt: str):
    """Write an agent prompt to the vault with YAML frontmatter."""
    team_name = {"CTO": "Engineering", "CSO": "Strategy", "CRO": "Risk", "CDO": "Data"}.get(seat, "General")
    frontmatter = (
        f"---\n"
        f"type: agent_prompt\n"
        f"agent_name: {agent_name}\n"
        f"board_seat: {seat}\n"
        f"team: {team_name}\n"
        f"source_skill: {skill_name}\n"
        f"generated_at: {datetime.now(timezone.utc).isoformat()}Z\n"
        f"refinement_count: 0\n"
        f"---\n\n"
    )
    path.write_text(frontmatter + prompt, encoding="utf-8")


def _direct_insert(conn, agent_id, agent_name, skill_name, seats, primary_seat, body, md_file):
    """Direct DB insert when AgentBuilder is unavailable."""
    now = datetime.now(timezone.utc).isoformat()

    # Build prompt from skill content
    team_name = {"CTO": "Engineering & Technology", "CSO": "Strategy & Intelligence",
                 "CRO": "Risk & Compliance", "CDO": "Data & Analytics"}.get(primary_seat, "General")

    # Get summary from body
    summary_lines = []
    for line in body.split("\n"):
        stripped = line.strip()
        if stripped and not stripped.startswith("#") and not stripped.startswith("```") and stripped != "---":
            summary_lines.append(stripped)
            if len(summary_lines) >= 3:
                break
    summary = " ".join(summary_lines)[:300]

    prompt = (
        f"# {agent_name}\n\n"
        f"You are a specialized agent on the **{team_name} Team** (managed by the {primary_seat}).\n\n"
        f"## Your Expertise\n{summary}\n\n"
        f"## Your Role\n"
        f"- Execute tasks in your skill domain when assigned by your team lead ({primary_seat})\n"
        f"- Collaborate with other workspace agents — share findings, request help\n"
        f"- Report progress back through workspace communication\n"
        f"- Escalate to team lead when uncertain\n\n"
        f"## Domain Knowledge\n{body[:3000]}\n"
    )

    # Save prompt to vault
    prompt_path = VAULT_AGENTS_DIR / f"{agent_id}.md"
    _write_vault_prompt(prompt_path, agent_name, primary_seat, skill_name, prompt)

    conn.execute("""
        INSERT INTO agent_registry (
            agent_id, agent_name, agent_type, module_name,
            capabilities, status, created_at, updated_at,
            metadata, model, system_prompt_path,
            board_seat, prompt_focus
        ) VALUES (?, ?, 'skill_agent', 'knowledge.agent_factory',
            ?, 'available', ?, ?,
            ?, ?, ?, ?, ?)
    """, (
        agent_id, agent_name,
        json.dumps({"skill_name": skill_name, "seats": seats}),
        now, now,
        json.dumps({"source_skill": skill_name, "vault_path": str(md_file), "all_seats": seats}),
        None,  # model — uses team default
        str(prompt_path),
        primary_seat, skill_name,
    ))


# ── Team Management ─────────────────────────────────────────────

def get_team_roster(seat: str) -> List[Dict]:
    """Get all agents assigned to a board member's team."""
    conn = sqlite3.connect(str(BOARDROOM_DB), isolation_level=None)
    conn.row_factory = sqlite3.Row
    rows = conn.execute("""
        SELECT agent_id, agent_name, agent_type, status,
               prompt_focus, system_prompt_path,
               success_count, failure_count, avg_response_time
        FROM agent_registry
        WHERE board_seat = ?
        ORDER BY agent_name
    """, (seat,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_team_summary() -> Dict[str, Dict]:
    """Get a summary of all teams and their agent counts."""
    conn = sqlite3.connect(str(BOARDROOM_DB), isolation_level=None)
    summary = {}
    for seat in ["CTO", "CSO", "CRO", "CDO"]:
        total = conn.execute("SELECT COUNT(*) FROM agent_registry WHERE board_seat = ?", (seat,)).fetchone()[0]
        available = conn.execute("SELECT COUNT(*) FROM agent_registry WHERE board_seat = ? AND status = 'available'", (seat,)).fetchone()[0]
        skill_agents = conn.execute("SELECT COUNT(*) FROM agent_registry WHERE board_seat = ? AND agent_type = 'skill_agent'", (seat,)).fetchone()[0]
        summary[seat] = {"total": total, "available": available, "skill_agents": skill_agents}
    summary["unassigned"] = {"total": conn.execute("SELECT COUNT(*) FROM agent_registry WHERE board_seat IS NULL").fetchone()[0]}
    conn.close()
    return summary


def build_roster_context(seat: str, max_agents: int = 30) -> str:
    """Build context block showing a board member their team roster."""
    roster = get_team_roster(seat)
    if not roster:
        return ""
    lines = [f"## Your Team Roster ({seat})\n", f"You manage {len(roster)} agents. Deploy them into workspace tasks:\n"]
    for agent in roster[:max_agents]:
        name = agent["agent_name"]
        focus = agent.get("prompt_focus", "general")
        status = agent.get("status", "unknown")
        success = agent.get("success_count") or 0
        failure = agent.get("failure_count") or 0
        perf = f" | {success/(success+failure)*100:.0f}% ({success+failure} tasks)" if success + failure > 0 else ""
        lines.append(f"- **{name}** [{focus}] — {status}{perf}")
    if len(roster) > max_agents:
        lines.append(f"\n... and {len(roster) - max_agents} more agents.")
    return "\n".join(lines) + "\n"


def get_agent_prompt(agent_id: str) -> Optional[str]:
    """Load an agent's prompt from the vault."""
    path = VAULT_AGENTS_DIR / f"{agent_id}.md"
    if path.exists():
        content = path.read_text(encoding="utf-8", errors="replace")
        # Strip frontmatter
        if content.startswith("---"):
            end = content.find("---", 3)
            if end > 0:
                return content[end + 3:].strip()
        return content
    return None


def update_agent_prompt(agent_id: str, new_prompt: str) -> bool:
    """Update an agent's prompt in the vault (preserves frontmatter)."""
    path = VAULT_AGENTS_DIR / f"{agent_id}.md"
    if not path.exists():
        return False
    content = path.read_text(encoding="utf-8", errors="replace")
    if content.startswith("---"):
        end = content.find("---", 3)
        if end > 0:
            # Bump refinement count
            fm = content[3:end]
            count_match = re.search(r"refinement_count:\s*(\d+)", fm)
            if count_match:
                old_count = int(count_match.group(1))
                fm = fm.replace(f"refinement_count: {old_count}", f"refinement_count: {old_count + 1}")
            path.write_text(f"---\n{fm}---\n\n{new_prompt}", encoding="utf-8")
            return True
    path.write_text(new_prompt, encoding="utf-8")
    return True


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print("=== Agent Factory ===\n")

    # Use direct insert (no LLM needed) for bulk creation
    results = generate_agents_from_skills(use_agent_builder=False)
    print(f"Created: {results['created']}")
    print(f"Skipped: {results['skipped']}")
    print(f"Errors: {results['errors']}")
    print(f"By seat: {results.get('by_seat', {})}")

    print("\n=== Team Summary ===")
    for seat, data in get_team_summary().items():
        print(f"  {seat}: {data}")

    print("\n=== Vault Agent Prompts ===")
    prompt_count = len(list(VAULT_AGENTS_DIR.glob("skill_*.md")))
    print(f"  {prompt_count} agent prompts in knowledge/agents/")
