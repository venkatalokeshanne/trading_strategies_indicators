"""
Independent reference broker for validating conversions (LESSONS P0).

Shares NO code with pinelib: a deliberately small re-implementation of Pine's documented
rules for the common cases —
  * the script runs at bar i's close and emits orders in SOURCE ORDER;
  * market orders fill one after another at bar i+1's open;
  * strategy.entry: ignored if already in that direction (pyramiding 0/1), reverses an
    opposite position; strategy.close: closes a position in that direction;
  * optional per-position stop/target brackets on the open→high→low→close or
    open→low→high→close path (high nearer the open first); a gap fills at the open.

A conversion's check computes its conditions with plain pandas from the PINE source and
supplies ``orders(i, pos) -> list`` in the Pine call order, e.g.
    lambda i, pos: ([("entry", 1)] if buy[i] else []) + ([("close", 1)] if sell[i] else [])
"""

from __future__ import annotations

import math
from typing import Callable, Sequence


def _path(o: float, h: float, l: float, c: float) -> list[float]:
    return [o, h, l, c] if (h - o) < (o - l) else [o, l, h, c]


def bracket_hit(o: float, h: float, l: float, c: float, pos: int, sl, tp):
    """Fill price of the first bracket level (stop ``sl`` / target ``tp``, None or nan = absent)
    touched on this bar's OHLC path by a position of direction ``pos``; None if neither."""
    pts = _path(o, h, l, c)
    for k, p in enumerate(pts):
        prev = pts[k - 1] if k else p
        lo, hi = min(prev, p), max(prev, p)
        cands = []
        for lvl, is_stop in ((sl, True), (tp, False)):
            if lvl is None or lvl != lvl:
                continue
            adverse = (pos > 0) == is_stop      # long stop / short target are below
            if k == 0:
                if (adverse and p <= lvl) or (not adverse and p >= lvl):
                    cands.append((0.0, p))
            elif lo <= lvl <= hi and ((adverse and p < prev) or (not adverse and p > prev)):
                cands.append((abs(lvl - prev), lvl))
        if cands:
            return min(cands)[1]
    return None


def simulate(o: Sequence[float], h: Sequence[float], l: Sequence[float], c: Sequence[float],
             orders: Callable[[int, int], list], *,
             stop: Callable[[int, int, float, int], float | None] | None = None,
             target: Callable[[int, int, float, int], float | None] | None = None,
             on_close: bool = False, slip: float = 0.0) -> list[tuple]:
    """Trades as (direction, entry_bar, entry_price, exit_bar, exit_price).
    ``stop(i, pos, entry_price, entry_bar)`` / ``target(...)``: the bracket level working on
    bar i (None = none). ``on_close``: process_orders_on_close. ``slip``: price units added
    against the trader on market fills."""
    n = len(c)
    trades: list[tuple] = []
    pos, ep, eb = 0, math.nan, -1
    queue: list = []

    def fill(order, i, px):
        nonlocal pos, ep, eb
        kind, d = order
        if kind == "entry":
            if pos == d:
                return
            if pos == -d:
                trades.append((pos, eb, ep, i, px - slip * pos))
            pos, ep, eb = d, px + slip * d, i
        elif kind == "close" and pos == d:
            trades.append((pos, eb, ep, i, px - slip * pos))
            pos = 0

    for i in range(n):
        for od in queue:                       # orders from the previous close, at this open
            fill(od, i, o[i])
        queue = []
        if pos != 0 and (stop or target):
            sl = stop(i, pos, ep, eb) if stop else None
            tp = target(i, pos, ep, eb) if target else None
            hit = bracket_hit(o[i], h[i], l[i], c[i], pos, sl, tp)
            if hit is not None:
                trades.append((pos, eb, ep, i, hit))
                pos = 0
        emitted = orders(i, pos)
        if on_close:
            for od in emitted:
                fill(od, i, c[i])
        else:
            queue = emitted
    return trades


def from_pinelib(res) -> list[tuple]:
    return [(t.direction, t.entry_bar, t.entry_price, t.exit_bar, t.exit_price) for t in res.broker.closed]


def compare(res, ref: list[tuple], tol: float = 1e-9) -> tuple[bool, str]:
    ours = from_pinelib(res)
    if len(ours) != len(ref):
        return False, f"trade count differs: pinelib {len(ours)} vs independent {len(ref)}; first diff {_first(ours, ref)}"
    for a, b in zip(ours, ref):
        if a[0] != b[0] or a[1] != b[1] or a[3] != b[3] or abs(a[2] - b[2]) > tol * max(1, abs(b[2])) \
                or abs(a[4] - b[4]) > tol * max(1, abs(b[4])):
            return False, f"first differing trade: pinelib {a} vs independent {b}"
    return True, f"{len(ours)} trades identical"


def _first(a, b):
    for x, y in zip(a, b):
        if x[:2] != y[:2] or x[3] != y[3]:
            return {"pinelib": x, "independent": y}
    return {"pinelib": a[len(b):len(b) + 1], "independent": b[len(a):len(a) + 1]}


