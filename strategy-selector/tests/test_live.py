import numpy as np
import pandas as pd

from src.selector import live


def _data():
    days = pd.bdate_range("2026-01-05", periods=60)
    rng = np.random.default_rng(0)
    L = pd.DataFrame([(v, s, d, rng.normal(5 if v == "A|5m|default" else 0, 10)) for d in days for s in ("X", "Y") for v in ("A|5m|default", "B|5m|default")],
                     columns=["variant", "symbol", "date", "pnl"])
    M = pd.DataFrame([(s, d, "trend") for d in days for s in ("X", "Y")], columns=["symbol", "date", "regime"])
    return days, L, M


def test_map_ignores_asof_and_later():
    days, L, M = _data()
    asof = days[50]
    base = live.train_map(L, M, asof)
    L2, M2 = L.copy(), M.copy()
    L2.loc[L2["date"] >= asof, "pnl"] = 1e6 * (L2["variant"] == "B|5m|default") - 1e6 * (L2["variant"] == "A|5m|default")
    M2.loc[M2["date"] >= asof, "regime"] = "chop"
    assert live.train_map(L2, M2, asof) == base
    assert base["trend"][0] == "A|5m|default"
