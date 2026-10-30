"""Independent check — AI MES Structure Break Strategy (AzGi4Rwo): 5-minute bars (24 h synthetic, price ~4000) on a US stock chart (periods counted from 09:30 New York), 1 contract, market orders at the next open, margin / commission / slippage off. Morning 09:30-11:30 and afternoon 13:30-15:30 ET windows (a new window when the clock enters one; at most N trades per window). A close through the last confirmed pivot high (left-strict pivots of lookback 3) with the close above the higher-timeframe EMA(21) (period closes, lookahead off), RSI > midline and volume above its average x multiplier, while flat, enters at the next open (short mirrored); the stop is a buffer beyond the last opposite pivot and the target R:R times the risk from the signal close; the exit is issued while the position is open at script time; everything is closed on the bar after a session ends. Uses the pending-order reference broker (simulate_ord).
Variants: defaults; HTF 30 minutes with EMA 10, pivot lookback 2, R:R 2 and a morning session only; max 1 trade per window, RSI midline 55 / volume multiplier 1.0."""
import numpy as np
import pandas as pd

from indep import bars, compare, np_ema, np_periods, np_rsi, np_security_lookahead_off, np_sma, run_conversion, simulate_ord
from pinelib import SymbolInfo

TV_ID = "AzGi4Rwo"


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
    pc = c[last_of]
    htf = np_security_lookahead_off(np_ema(pc, p["hlen"]), pid, last_of)
    ph, pl = piv(h, p["pl"], True), piv(l, p["pl"], False)
    rsi = np_rsi(c, 14)
    vavg = np_sma(v, 20)
    s1 = (930, 1130)
    s2 = (1330, 1530)
    S = dict(lh=np.nan, ll=np.nan, wt=0, es=np.nan, et=np.nan, prev_in=None)
    nn = lambda x: None if np.isnan(x) else x

    def orders(i, pos):
        out = []
        t, t1 = et[i], (et[i - 1] if i else np.nan)
        inm = p["u1"] and s1[0] <= t < s1[1]
        ina = p["u2"] and s2[0] <= t < s2[1]
        ins = inm or ina
        with np.errstate(invalid="ignore"):
            pm = p["u1"] and (t1 < s1[0] or t1 >= s1[1]) and inm
            pa = p["u2"] and (t1 < s2[0] or t1 >= s2[1]) and ina
        if pm or pa:
            S["wt"] = 0
        under = S["wt"] < p["maxt"]
        if not np.isnan(ph[i]):
            S["lh"] = ph[i]
        if not np.isnan(pl[i]):
            S["ll"] = pl[i]
        with np.errstate(invalid="ignore"):
            bh = not np.isnan(S["lh"]) and c[i] > S["lh"] and (c[i - 1] if i else np.nan) <= S["lh"]
            bl = not np.isnan(S["ll"]) and c[i] < S["ll"] and (c[i - 1] if i else np.nan) >= S["ll"]
            hv = v[i] > vavg[i] * p["vm"]
            lc = bool(bh and c[i] > htf[i] and rsi[i] > p["rm"] and hv and ins and under and pos == 0)
            sc = bool(bl and c[i] < htf[i] and rsi[i] < p["rm"] and hv and ins and under and pos == 0)
        ls = S["ll"] - p["buf"]
        ss = S["lh"] + p["buf"]
        lt = c[i] + (c[i] - ls) * p["rr"]
        stt = c[i] - (ss - c[i]) * p["rr"]
        if pos == 0:
            S["es"] = S["et"] = np.nan
        if lc:
            S["es"], S["et"] = ls, lt
            out.append(("entry", "Long", 1, None, None))
            S["wt"] += 1
        if sc:
            S["es"], S["et"] = ss, stt
            out.append(("entry", "Short", -1, None, None))
            S["wt"] += 1
        if pos > 0:
            out.append(("exit", "Long Exit", "Long", nn(S["es"]), nn(S["et"])))
        if pos < 0:
            out.append(("exit", "Short Exit", "Short", nn(S["es"]), nn(S["et"])))
        if S["prev_in"] is not None and S["prev_in"] and not ins:
            out.append(("close_all",))
        S["prev_in"] = ins
        return out

    ref = simulate_ord(o, h, l, c, orders)
    ok, d = compare(run_conversion(TV_ID, df, symbol=sym, tf="5", params=params, strategy_overrides={"commission_value": 0, "slippage": 0, "margin_long": 0, "margin_short": 0}), ref)
    return ok and len(ref) > 8, f"{d} (got {len(ref)})"


BASE = dict(htf=15, hlen=21, pl=3, rm=50.0, vm=1.3, rr=1.5, buf=1.0, maxt=2, u1=True, u2=True)


def check():
    df = bars(40000, seed=135, freq="5min")
    for k in ("open", "high", "low", "close"):
        df[k] = 4000 * (df[k] / 100) ** 0.1
    msgs, allok = [], True
    cases = (({}, {}),
             ({"HTF Timeframe": "30", "HTF EMA Length": 10, "Pivot Lookback (bars each side)": 2, "Reward:Risk Ratio": 2.0, "Use Afternoon Session": False},
              dict(htf=30, hlen=10, pl=2, rr=2.0, u2=False)),
             ({"Max Trades Per Session Window": 1, "RSI Midline": 55.0, "Volume Multiplier": 1.0}, dict(maxt=1, rm=55.0, vm=1.0)))
    for params, ov in cases:
        ok, m = one(df, params, {**BASE, **ov})
        allok &= ok
        msgs.append(m)
    return allok, " | ".join(msgs)
