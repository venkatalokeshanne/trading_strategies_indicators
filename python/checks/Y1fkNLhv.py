"""Independent check — Camarilla R5/S5 weekly reversal (Y1fkNLhv): previous Monday-week's
H/L/C from pandas, fade R5/S5, take profit at R4/S4 (the level from the previous close)."""
import pandas as pd

from indep import bars, compare, run_conversion, simulate

TV_ID = "Y1fkNLhv"


def check():
    df = bars(3000, seed=89)
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    t = pd.to_datetime(df.time, unit="ms", utc=True)
    wk = (t.dt.floor("D") - pd.to_timedelta(t.dt.weekday, unit="D")).to_numpy()
    g = pd.DataFrame({"wk": wk, "h": h, "l": l, "c": c}).groupby("wk").agg(h=("h", "max"), l=("l", "min"), c=("c", "last"))
    prev = g.shift(1).reindex(wk)
    ph, pl, pc = (prev[k].to_numpy() for k in ("h", "l", "c"))
    rng = ph - pl
    r4, s4 = pc + rng * 1.1 / 2, pc - rng * 1.1 / 2
    r5 = ph / pl * pc
    s5 = pc - (r5 - pc)
    sell = (h >= r5) & (c < r5)
    buy = (l <= s5) & (c > s5)
    ref = simulate(o, h, l, c, lambda i, pos: ([("entry", -1)] if sell[i] else []) + ([("entry", 1)] if buy[i] else []),
                   target=lambda i, pos, ep, eb: (s4 if pos > 0 else r4)[i - 1])
    return compare(run_conversion(TV_ID, df), ref)
