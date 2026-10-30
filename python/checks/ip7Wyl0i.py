"""Independent check — CRMI v6 BETA REFINED (ip7Wyl0i): 15-minute bars (24 h synthetic, price ~100) of a stock-style symbol, fixed quantity (the 10 %-of-equity sizing replaced), orders at the bar's close (process_orders_on_close), commission / slippage off.
EMA stack (20/50/200), 34-EMA mid-line, ATR(14), the 60-minute close / EMA(50) bias (lookahead off), the efficiency-ratio chop filter, the 0..100 buy / sell score (stack 30, discount / premium 20, strong-body breakout 20, HTF bias 30) against the mode minimum, the ATR stop and R:R 1.5 target with the minimum reward : risk, the 0.5 ATR displacement, the re-entry after a loss in the same direction, and the exit order rules (none in LONG mode while the EMA trend supports the position, only after 5 bars in FAST mode) are restated bar by bar.
Uses the quantity-aware bracket reference (indep.simulate_brackets, on_close). Variants: HYBRID, FAST, LONG."""
import numpy as np
import pandas as pd

from indep import bars, compare_q, np_atr, np_ema, np_periods, np_security_lookahead_off, np_sma, run_conversion, simulate_brackets
from pinelib import SymbolInfo

TV_ID = "ip7Wyl0i"
QTY = 10.0


def one(df, params, mode):
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    ef, em, es = np_ema(c, 20), np_ema(c, 50), np_ema(c, 200)
    atr = np_atr(h, l, c, 14)
    pid, last_of = np_periods(df, 60)
    pc = pd.Series(c).groupby(pid).last().to_numpy()
    hc = np_security_lookahead_off(pc, pid, last_of)
    he = np_security_lookahead_off(np_ema(pc, 50), pid, last_of)
    eq = np_ema(c, 34)
    imp = np.abs(c - o)
    avg_imp = np_sma(imp, 10)
    c1, c20 = np.r_[np.nan, c[:-1]], np.r_[[np.nan] * 20, c[:-20]]
    h1, l1 = np.r_[np.nan, h[:-1]], np.r_[np.nan, l[:-1]]
    step = np.abs(c - c1)
    ssum = np.full(n, np.nan)
    for i in range(20, n):
        ssum[i] = step[i - 19:i + 1].sum()
    log: list = []
    fast, longm, hybrid = mode == "FAST", mode == "LONG", mode == "HYBRID"
    min_score = 65 if fast else 75 if longm else 70
    mult = 1.5 if longm else 0.8
    S = dict(prev=None, last_dir=0, entry_bar=np.nan, loss_dir=0)

    def orders(i, info):
        out = []
        pos = info["pos"]
        pp = S["prev"]
        S["prev"] = pos
        with np.errstate(invalid="ignore", divide="ignore"):
            bull, bear = ef[i] > em[i] and em[i] > es[i], ef[i] < em[i] and em[i] < es[i]
            ts = 1 if bull else -1 if bear else 0
            bias = 1 if hc[i] > he[i] else -1 if hc[i] < he[i] else 0
            eff = abs(c[i] - c20[i]) / ssum[i]
            choppy = eff < 0.25
            strong = imp[i] > avg_imp[i] * 1.2
            bb, sb = (c[i] > h1[i] and strong), (c[i] < l1[i] and strong)
            buy = (30 if ts == 1 else 0) + (20 if c[i] < eq[i] else 0) + (20 if bb else 0) + (30 if bias == 1 else 0)
            sell = (30 if ts == -1 else 0) + (20 if c[i] > eq[i] else 0) + (20 if sb else 0) + (30 if bias == -1 else 0)
            lstop, sstop = c[i] - atr[i] * mult, c[i] + atr[i] * mult
            ltgt, stgt = c[i] + (c[i] - lstop) * 1.5, c[i] - (sstop - c[i]) * 1.5
            lrr, srr = (ltgt - c[i]) / (c[i] - lstop), (c[i] - stgt) / (sstop - c[i])
            disp = abs(c[i] - eq[i]) / atr[i] > 0.5
        if pos == 0 and pp is not None and pp != 0:
            last = log[-1]
            S["loss_dir"] = S["last_dir"] if last[0] * (last[4] - last[2]) * last[5] < 0 else 0
        with np.errstate(invalid="ignore"):
            lc = bool(buy >= min_score and lrr >= 1.2 and disp and (not longm or bias == 1) and not ((fast or hybrid) and choppy))
            sc = bool(sell >= min_score and srr >= 1.2 and disp and (not longm or bias == -1) and not ((fast or hybrid) and choppy))
        lc = lc or (S["loss_dir"] == 1 and bias == 1)
        sc = sc or (S["loss_dir"] == -1 and bias == -1)
        if lc and pos == 0:
            out.append(("entry", "Long", 1, QTY))
            S["last_dir"], S["entry_bar"] = 1, i
        if sc and pos == 0:
            out.append(("entry", "Short", -1, QTY))
            S["last_dir"], S["entry_bar"] = -1, i
        can_fast = (i - S["entry_bar"]) >= 5 if not np.isnan(S["entry_bar"]) else False
        if pos > 0 and not (longm and ts >= 0) and ((not fast) or can_fast):
            out.append(("exit", "L Exit", "", None, lstop, ltgt))
        if pos < 0 and not (longm and ts <= 0) and ((not fast) or can_fast):
            out.append(("exit", "S Exit", "", None, sstop, stgt))
        return out

    ref = simulate_brackets(o, h, l, c, orders, pyramiding=1, on_close=True, tick=0.01, qty_step=1e-9, log=log)
    sym = SymbolInfo.make("NASDAQ:XYZ", "stock", qty_step=1e-9)
    ok, d = compare_q(run_conversion(TV_ID, df, symbol=sym, tf="15", params=params,
                                     strategy_overrides={"margin_long": 0, "margin_short": 0, "commission_value": 0, "slippage": 0, "default_qty_type": "fixed", "default_qty_value": QTY}), ref)
    return ok and len(ref) > 12, f"{d} (got {len(ref)})"


def check():
    df = bars(30000, seed=5, freq="15min")
    for k in ("open", "high", "low", "close"):
        df[k] = 100 * (df[k] / 100) ** 0.3
    msgs, allok = [], True
    for m in ("HYBRID", "FAST", "LONG"):
        ok, msg = one(df, {"Mode": m}, m)
        allok &= ok
        msgs.append(msg)
    return allok, " | ".join(msgs)
