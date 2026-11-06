"""Independent check — ENSO/USDT Trend Pullback Sniper (CIkRyg3y): 15-minute bars (24 h synthetic) on a stock-style symbol (VWAP anchored at 09:30 New York), market orders at the next open, fixed quantity 10 on the pinelib side (the original sizes 100 % of equity), commission / slippage / margin off.
EMA fast over mid and the close over the slow EMA (mirror for shorts), the close on the right side of the session VWAP, within ATR x zone of the mid EMA, and the stochastic-RSI %K (SMA of the stochastic of the RSI over its own window) crossing up through %D (SMA of %K) with the previous %K below the oversold level (overbought for shorts), while flat.
Exit orders issued with the entry: 50 % at the first ATR target and the rest (100 % of the lot, capped by what is open) at the second, both with the same stop; a close beyond the slow EMA against the position closes it at the next open.
Uses the quantity-aware bracket reference (indep.simulate_brackets), which also compares the closed quantities.
Variants: defaults with a wide pullback zone and loose levels; short EMAs, tighter stop and wider targets."""
import numpy as np

from indep import bars, compare_q, np_atr, np_cross_over, np_cross_under, np_ema, np_rsi, np_stoch, np_vwap, run_conversion, simulate_brackets
from pinelib import SymbolInfo

TV_ID = "CIkRyg3y"
QTY = 10.0


def sma_prefix(x, n):
    """SMA as (prefix sum difference + current value) / n. The stochastic saturates at identical values for several bars, and %K == %D is then an exact tie
    whose side depends on the last ulp of the sum, so the smoothing uses the same summation order as the engine's rolling sum."""
    out = np.full(len(x), np.nan)
    psum = [0.0]
    pnan = [0]
    for i, v in enumerate(x):
        m = i
        if m + 1 >= n and not np.isnan(v) and pnan[m] - pnan[m - (n - 1)] == 0:
            out[i] = (psum[m] - psum[m - (n - 1)] + v) / n
        psum.append(psum[-1] + (0.0 if np.isnan(v) else v))
        pnan.append(pnan[-1] + (1 if np.isnan(v) else 0))
    return out


def one(df, params, p):
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    hlc3 = (h + l + c) / 3
    ef, em, es = np_ema(c, p["f"]), np_ema(c, p["m"]), np_ema(c, 50)
    vw = np_vwap(df, hlc3)
    atr = np_atr(h, l, c, 14)
    rsi = np_rsi(c, 14)
    k = sma_prefix(np_stoch(rsi, rsi, rsi, 14), 3)
    d = sma_prefix(k, 3)
    xu, xd = np_cross_over(k, d), np_cross_under(k, d)
    k1 = np.r_[np.nan, k[:-1]]
    with np.errstate(invalid="ignore"):
        up, dn = (ef > em) & (c > es), (ef < em) & (c < es)
        near = np.abs(c - em) <= atr * p["zone"]
        lc = up & (c > vw) & near & xu & (k1 < p["os"])
        sc = dn & (c < vw) & near & xd & (k1 > p["ob"])

    def orders(i, info):
        out = []
        pos = info["pos"]
        if lc[i] and pos == 0:
            sl, t1, t2 = c[i] - atr[i] * p["sl"], c[i] + atr[i] * p["t1"], c[i] + atr[i] * p["t2"]
            out += [("entry", "Long", 1, QTY), ("exit", "Long TP1", "Long", 50, sl, t1), ("exit", "Long TP2", "Long", 100, sl, t2)]
        if sc[i] and pos == 0:
            sl, t1, t2 = c[i] + atr[i] * p["sl"], c[i] - atr[i] * p["t1"], c[i] - atr[i] * p["t2"]
            out += [("entry", "Short", -1, QTY), ("exit", "Short TP1", "Short", 50, sl, t1), ("exit", "Short TP2", "Short", 100, sl, t2)]
        with np.errstate(invalid="ignore"):
            if pos > 0 and c[i] < es[i]:
                out.append(("close", "Long"))
            if pos < 0 and c[i] > es[i]:
                out.append(("close", "Short"))
        return out

    ref = simulate_brackets(o, h, l, c, orders)
    sym = SymbolInfo.make("NASDAQ:XYZ", "stock", qty_step=1e-9)
    ok, dd = compare_q(run_conversion(TV_ID, df, symbol=sym, tf="15", params=params,
                                      strategy_overrides={"margin_long": 0, "margin_short": 0, "default_qty_type": "fixed", "default_qty_value": QTY}), ref)
    return ok and len(ref) > 12, f"{dd} (got {len(ref)})"


BASE = dict(f=9, m=21, zone=1.0, os=20, ob=80, sl=1.5, t1=2.0, t2=3.0)


def check():
    df = bars(30000, seed=111, freq="15min")
    for k in ("open", "high", "low", "close"):
        df[k] = 100 * (df[k] / 100) ** 0.3
    msgs, allok = [], True
    cases = (({"Pullback Zone (ATR from EMA21)": 2.0, "Stoch Oversold": 35, "Stoch Overbought": 65}, dict(zone=2.0, os=35, ob=65)),
             ({"EMA Fast Length": 5, "EMA Mid Length": 13, "Pullback Zone (ATR from EMA21)": 3.0, "Stoch Oversold": 45, "Stoch Overbought": 55, "Stop Loss ATR Multiplier": 1.0, "Take Profit 1 ATR Multiplier": 1.0, "Take Profit 2 ATR Multiplier": 4.0},
              dict(f=5, m=13, zone=3.0, os=45, ob=55, sl=1.0, t1=1.0, t2=4.0)))
    for params, ov in cases:
        ok, m = one(df, params, {**BASE, **ov})
        allok &= ok
        msgs.append(m)
    return allok, " | ".join(msgs)
