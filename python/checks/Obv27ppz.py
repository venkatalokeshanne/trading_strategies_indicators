"""Independent check — RSI Divergence + EMA Filter (Obv27ppz): hourly bars of a stock-style symbol (mintick 0.01), market orders at the next open, fixed quantity 10 on the pinelib side (the original sizes 2 % of equity), commission / slippage / margin off.
Pivots (unique extreme over left / right bars) are paired with the RSI at the pivot bar (right bars back from the confirmation bar): higher price high with lower RSI = short signal; lower price low with higher RSI = long signal; optional overbought / oversold requirement on the earlier pivot's RSI; EMA filter. A signal while flat enters.
With R:R on, a stop and a limit around the signal close are issued with the entry; with the trailing option on, every bar of an open position re-issues a trailing stop whose activation and offset are both ATR x multiplier in ticks (so they follow the current ATR). Uses the quantity-aware bracket reference (indep.simulate_brackets), which also compares the closed quantities.
Variants: trailing multiplier 0.5 with the EMA filter off (the defaults leave too few trades); R:R stop / target with the trailing on and a looser pivot width, no EMA filter; OB/OS requirement with trailing off and R:R on."""
import numpy as np

from indep import bars, compare_q, np_atr, np_ema, np_rsi, run_conversion, simulate_brackets
from pinelib import SymbolInfo

TV_ID = "Obv27ppz"
QTY = 10.0


def pivots(x, lb, rb, high):
    n = len(x)
    out = np.full(n, np.nan)
    for i in range(lb + rb, n):
        m = i - rb
        win = x[m - lb:m + rb + 1]
        ext = win.max() if high else win.min()
        if x[m] == ext and (win == x[m]).sum() == 1:
            out[i] = x[m]
    return out


def one(df, params, p):
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    sym = SymbolInfo.make("NASDAQ:XYZ", "stock", qty_step=1e-9)
    tick = sym.mintick
    rsi, ema, atr = np_rsi(c, 14), np_ema(c, p["ema"]), np_atr(h, l, c, 14)
    ph, pl = pivots(h, p["lb"], p["rb"], True), pivots(l, p["lb"], p["rb"], False)
    S = dict(php=np.nan, phr=np.nan, lhp=np.nan, lhr=np.nan, plp=np.nan, plr=np.nan, llp=np.nan, llr=np.nan)

    def orders(i, info):
        r_at = rsi[i - p["rb"]] if i >= p["rb"] else np.nan
        if not np.isnan(ph[i]):
            S["php"], S["phr"], S["lhp"], S["lhr"] = S["lhp"], S["lhr"], ph[i], r_at
        if not np.isnan(pl[i]):
            S["plp"], S["plr"], S["llp"], S["llr"] = S["llp"], S["llr"], pl[i], r_at
        with np.errstate(invalid="ignore"):
            bear = (not np.isnan(ph[i])) and (not np.isnan(S["php"])) and S["lhp"] > S["php"] and S["lhr"] < S["phr"] and ((not p["obos"]) or S["phr"] >= 70)
            bull = (not np.isnan(pl[i])) and (not np.isnan(S["plp"])) and S["llp"] < S["plp"] and S["llr"] > S["plr"] and ((not p["obos"]) or S["plr"] <= 30)
            above = c[i] > ema[i]
            ls = bull and ((not p["filt"]) or above)
            ss = bear and ((not p["filt"]) or not above)
        out = []
        pos = info["pos"]
        if ls and pos == 0:
            out.append(("entry", "Long", 1, QTY))
            if p["rr"]:
                out.append(("exit", "Long Exit", "Long", None, c[i] - 1.5 * atr[i], c[i] + p["rrr"] * 1.5 * atr[i]))
        if ss and pos == 0:
            out.append(("entry", "Short", -1, QTY))
            if p["rr"]:
                out.append(("exit", "Short Exit", "Short", None, c[i] + 1.5 * atr[i], c[i] - p["rrr"] * 1.5 * atr[i]))
        tt = p["tm"] * atr[i] / tick
        if p["trail"] and pos > 0 and not np.isnan(tt):
            out.append(("exit", "Long Trail", "Long", None, None, None, tt, None, tt))
        if p["trail"] and pos < 0 and not np.isnan(tt):
            out.append(("exit", "Short Trail", "Short", None, None, None, tt, None, tt))
        return out

    ref = simulate_brackets(o, h, l, c, orders, tick=tick)
    ok, d = compare_q(run_conversion(TV_ID, df, symbol=sym, tf="60", params=params,
                                     strategy_overrides={"margin_long": 0, "margin_short": 0, "commission_value": 0, "slippage": 0, "default_qty_type": "fixed", "default_qty_value": QTY}), ref)
    return ok and len(ref) > 12, f"{d} (got {len(ref)})"


BASE = dict(lb=5, rb=5, ema=200, filt=True, obos=False, rr=False, rrr=2.0, trail=True, tm=2.0)


def check():
    df = bars(40000, seed=131, freq="1h")
    for k in ("open", "high", "low", "close"):
        df[k] = 100 * (df[k] / 100) ** 0.5
    msgs, allok = [], True
    cases = (({"Use EMA Trend Filter": False, "Trailing ATR Multiplier": 0.5}, dict(filt=False, tm=0.5)),
             ({"Use R:R Target/Stop": True, "Pivot Left Bars": 3, "Pivot Right Bars": 3, "Use EMA Trend Filter": False}, dict(rr=True, lb=3, rb=3, filt=False)),
             ({"Use Trailing ATR Stop": False, "Use R:R Target/Stop": True, "Require RSI in OB/OS at First Pivot": True, "Risk:Reward Ratio": 1.2, "Use EMA Trend Filter": False, "Pivot Left Bars": 3, "Pivot Right Bars": 2},
              dict(trail=False, rr=True, obos=True, rrr=1.2, filt=False, lb=3, rb=2)))
    for params, ov in cases:
        ok, m = one(df, params, {**BASE, **ov})
        allok &= ok
        msgs.append(m)
    return allok, " | ".join(msgs)
