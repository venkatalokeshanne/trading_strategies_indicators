"""Independent check — Volatility Expansion MNQ V7 (57J0Kih3): 30-min bars. ratio = ATR20 / nz(SMA40(ATR20), 1); < 0.95 compressed (stores high / low as break levels), > 1.02 expanding. While expanding, close crossing over the stored high
(under the stored low) enters when flat (the used level is cleared). v6 short-circuit: each cross runs only on expanding bars, against the last bar it ran on (LESSONS P4/P5). Risk = max(1.5 ATR, 10 ticks); while a position is open at a
close the exit (loss = risk, profit = 2 x risk, in ticks of 0.01 = price distance from the fill) works from the next bar. Margin off on the pinelib side."""
import numpy as np

from indep import bars, compare, np_atr, np_sma, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "57J0Kih3"
TICK = 0.01


def check():
    df = bars(30000, seed=298, freq="30min")
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    atr = np_atr(h, l, c, 20)
    avg = np_sma(atr, 40)
    with np.errstate(invalid="ignore"):
        ratio = atr / np.where(np.isnan(avg), 1.0, avg)
        comp, exp = ratio < 0.95, ratio > 1.02
    bh = bl = np.nan
    pa = [np.nan, np.nan]                        # (close, breakoutHigh) at the last bar the crossover ran
    pb = [np.nan, np.nan]
    risk = [np.nan]

    def orders(i, pos):
        nonlocal bh, bl
        if comp[i]:
            bh, bl = h[i], l[i]
        out = []
        lg = sg = False
        if exp[i]:
            lg = bool(c[i] > bh and pa[0] <= pa[1])
            pa[0], pa[1] = c[i], bh
            sg = bool(c[i] < bl and pb[0] >= pb[1])
            pb[0], pb[1] = c[i], bl
        if lg and pos == 0:
            risk[0] = max(atr[i] * 1.5, TICK * 10); out.append(("entry", 1)); bh = np.nan
        if sg and pos == 0:
            risk[0] = max(atr[i] * 1.5, TICK * 10); out.append(("entry", -1)); bl = np.nan
        return out

    with np.errstate(invalid="ignore"):
        ref = simulate(o, h, l, c, orders, stop=lambda i, pos, ep, eb: None if eb >= i else ep - pos * risk[0],
                       target=lambda i, pos, ep, eb: None if eb >= i else ep + pos * risk[0] * 2.0)
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="30", strategy_overrides={"margin_long": 0, "margin_short": 0}), ref)
    return ok and len(ref) > 10, f"{detail} (need >10 trades, got {len(ref)})"
