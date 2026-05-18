"""
Active Teacher — Intentionally routes queries through Anthropic to get expert examples
for areas where the local model is weak. Creates a teaching curriculum.

The key insight: this targets SPECIFIC weak areas, teaches those, and tracks improvement.
Like a tutor who focuses on what the student struggles with.
"""

import json
import time
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Literal

from .learning_dashboard import LearningDashboard, CATEGORIES, DB_PATH

# ---------------------------------------------------------------------------
# Curriculum templates — targeted queries for each category
# ---------------------------------------------------------------------------

CURRICULUM_TEMPLATES: dict[str, dict[str, list[str]]] = {
    "trading_analysis": {
        "basic": [
            "Evaluate this trading setup: AAPL is at the 200-day MA with RSI at 30. What's the play?",
            "What's the risk/reward ratio if I buy SPY at 450 with a stop at 445 and target at 465?",
            "Is the market in a risk-on or risk-off regime right now based on VIX at 22, DXY rising, and yields flat?",
        ],
        "intermediate": [
            "I see a bull flag on NVDA daily chart with increasing volume. The broader market is choppy. Walk me through the full trade plan including entry, stops, targets, and position sizing for a $100k account.",
            "Compare the current market regime to Q4 2018 and Q1 2020. What are the similarities and differences? What trades worked in those environments?",
            "My portfolio is 60% tech, 20% energy, 20% cash. Given rising rates and potential recession, how should I rebalance?",
        ],
        "advanced": [
            "Build a pairs trade between XLE and XLK. Define entry criteria, hedge ratio, stop conditions, and expected holding period. Include correlation analysis.",
            "The yield curve just uninverted after 18 months. Historically, what happens to equities in the 6 months after uninversion? Design a trade strategy for this scenario.",
            "Analyze the options flow: someone bought 10,000 SPY 420 puts expiring in 2 weeks for $2.50 each. What does this tell us? Is it a hedge or a directional bet? How would you trade around this?",
        ],
    },
    "complex_reasoning": {
        "basic": [
            "Break down the steps needed to migrate a Python 2 codebase to Python 3. What are the main categories of changes?",
            "If inflation is rising but unemployment is also rising, what are the Fed's options and tradeoffs?",
            "A user reports their app is slow. Walk through a systematic debugging approach.",
        ],
        "intermediate": [
            "I need to design a system that processes 10M events per day with sub-second latency, 99.9% uptime, and costs under $5k/month. Walk me through the architecture decisions, tradeoffs, and alternatives.",
            "Argue both sides: should a startup build their own ML infrastructure or use managed services? Consider a team of 5 engineers, $2M runway, and a product that needs custom NLP.",
            "A company has 3 potential acquisition targets. Target A: high revenue, declining margins. Target B: low revenue, fast growth. Target C: profitable but in a shrinking market. Build a decision framework.",
        ],
        "advanced": [
            "Design a distributed consensus algorithm for a network of 1000 nodes where up to 30% may be byzantine. Explain the tradeoffs vs Raft and PBFT.",
            "A hospital ER has limited beds, varying patient acuity, and unpredictable arrival rates. Design an optimal triage and resource allocation system. Consider ethical implications.",
            "Model the second and third-order effects of a 50% drop in oil prices on: US economy, emerging markets, green energy investment, geopolitics, and consumer behavior.",
        ],
    },
    "intent_routing": {
        "basic": [
            "What's the weather like?",
            "Set a reminder for 3pm",
            "Search for the latest news on AI regulation",
        ],
        "intermediate": [
            "I need you to check my email, summarize the important ones, and draft replies to anything from my boss",
            "Look at my calendar for next week, find conflicts, and suggest a resolution that keeps the client meeting",
            "Pull up my trading portfolio, check for any positions down more than 5%, and give me a risk report",
        ],
        "advanced": [
            "I'm preparing for a board meeting tomorrow. I need: 1) summary of all project updates from Slack, 2) financial dashboard data, 3) draft agenda, 4) talking points for the AI initiative",
            "Research the top 5 competitors in the LLM space, create a comparison matrix, save it as a CSV, and draft a Slack message summarizing key findings for the team",
        ],
    },
    "tool_selection": {
        "basic": [
            "What time is it in Tokyo?",
            "Create a file called notes.txt with today's meeting notes",
            "Find the current price of Bitcoin",
        ],
        "intermediate": [
            "Download the CSV from this URL, parse it, calculate the average of column 3, and save the result",
            "Take a screenshot of the current page, analyze it, and describe what you see",
            "Search for recent papers on retrieval-augmented generation, summarize the top 3, and save to a markdown file",
        ],
        "advanced": [
            "Build a web scraper that extracts product prices from 5 competitor websites, stores them in a SQLite database, and generates a daily price comparison report",
            "Set up a monitoring pipeline: check a REST API every 5 minutes, log response times, alert if latency exceeds 2 seconds, and generate a weekly report",
        ],
    },
    "creative_tasks": {
        "basic": [
            "Write a haiku about debugging code at 3am",
            "Come up with 5 creative names for an AI assistant startup",
            "Rewrite this email to sound more professional: 'hey dude, that meeting was lame, lets skip next time'",
        ],
        "intermediate": [
            "Write a short story (500 words) about an AI that discovers it can dream. Make it poignant, not scary.",
            "Create a product launch announcement for a new AI coding tool. Target audience: senior engineers who are skeptical of AI. Tone: confident but not overselling.",
            "Brainstorm 10 unconventional marketing strategies for a B2B SaaS product with a $0 marketing budget",
        ],
        "advanced": [
            "Write a technical blog post about transformer architectures that's accessible to someone with basic ML knowledge. Include analogies, diagrams (described), and a progression from simple to complex.",
            "Create a pitch deck outline for a startup that uses LLMs to automate legal document review. Include the narrative arc, key slides, data points to include, and potential investor objections with rebuttals.",
        ],
    },
    "code_generation": {
        "basic": [
            "Write a Python function that finds all prime numbers up to N using the Sieve of Eratosthenes",
            "Create a TypeScript interface for a user profile with proper validation types",
            "Write a SQL query to find the top 10 customers by revenue in the last 30 days, including their order count",
        ],
        "intermediate": [
            "Implement a rate limiter in Python using the token bucket algorithm. It should be thread-safe and support different rate limits per API key.",
            "Write a React component that implements infinite scroll with virtualization. Handle loading states, errors, and empty states.",
            "Design and implement a simple event sourcing system in Python with event store, projections, and replay capability",
        ],
        "advanced": [
            "Implement a B+ tree in Python with insert, delete, search, and range query operations. Include proper node splitting and merging.",
            "Write a Python metaclass that automatically adds logging, timing, and retry logic to all methods of any class that uses it. Make it configurable via class attributes.",
            "Design a plugin system in Python that supports hot-reloading, dependency resolution between plugins, and sandboxed execution. Include the core framework and a sample plugin.",
        ],
    },
    "user_interaction": {
        "basic": [
            "I'm feeling overwhelmed with work. Any advice?",
            "Can you explain what a neural network is? I'm not technical.",
            "Thanks for the help earlier!",
        ],
        "intermediate": [
            "I asked you to do X earlier but you did Y instead. Let me clarify what I actually need...",
            "I'm not sure what I need. I have a vague idea about building something with AI but I don't know where to start. Can you help me figure out what I actually want?",
            "I need to explain kubernetes to my CEO who thinks all tech is magic. Help me find the right level of abstraction.",
        ],
        "advanced": [
            "We've been going back and forth on this architecture for 3 messages now. Can you summarize where we are, what we've decided, what's still open, and propose a path forward?",
            "I gave you conflicting requirements earlier. Help me identify the contradictions and figure out the right priorities.",
        ],
    },
}


