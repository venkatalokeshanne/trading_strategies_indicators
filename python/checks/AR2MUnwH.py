"""Independent check — Alpha Supertrend Vector (AR2MUnwH): daily bars, slippage 0, margin off. Supertrend(3, ATR7) direction flips (dir -1 = up: change < 0 buys; change > 0 sells short), ADX7 > 25, choppiness 100*log10(sum14(TR) / (HH14 - LL14))/log10(14) < 61.8 (TR sum needs 14 valid true ranges: the first bar's TR is na). Entry at the next open (a same-side signal is ignored);
entryAtrPct = ATR7/close*100 refreshed at every trigger. While a position exists (as of a bar's close): target = entry*(1 +/- pct*3/100), stop = entry*(1 -/+ pct/100) capped at the 1% hard stop (the nearer one); they work from the next bar for the same direction."""
import numpy as np
import pandas as pd

from indep import bars, compare, np_atr, np_dmi, np_supertrend, np_tr, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "AR2MUnwH"


def check():
    df = bars(9000, seed=330)
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    c1 = np.r_[np.nan, c[:-1]]
    tr = np.where(np.isnan(c1), np.nan, np.maximum(h - l, np.maximum(np.abs(h - c1), np.abs(l - c1))))
    sm = pd.Series(tr).rolling(14).sum().to_numpy()
    hh = pd.Series(h).rolling(14).max().to_numpy()
    ll = pd.Series(l).rolling(14).min().to_numpy()
    with np.errstate(invalid="ignore", divide="ignore"):
        chop = 100 * np.log10(sm / (hh - ll)) / np.log10(14)
    _, d = np_supertrend(h, l, c, 3.0, 7)
    dd = d - np.r_[np.nan, d[:-1]]
    dp, dm, adx = np_dmi(h, l, c, 7)
    atr = np_atr(h, l, c, 7)
    pct = atr / c * 100
    with np.errstate(invalid="ignore"):
        tl = (dd < 0) & (adx > 25) & (chop < 61.8)
        ts = (dd > 0) & (adx > 25) & (chop < 61.8)
    s = dict(p=np.nan)
    tmp, lv = {}, {}

    def orders(i, pos):
        out = []
        if tl[i]:
            out.append(("entry", 1))
            s["p"] = pct[i]
        if ts[i]:
            out.append(("entry", -1))
            s["p"] = pct[i]
        ep = tmp.get(i) if pos != 0 else None
        lv[i] = None if ep is None else (1 if pos > 0 else -1, ep, s["p"])
        return out

    def stop(i, pos, ep, eb):
        tmp[i] = ep
        p = lv.get(i - 1) if i > 0 else None
        if p is None or p[0] * pos <= 0 or np.isnan(p[2]):
            return None
        return max(p[1] * (1 - p[2] / 100), p[1] * (1 - 0.01)) if pos > 0 else min(p[1] * (1 + p[2] / 100), p[1] * (1 + 0.01))

    def target(i, pos, ep, eb):
        p = lv.get(i - 1) if i > 0 else None
        if p is None or p[0] * pos <= 0 or np.isnan(p[2]):
            return None
        return p[1] * (1 + p[2] * 3 / 100) if pos > 0 else p[1] * (1 - p[2] * 3 / 100)

    with np.errstate(invalid="ignore"):
        ref = simulate(o, h, l, c, orders, stop=stop, target=target)
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="D", strategy_overrides={"margin_long": 0, "margin_short": 0, "slippage": 0}), ref)
    return ok and len(ref) > 10, f"{detail} (need >10 trades, got {len(ref)})"
