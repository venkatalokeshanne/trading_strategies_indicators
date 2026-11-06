"""Independent check — BOT GOAT trailing (jTHvkEVo; jTHvkEVo is the same logic on the 30-minute chart): 15-min continuous bars, margin off. EMA21 crossing EMA55 (Mon-Fri by the New York calendar) flips the position at the next open. The exit order is issued on every bar, so from a trade's fill bar on it holds a stop 100 ticks (0.01) from the entry price and a trailing
stop that arms after 60 ticks of profit and trails by 10 ticks (indep.simulate: trail in ticks)."""
import numpy as np
import pandas as pd

from indep import bars, compare, np_cross_over, np_cross_under, np_ema, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "jTHvkEVo"
FREQ, TF = "30min", "30"


def check():
    df = bars(16000, seed=460, freq=FREQ)
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    wk = pd.to_datetime(df["time"], unit="ms", utc=True).dt.tz_convert("America/New_York").dt.dayofweek.to_numpy() < 5
    f, s = np_ema(c, 21), np_ema(c, 55)
    up, dn = np_cross_over(f, s) & wk, np_cross_under(f, s) & wk

    def orders(i, pos):
        out = []
        if up[i]:
            out += [("close", -1), ("entry", 1)]
        if dn[i]:
            out += [("close", 1), ("entry", -1)]
        return out

    def stop(i, pos, ep, eb):
        return ep - 1.0 if pos > 0 else ep + 1.0

    def trail(i, pos, ep, eb):
        return (60, 10)

    ref = simulate(o, h, l, c, orders, stop=stop, trail=trail, tick=0.01)
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf=TF, strategy_overrides={"margin_long": 0, "margin_short": 0}), ref)
    return ok and len(ref) > 10, f"{detail} (need >10 trades, got {len(ref)})"
