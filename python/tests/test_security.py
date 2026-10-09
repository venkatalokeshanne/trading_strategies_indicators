"""request.security timing on historical bars — the main source of look-ahead bias."""

from __future__ import annotations

import math

import pandas as pd

from conftest import make_bars
from pinelib import Script, run, ta
from pinelib.symbols import SymbolInfo

SYM = SymbolInfo.make("TEST:X", "crypto")          # 24 h session, UTC days


def _daily_close_seen(lookahead: bool, expr=lambda v: v.close.cur):
    b = make_bars(n=24 * 6, freq="1h", flat_run=False)
    out = []

    class T(Script):
        def on_bar(self):
            out.append(self.security(None, "D", expr, lookahead=lookahead))

    run(T, b, symbol=SYM, timeframe="60")
    day = pd.to_datetime(b.time, unit="ms", utc=True).dt.date
    daily_close = b.groupby(day)["close"].last()
    return b, day, daily_close, out


def test_lookahead_off_value_appears_on_last_bar_of_the_day():
    b, day, dc, out = _daily_close_seen(False)
    days = list(dc.index)
    for i in range(len(b)):
        d = day.iloc[i]
        k = days.index(d)
        last = i == len(b) - 1 or day.iloc[i + 1] != d
        want = dc.iloc[k] if last else (dc.iloc[k - 1] if k > 0 else math.nan)
        got = out[i]
        assert (math.isnan(want) and math.isnan(got)) or got == want, i


def test_lookahead_on_shows_the_days_final_close_all_day():
    b, day, dc, out = _daily_close_seen(True)
    days = list(dc.index)
    for i in range(len(b)):
        assert out[i] == dc.iloc[days.index(day.iloc[i])]


def test_expression_runs_on_daily_bars_with_its_own_state():
    """ta.sma inside security is computed over DAILY closes, not hourly ones."""
    b, day, dc, out = _daily_close_seen(True, expr=lambda v: ta.sma(v.close, 2))
    days = list(dc.index)
    sma2 = dc.rolling(2).mean()
    i = len(b) - 1
    assert abs(out[i] - sma2.iloc[days.index(day.iloc[i])]) < 1e-9
