"""Independent check — DCA Grid 15 Orders (iOxqnyIv): 5-min bars. Written as a plain loop (indep.simulate has no pyramiding): market entries fill at
the next open; one take-profit limit at 1.8 % over the quantity-weighted average price, issued at each close while long and working on the NEXT
bar (so a grid entry that fills at that open is also taken at the old level). The grid adds (low <= last entry * (1 - 1.1 %)) only while orderCount
is armed; the script re-arms orderCount = 1 on flat bars and then resets it to 0 / lastEntry = na on the bar after the position closes."""
import numpy as np

from indep import bars, compare, run_conversion
from pinelib import SymbolInfo

TV_ID = "iOxqnyIv"


def check():
    df = bars(8000, seed=120, freq="5min")
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    open_e, trades, pending = [], [], []                      # open_e: (qty, price, bar); pending: qty of entries to fill at the next open
    tp_level, order_count, last_entry, prev_pos = np.nan, 0, np.nan, 0.0
    for i in range(n):
        for q in pending:
            open_e.append((q, o[i], i))
        pending = []
        if open_e and not np.isnan(tp_level):
            px = o[i] if o[i] >= tp_level else (tp_level if h[i] >= tp_level else None)
            if px is not None:
                trades += [(1, eb, ep, i, px) for _, ep, eb in open_e]
                open_e = []
        pos = sum(q for q, _, _ in open_e)
        if pos == 0:
            pending = [100.0 / c[i]]                          # Long_1 (replaces a pending Long_1)
            order_count, last_entry = 1, c[i]
        if pos > 0 and order_count < 15:
            nb = last_entry * (1 - 1.1 / 100) if not np.isnan(last_entry) else np.nan
            if l[i] <= nb:
                pending.append(100.0 * 1.2 ** order_count / c[i])
                last_entry = nb
                order_count += 1
        avg = sum(q * p for q, p, _ in open_e) / pos if pos > 0 else np.nan
        tp_level = avg * (1 + 1.8 / 100) if pos > 0 else np.nan
        if pos == 0 and prev_pos > 0:
            order_count, last_entry = 0, np.nan
        prev_pos = pos
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-12)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="5"), trades)
    return ok and len(trades) > 10, f"{detail} (need >10 trades, got {len(trades)})"
