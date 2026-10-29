"""Independent check — L&L HTF Trend Cloud Strategy (7aRO3Qf1): 15-minute bars (24 h synthetic) on a US stock chart (higher-timeframe periods counted from 09:30 New York), market orders at the next open, commission / slippage / margin off, one unit.
HTF = 30 minutes in Auto mode for a 15-minute chart (or the manual one): EMA8/13/21/34 of the period closes, trend = EMA13, ATR = EMA8 of the period true range (first period high-low); stop_direction = 1 when the HTF close > trend + pct x ATR, -1 when below trend - pct x ATR, else the previous value (na until first set); all values lookahead off.
A direction change enters (long needs the EMA stack up and HTF close >= trend, short the mirror, unless alignment is off); an entry on the other side reverses; the chart close beyond the cloud line against the direction closes the trade; optional percent stop / target from the average entry price. Uses the pending-order reference broker (simulate_ord).
Variants: defaults; Tight mode, alignment off; Manual 60-minute HTF, Loose mode, bullish signals only with a 1% stop / 2% target; Net mode (bearish only), SL/TP 0.5% / 1%."""
import numpy as np

from indep import bars, compare, np_periods, np_security_lookahead_off, run_conversion, simulate_ord
from pinelib import SymbolInfo

TV_ID = "7aRO3Qf1"
ALEN = {"Tight": 60, "Normal": 80, "Loose": 100, "FOMC": 120, "Net": 140}


def ema_seed(x, n):
    out = np.full(len(x), np.nan)
    if len(x) < n:
        return out
    out[n - 1] = x[:n].mean()
    k = 2.0 / (n + 1)
    for i in range(n, len(x)):
        out[i] = k * x[i] + (1 - k) * out[i - 1]
    return out


def one(df, params, p):
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    sym = SymbolInfo.make("NASDAQ:XYZ", "stock", qty_step=1e-9)
    pid, last_of = np_periods(df, p["tf"])
    npd = pid[-1] + 1
    pc = c[last_of]
    ph = np.array([h[pid == k].max() for k in range(npd)])
    pl = np.array([l[pid == k].min() for k in range(npd)])
    tr = np.empty(npd)
    tr[0] = ph[0] - pl[0]
    for k in range(1, npd):
        tr[k] = max(ph[k] - pl[k], abs(ph[k] - pc[k - 1]), abs(pl[k] - pc[k - 1]))
    mp = lambda arr: np_security_lookahead_off(arr, pid, last_of)
    e8, e13, e21, e34 = (mp(ema_seed(pc, k)) for k in (8, 13, 21, 34))
    ch, atrh = mp(pc), mp(ema_seed(tr, 8))
    S = dict(sd=np.nan)
    pct = ALEN[p["mode"]] / 100.0

    def orders(i, pos, info):
        out = []
        with np.errstate(invalid="ignore"):
            up = e8[i] > e13[i] and e13[i] > e21[i] and e21[i] > e34[i]
            dn = e8[i] < e13[i] and e13[i] < e21[i] and e21[i] < e34[i]
            av = pct * atrh[i]
            isup, isdn = ch[i] > e13[i] + av, ch[i] < e13[i] - av
            prev = S["sd"]
            sd = 1.0 if isup else (-1.0 if isdn else prev)
            S["sd"] = sd
            sl = e13[i] - av if sd == 1 else (e13[i] + av if sd == -1 else prev)
            bc, rc = sd == 1 and prev == -1, sd == -1 and prev == 1
            tb = up and ch[i] >= e13[i]
            tr_ = dn and ch[i] <= e13[i]
            lc = bool(bc and tb) if p["align"] else bool(bc)
            sc = bool(rc and tr_) if p["align"] else bool(rc)
            if p["sig"] == "Bullish Only":
                sc = False
            elif p["sig"] == "Bearish Only":
                lc = False
            lx = bool(c[i] < sl and sd == 1)
            sx = bool(c[i] > sl and sd == -1)
        if lc:
            out.append(("entry", "Long", 1, None, None))
        if sc:
            out.append(("entry", "Short", -1, None, None))
        if lx and pos > 0:
            out.append(("close", "Long"))
        if sx and pos < 0:
            out.append(("close", "Short"))
        if p["sltp"]:
            if pos > 0:
                out.append(("exit", "Long Exit", "Long", info["ep"] * (1 - p["slp"] / 100), info["ep"] * (1 + p["tpp"] / 100)))
            if pos < 0:
                out.append(("exit", "Short Exit", "Short", info["ep"] * (1 + p["slp"] / 100), info["ep"] * (1 - p["tpp"] / 100)))
        return out

    ref = simulate_ord(o, h, l, c, orders)
    ok, d = compare(run_conversion(TV_ID, df, symbol=sym, tf="15", params=params, strategy_overrides={"commission_value": 0, "slippage": 0, "margin_long": 0, "margin_short": 0}), ref)
    return ok and len(ref) > 8, f"{d} (got {len(ref)})"


BASE = dict(tf=30, mode="Normal", align=True, sig="Both", sltp=False, slp=1.0, tpp=2.0)


def check():
    df = bars(20000, seed=8, freq="15min")
    for k in ("open", "high", "low", "close"):
        df[k] = 100 * (df[k] / 100) ** 0.5
    msgs, allok = [], True
    cases = (({}, {}),
             ({"Trend Mode": "Tight", "Require Trend Alignment": False}, dict(mode="Tight", align=False)),
             ({"HTF Mode": "Manual", "HTF Aggregation (Manual)": "60", "Trend Mode": "Loose", "Entry Signal": "Bullish Only", "Use Stop Loss & Take Profit": True},
              dict(tf=60, mode="Loose", sig="Bullish Only", sltp=True)),
             ({"Trend Mode": "Net", "Entry Signal": "Bearish Only", "Use Stop Loss & Take Profit": True, "Stop Loss (%)": 0.5, "Take Profit (%)": 1.0, "Require Trend Alignment": False},
              dict(mode="Net", sig="Bearish Only", sltp=True, slp=0.5, tpp=1.0, align=False)))
    for params, ov in cases:
        ok, m = one(df, params, {**BASE, **ov})
        allok &= ok
        msgs.append(m)
    return allok, " | ".join(msgs)
