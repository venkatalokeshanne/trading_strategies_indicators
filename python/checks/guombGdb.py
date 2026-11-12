"""Independent check — Nasdaq NQ 24H Mejorada (guombGdb; 0R52t1hx is the same script): 1-min New York bars. Close crossing over the PREVIOUS bar's 20-bar highest high above EMA200 reverses long (under the previous 20-bar lowest low
below EMA200 short): close of the opposite id first, then the entry. The exit (stop 1 %, limit 2 %, trail_points = trail_offset = 0.5 % of the close read as TICKS) is issued with the entry on the signal bar. The 23:59 bar
closes everything (queued after any entry of the same bar). Margin off on the pinelib side."""
import numpy as np
import pandas as pd

from indep import bars, compare, np_cross_over, np_cross_under, np_ema, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "guombGdb"
SEED = 232


def build(tv_id, seed):
    df = bars(60000, seed=seed, freq="1min")
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    ny = pd.to_datetime(df["time"], unit="ms", utc=True).dt.tz_convert("America/New_York")
    eod = ((ny.dt.hour == 23) & (ny.dt.minute == 59)).to_numpy()
    e = np_ema(c, 200)
    hh = pd.Series(h).rolling(20).max().shift(1).to_numpy()
    ll = pd.Series(l).rolling(20).min().shift(1).to_numpy()
    with np.errstate(invalid="ignore"):
        lc = np_cross_over(c, hh) & (c > e)
        sc = np_cross_under(c, ll) & (c < e)
    lvl = {1: None, -1: None}

    def orders(i, pos):
        out = []
        if lc[i] and pos <= 0:
            tr = c[i] * 0.5 / 100
            out += [("close", -1), ("entry", 1)]; lvl[1] = (c[i] * 0.99, c[i] * 1.02, tr)
        if sc[i] and pos >= 0:
            tr = c[i] * 0.5 / 100
            out += [("close", 1), ("entry", -1)]; lvl[-1] = (c[i] * 1.01, c[i] * 0.98, tr)
        if eod[i] and pos != 0:                       # close_all() with nothing open creates no order
            out += [("close", 1), ("close", -1)]
        return out

    ref = simulate(o, h, l, c, orders, stop=lambda i, pos, ep, eb: lvl[pos][0], target=lambda i, pos, ep, eb: lvl[pos][1],
                   trail=lambda i, pos, ep, eb: (lvl[pos][2], lvl[pos][2]))
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(tv_id, df, symbol=sym, tf="1", strategy_overrides={"margin_long": 0, "margin_short": 0}), ref)
    return ok and len(ref) > 10, f"{detail} (need >10 trades, got {len(ref)})"


def check():
    return build(TV_ID, SEED)
