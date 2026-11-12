"""Independent check — AGNI MOMENTUM (yp4CqVVY): 5-min bars (continuous; the stoch of the RSI skips its leading na like Pine's highest/lowest), both directions enabled on both sides. Stoch-RSI K (SMA3 of the raw stoch of RSI14) crossing D (SMA3 of K) on the right side of
the 09:30-NY-reset VWAP(hlc3), with the IST clock at or after 00:15, enters when flat; stop = close -/+ 1.5 ATR, target = 3x that risk, fixed on the signal bar; while a position is open (as of the previous
close) the stop trails to max/min with the previous bar's low/high; the exit orders are issued from the bar after the fill; everything closes once the IST clock reaches 15:29 (close_all only if a position exists)."""
import numpy as np
import pandas as pd

from indep import bars, compare, np_atr, np_cross_over, np_cross_under, np_rsi, np_sma, np_vwap, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "yp4CqVVY"


def psma(x, n):
    """SMA from prefix sums (sum(i-n+1..i) = P[i] - P[i-n+1] + x[i]) so exact K == D plateaus (100 / 0) tie the same way on both sides; na if any na in the window."""
    x = np.asarray(x, float)
    nanc = np.r_[0, np.cumsum(np.isnan(x))]
    P = np.r_[0.0, np.cumsum(np.where(np.isnan(x), 0.0, x))]
    out = np.full(len(x), np.nan)
    for i in range(n - 1, len(x)):
        if nanc[i + 1] - nanc[i - n + 1] == 0:
            out[i] = (P[i] - P[i - (n - 1)] + x[i]) / n
    return out


def check():
    df = bars(15000, seed=24, freq="5min")
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    vw = np_vwap(df, (h + l + c) / 3)
    rsi = np_rsi(c, 14)
    hh = pd.Series(rsi).rolling(14, min_periods=1).max().to_numpy().copy()
    ll = pd.Series(rsi).rolling(14, min_periods=1).min().to_numpy().copy()
    hh[:13], ll[:13] = np.nan, np.nan
    with np.errstate(invalid="ignore", divide="ignore"):
        raw = 100 * (rsi - ll) / (hh - ll)
    raw[~np.isfinite(raw)] = np.nan
    k = psma(raw, 3)
    d = psma(k, 3)
    atr = np_atr(h, l, c, 14)
    ist = pd.to_datetime(df["time"], unit="ms", utc=True).dt.tz_convert("Asia/Kolkata")
    hhmm = (ist.dt.hour * 100 + ist.dt.minute).to_numpy()
    mins = (ist.dt.hour * 60 + ist.dt.minute).to_numpy()
    with np.errstate(invalid="ignore"):
        lt = np_cross_over(k, d) & (c > vw) & (mins >= 15)
        stg = np_cross_under(k, d) & (c < vw) & (mins >= 15)
    sl, tp = [np.nan], [np.nan]
    lv = {}

    def orders(i, pos):
        out = []
        if lt[i] and pos == 0:
            sl[0] = c[i] - atr[i] * 1.5
            tp[0] = c[i] + (c[i] - sl[0]) * 3
            out.append(("entry", 1))
        if stg[i] and pos == 0:
            sl[0] = c[i] + atr[i] * 1.5
            tp[0] = c[i] - (sl[0] - c[i]) * 3
            out.append(("entry", -1))
        if pos > 0 and i > 0:
            sl[0] = max(sl[0], l[i - 1])
        if pos < 0 and i > 0:
            sl[0] = min(sl[0], h[i - 1])
        lv[i] = (pos, sl[0], tp[0])
        if hhmm[i] >= 1529 and pos != 0:
            out.append(("close", 1 if pos > 0 else -1))
        return out

    def stop(i, pos, ep, eb):
        if i == 0 or lv[i - 1][0] == 0 or np.isnan(lv[i - 1][1]):
            return None
        return lv[i - 1][1]

    def target(i, pos, ep, eb):
        if i == 0 or lv[i - 1][0] == 0 or np.isnan(lv[i - 1][2]):
            return None
        return lv[i - 1][2]

    with np.errstate(invalid="ignore"):
        ref = simulate(o, h, l, c, orders, stop=stop, target=target)
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="5", params={"Allow SELL Trades?": True},
                                        strategy_overrides={"margin_long": 0, "margin_short": 0}), ref)
    return ok and len(ref) > 10, f"{detail} (need >10 trades, got {len(ref)})"
