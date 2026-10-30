"""Independent check — Market Structure Swing (tevFM5BB): 5-min bars. A wick through the previous bar's 5-bar extreme that closes back inside
(liquidity sweep) with the EMA200 trend and RSI 40/60 enters; bracket 1.5 ATR / 3 ATR from the signal close, working from the fill bar."""
import numpy as np

from indep import bars, compare, np_atr, np_ema, np_rsi, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "tevFM5BB"


def roll(x, n, fn):
    out = np.full(len(x), np.nan)
    for i in range(n - 1, len(x)):
        out[i] = fn(x[i - n + 1:i + 1])
    return out


def check():
    df = bars(20000, seed=116, freq="5min")
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    e200, rsi, atr = np_ema(c, 200), np_rsi(c, 14), np_atr(h, l, c, 14)
    sh1 = np.r_[np.nan, roll(h, 5, np.max)[:-1]]
    sl1 = np.r_[np.nan, roll(l, 5, np.min)[:-1]]
    with np.errstate(invalid="ignore"):
        lg = (c > e200) & (l < sl1) & (c > sl1) & (rsi > 40)
        sg = (c < e200) & (h > sh1) & (c < sh1) & (rsi < 60)
    cur = {1: (np.nan, np.nan), -1: (np.nan, np.nan)}
    hist = []

    def orders(i, pos):
        out = []
        if lg[i]:
            out.append(("entry", 1)); cur[1] = (c[i] - atr[i] * 1.5, c[i] + atr[i] * 3.0)
        if sg[i]:
            out.append(("entry", -1)); cur[-1] = (c[i] + atr[i] * 1.5, c[i] - atr[i] * 3.0)
        hist.append(dict(cur))
        return out

    ref = simulate(o, h, l, c, orders,
                   stop=lambda i, pos, ep, eb: hist[i - 1][pos][0] if i > 0 else None,
                   target=lambda i, pos, ep, eb: hist[i - 1][pos][1] if i > 0 else None)
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="5"), ref)
    return ok and len(ref) > 10, f"{detail} (need >10 trades, got {len(ref)})"
