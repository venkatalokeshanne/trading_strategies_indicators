"""Independent check — SIS Supertrend Ichimoku (GP3FEy2z): daily bars. Plain-Python loop of the Pine function avg(src, length, mult): ATR band around hl2 (upper sticks to min(up, upper[1]) while the previous close is under the
previous upper, lower likewise), os state from the close vs the bands, spt = lower if os == 1 else upper, running max/min of the close after a cross of the close through spt, result = (max + min) / 2 (math.max/min give
na if either side is na). Tenkan (9, x2) crossing over Kijun (26, x4) enters long / closes the short, under enters short / closes the long. Run for the three "Handelsmodus" settings."""
import numpy as np

from indep import bars, compare, np_atr, np_cross_over, np_cross_under, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "GP3FEy2z"


def nmax(a, b):
    return np.nan if (np.isnan(a) or np.isnan(b)) else max(a, b)


def nmin(a, b):
    return np.nan if (np.isnan(a) or np.isnan(b)) else min(a, b)


def line(h, l, c, length, mult):
    n = len(c)
    atr = np_atr(h, l, c, length) * mult
    hl2 = (h + l) / 2
    out = np.full(n, np.nan)
    upper = lower = os_ = mx = mn = spt = np.nan
    for i in range(n):
        src, prev = c[i], (c[i - 1] if i else np.nan)
        up, dn = hl2[i] + atr[i], hl2[i] - atr[i]
        pu, pl, po, pm, pn, ps = upper, lower, os_, mx, mn, spt
        upper = nmin(up, pu) if prev < pu else up
        lower = nmax(dn, pl) if prev > pl else dn
        os_ = 1 if src > upper else (0 if src < lower else po)
        spt = lower if os_ == 1 else upper
        crossed = (src > spt and prev <= ps) or (src < spt and prev >= ps)
        mx = nmax(src, pm) if (crossed or os_ == 1) else spt
        mn = nmin(src, pn) if (crossed or os_ == 0) else spt
        out[i] = np.nan if (np.isnan(mx) or np.isnan(mn)) else (mx + mn) / 2
    return out


def check():
    df = bars(5000, seed=259)
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    with np.errstate(invalid="ignore"):
        tk, kj = line(h, l, c, 9, 2.0), line(h, l, c, 26, 4.0)
    up, dn = np_cross_over(tk, kj), np_cross_under(tk, kj)
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    msgs, ok_all = [], True
    for mode in ("Beide", "Long", "Short"):
        def orders(i, pos, mode=mode):
            out = []
            if mode in ("Long", "Beide"):
                if up[i]:
                    out.append(("entry", 1))
                if dn[i]:
                    out.append(("close", 1))
            if mode in ("Short", "Beide"):
                if dn[i]:
                    out.append(("entry", -1))
                if up[i]:
                    out.append(("close", -1))
            return out

        ref = simulate(o, h, l, c, orders)
        ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="D", params={"Handelsmodus": mode},
                                            strategy_overrides={"margin_long": 0, "margin_short": 0}), ref)
        ok_all = ok_all and ok and len(ref) > 5
        msgs.append(f"{mode}: {detail} ({len(ref)})")
    return ok_all, "; ".join(msgs)
