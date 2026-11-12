"""Independent check — VWAP Mean-Reversion Scalper 1:3 (CG3O8g9A): 5-min bars. In a ranging market (ADX<25) fade closes beyond session VWAP
with RSI<40 / >60, only when flat. The bracket is issued with the entry on the signal bar: stop 1 ATR, target 3 ATR, plus a trailing stop
(activation 2 ATR, offset 1.2 ATR, both converted to ticks of 0.01) — all working from the fill bar. Uses indep.exit_hit (stop+target+trail)."""
import numpy as np

from indep import bars, compare, np_atr, np_dmi, np_rsi, np_vwap, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "CG3O8g9A"


def check():
    df = bars(30000, seed=112, freq="5min")
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    vw, rsi, atr = np_vwap(df, c), np_rsi(c, 14), np_atr(h, l, c, 14)
    _, _, adx = np_dmi(h, l, c, 14)
    with np.errstate(invalid="ignore"):
        rng = adx < 25
        lg, sg = (c < vw) & (rsi < 40) & rng, (c > vw) & (rsi > 60) & rng
    cur = {1: None, -1: None}                                 # (stop, target, trail points, trail offset) as last issued
    hist = []

    def orders(i, pos):
        out = []
        if lg[i] and pos == 0:
            out.append(("entry", 1)); cur[1] = (c[i] - atr[i], c[i] + atr[i] * 3, atr[i] * 2 / 0.01, atr[i] * 1.2 / 0.01)
        if sg[i] and pos == 0:
            out.append(("entry", -1)); cur[-1] = (c[i] + atr[i], c[i] - atr[i] * 3, atr[i] * 2 / 0.01, atr[i] * 1.2 / 0.01)
        hist.append(dict(cur))
        return out

    def lv(k):
        return lambda i, pos, ep, eb: hist[i - 1][pos][k] if i > 0 and hist[i - 1][pos] is not None else None

    ref = simulate(o, h, l, c, orders, stop=lv(0), target=lv(1),
                   trail=lambda i, pos, ep, eb: (hist[i - 1][pos][2], hist[i - 1][pos][3]) if i > 0 and hist[i - 1][pos] is not None else None,
                   tick=0.01)
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="5"), ref)
    return ok and len(ref) > 10, f"{detail} (need >10 trades, got {len(ref)})"
