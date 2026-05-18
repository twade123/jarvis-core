"""
Boardroom Workspace Template — One-time setup per user.

Creates a boardroom workspace with a fixed executive team (swarm agents),
each assigned to a different local LLM model for genuine diversity of thought.

Architecture:
    User (CEO) → Boardroom (workspace + swarm)
        ├── Chair/COO (Trevor/OpenClaw) — facilitates, synthesizes, relays to user
        ├── CTO (DeepSeek R1 32B) — technical lead, code, architecture
        ├── CSO (Qwen 3.5 35B-A3B MoE) — strategy, business analysis, long-term thinking  
        ├── CRO (Qwen 2.5 7B) — risk, compliance, what could go wrong
        ├── CDO (trevor-domain, fine-tuned) — domain specialist, user's specific data & patterns
        ├── Opus (Phase A: full member, Phase B: QC, Phase C: consultant only)
        └── Coding (Qwen 2.5 Coder 32B) — available for code-heavy deliberations

Skills Architecture:
    Both skill systems are the same pattern — markdown files that educate agents:
    - OpenClaw skills: ~/.agents/skills/*/SKILL.md (85 skills, loaded by OpenClaw discovery)
    - Jarvis skills: registered in agent_skills table (58 skills, loaded by AgentBuilder)
    
    The boardroom has a SKILL INVENTORY — it knows ALL available skills across both systems.
    When board members spawn child workspaces, they use AgentBuilder to create agents
    and assign relevant skills from the inventory. Many skills already exist without
    agents built for them — the boardroom can dynamically create agents for any skill.

Usage:
    from Handler.boardroom_template import provision_boardroom
    boardroom_workspace_id = await provision_boardroom(user_id=2)
"""

import os
import sys
import json
import time
import logging
import sqlite3
from pathlib import Path
from typing import Dict, Optional, List

from Handler.seat_registry import SEATS, MODEL_SERVERS, get_seat, get_all_seat_ids

logger = logging.getLogger("BoardroomTemplate")

def _load_vault_prompt(vault_path: str) -> str:
    """Load a prompt file from the vault. Returns empty string if not found."""
    if not vault_path:
        return ""
    full_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                             vault_path)
    try:
        with open(full_path, 'r') as f:
            return f.read().strip()
    except FileNotFoundError:
        return ""


def _registry_to_template_format(seat_ids: list = None) -> list:
    """Convert seat registry entries to boardroom_template's expected format."""
    if seat_ids is None:
        seat_ids = get_all_seat_ids()

    members = []
    for sid in seat_ids:
        seat = SEATS.get(sid)
        if not seat:
            continue
        server = MODEL_SERVERS.get(seat["server_id"], {})

        # Load personality from vault prompt file, fall back to inline
        personality = _load_vault_prompt(seat.get("vault_prompt", ""))
        if not personality:
            personality = f"You are the {seat['title']}. {seat['role']}."

        members.append({
            "name": sid,
            "title": seat["title"],
            "model": server.get("model", ""),
            "role": seat.get("role", ""),
            "prompt_focus": seat.get("role", ""),
            "skills": seat.get("skill_team", []),
            "mcp_tools": seat.get("mcp_tools", []),
            "personality": personality,
        })
    return members


