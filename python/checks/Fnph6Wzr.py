"""Independent check — Double U Strategy (Fnph6Wzr): 5-minute bars of a stock symbol, process_orders_on_close (every order fills at the signal close), pyramiding 3, slippage / margin off (sizing is a percent of equity, which does not change the trade prices).
Two ATR trailing stops (the first value is close +/- distance, then the usual ratchet / flip rules): a close crossing under the short trail below the trend EMA is a short signal, a close crossing over the long trail above it a long signal; exit counters (consecutive closes above / below the close N bars earlier) reaching exactly the sequence length close that side
and veto a same-direction entry on that bar. Uses the multi-trade reference broker (indep.simulate_pyr, 1 unit per trade, on_close).
Variants: defaults with a shorter trend EMA; different sensitivities / ATR lengths and a longer sequence; short sequence 5, reference 3."""
import numpy as np

from indep import bars, compare, np_atr, np_ema, np_cross_over, np_cross_under, run_conversion, simulate_pyr
from pinelib import SymbolInfo

TV_ID = "Fnph6Wzr"


def trail(c, dist, is_short):
    n = len(c)
    t = np.full(n, np.nan)
    for i in range(n):
        prev_t = t[i - 1] if i > 0 else np.nan
        if np.isnan(prev_t):
            t[i] = c[i] + dist[i] if is_short else c[i] - dist[i]
            continue
        c1 = c[i - 1]
        if c[i] > prev_t and c1 > prev_t:
            t[i] = max(prev_t, c[i] - dist[i])
        elif c[i] < prev_t and c1 < prev_t:
            t[i] = min(prev_t, c[i] + dist[i])
        else:
            t[i] = c[i] - dist[i] if c[i] > prev_t else c[i] + dist[i]
    return t


def one(df, params, p):
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    sym = SymbolInfo.make("NASDAQ:XYZ", "stock", qty_step=1e-9)
    trend = np_ema(c, p["trend"])
    st = trail(c, p["ss"] * np_atr(h, l, c, p["sa"]), True)
    lt = trail(c, p["ls"] * np_atr(h, l, c, p["la"]), False)
    with np.errstate(invalid="ignore"):
        sig_s = np_cross_under(c, st) & (c < trend)
        sig_l = np_cross_over(c, lt) & (c > trend)
    bull = np.zeros(n, int)
    bear = np.zeros(n, int)
    b1 = b2 = 0
    for i in range(n):
        ref = c[i - p["ref"]] if i >= p["ref"] else np.nan
        with np.errstate(invalid="ignore"):
            if c[i] > ref:
                b1, b2 = b1 + 1, 0
            elif c[i] < ref:
                b2, b1 = b2 + 1, 0
        bull[i], bear[i] = b1, b2

    def orders(i, pos):
        out = []
        lx, sx = bull[i] == p["seq"], bear[i] == p["seq"]
        if lx and pos > 0:
            out.append(("close", 1))
        if sx and pos < 0:
            out.append(("close", -1))
        if sig_l[i] and not lx:
            out.append(("entry", 1))
        if sig_s[i] and not sx:
            out.append(("entry", -1))
        return out

    ref = simulate_pyr(o, h, l, c, orders, pyramiding=3, on_close=True)
    ok, d = compare(run_conversion(TV_ID, df, symbol=sym, tf="5", params=params,
                                   strategy_overrides={"slippage": 0, "margin_long": 0, "margin_short": 0, "commission_value": 0}), ref)
    return ok and len(ref) > 12, f"{d} (got {len(ref)})"


BASE = dict(trend=700, ss=5.0, sa=3, ls=3.0, la=4, ref=5, seq=9)


def check():
    df = bars(30000, seed=41, freq="5min")
    for k in ("open", "high", "low", "close"):
        df[k] = 100 * (df[k] / 100) ** 0.4
    msgs, allok = [], True
    cases = (({"Trend EMA Length": 100}, dict(trend=100)),
             ({"Short Sensitivity": 2.0, "Short ATR Length": 5, "Long Sensitivity": 1.5, "Long ATR Length": 6, "Sequence Length": 12, "Trend EMA Length": 200},
              dict(ss=2.0, sa=5, ls=1.5, la=6, seq=12, trend=200)),
             ({"Sequence Length": 5, "Reference Bars": 3, "Trend EMA Length": 50}, dict(seq=5, ref=3, trend=50)))
    for params, ov in cases:
        ok, m = one(df, params, {**BASE, **ov})
        allok &= ok
        msgs.append(m)
    return allok, " | ".join(msgs)
