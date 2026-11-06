"""Independent check — OptSeller Pro (M3iyHPdI): 15-minute bars (24 h synthetic, price ~20000) of a stock-style symbol (VWAP restarting at 09:30 New York; Kolkata session 09:45 - 15:15, end-of-day window 15:25 - 15:30), process_orders_on_close (orders fill at the signal close), quantity 1, commission / slippage / margin off.
Bands = VWAP (or EMA20) +/- ATR x mult, the upper rounded up and the lower rounded down to the strike step. In session with fewer than the daily maximum trades (counter reset at the daily-period change, 09:30 New York), a high at or above the upper band (RSI > oversold) enters the 'SellCE' short, a low at or below the lower band (RSI < overbought) the 'SellPE' long, once per leg flag.
Legs are closed by id when the high / low reaches the stop or target percentage levels around the band, or in the end-of-day window; closes of an id not open at script time are ignored and the opposite leg reverses the net position. Uses the quantity-aware bracket reference (indep.simulate_brackets, on_close), comparing quantities too.
Variants: defaults with a 0.2 % target / 0.3 % stop and 5 trades a day; EMA centre, strike step 50, SuperTrend-independent."""
import math

import numpy as np
import pandas as pd

from indep import bars, compare_q, np_atr, np_ema, np_periods, np_rsi, np_vwap, run_conversion, simulate_brackets
from pinelib import SymbolInfo

TV_ID = "M3iyHPdI"


def one(df, params, p):
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    ist = pd.to_datetime(df["time"], unit="ms", utc=True).dt.tz_convert("Asia/Kolkata")
    mins = (ist.dt.hour * 60 + ist.dt.minute).to_numpy()
    sess = (mins >= 585) & (mins < 915)
    eod = (mins >= 925) & (mins < 930)
    pid, _ = np_periods(df, 1440)
    atr = np_atr(h, l, c, 14)
    center = np_vwap(df, (h + l + c) / 3) if p["vw"] else np_ema(c, 20)
    rsi = np_rsi(c, 14)
    S = dict(td=0, ce=False, pe=False)
    R = p["round"]

    def orders(i, info):
        out = []
        if i > 0 and pid[i] != pid[i - 1]:
            S["td"] = 0
        with np.errstate(invalid="ignore"):
            up, dn = center[i] + atr[i] * 1.8, center[i] - atr[i] * 1.8
            cel = math.ceil(up / R) * R if not np.isnan(up) else np.nan
            pel = math.floor(dn / R) * R if not np.isnan(dn) else np.nan
            okd = S["td"] < p["max"]
            cego = h[i] >= cel and sess[i] and okd and rsi[i] > 28
            pego = l[i] <= pel and sess[i] and okd and rsi[i] < 72
            ce_sl, ce_tg = cel * (1 + p["sl"] / 100), cel * (1 - p["tg"] / 100)
            pe_sl, pe_tg = pel * (1 - p["sl"] / 100), pel * (1 + p["tg"] / 100)
        if cego and not S["ce"]:
            out.append(("entry", "SellCE", -1, 1.0))
            S["ce"] = True
            S["td"] += 1
        if S["ce"]:
            if h[i] >= ce_sl:
                out.append(("close", "SellCE"))
                S["ce"] = False
            elif l[i] <= ce_tg:
                out.append(("close", "SellCE"))
                S["ce"] = False
        if pego and not S["pe"]:
            out.append(("entry", "SellPE", 1, 1.0))
            S["pe"] = True
            S["td"] += 1
        if S["pe"]:
            if l[i] <= pe_sl:
                out.append(("close", "SellPE"))
                S["pe"] = False
            elif h[i] >= pe_tg:
                out.append(("close", "SellPE"))
                S["pe"] = False
        if eod[i] and S["ce"]:
            out.append(("close", "SellCE"))
            S["ce"] = False
        if eod[i] and S["pe"]:
            out.append(("close", "SellPE"))
            S["pe"] = False
        return out

    ref = simulate_brackets(o, h, l, c, orders, on_close=True)
    sym = SymbolInfo.make("NASDAQ:XYZ", "stock", qty_step=1e-9)
    ok, d = compare_q(run_conversion(TV_ID, df, symbol=sym, tf="15", params=params,
                                     strategy_overrides={"margin_long": 0, "margin_short": 0, "commission_value": 0, "slippage": 0}), ref)
    return ok and len(ref) > 12, f"{d} (got {len(ref)})"


BASE = dict(round=100, vw=True, sl=0.8, tg=0.5, max=2)


def check():
    df = bars(60000, seed=581, freq="15min")
    base = df["close"].iloc[0]
    for k in ("open", "high", "low", "close"):
        df[k] = 20000 * (df[k] / base) ** 0.1
    msgs, allok = [], True
    cases = (({"SL %": 0.3, "Tgt %": 0.2, "Max/Day": 5}, dict(sl=0.3, tg=0.2, max=5)),
             ({"Use VWAP": False, "Round To": 50, "SL %": 0.3, "Tgt %": 0.2, "Max/Day": 5}, dict(vw=False, round=50, sl=0.3, tg=0.2, max=5)))
    for params, ov in cases:
        ok, m = one(df, params, {**BASE, **ov})
        allok &= ok
        msgs.append(m)
    return allok, " | ".join(msgs)
