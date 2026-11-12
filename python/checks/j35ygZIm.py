"""Independent check — LVN Rejection / Acceptance (j35ygZIm): 5-min bars. SMA(40) +/- 0.8 ATR zone; low-volume (< 0.8 x SMA40) rejection of a band edge, or two
consecutive closes beyond it (the previous close vs the CURRENT band edge), enters only when flat; ATR*1.5 stop / 3 ATR target around the position's
average price as of the previous close (na while flat -> nothing on a fresh position's first bar)."""
import numpy as np

from indep import bars, compare, np_atr, np_sma, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "j35ygZIm"


def check():
    df = bars(20000, seed=152, freq="5min")
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    v = df["volume"].to_numpy()
    n = len(c)
    basis, atr = np_sma(c, 40), np_atr(h, l, c, 14)
    up, lo = basis + atr * 0.8, basis - atr * 0.8
    lowv = v < np_sma(v, 40) * 0.8
    pc = np.r_[np.nan, c[:-1]]
    with np.errstate(invalid="ignore"):
        lg = ((l < lo) & (c > lo) & lowv) | ((c > up) & (pc > up))
        sg = ((h > up) & (c < up) & lowv) | ((c < lo) & (pc < lo))
    ep_now, avg_close = {}, np.full(n, np.nan)

    def orders(i, pos):
        avg_close[i] = ep_now.get(i, np.nan) if pos != 0 else np.nan
        return ([("entry", 1)] if lg[i] and pos == 0 else []) + ([("entry", -1)] if sg[i] and pos == 0 else [])

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
