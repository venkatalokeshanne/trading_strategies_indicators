"""Independent check — Atlantium Gold Safe Trader (Bjez8v7B): 5-min New York bars. EMA 10/40 crosses with RSI>50 / <50, 08:00-19:59 NY, flat, no ATR(5) spike over 2.5x ATR(20).
Pine v6 short-circuits `can_trade and ta.crossover(...)`: the cross only RUNS on bars where can_trade holds, so its "previous bar" is the last bar it ran on (LESSONS
P4/P5). SL/TP are the signal bar's ATR(14)*2.5 / *5.5 levels kept in vars; one exit without from_entry is issued each bar a position exists (works from the bar after the
fill, levels as of the previous bar); Friday from 20:00 NY closes the position at the next open."""
import numpy as np
import pandas as pd

from indep import bars, compare, np_atr, np_ema, np_rsi, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "Bjez8v7B"


def check():
    df = bars(30000, seed=165, freq="5min")
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    ny = pd.to_datetime(df["time"], unit="ms", utc=True).dt.tz_convert("America/New_York")
    hr = ny.dt.hour.to_numpy()
    fri = (ny.dt.dayofweek == 4).to_numpy()
    weekend = fri & (hr >= 20)
    allowed = (hr >= 8) & (hr <= 19)
    af, as_, atr = np_atr(h, l, c, 5), np_atr(h, l, c, 20), np_atr(h, l, c, 14)
    spike = af > as_ * 2.5
    ef, es, rsi = np_ema(c, 10), np_ema(c, 40), np_rsi(c, 14)
    st = dict(la=np.nan, lb=np.nan, sa=np.nan, sb=np.nan, sl=np.nan, tp=np.nan)     # last evaluated (ema_f, ema_s) for the up / down cross
    poscl, lvl = np.zeros(n), []

    def orders(i, pos):
        poscl[i] = pos
        out = []
        can = pos == 0 and allowed[i] and not weekend[i] and not spike[i]
        up = dn = False
        if can:
            up = ef[i] > es[i] and st["la"] <= st["lb"]
            dn = ef[i] < es[i] and st["sa"] >= st["sb"]
            st.update(la=ef[i], lb=es[i], sa=ef[i], sb=es[i])
            if up and rsi[i] > 50:
                out.append(("entry", 1)); st["sl"], st["tp"] = c[i] - atr[i] * 2.5, c[i] + atr[i] * 5.5
            if dn and rsi[i] < 50:
                out.append(("entry", -1)); st["sl"], st["tp"] = c[i] + atr[i] * 2.5, c[i] - atr[i] * 5.5
        if weekend[i] and pos != 0:
            out.append(("close", pos))
        lvl.append((st["sl"], st["tp"]))
        return out

    def level(k):
        return lambda i, pos, ep, eb: lvl[i - 1][k] if (i > 0 and poscl[i - 1] != 0) else None

    with np.errstate(invalid="ignore"):
        ref = simulate(o, h, l, c, orders, stop=level(0), target=level(1))
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="5"), ref)
    return ok and len(ref) > 10, f"{detail} (need >10 trades, got {len(ref)})"
