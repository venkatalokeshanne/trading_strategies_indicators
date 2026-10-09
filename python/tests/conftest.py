"""Shared fixtures: deterministic synthetic bars (no third-party market data in git)."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def make_bars(n: int = 1500, seed: int = 7, start: str = "2020-01-01", freq: str = "D",
              flat_run: bool = True) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    ret = rng.normal(0.0004, 0.018, n)
    close = 100 * np.exp(np.cumsum(ret))
    flat_run = flat_run and n > 210             # a run of identical closes: ties, zero ranges
    if flat_run:
        close[200:206] = close[199]
    open_ = np.concatenate([[close[0]], close[:-1]]) * (1 + rng.normal(0, 0.004, n))
    high = np.maximum(open_, close) * (1 + np.abs(rng.normal(0, 0.008, n)))
    low = np.minimum(open_, close) * (1 - np.abs(rng.normal(0, 0.008, n)))
    if flat_run:
        open_[200:206] = high[200:206] = low[200:206] = close[200:206]
    vol = rng.integers(1_000, 100_000, n).astype(float)
    t = pd.date_range(start, periods=n, freq=freq, tz="UTC")
    return pd.DataFrame({"time": t.as_unit("ms").asi8, "open": open_, "high": high,
                         "low": low, "close": close, "volume": vol})


@pytest.fixture
def bars() -> pd.DataFrame:
    return make_bars()
