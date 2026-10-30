"""Independent check — Asian Breakout AutoBot (slqi9xMe): 5-min bars (24h synthetic, UTC clock), one position, 1 unit. Asia box = running high / low of the 00:00-08:00 UTC bars, restarted by the first bar of each Asia session and
held afterwards. In the UK (08:00-13:30) or US (13:30-20:00) session a close crossing over the Asia high (under the low) while flat enters; stop = the opposite Asia extreme, target = high + 2 x range (low - 2 x range),
fixed prices issued with the entry. close_all on the first bar after the US session. Pinelib side margin and slippage off."""
import numpy as np

from indep import bars, compare, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "slqi9xMe"


def check():
    df = bars(12000, seed=881, freq="5min")
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    mins = ((df["time"].to_numpy() // 60000) % 1440).astype(int)
    asia = mins < 480
    uk = (mins >= 480) & (mins < 810)
    us = (mins >= 810) & (mins < 1200)
    ah = np.full(n, np.nan)
    al = np.full(n, np.nan)
    ch = cl = np.nan
    for i in range(n):
        if asia[i]:
            if i == 0 or not asia[i - 1]:
                ch, cl = h[i], l[i]
            else:
                ch, cl = max(ch, h[i]), min(cl, l[i])
        ah[i], al[i] = ch, cl
    ah1, al1, c1 = np.r_[np.nan, ah[:-1]], np.r_[np.nan, al[:-1]], np.r_[np.nan, c[:-1]]
    with np.errstate(invalid="ignore"):
        tw = uk | us
        lc = tw & (c1 <= ah1) & (c > ah)
        sc = tw & (c1 >= al1) & (c < al)
    us_end = np.r_[False, us[:-1] & ~us[1:]]
    lv = {"long": None, "short": None}

    def orders(i, pos):
        out = []
        if lc[i] and pos == 0:
            out.append(("entry", 1))
            lv["long"] = (al[i], ah[i] + (ah[i] - al[i]) * 2.0)
        if sc[i] and pos == 0:
            out.append(("entry", -1))
            lv["short"] = (ah[i], al[i] - (ah[i] - al[i]) * 2.0)
        if us_end[i] and pos != 0:
            out.append(("close", pos))
        return out

    def stop(i, pos, ep, eb):
        x = lv["long"] if pos > 0 else lv["short"]
        return None if x is None else x[0]

    def target(i, pos, ep, eb):
        x = lv["long"] if pos > 0 else lv["short"]
        return None if x is None else x[1]

    with np.errstate(invalid="ignore"):
        ref = simulate(o, h, l, c, orders, stop=stop, target=target)
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="5", strategy_overrides={"margin_long": 0, "margin_short": 0, "slippage": 0}), ref)
    return ok and len(ref) > 10, f"{detail} (need >10 trades, got {len(ref)})"
