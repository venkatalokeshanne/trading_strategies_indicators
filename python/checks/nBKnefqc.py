"""Independent check — Liquidity Geography (nBKnefqc), daily bars, market entries at the next open, fixed 10 units unless the
risk-based sizing is on (explicit quantity from a mirror equity: initial capital + closed P&L + open P&L), commission / slippage 0.
Pivot pools (10 bars each side) or N-day extremes of the previous bar, the sweep rule, the balance / trend regime (EMA travel in ATR),
the weekly EMA(20) bias (ISO weeks of the New York clock, lookahead off), the confluence test against the previous day's extreme / round
numbers and the gap-fill module are rebuilt in numpy; the per-signal stop / limit orders are replayed against the quantity-aware
reference broker."""
import numpy as np
import pandas as pd

from indep import bars, compare_q, np_atr, np_ema, run_conversion, simulate_brackets
from pinelib import SymbolInfo

TV_ID = "nBKnefqc"
QTY = 10.0
CAP = 100000.0


def roll(x, n, fn):
    out = np.full(len(x), np.nan)
    for i in range(n - 1, len(x)):
        out[i] = fn(x[i - n + 1:i + 1])
    return out


def reference(df, pool="Pivot", mode="Adaptive (fade in balance, follow trend)", gap=False, min_gap=0.01, risk_sizing=False, opp=False,
              confluence=False, max_hold=0):
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    atr = np_atr(h, l, c, 14)
    ny = pd.to_datetime(df["time"], unit="ms", utc=True).dt.tz_convert("America/New_York")
    iso = (ny.dt.tz_localize(None) - pd.Timedelta(minutes=570)).dt.isocalendar()
    wk = (iso["year"].astype(int) * 100 + iso["week"].astype(int)).to_numpy()
    last_of = np.r_[wk[1:] != wk[:-1], True]
    pid = np.cumsum(np.r_[True, wk[1:] != wk[:-1]]) - 1
    wclose = pd.Series(c).groupby(pid).last().to_numpy()
    wema = np_ema(wclose, 20)
    bias = np.full(n, np.nan)
    for j in range(n):
        p = pid[j] if last_of[j] else pid[j] - 1
        if p >= 0:
            bias[j] = wema[p]
    ema20 = np_ema(c, 20)
    travel = np.abs(ema20 - np.r_[[np.nan] * 20, ema20[:-20]]) / atr
    nh = np.r_[np.nan, roll(h, 20, np.max)[:-1]]
    nl = np.r_[np.nan, roll(l, 20, np.min)[:-1]]
    S = dict(ph=np.nan, pl=np.nan, bars=None)
    log = []

    def eq(i, info):
        closed = sum(d * (xp - ep) * q for d, _, ep, _, xp, q in log)
        return CAP + closed + sum(x["d"] * x["q"] * (c[i] - x["ep"]) for x in info["lots"])

    def orders(i, info):
        out = []
        P = 10
        if i >= 2 * P:
            j = i - P
            w = h[j - P:j + P + 1]
            if h[j] == w.max() and (w == h[j]).sum() == 1:
                S["ph"] = h[j]
            w = l[j - P:j + P + 1]
            if l[j] == w.min() and (w == l[j]).sum() == 1:
                S["pl"] = l[j]
        lh = S["ph"] if pool == "Pivot" else nh[i]
        ll = S["pl"] if pool == "Pivot" else nl[i]
        bull = not np.isnan(ll) and l[i] < ll and c[i] > ll
        bear = not np.isnan(lh) and h[i] > lh and c[i] < lh
        trending = travel[i] >= 2.0
        balance = not trending
        bu = not np.isnan(bias[i]) and c[i] > bias[i]
        bd = not np.isnan(bias[i]) and c[i] < bias[i]
        lok = {"Off": True, "Balance only": balance, "Trend-aligned only": bu}.get(mode, balance or bu)
        sok = {"Off": True, "Balance only": balance, "Trend-aligned only": bd}.get(mode, balance or bd)
        step = 10 ** np.floor(np.log10(c[i]))
        tol = 0.5 * atr[i]
        pdh, pdl = (h[i - 1], l[i - 1]) if i else (np.nan, np.nan)
        rnd = lambda x: np.floor(x / step + 0.5) * step
        lconf = (not confluence) or np.isnan(ll) or abs(ll - pdl) <= tol or abs(ll - rnd(ll)) <= tol
        sconf = (not confluence) or np.isnan(lh) or abs(lh - pdh) <= tol or abs(lh - rnd(lh)) <= tol
        flat = info["pos"] == 0
        took = False
        pc = c[i - 1] if i else np.nan
        if gap and flat:
            if o[i] < pc * (1 - min_gap) and travel[i] < 2.0:
                stop = c[i] - atr[i]
                q = eq(i, info) * 0.01 / (c[i] - stop) if risk_sizing and c[i] - stop > 0 else QTY
                out += [("entry", "Gap Long", 1, q), ("exit", "Gap Long Exit", "Gap Long", None, stop, pc)]
                took = True
            elif o[i] > pc * (1 + min_gap) and travel[i] < 2.0:
                stop = c[i] + atr[i]
                q = eq(i, info) * 0.01 / (stop - c[i]) if risk_sizing and stop - c[i] > 0 else QTY
                out += [("entry", "Gap Short", -1, q), ("exit", "Gap Short Exit", "Gap Short", None, stop, pc)]
                took = True
        if flat and not took:
            if bull and lok and lconf:
                stop = l[i] - 0.25 * atr[i]
                r = c[i] - stop
                tgt = lh if opp and not np.isnan(lh) and lh > c[i] else c[i] + 2.0 * r
                q = eq(i, info) * 0.01 / r if risk_sizing and r > 0 else QTY
                out += [("entry", "Sweep Long", 1, q), ("exit", "Sweep Long Exit", "Sweep Long", None, stop, tgt)]
            elif bear and sok and sconf:
                stop = h[i] + 0.25 * atr[i]
                r = stop - c[i]
                tgt = ll if opp and not np.isnan(ll) and ll < c[i] else c[i] - 2.0 * r
                q = eq(i, info) * 0.01 / r if risk_sizing and r > 0 else QTY
                out += [("entry", "Sweep Short", -1, q), ("exit", "Sweep Short Exit", "Sweep Short", None, stop, tgt)]
        if max_hold and info["pos"] != 0 and info["lots"] and i - info["lots"][0]["eb"] >= max_hold:
            out.append(("close_all",))
        return out

    return simulate_brackets(o, h, l, c, orders, pyramiding=1, log=log)


