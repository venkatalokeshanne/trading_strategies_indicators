"""Independent check — Asia Range Breakout (igbGCjKb): 15-min continuous bars. Trading day = the chart's 09:30-NY daily block. The 19:00-24:00 NY (bar start) range accumulates per day; when it ends it is frozen; during 00:00-05:00 NY a close beyond high + 0.2 (low - 0.2) with close vs EMA200 on the same side enters
when flat and fewer than 2 trades today (counted when the entry orders are placed). Both exits are rebuilt every bar from the position average price at script time (ATR14 x 1.2 stop / x 1.8 target; na while flat) and work from the next bar; the first bar after the 00:00-05:00 window closes any open position."""
import numpy as np
import pandas as pd

from indep import bars, compare, np_atr, np_ema, np_periods, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "igbGCjKb"


def check():
    df = bars(14000, seed=160, freq="15min")
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    ny = pd.to_datetime(df["time"], unit="ms", utc=True).dt.tz_convert("America/New_York")
    mins = (ny.dt.hour * 60 + ny.dt.minute).to_numpy()
    asia = mins >= 1140
    trade = mins < 300
    pid, _ = np_periods(df, 1440)
    ema, atr = np_ema(c, 200), np_atr(h, l, c, 14)
    s = dict(hi=np.nan, lo=np.nan, ready=False, n=0, pa=False, pt=False)
    tmp, lv = {}, {}

    def orders(i, pos):
        out = []
        if i == 0 or pid[i] != pid[i - 1]:
            s.update(hi=np.nan, lo=np.nan, ready=False, n=0)
        if asia[i]:
            s["hi"] = h[i] if np.isnan(s["hi"]) else max(s["hi"], h[i])
            s["lo"] = l[i] if np.isnan(s["lo"]) else min(s["lo"], l[i])
        if (not asia[i]) and s["pa"] and not np.isnan(s["hi"]):
            s["ready"] = True
        with np.errstate(invalid="ignore"):
            up = s["ready"] and trade[i] and c[i] > s["hi"] + 0.2 and c[i] > ema[i]
            dn = s["ready"] and trade[i] and c[i] < s["lo"] - 0.2 and c[i] < ema[i]
        if pos == 0 and s["n"] < 2:
            if up:
                out.append(("entry", 1))
                s["n"] += 1
            if dn:
                out.append(("entry", -1))
                s["n"] += 1
        ep = tmp.get(i) if pos != 0 else None
        lv[i] = None if ep is None else (ep, atr[i])
        if (not trade[i]) and s["pt"] and pos != 0:
            out.append(("close", 1 if pos > 0 else -1))
        s["pa"], s["pt"] = asia[i], trade[i]
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
        ref = simulate(o, h, l, c, orders, stop=stop, target=target)
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="15", strategy_overrides={"margin_long": 0, "margin_short": 0}), ref)
    return ok and len(ref) > 10, f"{detail} (need >10 trades, got {len(ref)})"
