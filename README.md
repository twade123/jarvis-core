# Jarvis Core — a self-hosted personal AI operating system

Jarvis is a daemonized always-on AI platform that runs on a single Mac Studio. It's not a chatbot — it's a multi-agent orchestration layer that takes voice or chat input, routes it through a 5-layer reasoning pipeline, dispatches across local MLX models / Anthropic / 37 MCP servers, and streams results back through a vanilla-JS web UI.

The system hosts live production workloads on top of itself — most notably the [Forex Trading Team](https://github.com/twade123/forex-trading-team) — and uses every interaction to compound learnings into a shared FTS-indexed knowledge vault that every agent reads at task start.

It's been running daily since early 2025. This repo is the orchestration core.

---

## The 5 things worth looking at

### 1. "One Brain" — unified skill substrate across 5 surfaces
Every skill lives once at `.agents/skills/{name}/SKILL.md`. Five different agent surfaces read from the same source: Claude Code, OpenClaw (local-Claude-Code-style agent), Trevor's swarm, sub-agents, and the knowledge vault. Edit a skill once, every system picks it up. 296 skill-agents auto-register into a single registry indexed by capability. See `.agents/skills/` + `Handler/handler_agent_registry.py`.

### 2. BoardRoom — 17-seat dynamic deliberation on 6 shared MLX servers
`BoardRoom` is Trevor's strategic deliberation subsystem. Not a separate product — it's the escalation path when the layered router decides a request is genuinely strategic (multi-domain decision, architectural tradeoff, "3% circuit-breaker question"). 17 C-level seats (CSO, CTO, CRO, CDO, CEO, COO, CMO, CFO, CCO, CHRO, CISO, CXO, VPE, CDS, GC, CPO, CRvO) map to **6 shared MLX servers** to fit in ~28 GB peak RAM on consumer hardware. Sequential role-conditioned deliberation with a bidirectional `REQUESTING USER FEEDBACK:` protocol. See `Jarvis_Agent_SDK/boardroom_connector.py`, `Handler/boardroom_template.py`, `Handler/seat_registry.py`, `Handler/meeting_broker.py`, `Handler/model_server_manager.py`.

### 3. Layered scoring router (5 layers, configurable weights)
Trevor doesn't pick a handler with a single classifier call. The router runs five layers sequentially, each with its own scoring mechanism, and weights re-balance based on request complexity:

| Layer | Mechanism | Source |
|---|---|---|
| 1. Pattern match | 5,555+ rows in `trevor_database.db:pattern_data` + 99.8%-accuracy intent model (42 MB) | `Core/trevor_core.py` |
| 2. Executable action | spaCy vector similarity over `handler_analysis.patterns` JSON (`"python"` + `"applescript"` actions) | `Handler/handler_analyzer*.py` |
| 3. Docstring semantics | 384 docstring entries + 126 semantic edges traversed cross-handler | `docstrings.db` (schema only in repo) |
| 4. Capability search | `find_agents_by_capability` over registry | `Handler/handler_agent_registry.py:746` |
| 5. LLM fallback | Direct dispatch or BoardRoom escalation | `Jarvis_Agent_SDK/jarvis_orchestrator.py` |

Simple requests favor pattern match; complex requests favor docstring semantics — weights flip automatically per the layered processing config. No code change to reorder layers.

### 4. Multi-tenant FastAPI gateway in front of a single MLX 35B
One Qwen3.5-35B-A3B-4bit model serves all tenants — Trevor, OpenClaw, Claude Code, BoardRoom, sub-agents, the trading team. A FastAPI gateway in front of MLX handles priority queueing (`trading=0, background=10, openclaw=3, claude_code=4, boardroom=5`) and runs a pinned-prompt warmer that re-warms canonical prompts every 180s to keep KV cache hot. This is how 17 deliberation seats + 6 active workspaces share one model without trampling each other. See `scripts/mlx_servers.sh`, `scripts/mlx_lm_server_lenient.py`, `scripts/mlx_vlm_server_with_tools.py`.

### 5. The Vault — FTS-indexed write-after-action shared memory
Every agent in the system — Claude Code, BoardRoom seats, trading sub-agents (validator/scout/guardian), Trevor itself, OpenClaw via a bridge — writes typed entries (`discovery | correction | failure | improvement | note`) after completing work, and reads relevant prior work before starting any task. FTS5 index over markdown files. Auto-decomposition of large `learnings.md` files into per-entry files for searchability. Per-agent + collective + boardroom-specific sub-corpora. This is how heterogeneous agents compound learnings without monolithic retraining. See `knowledge/` (the actual vault is included in this repo, ~28 MB of real entries), plus `knowledge/vault_writer.py` / `vault_cli.py`.

---

## System diagram

```
                            ┌──────────────────────────┐
                            │   trevor_desktop.html    │  ◄── vanilla JS, dark theme
                            │   (browser, port 8766)   │      single global state `S`
                            └────────────┬─────────────┘      SSE event stream
                                         │
                            ┌────────────▼─────────────┐
                            │      serve_ui.py         │  ◄── Flask + SSE
                            │  (lazy-loads orchestrator│      6,139 LOC
                            │   + boardroom + agg)     │
                            └────────────┬─────────────┘
                                         │
                            ┌────────────▼─────────────┐
                            │     trevor_core.py       │  ◄── intent classification
                            │   (the actual "brain")   │      voice pipeline (Whisper)
                            │       6,310 LOC          │      complexity scoring
                            └────────────┬─────────────┘
                                         │
                       ┌─────────────────┴─────────────────┐
                       │     jarvis_orchestrator.py        │  ◄── 5-layer router
                       │    (9,038 LOC, dispatch hub)      │
                       └─┬──────────┬──────────┬──────────┬┘
                         │          │          │          │
                  ┌──────▼──┐ ┌─────▼────┐ ┌───▼────┐ ┌───▼──────┐
                  │ Handler │ │ MCP Srvr │ │ Sub-   │ │ BoardRoom│
                  │ swarm   │ │ Launcher │ │ agents │ │ (17 seats│
                  │ (37     │ │ (28+9    │ │ (296   │ │  on 6    │
                  │  MCPs)  │ │  servers)│ │  skills│ │  servers)│
                  └─────────┘ └──────────┘ └────────┘ └──────────┘
                                         │
                            ┌────────────▼─────────────┐
                            │     MLX Gateway          │  ◄── FastAPI
                            │   (priority queue +      │      single Qwen 35B
                            │    pinned warmer)        │      multi-tenant
                            └──────────────────────────┘

                            ┌──────────────────────────┐
                            │     knowledge/ (vault)   │  ◄── FTS5 over markdown
                            │   read-before / write-   │      every agent contributes
                            │   after every task       │      shared memory
                            └──────────────────────────┘
```

---

## What's where

| Path | What |
|---|---|
| `Core/trevor_core.py` | The brain. Intent classification (99.8% acc model), voice pipeline, complexity analysis. |
| `Jarvis_Agent_SDK/jarvis_orchestrator.py` | The 5-layer router + dispatch hub. |
| `Jarvis_Agent_SDK/boardroom_connector.py` | BoardRoom entry point (and a chunky circular-import shim; would refactor in v2). |
| `Jarvis_Agent_SDK/database_directory.py` | Singleton DB access pattern — every DB connection in the system goes through here (WAL mode, 30s busy timeout). |
| `Handler/handler_swarm.py` | Swarm orchestration handler. |
| `Handler/handler_agent_builder.py` + `handler_agent_registry.py` | Dynamic agent generation + registry. |
| `Handler/boardroom_template.py` + `seat_registry.py` + `model_server_manager.py` + `meeting_broker.py` | BoardRoom internals. |
| `serve_ui.py` + `trevor_desktop.html` + `launch_trevor_desktop.sh` | The web UI (Flask + SSE + vanilla JS). |
| `scripts/mlx_*.sh\|py` | MLX serving stack (the multi-tenant gateway). |
| `knowledge/` | The full knowledge vault, scrubbed. The compounding memory. |
| `.agents/skills/` | 160 skill definitions (the "One Brain" source). |
| `Prompts/boardroom/` | BoardRoom system prompts (CTO, CSO, etc. seat conditioning). |
| `Prompts/trevor_core/` | Trevor's own system prompts. |
| `Prompts/mcp/` | MCP server prompts (terminal guidelines, code exploration, etc.). |
| `CLAUDE.md` | Project-level Claude Code instructions — kept here because it's a load-bearing artifact of the daily workflow. |

---

## The UI

`trevor_desktop.html` is a 234 KB single-page vanilla JS app — no React, no build step. Auto-logs in on localhost. Connects to `serve_ui.py` (Flask, port 8766) via Server-Sent Events.

**Global state:** single object `S = { token, user, threads, workspaces, boardroomSession, ... }`, persisted to localStorage.

**SSE event types:** `stream_token`, `boardroom_update`, `conversation_list`, `workspace_list`, `agent_activity`.

**Views:**
- Conversation threads (left rail)
- Workspace dashboards (forex trading, marketing team, etc.) — each workspace is its own pluggable surface
- BoardRoom live session view (17 seat icons, current speaker highlighted, deliberation transcript)
- Meeting templates picker (pre-built rosters: "Architecture Decision", "Strategic Pivot", etc.)

**Style:** Dark theme via CSS variables (`--bg: #0d1117`, `--surface: #161b22`, `--accent: #58a6ff`, monospace `--mono: 'SFMono-Regular', Consolas`).

**Helpers (not raw fetch):** `post()` / `get()` wrappers in the HTML handle auth tokens and JSON serialization.

---

## How the agents reason

A typical request flows like this:

1. **Input** lands at `serve_ui.py` (voice via Whisper or chat).
2. **Trevor Core** classifies intent against the 5,555-pattern model. If high-confidence + simple → direct handler. Otherwise → orchestrator.
3. **Orchestrator** runs the layered router:
   - Pattern → spaCy vectors → docstring semantics → capability search → LLM fallback
   - Each layer scores candidate handlers/agents; weights re-balance by complexity
4. **Dispatch** to the chosen handler. If the handler doesn't exist for this capability, `handler_agent_builder.find_or_build_agent()` registry-checks first, then falls back to LLM-generating a new agent (saved to the vault + registered in the DB).
5. **Optional escalation to BoardRoom** for strategic requests. Meeting template picks the seat roster. Each seat reads the prior seat's contribution + the vault context for its role, then contributes its deliberation. A synthesis pass produces the final answer + writes the decision to `knowledge/boardroom/decisions/`.
6. **Tool execution** via the 16 built-in Anthropic SDK tools, 28 handler MCPs, or 9 standalone MCPs (Gmail, GHL, Healthie [client-specific, removed from this repo], Canva, Meta Ads, etc.).
7. **Result** streams back through SSE to the UI.
8. **Vault write** at task completion — every meaningful action gets a typed entry. Auto-decomposition kicks in if a learnings file gets too long.

---

## Quick start

> This repo is the orchestration platform. It expects to run on macOS (Apple Silicon for MLX serving), and depends on environmental config (Anthropic key for the boardroom seats that use Opus/Sonnet, optional OANDA credentials if you run the trading workspace, etc.). See `.env.example` for required variables.

```bash
git clone https://github.com/twade123/jarvis-core.git
cd jarvis-core
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt  # generate from imports if missing

# 1. Configure
cp .env.example .env
# Edit .env (ANTHROPIC_API_KEY, OANDA_*, etc.)

# 2. Start local MLX servers (Apple Silicon required)
bash scripts/mlx_servers.sh

# 3. Initialize databases (schemas only; runtime data NOT included)
python Jarvis_Agent_SDK/database_directory.py --init

# 4. Launch the UI (port 8766)
python serve_ui.py
# or use the launcher:
bash launch_trevor_desktop.sh
```

---

## What's NOT in this repo (and why)

- **Real model weights / LoRA adapters** — too large for git. Publish on HuggingFace separately.
- **Trading team source** — separate repo: [forex-trading-team](https://github.com/twade123/forex-trading-team). It's one workspace that runs on top of this platform.
- **Live databases** — `trevor_database.db` is 11.8 GB of real conversation data. Schemas are in `Database/`. Runtime data is excluded.
- **Conversation logs** — `boardroom_conversations.json`, real session transcripts. Excluded.
- **Third-party integration MCPs** — `gohighlevel_mcp/`, `google_workspace_mcp/`, `meta_ads_mcp/`, `healthie_*`, etc. These contain credentials or client-specific schemas. Architecture is preserved in the handler framework; the actual integration code is omitted.
- **Client work** — anything tied to specific client engagements has been scrubbed.
- **Archived development phases** — the `archive/` directory (boardroom-phase3, root_cleanup_phase1-3, etc.) contains ~30 historical reorgs not relevant to current architecture.

---

## Why this exists

The thesis: **a disciplined swarm of role-bounded LLM agents — backed by deterministic infrastructure for routing, state, observability, and shared memory — beats any single-model approach for any task complex enough to require more than one perspective.** Trevor is the personal proof: built incrementally over months on one Mac Studio, used daily, hosts a live trading system, and gets measurably smarter as the vault grows.

---

## License

Private — provided here for review purposes.
