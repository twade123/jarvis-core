---
type: note
created: 2026-04-22
tags: [kronos, finetuning, forex, workflow, training]
agent: claude-code
---

# 06 — Kronos Finetuning Workflow

End-to-end procedure for training a new Kronos variant. Distinct from LLM LoRA distillation — Kronos trains the full model (or components) on forex OHLCV candles, not text tokens.

## Prerequisites

- Python 3.10+ with torch (MPS-capable on M-series) or CUDA
- `~/Jarvis/research/kronos/` cloned from the Kronos repo
- Parquet cache of historical OANDA candles (see "Data prep" below)
- ~30 GB free disk for training outputs

## The forex pipeline

```
OANDA historical candles (via broker API)
    ↓ fetch_candles (5000-candle pagination)
~/Jarvis/research/kronos/candle_cache/*.parquet  (per-pair, per-timeframe)
    ↓ prepare_training_data.py (pip-normalize, EMA sep, BB width)
~/Jarvis/research/kronos/finetune_forex/data/<dataset>.parquet
    ↓ train.py (full model finetune or adapter)
~/Jarvis/models/kronos/finetuned/<variant>/
    ├── basemodel/
    │   ├── best_model/
    │   ├── checkpoint-<N>/
    │   └── logs/
    └── tokenizer/
    ↓ update TUNING["kronos.model_name"] → new path
Live trading picks up new model on next daemon restart
```

## Step 1 — Fetch candles from OANDA

If candle_cache is stale, refresh:

```bash
source ~/myenv/bin/activate
cd ~/Jarvis/research/kronos

python fetch_candles.py \
  --pairs EUR_USD,GBP_USD,USD_JPY,... \
  --timeframe M15 \
  --from 2023-01-01 \
  --to 2026-04-01 \
  --out candle_cache/
```

**Gotcha (from 00-overview.md)**: OANDA's `fetch_candles` over-fetches with 5000-candle pagination → ~30s overhead per trade. For bulk fetches, be patient or use parallel pair fetches.

**Timezone trap (also from 00-overview)**: OANDA returns tz-aware UTC candles. Make sure downstream code normalizes `live_trades.entry_time` to UTC-aware before any pandas comparisons.

## Step 2 — Prepare training dataset

The current production variant (`forex_m15_pip_norm_refined`) uses:

- **Pip-normalized OHLC**: subtract baseline, divide by pip size (0.0001 for most, 0.01 for JPY pairs)
- **EMA separation feature**: `ema_fast - ema_slow` as an additional channel
- **BB width feature**: Bollinger Band width as a volatility signal

Script: `~/Jarvis/research/kronos/finetune_forex/prepare_training_data.py`

```bash
cd ~/Jarvis/research/kronos/finetune_forex

python prepare_training_data.py \
  --candles ../candle_cache/ \
  --trades ../../../Forex\ Trading\ Team/Data/trading_forex.db \
  --lookback 256 \
  --pred-len 24 \
  --normalize pip_norm \
  --features ema_sep,bb_width \
  --out data/forex_m15_2023_2026_pip_norm.parquet
```

Output: single parquet with training examples — each row is an OHLCV window + features + future candles target.

## Step 3 — Train

```bash
cd ~/Jarvis/research/kronos/finetune_forex

python train.py \
  --base NeoQuasar/Kronos-base \
  --tokenizer NeoQuasar/Kronos-Tokenizer-base \
  --data data/forex_m15_2023_2026_pip_norm.parquet \
  --epochs 3 \
  --batch-size 16 \
  --lr 1e-4 \
  --device mps \
  --out ~/Jarvis/models/kronos/finetuned/forex_m15_v3
```

