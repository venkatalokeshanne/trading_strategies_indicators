"""Independent check — Prism Strategy (LB3VE9t8), hourly bars, market orders at the next open, fixed 10 units, no commission.
The MA stack / RSI state machine, the valuewhen stop and target at the signal bar, the Fibonacci levels of the 100-bar range, the nearest
level on each side of the close combined with EMA12, the ratcheting structural stop and the exit trigger (a later bar's low / high
reaching the stop / the target resets the state and closes at the next open) are rebuilt in numpy and replayed against the
quantity-aware reference broker."""
import numpy as np

from indep import bars, compare_q, np_atr, np_ema, np_rsi, np_sma, run_conversion, simulate_brackets
from pinelib import SymbolInfo

TV_ID = "LB3VE9t8"
QTY = 10.0


def roll(x, n, fn):
    out = np.full(len(x), np.nan)
    for i in range(n - 1, len(x)):
        out[i] = fn(x[i - n + 1:i + 1])
    return out


def reference(df, atr_mult=1.5, rr=2.0, lb=100):
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    sma5 = np_sma(c, 5)
    e12, e15, e30, e60 = (np_ema(c, k) for k in (12, 15, 30, 60))
    rsi = np_rsi(c, 14)
    atr = np_atr(h, l, c, 14)
    hp, lp = roll(h, lb, np.max), roll(l, lb, np.min)
    S = dict(state=0, stop_l=np.nan, tgt_l=np.nan, stop_s=np.nan, tgt_s=np.nan, trail=np.nan)

    def orders(i, info):
        out = []
        with np.errstate(invalid="ignore"):
            bull = sma5[i] > e15[i] > e30[i] > e60[i]
            bear = sma5[i] < e15[i] < e30[i] < e60[i]
            ls = bull and rsi[i] > 50 and S["state"] == 0
            ss = bear and rsi[i] < 50 and S["state"] == 0
        if ls:
            S["state"] = 1
            S["stop_l"] = l[i] - atr[i] * atr_mult
            S["tgt_l"] = c[i] + abs(c[i] - S["stop_l"]) * rr
        if ss:
            S["state"] = -1
            S["stop_s"] = h[i] + atr[i] * atr_mult
            S["tgt_s"] = c[i] - abs(c[i] - S["stop_s"]) * rr
        isl, iss = S["state"] == 1, S["state"] == -1
        a_stop = S["stop_l"] if isl else S["stop_s"] if iss else np.nan
        a_tgt = S["tgt_l"] if isl else S["tgt_s"] if iss else np.nan
        rng = hp[i] - lp[i]
        fibs = [lp[i], hp[i] - rng * 0.764, hp[i] - rng * 0.618, hp[i] - rng * 0.5, hp[i] - rng * 0.382, hp[i] - rng * 0.214,
                hp[i], hp[i] + rng * 0.272, hp[i] + rng * 0.618]
        below = [f for f in fibs if f < c[i]]
        above = [f for f in fibs if f > c[i]]
        sup = max(below) if below else np.nan
        res = min(above) if above else np.nan
        e_below = e12[i] if e12[i] < c[i] else np.nan
        e_above = e12[i] if e12[i] > c[i] else np.nan
        wl = np.nanmax([e_below, sup]) if not (np.isnan(e_below) and np.isnan(sup)) else np.nan
        ws = np.nanmin([e_above, res]) if not (np.isnan(e_above) and np.isnan(res)) else np.nan
        adv = np.nan
        if isl and not np.isnan(wl):
            adv = wl - atr[i] * 0.2
        elif iss and not np.isnan(ws):
            adv = ws + atr[i] * 0.2
        if ls or ss:
            S["trail"] = a_stop if np.isnan(adv) else adv
        elif isl and not np.isnan(adv):
            S["trail"] = adv if np.isnan(S["trail"]) else max(S["trail"], adv)
        elif iss and not np.isnan(adv):
            S["trail"] = adv if np.isnan(S["trail"]) else min(S["trail"], adv)
        else:
            S["trail"] = np.nan
        cur = a_stop if np.isnan(S["trail"]) else S["trail"]
        with np.errstate(invalid="ignore"):
            sell = isl and not ls and (l[i] <= cur or h[i] >= a_tgt)
            buy = iss and not ss and (h[i] >= cur or l[i] <= a_tgt)
        if sell or buy:
            S["state"] = 0
        if ls:
            out.append(("entry", "Long", 1, QTY))
        if ss:
            out.append(("entry", "Short", -1, QTY))
        if sell:
            out.append(("close", "Long"))
        if buy:
            out.append(("close", "Short"))
        return out

    return simulate_brackets(o, h, l, c, orders, pyramiding=1, qty_step=1e-9)


def check():
    df = bars(20000, seed=19, freq="h")
    lc = np.log(df["close"].to_numpy() / 100)
    det = lc - np.polyval(np.polyfit(np.arange(len(lc)), lc, 1), np.arange(len(lc)))
    rel = {k: df[k].to_numpy() / df["close"].to_numpy() for k in ("open", "high", "low", "close")}
    for k in rel:
        df[k] = 100 * np.exp(0.5 * det) * rel[k] ** 0.5
    sym = SymbolInfo.make("BINANCE:BTCUSDT", "crypto", qty_step=1e-9)
    ov = {"margin_long": 0, "margin_short": 0, "commission_value": 0, "slippage": 0, "default_qty_type": "fixed", "default_qty_value": QTY}
    cases = (({}, {}), ({"ATR Stop Multiplier": 2.5, "Target Reward Ratio": 1.2, "Auto-Fib Lookback Bars": 50}, dict(atr_mult=2.5, rr=1.2, lb=50)))
    msgs, ok_all = [], True
    for params, kw in cases:
        ref = reference(df, **kw)
        ok, d = compare_q(run_conversion(TV_ID, df, symbol=sym, tf="60", params=params, strategy_overrides=ov), ref)
        ok_all = ok_all and ok and len(ref) > 12
        msgs.append(f"{d} (got {len(ref)})")
    return ok_all, " | ".join(msgs)
