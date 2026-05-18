---
type: note
created: 2026-04-14
tags: [kronos, foundation-model, trading, candlestick, research]
---

# Kronos — Foundation Model for Financial K-lines

## What it is
- Open-source decoder-only transformer for OHLCV candlesticks (Tsinghua, AAAI 2026, MIT license)
- Two-stage: BSQ tokenizer (hierarchical s1/s2 codes) → autoregressive transformer
- Trained on 12B K-lines from 45 global exchanges
- Repo: `research/kronos/` (cloned from shiyu-coder/Kronos)
- Paper: arXiv 2508.02739

## Models (all on HuggingFace NeoQuasar/*)
| Model | Params | Context | Use |
|---|---|---|---|
| Kronos-mini | 4.1M | 2048 | Long history, fast |
| Kronos-small | 24.7M | 512 | Balanced |
| Kronos-base | 102.3M | 512 | Best accuracy (we use this) |
| Kronos-large | 499M | 512 | Closed-source |

## Local runtime
- Auto-detects MPS on Apple Silicon (works natively, no MLX conversion)
- 102M model: ~30s per forecast at sample_count=20, ~2s batched on 13 pairs via `predict_batch()`
- Deps: torch, einops, huggingface_hub (>=1.3 to avoid transformers conflict), safetensors

## Output shape
- Returns DataFrame of forecasted [open, high, low, close, volume, amount] for next N bars
- Stochastic: temperature + top_p + sample_count for Monte Carlo paths
- Does NOT output trade signals — we derive direction/SL/TP from forecast statistics

## Integration files in our codebase
- `research/kronos/` — full Kronos repo + our backtest scripts
- `research/kronos/kronos_sanity_check.py` — 10-trade smoke test
- `research/kronos/kronos_backtest.py` — Part A (trade-anchored, 217 matched moments)
- `research/kronos/kronos_scout_full.py` — full 13-pair shadow scout, 60-day continuous scan
- Results: `research/kronos/results/`

## Critical lessons from initial integration
1. **Kronos confidence ≠ scout confidence.** Our derived `drift_pips/cone_pips` is NOT
   on the same scale as `scout.min_confidence` (0.85). Don't gate Kronos signals with
   scout's threshold — empirically calibrate from a confidence curve.
2. **Naive confidence is weak filter.** On 92 trades, win rate at conf=0.0 (82.6%) was
   essentially same as conf=0.8 (73.9%). Drift/cone ratio doesn't separate good from
   bad signals. Need better metric (path consistency across MC samples).
3. **OANDA fetch_candles** in `backtester.data_fetcher` over-fetches (5000-candle
   pagination). Causes ~30s overhead per trade. Pre-fetch to local parquet cache for
   batch jobs.
4. **Timezone trap.** `live_trades.entry_time` is sometimes tz-naive; OANDA candle
   times are tz-aware UTC. Always normalize to UTC-aware before pandas comparisons.
5. **MPS memory growth.** Add `torch.mps.empty_cache(); gc.collect()` after each
   forecast to prevent slow memory bloat over hundreds of trades.

## Vault structure for Kronos work
- `00-kronos-overview.md` — this file
- `01-preliminary-92-trade-results.md` — Part A first findings
- `02-scout-shadow-methodology.md` — full mirror test design
- `03-scout-shadow-final-results.md` — **2834-signal final results (83.9% wr, +7462p)**
- Design spec: `docs/superpowers/specs/2026-04-14-kronos-scout-component-design.md`
