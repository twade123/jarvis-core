"""
Vault Knowledge Loader — Loads domain-specific knowledge from the vault based on workspace.

Generic loader that any handler can use. For the forex workspace, it loads the validator
prompt, learnings, thesis, setups, and relevant education. For a different workspace,
it loads different knowledge entirely.

Usage:
    from knowledge.vault_knowledge_loader import VaultKnowledgeLoader
    loader = VaultKnowledgeLoader("forex-trading-team")
    system_prompt = loader.load_system_prompt("validator")
    learnings = loader.load_learnings("validator")
    education = loader.load_relevant_education({"fan_state": "bearish_ordered", "pattern": "hammer"})
    images = loader.get_teaching_images({"setup_type": "fan_expansion", "direction": "SELL"})
"""

import json
import logging
import os
import sqlite3
import time
from pathlib import Path
from typing import Dict, List, Optional

VAULT_ROOT = os.path.dirname(__file__)  # knowledge/
VAULT_DB = os.path.join(VAULT_ROOT, "_index.db")

logger = logging.getLogger("vault_knowledge_loader")


def _audit_log(agent: str, action: str, query: str = None,
               files_accessed: list = None, context: str = None,
               workspace_id: str = None, duration_ms: float = None,
               pair: str = None, cycle_id: str = None):
    """Log a vault access to both the vault audit trail AND the flight recorder.

    The vault audit log is always written (vault's own DB).
    The flight recorder is optional — only available in the trading pipeline.
    """
    # 1. Vault audit log (always)
    try:
        conn = sqlite3.connect(VAULT_DB, timeout=3, isolation_level=None)
        conn.execute(
            "INSERT INTO vault_audit_log (agent, action, query, files_accessed, file_count, context, workspace_id, duration_ms) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (agent, action, query,
             json.dumps(files_accessed) if files_accessed else None,
             len(files_accessed) if files_accessed else 0,
             context, workspace_id, duration_ms)
        )
        conn.commit()
        conn.close()
    except Exception:
        pass

    # 2. Flight recorder (optional — only in trading pipeline)
    try:
        from flight_recorder import flight, FlightStage
        stage_map = {
            "load_system_prompt": FlightStage.VAULT_LOAD,
            "load_learnings": FlightStage.VAULT_LOAD,
            "load_domain_knowledge": FlightStage.VAULT_LOAD,
            "load_relevant_education": FlightStage.VAULT_QUERY,
            "get_teaching_images": FlightStage.VAULT_IMAGES,
        }
        stage = stage_map.get(action)
        if stage and flight:
            flight.record(
                stage=stage,
                pair=pair or "",
                cycle_id=cycle_id or "",
                data={
                    "agent": agent,
                    "action": action,
                    "query": query or "",
                    "files": files_accessed or [],
                    "file_count": len(files_accessed) if files_accessed else 0,
                },
                note=f"{action}: {context or ''}",
                duration_ms=duration_ms or 0,
            )
    except (ImportError, Exception):
        pass  # Flight recorder not available outside trading pipeline


