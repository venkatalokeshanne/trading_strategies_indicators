"""Independent check — Volume-confirmed S/R breakout (CItvSvqk): daily bars from 2015 (the 2018-01-01 .. 2025-12-31 range binds). Support / resistance = the latest confirmed pivot low / high (10 bars each side, strict).
Entry (reversing) when the close crosses the level (crossover with the level of the previous bar, which must exist) on volume > 1.5 x SMA20, close beyond EMA200, in range. Stop = support - 0.25 ATR (resistance + 0.25 ATR for shorts) else close -/+ 1.5 ATR,
target = close +/- 3 ATR, set at the signal bar; the bracket is issued from the first script run that sees the position and works from the next bar. All four levels are cleared at any script run that finds the position flat after it was
open at the previous run - including the levels a breakout set on that same bar. Variants: default, pure ATR stops, no trend filter. Slippage / margin off on the pinelib side."""
import numpy as np

from indep import bars, compare, np_atr, np_cross_over, np_cross_under, np_ema, np_sma, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "CItvSvqk"
K = 10
T0, T1 = 1514764800000, 1767139200000


def one(df, params, struct, use_tf):
    o, h, l, c, v, t = (df[k].to_numpy() for k in ("open", "high", "low", "close", "volume", "time"))
    n = len(c)
    atr, ema, vavg = np_atr(h, l, c, 14), np_ema(c, 200), np_sma(v, 20)
    S = dict(res=np.nan, sup=np.nan, ls=np.nan, lt=np.nan, ss=np.nan, st=np.nan)
    poscl = np.zeros(n)
    stop_arr, tgt_arr = np.full(n, np.nan), np.full(n, np.nan)
    resh, suph = np.full(n, np.nan), np.full(n, np.nan)
    ph = np.full(n, np.nan)
    pl = np.full(n, np.nan)
    for i in range(2 * K, n):
        j = i - K
        if h[j] > h[j - K:j].max() and h[j] > h[j + 1:i + 1].max():
            ph[i] = h[j]
        if l[j] < l[j - K:j].min() and l[j] < l[j + 1:i + 1].min():
            pl[i] = l[j]
    state = dict(res=np.nan, sup=np.nan)
    for i in range(n):
        if not np.isnan(ph[i]):
            state["res"] = ph[i]
        if not np.isnan(pl[i]):
            state["sup"] = pl[i]
        resh[i], suph[i] = state["res"], state["sup"]
    with np.errstate(invalid="ignore"):
        surge = v > vavg * 1.5
        up_ok = (c > ema) if use_tf else np.ones(n, bool)
        dn_ok = (c < ema) if use_tf else np.ones(n, bool)
        inr = (t >= T0) & (t <= T1)
        lb = ~np.isnan(resh) & np_cross_over(c, resh) & surge & up_ok & inr
        sb = ~np.isnan(suph) & np_cross_under(c, suph) & surge & dn_ok & inr

    def orders(i, pos):
        poscl[i] = pos
        out = []
        if lb[i]:
            out.append(("entry", 1))
            S["ls"] = suph[i] - atr[i] * 0.25 if (struct and not np.isnan(suph[i])) else c[i] - atr[i] * 1.5
            S["lt"] = c[i] + atr[i] * 3.0
        if sb[i]:
            out.append(("entry", -1))
            S["ss"] = resh[i] + atr[i] * 0.25 if (struct and not np.isnan(resh[i])) else c[i] + atr[i] * 1.5
            S["st"] = c[i] - atr[i] * 3.0
        if pos > 0:
            stop_arr[i], tgt_arr[i] = S["ls"], S["lt"]
        if pos < 0:
            stop_arr[i], tgt_arr[i] = S["ss"], S["st"]
        if pos == 0 and i > 0 and poscl[i - 1] != 0:
            S.update(ls=np.nan, lt=np.nan, ss=np.nan, st=np.nan)
        return out

    def lvl(arr):
        def f(i, pos, ep, eb):
            if i == 0 or eb >= i or poscl[i - 1] * pos <= 0 or np.isnan(arr[i - 1]):
                return None
            return arr[i - 1]
        return f

    with np.errstate(invalid="ignore"):
        ref = simulate(o, h, l, c, orders, stop=lvl(stop_arr), target=lvl(tgt_arr))
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, d = compare(run_conversion(TV_ID, df, symbol=sym, tf="D", params=params, strategy_overrides={"margin_long": 0, "margin_short": 0, "slippage": 0}), ref)
    return ok and len(ref) > 10, f"{d} (got {len(ref)})"


def check():
    df = bars(6000, seed=541)
    msgs, allok = [], True
    for params, st_, tf in (({}, True, True), ({"Use broken swing level as stop (else pure ATR)": False}, False, True), ({"Require EMA trend filter": False}, True, False)):
        ok, m = one(df, params, st_, tf)
        allok &= ok
        msgs.append(m)
    return allok, " | ".join(msgs)
