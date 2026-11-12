"""Independent check — CJ Futures Low-Drawdown (OQYG2KC5): 5-min New York bars. Closes of the 240- and 60-minute blocks (plain pandas, from the 09:30 session start, lookahead off) against their own EMA50 give the trend;
in 08:30-11:30 NY, with volume above its SMA20, a pullback to the chart EMA50 + confirming candle (close beyond open and the previous high / low) enters when not already on that side (stop = 5-bar lowest low / highest high,
limit = 2 R, issued on the signal bar so it works from the fill bar). Margin off on the pinelib side."""
import numpy as np
import pandas as pd

from indep import bars, compare, np_ema, np_periods, np_security_lookahead_off, np_sma, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "OQYG2KC5"


def htf(df, c, minutes):
    pid, last_of = np_periods(df, minutes)
    hc = pd.Series(c).groupby(pid).last().to_numpy()
    return np_security_lookahead_off(hc, pid, last_of), np_security_lookahead_off(np_ema(hc, 50), pid, last_of)


def check():
    df = bars(60000, seed=225, freq="5min")
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    v = df["volume"].to_numpy()
    ny = pd.to_datetime(df["time"], unit="ms", utc=True).dt.tz_convert("America/New_York")
    m = (ny.dt.hour * 60 + ny.dt.minute).to_numpy()
    sess = (m >= 510) & (m < 690)
    tc, te = htf(df, c, 240)
    sc_, se = htf(df, c, 60)
    e = np_ema(c, 50)
    h1, l1 = np.r_[np.nan, h[:-1]], np.r_[np.nan, l[:-1]]
    lo5 = pd.Series(l).rolling(5).min().to_numpy()
    hi5 = pd.Series(h).rolling(5).max().to_numpy()
    with np.errstate(invalid="ignore"):
        bull, bear = (tc > te) & (sc_ > se), (tc < te) & (sc_ < se)
        gv = v > np_sma(v, 20)
        bs = sess & gv & (l <= e) & bull & (c > o) & (c > h1)
        ss = sess & gv & (h >= e) & bear & (c < o) & (c < l1)
    lvl = {1: (np.nan, np.nan), -1: (np.nan, np.nan)}

    def orders(i, pos):
        out = []
        if bs[i] and c[i] - lo5[i] > 0 and pos <= 0:
            out.append(("entry", 1)); lvl[1] = (lo5[i], c[i] + (c[i] - lo5[i]) * 2.0)
        if ss[i] and hi5[i] - c[i] > 0 and pos >= 0:
            out.append(("entry", -1)); lvl[-1] = (hi5[i], c[i] - (hi5[i] - c[i]) * 2.0)
        return out

    with np.errstate(invalid="ignore"):
        ref = simulate(o, h, l, c, orders, stop=lambda i, pos, ep, eb: lvl[pos][0], target=lambda i, pos, ep, eb: lvl[pos][1])
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="5", strategy_overrides={"margin_long": 0, "margin_short": 0}), ref)
    return ok and len(ref) > 10, f"{detail} (need >10 trades, got {len(ref)})"
