#!/usr/bin/env python3
"""
Remap combined_35b_clean: split stacked switch_mlp expert tensors [256, dim, dim]
into individual experts so convert_hf_to_gguf.py can process them.

switch_mlp.{down,gate,up}_proj.weight [256, in, out]
  -> mlp.experts.{0..255}.{down,gate,up}_proj.weight [in, out]

Run time: ~30-60 min (reads/writes 65GB of safetensors)
"""

import json
import re
import shutil
import struct
import sys
import gc
from pathlib import Path
import numpy as np

try:
    from safetensors.numpy import save_file, load_file
    from safetensors import safe_open
except ImportError:
    print("Installing safetensors...")
    import subprocess
    subprocess.run([sys.executable, "-m", "pip", "install", "safetensors"], check=True)
    from safetensors.numpy import save_file, load_file
    from safetensors import safe_open

SOURCE = Path("~/jarvis/models/fused/combined_35b_clean")
DEST = Path("~/jarvis/models/fused/combined_35b_remapped")
DEST.mkdir(parents=True, exist_ok=True)

print(f"Source: {SOURCE}")
print(f"Dest:   {DEST}")

# Copy non-weight files
for f in SOURCE.glob("*"):
    if not f.suffix == ".safetensors":
        shutil.copy2(f, DEST / f.name)
        print(f"Copied: {f.name}")

# Load the weight map
with open(SOURCE / "model.safetensors.index.json") as f:
    index = json.load(f)

weight_map = index["weight_map"]
all_keys = sorted(weight_map.keys())

# Figure out which shards exist
shards = sorted(set(weight_map.values()))
print(f"\nProcessing {len(shards)} shards, {len(all_keys)} tensors total")

new_weight_map = {}
new_metadata = {"total_size": 0}
shard_tensors = {}  # shard_name -> {tensor_name: array}

for shard_idx, shard_name in enumerate(shards):
    print(f"\n[{shard_idx+1}/{len(shards)}] Processing {shard_name}...")
    shard_path = SOURCE / shard_name
    
    # Load all tensors from this shard
    tensors_in_shard = {k: v for k, v in weight_map.items() if v == shard_name}
    print(f"  {len(tensors_in_shard)} tensors")
    
    new_tensors = {}
    
    with safe_open(shard_path, framework="numpy") as f:
        for name in tensors_in_shard:
            tensor = f.get_tensor(name)
            
            # Check if it's a stacked switch_mlp expert tensor
            if "switch_mlp" in name and tensor.ndim == 3 and tensor.shape[0] == 256:
                # Shape: [256, in_dim, out_dim] -> split into 256 experts
                proj_type = None
                if "down_proj" in name:
                    proj_type = "down_proj"
                elif "gate_proj" in name:
                    proj_type = "gate_proj"
                elif "up_proj" in name:
                    proj_type = "up_proj"
                
                if proj_type:
                    # Extract layer number
                    m = re.search(r"layers\.(\d+)", name)
                    if m:
                        layer_n = m.group(1)
                        print(f"  Splitting {name} [{tensor.shape}] -> 256 experts")
                        
                        for expert_i in range(256):
                            new_name = f"model.layers.{layer_n}.mlp.experts.{expert_i}.{proj_type}.weight"
                            # Each expert: [in_dim, out_dim]
                            new_tensors[new_name] = tensor[expert_i]
                        continue
            
            # All other tensors pass through unchanged
            new_tensors[name] = tensor
    
    # Save this shard
    out_shard_name = shard_name  # Keep same shard filenames
    out_shard_path = DEST / out_shard_name
    print(f"  Saving {len(new_tensors)} tensors to {out_shard_name}...")
    save_file(new_tensors, str(out_shard_path))
    
    # Update weight map
    for name in new_tensors:
        new_weight_map[name] = out_shard_name
    
    # Free memory
    del new_tensors
    gc.collect()
    print(f"  Done shard {shard_idx+1}")

# Write new index
new_index = {
    "metadata": {"total_size": sum(
        (DEST / s).stat().st_size for s in shards
    )},
    "weight_map": new_weight_map
}
with open(DEST / "model.safetensors.index.json", "w") as f:
    json.dump(new_index, f, indent=2)

print(f"\n✓ Done! Remapped model saved to {DEST}")
print(f"  Total tensors: {len(new_weight_map)}")
print(f"  Original:      {len(weight_map)}")
print(f"\nNext: python3 /opt/homebrew/bin/convert_hf_to_gguf.py {DEST} --outfile trevor-fused-35b-f16.gguf --outtype f16")
