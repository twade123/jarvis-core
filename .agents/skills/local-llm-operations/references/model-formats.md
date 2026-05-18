# Model Formats — base → merged → MLX / GGUF

## The pipeline

```
base/            — HuggingFace fp16, training-ready
  ↓ LoRA training writes adapter
adapters/        — LoRA weights (small, easy to swap)
  ↓ merge into base
merged/          — fp16 HuggingFace with LoRA baked in
  ↓ quantize + convert
mlx/             — MLX 4-bit for Apple Silicon serving  (PRODUCTION)
  OR
gguf/            — GGUF quantized for llama.cpp / Ollama (cold, for non-Apple)
```

Root: `~/Jarvis/models/`.

## What we have

```
base/
  Qwen3.5-35B-A3B/           — HF fp16 35B base

merged/
  qwen3.5-9b-jarvis/         — merged 9B v1 (not yet converted to MLX for production)

mlx/
  qwen3.5-9b-jarvis-4bit/    — 9B v1 MLX 4-bit, 5.1 GB, NOT deployed

gguf/
  trevor-35b-q4.gguf
  trevor-9b-q4_K_M.gguf
  trevor-combined-35b-f16.gguf
  trevor-fused-35b-f16.gguf
  trevor-fused-35b-q4_K_M.gguf
  Modelfile.trevor
  Modelfile.trevor-9b
  Modelfile.trevor-fused
```

## When to use each format

### `base/` (HuggingFace fp16)
- Input to LoRA training
- Input to adapter merging
- NEVER served directly — too big and unoptimized

### `adapters/` (LoRA)
- 500 MB - 2 GB each
- Loaded at MLX server startup (`--adapter-path`)
- Alternative to pre-merging (faster to iterate)

### `merged/` (fp16 with LoRA baked in)
- Intermediate output: LoRA → merged base
- Input to MLX or GGUF conversion
- NEVER served directly — still too big

### `mlx/` (MLX 4-bit)
- **Primary production serving format on Apple Silicon**
- ~15-20 GB per 35B model (vs 70 GB for fp16)
- ~5 GB per 9B model
- Served by `mlx_lm.server` / `mlx_lm_server_lenient.py` / `mlx_vlm_server_with_tools.py`

### `gguf/` (llama.cpp quantization)
- Cold export for non-Apple deployment
- q4_K_M ≈ 20 GB for 35B, 5-6 GB for 9B
- f16 GGUF ≈ 70 GB — for re-requantizing or moving
- Served by llama.cpp, Ollama, KoboldCpp, LM Studio
- NOT served in our production (we moved off Ollama)

## Conversions

### fp16 merged → MLX 4-bit

```bash
source ~/myenv/bin/activate
python -m mlx_lm.convert \
  --hf-path ~/Jarvis/models/merged/qwen3.5-35b-jarvis-v2 \
  --mlx-path ~/Jarvis/models/mlx/qwen3.5-35b-jarvis-v2-4bit \
  --quantize --q-bits 4
```

Flags:
- `--q-bits 4` is the sweet spot for 35B on 64 GB (memory vs quality)
- `--q-bits 8` for highest quality at ~2× memory (not worth it on 64 GB M-series)
- `--q-bits 2` for 9B experimental tiny mode (not worth it — quality loss)

Typical time: ~10-20 minutes for a 35B model on M1 Max.

### MLX → GGUF (FAILED PATH)

MLX quantization format is **incompatible with llama.cpp converter**. Multiple attempts documented in `2026-03-19-local-model-distillation-full-day-session.md`. If you need GGUF:
- Convert from **merged fp16**, not from MLX
- Use `llama.cpp/convert_hf_to_gguf.py` on `~/Jarvis/models/merged/qwen3.5-35b-jarvis-v2`

### fp16 merged → GGUF

```bash
cd /path/to/llama.cpp
python convert_hf_to_gguf.py \
  ~/Jarvis/models/merged/qwen3.5-35b-jarvis-v2 \
  --outtype f16 \
  --outfile ~/Jarvis/models/gguf/qwen3.5-35b-jarvis-v2-f16.gguf

# Then quantize
./llama-quantize \
  ~/Jarvis/models/gguf/qwen3.5-35b-jarvis-v2-f16.gguf \
  ~/Jarvis/models/gguf/qwen3.5-35b-jarvis-v2-q4_K_M.gguf \
  Q4_K_M
```

### Rotation: keep old versions

Disk is cheap. Keep v1, v2, v3 so rollback is trivial:

```
~/Jarvis/models/mlx/
  qwen3.5-35b-jarvis-v1-4bit/
  qwen3.5-35b-jarvis-v2-4bit/    ← current
  qwen3.5-35b-jarvis-v3-4bit/    ← when shipped
```

## Kronos is different

Kronos is PyTorch-native, loaded via HuggingFace `from_pretrained()` directly from `~/Jarvis/models/kronos/finetuned/<variant>/`. No MLX conversion, no GGUF. Runs on MPS. See `models/kronos-base.md` and `kronos-finetuning.md`.

## Disk hygiene

```bash
# See which formats take what
du -sh ~/Jarvis/models/{base,merged,mlx,gguf}/*

# Typical sizes
# 35B base HF fp16:    70 GB
# 35B merged fp16:     70 GB
# 35B MLX 4-bit:       17 GB
# 35B GGUF q4_K_M:     20 GB
# 9B merged fp16:      18 GB
# 9B MLX 4-bit:        5 GB
# 9B GGUF q4_K_M:      5 GB
```

Safe to delete: old `merged/` once `mlx/` is built and verified. Keep `adapters/` (small, recoverable). Keep all `mlx/` versions for rollback.

## Related

- `distillation.md` — the full pipeline from training to deployment
- `lora-adapters.md` — adapter naming, lifecycle
- `serving-mlx.md` — how MLX loads models and adapters