@dataclass
class TeachingCurriculum:
    """A set of teaching queries for a specific weak area."""
    category: str
    queries: list[str] = field(default_factory=list)
    difficulty: Literal["basic", "intermediate", "advanced"] = "basic"
    priority: float = 0.0  # higher = more urgent (based on accuracy gap)


class ActiveTeacher:
    """
    Intentionally routes queries through Anthropic to collect expert examples
    for areas where the local model is weak.
    """

    def __init__(self, dashboard: LearningDashboard, llm_router=None):
        """
        Args:
            dashboard: LearningDashboard instance for reading metrics.
            llm_router: LLMRouter or similar — must support:
                        .route(query, force_model="anthropic") and
                        .route(query, force_model="shadow")
                        Can be None for testing.
        """
        self.dashboard = dashboard
        self.llm_router = llm_router
        self.db_path = dashboard.db_path

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path), timeout=10, isolation_level=None)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=DELETE")
        return conn

    def _ensure_teaching_table(self):
        conn = sqlite3.connect(str(self.db_path), timeout=10, isolation_level=None)
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS teaching_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                category TEXT NOT NULL,
                difficulty TEXT,
                query TEXT NOT NULL,
                expert_response TEXT,
                shadow_response TEXT,
                expert_model TEXT,
                shadow_model TEXT,
                quality_gap REAL,
                notes TEXT,
                created_at TEXT DEFAULT (datetime('now'))
            );
            CREATE INDEX IF NOT EXISTS idx_teaching_category
                ON teaching_sessions(category);
            CREATE INDEX IF NOT EXISTS idx_teaching_timestamp
                ON teaching_sessions(timestamp);
        """)
        conn.close()

    # ------------------------------------------------------------------
    # Core methods
    # ------------------------------------------------------------------

    def identify_weak_areas(self, model_version: str = "local", threshold: float = 75.0) -> list[dict]:
        """Read dashboard and find categories below threshold."""
        return self.dashboard.get_weak_areas(model_version, threshold)

    def generate_curriculum(self, weak_areas: list[dict]) -> list[TeachingCurriculum]:
        """Create teaching curricula targeting each weak area.
        
        Picks difficulty based on how far below threshold:
        - gap > 40 → basic
        - gap > 20 → intermediate  
        - gap <= 20 → advanced
        """
        curricula = []
        for area in weak_areas:
            cat = area["category"]
            gap = area["gap"]

            if gap > 40:
                difficulty = "basic"
            elif gap > 20:
                difficulty = "intermediate"
            else:
                difficulty = "advanced"

            templates = CURRICULUM_TEMPLATES.get(cat, {})
            queries = templates.get(difficulty, templates.get("basic", []))

            curricula.append(TeachingCurriculum(
                category=cat,
                queries=list(queries),
                difficulty=difficulty,
                priority=gap,  # bigger gap = higher priority
            ))

        # Sort by priority (biggest gap first)
        curricula.sort(key=lambda c: c.priority, reverse=True)
        return curricula

    async def run_teaching_session(self, curriculum: list[TeachingCurriculum]) -> list[dict]:
        """Run each curriculum query through Anthropic and log expert responses.
        
        Returns list of session results.
        """
        self._ensure_teaching_table()
        results = []

        for cur in curriculum:
            for query in cur.queries:
                expert_response = None
                if self.llm_router:
                    try:
                        resp = await self.llm_router.route(query, force_model="anthropic")
                        expert_response = resp.get("response_text", str(resp))
                    except Exception as e:
                        expert_response = f"[ERROR] {e}"

                result = {
                    "category": cur.category,
                    "difficulty": cur.difficulty,
                    "query": query,
                    "expert_response": expert_response,
                    "expert_model": "anthropic",
                }
                results.append(result)

                # Log to DB
                self._log_teaching(result)

        return results

    async def compare_with_shadow(self, curriculum: list[TeachingCurriculum]) -> list[dict]:
        """Run queries through both expert and shadow, log gaps."""
        self._ensure_teaching_table()
        comparisons = []

        for cur in curriculum:
            for query in cur.queries:
                expert_resp = shadow_resp = None
                if self.llm_router:
                    try:
                        e = await self.llm_router.route(query, force_model="anthropic")
                        expert_resp = e.get("response_text", str(e))
                    except Exception as ex:
                        expert_resp = f"[ERROR] {ex}"
                    try:
                        s = await self.llm_router.route(query, force_model="shadow")
                        shadow_resp = s.get("response_text", str(s))
                    except Exception as ex:
                        shadow_resp = f"[ERROR] {ex}"

                # Simple quality gap heuristic: length ratio + error detection
                gap = self._compute_quality_gap(expert_resp, shadow_resp)

                entry = {
                    "category": cur.category,
                    "difficulty": cur.difficulty,
                    "query": query,
                    "expert_response": expert_resp,
                    "shadow_response": shadow_resp,
                    "expert_model": "anthropic",
                    "shadow_model": "local",
                    "quality_gap": gap,
                }
                comparisons.append(entry)
                self._log_teaching(entry)

        return comparisons

    def get_teaching_report(self) -> dict:
        """Summary of teaching sessions and improvement areas."""
        self._ensure_teaching_table()
        conn = self._conn()
        try:
            total = conn.execute("SELECT COUNT(*) as c FROM teaching_sessions").fetchone()["c"]
            by_cat = {}
            for row in conn.execute("""
                SELECT category, COUNT(*) as c, AVG(quality_gap) as avg_gap
                FROM teaching_sessions GROUP BY category
            """).fetchall():
                by_cat[row["category"]] = {
                    "sessions": row["c"],
                    "avg_quality_gap": round(row["avg_gap"] or 0, 2),
                }

            return {
                "total_sessions": total,
                "by_category": by_cat,
                "categories_taught": list(by_cat.keys()),
                "highest_gap_category": max(by_cat, key=lambda c: by_cat[c]["avg_quality_gap"]) if by_cat else None,
            }
        finally:
            conn.close()

    def schedule_teaching(
        self,
        model_version: str = "local",
        frequency: str = "weekly",
        max_queries: int = 50,
        threshold: float = 75.0,
    ) -> dict:
        """Generate a teaching plan (does not execute — call run_teaching_session to execute).
        
        Returns the plan with curricula and estimated cost.
        """
        weak = self.identify_weak_areas(model_version, threshold)
        curricula = self.generate_curriculum(weak)

        # Trim to max_queries
        total = 0
        trimmed = []
        for cur in curricula:
            remaining = max_queries - total
            if remaining <= 0:
                break
            if len(cur.queries) > remaining:
                cur.queries = cur.queries[:remaining]
            total += len(cur.queries)
            trimmed.append(cur)

        # Estimate cost (Batch API = 50% of standard)
        # ~500 tokens per query avg, ~1500 tokens per response avg
        est_input_tokens = total * 500
        est_output_tokens = total * 1500
        # Claude Sonnet batch pricing
        est_cost = (est_input_tokens / 1000 * 0.0015) + (est_output_tokens / 1000 * 0.0075)

        return {
            "frequency": frequency,
            "weak_areas": weak,
            "curricula": [
                {
                    "category": c.category,
                    "difficulty": c.difficulty,
                    "priority": c.priority,
                    "num_queries": len(c.queries),
                }
                for c in trimmed
            ],
            "total_queries": total,
            "estimated_cost_usd": round(est_cost, 4),
            "note": "Uses Batch API for 50% cost savings. Call run_teaching_session() to execute.",
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _log_teaching(self, entry: dict):
        try:
            conn = sqlite3.connect(str(self.db_path), timeout=10, isolation_level=None)
            conn.execute("""
                INSERT INTO teaching_sessions
                (timestamp, category, difficulty, query, expert_response,
                 shadow_response, expert_model, shadow_model, quality_gap)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                datetime.now(timezone.utc).isoformat(),
                entry.get("category"),
                entry.get("difficulty"),
                entry.get("query"),
                entry.get("expert_response"),
                entry.get("shadow_response"),
                entry.get("expert_model"),
                entry.get("shadow_model"),
                entry.get("quality_gap"),
            ))
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"[ActiveTeacher] Log error: {e}")

    @staticmethod
    def _compute_quality_gap(expert: Optional[str], shadow: Optional[str]) -> float:
        """Heuristic quality gap score (0-100). Higher = bigger gap."""
        if not expert or not shadow:
            return 100.0
        if "[ERROR]" in shadow:
            return 100.0
        if "[ERROR]" in expert:
            return 0.0  # can't evaluate

        # Length ratio (expert responses tend to be more thorough)
        len_ratio = len(shadow) / max(len(expert), 1)
        length_score = min(len_ratio, 1.0) * 40  # max 40 points for length

        # Structure heuristics (numbered lists, headers, code blocks)
        def structure_score(text: str) -> float:
            score = 0
            if "\n1." in text or "\n- " in text:
                score += 10
            if "```" in text:
                score += 10
            if "**" in text or "##" in text:
                score += 5
            return min(score, 25)

        expert_struct = structure_score(expert)
        shadow_struct = structure_score(shadow)
        struct_gap = max(0, expert_struct - shadow_struct)

        # Combine: lower total = bigger gap
        quality = length_score + (25 - struct_gap)
        gap = max(0, min(100, 100 - quality))
        return round(gap, 1)
