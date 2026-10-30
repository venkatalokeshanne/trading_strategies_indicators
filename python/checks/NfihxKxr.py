"""Independent check — High Activity Penny Stock V6 (NfihxKxr): daily bars. np_supertrend(2, 10) flipping to up (previous direction >= 0 NaN false) with volume > 1.2 * SMA20 and close > SMA50 goes long, flipping to down with close < SMA50
short (reversing). Unconditional exits at the position's average price as of the previous close (10 % target / 5 % stop; OLD average on a reversal's first bar). A direction against the position closes at the next open.
Margin off on the pinelib side."""
import numpy as np

from indep import bars, compare, np_sma, np_supertrend, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "NfihxKxr"


def check():
    df = bars(8000, seed=261)
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    v = df["volume"].to_numpy()
    n = len(c)
    _, d = np_supertrend(h, l, c, 2.0, 10)
    d1 = np.r_[np.nan, d[:-1]]
    sm, va = np_sma(c, 50), np_sma(v, 20)
    with np.errstate(invalid="ignore"):
        vok = v > va * 1.2
        buy = (d < 0) & (d1 >= 0) & vok & (c > sm)
        sell = (d > 0) & (d1 <= 0) & vok & (c < sm)
    ep_now, avg_close = {}, np.full(n, np.nan)

    def orders(i, pos):
        avg_close[i] = ep_now.get(i, np.nan) if pos != 0 else np.nan
        out = []
        if buy[i]:
            out.append(("entry", 1))
        if sell[i]:
            out.append(("entry", -1))
        if pos > 0 and d[i] > 0:
            out.append(("close", 1))
        if pos < 0 and d[i] < 0:
            out.append(("close", -1))
        return out

    def level(k):
        def fn(i, pos, ep, eb):
            ep_now[i] = ep
            if i == 0 or np.isnan(avg_close[i - 1]):
                return None
            a = avg_close[i - 1]
            if pos > 0:
                return a * 0.95 if k == 0 else a * 1.10
            return a * 1.05 if k == 0 else a * 0.90
        return fn

    with np.errstate(invalid="ignore"):
        ref = simulate(o, h, l, c, orders, stop=level(0), target=level(1))
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="D", strategy_overrides={"margin_long": 0, "margin_short": 0}), ref)
    return ok and len(ref) > 10, f"{detail} (need >10 trades, got {len(ref)})"
