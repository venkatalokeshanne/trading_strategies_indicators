"""Independent check — EMA 40 Pullback Pyramid (cz5KaioF): daily bars (2015 on, the 2018-01-01 UTC start is inside the sample), pyramiding 3 with one unit per entry (indep.simulate_pyr), slippage 0. EMA40 colour up = EMA40 > previous; bull flip = up now and not up before; trend = up and ADX14 > 20; base entry = flip and ADX > 20; a pullback candidate
(trend, armed or low <= EMA + 1 ATR14, close > EMA and bullish, not a base entry) or a close crossing over the EMA enters long at the next open provided 5 bars passed since the last entry attempt (the clock restarts even when pyramiding blocks the fill); a bear flip (slope turns down) or a close crossing under the EMA closes everything.
The pullback-armed flag is cleared when the trend is gone or an exit fires or a candidate fires, and set on a plain touch."""
import numpy as np
import pandas as pd

from indep import bars, compare, np_atr, np_cross_over, np_cross_under, np_dmi, np_ema, run_conversion, simulate_pyr
from pinelib import SymbolInfo

TV_ID = "cz5KaioF"


def check():
    df = bars(9000, seed=340)
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    f = np_ema(c, 40)
    dp, dm, adx = np_dmi(h, l, c, 14)
    atr = np_atr(h, l, c, 14)
    t0 = int(pd.Timestamp("2018-01-01", tz="UTC").value // 1_000_000)
    tc = df["time"].to_numpy() >= t0
    f1 = np.r_[np.nan, f[:-1]]
    with np.errstate(invalid="ignore"):
        up, dn = f > f1, f < f1
        bu = np_cross_over(c, f)
        be = np_cross_under(c, f)
    up1, dn1 = np.r_[False, up[:-1]], np.r_[False, dn[:-1]]
    s = dict(armed=False, last=None)

    def orders(i, pos):
        out = []
        with np.errstate(invalid="ignore"):
            flip_up, flip_dn = up[i] and not up1[i], dn[i] and not dn1[i]
            trend = up[i] and adx[i] > 20
            base = flip_up and adx[i] > 20
            touched = l[i] <= f[i] + atr[i]
            rec = c[i] > f[i] and c[i] > o[i]
            cand = trend and (s["armed"] or touched) and rec and not base
        can = s["last"] is None or i - s["last"] >= 5
        longc = (base or cand or (bool(bu[i]) and tc[i])) and can and tc[i]
        exitc = (flip_dn or (bool(be[i]) and tc[i])) and tc[i]
        if longc:
            out.append(("entry", 1))
            s["last"] = i
        if exitc:
            out.append(("close_all",))
        if (not trend) or exitc:
            s["armed"] = False
        elif cand:
            s["armed"] = False
        elif touched:
            s["armed"] = True
        return out

    ref = simulate_pyr(o, h, l, c, orders, pyramiding=3)
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="D", strategy_overrides={"margin_long": 0, "margin_short": 0, "slippage": 0}), ref)
    return ok and len(ref) > 10, f"{detail} (need >10 trades, got {len(ref)})"
