# Model Matrix

Every model in the Jarvis stack. Two layers of documentation:

- **Skill layer** (here, under `models/`): operational — ports, roles, deployment
- **Vault reference layer** (`knowledge/collective/models/` and `collective/kronos/`): deep per-model knowledge — architecture, known issues, fixes, chat templates, tool calling, official sources

All vault docs are FTS-indexed in `_index.db`, searchable by any agent.

## The 17-seat boardroom architecture (new 2026-04-22)

`Handler/seat_registry.py` maps 17 C-suite seats to 6 model servers (A–F). Multiple seats share a server differentiated by system prompt + persona.

⚠️ **Divergence**: `scripts/mlx_servers.sh` has NOT been updated to match `seat_registry.py` yet. Port 11504 differs between the two. See `knowledge/collective/models/boardroom-seat-mapping.md` for details.

### Server / seat table

| Server | Port | Model | Seats | Active Mem | Skill file | Vault series |
|---|---|---|---|---|---|---|
| **A** | 11502 | Qwen3.5-35B-A3B-4bit | **CEO** (Chair) | 4.5 GB | [models/qwen35-35b.md](models/qwen35-35b.md) | `collective/models/qwen3.5-35b/` (10 files) |
| **B** | 11501 | DeepSeek-R1-Distill-14B-4bit | **CTO** | 8.5 GB | [models/deepseek-r1-14b.md](models/deepseek-r1-14b.md) | `collective/models/deepseek-r1-distill-14b.md` |
| **C** | 11500 | Qwen3.5-9B-4bit | **CRO** (+ TA agent) | 5.5 GB | [models/qwen35-9b.md](models/qwen35-9b.md) | `collective/models/qwen3.5-9b/` (10 files) |
| **D** | 11504 | **Qwen3-30B-A3B-4bit** (NEW) | **CSO, CPO, CMO, CRvO** | 4.0 GB | — | `collective/models/qwen3-30b-a3b.md` |
| **E** | 11503 | Qwen2.5-7B-Instruct-4bit | **CDO, CFO** | 4.5 GB | [models/qwen25-7b.md](models/qwen25-7b.md) | `collective/models/qwen2.5-7b-instruct.md` |
| **F** | 11505 | **Qwen2.5-1.5B-Instruct-4bit** (NEW) | **COO, CCO, CHRO, CISO, CXO, VPE, CDS, GC** (8 ops) | 1.4 GB | — | `collective/models/qwen2.5-1.5b-instruct.md` |

**Legacy / transitioning**:
| — | 11504 | Qwen2.5-Coder-32B-Instruct-4bit | Coder seat | 20 GB | [models/qwen25-coder-32b.md](models/qwen25-coder-32b.md) | `collective/models/qwen2.5-coder-32b.md` |

Coder-32B is still in `mlx_servers.sh` but removed from `seat_registry.py`. Decision pending: retire or move to a different port.

Source of truth: `~/Jarvis/Handler/seat_registry.py`.

## Non-LLM neural model

| Model | Runtime | Role | Reference |
|---|---|---|---|
| **Kronos-base (102M)** | in-process MPS via `kronos_inference.py` | Forex OHLCV forecasting — **not an LLM** | `collective/kronos/` (7 files incl. finetuning workflow) |

## Voice / audio

| Model | Path | Used by | Reference |
|---|---|---|---|
| **Whisper** | `Core/models/{small,medium,large-v3}.pt`, `whisper/base.pt` | OpenClaw audio (small.pt), voice capture | [models/whisper.md](models/whisper.md) · `collective/models/whisper.md` |

## Resource map (64 GB M-series) — updated for 17-seat architecture

| Combo | RAM | Notes |
|---|---|---|
| Just CEO (A) resident | ~17 GB | Default minimal boardroom |
| CEO + CRO + CSO boardroom mini (A+C+D) | ~37 GB | Small deliberation |
| Full 6-server boardroom (A+B+C+D+E+F) | ~51 GB | All servers hot — doable on 64 GB |
| CEO vision + CRO active | ~53 GB | Vision doubles A's footprint; don't run 9B concurrently |
| Coder legacy (20 GB) + other boardroom | variable | Not in new registry — only run if explicitly kept |

Full details in `collective/models/boardroom-seat-mapping.md`.

## Adapter conventions

13 LoRA adapters at `~/jarvis/models/adapters/`:
`35b`, `35b_mlx`, `9b`, `combined_35b{,_hf,_peft}`, `combined_9b`, `ta_9b{,_peft}`, `trade_monitor_35b`, `trevor_35b`, `trevor_9b`, `validator_35b`.

**Currently loaded**:
- Server A (CSO) → `combined_35b`
- Server C (CRO) → `validator_35b` (naming gotcha — see `collective/models/qwen3.5-9b/06-validator-35b-adapter.md`)
- Servers B, D, E, F → no adapters (base only)

See `lora-adapters.md` for inventory, lifecycle, and planning.

## Model-format pipeline

`base/` (HF fp16) → `merged/` (LoRA merged) → `mlx/` (MLX 4-bit, Apple Silicon serving) → `gguf/` (llama.cpp/Ollama, non-Apple hosts).

Paths: `~/Jarvis/models/{base,merged,mlx,gguf}/`.

See `model-formats.md` for when to use each and how to convert.
