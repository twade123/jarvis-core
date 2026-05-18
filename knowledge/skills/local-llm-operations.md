---
name: local-llm-operations
description: Operate, configure, troubleshoot, and deploy Jarvis's local AI models — Qwen3.5 35B (Opus replacement, OpenClaw primary), Qwen3.5 9B (TA agent, boardroom CRO), Kronos (forex OHLCV forecasting), DeepSeek-R1-14B and Qwen2.5-7B and Qwen2.5-Coder-32B (boardroom specialists), Whisper (voice). Covers MLX serving, vLLM serving for Claude Code via ANTHROPIC_BASE_URL, OpenClaw openai-completions bridge, tool calling (Anthropic, OpenAI, Qwen native formats), thinking modes (enable_thinking=false for tools), compaction and token-usage tuning, LoRA distillation, model versioning, and unified vault plus Nexus memory integration. Use when launching or debugging MLX servers on ports 11500-11504; editing openclaw.json; deploying a newly-trained 35B or 9B; wiring Claude Code to local models; debugging speed drops, empty content, context overflow, or memory conflicts; setting up tool calling; running Kronos forecasts; integrating vault memory into agent context.
---

# Local LLM Operations

**How to use this skill:** SKILL.md is the map. Load only the reference files you need for the task at hand.

## Operator's mental model

Three independent systems:

1. **General agent work** (OpenClaw, Claude Code, most handlers) → **Qwen3.5 35B** on port 11502. Replaces Opus.
2. **Trading pipeline** → Anthropic (validator) + Qwen3.5 **9B** (TA) + **Kronos** (forex OHLCV forecasting). Separate stack, separate code paths.
3. **Boardroom specialist seats** → DeepSeek-R1-14B (CTO), Qwen2.5-7B (CDO), Qwen2.5-Coder-32B (Coder). Local, text-only, no adapters.

**Rule:** 35B is the everything-else model. Never swap it for a smaller model without a specific reason. If "9B stepping in as a subagent" comes up, the answer today is: **no, 9B is not distilled for that yet** — keep subagents on 35B.

## Versioning rule (applies to every model)

**Always point at the most recent tuned version.** Never serve raw HuggingFace base models when a Jarvis-tuned variant exists.

Current production pointers (update when a new tune lands):

| Model | Pointer location(s) | Current | Pattern |
|---|---|---|---|
| 35B | `~/.openclaw/openclaw.json` · `scripts/mlx_servers.sh` CSO · `handler_*.py` | `mlx-community/Qwen3.5-35B-A3B-4bit` + `combined_35b` LoRA | Multi-location (brittle) |
| 9B | `scripts/mlx_servers.sh` CRO | `mlx-community/Qwen3.5-9B-4bit` + `validator_35b` LoRA | Multi-location (brittle) |
| Kronos | `TUNING["kronos.model_name"]` | `models/kronos/finetuned/forex_m15_pip_norm_refined` | Single knob (gold standard) |

**The Kronos pattern (one pointer in TUNING) is the goal.** Use `scripts/swap_trained_model.sh` to find and update every pointer atomically when a new LoRA is deployed. Version paths like `~/Jarvis/models/mlx/qwen3.5-35b-jarvis-v2-4bit` so rollback is cheap.

## Navigate by task

**Two documentation layers**: this skill's `references/` covers the operational view (ports, deployment, non-negotiables). The vault at `~/Jarvis/knowledge/collective/models/` + `collective/kronos/` covers deep reference (architecture, known issues, chat templates, upstream docs) and is FTS-searchable by any agent.

| What you're doing | Load |
|---|---|
| First look at what models exist | `references/model-matrix.md` + the specific file in `references/models/` (skill) or `collective/models/*.md` (vault, deep) |
| Launching/debugging MLX servers | `references/serving-mlx.md` + `scripts/health_check.sh` |
| Pointing Claude Code at a local model | `references/serving-vllm.md` + `references/client-claude-code.md` + `scripts/claude_code_local.sh` |
| Editing OpenClaw config for token/compaction/tool issues | `references/client-openclaw.md` + `references/openclaw-settings.md` + `assets/openclaw.json.template` |
| Tool-calling broken / empty content | `references/tool-calling.md` + `references/thinking-mode.md` + `scripts/tool_call_smoke_test.py` |
| Handler/trading code calling a local model | `references/client-trading-handlers.md` |
| Training and deploying a new LoRA-tuned 35B/9B | `references/distillation.md` + `references/lora-adapters.md` + `references/model-formats.md` + `scripts/swap_trained_model.sh` |
| Kronos training or forecast debug | `references/models/kronos-base.md` + `references/kronos-finetuning.md` + `scripts/kronos_smoke_test.py` |
| Wiring vault + Nexus into agent context | `references/memory-integration.md` + `scripts/vault_search.py` |
| 90% slowdown on Claude Code | `references/client-claude-code.md` (Attribution Header KV gotcha) + `scripts/attribution_header_check.sh` |
| Unknown symptom | `references/troubleshooting.md` |

