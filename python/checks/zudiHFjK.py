"""Independent check — XAU Clear EMA ATR Strategy (zudiHFjK): 15-minute bars (price scaled into the 2000s, tick 0.01), process_orders_on_close (orders fill at the signal close), 1 unit by default scaled to 10 on the pinelib side, commission / slippage / margin off.
Buy = fast EMA over slow, close above the fast EMA while the previous close was at or below the previous fast EMA (sell mirrored). A signal closes the other side and enters; entry = close rounded to the tick, stop = entry -/+ ATR x multiplier (rounded), five targets at multiples of that risk (rounded).
From the first signal on, five exit orders of 20 % each (limit at the target, the common stop) are re-issued every bar for the last direction; a repeated signal in the direction of the open position cannot enter again but moves the levels. Uses the quantity-aware bracket reference (indep.simulate_brackets), comparing quantities too.
Variants: defaults; faster EMAs with a 1.0 ATR stop and nearer targets; wider stop with far targets."""
import numpy as np

from indep import bars, compare_q, np_atr, np_ema, run_conversion, simulate_brackets
from pinelib import SymbolInfo

TV_ID = "zudiHFjK"
QTY = 10.0


def one(df, params, p):
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    sym = SymbolInfo.make("BINANCE:XAUUSDT", "crypto", qty_step=1e-9)
    tick = sym.mintick
    rnd = lambda x: np.floor(x / tick + 0.5) * tick
    ef, es, atr = np_ema(c, p["f"]), np_ema(c, p["s"]), np_atr(h, l, c, 14)
    S = dict(d=0, sl=np.nan, tps=[np.nan] * 5)

    def orders(i, info):
        out = []
        with np.errstate(invalid="ignore"):
            buy = i > 0 and ef[i] > es[i] and c[i] > ef[i] and c[i - 1] <= ef[i - 1]
            sell = i > 0 and ef[i] < es[i] and c[i] < ef[i] and c[i - 1] >= ef[i - 1]
        if buy:
            e = rnd(c[i])
            sl = rnd(e - atr[i] * p["sl"])
            risk = e - sl
            S.update(d=1, sl=sl, tps=[rnd(e + risk * m) for m in p["tp"]])
            out += [("close", "SELL"), ("entry", "BUY", 1, QTY)]
        if sell:
            e = rnd(c[i])
            sl = rnd(e + atr[i] * p["sl"])
            risk = sl - e
            S.update(d=-1, sl=sl, tps=[rnd(e - risk * m) for m in p["tp"]])
            out += [("close", "BUY"), ("entry", "SELL", -1, QTY)]
        if S["d"] != 0:
            name = "BUY" if S["d"] == 1 else "SELL"
            for k in range(5):
                lim, sl = S["tps"][k], S["sl"]
                out.append(("exit", "%s TP%d" % (name, k + 1), name, 20, None if np.isnan(sl) else sl, None if np.isnan(lim) else lim))
        return out

    ref = simulate_brackets(o, h, l, c, orders, on_close=True, tick=tick)
    ok, d = compare_q(run_conversion(TV_ID, df, symbol=sym, tf="15", params=params,
                                     strategy_overrides={"margin_long": 0, "margin_short": 0, "default_qty_type": "fixed", "default_qty_value": QTY}), ref)
    return ok and len(ref) > 12, f"{d} (got {len(ref)})"


BASE = dict(f=21, s=50, sl=1.5, tp=(0.7, 1.2, 1.8, 2.5, 3.5))


def check():
    df = bars(30000, seed=161, freq="15min")
    base = df["close"].iloc[0]
    for k in ("open", "high", "low", "close"):
        df[k] = 2000 * (df[k] / base) ** 0.1
    msgs, allok = [], True
    cases = (({}, {}),
             ({"EMA Fast": 9, "EMA Slow": 21, "SL ATR Multiplier": 1.0, "TP1 STRONG": 0.4, "TP2 STRONG": 0.8, "TP3 GOOD": 1.2, "TP4 AGGRESSIVE": 1.6, "TP5 AGGRESSIVE": 2.0},
              dict(f=9, s=21, sl=1.0, tp=(0.4, 0.8, 1.2, 1.6, 2.0))),
             ({"SL ATR Multiplier": 3.0, "TP5 AGGRESSIVE": 6.0}, dict(sl=3.0, tp=(0.7, 1.2, 1.8, 2.5, 6.0))))
    for params, ov in cases:
        ok, m = one(df, params, {**BASE, **ov})
        allok &= ok
        msgs.append(m)
    return allok, " | ".join(msgs)
