"""Independent check — BTC Averages (Nqu2Bqhu): hourly bars. SMA 3/48/168. Each bar queues, in source order: entry Long (fast > slow and close > trend), close Long (fast < slow), entry Short (fast < slow and close < trend),
close Short (fast > slow); orders fill at the next open in that order, an entry on the side already open is ignored (pyramiding 1). Margin off on the pinelib side (99 % of equity sizing)."""
import numpy as np

from indep import bars, compare, np_sma, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "Nqu2Bqhu"


def check():
    df = bars(20000, seed=212, freq="1h")
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    f, s, t = np_sma(c, 3), np_sma(c, 48), np_sma(c, 168)
    with np.errstate(invalid="ignore"):
        le, lx, se, sx = (f > s) & (c > t), f < s, (f < s) & (c < t), f > s

    def orders(i, pos):
        out = []
        if le[i]:
            out.append(("entry", 1))
        if lx[i]:
            out.append(("close", 1))
        if se[i]:
            out.append(("entry", -1))
        if sx[i]:
            out.append(("close", -1))
        return out

    ref = simulate(o, h, l, c, orders)
    sym = SymbolInfo.make("BINANCE:ETHUSD", "crypto", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="60", strategy_overrides={"margin_long": 0, "margin_short": 0}), ref)
    return ok and len(ref) > 10, f"{detail} (need >10 trades, got {len(ref)})"
