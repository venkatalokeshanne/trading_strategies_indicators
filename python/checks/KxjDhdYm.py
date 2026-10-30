"""Independent check — SMC breakout (KxjDhdYm): daily bars, Swing Length 5 here (passed to both sides). ATR = RMA14 of the true range (first bar high-low). The latest confirmed pivot high / low (5 bars each side, strict) arms that side; a bar whose high (low) breaks the armed level
fires once (the side is disarmed on any break, traded or not). A signal enters when TradeisON is false; TradeisON is set by the signal but cleared again at the end of the same bar because the script still sees a flat position, and is cleared on every later flat bar.
SL = close -/+ |close - (low - 1.5 ATR)| (short: |close - (high + 1.5 ATR)|), TP = close +/- 1.1 x that distance; fixed at the signal bar."""
import numpy as np

from indep import bars, compare, np_rma, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "KxjDhdYm"
K = 5


def check():
    df = bars(9000, seed=13)
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    c1 = np.r_[np.nan, c[:-1]]
    tr = np.where(np.isnan(c1), h - l, np.maximum(h - l, np.maximum(np.abs(h - c1), np.abs(l - c1))))
    atr = np_rma(tr, 14)
    s = dict(uh=np.nan, ul=np.nan, pa=False, la=False, on=False)
    lvl = {}

    def orders(i, pos):
        out = []
        if i >= 2 * K:
            m = i - K
            w = h[m - K:m + K + 1]
            if h[m] == w.max() and (w == h[m]).sum() == 1:
                s["uh"], s["pa"] = h[m], True
            w = l[m - K:m + K + 1]
            if l[m] == w.min() and (w == l[m]).sum() == 1:
                s["ul"], s["la"] = l[m], True
        with np.errstate(invalid="ignore"):
            buy = h[i] > s["uh"] and s["pa"]
            sell = l[i] < s["ul"] and s["la"]
        if buy:
            s["pa"] = False
        if sell:
            s["la"] = False
        d1 = abs(c[i] - (l[i] - atr[i] * 1.5))
        d2 = abs(c[i] - (atr[i] * 1.5 + h[i]))
        if buy and not s["on"]:
            s["on"] = True
            lvl[1] = (c[i] - d1, c[i] + 1.1 * d1)
            out.append(("entry", 1))
        if sell and not s["on"]:
            s["on"] = True
            lvl[-1] = (c[i] + d2, c[i] - 1.1 * d2)
            out.append(("entry", -1))
        if pos == 0:
            s["on"] = False
        return out

    def stop(i, pos, ep, eb):
        return lvl[1 if pos > 0 else -1][0]

    def target(i, pos, ep, eb):
        return lvl[1 if pos > 0 else -1][1]

    with np.errstate(invalid="ignore"):
        ref = simulate(o, h, l, c, orders, stop=stop, target=target)
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="D", params={"Swing Length": K},
                                        strategy_overrides={"margin_long": 0, "margin_short": 0}), ref)
    return ok and len(ref) > 10, f"{detail} (need >10 trades, got {len(ref)})"
