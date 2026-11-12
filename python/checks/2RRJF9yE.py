"""Independent check — Sweep and Engulf (2RRJF9yE): daily bars, one position, 1 unit. Bullish sweep: low < previous low and close > previous high (bearish: high > previous high and close < previous low); the default
"invert" trades the opposite side (bullish sweep -> short). Signal while the script's own in-trade flag is off: stop = close -/+ 1.5 ATR14, target = close +/- 2 x risk, fixed prices issued together with the entry (they work from the
fill bar). The flag is cleared on a later bar (bar > entry bar) whose high / low reaches the target or stop, and a new signal may follow on that same bar. Margin and slippage off on the pinelib side. Variants run too:
Candle High/Low stop with no inversion."""
import numpy as np

from indep import bars, compare, np_atr, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "2RRJF9yE"


def one(df, invert, candle_sl):
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    atr = np_atr(h, l, c, 14)
    h1, l1 = np.r_[np.nan, h[:-1]], np.r_[np.nan, l[:-1]]
    with np.errstate(invalid="ignore"):
        bu = (l < l1) & (c > h1) & ~np.isnan(atr)
        be = (h > h1) & (c < l1) & ~np.isnan(atr)
    S = dict(it=False, d=0, eb=-1, sl=np.nan, tp=np.nan)

    def orders(i, pos):
        out = []
        if S["it"] and i > S["eb"]:
            d = S["d"]
            if (d == 1 and (h[i] >= S["tp"] or l[i] <= S["sl"])) or (d == -1 and (l[i] <= S["tp"] or h[i] >= S["sl"])):
                S["it"] = False
        rl, rs = (be[i], bu[i]) if invert else (bu[i], be[i])
        if rl and not S["it"]:
            sl = l[i] if candle_sl else c[i] - atr[i] * 1.5
            S.update(it=True, d=1, eb=i, sl=sl, tp=c[i] + (c[i] - sl) * 2.0)
            out.append(("entry", 1))
        if rs and not S["it"]:
            sl = h[i] if candle_sl else c[i] + atr[i] * 1.5
            S.update(it=True, d=-1, eb=i, sl=sl, tp=c[i] - (sl - c[i]) * 2.0)
            out.append(("entry", -1))
        return out

    def stop(i, pos, ep, eb):
        return S["sl"] if S["d"] == pos else None

    def target(i, pos, ep, eb):
        return S["tp"] if S["d"] == pos else None

    with np.errstate(invalid="ignore"):
        ref = simulate(o, h, l, c, orders, stop=stop, target=target)
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    params = {"Invert Strategy (Trade Opposite)": invert, "Stop Loss Method": "Candle High/Low" if candle_sl else "ATR"}
    ok, d = compare(run_conversion(TV_ID, df, symbol=sym, tf="D", params=params, strategy_overrides={"margin_long": 0, "margin_short": 0, "slippage": 0}), ref)
    return ok and len(ref) > 10, f"invert={invert} candleSL={candle_sl}: {d} (got {len(ref)})"


def check():
    df = bars(6000, seed=541)
    msgs, allok = [], True
    for inv, cs in ((True, False), (False, True)):
        ok, m = one(df, inv, cs)
        allok &= ok
        msgs.append(m)
    return allok, " | ".join(msgs)
