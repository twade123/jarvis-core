# Distillation — LoRA training + deployment pipeline

Applies to **Qwen3.5 35B and 9B** — the chat/agent LLMs. Kronos has its own pipeline documented separately in `kronos-finetuning.md`.

## Strategy

Distill frontier-model reasoning (Claude Opus, DeepSeek, GPT) + Jarvis-specific usage traces into local Qwen3.5. The distilled model becomes a synthesis of the best reasoning, specifically tuned to our platform.

Source of truth for strategy: `knowledge/agents/trevor/2026-03-19-local-model-distillation-full-day-session.md` + project memory `project_distillation_strategy.md`.

## The dataset

**v2 dataset** (in-flight as of this skill's writing): 24,711 entries total, 95/5 split → 22,301 train / 1,174 valid.

Sources:
| Source | Count |
|---|---|
| Trading / system data | ~20,000 |
| Claude Code tool-calling arcs | 4,017 |
| Plans | 29 |
| History arcs | 438 |
| Memory files | 17 |
| Paste cache | 93 |

Tool-calling arcs extracted from **961 Claude Code sessions** (210 main + 751 subagent). Includes:
- 3,396 tool calling
- 2,899 multi-tool chains
- 1,675 search workflows
- 1,365 error recovery
- 1,259 code edit
- 274 subagent dispatch
- 167 thinking/reasoning
- 123 planning

Files:
- `~/Jarvis/training_data/distillation/merged_35b_train.jsonl` (74 MB)
- `~/Jarvis/training_data/distillation/merged_valid.jsonl` (3.6 MB)

Format: `{"messages": [{"role": "...", "content": "..."}]}`. Tool calls flattened to `<tool_use>/<tool_result>` tags inside content. **This teaches Qwen its native format.** vLLM and our MLX server handle translation to/from Anthropic/OpenAI shape at inference time.

## Training infrastructure

**RunPod 2× A100 SXM 80GB in bf16.** Script: `train_lora_35b.py` (force GPU placement, no CPU offload).

Config:
- Speed: ~23s/step
- Steps: 5,576
- Epochs: 2
- ETA: ~36 hours
- Checkpoints every 500 steps
- Adapter saves to `/workspace/distillation_cloud/adapters/35b/`

**DO NOT train fp16 on M1 Max.** Always OOMs — GPU cap is 55 GB, model needs 70 GB.

## Why RunPod and not local

- M1 Max 64 GB can run MLX inference on 4-bit quant (40 GB), but can't hold fp16 + optimizer state for LoRA training at 35B scale
- 9B LoRA training fits on M1 Max (see below) — 35B doesn't

## 9B LoRA training on M1 Max — lessons learned

From `2026-03-20-trevor-9b-lora-training-key-lessons-on-mlxmetal-crashes.md`:

1. **Metal `ImpactingInteractivity` crash is NOT OOM.** It's macOS killing the GPU command buffer for taking too long. Caused by long sequences (4448 tokens) even when truncated to 1024. Fix: **filter training data to ≤4000 chars, don't reduce layers**.
2. **`--resume-adapter-file` does NOT restore optimizer state in MLX.** Starts gradients fresh on shifted weights, destabilizes Metal allocator. **Always train from scratch.**
3. **Filtered dataset path**: `~/jarvis/training_data/sessions/_lora_filtered_9b` — 8428 examples, all under 4000 chars (~1000 tokens). The 606 removed examples were session dumps and vault doc retrievals, not coding CoT.
4. **Stable config for 9B on M1 Max**: 6 layers, lr 3e-5, batch 1, seq 1024, grad-checkpoint, filtered data. Peak memory 42.976 GB stable.
5. **Qwen3.5-35B-A3B is NEWER than Qwen3-32B** — released Feb 2026 vs Sep 2025. Already on latest.

## Deployment pipeline (after training completes)

```
RunPod adapter → Download → Merge into base → Convert to MLX 4-bit → Deploy via swap_trained_model.sh
```

### Step 1: Download adapter via `runpodctl` / croc

The `runpodctl` CLI is installed locally (as of 2026-04-22). It uses [croc](https://github.com/schollz/croc) for P2P transfer — no SSH keys, no scp config.

**On the pod** (via RunPod web terminal or SSH):
```bash
cd /workspace/distillation_cloud/adapters
tar czf 35b-v2.tar.gz 35b/
runpodctl send 35b-v2.tar.gz
# prints: Code is: 1234-random-words-codephrase
```

**On local Mac:**
```bash
cd ~/jarvis/models/adapters
runpodctl receive 1234-random-words-codephrase
tar xzf 35b-v2.tar.gz
mv 35b combined_35b_v2
```

Full RunPod workflow (account setup, pod lifecycle, billing): see vault `collective/models/qwen3.5-35b/09-runpod-account-and-workflow.md`.

### Step 2: Merge LoRA into base

```bash
# 35B
cd ~/Jarvis && source ~/myenv/bin/activate
python train_lora_35b.py merge \
  --base Qwen/Qwen3.5-35B-A3B \
  --adapter ~/jarvis/models/adapters/combined_35b_v2 \
  --out ~/Jarvis/models/merged/qwen3.5-35b-jarvis-v2

# 9B
python train_lora.py --model 9b merge \
  --base Qwen/Qwen3.5-9B \
  --adapter ~/jarvis/models/adapters/combined_9b_v2 \
  --out ~/Jarvis/models/merged/qwen3.5-9b-jarvis-v2
```

Warning: `train_lora.py` was overwritten with a 35B-specific version during the v2 training cycle. Restore the original for 9B work before running.

### Step 3: Convert merged fp16 → MLX 4-bit

```bash
python -m mlx_lm.convert \
  --hf-path ~/Jarvis/models/merged/qwen3.5-35b-jarvis-v2 \
  --mlx-path ~/Jarvis/models/mlx/qwen3.5-35b-jarvis-v2-4bit \
  --quantize --q-bits 4
```

### Step 4: Verify tool calling before deploying

```bash
# Start a temporary MLX server on a free port
python3 ~/Jarvis/scripts/mlx_vlm_server_with_tools.py \
  --model ~/Jarvis/models/mlx/qwen3.5-35b-jarvis-v2-4bit \
  --port 11599 --host 127.0.0.1 &

# Smoke test
python3 .agents/skills/local-llm-operations/scripts/tool_call_smoke_test.py \
  --endpoint openai --port 11599

# Stop the test server
pkill -f "mlx_vlm.*--port 11599"
```

### Step 5: Swap production pointers

```bash
bash .agents/skills/local-llm-operations/scripts/swap_trained_model.sh \
  --model 35b \
  --path ~/Jarvis/models/mlx/qwen3.5-35b-jarvis-v2-4bit
```

The script updates:
1. `scripts/mlx_servers.sh` — CSO SEAT_CONFIG line
2. `~/.openclaw/openclaw.json` — model id + primary + subagents.primary
3. `handler_data_validator.py` — only if model name is hardcoded (shouldn't be — port is the only hardcode)

Shows a diff, requires explicit approval, backs up files before writing.

### Step 6: Restart and verify

```bash
bash ~/Jarvis/scripts/mlx_servers.sh restart
bash .agents/skills/local-llm-operations/scripts/health_check.sh
python3 .agents/skills/local-llm-operations/scripts/tool_call_smoke_test.py --endpoint openai --port 11502
```

## Versioning convention

`qwen3.5-35b-jarvis-v2-4bit`, `qwen3.5-35b-jarvis-v3-4bit`, etc. Keep old versions on disk for cheap rollback — the MLX 4-bit models are 15-20 GB each, disk is cheap.

Rollback:
```bash
bash .agents/skills/local-llm-operations/scripts/swap_trained_model.sh \
  --model 35b \
  --path ~/Jarvis/models/mlx/qwen3.5-35b-jarvis-v1-4bit
```

## When to retrain

- New significant tool-calling patterns emerge in Claude Code sessions → re-extract + train v3
- Agent behavior regresses (e.g., hallucinates tool schemas) → check training data freshness
- New base model released by Qwen → consider bumping base (full retrain required; LoRA doesn't transfer)

## Related

- `models/qwen35-35b.md` — current 35B state + pointer locations
- `models/qwen35-9b.md` — 9B v1 status, v2 pending
- `lora-adapters.md` — the 13 adapters in `~/jarvis/models/adapters/`
- `model-formats.md` — base → merged → MLX → GGUF pipeline
- `kronos-finetuning.md` — completely separate Kronos training pipeline
