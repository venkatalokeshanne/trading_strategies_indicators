"""Independent check — Universal Strategy Feed (gU6RDuh5): hourly bars, process_orders_on_close, volume mode (the only mode that needs no external series): long when volume > SMA200(volume) on a green-or-flat bar, short when above it on a red bar; signals alternate
(a signal fires only when it differs from the last one that fired; a same-bar long wins) and reverse the position at the close. Variants: no exits; percent exits (TP +0.5 % / SL -0.3 % of the average price, issued from the first script run that sees the position, working
from the next bar); ATR exits (TP +0.5 x, SL -0.3 x of the ATR sampled ONLY on signal bars: its RMA is fed just those bars, so it is na until 14 signals have been seen). Margin off on the pinelib side."""
import numpy as np

from indep import bars, compare, np_sma, np_tr, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "gU6RDuh5"


def one(df, params, exits):
    o, h, l, c, v = (df[k].to_numpy() for k in ("open", "high", "low", "close", "volume"))
    n = len(c)
    ma = np_sma(v, 200)
    tr = np_tr(h, l, c, True)
    with np.errstate(invalid="ignore"):
        lraw = (v > ma) & (c >= o)
        sraw = (v > ma) & (c < o)
    S = dict(last=0, fed=[], atr=np.nan)
    poscl = np.zeros(n)
    tp_arr, sl_arr = [None] * n, [None] * n

    def orders(i, pos):
        poscl[i] = pos
        out = []
        buy = lraw[i] and S["last"] != 1
        sell = sraw[i] and S["last"] != -1 and not buy
        if buy:
            S["last"] = 1
        if sell:
            S["last"] = -1
        if buy or sell:
            S["fed"].append(tr[i])
            f = S["fed"]
            if len(f) < 14:
                S["atr"] = np.nan
            elif len(f) == 14:
                S["atr"] = float(np.mean(f))
            else:
                S["atr"] = S["atr"] * 13 / 14 + f[-1] / 14
        if buy:
            out.append(("entry", 1))
        if sell:
            out.append(("entry", -1))
        if pos != 0 and exits != "none":
            if exits == "pct":
                tp, sl = (1.005, 0.997) if pos > 0 else (0.995, 1.003)
                tp_arr[i], sl_arr[i] = ("avg*", tp), ("avg*", sl)
            else:
                a = S["atr"]
                tp_arr[i] = ("avg+", pos * a * 0.5)
                sl_arr[i] = ("avg+", -pos * a * 0.3)
        return out

    def lvl(arr):
        def f(i, pos, ep, eb):
            if i == 0 or eb >= i or poscl[i - 1] * pos <= 0:
                return None
            spec = arr[i - 1]
            if not isinstance(spec, tuple):
                return None
            kind, x = spec
            r = ep * x if kind == "avg*" else ep + x
            return None if np.isnan(r) else r
        return f

    with np.errstate(invalid="ignore"):
        ref = simulate(o, h, l, c, orders, stop=lvl(sl_arr), target=lvl(tp_arr), on_close=True)
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, d = compare(run_conversion(TV_ID, df, symbol=sym, tf="60", params=params, strategy_overrides={"margin_long": 0, "margin_short": 0}), ref)
    return ok and len(ref) > 10, f"{d} (got {len(ref)})"


def check():
    df = bars(15000, seed=641, freq="1h")
    base = {"Signal Mode": "Volume (magnitude + candle)"}
    msgs, allok = [], True
    for extra, ex in (({}, "none"), ({"TP/SL Method": "Percent", "Take Profit %": 0.5, "Stop Loss %": 0.3}, "pct"), ({"TP/SL Method": "ATR", "ATR TP Multiplier": 0.5, "ATR SL Multiplier": 0.3}, "atr")):
        ok, m = one(df, {**base, **extra}, ex)
        allok &= ok
        msgs.append(m)
    return allok, " | ".join(msgs)
