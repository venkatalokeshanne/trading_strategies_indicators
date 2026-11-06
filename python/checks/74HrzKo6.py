"""Independent check — Gold NY Open ORB (74HrzKo6): 15-min continuous bars, slippage 0 (market-fill slippage is outside indep's scope for this script's exits). The trading day rolls at 09:30 New York (a new 'D' bar), which resets
the opening range (13:00-13:59 UTC bars of Mon-Fri by New York weekday) and the once-per-day flag. After the range is ready (a later bar of hour >= 14), a bullish close back above the range high between 14:00 and 16:30 UTC (previous close <= high,
volume > 1.5 x SMA20, range <= 2.5 ATR14, ATR <= 2 x SMA20(ATR)) enters long; bracket = close -/+ range, fixed at the signal; the 16:30 UTC weekday bar closes an open long."""
import numpy as np
import pandas as pd

from indep import bars, compare, np_atr, np_periods, np_sma, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "74HrzKo6"


def check():
    df = bars(24000, seed=71, freq="15min")
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    v = df["volume"].to_numpy()
    n = len(c)
    utc = pd.to_datetime(df["time"], unit="ms", utc=True)
    hr, mi = utc.dt.hour.to_numpy(), utc.dt.minute.to_numpy()
    wk = pd.to_datetime(df["time"], unit="ms", utc=True).dt.tz_convert("America/New_York").dt.dayofweek.to_numpy() < 5
    pid, _ = np_periods(df, 1440)
    atr = np_atr(h, l, c, 14)
    atr_avg = np_sma(atr, 20)
    vavg = np_sma(v, 20)
    s = dict(hi=np.nan, lo=np.nan, ready=False, fired=False)
    lvl = {}

    def orders(i, pos):
        out = []
        if i == 0 or pid[i] != pid[i - 1]:
            s.update(hi=np.nan, lo=np.nan, ready=False, fired=False)
        orp = wk[i] and hr[i] == 13
        ew = wk[i] and hr[i] >= 14 and (hr[i] < 16 or (hr[i] == 16 and mi[i] <= 30))
        se = wk[i] and hr[i] == 16 and mi[i] == 30
        if orp:
            s["hi"] = h[i] if np.isnan(s["hi"]) else max(s["hi"], h[i])
            s["lo"] = l[i] if np.isnan(s["lo"]) else min(s["lo"], l[i])
        if not orp and not np.isnan(s["hi"]) and not s["ready"] and hr[i] >= 14:
            s["ready"] = True
        rng = s["hi"] - s["lo"]
        with np.errstate(invalid="ignore"):
            ok = s["ready"] and not np.isnan(rng) and rng <= atr[i] * 2.5
            regime = atr[i] <= atr_avg[i] * 2.0
            lb = (ew and ok and regime and not s["fired"] and c[i] > s["hi"] and i > 0 and c[i - 1] <= s["hi"]
                  and c[i] > o[i] and v[i] > vavg[i] * 1.5)
        if lb:
            out.append(("entry", 1))
            lvl[1] = (c[i] - rng, c[i] + rng)
            s["fired"] = True
        if se and pos > 0:
            out.append(("close", 1))
        return out

    def stop(i, pos, ep, eb):
        return lvl.get(1, (None, None))[0]

    def target(i, pos, ep, eb):
        return lvl.get(1, (None, None))[1]

    ref = simulate(o, h, l, c, orders, stop=stop, target=target)
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="15", strategy_overrides={"margin_long": 0, "margin_short": 0, "slippage": 0}), ref)
    return ok and len(ref) > 5, f"{detail} (need >5 trades, got {len(ref)})"
