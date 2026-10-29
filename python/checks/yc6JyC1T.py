"""Independent check — Initial Balance Breakout (yc6JyC1T): 5-min bars (24h synthetic), one position, 1 unit. IB = running high / low of the 09:30-10:30 New York bars of each New York calendar day (reset at the first bar of the day),
locked on the first bar after the window; tradeable when 1 <= range <= 60 (min input loosened to 1 on both sides). In the 10:30-14:30 window a close crossing over the IB high (under the low) enters once per side per day while flat
and above (below) the VWAP anchored at 09:30 NY; stop = IB low (high), target = IB high + 1.5 x range (low - 1.5 x range), fixed at the entry bar. close_all on the 15:55 bar. Margin, slippage, commission off on the pinelib side."""
import numpy as np
import pandas as pd

from indep import bars, compare, np_vwap, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "yc6JyC1T"


def check():
    df = bars(20000, seed=359, freq="5min")
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    ny = pd.to_datetime(df["time"], unit="ms", utc=True).dt.tz_convert("America/New_York")
    mins = (ny.dt.hour * 60 + ny.dt.minute).to_numpy()
    day = ny.dt.date.to_numpy()
    in_ib = (mins >= 570) & (mins < 630)
    in_tr = (mins >= 630) & (mins < 870)
    in_eod = (mins >= 955) & (mins < 960)
    vw = np_vwap(df, (h + l + c) / 3)
    ibh = np.full(n, np.nan)
    ibl = np.full(n, np.nan)
    locked = np.zeros(n, bool)
    tradeable = np.zeros(n, bool)
    H = L = np.nan
    lk = tr_ = False
    for i in range(n):
        if i > 0 and day[i] != day[i - 1]:
            H = L = np.nan
            lk = tr_ = False
        if in_ib[i]:
            H = h[i] if np.isnan(H) else max(H, h[i])
            L = l[i] if np.isnan(L) else min(L, l[i])
            lk = False
        if not in_ib[i] and not np.isnan(H) and not lk:
            lk = True
            tr_ = 1.0 <= H - L <= 60.0
        ibh[i], ibl[i], locked[i], tradeable[i] = H, L, lk, tr_
    ibh1, ibl1, c1 = np.r_[np.nan, ibh[:-1]], np.r_[np.nan, ibl[:-1]], np.r_[np.nan, c[:-1]]
    with np.errstate(invalid="ignore"):
        xu = (c1 <= ibh1) & (c > ibh)
        xd = (c1 >= ibl1) & (c < ibl)
    st = {"lt": False, "stk": False, "day": None, "lv": None}

    def orders(i, pos):
        if i > 0 and day[i] != day[i - 1]:
            st["lt"] = st["stk"] = False
        out = []
        act = locked[i] and tradeable[i]
        if act and in_tr[i] and not st["lt"] and pos == 0 and c[i] > vw[i] and xu[i]:
            out.append(("entry", 1))
            rng = ibh[i] - ibl[i]
            st["lv"] = (1, ibl[i], ibh[i] + 1.5 * rng)
            st["lt"] = True
        if act and in_tr[i] and not st["stk"] and pos == 0 and c[i] < vw[i] and xd[i]:
            out.append(("entry", -1))
            rng = ibh[i] - ibl[i]
            st["lv"] = (-1, ibh[i], ibl[i] - 1.5 * rng)
            st["stk"] = True
        if in_eod[i] and pos != 0:
            out.append(("close", pos))
        return out

    def stop(i, pos, ep, eb):
        lv = st["lv"]
        return lv[1] if lv and lv[0] == pos else None

    def target(i, pos, ep, eb):
        lv = st["lv"]
        return lv[2] if lv and lv[0] == pos else None

    with np.errstate(invalid="ignore"):
        ref = simulate(o, h, l, c, orders, stop=stop, target=target)
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="5", params={"Min IB Range (pts)": 1.0},
                                        strategy_overrides={"margin_long": 0, "margin_short": 0, "slippage": 0, "commission_value": 0}), ref)
    return ok and len(ref) > 10, f"{detail} (need >10 trades, got {len(ref)})"
