"""Independent check — 1-2-3 Pattern + ATR Filter (t578EfVb): daily bars, process_orders_on_close, one position, trade list only. Confirmed pivots (8 bars left strict, 8 right non-strict; input loosened from 20) are kept in a 3-slot list; a high is accepted only when the
last accepted pivot was not a high (state pos <= 0) and a low only when pos >= 0, new items shifted in at the front (slots start at 0 / index 0). A new LOW with p0 > p2 and p0 < p1 (slots newest first) signals long, a new HIGH with p0 < p2
and p0 > p1 signals short, when slot 2's index > 0 and ATR14%/SMA50(ATR14%) <= 1.5 (loosened from 0.85); the "pattern" latch is cleared and re-armed on any change of slot 1 (which every new pivot causes). Entry at the close when flat; limit 0.98% / stop 9.5% around
the entry price issued while in a position (work from the next bar); a close order after 480 bars. Margin and slippage off, 5-unit-percent style sizing irrelevant to the trade list."""
import numpy as np
import pandas as pd

from indep import bars, compare, np_atr, np_sma, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "t578EfVb"
PRD, ATR_MAX = 8, 1.5          # loosened from 20 / 0.85 on both sides so enough trades occur


def pivots(x, L, R, high):
    n = len(x)
    out = np.full(n, np.nan)
    for i in range(L + R, n):
        p = i - R
        left, right = x[p - L:p], x[p + 1:p + R + 1]
        if high:
            if all(x[p] > left) and all(x[p] >= right):
                out[i] = x[p]
        else:
            if all(x[p] < left) and all(x[p] <= right):
                out[i] = x[p]
    return out


def check():
    df = bars(9000, seed=851)
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    ph, pl = pivots(h, PRD, PRD, True), pivots(l, PRD, PRD, False)
    atrp = np_atr(h, l, c, 14) / c * 100
    sm50 = np_sma(atrp, 50)
    with np.errstate(invalid="ignore", divide="ignore"):
        ratio = np.where(sm50 > 0, atrp / sm50, 1.0)       # na > 0 is false, so ratio = 1.0 while the average is still na
    with np.errstate(invalid="ignore"):
        ok_atr = ratio <= ATR_MAX
    S = dict(pv=[0.0, 0.0, 0.0], ix=[0, 0, 0], pos=0, pat=True, prev1=np.nan, eb=-1)
    poscl = np.zeros(n)
    ep_now = {"i": -1, "ep": np.nan}
    avg_at = np.full(n, np.nan)

    def orders(i, pos):
        poscl[i] = pos
        if pos != 0 and ep_now["i"] == i:
            avg_at[i] = ep_now["ep"]
        out = []
        jh = jl = False
        if not np.isnan(ph[i]) and S["pos"] <= 0:
            S["pv"] = [h[i - PRD]] + S["pv"][:2]
            S["ix"] = [i - PRD] + S["ix"][:2]
            S["pos"], jh = 1, True
        if not np.isnan(pl[i]) and S["pos"] >= 0:
            S["pv"] = [l[i - PRD]] + S["pv"][:2]
            S["ix"] = [i - PRD] + S["ix"][:2]
            S["pos"], jl = -1, True
        ls = ss = False
        if S["pat"] and S["ix"][2] > 0 and ok_atr[i]:
            p0, p1, p2 = S["pv"]
            if jl and p0 > p2 and p0 < p1:
                ls = True
                S["pat"] = False
            if jh and p0 < p2 and p0 > p1:
                ss = True
                S["pat"] = False
        if S["pv"][1] != S["prev1"] and not (np.isnan(S["prev1"])):
            S["pat"] = True
        S["prev1"] = S["pv"][1]
        if pos == 0:
            if ls:
                out.append(("entry", 1))
                S["eb"] = i
            elif ss:
                out.append(("entry", -1))
                S["eb"] = i
        if pos != 0 and i - S["eb"] >= 480:
            out.append(("close", pos))
        return out

    def stop(i, pos, ep, eb):
        ep_now["i"], ep_now["ep"] = i, ep
        if i == 0 or poscl[i - 1] * pos <= 0 or np.isnan(avg_at[i - 1]):
            return None
        return avg_at[i - 1] * (1 - 0.095) if pos > 0 else avg_at[i - 1] * (1 + 0.095)

    def target(i, pos, ep, eb):
        if i == 0 or poscl[i - 1] * pos <= 0 or np.isnan(avg_at[i - 1]):
            return None
        return avg_at[i - 1] * (1 + 0.0098) if pos > 0 else avg_at[i - 1] * (1 - 0.0098)

    with np.errstate(invalid="ignore"):
        ref = simulate(o, h, l, c, orders, stop=stop, target=target, on_close=True)
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="D", params={"Pivot lookback (prd)": PRD, "ATR ratio max (0 = off)": ATR_MAX}, strategy_overrides={"margin_long": 0, "margin_short": 0, "slippage": 0}), ref)
    return ok and len(ref) > 10, f"{detail} (need >10 trades, got {len(ref)})"
