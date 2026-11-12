"""Independent check — XAUUSD UT Bot (bXMbB82A): 15-min bars. xATR = ATR(1) = true range (first bar high-low), nLoss = 2*xATR; the trailing stop follows the UT Bot rules against the previous bar's stop (comparisons with na are false: bar 0 takes the else branch);
pos flips to +1 when close crosses above the previous stop, to -1 below; a buy is a flip to +1 from -1. Long when buy, close > the 1h EMA200 of closes (09:30-NY 60-minute blocks, lookahead off) and ADX14 > 25; entry at the next open with limit +1.5% / stop -1% of the signal
close (fixed, pyramiding 1: a signal while long is ignored but replaces the levels)."""
import numpy as np

from indep import bars, compare, np_dmi, np_ema, np_periods, np_security_lookahead_off, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "bXMbB82A"


def check():
    df = bars(16000, seed=75, freq="15min")
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    c1 = np.r_[np.nan, c[:-1]]
    tr = np.where(np.isnan(c1), h - l, np.maximum(h - l, np.maximum(np.abs(h - c1), np.abs(l - c1))))
    nloss = 2.0 * tr
    xts = np.full(n, np.nan)
    pos = np.zeros(n, int)
    p = 0
    prev = np.nan
    with np.errstate(invalid="ignore"):
        for i in range(n):
            cur = max(c[i] - nloss[i], 0.0)
            pc = c[i - 1] if i else np.nan
            if pc > prev and c[i] > prev:
                cur = max(prev, c[i] - nloss[i])
            elif pc < prev and c[i] < prev:
                cur = min(prev, c[i] + nloss[i])
            else:
                cur = c[i] - nloss[i] if c[i] > prev else c[i] + nloss[i]
            if c[i] > prev and pc <= prev:
                p = 1
            elif c[i] < prev and pc >= prev:
                p = -1
            pos[i] = p
            xts[i] = cur
            prev = cur
    buy = (pos == 1) & (np.r_[0, pos[:-1]] == -1)
    pid, last_of = np_periods(df, 60)
    pcl = np.array([c[last_of & (pid == k)][0] for k in range(pid[-1] + 1)])
    htf = np_security_lookahead_off(np_ema(pcl, 200), pid, last_of)
    dp, dm, adx = np_dmi(h, l, c, 14)
    with np.errstate(invalid="ignore"):
        sig = buy & (c > htf) & (adx > 25)
    lvl = {}

    def orders(i, pos_):
        if sig[i]:
            lvl[1] = (c[i] * 0.99, c[i] * 1.015)
            return [("entry", 1)]
        return []

    def stop(i, pos_, ep, eb):
        return lvl[1][0] if 1 in lvl else None

    def target(i, pos_, ep, eb):
        return lvl[1][1] if 1 in lvl else None

    with np.errstate(invalid="ignore"):
        ref = simulate(o, h, l, c, orders, stop=stop, target=target)
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="15", strategy_overrides={"margin_long": 0, "margin_short": 0}), ref)
    return ok and len(ref) > 10, f"{detail} (need >10 trades, got {len(ref)})"
