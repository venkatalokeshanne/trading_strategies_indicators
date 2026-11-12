"""Independent check — ES/NQ Execution System v2 (LuWMkgYU): 15-minute bars (24 h synthetic, price ~100) of a stock-style symbol (New York time, trading days from 09:30), market orders at the next open, quantity 1, pyramiding 0, commission / slippage / margin off.
Levels: previous-day high / low from the daily periods (high[1] / low[1] on the daily bars, lookahead off: a day's value shows on its last chart bar, the previous day's before that), the pre-market 04:00 - 09:30 range and the 09:30 - 10:00 opening range, the trackers being cleared at every daily-period change (which is 09:30, so the pre-market range is cleared before the
trading window - the quirk is part of the script). A sweep = high over / low under a level with a close back through it. In 09:30 - 11:30, below the daily trade cap, two or more sweeps of one side enter 1 unit; afterwards, every bar, an exit order per active side (never reset) is re-issued from the CURRENT bar's risk: stop to break-even after one R, trailing the close by the buffer past 2R, and a limit at 2R.
Uses the quantity-aware bracket reference (indep.simulate_brackets), comparing quantities too. Variants: defaults with a 2-trade cap; 1 trade cap with a wider stop buffer (0.8 ATR)."""
import numpy as np
import pandas as pd

from indep import bars, compare_q, np_atr, np_periods, np_security_lookahead_off, run_conversion, simulate_brackets
from pinelib import SymbolInfo

TV_ID = "LuWMkgYU"


def one(df, params, p):
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    ny = pd.to_datetime(df["time"], unit="ms", utc=True).dt.tz_convert("America/New_York")
    mins = (ny.dt.hour * 60 + ny.dt.minute).to_numpy()
    pid, last_of = np_periods(df, 1440)
    nper = int(pid.max()) + 1
    dh = np.full(nper, -np.inf)
    dl = np.full(nper, np.inf)
    for i in range(n):
        dh[pid[i]], dl[pid[i]] = max(dh[pid[i]], h[i]), min(dl[pid[i]], l[i])
    pdh_per = np.r_[np.nan, dh[:-1]]
    pdl_per = np.r_[np.nan, dl[:-1]]
    pdh, pdl = np_security_lookahead_off(pdh_per, pid, last_of), np_security_lookahead_off(pdl_per, pid, last_of)
    atr = np_atr(h, l, c, 14)
    S = dict(td=0, pmh=np.nan, pml=np.nan, orh=np.nan, orl=np.nan, la=False, sa=False, ep=np.nan, stop=np.nan)

    def orders(i, info):
        out = []
        newday = i == 0 or pid[i] != pid[i - 1]
        buf = atr[i] * p["am"]
        if newday and i > 0:
            S["td"] = 0
        ny_s = 570 <= mins[i] < 690
        if newday and i > 0:
            S["pmh"] = S["pml"] = np.nan
        if 240 <= mins[i] < 570:
            S["pmh"] = h[i] if np.isnan(S["pmh"]) else max(S["pmh"], h[i])
            S["pml"] = l[i] if np.isnan(S["pml"]) else min(S["pml"], l[i])
        if newday and i > 0:
            S["orh"] = S["orl"] = np.nan
        if 570 <= mins[i] < 600:
            S["orh"] = h[i] if np.isnan(S["orh"]) else max(S["orh"], h[i])
            S["orl"] = l[i] if np.isnan(S["orl"]) else min(S["orl"], l[i])
        with np.errstate(invalid="ignore"):
            sl = sum(1 for lv in (pdl[i], S["pml"], S["orl"]) if l[i] < lv and c[i] > lv)
            ss = sum(1 for lv in (pdh[i], S["pmh"], S["orh"]) if h[i] > lv and c[i] < lv)
        can = S["td"] < p["mt"]
        lc, sc = can and ny_s and sl >= 2, can and ny_s and ss >= 2
        lstop, sstop = l[i] - buf, h[i] + buf
        lrisk, srisk = c[i] - lstop, sstop - c[i]
        ltp2, stp2 = c[i] + lrisk * 2, c[i] - srisk * 2
        if lc:
            out.append(("entry", "LONG", 1, 1.0))
            S.update(ep=c[i], stop=lstop, la=True)
            S["td"] += 1
        if sc:
            out.append(("entry", "SHORT", -1, 1.0))
            S.update(ep=c[i], stop=sstop, sa=True)
            S["td"] += 1
        with np.errstate(invalid="ignore"):
            if S["la"]:
                if c[i] >= S["ep"] + lrisk:
                    S["stop"] = max(S["stop"], S["ep"])
                if c[i] >= ltp2:
                    S["stop"] = max(S["stop"], c[i] - buf)
                out.append(("exit", "LONG EXIT", "LONG", None, S["stop"], ltp2))
            if S["sa"]:
                if c[i] <= S["ep"] - srisk:
                    S["stop"] = min(S["stop"], S["ep"])
                if c[i] <= stp2:
                    S["stop"] = min(S["stop"], c[i] + buf)
                out.append(("exit", "SHORT EXIT", "SHORT", None, S["stop"], stp2))
        return out

    ref = simulate_brackets(o, h, l, c, orders)
    sym = SymbolInfo.make("NASDAQ:XYZ", "stock", qty_step=1e-9)
    ok, d = compare_q(run_conversion(TV_ID, df, symbol=sym, tf="15", params=params,
                                     strategy_overrides={"margin_long": 0, "margin_short": 0, "commission_value": 0, "slippage": 0}), ref)
    return ok and len(ref) > 6, f"{d} (got {len(ref)})"


BASE = dict(mt=4, am=0.35)


def check():
    df = bars(120000, seed=381, freq="15min")
    for k in ("open", "high", "low", "close"):
        df[k] = 100 * (df[k] / 100) ** 0.3
    msgs, allok = [], True
    cases = (({}, {}), ({"Max Trades Per Day": 2}, dict(mt=2)), ({"Max Trades Per Day": 1, "Stop Buffer ATR": 0.8}, dict(mt=1, am=0.8)))
    for params, ov in cases:
        ok, m = one(df, params, {**BASE, **ov})
        allok &= ok
        msgs.append(m)
    return allok, " | ".join(msgs)
