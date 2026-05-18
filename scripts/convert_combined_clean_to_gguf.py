#!/usr/bin/env python3
"""
Convert combined_35b_clean HF float16 to GGUF for Ollama.
"""

import subprocess
import sys
from pathlib import Path

# Paths
CLEAN_MODEL = Path("~/jarvis/models/fused/combined_35b_clean")
OUTPUT_GGUF = Path("~/jarvis/models/gguf/trevor-fused-35b.gguf")

print(f"Source: {CLEAN_MODEL}")
print(f"Output: {OUTPUT_GGUF}")

# Try llama-cpp-python's convert-lora-to-gguf first
# It should work on standard HF models
cmd = [
    "convert-lora-to-gguf",
    "--model", str(CLEAN_MODEL),
    "--outfile", str(OUTPUT_GGUF),
    "--type", "f16"
]

print(f"Command: {' '.join(cmd)}")

try:
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    print(result.stdout)
    print("✓ GGUF conversion successful")
except subprocess.CalledProcessError as e:
    print(f"✗ Error: {e}")
    print(f"stderr: {e.stderr}")
    
    # Fallback: use huggingface_hub to load and convert
    print("\nTrying huggingface_hub + llama-cpp-python path...")
    sys.exit(1)
