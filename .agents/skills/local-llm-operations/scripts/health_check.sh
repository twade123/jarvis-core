#!/usr/bin/env bash
# health_check.sh — probe every local model endpoint + Kronos + Whisper
#
# Usage: bash health_check.sh

set -uo pipefail

RED=$'\033[31m'
GREEN=$'\033[32m'
YELLOW=$'\033[33m'
RESET=$'\033[0m'

probe_port() {
  local seat=$1 port=$2
  if curl -sf "http://127.0.0.1:${port}/health" >/dev/null 2>&1; then
    local models
    models=$(curl -s "http://127.0.0.1:${port}/v1/models" 2>/dev/null | python3 -c 'import sys,json;d=json.load(sys.stdin);print(",".join(m["id"] for m in d.get("data",[])))' 2>/dev/null || echo "?")
    printf "  %s✓%s %-6s port=%s  models=%s\n" "$GREEN" "$RESET" "$seat" "$port" "$models"
    return 0
  else
    printf "  %s✗%s %-6s port=%s  %s(down)%s\n" "$RED" "$RESET" "$seat" "$port" "$YELLOW" "$RESET"
    return 1
  fi
}

echo "=== MLX seats ==="
probe_port CRO   11500 || true
probe_port CTO   11501 || true
probe_port CSO   11502 || true
probe_port CDO   11503 || true
probe_port Coder 11504 || true

echo ""
echo "=== vLLM (Claude Code bridge) ==="
if curl -sf http://127.0.0.1:8000/v1/models >/dev/null 2>&1; then
  printf "  %s✓%s vLLM   port=8000\n" "$GREEN" "$RESET"
else
  printf "  %s·%s vLLM   port=8000  (not running — optional, only needed for Claude Code)\n" "$YELLOW" "$RESET"
fi

echo ""
echo "=== Kronos ==="
VENV=~/myenv/bin/activate
# shellcheck disable=SC1090
source "$VENV"
python3 <<'PY'
import sys
try:
    sys.path.insert(0, '~/Jarvis/Forex Trading Team/Source')
    sys.path.insert(0, '~/Jarvis/research/kronos')
    from tuning_config import TUNING
    model_name = TUNING.get("kronos.model_name", {}).get("value")
    print(f"  TUNING kronos.model_name = {model_name}")
    import os
    if model_name and os.path.exists(model_name):
        print(f"  \033[32m✓\033[0m model path exists")
    else:
        print(f"  \033[31m✗\033[0m model path missing: {model_name}")
    import torch
    print(f"  MPS available: {torch.backends.mps.is_available()}")
except Exception as e:
    print(f"  \033[31m✗\033[0m Kronos check failed: {e}")
PY

echo ""
echo "=== Whisper ==="
for f in small.pt medium.pt large-v3.pt whisper/base.pt; do
  p="~/Jarvis/Core/models/$f"
  if [ -f "$p" ]; then
    size=$(du -h "$p" | cut -f1)
    printf "  %s✓%s %-20s %s\n" "$GREEN" "$RESET" "$f" "$size"
  else
    printf "  %s·%s %-20s (missing)\n" "$YELLOW" "$RESET" "$f"
  fi
done

echo ""
echo "=== OpenClaw settings sanity ==="
for key in agents.defaults.contextTokens agents.defaults.compaction.reserveTokens agents.defaults.compaction.reserveTokensFloor agents.defaults.bootstrapTotalMaxChars agents.defaults.model.primary; do
  val=$(openclaw config get "$key" 2>/dev/null | head -1 || echo "?")
  printf "  %-52s = %s\n" "$key" "$val"
done

echo ""
echo "=== Vault index ==="
if [ -f ~/Jarvis/knowledge/_index.db ]; then
  files_count=$(sqlite3 ~/Jarvis/knowledge/_index.db "SELECT COUNT(*) FROM files" 2>/dev/null || echo "?")
  fts_count=$(sqlite3 ~/Jarvis/knowledge/_index.db "SELECT COUNT(*) FROM fts_content" 2>/dev/null || echo "?")
  printf "  %s✓%s _index.db  files=%s  fts_content=%s\n" "$GREEN" "$RESET" "$files_count" "$fts_count"
else
  printf "  %s✗%s _index.db not found\n" "$RED" "$RESET"
fi
