"""Independent check — BTC 4H RSI + Bullish Engulfing (bmIiC79T): 5-min bars, long only. RSI<30 and a bullish engulfing candle opens a
trade when flat. While in the trade the exit is re-issued every bar (so bar i uses bar i-1's values, from the bar after the fill):
stop = that bar's low * 0.995; target = max(close of the oldest bar in the 100-bar window holding the highest volume, entry + 2*(entry - stop))."""
import numpy as np

from indep import bars, compare, np_rsi, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "bmIiC79T"


def check():
    df = bars(20000, seed=102, freq="5min")
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    v = df["volume"].to_numpy()
    n = len(c)
    rsi = np_rsi(c, 14)
    pc, po = np.r_[np.nan, c[:-1]], np.r_[np.nan, o[:-1]]
    with np.errstate(invalid="ignore"):
        sig = (pc < po) & (c > o) & (o <= pc) & (c >= po) & (rsi < 30)
    stop = l * (1 - 0.5 / 100)
    vhp = np.full(n, np.nan)
    cur = np.nan
    for i in range(99, n):
        w = v[i - 99:i + 1]
        j = np.flatnonzero(w == w.max())[0]                  # w[0] is the OLDEST bar; the loop runs newest->oldest, so the oldest match wins
        cur = c[i - 99 + j]
        vhp[i] = cur
    vhp_carry = np.full(n, np.nan)
    last = np.nan
    for i in range(n):
        if not np.isnan(vhp[i]):
            last = vhp[i]
        vhp_carry[i] = last

    def target(i, pos, ep, eb):
        if i <= eb:
            return None
        min_tp = ep + (ep - stop[i - 1]) * 2
        return min_tp if np.isnan(vhp_carry[i - 1]) else max(vhp_carry[i - 1], min_tp)

    ref = simulate(o, h, l, c, lambda i, pos: [("entry", 1)] if sig[i] and pos == 0 else [],
                   stop=lambda i, pos, ep, eb: stop[i - 1] if i > eb else None, target=target)
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="5"), ref)
    return ok and len(ref) > 10, f"{detail} (need >10 trades, got {len(ref)})"
