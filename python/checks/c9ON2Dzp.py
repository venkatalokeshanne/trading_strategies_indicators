"""Independent check — EMA RSI Volume (c9ON2Dzp): daily bars, stop / target distances 2 / 4 points here (passed to both sides; prices ~100). EMA9 vs EMA26 and RSI14 in (50, 70) and volume >= SMA3 of the PREVIOUS bars' volume:
long when not long, short when not short (the opposite side is closed first, same open as the reversal). Both exits are re-issued every bar with levels around the position average price as of the previous close (nothing while flat),
and they apply to whichever direction is open on the next bar (also a reversal that opens at that bar's open)."""
import numpy as np

from indep import bars, compare, np_ema, np_rsi, np_sma, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "c9ON2Dzp"
SL, TP = 2.0, 4.0


def check():
    df = bars(8000, seed=19)
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    v = df["volume"].to_numpy()
    n = len(c)
    e1, e2, rsi = np_ema(c, 9), np_ema(c, 26), np_rsi(c, 14)
    av = np_sma(np.r_[np.nan, v[:-1]], 3)
    with np.errstate(invalid="ignore"):
        hv = v >= av
        lg = (e1 > e2) & (rsi > 50) & (rsi < 70) & hv
        sh = (e1 < e2) & (rsi > 50) & (rsi < 70) & hv
    avg_prev = np.full(n, np.nan)

    tmp, ep_hist = {}, {}

    def orders(i, pos):
        ep_hist[i] = tmp.get(i) if pos != 0 else None     # average price at this bar's script time (after any intrabar exit)
        out = []
        if lg[i] and pos <= 0:
            out += [("close", -1), ("entry", 1)]
        if sh[i] and pos >= 0:
            out += [("close", 1), ("entry", -1)]
        return out

    def stop(i, pos, ep, eb):
        if i == 0:
            return None
        a = ep_hist.get(i - 1)
        if a is None:
            return None
        return a - SL if pos > 0 else a + SL

    def target(i, pos, ep, eb):
        if i == 0:
            return None
        a = ep_hist.get(i - 1)
        if a is None:
            return None
        return a + TP if pos > 0 else a - TP

    # The average price at each bar's script time is the entry price of the position held then; record it from the broker's own callbacks.
    def recording_stop(i, pos, ep, eb):
        tmp[i] = ep if pos != 0 else None
        return stop(i, pos, ep, eb)

    with np.errstate(invalid="ignore"):
        ref = simulate(o, h, l, c, orders, stop=recording_stop, target=target)
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="D", params={"Stop Loss (Points)": SL, "Take Profit (Points)": TP},
                                        strategy_overrides={"margin_long": 0, "margin_short": 0}), ref)
    return ok and len(ref) > 10, f"{detail} (need >10 trades, got {len(ref)})"
