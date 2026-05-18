#!/usr/bin/env python3
"""
mlx_to_gguf.py — Convert MLX fused model to GGUF for Ollama.

The MLX fused model has:
  1. language_model. prefix on all weights
  2. MLX quantization metadata (.biases, .scales alongside .weight)
  3. Weights stored as int4/uint32 packed format

This script:
  1. Loads each shard via mlx (handles uint32)
  2. Dequantizes int4 weights back to float16 using the scales/biases
  3. Strips language_model. prefix
  4. Skips .biases and .scales (quantization metadata, not needed for GGUF)
  5. Writes clean float16 safetensors with corrected index
  6. Runs convert_hf_to_gguf.py on the clean output
  7. Quantizes to Q4_K_M with llama-quantize

Usage:
  python3 mlx_to_gguf.py [--skip-deq] [--skip-convert] [--skip-quant]
"""

import argparse
import gc
import json
import os
import subprocess
import sys
from pathlib import Path

import mlx.core as mx

FUSED_DIR   = Path.home() / "jarvis/models/fused/combined_35b"
CLEAN_DIR   = Path.home() / "jarvis/models/fused/combined_35b_clean"
GGUF_DIR    = Path.home() / "jarvis/models/gguf"
GGUF_F16    = GGUF_DIR / "trevor-35b-f16.gguf"
GGUF_Q4     = GGUF_DIR / "trevor-35b-q4.gguf"
CONVERT     = Path("/tmp/llama_cpp_src/convert_hf_to_gguf.py")
QUANTIZE    = Path("/opt/homebrew/bin/llama-quantize")
VENV_PY     = Path("~/myenv/bin/python3")
LOG_DIR     = Path.home() / "jarvis/Logs"


def dequantize_mlx(packed: mx.array, scales: mx.array, biases: mx.array) -> mx.array:
    """
    Dequantize MLX int4 packed weights back to float16.
    MLX packs 2x int4 per uint8, with per-group scales and biases.
    Uses mlx.core.dequantize which handles the MLX quantization format natively.
    """
    try:
        # mlx.core.dequantize(w, scales, biases, group_size, bits)
        return mx.dequantize(packed, scales, biases, group_size=64, bits=4)
    except Exception as e:
        print(f"    dequantize failed: {e} — returning scales as proxy")
        return scales.astype(mx.float16)


def process_shard(shard_path: Path, key_pairs: list, out_path: Path,
                  all_tensors_in_shard: dict) -> dict:
    """Load shard, dequantize, remap keys, save clean float16 shard."""
    import numpy as np
    from safetensors.numpy import save_file

    print(f"  Loading {shard_path.name}...")
    raw = dict(mx.load(str(shard_path)))

    result = {}

    # Group keys by base name (strip .weight/.biases/.scales)
    base_names = {}
    for old_key in key_pairs:
        new_key = old_key.replace("language_model.model.", "model.") \
                         .replace("language_model.lm_head", "lm_head")
        base = old_key.rsplit(".", 1)[0]  # strip .weight/.biases/.scales
        base_names.setdefault(base, {})[old_key.split(".")[-1]] = (old_key, new_key)

    for base, parts in base_names.items():
        if "weight" not in parts:
            continue  # skip if no weight

        old_w_key, new_w_key = parts["weight"]
        if old_w_key not in raw:
            continue

        w = raw[old_w_key]
        suffix = new_w_key.split(".")[-1]

        # Check if this is a quantized weight (has matching scales)
        old_s_key = base + ".scales"
        old_b_key = base + ".biases"

        if old_s_key in raw and old_b_key in raw:
            # Dequantize int4 → float16
            scales = raw[old_s_key]
            biases = raw[old_b_key]
            print(f"    Dequantizing {new_w_key} {w.shape} → float16")
            w = dequantize_mlx(w, scales, biases)

        # Convert to numpy float16
        arr = np.array(w.astype(mx.float16), dtype=np.float16)
        result[new_w_key] = arr

    # Catch any remaining non-quantized tensors (norms, A_log, dt_bias, conv1d, etc.)
    for old_key in key_pairs:
        new_key = old_key.replace("language_model.model.", "model.") \
                         .replace("language_model.lm_head", "lm_head")
        suffix = old_key.split(".")[-1]
        if suffix in ("biases", "scales"):
            continue  # skip quant metadata
        if new_key in result:
            continue  # already processed
        if old_key not in raw:
            continue
        t = raw[old_key]
        # Skip packed uint types — they need dequant (already handled above via base_names)
        if t.dtype in (mx.uint8, mx.uint32, mx.uint16):
            print(f"    WARNING: skipping packed tensor {new_key} dtype={t.dtype}")
            continue
        arr = np.array(t.astype(mx.float16), dtype=np.float16)
        result[new_key] = arr

    print(f"    Writing {len(result)} tensors → {out_path.name}")
    save_file(result, str(out_path))

    del raw
    gc.collect()

    return {new_k: out_path.name for new_k in result}


