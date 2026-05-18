"""
Skill Loader — Imports skills into the knowledge vault and maps them to board seats.

Skills come from three sources:
1. OpenClaw SKILL.md files (~85 skills)
2. Jarvis agent_skills DB entries (~58 skills, 275 with duplicates)
3. Jarvis skill_file: entries (MCP docs, team docs)

Board seat mapping:
- CTO: coding, infra, MCP, agent development, testing, deployment
- CSO: research, analysis, strategy, competitive intel, planning
- CRO: audit, compliance, risk, security, contract review, legal
- CDO: data, SQL, visualization, dashboards, spreadsheets, statistics

Skills are stored in knowledge/skills/ as markdown with YAML frontmatter.
vault_writer.refine_learning() handles Opus corrections over time.
"""

import os
import re
import json
import sqlite3
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set

logger = logging.getLogger(__name__)

VAULT_SKILLS_DIR = Path(__file__).parent / "skills"
OPENCLAW_SKILLS_DIR = Path(__file__).parent.parent / ".agents" / "skills"
BOARDROOM_DB = Path(__file__).parent.parent / "Database" / "boardroom.db"

# ── Board seat → skill mapping by keyword patterns ──────────────
SEAT_PATTERNS = {
    "CTO": [
        "code", "coding", "develop", "agent", "hook", "plugin", "mcp",
        "frontend", "webapp", "testing", "github", "stripe", "fhir",
        "nextflow", "scvi", "skill-creator", "command", "claude-",
        "execution", "fetch_candles", "fetch_multi", "place_market",
        "get_account", "get_current", "get_instrument", "get_position",
        "oanda_data", "indicators", "chart_patterns", "candlestick",
    ],
    "CSO": [
        "research", "competitive", "analysis", "strategy", "planning",
        "campaign", "content", "brand", "call-prep", "daily-briefing",
        "account-research", "intelligence", "synthesis", "feature-spec",
        "roadmap", "stakeholder", "user-research", "metrics",
        "gather_intelligence", "forex_news", "query_news", "commodity",
        "knowledge_store", "intelligence_domain",
    ],
    "CRO": [
        "audit", "compliance", "risk", "security", "contract", "legal",
        "nda", "canned-response", "escalation", "healthcheck",
        "close-management", "reconciliation", "variance",
        "validation", "quality_control", "risk_status", "monitor_open",
        "check_sl_tp", "check_spread", "should_escalate",
        "trade_validator", "run_full_validation", "validator_domain",
    ],
    "CDO": [
        "data", "sql", "visualization", "dashboard", "xlsx", "csv",
        "statistical", "exploration", "pdf", "docx", "pptx",
        "journal-entry", "financial", "instrument-data",
        "confluence_scorer", "run_statistical", "log_trade",
        "trade_logger", "reporter_domain", "generate_cycle_summary",
        "knowledge_store.store", "knowledge_store.get",
    ],
}

# Skills that ALL board members should see
SHARED_SKILLS = [
    "memory-management", "task-management", "doc-coauthoring",
    "internal-comms", "knowledge-management",
    "cycle_orchestration", "evaluate_cycle_readiness",
    "process_operator_command", "make_trade_decision",
]


def _classify_skill(name: str, description: str = "") -> List[str]:
    """Map a skill name to one or more board seats."""
    text = f"{name} {description}".lower()
    seats = []
    for seat, patterns in SEAT_PATTERNS.items():
        for pat in patterns:
            if pat.lower() in text:
                seats.append(seat)
                break
    # If no match, assign to CDO (data catch-all)
    if not seats:
        seats = ["CDO"]
    return seats


