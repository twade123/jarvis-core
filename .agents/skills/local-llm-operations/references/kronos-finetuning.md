# Kronos Finetuning — separate pipeline

Kronos is NOT an LLM. Its finetuning pipeline is completely separate from LoRA distillation.

## What makes it different

- **No LoRA.** Kronos finetunes by training the full model (or parts) end-to-end on OHLCV candles.
- **Input is numerical.** OHLCV + timestamps, not text tokens.
- **Output is numerical.** Forecasted candles, not text.
- **Loss function is MSE/quantile loss**, not cross-entropy over a vocabulary.
- **No tokenizer swap.** Uses the BSQ tokenizer from the base repo.

## Training scripts

Base repo at `~/Jarvis/research/kronos/`. Our forex-specific adaptations:

```
~/Jarvis/research/kronos/finetune_forex/
  data/              — prepared parquet of forex M15 candles (3yr history + 248 real trades)
  finetuned/         — output models
    forex_m15_refined/
    forex_m15_pip_norm/
    forex_m15_eurusd/
    forex_m15_v2/
    forex_m15_thesis/
  configs/           — training configs (hyperparams, loss weights)
  examples/          — demo scripts
```

And a second path (likely duplication):
```
~/Jarvis/models/kronos/finetuned/
  forex_m15_pip_norm_refined/   ← PRODUCTION (per TUNING)
  forex_m15_pip_norm/
```

## Current production (forex_m15_pip_norm_refined)

Training details (from vault entry 2026-04-20):
- **Data**: 3 years forex M15 + 248 real trades
- **Normalization**: pip-normalized OHLC + EMA separation + BB width
- **Training time**: 15 hours
- **Backtest**: 60 days, 2584 trades → 73% WR, +5527p, PF 1.70, MDD 144p
- **Deployment config**: `SCALPER_MED` — SL 1.2× ATR (~10p), TP 2.0× ATR (~15p), tight ratchet 1.5p, early trailing 0.15 RR, loose gates

## How to train a new variant

```bash
cd ~/Jarvis/research/kronos/finetune_forex
source ~/myenv/bin/activate

# Example: retrain with new data
python train.py \
  --base NeoQuasar/Kronos-base \
  --data data/forex_m15_2024_2026.parquet \
  --out finetuned/forex_m15_v3 \
  --config configs/pip_norm_refined.yaml \
  --epochs 3
```

The config defines:
- Input window (usually 512 bars lookback)
- Prediction window (usually 24 bars forward)
- Learning rate, batch size
- Pair-specific normalization (e.g., JPY pairs use 0.01 pip size, others 0.0001)
- Augmentation (shuffle, flip, noise)

## Deploy a new Kronos variant (single-pointer swap)

Unlike the LLM swap (which touches 5 files), Kronos deployment is ONE change:

```bash
# Edit TUNING
python3 -c "
from tuning_config import set_tuning
set_tuning('kronos.model_name', '~/Jarvis/models/kronos/finetuned/forex_m15_v3/basemodel/best_model')
set_tuning('kronos.tokenizer_path', '~/Jarvis/models/kronos/finetuned/forex_m15_v3/tokenizer')
"

# Restart the trading daemon to reload
# (kronos_inference.py loads once at process start; restart picks up new TUNING)
```

Or via the tuning UI if present.

**This is why Kronos's pointer pattern is the gold standard** — one config row, no scattered file edits.

## Backtest before deploying

```bash
cd ~/Jarvis/research/kronos
source ~/myenv/bin/activate

# Smoke test: 10 trades
python kronos_sanity_check.py --model finetuned/forex_m15_v3/basemodel/best_model

# Full backtest: 60-day scan, 13 pairs
python kronos_scout_full.py --model finetuned/forex_m15_v3/basemodel/best_model \
  --days 60 --out results/kronos_v3_backtest.csv

# Part A trade-anchored (if you have a set of 217 matched moments)
python kronos_backtest.py --model finetuned/forex_m15_v3/basemodel/best_model
```

## Loading Kronos from code

```python
import sys
from pathlib import Path
sys.path.insert(0, '~/Jarvis/research/kronos')
from model import Kronos, KronosTokenizer, KronosPredictor
import torch

tokenizer = KronosTokenizer.from_pretrained('/path/to/tokenizer')
model = Kronos.from_pretrained('/path/to/basemodel/best_model')
device = 'mps' if torch.backends.mps.is_available() else 'cpu'
predictor = KronosPredictor(model, tokenizer, device=device, max_context=512)

# Single forecast
forecast_df = predictor.predict(
    df=candles_df,          # DataFrame with open/high/low/close/volume/amount
    timestamps=future_ts,   # DateTimeIndex for output bars
    sample_count=20,
    temperature=0.9,
    top_p=0.95
)
```

## Kronos smoke test (this skill's script)

```bash
python3 .agents/skills/local-llm-operations/scripts/kronos_smoke_test.py
```

Verifies the current TUNING-pointed Kronos model loads on MPS and produces a 24-bar forecast.

## Common failure modes

1. **Model file missing** → TUNING key points at a deleted path. Fix: update TUNING or restore file.
2. **MPS unavailable** → Falls back to CPU, forecast time balloons to 2-5 min. Fix: check PyTorch MPS build.
3. **Memory bloat over many forecasts** → Missing `torch.mps.empty_cache(); gc.collect()` between calls. Already in `kronos_inference.py`.
4. **Forecast returns garbage (all same price, or NaN)** → Input candles not normalized correctly. Fix: match the model's training normalization (pip-norm vs raw).
5. **Timezone error in pandas** → `live_trades.entry_time` is tz-naive, OANDA candles are tz-aware UTC. Always normalize to UTC before comparisons.

## Kronos model sizes

All on HuggingFace at `NeoQuasar/*`:
- Kronos-mini 4.1M — not used
- Kronos-small 24.7M — not used
- **Kronos-base 102M** — our base
- Kronos-large 499M — closed-source, not available

We finetune the 102M base. Training a 499M variant would require Kronos-large being released, which hasn't happened.

## Related

- `models/kronos-base.md` — runtime details, current production pointer
- `collective/kronos/` — vault docs on preliminary results, scout-shadow methodology, v2 optimizer results
- `research/kronos/` — the cloned repo
