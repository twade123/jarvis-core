#!/usr/bin/env python3
"""
Skill Builder — Creates, updates, and manages agent skills.
Skills are attached to agents in the registry and improve with usage.
Connects to: agents.db (v2), knowledge vault, agent registry.
"""

import json
import os
import sqlite3
import uuid
import logging
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any, Literal

logger = logging.getLogger(__name__)

# Paths
DB_PATH = os.path.expanduser("~/jarvis/Database/v2/agents.db")
INTEL_DB_PATH = os.path.expanduser("~/jarvis/Database/v2/intelligence.db")
VAULT_PATH = os.path.expanduser("~/jarvis/Knowledge/agents")

SkillType = Literal["tool_use", "analysis", "communication", "planning", "domain"]
Outcome = Literal["success", "failure"]


@dataclass
class Skill:
    """Represents an agent skill with proficiency tracking."""
    skill_id: str = ""
    skill_name: str = ""
    description: str = ""
    skill_type: str = "domain"  # tool_use|analysis|communication|planning|domain
    config: Dict[str, Any] = field(default_factory=dict)
    proficiency_score: float = 0.5
    usage_count: int = 0
    success_count: int = 0
    last_used: Optional[str] = None
    required_tools: List[str] = field(default_factory=list)
    required_context: List[str] = field(default_factory=list)

    def __post_init__(self):
        if not self.skill_id:
            self.skill_id = str(uuid.uuid4())

    def to_config_json(self) -> str:
        """Serialize to JSON for agent_skills.skill_config column."""
        return json.dumps({
            "description": self.description,
            "skill_type": self.skill_type,
            "config": self.config,
            "usage_count": self.usage_count,
            "success_count": self.success_count,
            "last_used": self.last_used,
            "required_tools": self.required_tools,
            "required_context": self.required_context,
        })

    @classmethod
    def from_db_row(cls, row: dict) -> "Skill":
        """Create Skill from agent_skills DB row."""
        cfg = json.loads(row.get("skill_config") or "{}")
        return cls(
            skill_id=row["id"],
            skill_name=row["skill_name"],
            description=cfg.get("description", ""),
            skill_type=cfg.get("skill_type", "domain"),
            config=cfg.get("config", {}),
            proficiency_score=row.get("proficiency_score", 0.5),
            usage_count=cfg.get("usage_count", 0),
            success_count=cfg.get("success_count", 0),
            last_used=cfg.get("last_used"),
            required_tools=cfg.get("required_tools", []),
            required_context=cfg.get("required_context", []),
        )


# ─── Skill Templates ────────────────────────────────────────────────

