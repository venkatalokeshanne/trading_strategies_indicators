"""Independent check — Good luck! (rncCBFXC): daily bars, pyramiding 2 (indep.simulate_pyr), 1 unit per lot (so the average price is the plain mean of the lots), market orders at the next open. Long entry: close above EMA9 with the previous close at/below the previous EMA9 (and, with the filter, EMA9 > EMA55);
short mirrored. A long signal first closes shorts then enters long (the entry stacks up to 2 lots when already long); close below EMA55 closes longs, above closes shorts. At EVERY script run both ATR stops are issued: LONG stop = avg - 1.5 ATR, SHORT stop = avg + 1.5 ATR, with avg the script-time average of
whatever position exists (na when flat) - so the stop that works on bar i for direction d is the one computed at bar i-1 even if bar i-1's position was the other side. Variants: default; no trend filter. Margin / slippage off, fixed 1-unit size on the pinelib side."""
import numpy as np

from indep import bars, compare, np_atr, np_ema, run_conversion, simulate_pyr
from pinelib import SymbolInfo

TV_ID = "rncCBFXC"


def one(df, params, use_tf):
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    f, s = np_ema(c, 9), np_ema(c, 55)
    atr = np_atr(h, l, c, 14)
    pf, pc = np.r_[np.nan, f[:-1]], np.r_[np.nan, c[:-1]]
    with np.errstate(invalid="ignore"):
        le = (c > f) & (pc <= pf) & ((f > s) if use_tf else True)
        se = (c < f) & (pc >= pf) & ((f < s) if use_tf else True)
        lx, sx = c < s, c > s
    S = dict(avg=np.nan, avg_i=-1)
    sl_l, sl_s = np.full(n, np.nan), np.full(n, np.nan)

    def stop(i, d, trades):
        S["avg"], S["avg_i"] = float(np.mean([t[2] for t in trades])), i
        if i == 0:
            return None
        v = sl_l[i - 1] if d > 0 else sl_s[i - 1]
        return None if np.isnan(v) else v

    def orders(i, pos):
        out = []
        if le[i]:
            out += [("close", -1), ("entry", 1)]
        if se[i]:
            out += [("close", 1), ("entry", -1)]
        if pos > 0 and lx[i]:
            out.append(("close", 1))
        if pos < 0 and sx[i]:
            out.append(("close", -1))
        if S["avg_i"] == i and pos != 0:
            sl_l[i] = S["avg"] - atr[i] * 1.5
            sl_s[i] = S["avg"] + atr[i] * 1.5
        return out

    with np.errstate(invalid="ignore"):
        ref = simulate_pyr(o, h, l, c, orders, pyramiding=2, stop=stop)
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, d = compare(run_conversion(TV_ID, df, symbol=sym, tf="D", params=params,
                                   strategy_overrides={"margin_long": 0, "margin_short": 0, "slippage": 0, "default_qty_type": "fixed", "default_qty_value": 1}), ref)
    return ok and len(ref) > 10, f"{d} (got {len(ref)})"


def check():
    df = bars(8000, seed=691)
    msgs, allok = [], True
    for params, tf in (({}, True), ({"Use Trend Filter": False}, False)):
        ok, m = one(df, params, tf)
        allok &= ok
        msgs.append(m)
    return allok, " | ".join(msgs)
