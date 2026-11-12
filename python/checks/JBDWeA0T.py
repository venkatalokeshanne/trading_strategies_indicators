"""Independent check — Market Breadth Trend (JBDWeA0T): 5-min bars. Fast/slow EMA trend plus a "breadth line" (SMA20 of 100/0 flags for
close > slow EMA) above 60 / below 40, reversing. Both exits are unconditional and use the position's average price as of the previous
bar's close (na while flat) with ATR*1.5 stop and 3 ATR target for BOTH directions (a reversal's first bar uses the OLD average)."""
import numpy as np

from indep import bars, compare, np_atr, np_ema, np_sma, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "JBDWeA0T"


def check():
    df = bars(20000, seed=100, freq="5min")
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    ef, es, atr = np_ema(c, 50), np_ema(c, 200), np_atr(h, l, c, 14)
    breadth = np_sma(np.where(c > es, 100.0, 0.0), 20)
    with np.errstate(invalid="ignore"):
        lg, sg = (ef > es) & (breadth > 60), (ef < es) & (breadth < 40)
    ep_now, avg_close = {}, np.full(n, np.nan)

    def orders(i, pos):
        avg_close[i] = ep_now.get(i, np.nan) if pos != 0 else np.nan
        return ([("entry", 1)] if lg[i] and pos <= 0 else []) + ([("entry", -1)] if sg[i] and pos >= 0 else [])

    def level(k):
        def f(i, pos, ep, eb):
            ep_now[i] = ep
            if i == 0 or np.isnan(avg_close[i - 1]) or np.isnan(atr[i - 1]):
                return None
            a, r = avg_close[i - 1], atr[i - 1] * 1.5
            return (a - r if pos > 0 else a + r) if k == 0 else (a + 2 * r if pos > 0 else a - 2 * r)
        return f

    ref = simulate(o, h, l, c, orders, stop=level(0), target=level(1))
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="5", strategy_overrides={"margin_long": 0, "margin_short": 0}), ref)
    return ok and len(ref) > 10, f"{detail} (need >10 trades, got {len(ref)})"