def check():
    df = bars(9000, seed=27, freq="D")
    lc = np.log(df["close"].to_numpy() / 100)
    det = lc - np.polyval(np.polyfit(np.arange(len(lc)), lc, 1), np.arange(len(lc)))
    rel = {k: df[k].to_numpy() / df["close"].to_numpy() for k in ("open", "high", "low", "close")}
    for k in rel:
        df[k] = 100 * np.exp(0.5 * det) * rel[k] ** 0.5
    sym = SymbolInfo.make("NASDAQ:XYZ", "stock", qty_step=1e-9)
    ov = {"margin_long": 0, "margin_short": 0, "commission_value": 0, "slippage": 0, "default_qty_type": "fixed", "default_qty_value": QTY,
          "initial_capital": CAP}
    cases = (({}, {}),
             ({"Liquidity pool source": "N-day high/low", "Sweep regime filter (Tier 1)": "Off", "Require confluence (Tier 2)": True},
              dict(pool="N-day high/low", mode="Off", confluence=True)),
             ({"Enable Gap-Fill module": True, "Min gap size %": 0.5, "Risk-based position sizing (Tier 3)": True,
               "Target = opposite liquidity (overrides RR)": True, "Max holding bars (0 = off)": 15},
              dict(gap=True, min_gap=0.005, risk_sizing=True, opp=True, max_hold=15)))
    msgs, ok_all = [], True
    for params, kw in cases:
        ref = reference(df, **kw)
        ok, d = compare_q(run_conversion(TV_ID, df, symbol=sym, tf="D", params=params, strategy_overrides=ov), ref, tol=1e-7)
        ok_all = ok_all and ok and len(ref) > 12
        msgs.append(f"{d} (got {len(ref)})")
    return ok_all, " | ".join(msgs)
