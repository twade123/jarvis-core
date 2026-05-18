# mlx_servers.sh internals

Deep walkthrough of the launcher script `~/Jarvis/scripts/mlx_servers.sh`. Useful when adding a new seat, debugging why a seat won't start, or planning the update to match the new `seat_registry.py` (see boardroom divergence flag).

## Anatomy

243 lines, pure zsh, no Python. Four functions:
- `start_seat <seat>` — launch a specific seat's server
- `stop_seat <seat>` — kill a specific seat's server
- `status_all` — list all seats with ✓ or ⬚
- Main — dispatch on `$1` (action) and `$2` (optional seat)

## Configuration: `SEAT_CONFIG`

Single authoritative map at the top of the file:

```zsh
SEAT_CONFIG="
CRO|11500|mlx-community/Qwen3.5-9B-4bit|lm_lenient
CTO|11501|mlx-community/DeepSeek-R1-Distill-Qwen-14B-4bit|lm
CSO|11502|mlx-community/Qwen3.5-35B-A3B-4bit|lm_lenient
CDO|11503|mlx-community/Qwen2.5-7B-Instruct-4bit|lm
Coder|11504|mlx-community/Qwen2.5-Coder-32B-Instruct-4bit|lm
"
```

Format: `SEAT_NAME|PORT|HF_REPO|SERVER_TYPE` (one per line, tab/pipe-separated).

**⚠️ Divergence as of 2026-04-22**: this no longer matches `Handler/seat_registry.py`. The registry was updated to:
- Port 11504 → Qwen3-30B-A3B (for strategy seats D)
- Port 11505 → Qwen2.5-1.5B (for ops seats F)

`mlx_servers.sh` needs corresponding update. See `collective/models/boardroom-seat-mapping.md`.

## Server type dispatch

```zsh
case "$stype" in
  lm)              # stock mlx_lm.server — text-only, no adapter flags
  lm_lenient)      # scripts/mlx_lm_server_lenient.py — KV cap + adapter support
  vlm)             # mlx_vlm.server — pure vision, per-request model
  vlm_with_tools)  # scripts/mlx_vlm_server_with_tools.py — vision + tool calling
esac
```

