---
name: MiroFish Context
title: MiroFish — Forex Simulation System for Boardroom Agents
scope: all_members
version: 1.0
updated: 2026-03-21
---

# MiroFish — What It Is and How to Use It

## The System

MiroFish is Jarvis's local, offline AI-powered forex market simulation platform. It takes real market analysis documents (news, technical analysis, confluence reports) and runs a synthetic "social media simulation" of trader reactions using LLM-powered agents. The output is a structured prediction of market sentiment and direction — essentially crowdsourced alpha from synthetic market participants.

**Location**: `~/Jarvis/MiroFish/`
**Backend**: Flask on port 5001
**Storage**: Neo4j graph database (Docker, port 7687)
**Embeddings**: Ollama nomic-embed-text (port 11434)

## Architecture — The Pipeline

```
Seed Document(s) → Ontology → Knowledge Graph → Simulation → Report
```

1. **Ontology Generation** (`POST /api/graph/ontology/generate`)
   Upload forex analysis docs. LLM extracts: entities (currencies, instruments, economic events), relationships, and a domain ontology tailored to the simulation requirement.

2. **Graph Build** (`POST /api/graph/build`)
   Chunks documents, runs NER, creates nodes and edges in Neo4j. Hybrid search (0.7×vector + 0.3×BM25). Returns async task_id — poll `/api/graph/task/{task_id}`.

3. **Simulation Create** (`POST /api/simulation/create`)
   Instantiates simulation from project. Configures Twitter + Reddit virtual platforms.

4. **Simulation Prepare** (`POST /api/simulation/prepare`)
   Generates LLM-powered agent profiles (traders, analysts, retail investors) with distinct personalities, risk tolerances, and biases drawn from the knowledge graph.

5. **Simulation Run** (`POST /api/simulation/start`)
   Runs OASIS framework: agents read posts, react, create content, follow/unfollow — multiple rounds. Model: the 7B swarm (see below).

6. **Report** (`POST /api/report/generate`)
   ReportAgent synthesizes simulation outcomes into a structured trade prediction: direction, confidence, key drivers, risks.

## Two-Tier Model Architecture

MiroFish uses a deliberate split between two local model tiers:

### Tier 1 — Boardroom Execution (9B Models, ports 11500–11502)
For boardroom deliberation, Trevor routing, complex multi-step reasoning:
- **CRO/CTO**: Qwen3.5-9B-4bit (port 11500) — fast reasoning, tool calling
- **CSO**: Qwen3.5-35B-A3B (port 11502) — deepest strategic analysis
- **Start/stop**: `~/Jarvis/scripts/mlx_servers.sh start [CRO|CTO|CSO]`

### Tier 2 — MiroFish Swarm (7B Model, CDO seat, port 11503)
For running hundreds of simulated trader agents cheaply and in parallel:
- **CDO**: Qwen2.5-7B-Instruct-4bit (port 11503)
- **Why 7B**: Each sim agent makes dozens of inference calls per round. At 7B, we can run 50-100 agents in parallel without saturating memory. At 9B, cost is too high.
- **LLM endpoint**: `http://localhost:11503/v1` (OpenAI-compatible)
- **Model ID**: `mlx-community/Qwen2.5-7B-Instruct-4bit`
- **Config**: `~/Jarvis/MiroFish/.env`

The CDO seat doubles as both a boardroom board member AND the MiroFish swarm server. This is intentional — it keeps the 7B model warm, and the CDO's domain expertise and the simulation swarm's collective "crowd" are conceptually aligned.

## Starting MiroFish Services

All services should be running before a simulation. Check status:

```bash
~/Jarvis/scripts/mlx_servers.sh status     # Check CDO (port 11503) is up
curl -s http://localhost:5001/api/graph/project/list | python3 -m json.tool | head -10
```

Start CDO if not running:
```bash
~/Jarvis/scripts/mlx_servers.sh start CDO
```

Start Flask app (if not running):
```bash
cd ~/Jarvis/MiroFish/backend && source ~/myenv/bin/activate && python run.py &
```

## Running a Simulation (Quick Reference)

**Pipeline script** (end-to-end, ~15-30 min for 3-round simulation):
```bash
cd ~/Jarvis/MiroFish && bash test_pipeline.sh
```

**Manual via API**:
```bash
# 1. Generate ontology
curl -X POST http://localhost:5001/api/graph/ontology/generate \
  -F "files=@/path/to/analysis.txt" \
  -F "simulation_requirement=Analyze SHORT position on USD_JPY" \
  -F "project_name=USD_JPY_test" \
  -F "domain_hint=forex"

# 2. Build graph (async — poll task_id)
curl -X POST http://localhost:5001/api/graph/build \
  -H "Content-Type: application/json" \
  -d '{"project_id": "proj_XXXX"}'

# 3-6. Create → Prepare → Start → Report (see test_pipeline.sh for full sequence)
```

**Seed documents**: Real forex analysis files live at:
`~/Jarvis/.planning/mirofish_backtest/seed_documents/`

## Simulation Output

Results land in:
- `~/Jarvis/MiroFish/simulation_output/` — raw simulation logs per agent/round
- `~/Jarvis/MiroFish/benchmark_results.json` — historical benchmark run results
- Report endpoint: `GET /api/report/{simulation_id}` returns structured JSON prediction

## Backtest Infrastructure

MiroFish has a parallel backtesting system at `~/Jarvis/.planning/mirofish_backtest/`:
- `bt_step1_ontology.py` — batch ontology generation from historical seed docs
- `bt_step2_build_sim.py` — batch graph build + simulation setup
- `bt_full_backtest.py` — full parallel backtest runner
- `run_parallel_simulation.py` — parallel simulation execution

These feed historical win/loss metrics into `benchmark_results.json` — useful for validating whether simulation predictions correlate with actual outcomes.

## How to Use MiroFish in Boardroom Decisions

When Tim asks about a forex trade decision, the boardroom can:

1. **DELEGATE simulation run** (if a fresh analysis doc is available):
   ```
   DELEGATE: mirofish_runner | Run 3-round USD_JPY SHORT simulation using seed: [path]
   ```

2. **Query existing simulation results** (CDO is best suited):
   ```
   RESEARCH: Search Neo4j for recent USD_JPY simulation outcomes with sentiment > 0.7
   ```

3. **Check benchmark data** (CDO):
   ```
   RESEARCH: Read ~/Jarvis/MiroFish/benchmark_results.json — show win rates by pair
   ```

4. **Cross-reference with live trading bot**:
   MiroFish predictions can be compared against the V4 pipeline predictions at `~/Jarvis/Logs/` to check alignment before Tim acts on a position.

## Known Issues and Notes

- **Port 11520 is deprecated**: The .env was previously pointing at port 11520 (a standalone MLX server). It now correctly points to CDO (port 11503). If anything references 11520, update it to 11503.
- **Ontology step is LLM-heavy**: Takes 5-15 min depending on doc size. Don't kill it — it will timeout if CDO is down.
- **Graph build can stall**: If it polls `processing` for >10 min with no progress in Flask logs, CDO may have dropped. Check with `~/Jarvis/scripts/mlx_servers.sh status`.
- **Embeddings via Ollama**: MiroFish embeddings use `nomic-embed-text` via Ollama (port 11434), NOT the MLX server. Ollama must be running.
- **Neo4j must be running**: `docker ps | grep neo4j` — if stopped, `docker start [container_id]`.
