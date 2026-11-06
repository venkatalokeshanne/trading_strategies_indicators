"""Independent check — SilverStream v2 (rP7izVek): 5-min bars. EMA30/50 trend + close beyond the previous bar's high/low, cooldown of 3 bars from the last signal (set even when the entry is ignored, pyramiding 1). Unconditional exits
at the position's average price +/- (target 2, stop 1, scaled to the price level and passed to both sides) as of the previous close: none while flat, and the OLD average on a reversal's first bar."""
import numpy as np

from indep import bars, compare, np_ema, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "rP7izVek"


def check():
    df = bars(20000, seed=213, freq="5min")
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    tm, sm = round(float(c.mean()) * 0.004, 4), round(float(c.mean()) * 0.002, 4)
    f, s = np_ema(c, 30), np_ema(c, 50)
    h1, l1 = np.r_[np.nan, h[:-1]], np.r_[np.nan, l[:-1]]
    with np.errstate(invalid="ignore"):
        bs, ss = (f > s) & (c > h1), (f < s) & (c < l1)
    last = [None]
    ep_now, avg_close = {}, np.full(n, np.nan)

    def orders(i, pos):
        avg_close[i] = ep_now.get(i, np.nan) if pos != 0 else np.nan
        ok = last[0] is None or i - last[0] > 3
        out = []
        if bs[i] and ok:
            out.append(("entry", 1)); last[0] = i
        if ss[i] and ok:
            out.append(("entry", -1)); last[0] = i
        return out

    def level(k):
        def fn(i, pos, ep, eb):
            ep_now[i] = ep
            if i == 0 or np.isnan(avg_close[i - 1]):
                return None
            a = avg_close[i - 1]
            return (a - pos * sm) if k == 0 else (a + pos * tm)
        return fn

    ref = simulate(o, h, l, c, orders, stop=level(0), target=level(1))
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="5", params={"Target Move ($)": tm, "Stop Move ($)": sm},
                                        strategy_overrides={"margin_long": 0, "margin_short": 0}), ref)
    return ok and len(ref) > 10, f"{detail} (need >10 trades, got {len(ref)})"
