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
             trail: Callable[[int, int, float, int], tuple | None] | None = None, tick: float = 0.01,
             log: list | None = None) -> list[tuple]:
    """Trades as (direction, entry_bar, entry_price, exit_bar, exit_price).
    ``trail(i, pos, entry_price, entry_bar) -> (points, offset)`` in TICKS (None = no trailing); ``tick`` = mintick.
    ``stop(i, pos, entry_price, entry_bar)`` / ``target(...)``: the bracket level working on
    bar i (None = none). ``on_close``: process_orders_on_close. ``slip``: price units added
    against the trader on market fills."""
    n = len(c)
    trades: list[tuple] = log if log is not None else []     # ``log``: the same list, readable by orders() while the run is in progress
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
    day = (local.dt.tz_localize(None) - pd.Timedelta(minutes=start_minutes)).dt.date.to_numpy()
    v = df["volume"].to_numpy()
    out, pv, vv = _np.empty(len(v)), 0.0, 0.0
    for i in range(len(v)):
        if i == 0 or day[i] != day[i - 1]:
            pv = vv = 0.0
        pv, vv = pv + src[i] * v[i], vv + v[i]
        out[i] = pv / vv
    return out


def np_dmi(h, l, c, n):
    """Pine ta.dmi(n, n) -> (+DI, -DI, ADX) from the textbook Wilder formulas (RMA of +DM/-DM over the RMA of tr; fixnan; RMA of |+DI - -DI|/sum)."""
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
        return plus, minus, np_rma(_np.abs(plus - minus) / _np.where(tot == 0, 1.0, tot), n) * 100


def np_adx(h, l, c, n):
    return np_dmi(h, l, c, n)[2]