def step1_dequantize():
    """Strip language_model prefix, dequantize int4 → fp16, write clean shards."""
    print("\n" + "="*60)
    print("Step 1: Dequantize MLX int4 → clean float16 safetensors")
    print("="*60)

    import shutil
    CLEAN_DIR.mkdir(parents=True, exist_ok=True)

    # Copy config/tokenizer files
    for f in FUSED_DIR.glob("*"):
        if not f.name.endswith(".safetensors") and f.name != "model.safetensors.index.json":
            shutil.copy2(f, CLEAN_DIR / f.name)

    # Load index
    idx = json.load(open(FUSED_DIR / "model.safetensors.index.json"))
    weight_map = idx["weight_map"]

    # Skip vision and quant metadata tensors, remap keys
    SKIP_SUFFIXES = {"biases", "scales"}
    SKIP_KEYS = {"language_model.model.embed_tokens.biases"}

    # Group by shard
    shard_keys: dict = {}
    new_weight_map = {}

    for old_key, shard in weight_map.items():
        if old_key in SKIP_KEYS:
            continue
        suffix = old_key.split(".")[-1]
        if suffix in SKIP_SUFFIXES:
            continue  # quant metadata — not in output
        shard_keys.setdefault(shard, []).append(old_key)

    # Process each shard
    all_new_map = {}
    for shard_file, keys in sorted(shard_keys.items()):
        shard_path = FUSED_DIR / shard_file
        out_path = CLEAN_DIR / shard_file
        new_map = process_shard(shard_path, keys, out_path, {})
        all_new_map.update(new_map)

    # Write new index
    new_idx = {"metadata": {"format": "pt"}, "weight_map": all_new_map}
    json.dump(new_idx, open(CLEAN_DIR / "model.safetensors.index.json", "w"), indent=2)
    print(f"\nClean model written to: {CLEAN_DIR}")


def step1b_split_experts():
    """
    Split stacked MoE expert tensors into numbered experts.

    MLX stacks all experts: switch_mlp.gate_proj.weight [256, 512, 2048]
    Converter expects:      mlp.experts.0.gate_proj.weight [512, 2048]
                            mlp.experts.1.gate_proj.weight [512, 2048] ...

    Also renames:
    - shared_expert_gate.weight [1, 2048] → mlp.gate.weight [2048]  (router)
    - shared_expert.X           → shared_expert.X (already correct)
    """
    import shutil
    from safetensors.numpy import load_file, save_file

    print("\n" + "="*60)
    print("Step 1b: Split stacked MoE experts into numbered tensors")
    print("="*60)

    SPLIT_DIR = Path.home() / "jarvis/models/fused/combined_35b_split"
    SPLIT_DIR.mkdir(parents=True, exist_ok=True)

    # Copy config/tokenizer
    for f in CLEAN_DIR.glob("*"):
        if not f.name.endswith(".safetensors") and f.name != "model.safetensors.index.json":
            shutil.copy2(f, SPLIT_DIR / f.name)

    idx = json.load(open(CLEAN_DIR / "model.safetensors.index.json"))
    weight_map = idx["weight_map"]

    # Build per-shard plan
    shard_keys: dict = {}
    for key, shard in weight_map.items():
        shard_keys.setdefault(shard, []).append(key)

    new_weight_map = {}
    shard_counter = 0

    for shard_file, keys in sorted(shard_keys.items()):
        print(f"  Processing {shard_file}...")
        tensors = load_file(str(CLEAN_DIR / shard_file))
        out = {}

        for key in keys:
            t = tensors[key]

            # switch_mlp → split into numbered experts
            if "switch_mlp." in key:
                # key: model.layers.N.mlp.switch_mlp.gate_proj.weight
                # out: model.layers.N.mlp.experts.E.gate_proj.weight
                proj = key.split("switch_mlp.")[-1]  # gate_proj.weight
                prefix = key.split(".mlp.switch_mlp.")[0]  # model.layers.N
                n_experts = t.shape[0]
                for e in range(n_experts):
                    new_key = f"{prefix}.mlp.experts.{e}.{proj}"
                    out[new_key] = t[e]
                    new_weight_map[new_key] = shard_file
                continue

            # shared_expert_gate — keep as-is, converter maps it to FFN_GATE_INP_SHEXP
            # Do NOT rename to mlp.gate — that would overwrite the router

            # Everything else passes through
            out[key] = t
            new_weight_map[key] = shard_file

        print(f"    {len(tensors)} in → {len(out)} out")
        save_file(out, str(SPLIT_DIR / shard_file))
        del tensors, out
        gc.collect()

    # Write new index
    new_idx = {"metadata": {"format": "pt"}, "weight_map": new_weight_map}
    json.dump(new_idx, open(SPLIT_DIR / "model.safetensors.index.json", "w"), indent=2)
    print(f"Split model written to: {SPLIT_DIR}")

    # Update module-level CLEAN_DIR so step2 uses split output
    import sys
    mod = sys.modules[__name__]
    mod.CLEAN_DIR = SPLIT_DIR


