#!/usr/bin/env bash
# swap_trained_model.sh — update every pointer when deploying a new trained model.
#
# The 35B has pointers scattered across:
#   1. scripts/mlx_servers.sh                (SEAT_CONFIG CSO line)
#   2. ~/.openclaw/openclaw.json             (models.providers.mlx.models[0].id)
#   3. ~/.openclaw/openclaw.json             (agents.defaults.model.primary)
#   4. ~/.openclaw/openclaw.json             (agents.defaults.subagents.model.primary)
#   5. ~/.openclaw/openclaw.json             (agents.defaults.models.<key>)
#
# This script shows the diff and applies on explicit approval.
#
# Usage:
#   bash swap_trained_model.sh --model 35b --path ~/Jarvis/models/mlx/qwen3.5-35b-jarvis-v2-4bit
#   bash swap_trained_model.sh --model 9b  --path ~/Jarvis/models/mlx/qwen3.5-9b-jarvis-v2-4bit
#   bash swap_trained_model.sh --model 35b --adapter ~/jarvis/models/adapters/combined_35b_v2
#
# Requires explicit confirmation before writing.

set -euo pipefail

MODEL=""
NEW_PATH=""
NEW_ADAPTER=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --model)   MODEL="$2"; shift 2 ;;
    --path)    NEW_PATH="$2"; shift 2 ;;
    --adapter) NEW_ADAPTER="$2"; shift 2 ;;
    *) echo "Unknown arg: $1" >&2; exit 2 ;;
  esac
done

if [[ -z "$MODEL" ]]; then
  echo "--model required (35b or 9b)" >&2
  exit 2
fi
if [[ -z "$NEW_PATH" && -z "$NEW_ADAPTER" ]]; then
  echo "--path (fully-merged MLX model) or --adapter (LoRA adapter dir) required" >&2
  exit 2
fi

case "$MODEL" in
  35b) SEAT="CSO"; PORT=11502 ;;
  9b)  SEAT="CRO"; PORT=11500 ;;
  *)   echo "--model must be 35b or 9b" >&2; exit 2 ;;
esac

MLX_SERVERS_SH="~/Jarvis/scripts/mlx_servers.sh"
OPENCLAW_JSON="~/.openclaw/openclaw.json"

echo "=== swap_trained_model ==="
echo "  model        = $MODEL"
echo "  seat         = $SEAT  (port $PORT)"
[[ -n "$NEW_PATH" ]] && echo "  new model    = $NEW_PATH"
[[ -n "$NEW_ADAPTER" ]] && echo "  new adapter  = $NEW_ADAPTER"
echo ""

# --- Sanity: paths exist ---
if [[ -n "$NEW_PATH" ]] && [[ ! -d "$NEW_PATH" ]]; then
  echo "ERROR: new model path does not exist: $NEW_PATH" >&2
  exit 1
fi
if [[ -n "$NEW_ADAPTER" ]] && [[ ! -d "$NEW_ADAPTER" ]]; then
  echo "ERROR: new adapter path does not exist: $NEW_ADAPTER" >&2
  exit 1
fi

# --- Current state ---
echo "--- Current state ---"
echo "mlx_servers.sh CSO/CRO line:"
grep -E "^${SEAT}\|" "$MLX_SERVERS_SH" || true
echo ""
if [[ "$MODEL" == "35b" ]]; then
  CURRENT_ID=$(openclaw config get agents.defaults.model.primary 2>/dev/null | head -1 || echo "?")
  echo "openclaw primary model: $CURRENT_ID"
fi
echo ""

# --- Propose changes ---
echo "--- Proposed changes ---"
if [[ -n "$NEW_PATH" ]]; then
  echo "1. mlx_servers.sh SEAT_CONFIG ${SEAT} line → model path becomes: $NEW_PATH"
  if [[ "$MODEL" == "35b" ]]; then
    echo "2. openclaw.json models.providers.mlx.models[0].id → $NEW_PATH"
    echo "3. openclaw.json agents.defaults.model.primary → mlx/$NEW_PATH"
    echo "4. openclaw.json agents.defaults.subagents.model.primary → mlx/$NEW_PATH"
    echo "5. openclaw.json agents.defaults.models: rename key to mlx/$NEW_PATH (preserve params)"
  fi
