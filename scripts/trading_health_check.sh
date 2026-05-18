#!/usr/bin/env bash
# trading_health_check.sh — Watchdog for core trading services during market hours
#
# Checks and auto-restarts services that should ALWAYS be running during trading hours:
#   - serve_ui (port 8766)  — dashboard + API
#   - scout    (port 8767)  — snipe watcher
#   - CRO      (port 11500) — MLX execution model (Qwen3.5-9B)
#   - OpenClaw gateway (port 18789) — Trevor AI (monitored only, not auto-restarted)
#
# Does NOT touch CSO (11502 / 35B) — explicitly managed by intelligence crons.
# Does NOT touch CTO/CDO/Coder — boardroom, not trading infrastructure.
#
# Designed to run every 15 min on weekdays 3:30 AM – 5:00 PM ET.
# Exits 0 if all healthy, 1 if any restarts were needed (so cron logs the event).

set -uo pipefail

RESTARTED=()
FAILED=()

PYTHON="~/myenv/bin/python"
JARVIS="~/jarvis"
SOURCE="$JARVIS/Forex Trading Team/Source"
LAUNCHER="$SOURCE/trading_launcher.sh"
MLX_SCRIPT="$JARVIS/scripts/mlx_servers.sh"
LOG="$JARVIS/Logs/server/health_check.log"
FLIGHT_DB="$SOURCE/flight_recorder.db"
mkdir -p "$(dirname "$LOG")"

TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')

log() { echo "[$TIMESTAMP] $*" | tee -a "$LOG"; }

# ── Helper: check if a port is in use ─────────────────────────────
port_alive() {
    lsof -i ":$1" -sTCP:LISTEN -t > /dev/null 2>&1
}

# ── Helper: endpoint HTTP check (faster than port check for serve_ui) ──
http_ok() {
    curl -sf --max-time 5 "$1" -o /dev/null 2>/dev/null
}

# ── Helper: log service event to flight recorder ──────────────────
flight_log() {
    local stage="$1"   # service_down | service_restart | service_up
    local service="$2"
    local note="$3"
    if [ -f "$FLIGHT_DB" ]; then
        sqlite3 "$FLIGHT_DB" \
          "INSERT INTO flight_log (timestamp, stage, pair, status, note, user_id)
           VALUES (datetime('now'), '$stage', 'SYSTEM', 'ok', '$service: $note', 2);" \
          2>/dev/null || true
    fi
}

log "=== Trading Health Check ==="

# ── 1. serve_ui (port 8766) ────────────────────────────────────────
if http_ok "http://127.0.0.1:8766/"; then
    log "  ✅ serve_ui (8766) — healthy"
else
    log "  ⚠️  serve_ui (8766) — DOWN, restarting..."
    flight_log "service_down" "serve_ui" "port 8766 not responding"
    # Kill anything lingering on the port first
    lsof -ti :8766 | xargs kill -9 2>/dev/null || true
    sleep 1
    cd "$JARVIS" && source ~/myenv/bin/activate
    nohup "$PYTHON" serve_ui.py >> logs/server/serve_ui.log 2>&1 &
    sleep 8
    if http_ok "http://127.0.0.1:8766/"; then
        log "  ✅ serve_ui restarted OK (PID $!)"
        flight_log "service_restart" "serve_ui" "auto-restarted by health check, now healthy"
        RESTARTED+=("serve_ui")
    else
        log "  ❌ serve_ui FAILED to restart — check logs/server/serve_ui.log"
        flight_log "service_down" "serve_ui" "restart attempted but FAILED"
        FAILED+=("serve_ui")
    fi
fi

# ── 2. Scout (port 8767) ──────────────────────────────────────────
if port_alive 8767; then
    log "  ✅ scout (8767) — healthy"
else
    log "  ⚠️  scout (8767) — DOWN, restarting..."
    flight_log "service_down" "scout" "port 8767 not responding"
    cd "$SOURCE" && source ~/myenv/bin/activate
    nohup "$PYTHON" -m trade_scout >> "$SOURCE/logs/scout.log" 2>&1 &
    SCOUT_NEW_PID=$!
    # Scout runs a full market scan (~10-15s) before binding to port 8767 — wait up to 40s
    SCOUT_WAITED=0
    while [[ $SCOUT_WAITED -lt 40 ]]; do
        sleep 3
        SCOUT_WAITED=$((SCOUT_WAITED + 3))
        if port_alive 8767; then
            log "  ✅ scout restarted OK (PID $SCOUT_NEW_PID, took ${SCOUT_WAITED}s)"
            flight_log "service_restart" "scout" "auto-restarted by health check, now healthy"
            RESTARTED+=("scout")
            break
        fi
        # If process died, no point waiting further
        if ! kill -0 "$SCOUT_NEW_PID" 2>/dev/null; then
            log "  ❌ scout process died during startup — check $SOURCE/logs/scout.log"
            flight_log "service_down" "scout" "process died during startup"
            FAILED+=("scout")
            break
        fi
    done
    if [[ $SCOUT_WAITED -ge 40 ]] && ! port_alive 8767; then
        log "  ❌ scout FAILED to bind port after 40s — check $SOURCE/logs/scout.log"
        flight_log "service_down" "scout" "port 8767 not bound after 40s"
        FAILED+=("scout")
    fi
fi

# ── 3. CRO — MLX execution model (port 11500, Qwen3.5-9B) ────────
if port_alive 11500; then
    log "  ✅ CRO/MLX-exec (11500) — healthy"
