"""Independent check — Liquidity Sweep & RSI Divergence (zCYYilCg): hourly synthetic bars with small bodies and long wicks (so dojis are common). Dragonfly doji (body <= 10 % of range, lower wick >= 70 %, upper wick <= 10 %)
whose low is below the lowest low of the previous 50 bars while RSI14 is above the lowest RSI of the previous 50 bars goes long when flat (gravestone mirrored). Entry + exit (stop = bar low / high, limit = 2.5 R) are issued on the
signal bar, so the bracket works from the fill bar; quantity (fixed $50 risk) never moves prices. Margin off on the pinelib side."""
import numpy as np
import pandas as pd

from indep import compare, np_rsi, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "zCYYilCg"


def doji_bars(n, seed):
    rng = np.random.default_rng(seed)
    close = 100 * np.exp(np.cumsum(rng.normal(0, 0.006, n)))
    open_ = np.r_[close[0], close[:-1]] * (1 + rng.normal(0, 0.0004, n))
    body_hi, body_lo = np.maximum(open_, close), np.minimum(open_, close)
    up = np.abs(rng.normal(0, 0.012, n)) * (rng.random(n) < 0.55)
    dn = np.abs(rng.normal(0, 0.012, n)) * (rng.random(n) < 0.55)
    t = pd.date_range("2015-01-01", periods=n, freq="1h", tz="UTC").as_unit("ms").asi8
    return pd.DataFrame({"time": t, "open": open_, "high": body_hi * (1 + up), "low": body_lo * (1 - dn), "close": close,
                         "volume": rng.integers(1000, 100000, n).astype(float)})


def check():
    df = doji_bars(40000, 274)
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    rsi = np_rsi(c, 14)
    rng = h - l
    body, uw, lw = np.abs(o - c), h - np.maximum(o, c), np.minimum(o, c) - l
    with np.errstate(invalid="ignore"):
        doji = (rng > 0) & (body <= rng * 0.10)
        drag = doji & (lw >= rng * 0.70) & (uw <= rng * 0.10)
        grave = doji & (uw >= rng * 0.70) & (lw <= rng * 0.10)
    pl = pd.Series(l).shift(1).rolling(50).min().to_numpy()
    ph = pd.Series(h).shift(1).rolling(50).max().to_numpy()
    # ta.lowest / ta.highest skip na values but need a full window of bars: RSI is na for its first 14 bars
    prl = pd.Series(rsi).shift(1).rolling(50, min_periods=1).min().to_numpy().copy()
    prh = pd.Series(rsi).shift(1).rolling(50, min_periods=1).max().to_numpy().copy()
    prl[:50] = np.nan
    prh[:50] = np.nan
    with np.errstate(invalid="ignore"):
        ls = drag & (l < pl) & (rsi > prl)
        ss = grave & (h > ph) & (rsi < prh)
    lvl = {1: (np.nan, np.nan), -1: (np.nan, np.nan)}

    def orders(i, pos):
        out = []
        if ls[i] and pos == 0 and abs(c[i] - l[i]) > 0:
            out.append(("entry", 1)); lvl[1] = (l[i], c[i] + abs(c[i] - l[i]) * 2.5)
        if ss[i] and pos == 0 and abs(h[i] - c[i]) > 0:
            out.append(("entry", -1)); lvl[-1] = (h[i], c[i] - abs(h[i] - c[i]) * 2.5)
        return out

    with np.errstate(invalid="ignore"):
        ref = simulate(o, h, l, c, orders, stop=lambda i, pos, ep, eb: lvl[pos][0], target=lambda i, pos, ep, eb: lvl[pos][1])
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="60", strategy_overrides={"margin_long": 0, "margin_short": 0}), ref)
    return ok and len(ref) > 5, f"{detail} (need >5 trades, got {len(ref)})"
