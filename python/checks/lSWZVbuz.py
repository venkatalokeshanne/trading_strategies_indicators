"""Independent check — Supertrend + MA Crossover (lSWZVbuz): daily bars, one position (entries reverse), trade list only. Hand-built SuperTrend on HL2 with ATR10 x 3: final upper = upper if there is none yet / upper < previous final upper /
previous source > previous final upper, else previous (final lower mirrored); direction 1 (up) flips to -1 when source < previous final lower, -1 flips to 1 when source > previous final upper (stays 1 while ATR[1] is na); line = final lower
when dir = 1 else final upper. EMA20(close) crossing over the line goes long, under goes short; variants: reverse mode with a WMA, and the default. Stop 1% / target 2% around the entry price issued while in a position (work from the next bar,
only if a same-side position existed at the previous script run). Margin and slippage off on the pinelib side."""
import numpy as np

from indep import bars, compare, np_atr, np_cross_over, np_cross_under, np_ema, np_wma, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "lSWZVbuz"


def one(df, ma_type, reverse):
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    src = (h + l) / 2
    atr = np_atr(h, l, c, 10)
    fu = np.full(n, np.nan)
    fl = np.full(n, np.nan)
    d = np.ones(n, int)
    for i in range(n):
        up, lo = src[i] + 3.0 * atr[i], src[i] - 3.0 * atr[i]
        if i == 0 or np.isnan(fu[i - 1]):
            fu[i] = up
        else:
            fu[i] = up if (up < fu[i - 1] or src[i - 1] > fu[i - 1]) else fu[i - 1]
        if i == 0 or np.isnan(fl[i - 1]):
            fl[i] = lo
        else:
            fl[i] = lo if (lo > fl[i - 1] or src[i - 1] < fl[i - 1]) else fl[i - 1]
        if i == 0 or np.isnan(atr[i - 1]):
            d[i] = 1
        elif d[i - 1] == -1 and src[i] > fu[i - 1]:
            d[i] = 1
        elif d[i - 1] == 1 and src[i] < fl[i - 1]:
            d[i] = -1
        else:
            d[i] = d[i - 1]
    line = np.where(d == 1, fl, fu)
    ma = np_ema(c, 20) if ma_type == "EMA" else np_wma(c, 20)
    with np.errstate(invalid="ignore"):
        cu, cd = np_cross_over(ma, line), np_cross_under(ma, line)
    ls, ss = (cd, cu) if reverse else (cu, cd)
    poscl = np.zeros(n)
    ep_now = {"i": -1, "ep": np.nan}
    avg_at = np.full(n, np.nan)

    def orders(i, pos):
        poscl[i] = pos
        if pos != 0 and ep_now["i"] == i:
            avg_at[i] = ep_now["ep"]
        out = []
        if ls[i]:
            out.append(("entry", 1))
        if ss[i]:
            out.append(("entry", -1))
        return out

    def stop(i, pos, ep, eb):
        ep_now["i"], ep_now["ep"] = i, ep
        if i == 0 or poscl[i - 1] * pos <= 0 or np.isnan(avg_at[i - 1]):
            return None
        return avg_at[i - 1] * (1 - 0.01 * pos)

    def target(i, pos, ep, eb):
        if i == 0 or poscl[i - 1] * pos <= 0 or np.isnan(avg_at[i - 1]):
            return None
        return avg_at[i - 1] * (1 + 0.02 * pos)

    with np.errstate(invalid="ignore"):
        ref = simulate(o, h, l, c, orders, stop=stop, target=target)
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, dd = compare(run_conversion(TV_ID, df, symbol=sym, tf="D", params={"MA Type": ma_type, "Reverse Trading Mode": reverse},
                                    strategy_overrides={"margin_long": 0, "margin_short": 0, "slippage": 0}), ref)
    return ok and len(ref) > 10, f"{ma_type}/reverse={reverse}: {dd} (got {len(ref)})"


def check():
    df = bars(6000, seed=991)
    msgs, allok = [], True
    for mt, rv in (("EMA", False), ("WMA", True)):
        ok, m = one(df, mt, rv)
        allok &= ok
        msgs.append(m)
    return allok, " | ".join(msgs)
