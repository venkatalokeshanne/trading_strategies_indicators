"""Independent check — Trend Pulse Channel Strategy (vJc6IOTz): daily bars, market orders at the next open, long only. alpha: beta = (1 - cos(2 pi / period)) / (1.414^(2 / poles) - 1), alpha = -beta + sqrt(beta^2 + 2 beta); EMA length = max(1, round(2 / alpha)); the filter is the source (hlc3) passed through `poles` EMAs of that length in cascade, the same for the true range (ta.tr(true)); optional lag reduction x + (x - x[lag]) with lag = int((period - 1) / (2 poles)); optional fast blend with the single-pole version. upper = filter + filtered TR x multiplier. Close crossing above the upper band (from 2018-01-01) enters long; crossing back under it exits. Margin / commission / slippage off on the pinelib side.
Variants: defaults (4 poles, period 144); 2 poles / period 30 with reduced lag, fast response and multiplier 1; 9 poles / period 60."""
import numpy as np

from indep import bars, compare, np_tr, run_conversion, simulate

TV_ID = "vJc6IOTz"


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


def cascade(x, a, p):
    n = max(1, int(np.floor(2 / a + 0.5)))
    r = ema_na(x, n)
    for _ in range(p - 1):
        r = ema_na(r, n)
    return r


def one(df, params, poles, period, mult, lag_mode, fast):
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    t = df["time"].to_numpy()
    n = len(c)
    src = (h + l + c) / 3
    tr = np_tr(h, l, c, handle_na=True)
    beta = (1 - np.cos(2 * np.pi / period)) / (1.414 ** (2 / poles) - 1)
    alpha = -beta + np.sqrt(beta * beta + 2 * beta)
    lag = int((period - 1) / (2 * poles)) if lag_mode else 0
    if lag_mode:
        sl = np.r_[np.full(lag, np.nan), src[:-lag]]
        tl = np.r_[np.full(lag, np.nan), tr[:-lag]]
        sd = np.where(np.isnan(sl), src, src + (src - sl))
        td = np.where(np.isnan(tl), tr, tr + (tr - tl))
    else:
        sd, td = src, tr
    filt, ftr = cascade(sd, alpha, poles), cascade(td, alpha, poles)
    if fast:
        filt = (filt + cascade(sd, alpha, 1)) / 2
        ftr = (ftr + cascade(td, alpha, 1)) / 2
    up = filt + ftr * mult
    pc, pu = np.r_[np.nan, c[:-1]], np.r_[np.nan, up[:-1]]
    with np.errstate(invalid="ignore"):
        xu = (c > up) & (pc <= pu)
        xd = (c < up) & (pc >= pu)
    inr = (t >= 1514764800000) & (t <= 3155759940000)

    def orders(i, pos):
        out = []
        if xu[i] and inr[i]:
            out.append(("entry", 1))
        if xd[i] and inr[i] and pos > 0:
            out.append(("close", 1))
        return out

    ref = simulate(o, h, l, c, orders)
    ok, d = compare(run_conversion(TV_ID, df, params=params, strategy_overrides={"slippage": 0, "commission_value": 0}), ref)
    return ok and len(ref) > 5, f"{d} (got {len(ref)})"


def check():
    df = bars(6000, seed=19)
    msgs, allok = [], True
    cases = (({}, (4, 144, 1.414, False, False)),
             ({"Poles": 2, "Period": 30, "Range Multiplier": 1.0, "Reduced Lag": True, "Fast Response": True}, (2, 30, 1.0, True, True)),
             ({"Poles": 9, "Period": 60}, (9, 60, 1.414, False, False)))
    for params, args in cases:
        ok, m = one(df, params, *args)
        allok &= ok
        msgs.append(m)
    return allok, " | ".join(msgs)
