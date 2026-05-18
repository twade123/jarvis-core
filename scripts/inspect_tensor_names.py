#!/usr/bin/env python3
"""
Remap combined_35b_clean tensor names from MLX-fused format to HF format
expected by convert_hf_to_gguf.py.

The issue: MLX fused model uses 'switch_mlp.{down,gate,up}_proj' for MoE experts
but llama.cpp converter expects 'mlp.experts.{n}.{down,gate,up}_proj' format.
"""

import json
import re
import shutil
from pathlib import Path

SOURCE = Path("~/jarvis/models/fused/combined_35b_clean")
DEST = Path("~/jarvis/models/fused/combined_35b_remapped")

DEST.mkdir(parents=True, exist_ok=True)

# First inspect what tensor names actually exist
print("=== INSPECTING TENSOR NAMES ===")
index_file = SOURCE / "model.safetensors.index.json"
with open(index_file) as f:
    index = json.load(f)

weight_map = index["weight_map"]
all_keys = sorted(weight_map.keys())

# Categorize them
switch_mlp_keys = [k for k in all_keys if "switch_mlp" in k]
regular_ffn_keys = [k for k in all_keys if "mlp" in k and "switch_mlp" not in k]

print(f"\nTotal tensors: {len(all_keys)}")
print(f"switch_mlp tensors: {len(switch_mlp_keys)}")
print(f"Regular MLP tensors: {len(regular_ffn_keys)}")

print("\n=== SAMPLE switch_mlp KEYS (first 10) ===")
for k in switch_mlp_keys[:10]:
    print(f"  {k}")

print("\n=== SAMPLE regular MLP KEYS (first 10) ===")
for k in regular_ffn_keys[:10]:
    print(f"  {k}")

# Check what the converter actually needs - look at _LinearAttentionVReorderBase
# Expected format per convert_hf_to_gguf.py:
# model.layers.{n}.mlp.experts.{i}.gate_proj.weight -> ffn_gate_exps
# model.layers.{n}.mlp.experts.{i}.down_proj.weight -> ffn_down_exps  
# model.layers.{n}.mlp.experts.{i}.up_proj.weight -> ffn_up_exps
# model.layers.{n}.mlp.switch_mlp.gate_proj.weight -> UNKNOWN (causes error)

print("\n=== ANALYZING SWITCH_MLP STRUCTURE ===")
# See if switch_mlp is stacked or per-expert
sample = switch_mlp_keys[0] if switch_mlp_keys else None
if sample:
    print(f"Sample: {sample}")
    # Get the shape info from safetensors
    import struct
    shard = weight_map[sample]
    shard_path = SOURCE / shard
    
    # Read safetensors header to get shape
    with open(shard_path, "rb") as f:
        header_size = struct.unpack("<Q", f.read(8))[0]
        header = json.loads(f.read(header_size).decode("utf-8"))
    
    # Find our tensor
    if sample in header:
        info = header[sample]
        print(f"Shape: {info.get('shape', 'unknown')}")
        print(f"dtype: {info.get('dtype', 'unknown')}")
    
    # Sample all unique switch_mlp patterns
    patterns = set()
    for k in switch_mlp_keys:
        # Extract pattern: replace layer number with {n}
        pat = re.sub(r'layers\.\d+', 'layers.{n}', k)
        patterns.add(pat)
    
    print(f"\nUnique switch_mlp patterns ({len(patterns)}):")
    for p in sorted(patterns):
        print(f"  {p}")
