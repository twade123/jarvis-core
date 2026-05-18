#!/usr/bin/env zsh
# MLX Model Server Manager — starts/stops/checks all boardroom MLX servers
# Single source of truth for port assignments and model mappings.
#
# Usage:
#   ./scripts/mlx_servers.sh start [seat]   # Start all or one seat
#   ./scripts/mlx_servers.sh stop  [seat]   # Stop all or one seat
#   ./scripts/mlx_servers.sh status         # Check all servers
#   ./scripts/mlx_servers.sh restart        # Stop + start all

set -uo pipefail

# ── Port & Model Mapping (canonical — 4 distinct models for genuinely different reasoning) ──
# Format: SEAT|PORT|HF_REPO|SERVER_TYPE
# server_type: lm=text-only (mlx_lm.server), vlm=vision-language (mlx_vlm.server — loads model per-request)
SEAT_CONFIG="
CRO|11500|mlx-community/Qwen3.5-9B-4bit|lm_lenient
CTO|11501|mlx-community/DeepSeek-R1-Distill-Qwen-14B-4bit|lm
CSO|11502|mlx-community/Qwen3.5-35B-A3B-4bit|vlm_with_tools
CDO|11503|mlx-community/Qwen2.5-7B-Instruct-4bit|lm
Strategy|11504|mlx-community/Qwen3-30B-A3B-4bit|lm_lenient
Ops|11505|mlx-community/Qwen2.5-1.5B-Instruct-4bit|lm
"

# ── LoRA Adapter Paths (loaded at server startup if present) ──────────────────
# Maps seat name → adapter dir. Empty string = no adapter (base model only).
# Adapters are trained by lora_trainer.py and saved here after each run.
ADAPTER_ROOT="~/jarvis/models/adapters"
typeset -A SEAT_ADAPTER
SEAT_ADAPTER["CRO"]="${ADAPTER_ROOT}/validator_35b"  # Validator LoRA on 9B (vision, chart analysis)
SEAT_ADAPTER["CSO"]="${ADAPTER_ROOT}/35b_mlx"        # v2 distilled LoRA (24,711 entries from RunPod, Apr 22 2026)
SEAT_ADAPTER["CTO"]=""   # No adapter — DeepSeek base only
SEAT_ADAPTER["CDO"]=""   # No adapter
# lm_lenient = mlx_lm with KV cache capped at 16384 tokens (RotatingKVCache)
# Prevents unbounded KV cache accumulation across requests. strict=False no longer needed (mlx_lm >=0.31.1).
LENIENT_SCRIPT="~/jarvis/scripts/mlx_lm_server_lenient.py"
# vlm_with_tools = mlx_vlm with ChatRequest patched for tool calling — vision + tools
# Use this for the CSO seat (Qwen3.5-35B) where both vision and tool calling are needed
VLM_TOOLS_SCRIPT="~/jarvis/scripts/mlx_vlm_server_with_tools.py"

# Default resident seats — chair (CSO/35B agent fleet) + boardroom CRO (9B) always-resident.
# All others (CTO/CDO/Strategy/Ops) lazy-load on demand per deliberation.
RESIDENT_SEATS="CSO CRO"

VENV="~/myenv/bin/activate"
LOG_DIR="~/jarvis/Logs/mlx"
mkdir -p "$LOG_DIR"

get_port() {
  echo "$SEAT_CONFIG" | grep "^${1}|" | cut -d'|' -f2
}

get_model() {
  echo "$SEAT_CONFIG" | grep "^${1}|" | cut -d'|' -f3
}

get_server_type() {
  echo "$SEAT_CONFIG" | grep "^${1}|" | cut -d'|' -f4
}

