"""Independent check — Hull RSI Trend Rider (0ZBQpzty): daily bars. HMA(550) = WMA(2*WMA(c,275) - WMA(c,550), 23); trend 1 when it rises, else -1 (na compares false); flag resets when the direction changes. v6 short-circuit: the RSI
crossunder(50) runs only on trend==1 bars and the crossover(50) only on trend==-1 bars, each against the last bar it ran on. Long (trend 1, cross under, not taken, flat): stop = lowest low of 13 fed values, target = close + 5 risk;
short mirrored. A position open at a close issues the exit, which works from the next bar; a trend flip closes at the next open. Margin off on the pinelib side."""
import numpy as np

from indep import bars, compare, np_rsi, np_wma, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "0ZBQpzty"


def check():
    df = bars(6000, seed=224)
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    hma = np_wma(2 * np_wma(c, 275) - np_wma(c, 550), 23)
    prev = np.r_[np.nan, hma[:-1]]
    with np.errstate(invalid="ignore"):
        td = np.where(hma > prev, 1, -1)
    rsi = np_rsi(c, 14)
    taken, pl, ps = False, np.nan, np.nan
    fed_lo, fed_hi = [], []                              # ta.lowest / ta.highest sit inside `if`: their 13-bar windows hold only the values fed on bars where the branch ran (LESSONS P5)
    sl, tp = [np.nan], [np.nan]
    poscl = np.zeros(n)

    def orders(i, pos):
        nonlocal taken, pl, ps
        poscl[i] = pos
        if i > 0 and td[i] != td[i - 1]:
            taken = False
        lc = sc = False
        if td[i] == 1:
            lc = bool(rsi[i] < 50 and pl >= 50)
            pl = rsi[i]
        if td[i] == -1:
            sc = bool(rsi[i] > 50 and ps <= 50)
            ps = rsi[i]
        out = []
        if lc and not taken and pos == 0:
            fed_lo.append(l[i])
            sl[0] = min(fed_lo[-13:]) if len(fed_lo) >= 13 else np.nan
            tp[0] = c[i] + (c[i] - sl[0]) * 5.0
            out.append(("entry", 1)); taken = True
        if sc and not taken and pos == 0:
            fed_hi.append(h[i])
            sl[0] = max(fed_hi[-13:]) if len(fed_hi) >= 13 else np.nan
            tp[0] = c[i] - (sl[0] - c[i]) * 5.0
            out.append(("entry", -1)); taken = True
        if pos > 0 and td[i] == -1:
            out.append(("close", 1))
        if pos < 0 and td[i] == 1:
            out.append(("close", -1))
        return out

    def level(k):
        return lambda i, pos, ep, eb: None if eb >= i else (sl[0] if k == 0 else tp[0])

    with np.errstate(invalid="ignore"):
        ref = simulate(o, h, l, c, orders, stop=level(0), target=level(1))
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="D", strategy_overrides={"margin_long": 0, "margin_short": 0}), ref)
    return ok and len(ref) > 5, f"{detail} (need >5 trades, got {len(ref)})"