class SkillTemplate:
    """Pre-built skill definitions for common capabilities."""

    TEMPLATES: Dict[str, Dict[str, Any]] = {
        "trading_analysis": {
            "description": "Technical analysis — chart reading, indicator evaluation, setup scoring",
            "skill_type": "analysis",
            "config": {"indicators": ["RSI", "MACD", "EMA", "ATR"], "timeframes": ["H1", "H4", "D1"]},
            "required_tools": ["mcp:oanda", "mcp:data_validator"],
            "required_context": ["knowledge/workspaces/forex-trading-team/"],
        },
        "chart_reading": {
            "description": "Read and interpret price charts, identify patterns and levels",
            "skill_type": "analysis",
            "config": {"patterns": ["double_top", "head_shoulders", "flag", "wedge"]},
            "required_tools": ["mcp:oanda"],
            "required_context": [],
        },
        "risk_assessment": {
            "description": "Position sizing, exposure calculation, threat scoring",
            "skill_type": "analysis",
            "config": {"max_risk_pct": 2.0, "max_exposure_pct": 10.0, "correlation_threshold": 0.7},
            "required_tools": ["mcp:oanda", "mcp:data_validator"],
            "required_context": ["knowledge/workspaces/forex-trading-team/risk-rules.md"],
        },
        "market_scanning": {
            "description": "Pattern detection, alert generation, pair monitoring",
            "skill_type": "tool_use",
            "config": {"scan_interval_min": 15, "pairs": ["EUR_USD", "GBP_USD", "USD_JPY"]},
            "required_tools": ["mcp:oanda"],
            "required_context": [],
        },
        "pattern_detection": {
            "description": "Detect chart patterns and price action setups",
            "skill_type": "analysis",
            "config": {"min_confidence": 0.6},
            "required_tools": ["mcp:oanda"],
            "required_context": [],
        },
        "data_validation": {
            "description": "Input checking, schema validation, quality scoring",
            "skill_type": "tool_use",
            "config": {"strict_mode": True, "quality_threshold": 0.8},
            "required_tools": ["mcp:data_validator"],
            "required_context": [],
        },
        "setup_evaluation": {
            "description": "Score and validate trade setups against criteria",
            "skill_type": "analysis",
            "config": {"min_rr": 1.5, "required_confluences": 3},
            "required_tools": ["mcp:data_validator"],
            "required_context": [],
        },
        "code_generation": {
            "description": "Write code, debug, optimize",
            "skill_type": "tool_use",
            "config": {"languages": ["python", "javascript", "sql"]},
            "required_tools": ["mcp:terminal"],
            "required_context": [],
        },
        "research": {
            "description": "Web search, information synthesis, report generation",
            "skill_type": "analysis",
            "config": {"max_sources": 10, "synthesis_depth": "detailed"},
            "required_tools": ["mcp:news", "mcp:wolfram"],
            "required_context": [],
        },
        "communication": {
            "description": "Draft messages, summarize, translate",
            "skill_type": "communication",
            "config": {"tone": "professional", "max_length": 2000},
            "required_tools": [],
            "required_context": [],
        },
        "planning": {
            "description": "Task breakdown, dependency mapping, timeline estimation",
            "skill_type": "planning",
            "config": {"max_depth": 5, "estimation_method": "three_point"},
            "required_tools": [],
            "required_context": [],
        },
        "market_narrative": {
            "description": "Build macro/micro market narratives and directional theses",
            "skill_type": "analysis",
            "config": {"narrative_types": ["fundamental", "technical", "sentiment"]},
            "required_tools": ["mcp:news", "mcp:oanda"],
            "required_context": [],
        },
        "trend_assessment": {
            "description": "Evaluate trend strength and direction across timeframes",
            "skill_type": "analysis",
            "config": {"timeframes": ["H1", "H4", "D1", "W1"]},
            "required_tools": ["mcp:oanda"],
            "required_context": [],
        },
        "risk_monitoring": {
            "description": "Real-time position and exposure monitoring with alerts",
            "skill_type": "tool_use",
            "config": {"alert_threshold_pct": 1.5, "check_interval_min": 5},
            "required_tools": ["mcp:oanda"],
            "required_context": [],
        },
        "threat_scoring": {
            "description": "Score potential threats to open positions",
            "skill_type": "analysis",
            "config": {"threat_categories": ["volatility", "news", "correlation", "liquidity"]},
            "required_tools": ["mcp:oanda", "mcp:news"],
            "required_context": [],
        },
        "position_management": {
            "description": "Manage open positions — trailing stops, scaling, exits",
            "skill_type": "tool_use",
            "config": {"trailing_methods": ["atr", "fixed_pips", "swing"]},
            "required_tools": ["mcp:oanda"],
            "required_context": [],
        },
        "team_coordination": {
            "description": "Coordinate multi-agent workflows and handoffs",
            "skill_type": "planning",
            "config": {"max_parallel_tasks": 4},
            "required_tools": [],
            "required_context": [],
        },
        "decision_making": {
            "description": "Aggregate agent inputs and make go/no-go decisions",
            "skill_type": "planning",
            "config": {"min_consensus": 0.6, "veto_enabled": True},
            "required_tools": [],
            "required_context": [],
        },
        "exposure_calculation": {
            "description": "Calculate portfolio exposure by currency, correlation, direction",
            "skill_type": "analysis",
            "config": {"include_correlation": True},
            "required_tools": ["mcp:oanda"],
            "required_context": [],
        },
        "position_sizing": {
            "description": "Calculate optimal position sizes based on risk parameters",
            "skill_type": "analysis",
            "config": {"method": "fixed_fractional", "risk_per_trade_pct": 1.0},
            "required_tools": ["mcp:oanda"],
            "required_context": [],
        },
        "data_summarization": {
            "description": "Summarize trading data, performance metrics, market conditions",
            "skill_type": "communication",
            "config": {"format": "structured", "include_charts": False},
            "required_tools": [],
            "required_context": [],
        },
        "report_generation": {
            "description": "Generate formatted reports — daily, weekly, trade reviews",
            "skill_type": "communication",
            "config": {"report_types": ["daily_summary", "trade_review", "weekly_performance"]},
            "required_tools": [],
            "required_context": [],
        },
    }

    @classmethod
    def get(cls, template_name: str) -> Optional[Dict[str, Any]]:
        return cls.TEMPLATES.get(template_name)

    @classmethod
    def list_templates(cls) -> List[str]:
        return list(cls.TEMPLATES.keys())


# ─── Trading Team Role → Skill Mapping ───────────────────────────────