def np_periods(df, minutes: int, start_minutes: int = 9 * 60 + 30, tz: str = "America/New_York"):
    """Higher-timeframe periods of intraday chart bars (pinelib/TradingView convention: blocks of ``minutes`` counted from the
    session start, per trading day). Returns (pid, last_of): the period index of each chart bar and whether it is the LAST
    chart bar of its period. request.security(..., lookahead off) shows a period's value on that last bar and the PREVIOUS
    period's value on the earlier bars."""
    import pandas as pd
    ny = pd.to_datetime(df["time"], unit="ms", utc=True).dt.tz_convert(tz)
    day = (ny.dt.tz_localize(None) - pd.Timedelta(minutes=start_minutes)).dt.date.to_numpy()
    slot = (((ny.dt.hour * 60 + ny.dt.minute - start_minutes) % 1440) // minutes).to_numpy()
    key = _np.array([f"{d}-{s}" for d, s in zip(day, slot)])
    pid = _np.cumsum(_np.r_[True, key[1:] != key[:-1]]) - 1
    last_of = _np.r_[key[1:] != key[:-1], True]
    return pid, last_of


def np_security_lookahead_off(values_per_period, pid, last_of):
    """Map one value per higher-timeframe period back to chart bars (lookahead off)."""
    out = _np.full(len(pid), _np.nan)
    for j in range(len(pid)):
        p = pid[j] if last_of[j] else pid[j] - 1
        if p >= 0:
            out[j] = values_per_period[p]
    return out


def simulate_pyr(o, h, l, c, orders, *, pyramiding: int = 1, stop=None, target=None, on_close: bool = False,
                 log: list | None = None) -> list[tuple]:
    """Multi-trade reference broker (1 unit per trade) for pyramiding strategies, written from Pine's documented rules and sharing no code with pinelib.
    ``orders(i, pos)`` -> list of ("entry", d) | ("close", d) | ("close_all",), in source order; ``pos`` is the signed number of open trades.
    entry: opposite trades are closed first (reversal); same-direction trades stack up to ``pyramiding`` (extra entries are ignored).
    close d: closes every open trade of direction d; close_all: everything. Market orders fill at the next open (or at the signal close if ``on_close``).
    ``stop(i, d, trades)`` / ``target(i, d, trades)``: the level working on bar i for the open trades of direction d (``trades`` = [(d, entry_bar, entry_price)]),
    None = none; all open trades of that direction exit together at the first level the bar's path touches (a gap fills at the open).
    Returns trades as (direction, entry_bar, entry_price, exit_bar, exit_price), appended in the order they close (oldest first within one close)."""
    n = len(c)
    trades: list[tuple] = log if log is not None else []
    open_: list[tuple] = []
    queue: list = []

    def close_trades(sel, i, px):
        nonlocal open_
        for t in [t for t in open_ if sel(t)]:
            trades.append((t[0], t[1], t[2], i, px))
        open_ = [t for t in open_ if not sel(t)]

    def fill(od, i, px):
        nonlocal open_
        if od[0] == "entry":
            d = od[1]
            if open_ and open_[0][0] == -d:
                close_trades(lambda t: True, i, px)
            elif open_ and len(open_) >= max(1, pyramiding):
                return
            open_.append((d, i, px))
        elif od[0] == "close":
            close_trades(lambda t: t[0] == od[1], i, px)
        else:
            close_trades(lambda t: True, i, px)

    for i in range(n):
        for od in queue:
            fill(od, i, o[i])
        queue = []
        if open_ and (stop or target):
            d = open_[0][0]
            sl = stop(i, d, list(open_)) if stop else None
            tp = target(i, d, list(open_)) if target else None
            hit = bracket_hit(o[i], h[i], l[i], c[i], d, sl, tp)
            if hit is not None:
                close_trades(lambda t: True, i, hit)
        emitted = orders(i, sum(t[0] for t in open_))
        if on_close:
            for od in emitted:
                fill(od, i, c[i])
        else:
            queue = emitted
    return trades


def np_cci(x, n):
    """Pine ta.cci: (src - sma) / (0.015 * mean absolute deviation) over n bars."""
    x = _np.asarray(x, float)
    out = _np.full(len(x), _np.nan)
    for i in range(n - 1, len(x)):
        w = x[i - n + 1:i + 1]
        mean = w.mean()
        dev = _np.abs(w - mean).mean()
        out[i] = (x[i] - mean) / (0.015 * dev) if dev != 0 else _np.nan
    return out


def simulate_ord(o, h, l, c, orders, *, log: list | None = None, on_close: bool = False) -> list[tuple]:
    """Reference broker with a PENDING ORDER BOOK (stop / limit entries, exits by entry id, cancels) for one net position
    (pyramiding 0/1), written from Pine's documented rules and sharing no code with pinelib.
    ``orders(i, pos)`` runs at bar i's close and returns actions in source order:
      ("entry", id, d, stop|None, limit|None)   market when both None, else a pending order kept until filled / replaced / cancelled
      ("exit", xid, from_id, stop|None, limit|None[, profit_pts|None, loss_pts|None])   attaches to the open trade with entry id ``from_id`` (or to its pending entry); replaces the exit with id xid
      ("entry", id, d, stop, limit, qty)        optional quantity (default 1), used by partial closes
      ("close", id) | ("close_all",)            market, at the next open (ignored when nothing is open at script time)
      ("close_part", id, qty)                   partial market close of qty units (one more closed-trade row; the exits keep working on the rest)
      ("cancel", id) | ("cancel_all",)
    Bar j: market orders fill at the open, then the pending orders are walked along the O->H->L->C (or O->L->H->C) path: whichever level is reached
    first fills (a level already passed at the open fills at the open), an entry's own exits are live straight after its fill, and an exit
    removes the exits of its trade. An opposite pending entry reverses; a same-direction one is ignored. ``on_close``: process_orders_on_close for the market orders. Returns (direction, entry_bar, entry_price, exit_bar, exit_price)."""
    n = len(c)
    trades: list[tuple] = log if log is not None else []
    cur = {"d": 0, "id": None, "ep": math.nan, "eb": -1, "q": 1.0}
    pend: list[dict] = []
    exits: dict = {}
    mq: list = []
    seq = [0]

    def close_pos(i, px, part=None):
        """Close the whole position, or ``part`` units of it (one more closed-trade row, the rest stays open)."""
        trades.append((cur["d"], cur["eb"], cur["ep"], i, px))
        if part is not None and part < cur["q"] - 1e-12:
            cur["q"] -= part
            return
        for k in [k for k, e in exits.items() if e["from"] == cur["id"]]:
            del exits[k]
        cur.update(d=0, id=None, ep=math.nan, eb=-1, q=1.0)

    def open_pos(i, d, eid, px, q=1.0):
        if cur["d"] == d:
            return
        if cur["d"] == -d:
            close_pos(i, px)
        cur.update(d=d, id=eid, ep=px, eb=i, q=q)

    def fire_market(i, px):
        for od in mq:
            if od[0] == "entry":
                open_pos(i, od[2], od[1], px, od[3])
            elif od[0] == "close_part" and cur["d"] != 0 and cur["id"] == od[1]:
                close_pos(i, px, od[2])
            elif od[0] == "close" and cur["d"] != 0 and cur["id"] == od[1]:
                close_pos(i, px)
            elif od[0] == "close_all" and cur["d"] != 0:
                close_pos(i, px)
        mq.clear()

    def hit(p0, p1, opening, lvl, rises_to_fill):
        """(distance, price) if the order level is reached on the segment p0->p1; rises_to_fill: filled when price is at/above the level."""
        if opening:
            if (p0 >= lvl) if rises_to_fill else (p0 <= lvl):
                return (0.0, p0)
            return None
        lo, hi = min(p0, p1), max(p0, p1)
        if lo <= lvl <= hi and ((p1 > p0) if rises_to_fill else (p1 < p0)):
            return (abs(lvl - p0), lvl)
        return None

    for i in range(n):
        fire_market(i, o[i])
        pts = _path(o[i], h[i], l[i], c[i])
        segs = [(pts[0], pts[0], True)] + [(pts[k - 1], pts[k], False) for k in range(1, 4) if pts[k] != pts[k - 1]]
        for p0, p1, opening in segs:
            while True:
                cands = []
                for od in pend:
                    d = od["d"]
                    if od["stop"] is not None and od["limit"] is not None:     # stop-limit: not supported by this reference
                        raise NotImplementedError
                    lvl, kind = (od["stop"], "stop") if od["stop"] is not None else (od["limit"], "limit")
                    rises = (d > 0) == (kind == "stop")
                    r = hit(p0, p1, opening, lvl, rises)
                    if r:       # a same-direction entry that triggers is consumed without opening anything (pyramiding limit)
                        cands.append((r[0], od["seq"], "entry", od, r[1]))
                if cur["d"] != 0:
                    for xid, e in exits.items():
                        if e["from"] != cur["id"]:
                            continue
                        xs, xl = e["stop"], e["limit"]
                        if xs is None and e.get("loss") is not None:        # relative levels: points from the trade's entry price
                            xs = cur["ep"] - cur["d"] * e["loss"]
                        if xl is None and e.get("profit") is not None:
                            xl = cur["ep"] + cur["d"] * e["profit"]
                        for lvl, kind in ((xs, "stop"), (xl, "limit")):
                            if lvl is None or lvl != lvl:
                                continue
                            rises = (cur["d"] < 0) == (kind == "stop")      # long stop / short limit trigger on falling price
                            r = hit(p0, p1, opening, lvl, rises)
                            if r:
                                cands.append((r[0], e["seq"], "exit", e, r[1]))
                if not cands:
                    break
                _, _, kind, od, px = min(cands, key=lambda x: (x[0], x[1]))
                if kind == "exit":
                    close_pos(i, px)
                else:
                    pend.remove(od)
                    open_pos(i, od["d"], od["id"], px, od["q"])
                if not (opening and px == p0):      # a fill inside the segment: carry on from the fill price (a gap fill at the open stays "opening")
                    opening = False
                p0 = px
        emitted = orders(i, cur["d"], dict(cur)) if orders.__code__.co_argcount >= 3 else orders(i, cur["d"])      # optional 3rd arg: the open trade {d, id, ep, eb}
        for a in emitted:
            seq[0] += 1
            if a[0] == "entry":
                eid, d, stop, limit = a[1:5]
                q = a[5] if len(a) > 5 else 1.0          # optional quantity (only matters for partial closes)
                pend[:] = [p for p in pend if p["id"] != eid]
                mq[:] = [m for m in mq if not (m[0] == "entry" and m[1] == eid)]
                if stop is None and limit is None:
                    mq.append(("entry", eid, d, q))
                else:
                    pend.append(dict(id=eid, d=d, stop=stop, limit=limit, q=q, seq=seq[0]))
            elif a[0] == "exit":
                xid, frm, stop, limit = a[1:5]
                profit, loss = (a[5], a[6]) if len(a) > 5 else (None, None)      # optional "profit" / "loss" in price points from the entry price
                if stop is None and limit is None and profit is None and loss is None:
                    exits.pop(xid, None)
                else:
                    exits[xid] = {"from": frm, "stop": stop, "limit": limit, "profit": profit, "loss": loss, "seq": seq[0]}
            elif a[0] == "close":
                if cur["d"] != 0:
                    mq.append(("close", a[1]))
            elif a[0] == "close_part":      # ("close_part", id, quantity): a partial market close
                if cur["d"] != 0:
                    mq.append(("close_part", a[1], a[2]))
            elif a[0] == "close_all":
                if cur["d"] != 0:
                    mq.append(("close_all",))
            elif a[0] == "cancel":
                pend[:] = [p for p in pend if p["id"] != a[1]]
                exits.pop(a[1], None)
            elif a[0] == "cancel_all":
                pend.clear()
                exits.clear()
        if on_close:        # process_orders_on_close: market orders fill at this bar's close (pending stop / limit orders still wait for the path)
            fire_market(i, c[i])
    return trades
