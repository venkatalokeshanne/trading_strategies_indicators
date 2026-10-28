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


def exit_hit(o, h, l, c, pos, sl, tp, trail, st):
    """Like bracket_hit, plus Pine's trailing stop. ``trail`` = (activation_price, offset_price) or None;
    ``st`` is the per-position dict holding the trailing extreme between bars (key "ext").
    Walks the same O->(H|L)->(L|H)->C path segment by segment: the trailing extreme moves to the best price of
    each segment once the activation price has been reached; the stop then sits ``offset`` behind it and fills
    when a segment moves down through it (long) / up through it (short); gaps fill at the open."""
    pts = _path(o, h, l, c)
    segs = [(o, o, True)] + [(pts[k - 1], pts[k], False) for k in range(1, len(pts)) if pts[k] != pts[k - 1]]
    for p0, p1, opening in segs:
        lvl_trail = None
        if trail is not None:
            best = max(p0, p1) if pos > 0 else min(p0, p1)
            ext = st.get("ext")
            if ext is None:
                if (best >= trail[0]) if pos > 0 else (best <= trail[0]):
                    ext = best
            else:
                ext = max(ext, best) if pos > 0 else min(ext, best)
            if ext is not None:
                st["ext"] = ext
                lvl_trail = ext - pos * trail[1]
        lo, hi = min(p0, p1), max(p0, p1)
        up = p1 >= p0
        cands = []
        for kind, lvl in (("tp", tp), ("sl", sl), ("sl", lvl_trail)):
            if lvl is None or lvl != lvl:
                continue
            favourable = kind == "tp"
            beyond = (p0 >= lvl) if (pos > 0) == favourable else (p0 <= lvl)      # long limit / short stop: price above
            if opening:
                if beyond:
                    cands.append((0.0, p0))
            else:
                moving_right_way = up if (pos > 0) == favourable else (not up)
                if lo <= lvl <= hi and moving_right_way:
                    cands.append((abs(lvl - p0), lvl))
        if cands:
            return min(cands, key=lambda x: x[0])[1]
    return None


def simulate(o: Sequence[float], h: Sequence[float], l: Sequence[float], c: Sequence[float],
             orders: Callable[[int, int], list], *,
             stop: Callable[[int, int, float, int], float | None] | None = None,
             target: Callable[[int, int, float, int], float | None] | None = None,
             on_close: bool = False, slip: float = 0.0,
             trail: Callable[[int, int, float, int], tuple | None] | None = None, tick: float = 0.01) -> list[tuple]:
    """Trades as (direction, entry_bar, entry_price, exit_bar, exit_price).
    ``trail(i, pos, entry_price, entry_bar) -> (points, offset)`` in TICKS (None = no trailing); ``tick`` = mintick.
    ``stop(i, pos, entry_price, entry_bar)`` / ``target(...)``: the bracket level working on
    bar i (None = none). ``on_close``: process_orders_on_close. ``slip``: price units added
    against the trader on market fills."""
    n = len(c)
    trades: list[tuple] = []
    pos, ep, eb = 0, math.nan, -1
    tst: dict = {}
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
            tst.clear()
        elif kind == "close" and pos == d:
            trades.append((pos, eb, ep, i, px - slip * pos))
            pos = 0

    for i in range(n):
        for od in queue:                       # orders from the previous close, at this open
            fill(od, i, o[i])
        queue = []
        if pos != 0 and (stop or target or trail):
            sl = stop(i, pos, ep, eb) if stop else None
            tp = target(i, pos, ep, eb) if target else None
            tr = trail(i, pos, ep, eb) if trail else None
            if tr is not None:
                tr = (ep + pos * tr[0] * tick, tr[1] * tick)
            hit = exit_hit(o[i], h[i], l[i], c[i], pos, sl, tp, tr, tst) if trail else bracket_hit(o[i], h[i], l[i], c[i], pos, sl, tp)
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


def np_wma(x, n):
    x = _np.asarray(x, float)
    w = _np.arange(1, n + 1, dtype=float)
    out = _np.full(len(x), _np.nan)
    for i in range(n - 1, len(x)):
        out[i] = (x[i - n + 1:i + 1] * w).sum() / w.sum()
    return out


def np_supertrend(h, l, c, factor, n):
    """Pine ta.supertrend reference: (line, direction), direction -1 = up-trend."""
    h, l, c = (_np.asarray(v, float) for v in (h, l, c))
    atr = np_atr(h, l, c, n)
    src = (h + l) / 2
    m = len(c)
    up, lo = src + factor * atr, src - factor * atr
    line, d = _np.full(m, _np.nan), _np.full(m, _np.nan)
    for i in range(m):
        plo = lo[i - 1] if i and not _np.isnan(lo[i - 1]) else 0.0
        pup = up[i - 1] if i and not _np.isnan(up[i - 1]) else 0.0
        pc = c[i - 1] if i else _np.nan
        if not (lo[i] > plo or pc < plo):
            lo[i] = plo
        if not (up[i] < pup or pc > pup):
            up[i] = pup
        if i == 0 or _np.isnan(atr[i - 1]):
            d[i] = 1
        elif line[i - 1] == pup:
            d[i] = -1 if c[i] > up[i] else 1
        else:
            d[i] = 1 if c[i] < lo[i] else -1
        line[i] = lo[i] if d[i] == -1 else up[i]
    return line, d


def np_vwap(df, src, start_minutes: int = 9 * 60 + 30, tz: str = "America/New_York"):
    """Pine ta.vwap(src): volume-weighted mean of ``src``, reset at each session start
    (default 09:30 New York, the stock session pinelib assumes)."""
    import pandas as pd
    local = pd.to_datetime(df["time"], unit="ms", utc=True).dt.tz_convert(tz)
    day = (local - pd.Timedelta(minutes=start_minutes)).dt.date.to_numpy()
    v = df["volume"].to_numpy()
    out, pv, vv = _np.empty(len(v)), 0.0, 0.0
    for i in range(len(v)):
        if i == 0 or day[i] != day[i - 1]:
            pv = vv = 0.0
        pv, vv = pv + src[i] * v[i], vv + v[i]
        out[i] = pv / vv
    return out


def np_adx(h, l, c, n):
    """Pine ta.dmi(n, n) ADX from the textbook Wilder formulas (RMA of +DM/-DM over the RMA of tr; fixnan; RMA of |+DI - -DI|/sum)."""
    h, l, c = (_np.asarray(v, float) for v in (h, l, c))
    up = _np.r_[_np.nan, _np.diff(h)]
    down = -_np.r_[_np.nan, _np.diff(l)]
    pdm = _np.where(_np.isnan(up), _np.nan, _np.where((up > down) & (up > 0), up, 0.0))
    mdm = _np.where(_np.isnan(down), _np.nan, _np.where((down > up) & (down > 0), down, 0.0))
    trur = np_rma(np_tr(h, l, c, False), n)

    def ffill(x):
        out = x.copy()
        for i in range(1, len(out)):
            if _np.isnan(out[i]):
                out[i] = out[i - 1]
        return out

    with _np.errstate(divide="ignore", invalid="ignore"):
        plus = ffill(100 * np_rma(pdm, n) / trur)
        minus = ffill(100 * np_rma(mdm, n) / trur)
        tot = plus + minus
        return np_rma(_np.abs(plus - minus) / _np.where(tot == 0, 1.0, tot), n) * 100
