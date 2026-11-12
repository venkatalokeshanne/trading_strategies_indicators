"""Independent check — PDH/PDL Break 0DTE (9o35mG93): 5-minute bars (24h synthetic, New York clock), one position (entries reverse), trade list only. Trading day = from 09:30 New York (pinelib/TradingView stock convention); the previous day's high / low
(PDH / PDL) are frozen at the first bar of the new day. Trend = daily-anchored VWAP (from 09:30) above the 60-minute EMA20 (09:30 blocks, lookahead off). WaveTrend: esa = EMA10(hlc3), dv = EMA10(|hlc3 - esa|), ci = (hlc3 - esa) / (0.015 dv),
wt1 = EMA21(ci); |wt1| < 60 and wt1 rising (long) / falling (short). Window: the script's float arithmetic gives (930/100)*60 + 30 = 588 and (1130/100)*60 + 30 = 708 minutes (09:48 .. 11:48 New York). A close above PDH (below PDL) once per day per side
inside the window enters; stop = the broken level, target = close +/- 2 x |close - level|, kept as variables and issued from the first script run with the position (works from the bar after); any position is closed (next open) from 11:48 on. Margin and slippage off on the pinelib side."""
import numpy as np
import pandas as pd

from indep import bars, compare, np_ema, np_periods, np_security_lookahead_off, np_vwap, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "9o35mG93"


def check():
    df = bars(25000, seed=531, freq="5min")
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    ny = pd.to_datetime(df["time"], unit="ms", utc=True).dt.tz_convert("America/New_York")
    et = (ny.dt.hour * 60 + ny.dt.minute).to_numpy()
    tday = (ny.dt.tz_localize(None) - pd.Timedelta(minutes=570)).dt.date.to_numpy()
    hlc3 = (h + l + c) / 3
    pid, last_of = np_periods(df, 60)
    pcl = np.array([c[last_of & (pid == k)][0] for k in range(pid[-1] + 1)])
    h_ema = np_security_lookahead_off(np_ema(pcl, 20), pid, last_of)
    vw = np_vwap(df, hlc3)
    esa = np_ema(hlc3, 10)
    dv = np_ema(np.abs(hlc3 - esa), 10)
    ci = (hlc3 - esa) / (0.015 * np.where(dv == 0.0, 0.000001, dv))
    wt = np_ema(ci, 21)
    wt1 = np.r_[np.nan, wt[:-1]]
    S = dict(pdh=np.nan, pdl=np.nan, dh=np.nan, dl=np.nan, lf=False, sf=False, ls=np.nan, lt=np.nan, ss=np.nan, st=np.nan)
    poscl = np.zeros(n)
    stop_arr = np.full(n, np.nan)
    tgt_arr = np.full(n, np.nan)

    def orders(i, pos):
        poscl[i] = pos
        out = []
        if i == 0 or tday[i] != tday[i - 1]:
            S["pdh"], S["pdl"], S["dh"], S["dl"] = S["dh"], S["dl"], h[i], l[i]
            S["lf"] = S["sf"] = False
        else:
            S["dh"], S["dl"] = max(S["dh"], h[i]), min(S["dl"], l[i])
        in_time = 588 <= et[i] < 708
        with np.errstate(invalid="ignore"):
            bull = vw[i] > h_ema[i]
            wt_ok = abs(wt[i]) < 60.0
            lb = (not np.isnan(S["pdh"])) and (not S["lf"]) and c[i] > S["pdh"] and bull and wt_ok and wt[i] > wt1[i] and in_time
            sb = (not np.isnan(S["pdl"])) and (not S["sf"]) and c[i] < S["pdl"] and (not bull) and wt_ok and wt[i] < wt1[i] and in_time
        if lb:
            S["lf"] = True
            S["ls"], S["lt"] = S["pdh"], c[i] + 2.0 * (c[i] - S["pdh"])
            out.append(("entry", 1))
        if sb:
            S["sf"] = True
            S["ss"], S["st"] = S["pdl"], c[i] - 2.0 * (S["pdl"] - c[i])
            out.append(("entry", -1))
        if pos > 0:
            stop_arr[i], tgt_arr[i] = S["ls"], S["lt"]
        if pos < 0:
            stop_arr[i], tgt_arr[i] = S["ss"], S["st"]
        if et[i] >= 708 and pos != 0:
            out += [("close", 1), ("close", -1)]
        return out

    def stop(i, pos, ep, eb):
        if i == 0 or poscl[i - 1] * pos <= 0 or np.isnan(stop_arr[i - 1]):
            return None
        return stop_arr[i - 1]

    def target(i, pos, ep, eb):
        if i == 0 or poscl[i - 1] * pos <= 0 or np.isnan(tgt_arr[i - 1]):
            return None
        return tgt_arr[i - 1]

    with np.errstate(invalid="ignore"):
        ref = simulate(o, h, l, c, orders, stop=stop, target=target)
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="5", strategy_overrides={"margin_long": 0, "margin_short": 0, "slippage": 0, "default_qty_value": 5}), ref)
    return ok and len(ref) > 10, f"{detail} (need >10 trades, got {len(ref)})"
