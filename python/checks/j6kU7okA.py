"""Independent check — Institutional Flow STRATEGY (j6kU7okA): 15-minute bars (24 h synthetic, price ~100, tick 0.01) of a stock-style symbol, market orders at the next open, default quantity 1, commission / slippage / margin off.
Break of structure = the close crossing over the last confirmed 10/10 pivot high (under the pivot low; pivot: left strictly, right not); a fair-value gap (low over the high two bars back / high under the low two bars back) within the last N bars (bars-since-gap <= N); trend filter SMA290 and EMA200. With the script's trade flag off a signal enters 1 unit;
the stop (fixed points x pip size, pip size = tick), target (RR x stop, plus tick buffer) and break-even trigger live in the script: each bar of an active flag a break-even touch moves the stop to the entry, a stop touch (checked first, also on the signal bar) or a target touch clears the flag and closes by id at the next open.
Uses the quantity-aware bracket reference (indep.simulate_brackets), comparing quantities too. Variants: SMA 50 / EMA 30, SL 10 pips, RR 1.5; MA filter off, FVG window 10, BE at 0.5R."""
import numpy as np

from indep import bars, compare_q, np_cross_over, np_cross_under, np_ema, np_sma, run_conversion, simulate_brackets
from pinelib import SymbolInfo

TV_ID = "j6kU7okA"


def pivots(x, k, high):
    n = len(x)
    out = np.full(n, np.nan)
    for i in range(2 * k, n):
        m = i - k
        c = x[m]
        lw, rw = x[m - k:m], x[m + 1:i + 1]
        ok = (np.all(c > lw) and np.all(c >= rw)) if high else (np.all(c < lw) and np.all(c <= rw))
        if ok:
            out[i] = c
    return out


def one(df, params, p):
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    sym = SymbolInfo.make("NASDAQ:XYZ", "stock", qty_step=1e-9)
    tick = sym.mintick
    sm, em = np_sma(c, p["sma"]), np_ema(c, p["ema"])
    ph, pl = pivots(h, 10, True), pivots(l, 10, False)
    lh = np.full(n, np.nan)
    ll = np.full(n, np.nan)
    a = b = np.nan
    for i in range(n):
        if not np.isnan(ph[i]):
            a = ph[i]
        if not np.isnan(pl[i]):
            b = pl[i]
        lh[i], ll[i] = a, b
    bb, sb = np_cross_over(c, lh), np_cross_under(c, ll)
    bf = np.r_[False, False, l[2:] > h[:-2]]
    sf = np.r_[False, False, h[2:] < l[:-2]]
    def since(f):
        out = np.full(n, np.nan)
        last = None
        for i in range(n):
            if f[i]:
                last = i
            out[i] = np.nan if last is None else i - last
        return out
    bs, ss_ = since(bf), since(sf)
    S = dict(act=False, bem=False, ent=np.nan, sl=np.nan, tp=np.nan)
    sld = p["pips"] * tick

    def orders(i, info):
        out = []
        with np.errstate(invalid="ignore"):
            tb = (not p["ma"]) or (c[i] > sm[i] and c[i] > em[i])
            tr = (not p["ma"]) or (c[i] < sm[i] and c[i] < em[i])
            ls = bool(bb[i]) and bs[i] <= p["fvg"] and tb
            sh = bool(sb[i]) and ss_[i] <= p["fvg"] and tr
        if (ls or sh) and not S["act"]:
            S.update(act=True, bem=False, ent=c[i])
            if ls:
                out.append(("entry", "Long", 1, 1.0))
                S["sl"], S["tp"] = c[i] - sld, c[i] + sld * p["rr"]
            else:
                out.append(("entry", "Short", -1, 1.0))
                S["sl"], S["tp"] = c[i] + sld, c[i] - sld * p["rr"]
        if S["act"]:
            il = S["tp"] > S["sl"]
            if p["be"] and not S["bem"]:
                trig = S["ent"] + sld * p["ber"] if il else S["ent"] - sld * p["ber"]
                if (il and h[i] >= trig) or (not il and l[i] <= trig):
                    S["sl"], S["bem"] = S["ent"], True
            if (il and l[i] <= S["sl"]) or (not il and h[i] >= S["sl"]):
                S["act"] = False
                out += [("close", "Long"), ("close", "Short")]
            elif (il and h[i] >= S["tp"]) or (not il and l[i] <= S["tp"]):
                S["act"] = False
                out += [("close", "Long"), ("close", "Short")]
        return out

    ref = simulate_brackets(o, h, l, c, orders)
    ok, d = compare_q(run_conversion(TV_ID, df, symbol=sym, tf="15", params=params,
                                     strategy_overrides={"margin_long": 0, "margin_short": 0, "commission_value": 0, "slippage": 0}), ref)
    return ok and len(ref) > 12, f"{d} (got {len(ref)})"


BASE = dict(sma=290, ema=200, ma=True, fvg=5, pips=20.0, rr=2.0, be=True, ber=1.0)


def check():
    df = bars(60000, seed=601, freq="15min")
    for k in ("open", "high", "low", "close"):
        df[k] = 100 * (df[k] / 100) ** 0.3
    msgs, allok = [], True
    cases = (({"SMA Length": 50, "EMA Length": 30, "Fixed SL (Pips/Points)": 10.0, "Risk:Reward Ratio": 1.5}, dict(sma=50, ema=30, pips=10.0, rr=1.5)),
             ({"Enable MA Filter": False, "FVG Lookback Window": 10, "Trigger BE at RR": 0.5, "Fixed SL (Pips/Points)": 50.0}, dict(ma=False, fvg=10, ber=0.5, pips=50.0)))
    for params, ov in cases:
        ok, m = one(df, params, {**BASE, **ov})
        allok &= ok
        msgs.append(m)
    return allok, " | ".join(msgs)
