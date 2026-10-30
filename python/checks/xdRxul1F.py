"""Independent check — AI MES London Open Breakout (xdRxul1F): 5-minute bars (24 h synthetic, price ~4000) on a US stock chart (HTF periods counted from 09:30 New York), 1 contract, market orders at the next open, margin / commission / slippage off. Pre-London window 02:30-03:00 ET builds a high / low locked at the first London bar (03:00-06:00 ET); inside London, flat and under the per-session trade limit, a close through the locked range (size >= minimum) or through the last confirmed pivot (left-strict, lookback 4), RSI floor / ceiling, volume surge and the HTF EMA(21) bias (period closes, lookahead off) enters at the next open; stop = the wider of pivot +/- buffer and the ATR floor (na pivot -> no levels), target = R:R x risk from the signal close; exit issued while the position is open; everything is closed on the bar after the sessions end. Uses the pending-order reference broker (simulate_ord).
Variants: defaults; HTF filter off, volume filter off, R:R 2, buffer 1; other windows (pre 01:30, London 02:00-05:00), HTF 30, min range 1, max 1 trade."""
import numpy as np
import pandas as pd

from indep import bars, compare, np_atr, np_ema, np_periods, np_rsi, np_security_lookahead_off, np_sma, run_conversion, simulate_ord
from pinelib import SymbolInfo

TV_ID = "xdRxul1F"


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
    pid, last_of = np_periods(df, p["htf"])
    htf = np_security_lookahead_off(np_ema(c[last_of], 21), pid, last_of)
    ph, pl = piv(h, 4, True), piv(l, 4, False)
    rsi = np_rsi(c, 14)
    atr = np_atr(h, l, c, 14)
    vavg = np_sma(v, 20)
    pre_t, lon_t, end_t = p["pre"], p["lon"], p["end"]
    S = dict(st=0, prh=np.nan, prl=np.nan, lh=np.nan, ll=np.nan, lph=np.nan, lpl=np.nan, es=np.nan, et=np.nan)
    nn = lambda x: None if np.isnan(x) else x

    def orders(i, pos):
        out = []
        t = et[i]
        ipre = pre_t <= t < lon_t
        ilon = lon_t <= t < end_t
        iany = ipre or ilon
        t1 = et[i - 1] if i else -1
        ilon1 = lon_t <= t1 < end_t
        iany1 = (pre_t <= t1 < lon_t) or ilon1
        ns = ilon and not ilon1
        if ns:
            S["st"] = 0
        if ipre:
            S["prh"] = h[i] if np.isnan(S["prh"]) else max(S["prh"], h[i])
            S["prl"] = l[i] if np.isnan(S["prl"]) else min(S["prl"], l[i])
        if ns:
            S["lh"], S["ll"] = S["prh"], S["prl"]
            S["prh"] = S["prl"] = np.nan
        rsz = np.nan if (np.isnan(S["lh"]) or np.isnan(S["ll"])) else S["lh"] - S["ll"]
        valid = (not np.isnan(rsz)) and rsz >= p["minr"]
        if not np.isnan(ph[i]):
            S["lph"] = ph[i]
        if not np.isnan(pl[i]):
            S["lpl"] = pl[i]
        c1 = c[i - 1] if i else np.nan
        with np.errstate(invalid="ignore"):
            bh = not np.isnan(S["lph"]) and c[i] > S["lph"] and c1 <= S["lph"]
            bl = not np.isnan(S["lpl"]) and c[i] < S["lpl"] and c1 >= S["lpl"]
            hv = (not p["usevol"]) or v[i] > vavg[i] * p["vm"]
            rbl = valid and c[i] > S["lh"] and c1 <= S["lh"]
            rbs = valid and c[i] < S["ll"] and c1 >= S["ll"]
            hl = (not p["usehtf"]) or c[i] > htf[i]
            hs = (not p["usehtf"]) or c[i] < htf[i]
            under = S["st"] < p["maxt"]
            lc = bool(ilon and under and pos == 0 and (rbl or bh) and rsi[i] >= p["rl"] and hv and hl)
            sc = bool(ilon and under and pos == 0 and (rbs or bl) and rsi[i] <= p["rs"] and hv and hs)
            pls = S["lpl"] - p["buf"]
            pss = S["lph"] + p["buf"]
            als, ass = c[i] - atr[i] * p["am"], c[i] + atr[i] * p["am"]
            lstop = np.nan if (np.isnan(pls) or np.isnan(als)) else min(pls, als)
            sstop = np.nan if (np.isnan(pss) or np.isnan(ass)) else max(pss, ass)
            ltgt = c[i] + (c[i] - lstop) * p["rr"]
            stgt = c[i] - (sstop - c[i]) * p["rr"]
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
    return ok and len(ref) > 8, f"{d} (got {len(ref)})"


BASE = dict(htf=60, pre=230, lon=300, end=600, minr=3.0, rl=45.0, rs=55.0, vm=1.2, usevol=True, usehtf=True, rr=1.5, buf=2.0, am=1.5, maxt=2)


def check():
    df = bars(40000, seed=864, freq="5min")
    for k in ("open", "high", "low", "close"):
        df[k] = 4000 * (df[k] / 100) ** 0.1
    msgs, allok = [], True
    cases = (({}, {}),
             ({"Use HTF Bias Filter": False, "Use Volume Filter": False, "Reward:Risk Ratio": 2.0, "Stop Buffer beyond pivot (pts)": 1.0}, dict(usevol=False, usehtf=False, rr=2.0, buf=1.0)),
             ({"Pre-London Range Start Hour (ET)": 1, "London Open Hour (ET)": 2, "London Close Hour (ET)": 5, "HTF Timeframe": "30", "Min Pre-London Range Size (pts)": 1.0, "Max Trades Per Session": 1},
              dict(pre=130, lon=200, end=500, htf=30, minr=1.0, maxt=1)))
    for params, ov in cases:
        ok, m = one(df, params, {**BASE, **ov})
        allok &= ok
        msgs.append(m)
    return allok, " | ".join(msgs)
