"""Independent check — NASDAQ ORB Strict (eWkFVSVF): 5-min New York bars, process_orders_on_close (market orders fill
at the signal bar's close). Range = bars starting 09:30-09:44, locked at the 09:45 bar; first close through the range
after 09:45 with RVOL >= 1.5 enters (one trade per day), stop = range midpoint, target 2R from the signal close;
all positions are closed on the 16:00 bar. The bracket works from the bar after the signal."""
import numpy as np
import pandas as pd

from indep import bars, compare, np_sma, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "eWkFVSVF"


def check():
    df = bars(20000, seed=80, freq="5min")
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    v = df["volume"].to_numpy()
    n = len(c)
    ny = pd.to_datetime(df["time"], unit="ms", utc=True).dt.tz_convert("America/New_York")
    hr, mi = ny.dt.hour.to_numpy(), ny.dt.minute.to_numpy()
    vma = np_sma(v, 20)
    st = dict(hi=np.nan, lo=np.nan, mid=np.nan, locked=False, taken=False, stop=np.nan, tgt=np.nan)
    prev_hi = prev_lo = np.nan
    after = []

    def orders(i, pos):
        nonlocal prev_hi, prev_lo
        out = []
        if hr[i] == 9 and mi[i] == 30:
            st.update(hi=h[i], lo=l[i], mid=np.nan, locked=False, taken=False)
        elif hr[i] == 9 and 30 <= mi[i] < 45:
            st["hi"] = np.nan if np.isnan(st["hi"]) else max(h[i], st["hi"])
            st["lo"] = np.nan if np.isnan(st["lo"]) else min(l[i], st["lo"])
        if hr[i] == 9 and mi[i] == 45 and not st["locked"]:
            st.update(mid=(st["hi"] + st["lo"]) / 2, locked=True)
        rvol = v[i] / vma[i] if (not np.isnan(vma[i]) and vma[i] > 0) else 1.0
        win = (hr[i] == 9 and mi[i] >= 45) or (9 < hr[i] < 16)
        up = i > 0 and c[i] > st["hi"] and c[i - 1] <= prev_hi          # crossover uses the previous bar's level
        dn = i > 0 and c[i] < st["lo"] and c[i - 1] >= prev_lo
        if win and st["locked"] and not st["taken"] and pos == 0:
            if up:
                if rvol >= 1.5:
                    out.append(("entry", 1))
                    st.update(stop=st["mid"], tgt=c[i] + (c[i] - st["mid"]) * 2.0, taken=True)
            elif dn:
                if rvol >= 1.5:
                    out.append(("entry", -1))
                    st.update(stop=st["mid"], tgt=c[i] - (st["mid"] - c[i]) * 2.0, taken=True)
        if hr[i] == 16 and mi[i] == 0 and pos != 0:
            out.append(("close", pos))
        prev_hi, prev_lo = st["hi"], st["lo"]
        after.append((st["stop"], st["tgt"]))
        return out

    def level(k):
        return lambda i, pos, ep, eb: after[i - 1][k] if (i > 0 and i > eb) else None

    with np.errstate(invalid="ignore"):
        ref = simulate(o, h, l, c, orders, stop=level(0), target=level(1), on_close=True)
    sym = SymbolInfo.make("NASDAQ:QQQ", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="5"), ref)
    return ok and len(ref) > 10, f"{detail} (need >10 trades, got {len(ref)})"