def import_openclaw_skills() -> int:
    """Import OpenClaw SKILL.md files into the vault."""
    VAULT_SKILLS_DIR.mkdir(parents=True, exist_ok=True)
    imported = 0

    if not OPENCLAW_SKILLS_DIR.exists():
        logger.warning("OpenClaw skills dir not found: %s", OPENCLAW_SKILLS_DIR)
        return 0

    for skill_dir in sorted(OPENCLAW_SKILLS_DIR.iterdir()):
        skill_md = skill_dir / "SKILL.md"
        if not skill_md.exists():
            continue

        name = skill_dir.name
        content = skill_md.read_text(encoding="utf-8", errors="replace")

        # Extract first paragraph as description
        lines = content.strip().split("\n")
        desc_lines = []
        for line in lines:
            if line.startswith("#"):
                continue
            if line.strip() == "" and desc_lines:
                break
            if line.strip():
                desc_lines.append(line.strip())
        description = " ".join(desc_lines)[:200]

        seats = _classify_skill(name, description)

        # Build vault entry with YAML frontmatter
        vault_path = VAULT_SKILLS_DIR / f"{name}.md"

        # Don't overwrite if already exists (preserves refinements)
        if vault_path.exists():
            continue

        frontmatter = (
            f"---\n"
            f"type: skill\n"
            f"source: openclaw\n"
            f"skill_name: {name}\n"
            f"board_seats: [{', '.join(seats)}]\n"
            f"imported_at: {datetime.utcnow().isoformat()}Z\n"
            f"refinement_count: 0\n"
            f"---\n\n"
        )
        vault_path.write_text(frontmatter + content, encoding="utf-8")
        imported += 1

    logger.info("Imported %d OpenClaw skills to vault", imported)
    return imported


def import_jarvis_skills() -> int:
    """Import Jarvis agent_skills DB entries into the vault."""
    VAULT_SKILLS_DIR.mkdir(parents=True, exist_ok=True)
    imported = 0

    if not BOARDROOM_DB.exists():
        logger.warning("boardroom.db not found: %s", BOARDROOM_DB)
        return 0

    conn = sqlite3.connect(str(BOARDROOM_DB), isolation_level=None)
    conn.row_factory = sqlite3.Row

    # Get unique skills with their definitions
    rows = conn.execute("""
        SELECT skill_name, skill_type, definition_json,
               AVG(performance_score) as avg_score,
               COUNT(*) as agent_count
        FROM agent_skills
        GROUP BY skill_name
        ORDER BY skill_name
    """).fetchall()

    for row in rows:
        name = row["skill_name"]
        safe_name = re.sub(r"[^a-zA-Z0-9_.-]", "_", name)
        vault_path = VAULT_SKILLS_DIR / f"jarvis-{safe_name}.md"

        if vault_path.exists():
            continue

        definition = row["definition_json"] or "{}"
        try:
            defn = json.loads(definition) if isinstance(definition, str) else definition
        except (json.JSONDecodeError, TypeError):
            defn = {"raw": str(definition)[:500]}

        seats = _classify_skill(name, json.dumps(defn)[:300])
        skill_type = row["skill_type"] or "unknown"
        avg_score = row["avg_score"] or 0

        # Build description from definition
        desc_parts = []
        if isinstance(defn, dict):
            if "description" in defn:
                desc_parts.append(defn["description"])
            if "parameters" in defn:
                params = defn["parameters"]
                if isinstance(params, dict):
                    desc_parts.append(f"Parameters: {', '.join(params.keys())}")

        description = "\n".join(desc_parts) if desc_parts else f"Jarvis skill: {name}"

        frontmatter = (
            f"---\n"
            f"type: skill\n"
            f"source: jarvis\n"
            f"skill_name: {name}\n"
            f"skill_type: {skill_type}\n"
            f"board_seats: [{', '.join(seats)}]\n"
            f"avg_performance: {avg_score:.1f}\n"
            f"agent_count: {row['agent_count']}\n"
            f"imported_at: {datetime.utcnow().isoformat()}Z\n"
            f"refinement_count: 0\n"
            f"---\n\n"
            f"# {name}\n\n"
            f"{description}\n\n"
            f"## Definition\n\n"
            f"```json\n{json.dumps(defn, indent=2)[:2000]}\n```\n"
        )
        vault_path.write_text(frontmatter, encoding="utf-8")
        imported += 1

    conn.close()
    logger.info("Imported %d Jarvis skills to vault", imported)
    return imported


