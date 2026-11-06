"""Independent check — Volatility Gaussian Bands (uIblGAUC): daily-style bars around 15 000, market orders at the next open, 100 % equity, one position (a reversal closes the opposite side first). Medium-cycle bands: RMA(close, 15) taken 7 bars back (the close where it is not yet available) plus / minus 3 x ATR(15); long entry line = upper + 10, short entry line = lower - 10. A close crossing above (below) the entry line while not long (not short) enters, reversing the opposite position. SuperTrend 1 (hl2 +/- 2 x ATR10, with the source's own recursion) shifted by +/- 10 x 1.0 points: an open long leaves when the close crosses under st1 - 10, an open short when the close crosses over st1 + 10. Optional hard stop = highest high since entry - points (lowest low + points for shorts), issued once in the position so it works from the next bar. Margin off on the pinelib side.
Variants: defaults; hard stop 150 points and 2.5 renko bricks of 20 points; a smaller entry offset."""
import numpy as np

from indep import bars, compare, np_atr, np_rma, run_conversion, simulate

TV_ID = "uIblGAUC"


def one(df, params, off_hi, off_lo, brick, nbr, hard):
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    ma = np_rma(c, 15)
    atr15 = np_atr(h, l, c, 15)
    back = np.r_[np.full(7, np.nan), ma[:-7]]
    base = np.where(np.isnan(back), c, back)
    mct, mcb = base + 3 * atr15, base - 3 * atr15
    lel, sel = mct + off_hi, mcb - off_lo
    atr10 = np_atr(h, l, c, 10)
    hl2 = (h + l) / 2
    upB, dnB = hl2 - 2 * atr10, hl2 + 2 * atr10
    upT, dnT, d1 = np.full(n, np.nan), np.full(n, np.nan), np.ones(n)
    pu = pdn = np.nan
    pdir = 1
    for i in range(n):
        u, dn = pu, pdn
        if np.isnan(u) and not np.isnan(atr10[i]):
            u = upB[i]
        if np.isnan(dn) and not np.isnan(atr10[i]):
            dn = dnB[i]
        ready = not np.isnan(atr10[i]) and not np.isnan(u) and not np.isnan(dn)
        upp = (pu if not np.isnan(pu) else u) if ready else upB[i]
        dnp = (pdn if not np.isnan(pdn) else dn) if ready else dnB[i]
        pc = c[i - 1] if i > 0 else np.nan
        bu = max(upB[i], upp) if pc > upp else upB[i]
        bd = min(dnB[i], dnp) if pc < dnp else dnB[i]
        if ready:
            u, dn = bu, bd
        if ready and c[i] > (pdn if not np.isnan(pdn) else dnB[i]):
            dr = 1
        elif ready and c[i] < (pu if not np.isnan(pu) else upB[i]):
            dr = -1
        else:
            dr = pdir
        upT[i], dnT[i], d1[i] = u, dn, dr
        pu, pdn, pdir = u, dn, dr
    st1 = np.where(d1 == 1, upT, dnT)
    sll = brick * nbr
    lsl, ssl = st1 - sll, st1 + sll
    pc_ = np.r_[np.nan, c[:-1]]
    with np.errstate(invalid="ignore"):
        xl = (c < lel) * 0
        cu = (c > lel) & (pc_ <= np.r_[np.nan, lel[:-1]])
        cd = (c < sel) & (pc_ >= np.r_[np.nan, sel[:-1]])
        exb = (c < lsl) & (pc_ >= np.r_[np.nan, lsl[:-1]])
        exs = (c > ssl) & (pc_ <= np.r_[np.nan, ssl[:-1]])
    S = dict(hi=np.nan, lo=np.nan, pp=0)
    ST = {}

    def orders(i, pos):
        out = []
        pp = S["pp"]
        S["pp"] = pos
        if cu[i] and pos <= 0:
            out += [("close", -1), ("entry", 1)]
        if cd[i] and pos >= 0:
            out += [("close", 1), ("entry", -1)]
        if pos > 0 and exb[i]:
            out.append(("close", 1))
        if pos < 0 and exs[i]:
            out.append(("close", -1))
        if pos > 0 and pp <= 0:
            S["hi"] = h[i]
        if pos < 0 and pp >= 0:
            S["lo"] = l[i]
        if pos > 0:
            S["hi"] = h[i] if np.isnan(S["hi"]) else max(S["hi"], h[i])
            if hard > 0:
                ST[i] = (1, S["hi"] - hard)
        if pos < 0:
            S["lo"] = l[i] if np.isnan(S["lo"]) else min(S["lo"], l[i])
            if hard > 0:
                ST[i] = (-1, S["lo"] + hard)
        return out

    def stop(i, pos, ep, eb):
        e = ST.get(i - 1)
        return e[1] if e is not None and e[0] == pos else None

    with np.errstate(invalid="ignore"):
        ref = simulate(o, h, l, c, orders, stop=stop)
    ok, d = compare(run_conversion(TV_ID, df, params=params, strategy_overrides={"margin_long": 0, "margin_short": 0}), ref)
    return ok and len(ref) > 5, f"{d} (got {len(ref)})"


def check():
    df = bars(6000, seed=88)
    for k in ("open", "high", "low", "close"):
        df[k] = 15000 * (df[k] / 100) ** 0.45
    msgs, allok = [], True
    cases = (({}, (10.0, 10.0, 10.0, 1.0, 0.0)),
             ({"Hard Stoploss (points from entry)": 150.0, "Renko Box Size (points)": 20.0, "SL in Renko bricks (can be decimal/negative)": 2.5}, (10.0, 10.0, 20.0, 2.5, 150.0)),
             ({"Entry Offset from mcb (pts)": 2.0, "Entry Offset from mct (pts)": 3.0}, (2.0, 3.0, 10.0, 1.0, 0.0)))
    for params, args in cases:
        ok, m = one(df, params, *args)
        allok &= ok
        msgs.append(m)
    return allok, " | ".join(msgs)
