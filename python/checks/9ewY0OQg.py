"""Independent check — HA signals on regular candles (9ewY0OQg): daily bars. Heikin-Ashi built from the chart candles (close = ohlc4, open = avg(previous HA open, previous HA close) seeded with (open+close)/2, high / low include the HA open and close). ZL source = HAclose + (HAclose - HAclose[25]),
SMMA50 of it (seeded by the first SMA once 50 valid values exist, then (prev*49 + x)/50). Chandelier: ATR(1) = true range of the regular candles, long stop = HAhigh - 2 TR (ratcheting while the previous HA close is above the previous stop), short stop = HAlow + 2 TR; dir flips to 1 when HAclose > previous short stop, to -1 when below previous long stop.
A flip to 1 (from -1) with HAclose > SMMA buys when not long (short mirrors); the stop (signal bar low / high) is issued once the position exists (from the bar after the one that sees it); a HA close back through the SMMA closes the trade."""
import numpy as np

from indep import bars, compare, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "9ewY0OQg"


def check():
    df = bars(9000, seed=17)
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    hc = (o + h + l + c) / 4
    ho = np.zeros(n)
    ho[0] = (o[0] + c[0]) / 2
    for i in range(1, n):
        ho[i] = (ho[i - 1] + hc[i - 1]) / 2
    hh, hl = np.maximum(h, np.maximum(ho, hc)), np.minimum(l, np.minimum(ho, hc))
    c1 = np.r_[np.nan, c[:-1]]
    tr = np.where(np.isnan(c1), h - l, np.maximum(h - l, np.maximum(np.abs(h - c1), np.abs(l - c1))))
    zl = hc + (hc - np.r_[[np.nan] * 25, hc[:-25]])
    sm = np.full(n, np.nan)
    for i in range(n):
        if np.isnan(sm[i - 1] if i else np.nan):
            w = zl[max(0, i - 49):i + 1]
            if i >= 49 and not np.isnan(w).any():
                sm[i] = w.mean()
        else:
            sm[i] = (sm[i - 1] * 49 + zl[i]) / 50
    lsh = np.full(n, np.nan)
    ssh = np.full(n, np.nan)
    dr = np.ones(n, int)
    dprev = np.full(n, np.nan)
    d = 1
    with np.errstate(invalid="ignore"):
        for i in range(n):
            lraw, sraw = hh[i] - 2 * tr[i], hl[i] + 2 * tr[i]
            pl = lsh[i - 1] if i and not np.isnan(lsh[i - 1]) else lraw
            ps = ssh[i - 1] if i and not np.isnan(ssh[i - 1]) else sraw
            hc1 = hc[i - 1] if i else np.nan
            lsh[i] = max(lraw, pl) if hc1 > pl else lraw
            ssh[i] = min(sraw, ps) if hc1 < ps else sraw
            ps2 = ssh[i - 1] if i and not np.isnan(ssh[i - 1]) else ssh[i]
            pl2 = lsh[i - 1] if i and not np.isnan(lsh[i - 1]) else lsh[i]
            dprev[i] = d
            d = 1 if hc[i] > ps2 else -1 if hc[i] < pl2 else d
            dr[i] = d
        buy = (dr == 1) & (dprev == -1) & (hc > sm)
        sell = (dr == -1) & (dprev == 1) & (hc < sm)
    s = dict(lsl=np.nan, ssl=np.nan)
    poscl = np.zeros(n)

    def orders(i, pos):
        poscl[i] = pos
        out = []
        if buy[i] and pos <= 0:
            s["lsl"] = l[i]
            out.append(("entry", 1))
        if sell[i] and pos >= 0:
            s["ssl"] = h[i]
            out.append(("entry", -1))
        with np.errstate(invalid="ignore"):
            if pos > 0 and hc[i] < sm[i]:
                out.append(("close", 1))
            if pos < 0 and hc[i] > sm[i]:
                out.append(("close", -1))
        if pos == 0:
            s["lsl"] = s["ssl"] = np.nan
        return out

    lvl = {}

    def stop(i, pos, ep, eb):
        if i == 0 or poscl[i - 1] * pos <= 0:
            return None
        v = lvl.get((i - 1, 1 if pos > 0 else -1))
        return v

    # the stop is issued at each script run with a position, from the then-current stop variable: record it as a function of i
    def orders2(i, pos):
        out = orders(i, pos)
        if pos > 0 and not np.isnan(s["lsl"]):
            lvl[(i, 1)] = s["lsl"]
        if pos < 0 and not np.isnan(s["ssl"]):
            lvl[(i, -1)] = s["ssl"]
        return out

    with np.errstate(invalid="ignore"):
        ref = simulate(o, h, l, c, orders2, stop=stop)
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="D", strategy_overrides={"margin_long": 0, "margin_short": 0}), ref)
    return ok and len(ref) > 10, f"{detail} (need >10 trades, got {len(ref)})"
