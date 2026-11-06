"""Independent check — GC Asia VWAP Pullback (NWBqWw6O): 15-min continuous bars, VWAP band 1.5 here (passed to both sides), orders at the signal close (process_orders_on_close). Asia session = New York 18:00-03:00 (bar start). Long: close > VWAP(hlc3, 09:30-NY reset), low within +/- band of VWAP, close > VWAP, in session;
short mirrors with the high. Both exits are rebuilt every bar from the position average price at script time (ATR14 x 1.2 stop, x 1.8 target; na while flat), apply from the next bar and to the trade of their own direction (also right after a reversal); on the first bar after the session
ends any open trade is closed at that bar's close."""
import numpy as np
import pandas as pd

from indep import bars, compare, np_atr, np_vwap, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "NWBqWw6O"
BAND = 1.5


def check():
    df = bars(14000, seed=140, freq="15min")
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    ny = pd.to_datetime(df["time"], unit="ms", utc=True).dt.tz_convert("America/New_York")
    mins = (ny.dt.hour * 60 + ny.dt.minute).to_numpy()
    asia = (mins >= 1080) | (mins < 180)
    vw = np_vwap(df, (h + l + c) / 3)
    atr = np_atr(h, l, c, 14)
    with np.errstate(invalid="ignore"):
        lg = asia & (c > vw) & (l <= vw + BAND) & (l >= vw - BAND) & (c > vw)
        sh = asia & (c < vw) & (h >= vw - BAND) & (h <= vw + BAND) & (c < vw)
    prev_asia = np.r_[False, asia[:-1]]
    tmp, lv = {}, {}

    def orders(i, pos):
        out = []
        if lg[i]:
            out.append(("entry", 1))
        if sh[i]:
            out.append(("entry", -1))
        ep = tmp.get(i) if pos != 0 else None
        lv[i] = None if ep is None else (ep, atr[i])
        if (not asia[i]) and prev_asia[i] and pos != 0:
            out.append(("close", 1 if pos > 0 else -1))
        return out

    def stop(i, pos, ep, eb):
        tmp[i] = ep
        p = lv.get(i - 1) if i > 0 else None
        if p is None or np.isnan(p[1]):
            return None
        return p[0] - 1.2 * p[1] if pos > 0 else p[0] + 1.2 * p[1]

    def target(i, pos, ep, eb):
        p = lv.get(i - 1) if i > 0 else None
        if p is None or np.isnan(p[1]):
            return None
        return p[0] + 1.8 * p[1] if pos > 0 else p[0] - 1.8 * p[1]

    with np.errstate(invalid="ignore"):
        ref = simulate(o, h, l, c, orders, stop=stop, target=target, on_close=True)
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="15", params={"VWAP pullback band ($)": BAND},
                                        strategy_overrides={"margin_long": 0, "margin_short": 0}), ref)
    return ok and len(ref) > 10, f"{detail} (need >10 trades, got {len(ref)})"
