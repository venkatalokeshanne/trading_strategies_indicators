"""
``request.security`` on historical bars.

The requested expression is evaluated bar by bar on the REAL requested bars — a separate
execution with its own call-site state, exactly like Pine — and mapped back to chart bars:

  lookahead off (default): a higher-timeframe bar's value appears on the LAST chart bar of
    its period; earlier chart bars of the period show the previous period's value.
  lookahead on: every chart bar of the period shows the period's final value. That is
    look-ahead unless the expression itself is offset ([1]) — the repaint audit flags it.
  gaps on: the value only on the bar where it changes; na elsewhere.

Higher timeframes of the chart symbol are built from the chart's own bars (periods aligned
to the trading session). Another symbol is fetched at the chart timeframe through the
context's ``data_provider``, aligned to chart bar times, then treated the same way.
"""

from __future__ import annotations

import math
from typing import Any, Callable

import numpy as np
import pandas as pd

from .core import NA, Context, RT, fl, register_stop

_isnan = math.isnan


@register_stop
def _call_fn(fn: Callable, view: Any) -> Any:
    return fn(view)


def security_value(script, key: tuple, symbol: str | None, timeframe: str, fn: Callable,
                   lookahead: bool, gaps: bool) -> Any:
    c: Context = script._ctx
    cache_key = (key, symbol, timeframe, lookahead, gaps)
    mapped = c.security_cache.get(cache_key)
    if mapped is None:
        mapped = _build(script, symbol, timeframe, fn, lookahead, gaps)
        c.security_cache[cache_key] = mapped
    row = mapped[c.bar_index]
    return row


def _build(script, symbol: str | None, timeframe: str, fn: Callable, lookahead: bool, gaps: bool) -> list:
    from .runner import tf_seconds

    c: Context = script._ctx
    chart_tf = c.tf
    tf = timeframe or chart_tf
    same_symbol = symbol in (None, "", c.sym.tickerid, c.sym.ticker)

    # bars of the requested symbol at the CHART timeframe, aligned to chart bars
    if same_symbol:
        base = c.bars_df
    else:
        if c.data_provider is None:
            raise RuntimeError(f"request.security({symbol!r}) needs a data_provider")
        other = c.data_provider(symbol, chart_tf)
        base = _align(other, c.bars_df)

    if tf_seconds(tf) < tf_seconds(chart_tf):
        return _lower_tf(script, symbol, tf, fn)

    if tf_seconds(tf) == tf_seconds(chart_tf):
        values = _evaluate(script, base, fn, chart_tf)
        return values

    from .runner import _period_keys
    period = _period_keys(c, tf)
    htf = _resample(base, period)
    values = _evaluate(script, htf["bars"], fn, tf)
    group = htf["group"]                       # chart bar → HTF bar index
    n = c.n_bars
    out: list = [NA] * n
    prev_idx = None
    for i in range(n):
        k = group[i]
        last_of_period = (i == n - 1) or group[i + 1] != k
        if lookahead:
            src = k
        else:
            src = k if last_of_period else k - 1
        val = values[src] if src >= 0 else _na_like(values[0])
        if gaps:
            out[i] = val if src != prev_idx else _na_like(val)
        else:
            out[i] = val
        prev_idx = src
    return out


def _na_like(v: Any) -> Any:
    if isinstance(v, tuple):
        return tuple(NA for _ in v)
    return NA


def _resample(df: pd.DataFrame, period: list) -> dict:
    group: list[int] = []
    rows: list[dict] = []
    last_key = object()
    for i, key in enumerate(period):
        r = df.iloc[i]
        if key != last_key:
            rows.append({"time": int(r["time"]), "open": r["open"], "high": r["high"],
                         "low": r["low"], "close": r["close"], "volume": r["volume"]})
            last_key = key
        else:
            b = rows[-1]
            b["high"] = max(b["high"], r["high"]) if r["high"] == r["high"] else b["high"]
            b["low"] = min(b["low"], r["low"]) if r["low"] == r["low"] else b["low"]
            b["close"] = r["close"]
            b["volume"] = (b["volume"] if b["volume"] == b["volume"] else 0.0) + (r["volume"] if r["volume"] == r["volume"] else 0.0)
        group.append(len(rows) - 1)
    return {"bars": pd.DataFrame(rows), "group": group}


def _align(other: pd.DataFrame, chart: pd.DataFrame) -> pd.DataFrame:
    from .runner import _prepare
    o = _prepare(other).sort_values("time")
    left = chart[["time"]].copy()
    merged = pd.merge_asof(left, o, on="time", direction="backward")
    return merged


def _evaluate(script, bars: pd.DataFrame, fn: Callable, tf: str) -> list:
    from .runner import SeriesView
    sub = Context.from_bars(bars, script.syminfo, tf)
    sub.data_provider = script._ctx.data_provider
    view = SeriesView(sub, script.syminfo, tf)
    prev = RT.ctx
    RT.ctx = sub
    out = []
    try:
        for i in range(sub.n_bars):
            sub.bar_index = i
            v = _call_fn(fn, view)
            out.append(tuple(fl(x) for x in v) if isinstance(v, (tuple, list)) else
                       (v if isinstance(v, bool) else fl(v)))
    finally:
        RT.ctx = prev
    return out


def _lower_tf(script, symbol, tf, fn) -> list:
    """Chart bar → the expression's value on the LAST lower-timeframe bar inside it."""
    c = script._ctx
    if c.data_provider is None:
        raise RuntimeError("request.security on a lower timeframe needs a data_provider")
    ltf = c.data_provider(symbol or c.sym.tickerid, tf)
    from .runner import _prepare
    ltf = _prepare(ltf)
    values = _evaluate(script, ltf, fn, tf)
    lt = np.asarray(ltf["time"], dtype=np.int64)
    out = []
    times = c.time_arr
    for i in range(c.n_bars):
        end = times[i + 1] if i + 1 < c.n_bars else times[i] + c.tf_secs * 1000
        j = int(np.searchsorted(lt, end, side="left")) - 1
        out.append(values[j] if j >= 0 and lt[j] >= times[i] else NA)
    return out
