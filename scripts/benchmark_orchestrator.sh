#!/bin/bash
# benchmark_orchestrator.sh — Auto-chain IFEval + GPQA on distilled then base 35B.
# Waits for current IFEval (background task) to finish, then runs the rest unattended.
#
# Pipeline:
#   1. Wait for distilled IFEval to complete (/tmp/ifeval_distilled_run.log "Saving results aggregated")
#   2. GPQA Diamond on distilled (CSO already has 35b_mlx adapter loaded)
#   3. Stop CSO, relaunch bare (no adapter), wait for /health
#   4. IFEval on base
#   5. GPQA Diamond on base
#   6. Final summary
#
# All output to /tmp/benchmark_orchestrator.log

set -u
LOG=/tmp/benchmark_orchestrator.log
exec >> "$LOG" 2>&1

echo ""
echo "=================================================================="
echo "BENCHMARK ORCHESTRATOR START — $(date)"
echo "=================================================================="

source ~/myenv/bin/activate

MODEL_ARGS_BASE='base_url=http://127.0.0.1:11502/v1/chat/completions,model=mlx-community/Qwen3.5-35B-A3B-4bit,num_concurrent=1,tokenized_requests=False,eos_string=<|im_end|>'
COMMON_FLAGS='--apply_chat_template --log_samples'

OUT_DISTILLED=~/Jarvis/Models/benchmarks/distilled_35b/distilled_v2
OUT_BASE=~/Jarvis/Models/benchmarks/distilled_35b/base_rerun
mkdir -p "$OUT_DISTILLED" "$OUT_BASE"

# ── STEP 1: Wait for distilled IFEval to complete ────────────────
echo ""
echo "[$(date +%H:%M:%S)] STEP 1: Waiting for distilled IFEval to finish..."
while ! grep -q "Saving results aggregated" /tmp/ifeval_distilled_run.log 2>/dev/null; do
  sleep 30
done
echo "[$(date +%H:%M:%S)] Distilled IFEval finished ✓"
tail -10 /tmp/ifeval_distilled_run.log

# ── STEP 2: GPQA Diamond on distilled ────────────────────────────
echo ""
echo "[$(date +%H:%M:%S)] STEP 2: GPQA Diamond on distilled (CSO has 35b_mlx adapter)..."
curl -sf http://127.0.0.1:11502/health || { echo "ERR: CSO not healthy"; exit 1; }

lm_eval --model local-chat-completions \
  --model_args "$MODEL_ARGS_BASE" \
  --tasks gpqa_diamond_cot_zeroshot \
  --output_path "$OUT_DISTILLED/" \
  $COMMON_FLAGS
echo "[$(date +%H:%M:%S)] GPQA distilled done ✓"

# ── STEP 2b: MMLU-Pro on distilled (limit 2000, 5-shot to match Qwen methodology) ─
echo ""
echo "[$(date +%H:%M:%S)] STEP 2b: MMLU-Pro on distilled (--limit 2000, ~4 hrs)..."
curl -sf http://127.0.0.1:11502/health || { echo "ERR: CSO not healthy before MMLU-Pro"; exit 1; }

lm_eval --model local-chat-completions \
  --model_args "$MODEL_ARGS_BASE" \
  --tasks mmlu_pro \
  --output_path "$OUT_DISTILLED/" \
  --num_fewshot 5 \
  --limit 2000 \
  $COMMON_FLAGS
echo "[$(date +%H:%M:%S)] MMLU-Pro distilled done ✓"

# ── PAUSE for Tim's validator test ────────────────────────────────
echo ""
echo "[$(date +%H:%M:%S)] ════════════════════════════════════════════════"
echo "[$(date +%H:%M:%S)] PAUSED — Tim is running a separate validator test"
echo "[$(date +%H:%M:%S)] To resume: touch /tmp/resume_benchmark"
echo "[$(date +%H:%M:%S)] Auto-resume after 120 min if no signal"
echo "[$(date +%H:%M:%S)] ════════════════════════════════════════════════"
PAUSE_START=$(date +%s)
rm -f /tmp/resume_benchmark 2>/dev/null
while true; do
  if [ -f /tmp/resume_benchmark ]; then
    rm -f /tmp/resume_benchmark
    echo "[$(date +%H:%M:%S)] Resume signal received — continuing pipeline"
    break
  fi
  NOW=$(date +%s)
  ELAPSED=$((NOW - PAUSE_START))
  if [ $ELAPSED -gt 7200 ]; then
    echo "[$(date +%H:%M:%S)] 120-min auto-resume timeout — continuing pipeline"
    break
  fi
  sleep 30
done

