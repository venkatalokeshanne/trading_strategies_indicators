"""Independent check — SPX Scalper (UM3R9Ucl): 5-min bars, one position (reversals allowed), regular session 09:30-16:00 New York by the bar's start time. Long: EMA9 > EMA21, close > EMA200, low <= EMA9 < close,
RSI14 crosses over 50, volume > 1.1 x SMA20 (short is the mirror). Both exit calls run every bar: stop 1 ATR / target 1.3 ATR around the position average price as of the previous script run (none when flat then; the OLD
average applies to a position that opens on this bar, and the direction's own formula). trail_points without trail_offset creates no trailing stop. 18-bar time stop and a session-end exit are close_all (modelled
as closing both directions so a reversal queued in the same bar is closed too), filled at the next open. Position size 5% on the pinelib side; margin and slippage off."""
import numpy as np
import pandas as pd

from indep import bars, compare, np_atr, np_cross_over, np_cross_under, np_ema, np_rsi, np_sma, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "UM3R9Ucl"


def check():
    df = bars(20000, seed=613, freq="5min")
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    v = df["volume"].to_numpy()
    n = len(c)
    ny = pd.to_datetime(df["time"], unit="ms", utc=True).dt.tz_convert("America/New_York")
    mins = (ny.dt.hour * 60 + ny.dt.minute).to_numpy()
    insess = (mins >= 570) & (mins < 960)
    fe, se, te = np_ema(c, 9), np_ema(c, 21), np_ema(c, 200)
    rsi = np_rsi(c, 14)
    vm = np_sma(v, 20)
    atr = np_atr(h, l, c, 14)
    with np.errstate(invalid="ignore"):
        volok = v > vm * 1.10
        ls = insess & (fe > se) & (c > te) & (l <= fe) & (c > fe) & np_cross_over(rsi, 50.0) & volok
        ss = insess & (fe < se) & (c < te) & (h >= fe) & (c < fe) & np_cross_under(rsi, 50.0) & volok
    avgcl = np.full(n, np.nan)
    S = {"i": -1, "ep": np.nan, "bit": 0}

    def orders(i, pos):
        out = []
        if ls[i]:
            out.append(("entry", 1))
        if ss[i]:
            out.append(("entry", -1))
        S["bit"] = S["bit"] + 1 if pos != 0 else 0
        if pos != 0 and S["i"] == i:
            avgcl[i] = S["ep"]
        if pos != 0 and S["bit"] >= 18:
            out += [("close", 1), ("close", -1)]
        elif pos != 0 and not insess[i]:
            out += [("close", 1), ("close", -1)]
        return out

    def stop(i, pos, ep, eb):
        S["i"], S["ep"] = i, ep
        if i == 0 or np.isnan(avgcl[i - 1]) or np.isnan(atr[i - 1]):
            return None
        return avgcl[i - 1] - atr[i - 1] * 1.0 if pos > 0 else avgcl[i - 1] + atr[i - 1] * 1.0

    def target(i, pos, ep, eb):
        if i == 0 or np.isnan(avgcl[i - 1]) or np.isnan(atr[i - 1]):
            return None
        return avgcl[i - 1] + atr[i - 1] * 1.3 if pos > 0 else avgcl[i - 1] - atr[i - 1] * 1.3

    with np.errstate(invalid="ignore"):
        ref = simulate(o, h, l, c, orders, stop=stop, target=target)
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="5", strategy_overrides={"margin_long": 0, "margin_short": 0, "slippage": 0, "default_qty_value": 5}), ref)
    return ok and len(ref) > 10, f"{detail} (need >10 trades, got {len(ref)})"
