"""Independent check — AI MES Globex Overnight Strategy (O1xDXgrx): 5-minute bars (24 h synthetic, price ~4000) on a US stock chart (HTF periods counted from 09:30 New York), 1 contract, market orders at the next open, margin / commission / slippage off. 18:00-18:30 ET builds the range, locked when the trading part starts; the trading condition is `clock >= 18:30 and (clock < 09:30 or clock >= 18:00)` (so only the evening part is traded); outside the 08:15-08:45 blackout, flat and under the session limit, a range breakout, a pivot-break trend entry (HTF EMA(21) bias with lookahead off, RSI, volume) or a fade enters at the next open; stop = the wider of pivot +/- buffer and the ATR floor (ATR stop when no pivot), target = R:R x risk or the range midpoint for a pure fade; exit issued while open; everything closes after the sessions end. Uses the pending-order reference broker (simulate_ord).
Variants: defaults; no HTF / volume filters, range up to 60 and R:R 2; RSI limits relaxed, buffers 0, max 1 trade."""
import numpy as np
import pandas as pd

from indep import bars, compare, np_atr, np_ema, np_periods, np_rsi, np_security_lookahead_off, np_sma, run_conversion, simulate_ord
from pinelib import SymbolInfo

TV_ID = "O1xDXgrx"


def piv(x, ln, high):
    out = np.full(len(x), np.nan)
    for i in range(2 * ln, len(x)):
        w = x[i - 2 * ln:i + 1]
        ctr = w[ln]
        a, b = w[:ln], w[ln + 1:]
        if (high and (a < ctr).all() and (b <= ctr).all()) or ((not high) and (a > ctr).all() and (b >= ctr).all()):
            out[i] = ctr
    return out


