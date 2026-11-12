"""Independent check — VuManChu WT Zero Cross V1.2.3 (iz6acv9B): hourly bars, process_orders_on_close (orders fill at the signal close), fixed quantity 10 on the pinelib side (the original sizes 2 % of equity), commission / slippage / margin off.
WaveTrend (esa / de / ci / wt1 = EMA, wt2 = SMA of wt1) on hlc3; the entry signal is wt1 crossing zero after the previous bar's running extreme since the last zero crossing reached the minimum swing; the take-profit circles are WT crosses beyond +-60. The script's own tracker (in-long / in-short flags, take-profit counter,
stop level from ATR / fixed % / both, reset whenever flat) is restated statement by statement, including the if / else-if priority chain; a tracked stop that the bar's low / high reaches closes at the signal close and an exit order with that stop is re-issued every bar. Partial closes take their percentage of the REMAINING position at the signal close.
Uses the quantity-aware bracket reference (indep.simulate_brackets, on_close), comparing quantities too.
Variants: defaults with a small swing; ATR + fixed stop ('Both') with a trend filter on and TP shares 30 / 40; stop loss disabled."""
import numpy as np

from indep import bars, compare_q, np_atr, np_ema, np_sma, run_conversion, simulate_brackets
from pinelib import SymbolInfo

TV_ID = "iz6acv9B"
QTY = 10.0


def one(df, params, p):
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    src = (h + l + c) / 3
    esa = np_ema(src, 9)
    de = np_ema(np.abs(src - esa), 9)
    with np.errstate(divide="ignore", invalid="ignore"):
        ci = (src - esa) / (0.015 * de)
    wt1 = np_ema(ci, 27)
    wt2 = np_sma(wt1, 3)
    ema = np_ema(c, p["emal"])
    atr = np_atr(h, l, c, 14)
    S = dict(lo=0.0, hi=0.0, il=False, ish=False, tpc=0, sl=np.nan)

    def stop(isl, ep, a):
        ats = ep - a * 2.0 if isl else ep + a * 2.0
        fx = ep * (1 - 1.0 / 100) if isl else ep * (1 + 1.0 / 100)
        if p["slt"] == "ATR":
            return ats
        if p["slt"] == "Fixed %":
            return fx
        return max(ats, fx) if isl else min(ats, fx)

    def orders(i, info):
        out = []
        w1p = wt1[i - 1] if i else np.nan
        w2p = wt2[i - 1] if i else np.nan
        lo_prev, hi_prev = S["lo"], S["hi"]
        with np.errstate(invalid="ignore"):
            S["lo"] = min(S["lo"], wt1[i]) if wt1[i] < 0 else 0.0
            S["hi"] = max(S["hi"], wt1[i]) if wt1[i] > 0 else 0.0
            ls = (w1p < 0 and wt1[i] >= 0) and lo_prev <= -p["sw"]
            ss = (w1p > 0 and wt1[i] <= 0) and hi_prev >= p["sw"]
            up = (w1p - w2p < 0) and (wt1[i] - wt2[i] >= 0)
            dn = (w1p - w2p > 0) and (wt1[i] - wt2[i] <= 0)
            buy_c = up and wt1[i] < -60 and wt2[i] < -60
            sell_c = dn and wt1[i] > 60 and wt2[i] > 60
            la = (not p["tf"]) or c[i] > ema[i]
            sa = (not p["tf"]) or c[i] < ema[i]
        if info["pos"] == 0:
            S.update(il=False, ish=False, tpc=0, sl=np.nan)
        if ls and la:
            out += [("close", "Short"), ("entry", "Long", 1, QTY)]
            S.update(il=True, ish=False, tpc=0, sl=stop(True, c[i], atr[i]) if p["sl"] else np.nan)
        elif ss and sa:
            out += [("close", "Long"), ("entry", "Short", -1, QTY)]
            S.update(ish=True, il=False, tpc=0, sl=stop(False, c[i], atr[i]) if p["sl"] else np.nan)
        elif ls and not la and S["ish"]:
            out.append(("close", "Short"))
            S.update(ish=False, tpc=0, sl=np.nan)
        elif ss and not sa and S["il"]:
            out.append(("close", "Long"))
            S.update(il=False, tpc=0, sl=np.nan)
        elif S["il"] and sell_c:
            if S["tpc"] < 5:
                out.append(("close", "Long", p["tp"][S["tpc"]]))
                S["tpc"] += 1
        elif S["ish"] and buy_c:
            if S["tpc"] < 5:
                out.append(("close", "Short", p["tp"][S["tpc"]]))
                S["tpc"] += 1
        if p["sl"] and not np.isnan(S["sl"]):
            if S["il"] and l[i] <= S["sl"]:
                out.append(("close", "Long"))
                S.update(il=False, tpc=0, sl=np.nan)
            if S["ish"] and h[i] >= S["sl"]:
                out.append(("close", "Short"))
                S.update(ish=False, tpc=0, sl=np.nan)
        if p["sl"] and not np.isnan(S["sl"]):
            if S["il"]:
                out.append(("exit", "Long SL", "Long", None, S["sl"], None))
            if S["ish"]:
                out.append(("exit", "Short SL", "Short", None, S["sl"], None))
        return out

    ref = simulate_brackets(o, h, l, c, orders, on_close=True)
    sym = SymbolInfo.make("NASDAQ:XYZ", "stock", qty_step=1e-9)
    ok, d = compare_q(run_conversion(TV_ID, df, symbol=sym, tf="60", params=params,
                                     strategy_overrides={"margin_long": 0, "margin_short": 0, "commission_value": 0, "slippage": 0, "default_qty_type": "fixed", "default_qty_value": QTY}), ref)
    return ok and len(ref) > 12, f"{d} (got {len(ref)})"


BASE = dict(emal=200, sw=10.0, tf=False, sl=True, slt="ATR", tp=(50.0,) * 5)


def check():
    df = bars(30000, seed=181, freq="1h")
    for k in ("open", "high", "low", "close"):
        df[k] = 100 * (df[k] / 100) ** 0.5
    msgs, allok = [], True
    cases = (({"Min Swing Before Cross": 5.0}, dict(sw=5.0)),
             ({"Min Swing Before Cross": 5.0, "Stop Loss Type": "Both", "Enable Trend Filter": True, "TP1 %": 30.0, "TP2 %": 40.0, "EMA Length": 100},
              dict(sw=5.0, emal=100, slt="Both", tf=True, tp=(30.0, 40.0, 50.0, 50.0, 50.0))),
             ({"Min Swing Before Cross": 5.0, "Enable Stop Loss": False}, dict(sw=5.0, sl=False)))
    for params, ov in cases:
        ok, m = one(df, params, {**BASE, **ov})
        allok &= ok
        msgs.append(m)
    return allok, " | ".join(msgs)
