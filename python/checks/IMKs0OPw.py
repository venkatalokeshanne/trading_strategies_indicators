"""Independent check — Volatility Reversion Scalper (IMKs0OPw): 5-min bars. Williams-VIX-fix style wvf vs its 25th percentile
(NOTE the original's swapped arguments: window length 99 / 101, percentile 25), price under the 0.618-sigma lower band and a
bullish reversal candle; long-only, 5 % limit target on the average price, placed at the close of the bar in the position."""
import numpy as np

from indep import bars, compare, np_sma, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "IMKs0OPw"


def roll(x, n, fn):
    out = np.full(len(x), np.nan)
    for i in range(n - 1, len(x)):
        w = x[i - n + 1:i + 1]
        if not np.isnan(w).any():
            out[i] = fn(w)
    return out


def check():
    df = bars(12000, seed=86, freq="5min")
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    hi11 = roll(c, 11, np.max)
    wvf = (hi11 - l) / hi11 * 100
    rh = roll(wvf, 99, lambda w: np.percentile(w, 25))           # swapped arguments: length 99, percentage 25
    rl = roll(wvf, 101, lambda w: np.percentile(w, 25))
    with np.errstate(invalid="ignore"):
        vix = np.where(wvf >= rh, 1, np.where(wvf <= rl, -1, 0))
    basis = np_sma(c, 10)
    dev = 0.618 * roll(c, 10, np.std)
    lower = basis - dev
    pc, po = np.r_[np.nan, c[:-1]], np.r_[np.nan, o[:-1]]
    with np.errstate(invalid="ignore"):
        buy = ((c <= lower) | (o <= lower)) & (vix == 1) & (c > o) & (pc < po)
    ref = simulate(o, h, l, c, lambda i, pos: [("entry", 1)] if buy[i] else [],
                   target=lambda i, pos, ep, eb: ep * 1.05 if i > eb else None)
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="5", params={"Start Date": 0, "End Date": 2 ** 60}), ref)
    return ok and len(ref) > 10, f"{detail} (need >10 trades, got {len(ref)})"
