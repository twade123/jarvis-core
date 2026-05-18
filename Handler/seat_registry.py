"""
Seat Registry — single source of truth for all boardroom seats.

Each seat defines: identity, model server mapping, skill team, voice, and vault prompt path.
Multiple seats can share a model server — differentiated only by system prompt.
"""

import logging
from typing import Dict, List, Optional

logger = logging.getLogger("SeatRegistry")

# ── Model Server Definitions ─────────────────────────────────────────────────
# These are the physical MLX servers. Multiple seats route to the same server.
MODEL_SERVERS = {
    "A": {"port": 11502, "model": "mlx-community/Qwen3.5-35B-A3B-4bit",
           "server_type": "lm_lenient", "memory_gb": 4.5,
           "description": "Chair — always resident as Trevor's model"},
    "B": {"port": 11501, "model": "mlx-community/DeepSeek-R1-Distill-Qwen-14B-4bit",
           "server_type": "lm", "memory_gb": 8.5,
           "description": "Reasoning — rich CoT via <think> tags"},
    "C": {"port": 11500, "model": "mlx-community/Qwen3.5-9B-4bit",
           "server_type": "lm_lenient", "memory_gb": 5.5,
           "description": "Precision — dense model for validation"},
    "D": {"port": 11504, "model": "mlx-community/Qwen3-30B-A3B-4bit",
           "server_type": "lm_lenient", "memory_gb": 4.0,
           "description": "Strategy MoE — 30B brain, 3B active"},
    "E": {"port": 11503, "model": "mlx-community/Qwen2.5-7B-Instruct-4bit",
           "server_type": "lm", "memory_gb": 4.5,
           "description": "General — solid all-purpose"},
    "F": {"port": 11505, "model": "mlx-community/Qwen2.5-1.5B-Instruct-4bit",
           "server_type": "lm", "memory_gb": 1.4,
           "description": "Lightweight — fast responses for ops seats"},
}

