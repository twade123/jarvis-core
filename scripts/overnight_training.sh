#!/bin/bash
# Overnight 35B LoRA training script
# Runs at 10:30pm ET (03:30 UTC) daily
# Stops 9B server, trains trevor_35b then validator_35b, restarts 9B
# Must complete before London open at 3am ET (08:00 UTC)

set -euo pipefail

LOG=~/jarvis/logs/overnight_training.log
VENV=~/myenv/bin/activate
PYTHON=~/myenv/bin/python3
JARVIS=~/jarvis
SOURCE="$JARVIS/Forex Trading Team/Source"
NOTIFY_SCRIPT="$SOURCE/trade_notify.py"

log() {
    echo "$(date -u '+%Y-%m-%d %H:%M:%S UTC') $*" | tee -a "$LOG"
}

notify() {
    # Send Telegram notification via trade_notify
    source "$VENV"
    python3 -c "
import sys; sys.path.insert(0,'$SOURCE')
from trade_notify import _write
_write('watchdog_restart', {'message': '$1', 'service': 'overnight_training'})
" 2>/dev/null || true
}

log "═══════════════════════════════════════"
log "OVERNIGHT TRAINING STARTED"
log "═══════════════════════════════════════"

# Check if London is about to open (bail if past 07:00 UTC)
HOUR=$(date -u +%H)
MIN=$(date -u +%M)
if [ "$HOUR" -ge 7 ]; then
    log "⚠️  Skipping — too close to London open ($(date -u '+%H:%M UTC'))"
    exit 0
fi

source "$VENV"

# ── Step 1: Pause trading (stop trade_scout so no new cycles fire) ────────────
log "Step 1: Pausing trade_scout..."
pkill -f trade_scout 2>/dev/null || true
sleep 5
log "  trade_scout stopped"

# ── Step 2: Stop 9B MLX server to free GPU memory ─────────────────────────────
log "Step 2: Stopping 9B MLX server (port 11500)..."
bash "$JARVIS/scripts/mlx_servers.sh" stop CRO 2>/dev/null || true
sleep 3
log "  9B server stopped"

# Confirm memory freed
AVAIL=$(python3 -c "
import subprocess
r = subprocess.run(['vm_stat'], capture_output=True, text=True)
for line in r.stdout.splitlines():
    if 'Pages free' in line:
        pages = int(line.split(':')[1].strip().rstrip('.'))
        print(f'{pages * 16384 / 1024**3:.1f}')
        break
" 2>/dev/null || echo "?")
log "  Free memory: ~${AVAIL}GB"

# ── Step 3: Run trevor_35b training ──────────────────────────────────────────
log "Step 3: Starting trevor_35b LoRA training (150 iters)..."
notify "🧠 Overnight training started — trevor_35b (150 iters)"

cd "$SOURCE"
python3 -c "
import sys
sys.path.insert(0, '.')
from lora_trainer import run_lora_training, _load_training_state, _count_training_pairs, MODEL_CONFIGS
import time

cfg = MODEL_CONFIGS['trevor_35b']
count = _count_training_pairs(cfg['training_file'])
print(f'Training trevor_35b on {count} pairs, 150 iters')
proc = run_lora_training('trevor_35b')
if proc is None:
    print('ERROR: failed to start training')
    exit(1)
print(f'PID: {proc.pid} | log: {cfg[\"log_file\"]}')
# Wait for completion
proc.wait()
rc = proc.returncode
print(f'Exit code: {rc}')
exit(rc)
" 2>&1 | tee -a "$LOG"

TREVOR_RC=${PIPESTATUS[0]}
if [ "$TREVOR_RC" -eq 0 ]; then
    log "✅ trevor_35b training COMPLETE"
    notify "✅ trevor_35b training complete"
else
    log "❌ trevor_35b training FAILED (exit code $TREVOR_RC)"
    notify "❌ trevor_35b training FAILED — check $LOG"
fi

# ── Step 4: Run validator_35b training ───────────────────────────────────────
# Only if still enough time before London (07:00 UTC cutoff)
HOUR_NOW=$(date -u +%H)
if [ "$HOUR_NOW" -lt 7 ]; then
    log "Step 4: Starting validator_35b LoRA training (100 iters)..."
    notify "🧠 Starting validator_35b training (100 iters)"

    python3 -c "
import sys
sys.path.insert(0, '.')
from lora_trainer import run_lora_training, _count_training_pairs, MODEL_CONFIGS

cfg = MODEL_CONFIGS['validator_35b']
count = _count_training_pairs(cfg['training_file'])
print(f'Training validator_35b on {count} pairs, 100 iters')
proc = run_lora_training('validator_35b')
if proc is None:
    print('ERROR: failed to start training')
    exit(1)
print(f'PID: {proc.pid} | log: {cfg[\"log_file\"]}')
proc.wait()
rc = proc.returncode
print(f'Exit code: {rc}')
exit(rc)
" 2>&1 | tee -a "$LOG"

    VALIDATOR_RC=${PIPESTATUS[0]}
    if [ "$VALIDATOR_RC" -eq 0 ]; then
        log "✅ validator_35b training COMPLETE"
        notify "✅ validator_35b training complete"
    else
        log "❌ validator_35b training FAILED (exit code $VALIDATOR_RC)"
        notify "❌ validator_35b training FAILED — check $LOG"
    fi
else
    log "⚠️  Skipping validator_35b — too close to London open"
fi

# ── Step 5: Restart 9B server ─────────────────────────────────────────────────
log "Step 5: Restarting 9B MLX server..."
bash "$JARVIS/scripts/mlx_servers.sh" start CRO 2>/dev/null
log "  9B server restarted"

# ── Step 6: Restart trade_scout ──────────────────────────────────────────────
log "Step 6: Restarting trade_scout..."
cd "$SOURCE"
nohup "$PYTHON" -m trade_scout >> "$JARVIS/Forex Trading Team/Source/logs/scout.log" 2>&1 &
sleep 5
if pgrep -f trade_scout > /dev/null; then
    log "  ✅ trade_scout restarted (PID $(pgrep -f trade_scout | head -1))"
    notify "✅ Overnight training done — trading resumed. Check logs: $LOG"
else
    log "  ❌ trade_scout failed to restart"
    notify "⚠️ Training done but trade_scout failed to restart — check manually"
fi

log "═══════════════════════════════════════"
log "OVERNIGHT TRAINING COMPLETE"
log "═══════════════════════════════════════"
