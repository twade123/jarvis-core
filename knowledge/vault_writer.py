#!/usr/bin/env python3
"""
Knowledge Vault Writer — The learning backbone for every agent.

This is what makes agents GET SMARTER over time. After every task, deliberation,
trade, or Opus correction, the vault writer:
1. Updates the agent's learnings.md with what happened and WHY
2. Extracts universal patterns to collective/patterns/
3. Updates prompt/skill improvement suggestions
4. Reindexes the vault so all agents see the new knowledge immediately

The vault has two storage layers working together:
- Database (SQLite): structured metrics — win rates, scores, row counts. Fast queries.
- Vault (Markdown): narrative context — WHY something worked, reasoning, lessons learned.
Neither replaces the other. Database = evidence. Vault = understanding.

Usage:
    from knowledge.vault_writer import VaultWriter
    writer = VaultWriter()
    
    # After an agent completes a task
    writer.record_agent_learning(agent_name="scout", learning={
        "type": "discovery",
        "summary": "S15 + squeeze on EUR_USD during London = 89% win rate",
        "context": "Failed during Asian session low volume",
        "tags": ["S15", "squeeze", "EUR_USD", "session_filter"]
    })
    
    # After a boardroom deliberation
    writer.record_decision(topic="Build crypto trading team", 
                          decision="Clone forex architecture, swap OANDA for Coinbase",
                          reasoning="CTO confirmed same pipeline works, CRO flagged 24/7 risk",
                          outcome=None)  # filled in later
    
    # After Opus corrects a local model
    writer.record_opus_correction(agent_name="CTO", task="architecture review",
                                  local_output="...", opus_correction="...",
                                  opus_reasoning="...")
    
    # Update a skill or prompt based on learnings
    writer.suggest_prompt_improvement(agent_name="scout", 
                                      current_prompt="...",
                                      suggestion="Add session filter gate",
                                      evidence="89% London vs 73% Asian on S15")
"""

import os
import json
import time
import sqlite3
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, List, Any

logger = logging.getLogger("VaultWriter")

VAULT_DIR = os.path.dirname(os.path.abspath(__file__))
INDEX_DB = os.path.join(VAULT_DIR, "_index.db")

# ── Flight Recorder v2 (lazy import) ─────────────────────────────────────────
_flight_v2 = None

def _get_flight_recorder():
    """Lazy singleton for Flight Recorder v2."""
    global _flight_v2
    if _flight_v2 is None:
        try:
            from connection_doctor.flight_recorder_v2 import FlightRecorderV2
            _flight_v2 = FlightRecorderV2()
        except (ImportError, Exception):
            _flight_v2 = False  # Not available
    return _flight_v2 if _flight_v2 else None


def _notify_vault_keeper(path):
    """Notify vault keeper of new write (fire-and-forget)."""
    try:
        import urllib.request
        url = f"http://localhost:8802/api/trigger-scan?mode=single&path={path}"
        req = urllib.request.Request(url, method='POST', data=b'')
        urllib.request.urlopen(req, timeout=2)
    except Exception:
        pass  # Vault keeper may not be running - that's fine


