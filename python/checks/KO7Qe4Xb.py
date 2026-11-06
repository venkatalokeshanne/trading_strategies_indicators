"""Independent check — Strategy Validation Framework (KO7Qe4Xb): 5-min bars. EMA 9/21 cross enters only when flat; the exits are unconditional ATR levels
(3 ATR stop / 6 ATR target) around the position's average price as of the previous close (na while flat -> nothing on a fresh position's first bar).
Slippage (1 tick) and margin are off on the pinelib side: indep.simulate models slippage on market fills only; quantity is risk based."""
import numpy as np

from indep import bars, compare, np_atr, np_cross_over, np_cross_under, np_ema, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "KO7Qe4Xb"


def check():
    df = bars(20000, seed=134, freq="5min")
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    f, s, atr = np_ema(c, 9), np_ema(c, 21), np_atr(h, l, c, 14)
    up, dn = np_cross_over(f, s), np_cross_under(f, s)
    ep_now, avg_close = {}, np.full(n, np.nan)

    def orders(i, pos):
        avg_close[i] = ep_now.get(i, np.nan) if pos != 0 else np.nan
        return ([("entry", 1)] if up[i] and pos == 0 else []) + ([("entry", -1)] if dn[i] and pos == 0 else [])

    def level(k):
        def fn(i, pos, ep, eb):
            ep_now[i] = ep
            if i == 0 or np.isnan(avg_close[i - 1]) or np.isnan(atr[i - 1]):
                return None
            a = avg_close[i - 1]
            return (a - 3 * atr[i - 1] if pos > 0 else a + 3 * atr[i - 1]) if k == 0 else (a + 6 * atr[i - 1] if pos > 0 else a - 6 * atr[i - 1])
        return fn

    ref = simulate(o, h, l, c, orders, stop=level(0), target=level(1))
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="5", strategy_overrides={"slippage": 0, "margin_long": 0, "margin_short": 0}), ref)
    return ok and len(ref) > 10, f"{detail} (need >10 trades, got {len(ref)})"