else
    log "  ⚠️  CRO/MLX-exec (11500) — DOWN, restarting..."
    flight_log "service_down" "CRO-mlx" "port 11500 not responding"
    bash "$MLX_SCRIPT" start CRO >> "$LOG" 2>&1
    sleep 5
    if port_alive 11500; then
        log "  ✅ CRO restarted OK"
        flight_log "service_restart" "CRO-mlx" "auto-restarted by health check, now healthy"
        RESTARTED+=("CRO-11500")
    else
        log "  ❌ CRO FAILED to restart — check $JARVIS/Logs/mlx/"
        flight_log "service_down" "CRO-mlx" "restart attempted but FAILED"
        FAILED+=("CRO-11500")
    fi
fi

# ── 4. OpenClaw gateway (port 18789) ─────────────────────────────
# LaunchAgent (ai.openclaw.gateway.plist, KeepAlive=true) is the real restart mechanism.
# This check detects when launchd dropped the plist (too many rapid crashes) and
# re-bootstraps it — which is different from restarting the process directly.
if port_alive 18789; then
    log "  ✅ OpenClaw gateway (18789) — healthy"
else
    log "  ⚠️  OpenClaw gateway (18789) — DOWN"
    flight_log "service_down" "openclaw-gateway" "port 18789 not responding"

    # Re-bootstrap the launchd plist — this lets KeepAlive take over again
    PLIST="$HOME/Library/LaunchAgents/ai.openclaw.gateway.plist"
    launchctl bootout "gui/$UID" "$PLIST" 2>/dev/null || true
    sleep 2
    launchctl bootstrap "gui/$UID" "$PLIST" 2>/dev/null
    sleep 8

    if port_alive 18789; then
        log "  ✅ OpenClaw gateway re-bootstrapped, now healthy"
        flight_log "service_restart" "openclaw-gateway" "launchd re-bootstrapped, now healthy"
        RESTARTED+=("openclaw-gateway")
        curl -s -X POST "https://api.telegram.org/bot8588745151:AAEt1nRdUD1yUER94r2MQJ5sPOgMLAzzzdI/sendMessage" \
            -d "chat_id=6368550107&text=⚡ Trevor AI was down — launchd re-bootstrapped, all good now." \
            -o /dev/null
    else
        log "  ❌ OpenClaw gateway still down after re-bootstrap"
        flight_log "service_down" "openclaw-gateway" "re-bootstrap failed — manual intervention needed"
        FAILED+=("openclaw-gateway")
        curl -s -X POST "https://api.telegram.org/bot8588745151:AAEt1nRdUD1yUER94r2MQJ5sPOgMLAzzzdI/sendMessage" \
            -d "chat_id=6368550107&text=❌ Trevor AI is DOWN and launchd re-bootstrap failed. Run: launchctl bootstrap gui/\$UID ~/Library/LaunchAgents/ai.openclaw.gateway.plist" \
            -o /dev/null
    fi
fi

# ── 5. CSO — 35B intelligence model (Ollama port 11434) ──────────────────
# CSO MLX server replaced by Ollama. Check Ollama instead.
if port_alive 11434; then
    log "  ✅ CSO/35B-intel (Ollama 11434) — healthy"
else
    log "  ⚠️  Ollama (11434) — DOWN"
    flight_log "service_down" "CSO-ollama" "Ollama port 11434 not responding"
    FAILED+=("CSO-Ollama-11434")
fi

# ── 6. Trading Watchdog (trading_watchdog.py) ─────────────────────
# The watchdog auto-restarts serve_ui and scout — if it's down, nothing else auto-recovers.
if pgrep -f "trading_watchdog.py" > /dev/null 2>&1; then
    log "  ✅ trading_watchdog — healthy"
else
    log "  ⚠️  trading_watchdog — DOWN, restarting..."
    flight_log "service_down" "trading_watchdog" "process not found"
    cd "$JARVIS" && source ~/myenv/bin/activate
    nohup "$PYTHON" trading_watchdog.py >> "$JARVIS/logs/watchdog.log" 2>&1 &
    sleep 3
    if pgrep -f "trading_watchdog.py" > /dev/null 2>&1; then
        log "  ✅ trading_watchdog restarted OK (PID $!)"
        flight_log "service_restart" "trading_watchdog" "auto-restarted by health check"
        RESTARTED+=("trading_watchdog")
    else
        log "  ❌ trading_watchdog FAILED to restart"
        flight_log "service_down" "trading_watchdog" "restart failed"
        FAILED+=("trading_watchdog")
    fi
fi

# ── Summary ──────────────────────────────────────────────────────
ALL_ISSUES=()
[[ ${#RESTARTED[@]} -gt 0 ]] && ALL_ISSUES+=("${RESTARTED[@]}")
[[ ${#FAILED[@]} -gt 0 ]]    && ALL_ISSUES+=("${FAILED[@]}")
if [ ${#ALL_ISSUES[@]} -gt 0 ]; then
    log "  ⚡ Restarted: ${RESTARTED[*]:-none}"
    [ ${#FAILED[@]} -gt 0 ] && log "  ❌ Failed to recover: ${FAILED[*]}"
    log "=== Health check complete — issues detected ==="
    exit 1  # Non-zero so cron logs the restart event visibly
else
    log "  All trading services healthy"
    log "=== Health check complete — all OK ==="
    exit 0
fi
