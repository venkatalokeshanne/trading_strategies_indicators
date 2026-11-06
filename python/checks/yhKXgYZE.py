"""Independent check — TQQQ EMA Strategy (yhKXgYZE): daily bars (returns compressed 8x so the +30 % target / ratchet levels are reachable but not trivial), long only, market entries at the next open. EMA20 crosses over EMA50 with ADX(14) >= 20 and nothing open -> buy. At every script run with the position open: take-profit = avg x 1.3;
stop = max(previous trail, avg x 0.95 / avg when 10 % in profit at the close / avg x 1.1 when 20 % in profit), both working from the next bar; the trail is cleared when flat. Variants: default; tighter 1.1 target and 0.98 stop. Margin / slippage / commission off on the pinelib side."""
import numpy as np

from indep import bars, compare, np_cross_over, np_dmi, np_ema, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "yhKXgYZE"


def one(df, params, tpm, slm):
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    f, s = np_ema(c, 20), np_ema(c, 50)
    adx = np_dmi(h, l, c, 14)[2]
    with np.errstate(invalid="ignore"):
        sig = np_cross_over(f, s) & (adx >= 20)
    S = dict(trail=np.nan, ep=np.nan)
    poscl = np.zeros(n)
    sl_arr, tp_arr = np.full(n, np.nan), np.full(n, np.nan)

    def orders(i, pos):
        poscl[i] = pos
        out = []
        if sig[i] and pos == 0:
            out.append(("entry", 1))
        if pos > 0:
            ep = S["ep"]
            pp = (c[i] - ep) / ep
            ns = ep * slm
            if pp >= 0.2:
                ns = ep * 1.1
            elif pp >= 0.1:
                ns = ep
            S["trail"] = ns if np.isnan(S["trail"]) else max(S["trail"], ns)
            sl_arr[i], tp_arr[i] = S["trail"], ep * tpm
        else:
            S["trail"] = np.nan
        return out

    def lvl(arr):
        def f_(i, pos, ep, eb):
            S["ep"] = ep
            return None if (i == 0 or eb >= i or poscl[i - 1] <= 0 or np.isnan(arr[i - 1])) else arr[i - 1]
        return f_

    sf, tf = lvl(sl_arr), lvl(tp_arr)

    def stop(i, pos, ep, eb):
        S["ep"] = ep
        return sf(i, pos, ep, eb)

    with np.errstate(invalid="ignore"):
        ref = simulate(o, h, l, c, orders, stop=stop, target=tf)
    sym = SymbolInfo.make("NASDAQ:TQQQ", "stock", qty_step=1e-9)
    ok, d = compare(run_conversion(TV_ID, df, symbol=sym, tf="D", params=params, strategy_overrides={"margin_long": 0, "margin_short": 0, "slippage": 0}), ref)
    return ok and len(ref) > 10, f"{d} (got {len(ref)})"


def check():
    df = bars(14000, seed=851)
    for k in ("open", "high", "low", "close"):
        df[k] = 100.0 * (df[k] / 100.0) ** 0.5
    msgs, allok = [], True
    for params, a, b in (({}, 1.3, 0.95), ({"Take Profit Price Multiplier": 1.1, "Stop Loss Price Multiplier": 0.98}, 1.1, 0.98)):
        ok, m = one(df, params, a, b)
        allok &= ok
        msgs.append(m)
    return allok, " | ".join(msgs)
