"""
Vault Table of Contents — Generates a lightweight knowledge index for agent system prompts.

Every agent gets a TOC in its system prompt so it knows what knowledge is available
in the vault. The agent's LLM reasoning decides what to pull — we don't pre-select.

The TOC is:
- Workspace-scoped (forex agents see forex knowledge, healthcare sees healthcare)
- Agent-scoped (validator sees its learnings + team knowledge)
- Cached (rebuilt only when vault changes)
- Small (~500-800 tokens) — fits in any system prompt without bloat

Usage:
    from knowledge.vault_toc import VaultTOC
    toc = VaultTOC("forex-trading-team", "validator")
    toc_text = toc.generate()  # Ready to inject into system prompt
"""

import os
import sqlite3
from datetime import datetime
from typing import Dict, List, Optional

VAULT_ROOT = os.path.dirname(__file__)
VAULT_DB = os.path.join(VAULT_ROOT, "_index.db")

# Cache: workspace+agent → (toc_text, generated_at)
_toc_cache: Dict[str, tuple] = {}
_CACHE_TTL_SECONDS = 300  # Rebuild every 5 min max


class VaultTOC:
    """Generates a table of contents for the vault, scoped to workspace + agent."""

    def __init__(self, workspace_id: str = None, agent_name: str = None,
                 db_path: str = None):
        self.workspace_id = workspace_id
        self.agent_name = agent_name
        self.db_path = db_path or VAULT_DB

    def generate(self, force: bool = False) -> str:
        """Generate the TOC text. Returns cached version if fresh.

        Returns a markdown string ready to inject into a system prompt.
        """
        cache_key = f"{self.workspace_id}:{self.agent_name}"
        if not force and cache_key in _toc_cache:
            text, ts = _toc_cache[cache_key]
            if (datetime.now() - ts).total_seconds() < _CACHE_TTL_SECONDS:
                return text

        toc = self._build_toc()
        _toc_cache[cache_key] = (toc, datetime.now())
        return toc

    def _build_toc(self) -> str:
        """Build the TOC from the vault index."""
        conn = sqlite3.connect(self.db_path, timeout=5, isolation_level=None)
        sections = []

        # 1. Agent's own knowledge
        if self.agent_name:
            sections.append(self._agent_section(conn))

        # 2. Team agents (other agents in this workspace)
        sections.append(self._team_section(conn))

        # 3. Trading knowledge / domain education
        sections.append(self._education_section(conn))

        # 4. Collective knowledge (patterns, retrospectives)
        sections.append(self._collective_section(conn))

        # 5. Image catalog summary
        sections.append(self._image_section(conn))

        # 6. Skills relevant to this agent
        if self.agent_name:
            sections.append(self._skills_section(conn))

        conn.close()

        header = "## YOUR KNOWLEDGE VAULT\n"
        header += "You have access to the following knowledge. Use your reasoning to decide what you need based on what you see.\n"
        header += "To reference a section, cite it by name in your reasoning.\n\n"

        body = "\n".join(s for s in sections if s)
        return header + body

    def _agent_section(self, conn) -> str:
        """This agent's own prompt, learnings, profile."""
        agent_dir = os.path.join(VAULT_ROOT, "agents", self.agent_name)
        if not os.path.isdir(agent_dir):
            return ""

        files = []
        for f in sorted(os.listdir(agent_dir)):
            if f.endswith(".md"):
                path = os.path.join(agent_dir, f)
                size = os.path.getsize(path)
                name = f.replace(".md", "")
                # Read first line for description
                desc = ""
                with open(path) as fh:
                    for line in fh:
                        line = line.strip()
                        if line and not line.startswith("---") and not line.startswith("#"):
                            desc = line[:80]
                            break
                files.append(f"  - **{name}** ({size//1024}KB): {desc}")

        if not files:
            return ""

        return f"### Your Knowledge (agents/{self.agent_name}/)\n" + "\n".join(files) + "\n"

    def _team_section(self, conn) -> str:
        """Other agents on the team with learnings."""
        # Get the workspace's agents from README
        ws_readme = os.path.join(VAULT_ROOT, "workspaces",
                                  self.workspace_id or "", "README.md")
        team_agents = []
        if os.path.exists(ws_readme):
            with open(ws_readme) as f:
                in_agents = False
                for line in f:
                    if "## Agents" in line:
                        in_agents = True
                        continue
                    if in_agents and line.startswith("##"):
                        break
                    if in_agents and "**" in line:
                        # Extract agent name from "1. **oanda_data** — description"
                        parts = line.split("**")
                        if len(parts) >= 2:
                            name = parts[1].strip()
                            if name != self.agent_name:
                                team_agents.append(name)

        if not team_agents:
            return ""

        lines = ["### Team Agent Knowledge"]
        for agent in team_agents:
            agent_dir = os.path.join(VAULT_ROOT, "agents", agent)
            if os.path.isdir(agent_dir):
                has_learnings = os.path.exists(os.path.join(agent_dir, "learnings.md"))
                has_prompt = os.path.exists(os.path.join(agent_dir, "prompt.md"))
                if has_learnings or has_prompt:
                    parts = []
                    if has_prompt:
                        parts.append("prompt")
                    if has_learnings:
                        parts.append("learnings")
                    lines.append(f"  - **{agent}**: {', '.join(parts)}")

        return "\n".join(lines) + "\n" if len(lines) > 1 else ""

    def _education_section(self, conn) -> str:
        """Education/knowledge files for the domain."""
        edu_dir = os.path.join(VAULT_ROOT, "collective", "trading-knowledge")
        if not os.path.isdir(edu_dir):
            return ""

        lines = ["### Domain Knowledge (collective/trading-knowledge/)"]

        # Core files
        for f in sorted(os.listdir(edu_dir)):
            if f.endswith(".md"):
                path = os.path.join(edu_dir, f)
                size = os.path.getsize(path)
                name = f.replace(".md", "")
                # Get description from frontmatter or first heading
                desc = self._get_file_description(path)
                lines.append(f"  - **{name}** ({size//1024}KB): {desc}")

        # Education subdirectory
        edu_sub = os.path.join(edu_dir, "education")
        if os.path.isdir(edu_sub):
            lines.append("  **Education Library:**")
            for f in sorted(os.listdir(edu_sub)):
                if f.endswith(".md"):
                    path = os.path.join(edu_sub, f)
                    size = os.path.getsize(path)
                    name = f.replace(".md", "")
                    desc = self._get_file_description(path)
                    lines.append(f"    - **{name}** ({size//1024}KB): {desc}")

        return "\n".join(lines) + "\n"

    def _collective_section(self, conn) -> str:
        """Collective patterns and retrospectives."""
        lines = ["### Collective Memory"]

        # Patterns
        patterns_dir = os.path.join(VAULT_ROOT, "collective", "patterns")
        if os.path.isdir(patterns_dir):
            pattern_files = [f for f in os.listdir(patterns_dir) if f.endswith(".md")]
            if pattern_files:
                latest = sorted(pattern_files)[-1]
                lines.append(f"  - **patterns/**: {len(pattern_files)} daily pattern files (latest: {latest.replace('.md','')})")

        # Retrospectives
        retro_dir = os.path.join(VAULT_ROOT, "collective", "scout-retrospective")
        if os.path.isdir(retro_dir):
            retro_files = [f for f in os.listdir(retro_dir) if f.endswith(".md")]
            if retro_files:
                latest = sorted(retro_files)[-1]
                lines.append(f"  - **scout-retrospective/**: {len(retro_files)} daily retros (latest: {latest.replace('.md','')})")

        # Boardroom decisions
        decisions_dir = os.path.join(VAULT_ROOT, "boardroom", "decisions")
        if os.path.isdir(decisions_dir):
            dec_files = [f for f in os.listdir(decisions_dir) if f.endswith(".md")]
            if dec_files:
                lines.append(f"  - **boardroom/decisions/**: {len(dec_files)} strategic decisions")

        return "\n".join(lines) + "\n" if len(lines) > 1 else ""

    def _image_section(self, conn) -> str:
        """Image catalog summary."""
        try:
            total = conn.execute("SELECT COUNT(*) FROM image_catalog").fetchone()[0]
            if total == 0:
                return ""

            sources = conn.execute(
                "SELECT source, COUNT(*) FROM image_catalog GROUP BY source"
            ).fetchall()

            lines = [f"### Teaching Image Library ({total} images)"]
            for src, cnt in sources:
                labels = {
                    "teaching": "Curated TRADE/SKIP examples with descriptions",
                    "pattern_reference": "Chart pattern reference images (S1-S20)",
                    "user_annotation": "Your submitted annotated charts",
                    "labeled_outcome": "Past trades with WIN/LOSS outcomes",
                }
                desc = labels.get(src, src)
                lines.append(f"  - **{src}**: {cnt} images — {desc}")

            lines.append("  *Search by: setup_type, pattern_name, fan_state, direction, pair*")

            return "\n".join(lines) + "\n"
        except Exception:
            return ""

    def _skills_section(self, conn) -> str:
        """Skills relevant to this agent's domain."""
        if not self.agent_name:
            return ""

        # Find skills that mention this agent or trading-related keywords
        skills_dir = os.path.join(VAULT_ROOT, "skills")
        if not os.path.isdir(skills_dir):
            return ""

        # Filter to domain-relevant skills (jarvis-* for trading)
        relevant = []
        for f in sorted(os.listdir(skills_dir)):
            if not f.endswith(".md"):
                continue
            name = f.replace(".md", "")
            # Include jarvis-* skills (trading pipeline) and agent-specific
            if name.startswith("jarvis-") and any(kw in name for kw in [
                "validator", "trade", "candle", "chart", "indicator", "confluence",
                "fetch_candles", "news", "weather", "intelligence", "execution",
                "monitor", "reporter", "cycle", "knowledge", "alignment",
            ]):
                relevant.append(name)

        if not relevant:
            return ""

        lines = [f"### Available Skills ({len(relevant)} trading-related)"]
        for name in relevant[:15]:  # Cap at 15 to keep TOC small
            lines.append(f"  - {name}")
        if len(relevant) > 15:
            lines.append(f"  - ... and {len(relevant) - 15} more")

        return "\n".join(lines) + "\n"

    def _get_file_description(self, path: str) -> str:
        """Extract a short description from a file's frontmatter or first heading."""
        try:
            with open(path) as f:
                content = f.read(500)

            # Check frontmatter for description
            if content.startswith("---"):
                end = content.find("---", 3)
                if end != -1:
                    fm = content[3:end]
                    for line in fm.split("\n"):
                        if line.strip().startswith("description:"):
                            return line.split(":", 1)[1].strip()[:80]

            # Fall back to first heading or non-empty line
            for line in content.split("\n"):
                line = line.strip()
                if line.startswith("# "):
                    return line[2:].strip()[:80]
                if line and not line.startswith("---"):
                    return line[:80]
        except Exception:
            pass
        return ""


def generate_toc(workspace_id: str = None, agent_name: str = None) -> str:
    """Convenience function to generate a TOC string."""
    return VaultTOC(workspace_id, agent_name).generate()
