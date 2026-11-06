"""Independent check — Super Negative RR (w8FXpidd): hourly bars on a symbol worth 100 $ per price point (tick 0.01, so a tick is 1 $). Signal at the bar close while flat: previous candle's total wick > ATR(14) of that bar,
upper wick > 2 x lower wick (-> long) or lower wick > 2 x upper wick (-> short), body >= 0.1 ATR; the ATR/candle are those of the PREVIOUS bar (prevAtr = atr[1]). Bracket from the fill price: take-profit 300 ticks (3.00), stop 1000 ticks (10.00); working from the fill bar. Commission / slippage / margin off on the pinelib side."""
import numpy as np

from indep import bars, compare, np_atr, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "w8FXpidd"


def check():
    df = bars(20000, seed=581, freq="1h")
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    atr = np_atr(h, l, c, 14)
    sh = lambda x: np.r_[np.nan, x[:-1]]
    pa, ph, pl, po, pc = sh(atr), sh(h), sh(l), sh(o), sh(c)
    body_hi, body_lo = np.fmax(po, pc), np.fmin(po, pc)
    up, lo = ph - body_hi, body_lo - pl
    with np.errstate(invalid="ignore"):
        base = ((up + lo) > pa) & ((body_hi - body_lo) >= pa * 0.1)
        long_sig = base & (up > lo * 2.0)
        short_sig = base & (lo > up * 2.0)

    def orders(i, pos):
        if pos != 0:
            return []
        if long_sig[i]:
            return [("entry", 1)]
        if short_sig[i]:
            return [("entry", -1)]
        return []

    stop = lambda i, pos, ep, eb: ep - pos * 10.0
    tgt = lambda i, pos, ep, eb: ep + pos * 3.0
    with np.errstate(invalid="ignore"):
        ref = simulate(o, h, l, c, orders, stop=stop, target=tgt)
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9, pointvalue=100.0)
    res = run_conversion(TV_ID, df, symbol=sym, tf="60", strategy_overrides={"margin_long": 0, "margin_short": 0, "slippage": 0, "commission_value": 0})
    ok, d = compare(res, ref)
    return ok and len(ref) > 10, f"{d} (got {len(ref)})"
