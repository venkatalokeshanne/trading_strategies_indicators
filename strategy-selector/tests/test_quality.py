import json

import pandas as pd

from src import config
from src.data import quality, twelvedata as td


def make(tmp, days):
    """days: {date: (n_minutes_from_open, price_scale)} -> cache for symbol XXX."""
    cfg = config.load()
    cfg["paths"]["cache"] = tmp
    d = td._dir(cfg, "XXX")
    rows = []
    for day, (n, px) in days.items():
        o = pd.Timestamp(f"{day} 09:30", tz="America/New_York")
        for i in range(n):
            rows.append(dict(time=(o + pd.Timedelta(minutes=i)).tz_convert("UTC"), open=px, high=px, low=px, close=px, volume=100.0))
    td._store(d, pd.DataFrame(rows))
    (d / "coverage.json").write_text(json.dumps(sorted(days)))
    return cfg


def test_early_close_and_split_gap(tmp_path):
    # 2023-11-24 closes 13:00 ET -> 210 minutes is a complete day; 390 would be outside-session bars
    cfg = make(tmp_path, {"2023-11-22": (390, 100.0), "2023-11-24": (210, 100.0), "2023-11-27": (390, 40.0)})
    t, s = quality.check_symbol(cfg, "XXX")
    t = t.set_index(t["day"].astype(str))
    assert t.loc["2023-11-24", "expected"] == 210 and t.loc["2023-11-24", "flags"] == ""
    assert t.loc["2023-11-27", "flags"] == "gap"          # -60% overnight = split-like
    assert t.loc["2023-11-22", "flags"] == ""


def test_full_length_bars_on_early_close_flagged(tmp_path):
    cfg = make(tmp_path, {"2023-11-24": (390, 100.0)})
    t, _ = quality.check_symbol(cfg, "XXX")
    assert "outside" in t.iloc[0]["flags"]
