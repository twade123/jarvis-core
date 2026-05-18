#!/usr/bin/env python3
"""
vault_index_agents.py — Index ALL agent prompts and skills into the vault.

Runs on startup or manually. Ensures the vault is the single source of truth
for every agent definition in the system:

Sources indexed:
1. OpenClaw skills  (~/.agents/skills/**/SKILL.md)
2. Claude Code agents (.claude/agents/*.md)
3. Trading agents (knowledge/agents/**/profile.md — already exist)

After indexing, every agent's learnings.md is linked to their definition.
The vault becomes the one place to find any agent: what it does, what it's learned.
"""

import os
import re
import sqlite3
import logging
from datetime import datetime
from pathlib import Path

logger = logging.getLogger("vault_index_agents")

VAULT_DIR     = Path(__file__).parent
JARVIS_DIR    = VAULT_DIR.parent
SKILLS_DIR    = JARVIS_DIR / ".agents" / "skills"
CLAUDE_AGENTS = JARVIS_DIR / ".claude" / "agents"
INDEX_DB      = VAULT_DIR / "_index.db"
NOW           = datetime.now().isoformat(timespec='seconds')

FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)


def parse_frontmatter(text: str) -> dict:
    m = FRONTMATTER_RE.match(text)
    if not m:
        return {}
    fm = {}
    for line in m.group(1).splitlines():
        if ":" in line:
            k, _, v = line.partition(":")
            fm[k.strip()] = v.strip().strip('"').strip("'")
    return fm


def upsert_file(cur, path: str, title: str, file_type: str):
    cur.execute("SELECT id FROM files WHERE path=?", (path,))
    row = cur.fetchone()
    if row:
        cur.execute("UPDATE files SET title=?, file_type=?, updated_at=? WHERE path=?",
                    (title, file_type, NOW, path))
        return row[0]
    else:
        cur.execute("""INSERT INTO files (path, title, file_type, created_at, updated_at, status)
                       VALUES (?,?,?,?,?,'active')""",
                    (path, title, file_type, NOW, NOW))
        return cur.lastrowid


def index_openclaw_skills(cur):
    """Index OpenClaw SKILL.md files → vault path skills/{name}.md"""
    if not SKILLS_DIR.exists():
        logger.warning("OpenClaw skills dir not found: %s", SKILLS_DIR)
        return 0

    count = 0
    for skill_dir in sorted(SKILLS_DIR.iterdir()):
        skill_md = skill_dir / "SKILL.md"
        if not skill_md.exists():
            continue

        text = skill_md.read_text(errors="replace")
        fm = parse_frontmatter(text)
        name = fm.get("name") or skill_dir.name
        desc = fm.get("description", "")[:200]

        # Write a vault copy in skills/
        vault_skill_path = VAULT_DIR / "skills" / f"{skill_dir.name}.md"
        vault_skill_path.parent.mkdir(parents=True, exist_ok=True)
        vault_rel = f"skills/{skill_dir.name}.md"

        # Only rewrite if it doesn't exist or source is newer
        if not vault_skill_path.exists():
            vault_skill_path.write_text(text)

        upsert_file(cur, vault_rel, name, "skill")
        count += 1

    logger.info("Indexed %d OpenClaw skills", count)
    return count


def index_claude_code_agents(cur):
    """Index .claude/agents/*.md → vault path agents/claude-code/{name}.md"""
    if not CLAUDE_AGENTS.exists():
        logger.warning("Claude agents dir not found: %s", CLAUDE_AGENTS)
        return 0

    count = 0
    for agent_file in sorted(CLAUDE_AGENTS.glob("*.md")):
        text = agent_file.read_text(errors="replace")
        fm = parse_frontmatter(text)
        name = fm.get("name") or agent_file.stem
        desc = fm.get("description", "")[:200]

        # Write into vault
        vault_agent_dir = VAULT_DIR / "agents" / "claude-code"
        vault_agent_dir.mkdir(parents=True, exist_ok=True)
        vault_path = vault_agent_dir / agent_file.name
        vault_rel = f"agents/claude-code/{agent_file.name}"

        vault_path.write_text(text)

        upsert_file(cur, vault_rel, name, "agent_definition")

        # Ensure learnings.md exists for this agent
        learnings_path = vault_agent_dir / f"{agent_file.stem}-learnings.md"
        learnings_rel = f"agents/claude-code/{agent_file.stem}-learnings.md"
        if not learnings_path.exists():
            learnings_path.write_text(f"""---
type: pattern
agent: {name}
created: {NOW}
updated: {NOW}
tags: [claude-code, {agent_file.stem}]
status: active
---

# {name} — Learnings

*No learnings yet. After completing tasks, write here:*
```bash
python3 ~/jarvis/knowledge/vault_cli.py --agent "claude-code" --type "note" --summary "..." --context "..."
```
""")
            upsert_file(cur, learnings_rel, f"{name} learnings", "pattern")

        count += 1

    logger.info("Indexed %d Claude Code agents", count)
    return count


def run():
    conn = sqlite3.connect(str(INDEX_DB), isolation_level=None)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    skills_count  = index_openclaw_skills(cur)
    agents_count  = index_claude_code_agents(cur)
    conn.commit()
    conn.close()

    print(f"✅ Vault index complete — {skills_count} skills, {agents_count} Claude Code agents")

    # Re-run the full indexer to update FTS
    try:
        from knowledge.indexer import run as reindex
        reindex()
    except Exception as e:
        logger.warning("FTS reindex failed: %s", e)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run()
