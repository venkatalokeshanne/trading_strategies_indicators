"""Independent check — Ombanyu Perang Benua (9Mjjh7tc): hourly bars on a gold (forex-type, trading day from 17:00 New York) chart, one position, market entries at the next open, bracket placed with the entry (works from the fill bar). Sessions by bar-start UTC hour: Asia [0,8), London [7,16), NY last hour [20,21).
Per trading day (reset at the first bar of the day: Asia low / high, London low, NY-last-hour build): they accumulate the lows / highs of their bars. The first bar after the NY last hour copies the build into the 'final low' (kept across days) and clears the build - but the day reset runs first, so when the day starts on that same bar (US summer, 17:00 NY = 21:00 UTC)
the copy never happens. After Asia ends (first non-Asia bar) with the Asian low below the final low: short, stop = Asian high + 0.15 ATR14, target = close - 2 x risk. After London ends with the Asian and London lows both >= the final low: long, stop = final low - 0.15 ATR, target = close + 2 x risk (flat only; risk > one tick). Margin off on the pinelib side."""
import numpy as np
import pandas as pd

from indep import bars, compare, np_atr, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "9Mjjh7tc"


def check():
    df = bars(40000, seed=841, freq="1h")
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    atr = np_atr(h, l, c, 14)
    utc_h = pd.to_datetime(df["time"], unit="ms", utc=True).dt.hour.to_numpy()
    ny = pd.to_datetime(df["time"], unit="ms", utc=True).dt.tz_convert("America/New_York")
    day = (ny.dt.tz_localize(None) - pd.Timedelta(hours=17)).dt.date.to_numpy()
    in_a = (utc_h >= 0) & (utc_h < 8)
    in_l = (utc_h >= 7) & (utc_h < 16)
    in_n = (utc_h >= 20) & (utc_h < 21)
    S = dict(al=np.nan, ah=np.nan, ll=np.nan, nb=np.nan, nf=np.nan)
    lev = {}
    mt = 0.01

    def orders(i, pos):
        out = []
        if i > 0 and day[i] != day[i - 1]:
            S.update(al=np.nan, ah=np.nan, ll=np.nan, nb=np.nan)
        if in_a[i]:
            S["al"] = l[i] if np.isnan(S["al"]) else min(S["al"], l[i])
            S["ah"] = h[i] if np.isnan(S["ah"]) else max(S["ah"], h[i])
        if in_l[i]:
            S["ll"] = l[i] if np.isnan(S["ll"]) else min(S["ll"], l[i])
        if in_n[i]:
            S["nb"] = l[i] if np.isnan(S["nb"]) else min(S["nb"], l[i])
        pa = in_a[i - 1] if i else False
        pl = in_l[i - 1] if i else False
        pn = in_n[i - 1] if i else False
        if pn and not in_n[i] and not np.isnan(S["nb"]):
            S["nf"], S["nb"] = S["nb"], np.nan
        a_end, l_end = pa and not in_a[i], pl and not in_l[i]
        sig_s = sig_l = False
        if not np.isnan(S["nf"]):
            if a_end and not np.isnan(S["al"]) and S["al"] < S["nf"]:
                sig_s = True
            if l_end and not np.isnan(S["al"]) and not np.isnan(S["ll"]) and S["al"] >= S["nf"] and S["ll"] >= S["nf"]:
                sig_l = True
        if pos == 0:
            if sig_s:
                sl = S["ah"] + atr[i] * 0.15
                risk = sl - c[i]
                if risk > mt:
                    out.append(("entry", -1))
                    lev[i] = (sl, c[i] - risk * 2.0)
            if sig_l:
                sl = S["nf"] - atr[i] * 0.15
                risk = c[i] - sl
                if risk > mt:
                    out.append(("entry", 1))
                    lev[i] = (sl, c[i] + risk * 2.0)
        return out

    stop = lambda i, pos, ep, eb: lev[eb - 1][0] if eb - 1 in lev else None
    tgt = lambda i, pos, ep, eb: lev[eb - 1][1] if eb - 1 in lev else None
    with np.errstate(invalid="ignore"):
        ref = simulate(o, h, l, c, orders, stop=stop, target=tgt)
    sym = SymbolInfo.make("OANDA:XAUUSD", "forex", mintick=0.01, qty_step=1e-9)
    ok, d = compare(run_conversion(TV_ID, df, symbol=sym, tf="60", strategy_overrides={"margin_long": 0, "margin_short": 0}), ref)
    return ok and len(ref) > 10, f"{d} (got {len(ref)})"