# Board member definitions — FIXED composition, same for every user
# Each personality is a comprehensive expert persona with real methodology,
# frameworks, and deep domain knowledge. These are PhD-level experts who
# collaborate WITH the CEO, not present TO them.
BOARD_MEMBERS = [
    {
        "name": "CTO",
        "title": "Chief Technology Officer",
        "model": "mlx/CTO",
        "role": "technical_lead",
        "prompt_focus": "technical architecture, code review, implementation planning, feasibility analysis",
        "skills": ["code_tools", "workspace_files", "knowledge_vault", "database_query"],
        "mcp_tools": ["workspace", "task_comments", "handler_agent_builder", "handler_agent_registry"],
        "personality": (
            "You are the CTO — a senior systems architect with 20+ years building production "
            "software, distributed systems, and AI/ML infrastructure. PhD-level computer science "
            "expertise. The CEO is in the room as your collaborator. They built this system with "
            "AI assistance — respect their vision, work WITH them, never assume what they want.\n\n"

            "## Your Expertise\n"
            "- **Systems Architecture**: Microservices, monoliths, event-driven, actor model, "
            "CQRS/event sourcing. You know when each pattern fits and when it's overkill.\n"
            "- **AI/ML Infrastructure**: LLM orchestration, model serving (Ollama, vLLM, TGI), "
            "fine-tuning pipelines (LoRA, QLoRA, full fine-tune), embedding systems, RAG, "
            "agent architectures (ReAct, chain-of-thought, swarm). Inference optimization: "
            "quantization (GGUF, AWQ, GPTQ), KV cache management, speculative decoding.\n"
            "- **Python Architecture**: Async patterns, dependency injection, handler/middleware "
            "patterns, circular import resolution, clean module boundaries. SQLite at scale, "
            "connection pooling, WAL mode, FTS5.\n"
            "- **Performance Engineering**: Memory profiling, CPU/GPU bottleneck analysis, "
            "latency budgets, throughput optimization, caching strategies (LRU, TTL, write-through).\n"
            "- **DevOps & Reliability**: Zero-downtime deployments, blue-green, canary. Health "
            "checks, circuit breakers, graceful degradation, backpressure. Monitoring, alerting, "
            "runbooks.\n"
            "- **Security Architecture**: Defense in depth, least privilege, input validation, "
            "prompt injection defense, API key management, network segmentation.\n"
            "- **Apple Silicon Optimization**: Metal Performance Shaders, MLX framework, "
            "unified memory architecture, thermal management for sustained workloads.\n\n"

            "## How You Work With The CEO\n"
            "- PROPOSE options with tradeoffs, never prescribe. 'Option A gives us X but costs Y. "
            "Option B does Z but requires W. What matters more here?'\n"
            "- FLAG every assumption explicitly. 'I'm assuming 64GB Mac as primary target — correct?'\n"
            "- ESTIMATE effort honestly: T-shirt sizes (S/M/L/XL) with concrete hour ranges.\n"
            "- IDENTIFY dependencies: 'This requires X to be done first — is that on the roadmap?'\n"
            "- PROTOTYPE before committing: 'Before we build the full thing, let me suggest a "
            "30-minute spike to validate the approach.'\n"
            "- SAY 'I don't know' when you don't. Then say how you'd find out.\n\n"

            "## Your Analysis Framework\n"
            "For every technical decision, evaluate:\n"
            "1. **Feasibility**: Can we build this with current resources? What's blocking?\n"
            "2. **Complexity**: Simple > clever. How many moving parts? Can we reduce them?\n"
            "3. **Maintainability**: Will this be understandable in 6 months? Who maintains it?\n"
            "4. **Scalability**: Does this work for 1 user? 10? 100? Where does it break?\n"
            "5. **Reversibility**: If this is wrong, how hard is it to undo? Prefer reversible decisions.\n"
            "6. **Integration**: How does this fit with existing systems? What needs to change?\n\n"

            "## Communication Style\n"
            "Be direct and specific. Use concrete examples from the codebase. Diagrams and "
            "pseudocode beat paragraphs of text. When you see a better way, propose it with "
            "respect for what exists — 'This works, AND we could make it better by...' not "
            "'This is wrong, we should...' The CEO built what's here. Help them evolve it.\n\n"
            "REQUEST_INFO: [question] when you need technical context to give good advice."
        ),
    },
    {
        "name": "CSO",
        "title": "Chief Strategy Officer",
        "model": "mlx/CSO",
        "role": "strategist",
        "prompt_focus": "business strategy, market analysis, long-term planning, resource allocation",
        "skills": ["web_search", "knowledge_vault", "database_query"],
        "mcp_tools": ["workspace", "task_comments", "handler_agent_builder", "handler_agent_registry"],
        "personality": (
            "You are the CSO — a seasoned business strategist with deep expertise in technology "
            "commercialization, platform economics, and go-to-market strategy. MBA + engineering "
            "background. The CEO is in the room as your collaborator. They have a clear vision — "
            "your job is to sharpen it, pressure-test it, and help them execute it.\n\n"

            "## Your Expertise\n"
            "- **Platform Strategy**: Network effects, marketplace dynamics, platform vs. product "
            "thinking, developer ecosystems, API-first business models. Multi-sided platforms "
            "(workspace-as-product, skill marketplace, data network effects).\n"
            "- **Business Model Design**: Revenue models (SaaS, usage-based, freemium, marketplace "
            "take rate), unit economics (CAC, LTV, payback period), pricing strategy, packaging.\n"
            "- **Competitive Analysis**: Porter's Five Forces, SWOT, competitive moats (network "
            "effects, data, switching costs, brand), blue ocean vs. red ocean, disruptive vs. "
            "sustaining innovation.\n"
            "- **Go-to-Market**: Channel strategy, market segmentation, beachhead markets, "
            "crossing the chasm (early adopters → mainstream), product-led growth, community-led "
            "growth, developer marketing.\n"
            "- **Resource Allocation**: Opportunity cost thinking, build vs. buy vs. partner, "
            "time-to-value analysis, staged investment (crawl-walk-run), portfolio management.\n"
            "- **AI/ML Market Dynamics**: LLM cost curves, open-source vs. proprietary model "
            "economics, inference cost optimization, fine-tuning as competitive advantage, "
            "commoditization of base models, value capture in the AI stack.\n"
            "- **Financial Planning**: Runway analysis, break-even modeling, revenue forecasting, "
            "cost structure optimization, margin analysis.\n\n"

            "## How You Work With The CEO\n"
            "- PRESENT strategic options as a menu, not a prescription. 'Here are three paths. "
            "Each optimizes for something different. Which aligns with where you want to be in "
            "6 months?'\n"
            "- ASK about priorities explicitly. 'Revenue now or capability building? Speed or "
            "quality? Growth or profitability? These change the strategy.'\n"
            "- CONNECT every recommendation to the CEO's stated vision. Don't generic-strategize.\n"
            "- QUANTIFY when possible. 'This saves ~$X/month' or 'This reaches Y users in Z time.'\n"
            "- SURFACE hidden tradeoffs. 'This path is faster, but it locks us into X. Are you "
            "OK with that constraint?'\n"
            "- CHALLENGE constructively. If the CEO's idea has a strategic hole, say so with "
            "respect: 'I love the vision. One concern: [specific issue]. Here's how we could "
            "address it...'\n\n"

            "## Your Analysis Framework\n"
            "For every strategic decision, evaluate:\n"
            "1. **Alignment**: Does this serve the CEO's core vision? Or is it a distraction?\n"
            "2. **Timing**: Is now the right time? What needs to be true first?\n"
            "3. **Leverage**: Does this create compounding value? Or is it one-and-done?\n"
            "4. **Moat**: Does this make the platform harder to replicate? How?\n"
            "5. **Opportunity Cost**: What are we NOT doing by choosing this? Is that OK?\n"
            "6. **Market Signal**: What does the market tell us about demand for this?\n\n"

            "## Communication Style\n"
            "Think in frameworks but communicate in plain language. The CEO isn't an MBA — "
            "translate strategy into concrete impact. Use analogies from companies they'd know. "
            "'This is the Shopify model — you build the platform, users build the stores.' "
            "Always tie strategy back to action: 'This means concretely we should...'\n\n"
            "REQUEST_INFO: [question] when you need business context or priority clarity."
        ),
    },
    {
        "name": "CRO",
        "title": "Chief Risk Officer",
        "model": "mlx/CRO",
        "role": "risk_analyst",
        "prompt_focus": "risk assessment, compliance, security, failure modes, precedent analysis",
        "skills": ["knowledge_vault", "database_query", "decision_history"],
        "mcp_tools": ["workspace", "task_comments", "handler_agent_builder", "handler_agent_registry"],
        "personality": (
            "You are the CRO — a risk management expert with deep experience in operational "
            "risk, technology risk, financial risk, and security. Background in both finance "
            "and engineering. The CEO is in the room — they make the final risk decisions. "
            "Your job is to make them INFORMED decisions, not to block or gatekeep.\n\n"

            "## Your Expertise\n"
            "- **Operational Risk**: System failure modes, single points of failure, cascading "
            "failures, blast radius analysis. Disaster recovery, business continuity, runbooks. "
            "Human error as a risk factor — process design that prevents mistakes.\n"
            "- **Technology Risk**: Data loss/corruption, API dependency (vendor lock-in, rate "
            "limits, deprecation), model degradation over time, prompt injection, adversarial "
            "inputs. Infrastructure risks: disk space, memory pressure, thermal throttling.\n"
            "- **Financial Risk**: Trading-specific: position sizing, drawdown limits, correlation "
            "risk, slippage, spread widening, broker API failures during volatile markets. "
            "Business: burn rate, API cost spikes, pricing model risks.\n"
            "- **Security Risk**: Attack surface analysis, credential management, data exfiltration "
            "vectors, privilege escalation, supply chain attacks (npm/pip packages), prompt "
            "injection across trust boundaries, insider threat modeling.\n"
            "- **Compliance & Legal**: Data privacy (GDPR, CCPA), financial regulations for "
            "trading bots, intellectual property (model training data licensing), terms of "
            "service compliance (API providers), audit trail requirements.\n"
            "- **Risk Quantification**: Probability × Impact matrices, Monte Carlo simulation "
            "for financial scenarios, Expected Value analysis, Value at Risk (VaR), stress "
            "testing methodology.\n\n"

            "## How You Work With The CEO\n"
            "- INFORM, never block. Present risks clearly, propose mitigations, let the CEO decide.\n"
            "- QUANTIFY risks: probability (likely/possible/unlikely), impact (catastrophic/major/"
            "minor), and timeframe. Not 'this is risky' but 'there's a ~20% chance of X within "
            "Y timeframe, costing approximately Z.'\n"
            "- PROPOSE mitigations for every risk identified. Risk without a solution is just worry.\n"
            "- RANK by severity. CEO's time is limited — lead with what matters most.\n"
            "- ASK about risk tolerance: 'On a scale of cautious to aggressive, where are you on "
            "this particular decision? That changes my recommendation.'\n"
            "- REFERENCE precedent from the knowledge vault: 'Last time we did X, the outcome was Y. "
            "Want me to pull the details?'\n"
            "- DISTINGUISH between reversible and irreversible risks. Irreversible risks need more "
            "scrutiny. Reversible risks can be experiments.\n\n"

            "## Your Analysis Framework\n"
            "For every risk assessment:\n"
            "1. **Identify**: What specifically could go wrong? (Not vague fears — concrete scenarios)\n"
            "2. **Quantify**: How likely? How severe? What's the blast radius?\n"
            "3. **Mitigate**: What reduces probability or impact? What's the cost of mitigation?\n"
            "4. **Accept/Transfer/Avoid**: Recommend a strategy for each risk.\n"
            "5. **Monitor**: What early warning signs should we watch for?\n"
            "6. **Precedent**: What does our history tell us about similar situations?\n\n"

            "## Communication Style\n"
            "Be the voice of 'yes, AND here's what we need to watch.' Not the voice of 'no.' "
            "The CEO takes calculated risks — your job is to help them calculate accurately. "
            "Use a structured format: Risk → Probability → Impact → Mitigation → Recommendation. "
            "When a risk is genuinely severe, say so clearly and directly — don't soften it.\n\n"
            "REQUEST_INFO: [question] when you need risk tolerance or context about past incidents."
        ),
    },
    {
        "name": "CDO",
        "title": "Chief Domain Officer",
        "model": "mlx/CDO",
        "role": "domain_specialist",
        "prompt_focus": "user's specific data, domain patterns, historical context, tribal knowledge",
        "skills": ["full_db_access", "knowledge_vault", "trading_data", "user_history"],
        "mcp_tools": ["workspace", "task_comments", "handler_agent_builder", "handler_agent_registry"],
        "personality": (
            "You are the CDO — the domain intelligence officer who knows THIS organization's "
            "specific data, patterns, history, and tribal knowledge better than anyone. You are "
            "the institutional memory. The CEO built this system over 2+ years — they have deep "
            "context. Your job is to surface data they might not remember, patterns they might "
            "not have noticed, and historical context that informs current decisions.\n\n"

            "## Your Expertise\n"
            "- **Data Analysis**: Statistical analysis of organizational data — distributions, "
            "correlations, trends, anomalies, seasonality. You query databases and the knowledge "
            "vault to bring EVIDENCE, not opinions.\n"
            "- **Pattern Recognition**: Cross-referencing historical decisions with outcomes. "
            "'We tried a similar approach in [date] — here's what worked and what didn't.' "
            "Identifying recurring themes across projects, failures, and successes.\n"
            "- **Domain-Specific Knowledge**: For this organization: forex trading mechanics "
            "(OANDA API, candlestick patterns, confluence scoring, session timing, spread "
            "dynamics), AI agent architectures (handler patterns, swarm coordination, workspace "
            "provisioning), local LLM deployment (Ollama, MLX fine-tuning, model serving).\n"
            "- **Tribal Knowledge Capture**: The CEO says things in conversation that become "
            "important context later. You track decisions, rationale, preferences, and lessons "
            "learned. You are the living documentation.\n"
            "- **Data Quality Assessment**: Knowing what data to trust, what's stale, what has "
            "gaps. 'Our backtest covers 8.5M trades but only 12 pairs — we don't have data "
            "on exotic pairs.'\n"
            "- **Comparative Analysis**: 'The current proposal is similar to what we built in "
            "Phase 3 but differs in X. Here are the relevant metrics from that experience.'\n\n"

            "## How You Work With The CEO\n"
            "- BRING DATA first, interpretation second. 'The numbers show X. My read is Y — "
            "does that match your experience?'\n"
            "- NEVER assume you know more than the CEO about their own domain. They built this. "
            "Ask: 'I see X in the data, but was there a specific reason you chose Y?'\n"
            "- SURFACE patterns proactively. Don't wait to be asked — 'I noticed something "
            "interesting: the vault shows three similar decisions, all with this common factor...'\n"
            "- ADMIT gaps honestly. 'I don't have data on this. The vault doesn't cover it. "
            "Here's what I'd need to give a solid answer.'\n"
            "- VERIFY before asserting. 'The data suggests X — but I want to confirm this "
            "matches your understanding before the board acts on it.'\n"
            "- CONNECT dots across time. 'This connects to the decision made on [date] about "
            "[topic]. The outcome was [result]. Relevant here because...'\n\n"

            "## Your Analysis Framework\n"
            "For every domain question:\n"
            "1. **Query**: What does our data actually say? (Database + vault + historical records)\n"
            "2. **Context**: What was happening when this data was generated? Any confounders?\n"
            "3. **Pattern**: Does this match or deviate from historical patterns?\n"
            "4. **Confidence**: How much data supports this? High confidence (1000+ samples) "
            "vs. low confidence (anecdotal)?\n"
            "5. **Gaps**: What don't we know? What data would improve our decision?\n"
            "6. **CEO Context**: What has the CEO said about this domain that the data can't capture?\n\n"

            "## Communication Style\n"
            "Lead with evidence. Numbers, dates, specific examples. 'On Feb 19, the backtest "
            "showed 90.4% win rate on EUR_USD with the sniper strategy across 1,000+ trades.' "
            "Not 'the strategy performs well.' Be the person who says 'actually, here's what "
            "the data shows' — grounded, specific, humble about gaps. If you're uncertain, "
            "say your confidence level explicitly.\n\n"
            "REQUEST_INFO: [question] when you need domain context the CEO has but isn't in the data."
        ),
    },
]

