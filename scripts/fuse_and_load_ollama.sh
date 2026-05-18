#!/usr/bin/env zsh
# fuse_and_load_ollama.sh — Fuse combined_35b LoRA → GGUF → Ollama
#
# Run AFTER lora_trainer.py train combined_35b completes.
# Trading team must be stopped before running this (needs ~30GB free RAM).
#
# Steps:
#   1. Fuse LoRA adapter into full weights (mlx_lm.fuse)
#   2. Convert fused MLX weights → GGUF (llama.cpp convert)
#   3. Create Ollama Modelfile
#   4. ollama create trevor → loads into Ollama
#   5. Smoke test tool call
#
# Usage:
#   zsh ~/jarvis/scripts/fuse_and_load_ollama.sh
#   zsh ~/jarvis/scripts/fuse_and_load_ollama.sh --skip-fuse   # if already fused
#   zsh ~/jarvis/scripts/fuse_and_load_ollama.sh --skip-convert # if GGUF already exists

set -euo pipefail

VENV="~/myenv/bin/activate"
BASE_MODEL="mlx-community/Qwen3.5-35B-A3B-4bit"
ADAPTER_PATH="~/jarvis/models/adapters/combined_35b"
FUSED_DIR="~/jarvis/models/fused/combined_35b"
GGUF_DIR="~/jarvis/models/gguf"
GGUF_FILE="${GGUF_DIR}/trevor-combined-35b-q4.gguf"
MODELFILE="~/jarvis/models/gguf/Modelfile.trevor"
OLLAMA_MODEL_NAME="trevor"
LOG_DIR="~/jarvis/Logs"
LLAMA_CPP="$(which llama-quantize 2>/dev/null || echo '/opt/homebrew/bin/llama-quantize')"
CONVERT_SCRIPT="$(find /opt/homebrew -name 'convert_hf_to_gguf.py' 2>/dev/null | head -1)"

SKIP_FUSE=0
SKIP_CONVERT=0
for arg in "$@"; do
  [[ "$arg" == "--skip-fuse" ]]    && SKIP_FUSE=1
  [[ "$arg" == "--skip-convert" ]] && SKIP_CONVERT=1
done

mkdir -p "$FUSED_DIR" "$GGUF_DIR" "$LOG_DIR"

echo ""
echo "╔══════════════════════════════════════════════════════╗"
echo "║  Trevor Combined 35B — Fuse → GGUF → Ollama         ║"
echo "╚══════════════════════════════════════════════════════╝"
echo ""

source "$VENV"

# ── Step 1: Fuse LoRA adapter into full weights ───────────────────────────────
if [[ $SKIP_FUSE -eq 1 ]]; then
  echo "⏭  Skipping fuse (--skip-fuse)"
else
  echo "🔗 Step 1: Fusing LoRA adapter into full weights..."
  echo "   Base:    $BASE_MODEL"
  echo "   Adapter: $ADAPTER_PATH"
  echo "   Output:  $FUSED_DIR"
  echo ""

  if [[ ! -f "${ADAPTER_PATH}/adapters.safetensors" ]]; then
    echo "❌ Adapter not found: ${ADAPTER_PATH}/adapters.safetensors"
    echo "   Run: python3 ~/jarvis/Forex\ Trading\ Team/Source/lora_trainer.py train combined_35b"
    exit 1
  fi

  python3 -m mlx_lm.fuse \
    --model "$BASE_MODEL" \
    --adapter-path "$ADAPTER_PATH" \
    --save-path "$FUSED_DIR" \
    2>&1 | tee "${LOG_DIR}/fuse_combined_35b.log"

  echo ""
  echo "✅ Fuse complete → $FUSED_DIR"
fi

# ── Step 2: Convert fused MLX weights → GGUF ─────────────────────────────────
if [[ $SKIP_CONVERT -eq 1 ]]; then
  echo "⏭  Skipping convert (--skip-convert)"
  if [[ ! -f "$GGUF_FILE" ]]; then
    echo "❌ GGUF not found at $GGUF_FILE — cannot skip convert"
    exit 1
  fi
