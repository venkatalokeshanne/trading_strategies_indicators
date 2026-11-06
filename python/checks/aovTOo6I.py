"""Independent check — XAUUSD RSI Long + Short (aovTOo6I): 1-minute bars, RSI14 of the 5-minute timeframe (09:30-NY blocks, lookahead off). RSI < 29 with no position buys, RSI > 71 shorts (next open); a fixed $10 move
(take-profit $20 / stop-loss $20 divided by 2 ounces) around the entry price, issued only while in a position so it works from the next bar. Margin and slippage off on the pinelib side."""
import numpy as np

from indep import bars, compare, np_periods, np_rsi, np_security_lookahead_off, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "aovTOo6I"


def check():
    df = bars(30000, seed=311, freq="1min")
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    pid, last_of = np_periods(df, 5)
    pcl = np.array([c[last_of & (pid == k)][0] for k in range(pid[-1] + 1)])
    rsi = np_security_lookahead_off(np_rsi(pcl, 14), pid, last_of)
    poscl = np.zeros(n)

    def orders(i, pos):
        poscl[i] = pos
        out = []
        with np.errstate(invalid="ignore"):
            if pos == 0 and rsi[i] < 29.0:
                out.append(("entry", 1))
            if pos == 0 and rsi[i] > 71.0:
                out.append(("entry", -1))
        return out

    def stop(i, pos, ep, eb):
        if i == 0 or poscl[i - 1] * pos <= 0:
            return None
        return ep - 10.0 if pos > 0 else ep + 10.0

    def target(i, pos, ep, eb):
        if i == 0 or poscl[i - 1] * pos <= 0:
            return None
        return ep + 10.0 if pos > 0 else ep - 10.0

    ref = simulate(o, h, l, c, orders, stop=stop, target=target)
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="1", strategy_overrides={"margin_long": 0, "margin_short": 0, "slippage": 0}), ref)
    return ok and len(ref) > 10, f"{detail} (need >10 trades, got {len(ref)})"
