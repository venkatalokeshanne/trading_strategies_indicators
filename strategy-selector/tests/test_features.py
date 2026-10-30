"""Leak test: altering bars after the checkpoint (and every later day) must leave the day's features unchanged."""
import numpy as np
import pandas as pd
import pytest

from src import config
from src.data.quality import load
from src.data.twelvedata import TZ
from src.features import day

CFG = config.load()


def _bars():
    b = load(CFG, "AAPL")
    if b.empty:
        pytest.skip("no cached AAPL bars")
    return b[b["time"] >= pd.Timestamp("2024-02-01", tz=TZ)].reset_index(drop=True)


def _scramble(b, d0, cp):
    """Randomise OHLCV of every bar at/after the checkpoint on day d0, and of all later days; premarket keeps the opening print."""
    et = b["time"].dt.tz_convert(TZ)
    mins = et.dt.hour * 60 + et.dt.minute
    dayv = et.dt.normalize().dt.tz_localize(None)
    cut = day.OPEN + (0 if cp == "premarket" else int(cp.split("+")[1]))
    hit = (dayv > d0) | ((dayv == d0) & (mins >= cut))
    x = b.copy()
    rng = np.random.default_rng(1)
    keep_open = hit & (dayv == d0) & (mins == day.OPEN) & (cp == "premarket")
    for c in ("open", "high", "low", "close"):
        new = x[c] * (1 + rng.normal(0, 0.05, len(x)))
        x[c] = np.where(hit & ~(keep_open & (c == "open")), new, x[c])
    x["volume"] = np.where(hit, x["volume"] * rng.uniform(0.1, 9, len(x)), x["volume"])
    return x


@pytest.mark.parametrize("cp", ["premarket", "open+5", "open+10", "open+15"])
def test_no_lookahead(cp):
    b = _bars()
    f0 = day.day_features(b, cp)
    d0 = f0.index[len(f0) // 2]
    f1 = day.day_features(_scramble(b, d0, cp), cp)
    assert f0.index.equals(f1.index)
    pd.testing.assert_frame_equal(f0.loc[:d0], f1.loc[:d0], check_exact=True)
    assert not f0.loc[d0].isna().all()
    assert not f0.loc[d0 + pd.Timedelta(days=3):].equals(f1.loc[d0 + pd.Timedelta(days=3):])   # the scramble really changed later days