# ── STEP 2c: SWE-bench 1-task smoke on distilled (validate harness wiring) ─
echo ""
echo "[$(date +%H:%M:%S)] STEP 2c: SWE-bench smoke (sympy__sympy-20916, distilled)..."
curl -sf http://127.0.0.1:11502/health || { echo "ERR: CSO not healthy before SWE-bench"; }

mkdir -p ~/Jarvis/Models/benchmarks/distilled_35b/swebench_smoke_distilled
mini-extra swebench \
  --subset verified \
  --split test \
  --filter "sympy__sympy-20916" \
  --output ~/Jarvis/Models/benchmarks/distilled_35b/swebench_smoke_distilled/ \
  --model "openai/mlx-community/Qwen3.5-35B-A3B-4bit" \
  --workers 1 \
  -c ~/myenv/lib/python3.10/site-packages/minisweagent/config/benchmarks/swebench.yaml \
  -c "model.model_kwargs.api_base=http://127.0.0.1:11502/v1" \
  -c "model.model_kwargs.api_key=local" \
  -c "agent.cost_limit=0" \
  -c "agent.step_limit=30" \
  --yolo 2>&1 | tail -50 || echo "[$(date +%H:%M:%S)] SWE-bench smoke errored — check log, but continuing pipeline (this was a validation step, not gating)"

echo "[$(date +%H:%M:%S)] SWE-bench smoke step done (success or fail, see output above)"

# ── STEP 3: Stop CSO, restart bare (no adapter) ──────────────────
echo ""
echo "[$(date +%H:%M:%S)] STEP 3: Switching CSO to BASE (no adapter)..."
pkill -f "mlx_vlm_server_with_tools.*--port 11502" 2>&1
sleep 5
nohup python3 ~/Jarvis/scripts/mlx_vlm_server_with_tools.py \
  --model mlx-community/Qwen3.5-35B-A3B-4bit \
  --port 11502 --host 127.0.0.1 \
  > ~/Jarvis/Logs/mlx/CSO_base.log 2>&1 &

# Wait for /health
echo "[$(date +%H:%M:%S)] Waiting for bare CSO /health..."
for i in $(seq 1 120); do
  if curl -sf http://127.0.0.1:11502/health 2>/dev/null | grep -q "loaded_adapter"; then
    health=$(curl -s http://127.0.0.1:11502/health)
    if echo "$health" | grep -q '"loaded_adapter":null'; then
      echo "[$(date +%H:%M:%S)] Bare CSO ready (no adapter) ✓"
      break
    elif echo "$health" | grep -q "35b_mlx"; then
      echo "ERR: CSO came up WITH adapter — restart logic broken"
      exit 1
    fi
  fi
  sleep 2
done
curl -s http://127.0.0.1:11502/health
echo ""

# ── STEP 4: IFEval on base ───────────────────────────────────────
echo ""
echo "[$(date +%H:%M:%S)] STEP 4: IFEval on BASE 35B..."
lm_eval --model local-chat-completions \
  --model_args "$MODEL_ARGS_BASE" \
  --tasks ifeval \
  --output_path "$OUT_BASE/" \
  $COMMON_FLAGS
echo "[$(date +%H:%M:%S)] IFEval base done ✓"

# ── STEP 5: GPQA Diamond on base ─────────────────────────────────
echo ""
echo "[$(date +%H:%M:%S)] STEP 5: GPQA Diamond on BASE 35B..."
lm_eval --model local-chat-completions \
  --model_args "$MODEL_ARGS_BASE" \
  --tasks gpqa_diamond_cot_zeroshot \
  --output_path "$OUT_BASE/" \
  $COMMON_FLAGS
echo "[$(date +%H:%M:%S)] GPQA base done ✓"

# ── STEP 5b: MMLU-Pro on base (--limit 500 to fit weekend window) ────
echo ""
echo "[$(date +%H:%M:%S)] STEP 5b: MMLU-Pro on BASE 35B (--limit 500, ~3.5 hrs)..."
lm_eval --model local-chat-completions \
  --model_args "$MODEL_ARGS_BASE" \
  --tasks mmlu_pro \
  --output_path "$OUT_BASE/" \
  --num_fewshot 5 \
  --limit 500 \
  $COMMON_FLAGS
echo "[$(date +%H:%M:%S)] MMLU-Pro base done ✓"

echo ""
echo "=================================================================="
echo "ORCHESTRATOR COMPLETE — $(date)"
echo "=================================================================="
echo ""
echo "Results:"
echo "  Distilled (with 35b_mlx adapter):"
ls -la "$OUT_DISTILLED/"*/results_*.json 2>&1 | tail -3
echo "  Base (no adapter):"
ls -la "$OUT_BASE/"*/results_*.json 2>&1 | tail -3
echo ""
echo "Run report compilation:  python3 ~/Jarvis/scripts/benchmark_compile_report.py"
