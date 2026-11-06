"""Independent check — Hyperliquid-Ready Webhook Strategy Template (8iAYXXsS): daily bars, market orders at the signal close (process_orders_on_close). EMA(fast) x> / x< EMA(slow) with an RSI side filter; stop and target = signal close -/+ ATR multiples, kept in stored levels. With the trail on, the stop ratchets (close -/+ trail x ATR, only if it improves on the stored trail stop by min-improvement x ATR); the exit (stop = trail or stored stop, limit = stored target) is issued on a signal bar or while a position is open at script time, unless the opposite signal fires. Uses the pending-order reference broker (simulate_ord, on_close). Commission / slippage / margin off on the pinelib side.
Variants: defaults; trail off, longs only; both sides, tighter trail with RSI thresholds 55 / 45 and EMAs 10 / 30."""
import numpy as np

from indep import bars, compare, np_atr, np_ema, np_rsi, run_conversion, simulate_ord

TV_ID = "8iAYXXsS"


def one(df, params, fl, sl_, rl, rs, longs, shorts, trail, slm, tpm, trm, mi):
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    ef, es = np_ema(c, fl), np_ema(c, sl_)
    rsi, atr = np_rsi(c, 14), np_atr(h, l, c, 14)
    with np.errstate(invalid="ignore"):
        pf, ps = np.r_[np.nan, ef[:-1]], np.r_[np.nan, es[:-1]]
        xu = (ef > es) & (pf <= ps)
        xd = (ef < es) & (pf >= ps)
    S = dict(sl=np.nan, tp=np.nan, tr=np.nan)

    def orders(i, pos):
        out = []
        with np.errstate(invalid="ignore"):
            ls = bool(longs and xu[i] and rsi[i] >= rl)
            ss = bool(shorts and xd[i] and rsi[i] <= rs)
            a = atr[i]
            if ls:
                S.update(sl=c[i] - a * slm, tp=c[i] + a * tpm, tr=c[i] - a * slm)
                out.append(("entry", "Long", 1, None, None))
            if ss:
                S.update(sl=c[i] + a * slm, tp=c[i] - a * tpm, tr=c[i] + a * slm)
                out.append(("entry", "Short", -1, None, None))
            if trail and pos > 0 and not ls and not ss:
                cand = c[i] - a * trm
                if cand > S["tr"] + a * mi:
                    S["tr"] = cand
            if trail and pos < 0 and not ls and not ss:
                cand = c[i] + a * trm
                if cand < S["tr"] - a * mi:
                    S["tr"] = cand
            stop = S["tr"] if trail else S["sl"]
            nn = lambda v: None if np.isnan(v) else v
            if (ls or pos > 0) and not ss:
                out.append(("exit", "Long-X", "Long", nn(stop), nn(S["tp"])))
            if (ss or pos < 0) and not ls:
                out.append(("exit", "Short-X", "Short", nn(stop), nn(S["tp"])))
        return out

    ref = simulate_ord(o, h, l, c, orders, on_close=True)
    ok, d = compare(run_conversion(TV_ID, df, params=params, strategy_overrides={"commission_value": 0, "slippage": 0, "margin_long": 0, "margin_short": 0}), ref)
    return ok and len(ref) > 8, f"{d} (got {len(ref)})"


def check():
    df = bars(3000, seed=404)
    msgs, allok = [], True
    cases = (({}, (21, 55, 50, 50, True, True, True, 1.5, 3.0, 2.0, 0.25)),
             ({"Enable Shorts": False, "ATR Trailing Stop (ratchet)": False}, (21, 55, 50, 50, True, False, False, 1.5, 3.0, 2.0, 0.25)),
             ({"Fast EMA": 10, "Slow EMA": 30, "RSI ≥ for Longs": 55, "RSI ≤ for Shorts": 45, "Trail × ATR": 1.0, "Min improvement to re-alert (× ATR)": 0.0,
               "Stop-Loss  × ATR": 2.0, "Take-Profit × ATR": 5.0}, (10, 30, 55, 45, True, True, True, 2.0, 5.0, 1.0, 0.0)))
    for params, args in cases:
        ok, m = one(df, params, *args)
        allok &= ok
        msgs.append(m)
    return allok, " | ".join(msgs)
