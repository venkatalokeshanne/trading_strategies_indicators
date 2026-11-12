"""Independent check — Spike EA (8pUGH47d): daily bars. The previous bar is a spike when its range >= threshold * unit (unit = median daily range, passed to both sides; stop 1.5 / take 2 units); bullish spike buys, others sell.
Flat -> entry; opposite position open -> close only (no reversal). A stop / limit around the entry price is issued while a position is open at a close, so it works from the bar after the fill."""
import numpy as np

from indep import bars, compare, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "8pUGH47d"


def check():
    df = bars(6000, seed=220)
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    unit = float(np.median(h - l))
    sd, td = 1.5 * unit, 2.0 * unit
    rng = np.r_[np.nan, (h - l)[:-1]]
    po, pc = np.r_[np.nan, o[:-1]], np.r_[np.nan, c[:-1]]
    with np.errstate(invalid="ignore"):
        spike = rng >= 0.5 * unit
        bs, ss = spike & (pc > po), spike & (pc <= po)

    def orders(i, pos):
        out = []
        if bs[i]:
            if pos < 0:
                out.append(("close", -1))
            elif pos == 0:
                out.append(("entry", 1))
        if ss[i]:
            if pos > 0:
                out.append(("close", 1))
            elif pos == 0:
                out.append(("entry", -1))
        return out

    ref = simulate(o, h, l, c, orders,
                   stop=lambda i, pos, ep, eb: None if eb >= i else ep - pos * sd,
                   target=lambda i, pos, ep, eb: None if eb >= i else ep + pos * td)
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="D",
                                        params={"Price Unit for Threshold": unit, "Stop Loss Price Distance": sd, "Take Profit Price Distance": td}), ref)
    return ok and len(ref) > 10, f"{detail} (need >10 trades, got {len(ref)})"
