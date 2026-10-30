"""Independent check — SENSEX Disciplined Sniper (lhrEFuTq): 5-min New York bars. Windows 09:20-12:00 and 13:30-14:30 (bar start); a per-trading-day counter (days start at 09:30, the pinelib / np_periods convention) caps entries
at 4 and resets on the first bar of each day; flat + close > EMA200 + RSI14 > 60 + ADX14 > 20 + volume > SMA20 buys (mirror short at RSI < 40). Entry + exit (limit/stop +/- 80 points around the signal close) are issued
on the signal bar, so the bracket works from the fill bar. Margin off on the pinelib side."""
import numpy as np
import pandas as pd

from indep import bars, compare, np_adx, np_ema, np_periods, np_rsi, np_sma, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "lhrEFuTq"


def check():
    df = bars(40000, seed=230, freq="5min")
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    v = df["volume"].to_numpy()
    n = len(c)
    ny = pd.to_datetime(df["time"], unit="ms", utc=True).dt.tz_convert("America/New_York")
    m = (ny.dt.hour * 60 + ny.dt.minute).to_numpy()
    win = ((m >= 560) & (m < 720)) | ((m >= 810) & (m < 870))
    day, _ = np_periods(df, 1440)
    e, rsi, adx = np_ema(c, 200), np_rsi(c, 14), np_adx(h, l, c, 14)
    with np.errstate(invalid="ignore"):
        hv = v > np_sma(v, 20)
        base = win & (adx > 20) & hv
        lg, sg = base & (c > e) & (rsi > 60), base & (c < e) & (rsi < 40)
    cnt = [0]
    lvl = {1: (np.nan, np.nan), -1: (np.nan, np.nan)}

    def orders(i, pos):
        if i > 0 and day[i] != day[i - 1]:
            cnt[0] = 0
        out = []
        if cnt[0] < 4 and pos == 0:
            if lg[i]:
                out.append(("entry", 1)); lvl[1] = (c[i] - 80, c[i] + 80); cnt[0] += 1
            if sg[i]:
                out.append(("entry", -1)); lvl[-1] = (c[i] + 80, c[i] - 80); cnt[0] += 1
        return out

    with np.errstate(invalid="ignore"):
        ref = simulate(o, h, l, c, orders, stop=lambda i, pos, ep, eb: lvl[pos][0], target=lambda i, pos, ep, eb: lvl[pos][1])
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="5", strategy_overrides={"margin_long": 0, "margin_short": 0}), ref)
    return ok and len(ref) > 10, f"{detail} (need >10 trades, got {len(ref)})"
