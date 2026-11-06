"""Independent check — ICT 2022 NAS100 Smart Trend v2.0 (tDFJR5PV): 15-minute bars (24 h synthetic) on a US stock chart (60-minute periods counted from 09:30 New York), market orders at the next open, commission / slippage / margin off.
Killzones in Jerusalem time (Asian 02-05, London 09-12, NY 15:30-18:30, lunch 19-21); pivots (left-strict, right non-strict) reset when a killzone starts; a close through the latest pivot level with a displacement candle (body > multiple x SMA(20) of the previous bars' bodies), killzone, and the 60-minute close (mapped, lookahead off) above / below
its EMA (run over the mapped chart-bar series, seeded once 50 non-na values exist) enters at the next open; ATR(14) x multiplier (or the previous bar's extreme) gives the stop, R:R x that the target, both issued with the entry; cooldown, minimum stop (ticks of 0.01) and opentrades == 0 apply. Uses the pending-order reference broker (simulate_ord).
Variants: defaults; EMA 20, displacement 1.0, sweep required, cooldown 2, R:R 1.5; non-ATR stops (previous bar extreme, min SL 5 points), Asian + lunch killzones only, trend filter off, longs only."""
import numpy as np
import pandas as pd

from indep import bars, compare, np_atr, np_periods, np_security_lookahead_off, np_sma, run_conversion, simulate_ord
from pinelib import SymbolInfo

TV_ID = "tDFJR5PV"


def ema_na(x, n):
    out = np.full(len(x), np.nan)
    idx = np.flatnonzero(~np.isnan(x))
    if len(idx) < n:
        return out
    s = idx[0] + n - 1
    out[s] = x[idx[0]:s + 1].mean()
    k = 2.0 / (n + 1)
    for i in range(s + 1, len(x)):
        out[i] = k * x[i] + (1 - k) * out[i - 1]
    return out


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
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    sym = SymbolInfo.make("NASDAQ:XYZ", "stock", qty_step=1e-9)
    il = pd.to_datetime(df["time"], unit="ms", utc=True).dt.tz_convert("Asia/Jerusalem")
    tot = (il.dt.hour * 60 + il.dt.minute).to_numpy()
    kz = np.zeros(n, bool)
    if p["asian"]:
        kz |= (tot >= 120) & (tot < 300)
    if p["lon"]:
        kz |= (tot >= 540) & (tot < 720)
    if p["ny"]:
        kz |= (tot >= 930) & (tot < 1110)
    if p["lunch"]:
        kz |= (tot >= 1140) & (tot < 1260)
    pid, last_of = np_periods(df, 60)
    h1c = np_security_lookahead_off(c[last_of], pid, last_of)
    h1e = ema_na(h1c, p["el"])
    atr = np_atr(h, l, c, 14)
    body = np.abs(c - o)
    bprev = np.r_[np.nan, body[:-1]]
    avgb = np_sma(bprev, 20)
    ph, pl = piv(h, p["pl"], True), piv(l, p["pl"], False)
    S = dict(lh=np.nan, ll=np.nan, sh=False, sl=False, ltb=-999)

    def orders(i, pos):
        out = []
        sc = bool(kz[i]) and not (i > 0 and kz[i - 1])
        if sc:
            S["lh"] = S["ll"] = np.nan
            S["sh"] = S["sl"] = False
        if not np.isnan(ph[i]):
            S["lh"] = ph[i]
        if not np.isnan(pl[i]):
            S["ll"] = pl[i]
        with np.errstate(invalid="ignore"):
            if kz[i]:
                if not np.isnan(S["lh"]) and h[i] > S["lh"]:
                    S["sh"] = True
                if not np.isnan(S["ll"]) and l[i] < S["ll"]:
                    S["sl"] = True
            disp = avgb[i] > 0 and body[i] > avgb[i] * p["dm"]
            bull, bear = h1c[i] > h1e[i], h1c[i] < h1e[i]
            mb = (not np.isnan(S["lh"])) and c[i] > S["lh"] and disp and kz[i] and ((not p["rs"]) or S["sl"]) and (bull if p["trend"] else True)
            ms = (not np.isnan(S["ll"])) and c[i] < S["ll"] and disp and kz[i] and ((not p["rs"]) or S["sh"]) and (bear if p["trend"] else True)
            cd = i > S["ltb"] + p["cool"]
            sll = atr[i] * 1.5 if p["atrsl"] else abs(c[i] - l[i - 1]) if i else np.nan
            sls = atr[i] * 1.5 if p["atrsl"] else abs(h[i - 1] - c[i]) if i else np.nan
            lok = p["long"] and mb and cd and pos == 0
            sok = p["short"] and ms and cd and pos == 0
            lv, sv = sll / 0.01 >= p["minsl"], sls / 0.01 >= p["minsl"]
        if lok and lv:
            out.append(("entry", "LONG", 1, None, None))
            out.append(("exit", "LONG_X", "LONG", c[i] - sll, c[i] + sll * p["rr"]))
            S["ltb"], S["sl"], S["lh"] = i, False, np.nan
        if sok and sv:
            out.append(("entry", "SHORT", -1, None, None))
            out.append(("exit", "SHORT_X", "SHORT", c[i] + sls, c[i] - sls * p["rr"]))
            S["ltb"], S["sh"], S["ll"] = i, False, np.nan
        return out

    ref = simulate_ord(o, h, l, c, orders)
    ok, d = compare(run_conversion(TV_ID, df, symbol=sym, tf="15", params=params, strategy_overrides={"commission_value": 0, "slippage": 0, "margin_long": 0, "margin_short": 0}), ref)
    return ok and len(ref) > 8, f"{d} (got {len(ref)})"


BASE = dict(asian=True, lon=True, ny=True, lunch=True, el=50, pl=2, dm=1.3, rs=False, minsl=30.0, atrsl=True, cool=4, rr=2.0, trend=True, long=True, short=True)


def check():
    df = bars(30000, seed=19, freq="15min")
    for k in ("open", "high", "low", "close"):
        df[k] = 100 * (df[k] / 100) ** 0.5
    msgs, allok = [], True
    cases = (({}, {}),
             ({"EMA Period": 20, "Displacement Multiplier": 1.0, "Require Liquidity Sweep": True, "Cooldown Bars Between Trades": 2, "Risk:Reward Ratio": 1.5},
              dict(el=20, dm=1.0, rs=True, cool=2, rr=1.5)),
             ({"Use ATR-based SL (smarter)": False, "Min SL (Points for NAS100)": 5.0, "London Session": False, "NY Session": False, "Enable H1 EMA Trend Filter": False, "Enable SHORT trades": False},
              dict(atrsl=False, minsl=5.0, lon=False, ny=False, trend=False, short=False)))
    for params, ov in cases:
        ok, m = one(df, params, {**BASE, **ov})
        allok &= ok
        msgs.append(m)
    return allok, " | ".join(msgs)
