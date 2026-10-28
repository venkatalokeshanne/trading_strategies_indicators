"""Independent check — 4-EMA Trend & Pullback (c4pAKqEX): hourly bars. EMA7 over EMA21 with EMA50 > EMA200 buys; EMA7 under EMA21 with EMA50 < EMA200 sells short (reversing). A long closes at the next open on EMA7/21 cross under or close < EMA50;
a short on a cross over or close > EMA50 (close calls only when that side is open at the bar close). Queued in source order: entry Long, close Long, entry Short, close Short. Margin off on the pinelib side."""
import numpy as np

from indep import bars, compare, np_cross_over, np_cross_under, np_ema, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "c4pAKqEX"


def check():
    df = bars(30000, seed=309, freq="1h")
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    e7, e21, e50, e200 = (np_ema(c, k) for k in (7, 21, 50, 200))
    up, dn = np_cross_over(e7, e21), np_cross_under(e7, e21)
    with np.errstate(invalid="ignore"):
        lx, sx = dn | (c < e50), up | (c > e50)
        lt, st = (e50 > e200) & up, (e50 < e200) & dn

    def orders(i, pos):
        out = []
        if lt[i]:
            out.append(("entry", 1))
        if pos > 0 and lx[i]:
            out.append(("close", 1))
        if st[i]:
            out.append(("entry", -1))
        if pos < 0 and sx[i]:
            out.append(("close", -1))
        return out

    ref = simulate(o, h, l, c, orders)
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="60", strategy_overrides={"margin_long": 0, "margin_short": 0}), ref)
    return ok and len(ref) > 10, f"{detail} (need >10 trades, got {len(ref)})"
