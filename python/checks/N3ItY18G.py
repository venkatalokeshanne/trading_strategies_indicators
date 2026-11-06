"""Independent check — Vortex Reversal Engine (N3ItY18G), hourly bars, market entries at the next open, fixed 10 units, slippage
0. Bollinger bands (population stdev), RSI, ATR, ADX, the bars-since-touch counters, the cooldown and the UTC session filter are rebuilt
in numpy; the exit orders issued with each entry (limit / stop from the signal close, optional 50 % partial with a second order that
adds a tick-form trailing stop) are replayed against the quantity-aware reference broker."""
import numpy as np
import pandas as pd

from indep import bars, compare_q, np_atr, np_dmi, np_rsi, np_sma, run_conversion, simulate_brackets
from pinelib import SymbolInfo

TV_ID = "N3ItY18G"
QTY = 10.0
TICK = 0.01


def bars_since(cond):
    out = np.full(len(cond), np.nan)
    last = None
    for i, v in enumerate(cond):
        if v:
            last = i
        out[i] = np.nan if last is None else i - last
    return out


def reference(df, partial=False, trail=True, session=None, adx_max=30.0, vol_f=False):
    o, h, l, c, v = (df[k].to_numpy() for k in ("open", "high", "low", "close", "volume"))
    n = len(c)
    basis = np_sma(c, 20)
    dev = np.array([np.std(c[i - 19:i + 1]) if i >= 19 else np.nan for i in range(n)]) * 2.0
    up, lo = basis + dev, basis - dev
    rsi = np_rsi(c, 14)
    atr = np_atr(h, l, c, 14)
    adx = np_dmi(h, l, c, 14)[2]
    vol_sma = np_sma(v, 20)
    hr = pd.to_datetime(df["time"], unit="ms", utc=True).dt.hour.to_numpy()
    with np.errstate(invalid="ignore"):
        tl = bars_since(l <= lo) <= 5
        tu = bars_since(h >= up) <= 5
        os_ = bars_since(rsi < 30) <= 5
        ob_ = bars_since(rsi > 70) <= 5
    rsi1 = np.r_[np.nan, rsi[:-1]]
    S = dict(ll=-999, ls=-999)

    def sess_ok(i):
        if session is None:
            return True
        asia, lon, ny = hr[i] < 8, 8 <= hr[i] < 16, 13 <= hr[i] < 22
        return {"Asia": asia, "London": lon, "New York": ny, "London+NY": lon or ny}[session]

    def orders(i, info):
        out = []
        flat = info["pos"] == 0
        rng = (adx[i] < adx_max)
        mid = (h[i] + l[i]) / 2
        vol_ok = (not vol_f) or v[i] > vol_sma[i]
        cool = (i - S["ll"]) >= 5 and (i - S["ls"]) >= 5
        long_sig = flat and rng and (c[i] > lo[i] and c[i] < basis[i] and tl[i]) and os_[i] and (rsi[i] > rsi1[i] and rsi[i] < 55) \
            and (c[i] > o[i] and c[i] > mid) and vol_ok and sess_ok(i) and cool
        short_sig = flat and rng and (c[i] < up[i] and c[i] > basis[i] and tu[i]) and ob_[i] and (rsi[i] < rsi1[i] and rsi[i] > 45) \
            and (c[i] < o[i] and c[i] < mid) and vol_ok and sess_ok(i) and cool
        for d, sig, name, k in ((1, long_sig, "Long", "L"), (-1, short_sig, "Short", "S")):
            if not sig:
                continue
            S["ll" if d == 1 else "ls"] = i
            tp, sl, tp2 = c[i] + d * atr[i] * 1.0, c[i] - d * atr[i] * 3.5, c[i] + d * atr[i] * 3.0
            out.append(("entry", name, d, QTY))
            if partial:
                out.append(("exit", f"{k}X1", name, 50.0, sl, tp))
                if trail:
                    tk = float(np.floor(atr[i] * 1.5 / TICK + 0.5))
                    out.append(("exit", f"{k}X2", name, None, sl, tp2, tk, None, tk))
                else:
                    out.append(("exit", f"{k}X2", name, None, sl, tp2))
            else:
                out.append(("exit", f"{k}X", name, None, sl, tp))
        return out

    return simulate_brackets(o, h, l, c, orders, pyramiding=1, tick=TICK, qty_step=1e-9)


def check():
    df = bars(30000, seed=24, freq="h")
    lc = np.log(df["close"].to_numpy() / 100)
    det = lc - np.polyval(np.polyfit(np.arange(len(lc)), lc, 1), np.arange(len(lc)))
    rel = {k: df[k].to_numpy() / df["close"].to_numpy() for k in ("open", "high", "low", "close")}
    for k in rel:
        df[k] = 100 * np.exp(0.5 * det) * rel[k] ** 0.5
    sym = SymbolInfo.make("OANDA:EURUSD", "crypto", mintick=0.01, qty_step=1e-9)
    ov = {"margin_long": 0, "margin_short": 0, "commission_value": 0, "slippage": 0, "default_qty_type": "fixed", "default_qty_value": QTY}
    cases = (({}, {}),
             ({"Partial Exit Mode": True}, dict(partial=True)),
             ({"Partial Exit Mode": True, "Trailing Stop (partial)": False, "Session Filter": True, "Session": "New York", "ADX Max (Range Filter)": 40},
              dict(partial=True, trail=False, session="New York", adx_max=40.0)))
    msgs, ok_all = [], True
    for params, kw in cases:
        ref = reference(df, **kw)
        ok, d = compare_q(run_conversion(TV_ID, df, symbol=sym, tf="60", params=params, strategy_overrides=ov), ref)
        ok_all = ok_all and ok and len(ref) > 12
        msgs.append(f"{d} (got {len(ref)})")
    return ok_all, " | ".join(msgs)
