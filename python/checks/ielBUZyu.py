"""Independent check — Strategy 250 XAUUSD Composite Quality Score (ielBUZyu): daily bars, process_orders_on_close, one position. Donchian channel = highest high / lowest low of the previous 50 bars; a close above (below) it is a break. The side is long when the close is above the channel high (otherwise the short formulas apply). Score = clamp(EMA200 slope / 0.0003, +/-1.5) + 2 x (bias - 0.5) (bias = previous close in the previous 600-bar range; mirrored for shorts) + clamp(distance from the EMA200 in ATR14 / 3, 0, 1) - [2 x share of the last 20 closes within +/- 1 ATR of the channel level + min(2, sweep in ATR) + 2 x max(0, 0.5 - previous close position in the channel) (mirrored)]. Enter when flat, broken, score >= minimum and the slope has the same sign; exit on a close back through the other side or after N bars held.
Commission off on the pinelib side. Variants: default minimum 0.8 with a low minimum -1, and a 10-bar maximum hold with longs only."""
import numpy as np
import pandas as pd

from indep import bars, compare, np_atr, np_ema, run_conversion, simulate

TV_ID = "ielBUZyu"


def one(df, params, mins, hold, shorts):
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    sh = lambda x, k=1: np.r_[np.full(k, np.nan), x[:-k]]
    dh = pd.Series(sh(h)).rolling(50).max().to_numpy()
    dl = pd.Series(sh(l)).rolling(50).min().to_numpy()
    mh = pd.Series(sh(h)).rolling(600).max().to_numpy()
    ml = pd.Series(sh(l)).rolling(600).min().to_numpy()
    ema = np_ema(c, 200)
    atr = np_atr(h, l, c, 14)
    plow = pd.Series(sh(l, 20)).rolling(50).min().to_numpy()
    rlow = pd.Series(sh(l)).rolling(20).min().to_numpy()
    phigh = pd.Series(sh(h, 20)).rolling(50).max().to_numpy()
    rhigh = pd.Series(sh(h)).rolling(20).max().to_numpy()
    S = dict(eb=None)

    def orders(i, pos):
        out = []
        if i < 650:
            return out
        base = ema[i - 30]
        slope = (ema[i] - base) / (base * 30) if base > 0 else 0.0
        ss = min(1.5, max(-1.5, slope / 0.0003))
        lb = c[i] > dh[i]
        sb = c[i] < dl[i]
        rng = mh[i] - ml[i]
        ready = not (np.isnan(dh[i]) or np.isnan(dl[i]) or np.isnan(ema[i]) or np.isnan(atr[i]) or np.isnan(mh[i]) or np.isnan(base)) and atr[i] > 0 and rng > 0
        q = np.nan
        if ready:
            bias = (c[i - 1] - ml[i]) / rng
            bsc = (bias - 0.5) * 2 if lb else (0.5 - bias) * 2
            dist = (c[i] - ema[i]) / atr[i] if lb else (ema[i] - c[i]) / atr[i]
            esc = min(1.0, max(0.0, dist / 3))
            lvl = dh[i] if lb else dl[i]
            acc = np.mean([(c[i - j] >= lvl - atr[i]) and (c[i - j] <= lvl + atr[i]) for j in range(1, 21)])
            if lb:
                sw = max(0.0, (plow[i] - rlow[i]) / atr[i]) if not (np.isnan(plow[i]) or np.isnan(rlow[i])) else np.nan
            else:
                sw = max(0.0, (rhigh[i] - phigh[i]) / atr[i]) if not (np.isnan(phigh[i]) or np.isnan(rhigh[i])) else np.nan
            rp = (c[i - 1] - dl[i]) / (dh[i] - dl[i]) if dh[i] - dl[i] > 0 else np.nan
            rpen = max(0.0, 0.5 - rp) * 2 if lb else max(0.0, rp - 0.5) * 2
            q = ss + bsc + esc - (acc * 2 + min(2.0, sw) + rpen)
        held = i - S["eb"] if S["eb"] is not None else None
        le = ready and pos == 0 and lb and q >= mins and slope > 0
        se = ready and shorts and pos == 0 and sb and q >= mins and slope < 0
        lx = pos > 0 and (c[i] < dl[i] or (held is not None and held >= hold))
        sx = pos < 0 and (c[i] > dh[i] or (held is not None and held >= hold))
        if le:
            out.append(("entry", 1))
            S["eb"] = i
        if se:
            out.append(("entry", -1))
            S["eb"] = i
        if lx or sx:
            out.append(("close", pos))
            S["eb"] = None
        return out

    with np.errstate(invalid="ignore"):
        ref = simulate(o, h, l, c, orders, on_close=True)
    ok, d = compare(run_conversion(TV_ID, df, params=params, strategy_overrides={"commission_value": 0}), ref)
    return ok and len(ref) > 5, f"{d} (got {len(ref)})"


def check():
    df = bars(5000, seed=99)
    for k in ("open", "high", "low", "close"):
        df[k] = 100 * (df[k] / 100) ** 0.6
    msgs, allok = [], True
    for params, args in (({}, (0.8, 80, True)),
                         ({"Minimum Quality Score": -1.0}, (-1.0, 80, True)),
                         ({"Minimum Quality Score": -2.0, "Máximo de barras en posición": 10, "Permitir shorts": False}, (-2.0, 10, False))):
        ok, m = one(df, params, *args)
        allok &= ok
        msgs.append(m)
    return allok, " | ".join(msgs)
