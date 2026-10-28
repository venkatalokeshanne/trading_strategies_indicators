"""Independent check — EMA 9,20 + S/R Breakout v5 (5EGVP61U): daily bars, process_orders_on_close (fills at the signal bar's close). EMA9 crossing over (under) EMA20 with the close beyond EMA9 and body >= 30 % of the range enters long
(short) when flat. The script reads the position before that close's fill, so the 12 % / 6 % bracket around the entry price is first issued on the bar AFTER the fill and works from the following bar. Margin off on the pinelib side."""
import numpy as np

from indep import bars, compare, np_cross_over, np_cross_under, np_ema, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "5EGVP61U"


def check():
    df = bars(8000, seed=303)
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    f, s = np_ema(c, 9), np_ema(c, 20)
    rng = h - l
    with np.errstate(invalid="ignore", divide="ignore"):
        strong = (rng > 0) & (np.abs(c - o) / rng >= 0.3)
        bc, sc = np_cross_over(f, s) & (c > f) & strong, np_cross_under(f, s) & (c < f) & strong
    poscl = np.zeros(n)

    def orders(i, pos):
        poscl[i] = pos
        out = []
        if bc[i] and pos == 0:
            out.append(("entry", 1))
        if sc[i] and pos == 0:
            out.append(("entry", -1))
        return out

    ref = simulate(o, h, l, c, orders, on_close=True,
                   stop=lambda i, pos, ep, eb: None if (i == 0 or poscl[i - 1] != pos) else ep * (1 - 0.06 * pos),
                   target=lambda i, pos, ep, eb: None if (i == 0 or poscl[i - 1] != pos) else ep * (1 + 0.12 * pos))
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="D", strategy_overrides={"margin_long": 0, "margin_short": 0}), ref)
    return ok and len(ref) > 10, f"{detail} (need >10 trades, got {len(ref)})"
