"""Independent check — Trend Efficiency Framework (oTVSg42n): 5-min bars. EMA 20/50 trend with a 20-bar efficiency ratio (|net move| / sum of |bar-to-bar
moves|) above 0.55 enters (reversing); both exits unconditional with ATR*1.5 stop and 3 ATR target around the position's average price as of the
previous close (na while flat; OLD average on a reversal's first bar). Margin off on the pinelib side (synthetic prices drift above the account)."""
import numpy as np

from indep import bars, compare, np_atr, np_ema, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "oTVSg42n"


def check():
    df = bars(20000, seed=137, freq="5min")
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    f, s, atr = np_ema(c, 20), np_ema(c, 50), np_atr(h, l, c, 14)
    eff = np.full(n, np.nan)
    d = np.abs(np.diff(c))
    for i in range(20, n):
        total = d[i - 20:i].sum()                              # |c[k]-c[k-1]| for k = i-19 .. i
        eff[i] = abs(c[i] - c[i - 20]) / total if total != 0 else 0.0
    with np.errstate(invalid="ignore"):
        lg, sg = (f > s) & (eff > 0.55), (f < s) & (eff > 0.55)
    ep_now, avg_close = {}, np.full(n, np.nan)

    def orders(i, pos):
        avg_close[i] = ep_now.get(i, np.nan) if pos != 0 else np.nan
        return ([("entry", 1)] if lg[i] and pos <= 0 else []) + ([("entry", -1)] if sg[i] and pos >= 0 else [])

    def level(k):
        def fn(i, pos, ep, eb):
            ep_now[i] = ep
            if i == 0 or np.isnan(avg_close[i - 1]) or np.isnan(atr[i - 1]):
                return None
            a, r = avg_close[i - 1], atr[i - 1] * 1.5
            return (a - r if pos > 0 else a + r) if k == 0 else (a + 2 * r if pos > 0 else a - 2 * r)
        return fn

    ref = simulate(o, h, l, c, orders, stop=level(0), target=level(1))
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="5", strategy_overrides={"margin_long": 0, "margin_short": 0}), ref)
    return ok and len(ref) > 10, f"{detail} (need >10 trades, got {len(ref)})"
