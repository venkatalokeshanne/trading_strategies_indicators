"""Independent check — AVS VWAP EMA Pullback Pro (8iyycJbD): 15-minute bars (24 h synthetic) on a stock-style symbol (New York time, VWAP restarting at 09:30), process_orders_on_close (orders fill at the signal close), fixed quantity 10 (the original uses the default quantity 1; scaled to see the 50 % pieces), commission / slippage / margin off.
Session = bar open time between 07:00 and 20:00 New York. Long: close over VWAP, EMA fast over slow, +DI over -DI, ADX >= minimum, low within the pullback % of the VWAP, close back over VWAP and fast EMA, RSI over the long level (short mirrored; a bar that signals both ways does nothing).
Entry while not already long (shorts: not already short) with two 50 % exit orders at 1R / 2R and the stop at min(VWAP, slow EMA) - ATR x mult (mirrored). Uses the quantity-aware bracket reference (indep.simulate_brackets, on_close), comparing quantities too.
Variants: defaults with loose ADX / RSI; deeper pullback, tighter stop and nearer targets."""
import numpy as np
import pandas as pd

from indep import bars, compare_q, np_atr, np_dmi, np_ema, np_rsi, np_vwap, run_conversion, simulate_brackets
from pinelib import SymbolInfo

TV_ID = "8iyycJbD"
QTY = 10.0


def one(df, params, p):
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    loc = pd.to_datetime(df["time"], unit="ms", utc=True).dt.tz_convert("America/New_York")
    mins = (loc.dt.hour * 60 + loc.dt.minute).to_numpy()
    sess = (mins >= 7 * 60) & (mins < 20 * 60)
    ef, es = np_ema(c, 20), np_ema(c, 50)
    rsi, atr = np_rsi(c, 14), np_atr(h, l, c, 14)
    vw = np_vwap(df, (h + l + c) / 3)
    pdi, mdi, adx = np_dmi(h, l, c, 14)
    with np.errstate(invalid="ignore"):
        bull = (c > vw) & (ef > es) & (pdi > mdi)
        bear = (c < vw) & (ef < es) & (mdi > pdi)
        ok = adx >= p["adx"]
        pl = bull & (l <= vw * (1 + p["pb"] / 100))
        ps = bear & (h >= vw * (1 - p["pb"] / 100))
        ls = sess & ok & pl & (c > vw) & (c > ef) & (rsi > p["rl"])
        ss = sess & ok & ps & (c < vw) & (c < ef) & (rsi < p["rs"])
    sym = SymbolInfo.make("NASDAQ:XYZ", "stock", qty_step=1e-9)

    def orders(i, info):
        out = []
        el, esh = ls[i] and not ss[i], ss[i] and not ls[i]
        pos = info["pos"]
        if el:
            sl = min(vw[i], es[i]) - atr[i] * p["sm"]
            risk = c[i] - sl
            if risk > 0 and pos <= 0:
                out += [("entry", "Long", 1, QTY), ("exit", "Long TP1", "Long", 50, sl, c[i] + risk * p["r1"]), ("exit", "Long TP2", "Long", 50, sl, c[i] + risk * p["r2"])]
        if esh:
            sl = max(vw[i], es[i]) + atr[i] * p["sm"]
            risk = sl - c[i]
            if risk > 0 and pos >= 0:
                out += [("entry", "Short", -1, QTY), ("exit", "Short TP1", "Short", 50, sl, c[i] - risk * p["r1"]), ("exit", "Short TP2", "Short", 50, sl, c[i] - risk * p["r2"])]
        return out

    ref = simulate_brackets(o, h, l, c, orders, on_close=True)
    ok_, d = compare_q(run_conversion(TV_ID, df, symbol=sym, tf="15", params=params,
                                      strategy_overrides={"margin_long": 0, "margin_short": 0, "commission_value": 0, "slippage": 0, "default_qty_type": "fixed", "default_qty_value": QTY}), ref)
    return ok_ and len(ref) > 12, f"{d} (got {len(ref)})"


BASE = dict(adx=18.0, pb=0.25, rl=52.0, rs=48.0, sm=1.2, r1=1.0, r2=2.0)


def check():
    df = bars(30000, seed=171, freq="15min")
    for k in ("open", "high", "low", "close"):
        df[k] = 100 * (df[k] / 100) ** 0.3
    msgs, allok = [], True
    cases = (({"Minimum ADX": 10.0, "RSI Long Level": 50.0, "RSI Short Level": 50.0, "VWAP Pullback %": 0.5}, dict(adx=10.0, rl=50.0, rs=50.0, pb=0.5)),
             ({"Minimum ADX": 10.0, "VWAP Pullback %": 1.0, "SL ATR Multiplier": 0.6, "TP1 RR": 0.7, "TP2 RR": 1.4}, dict(adx=10.0, pb=1.0, sm=0.6, r1=0.7, r2=1.4)))
    for params, ov in cases:
        ok, m = one(df, params, {**BASE, **ov})
        allok &= ok
        msgs.append(m)
    return allok, " | ".join(msgs)
