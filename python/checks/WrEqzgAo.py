"""Independent check — PPO Divergence (WrEqzgAo): daily bars. PPO = (EMA12 - EMA26) / EMA26 * 100. Pivots (5 bars each side, strict, no na in the window) of price and of PPO are confirmed 5 bars later; the last two price pivot lows
and their PPO values (taken at the same confirmation bars, possibly na) give bullish divergence when the price low is lower and the PPO low higher (bearish mirrored). Signal only on the confirmation bar of a new PRICE pivot.
Entry + exit (2 % stop, 4 % target around the signal close) are issued on the signal bar, so the bracket works from the fill bar. Margin off on the pinelib side."""
import numpy as np

from indep import bars, compare, np_ema, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "WrEqzgAo"
K = 5


def pivots(x, high):
    n = len(x)
    out = np.full(n, np.nan)                                 # value at the confirmation bar
    for i in range(2 * K, n):
        j = i - K
        w = x[j - K:i + 1]
        if np.isnan(w).any():
            continue
        if high and x[j] > x[j - K:j].max() and x[j] > x[j + 1:i + 1].max():
            out[i] = x[j]
        if (not high) and x[j] < x[j - K:j].min() and x[j] < x[j + 1:i + 1].min():
            out[i] = x[j]
    return out


def check():
    df = bars(40000, seed=279)
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    s = np_ema(c, 26)
    ppo = (np_ema(c, 12) - s) / s * 100
    phi, plo = pivots(h, True), pivots(l, False)
    ppi, ppl = pivots(ppo, True), pivots(ppo, False)
    pl = dict(last_p=np.nan, last_o=np.nan, prev_p=np.nan, prev_o=np.nan)
    ph = dict(last_p=np.nan, last_o=np.nan, prev_p=np.nan, prev_o=np.nan)
    lvl = {1: (np.nan, np.nan), -1: (np.nan, np.nan)}

    def orders(i, pos):
        if not np.isnan(plo[i]):
            pl.update(prev_p=pl["last_p"], prev_o=pl["last_o"], last_p=plo[i], last_o=ppl[i])
        if not np.isnan(phi[i]):
            ph.update(prev_p=ph["last_p"], prev_o=ph["last_o"], last_p=phi[i], last_o=ppi[i])
        out = []
        with np.errstate(invalid="ignore"):
            bull = (not np.isnan(plo[i])) and pl["last_p"] < pl["prev_p"] and pl["last_o"] > pl["prev_o"]
            bear = (not np.isnan(phi[i])) and ph["last_p"] > ph["prev_p"] and ph["last_o"] < ph["prev_o"]
        if bull:
            out.append(("entry", 1)); lvl[1] = (c[i] * 0.98, c[i] * 1.04)
        if bear:
            out.append(("entry", -1)); lvl[-1] = (c[i] * 1.02, c[i] * 0.96)
        return out

    ref = simulate(o, h, l, c, orders, stop=lambda i, pos, ep, eb: lvl[pos][0], target=lambda i, pos, ep, eb: lvl[pos][1])
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="D", strategy_overrides={"margin_long": 0, "margin_short": 0}), ref)
    return ok and len(ref) > 10, f"{detail} (need >10 trades, got {len(ref)})"
