"""Independent check — 4-EMA & RSI Trend Pullback (mHFkCOkr): daily bars, EMA lengths 7/21/50/200 scaled to 7/21/40/100 here (passed to both sides). EMA50 > EMA200 + EMA7 crossing over EMA21 + RSI14 in (50, 70) goes long; EMA50 < EMA200 + cross under + RSI in (30, 50) goes short.
A long closes on a cross under or close < EMA50 (only if long), a short on a cross over or close > EMA50; closes and entries at the next open (a bar can exit one side and enter the other)."""
import numpy as np

from indep import bars, compare, np_cross_over, np_cross_under, np_ema, np_rsi, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "mHFkCOkr"
L50, L200 = 40, 100


def check():
    df = bars(9000, seed=23)
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    e7, e21, e50, e200 = np_ema(c, 7), np_ema(c, 21), np_ema(c, L50), np_ema(c, L200)
    rsi = np_rsi(c, 14)
    up, dn = np_cross_over(e7, e21), np_cross_under(e7, e21)
    with np.errstate(invalid="ignore"):
        lt = (e50 > e200) & up & (rsi > 50) & (rsi < 70)
        st_ = (e50 < e200) & dn & (rsi < 50) & (rsi > 30)
        lx = dn | (c < e50)
        sx = up | (c > e50)

    def orders(i, pos):
        out = []
        if lt[i]:
            out.append(("entry", 1))
        if pos > 0 and lx[i]:
            out.append(("close", 1))
        if st_[i]:
            out.append(("entry", -1))
        if pos < 0 and sx[i]:
            out.append(("close", -1))
        return out

    ref = simulate(o, h, l, c, orders)
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="D", params={"EMA 50 (Trend & Dynamic Stop)": L50, "EMA 200 (Macro Trend)": L200},
                                        strategy_overrides={"margin_long": 0, "margin_short": 0}), ref)
    return ok and len(ref) > 10, f"{detail} (need >10 trades, got {len(ref)})"
