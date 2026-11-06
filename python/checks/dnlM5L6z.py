"""Independent check — Swing Trend Strategy PRO (dnlM5L6z): daily bars, process_orders_on_close (fills at the signal bar's close), long only, 100 % of equity. Entry: close > EMA200 and EMA50 > EMA200, ADX(14) > 20, close > EMA20 and
RSI14 crossing over 55; v6 short-circuit: the cross only runs on bars where the first three tests pass, against the last bar it ran on. While a position is open at the close, an 8 % stop around the entry price is issued, working
from the next bar. Close < EMA50 closes at that close. Margin off on the pinelib side."""
import numpy as np

from indep import bars, compare, np_adx, np_ema, np_rsi, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "dnlM5L6z"


def check():
    df = bars(6000, seed=229)
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    ef, em, el, rsi, adx = np_ema(c, 20), np_ema(c, 50), np_ema(c, 200), np_rsi(c, 14), np_adx(h, l, c, 14)
    with np.errstate(invalid="ignore"):
        pre = (c > el) & (em > el) & (adx > 20) & (c > ef)
        tx = c < em
    prev = [np.nan]

    def orders(i, pos):
        out = []
        if pre[i]:
            cross = bool(rsi[i] > 55 and prev[0] <= 55)
            prev[0] = rsi[i]
            if cross:
                out.append(("entry", 1))
        if pos > 0 and tx[i]:
            out.append(("close", 1))
        return out

    ref = simulate(o, h, l, c, orders, on_close=True, stop=lambda i, pos, ep, eb: None if eb >= i else ep * 0.92)
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="D", strategy_overrides={"margin_long": 0, "margin_short": 0}), ref)
    return ok and len(ref) > 10, f"{detail} (need >10 trades, got {len(ref)})"
