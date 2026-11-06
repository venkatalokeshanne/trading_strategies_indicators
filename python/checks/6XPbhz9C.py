"""Independent check — Mean Reversion Setup LliterH (6XPbhz9C): daily bars of a stock-style symbol (qty step 0.01), market orders at the next open, fixed quantity 10 on the pinelib side (the original sizes 100 % of equity), commission / slippage / margin off.
Entry while flat: close under (10-bar highest high - multiplier x 25-bar SMA of the range), internal bar strength (close - low)/(high - low) under the cap, close over the regime SMA. The script's own hard-stop / peak / trail variables are restated in order, including the reset of all three whenever the position is flat at script time (so, being set only on the signal bar, they are cleared before the position exists and the peak, starting from na, never recovers):
leg 1 closes half of the remaining position on every bar closing above the previous high; hard stop and leg 2 are inactive in that case. Uses the quantity-aware bracket reference (indep.simulate_brackets with partial closes and quantity rounding), comparing quantities too.
Variants: defaults with a looser multiplier 1.0 and IBS cap 0.6; regime filter off, multiplier 0.8."""
import numpy as np

from indep import bars, compare_q, np_atr, np_sma, run_conversion, simulate_brackets
from pinelib import SymbolInfo

TV_ID = "6XPbhz9C"
QTY = 10.0


def one(df, params, p):
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    hh = np.array([h[i - 9:i + 1].max() if i >= 9 else np.nan for i in range(n)])
    avg = np_sma(h - l, 25)
    reg = np_sma(c, 50)
    atr = np_atr(h, l, c, 14)
    S = dict(hard=np.nan, peak=np.nan, trail=np.nan)

    def orders(i, info):
        out = []
        pos = info["pos"]
        with np.errstate(invalid="ignore", divide="ignore"):
            thr = hh[i] - p["mult"] * avg[i]
            ibs = 0.0 if h[i] == l[i] else (c[i] - l[i]) / (h[i] - l[i])
            lc = c[i] < thr and ibs < p["ibs"] and ((c[i] > reg[i]) if p["reg"] else True) and pos == 0
            if lc:
                S.update(hard=c[i] - 2.0 * atr[i], peak=c[i], trail=c[i] - 1.5 * atr[i])
            if pos > 0:
                S["peak"] = max(S["peak"], c[i]) if not np.isnan(S["peak"]) else np.nan
                S["trail"] = S["peak"] - 1.5 * atr[i]
            if pos == 0:
                S.update(hard=np.nan, peak=np.nan, trail=np.nan)
            inpos = pos > 0
            hs = inpos and not np.isnan(S["hard"]) and c[i] <= S["hard"]
            l1 = inpos and not hs and i > 0 and c[i] > h[i - 1]
            l2 = inpos and not hs and not l1 and not np.isnan(S["trail"]) and c[i] <= S["trail"]
        if lc:
            out.append(("entry", "Buy", 1, QTY))
        if hs:
            out.append(("close", "Buy"))
        if l1:
            out.append(("close", "Buy", 50.0))
        if l2:
            out.append(("close", "Buy"))
        return out

    ref = simulate_brackets(o, h, l, c, orders, qty_step=0.01)
    sym = SymbolInfo.make("NASDAQ:XYZ", "stock", qty_step=0.01)
    ok, d = compare_q(run_conversion(TV_ID, df, symbol=sym, tf="D", params=params,
                                     strategy_overrides={"margin_long": 0, "margin_short": 0, "commission_value": 0, "slippage": 0, "default_qty_type": "fixed", "default_qty_value": QTY}), ref)
    return ok and len(ref) > 5, f"{d} (got {len(ref)})"


BASE = dict(mult=2.5, ibs=0.3, reg=True)


def check():
    df = bars(12000, seed=391, freq="D")
    msgs, allok = [], True
    cases = (({"Drop Multiplier": 1.0, "Max IBS Level": 0.6}, dict(mult=1.0, ibs=0.6)),
             ({"Drop Multiplier": 0.8, "Enable Regime Filter": False}, dict(mult=0.8, reg=False)))
    for params, ov in cases:
        ok, m = one(df, params, {**BASE, **ov})
        allok &= ok
        msgs.append(m)
    return allok, " | ".join(msgs)