start_seat() {
  local seat=$1
  local port
  port=$(get_port "$seat")
  local model
  model=$(get_model "$seat")

  if [ -z "$port" ] || [ -z "$model" ]; then
    echo "❌ Unknown seat: $seat"
    return 1
  fi

  local stype
  stype=$(get_server_type "$seat")

  # Primary guard: TCP port already bound = something is serving, don't spawn another
  if lsof -i "TCP:${port}" -sTCP:LISTEN 2>/dev/null | grep -q LISTEN; then
    echo "✅ $seat already running on port $port (port bound)"
    return 0
  fi
  # Secondary guard: process already exists (catches case where process started but port not yet bound)
  if pgrep -f "mlx_.*--port ${port}" >/dev/null 2>&1; then
    echo "✅ $seat process exists on port $port"
    return 0
  fi
  # Kill any stale process of the wrong type on this port
  for bad in lm vlm; do
    if [ "$bad" != "$stype" ]; then
      local stale
      stale=$(pgrep -f "mlx_${bad}.*--port ${port}\b" 2>/dev/null || true)
      if [ -n "$stale" ]; then
        echo "   Killing stale mlx_${bad} on port $port (PID $stale)..."
        kill -9 "$stale" 2>/dev/null || true
        sleep 1
      fi
    fi
  done

  echo "🚀 Starting $seat on port $port ($model) [$stype]..."
  source "$VENV"

  if [ "$stype" = "vlm" ]; then
    # Pure VLM (vision required): mlx_vlm.server, model passed per-request
    nohup python3 -m mlx_vlm.server \
      --port "$port" \
      --host 127.0.0.1 \
      > "$LOG_DIR/${seat}.log" 2>&1 &
  elif [ "$stype" = "lm_lenient" ]; then
    # VLM weights but text-only use: loads with strict=False, enables tool calling
    local adapter_path="${SEAT_ADAPTER[$seat]:-}"
    local adapter_args=""
    if [ -n "$adapter_path" ] && [ -d "$adapter_path" ] && ls "$adapter_path"/*.safetensors >/dev/null 2>&1; then
      adapter_args="--adapter-path $adapter_path"
      echo "   🎯 Loading LoRA adapter from $adapter_path"
    fi
    nohup python3 "$LENIENT_SCRIPT" \
      --model "$model" \
      --port "$port" \
      --host 127.0.0.1 \
      --chat-template-args '{"enable_thinking":false}' \
      --prompt-cache-size 2 \
      $adapter_args \
      > "$LOG_DIR/${seat}.log" 2>&1 &
  elif [ "$stype" = "vlm_with_tools" ]; then
    # Vision + tool calling: mlx_vlm with ChatRequest patched for tools (CSO seat)
    local adapter_path="${SEAT_ADAPTER[$seat]:-}"
    local adapter_args=""
    if [ -n "$adapter_path" ] && [ -d "$adapter_path" ] && ls "$adapter_path"/*.safetensors >/dev/null 2>&1; then
      adapter_args="--adapter-path $adapter_path"
      echo "   🎯 Loading LoRA adapter from $adapter_path"
    fi
    nohup python3 "$VLM_TOOLS_SCRIPT" \
      --model "$model" \
      --port "$port" \
      --host 127.0.0.1 \
      $adapter_args \
      > "$LOG_DIR/${seat}.log" 2>&1 &
  else
    # Pure text models: standard mlx_lm.server
    nohup python3 -m mlx_lm.server \
      --model "$model" \
      --port "$port" \
      --host 127.0.0.1 \
      > "$LOG_DIR/${seat}.log" 2>&1 &
  fi

  local pid=$!
  echo "   PID=$pid, waiting for ready..."

  # Wait up to 120s for health endpoint
  local elapsed=0
  while [ $elapsed -lt 120 ]; do
    if curl -sf "http://127.0.0.1:${port}/health" >/dev/null 2>&1; then
      echo "✅ $seat ready on port $port (${elapsed}s)"
      return 0
    fi
    if ! kill -0 $pid 2>/dev/null; then
      echo "❌ $seat process died. Check $LOG_DIR/${seat}.log"
      return 1
    fi
    sleep 3
    elapsed=$((elapsed + 3))
  done

  echo "❌ $seat timed out after 120s"
  return 1
}

stop_seat() {
  local seat=$1
  local port
  port=$(get_port "$seat")

  if [ -z "$port" ]; then
    echo "❌ Unknown seat: $seat"
    return 1
  fi

  # Find mlx_lm or mlx_vlm process on this specific port
  # Pattern matches both server types without killing unrelated processes
  local pid
  pid=$(pgrep -f "mlx_(lm|vlm).*--port ${port}\b" 2>/dev/null || \
        pgrep -f "mlx_lm.*--port ${port}" 2>/dev/null || \
        pgrep -f "mlx_vlm.*--port ${port}" 2>/dev/null || true)
  if [ -n "$pid" ]; then
    kill "$pid" 2>/dev/null || true
    echo "🛑 Stopped $seat (port $port, PID $pid)"
  else
    echo "   $seat not running on port $port"
  fi
}

status_all() {
  echo "=== MLX Server Status ==="
  for seat in CRO CTO CSO CDO; do
    local port=$(get_port "$seat")
    local pid=$(lsof -ti :"${port}" 2>/dev/null || true)
    if [ -n "$pid" ]; then
      echo "  ✅ $seat  port=$port  pid=$pid"
    else
      echo "  ⬚  $seat  port=$port  (stopped)"
    fi
  done
}

# ── Main ──
action="${1:-status}"
seat="${2:-}"

case "$action" in
  start)
    if [ -n "$seat" ]; then
      start_seat "$seat"
    else
      for s in $RESIDENT_SEATS; do
        start_seat "$s"
      done
    fi
    ;;
  stop)
    if [ -n "$seat" ]; then
      stop_seat "$seat"
    else
      for s in CRO CTO CSO CDO Coder; do
        stop_seat "$s"
      done
    fi
    ;;
  restart)
    for s in $RESIDENT_SEATS; do
      stop_seat "$s"
    done
    sleep 2
    for s in $RESIDENT_SEATS; do
      start_seat "$s"
    done
    ;;
  status)
    status_all
    ;;
  *)
    echo "Usage: $0 {start|stop|restart|status} [seat]"
    exit 1
    ;;
esac
