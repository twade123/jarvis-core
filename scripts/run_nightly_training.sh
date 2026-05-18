#!/bin/bash
# Nightly LoRA training for trevor_35b and validator_35b
# Runs at 11 PM ET — kills 35B inference server, trains, restarts with adapters
# Called by: Nightly Session Distillation cron (expanded)

set -e
LOG="/tmp/nightly_training_$(date +%Y%m%d_%H%M).log"
echo "[$(date)] Starting nightly training" | tee "$LOG"

# ── Step 1: Kill 35B inference server to free RAM ───────────────────────────
echo "[$(date)] Killing 35B inference server..." | tee -a "$LOG"
pkill -f "Qwen3.5-35B" 2>/dev/null || true
pkill -f "11502" 2>/dev/null || true
sleep 5

# Verify RAM freed
FREE_GB=$(python3 -c "
import re, subprocess
out = subprocess.check_output(['vm_stat'], text=True)
pages = {m[0]: int(m[1]) for m in re.findall(r'Pages (.+?):\s+(\d+)', out)}
ps=16384; print(round((pages.get('free',0)+pages.get('inactive',0))*ps/1e9, 1))
")
echo "[$(date)] Available RAM: ${FREE_GB}GB" | tee -a "$LOG"

# ── Step 2: Run distillation pipeline ───────────────────────────────────────
echo "[$(date)] Running session distiller..." | tee -a "$LOG"
source ~/myenv/bin/activate
cd ~/jarvis
python3 Core/session_distiller.py --extract 2>&1 | tail -5 | tee -a "$LOG"
python3 Core/session_distiller.py --extract-cc 2>&1 | tail -3 | tee -a "$LOG"
python3 Core/session_distiller.py --export 2>&1 | tail -3 | tee -a "$LOG"

# ── Step 3: Count new pairs since last training ──────────────────────────────
NEW_PAIRS=$(python3 -c "
import sqlite3, json, os
ts_file = 'models/training_state.json'
last_count = 0
if os.path.exists(ts_file):
    ts = json.load(open(ts_file))
    last_count = ts.get('trevor_35b', {}).get('pairs_at_last_training', 0) or 0
conn = sqlite3.connect('training_data/sessions/session_training.db')
total = conn.execute('SELECT COUNT(*) FROM training_pairs').fetchone()[0]
conn.close()
print(total - last_count)
")
echo "[$(date)] New pairs since last training: $NEW_PAIRS" | tee -a "$LOG"

MIN_PAIRS=50
if [ "$NEW_PAIRS" -lt "$MIN_PAIRS" ]; then
    echo "[$(date)] Only $NEW_PAIRS new pairs — below minimum $MIN_PAIRS. Skipping training." | tee -a "$LOG"
    # Still restart 35B server
    ~/jarvis/scripts/mlx_servers.sh start CSO >> "$LOG" 2>&1 &
    exit 0
fi

# ── Step 4: Train trevor_35b ─────────────────────────────────────────────────
echo "[$(date)] Training trevor_35b (150 iters)..." | tee -a "$LOG"
ADAPTER_DIR="~/jarvis/models/adapters/trevor_35b"
DATA_PATH="~/jarvis/training_data/sessions/session_training.jsonl"
mkdir -p "$ADAPTER_DIR"

python3 -m mlx_lm.lora \
    --model mlx-community/Qwen3.5-35B-A3B-4bit \
    --train \
    --data "$DATA_PATH" \
    --adapter-path "$ADAPTER_DIR" \
    --iters 150 \
    --batch-size 1 \
    --num-layers 8 \
    --lora-rank 8 \
    --lora-scale 20.0 \
    --learning-rate 1e-5 \
    --grad-checkpoint \
    --save-every 50 \
    2>&1 | tee -a "$LOG"

TRAIN_EXIT=$?
if [ $TRAIN_EXIT -ne 0 ]; then
    echo "[$(date)] trevor_35b training FAILED (exit $TRAIN_EXIT)" | tee -a "$LOG"
else
    echo "[$(date)] trevor_35b training COMPLETE" | tee -a "$LOG"
    # Update training state
    python3 -c "
import json, sqlite3, time, os
ts_file = 'models/training_state.json'
ts = json.load(open(ts_file)) if os.path.exists(ts_file) else {}
conn = sqlite3.connect('training_data/sessions/session_training.db')
total = conn.execute('SELECT COUNT(*) FROM training_pairs').fetchone()[0]
conn.close()
ts['trevor_35b'] = {
    'last_trained': time.strftime('%Y-%m-%dT%H:%M:%S'),
    'pairs_at_last_training': total,
    'training_iters': 150,
    'adapter_path': 'models/adapters/trevor_35b',
    'status': 'trained',
    'pid': None
}
ts['runs'] = ts.get('runs', 0) + 1
json.dump(ts, open(ts_file, 'w'), indent=2)
print(f'State updated: {total} pairs')
"
fi

# ── Step 5: Restart 35B server WITH adapters ─────────────────────────────────
echo "[$(date)] Restarting 35B server with adapters..." | tee -a "$LOG"
ADAPTER_ARG=""
if [ -f "$ADAPTER_DIR/adapters.npz" ] || [ -f "$ADAPTER_DIR/adapter.bin" ]; then
    ADAPTER_ARG="--adapter-path $ADAPTER_DIR"
    echo "[$(date)] Loading trained adapters from $ADAPTER_DIR" | tee -a "$LOG"
else
    echo "[$(date)] WARNING: No adapter weights found — starting base model" | tee -a "$LOG"
fi

nohup python3 ~/jarvis/scripts/mlx_lm_server_lenient.py \
    --model mlx-community/Qwen3.5-35B-A3B-4bit \
    --port 11502 \
    --host 127.0.0.1 \
    $ADAPTER_ARG \
    >> /tmp/mlx_35b_server.log 2>&1 &

echo "[$(date)] 35B server restarting (PID $!)" | tee -a "$LOG"
echo "[$(date)] Training complete. Log: $LOG"
echo "TRAINING_LOG=$LOG"