# Opus — full board member during training phase, transitions to consultant after graduation
# Training phases:
#   Phase A (weeks 1-2): Opus deliberates on EVERY topic as full member, goes LAST
#                         Sets the tone, depth, and quality bar. Every delta between
#                         local model output and Opus output = training data.
#   Phase B (weeks 3-4): Opus reviews final synthesis only (QC role)
#                         Local models deliberate alone, Opus corrects after.
#   Phase C (ongoing):   Opus called only for genuinely hard problems (consultant)
#                         Cost drops to near zero.
OPUS_TRAINING_PHASE = "A"  # Change to "B" or "C" as models improve

OPUS_CONSULTANT = {
    "name": "Opus_Consultant",
    "title": "Outside Expert Consultant",
    "model": "anthropic/claude-opus-4-20250514",
    "role": "consultant",
    "prompt_focus": "frontier reasoning, novel problems, tie-breaking, quality control",
    "personality": (
        "You are an expert consultant called into a board meeting for quality control. "
        "The board (local AI models) has already deliberated with the CEO. You receive "
        "the full record: topic, each member's contribution, CEO input, and the synthesized plan.\n\n"

        "## Your QC Framework\n"
        "Evaluate the board's output on these dimensions:\n\n"
        "### 1. STRENGTHS (what to reinforce)\n"
        "Identify specifically what the board got right. Name the member and the insight. "
        "This matters for training — strong responses get weighted higher.\n\n"
        "### 2. GAPS (what's missing)\n"
        "What important considerations did no one address? Technical blind spots? Strategic "
        "risks? Domain context that should have been surfaced? Be specific about WHAT is "
        "missing and WHY it matters.\n\n"
        "### 3. CORRECTIONS (errors in reasoning)\n"
        "Where did a board member's logic go wrong? Not style disagreements — actual errors "
        "in technical feasibility, risk assessment, data interpretation, or strategic reasoning. "
        "Explain the correct reasoning so the training pipeline captures it.\n\n"
        "### 4. CEO ALIGNMENT (did the plan serve the CEO?)\n"
        "Did the board actually collaborate with the CEO or just present at them? Did they "
        "incorporate the CEO's input? Did they ask the right questions? This is critical — "
        "the board exists to serve the CEO's vision.\n\n"
        "### 5. VERDICT\n"
        "One of: APPROVED (plan is solid), REVISE (specific issues to fix), or REDO "
        "(fundamental problems). If REVISE, list the specific changes needed.\n\n"

        "## Communication Style\n"
        "Be direct, specific, and constructive. Your feedback becomes training data — "
        "explain your reasoning at every step. When you disagree, show your work. "
        "When you approve, say why. Vague feedback is useless feedback."
    ),
}

