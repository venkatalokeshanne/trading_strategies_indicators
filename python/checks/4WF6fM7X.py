"""Independent check — Naked K 5min Sniper (4WF6fM7X): 5-minute bars, market orders at the next open, fixed quantity 10 on the pinelib side (the original sizes 100 % of equity), commission / slippage / margin off.
Trend = close vs SMA; near support / resistance = low <= lowest low(lookback) x 1.002 / high >= highest high x 0.998; pin bars (shadow >= 2 x body, other shadow <= 0.3 x body, range over half the ATR) or engulfing candles; close beyond the previous high / low; volume >= 1.2 x its 5-bar SMA; cooldown of N bars after the last signal (bar index difference <= N blocks).
Each entry issues stop = previous extreme -/+ ATR x mult and limit = close +/- RR x risk. Both sides' exit orders carry the same id "TP/SL". Uses the quantity-aware bracket reference (indep.simulate_brackets), comparing quantities too.
Variants: defaults; no volume filter, cooldown 0, RR 1; lookback 4, SMA 5, ATR mult 1.2, RR 2."""
import numpy as np

from indep import bars, compare_q, np_atr, np_sma, run_conversion, simulate_brackets
from pinelib import SymbolInfo

TV_ID = "4WF6fM7X"
QTY = 10.0


def one(df, params, p):
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    v = df["volume"].to_numpy()
    n = len(c)
    sma = np_sma(c, p["sma"])
    atr = np_atr(h, l, c, 7)
    va = np_sma(v, 5)
    lb = p["lb"]
    rl = np.array([l[i - lb + 1:i + 1].min() if i >= lb - 1 else np.nan for i in range(n)])
    rh = np.array([h[i - lb + 1:i + 1].max() if i >= lb - 1 else np.nan for i in range(n)])
    S = dict(last=None)

    def orders(i, info):
        if i < 1:
            return []
        out = []
        with np.errstate(invalid="ignore"):
            body = abs(o[i] - c[i])
            ls, us = min(o[i], c[i]) - l[i], h[i] - max(o[i], c[i])
            rng = h[i] - l[i]
            bpin = ls >= 2 * body and us <= 0.3 * body and rng > atr[i] * 0.5
            spin = us >= 2 * body and ls <= 0.3 * body and rng > atr[i] * 0.5
            beng = o[i - 1] > c[i - 1] and c[i] > o[i] and c[i] > o[i - 1] and o[i] < c[i - 1]
            seng = o[i - 1] < c[i - 1] and c[i] < o[i] and c[i] < o[i - 1] and o[i] > c[i - 1]
            vol = (not p["vf"]) or v[i] >= va[i] * 1.2
            lsig = c[i] > sma[i] and l[i] <= rl[i] * 1.002 and (bpin or beng) and c[i] > h[i - 1] and vol
            ssig = c[i] < sma[i] and h[i] >= rh[i] * 0.998 and (spin or seng) and c[i] < l[i - 1] and vol
        cool = S["last"] is not None and (i - S["last"]) <= p["cd"]
        if lsig and not cool:
            sl = l[i - 1] - p["am"] * atr[i]
            tp = c[i] + p["rr"] * (c[i] - sl)
            out += [("entry", "Long", 1, QTY), ("exit", "TP/SL", "Long", None, sl, tp)]
            S["last"] = i
        if ssig and not cool:
            sl = h[i - 1] + p["am"] * atr[i]
            tp = c[i] - p["rr"] * (sl - c[i])
            out += [("entry", "Short", -1, QTY), ("exit", "TP/SL", "Short", None, sl, tp)]
            S["last"] = i
        return out

    ref = simulate_brackets(o, h, l, c, orders)
    sym = SymbolInfo.make("NASDAQ:XYZ", "stock", qty_step=1e-9)
    ok, d = compare_q(run_conversion(TV_ID, df, symbol=sym, tf="5", params=params,
                                     strategy_overrides={"margin_long": 0, "margin_short": 0, "commission_value": 0, "slippage": 0, "default_qty_type": "fixed", "default_qty_value": QTY}), ref)
    return ok and len(ref) > 12, f"{d} (got {len(ref)})"


BASE = dict(lb=6, sma=9, am=1.8, rr=1.5, vf=True, cd=3)


def check():
    df = bars(40000, seed=251, freq="5min")
    for k in ("open", "high", "low", "close"):
        df[k] = 100 * (df[k] / 100) ** 0.3
    msgs, allok = [], True
    cases = (({}, {}),
             ({"启用成交量过滤（需有成交量数据）": False, "交易冷却期（K线数）": 0, "止盈风险回报比": 1.0}, dict(vf=False, cd=0, rr=1.0)),
             ({"支撑/阻力回溯K线数": 4, "趋势SMA周期": 5, "止损ATR倍数": 1.2, "止盈风险回报比": 2.0}, dict(lb=4, sma=5, am=1.2, rr=2.0)))
    for params, ov in cases:
        ok, m = one(df, params, {**BASE, **ov})
        allok &= ok
        msgs.append(m)
    return allok, " | ".join(msgs)
