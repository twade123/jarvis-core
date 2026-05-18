#!/usr/bin/env python3
"""
train_and_export_gguf.py — Train combined_35b LoRA and export to GGUF in one shot.

Pipeline:
  1. Run mlx_lm.lora training (M1 Max optimized, strict=False for VLM weights)
  2. Remap MLX VLM adapter keys → PEFT-compatible keys
  3. Write PEFT adapter_model.safetensors + adapter_config.json
  4. Convert base GGUF + PEFT adapter → Trevor GGUF (convert_lora_to_gguf.py)
  5. Quantize f16 → Q4_K_M
  6. ollama create trevor

This is the permanent retrain path. No fuse step. Output is portable GGUF.

Usage:
  python3 train_and_export_gguf.py [--skip-train] [--skip-export]

  --skip-train   Skip training, go straight to export (adapter already trained)
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
BASE_HF = "mlx-community/Qwen3.5-35B-A3B-4bit"
ADAPTER_DIR = JARVIS / "models/adapters/combined_35b"
PEFT_DIR = JARVIS / "models/adapters/combined_35b_peft"
GGUF_DIR = JARVIS / "models/gguf"
GGUF_F16 = GGUF_DIR / "trevor-combined-35b-f16.gguf"
GGUF_Q4 = GGUF_DIR / "trevor-combined-35b-q4.gguf"
TRAIN_DATA = JARVIS / "training_data/sessions/_lora_combined_35b"
LOG_DIR = JARVIS / "Logs"
LLAMA_CPP_SRC = Path("/tmp/llama_cpp_src")
LLAMA_QUANTIZE = Path("/opt/homebrew/bin/llama-quantize")
OLLAMA_MODEL = "trevor"

# Ollama base model name (pulled separately)
OLLAMA_BASE = "qwen3.5:35b-a3b-q4_K_M"


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
    print("Step 1: Training LoRA adapter")
    print("="*60)

    data_dir = TRAIN_DATA / "_lora_combined_35b"
    data_dir.mkdir(parents=True, exist_ok=True)
    train_link = data_dir / "train.jsonl"
    if train_link.exists():
        train_link.unlink()
    train_link.symlink_to((TRAIN_DATA / "train.jsonl").resolve())

    cmd = [
        VENV_PYTHON, "-m", "mlx_lm", "lora",
        "--model", BASE_HF,
        "--data", str(data_dir),
        "--adapter-path", str(ADAPTER_DIR),
        "--iters", "300",
        "--batch-size", "1",
        "--num-layers", "2",
        "--max-seq-length", "256",
        "--grad-checkpoint",
        "--train",
    ]

    log = str(LOG_DIR / "lora_train_combined_35b.log")
    print(f"Log: {log}")
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    # Train with strict=False patch for VLM weights
    patch = """
