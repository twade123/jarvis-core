#!/bin/bash
# Fine-tune a local routing model using MLX
# Prerequisites: pip install mlx-lm
# Input: training_data/training_alpaca.jsonl (from build_training_data.py)
#
# This creates a LoRA adapter that makes qwen2.5:7b better at routing
# Jarvis requests to the correct handler.

set -e
cd "$(dirname "$0")/.."

TRAINING_DATA="training_data/training_alpaca.jsonl"
BASE_MODEL="qwen2.5-7b-mlx"
ADAPTER_DIR="models/router-adapter"
FUSED_DIR="models/router-fused"

echo "🧠 Trevor Router Fine-Tuning"
echo "============================="

if [ ! -f "$TRAINING_DATA" ]; then
    echo "❌ Training data not found. Run: python Core/build_training_data.py"
    exit 1
fi

EXAMPLES=$(wc -l < "$TRAINING_DATA")
echo "Training examples: $EXAMPLES"
echo ""

# Step 1: Convert base model to MLX format (one-time)
if [ ! -d "$BASE_MODEL" ]; then
    echo "📦 Converting Qwen2.5-7B to MLX format..."
    python -m mlx_lm.convert --hf-path Qwen/Qwen2.5-7B-Instruct --mlx-path ./$BASE_MODEL
fi

# Step 2: Split training data
echo "📊 Preparing train/valid split..."
mkdir -p training_data/split
python3 -c "
import json, random
data = [json.loads(l) for l in open('$TRAINING_DATA')]
random.shuffle(data)
split = int(len(data) * 0.9)
with open('training_data/split/train.jsonl', 'w') as f:
    for d in data[:split]: f.write(json.dumps(d) + '\n')
with open('training_data/split/valid.jsonl', 'w') as f:
    for d in data[split:]: f.write(json.dumps(d) + '\n')
print(f'Train: {split}, Valid: {len(data)-split}')
"

# Step 3: LoRA fine-tune
echo "🔧 Fine-tuning with LoRA..."
python -m mlx_lm.lora \
    --model ./$BASE_MODEL \
    --data ./training_data/split \
    --train \
    --batch-size 4 \
    --lora-layers 16 \
    --epochs 3 \
    --learning-rate 1e-4 \
    --adapter-path ./$ADAPTER_DIR

# Step 4: Fuse LoRA weights into base model
echo "🔗 Fusing LoRA adapter..."
python -m mlx_lm.fuse \
    --model ./$BASE_MODEL \
    --adapter-path ./$ADAPTER_DIR \
    --save-path ./$FUSED_DIR

# Step 5: Create Ollama model
echo "📦 Creating Ollama model: jarvis-router..."
cat > models/Modelfile << 'EOF'
FROM ./models/router-fused
PARAMETER temperature 0.1
PARAMETER num_ctx 4096
SYSTEM """You are the Jarvis intent classifier. Given a user request, determine the appropriate handler and intent. Respond in JSON: {"handler": "handler_name", "intent": "INTENT_NAME", "category": "category", "confidence": 0.0-1.0}"""
EOF

# Convert MLX to GGUF then import
python -m mlx_lm.convert --mlx-path ./$FUSED_DIR --gguf-path ./models/jarvis-router.gguf
ollama create jarvis-router -f models/Modelfile

echo ""
echo "✅ Fine-tuning complete!"
echo "Model available as: ollama/jarvis-router"
echo "Test with: ollama run jarvis-router 'check the weather in Miami'"