def step2_convert():
    """Run convert_hf_to_gguf.py on the clean model."""
    print("\n" + "="*60)
    print("Step 2: Convert to GGUF (f16)")
    print("="*60)

    if not CONVERT.exists():
        print(f"Cloning llama.cpp for convert script...")
        subprocess.run(["git", "clone", "--depth", "1",
                        "https://github.com/ggml-org/llama.cpp.git",
                        str(CONVERT.parent)], check=True)
        subprocess.run([str(VENV_PY), "-m", "pip", "install",
                        str(CONVERT.parent / "gguf-py"), "-q"], check=True)

    GGUF_DIR.mkdir(parents=True, exist_ok=True)
    log = LOG_DIR / "convert_clean_gguf.log"
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    print(f"Log: {log}")
    cmd = [str(VENV_PY), str(CONVERT),
           str(CLEAN_DIR),
           "--outfile", str(GGUF_F16),
           "--outtype", "f16"]
    print(f"$ {' '.join(cmd)}")

    with open(log, "w") as lf:
        result = subprocess.run(cmd, stdout=lf, stderr=subprocess.STDOUT)

    if result.returncode != 0:
        print(f"FAILED — check {log}")
        # Show last 20 lines
        lines = open(log).readlines()
        print("".join(lines[-20:]))
        sys.exit(1)

    print(f"GGUF f16: {GGUF_F16} ({GGUF_F16.stat().st_size / 1e9:.1f}GB)")


def step3_quantize():
    """Quantize f16 GGUF → Q4_K_M."""
    print("\n" + "="*60)
    print("Step 3: Quantize f16 → Q4_K_M")
    print("="*60)

    if not QUANTIZE.exists():
        print(f"llama-quantize not found at {QUANTIZE}")
        print("Run: brew install llama.cpp")
        return

    log = LOG_DIR / "quantize_trevor.log"
    cmd = [str(QUANTIZE), str(GGUF_F16), str(GGUF_Q4), "Q4_K_M"]
    print(f"$ {' '.join(cmd)}")

    with open(log, "w") as lf:
        result = subprocess.run(cmd, stdout=lf, stderr=subprocess.STDOUT)

    if result.returncode != 0:
        print(f"Quantize failed — check {log}")
        lines = open(log).readlines()
        print("".join(lines[-10:]))
        return

    print(f"Q4 GGUF: {GGUF_Q4} ({GGUF_Q4.stat().st_size / 1e9:.1f}GB)")
    GGUF_F16.unlink(missing_ok=True)
    print("Removed f16 intermediate.")


def step4_ollama():
    """Load into Ollama."""
    print("\n" + "="*60)
    print("Step 4: Load into Ollama")
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
You are direct, resourceful, and business-minded. Deep knowledge of Tim's forex
trading system (validator, scout, guardian, EMA fan), jarvis AI platform,
Claude Code workflows, and boardroom agents.
Get to the point. Give clear decisions — APPROVE/REJECT/WAIT. No preamble.\"\"\"
""")

    subprocess.run(["ollama", "rm", "trevor"], capture_output=True)
    result = subprocess.run(["ollama", "create", "trevor", "-f", str(modelfile)])
    if result.returncode == 0:
        print("✅ Trevor loaded into Ollama")
        subprocess.run(["ollama", "list"])
    else:
        print("Ollama create failed")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--skip-deq",     action="store_true", help="Skip dequantize step")
    parser.add_argument("--skip-convert", action="store_true", help="Skip GGUF convert step")
    parser.add_argument("--skip-quant",   action="store_true", help="Skip Q4 quantize step")
    parser.add_argument("--skip-ollama",  action="store_true", help="Skip Ollama load step")
    args = parser.parse_args()

    if not args.skip_deq:
        step1_dequantize()
    step1b_split_experts()
    if not args.skip_convert:
        step2_convert()
    if not args.skip_quant:
        step3_quantize()
    if not args.skip_ollama:
        step4_ollama()

    print("\n✅ Done.")


if __name__ == "__main__":
    main()
