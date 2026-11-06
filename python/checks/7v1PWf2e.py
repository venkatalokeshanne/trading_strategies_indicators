"""Independent check — Adaptive Regime Momentum [JOAT] (7v1PWf2e): daily bars, market orders at the next open, one position. combo MA = (ALMA(close, 34, 0.85, 6) + EMA34(2 EMA34 - EMA34(EMA34))) / 2 with the ALMA weights exp(-(i - m)^2 / (2 s^2)) (m = offset (n - 1), s = n / sigma, i = 0 the oldest bar); long: the combo MA rose on each of the last `confirm` bars, close above it, volume RSI(8)/50 > 1.0 and RSI14 > 50; short mirrored. While in a trade the exit (stop 2.5 ATR, target 4 ATR from the average entry price, current ATR) is re-issued every bar (working from the bar after the fill); the position is also closed at the next open when the close falls under (rises over) the MA by 1.5 ATR or the MA slope turns against it. Commission off on the pinelib side.
Variants: defaults; MA 20, 2 confirm bars with the volume and RSI filters off."""
import numpy as np

from indep import bars, compare, np_atr, np_rsi, run_conversion, simulate

TV_ID = "7v1PWf2e"


def ema_na(x, n):
    out = np.full(len(x), np.nan)
    idx = np.flatnonzero(~np.isnan(x))
    if len(idx) < n:
        return out
    s = idx[0] + n - 1
    out[s] = x[idx[0]:s + 1].mean()
    k = 2.0 / (n + 1)
    for i in range(s + 1, len(x)):
        out[i] = k * x[i] + (1 - k) * out[i - 1]
    return out


def alma(x, n, off, sig):
    m, s = off * (n - 1), n / sig
    w = np.exp(-((np.arange(n) - m) ** 2) / (2 * s * s))
    out = np.full(len(x), np.nan)
    for i in range(n - 1, len(x)):
        out[i] = (x[i - n + 1:i + 1] * w).sum() / w.sum()
    return out


def one(df, params, ln, conf, volf, rsif):
    o, h, l, c, v = (df[k].to_numpy() for k in ("open", "high", "low", "close", "volume"))
    n = len(c)
    e1 = ema_na(c, ln)
    e2 = ema_na(e1, ln)
    zl = ema_na(2.0 * e1 - e2, ln)
    cm = (alma(c, ln, 0.85, 6.0) + zl) / 2.0
    atr, rsi, vrsi = np_atr(h, l, c, 14), np_rsi(c, 14), np_rsi(v, 8) / 50.0

    def orders(i, pos):
        out = []
        if i < conf + 1:
            return out
        with np.errstate(invalid="ignore"):
            up = all(cm[i - k] - cm[i - k - 1] > 0 for k in range(conf))
            dn = all(cm[i - k] - cm[i - k - 1] < 0 for k in range(conf))
            sl = cm[i] - cm[i - 1]
            lc = up and c[i] > cm[i] and ((not volf) or vrsi[i] > 1.0) and ((not rsif) or rsi[i] > 50)
            sc = dn and c[i] < cm[i] and ((not volf) or vrsi[i] > 1.0) and ((not rsif) or rsi[i] < 50)
            lx = c[i] < cm[i] - atr[i] * 1.5 or sl < 0
            sx = c[i] > cm[i] + atr[i] * 1.5 or sl > 0
        if lc and pos == 0:
            out.append(("entry", 1))
        if sc and pos == 0:
            out.append(("entry", -1))
        if lx and pos > 0:
            out.append(("close", 1))
        if sx and pos < 0:
            out.append(("close", -1))
        return out

    stop = lambda i, pos, ep, eb: (ep - pos * 2.5 * atr[i - 1]) if i > eb else None
    tgt = lambda i, pos, ep, eb: (ep + pos * 4.0 * atr[i - 1]) if i > eb else None
    with np.errstate(invalid="ignore"):
        ref = simulate(o, h, l, c, orders, stop=stop, target=tgt)
    ok, d = compare(run_conversion(TV_ID, df, params=params, strategy_overrides={"commission_value": 0}), ref)
    return ok and len(ref) > 5, f"{d} (got {len(ref)})"


def check():
    df = bars(8000, seed=71)
    msgs, allok = [], True
    for params, args in (({}, (34, 3, True, True)),
                         ({"MA Length": 20, "Slope Confirm Bars": 2, "Use Volume Filter": False, "Use RSI Filter": False}, (20, 2, False, False))):
        ok, m = one(df, params, *args)
        allok &= ok
        msgs.append(m)
    return allok, " | ".join(msgs)
