"""Independent check — Q-Trend with SL and Trailing Stop (VapgznSq): daily bars from 2015 (the date window is passed as 2015-01-01 .. 2035-12-31). m starts at (highest + lowest of 200 closes) / 2 and is frozen from the previous
bar once bar_index > 200; epsilon = ATR14 of the previous bar; change_up = cross(over) of the close with m + epsilon, or the close above it (Type B uses ta.cross for both); m then steps by +/- epsilon on a break (or stays). A change to
B after S (S after B) enters and closes the other side; the exit is `stop = atr * 2` as a PRICE level with trail_points = trail_offset = atr * 1 ticks (tick 0.01), issued with the entry. Run for Type A and Type B.
Margin off on the pinelib side."""
import numpy as np
import pandas as pd

from indep import bars, compare, np_atr, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "VapgznSq"
TICK = 0.01


def check():
    df = bars(4500, seed=292)
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    hi = pd.Series(c).rolling(200).max().to_numpy()
    lo = pd.Series(c).rolling(200).min().to_numpy()
    atr_raw = np_atr(h, l, c, 14)
    atr = np.r_[np.nan, atr_raw[:-1]]
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    t0 = int(pd.Timestamp("2015-01-01", tz="UTC").value // 1_000_000)
    t1 = int(pd.Timestamp("2035-12-31", tz="UTC").value // 1_000_000)
    msgs, ok_all = [], True
    for mode in ("Type A", "Type B"):
        m_prev = np.nan
        ls_prev = ""
        up_prev = dn_prev = np.nan
        cu = np.zeros(n, bool)
        cd = np.zeros(n, bool)
        lc, sc = np.zeros(n, bool), np.zeros(n, bool)
        for i in range(n):
            m = (hi[i] + lo[i]) / 2
            m = m_prev if i > 200 else m
            eps = 1.0 * atr[i]
            up, dn = m + eps, m - eps
            s, s1 = c[i], (c[i - 1] if i else np.nan)
            with np.errstate(invalid="ignore"):
                if mode == "Type B":
                    xu = bool((s > up and s1 <= up_prev) or (s < up and s1 >= up_prev))
                    xd = bool((s > dn and s1 <= dn_prev) or (s < dn and s1 >= dn_prev))
                else:
                    xu = bool(s > up and s1 <= up_prev)
                    xd = bool(s < dn and s1 >= dn_prev)
                chg_up = xu or bool(s > up)
                chg_dn = xd or bool(s < dn)
                if (chg_up or chg_dn) and m != m_prev:
                    m_final = m
                elif chg_up:
                    m_final = m + eps
                elif chg_dn:
                    m_final = m - eps
                else:
                    m_final = m if np.isnan(m_prev) else m_prev
            ls = "B" if chg_up else ("S" if chg_dn else ls_prev)
            lc[i] = chg_up and ls_prev != "B"
            sc[i] = chg_dn and ls_prev != "S"
            ls_prev = ls
            up_prev, dn_prev, m_prev = up, dn, m_final
        lvl = {1: (np.nan, np.nan), -1: (np.nan, np.nan)}

        def orders(i, pos, lc=lc, sc=sc, lvl=lvl):
            out = []
            if lc[i]:
                out += [("entry", 1), ("close", -1)]; lvl[1] = (atr[i] * 2.0, atr[i] * 1.0)
            if sc[i]:
                out += [("entry", -1), ("close", 1)]; lvl[-1] = (atr[i] * 2.0, atr[i] * 1.0)
            return out

        with np.errstate(invalid="ignore"):
            ref = simulate(o, h, l, c, orders, stop=lambda i, pos, ep, eb, lvl=lvl: lvl[pos][0],
                           trail=lambda i, pos, ep, eb, lvl=lvl: (lvl[pos][1], lvl[pos][1]), tick=TICK)
        ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="D", params={"Signal mode": mode, "Start Date": t0, "End Date": t1},
                                            strategy_overrides={"margin_long": 0, "margin_short": 0}), ref)
        ok_all = ok_all and ok and len(ref) > 5
        msgs.append(f"{mode}: {detail} ({len(ref)})")
    return ok_all, "; ".join(msgs)
