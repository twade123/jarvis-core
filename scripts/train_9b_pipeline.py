#!/usr/bin/env python3
"""
Train the 9B model on all training data.
Independent of 35B solution.
"""

from pathlib import Path
import json

# Configuration
BASE_MODEL = "Qwen3.5-9B"  # Smaller, faster
OUTPUT_ADAPTER = Path("~/jarvis/models/adapters/ta_9b")
TRAIN_DATA = Path("~/jarvis/training_data/sessions/_lora_combined_35b/train.jsonl")

print(f"=== 9B TRAINING CONFIGURATION ===")
print(f"Base model: Qwen3.5-9B")
print(f"Output adapter: {OUTPUT_ADAPTER}")
print(f"Training data: {TRAIN_DATA}")
print(f"\nThis pipeline is independent of the 35B solution.")
print(f"Will train on ALL training data, developing its own expertise.")
print(f"\nMemory usage: ~17GB (vs 35B's ~23GB peak)")

# Check if training data exists
if not TRAIN_DATA.exists():
    print(f"ERROR: Training data not found: {TRAIN_DATA}")
    exit(1)

# Load training pairs
with open(TRAIN_DATA) as f:
    lines = [json.loads(line) for line in f if line.strip()]
print(f"\nTraining pairs: {len(lines)}")

# This is a template - actual training uses PEFT + Hugging Face transformers
# with Qwen3.5-9B base model
TRAIN_CONFIG = {
    "base_model": "Qwen3.5-9B",
    "adapter_output": str(OUTPUT_ADAPTER),
    "lr": 1e-5,
    "num_epochs": 1,
    "batch_size": 2,
    "gradient_accumulation_steps": 2,
    "max_seq_len": 256,
    "num_iters": 100
}

with open(Path("~/jarvis/scripts/training_9b_config.json"), "w") as f:
    json.dump(TRAIN_CONFIG, f, indent=2)

print(f"\nConfig saved: ~/jarvis/scripts/training_9b_config.json")
print(f"Next: Run training (12-24 hours on M1 Max)")
