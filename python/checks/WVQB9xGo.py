"""Independent check — London NZ Sweep + FVG (WVQB9xGo): 5-min trending synthetic bars, sessions in Pacific/Auckland (bar start; DST handled by the tz database): Asia 13:00-19:00 tracks the high / low, London 20:00-22:00. The first sweep of the
Asia low / high inside London fixes the direction (once per window, reset at the window's first bar); a displacement candle (body > ATR14) with a gap vs two bars ago (low > high[2] / high < low[2]) and the 60-minute close vs its
SMA20 (plain-pandas blocks from 09:30 NY, lookahead off) enters once per window. Entry + exit (stop = previous low / high, limit = 3 R) are issued together on the signal bar, so the bracket works from the fill bar; quantity is
irrelevant to prices. Margin off on the pinelib side (risk-sized quantity can exceed equity)."""
import numpy as np
import pandas as pd

from indep import bars, compare, np_atr, np_periods, np_security_lookahead_off, np_sma, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "WVQB9xGo"


def trend_bars(n, seed, freq):
    """Strongly trending OHLCV (slow AR(1) drift much larger than the noise) so that two-bar gaps are common."""
    rng = np.random.default_rng(seed)
    drift = np.zeros(n)
    for i in range(1, n):
        drift[i] = 0.97 * drift[i - 1] + rng.normal(0, 0.0012)
    close = 100 * np.exp(np.cumsum(drift + rng.normal(0, 0.004, n)))
    open_ = np.concatenate([[close[0]], close[:-1]]) * (1 + rng.normal(0, 0.0015, n))
    high = np.maximum(open_, close) * (1 + np.abs(rng.normal(0, 0.002, n)))
    low = np.minimum(open_, close) * (1 - np.abs(rng.normal(0, 0.002, n)))
    t = pd.date_range("2015-01-01", periods=n, freq=freq, tz="UTC").as_unit("ms").asi8
    return pd.DataFrame({"time": t, "open": open_, "high": high, "low": low, "close": close, "volume": rng.integers(1000, 100000, n).astype(float)})


def check():
    df = trend_bars(100000, 228, "5min")
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    loc = pd.to_datetime(df["time"], unit="ms", utc=True).dt.tz_convert("Pacific/Auckland")
    m = (loc.dt.hour * 60 + loc.dt.minute).to_numpy()
    asia, lon = (m >= 780) & (m < 1140), (m >= 1200) & (m < 1320)
    pid, last_of = np_periods(df, 60)
    hc = pd.Series(c).groupby(pid).last().to_numpy()
    hclose = np_security_lookahead_off(hc, pid, last_of)
    hma = np_security_lookahead_off(np_sma(hc, 20), pid, last_of)
    atr = np_atr(h, l, c, 14)
    h2, l2 = np.r_[np.nan, np.nan, h[:-2]], np.r_[np.nan, np.nan, l[:-2]]
    h1, l1 = np.r_[np.nan, h[:-1]], np.r_[np.nan, l[:-1]]
    with np.errstate(invalid="ignore"):
        bdisp, sdisp = (c > o) & (np.abs(c - o) > atr), (c < o) & (np.abs(c - o) > atr)
        bfvg, sfvg = l > h2, h < l2
        bbias, sbias = hclose > hma, hclose < hma
    ah = al = np.nan
    taken, sd = False, 0
    lvl = {1: (np.nan, np.nan), -1: (np.nan, np.nan)}

    def orders(i, pos):
        nonlocal ah, al, taken, sd
        astart = asia[i] and not (i > 0 and asia[i - 1])
        lstart = lon[i] and not (i > 0 and lon[i - 1])
        if astart:
            ah, al = h[i], l[i]
        if asia[i]:
            ah = max(h[i] if np.isnan(ah) else ah, h[i])
            al = min(l[i] if np.isnan(al) else al, l[i])
        if lstart:
            taken, sd = False, 0
        bsw = lon[i] and l[i] < al
        ssw = lon[i] and h[i] > ah
        if not taken and sd == 0:
            if bsw:
                sd = 1
            elif ssw:
                sd = -1
        out = []
        with np.errstate(invalid="ignore"):
            buy = (not taken) and lon[i] and sd == 1 and bdisp[i] and bfvg[i] and bbias[i]
            sell = (not taken) and lon[i] and sd == -1 and sdisp[i] and sfvg[i] and sbias[i]
        if buy:
            sl = l1[i]
            if abs(c[i] - sl) > 0:
                out.append(("entry", 1)); lvl[1] = (sl, c[i] + (c[i] - sl) * 3.0); taken = True
        if sell:
            sl = h1[i]
            if abs(sl - c[i]) > 0:
                out.append(("entry", -1)); lvl[-1] = (sl, c[i] - (sl - c[i]) * 3.0); taken = True
        return out

    with np.errstate(invalid="ignore"):
        ref = simulate(o, h, l, c, orders, stop=lambda i, pos, ep, eb: lvl[pos][0], target=lambda i, pos, ep, eb: lvl[pos][1])
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="5", strategy_overrides={"margin_long": 0, "margin_short": 0}), ref)
    return ok and len(ref) > 5, f"{detail} (need >5 trades, got {len(ref)})"
