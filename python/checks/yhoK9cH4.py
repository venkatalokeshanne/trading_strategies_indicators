"""Independent check — LL Momentum and Curl Master (yhoK9cH4): daily bars. Long: close - close[20] > 0, SMA50 change > 0, close > EMA200, volume > 1.2 x SMA20(volume), flat; short: momentum < 0, SMA50 falling, close < EMA200. Entries at the next open; stop = signal low - 2 ATR14 (short: signal high + 1.5 ATR14), set at the signal.
While a position exists (as of a bar's close) the exit is issued: stop = that stored stop, target = entry price + 4 ATR14 (short: - 3 ATR14) with that bar's ATR; it works from the next bar for the same direction."""
import numpy as np

from indep import bars, compare, np_atr, np_ema, np_sma, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "yhoK9cH4"


def check():
    df = bars(9000, seed=77)
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    v = df["volume"].to_numpy()
    n = len(c)
    mom = c - np.r_[[np.nan] * 20, c[:-20]]
    sm = np_sma(c, 50)
    chg = sm - np.r_[np.nan, sm[:-1]]
    ema, atr = np_ema(c, 200), np_atr(h, l, c, 14)
    with np.errstate(invalid="ignore"):
        vf = v > np_sma(v, 20) * 1.2
        lc = (mom > 0) & (chg > 0) & (c > ema) & vf
        sc = (mom < 0) & (chg < 0) & (c < ema) & vf
    stops = {}
    tmp, lv = {}, {}

    def orders(i, pos):
        out = []
        if lc[i] and pos == 0:
            out.append(("entry", 1))
            stops[1] = l[i] - atr[i] * 2.0
        if sc[i] and pos == 0:
            out.append(("entry", -1))
            stops[-1] = h[i] + atr[i] * 1.5
        ep = tmp.get(i) if pos != 0 else None
        lv[i] = None if ep is None else (1 if pos > 0 else -1, ep + 4 * atr[i] if pos > 0 else ep - 3 * atr[i])
        return out

    def stop(i, pos, ep, eb):
        tmp[i] = ep
        p = lv.get(i - 1) if i > 0 else None
        if p is None or p[0] * pos <= 0:
            return None
        return stops[1 if pos > 0 else -1]

    def target(i, pos, ep, eb):
        p = lv.get(i - 1) if i > 0 else None
        if p is None or p[0] * pos <= 0 or np.isnan(p[1]):
            return None
        return p[1]

    with np.errstate(invalid="ignore"):
        ref = simulate(o, h, l, c, orders, stop=stop, target=target)
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="D", strategy_overrides={"margin_long": 0, "margin_short": 0}), ref)
    return ok and len(ref) > 10, f"{detail} (need >10 trades, got {len(ref)})"