TRADING_TEAM_SKILLS: Dict[str, List[str]] = {
    "scout": ["market_scanning", "pattern_detection"],
    "technical_analyst": ["trading_analysis", "chart_reading"],
    "thesis_builder": ["market_narrative", "trend_assessment"],
    "validator": ["data_validation", "risk_assessment", "setup_evaluation"],
    "guardian": ["risk_monitoring", "threat_scoring", "position_management"],
    "orchestrator": ["planning", "team_coordination", "decision_making"],
    "risk_manager": ["risk_assessment", "exposure_calculation", "position_sizing"],
    "reporter": ["data_summarization", "report_generation", "communication"],
}

# Map vault folder names to agent_registry names/ids
VAULT_TO_REGISTRY: Dict[str, str] = {
    "scout": "oanda_data",
    "technical-analyst": "technical_analyst",
    "thesis-builder": "intelligence",
    "validator": "validator",
    "guardian": "trade_monitor",
    "orchestrator": "cycle_orchestrator",
    "risk-manager": "execution",
    "reporter": "reporter",
}


def _get_db(path: str = DB_PATH) -> sqlite3.Connection:
    conn = sqlite3.connect(path, isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=DELETE")
    return conn


# ─── SkillBuilder ────────────────────────────────────────────────────

class SkillBuilder:
    """Creates, attaches, and manages agent skills."""

    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path

    def create_skill(
        self,
        name: str,
        description: str,
        skill_type: str = "domain",
        config: Optional[Dict] = None,
        required_tools: Optional[List[str]] = None,
        required_context: Optional[List[str]] = None,
    ) -> Skill:
        """Create a new Skill object (not yet attached to any agent)."""
        return Skill(
            skill_name=name,
            description=description,
            skill_type=skill_type,
            config=config or {},
            required_tools=required_tools or [],
            required_context=required_context or [],
        )

    def create_skill_from_template(self, template_name: str) -> Optional[Skill]:
        """Create a Skill from a pre-built template."""
        tmpl = SkillTemplate.get(template_name)
        if not tmpl:
            logger.warning(f"Unknown skill template: {template_name}")
            return None
        return Skill(
            skill_name=template_name,
            description=tmpl["description"],
            skill_type=tmpl["skill_type"],
            config=tmpl.get("config", {}),
            required_tools=tmpl.get("required_tools", []),
            required_context=tmpl.get("required_context", []),
        )

    def attach_to_agent(self, skill: Skill, agent_id: str) -> bool:
        """Attach a skill to an agent in agents.db. Returns True on success."""
        try:
            with _get_db(self.db_path) as conn:
                conn.execute(
                    """INSERT INTO agent_skills (id, agent_id, skill_name, skill_config, proficiency_score)
                       VALUES (?, ?, ?, ?, ?)
                       ON CONFLICT (agent_id, skill_name) DO UPDATE SET
                         skill_config = excluded.skill_config,
                         proficiency_score = excluded.proficiency_score""",
                    (skill.skill_id, agent_id, skill.skill_name, skill.to_config_json(), skill.proficiency_score),
                )
                conn.commit()
            logger.info(f"Attached skill '{skill.skill_name}' to agent {agent_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to attach skill: {e}")
            return False

    def detach_from_agent(self, skill_name: str, agent_id: str) -> bool:
        """Remove a skill from an agent."""
        try:
            with _get_db(self.db_path) as conn:
                conn.execute(
                    "DELETE FROM agent_skills WHERE agent_id = ? AND skill_name = ?",
                    (agent_id, skill_name),
                )
                conn.commit()
            return True
        except Exception as e:
            logger.error(f"Failed to detach skill: {e}")
            return False

    def update_proficiency(self, skill_name: str, agent_id: str, outcome: str) -> Optional[float]:
        """
        Adjust proficiency based on outcome.
        success: +0.01, failure: -0.02, capped [0.0, 1.0].
        Returns new score or None on error.
        """
        delta = 0.01 if outcome == "success" else -0.02
        try:
            with _get_db(self.db_path) as conn:
                row = conn.execute(
                    "SELECT id, skill_config, proficiency_score FROM agent_skills WHERE agent_id = ? AND skill_name = ?",
                    (agent_id, skill_name),
                ).fetchone()
                if not row:
                    return None
                new_score = max(0.0, min(1.0, row["proficiency_score"] + delta))
                cfg = json.loads(row["skill_config"] or "{}")
                cfg["usage_count"] = cfg.get("usage_count", 0) + 1
                if outcome == "success":
                    cfg["success_count"] = cfg.get("success_count", 0) + 1
                cfg["last_used"] = datetime.now(timezone.utc).isoformat()
                conn.execute(
                    "UPDATE agent_skills SET proficiency_score = ?, skill_config = ? WHERE id = ?",
                    (new_score, json.dumps(cfg), row["id"]),
                )
                conn.commit()
            return new_score
        except Exception as e:
            logger.error(f"Failed to update proficiency: {e}")
            return None

    def get_agent_skills(self, agent_id: str) -> List[Skill]:
        """Get all skills for an agent."""
        with _get_db(self.db_path) as conn:
            rows = conn.execute(
                "SELECT * FROM agent_skills WHERE agent_id = ?", (agent_id,)
            ).fetchall()
        return [Skill.from_db_row(dict(r)) for r in rows]

    def get_skilled_agents(self, skill_name: str) -> List[Dict[str, Any]]:
        """Get all agents who have a given skill, with proficiency."""
        with _get_db(self.db_path) as conn:
            rows = conn.execute(
                """SELECT s.*, r.agent_name, r.agent_type
                   FROM agent_skills s
                   JOIN agent_registry r ON s.agent_id = r.id
                   WHERE s.skill_name = ?
                   ORDER BY s.proficiency_score DESC""",
                (skill_name,),
            ).fetchall()
        return [
            {"agent_id": r["agent_id"], "agent_name": r["agent_name"],
             "proficiency": r["proficiency_score"]}
            for r in rows
        ]

    def recommend_agent_for_task(
        self, task_description: str, available_agent_ids: List[str]
    ) -> Optional[Dict[str, Any]]:
        """
        Recommend the best agent for a task based on skill keyword matching + proficiency.
        Simple keyword overlap scoring — no LLM needed.
        """
        task_words = set(task_description.lower().split())
        best = None
        best_score = -1.0

        with _get_db(self.db_path) as conn:
            for agent_id in available_agent_ids:
                rows = conn.execute(
                    "SELECT skill_name, skill_config, proficiency_score FROM agent_skills WHERE agent_id = ?",
                    (agent_id,),
                ).fetchall()
                agent_score = 0.0
                matched_skills = []
                for r in rows:
                    cfg = json.loads(r["skill_config"] or "{}")
                    skill_words = set(r["skill_name"].replace("_", " ").lower().split())
                    desc_words = set(cfg.get("description", "").lower().split())
                    overlap = len(task_words & (skill_words | desc_words))
                    if overlap > 0:
                        agent_score += overlap * r["proficiency_score"]
                        matched_skills.append(r["skill_name"])
                if agent_score > best_score:
                    best_score = agent_score
                    name_row = conn.execute(
                        "SELECT agent_name FROM agent_registry WHERE id = ?", (agent_id,)
                    ).fetchone()
                    best = {
                        "agent_id": agent_id,
                        "agent_name": name_row["agent_name"] if name_row else agent_id,
                        "score": agent_score,
                        "matched_skills": matched_skills,
                    }
        return best

    def attach_default_skills_for_role(self, agent_id: str, role_key: str) -> List[str]:
        """
        Attach default skills based on a trading team role key.
        Compatible with agent_builder — call after creating an agent.
        Returns list of attached skill names.
        """
        skill_names = TRADING_TEAM_SKILLS.get(role_key, [])
        attached = []
        for name in skill_names:
            skill = self.create_skill_from_template(name)
            if skill and self.attach_to_agent(skill, agent_id):
                attached.append(name)
        return attached


# ─── SkillLearning ───────────────────────────────────────────────────

class SkillLearning:
    """Records skill usage and connects to the knowledge vault for agent learning."""

    def __init__(self, db_path: str = DB_PATH, vault_path: str = VAULT_PATH):
        self.db_path = db_path
        self.vault_path = vault_path
        self.builder = SkillBuilder(db_path)

    def record_skill_usage(
        self,
        agent_id: str,
        skill_name: str,
        task: str,
        outcome: str,
        notes: str = "",
    ) -> Dict[str, Any]:
        """
        Record a skill usage event:
        1. Update proficiency in agents.db
        2. Append to knowledge vault learnings
        3. Log to intelligence.db
        """
        result: Dict[str, Any] = {"agent_id": agent_id, "skill_name": skill_name, "outcome": outcome}

        # 1. Update proficiency
        new_score = self.builder.update_proficiency(skill_name, agent_id, outcome)
        result["new_proficiency"] = new_score

        # 2. Write to vault learnings
        agent_name = self._get_agent_name(agent_id)
        if agent_name:
            vault_name = agent_name.lower().replace(" ", "-").replace("_", "-")
            self._append_vault_learning(vault_name, skill_name, task, outcome, notes)

        # 3. Log to intelligence.db
        self._log_to_intelligence(agent_id, skill_name, task, outcome, notes)

        return result

    def _get_agent_name(self, agent_id: str) -> Optional[str]:
        with _get_db(self.db_path) as conn:
            row = conn.execute(
                "SELECT agent_name FROM agent_registry WHERE id = ?", (agent_id,)
            ).fetchone()
        return row["agent_name"] if row else None

    def _append_vault_learning(
        self, vault_name: str, skill_name: str, task: str, outcome: str, notes: str
    ):
        """Append learning entry to knowledge/agents/{name}/learnings.md"""
        agent_dir = os.path.join(self.vault_path, vault_name)
        os.makedirs(agent_dir, exist_ok=True)
        path = os.path.join(agent_dir, "learnings.md")
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        entry = f"\n## {ts} — {skill_name} ({outcome})\n**Task:** {task}\n"
        if notes:
            entry += f"**Notes:** {notes}\n"
        with open(path, "a") as f:
            f.write(entry)

    def _log_to_intelligence(
        self, agent_id: str, skill_name: str, task: str, outcome: str, notes: str
    ):
        """Log skill usage to intelligence.db training_data table."""
        try:
            conn = sqlite3.connect(INTEL_DB_PATH, isolation_level=None)
            conn.execute("PRAGMA journal_mode=DELETE")
            # Check if training_data table exists
            tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
            if "training_data" in tables:
                conn.execute(
                    """INSERT INTO training_data (id, category, input_text, output_text, metadata, created_at)
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    (
                        str(uuid.uuid4()),
                        f"skill_usage:{skill_name}",
                        task,
                        outcome,
                        json.dumps({"agent_id": agent_id, "notes": notes}),
                        datetime.now(timezone.utc).isoformat(),
                    ),
                )
                conn.commit()
            conn.close()
        except Exception as e:
            logger.warning(f"Could not log to intelligence.db: {e}")


# ─── Provisioning: populate trading team skills ──────────────────────

def provision_trading_team(db_path: str = DB_PATH, vault_path: str = VAULT_PATH) -> Dict[str, List[str]]:
    """
    Pre-populate skills for the 8 trading team agents.
    Writes to agents.db AND updates knowledge vault profiles.
    Returns {agent_name: [skill_names]}.
    """
    builder = SkillBuilder(db_path)
    results: Dict[str, List[str]] = {}

    with _get_db(db_path) as conn:
        for vault_folder, registry_name in VAULT_TO_REGISTRY.items():
            # Normalize role key: vault folder "technical-analyst" → "technical_analyst"
            role_key = vault_folder.replace("-", "_")
            skill_names = TRADING_TEAM_SKILLS.get(role_key, [])
            if not skill_names:
                continue

            # Find agent in registry
            row = conn.execute(
                "SELECT id, agent_name FROM agent_registry WHERE agent_name = ?",
                (registry_name,),
            ).fetchone()
            if not row:
                logger.warning(f"Agent '{registry_name}' not found in registry, skipping")
                continue

            agent_id = row["id"]
            agent_name = row["agent_name"]
            attached = []

            for sname in skill_names:
                skill = builder.create_skill_from_template(sname)
                if skill and builder.attach_to_agent(skill, agent_id):
                    attached.append(sname)

            results[agent_name] = attached

            # Update vault profile
            _update_vault_profile(vault_path, vault_folder, attached)

    logger.info(f"Provisioned trading team skills: {results}")
    return results


def _update_vault_profile(vault_path: str, vault_folder: str, skill_names: List[str]):
    """Append skills section to the agent's vault profile.md if not already present."""
    profile_path = os.path.join(vault_path, vault_folder, "profile.md")
    if not os.path.exists(profile_path):
        return

    with open(profile_path, "r") as f:
        content = f.read()

    if "## Skills" in content:
        return  # Already has skills section

    skills_section = "\n## Skills\n" + "\n".join(f"- {s}" for s in skill_names) + "\n"
    with open(profile_path, "a") as f:
        f.write(skills_section)


# ─── CLI / direct execution ─────────────────────────────────────────

if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    if len(sys.argv) > 1 and sys.argv[1] == "provision":
        results = provision_trading_team()
        for agent, skills in results.items():
            print(f"  {agent}: {', '.join(skills)}")
        print("Done.")
    else:
        print("Usage: python -m Handler.modules.skill_builder provision")
        print("  provision — attach trading team skills to agents in DB + vault")
