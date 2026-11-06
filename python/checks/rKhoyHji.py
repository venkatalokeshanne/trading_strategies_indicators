"""Independent check — BTC Scalper T3 (rKhoyHji): hourly bars. T3(8, 0.7) = c1 e6 + c2 e5 + c3 e4 + c4 e3 of six chained EMAs (Tillson). Close crossing over it on volume > SMA20 buys, under sells short (reversing). Entry + exit on the signal
bar; profit / loss are passed in TICKS as close*(1 +/- pct)/mintick (a whole-price distance, as written): long target = fill + 1.008*close_sig, stop = fill - 0.995*close_sig; short target = fill - 0.992*close_sig, stop =
fill + 1.005*close_sig. Slippage (1 tick) and margin off on the pinelib side."""
import numpy as np

from indep import bars, compare, np_cross_over, np_cross_under, np_ema, np_sma, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "rKhoyHji"


def check():
    df = bars(30000, seed=296, freq="1h")
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    v = df["volume"].to_numpy()
    e = [c]
    for _ in range(6):
        e.append(np_ema(e[-1], 8))
    f = 0.7
    c1 = -f ** 3
    c2 = 3 * f ** 2 + 3 * f ** 3
    c3 = -6 * f ** 2 - 3 * f - 3 * f ** 3
    c4 = 1 + 3 * f + f ** 3 + 3 * f ** 2
    t3 = c1 * e[6] + c2 * e[5] + c3 * e[4] + c4 * e[3]
    with np.errstate(invalid="ignore"):
        vc = v > np_sma(v, 20)
        lg, sh = np_cross_over(c, t3) & vc, np_cross_under(c, t3) & vc
    lvl = {1: (np.nan, np.nan), -1: (np.nan, np.nan)}                    # (stop distance, target distance) relative to the fill price

    def orders(i, pos):
        out = []
        if lg[i]:
            out.append(("entry", 1)); lvl[1] = (0.995 * c[i], 1.008 * c[i])
        if sh[i]:
            out.append(("entry", -1)); lvl[-1] = (1.005 * c[i], 0.992 * c[i])
        return out

    with np.errstate(invalid="ignore"):
        ref = simulate(o, h, l, c, orders, stop=lambda i, pos, ep, eb: ep - pos * lvl[pos][0], target=lambda i, pos, ep, eb: ep + pos * lvl[pos][1])
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="60", strategy_overrides={"slippage": 0, "margin_long": 0, "margin_short": 0}), ref)
    return ok and len(ref) > 10, f"{detail} (need >10 trades, got {len(ref)})"