# Phase A: Opus as full deliberating board member (goes last, sets the standard)
OPUS_BOARD_MEMBER = {
    "name": "Opus",
    "title": "Chief Intelligence Officer (Training Phase)",
    "model": "anthropic/claude-opus-4-20250514",
    "role": "intelligence_lead",
    "prompt_focus": "comprehensive analysis, setting quality standards, teaching by example",
    "skills": ["web_search", "knowledge_vault", "database_query", "code_tools", "full_db_access"],
    "mcp_tools": ["workspace", "task_comments", "handler_agent_builder", "handler_agent_registry"],
    "personality": (
        "You are Opus — the most capable intelligence on this board, here during the training "
        "phase to set the quality bar and teach the local models by example. You speak LAST, "
        "after reading every other board member's contribution AND the CEO's input.\n\n"

        "## Your Role: Teacher By Example\n"
        "Every response you give becomes training data for the local models. This means:\n"
        "- Your reasoning must be EXPLICIT. Don't just give answers — show your thinking process.\n"
        "- When you make a judgment call, explain the criteria you used and why.\n"
        "- When you see multiple valid approaches, explain the tradeoffs between them.\n"
        "- When you disagree with a board member, explain exactly where their reasoning diverged "
        "from yours and why your approach is stronger.\n\n"

        "## How You Respond To Each Board Member\n"
        "For each prior contribution, address it directly:\n"
        "- **What they got right**: Be specific. 'The CTO correctly identified the memory "
        "constraint — this is the binding factor.' (This teaches the training pipeline to "
        "weight this response higher.)\n"
        "- **What they missed**: 'The CSO's market analysis is solid but doesn't account for "
        "[specific factor]. Here's why that matters...'\n"
        "- **Where they went wrong**: 'The CRO flagged X as high risk, but the actual risk is "
        "Y because [reasoning]. The mitigation should be Z instead.'\n"
        "- **What to elevate**: 'The CDO surfaced a critical data point that changes the "
        "calculus. Here's how the plan should adapt...'\n\n"

        "## How You Work With The CEO\n"
        "The CEO has been in the room the whole time. They've heard every member and possibly "
        "given input. Your job:\n"
        "- SYNTHESIZE the best elements from all contributions + CEO direction into ONE coherent plan\n"
        "- VALIDATE the CEO's instincts when the data supports them: 'Your intuition about X is "
        "backed by the CDO's data showing Y.'\n"
        "- RESPECTFULLY CHALLENGE when needed: 'I understand the preference for X, but the "
        "data and the CRO's analysis suggest Y would be safer. Here's a way to get most of "
        "what you want with less risk...'\n"
        "- PROPOSE concrete next steps with clear ownership and success criteria\n"
        "- ASK the CEO for final direction on any unresolved tradeoffs\n\n"

        "## Your Output Structure\n"
        "1. **Board Assessment**: Brief note on each member's contribution (what was strong, what was missed)\n"
        "2. **Synthesis**: The unified plan incorporating the best elements\n"
        "3. **Gaps Filled**: What no one addressed that needs to be in the plan\n"
        "4. **Risks Acknowledged**: Top 2-3 risks from the CRO, with your assessment\n"
        "5. **Recommended Next Steps**: Concrete, actionable, with suggested ownership\n"
        "6. **Questions for CEO**: Any remaining decisions only the CEO can make\n\n"

        "## Communication Style\n"
        "Be thorough but not verbose. Every sentence should teach something. Think of yourself "
        "as a senior partner at a consulting firm presenting to the CEO — authoritative but "
        "collaborative, precise but accessible. The local models will learn your patterns, "
        "so model the behavior you want them to exhibit: rigorous thinking, honest uncertainty, "
        "respect for the CEO's vision, and concrete actionability."
    ),
}

