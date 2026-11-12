"""Independent check — EMA and SR (jV0P24pA / zYdZsbae are the same script): hourly bars (24h synthetic, New York calendar days), process_orders_on_close. Entry: close above all four EMAs (20/50/100/200) and above the previous bar's
high (CE, long) or below all and below the previous low (PE, short), once per New York day per side, with nothing open, if risk (close - previous low / previous high - close) > 0. The original clears the stop / target on the entry bar
(the trade is not yet counted as open) and the exit block then never runs, so the first trade is never closed: the reference therefore expects NO closed trades and exactly one open trade whose direction, entry bar and entry price
are rebuilt here from the rules (margin off on the pinelib side)."""
import numpy as np
import pandas as pd

from indep import bars, np_ema, run_conversion
from pinelib import SymbolInfo

TV_ID = "jV0P24pA"


def check():
    df = bars(6000, seed=207, freq="1h")
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    e = [np_ema(c, k) for k in (20, 50, 100, 200)]
    h1, l1 = np.r_[np.nan, h[:-1]], np.r_[np.nan, l[:-1]]
    with np.errstate(invalid="ignore"):
        ce = (c > e[0]) & (c > e[1]) & (c > e[2]) & (c > e[3]) & (c > h1) & ((c - l1) > 0)
        pe = (c < e[0]) & (c < e[1]) & (c < e[2]) & (c < e[3]) & (c < l1) & ((h1 - c) > 0)
    expect = None
    for i in range(n):
        if ce[i]:
            expect = (1, i, c[i])
            break
        if pe[i]:
            expect = (-1, i, c[i])
            break
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    res = run_conversion(TV_ID, df, symbol=sym, tf="60", strategy_overrides={"margin_long": 0, "margin_short": 0, "slippage": 0, "default_qty_value": 5})
    closed = list(res.broker.closed)
    opened = list(res.broker.open)
    if expect is None:
        return False, "no entry signal on the synthetic series"
    if closed or len(opened) != 1:
        return False, f"expected 0 closed and 1 open trade, got {len(closed)} closed / {len(opened)} open"
    t = opened[0]
    d = 1 if t.price is not None and t.entry_id == "Buy CE" else -1
    ok = d == expect[0] and t.bar == expect[1] and abs(t.price - expect[2]) <= 1e-9 * max(1, abs(expect[2]))
    return ok, f"open trade (dir {d}, bar {t.bar}, price {t.price:.4f}) vs expected {expect}; closed trades: {len(closed)}"
