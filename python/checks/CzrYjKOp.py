"""Independent check — Traffic Light (CzrYjKOp): 5-min New York bars. The first opposite-colour candle pair of
each trading day (day starts 09:30 NY) defines hi/lo; a close through hi/lo while flat enters (max 3 per day)
with stop = the other side and target = 2R; the 15:20+ bar closes any position at the next open. The bracket is
re-issued every bar in a position, so it first works on the bar after the fill."""
import numpy as np
import pandas as pd

from indep import bars, compare, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "CzrYjKOp"


def check():
    df = bars(20000, seed=77, freq="5min")
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    ny = pd.to_datetime(df["time"], unit="ms", utc=True).dt.tz_convert("America/New_York")
    hr, mi = ny.dt.hour.to_numpy(), ny.dt.minute.to_numpy()
    key = (ny - pd.Timedelta(minutes=570)).dt.date.to_numpy()
    st = dict(hi=np.nan, lo=np.nan, found=False, count=0, stop=np.nan, tgt=np.nan)
    after = []                                            # (stop, target) at the end of each bar

    def orders(i, pos):
        out = []
        new_day = i > 0 and key[i] != key[i - 1]
        if new_day:
            st.update(hi=np.nan, lo=np.nan, found=False, count=0)
        if not st["found"] and not new_day and i > 0:
            g, r = c[i] > o[i], c[i] < o[i]
            pg, pr = c[i - 1] > o[i - 1], c[i - 1] < o[i - 1]
            if (g and pr) or (r and pg):
                st.update(hi=max(h[i], h[i - 1]), lo=min(l[i], l[i - 1]), found=True)
        up = i > 0 and not np.isnan(st["hi"]) and c[i] > st["hi"] and c[i - 1] <= st["hi"]
        dn = i > 0 and not np.isnan(st["lo"]) and c[i] < st["lo"] and c[i - 1] >= st["lo"]
        if st["found"] and up and pos == 0 and st["count"] < 3:
            st.update(stop=st["lo"], tgt=st["hi"] + (st["hi"] - st["lo"]) * 2.0, count=st["count"] + 1)
            out.append(("entry", 1))
        if st["found"] and dn and pos == 0 and st["count"] < 3:
            st.update(stop=st["hi"], tgt=st["lo"] - (st["hi"] - st["lo"]) * 2.0, count=st["count"] + 1)
            out.append(("entry", -1))
        if hr[i] == 15 and mi[i] >= 20 and pos != 0:
            out.append(("close", pos))
        after.append((st["stop"], st["tgt"]))
        return out

    def level(k):
        return lambda i, pos, ep, eb: after[i - 1][k] if (i > 0 and i > eb) else None

    ref = simulate(o, h, l, c, orders, stop=level(0), target=level(1))
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="5"), ref)
    return ok and len(ref) > 10, f"{detail} (need >10 trades, got {len(ref)})"
