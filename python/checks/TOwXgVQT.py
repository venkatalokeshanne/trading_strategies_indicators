"""Independent check — Quanloki QQE (TOwXgVQT): daily bars, slippage 0, orders at the signal close (process_orders_on_close), pyramiding 0. RsiMa = EMA5(RSI14); dar = EMA27(EMA27(|RsiMa[1] - RsiMa|)) * 4.238; long / short bands follow QQE; trend flips to 1 when RsiMa crosses the previous short band, to -1 when the previous long band
crosses RsiMa (ta.cross = either direction), otherwise keeps (initial 1); trend line = long band in an up trend, else short band. A signal is the trend line crossing RsiMa (long: line below RsiMa now and at-or-above before). Each signal closes the other side and enters at the close."""
import numpy as np

from indep import bars, compare, np_ema, np_rsi, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "TOwXgVQT"


def cross(a, b, pa, pb):
    return bool((a > b and pa <= pb) or (a < b and pa >= pb))


def check():
    df = bars(9000, seed=2)
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    ri = np_ema(np_rsi(c, 14), 5)
    atr_r = np.abs(np.r_[np.nan, ri[:-1]] - ri)
    dar = np_ema(np_ema(atr_r, 27), 27) * 4.238
    lb = np.full(n, np.nan)
    sb = np.full(n, np.nan)
    tl = np.full(n, np.nan)
    trend = 1
    with np.errstate(invalid="ignore"):
        for i in range(n):
            lb1 = 0.0 if i == 0 or np.isnan(lb[i - 1]) else lb[i - 1]
            sb1 = 0.0 if i == 0 or np.isnan(sb[i - 1]) else sb[i - 1]
            r1 = ri[i - 1] if i else np.nan
            nl, ns = ri[i] - dar[i], ri[i] + dar[i]
            lb[i] = max(lb1, nl) if (r1 > lb1 and ri[i] > lb1) else nl
            sb[i] = min(sb1, ns) if (r1 < sb1 and ri[i] < sb1) else ns
            plb = lb[i - 1] if i else np.nan
            psb = sb[i - 1] if i else np.nan
            c1 = i > 0 and cross(plb, ri[i], plb if i < 2 else lb[i - 2], r1)
            c2 = i > 0 and cross(ri[i], psb, r1, psb if i < 2 else sb[i - 2])
            trend = 1 if c2 else -1 if c1 else trend
            tl[i] = lb[i] if trend == 1 else sb[i]
    tl1, ri1 = np.r_[np.nan, tl[:-1]], np.r_[np.nan, ri[:-1]]
    with np.errstate(invalid="ignore"):
        ls = (tl < ri) & (tl1 >= ri1)
        ss = (tl > ri) & (tl1 <= ri1)

    def orders(i, pos):
        out = []
        if ls[i]:
            out += [("close", -1), ("entry", 1)]
        if ss[i]:
            out += [("close", 1), ("entry", -1)]
        return out

    ref = simulate(o, h, l, c, orders, on_close=True)
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="D", strategy_overrides={"margin_long": 0, "margin_short": 0, "slippage": 0}), ref)
    return ok and len(ref) > 10, f"{detail} (need >10 trades, got {len(ref)})"
