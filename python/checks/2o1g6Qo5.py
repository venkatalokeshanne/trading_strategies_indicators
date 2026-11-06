"""Independent check — MACD trend enhanced (2o1g6Qo5): hourly bars, long only. MACD(12, 26, 9) line crossing over its signal while flat opens the long (entry price =
signal close). While in the position, evaluated at every bar's close: break-even armed once high >= entry * 1.015; stop = max(entry or entry*0.98, 99 % of the
highest high of the last 5 calls); close when low <= stop or MACD crosses down. The highest() call is inside the position block, so (LESSONS P5) its window is
the last 5 values it was FED, not the last 5 chart bars; until 5 calls the trailing stop is na and so is the max() (only the cross can close)."""
import numpy as np

from indep import bars, compare, np_cross_over, np_cross_under, np_ema, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "2o1g6Qo5"


def check():
    df = bars(20000, seed=156, freq="1h")
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    macd = np_ema(c, 12) - np_ema(c, 26)
    sig = np_ema(macd, 9)
    gc, dc = np_cross_over(macd, sig), np_cross_under(macd, sig)
    st = dict(ep=0.0, be=False)
    fed = []                                           # highs seen by the ta.highest call site

    def orders(i, pos):
        out = []
        if gc[i] and pos == 0:
            out.append(("entry", 1)); st["ep"] = c[i]; st["be"] = False
        if pos > 0:
            ep_ = st["ep"]
            init_sl = ep_ * (1 - 0.02)
            if h[i] >= ep_ * (1 + 0.015):
                st["be"] = True
            cur = ep_ if st["be"] else init_sl
            fed.append(h[i])
            trail = max(fed[-5:]) * (1 - 0.01) if len(fed) >= 5 else np.nan
            final = np.nan if np.isnan(trail) else max(cur, trail)
            stopped = (not np.isnan(final)) and l[i] <= final
            if stopped or dc[i]:
                out.append(("close", 1))
        return out

    with np.errstate(invalid="ignore"):
        ref = simulate(o, h, l, c, orders)
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="60", strategy_overrides={"margin_long": 0, "margin_short": 0}), ref)
    return ok and len(ref) > 10, f"{detail} (need >10 trades, got {len(ref)})"
