from datetime import date

import pandas as pd

from src import config
from src.data import twelvedata as td


def fake_http(calls, bad_key=None):
    def http(url, params, timeout):
        calls.append(params)
        class R:
            def json(self_):
                if params["apikey"] == bad_key:
                    return {"code": 429, "message": "limit"}
                s = pd.Timestamp(params["start_date"]); e = pd.Timestamp(params["end_date"])
                idx = [t for t in pd.date_range(s, e, freq="1min")
                       if t.weekday() < 5 and 570 <= t.hour * 60 + t.minute < 960 and t >= s][:int(params["outputsize"])]
                return {"values": [{"datetime": str(t), "open": "1", "high": "2", "low": "0.5", "close": "1", "volume": "10"} for t in idx]}
        return R()
    return http


def cfg(tmp):
    c = config.load()
    c["paths"]["cache"] = tmp
    c["data"]["outputsize"] = 800    # force pagination
    return c


def test_resume_and_pagination(tmp_path, monkeypatch):
    monkeypatch.setattr(td.time, "sleep", lambda s: None)
    c, calls = cfg(tmp_path), []
    keys = td.Keys(["bad", "good"])
    h = fake_http(calls, bad_key="bad")
    new, _ = td.fetch_symbol(c, keys, "AAA", "2024-03-04", "2024-03-08", h)
    assert new == 5 * 390 and td.summary(c, "AAA") == (5 * 390, 5)
    n_calls = len(calls)
    assert td.fetch_symbol(c, keys, "AAA", "2024-03-04", "2024-03-08", h) == (0, 0) and len(calls) == n_calls
    # extending the range fetches only the new weekdays
    new, _ = td.fetch_symbol(c, keys, "AAA", "2024-03-04", "2024-03-12", h)
    assert new == 2 * 390


def test_missing_ranges():
    cov = {"2024-03-05"}
    assert td._missing_ranges(cov, date(2024, 3, 4), date(2024, 3, 6)) == [(date(2024, 3, 4),) * 2, (date(2024, 3, 6),) * 2]