On M1 Max with 102M base model:
- ~30 min per epoch on ~100K training examples
- Full model finetune (not LoRA — Kronos doesn't use adapters)
- Peak MPS memory: ~4 GB

**M1 Max Metal caveat**: NOT the same crash concern as 9B LLM training. Kronos at 102M is small; command buffers finish well within macOS's time budget. No filtering needed.

## Step 4 — Verify new variant

### Smoke test via skill script
```bash
# First update TUNING to point at the new variant
python3 -c "
from tuning_config import set_tuning
set_tuning('kronos.model_name', '~/Jarvis/models/kronos/finetuned/forex_m15_v3/basemodel/best_model')
"

# Then run the smoke test
python3 .agents/skills/local-llm-operations/scripts/kronos_smoke_test.py
```

Expected: loads, forecasts 24 bars in ~5s, returns a sensible DataFrame.

### Sanity check on 10 real trades
```bash
cd ~/Jarvis/research/kronos
python kronos_sanity_check.py \
  --model finetuned/forex_m15_v3/basemodel/best_model \
  --trades 10
```

Look for:
- No crashes
- Forecast drift_pips values in reasonable range (roughly matches ATR)
- MC spread (cone_pips) ~ realistic volatility

### Part A backtest (trade-anchored)
```bash
python kronos_backtest.py \
  --model finetuned/forex_m15_v3/basemodel/best_model \
  --config SCALPER_MED
```

Compares Kronos sim exits to real live trades over a historical set. Benchmark from production refined: 82.6% WR sim vs 55.4% actual (no spread cost caveat).

### Full scout shadow (13 pairs, 60 days)
```bash
python kronos_scout_full.py \
  --model finetuned/forex_m15_v3/basemodel/best_model \
  --pairs 13 --days 60 \
  --out results/kronos_v3_full.csv
```

Takes ~3 hours on M1 Max. Benchmark from refined: 73% WR, +5527p, PF 1.70, MDD 144p on 2584 trades.

## Step 5 — Deploy if passing gates

Quality gates for promotion:
1. Sanity check: 10/10 forecasts produce valid outputs, no NaN
2. Part A backtest: WR within 5% of current production, drift characteristics match
3. Scout shadow: WR within 3% of `forex_m15_pip_norm_refined`, PF ≥ 1.5

If all pass:

```bash
# Update the single TUNING pointer — no scattered pointer chase like LLMs
python3 <<PY
from tuning_config import set_tuning, get_tuning
# Backup current for rollback
print("Previous:", get_tuning("kronos.model_name"))
set_tuning("kronos.model_name",
  "~/Jarvis/models/kronos/finetuned/forex_m15_v3/basemodel/best_model")
set_tuning("kronos.tokenizer_path",
  "~/Jarvis/models/kronos/finetuned/forex_m15_v3/tokenizer")
print("New:", get_tuning("kronos.model_name"))
PY

# Restart the trading daemon to reload
# (Kronos is loaded once at process start; no hot-reload)
```

## Step 6 — Monitor post-deployment

Watch for 2-3 trading days:
- `ghost_verdicts` tables don't apply to Kronos (that's for validator)
- `flight_recorder` pipeline shows Kronos forecasts for each live trade
- If Kronos-influenced trades degrade WR noticeably, rollback:

```bash
python3 -c "
from tuning_config import set_tuning
set_tuning('kronos.model_name',
  '~/Jarvis/models/kronos/finetuned/forex_m15_pip_norm_refined/basemodel/best_model')
"
# Restart daemon
```

## Rollback is one line (gold standard)

Unlike LLM swaps (5+ pointer locations, `swap_trained_model.sh`), Kronos rollback is:

```python
set_tuning("kronos.model_name", "<previous-path>")
```

Restart trading daemon. Done.

## When to retrain

| Trigger | Action |
|---|---|
| New 6-month data available | Retrain to capture regime changes |
| Current variant WR drops > 5% from historical baseline | Diagnose first (market regime change vs model decay), retrain if decay |
| Kronos repo updates with better base | Evaluate, may be worth retraining on new base |
| Adding new features (e.g., order flow) | Requires new data prep script + retrain |

## Known finetuning gotchas

### 1. JPY pairs need different pip normalization
USD_JPY moves in 0.01 units (vs 0.0001 for EUR_USD). `prepare_training_data.py` auto-detects based on pair name, but manually verify:
```python
df[df['pair'] == 'USD_JPY']['pip_normalized_move'].describe()
# Should be in roughly the same range as df[df['pair'] == 'EUR_USD']
```

### 2. Imbalanced pair representation
If 80% of training data is EUR pairs, model overfits to EUR dynamics. Balance by:
- Sampling equal rows per pair
- Or weighted loss per pair

Current production refined is pair-balanced; don't lose this when preparing new datasets.

### 3. Lookahead bias
Easy mistake: training window includes future information (e.g., an indicator computed using future data). Spot check by training on a single pair and backtesting on that same pair's holdout — if WR is suspiciously high (>80%), look for leakage.

### 4. MPS cache growth
Train loops must call `torch.mps.empty_cache(); gc.collect()` between epochs, otherwise MPS fragments. Inherit from `kronos_inference.py` pattern.

## Finetuned variants history

From `../models/kronos/finetuned/`:

| Variant | Status | Notes |
|---|---|---|
| **forex_m15_pip_norm_refined** | **PRODUCTION** | 73% WR, +5527p, PF 1.70 — current TUNING target |
| forex_m15_pip_norm | superseded | earlier pip-norm run |
| forex_m15_refined | experimental | refinement branch |
| forex_m15_eurusd | pair-specific | EUR_USD only — keeps as reference |
| forex_m15_v2 | experiment | v2 architecture attempt |
| forex_m15_thesis | experiment | thesis-branch variant |

Production path: `~/Jarvis/models/kronos/finetuned/forex_m15_pip_norm_refined/basemodel/best_model`.

## Related

- `00-kronos-overview.md` — what Kronos is + core integration details
- `01-preliminary-92-trade-results.md` — initial validation
- `02-scout-shadow-methodology.md` — evaluation methodology
- `03-scout-shadow-final-results.md` — 2834-signal final results
- `04-thesis-overlay-results.md` — thesis overlay test
- `05-v2-optimizer-results.md` — 500-trial Optuna sweep results
- Skill: `.agents/skills/local-llm-operations/references/kronos-finetuning.md` (operational summary — this vault doc is the deeper workflow)
- Skill script: `.agents/skills/local-llm-operations/scripts/kronos_smoke_test.py`
- `~/Jarvis/research/kronos/` — the training code