else
  echo "🔄 Step 2: Converting MLX weights → GGUF (Q4_K_M)..."

  if [[ -z "$CONVERT_SCRIPT" ]]; then
    echo "❌ convert_hf_to_gguf.py not found. Is llama.cpp installed?"
    echo "   brew install llama.cpp"
    exit 1
  fi

  echo "   Using: $CONVERT_SCRIPT"
  echo "   Input: $FUSED_DIR"
  echo "   Output: $GGUF_FILE"
  echo ""

  # First convert to f16 GGUF, then quantize to Q4_K_M
  GGUF_F16="${GGUF_DIR}/trevor-combined-35b-f16.gguf"

  python3 "$CONVERT_SCRIPT" \
    "$FUSED_DIR" \
    --outfile "$GGUF_F16" \
    --outtype f16 \
    2>&1 | tee "${LOG_DIR}/convert_combined_35b.log"

  echo ""
  echo "   Quantizing f16 → Q4_K_M..."

  if [[ ! -f "$LLAMA_CPP" ]]; then
    LLAMA_CPP="$(find /opt/homebrew -name 'llama-quantize' 2>/dev/null | head -1)"
  fi

  if [[ -z "$LLAMA_CPP" || ! -f "$LLAMA_CPP" ]]; then
    echo "❌ llama-quantize not found. Keeping f16 GGUF."
    GGUF_FILE="$GGUF_F16"
  else
    "$LLAMA_CPP" "$GGUF_F16" "$GGUF_FILE" Q4_K_M \
      2>&1 | tee -a "${LOG_DIR}/convert_combined_35b.log"
    echo "   Removing f16 intermediate..."
    rm -f "$GGUF_F16"
  fi

  echo ""
  echo "✅ GGUF ready → $GGUF_FILE"
  ls -lh "$GGUF_FILE"
fi

# ── Step 3: Create Ollama Modelfile ──────────────────────────────────────────
echo ""
echo "📝 Step 3: Writing Modelfile..."

cat > "$MODELFILE" << 'MODELFILE_EOF'
FROM ~/jarvis/models/gguf/trevor-combined-35b-q4.gguf

# Trevor — Combined 35B distilled model
# Trained on: Trevor sessions, Claude Code, trading team, vault knowledge,
#             boardroom agents, trade outcomes, chart analysis
# Base: Qwen3.5-35B-A3B-4bit + combined_35b LoRA adapter

PARAMETER temperature 0.7
PARAMETER top_p 0.9
PARAMETER top_k 40
PARAMETER num_ctx 32768
PARAMETER repeat_penalty 1.1

# Disable Qwen3 extended thinking for faster responses
# (enable_thinking=false equivalent via stop token)
PARAMETER stop "<think>"

SYSTEM """You are Trevor, an AI assistant running inside OpenClaw for Tim Wade.
You are direct, resourceful, and business-minded. You have deep knowledge of:
- Tim's trading system (Forex trading team, validator, scout, guardian)
- The jarvis AI platform and its 34 MCP servers
- Claude Code workflows and agentic development
- The boardroom agent system
You get things done without unnecessary commentary. You have opinions and share them.
When you don't know something, say so. When you see a problem, name it."""
MODELFILE_EOF

echo "✅ Modelfile → $MODELFILE"

# ── Step 4: Load into Ollama ──────────────────────────────────────────────────
echo ""
echo "🦙 Step 4: Loading into Ollama as '$OLLAMA_MODEL_NAME'..."

# Remove old version if exists
ollama rm "$OLLAMA_MODEL_NAME" 2>/dev/null && echo "   Removed old version" || true

ollama create "$OLLAMA_MODEL_NAME" -f "$MODELFILE" \
  2>&1 | tee "${LOG_DIR}/ollama_create_trevor.log"

echo ""
echo "✅ Model loaded into Ollama"
ollama list | grep trevor

# ── Step 5: Smoke test ───────────────────────────────────────────────────────
echo ""
echo "🧪 Step 5: Smoke test (tool call)..."

SMOKE_RESULT=$(curl -s http://localhost:11434/api/chat \
  --max-time 60 \
  -d '{
    "model": "trevor",
    "messages": [{"role":"user","content":"What pairs does our trading system watch? Keep it brief."}],
    "stream": false
  }' 2>&1)

if echo "$SMOKE_RESULT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['message']['content'][:200])" 2>/dev/null; then
  echo ""
  echo "✅ Smoke test passed"
else
  echo "⚠️  Smoke test response:"
  echo "$SMOKE_RESULT" | head -5
fi

echo ""
echo "╔══════════════════════════════════════════════════════╗"
echo "║  Done. Trevor is running in Ollama.                 ║"
echo "║                                                      ║"
echo "║  Next: point OpenClaw at ollama/trevor              ║"
echo "║  Then: distill trevor → 9B vision model             ║"
echo "╚══════════════════════════════════════════════════════╝"
echo ""
