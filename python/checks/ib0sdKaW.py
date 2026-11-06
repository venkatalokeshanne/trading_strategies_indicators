"""Independent check — Katana V5 Pro FVG 50% Model (ib0sdKaW): 15-minute bars, process_orders_on_close, one position, fixed-quantity sizing, or risk-based sizing in the second variant (the quantity does not change the trade list). Bullish signal bar: low > high[2], close > open, range >= ATR14 x 1.0, close > EMA200, RSI14 >= 50, inside 08:00-18:00 UTC. While flat with no setup it arms a setup: swing range = [lowest low of 20 bars, this bar's high]; entry 50 %, stop 25 %, target 75 % of it (or 1R / 1.5R / 2R of the entry-stop distance), requiring range > mintick and a stop distance >= 3 (price). The setup expires when more than 10 bars old; the first bar (the arming bar included) whose range touches the entry level enters at its CLOSE and issues the stop / target, working from the next bar. Short mirrored (range = [this low, highest high of 20], RSI <= 50, close < EMA200). Variants: default, 1.5R target with a minimum stop of 1 and no session / trend filters, longs only with 2R.
Margin off on the pinelib side."""
import numpy as np
import pandas as pd

from indep import bars, compare, np_atr, np_ema, np_rsi, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "ib0sdKaW"


def one(df, params, tp_mode, mins, sess, trend, rsif, longs, shorts, disp=True):
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    atr, ema, rsi = np_atr(h, l, c, 14), np_ema(c, 200), np_rsi(c, 14)
    t = pd.to_datetime(df["time"], unit="ms", utc=True)
    m = (t.dt.hour * 60 + t.dt.minute).to_numpy()
    ins = (m >= 480) & (m < 1080)
    lo20 = pd.Series(l).rolling(20).min().to_numpy()
    hi20 = pd.Series(h).rolling(20).max().to_numpy()
    S = dict(act=False, side="", bar=-1, e=np.nan, s=np.nan, tp=np.nan)
    lev = {}

    def orders(i, pos):
        out = []
        if i < 2:
            return out
        with np.errstate(invalid="ignore"):
            vd = (not disp) or (h[i] - l[i] >= atr[i] * 1.0)
            ok_s = (not sess) or ins[i]
            bull = l[i] > h[i - 2] and c[i] > o[i] and vd and ((not trend) or c[i] > ema[i]) and ((not rsif) or rsi[i] >= 50) and ok_s
            bear = h[i] < l[i - 2] and c[i] < o[i] and vd and ((not trend) or c[i] < ema[i]) and ((not rsif) or rsi[i] <= 50) and ok_s
        if S["act"] and pos == 0 and i - S["bar"] > 10:
            S["act"] = False
        if pos != 0:
            S["act"] = False
        can = pos == 0 and not S["act"]
        if not np.isnan(lo20[i]):
            rg = h[i] - lo20[i]
            le, ls, lk = lo20[i] + rg * 0.5, lo20[i] + rg * 0.25, lo20[i] + rg * 0.75
            rk = abs(le - ls)
            ltp = {"k": lk, "1": le + rk, "1.5": le + rk * 1.5, "2": le + rk * 2}[tp_mode]
            vl = rg > 0.01 and ls < le and ltp > le and (mins <= 0 or rk >= mins)
            if longs and can and bull and vl:
                S.update(act=True, side="L", bar=i, e=le, s=ls, tp=ltp)
            srg = hi20[i] - l[i]
            se, ss, sk = hi20[i] - srg * 0.5, hi20[i] - srg * 0.25, hi20[i] - srg * 0.75
            sr = abs(ss - se)
            stp = {"k": sk, "1": se - sr, "1.5": se - sr * 1.5, "2": se - sr * 2}[tp_mode]
            vs = srg > 0.01 and ss > se and stp < se and (mins <= 0 or sr >= mins)
            if shorts and can and bear and vs:
                S.update(act=True, side="S", bar=i, e=se, s=ss, tp=stp)
        if S["act"] and pos == 0 and l[i] <= S["e"] <= h[i]:
            out.append(("entry", 1 if S["side"] == "L" else -1))
            lev[i] = (S["s"], S["tp"])
            S["act"] = False
        return out

    stop = lambda i, pos, ep, eb: lev[eb][0] if eb in lev else None
    tgt = lambda i, pos, ep, eb: lev[eb][1] if eb in lev else None
    ref = simulate(o, h, l, c, orders, stop=stop, target=tgt, on_close=True)
    sym = SymbolInfo.make("OANDA:XAUUSD", "forex", mintick=0.01, qty_step=1e-9)
    ok, d = compare(run_conversion(TV_ID, df, symbol=sym, tf="15", params=dict({"Position sizing mode": "Fixed Qty"}, **params), strategy_overrides={"margin_long": 0, "margin_short": 0}), ref)
    return ok and len(ref) > 10, f"{d} (got {len(ref)})"


def check():
    df = bars(20000, seed=606, freq="15min")
    msgs, allok = [], True
    cases = (({}, ("k", 3.0, True, True, True, True, True)),
             ({"Position sizing mode": "Risk Based", "Take profit mode": "1.5R", "Minimum stop distance in price": 1.0, "Use session filter": False, "Use EMA trend filter": False}, ("1.5", 1.0, False, False, True, True, True)),
             ({"Take profit mode": "2R", "Allow shorts": False, "Use RSI filter": False, "Minimum stop distance in price": 1.0}, ("2", 1.0, True, True, False, True, False)))
    for params, args in cases:
        ok, m = one(df, params, *args)
        allok &= ok
        msgs.append(m)
    return allok, " | ".join(msgs)