def get_skills_for_seat(seat: str, max_skills: int = 20) -> List[Dict]:
    """Get relevant skill summaries for a board seat.

    Returns list of {name, description, source, path} dicts,
    prioritized by relevance and performance score.
    """
    if not VAULT_SKILLS_DIR.exists():
        return []

    skills = []
    for md_file in sorted(VAULT_SKILLS_DIR.glob("*.md")):
        content = md_file.read_text(encoding="utf-8", errors="replace")

        # Parse frontmatter
        if content.startswith("---"):
            end = content.find("---", 3)
            if end > 0:
                fm = content[3:end].strip()
                body = content[end + 3:].strip()
            else:
                fm, body = "", content
        else:
            fm, body = "", content

        # Check seat assignment
        if f"board_seats:" in fm:
            seats_line = [l for l in fm.split("\n") if "board_seats:" in l]
            if seats_line:
                if seat not in seats_line[0] and "ALL" not in seats_line[0]:
                    continue

        # Extract name and first meaningful line
        name = md_file.stem
        source = "openclaw" if "source: openclaw" in fm else "jarvis"
        
        # Get first non-header, non-empty, non-frontmatter line as description
        desc = ""
        in_frontmatter = False
        for line in body.split("\n"):
            stripped = line.strip()
            if stripped == "---":
                in_frontmatter = not in_frontmatter
                continue
            if in_frontmatter:
                continue
            if stripped and not stripped.startswith("#") and not stripped.startswith("```"):
                desc = stripped[:150]
                break

        perf = 0.0
        perf_match = re.search(r"avg_performance:\s*([\d.]+)", fm)
        if perf_match:
            perf = float(perf_match.group(1))

        skills.append({
            "name": name,
            "description": desc,
            "source": source,
            "path": str(md_file),
            "performance": perf,
        })

    # Sort: higher performance first, then alphabetical
    skills.sort(key=lambda s: (-s["performance"], s["name"]))
    return skills[:max_skills]


def build_skill_context(seat: str, task: str = "", max_chars: int = 4000) -> str:
    """Build a skill context block to inject into a board member's prompt.

    Returns a formatted string listing available skills and brief descriptions,
    staying within max_chars to avoid context bloat.
    """
    skills = get_skills_for_seat(seat)
    if not skills:
        return ""

    lines = [
        f"## Available Skills ({seat} domain)\n",
        "You can reference these skills and request their execution:\n",
    ]
    char_count = sum(len(l) for l in lines)

    for s in skills:
        line = f"- **{s['name']}**: {s['description']}\n"
        if char_count + len(line) > max_chars:
            lines.append(f"\n... and {len(skills) - len(lines) + 2} more skills available.\n")
            break
        lines.append(line)
        char_count += len(line)

    return "".join(lines)


def get_full_skill_content(skill_name: str) -> Optional[str]:
    """Load full skill content from vault (for deep-dive during deliberation)."""
    # Try exact match
    path = VAULT_SKILLS_DIR / f"{skill_name}.md"
    if path.exists():
        return path.read_text(encoding="utf-8", errors="replace")

    # Try jarvis- prefix
    path = VAULT_SKILLS_DIR / f"jarvis-{skill_name}.md"
    if path.exists():
        return path.read_text(encoding="utf-8", errors="replace")

    # Fuzzy match
    for md_file in VAULT_SKILLS_DIR.glob("*.md"):
        if skill_name.lower() in md_file.stem.lower():
            return md_file.read_text(encoding="utf-8", errors="replace")

    return None


def import_all() -> Dict[str, int]:
    """Import all skills from all sources."""
    results = {
        "openclaw": import_openclaw_skills(),
        "jarvis": import_jarvis_skills(),
    }
    total = sum(results.values())
    logger.info("Total skills imported to vault: %d", total)
    return results


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    results = import_all()
    print(f"\nImported: {results}")
    print(f"\nSkills per seat:")
    for seat in ["CTO", "CSO", "CRO", "CDO"]:
        skills = get_skills_for_seat(seat)
        print(f"  {seat}: {len(skills)} skills")
        for s in skills[:5]:
            print(f"    - {s['name']}: {s['description'][:60]}")
