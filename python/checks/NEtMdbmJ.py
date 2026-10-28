"""Independent check — Multi-Timeframe Trend Alignment (NEtMdbmJ): 5-min New York bars. EMA 20/50 cross in the direction of the close vs the 4-hour EMA200
(plain-pandas 240-minute blocks from the 09:30 session start; lookahead off: a block's value on its last chart bar, the previous block's before that).
Both exits unconditional: ATR*1.5 stop / 3 ATR target around the position's average price as of the previous close (na while flat; OLD average on a
reversal's first bar). Margin off on the pinelib side."""
import numpy as np
import pandas as pd

from indep import bars, compare, np_atr, np_cross_over, np_cross_under, np_ema, np_periods, np_security_lookahead_off, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "NEtMdbmJ"


def check():
    df = bars(60000, seed=151, freq="5min")
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    pid, last_of = np_periods(df, 240)
    hc = pd.Series(c).groupby(pid).last().to_numpy()
    htf = np_security_lookahead_off(np_ema(hc, 200), pid, last_of)
    f, s, atr = np_ema(c, 20), np_ema(c, 50), np_atr(h, l, c, 14)
    with np.errstate(invalid="ignore"):
        lg = (c > htf) & np_cross_over(f, s)
        sg = (c < htf) & np_cross_under(f, s)
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