class VaultKnowledgeLoader:
    """Loads domain-specific knowledge from the vault based on workspace context."""

    def __init__(self, workspace_id: str = None, vault_path: str = None,
                 pair: str = None, cycle_id: str = None):
        """
        Args:
            workspace_id: The workspace context (e.g., "forex-trading-team").
                          If None, loads generic/unscoped knowledge.
            vault_path: Override path to the vault root directory.
            pair: Trading pair for flight recorder logging (e.g., "EUR_USD").
            cycle_id: Cycle ID for flight recorder logging.
        """
        self.workspace_id = workspace_id
        self.vault_root = vault_path or VAULT_ROOT
        self.db_path = os.path.join(self.vault_root, "_index.db")
        self._cache = {}
        self._pair = pair
        self._cycle_id = cycle_id
        self._ws_config = self._load_workspace_config()

    def _load_workspace_config(self) -> Dict:
        """Load workspace config from its README.md frontmatter.

        Returns fields like validator_agent, knowledge_base from the YAML frontmatter.
        """
        if not self.workspace_id:
            return {}

        readme_path = os.path.join(
            self.vault_root, "workspaces", self.workspace_id, "README.md"
        )
        if not os.path.exists(readme_path):
            return {}

        with open(readme_path, "r") as f:
            content = f.read()

        if not content.startswith("---"):
            return {}

        end = content.find("---", 3)
        if end == -1:
            return {}

        frontmatter = content[3:end].strip()
        config = {}
        for line in frontmatter.split("\n"):
            if ":" in line:
                key, _, value = line.partition(":")
                key = key.strip()
                value = value.strip()
                # Strip brackets for list values
                if value.startswith("[") and value.endswith("]"):
                    value = [v.strip() for v in value[1:-1].split(",")]
                config[key] = value
        return config

    @property
    def validator_agent(self) -> str:
        """The agent name this workspace uses for validation.
        Defaults to 'validator' if not specified in workspace config."""
        return self._ws_config.get("validator_agent", "validator")

    @property
    def knowledge_base_path(self) -> Optional[str]:
        """The knowledge base directory for this workspace (relative to vault root)."""
        return self._ws_config.get("knowledge_base")

    def load_system_prompt(self, agent_name: str = None, include_toc: bool = True) -> Optional[str]:
        """Load the system prompt from knowledge/agents/{agent_name}/prompt.md.

        If agent_name is None, uses the workspace's configured validator_agent.
        When include_toc=True (default), appends the vault Table of Contents
        so the agent knows what knowledge is available and can reason about
        what to pull.

        Returns the full prompt text, or None if not found.
        """
        agent_name = agent_name or self.validator_agent
        cache_key = f"prompt:{agent_name}:toc={include_toc}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        prompt_path = os.path.join(self.vault_root, "agents", agent_name, "prompt.md")
        if not os.path.exists(prompt_path):
            return None

        with open(prompt_path, "r") as f:
            content = f.read()

        # Strip frontmatter if present
        if content.startswith("---"):
            end = content.find("---", 3)
            if end != -1:
                content = content[end + 3:].strip()

        # Append vault TOC so the agent knows what knowledge is available
        if include_toc:
            try:
                from knowledge.vault_toc import generate_toc
                toc = generate_toc(self.workspace_id, agent_name)
                if toc:
                    content += f"\n\n---\n\n{toc}"
            except Exception:
                pass  # TOC is nice-to-have, don't fail the prompt load

        self._cache[cache_key] = content
        _audit_log(
            agent=agent_name, action="load_system_prompt",
            files_accessed=[f"agents/{agent_name}/prompt.md"],
            context=f"{len(content)} chars, toc={'yes' if include_toc else 'no'}",
            workspace_id=self.workspace_id,
            pair=self._pair, cycle_id=self._cycle_id,
        )
        return content

    def load_learnings(self, agent_name: str = None) -> Optional[str]:
        """Load recent learnings from knowledge/agents/{agent_name}/learnings.md.

        If agent_name is None, uses the workspace's configured validator_agent.
        Returns formatted learnings text, or None if not found.
        """
        agent_name = agent_name or self.validator_agent
        cache_key = f"learnings:{agent_name}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        path = os.path.join(self.vault_root, "agents", agent_name, "learnings.md")
        if not os.path.exists(path):
            return None

        with open(path, "r") as f:
            content = f.read()

        if content.startswith("---"):
            end = content.find("---", 3)
            if end != -1:
                content = content[end + 3:].strip()

        self._cache[cache_key] = content
        _audit_log(
            agent=agent_name, action="load_learnings",
            files_accessed=[f"agents/{agent_name}/learnings.md"],
            context=f"{len(content)} chars",
            workspace_id=self.workspace_id,
            pair=self._pair, cycle_id=self._cycle_id,
        )
        return content

    def load_domain_knowledge(self) -> Dict[str, str]:
        """Load workspace-scoped knowledge (thesis, setups, education files).

        For forex-trading-team: loads thesis_definition, setup_knowledge,
        and all education/*.md files.

        Returns dict mapping topic name to content.
        """
        cache_key = f"domain:{self.workspace_id}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        knowledge = {}
        trading_knowledge_dir = os.path.join(
            self.vault_root, "collective", "trading-knowledge"
        )

        # Load core trading knowledge files
        for filename in ["thesis_definition.md", "setup_knowledge.md"]:
            filepath = os.path.join(trading_knowledge_dir, filename)
            if os.path.exists(filepath):
                with open(filepath, "r") as f:
                    content = f.read()
                # Strip frontmatter
                if content.startswith("---"):
                    end = content.find("---", 3)
                    if end != -1:
                        content = content[end + 3:].strip()
                key = filename.replace(".md", "")
                knowledge[key] = content

        # Load education files
        education_dir = os.path.join(trading_knowledge_dir, "education")
        if os.path.isdir(education_dir):
            for filename in sorted(os.listdir(education_dir)):
                if filename.endswith(".md"):
                    filepath = os.path.join(education_dir, filename)
                    with open(filepath, "r") as f:
                        content = f.read()
                    if content.startswith("---"):
                        end = content.find("---", 3)
                        if end != -1:
                            content = content[end + 3:].strip()
                    key = f"education/{filename.replace('.md', '')}"
                    knowledge[key] = content

        # Load workspace-specific knowledge
        if self.workspace_id:
            ws_dir = os.path.join(self.vault_root, "workspaces", self.workspace_id)
            if os.path.isdir(ws_dir):
                for filename in os.listdir(ws_dir):
                    if filename.endswith(".md"):
                        filepath = os.path.join(ws_dir, filename)
                        with open(filepath, "r") as f:
                            content = f.read()
                        if content.startswith("---"):
                            end = content.find("---", 3)
                            if end != -1:
                                content = content[end + 3:].strip()
                        key = f"workspace/{filename.replace('.md', '')}"
                        knowledge[key] = content

        self._cache[cache_key] = knowledge
        return knowledge

    def load_relevant_education(
        self, context: Dict, max_tokens: int = 500
    ) -> str:
        """Query vault FTS for education content relevant to the current situation.

        Args:
            context: Dict with keys like fan_state, pattern_name, setup_type,
                     pair, regime, phase, etc. Used to build FTS query.
            max_tokens: Approximate max length of returned text (in words, not LLM tokens).

        Returns:
            Formatted education excerpt relevant to the current setup.
        """
        # Build FTS query from context
        query_parts = []
        for key in ["fan_state", "pattern_name", "setup_type", "regime", "phase"]:
            val = context.get(key)
            if val and val != "unknown" and val != "mixed":
                clean = val.replace("_", " ")
                query_parts.append(clean)

        if context.get("pair"):
            query_parts.append(context["pair"].replace("_", " "))

        # Also accept free text query (from chart_read or setup_identified)
        text_query = context.get("text_query", "")
        if text_query:
            # Extract meaningful words for FTS
            words = [w for w in text_query.lower().split() if len(w) > 3
                     and w not in ("this", "that", "with", "from", "have", "been",
                                   "will", "would", "could", "should", "there", "their",
                                   "what", "when", "where", "which", "about", "after",
                                   "before", "below", "above", "price", "chart", "shows")]
            if words:
                query_parts.extend(words[:5])  # Max 5 terms from free text

        if not query_parts:
            return ""

        query = " OR ".join(query_parts)

        conn = sqlite3.connect(self.db_path, isolation_level=None)
        try:
            rows = conn.execute(
                "SELECT path FROM fts_content WHERE fts_content MATCH ? LIMIT 5",
                (query,),
            ).fetchall()
        except Exception:
            conn.close()
            return ""

        conn.close()

        # Log search results for vault analytics
        if rows:
            self._log_search_hits([r[0] for r in rows])

        # Read matched files and extract relevant sections
        excerpts = []
        total_words = 0

        for (path,) in rows:
            # Only include education and trading-knowledge files
            if "education/" not in path and "trading-knowledge/" not in path:
                continue

            full_path = os.path.join(self.vault_root, path)
            if not os.path.exists(full_path):
                continue

            with open(full_path, "r") as f:
                content = f.read()

            # Strip frontmatter
            if content.startswith("---"):
                end = content.find("---", 3)
                if end != -1:
                    content = content[end + 3:].strip()

            # Extract the most relevant section (search for context terms in content)
            best_section = self._extract_relevant_section(content, context)
            if best_section:
                words = len(best_section.split())
                if total_words + words > max_tokens:
                    # Truncate to stay within budget
                    remaining = max_tokens - total_words
                    best_section = " ".join(best_section.split()[:remaining]) + "..."
                    excerpts.append(best_section)
                    break
                excerpts.append(best_section)
                total_words += words

        if not excerpts:
            return ""

        # Audit: log what education was found and which query matched
        matched_files = [p for (p,) in rows if "education/" in p or "trading-knowledge/" in p]
        _audit_log(
            agent=self.validator_agent, action="load_relevant_education",
            query=query,
            files_accessed=matched_files,
            context=f"context_keys={list(context.keys())}, excerpts={len(excerpts)}, words={total_words}",
            workspace_id=self.workspace_id,
            pair=self._pair, cycle_id=self._cycle_id,
        )
        logger.info(
            "[VAULT] Education query '%s' → %d files, %d words: %s",
            query, len(matched_files), total_words, matched_files
        )

        return "\n\n---\n\n".join(excerpts)

    def _log_search_hits(self, paths):
        """Log which vault entries were returned in search results."""
        if not paths:
            return
        try:
            conn = sqlite3.connect(str(self.db_path))
            conn.executemany(
                "INSERT INTO search_log (path) VALUES (?)",
                [(p,) for p in paths]
            )
            conn.commit()
            conn.close()
        except Exception:
            pass  # Never fail vault operations due to logging

    def _extract_relevant_section(
        self, content: str, context: Dict, max_lines: int = 30
    ) -> Optional[str]:
        """Extract the most relevant section of a document based on context."""
        lines = content.split("\n")
        search_terms = []
        for key in ["fan_state", "pattern_name", "setup_type", "regime"]:
            val = context.get(key)
            if val:
                search_terms.extend(val.replace("_", " ").lower().split())

        if not search_terms:
            return None

        # Find the line with the most matches
        best_idx = -1
        best_score = 0
        for i, line in enumerate(lines):
            lower = line.lower()
            score = sum(1 for term in search_terms if term in lower)
            if score > best_score:
                best_score = score
                best_idx = i

        if best_idx < 0:
            return None

        # Extract section: go back to the nearest heading, then forward max_lines
        start = best_idx
        for j in range(best_idx, max(0, best_idx - 10), -1):
            if lines[j].startswith("#"):
                start = j
                break

        end = min(len(lines), start + max_lines)
        section = "\n".join(lines[start:end]).strip()
        return section if len(section) > 20 else None

    def get_teaching_images(self, context: Dict, limit: int = 5) -> List[Dict]:
        """Get relevant teaching image paths from image_catalog.

        Args:
            context: Dict with setup_type, direction, pair, pattern_name, fan_state
            limit: Max images to return

        Returns:
            List of dicts with file_path and description
        """
        conn = sqlite3.connect(self.db_path, isolation_level=None)
        conn.row_factory = sqlite3.Row

        # Check if image_catalog table exists
        tables = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='image_catalog'"
        ).fetchone()
        if not tables:
            conn.close()
            return []

        # Build query based on available context
        conditions = ["source IN ('teaching', 'pattern_reference')"]
        params = []

        setup_type = context.get("setup_type")
        if setup_type:
            conditions.append("(setup_type = ? OR tags LIKE ?)")
            params.extend([setup_type, f"%{setup_type}%"])

        direction = context.get("direction")
        if direction:
            conditions.append("(direction = ? OR direction IS NULL)")
            params.append(direction)

        pattern_name = context.get("pattern_name")
        if pattern_name:
            conditions.append("(pattern_name = ? OR tags LIKE ?)")
            params.extend([pattern_name, f"%{pattern_name}%"])

        where = " AND ".join(conditions)

        # Prefer matching pair
        pair = context.get("pair", "")
        query = f"""
            SELECT file_path, description, pair, label, setup_type, pattern_name,
                   CASE WHEN pair = ? THEN 1 ELSE 0 END AS pair_match
            FROM image_catalog
            WHERE {where}
            ORDER BY pair_match DESC, source ASC
            LIMIT ?
        """
        params_final = [pair] + params + [limit]

        try:
            rows = conn.execute(query, params_final).fetchall()
        except Exception:
            rows = []

        conn.close()
        return [dict(r) for r in rows]

    def load_file_impact(self, file_path: str) -> Dict:
        """Load code dependency and vault knowledge context for a file.

        Args:
            file_path: Relative path (e.g., 'Handler/handler_base.py')
        Returns:
            dict with importers, imports, vault_notes, hub_score, change_frequency
        """
        cache_key = f"impact:{file_path}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        from knowledge.indexer import get_file_context
        context = get_file_context(file_path)

        self._cache[cache_key] = context
        _audit_log(
            agent="claude-code", action="load_file_impact",
            files_accessed=[file_path],
            context=f"importers={len(context.get('importers', []))}, imports={len(context.get('imports', []))}",
            workspace_id=self.workspace_id,
            pair=self._pair, cycle_id=self._cycle_id,
        )
        return context

    def clear_cache(self):
        """Clear the in-memory cache (call after vault updates)."""
        self._cache.clear()
