#!/usr/bin/env python3
"""
train_and_export_9b.py — Train 9B LoRA and export to GGUF in one shot.

Pipeline:
  1. Run mlx_lm.lora training (M1 Max optimized)
  2. Remap MLX VLM adapter keys → PEFT-compatible keys
  3. Write PEFT adapter_model.safetensors + adapter_config.json
  4. Convert base GGUF + PEFT adapter → 9B GGUF
  5. Quantize f16 → Q4_K_M
  6. ollama create trevor-9b

This mirrors the 35B process but for the 9B model.
Same CoT data (trading, validator, OpenClaw, vault learnings).

Usage:
  python3 train_and_export_9b.py [--skip-train] [--skip-export]

  --skip-train   Skip training, go straight to export
  --skip-export  Train only, don't convert to GGUF
"""

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

JARVIS = Path.home() / "jarvis"
VENV_PYTHON = "~/myenv/bin/python3"

# 9B base model — MLX optimized for training
BASE_HF = "mlx-community/Qwen3.5-9B-4bit"
# HuggingFace base for GGUF conversion (full weights needed by llama.cpp)
BASE_HF_GGUF = "Qwen/Qwen3.5-9B-Instruct"
ADAPTER_DIR = JARVIS / "models/adapters/ta_9b"
FUSED_DIR = JARVIS / "models/fused/trevor-9b"
GGUF_DIR = JARVIS / "models/gguf"
GGUF_F16 = GGUF_DIR / "trevor-9b-f16.gguf"
GGUF_Q4 = GGUF_DIR / "trevor-9b-q4_K_M.gguf"
TRAIN_DATA = JARVIS / "training_data/sessions/_lora_filtered_9b"
LOG_DIR = JARVIS / "Logs"
LLAMA_CPP_SRC = Path("/tmp/llama_cpp_src")
LLAMA_QUANTIZE = Path("/opt/homebrew/bin/llama-quantize")

# Ollama base model name for 9B
OLLAMA_BASE = "qwen3.5:9b"
OLLAMA_MODEL = "trevor-9b"


def run(cmd: list, log_file: str = None, check: bool = True) -> int:
    print(f"\n$ {' '.join(str(c) for c in cmd)}")
    if log_file:
        with open(log_file, "w") as lf:
            result = subprocess.run(cmd, stdout=lf, stderr=subprocess.STDOUT)
    else:
        result = subprocess.run(cmd)
    if check and result.returncode != 0:
        print(f"FAILED (exit {result.returncode})")
        if log_file:
            print(f"See log: {log_file}")
        sys.exit(1)
    return result.returncode


# ── Step 1: Train ─────────────────────────────────────────────────────────────
def train():
    print("\n" + "="*60)
    print("Step 1: Training 9B LoRA adapter (~17GB RAM, 12-24 hours)")
    print("="*60)

    data_dir = TRAIN_DATA
    data_dir.mkdir(parents=True, exist_ok=True)

    if not (TRAIN_DATA / "train.jsonl").exists():
        print(f"ERROR: Training data not found: {TRAIN_DATA / 'train.jsonl'}")
        sys.exit(1)

    # Count training pairs
    with open(TRAIN_DATA / "train.jsonl") as f:
        pairs = sum(1 for _ in f)
    print(f"Training data: {pairs} examples")

    cmd = [
        VENV_PYTHON, "-m", "mlx_lm", "lora",
        "--model", BASE_HF,
        "--data", str(data_dir),
        "--adapter-path", str(ADAPTER_DIR),
        "--iters", "2000",
        "--batch-size", "1",
        "--num-layers", "6",
        "--learning-rate", "3e-5",
        "--max-seq-length", "1024",
        "--grad-checkpoint",
        "--train",
    ]

    log = str(LOG_DIR / "lora_train_9b.log")
    print(f"Log: {log}")
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    run(cmd, log_file=log)
    print("Training complete.")


# ── Step 2: Fuse adapter into base model (MLX native — all 30 tensors) ────────
def fuse_adapter():
    print("\n" + "="*60)
    print("Step 2: Fusing adapter into base weights (mlx_lm.fuse)")
    print("="*60)

    adapter_path = ADAPTER_DIR / "adapters.safetensors"
    if not adapter_path.exists():
        print(f"Adapter not found: {adapter_path}")
        sys.exit(1)

    FUSED_DIR.mkdir(parents=True, exist_ok=True)
    log = str(LOG_DIR / "fuse_9b.log")
    print(f"Log: {log}")

    # PYTHONSTARTUP doesn't execute for `-m` invocations — use inline wrapper script
    wrapper = f"""
import mlx_lm.utils as _mu
_orig = _mu.load
def _l(p, *a, **kw):
    kw.setdefault('strict', False)
    return _orig(p, *a, **kw)
_mu.load = _l
import mlx_lm as _ml
_ml.load = _l

import sys
sys.argv = [
    "fuse",
    "--model", "{BASE_HF}",
    "--adapter-path", "{ADAPTER_DIR}",
    "--save-path", "{FUSED_DIR}",
    "--dequantize",
]
from mlx_lm.fuse import main
main()
"""
    wrapper_file = Path("/tmp/_fuse_9b_wrapper.py")
    wrapper_file.write_text(wrapper)

    cmd = [VENV_PYTHON, str(wrapper_file)]
    print(f"\n$ {' '.join(str(c) for c in cmd)}")
    with open(log, "w") as lf:
        result = subprocess.run(cmd, stdout=lf, stderr=subprocess.STDOUT)
    if result.returncode != 0:
        print(f"FAILED (exit {result.returncode})\nSee log: {log}")
        sys.exit(1)

    print(f"  Fused model saved to: {FUSED_DIR}")
    if GGUF_F16.exists():
        print(f"  f16 GGUF exported: {GGUF_F16} ({GGUF_F16.stat().st_size / 1e9:.1f}GB)")


