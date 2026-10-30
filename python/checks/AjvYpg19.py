"""Independent check — Fade The Crowd Protocol (AjvYpg19): daily bars, one position, trade list only. MACD(8,17,9) cross (any direction): with histogram > 0 after the cross and high >= VWMA20 -> SHORT, histogram < 0 and low <= VWMA20 -> LONG;
Choppiness(7) = 100 x log10(sum7(TR) / (highest high7 - lowest low7)) / log10(7) < 100 (TR na on bar 0), ADX7 > 20, at least 7 bars since the last exit (script-time position went to 0), flat. Entry at the next open; on the first script
run holding the position (the bar after the fill) TP = fill x (1 -/+ 3 ATR7%), stop = the tighter of fill x (1 +/- 2 ATR7%) and fill x (1 +/- 1.3%) with the ATR7% saved at the signal bar; the exit order then works from the following bar. Margin and
slippage off on the pinelib side."""
import numpy as np
import pandas as pd

from indep import bars, compare, np_atr, np_cross_over, np_cross_under, np_dmi, np_ema, np_tr, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "AjvYpg19"


def check():
    df = bars(6000, seed=121)
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    v = df["volume"].to_numpy()
    n = len(c)
    trs = pd.Series(np_tr(h, l, c, False)).rolling(7).sum().to_numpy()
    rng = pd.Series(h).rolling(7).max().to_numpy() - pd.Series(l).rolling(7).min().to_numpy()
    with np.errstate(invalid="ignore", divide="ignore"):
        chop = 100 * np.log10(trs / rng) / np.log10(7)
    _, _, adx = np_dmi(h, l, c, 7)
    macd = np_ema(c, 8) - np_ema(c, 17)
    sig = np_ema(macd, 9)
    hist = macd - sig
    vw = pd.Series(c * v).rolling(20).sum().to_numpy() / pd.Series(v).rolling(20).sum().to_numpy()
    atrp = np_atr(h, l, c, 7) / c * 100
    cross = np_cross_over(macd, sig) | np_cross_under(macd, sig)
    S = dict(prev=None, last=None, stored=np.nan)
    poscl = np.zeros(n)
    ep_now = {"i": -1, "ep": np.nan}
    lvl = {}

    def orders(i, pos):
        poscl[i] = pos
        out = []
        if S["prev"] is not None and S["prev"] != 0 and pos == 0:
            S["last"] = i
        S["prev"] = pos
        cool = S["last"] is None or i - S["last"] >= 7
        with np.errstate(invalid="ignore"):
            base = bool(cross[i] and chop[i] < 100.0 and adx[i] > 20.0 and cool and pos == 0)
            ts = base and hist[i] > 0 and h[i] >= vw[i]
            tl = base and hist[i] < 0 and l[i] <= vw[i]
        if ts:
            S["stored"] = atrp[i]
            out.append(("entry", -1))
        if tl:
            S["stored"] = atrp[i]
            out.append(("entry", 1))
        if pos != 0 and ep_now["i"] == i and (i == 0 or poscl[i - 1] == 0):
            fp, st_ = ep_now["ep"], S["stored"]
            tpd, sld, plug = st_ * 3.0 / 100, st_ * 2.0 / 100, 1.3 / 100
            if pos > 0:
                lvl["v"] = (max(fp * (1 - sld), fp * (1 - plug)), fp * (1 + tpd))
            else:
                lvl["v"] = (min(fp * (1 + sld), fp * (1 + plug)), fp * (1 - tpd))
            lvl["from"] = i + 1
        return out

    def stop(i, pos, ep, eb):
        ep_now["i"], ep_now["ep"] = i, ep
        if i == 0 or poscl[i - 1] * pos <= 0 or "v" not in lvl or i < lvl["from"]:
            return None
        return lvl["v"][0]

    def target(i, pos, ep, eb):
        if i == 0 or poscl[i - 1] * pos <= 0 or "v" not in lvl or i < lvl["from"]:
            return None
        return lvl["v"][1]

    with np.errstate(invalid="ignore"):
        ref = simulate(o, h, l, c, orders, stop=stop, target=target)
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="D", strategy_overrides={"margin_long": 0, "margin_short": 0, "slippage": 0}), ref)
    return ok and len(ref) > 10, f"{detail} (need >10 trades, got {len(ref)})"
