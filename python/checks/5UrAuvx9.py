"""Independent check — Gold HFT Hybrid MT5 (5UrAuvx9): 5-min New York bars. EMA 9/21 cross with ADX>15 on Monday-Friday 07:00-20:00 NY. Both exits are
unconditional: target +5 / stop -3 points around the position's average price as of the previous close (na while flat; the OLD average on a reversal's
first bar) PLUS an always-armed trailing stop: activation 3 points from the entry price, offset 1.5 points (300 / 150 ticks of 0.01). Uses
indep.exit_hit (stop+target+trail)."""
import numpy as np
import pandas as pd

from indep import bars, compare, np_cross_over, np_cross_under, np_dmi, np_ema, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "5UrAuvx9"


def check():
    df = bars(30000, seed=127, freq="5min")
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    ny = pd.to_datetime(df["time"], unit="ms", utc=True).dt.tz_convert("America/New_York")
    m = (ny.dt.hour * 60 + ny.dt.minute).to_numpy()
    wk = (ny.dt.dayofweek < 5).to_numpy()
    sess = wk & (m >= 420) & (m < 1200)
    f, s = np_ema(c, 9), np_ema(c, 21)
    _, _, adx = np_dmi(h, l, c, 14)
    with np.errstate(invalid="ignore"):
        lg = np_cross_over(f, s) & (adx > 15) & sess
        sg = np_cross_under(f, s) & (adx > 15) & sess
    ep_now, avg_close = {}, np.full(n, np.nan)

    def orders(i, pos):
        avg_close[i] = ep_now.get(i, np.nan) if pos != 0 else np.nan
        return ([("entry", 1)] if lg[i] else []) + ([("entry", -1)] if sg[i] else [])

    def stop(i, pos, ep, eb):
        ep_now[i] = ep
        if i == 0 or np.isnan(avg_close[i - 1]):
            return None
        return avg_close[i - 1] - 3.0 if pos > 0 else avg_close[i - 1] + 3.0

    def target(i, pos, ep, eb):
        if i == 0 or np.isnan(avg_close[i - 1]):
            return None
        return avg_close[i - 1] + 5.0 if pos > 0 else avg_close[i - 1] - 5.0

    ref = simulate(o, h, l, c, orders, stop=stop, target=target, trail=lambda i, pos, ep, eb: (300.0, 150.0), tick=0.01)
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="5", strategy_overrides={"margin_long": 0, "margin_short": 0}), ref)
    return ok and len(ref) > 10, f"{detail} (need >10 trades, got {len(ref)})"
