"""Independent check — LuxAlgo SMC Pro Ultimate (mEHJ2lCm), daily bars. Pivot highs / lows (internal 9, swing 50) from a window
max / min, the crossover of the close over the last pivot, the discount / premium half of the 100-bar range and the fair-value
gap on this or the previous bar are rebuilt in numpy; the trade handling (stop 3 ATR(9) trailing the bar low / high, 50 % limit
exit at 1.5 R armed once the bar reaches it, stop moved to the average price) is replayed against the quantity-aware reference
broker. Variants change the structure mode, direction and which filters are active."""
import numpy as np

from indep import bars, compare_q, np_atr, run_conversion, simulate_brackets
from pinelib import SymbolInfo

TV_ID = "mEHJ2lCm"
QTY = 10.0


def roll(x, n, fn):
    out = np.full(len(x), np.nan)
    for i in range(n - 1, len(x)):
        out[i] = fn(x[i - n + 1:i + 1])
    return out


def last_pivot(x, lb, hi):
    n = len(x)
    win = roll(x, 2 * lb + 1, np.max if hi else np.min)
    out = np.full(n, np.nan)
    cur = np.nan
    for i in range(n):
        if i >= lb and not np.isnan(win[i]) and x[i - lb] == win[i]:
            cur = x[i - lb]
        out[i] = cur
    return out


def cross(a, b, up):
    pa, pb = np.r_[np.nan, a[:-1]], np.r_[np.nan, b[:-1]]
    with np.errstate(invalid="ignore"):
        return (a > b) & (pa <= pb) if up else (a < b) & (pa >= pb)


def reference(df, mode="All", direction="Both", fvg=True, pd=True):
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    atr = np_atr(h, l, c, 9)
    eq = (roll(h, 100, np.max) + roll(l, 100, np.min)) / 2
    h2, l2, c1 = np.r_[[np.nan] * 2, h[:-2]], np.r_[[np.nan] * 2, l[:-2]], np.r_[np.nan, c[:-1]]
    bfvg = (l > h2) & (c1 > h2)
    sfvg = (h < l2) & (c1 < l2)
    bfvg1, sfvg1 = np.r_[False, bfvg[:-1]], np.r_[False, sfvg[:-1]]
    ish, isl = last_pivot(h, 9, True), last_pivot(l, 9, False)
    ssh, ssl = last_pivot(h, 50, True), last_pivot(l, 50, False)
    xoi, xui = cross(c, ish, True), cross(c, isl, False)
    xos, xus = cross(c, ssh, True), cross(c, ssl, False)
    mss_l = {"Internal": xoi, "Swing": xos, "All": xoi | xos}[mode]
    mss_s = {"Internal": xui, "Swing": xus, "All": xui | xus}[mode]
    btrig = mss_l & ((c < eq) if pd else True) & ((bfvg1 | bfvg) if fvg else True)
    strig = mss_s & ((c > eq) if pd else True) & ((sfvg1 | sfvg) if fvg else True)
    S = dict(sl=np.nan, tp=np.nan, hit=False)

    def orders(i, info):
        pos = info["pos"]
        out = []
        if btrig[i] and pos == 0 and direction in ("Both", "Long Only"):
            S["sl"] = l[i] - atr[i] * 3.0
            S["tp"] = c[i] + (c[i] - S["sl"]) * 1.5
            S["hit"] = False
            out.append(("entry", "Long", 1, QTY))
        if strig[i] and pos == 0 and direction in ("Both", "Short Only"):
            S["sl"] = h[i] + atr[i] * 3.0
            S["tp"] = c[i] - (S["sl"] - c[i]) * 1.5
            S["hit"] = False
            out.append(("entry", "Short", -1, QTY))
        if pos > 0:
            if not S["hit"] and h[i] >= S["tp"]:
                out.append(("exit", "TP1_L", "Long", 50.0, None, S["tp"]))
                S["hit"], S["sl"] = True, info["avg"]
            trail = l[i] - atr[i] * 3.0
            if trail > S["sl"]:
                S["sl"] = trail
            out.append(("exit", "Exit_L", "Long", None, S["sl"], None))
        if pos < 0:
            if not S["hit"] and l[i] <= S["tp"]:
                out.append(("exit", "TP1_S", "Short", 50.0, None, S["tp"]))
                S["hit"], S["sl"] = True, info["avg"]
            trail = h[i] + atr[i] * 3.0
            if trail < S["sl"]:
                S["sl"] = trail
            out.append(("exit", "Exit_S", "Short", None, S["sl"], None))
        return out

    return simulate_brackets(o, h, l, c, orders, pyramiding=1, qty_step=1e-9)


def check():
    df = bars(12000, seed=4, freq="D")
    sym = SymbolInfo.make("NASDAQ:XYZ", "stock", qty_step=1e-9)
    ov = {"margin_long": 0, "margin_short": 0, "commission_value": 0, "slippage": 0, "default_qty_type": "fixed", "default_qty_value": QTY}
    msgs, ok_all = [], True
    cases = (({}, {}),
             ({"Structure Mode": "Internal", "Require FVG Presence": False}, dict(mode="Internal", fvg=False)),
             ({"Structure Mode": "Swing", "Only Buy in Discount / Sell in Premium": False, "Trade Direction": "Long Only"},
              dict(mode="Swing", pd=False, direction="Long Only")))
    for params, kw in cases:
        ref = reference(df, **kw)
        ok, d = compare_q(run_conversion(TV_ID, df, symbol=sym, tf="D", params=params, strategy_overrides=ov), ref)
        ok_all = ok_all and ok and len(ref) > 12
        msgs.append(f"{d} (got {len(ref)})")
    return ok_all, " | ".join(msgs)
