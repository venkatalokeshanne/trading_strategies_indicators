"""Independent check — 2x Universelle Linien (mpwbMiL9): daily bars, 1 unit. A cross of line 1 over / under line 2 enters long / short (reversing) and closes the opposite side. Several
line-type pairs are compared against numpy moving averages: SMA/EMA/WMA/RMA/DEMA/TEMA/TMA/price and the direction filter (long only). Margin and slippage off on the pinelib side."""
import numpy as np

from indep import bars, compare, np_cross_over, np_cross_under, np_ema, np_rma, np_sma, np_wma, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "mpwbMiL9"


def line(kind, c, n):
    if kind == "SMA":
        return np_sma(c, n)
    if kind == "EMA":
        return np_ema(c, n)
    if kind == "WMA":
        return np_wma(c, n)
    if kind in ("RMA", "SMMA"):
        return np_rma(c, n)
    if kind == "DEMA":
        e = np_ema(c, n)
        return 2 * e - np_ema(e, n)
    if kind == "TEMA":
        e1 = np_ema(c, n)
        e2 = np_ema(e1, n)
        return 3 * (e1 - e2) + np_ema(e2, n)
    if kind == "TMA":
        h = int(np.floor((n + 1) / 2 + 0.5))
        return np_sma(np_sma(c, h), h)
    if kind == "Nur Preis":
        return c
    raise ValueError(kind)


def one(df, t1, n1, t2, n2, richtung):
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    a, b = line(t1, c, n1), line(t2, c, n2)
    with np.errstate(invalid="ignore"):
        up, dn = np_cross_over(a, b), np_cross_under(a, b)

    def orders(i, pos):
        out = []
        if richtung in ("beide", "long"):
            if up[i]:
                out.append(("entry", 1))
            if dn[i] and pos > 0:
                out.append(("close", 1))
        if richtung in ("beide", "short"):
            if dn[i]:
                out.append(("entry", -1))
            if up[i] and pos < 0:
                out.append(("close", -1))
        return out

    ref = simulate(o, h, l, c, orders)
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    p = {"richtung": richtung, "Art der Linie 1": t1, "Länge 1": n1, "Art der Linie 2": t2, "Länge 2": n2}
    ok, d = compare(run_conversion(TV_ID, df, symbol=sym, tf="D", params=p, strategy_overrides={"margin_long": 0, "margin_short": 0, "slippage": 0}), ref)
    return ok and len(ref) > 5, f"{t1}{n1}/{t2}{n2}/{richtung}: {d} (got {len(ref)})"


def check():
    df = bars(4000, seed=511)
    msgs, allok = [], True
    for args in (("EMA", 21, "SMA", 50, "beide"), ("WMA", 9, "RMA", 30, "beide"), ("DEMA", 12, "TEMA", 20, "long"), ("TMA", 15, "SMA", 40, "short"),
                 ("Nur Preis", 1, "EMA", 20, "beide")):
        ok, m = one(df, *args)
        allok &= ok
        msgs.append(m)
    return allok, " | ".join(msgs)