class VaultWriter:
    """Write learnings, decisions, and improvements to the knowledge vault."""

    def __init__(self, vault_dir: str = None):
        self.vault_dir = vault_dir or VAULT_DIR
        self._ensure_dirs()
    
    def _ensure_dirs(self):
        """Ensure core vault directories exist."""
        for subdir in ["agents", "collective/patterns", "collective/training-data",
                       "boardroom/decisions", "boardroom/sessions"]:
            os.makedirs(os.path.join(self.vault_dir, subdir), exist_ok=True)
    
    def _now_iso(self) -> str:
        return datetime.now().isoformat(timespec='seconds')
    
    def _now_date(self) -> str:
        return datetime.now().strftime("%Y-%m-%d")
    
    # ------------------------------------------------------------------
    # Agent Learnings
    # ------------------------------------------------------------------
    
    def record_agent_learning(self, agent_name: str, learning: Dict[str, Any],
                               workspace: str = None) -> str:
        """
        Append a learning to an agent's learnings.md file.
        
        Args:
            agent_name: e.g., "scout", "CTO", "validator"
            learning: {
                "type": "discovery" | "correction" | "failure" | "improvement",
                "summary": "One-line summary",
                "context": "Full context of what happened",
                "evidence": "Data/metrics that support this",
                "tags": ["tag1", "tag2"],
                "related": ["[[agents/validator]]", "[[workspaces/forex]]"]  # wiki links
            }
            workspace: Optional workspace context (e.g., "forex-trading-team")
            
        Returns:
            Path to the updated learnings file.
        """
        # Ensure agent directory exists
        agent_dir = os.path.join(self.vault_dir, "agents", agent_name.lower().replace(" ", "-"))
        os.makedirs(agent_dir, exist_ok=True)
        
        learnings_path = os.path.join(agent_dir, "learnings.md")
        
        # Create file with frontmatter if it doesn't exist
        if not os.path.exists(learnings_path):
            with open(learnings_path, 'w') as f:
                f.write(f"""---
type: pattern
created: {self._now_iso()}
updated: {self._now_iso()}
tags: [{agent_name.lower()}]
links: []
status: active
---

# {agent_name} — Learnings

""")
        
        # Build the learning entry with Obsidian-compatible callout syntax
        entry_type = learning.get("type", "note")
        # Map types to Obsidian callout types
        callout_map = {
            "discovery": "tip",
            "correction": "warning",
            "failure": "danger",
            "improvement": "success",
            "note": "info",
        }
        callout_type = callout_map.get(entry_type, "info")
        type_emoji = {"discovery": "💡", "correction": "🔧", "failure": "❌",
                      "improvement": "📈", "note": "📝"}.get(entry_type, "📝")

        tags = learning.get("tags", [])
        related = learning.get("related", [])

        entry = f"\n## {type_emoji} {learning.get('summary', 'Untitled')}\n"
        entry += f"**Date:** {self._now_iso()}\n"
        entry += f"**Type:** {entry_type}\n"
        if workspace:
            entry += f"**Workspace:** [[workspaces/{workspace}]]\n"
        if tags:
            entry += f"**Tags:** {', '.join(tags)}\n"
        entry += f"\n> [!{callout_type}] {entry_type.upper()}\n"
        context = learning.get('context', '')
        if context:
            for line in context.split('\n'):
                entry += f"> {line}\n"
        if learning.get("evidence"):
            entry += f"> **Evidence:** {learning['evidence']}\n"
        entry += "\n"
        if related:
            entry += f"**Related:** {', '.join(related)}\n"
        entry += "\n---\n"
        
        # Write to monthly log file (keeps individual files manageable)
        monthly_dir = os.path.join(agent_dir, "log")
        os.makedirs(monthly_dir, exist_ok=True)
        month_file = os.path.join(monthly_dir, f"{self._now_date()[:7]}.md")  # YYYY-MM.md

        if not os.path.exists(month_file):
            with open(month_file, 'w') as f:
                f.write(f"---\ntype: agent_log\nagent: {agent_name}\nmonth: {self._now_date()[:7]}\n"
                        f"tags: [{agent_name.lower()}, log]\nstatus: active\n---\n\n"
                        f"# {agent_name} — {self._now_date()[:7]} Log\n\n")

        with open(month_file, 'a') as f:
            f.write(entry)

        # Also append to learnings.md
        with open(learnings_path, 'a') as f:
            f.write(entry)
        # NOTE: trim DISABLED — vault keeper handles pruning/decomposition now.
        # Was aggressively truncating to 10 entries and caused data loss.

        # Update frontmatter timestamp
        self._update_frontmatter_timestamp(learnings_path)

        # If this is a universal pattern, also write to collective
        if entry_type in ("discovery", "improvement") and learning.get("universal", False):
            self._record_collective_pattern(agent_name, learning)

        logger.info(f"Recorded {entry_type} for {agent_name}: {learning.get('summary', '')[:60]}")
        try:
            fr = _get_flight_recorder()
            if fr:
                fr.record(domain="vault", stage="VAULT_WRITE", source=f"vault_writer.{agent_name}", target=learning.get("type", "unknown"), status="ok")
        except Exception:
            pass
        self._update_fts(learnings_path)
        _notify_vault_keeper(learnings_path)
        return learnings_path
    
    def _trim_learnings_file(self, path: str, max_entries: int = 10):
        """Keep only the last N entries in a learnings.md file.

        Old entries are preserved in the monthly log/ files — this just keeps
        the main learnings.md as a rolling window of recent entries so agents
        see the most relevant context without loading 800 lines.
        """
        try:
            with open(path, 'r') as f:
                content = f.read()

            # Split on entry separator
            parts = content.split("\n---\n")

            if len(parts) <= max_entries + 1:  # +1 for frontmatter header
                return  # Nothing to trim

            # Keep frontmatter (first part) + last N entries
            header = parts[0]
            recent = parts[-(max_entries):]

            trimmed = header + "\n---\n".join([""] + recent)

            with open(path, 'w') as f:
                f.write(trimmed)

            logger.info(f"Trimmed {path}: kept {max_entries} of {len(parts)-1} entries")
        except Exception as e:
            logger.debug(f"Trim failed for {path}: {e}")

    def _record_collective_pattern(self, source_agent: str, learning: Dict):
        """Write a universal pattern to collective/patterns/ for all agents to benefit."""
        patterns_dir = os.path.join(self.vault_dir, "collective", "patterns")
        os.makedirs(patterns_dir, exist_ok=True)
        
        # Append to date-based patterns file
        patterns_file = os.path.join(patterns_dir, f"{self._now_date()}.md")
        
        if not os.path.exists(patterns_file):
            with open(patterns_file, 'w') as f:
                f.write(f"""---
type: collective_patterns
created: {self._now_iso()}
tags: [collective, patterns]
---

# Collective Patterns — {self._now_date()}

""")
        
        entry = (
            f"\n### {learning.get('summary', 'Pattern')}\n"
            f"**Source:** [[agents/{source_agent}]]\n"
            f"**Date:** {self._now_iso()}\n"
            f"{learning.get('context', '')}\n"
            f"**Evidence:** {learning.get('evidence', 'N/A')}\n\n---\n"
        )
        
        with open(patterns_file, 'a') as f:
            f.write(entry)
    
    # ------------------------------------------------------------------
    # Boardroom Decisions
    # ------------------------------------------------------------------
    
    def record_decision(self, topic: str, decision: str, reasoning: str,
                        contributions: Dict[str, str] = None,
                        opus_review: str = None,
                        outcome: str = None, outcome_rating: float = None,
                        workspace: str = None, user_id: int = None) -> str:
        """Record a boardroom decision to the vault."""
        decisions_dir = os.path.join(self.vault_dir, "boardroom", "decisions")
        os.makedirs(decisions_dir, exist_ok=True)
        
        # Date-based decisions file
        decisions_file = os.path.join(decisions_dir, f"{self._now_date()}.md")
        
        if not os.path.exists(decisions_file):
            with open(decisions_file, 'w') as f:
                f.write(f"""---
type: boardroom_decisions
created: {self._now_iso()}
tags: [boardroom, decisions]
---

# Boardroom Decisions — {self._now_date()}

""")
        
        entry = f"\n## {topic}\n"
        entry += f"**Date:** {self._now_iso()}\n"
        entry += f"**Decision:** {decision}\n\n"
        entry += f"### Reasoning\n{reasoning}\n\n"
        
        if contributions:
            entry += "### Board Member Contributions\n"
            for member, contribution in contributions.items():
                entry += f"\n**{member}:**\n{contribution[:500]}\n"
        
        if opus_review:
            entry += f"\n### Opus Review\n{opus_review[:1000]}\n"
        
        if outcome:
            entry += f"\n### Outcome\n{outcome}\n"
            if outcome_rating is not None:
                entry += f"**Rating:** {outcome_rating}/10\n"
        else:
            entry += "\n### Outcome\n*Pending — update when results are known.*\n"
        
        entry += "\n---\n"
        
        with open(decisions_file, 'a') as f:
            f.write(entry)
        
        logger.info(f"Decision recorded: {topic[:60]}")
        self._update_fts(decisions_file)
        _notify_vault_keeper(decisions_file)
        return decisions_file
    
    # ------------------------------------------------------------------
    # Opus Corrections (Training Data)
    # ------------------------------------------------------------------
    
    def record_opus_correction(self, agent_name: str, task: str,
                                local_output: str, opus_correction: str,
                                opus_reasoning: str, category: str = None) -> str:
        """
        Record an Opus correction — THIS IS TRAINING DATA.
        
        Every correction is:
        1. Saved to the vault (narrative understanding)
        2. Saved in structured format for fine-tuning
        3. Appended to the agent's learnings
        """
        # 1. Save structured training example
        training_dir = os.path.join(self.vault_dir, "collective", "training-data")
        os.makedirs(training_dir, exist_ok=True)
        
        training_file = os.path.join(training_dir, f"opus-corrections-{self._now_date()}.jsonl")
        
        training_example = {
            "timestamp": self._now_iso(),
            "agent": agent_name,
            "task": task[:500],
            "category": category or "general",
            "local_output": local_output[:2000],
            "opus_correction": opus_correction[:2000],
            "opus_reasoning": opus_reasoning[:2000],
        }
        
        with open(training_file, 'a') as f:
            f.write(json.dumps(training_example) + "\n")
        
        # 2. Record as agent learning
        self.record_agent_learning(agent_name, {
            "type": "correction",
            "summary": f"Opus corrected: {task[:80]}",
            "context": (
                f"**Task:** {task[:200]}\n\n"
                f"**My output:** {local_output[:300]}...\n\n"
                f"**Opus correction:** {opus_correction[:300]}...\n\n"
                f"**Why:** {opus_reasoning[:300]}"
            ),
            "evidence": f"Category: {category or 'general'}",
            "tags": ["opus-correction", category or "general"],
        })
        
        logger.info(f"Opus correction recorded for {agent_name}: {task[:60]}")
        # Note: record_agent_learning() above already updated FTS for the learnings file.
        # The JSONL training file doesn't need FTS indexing (not markdown).
        _notify_vault_keeper(training_file)
        return training_file
    
    # ------------------------------------------------------------------
    # Prompt & Skill Improvements
    # ------------------------------------------------------------------
    
    def suggest_prompt_improvement(self, agent_name: str, 
                                    suggestion: str, evidence: str,
                                    current_prompt_excerpt: str = None,
                                    skill_name: str = None) -> str:
        """
        Record a prompt/skill improvement suggestion based on learnings.
        
        Over time, these accumulate into a clear picture of how to improve
        each agent's prompt and skills. The boardroom reviews these periodically
        and applies the best improvements.
        """
        agent_dir = os.path.join(self.vault_dir, "agents", agent_name.lower().replace(" ", "-"))
        os.makedirs(agent_dir, exist_ok=True)
        
        improvements_path = os.path.join(agent_dir, "improvements.md")
        
        if not os.path.exists(improvements_path):
            with open(improvements_path, 'w') as f:
                f.write(f"""---
type: improvements
created: {self._now_iso()}
tags: [{agent_name.lower()}, improvements, prompts]
status: active
---

# {agent_name} — Prompt & Skill Improvements

Accumulated suggestions for improving this agent's prompts and skills,
based on real-world performance, Opus corrections, and learnings.

""")
        
        entry = f"\n## 📈 {suggestion[:80]}\n"
        entry += f"**Date:** {self._now_iso()}\n"
        entry += f"**Status:** proposed\n"
        if skill_name:
            entry += f"**Skill:** {skill_name}\n"
        entry += f"\n**Evidence:** {evidence}\n"
        if current_prompt_excerpt:
            entry += f"\n**Current prompt excerpt:**\n```\n{current_prompt_excerpt[:300]}\n```\n"
        entry += f"\n**Suggestion:** {suggestion}\n"
        entry += "\n---\n"
        
        with open(improvements_path, 'a') as f:
            f.write(entry)
        
        logger.info(f"Improvement suggested for {agent_name}: {suggestion[:60]}")
        self._update_fts(improvements_path)
        return improvements_path
    
    # ------------------------------------------------------------------
    # Skill Execution Logging
    # ------------------------------------------------------------------

    def record_skill_execution(self, skill_name: str, task_summary: str,
                                response_summary: str,
                                quality_score: float = None,
                                session_key: str = None) -> str:
        """
        Log one execution of a Trevor skill as a usage event.

        Called by the session distiller whenever it detects a SKILL.md read
        followed by a substantial response. Builds per-skill usage logs that
        accumulate into a clear picture of:
          - Which skills are used most often
          - What tasks they're applied to
          - Which executions were marked high quality (quality_score >= 0.8)

        When quality_score >= 0.8, also writes a prompt improvement suggestion
        so the boardroom can periodically review and bake the best patterns
        into the SKILL.md.

        Args:
            skill_name:        e.g. "canvas-design", "frontend-design"
            task_summary:      First 200 chars of the user's request
            response_summary:  First 300 chars of the skill-driven response
            quality_score:     0.0–1.0 (None = unknown, 1.0 = explicit praise)
            session_key:       OpenClaw session ID (optional, for traceability)

        Returns:
            Path to the skill's usage-log.md file.
        """
        skills_dir = os.path.join(self.vault_dir, "skills", skill_name.lower().replace(" ", "-"))
        os.makedirs(skills_dir, exist_ok=True)

        log_path = os.path.join(skills_dir, "usage-log.md")

        if not os.path.exists(log_path):
            with open(log_path, "w") as f:
                f.write(f"""---
type: skill_usage
skill: {skill_name}
created: {self._now_iso()}
tags: [{skill_name.lower()}, skill-usage, training-data]
---

# {skill_name} — Usage Log

Every execution of this skill is recorded here.
High-quality executions (score ≥ 0.8) feed back into prompt improvement suggestions.

""")

        quality_str = f"{quality_score:.1f}" if quality_score is not None else "unknown"
        quality_flag = " ⭐" if quality_score is not None and quality_score >= 0.8 else ""
        session_str = f"\n**Session:** `{session_key}`" if session_key else ""

        entry = (
            f"\n## {self._now_iso()}{quality_flag}\n"
            f"**Quality:** {quality_str}{session_str}\n"
            f"\n**Task:** {task_summary[:200]}\n"
            f"\n**Response:** {response_summary[:300]}\n"
            f"\n---\n"
        )

        with open(log_path, "a") as f:
            f.write(entry)

        # High-quality execution → write a prompt improvement suggestion
        if quality_score is not None and quality_score >= 0.8:
            self.suggest_prompt_improvement(
                agent_name="Trevor",
                suggestion=(
                    f"Skill '{skill_name}' received explicit positive feedback for: "
                    f"{task_summary[:120]}"
                ),
                evidence=f"Quality score: {quality_score:.1f}. Response: {response_summary[:200]}",
                skill_name=skill_name,
            )

        logger.info(
            "Skill execution logged: %s (quality=%s)", skill_name, quality_str
        )
        self._update_fts(log_path)
        return log_path

    # ------------------------------------------------------------------
    # Knowledge Evolution — Living Documents
    # ------------------------------------------------------------------
    # Learnings are never overwritten. They evolve through threaded 
    # refinements: corrections, confirmations, expanded context, and
    # superseded notes. Like a wiki edit history, not a replacement.
    # ------------------------------------------------------------------
    
    def refine_learning(self, agent_name: str, original_summary: str,
                         refinement: Dict[str, Any]) -> str:
        """
        Add a refinement to an existing learning — correction, expansion, 
        confirmation, or supersede notice. The original stays intact.
        
        Args:
            agent_name: Agent whose learning to refine.
            original_summary: Summary text of the original learning (used for matching).
            refinement: {
                "action": "correct" | "expand" | "confirm" | "supersede",
                "note": "What changed or was added",
                "evidence": "Supporting data",
                "source": "opus" | "agent" | "user" | "backtest",
                "confidence": 0.0-1.0 (how confident in this refinement)
            }
            
        Returns:
            Path to the updated learnings file.
        """
        agent_dir = os.path.join(self.vault_dir, "agents", agent_name.lower().replace(" ", "-"))
        learnings_path = os.path.join(agent_dir, "learnings.md")
        
        if not os.path.exists(learnings_path):
            logger.warning(f"No learnings file for {agent_name}, creating new learning instead")
            return self.record_agent_learning(agent_name, {
                "type": "note",
                "summary": refinement.get("note", "Refinement without original"),
                "context": refinement.get("note", ""),
                "evidence": refinement.get("evidence", ""),
            })
        
        action = refinement.get("action", "expand")
        action_emoji = {
            "correct": "🔄", "expand": "➕", 
            "confirm": "✅", "supersede": "⚠️"
        }.get(action, "📝")
        
        source = refinement.get("source", "agent")
        confidence = refinement.get("confidence", 0.5)
        confidence_label = "high" if confidence >= 0.8 else "medium" if confidence >= 0.5 else "low"
        
        # Build the threaded refinement entry
        # These go UNDER the original learning they refine
        entry = (
            f"\n> {action_emoji} **{action.upper()}** ({self._now_iso()}) "
            f"— *source: {source}, confidence: {confidence_label}*\n"
            f"> {refinement.get('note', '')}\n"
        )
        if refinement.get("evidence"):
            entry += f"> **Evidence:** {refinement['evidence']}\n"
        entry += "\n"
        
        # Find the original learning and append refinement right after it
        with open(learnings_path, 'r') as f:
            content = f.read()
        
        # Search for the original learning by summary text
        search_text = original_summary[:60]  # match on first 60 chars
        idx = content.find(search_text)
        
        if idx >= 0:
            # Find the next "---" separator after this learning
            separator_idx = content.find("\n---\n", idx)
            if separator_idx >= 0:
                # Insert refinement just before the separator
                content = content[:separator_idx] + entry + content[separator_idx:]
            else:
                # No separator found, append to end
                content += entry
        else:
            # Original not found — append as standalone refinement
            content += (
                f"\n## {action_emoji} Refinement: {original_summary[:60]}...\n"
                f"**Original not found — standalone refinement**\n"
                f"{entry}\n---\n"
            )
            logger.warning(f"Original learning not found for '{search_text}', appended standalone")
        
        with open(learnings_path, 'w') as f:
            f.write(content)
        
        self._update_frontmatter_timestamp(learnings_path)
        
        logger.info(f"Refined learning for {agent_name}: {action} on '{original_summary[:40]}'")
        return learnings_path
    
    def review_and_evolve(self, agent_name: str, reviewer: str = "opus",
                           review_notes: List[Dict] = None) -> List[str]:
        """
        Batch-evolve an agent's learnings based on a review session.
        Called after Opus (or a senior model) reviews an agent's knowledge.
        
        Args:
            agent_name: Agent to review.
            reviewer: Who's doing the review ("opus", "user", "backtest").
            review_notes: List of {
                "original_summary": "...",
                "action": "correct" | "expand" | "confirm" | "supersede",
                "note": "...",
                "evidence": "...",
                "confidence": 0.0-1.0
            }
            
        Returns:
            List of updated file paths.
        """
        if not review_notes:
            return []
        
        updated = []
        for note in review_notes:
            note["source"] = reviewer
            path = self.refine_learning(
                agent_name=agent_name,
                original_summary=note.get("original_summary", ""),
                refinement=note
            )
            updated.append(path)
        
        # Record the review itself as a meta-learning
        self.record_agent_learning(agent_name, {
            "type": "improvement",
            "summary": f"Knowledge review by {reviewer}: {len(review_notes)} refinements",
            "context": (
                f"Reviewer: {reviewer}\n"
                f"Actions: {', '.join(n.get('action', '?') for n in review_notes)}\n"
                f"Average confidence: {sum(n.get('confidence', 0.5) for n in review_notes) / len(review_notes):.1%}"
            ),
            "tags": ["review", reviewer, "evolution"],
        })
        
        # record_agent_learning() above already updated FTS for each refined file
        
        logger.info(f"Evolved {len(review_notes)} learnings for {agent_name} (reviewer: {reviewer})")
        return updated
    
    def get_learning_timeline(self, agent_name: str) -> List[Dict]:
        """
        Get the full evolution timeline for an agent's learnings.
        Returns entries in chronological order with refinements nested.
        Useful for understanding HOW knowledge evolved, not just current state.
        """
        agent_dir = os.path.join(self.vault_dir, "agents", agent_name.lower().replace(" ", "-"))
        learnings_path = os.path.join(agent_dir, "learnings.md")
        
        if not os.path.exists(learnings_path):
            return []
        
        with open(learnings_path, 'r') as f:
            content = f.read()
        
        timeline = []
        # Split on ## (H2 headers = top-level entries)
        sections = content.split("\n## ")[1:]  # skip frontmatter/header
        
        for section in sections:
            lines = section.strip().split("\n")
            entry = {"summary": lines[0] if lines else "?", "refinements": [], "raw": section}
            
            # Extract refinements (blockquotes with action emojis)
            for line in lines:
                if line.startswith("> ") and any(e in line for e in ["🔄", "➕", "✅", "⚠️"]):
                    entry["refinements"].append(line[2:])  # strip "> "
            
            # Extract date
            for line in lines:
                if line.startswith("**Date:**"):
                    entry["date"] = line.replace("**Date:**", "").strip()
                    break
            
            timeline.append(entry)
        
        return timeline

    # ------------------------------------------------------------------
    # Context Loading (READ side)
    # ------------------------------------------------------------------
    
    def load_agent_context(self, agent_name: str, max_learnings: int = 20) -> str:
        """
        Load an agent's knowledge context for injection into their system prompt.
        
        Returns markdown with: profile + recent learnings + relevant collective patterns.
        This is what makes agents REMEMBER across sessions.
        """
        agent_dir = os.path.join(self.vault_dir, "agents", agent_name.lower().replace(" ", "-"))
        context_parts = []
        
        # 1. Agent profile
        profile_path = os.path.join(agent_dir, "profile.md")
        if os.path.exists(profile_path):
            with open(profile_path, 'r') as f:
                content = f.read()
                # Strip frontmatter
                if content.startswith("---"):
                    parts = content.split("---", 2)
                    if len(parts) >= 3:
                        content = parts[2].strip()
                context_parts.append(f"## Your Profile\n{content}")
        
        # 2. Recent learnings (last N entries)
        learnings_path = os.path.join(agent_dir, "learnings.md")
        if os.path.exists(learnings_path):
            with open(learnings_path, 'r') as f:
                content = f.read()
            # Extract individual entries (split on ## )
            entries = content.split("\n## ")[1:]  # skip header
            recent = entries[-max_learnings:] if len(entries) > max_learnings else entries
            if recent:
                context_parts.append("## Your Learnings (Recent)\n" + 
                                   "\n## ".join(recent))
        
        # 3. Improvement suggestions
        improvements_path = os.path.join(agent_dir, "improvements.md")
        if os.path.exists(improvements_path):
            with open(improvements_path, 'r') as f:
                content = f.read()
            # Only include proposed (not applied) improvements
            if "proposed" in content:
                context_parts.append("## Pending Improvements\n" + 
                                   content.split("# ")[1] if "# " in content else content[-500:])
        
        # 4. Relevant collective patterns (last 5)
        patterns_dir = os.path.join(self.vault_dir, "collective", "patterns")
        if os.path.isdir(patterns_dir):
            pattern_files = sorted(os.listdir(patterns_dir))[-3:]  # last 3 days
            patterns = []
            for pf in pattern_files:
                if pf.endswith(".md"):
                    with open(os.path.join(patterns_dir, pf), 'r') as f:
                        patterns.append(f.read()[-500:])  # last 500 chars per file
            if patterns:
                context_parts.append("## Collective Patterns (Recent)\n" + "\n".join(patterns))
        
        # 5. Skills + Team Roster for board members
        try:
            # Map agent names to board seats
            seat_map = {
                "cto": "CTO", "chief_technology_officer": "CTO",
                "cso": "CSO", "chief_strategy_officer": "CSO",
                "cro": "CRO", "chief_risk_officer": "CRO",
                "cdo": "CDO", "chief_data_officer": "CDO",
                "opus": "CSO",  # Opus sees strategy skills by default
            }
            agent_lower = agent_name.lower().replace(" ", "_")
            seat = seat_map.get(agent_lower)
            if seat:
                # Skill catalog
                from knowledge.skill_loader import build_skill_context
                skill_ctx = build_skill_context(seat, max_chars=3000)
                if skill_ctx:
                    context_parts.append(skill_ctx)

                # Team roster — agents this board member can deploy
                from knowledge.agent_factory import build_roster_context
                roster_ctx = build_roster_context(seat, max_agents=25)
                if roster_ctx:
                    context_parts.append(roster_ctx)
        except Exception as e:
            logger.debug("Skill/roster context load failed for %s: %s", agent_name, e)

        return "\n\n".join(context_parts) if context_parts else ""
    
    def load_decision_history(self, topic_keywords: List[str] = None,
                               limit: int = 10) -> str:
        """Load relevant decision history for boardroom context."""
        decisions_dir = os.path.join(self.vault_dir, "boardroom", "decisions")
        if not os.path.isdir(decisions_dir):
            return ""
        
        all_content = []
        for fname in sorted(os.listdir(decisions_dir), reverse=True)[:5]:  # last 5 days
            if fname.endswith(".md"):
                with open(os.path.join(decisions_dir, fname), 'r') as f:
                    all_content.append(f.read())
        
        full_text = "\n".join(all_content)
        
        # If keywords provided, filter to relevant entries
        if topic_keywords and full_text:
            entries = full_text.split("\n## ")
            relevant = [e for e in entries if any(kw.lower() in e.lower() for kw in topic_keywords)]
            if relevant:
                return "## Relevant Past Decisions\n\n## " + "\n\n## ".join(relevant[-limit:])
        
        return full_text[-2000:] if full_text else ""  # last 2000 chars as fallback
    
    # ------------------------------------------------------------------
    # Backlinks (reverse link lookup — Obsidian's killer feature)
    # ------------------------------------------------------------------

    def get_backlinks(self, path: str) -> List[Dict[str, str]]:
        """
        Return all vault files that link TO the given path.

        This is the reverse of the forward-link graph stored in the `links`
        table — "what notes reference this note?"

        Args:
            path: Relative vault path, e.g. "skills/account-research" or
                  "skills/account-research.md".  Both forms are accepted.

        Returns:
            List of dicts: [{"source_path": str, "link_text": str}, ...]
        """
        if not os.path.exists(INDEX_DB):
            logger.warning("get_backlinks: _index.db not found — run reindex() first")
            return []

        # Normalise: accept with or without .md extension
        targets = [path]
        if path.endswith(".md"):
            targets.append(path[:-3])
        else:
            targets.append(path + ".md")

        conn = sqlite3.connect(INDEX_DB, isolation_level=None)
        try:
            placeholders = ",".join("?" * len(targets))
            rows = conn.execute(
                f"""
                SELECT f.path, l.link_text
                FROM links l
                JOIN files f ON f.id = l.source_file_id
                WHERE l.target_path IN ({placeholders})
                   OR l.target_file_id IN (
                       SELECT id FROM files WHERE path IN ({placeholders})
                   )
                ORDER BY f.path
                """,
                targets + targets,
            ).fetchall()
        finally:
            conn.close()

        return [{"source_path": r[0], "link_text": r[1]} for r in rows]

    # ------------------------------------------------------------------
    # Boardroom Session Recording
    # ------------------------------------------------------------------

    def record_session(self, topic: str, synthesis: str,
                       contributions: List[Dict] = None,
                       rounds: int = 1,
                       workspace: str = None) -> str:
        """
        Write a boardroom session note to boardroom/sessions/YYYY-MM-DD-{slug}.md.

        Called from trevor_escalation.boardroom_deliberation() when
        boardroom_action == 'satisfied' and Opus writes the final synthesis.

        Args:
            topic: The question/task the boardroom deliberated on.
            synthesis: Opus's final synthesis text.
            contributions: List of {member, response} dicts from the session.
            rounds: Number of deliberation rounds completed.
            workspace: Optional workspace context slug.

        Returns:
            Path to the session file written.
        """
        sessions_dir = os.path.join(self.vault_dir, "boardroom", "sessions")
        os.makedirs(sessions_dir, exist_ok=True)

        # Slug from topic — lowercase, spaces → dashes, max 40 chars
        import re as _re
        slug = _re.sub(r"[^a-z0-9]+", "-", topic.lower())[:40].strip("-")
        filename = f"{self._now_date()}-{slug}.md"
        session_path = os.path.join(sessions_dir, filename)

        # Build member list for frontmatter
        members = []
        if contributions:
            members = list({c.get("member", "?") for c in contributions})

        lines = [
            "---",
            f"type: boardroom_session",
            f"created: {self._now_iso()}",
            f"rounds: {rounds}",
            f"members: [{', '.join(members)}]",
            f"tags: [boardroom, session]",
        ]
        if workspace:
            lines.append(f"workspace: {workspace}")
        lines += ["---", "", f"# Boardroom Session: {topic}", ""]

        if contributions:
            lines.append("## Board Contributions")
            for c in contributions:
                member = c.get("member", "?")
                response = c.get("response", "")[:600]
                lines.append(f"\n### {member}")
                lines.append(response)

        lines += ["", "## Opus Synthesis", synthesis or "*No synthesis recorded.*", ""]

        with open(session_path, "w") as f:
            f.write("\n".join(lines))

        logger.info(f"Boardroom session recorded: {filename}")
        self._update_fts(session_path)
        return session_path

    # ------------------------------------------------------------------
    # Reindex
    # ------------------------------------------------------------------
    
    def _update_fts(self, abs_path: str):
        """Update FTS index for a single file after writing it.

        Uses surgical single-file update instead of full 818-file reindex.
        Falls back to full reindex if single-file update isn't available.
        """
        try:
            rel_path = os.path.relpath(abs_path, self.vault_dir)
            from knowledge.indexer import update_single_file
            update_single_file(rel_path, self.vault_dir)
        except ImportError:
            self.reindex()
        except Exception as e:
            logger.warning(f"FTS update for {abs_path} failed: {e}")

    def reindex(self):
        """Run full vault indexer. Use _update_fts() for single-file updates instead."""
        try:
            from knowledge.indexer import run as run_indexer
            run_indexer()
        except Exception as e:
            logger.warning(f"Vault reindex failed: {e}")
            try:
                import subprocess
                indexer_path = os.path.join(self.vault_dir, "indexer.py")
                subprocess.run(["python3", indexer_path], check=True, capture_output=True)
            except Exception as e2:
                logger.error(f"Vault reindex fallback also failed: {e2}")
    
    # ------------------------------------------------------------------
    # Utilities
    # ------------------------------------------------------------------
    
    def _update_frontmatter_timestamp(self, filepath: str):
        """Update the 'updated' field in a file's YAML frontmatter."""
        try:
            with open(filepath, 'r') as f:
                content = f.read()
            if content.startswith("---"):
                parts = content.split("---", 2)
                if len(parts) >= 3:
                    fm = parts[1]
                    # Replace updated timestamp
                    import re
                    fm = re.sub(r'updated:.*', f'updated: {self._now_iso()}', fm)
                    content = f"---{fm}---{parts[2]}"
                    with open(filepath, 'w') as f:
                        f.write(content)
        except Exception as e:
            logger.debug(f"Could not update frontmatter: {e}")
    
    def get_training_data_stats(self) -> Dict:
        """Get stats on accumulated training data."""
        training_dir = os.path.join(self.vault_dir, "collective", "training-data")
        stats = {"total_examples": 0, "by_agent": {}, "by_category": {}, "files": 0}
        
        if not os.path.isdir(training_dir):
            return stats
        
        for fname in os.listdir(training_dir):
            if fname.endswith(".jsonl"):
                stats["files"] += 1
                with open(os.path.join(training_dir, fname), 'r') as f:
                    for line in f:
                        try:
                            example = json.loads(line)
                            stats["total_examples"] += 1
                            agent = example.get("agent", "unknown")
                            cat = example.get("category", "general")
                            stats["by_agent"][agent] = stats["by_agent"].get(agent, 0) + 1
                            stats["by_category"][cat] = stats["by_category"].get(cat, 0) + 1
                        except json.JSONDecodeError:
                            pass
        
        return stats
