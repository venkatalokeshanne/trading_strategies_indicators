"""Independent check — Vishall EMA/DMI (AViiuAoi): daily bars, long only, Min ADX 15 / Min EMA20 slope 0.02 here (passed to both sides). Entry when flat: close > EMA9 > EMA20 > EMA50 > EMA200, ADX14 > min, +DI > -DI,
EMA20 slope > min and slope[1] > 0, ROC5 = 100*(c - c[5])/c[5] > 0 and rising; exit when close < EMA9, EMA9 < EMA20, +DI < -DI, ADX < min or ROC < 0 (only if a position exists)."""
import numpy as np

from indep import bars, compare, np_dmi, np_ema, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "AViiuAoi"
ADX_MIN, SLOPE_MIN = 15.0, 0.02


def check():
    df = bars(8000, seed=52)
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    e9, e20, e50, e200 = (np_ema(c, k) for k in (9, 20, 50, 200))
    roc = np.r_[[np.nan] * 5, 100 * (c[5:] - c[:-5]) / c[:-5]]
    accel = roc - np.r_[np.nan, roc[:-1]]
    slope = e20 - np.r_[np.nan, e20[:-1]]
    slope1 = np.r_[np.nan, slope[:-1]]
    dp, dm, adx = np_dmi(h, l, c, 14)
    with np.errstate(invalid="ignore"):
        entry = (c > e9) & (e9 > e20) & (e20 > e50) & (e50 > e200) & (adx > ADX_MIN) & (dp > dm) & (slope > SLOPE_MIN) & (slope1 > 0) & (roc > 0) & (accel > 0)
        ex = (c < e9) | (e9 < e20) | (dp < dm) | (adx < ADX_MIN) | (roc < 0)

    def orders(i, pos):
        out = []
        if entry[i] and pos == 0:
            out.append(("entry", 1))
        if ex[i] and pos > 0:
            out.append(("close", 1))
        return out

    ref = simulate(o, h, l, c, orders)
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="D", params={"Min ADX": ADX_MIN, "Min EMA20 Slope": SLOPE_MIN},
                                        strategy_overrides={"margin_long": 0, "margin_short": 0}), ref)
    return ok and len(ref) > 10, f"{detail} (need >10 trades, got {len(ref)})"
