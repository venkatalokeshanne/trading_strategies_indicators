"""Independent check — ES Master Flow Swing (pK4Xvayh): 3-minute bars on an ES-type future (point value 50, trading day from 17:00 Chicago), market orders at the next open, one contract, one position. Entry: close crossing the Keltner (20, 2; EMA of the close +/- 2 x EMA of the true range) band, close beyond both EMA50 and EMA200 in the same direction, ADX14 > 12, a bar starting 09:30-15:15 New York, no halt. Halts: the day's equity change (closed P&L plus the open position marked at the close, in dollars) <= -1000, reset on the first bar of a trading day; or 3 consecutive losing trades (sticky, as no trade can end it). Trail: initial low - 3 ATR (high + 3 ATR) set at the signal, then once in the position max(trail, low - 2.5 ATR) (min(trail, high + 2.5 ATR)); when the bar's low (high) reaches the trail the position is closed at the next open. The bar starting 15:10-15:15 closes everything, a halt closes any open position. Commission / slippage off on the pinelib side.
Variants: all rules on; consecutive breaker off and daily limit 300; session filter off, consecutive limit 6."""
import numpy as np
import pandas as pd

from indep import bars, compare, np_atr, np_dmi, np_ema, np_tr, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "pK4Xvayh"


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


def one(df, params, use_sess, use_daily, max_loss, use_consec, max_consec):
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    e50, e200 = np_ema(c, 50), np_ema(c, 200)
    atr = np_atr(h, l, c, 14)
    adx = np_dmi(h, l, c, 14)[2]
    basis = ema_na(c, 20)
    rng = ema_na(np_tr(h, l, c, handle_na=False), 20)
    up, lo = basis + rng * 2.0, basis - rng * 2.0
    pc = np.r_[np.nan, c[:-1]]
    pu, pl = np.r_[np.nan, up[:-1]], np.r_[np.nan, lo[:-1]]
    with np.errstate(invalid="ignore"):
        bo_b = (c > up) & (pc <= pu)
        bo_s = (c < lo) & (pc >= pl)
    ny = pd.to_datetime(df["time"], unit="ms", utc=True).dt.tz_convert("America/New_York")
    m = (ny.dt.hour * 60 + ny.dt.minute).to_numpy()
    ins = ((m >= 570) & (m < 915)) if use_sess else np.ones(n, bool)
    eod = ((m >= 910) & (m < 915)) if use_sess else np.zeros(n, bool)
    chi = pd.to_datetime(df["time"], unit="ms", utc=True).dt.tz_convert("America/Chicago")
    day = (chi.dt.tz_localize(None) - pd.Timedelta(hours=17)).dt.date.to_numpy()
    log = []
    S = dict(dse=None, halted=False, cl=0, lc=0, trail=np.nan, ep=np.nan, pp=0)

    def equity(i, pos):
        closed = sum(t[0] * (t[4] - t[2]) for t in log) * 50.0
        openp = pos * (c[i] - S["ep"]) * 50.0 if pos != 0 else 0.0
        return 50000.0 + closed + openp

    def orders(i, pos):
        out = []
        if pos != 0 and S["pp"] == 0:
            S["ep"] = o[i]
        S["pp"] = pos
        eq = equity(i, pos)
        if S["dse"] is None:
            S["dse"] = eq
        if i > 0 and day[i] != day[i - 1]:
            S["dse"] = eq
            S["halted"] = False
        if use_daily and eq - S["dse"] <= -max_loss:
            S["halted"] = True
        if len(log) > S["lc"]:
            lt = log[-1]
            S["cl"] = S["cl"] + 1 if lt[0] * (lt[4] - lt[2]) < 0 else 0
            S["lc"] = len(log)
        ch = use_consec and S["cl"] >= max_consec
        ok = not S["halted"] and not ch
        trend = adx[i] > 12
        bull = c[i] > e200[i] and c[i] > e50[i] and trend and bo_b[i]
        bear = c[i] < e200[i] and c[i] < e50[i] and trend and bo_s[i]
        ls = bull and ins[i] and ok and pos == 0
        ss = bear and ins[i] and ok and pos == 0
        if pos > 0:
            nt = l[i] - atr[i] * 2.5
            S["trail"] = l[i] - atr[i] * 3.0 if np.isnan(S["trail"]) else max(S["trail"], nt)
        if pos < 0:
            nt = h[i] + atr[i] * 2.5
            S["trail"] = h[i] + atr[i] * 3.0 if np.isnan(S["trail"]) else min(S["trail"], nt)
        if pos == 0:
            S["trail"] = np.nan
        tl = pos > 0 and not np.isnan(S["trail"]) and l[i] <= S["trail"]
        ts = pos < 0 and not np.isnan(S["trail"]) and h[i] >= S["trail"]
        if ls:
            out.append(("entry", 1))
            S["trail"] = l[i] - atr[i] * 3.0
        if ss:
            out.append(("entry", -1))
            S["trail"] = h[i] + atr[i] * 3.0
        if tl or ts:
            out.append(("close", pos))
        if eod[i] and pos != 0:
            out.append(("close", pos))
        if (S["halted"] or ch) and pos != 0:
            out.append(("close", pos))
        return out

    with np.errstate(invalid="ignore"):
        ref = simulate(o, h, l, c, orders, log=log)
    sym = SymbolInfo.make("CME_MINI:ES1!", "futures", qty_step=1e-9)
    ok, d = compare(run_conversion(TV_ID, df, symbol=sym, tf="3", params=params, strategy_overrides={"slippage": 0, "commission_value": 0}), ref)
    return ok and len(ref) > 10, f"{d} (got {len(ref)})"


def check():
    df = bars(40000, seed=151, freq="3min")
    for k in ("open", "high", "low", "close"):
        df[k] = 4000 * (df[k] / 100) ** 0.1
    msgs, allok = [], True
    cases = (({"Max Consecutive Losses": 8}, True, True, 1000.0, True, 8),
             ({"Consecutive Loss Breaker": False, "Max Daily Loss ($)": 300.0}, True, True, 300.0, False, 3),
             ({"Session Filter (Cash Only)": False, "Max Consecutive Losses": 6}, False, True, 1000.0, True, 6))
    for params, *args in cases:
        ok, m = one(df, params, *args)
        allok &= ok
        msgs.append(m)
    return allok, " | ".join(msgs)
