"""Independent check — SMA sandwich (4N7k2rJQ): hourly bars. SMA200 > SMA100 > close > SMA13 > SMA26 with |SMA13-SMA26|/SMA13 within the threshold (1 % here instead of 0.3, passed to both sides) enters long on the FIRST bar of
that state; the mirror enters short. A long closes at the next open when high < SMA13, a short when low > SMA13. Entries are queued before closes. Margin off on the pinelib side."""
import numpy as np

from indep import bars, compare, np_sma, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "4N7k2rJQ"
THR = 1.0


def check():
    df = bars(40000, seed=216, freq="1h")
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    a, b, s100, s200 = np_sma(c, 13), np_sma(c, 26), np_sma(c, 100), np_sma(c, 200)
    with np.errstate(invalid="ignore", divide="ignore"):
        cl = np.abs(a - b) / a * 100 <= THR
        lc = (s200 > s100) & (s100 > c) & (c > a) & (a > b) & cl
        sc = (s200 < s100) & (s100 < c) & (c < a) & (a < b) & cl
    lc1, sc1 = np.r_[False, lc[:-1]], np.r_[False, sc[:-1]]
    with np.errstate(invalid="ignore"):
        lx, sx = h < a, l > a

    def orders(i, pos):
        out = []
        if lc[i] and not lc1[i]:
            out.append(("entry", 1))
        if sc[i] and not sc1[i]:
            out.append(("entry", -1))
        if pos > 0 and lx[i]:
            out.append(("close", 1))
        if pos < 0 and sx[i]:
            out.append(("close", -1))
        return out

    ref = simulate(o, h, l, c, orders)
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="60", params={"13/26密集阈值 (%)": THR},
                                        strategy_overrides={"margin_long": 0, "margin_short": 0}), ref)
    return ok and len(ref) > 10, f"{detail} (need >10 trades, got {len(ref)})"