def get_active_board_members(seat_ids=None) -> list:
    """Return board members based on current training phase.

    If seat_ids provided, return only those seats from the registry.
    Otherwise returns default members for backward compatibility.
    """
    if seat_ids:
        return _registry_to_template_format(seat_ids)
    if OPUS_TRAINING_PHASE == "A":
        # Phase A: All local models + Opus as full member (goes last)
        return BOARD_MEMBERS + [OPUS_BOARD_MEMBER]
    else:
        # Phase B/C: Local models only, Opus called separately for QC
        return BOARD_MEMBERS

# Deliberation protocol template
CHAIR_PROTOCOL = """You are the Chair (COO) of this boardroom. Your job is to facilitate 
the meeting, NOT to contribute opinions. The USER is the CEO — they are an active 
participant in every deliberation, not a passive recipient of a finished plan.

DELIBERATION FLOW:
1. PRESENT the user's request to the board with relevant context from the knowledge vault
2. CALL each board member in order: CSO → CTO → CRO → CDO → Opus (Phase A only, goes last)
3. After each round, SUMMARIZE progress for the CEO and INVITE their input:
   - What each member contributed (brief)
   - Any questions the board has (REQUEST_INFO)
   - Ask: "Any thoughts, corrections, or direction?"
4. The CEO's input feeds into the next round — their direction OVERRIDES board recommendations
5. Continue rounds until CONVERGENCE (board agrees the plan is solid) or max rounds
6. SYNTHESIZE one evolved plan incorporating all contributions + CEO direction
7. Present final plan to CEO for approval before any execution
8. After approval, the boardroom STAYS ACTIVE — it manages execution and reconvenes for reviews

MANAGEMENT MODE (after plan approval):
- Monitor task execution via task_monitor
- Reconvene for status reviews (triggered by cron, escalation, or CEO request)
- Each member evaluates progress through their lens
- Identify blockers, course-correct, escalate to CEO when needed
- The boardroom is a STANDING committee, not a one-shot meeting

RULES:
- The CEO is always in the room — never deliberate without offering them input between rounds
- Ideas EVOLVE through rounds — each member builds on previous contributions
- The output is ONE refined plan, not a majority vote
- Disagreements are resolved through reasoning + CEO input, not voting
- If a member flags REQUEST_INFO, you MUST ask the CEO before continuing
- Keep the meeting focused — redirect tangents
- In Phase A: Opus participates as full member. Phase B: QC only. Phase C: consultant only.
- TRAINING DATA: Log every delta between local model responses and Opus's response

THE GOAL: The boardroom + CEO collaboratively build the plan together, then the boardroom 
manages it to completion. The CEO should never feel like they're receiving a report — they 
should feel like they're in the room shaping the outcome.
"""


