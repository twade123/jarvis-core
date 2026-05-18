#!/usr/bin/env bash
# Claude Code → Local 35B (Qwen3.5-35B-A3B with Trevor LoRA)
# Usage: claude_local.sh [any claude args]
#   e.g. claude_local.sh
#        claude_local.sh --print "explain this"
#
# Requires CSO seat running: ~/jarvis/scripts/mlx_servers.sh start CSO

PORT=11502
ADAPTER_PATH="$HOME/jarvis/models/adapters/trevor_35b"

# Verify server is up
if ! curl -sf "http://127.0.0.1:${PORT}/health" >/dev/null 2>&1; then
    echo "⚠️  CSO server not running on port $PORT"
    echo "Start it with: ~/jarvis/scripts/mlx_servers.sh start CSO"
    exit 1
fi

export ANTHROPIC_BASE_URL="http://127.0.0.1:${PORT}/v1"
export ANTHROPIC_API_KEY="local"

# The server advertises its model name — use it
MODEL_ID=$(curl -sf "http://127.0.0.1:${PORT}/v1/models" | python3 -c "
import sys,json
d=json.load(sys.stdin)
models = d.get('data',[])
print(models[0]['id'] if models else 'local')
" 2>/dev/null || echo "local")

echo "⚡ Claude Code → Local 35B ($MODEL_ID) on port $PORT"
if [ -f "$ADAPTER_PATH/adapters.safetensors" ]; then
    echo "   LoRA adapter: $ADAPTER_PATH ✅"
fi
echo ""

exec /opt/homebrew/bin/claude --model "$MODEL_ID" "$@"