Currently all 5 defined seats use `lm` or `lm_lenient`. `vlm_with_tools` is available if the CSO seat ever switches to native VLM serving (doesn't today — 35B is on `lm_lenient`).

## Adapter loading

```zsh
typeset -A SEAT_ADAPTER
SEAT_ADAPTER["CRO"]="${ADAPTER_ROOT}/validator_35b"
SEAT_ADAPTER["CSO"]="${ADAPTER_ROOT}/combined_35b"
SEAT_ADAPTER["CTO"]=""
SEAT_ADAPTER["CDO"]=""
```

Per-seat adapter path. Empty = base only. Script checks that `.safetensors` files exist before passing `--adapter-path`:

```zsh
if [ -n "$adapter_path" ] && [ -d "$adapter_path" ] && ls "$adapter_path"/*.safetensors >/dev/null 2>&1; then
  adapter_args="--adapter-path $adapter_path"
  echo "   🎯 Loading LoRA adapter from $adapter_path"
fi
```

## Stale-process guards (why restarts are reliable)

### Guard 1 — TCP port check
```zsh
if lsof -i "TCP:${port}" -sTCP:LISTEN 2>/dev/null | grep -q LISTEN; then
  echo "✅ $seat already running on port $port (port bound)"
  return 0
fi
```

If something is LISTENing on the port, don't spawn. Handles the case where a server is running but `pgrep` wouldn't match (e.g., manual launch without the expected process name).

### Guard 2 — Process name check
```zsh
if pgrep -f "mlx_.*--port ${port}" >/dev/null 2>&1; then
  echo "✅ $seat process exists on port $port"
  return 0
fi
```

Catches the case where process exists but port isn't bound yet (slow startup).

### Guard 3 — Wrong-server-type kill
```zsh
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
```

If port 11502 had `mlx_lm` running but you want to switch to `mlx_vlm`, this finds the old process of the wrong type and kills it with SIGKILL. Prevents the "I restarted but it's still serving the old model" class of bug.

## Launch mechanics

```zsh
nohup python3 "$LENIENT_SCRIPT" \
  --model "$model" \
  --port "$port" \
  --host 127.0.0.1 \
  --chat-template-args '{"enable_thinking":false}' \
  --prompt-cache-size 2 \
  $adapter_args \
  > "$LOG_DIR/${seat}.log" 2>&1 &

local pid=$!
```

- `nohup` so server survives terminal close
- All stdout/stderr → `~/jarvis/Logs/mlx/<seat>.log`
- `&` to background, `$!` captures PID

## Health poll (wait for `/health`)

```zsh
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
```

- Polls `/health` every 3 seconds
- `kill -0 $pid` checks process exists without sending a signal
- If process dies before /health passes, reports that AND points at the log
- Total timeout: 120 seconds (enough for cold start + adapter load)

## Stop mechanics

```zsh
local pid
pid=$(pgrep -f "mlx_(lm|vlm).*--port ${port}\b" 2>/dev/null || \
      pgrep -f "mlx_lm.*--port ${port}" 2>/dev/null || \
      pgrep -f "mlx_vlm.*--port ${port}" 2>/dev/null || true)
if [ -n "$pid" ]; then
  kill "$pid" 2>/dev/null || true
  echo "🛑 Stopped $seat (port $port, PID $pid)"
fi
```

Tries three matching patterns to be robust:
1. `mlx_(lm|vlm)` alternation with word-boundary
2. `mlx_lm` only
3. `mlx_vlm` only

Sends `SIGTERM` (not -9) so mlx_lm can clean up KV cache. If stuck, rerun with `-9`.

## Resident seats (default startup)

```zsh
RESIDENT_SEATS="CRO CTO CSO CDO"
```

These are the 4 seats that boot with `bash mlx_servers.sh start` (no seat arg). Coder is NOT in the set — must be started explicitly with `bash mlx_servers.sh start Coder`.

## How to add a new seat (current model)

1. Add a line to `SEAT_CONFIG` with format `NAME|PORT|REPO|SERVER_TYPE`
2. If it needs an adapter: `SEAT_ADAPTER["NAME"]="${ADAPTER_ROOT}/<adapter-dir>"`
3. If it should be resident: add to `RESIDENT_SEATS`
4. Test: `bash scripts/mlx_servers.sh start NAME`
5. Verify health: `curl -sf http://127.0.0.1:<port>/health`

## How to update for the new boardroom registry (when ready)

Changes needed per `boardroom-seat-mapping.md`:

```zsh
# Rename "Coder" line to "Strategy" and swap model
# BEFORE:
Coder|11504|mlx-community/Qwen2.5-Coder-32B-Instruct-4bit|lm

# AFTER:
Strategy|11504|mlx-community/Qwen3-30B-A3B-4bit|lm_lenient

# Add new line:
Ops|11505|mlx-community/Qwen2.5-1.5B-Instruct-4bit|lm

# Optional — update RESIDENT_SEATS if F (ops) should boot at startup
# Current: RESIDENT_SEATS="CRO CTO CSO CDO"
# Possible: RESIDENT_SEATS="CRO CTO CSO CDO Strategy Ops"  (if memory allows)
```

Decision point: keep Coder-32B running on a different port alongside? Or retire it in favor of Qwen3-30B-A3B? The latter is cheaper memory-wise.

## Common issues

### "address already in use"
Stale process holding port. Don't use the script's stop (stale is the wrong type). Manual:
```bash
lsof -i TCP:<port> -sTCP:LISTEN
kill -9 <pid>
```

### Server starts, `/health` never passes
Loading adapter or model weights — watch `~/jarvis/Logs/mlx/<seat>.log`. First launch can take 120s+ on slow disk.

### Process launches, exits immediately
Check the log. Common causes:
- Wrong HF repo name (404)
- Python import error (missing mlx_vlm etc.)
- GPU unavailable (Metal driver issue)

### Multiple seats stop responding simultaneously
macOS killed them for GPU command-buffer violations. Check Console.app for `ImpactingInteractivity` messages. Usually caused by running 35B + 9B + vision concurrently — hit memory ceiling.

## Log rotation

`mlx_servers.sh` doesn't rotate logs. After a few weeks of restarts, `~/jarvis/Logs/mlx/*.log` can bloat. Manual cleanup:

```bash
cd ~/jarvis/Logs/mlx
# Keep last 1 MB of each log
for f in *.log; do tail -c 1M "$f" > "$f.tmp" && mv "$f.tmp" "$f"; done
```

Or add a cron/launchd job.

## Related

- `serving-mlx.md` — higher-level overview of the serving stack
- `collective/models/boardroom-seat-mapping.md` — the new 17-seat registry
- Vault: `collective/models/qwen3.5-35b/02-installation-and-serving.md` — CSO-specific
- Vault: `collective/models/qwen3.5-9b/02-installation-and-serving.md` — CRO-specific