import mlx_lm.utils as _mu
_orig = _mu.load
def _l(p, *a, **kw): kw.setdefault('strict', False); return _orig(p, *a, **kw)
_mu.load = _l
import mlx_lm as _ml; _ml.load = _l
"""
    patch_file = Path("/tmp/_mlx_strict_patch.pth")
    patch_file.write_text(patch)

    env = os.environ.copy()
    env["PYTHONSTARTUP"] = str(patch_file)
    with open(log, "w") as lf:
        result = subprocess.run(cmd, stdout=lf, stderr=subprocess.STDOUT, env=env)

    if result.returncode != 0:
        print(f"Training failed — check {log}")
        sys.exit(1)
    print("Training complete.")


# ── Step 2: Remap adapter keys MLX VLM → PEFT ────────────────────────────────
def remap_adapter():
    print("\n" + "="*60)
    print("Step 2: Remapping adapter keys to PEFT format")
    print("="*60)

    try:
        import torch
        from safetensors.torch import load_file, save_file
    except ImportError:
        run([VENV_PYTHON, "-m", "pip", "install", "safetensors", "torch", "-q"])
        import torch
        from safetensors.torch import load_file, save_file

    adapter_path = ADAPTER_DIR / "adapters.safetensors"
    if not adapter_path.exists():
        print(f"Adapter not found: {adapter_path}")
        sys.exit(1)

    tensors = load_file(str(adapter_path))
    print(f"  Loaded {len(tensors)} tensors from MLX adapter")

    # Key remapping: MLX VLM → PEFT/HuggingFace naming
    # MLX: language_model.model.layers.N.linear_attn.in_proj_qkv.lora_a
    # PEFT: base_model.model.model.layers.N.self_attn.qkv_proj.lora_A.weight
    remapped = {}
    skipped = []

    ATTN_MAP = {
        "in_proj_qkv": "self_attn.qkv_proj",
        "in_proj_a":   "self_attn.q_proj",
        "in_proj_b":   "self_attn.k_proj",
        "in_proj_z":   "self_attn.v_proj",
        "out_proj":    "self_attn.o_proj",
        "mlp.gate":    "mlp.gate_proj",
        "mlp.up":      "mlp.up_proj",
        "mlp.down":    "mlp.down_proj",
    }

    for old_key, tensor in tensors.items():
        # Strip language_model. prefix
        key = old_key
        if key.startswith("language_model."):
            key = key[len("language_model."):]

        # model.layers.N.linear_attn.X.lora_a/b
        parts = key.split(".")
        if len(parts) < 5 or parts[0] != "model" or parts[1] != "layers":
            skipped.append(old_key)
            continue

        layer_idx = parts[2]
        # linear_attn.in_proj_qkv → self_attn.qkv_proj etc.
        remainder = ".".join(parts[3:])  # e.g. linear_attn.in_proj_qkv.lora_a

        mapped_attn = None
        for mlx_name, peft_name in ATTN_MAP.items():
            if f"linear_attn.{mlx_name}.lora_a" in remainder:
                suffix = "lora_A.weight"
                mapped_attn = peft_name
                break
            elif f"linear_attn.{mlx_name}.lora_b" in remainder:
                suffix = "lora_B.weight"
                mapped_attn = peft_name
                break

        if not mapped_attn:
            skipped.append(old_key)
            continue

        new_key = f"base_model.model.model.layers.{layer_idx}.{mapped_attn}.{suffix}"

        # MLX stores: lora_a=[in, rank], lora_b=[rank, out]
        # PEFT expects: lora_A=[rank, in],  lora_B=[out, rank]
        # So both need transposing.
        t = tensor.T  # transpose always
        remapped[new_key] = t.float().contiguous()

    print(f"  Remapped: {len(remapped)} tensors")
    if skipped:
        print(f"  Skipped (vision/other): {len(skipped)}")

    # Write PEFT adapter
    PEFT_DIR.mkdir(parents=True, exist_ok=True)
    save_file(remapped, str(PEFT_DIR / "adapter_model.safetensors"))

    # Write adapter_config.json
    adapter_config = {
        "alpha_pattern": {},
        "auto_mapping": None,
        "base_model_name_or_path": BASE_HF,
        "bias": "none",
        "fan_in_fan_out": False,
        "inference_mode": True,
        "init_lora_weights": True,
        "layers_pattern": None,
        "layers_to_transform": None,
        "lora_alpha": 20.0,
        "lora_dropout": 0.0,
        "modules_to_save": None,
        "peft_type": "LORA",
        "r": 8,
        "revision": None,
        "target_modules": list(set(
            k.split(".")[-3] for k in remapped.keys()
            if "lora_A" in k
        )),
        "task_type": "CAUSAL_LM",
    }
    (PEFT_DIR / "adapter_config.json").write_text(
        json.dumps(adapter_config, indent=2)
    )
    print(f"  PEFT adapter written to: {PEFT_DIR}")


# ── Step 3: Convert PEFT adapter to GGUF ─────────────────────────────────────
def convert_to_gguf():
    print("\n" + "="*60)
    print("Step 3: Converting PEFT adapter → GGUF")
    print("="*60)

    # Find convert_lora_to_gguf.py
    convert_script = LLAMA_CPP_SRC / "convert_lora_to_gguf.py"
    if not convert_script.exists():
        print("Cloning llama.cpp source for convert script...")
        run(["git", "clone", "--depth", "1",
             "https://github.com/ggml-org/llama.cpp.git",
             str(LLAMA_CPP_SRC)])
        # Install matching gguf package
        run([VENV_PYTHON, "-m", "pip", "install",
             str(LLAMA_CPP_SRC / "gguf-py"), "-q"])

    # Use the HuggingFace cached model dir as base (convert_lora_to_gguf needs config.json)
    hf_cache = Path.home() / ".cache/huggingface/hub"
    base_model_dir = None
    for snap_dir in hf_cache.glob("models--mlx-community--Qwen3.5-35B-A3B-4bit/snapshots/*"):
        if (snap_dir / "config.json").exists():
            base_model_dir = snap_dir
            break

    if not base_model_dir:
        print("Base HF model not found in cache — should be at:")
        print("  ~/.cache/huggingface/hub/models--mlx-community--Qwen3.5-35B-A3B-4bit/")
        sys.exit(1)

    print(f"  Base model dir: {base_model_dir}")

    GGUF_DIR.mkdir(parents=True, exist_ok=True)
    log = str(LOG_DIR / "convert_lora_gguf.log")

    run([
        VENV_PYTHON, str(convert_script),
        str(PEFT_DIR),
        "--base", str(base_model_dir),
        "--outfile", str(GGUF_F16),
        "--outtype", "f16",
    ], log_file=log)

    print(f"  f16 GGUF: {GGUF_F16}")


# ── Step 4: Quantize to Q4_K_M ───────────────────────────────────────────────
def quantize():
    print("\n" + "="*60)
    print("Step 4: Quantizing f16 → Q4_K_M")
    print("="*60)

    if not LLAMA_QUANTIZE.exists():
        print(f"llama-quantize not found at {LLAMA_QUANTIZE} — skipping quantize, using f16")
        GGUF_Q4.symlink_to(GGUF_F16)
        return

    log = str(LOG_DIR / "quantize_trevor.log")
    run([str(LLAMA_QUANTIZE), str(GGUF_F16), str(GGUF_Q4), "Q4_K_M"],
        log_file=log)

    print(f"  Removing f16 intermediate...")
    GGUF_F16.unlink(missing_ok=True)
    print(f"  Q4 GGUF: {GGUF_Q4} ({GGUF_Q4.stat().st_size / 1e9:.1f}GB)")


# ── Step 5: Load into Ollama ──────────────────────────────────────────────────
def load_ollama():
    print("\n" + "="*60)
    print("Step 5: Loading into Ollama")
    print("="*60)

    gguf = GGUF_Q4 if GGUF_Q4.exists() else GGUF_F16
    modelfile = GGUF_DIR / "Modelfile.trevor"
    modelfile.write_text(f"""FROM {gguf}

