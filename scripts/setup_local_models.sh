#!/bin/bash
# Setup Local Models for Trevor Platform
# Run with: bash scripts/setup_local_models.sh
#
# This pulls the models recommended in the master plan.
# Total download: ~25-30GB. Total RAM usage when loaded: ~25GB
# Your Mac has 64GB — plenty of headroom.
#
# Models:
#   qwen2.5:7b    (~5GB)  - Fast routing/classification, board member agent
#   deepseek-r1:32b (~20GB) - Reasoning/complex tasks, CTO board member
#   llama3.3:latest (~4GB) - Alternative perspective, CRO board member
#
# After pulling, these are available via:
#   ollama/qwen2.5:7b
#   ollama/deepseek-r1:32b
#   ollama/llama3.3:latest
#
# The LLMRouter in claude_client.py automatically routes to them.

set -e

echo "🚀 Trevor Platform — Local Model Setup"
echo "========================================"
echo ""

# Check Ollama is installed
if ! command -v ollama &>/dev/null; then
    echo "❌ Ollama not found. Install from https://ollama.com"
    exit 1
fi

# Start Ollama if not running
if ! ollama list &>/dev/null 2>&1; then
    echo "Starting Ollama..."
    ollama serve &
    sleep 3
fi

echo "Current models:"
ollama list
echo ""

# Phase 1: Small routing model (fast, used for most requests)
echo "📦 Pulling qwen2.5:7b (routing/classification, ~5GB)..."
ollama pull qwen2.5:7b

# Phase 2: Reasoning model (used for complex tasks)
echo "📦 Pulling deepseek-r1:32b (reasoning/CTO, ~20GB)..."
echo "   This is the big one — may take a while..."
ollama pull deepseek-r1:32b

# Phase 3: Alternative perspective model
echo "📦 Pulling llama3.3:latest (CRO board member, ~4GB)..."
ollama pull llama3.3:latest

echo ""
echo "✅ All models pulled!"
echo ""
ollama list
echo ""
echo "Next steps:"
echo "  1. Models are now available via LLMRouter (ollama/qwen2.5:7b, etc.)"
echo "  2. Boardroom members will use these automatically"
echo "  3. Run training_data/build_training_data.py to generate fine-tuning data"
echo "  4. Fine-tune with MLX for even better performance"