# ─────────────────────────────────────────────────────────────── shared check helpers
# Plain numpy re-statements of Pine's documented formulas — NOT pinelib.
import numpy as _np


def bars(n: int = 3000, seed: int = 11, freq: str = "D"):
    """Deterministic synthetic OHLCV (trending + choppy phases) as a DataFrame."""
    import pandas as pd
    rng = _np.random.default_rng(seed)
    drift = _np.where((_np.arange(n) // 400) % 2 == 0, 0.0008, -0.0004)
    close = 100 * _np.exp(_np.cumsum(drift + rng.normal(0, 0.017, n)))
    open_ = _np.concatenate([[close[0]], close[:-1]]) * (1 + rng.normal(0, 0.004, n))
    high = _np.maximum(open_, close) * (1 + _np.abs(rng.normal(0, 0.009, n)))
    low = _np.minimum(open_, close) * (1 - _np.abs(rng.normal(0, 0.009, n)))
    t = pd.date_range("2015-01-01", periods=n, freq=freq, tz="UTC").as_unit("ms").asi8
    return pd.DataFrame({"time": t, "open": open_, "high": high, "low": low, "close": close,
                         "volume": rng.integers(1000, 100000, n).astype(float)})


def np_sma(x, n):
    x = _np.asarray(x, float)
    out = _np.full(len(x), _np.nan)
    for i in range(n - 1, len(x)):
        w = x[i - n + 1:i + 1]
        if not _np.isnan(w).any():
            out[i] = w.mean()
    return out


def _recursive(x, n, alpha):
    x = _np.asarray(x, float)
    out = _np.full(len(x), _np.nan)
    prev = _np.nan
    for i in range(len(x)):
        if _np.isnan(prev):
            if i >= n - 1 and not _np.isnan(x[i - n + 1:i + 1]).any():
                prev = x[i - n + 1:i + 1].mean()
                out[i] = prev
        else:
            prev = alpha * x[i] + (1 - alpha) * prev
            out[i] = prev
    return out


def np_ema(x, n):
    return _recursive(x, n, 2 / (n + 1))


def np_rma(x, n):
    return _recursive(x, n, 1 / n)


def np_cross_over(a, b):
    a, b = _np.asarray(a, float), _np.broadcast_to(_np.asarray(b, float), _np.shape(a))
    pa, pb = _np.r_[_np.nan, a[:-1]], _np.r_[_np.nan, b[:-1]]
    return (a > b) & (pa <= pb)


def np_cross_under(a, b):
    a, b = _np.asarray(a, float), _np.broadcast_to(_np.asarray(b, float), _np.shape(a))
    pa, pb = _np.r_[_np.nan, a[:-1]], _np.r_[_np.nan, b[:-1]]
    return (a < b) & (pa >= pb)


def load_conversion(tv_id: str):
    import sys
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(root / "python"))
    from tradesearch.catalog import load_script
    hits = sorted((root / "python").glob(f"*/{tv_id}*.py"))
    hits = [h for h in hits if h.parent.name in ("strategies", "indicators")]
    return load_script(hits[0])


def run_conversion(tv_id: str, df, symbol=None, tf: str = "D", **kw):
    from pinelib import SymbolInfo, run
    return run(load_conversion(tv_id), df, symbol=symbol or SymbolInfo.make("TEST:SYNTH", "crypto", qty_step=1e-9),
               timeframe=tf, **kw)


def np_tr(h, l, c, handle_na=True):
    h, l, c = (_np.asarray(x, float) for x in (h, l, c))
    pc = _np.r_[_np.nan, c[:-1]]
    tr = _np.fmax(h - l, _np.fmax(_np.abs(h - pc), _np.abs(l - pc)))
    tr[0] = h[0] - l[0] if handle_na else _np.nan
    return tr


def np_atr(h, l, c, n):
    return np_rma(np_tr(h, l, c, True), n)


def np_rsi(x, n):
    x = _np.asarray(x, float)
    ch = _np.r_[_np.nan, _np.diff(x)]
    u = _np.where(_np.isnan(ch), _np.nan, _np.maximum(ch, 0))
    d = _np.where(_np.isnan(ch), _np.nan, _np.maximum(-ch, 0))
    ru, rd = np_rma(u, n), np_rma(d, n)
    with _np.errstate(divide="ignore", invalid="ignore"):
        r = 100 - 100 / (1 + ru / rd)
    r[(rd == 0) & ~_np.isnan(ru)] = 100.0
    return r


def np_stoch(c, h, l, n):
    import pandas as pd
    hh = pd.Series(h).rolling(n).max().to_numpy()
    ll = pd.Series(l).rolling(n).min().to_numpy()
    with _np.errstate(divide="ignore", invalid="ignore"):
        k = 100 * (_np.asarray(c) - ll) / (hh - ll)
    k[~_np.isfinite(k)] = _np.nan
    return k
