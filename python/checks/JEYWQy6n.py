"""Independent check — TEMA Zero-Lag Momentum (JEYWQy6n): hourly bars. Fast MACD(29,27) crossing its SMA(5) signal while the triple-EMA
line (81) is rising/falling reverses the position: close the other side if open, then enter. No exits otherwise."""
import numpy as np

from indep import bars, compare, np_cross_over, np_cross_under, np_ema, np_sma, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "JEYWQy6n"


def check():
    df = bars(20000, seed=108, freq="1h")
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    e1 = np_ema(c, 81)
    e2 = np_ema(e1, 81)
    e3 = np_ema(e2, 81)
    avg = 3 * (e1 - e2) + e3
    pavg = np.r_[np.nan, avg[:-1]]
    macd = np_ema(c, 29) - np_ema(c, 27)
    sig = np_sma(macd, 5)
    with np.errstate(invalid="ignore"):
        lg = np_cross_over(macd, sig) & (avg > pavg)
        sg = np_cross_under(macd, sig) & (avg < pavg)

    def orders(i, pos):
        out = []
        if lg[i]:
            if pos < 0:
                out.append(("close", -1))
            out.append(("entry", 1))
        if sg[i]:
            if pos > 0:
                out.append(("close", 1))
            out.append(("entry", -1))
        return out

    ref = simulate(o, h, l, c, orders)
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="60"), ref)
    return ok and len(ref) > 10, f"{detail} (need >10 trades, got {len(ref)})"