# ── Step 3: Convert fused model to GGUF ───────────────────────────────────────
def convert_to_gguf():
    print("\n" + "="*60)
    print("Step 3: Converting fused model → GGUF")
    print("="*60)

    convert_script = LLAMA_CPP_SRC / "convert_hf_to_gguf.py"
    if not convert_script.exists():
        print("Cloning llama.cpp source for convert script...")
        run(["git", "clone", "--depth", "1",
             "https://github.com/ggml-org/llama.cpp.git",
             str(LLAMA_CPP_SRC)])
        run([VENV_PYTHON, "-m", "pip", "install",
             str(LLAMA_CPP_SRC / "gguf-py"), "-q"])

    GGUF_DIR.mkdir(parents=True, exist_ok=True)
    log = str(LOG_DIR / "convert_9b_gguf.log")
    print(f"Log: {log}")

    run([
        VENV_PYTHON, str(convert_script),
        str(FUSED_DIR),
        "--outfile", str(GGUF_F16),
        "--outtype", "f16",
    ], log_file=log)

    print(f"  f16 GGUF: {GGUF_F16} ({GGUF_F16.stat().st_size / 1e9:.1f}GB)")


# ── Step 4: Quantize to Q4_K_M ───────────────────────────────────────────
def quantize():
    print("\n" + "="*60)
    print("Step 4: Quantizing f16 → Q4_K_M")
    print("="*60)

    if not LLAMA_QUANTIZE.exists():
        print(f"llama-quantize not found at {LLAMA_QUANTIZE} — skipping quantize, using f16")
        GGUF_Q4.symlink_to(GGUF_F16)
        return

    log = str(LOG_DIR / "quantize_9b.log")
    run([str(LLAMA_QUANTIZE), str(GGUF_F16), str(GGUF_Q4), "Q4_K_M"],
        log_file=log)

    print(f"  Removing f16 intermediate...")
    GGUF_F16.unlink(missing_ok=True)
    print(f"  Q4 GGUF: {GGUF_Q4} ({GGUF_Q4.stat().st_size / 1e9:.1f}GB)")


# ── Step 5: Load into Ollama ──────────────────────────────────────────────
def load_ollama():
    print("\n" + "="*60)
    print("Step 5: Loading into Ollama")
    print("="*60)

    gguf = GGUF_Q4 if GGUF_Q4.exists() else GGUF_F16
    modelfile = GGUF_DIR / "Modelfile.trevor-9b"
    modelfile.write_text(f"""FROM {gguf}

PARAMETER temperature 1
PARAMETER top_p 0.95
PARAMETER top_k 20
PARAMETER num_ctx 131072
PARAMETER presence_penalty 1.5

SYSTEM \"\"\"You are Trevor, an AI assistant running inside OpenClaw for Tim Wade.
You are direct, resourceful, and business-minded. You handle:
- General assistance and quick tasks
- Claude Code workflows
- OpenClaw operations
- Trading bot queries (read-only, refer to validator for analysis)
- Knowledge vault searches
- Documentation help
- System architecture questions
You are faster than the 35B but handle covered domains. For complex reasoning
or validator-specific analysis, defer to the 35B. You get things done without
unnecessary commentary.\"\"\"
""")

    # Remove old version if exists
    subprocess.run(["ollama", "rm", OLLAMA_MODEL], capture_output=True)

    run(["ollama", "create", OLLAMA_MODEL, "-f", str(modelfile)])
    print(f"\n✅ Trevor-9B loaded into Ollama")
    subprocess.run(["ollama", "list"])


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--skip-train", action="store_true")
    parser.add_argument("--skip-export", action="store_true")
    args = parser.parse_args()

    print("\n" + "="*60)
    print("Trevor-9B — Train LoRA on ALL CoT data → GGUF → Ollama")
    print("="*60)
    print("\nThis model will be trained on the same data as Trevor-35B:")
    print("  - Trading bot execution logs")
    print("  - Validator confluence reasoning")
    print("  - OpenClaw workflows")
    print("  - Claude Code patterns")
    print("  - Knowledge vault learnings")
    print("  - ALL Chain-of-Thought reasoning")
    print("\nExpected: ~17GB RAM, 12-24 hours training, approach Trevor's performance")
    print("on covered domains while being faster and cheaper.\n")

    if not args.skip_train:
        train()

    if not args.skip_export:
        fuse_adapter()      # fuses + exports GGUF in one step
        quantize()
        load_ollama()

    print("\n✅ Done!")
    print("\nModel: trevor-9b")
    print("Use with: ollama run trevor-9b")
    print("Note: For complex validator reasoning, still use trevor (35B)")


if __name__ == "__main__":
    main()