PARAMETER temperature 0.7
PARAMETER top_p 0.9
PARAMETER top_k 40
PARAMETER num_ctx 32768
PARAMETER repeat_penalty 1.1

SYSTEM \"\"\"You are Trevor, an AI assistant running inside OpenClaw for Tim Wade.
You are direct, resourceful, and business-minded. You have deep knowledge of:
- Tim's trading system (Forex trading team, validator, scout, guardian)
- The jarvis AI platform and its 34 MCP servers
- Claude Code workflows and agentic development
- The boardroom agent system
You get things done without unnecessary commentary. You have opinions and share them.
When you don't know something, say so. When you see a problem, name it.\"\"\"
""")

    # Remove old version
    subprocess.run(["ollama", "rm", OLLAMA_MODEL], capture_output=True)

    run(["ollama", "create", OLLAMA_MODEL, "-f", str(modelfile)])
    print(f"\n✅ Trevor loaded into Ollama")
    subprocess.run(["ollama", "list"])


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--skip-train", action="store_true")
    parser.add_argument("--skip-export", action="store_true")
    args = parser.parse_args()

    print("\n" + "="*60)
    print("Trevor Combined 35B — Train → PEFT → GGUF → Ollama")
    print("="*60)

    if not args.skip_train:
        train()

    if not args.skip_export:
        remap_adapter()
        convert_to_gguf()
        quantize()
        load_ollama()

    print("\n✅ Done.")


if __name__ == "__main__":
    main()
