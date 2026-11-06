"""Independent check — 3 Soldiers 3 Crows + 8 MA (V3jpZpIs): daily bars, defaults except the cooldown (3 bars here, passed to both sides) and a shorter slow MA (30 bars here, passed
to both sides). Source = high; fast = SMA of high; slow = ZLEMA = EMA(high + (high - high[lag])) with lag = floor((n-1)/2), nz() on the lag (0 before enough history). Three white soldiers / black crows
above/below both MAs, cooldown by bar index from the last same-side signal (init 0), market entries at the next open reversing an open opposite trade."""
import numpy as np

from indep import bars, compare, np_ema, np_sma, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "V3jpZpIs"
CD, SLOW = 3, 30


def check():
    df = bars(6000, seed=77)
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    fast = np_sma(h, 22)
    lag = (SLOW - 1) // 2
    sh = np.r_[np.zeros(lag), h[:-lag]] if lag else h
    slow = np_ema(h + (h - sh), SLOW)
    lb = ls = [0]
    lb, ls = [0], [0]

    def orders(i, pos):
        if i < 2:
            return []
        w = c[i] > o[i] and c[i-1] > o[i-1] and c[i-2] > o[i-2] and o[i-1] <= c[i-2] and c[i-1] > c[i-2] and o[i] <= c[i-1] and c[i] > c[i-1]
        k = c[i] < o[i] and c[i-1] < o[i-1] and c[i-2] < o[i-2] and o[i-1] >= c[i-2] and c[i-1] < c[i-2] and o[i] >= c[i-1] and c[i] < c[i-1]
        out = []
        with np.errstate(invalid="ignore"):
            if w and c[i] > fast[i] and c[i] > slow[i] and (i - lb[0]) > CD:
                out.append(("entry", 1))
                lb[0] = i
            if k and c[i] < fast[i] and c[i] < slow[i] and (i - ls[0]) > CD:
                out.append(("entry", -1))
                ls[0] = i
        return out

    ref = simulate(o, h, l, c, orders)
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="D", params={"Cooldown (свечей)": CD, "Период MA 2": SLOW},
                                        strategy_overrides={"margin_long": 0, "margin_short": 0}), ref)
    return ok and len(ref) > 10, f"{detail} (need >10 trades, got {len(ref)})"
