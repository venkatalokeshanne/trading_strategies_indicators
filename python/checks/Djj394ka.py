"""Independent check — S/R Breakout LONG ONLY (Djj394ka): daily bars, process_orders_on_close, up to 20 lots each with its own limit (1 unit per lot). Pivot high / low with 15 bars each side (strict on the left, non-strict on the
right), latest confirmed values are resistance / support; channel = (R - S) / S x 100 <= 2 (loosened to 15 on both sides so trades occur); a close crossing over R, close above the previous bar's SMA200 and further from it than 1%,
fewer than 20 open lots and >= 10 bars since the last entry opens a lot at the close. A lot's limit (entry x 1.01) is issued from the next bar's script run (opentrades does not yet hold the lot on its own entry bar), so it can
fill from the bar after that; a gap above the limit fills at the open. Lots close oldest first within a bar. Margin and slippage off on the pinelib side."""
import numpy as np
import pandas as pd

from indep import bars, compare, np_cross_over, np_sma, run_conversion
from pinelib import SymbolInfo

TV_ID = "Djj394ka"


def pivots(x, L, R, high):
    n = len(x)
    out = np.full(n, np.nan)
    for i in range(L + R, n):
        p = i - R
        w = x[p - L:p + R + 1]
        if high:
            if x[p] == w.max() and all(x[p] > x[p - L:p]):
                out[i] = x[p]
        else:
            if x[p] == w.min() and all(x[p] < x[p - L:p]):
                out[i] = x[p]
    return out


def check():
    df = bars(8000, seed=419)
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    ph, pl = pivots(h, 15, 15, True), pivots(l, 15, 15, False)
    res = pd.Series(ph).ffill().to_numpy()
    sup = pd.Series(pl).ffill().to_numpy()
    with np.errstate(invalid="ignore", divide="ignore"):
        rng = (res - sup) / sup * 100
        sma = np.r_[np.nan, np_sma(c, 200)[:-1]]
        xo = np_cross_over(c, res)
        okd = (np.abs(c - sma) / sma * 100) > 1.0
        sig = xo & (rng <= 15.0) & (c > sma) & okd
    lots: list = []                     # [entry_bar, entry_price, active_from_bar]
    trades: list = []
    last = -10 ** 9
    for i in range(n):
        for lot in list(lots):          # limits issued at an earlier script run work on this bar
            if i >= lot[2]:
                tp = lot[1] * 1.01
                if o[i] >= tp:
                    trades.append((1, lot[0], lot[1], i, o[i]))
                    lots.remove(lot)
                elif h[i] >= tp:
                    trades.append((1, lot[0], lot[1], i, tp))
                    lots.remove(lot)
        if sig[i] and len(lots) < 20 and (i - last) >= 10:
            for lot in lots:            # lots open at this script run get their limit now (work from i + 1)
                lot[2] = min(lot[2], i + 1)
            lots.append([i, c[i], i + 2])
            last = i
        else:
            for lot in lots:
                lot[2] = min(lot[2], i + 1)
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="D", params={"Макс. ширина канала (%)": 15.0},
                                        strategy_overrides={"margin_long": 0, "margin_short": 0, "slippage": 0, "default_qty_value": 1}), trades)
    return ok and len(trades) > 5, f"{detail} (need >5 trades, got {len(trades)})"
