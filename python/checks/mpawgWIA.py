"""Independent check — FVG BOS 50-62 (mpawgWIA): 4-hour bars, one trade at a time, market entries at the next open. Swing high / low = latest confirmed pivot (5 bars each side, strict). A bullish FVG (low > high two bars earlier) whose middle body exceeds 0.8 ATR14,
whose size (low - high[2]) exceeds 0.15 ATR and whose close breaks the latest swing high becomes the active zone (top = low, bottom = high[2]); bearish mirrored (high < low[2], top = low[2], bottom = high). A close below the active bull bottom (above the bear top) clears the zone.
Touch: low <= the 62 % retrace level (top - 0.62 gap; bear: bottom + 0.62 gap) and close >= bottom (<= top) while flat at the script run. Stop = bottom - 2 ticks (top + 2), target = level +/- 2 x risk (risk from the LEVEL, not the fill), placed with the entry and working from the fill bar;
the zone is consumed on entry. Variants: default and 50 %. Margin off on the pinelib side."""
import numpy as np

from indep import bars, compare, np_atr, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "mpawgWIA"
K = 5


def one(df, params, frac):
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    atr = np_atr(h, l, c, 14)
    ph, pl = np.full(n, np.nan), np.full(n, np.nan)
    for i in range(2 * K, n):
        j = i - K
        if h[j] > h[j - K:j].max() and h[j] > h[j + 1:i + 1].max():
            ph[i] = h[j]
        if l[j] < l[j - K:j].min() and l[j] < l[j + 1:i + 1].min():
            pl[i] = l[j]
    S = dict(sh=np.nan, sl=np.nan, bt=np.nan, bb=np.nan, st=np.nan, sb=np.nan)
    lev = {}

    def orders(i, pos):
        out = []
        if not np.isnan(ph[i]):
            S["sh"] = ph[i]
        if not np.isnan(pl[i]):
            S["sl"] = pl[i]
        if i >= 2:
            body = abs(c[i - 1] - o[i - 1])
            if l[i] > h[i - 2] and body > atr[i] * 0.8 and (l[i] - h[i - 2]) > atr[i] * 0.15 and c[i] > S["sh"]:
                S["bt"], S["bb"] = l[i], h[i - 2]
            if h[i] < l[i - 2] and body > atr[i] * 0.8 and (l[i - 2] - h[i]) > atr[i] * 0.15 and c[i] < S["sl"]:
                S["st"], S["sb"] = l[i - 2], h[i]
        if not np.isnan(S["bb"]) and c[i] < S["bb"]:
            S["bt"] = S["bb"] = np.nan
        if not np.isnan(S["st"]) and c[i] > S["st"]:
            S["st"] = S["sb"] = np.nan
        lvl_b = S["bt"] - (S["bt"] - S["bb"]) * frac if not np.isnan(S["bt"]) else np.nan
        lvl_s = S["sb"] + (S["st"] - S["sb"]) * frac if not np.isnan(S["st"]) else np.nan
        flat = pos == 0
        long_touch = (not np.isnan(S["bt"])) and l[i] <= lvl_b and c[i] >= S["bb"]
        short_touch = (not np.isnan(S["sb"])) and h[i] >= lvl_s and c[i] <= S["st"]
        lsl = S["bb"] - 0.02 if not np.isnan(S["bb"]) else np.nan
        ssl = S["st"] + 0.02 if not np.isnan(S["st"]) else np.nan
        lrisk = lvl_b - lsl
        srisk = ssl - lvl_s
        if flat and long_touch and lrisk > 0:
            out.append(("entry", 1))
            lev[i] = (lsl, lvl_b + lrisk * 2.0)
            S["bt"] = S["bb"] = np.nan
        if flat and short_touch and srisk > 0:
            out.append(("entry", -1))
            lev[i] = (ssl, lvl_s - srisk * 2.0)
            S["st"] = S["sb"] = np.nan
        return out

    stop = lambda i, pos, ep, eb: lev[eb - 1][0] if eb - 1 in lev else None
    tgt = lambda i, pos, ep, eb: lev[eb - 1][1] if eb - 1 in lev else None
    with np.errstate(invalid="ignore"):
        ref = simulate(o, h, l, c, orders, stop=stop, target=tgt)
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, d = compare(run_conversion(TV_ID, df, symbol=sym, tf="240", params=params, strategy_overrides={"margin_long": 0, "margin_short": 0}), ref)
    return ok and len(ref) > 10, f"{d} (got {len(ref)})"


def check():
    df = bars(30000, seed=601, freq="4h")
    msgs, allok = [], True
    for params, frac in (({}, 0.62), ({"Entry trigger level": "50%"}, 0.50)):
        ok, m = one(df, params, frac)
        allok &= ok
        msgs.append(m)
    return allok, " | ".join(msgs)
