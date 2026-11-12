"""Independent check — Feynman Renorm armed stops (4bBrEQ7T): daily bars, pending stop entries only (process_orders_on_close has no market order to act on). Score long = 3 (close > EMA200) + 3 (volume > SMA20(volume)) + 2 (RSI14 < 65) + 2 (bullish bar); short mirrored (RSI > 35, bearish). Armed at >= 10 (min score): a buy-stop at high + 1.5 ATR14 while not long, a sell-stop at low - 1.5 ATR14 while not short, renewed at each bar close, otherwise left pending; fills at the level (at the open when gapped) and reverses the other side. Uses the pending-order reference broker (simulate_ord). Margin off on the pinelib side. Variants: min score 10, and 8 (more often armed)."""
import numpy as np

from indep import bars, compare, np_atr, np_ema, np_rsi, np_sma, run_conversion, simulate_ord

TV_ID = "4bBrEQ7T"


def one(df, params, ms):
    o, h, l, c, v = (df[k].to_numpy() for k in ("open", "high", "low", "close", "volume"))
    atr, ema, rsi, vma = np_atr(h, l, c, 14), np_ema(c, 200), np_rsi(c, 14), np_sma(v, 20)

    def orders(i, pos):
        with np.errstate(invalid="ignore"):
            bs = 3 * (c[i] > ema[i]) + 3 * (v[i] > vma[i]) + 2 * (rsi[i] < 65) + 2 * (c[i] > o[i])
            ss = 3 * (c[i] < ema[i]) + 3 * (v[i] > vma[i]) + 2 * (rsi[i] > 35) + 2 * (c[i] < o[i])
        out = []
        if bs >= ms and pos <= 0:
            out.append(("entry", "Long", 1, None if np.isnan(atr[i]) else h[i] + atr[i] * 1.5, None))
        if ss >= ms and pos >= 0:
            out.append(("entry", "Short", -1, None if np.isnan(atr[i]) else l[i] - atr[i] * 1.5, None))
        return out

    ref = simulate_ord(o, h, l, c, orders)
    ok, d = compare(run_conversion(TV_ID, df, params=params, strategy_overrides={"margin_long": 0, "margin_short": 0}), ref)
    return ok and len(ref) > 5, f"{d} (got {len(ref)})"


def check():
    df = bars(5000, seed=47)
    msgs, allok = [], True
    for params, ms in (({}, 10), ({"Min Score to ARM Orders": 8}, 8)):
        ok, m = one(df, params, ms)
        allok &= ok
        msgs.append(m)
    return allok, " | ".join(msgs)