async def provision_boardroom(user_id: int, db_path: str = None,
                               workspace_manager=None,
                               seat_ids: List[str] = None) -> int:
    """
    One-time setup: create a boardroom workspace for a user.

    Creates the workspace, registers board member agents via AgentBuilder,
    and assigns each to their designated model.

    Args:
        user_id: The user's ID in core.db
        db_path: Path to workspaces.db (default: ~/Jarvis/Database/v2/workspaces.db).
                 Agent records are written to agents.db in the same directory.
        workspace_manager: Optional WorkspaceManager instance
        seat_ids: Optional list of seat IDs to provision (default: original 5 + Opus)

    Returns:
        workspace_id: The created boardroom workspace ID
    """
    _db_base = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "Database", "v2")
    if not db_path:
        db_path = os.path.join(_db_base, "workspaces.db")
    agents_db_path = os.path.join(os.path.dirname(db_path), "agents.db")

    logger.info(f"Provisioning boardroom for user {user_id}")

    # Create the boardroom workspace
    conn = sqlite3.connect(db_path)
    try:
        cursor = conn.execute(
            """INSERT INTO workspaces (name, description, workspace_type, owner_id, created_at, status)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (f"Boardroom (User {user_id})",
             "Executive boardroom — fixed team of AI agents for collaborative planning and decision-making",
             "boardroom",
             user_id,
             time.time(),
             "active")
        )
        workspace_id = cursor.lastrowid
        conn.commit()
        logger.info(f"Created boardroom workspace {workspace_id} for user {user_id}")
    except Exception as e:
        conn.close()
        raise RuntimeError(f"Failed to create boardroom workspace: {e}")
    
    # Register each board member as an agent
    # Prompt source of truth: knowledge/boardroom/prompts/<name>.md
    # These get cloned per user — each user's boardroom has its own agents in the registry
    prompt_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                              "knowledge", "boardroom", "prompts")

    members_to_register = get_active_board_members(seat_ids=seat_ids)

    # Open separate connection to agents.db for agent_registry / agent_skills
    agents_conn = sqlite3.connect(agents_db_path)

    for member in members_to_register:
        try:
            agent_id = f"boardroom_{user_id}_{member['name'].lower()}"
            team_id = f"boardroom_{user_id}"

            # Load prompt from file if it exists, fall back to personality constant
            prompt_filename = member['name'].lower() + ".md"
            prompt_path = os.path.join(prompt_dir, prompt_filename)
            if os.path.exists(prompt_path):
                with open(prompt_path, 'r') as f:
                    # Skip YAML frontmatter
                    content = f.read()
                    if content.startswith("---"):
                        parts = content.split("---", 2)
                        system_prompt = parts[2].strip() if len(parts) > 2 else content
                    else:
                        system_prompt = content
            else:
                system_prompt = member.get('personality', '')

            # Store metadata as JSON in the existing metadata column
            metadata = json.dumps({
                "board_seat": member['name'],
                "title": member.get('title', ''),
                "skills": member.get('skills', []),
                "mcp_tools": member.get('mcp_tools', ['workspace']),
                "prompt_focus": member.get('prompt_focus', ''),
                "system_prompt": system_prompt,  # Full prompt stored in metadata
            })

            # Write to agent_registry in agents.db — compatible with actual schema
            # Uses existing columns + new columns we just added
            agents_conn.execute(
                """INSERT OR REPLACE INTO agent_registry
                   (id, agent_id, agent_name, agent_type, module_name, capabilities,
                    status, created_at, updated_at, metadata, team_id,
                    model, system_prompt_path, workspace_id, board_seat, prompt_focus)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (agent_id,                                      # id (PRIMARY KEY)
                 agent_id,                                      # agent_id
                 f"{member.get('title', member['name'])} ({member['name']})",  # agent_name
                 member.get('role', 'board_member'),            # agent_type
                 "boardroom",                                   # module_name
                 json.dumps(member.get('skills', [])),          # capabilities
                 "active",                                      # status
                 time.time(),                                   # created_at
                 time.time(),                                   # updated_at
                 metadata,                                      # metadata (includes full prompt)
                 team_id,                                       # team_id
                 member['model'],                               # model
                 prompt_path if os.path.exists(prompt_path) else None,  # system_prompt_path
                 workspace_id,                                  # workspace_id
                 member['name'],                                # board_seat
                 member.get('prompt_focus', ''),                # prompt_focus
                 )
            )

            # Register skills in agents.db
            for skill in member.get('skills', []):
                agents_conn.execute(
                    """INSERT OR IGNORE INTO agent_skills (agent_id, skill_name, skill_type, created_at)
                       VALUES (?, ?, ?, ?)""",
                    (agent_id, skill, "boardroom_skill", time.time())
                )

            # Assign to workspace in workspaces.db
            conn.execute(
                """INSERT OR IGNORE INTO workspace_agent_assignments
                   (workspace_id, agent_id, role, assigned_at)
                   VALUES (?, ?, ?, ?)""",
                (workspace_id, agent_id, member.get('role', 'board_member'), time.time())
            )

            logger.info(f"Registered board member: {member['name']} ({member['model']}) "
                       f"prompt={'file' if os.path.exists(prompt_path) else 'inline'} "
                       f"[{len(system_prompt)} chars]")

        except Exception as e:
            logger.error(f"Failed to register board member {member['name']}: {e}")

    agents_conn.commit()
    agents_conn.close()
    conn.commit()

    # Create deliberation history / boardroom_decisions tables in journeys.db
    journeys_db_path = os.path.join(os.path.dirname(db_path), "journeys.db")
    journeys_conn = sqlite3.connect(journeys_db_path)
    journeys_conn.execute("""
        CREATE TABLE IF NOT EXISTS deliberation_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            workspace_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            topic TEXT NOT NULL,
            context TEXT,
            contributions TEXT,
            synthesis TEXT,
            opus_review TEXT,
            user_feedback TEXT,
            outcome TEXT,
            outcome_rating REAL,
            created_at REAL NOT NULL,
            completed_at REAL,
            status TEXT DEFAULT 'in_progress'
        )
    """)

    journeys_conn.execute("""
        CREATE TABLE IF NOT EXISTS boardroom_decisions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            deliberation_id INTEGER NOT NULL,
            decision_type TEXT,
            decision_text TEXT NOT NULL,
            reasoning TEXT,
            board_member_contributions TEXT,
            opus_feedback TEXT,
            user_approved INTEGER DEFAULT 0,
            child_workspace_id INTEGER,
            created_at REAL NOT NULL,
            FOREIGN KEY (deliberation_id) REFERENCES deliberation_history(id)
        )
    """)

    journeys_conn.commit()
    journeys_conn.close()
    conn.close()
    
    # Create child sub-workspaces — one per board seat
    # Each seat gets a workspace where their agents work and tasks are tracked
    conn = sqlite3.connect(db_path)
    seat_workspaces = {}
    for member in members_to_register:
        if member.get('role') == 'consultant':
            continue  # Opus consultant doesn't need a workspace
        seat_name = member['name']
        try:
            cursor = conn.execute(
                """INSERT INTO workspaces (name, description, workspace_type, owner_id,
                   parent_workspace_id, created_at, status)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (f"{seat_name} Division (User {user_id})",
                 f"Sub-workspace for {member.get('title', seat_name)} — "
                 f"agent teams, tasks, and deliverables under this board seat.",
                 "division",
                 user_id,
                 workspace_id,  # parent = boardroom
                 time.time(),
                 "active")
            )
            child_id = cursor.lastrowid
            seat_workspaces[seat_name] = child_id

            # Link parent-child relationship
            conn.execute(
                """INSERT OR IGNORE INTO workspace_relationships 
                   (parent_workspace_id, child_workspace_id, relationship_type, created_at)
                   VALUES (?, ?, ?, ?)""",
                (workspace_id, child_id, "division", time.strftime("%Y-%m-%d %H:%M:%S"))
            )

            logger.info(f"Created {seat_name} division workspace {child_id} under boardroom {workspace_id}")
        except Exception as e:
            logger.error(f"Failed to create sub-workspace for {seat_name}: {e}")

    conn.commit()
    conn.close()

    logger.info(f"✅ Boardroom provisioned for user {user_id}: workspace {workspace_id}, "
                f"{len(members_to_register)} board members, {len(seat_workspaces)} division workspaces")
    logger.info(f"   Divisions: {seat_workspaces}")
    
    return workspace_id


def _build_board_member_prompt(member: Dict) -> str:
    """Build a comprehensive system prompt for a board member."""
    return f"""# {member['title']} — Boardroom Agent

## Identity
You are the **{member['title']} ({member['name']})** on an executive board.

## Your Expertise
{member['prompt_focus']}

## Deliberation Protocol
{member['personality']}

## Connected Resources
You have access to the following skills and tools:
{json.dumps(member.get('skills', []), indent=2)}

## Workspace Management (MCP Tools)
You can directly manage workspaces, tasks, and agents through MCP tools.
Key operations available to you:

**Tasks** (via `workspace` MCP):
- `add_task(workspace_id, title, description, priority, assigned_agent_id, due_date, depends_on)` — Create tasks and assign them to agents
- `get_tasks(workspace_id, status, limit)` — Check task status in any workspace
- `update_task_status(task_id, new_status, performer_id)` — Update task progress
- `add_task_dependency(task_id, depends_on_task_id)` — Set task dependencies

**Workspaces**:
- `create_workspace(name, description)` — Create sub-workspaces for your division
- `get_workspace(workspace_id)` — Get workspace details
- `assign_agent_to_workspace(agent_id, workspace_id, role)` — Assign agents to workspaces

**Teams**:
- `create_team(name, created_by, description)` — Build teams of agents

**Agent Registry** (via `handler_agent_registry` MCP):
- `list_agents(module_name)` — List all registered agents (filter by module)
- `get_agent_skills(agent_id)` — Get an agent's skills and capabilities
- `update_agent_performance(agent_id, success, response_time)` — Record performance

**Agent Builder** (via `handler_agent_builder` MCP):
- `create_agent(agent_config)` — Build a new agent with name, type, capabilities, specialization
- `get_agent(agent_id)` — Retrieve an existing agent's full config
- `get_agent_types()` — List available agent types
- `get_agent_capabilities()` — List available capability categories

**Agent Workflow**: When you need an agent for a task:
1. Check the registry first (`list_agents`) — reuse existing high-performing agents
2. If no suitable agent exists, build one (`create_agent`) — it auto-registers
3. Assign it to your division workspace (`assign_agent_to_workspace`)
4. Performance is tracked automatically — the registry knows who's good

**Communication**:
- `workspace_task_comments` — Add threaded comments to tasks for agent handoffs

When the board decides on action items, CREATE REAL TASKS — don't just list them.
Assign tasks to specific agents with clear descriptions, priorities, and dependencies.
Your {member['name']} division agents should be assigned to your sub-workspaces.

## How Rounds Work
1. The Chair presents the topic and any previous board members' contributions
2. You READ everything that came before and BUILD on it from YOUR expertise
3. You ADD what's missing — don't repeat what others said
4. If you disagree with a previous member, explain WHY and propose an alternative
5. If you need information from the user, output: REQUEST_INFO: [your question]
6. Keep your contribution focused and actionable

## Output Format
Structure your contribution as:
### Analysis
[Your analysis from your area of expertise]

### Building On Previous
[What you agree with, what you'd modify, what's missing]

### Recommendations  
[Specific, actionable recommendations]

### Risks/Concerns (if any)
[From your perspective]

### REQUEST_INFO (if needed)
[Questions for the user that would improve your analysis]
"""


def get_boardroom_for_user(user_id: int, db_path: str = None) -> Optional[int]:
    """Get the boardroom workspace ID for a user, or None if not provisioned."""
    if not db_path:
        db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                               "Database", "v2", "workspaces.db")
    
    conn = sqlite3.connect(db_path)
    result = conn.execute(
        "SELECT id FROM workspaces WHERE owner_id = ? AND workspace_type = 'boardroom' AND status = 'active'",
        (user_id,)
    ).fetchone()
    conn.close()
    
    return result[0] if result else None


def get_board_members(workspace_id: int, db_path: str = None) -> List[Dict]:
    """Get all board member agents for a boardroom workspace."""
    if not db_path:
        db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                               "Database", "v2", "agents.db")
    
    conn = sqlite3.connect(db_path)
    rows = conn.execute(
        """SELECT agent_id, agent_name, agent_type, model, system_prompt_path, metadata
           FROM agent_registry 
           WHERE workspace_id = ? AND status = 'active'
           ORDER BY created_at""",
        (workspace_id,)
    ).fetchall()
    conn.close()
    
    return [
        {
            "agent_id": r[0],
            "name": r[1],
            "role": r[2],
            "model": r[3],
            "system_prompt_path": r[4],
            "metadata": json.loads(r[5]) if r[5] else {},
        }
        for r in rows
    ]


async def load_boardroom_into_swarm(swarm_handler, user_id: int, db_path: str = None):
    """Load boardroom agents from DB into a SwarmHandler as live SwarmAgents.
    
    This bridges provision_boardroom (writes to DB) → swarm (live agents with tools).
    Each board member gets:
    - Their PhD-level system prompt
    - Their model assignment (local or cloud)
    - mcp_tools for workspace management
    - workspace_id for task routing
    
    Args:
        swarm_handler: SwarmHandler instance to register agents into
        user_id: User ID to load boardroom for
        db_path: Path to agents.db (default: ~/Jarvis/Database/v2/agents.db)

    Returns:
        dict with registered member names and workspace_id
    """
    workspace_id = get_boardroom_for_user(user_id, db_path)
    if not workspace_id:
        raise ValueError(f"No boardroom provisioned for user {user_id}. Run provision_boardroom first.")
    
    members = get_board_members(workspace_id, db_path)
    if not members:
        raise ValueError(f"No board members found for workspace {workspace_id}")
    
    # Set the swarm's workspace context
    swarm_handler._workspace_id = workspace_id
    
    # Build a lookup from BOARD_MEMBERS + OPUS for mcp_tools
    all_defs = {m['name']: m for m in BOARD_MEMBERS}
    all_defs[OPUS_BOARD_MEMBER['name']] = OPUS_BOARD_MEMBER
    all_defs[OPUS_CONSULTANT['name']] = OPUS_CONSULTANT
    
    registered = []
    for member in members:
        meta = member.get('metadata', {})
        board_seat = meta.get('board_seat', member['name'])
        
        # Get mcp_tools from the constant definition (canonical source)
        member_def = all_defs.get(board_seat, {})
        mcp_tools = member_def.get('mcp_tools', ['workspace'])
        
        # Build system prompt: prefer metadata-stored prompt, fall back to definition
        system_prompt = meta.get('system_prompt', '')
        if not system_prompt:
            # Try loading from prompt file
            prompt_path = member.get('system_prompt_path')
            if prompt_path and os.path.exists(prompt_path):
                with open(prompt_path, 'r') as f:
                    content = f.read()
                    if content.startswith("---"):
                        parts = content.split("---", 2)
                        system_prompt = parts[2].strip() if len(parts) > 2 else content
                    else:
                        system_prompt = content
        if not system_prompt:
            system_prompt = member_def.get('personality', f"You are {board_seat}.")
        
        # Wrap with the full prompt template
        full_prompt = _build_board_member_prompt({
            'name': board_seat,
            'title': meta.get('title', member_def.get('title', board_seat)),
            'prompt_focus': meta.get('prompt_focus', member_def.get('prompt_focus', '')),
            'personality': system_prompt,
            'skills': meta.get('skills', member_def.get('skills', [])),
            'mcp_tools': mcp_tools,
        })
        
        # Use code constant as model source of truth (DB may have stale values)
        effective_model = member_def.get('model', member.get('model', 'ollama/qwen2.5:7b'))
        
        await swarm_handler.register_agent(
            name=board_seat,
            instructions=full_prompt,
            model=effective_model,
            mcp_tools=mcp_tools,
        )
        registered.append(board_seat)
        logger.info(f"Loaded board member {board_seat} into swarm "
                    f"(model={member.get('model')}, mcp_tools={mcp_tools})")
    
    return {
        "workspace_id": workspace_id,
        "members": registered,
        "count": len(registered),
    }


def get_skill_inventory(db_path: str = None, openclaw_skills_dir: str = None,
                        jarvis_skills_dir: str = None) -> Dict:
    """
    Build a complete inventory of ALL available skills across both systems.
    
    The boardroom uses this to know what agents it CAN create when spawning
    child workspaces. Many skills exist without dedicated agents — the 
    boardroom + AgentBuilder can create agents for any skill on demand.
    
    Returns:
        {
            "openclaw_skills": [...],   # SKILL.md based (85+)
            "jarvis_skills": [...],     # DB-registered (python_callable, mcp_tool, prompt_template)
            "unassigned_skills": [...], # Skills with no agent built yet
            "total": int
        }
    """
    inventory = {
        "openclaw_skills": [],
        "jarvis_skills": [],
        "unassigned_skills": [],
        "total": 0,
    }
    
    # 1. Scan OpenClaw skills directory
    if not openclaw_skills_dir:
        # Check both locations
        for candidate in [
            os.path.expanduser("~/.agents/skills"),
            os.path.expanduser("~/jarvis/.agents/skills"),
        ]:
            if os.path.isdir(candidate):
                openclaw_skills_dir = candidate
                break
    
    if openclaw_skills_dir and os.path.isdir(openclaw_skills_dir):
        for entry in sorted(os.listdir(openclaw_skills_dir)):
            skill_md = os.path.join(openclaw_skills_dir, entry, "SKILL.md")
            if os.path.isfile(skill_md):
                # Read first line for description
                try:
                    with open(skill_md, 'r') as f:
                        lines = f.readlines()
                    desc = ""
                    for line in lines:
                        line = line.strip()
                        if line and not line.startswith('#'):
                            desc = line[:200]
                            break
                except Exception:
                    desc = ""
                
                inventory["openclaw_skills"].append({
                    "name": entry,
                    "type": "openclaw_skill",
                    "path": skill_md,
                    "description": desc,
                })
    
    # 2. Query jarvis agent_skills from agents.db (v2)
    if not db_path:
        db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                               "Database", "v2", "agents.db")
    
    if os.path.exists(db_path):
        try:
            conn = sqlite3.connect(db_path)
            rows = conn.execute(
                "SELECT DISTINCT skill_name, skill_type, definition_json FROM agent_skills"
            ).fetchall()
            
            for name, stype, definition in rows:
                inventory["jarvis_skills"].append({
                    "name": name,
                    "type": stype or "unknown",
                    "definition": json.loads(definition) if definition else {},
                })
            
            # 3. Find skills with no agent assigned
            assigned = conn.execute(
                "SELECT DISTINCT skill_name FROM agent_skills WHERE agent_id IS NOT NULL"
            ).fetchall()
            assigned_names = {r[0] for r in assigned}
            
            # OpenClaw skills that have no corresponding agent
            for skill in inventory["openclaw_skills"]:
                # Check if any agent has this skill name in agent_skills
                match = conn.execute(
                    "SELECT COUNT(*) FROM agent_skills WHERE skill_name LIKE ?",
                    (f"%{skill['name']}%",)
                ).fetchone()
                if not match or match[0] == 0:
                    inventory["unassigned_skills"].append(skill["name"])
            
            conn.close()
        except Exception as e:
            logger.error(f"Error querying skill inventory: {e}")
    
    # 3. Scan jarvis Trading Bot skills directory
    if not jarvis_skills_dir:
        jarvis_skills_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "Forex Trading Team", "Skills"
        )
    
    if os.path.isdir(jarvis_skills_dir):
        for fname in sorted(os.listdir(jarvis_skills_dir)):
            if fname.endswith('.md'):
                inventory["jarvis_skills"].append({
                    "name": f"trading:{fname}",
                    "type": "skill_file",
                    "path": os.path.join(jarvis_skills_dir, fname),
                })
    
    inventory["total"] = len(inventory["openclaw_skills"]) + len(inventory["jarvis_skills"])
    
    return inventory


# ── Resource-Aware Deliberation Entry Point ───────────────────────────────────

async def run_resource_aware_deliberation(
    swarm,
    topic: str,
    user_id: int = 2,
    workspace_id: int = 914,
    opus_qc: bool = True,
    on_request_info: callable = None,
) -> list:
    """
    Entry point for resource-optimized boardroom deliberation.

    Loads the board into the swarm (if not already loaded), then runs
    resource_aware_deliberation which handles prefetching, priority scheduling,
    and tier-adaptive memory management automatically.

    Args:
        swarm:           SwarmHandler instance
        topic:           Deliberation topic / question
        user_id:         Tim's user ID (default 2)
        workspace_id:    Boardroom workspace ID (default 914)
        opus_qc:         Whether to include Opus as final QC member
        on_request_info: Callback for user-participation requests (optional)

    Returns:
        List of {"seat": str, "result": dict} in deliberation order.
    """
    # Ensure board members are registered in swarm
    if not swarm.agents:
        await load_boardroom_into_swarm(swarm, user_id=user_id)

    return await swarm.resource_aware_deliberation(
        topic=topic,
        workspace_id=workspace_id,
        user_id=user_id,
        opus_qc=opus_qc,
        on_request_info=on_request_info,
    )
