"""Independent check — FVG + Break of Structure (jyhTizLX): daily bars. Latest confirmed pivot high / low (10 bars each side) are the swing levels; a close beyond one = BOS. A 3-bar gap (low > high[2], or high < low[2])
seen within 20 bars of a same-direction BOS is stored; a later bar (within 20 bars of the gap) that reaches back into the stored gap (low <= gap top / high >= gap bottom) and closes at or beyond its far edge, while flat, enters;
the stop (gap edge -/+ 0.1 ATR) and target (close +/- 2 ATR) are fixed on that bar and persist for the trade; the stored gap on that side is cleared."""
import numpy as np

from indep import bars, compare, np_atr, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "jyhTizLX"
K = 10


def check():
    df = bars(8000, seed=33)
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    atr = np_atr(h, l, c, 14)
    sh_lvl = sl_lvl = np.nan
    bos_u = bos_d = None
    bh = bl = bbar = None
    sh_, sl_, sbar = None, None, None
    sig = {}
    lvl = {}

    def orders(i, pos):
        nonlocal sh_lvl, sl_lvl, bos_u, bos_d, bh, bl, bbar, sh_, sl_, sbar
        if i >= 2 * K:
            m = i - K
            w = h[m - K:m + K + 1]
            if h[m] == w.max() and (w == h[m]).sum() == 1:
                sh_lvl = h[m]
            w = l[m - K:m + K + 1]
            if l[m] == w.min() and (w == l[m]).sum() == 1:
                sl_lvl = l[m]
        if not np.isnan(sh_lvl) and c[i] > sh_lvl:
            bos_u = i
        if not np.isnan(sl_lvl) and c[i] < sl_lvl:
            bos_d = i
        if i >= 2:
            if l[i] > h[i - 2] and bos_u is not None and i - bos_u <= 20:
                bh, bl, bbar = l[i], h[i - 2], i
            if h[i] < l[i - 2] and bos_d is not None and i - bos_d <= 20:
                sh_, sl_, sbar = l[i - 2], h[i], i
        out = []
        if bl is not None and i - bbar <= 20 and l[i] <= bh and c[i] >= bl and pos == 0:
            out.append(("entry", 1))
            lvl[1] = (bl - atr[i] * 0.1, c[i] + atr[i] * 2)
            bh = bl = None
        if sh_ is not None and i - sbar <= 20 and h[i] >= sl_ and c[i] <= sh_ and pos == 0:
            out.append(("entry", -1))
            lvl[-1] = (sh_ + atr[i] * 0.1, c[i] - atr[i] * 2)
            sh_ = sl_ = None
        return out

    def stop(i, pos, ep, eb):
        return lvl[1 if pos > 0 else -1][0] if (1 if pos > 0 else -1) in lvl else None

    def target(i, pos, ep, eb):
        return lvl[1 if pos > 0 else -1][1] if (1 if pos > 0 else -1) in lvl else None

    with np.errstate(invalid="ignore"):
        ref = simulate(o, h, l, c, orders, stop=stop, target=target)
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="D", strategy_overrides={"margin_long": 0, "margin_short": 0}), ref)
    return ok and len(ref) > 10, f"{detail} (need >10 trades, got {len(ref)})"