def one(df, params, p):
    o, h, l, c, v = (df[k].to_numpy() for k in ("open", "high", "low", "close", "volume"))
    n = len(c)
    sym = SymbolInfo.make("NASDAQ:XYZ", "stock", qty_step=1e-9)
    ny = pd.to_datetime(df["time"], unit="ms", utc=True).dt.tz_convert("America/New_York")
    et = (ny.dt.hour * 100 + ny.dt.minute).to_numpy()
    pid, last_of = np_periods(df, 60)
    htf = np_security_lookahead_off(np_ema(c[last_of], 21), pid, last_of)
    ph, pl = piv(h, 4, True), piv(l, 4, False)
    rsi = np_rsi(c, 14)
    atr = np_atr(h, l, c, 14)
    vavg = np_sma(v, 20)
    S = dict(st=0, rh=np.nan, rl=np.nan, lh=np.nan, ll=np.nan, mid=np.nan, lph=np.nan, lpl=np.nan, es=np.nan, et=np.nan)
    nn = lambda x: None if np.isnan(x) else x

    def zones(t):
        ib = 1800 <= t < 1830
        ig = (t >= 1830) and (t < 930 or t >= 1800)
        return ib, ig

    def orders(i, pos):
        out = []
        t = et[i]
        ib, ig = zones(t)
        iany = ib or ig
        ib1, ig1 = zones(et[i - 1]) if i else (False, False)
        iany1 = ib1 or ig1
        blk = p["news"] and 815 <= t < 845
        ns = ig and not ig1
        if ns:
            S["st"] = 0
        if ib:
            S["rh"] = h[i] if np.isnan(S["rh"]) else max(S["rh"], h[i])
            S["rl"] = l[i] if np.isnan(S["rl"]) else min(S["rl"], l[i])
        if ns:
            S["lh"], S["ll"], S["mid"] = S["rh"], S["rl"], (S["rh"] + S["rl"]) / 2
            S["rh"] = S["rl"] = np.nan
        lh, ll = S["lh"], S["ll"]
        if not np.isnan(ph[i]):
            S["lph"] = ph[i]
        if not np.isnan(pl[i]):
            S["lpl"] = pl[i]
        c1 = c[i - 1] if i else np.nan
        with np.errstate(invalid="ignore"):
            rsz = np.nan if (np.isnan(lh) or np.isnan(ll)) else lh - ll
            valid = (not np.isnan(rsz)) and p["minr"] <= rsz <= p["maxr"]
            hl = (not p["usehtf"]) or c[i] > htf[i]
            hs = (not p["usehtf"]) or c[i] < htf[i]
            vb = (not p["usevol"]) or v[i] > vavg[i] * 1.3
            vf = (not p["usevol"]) or v[i] > vavg[i] * 0.7
            pbh = not np.isnan(S["lph"]) and c[i] > S["lph"] and c1 <= S["lph"]
            pbl = not np.isnan(S["lpl"]) and c[i] < S["lpl"] and c1 >= S["lpl"]
            rbl = valid and c[i] > lh + p["bb"] and c1 <= lh + p["bb"] and rsi[i] > p["rbmin"] and vb and hl
            rbs = valid and c[i] < ll - p["bb"] and c1 >= ll - p["bb"] and rsi[i] < p["rbmax"] and vb and hs
            tl = pbh and c[i] > htf[i] and rsi[i] > p["rbmin"] and vb
            ts = pbl and c[i] < htf[i] and rsi[i] < p["rbmax"] and vb
            bkl, bks = rbl or tl, rbs or ts
            tgh = h[i] >= lh - p["fb"]
            tgl = l[i] <= ll + p["fb"]
            fs = valid and tgh and c[i] < lh and c1 >= lh and rsi[i] > p["ob"] and vf and hs
            fl = valid and tgl and c[i] > ll and c1 <= ll and rsi[i] < p["os"] and vf and hl
            under = S["st"] < p["maxt"]
            lc = bool(ig and under and pos == 0 and (not blk) and (bkl or fl))
            sc = bool(ig and under and pos == 0 and (not blk) and (bks or fs))
            als, ass = c[i] - atr[i] * 2.0, c[i] + atr[i] * 2.0
            pls = als if np.isnan(S["lpl"]) else S["lpl"] - p["buf"]
            pss = ass if np.isnan(S["lph"]) else S["lph"] + p["buf"]
            lstop = np.nan if (np.isnan(pls) or np.isnan(als)) else min(pls, als)
            sstop = np.nan if (np.isnan(pss) or np.isnan(ass)) else max(pss, ass)
            ltgt = S["mid"] if (fl and not bkl) else c[i] + (c[i] - lstop) * p["rr"]
            stgt = S["mid"] if (fs and not bks) else c[i] - (sstop - c[i]) * p["rr"]
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


BASE = dict(minr=3.0, maxr=25.0, bb=0.75, fb=1.0, usehtf=True, usevol=True, ob=65.0, os=35.0, rbmin=52.0, rbmax=48.0, rr=1.5, buf=2.0, maxt=2, news=True)


def check():
    df = bars(40000, seed=2020, freq="5min")
    for k in ("open", "high", "low", "close"):
        df[k] = 4000 * (df[k] / 100) ** 0.1
    msgs, allok = [], True
    cases = (({}, dict(minn=5)),
             ({"Use HTF Bias Filter": False, "Use Volume Filter": False, "Max Range Size (pts)": 60.0, "Reward:Risk Ratio": 2.0}, dict(usehtf=False, usevol=False, maxr=60.0, rr=2.0)),
             ({"RSI Overbought (fade threshold)": 55.0, "RSI Oversold (fade threshold)": 45.0, "Breakout Confirmation (pts)": 0.0, "Stop Buffer beyond range (pts)": 0.0,
               "Max Trades Per Session": 1, "Max Range Size (pts)": 40.0},
              dict(ob=55.0, os=45.0, bb=0.0, buf=0.0, maxt=1, maxr=40.0)))
    for params, ov in cases:
        ok, m = one(df, params, {**BASE, **ov})
        allok &= ok
        msgs.append(m)
    return allok, " | ".join(msgs)
