# LoRA Adapters

All at `~/jarvis/models/adapters/`. Adapter naming reflects **training data**, not model size.

## The 13 adapters

| Adapter | Base | Status | What it trains |
|---|---|---|---|
| `35b` | Qwen3.5-35B | reference | plain 35B adapter (minimal fine-tune) |
| `35b_mlx` | Qwen3.5-35B MLX | reference | MLX-format variant of `35b` |
| `9b` | Qwen3.5-9B | reference | plain 9B adapter |
| `combined_35b` | Qwen3.5-35B | **LIVE on CSO** | Combined Trevor + validator knowledge |
| `combined_35b_hf` | Qwen3.5-35B HF | reference | HuggingFace-format copy |
| `combined_35b_peft` | Qwen3.5-35B | reference | PEFT-format copy (for Ollama/llama.cpp) |
| `combined_9b` | Qwen3.5-9B | not live | 9B version of combined dataset |
| `ta_9b` | Qwen3.5-9B | reference | TA-narrative specialist |
| `ta_9b_peft` | Qwen3.5-9B | reference | PEFT copy |
| `trade_monitor_35b` | Qwen3.5-35B | reference | Trade monitoring specialist |
| `trevor_35b` | Qwen3.5-35B | reference | Trevor-agent specialist |
| `trevor_9b` | Qwen3.5-9B | reference | Trevor-agent 9B variant |
| `validator_35b` | **Qwen3.5-9B** (loaded on 9B) | **LIVE on CRO** | Validator knowledge — name is historical |

## Currently deployed

- **CSO seat (35B, port 11502)** loads `combined_35b`
- **CRO seat (9B, port 11500)** loads `validator_35b` (despite the name, it's on 9B)

The mapping is set in `mlx_servers.sh`:
```zsh
typeset -A SEAT_ADAPTER
SEAT_ADAPTER["CRO"]="${ADAPTER_ROOT}/validator_35b"
SEAT_ADAPTER["CSO"]="${ADAPTER_ROOT}/combined_35b"
SEAT_ADAPTER["CTO"]=""   # no adapter — DeepSeek base only
SEAT_ADAPTER["CDO"]=""   # no adapter
```

## Adapter format gotchas

- **`.safetensors`** is the file we need. Server startup checks `ls $adapter_path/*.safetensors` and skips loading if none exist.
- **`_peft`** suffix = HuggingFace PEFT format (required for llama.cpp / Ollama loading). Not used by MLX.
- **`_hf`** suffix = raw HuggingFace format (fp16, for re-merging or re-training).
- **MLX adapter** = adapter saved with MLX's LoRA trainer, compatible with `mlx_lm`'s `--adapter-path` flag.

## Lifecycle

1. Train → adapter saved to `~/jarvis/models/adapters/<name>/` (`.safetensors` files)
2. Server loads adapter at startup via `--adapter-path` arg
3. When retraining → new adapter goes to new versioned dir (`combined_35b_v2/`)
4. `swap_trained_model.sh` updates `SEAT_ADAPTER[<seat>]` pointer in `mlx_servers.sh` and restarts

## Merging vs adapter loading

Two deployment modes:

### Mode A — Base + adapter at server startup (current)
- Pro: base stays generic, adapter is small (~500 MB), easy to swap
- Con: extra memory overhead at load time (adapter merges dynamically)
- When: active iteration, adapter not yet "locked in"

### Mode B — Pre-merged + MLX-converted (production ideal)
- Pro: single load, no runtime merge overhead
- Con: each merged version is a full 15-20 GB model on disk
- When: adapter is production-ready; disk is cheap so keep versioned copies

We're currently **Mode A** for both 35B (CSO with `combined_35b`) and 9B (CRO with `validator_35b`).

`~/Jarvis/models/mlx/qwen3.5-9b-jarvis-4bit` exists as a Mode B build for 9B but is **not deployed** — waiting for v2 retrain.

## Rebuild / reload

```bash
# Pull a fresh adapter from RunPod
scp -r runpod:/workspace/distillation_cloud/adapters/35b ~/jarvis/models/adapters/combined_35b_v2

# Point CSO at v2
# (edit scripts/mlx_servers.sh — SEAT_ADAPTER["CSO"]="${ADAPTER_ROOT}/combined_35b_v2")

# Restart CSO
bash ~/Jarvis/scripts/mlx_servers.sh stop CSO
bash ~/Jarvis/scripts/mlx_servers.sh start CSO

# Verify
curl http://127.0.0.1:11502/health
```

Or use the wrapper:
```bash
bash .agents/skills/local-llm-operations/scripts/swap_trained_model.sh \
  --model 35b --adapter ~/jarvis/models/adapters/combined_35b_v2
```

## Related

- `distillation.md` — training pipeline
- `model-formats.md` — base → merged → MLX/GGUF
- `serving-mlx.md` — how the adapter path flag works