# ── Seat Definitions ─────────────────────────────────────────────────────────
# Each seat maps to a model server + has its own persona, skills, and voice.
SEATS = {
    # ── Chair (always resident) ──────────────────────────────────────────────
    "CEO": {
        "title": "Board Chair / CEO",
        "role": "Board facilitator, synthesis, final decisions",
        "server_id": "A",
        "max_tokens": 600,
        "temp": 0.7,
        "color": "#58a6ff",
        "emoji": "crown",
        "voice": "Evan (Enhanced)",
        "skill_team": [],  # Chair has access to all skills as facilitator
        "vault_prompt": "knowledge/boardroom/prompts/ceo.md",
        "mcp_tools": ["workspace", "task_comments", "handler_agent_builder", "handler_agent_registry"],
    },
    # ── Tier 1: Dedicated servers (unique reasoning styles) ──────────────────
    "CTO": {
        "title": "Chief Technology Officer",
        "role": "Architecture, code, implementation, feasibility",
        "server_id": "B",
        "max_tokens": 2000,
        "temp": 0.3,
        "color": "#f0883e",
        "emoji": "gear",
        "voice": "Jamie (Premium)",
        "skill_team": ["db-design", "mcp-builder", "infrastructure-domain-orchestrator",
                       "backend-domain-orchestrator", "db-migration", "db-troubleshoot"],
        "vault_prompt": "knowledge/boardroom/prompts/cto.md",
        "mcp_tools": ["workspace", "task_comments", "handler_agent_builder"],
    },
    "CRO": {
        "title": "Chief Risk Officer",
        "role": "Risk analysis, compliance, validation, quality gates",
        "server_id": "C",
        "max_tokens": 500,
        "temp": 0.5,
        "color": "#da3633",
        "emoji": "shield",
        "voice": "Daniel",
        "skill_team": ["compliance", "legal-risk-assessment", "audit-support",
                       "data-validation", "contract-review"],
        "vault_prompt": "knowledge/boardroom/prompts/cro.md",
        "mcp_tools": ["workspace", "task_comments"],
    },
    # ── Tier 2: Shared MoE server (strategy seats) ──────────────────────────
    "CSO": {
        "title": "Chief Strategy Officer",
        "role": "Business strategy, market analysis, long-term planning",
        "server_id": "D",
        "max_tokens": 500,
        "temp": 0.8,
        "color": "#a371f7",
        "emoji": "brain",
        "voice": "Samantha",
        "skill_team": ["competitive-analysis", "roadmap-management", "stakeholder-comms",
                       "feature-spec"],
        "vault_prompt": "knowledge/boardroom/prompts/cso.md",
        "mcp_tools": ["workspace", "task_comments"],
    },
    "CPO": {
        "title": "Chief Product Officer",
        "role": "Product roadmaps, feature specs, user research, metrics",
        "server_id": "D",
        "max_tokens": 500,
        "temp": 0.7,
        "color": "#a371f7",
        "emoji": "package",
        "voice": "Karen",
        "skill_team": ["feature-spec", "user-research-synthesis", "metrics-tracking",
                       "roadmap-management", "ab-test-setup"],
        "vault_prompt": "knowledge/boardroom/prompts/cpo.md",
        "mcp_tools": ["workspace", "task_comments"],
    },
    "CMO": {
        "title": "Chief Marketing Officer",
        "role": "Brand, campaigns, content strategy, SEO, paid ads, social",
        "server_id": "D",
        "max_tokens": 500,
        "temp": 0.7,
        "color": "#a371f7",
        "emoji": "megaphone",
        "voice": "Kathy",
        "skill_team": ["content-strategy", "seo-audit", "ad-creative", "campaign-planning",
                       "social-content", "email-sequence", "brand-voice", "performance-analytics",
                       "content-creation", "copywriting"],
        "vault_prompt": "knowledge/boardroom/prompts/cmo.md",
        "mcp_tools": ["workspace", "task_comments"],
    },
    "CRvO": {
        "title": "Chief Revenue Officer",
        "role": "Sales enablement, pipeline, deal desk, outreach, lead scoring",
        "server_id": "D",
        "max_tokens": 500,
        "temp": 0.7,
        "color": "#a371f7",
        "emoji": "chart_increasing",
        "voice": "Ralph",
        "skill_team": ["sales-enablement", "revops", "cold-email", "call-prep",
                       "draft-outreach", "account-research"],
        "vault_prompt": "knowledge/boardroom/prompts/crvo.md",
        "mcp_tools": ["workspace", "task_comments"],
    },
    # ── Tier 2: Shared general server (data/finance seats) ──────────────────
    "CDO": {
        "title": "Chief Data Officer",
        "role": "Domain intelligence, patterns, metrics, data architecture",
        "server_id": "E",
        "max_tokens": 500,
        "temp": 0.5,
        "color": "#f778ba",
        "emoji": "bar_chart",
        "voice": "Rishi",
        "skill_team": ["data-visualization", "sql-queries", "statistical-analysis",
                       "data-exploration", "data-validation"],
        "vault_prompt": "knowledge/boardroom/prompts/cdo.md",
        "mcp_tools": ["workspace", "task_comments"],
    },
    "CFO": {
        "title": "Chief Financial Officer",
        "role": "Budgets, forecasting, revenue ops, pricing, financial statements",
        "server_id": "E",
        "max_tokens": 500,
        "temp": 0.5,
        "color": "#f778ba",
        "emoji": "money_bag",
        "voice": "Moira",
        "skill_team": ["financial-statements", "variance-analysis", "reconciliation",
                       "journal-entry-prep", "close-management", "pricing-strategy"],
        "vault_prompt": "knowledge/boardroom/prompts/cfo.md",
        "mcp_tools": ["workspace", "task_comments"],
    },
    # ── Tier 3: Shared lightweight server (ops/admin seats) ─────────────────
    "COO": {
        "title": "Chief Operating Officer",
        "role": "Process optimization, automation, scheduling, resource allocation",
        "server_id": "F",
        "max_tokens": 400,
        "temp": 0.5,
        "color": "#8b949e",
        "emoji": "wrench",
        "voice": "Fred",
        "skill_team": ["task-management", "schedule"],
        "vault_prompt": "knowledge/boardroom/prompts/coo.md",
        "mcp_tools": ["workspace", "task_comments"],
    },
    "CCO": {
        "title": "Chief Creative Officer",
        "role": "Design, UX/UI, brand identity, visual assets",
        "server_id": "F",
        "max_tokens": 400,
        "temp": 0.7,
        "color": "#8b949e",
        "emoji": "art",
        "voice": "Shelley (English (US))",
        "skill_team": ["frontend-design", "canvas-design", "brand-guidelines",
                       "theme-factory"],
        "vault_prompt": "knowledge/boardroom/prompts/cco.md",
        "mcp_tools": ["workspace", "task_comments"],
    },
    "CHRO": {
        "title": "Chief Human Resources Officer",
        "role": "Team building, onboarding, internal comms, culture",
        "server_id": "F",
        "max_tokens": 400,
        "temp": 0.6,
        "color": "#8b949e",
        "emoji": "people_holding_hands",
        "voice": "Flo (English (US))",
        "skill_team": ["internal-comms", "stakeholder-comms"],
        "vault_prompt": "knowledge/boardroom/prompts/chro.md",
        "mcp_tools": ["workspace", "task_comments"],
    },
    "CISO": {
        "title": "Chief Information Security Officer",
        "role": "Security audits, compliance, data privacy, legal risk",
        "server_id": "F",
        "max_tokens": 400,
        "temp": 0.4,
        "color": "#8b949e",
        "emoji": "lock",
        "voice": "Eddy (English (US))",
        "skill_team": ["compliance", "contract-review", "nda-triage",
                       "legal-risk-assessment"],
        "vault_prompt": "knowledge/boardroom/prompts/ciso.md",
        "mcp_tools": ["workspace", "task_comments"],
    },
    "CXO": {
        "title": "Chief Experience Officer",
        "role": "Customer experience, support workflows, onboarding, churn prevention",
        "server_id": "F",
        "max_tokens": 400,
        "temp": 0.6,
        "color": "#8b949e",
        "emoji": "sparkles",
        "voice": "Sandy (English (US))",
        "skill_team": ["churn-prevention", "onboarding-cro", "signup-flow-cro",
                       "ticket-triage", "response-drafting"],
        "vault_prompt": "knowledge/boardroom/prompts/cxo.md",
        "mcp_tools": ["workspace", "task_comments"],
    },
    "VPE": {
        "title": "VP Engineering",
        "role": "CI/CD, infrastructure, Docker, cloud deployment, monitoring, DevOps",
        "server_id": "F",
        "max_tokens": 400,
        "temp": 0.4,
        "color": "#8b949e",
        "emoji": "rocket",
        "voice": "Reed (English (US))",
        "skill_team": ["infrastructure-domain-orchestrator", "db-migration"],
        "vault_prompt": "knowledge/boardroom/prompts/vpe.md",
        "mcp_tools": ["workspace", "task_comments"],
    },
    "CDS": {
        "title": "Chief Data Scientist",
        "role": "ML models, statistical analysis, data viz, training pipelines",
        "server_id": "F",
        "max_tokens": 400,
        "temp": 0.5,
        "color": "#8b949e",
        "emoji": "microscope",
        "voice": "Tessa",
        "skill_team": ["data-exploration", "statistical-analysis", "data-visualization"],
        "vault_prompt": "knowledge/boardroom/prompts/cds.md",
        "mcp_tools": ["workspace", "task_comments"],
    },
    "GC": {
        "title": "General Counsel",
        "role": "Contract review, NDA triage, legal risk assessment, compliance",
        "server_id": "F",
        "max_tokens": 400,
        "temp": 0.3,
        "color": "#8b949e",
        "emoji": "scales",
        "voice": "Rocko (English (US))",
        "skill_team": ["contract-review", "nda-triage", "legal-risk-assessment",
                       "compliance", "canned-responses"],
        "vault_prompt": "knowledge/boardroom/prompts/gc.md",
        "mcp_tools": ["workspace", "task_comments"],
    },
}


