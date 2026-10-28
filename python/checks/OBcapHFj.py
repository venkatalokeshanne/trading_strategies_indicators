"""Independent check — Donchian Basis Cross with Band TP (OBcapHFj): 15-min continuous bars, window parameters set to span the whole sample (2015-01-01 .. 2099 UTC). Basis = (highest high 40 + lowest low 40)/2; a close crossing over (under) it, inside 09:30-16:00 UTC (bar start) and flat, enters long (short) at the next open;
stop = close -/+ 3 ATR14, target = the opposite band value (upper for long, lower for short) at the signal bar, both fixed on that bar."""
import numpy as np
import pandas as pd

from indep import bars, compare, np_atr, np_cross_over, np_cross_under, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "OBcapHFj"


def check():
    df = bars(16000, seed=190, freq="15min")
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    ub = pd.Series(h).rolling(40).max().to_numpy()
    lb = pd.Series(l).rolling(40).min().to_numpy()
    basis = (ub + lb) / 2
    mins = (pd.to_datetime(df["time"], unit="ms", utc=True).dt.hour * 60 + pd.to_datetime(df["time"], unit="ms", utc=True).dt.minute).to_numpy()
    sess = (mins >= 570) & (mins < 960)
    atr = np_atr(h, l, c, 14)
    with np.errstate(invalid="ignore"):
        lg, sh = np_cross_over(c, basis) & sess, np_cross_under(c, basis) & sess
    lvl = {}

    def orders(i, pos):
        out = []
        if lg[i] and pos == 0:
            out.append(("entry", 1))
            lvl[1] = (c[i] - 3 * atr[i], ub[i])
        if sh[i] and pos == 0:
            out.append(("entry", -1))
            lvl[-1] = (c[i] + 3 * atr[i], lb[i])
        return out

    def stop(i, pos, ep, eb):
        return lvl[1 if pos > 0 else -1][0]

    def target(i, pos, ep, eb):
        return lvl[1 if pos > 0 else -1][1]

    with np.errstate(invalid="ignore"):
        ref = simulate(o, h, l, c, orders, stop=stop, target=target)
    t0 = int(pd.Timestamp("2015-01-01", tz="UTC").value // 1_000_000)
    t1 = int(pd.Timestamp("2099-01-01", tz="UTC").value // 1_000_000)
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="15", params={"Start Time": t0, "End Time": t1},
                                        strategy_overrides={"margin_long": 0, "margin_short": 0}), ref)
    return ok and len(ref) > 10, f"{detail} (need >10 trades, got {len(ref)})"
