"""Independent check — WLD 4H Auto Entry (qUrvPAmT): 4-hour bars. UT-Bot trailing stop with ATR period 1 (= true range) x 2 (the Pine recursion, na on the first bar restarts it); buy when the close is above it and EMA(close, 1) just crossed
over it, sell mirrored. A signal is accepted when none was accepted within the last 4 bars, MACD(12,26,9) is on the same side of its signal line and close and low (high) are beyond EMA50; it enters that bar (fills at the next
open). An open position closes at the next open once 4 bars have passed since its entry bar, or when the opposite signal (confirmed the same way) appears; closing resets the signal state."""
import numpy as np

from indep import bars, compare, np_ema, np_tr, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "qUrvPAmT"


def check():
    df = bars(30000, seed=276, freq="4h")
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    e50 = np_ema(c, 50)
    macd = np_ema(c, 12) - np_ema(c, 26)
    sig = np_ema(macd, 9)
    nloss = 2.0 * np_tr(h, l, c, False)
    stop = np.full(n, np.nan)
    for i in range(n):
        prev = stop[i - 1] if i else np.nan
        s, s1 = c[i], (c[i - 1] if i else np.nan)
        if np.isnan(prev):
            stop[i] = s - nloss[i]
        elif s > prev and s1 > prev:
            stop[i] = np.nan if (np.isnan(nloss[i])) else max(prev, s - nloss[i])
        elif s < prev and s1 < prev:
            stop[i] = np.nan if (np.isnan(nloss[i])) else min(prev, s + nloss[i])
        elif s > prev:
            stop[i] = s - nloss[i]
        else:
            stop[i] = s + nloss[i]
    prev_s, prev_c = np.r_[np.nan, stop[:-1]], np.r_[np.nan, c[:-1]]
    with np.errstate(invalid="ignore"):
        above = (c > stop) & (prev_c <= prev_s)                # ema(close, 1) == close crossing over the stop
        below = (stop > c) & (prev_s <= prev_c)                # crossover(stop, close)
        buy, sell = (c > stop) & above, (c < stop) & below
    st = dict(sb=None, typ="none", eb=None)

    def orders(i, pos):
        out = []
        with np.errstate(invalid="ignore"):
            if st["sb"] is None or i > st["sb"] + 4:
                if buy[i] and macd[i] > sig[i] and c[i] > e50[i] and l[i] > e50[i]:
                    st["sb"], st["typ"] = i, "long"
                elif sell[i] and macd[i] < sig[i] and c[i] < e50[i] and h[i] < e50[i]:
                    st["sb"], st["typ"] = i, "short"
            el = st["typ"] == "long" and i == st["sb"] and c[i] > e50[i] and macd[i] > sig[i]
            es = st["typ"] == "short" and i == st["sb"] and c[i] < e50[i] and macd[i] < sig[i]
            eb_open = st["eb"]                                     # entry bar of the trade that is open NOW (a pending entry does not change it)
            if el:
                out.append(("entry", 1))
                if pos <= 0:
                    st["eb"] = i + 1
            if es:
                out.append(("entry", -1))
                if pos >= 0:
                    st["eb"] = i + 1
            exit_t = False
            if pos != 0 and eb_open is not None and i - eb_open >= 4:
                exit_t = True
            opp = False
            if st["typ"] == "long":
                opp = bool(sell[i] and c[i] < e50[i] and macd[i] < sig[i])
            elif st["typ"] == "short":
                opp = bool(buy[i] and c[i] > e50[i] and macd[i] > sig[i])
            if pos != 0 and opp:
                exit_t = True
        if exit_t:
            out += [("close", 1), ("close", -1)]
            st["sb"], st["typ"] = None, "none"
        return out

    ref = simulate(o, h, l, c, orders)
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="240", strategy_overrides={"margin_long": 0, "margin_short": 0}), ref)
    return ok and len(ref) > 10, f"{detail} (need >10 trades, got {len(ref)})"
