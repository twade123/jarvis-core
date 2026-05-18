#!/usr/bin/env python3
"""kronos_smoke_test.py — verify the current Kronos model loads and forecasts.

Reads TUNING["kronos.model_name"], loads via KronosPredictor, runs one 24-bar
forecast on synthetic candles, and reports.

Run after swapping TUNING to a new model variant.

Usage:
  python3 kronos_smoke_test.py
"""

from __future__ import annotations

import sys
import time
from pathlib import Path


def main() -> int:
    sys.path.insert(0, '~/Jarvis/Forex Trading Team/Source')
    sys.path.insert(0, '~/Jarvis/research/kronos')

    print("→ Loading TUNING config...")
    from tuning_config import TUNING
    model_name = TUNING.get("kronos.model_name", {}).get("value")
    tokenizer_path = TUNING.get("kronos.tokenizer_path", {}).get("value", "NeoQuasar/Kronos-Tokenizer-base")

    print(f"  kronos.model_name     = {model_name}")
    print(f"  kronos.tokenizer_path = {tokenizer_path}")

    if not model_name:
        print("✗ kronos.model_name not set in TUNING")
        return 1
    if model_name.startswith("/") and not Path(model_name).exists():
        print(f"✗ model path does not exist: {model_name}")
        return 1

    print("→ Importing Kronos...")
    from model import Kronos, KronosTokenizer, KronosPredictor

    print("→ Checking MPS...")
    import torch
    device = "mps" if torch.backends.mps.is_available() else "cpu"
    print(f"  device = {device}")
    if device == "cpu":
        print("  ⚠️  MPS unavailable — forecast will be slow")

    print("→ Loading tokenizer...")
    t0 = time.time()
    tokenizer = KronosTokenizer.from_pretrained(tokenizer_path)
    print(f"  loaded in {time.time() - t0:.1f}s")

    print("→ Loading model...")
    t0 = time.time()
    model = Kronos.from_pretrained(model_name)
    print(f"  loaded in {time.time() - t0:.1f}s")

    print("→ Creating predictor...")
    predictor = KronosPredictor(model, tokenizer, device=device, max_context=512)

    print("→ Generating synthetic candles (512 bars of M15)...")
    import pandas as pd
    import numpy as np
    rng = np.random.default_rng(42)
    n = 512
    base = 1.1000
    closes = base + np.cumsum(rng.normal(0, 0.0005, n))
    candles = pd.DataFrame({
        "open": closes + rng.normal(0, 0.0001, n),
        "high": closes + np.abs(rng.normal(0, 0.0003, n)),
        "low": closes - np.abs(rng.normal(0, 0.0003, n)),
        "close": closes,
        "volume": rng.integers(50, 500, n),
        "amount": rng.integers(50000, 500000, n),
    })
    candles.index = pd.date_range(end=pd.Timestamp.now(tz="UTC"), periods=n, freq="15min")

    future_ts = pd.date_range(
        start=candles.index[-1] + pd.Timedelta(minutes=15),
        periods=24, freq="15min"
    )

    print("→ Running single forecast (sample_count=5, 24 bars)...")
    t0 = time.time()
    forecast = predictor.predict(
        df=candles,
        timestamps=future_ts,
        sample_count=5,
        temperature=0.9,
        top_p=0.95,
    )
    elapsed = time.time() - t0
    print(f"  forecast in {elapsed:.1f}s")

    if forecast is None or len(forecast) == 0:
        print("✗ forecast returned empty")
        return 1

    print(f"→ Forecast shape: {forecast.shape}")
    print(f"  first row: {forecast.iloc[0].to_dict()}")
    print(f"  last row:  {forecast.iloc[-1].to_dict()}")

    # Cleanup
    import gc
    if device == "mps":
        torch.mps.empty_cache()
    gc.collect()

    print("\n✓ PASS — Kronos loads and forecasts")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        print(f"\n✗ FAIL: {type(e).__name__}: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)
