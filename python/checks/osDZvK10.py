"""Independent check — ZLEMA trailing stop (osDZvK10): 5-min bars. Zero-lag EMA(20) with volatility bands (highest(ATR(20), 60) * 0.2); a close through the
upper/lower band with the EMA15 filter sets the trend, a cross of the ZLEMA in the trend direction enters (reversing). The stop is a manual ratchet:
re-issued each bar while in the position as max(prev, lower) (long) / min(prev, upper) (short) and cleared when flat, so bar i works with the value
from bar i-1's close; a reversal's first bar has no stop."""
import numpy as np

from indep import bars, compare, np_atr, np_cross_over, np_cross_under, np_ema, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "osDZvK10"


def roll(x, n, fn):
    """ta.highest/lowest: na only until n BARS exist; na values inside the window are skipped."""
    out = np.full(len(x), np.nan)
    for i in range(n - 1, len(x)):
        w = x[i - n + 1:i + 1]
        w = w[~np.isnan(w)]
        if len(w):
            out[i] = fn(w)
    return out


def check():
    df = bars(20000, seed=128, freq="5min")
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    lag = 9
    lagged = np.r_[[np.nan] * lag, c[:-lag]]
    z = np_ema(c + (c - lagged), 20)
    vol = roll(np_atr(h, l, c, 20), 60, np.max) * 0.2
    up, lo = z + vol, z - vol
    e15 = np_ema(c, 15)
    with np.errstate(invalid="ignore"):
        xu = np_cross_over(c, up) & (c > e15)
        xd = np_cross_under(c, lo) & (c < e15)
        cz_up, cz_dn = np_cross_over(c, z), np_cross_under(c, z)
    trend = 0
    long_s = short_s = np.nan
    stops = []                                     # (long_stop, short_stop) at the end of each bar

    def orders(i, pos):
        nonlocal trend, long_s, short_s
        if xu[i]:
            trend = 1
        if xd[i]:
            trend = -1
        out = []
        if cz_up[i] and trend == 1 and c[i] > e15[i]:
            out.append(("entry", 1))
        if cz_dn[i] and trend == -1 and c[i] < e15[i]:
            out.append(("entry", -1))
        if pos > 0:
            long_s = lo[i] if np.isnan(long_s) else np.fmax(long_s, lo[i]) if not np.isnan(lo[i]) else np.nan
        if pos < 0:
            short_s = up[i] if np.isnan(short_s) else np.fmin(short_s, up[i]) if not np.isnan(up[i]) else np.nan
        if pos == 0:
            long_s = short_s = np.nan
        stops.append((long_s if pos > 0 else np.nan, short_s if pos < 0 else np.nan))   # an exit exists only if it was issued this bar (pos > 0 / < 0)
        return out

    ref = simulate(o, h, l, c, orders,
                   stop=lambda i, pos, ep, eb: (stops[i - 1][0] if pos > 0 else stops[i - 1][1]) if i > 0 else None)
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="5", strategy_overrides={"margin_long": 0, "margin_short": 0}), ref)
    return ok and len(ref) > 10, f"{detail} (need >10 trades, got {len(ref)})"
