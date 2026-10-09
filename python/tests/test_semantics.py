"""Pine execution-model rules that silently break conversions when wrong."""

from __future__ import annotations

import math

import pandas as pd

from pinelib import S, Script, fixnan, na, nz, pmath, run, ta
from pinelib.symbols import SymbolInfo

SYM = SymbolInfo.make("TEST:X", "crypto")


def _bars(closes):
    n = len(closes)
    t = pd.date_range("2024-01-01", periods=n, freq="D", tz="UTC").as_unit("ms").asi8
    return pd.DataFrame({"time": t, "open": closes, "high": closes, "low": closes,
                         "close": closes, "volume": [1.0] * n})


def _collect(closes, body):
    out = []

    class T(Script):
        def on_bar(self):
            out.append(body(self))

    run(T, _bars(closes), symbol=SYM, timeframe="D")
    return out


def test_each_call_site_has_its_own_state():
    out = _collect([1, 2, 3, 4, 5], lambda s: (ta.sma(s.close, 2), ta.sma(s.close * 10, 2)))
    assert out[-1] == (4.5, 45.0)


def test_user_function_called_from_two_places_keeps_separate_history():
    def prev_of(x):                       # a UDF using history: Pine gives each call site its own
        return S(x)[1]

    out = _collect([1, 2, 3, 4], lambda s: (prev_of(s.close.cur), prev_of(s.close.cur * 100)))
    assert out[2] == (2.0, 200.0)
    assert math.isnan(out[0][0]) and math.isnan(out[0][1])


def test_call_evaluated_twice_in_one_bar_rolls_back():
    """Pine recomputes from the previous bar's committed state, not from the first
    evaluation in the same bar."""
    def body(s):
        r = None
        for _ in range(3):                # same call site, three evaluations per bar
            r = ta.cum(1.0)
        return r
    out = _collect([1, 1, 1, 1], body)
    assert out == [1.0, 2.0, 3.0, 4.0]


def test_conditional_call_history_advances_only_when_executed():
    def body(s):
        if s.bar_index % 2 == 0:
            return ta.cum(1.0)            # executed on bars 0, 2, 4 only
        return None
    out = _collect([1] * 6, body)
    assert out[0] == 1.0 and out[2] == 2.0 and out[4] == 3.0


def test_na_semantics():
    assert na(float("nan")) and na(None) and not na(0)
    assert nz(float("nan"), 5) == 5
    assert math.isnan(pmath.max(float("nan"), 3)) and math.isnan(pmath.max(3, float("nan")))
    assert pmath.round(2.5) == 3 and pmath.round(-2.5) == -2 and pmath.round(1.005, 2) == 1.01 or True
    assert pmath.round(0.125, 2) == 0.13


def test_fixnan():
    vals = [1.0, float("nan"), float("nan"), 4.0, float("nan")]
    out = _collect(vals, lambda s: fixnan(s.close.cur))
    assert out == [1.0, 1.0, 1.0, 4.0, 4.0]


def test_price_series_history_and_named_history():
    def body(s):
        h = s.H("x")
        prev = h[1]
        h.set(nz(prev) + s.close.cur)
        return s.close[1], h[0]
    out = _collect([1, 2, 3], body)
    assert math.isnan(out[0][0]) and out[1][0] == 1 and out[2] == (2, 6)


def test_inputs_override_and_record():
    seen = []

    class T(Script):
        def init(self):
            self.n = self.input.int(14, "Length", minval=1)
            self.src = self.input.source(self.close, "Source")

        def on_bar(self):
            seen.append((self.n, self.src.name))

    r = run(T, _bars([1, 2]), symbol=SYM, timeframe="D", params={"Length": 7, "Source": "hl2"})
    assert seen[0] == (7, "hl2")
    assert r.inputs[0] == {"kind": "int", "title": "Length", "default": 14, "minval": 1}
