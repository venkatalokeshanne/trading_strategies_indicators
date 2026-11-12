"""Independent check — Signal Engine Quantum Edge (n9ty3SVh): 4-hour bars, always-in-the-market reversing entries at the next open, qty 1. SuperTrend on hl2 with ATR(15) x 9.1 (RMA ATR or SMA of the true range): lower band up = hl2 - M x ATR, ratcheted up (max with the previous final up) while the previous close was above the previous up; upper band dn mirrored. Trend starts at 1, flips to 1 when the close
is above the previous dn while it was -1, to -1 when below the previous up while it was +1. A flip to +1 (-1) inside the window (from 2018-09-01 New York) is a long (short). Variants: Wilder ATR and SMA-of-TR ATR. Margin off on the pinelib side."""
import numpy as np
import pandas as pd

from indep import bars, compare, np_atr, np_sma, np_tr, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "n9ty3SVh"


def one(df, params, wilder, mult):
    o, h, l, c, t = (df[k].to_numpy() for k in ("open", "high", "low", "close", "time"))
    n = len(c)
    atr = np_atr(h, l, c, 15) if wilder else np_sma(np_tr(h, l, c, True), 15)
    s_ = (h + l) / 2
    up, dn, tr = np.full(n, np.nan), np.full(n, np.nan), np.zeros(n, int)
    for i in range(n):
        u = s_[i] - mult * atr[i]
        u1 = up[i - 1] if i and not np.isnan(up[i - 1]) else u
        if i and c[i - 1] > u1:
            u = max(u, u1)
        d = s_[i] + mult * atr[i]
        d1 = dn[i - 1] if i and not np.isnan(dn[i - 1]) else d
        if i and c[i - 1] < d1:
            d = min(d, d1)
        up[i], dn[i] = u, d
        tp = tr[i - 1] if i else 1
        if tp == -1 and c[i] > d1:
            tp = 1
        elif tp == 1 and c[i] < u1:
            tp = -1
        tr[i] = tp
    prev = np.r_[0, tr[:-1]]
    buy, sell = (tr == 1) & (prev == -1), (tr == -1) & (prev == 1)
    t0 = pd.Timestamp(2018, 9, 1, tz="America/New_York").value // 10**6
    win = t >= t0

    def orders(i, pos):
        out = []
        if buy[i] and win[i]:
            out.append(("entry", 1))
        if sell[i] and win[i]:
            out.append(("entry", -1))
        return out

    with np.errstate(invalid="ignore"):
        ref = simulate(o, h, l, c, orders)
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, d_ = compare(run_conversion(TV_ID, df, symbol=sym, tf="240", params=params, strategy_overrides={"margin_long": 0, "margin_short": 0}), ref)
    return ok and len(ref) > 10, f"{d_} (got {len(ref)})"


def check():
    df = bars(30000, seed=821, freq="4h")
    msgs, allok = [], True
    # the default 9.1-ATR band almost never flips on these bars, so both variants set a 1.5 multiplier
    for params, wilder in (({"ATR Multiplier": 1.5}, True), ({"ATR Multiplier": 1.5, "Change ATR Calculation Method": False}, False)):
        ok, m = one(df, params, wilder, 1.5)
        allok &= ok
        msgs.append(m)
    return allok, " | ".join(msgs)
