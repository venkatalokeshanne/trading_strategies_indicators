"""Independent check — QQE Trend Strategy (KM4wOmrL): daily bars, one position (entries reverse), 1 unit, trade list only. qqeCalc, re-stated with plain loops: rsi = RSI14, qqeL = EMA5(rsi), dar = EMA9(EMA9(|qqeL - qqeL[1]|)) x factor; long band lb = max(lb[1], qqeL - dar) while
qqeL > lb[1] else qqeL - dar (nz seeds with the new value), short band sb = min(sb[1], qqeL + dar) while qqeL < sb[1] else qqeL + dar; trend = 1 if qqeL crosses over sb[1], else -1 if it crosses under lb[1] (that cross-under is only evaluated on bars where the
cross-over is false, so its remembered previous arguments skip bars), else the previous trend (1 initially). The slow-band trend (4.236) turning from -1 to 1 with qqeL > 50 buys, from 1 to -1 with qqeL < 50 sells; variants: Fast band (2.618) and
Long Only (never exits, so zero closed trades on both sides) and the 50-line filter off. Margin and slippage off on the pinelib side."""
import numpy as np

from indep import bars, compare, np_ema, np_rsi, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "KM4wOmrL"


def qqe(c, factor):
    n = len(c)
    q = np_ema(np_rsi(c, 14), 5)
    d1 = np.abs(q - np.r_[np.nan, q[:-1]])
    dar = np_ema(np_ema(d1, 9), 9) * factor
    lb = np.full(n, np.nan)
    sb = np.full(n, np.nan)
    tr = np.ones(n, int)
    cu_prev = None            # previous evaluated (a, b) of the cross-under call
    co_prev = None            # previous evaluated (a, b) of the cross-over call
    for i in range(n):
        lbp = lb[i - 1] if i else np.nan
        sbp = sb[i - 1] if i else np.nan
        nzl = lbp if not np.isnan(lbp) else q[i] - dar[i]
        nzs = sbp if not np.isnan(sbp) else q[i] + dar[i]
        with np.errstate(invalid="ignore"):
            lb[i] = max(nzl, q[i] - dar[i]) if q[i] > nzl else q[i] - dar[i]
            sb[i] = min(nzs, q[i] + dar[i]) if q[i] < nzs else q[i] + dar[i]
            a, b = q[i], sbp
            co = co_prev is not None and a > b and co_prev[0] <= co_prev[1]
            co_prev = (a, b)
            if co:
                t = 1
            else:
                a2, b2 = q[i], lbp
                cu = cu_prev is not None and a2 < b2 and cu_prev[0] >= cu_prev[1]
                cu_prev = (a2, b2)
                t = -1 if cu else (tr[i - 1] if i else 1)
        tr[i] = t
    return q, tr


def one(df, mode, direction, f50=True):
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    q, fast = qqe(c, 2.618)
    _, slow = qqe(c, 4.236)
    active = fast if mode == "Fast" else slow
    prev = np.r_[0, active[:-1]]
    with np.errstate(invalid="ignore"):
        buy = (active == 1) & (prev == -1) & ((q > 50) if f50 else True)
        sell = (active == -1) & (prev == 1) & ((q < 50) if f50 else True)

    def orders(i, pos):
        out = []
        if buy[i] and direction != "Short Only":
            out.append(("entry", 1))
        if sell[i] and direction != "Long Only":
            out.append(("entry", -1))
        return out

    ref = simulate(o, h, l, c, orders)
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, d = compare(run_conversion(TV_ID, df, symbol=sym, tf="D", params={"Signal Band": mode, "Trade Direction": direction, "50-Line Direction Filter": f50},
                                   strategy_overrides={"margin_long": 0, "margin_short": 0, "slippage": 0}), ref)
    return ok and (len(ref) > 5 or direction != "Both"), f"{mode}/{direction}/50f={f50}: {d} (got {len(ref)})"


def check():
    df = bars(8000, seed=964)
    msgs, allok = [], True
    for mode, dr, f in (("Slow", "Both", True), ("Fast", "Both", True), ("Slow", "Both", False), ("Slow", "Long Only", True)):
        ok, m = one(df, mode, dr, f)
        allok &= ok
        msgs.append(m)
    return allok, " | ".join(msgs)
