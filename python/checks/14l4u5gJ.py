"""Independent check — Tomukas Scale-In V2 (14l4u5gJ): hourly bars of a stock-style symbol, process_orders_on_close (orders fill at the signal close), the strategy's own quantities (1, 2, 4... as inputs 10 / 10 / 20 / 40 / 80 units), pyramiding 5, commission / slippage / margin off.
Sweep = in an EMA100 > EMA200 trend, low under the lowest low of the previous L bars (shifted by one) with the close back above it on an up candle (mirror for shorts). Entry L1/S1 while flat; while a position is open and the sweep repeats, entry k+1 is added when the number of open lots (the script's strategy.opentrades) is k. One exit order (limit at the average entry price +/- ATR x mult, all lots)
is re-issued each bar while a position is open. Uses the quantity-aware bracket reference (indep.simulate_brackets, on_close; info["n"] = open lots), comparing quantities too.
Variants: defaults with lookback 8; lookback 5, TP 0.8 ATR; lookback 12, TP 3 ATR."""
import numpy as np

from indep import bars, compare_q, np_atr, np_ema, run_conversion, simulate_brackets
from pinelib import SymbolInfo

TV_ID = "14l4u5gJ"
Q = (10.0, 10.0, 20.0, 40.0, 80.0)


def one(df, params, p):
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    e1, e2 = np_ema(c, 100), np_ema(c, 200)
    atr = np_atr(h, l, c, 14)
    L = p["lb"]
    ls_ = np.r_[np.nan, l[:-1]]
    hs = np.r_[np.nan, h[:-1]]
    pl = np.array([np.nanmin(ls_[i - L + 1:i + 1]) if i >= L - 1 and not np.all(np.isnan(ls_[i - L + 1:i + 1])) else np.nan for i in range(n)])
    ph = np.array([np.nanmax(hs[i - L + 1:i + 1]) if i >= L - 1 and not np.all(np.isnan(hs[i - L + 1:i + 1])) else np.nan for i in range(n)])
    with np.errstate(invalid="ignore"):
        lsw = (e1 > e2) & (l < pl) & (c > pl) & (c > o)
        ssw = (e1 < e2) & (h > ph) & (c < ph) & (c < o)

    def orders(i, info):
        out = []
        pos, k = info["pos"], info["n"]
        if lsw[i] and pos == 0:
            out.append(("entry", "L1", 1, Q[0]))
        if ssw[i] and pos == 0:
            out.append(("entry", "S1", -1, Q[0]))
        for j in range(1, 5):
            if pos > 0 and lsw[i] and k == j:
                out.append(("entry", "L%d" % (j + 1), 1, Q[j]))
        for j in range(1, 5):
            if pos < 0 and ssw[i] and k == j:
                out.append(("entry", "S%d" % (j + 1), -1, Q[j]))
        if pos > 0:
            out.append(("exit", "TP LONG", "", None, None, info["avg"] + atr[i] * p["tp"]))
        if pos < 0:
            out.append(("exit", "TP SHORT", "", None, None, info["avg"] - atr[i] * p["tp"]))
        return out

    ref = simulate_brackets(o, h, l, c, orders, pyramiding=5, on_close=True)
    sym = SymbolInfo.make("NASDAQ:XYZ", "stock", qty_step=1e-9)
    ok, d = compare_q(run_conversion(TV_ID, df, symbol=sym, tf="60", params=params,
                                     strategy_overrides={"margin_long": 0, "margin_short": 0, "commission_value": 0, "slippage": 0}), ref)
    return ok and len(ref) > 12, f"{d} (got {len(ref)})"


BASE = dict(lb=20, tp=1.5)


def check():
    df = bars(30000, seed=271, freq="1h")
    for k in ("open", "high", "low", "close"):
        df[k] = 100 * (df[k] / 100) ** 0.5
    msgs, allok = [], True
    cases = (({"Sweep Lookback": 8}, dict(lb=8)),
             ({"Sweep Lookback": 5, "TP ATR Multiplier": 0.8}, dict(lb=5, tp=0.8)),
             ({"Sweep Lookback": 12, "TP ATR Multiplier": 3.0}, dict(lb=12, tp=3.0)))
    for params, ov in cases:
        ok, m = one(df, params, {**BASE, **ov})
        allok &= ok
        msgs.append(m)
    return allok, " | ".join(msgs)