## Non-negotiables (these bite)

1. **`enable_thinking: false`** must be set on Qwen3.5 models when tool-calling. Otherwise the answer goes to `reasoning` field and `content` is empty — OpenClaw and Claude Code both silently fail.
2. **35B and 9B are mutually exclusive during live trading.** 35B VLM uses 40+ GB with vision; 9B uses ~16 GB; total exceeds the 64 GB box. Running both crashes the 9B.
3. **OpenClaw's `anthropic` provider is hardwired to api.anthropic.com.** You cannot point it at a local vLLM. For OpenClaw, local always means `openai-completions` shape.
4. **Claude Code respects `ANTHROPIC_BASE_URL`.** This is the only way to make the `claude` CLI use a local model, and it requires **vLLM with `--tool-call-parser qwen3_coder`**, not MLX.
5. **Claude Code's Attribution Header invalidates KV cache → 90% speed drop.** Fix: unsloth.ai/docs/basics/claude-code.
6. **Don't use Ollama for serving local models to OpenClaw.** Its streaming doesn't emit `tool_calls` delta chunks — tool calls and compaction silently fail. Use MLX or vLLM.
7. **Metal "ImpactingInteractivity" crash ≠ OOM.** macOS kills GPU command buffers for taking too long. Fix by filtering training data to ≤4000 chars, not by reducing layers.

## Memory and vault integration

The unified knowledge graph lives at `~/Jarvis/knowledge/_index.db` — **two layers overlaid as one**:

- **Vault** (`source='vault'`, 858 MD files): learnings, patterns, decisions, skills, agents. Linked via `wiki_link`.
- **Code** (`source='code'`, 6,905 Python modules): AST scan from `.nexus-map/`, imported via `knowledge/nexus_bridge.py`. Linked via `code_import` (2,274 edges).

A single FTS5 query hits both corpora. Graph traversal answers code-impact + knowledge-context in one pass. See `references/memory-integration.md`.

Already-wired helpers the 35B should use:
- `vault_cli.py` — search/write vault (CLI)
- `nexus-query` skill — code structure queries
- `openclaw_vault_bridge.py --all` — regenerate `VAULT_CONTEXT.md` + sync daily logs
- `scripts/vault_search.py` (this skill) — one-shot unified query

## Quick copy-paste

```bash
# MLX server status
~/Jarvis/scripts/mlx_servers.sh status

# Start all 4 resident seats (CRO CTO CSO CDO)
~/Jarvis/scripts/mlx_servers.sh start

# Health check: MLX + vLLM + Kronos + Whisper
bash .agents/skills/local-llm-operations/scripts/health_check.sh

# Smoke-test 35B tool calling (OpenAI-shape and Anthropic-shape)
python3 .agents/skills/local-llm-operations/scripts/tool_call_smoke_test.py

# Unified vault + code search
python3 .agents/skills/local-llm-operations/scripts/vault_search.py "your keywords"

# Point Claude Code at local 35B (requires vLLM running on 8000)
source .agents/skills/local-llm-operations/scripts/claude_code_local.sh

# Deploy a newly-merged/MLX-converted model
bash .agents/skills/local-llm-operations/scripts/swap_trained_model.sh \
  --model 35b --path ~/Jarvis/models/mlx/qwen3.5-35b-jarvis-v2-4bit
```

## Maintenance

- When a new LoRA finishes training on RunPod → `references/distillation.md` covers merge → MLX convert → `swap_trained_model.sh`.
- When OpenClaw updates via npm → re-check `references/client-openclaw.md` for any JS-bundle patches and `references/openclaw-settings.md` for schema drift.
- After every meaningful change → write to vault via `vault_cli.py`.
