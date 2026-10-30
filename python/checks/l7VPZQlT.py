"""Independent check — Liquidity Entry Logic v14 (l7VPZQlT): 15-minute bars (24 h synthetic, price ~100) of a stock-style symbol (New York time; 4-hour periods from 09:30), market orders at the next open, fixed quantity 10 on the pinelib side (the original sizes 100 % of equity), commission / slippage / margin off.
Asian high / low from the session's first bar (18:00 - 24:00 NY bar open times) and kept afterwards; sweep wick > 45 % of the bar with the bar closing in the sweep colour; bull / bear score = 2 x sweep + impulse (1.3 x average range) + stacked chart EMAs (close vs EMA321 vs EMA440) + the 4-hour EMA321 vs EMA440 (period closes, lookahead off) + the 09:30 - 12:00 window + trending (|close - close[10]| > 1.2 x SMA20 of the range) + not choppy (SMA10 of that range under its SMA50).
A score at or above the threshold (or 4 with 'only A+' off) enters (reversal); one exit order per side with the ATR stop / target of the signal bar is re-issued every bar. Uses the quantity-aware bracket reference (indep.simulate_brackets), comparing quantities too. Variants: only-A+ off; threshold 5."""
import numpy as np
import pandas as pd

from indep import bars, compare_q, np_atr, np_ema, np_periods, np_security_lookahead_off, np_sma, run_conversion, simulate_brackets
from pinelib import SymbolInfo

TV_ID = "l7VPZQlT"
QTY = 10.0


def one(df, params, p):
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    ny = pd.to_datetime(df["time"], unit="ms", utc=True).dt.tz_convert("America/New_York")
    mins = (ny.dt.hour * 60 + ny.dt.minute).to_numpy()
    asia, nys = mins >= 1080, (mins >= 570) & (mins < 720)
    me, se = np_ema(c, 321), np_ema(c, 440)
    pid, last_of = np_periods(df, 240)
    pc = c[last_of]
    hm = np_security_lookahead_off(np_ema(pc, 321), pid, last_of)
    hs = np_security_lookahead_off(np_ema(pc, 440), pid, last_of)
    rs = np_sma(h - l, 20)
    ts = np.abs(c - np.r_[np.full(10, np.nan), c[:-10]])
    chop = np_sma(rs, 10) < np_sma(rs, 50)
    ar = np_sma(h - l, 10)
    atr = np_atr(h, l, c, 14)
    S = dict(ah=np.nan, al=np.nan, prev=False)

    def orders(i, info):
        out = []
        pos = info["pos"]
        if asia[i] and not S["prev"]:
            S["ah"], S["al"] = h[i], l[i]
        S["prev"] = bool(asia[i])
        if asia[i]:
            S["ah"], S["al"] = max(S["ah"], h[i]), min(S["al"], l[i])
        with np.errstate(invalid="ignore"):
            wick = h[i] - l[i]
            uw, lw = h[i] - max(o[i], c[i]), min(o[i], c[i]) - l[i]
            sh = h[i] > S["ah"] and uw > wick * 0.45 and c[i] < o[i]
            sl_ = l[i] < S["al"] and lw > wick * 0.45 and c[i] > o[i]
            bi = c[i] > o[i] and wick > ar[i] * 1.3
            si = c[i] < o[i] and wick > ar[i] * 1.3
            trending = ts[i] > rs[i] * 1.2
            tb = c[i] > me[i] and me[i] > se[i]
            tr = c[i] < me[i] and me[i] < se[i]
            bs = (2 if sl_ else 0) + bi + tb + (hm[i] > hs[i]) + nys[i] + trending + (not chop[i])
            ss = (2 if sh else 0) + si + tr + (hm[i] < hs[i]) + nys[i] + trending + (not chop[i])
        th = p["th"] if p["ap"] else 4
        lc, sc = bs >= th, ss >= th
        a = atr[i]
        lsl, ltp, ssl, stp = c[i] - a * 1.5, c[i] + a * 3.0, c[i] + a * 1.5, c[i] - a * 3.0
        if lc and pos <= 0:
            out.append(("entry", "Long", 1, QTY))
        if sc and pos >= 0:
            out.append(("entry", "Short", -1, QTY))
        nn = lambda x: None if np.isnan(x) else x
        out += [("exit", "L Exit", "Long", None, nn(lsl), nn(ltp)), ("exit", "S Exit", "Short", None, nn(ssl), nn(stp))]
        return out

    ref = simulate_brackets(o, h, l, c, orders)
    sym = SymbolInfo.make("NASDAQ:XYZ", "stock", qty_step=1e-9)
    ok, d = compare_q(run_conversion(TV_ID, df, symbol=sym, tf="15", params=params,
                                     strategy_overrides={"margin_long": 0, "margin_short": 0, "commission_value": 0, "slippage": 0, "default_qty_type": "fixed", "default_qty_value": QTY}), ref)
    return ok and len(ref) > 12, f"{d} (got {len(ref)})"


BASE = dict(th=6, ap=True)


def check():
    df = bars(120000, seed=611, freq="15min")
    for k in ("open", "high", "low", "close"):
        df[k] = 100 * (df[k] / 100) ** 0.3
    msgs, allok = [], True
    cases = (({"Only Take A+ Trades": False}, dict(ap=False)), ({"A+ Threshold (0–8)": 5, "Only Take A+ Trades": True}, dict(th=5)))
    for params, ov in cases:
        ok, m = one(df, params, {**BASE, **ov})
        allok &= ok
        msgs.append(m)
    return allok, " | ".join(msgs)