fi
if [[ -n "$NEW_ADAPTER" ]]; then
  echo "1. mlx_servers.sh SEAT_ADAPTER[${SEAT}] → $NEW_ADAPTER"
fi
echo ""

# --- Require confirmation ---
read -r -p "Apply these changes? (type 'yes' to confirm): " confirm
if [[ "$confirm" != "yes" ]]; then
  echo "Aborted. No files modified."
  exit 0
fi

# --- Backup ---
TS=$(date +%Y%m%d-%H%M%S)
cp "$MLX_SERVERS_SH"  "${MLX_SERVERS_SH}.bak.${TS}"
cp "$OPENCLAW_JSON"   "${OPENCLAW_JSON}.bak.${TS}"
echo "  Backups: ${MLX_SERVERS_SH}.bak.${TS}, ${OPENCLAW_JSON}.bak.${TS}"

# --- Apply: mlx_servers.sh ---
if [[ -n "$NEW_PATH" ]]; then
  python3 <<PY
import re, pathlib
p = pathlib.Path("$MLX_SERVERS_SH")
text = p.read_text()
pattern = re.compile(rf"^(${SEAT}\|${PORT}\|)[^|]+(\|.+)$", re.MULTILINE)
new_text, n = pattern.subn(rf"\g<1>${NEW_PATH}\g<2>", text)
if n != 1:
    raise SystemExit(f"ERROR: expected 1 substitution in SEAT_CONFIG ${SEAT}, got {n}")
p.write_text(new_text)
print(f"  ✓ mlx_servers.sh updated ({n} line)")
PY
fi

if [[ -n "$NEW_ADAPTER" ]]; then
  python3 <<PY
import re, pathlib
p = pathlib.Path("$MLX_SERVERS_SH")
text = p.read_text()
pattern = re.compile(rf'^(SEAT_ADAPTER\["${SEAT}"\]=")[^"]*("[^\n]*)$', re.MULTILINE)
new_text, n = pattern.subn(rf'\g<1>${NEW_ADAPTER}\g<2>', text)
if n != 1:
    raise SystemExit(f"ERROR: expected 1 substitution in SEAT_ADAPTER ${SEAT}, got {n}")
p.write_text(new_text)
print(f"  ✓ SEAT_ADAPTER[${SEAT}] updated")
PY
fi

# --- Apply: openclaw.json (35B only currently — 9B doesn't go through OpenClaw directly) ---
if [[ "$MODEL" == "35b" && -n "$NEW_PATH" ]]; then
  python3 <<PY
import json, pathlib, re
p = pathlib.Path("$OPENCLAW_JSON")
raw = p.read_text()
# OpenClaw uses json5; strip trailing commas for strict parse
cleaned = re.sub(r',(\s*[}\]])', r'\1', raw)
cfg = json.loads(cleaned)

new_id = "$NEW_PATH"
new_primary = f"mlx/{new_id}"

# 1. models.providers.mlx.models[0].id
cfg["models"]["providers"]["mlx"]["models"][0]["id"] = new_id
# 2. agents.defaults.model.primary
old_primary = cfg["agents"]["defaults"]["model"]["primary"]
cfg["agents"]["defaults"]["model"]["primary"] = new_primary
# 3. agents.defaults.subagents.model.primary
cfg["agents"]["defaults"]["subagents"]["model"]["primary"] = new_primary
# 4. Rename models key
models = cfg["agents"]["defaults"]["models"]
if old_primary in models:
    models[new_primary] = models.pop(old_primary)

# Write back (lose json5 trailing commas, but OpenClaw is fine with strict json output)
p.write_text(json.dumps(cfg, indent=2))
print(f"  ✓ openclaw.json updated (id + primary + subagents.primary + models key)")
PY
fi

echo ""
echo "--- Done. Next steps: ---"
echo "  1. bash ~/Jarvis/scripts/mlx_servers.sh restart"
echo "  2. bash $(dirname "$0")/health_check.sh"
echo "  3. python3 $(dirname "$0")/tool_call_smoke_test.py --endpoint openai --port $PORT"
echo ""
echo "To rollback: restore from ${MLX_SERVERS_SH}.bak.${TS} and ${OPENCLAW_JSON}.bak.${TS}"