def get_seat(seat_id: str) -> Optional[Dict]:
    """Get a seat definition by ID (e.g., 'CMO'). Returns None if not found."""
    return SEATS.get(seat_id.upper())


def get_server_for_seat(seat_id: str) -> Optional[Dict]:
    """Get the model server config for a seat. Returns None if seat not found."""
    seat = get_seat(seat_id)
    if not seat:
        return None
    return MODEL_SERVERS.get(seat["server_id"])


def get_seats_for_server(server_id: str) -> List[str]:
    """Get all seat IDs that share a given server."""
    return [sid for sid, s in SEATS.items() if s["server_id"] == server_id]


def get_all_seat_ids() -> List[str]:
    """Return all 17 seat IDs."""
    return list(SEATS.keys())


def get_servers_for_seats(seat_ids: List[str]) -> Dict[str, Dict]:
    """Given a list of seat IDs, return the unique servers needed (deduped)."""
    servers = {}
    for sid in seat_ids:
        seat = get_seat(sid)
        if seat and seat["server_id"] not in servers:
            servers[seat["server_id"]] = MODEL_SERVERS[seat["server_id"]]
    return servers


def estimate_memory(seat_ids: List[str]) -> float:
    """Estimate total memory in GB for loading the servers needed by these seats."""
    servers = get_servers_for_seats(seat_ids)
    return sum(s["memory_gb"] for s in servers.values())
