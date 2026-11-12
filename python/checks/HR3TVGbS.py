"""Independent check — AI MES Asian Session Strategy (HR3TVGbS): 5-minute bars (24 h synthetic, price ~4000) on a US stock chart (HTF periods counted from 09:30 New York), 1 contract, market orders at the next open, margin / commission / slippage off. 18:00-18:30 ET builds the range (locked at the first bar of the 18:30-23:59 trading part; midpoint = (high + low)/2 of the building high / low); inside it, flat and under the per-session limit, a breakout (close beyond the range by the buffer on the bar after the previous close was not, RSI > / < 50, volume above multiplier, HTF EMA(21) bias with lookahead off) or a fade (tag of the edge within the buffer, close back inside, RSI extreme, volume floor) enters at the next open; stop = the wider of range edge +/- buffer and the ATR floor, target = R:R x risk (breakout) or the range midpoint (fade); the exit is issued while the position is open; everything is closed after the sessions end. Uses the pending-order reference broker (simulate_ord).
Variants: defaults; no HTF / volume filters, wider range limits and R:R 2; other RSI limits, buffer 0 and max 1 trade."""
import numpy as np
import pandas as pd

from indep import bars, compare, np_atr, np_ema, np_periods, np_rsi, np_security_lookahead_off, np_sma, run_conversion, simulate_ord
from pinelib import SymbolInfo

TV_ID = "HR3TVGbS"


def one(df, params, p):
    o, h, l, c, v = (df[k].to_numpy() for k in ("open", "high", "low", "close", "volume"))
    n = len(c)
    sym = SymbolInfo.make("NASDAQ:XYZ", "stock", qty_step=1e-9)
    ny = pd.to_datetime(df["time"], unit="ms", utc=True).dt.tz_convert("America/New_York")
    et = (ny.dt.hour * 100 + ny.dt.minute).to_numpy()
    pid, last_of = np_periods(df, 60)
    htf = np_security_lookahead_off(np_ema(c[last_of], 21), pid, last_of)
    rsi = np_rsi(c, 14)
    atr = np_atr(h, l, c, 14)
    vavg = np_sma(v, 20)
    S = dict(st=0, rh=np.nan, rl=np.nan, lh=np.nan, ll=np.nan, mid=np.nan, es=np.nan, et=np.nan)
    nn = lambda x: None if np.isnan(x) else x

    def orders(i, pos):
        out = []
        t = et[i]
        ib = 1800 <= t < 1830
        ia = 1830 <= t <= 2359
        iany = ib or ia
        t1 = et[i - 1] if i else -1
        ia1 = 1830 <= t1 <= 2359
        iany1 = (1800 <= t1 < 1830) or ia1
        ns = ia and not ia1
        if ns:
            S["st"] = 0
        if ib:
            S["rh"] = h[i] if np.isnan(S["rh"]) else max(S["rh"], h[i])
            S["rl"] = l[i] if np.isnan(S["rl"]) else min(S["rl"], l[i])
        if ns:
            S["lh"], S["ll"], S["mid"] = S["rh"], S["rl"], (S["rh"] + S["rl"]) / 2
            S["rh"] = S["rl"] = np.nan
        lh, ll = S["lh"], S["ll"]
        c1 = c[i - 1] if i else np.nan
        with np.errstate(invalid="ignore"):
            rsz = np.nan if (np.isnan(lh) or np.isnan(ll)) else lh - ll
            valid = (not np.isnan(rsz)) and p["minr"] <= rsz <= p["maxr"]
            hl = (not p["usehtf"]) or c[i] > htf[i]
            hs = (not p["usehtf"]) or c[i] < htf[i]
            vb = (not p["usevol"]) or v[i] > vavg[i] * 1.2
            vf = (not p["usevol"]) or v[i] > vavg[i] * 0.8
            bl = valid and c[i] > lh + p["bb"] and c1 <= lh + p["bb"] and rsi[i] > 50 and vb and hl
            bs = valid and c[i] < ll - p["bb"] and c1 >= ll - p["bb"] and rsi[i] < 50 and vb and hs
            tgh = h[i] >= lh - 1.0
            tgl = l[i] <= ll + 1.0
            fs = valid and tgh and c[i] < lh and c1 >= lh and rsi[i] > p["ob"] and vf and hs
            fl = valid and tgl and c[i] > ll and c1 <= ll and rsi[i] < p["os"] and vf and hl
            under = S["st"] < p["maxt"]
            lc = bool(ia and under and pos == 0 and (bl or fl))
            sc = bool(ia and under and pos == 0 and (bs or fs))
            als, ass = c[i] - atr[i] * 1.5, c[i] + atr[i] * 1.5
            bls, bss = ll - 1.5, lh + 1.5
            lstop = np.nan if (np.isnan(bls) or np.isnan(als)) else min(bls, als)
            sstop = np.nan if (np.isnan(bss) or np.isnan(ass)) else max(bss, ass)
            ltgt = S["mid"] if fl else c[i] + (c[i] - lstop) * p["rr"]
            stgt = S["mid"] if fs else c[i] - (sstop - c[i]) * p["rr"]
        if pos == 0:
            S["es"] = S["et"] = np.nan
        if lc:
            S["es"], S["et"] = lstop, ltgt
            out.append(("entry", "Long", 1, None, None))
            S["st"] += 1
        if sc:
            S["es"], S["et"] = sstop, stgt
            out.append(("entry", "Short", -1, None, None))
            S["st"] += 1
        if pos > 0:
            out.append(("exit", "Long Exit", "Long", nn(S["es"]), nn(S["et"])))
        if pos < 0:
            out.append(("exit", "Short Exit", "Short", nn(S["es"]), nn(S["et"])))
        if (not iany) and iany1:
            out.append(("close_all",))
        return out

    ref = simulate_ord(o, h, l, c, orders)
    ok, d = compare(run_conversion(TV_ID, df, symbol=sym, tf="5", params=params, strategy_overrides={"commission_value": 0, "slippage": 0, "margin_long": 0, "margin_short": 0}), ref)
    return ok and len(ref) > p.get("minn", 8), f"{d} (got {len(ref)})"


BASE = dict(minr=3.0, maxr=20.0, bb=0.5, usehtf=True, usevol=True, ob=62.0, os=38.0, rr=1.5, maxt=2)


def check():
    df = bars(40000, seed=975, freq="5min")
    for k in ("open", "high", "low", "close"):
        df[k] = 4000 * (df[k] / 100) ** 0.1
    msgs, allok = [], True
    cases = (({}, dict(minn=5)),
             ({"Use HTF Bias Filter": False, "Use Volume Filter": False, "Max Range Size (pts)": 60.0, "Reward:Risk Ratio": 2.0}, dict(usehtf=False, usevol=False, maxr=60.0, rr=2.0)),
             ({"RSI Overbought (fade shorts)": 55.0, "RSI Oversold (fade longs)": 45.0, "Breakout Confirmation (pts)": 0.0, "Max Trades Per Session": 1, "Max Range Size (pts)": 35.0},
              dict(ob=55.0, os=45.0, bb=0.0, maxt=1, maxr=35.0)))
    for params, ov in cases:
        ok, m = one(df, params, {**BASE, **ov})
        allok &= ok
        msgs.append(m)
    return allok, " | ".join(msgs)
