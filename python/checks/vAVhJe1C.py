"""Independent check — 30M Options Swing Edge (vAVhJe1C): 30-minute bars (24 h synthetic) on a US stock chart (daily and 2-hour periods counted from 09:30 New York), orders at the bar close (process_orders_on_close), margin / commission / slippage off, one unit.
Daily and 2-hour suites (EMA 20/50/200, RSI 14/9, MACD, DMI 20/14, CCI, WaveTrend of the period's OHLC; lookahead off) give the bias; the chart adds the MACD-cross window, the seven-point score, the pullback window (barssince), the chop filter and the cooldowns; a signal against an open position closes it first (reversal); the ATR stop turns into break-even / trailing once the profit threshold is reached;
the trade-tracking variables are cleared at the end of the entry bar when the position was still flat at script time (so a trade from flat has no entry bar: the hold / time / theta exits never fire and the ATR is the current one), but survive a reversal. Uses the pending-order reference broker (simulate_ord, on_close).
Variants: defaults; Aggressive mode with a shorter MACD window (3) and pullback window 20, no chop filter; Safe mode (score 6), cooldowns 2 / 1, theta exit on, trail start 1.0 / trail 2.0."""
import numpy as np

from indep import bars, compare, np_atr, np_cci, np_periods, np_rsi, np_security_lookahead_off, np_sma, np_tr, run_conversion, simulate_ord
from pinelib import SymbolInfo

TV_ID = "vAVhJe1C"


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


def rma_na(x, n):
    out = np.full(len(x), np.nan)
    ok = ~np.isnan(x)
    run = 0
    s = None
    for i in range(len(x)):
        run = run + 1 if ok[i] else 0
        if run == n:
            s = i
            break
    if s is None:
        return out
    out[s] = x[s - n + 1:s + 1].mean()
    a = 1.0 / n
    for i in range(s + 1, len(x)):
        out[i] = a * x[i] + (1 - a) * out[i - 1]
    return out


def ffill(x):
    out = x.copy()
    for i in range(1, len(out)):
        if np.isnan(out[i]):
            out[i] = out[i - 1]
    return out


def dmi(h, l, c, ln, sm):
    up = np.r_[np.nan, np.diff(h)]
    dn = -np.r_[np.nan, np.diff(l)]
    with np.errstate(invalid="ignore", divide="ignore"):
        pdm = np.where(np.isnan(up), np.nan, np.where((up > dn) & (up > 0), up, 0.0))
        mdm = np.where(np.isnan(dn), np.nan, np.where((dn > up) & (dn > 0), dn, 0.0))
        trur = rma_na(np_tr(h, l, c, False), ln)
        plus = ffill(100 * rma_na(pdm, ln) / trur)
        minus = ffill(100 * rma_na(mdm, ln) / trur)
        tot = plus + minus
        adx = 100 * rma_na(np.abs(plus - minus) / np.where(tot == 0, 1.0, tot), sm)
    return plus, minus, adx


def suite(h, l, c):
    hl3 = (h + l + c) / 3.0
    m = ema_na(c, 12) - ema_na(c, 26)
    s = ema_na(m, 9)
    esa = ema_na(hl3, 10)
    dev = ema_na(np.abs(hl3 - esa), 10)
    with np.errstate(invalid="ignore", divide="ignore"):
        ci = np.where(dev != 0, (hl3 - esa) / (0.015 * dev), 0.0)
    w1 = ema_na(ci, 11)
    w2 = np_sma(w1, 4)
    pdi, mdi, adx = dmi(h, l, c, 20, 14)
    return dict(c=c, e20=ema_na(c, 20), e50=ema_na(c, 50), e200=ema_na(c, 200), r14=np_rsi(c, 14), r9=np_rsi(c, 9), m=m, s=s, hist=m - s,
                pdi=pdi, mdi=mdi, adx=adx, cci=np_cci(hl3, 20), w1=w1, w2=w2)


def htf_suite(df, minutes):
    h, l, c = (df[k].to_numpy() for k in ("high", "low", "close"))
    pid, last_of = np_periods(df, minutes)
    npd = pid[-1] + 1
    ph = np.array([h[pid == k].max() for k in range(npd)])
    pl = np.array([l[pid == k].min() for k in range(npd)])
    ste = suite(ph, pl, c[last_of])
    return {k: np_security_lookahead_off(v, pid, last_of) for k, v in ste.items()}


def barssince(cond):
    out = np.full(len(cond), np.nan)
    last = None
    for i, x in enumerate(cond):
        if x:
            last = i
        if last is not None:
            out[i] = i - last
    return out


def one(df, params, p):
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    sym = SymbolInfo.make("NASDAQ:XYZ", "stock", qty_step=1e-9)
    D, C2 = htf_suite(df, 1440), htf_suite(df, 120)
    K = suite(h, l, c)
    e20, e50, rsi, rsif = K["e20"], K["e50"], K["r14"], K["r9"]
    ml, sl_, hist = K["m"], K["s"], K["hist"]
    rma_ = np_sma(rsi, 14)
    atr = np_atr(h, l, c, 14)
    hl3 = (h + l + c) / 3.0
    pm = np.r_[np.nan, ml[:-1]]
    ps = np.r_[np.nan, sl_[:-1]]
    with np.errstate(invalid="ignore"):
        xu = (ml > sl_) & (pm <= ps)
        xd = (ml < sl_) & (pm >= ps)
    bsu, bsd = barssince(xu), barssince(xd)
    hist1 = np.r_[np.nan, hist[:-1]]
    c1 = np.r_[np.nan, c[:-1]]
    with np.errstate(invalid="ignore"):
        pcn = (l <= e20) | (l <= e50) | (rsi < 45)
        ppn = (h >= e20) | (h >= e50) | (rsi > 55)
    bsc, bsp = barssince(pcn), barssince(ppn)
    rhi = np.full(n, np.nan)
    rlo = np.full(n, np.nan)
    lb = p["cl"]
    for i in range(lb - 1, n):
        rhi[i] = h[i - lb + 1:i + 1].max()
        rlo[i] = l[i - lb + 1:i + 1].min()
    rhi1, rlo1 = np.r_[np.nan, rhi[:-1]], np.r_[np.nan, rlo[:-1]]
    thr = {"Aggressive": 4, "Balanced": 5, "Safe": 6}[p["mode"]]
    S = dict(le=None, lx=None, eb=None, ea=np.nan, hse=np.nan, lse=np.nan, stop=np.nan, prev=0.0)

    def orders(i, pos, info):
        out = []
        with np.errstate(invalid="ignore"):
            d_bull = D["c"][i] > D["e50"][i] and D["r14"][i] > 50
            d_bear = D["c"][i] < D["e50"][i] and D["r14"][i] < 50
            d_sb = D["c"][i] > D["e50"][i] and D["e50"][i] > D["e200"][i] and D["r14"][i] > 52
            d_sr = D["c"][i] < D["e50"][i] and D["e50"][i] < D["e200"][i] and D["r14"][i] < 48
            X = C2
            t_bull = X["c"][i] > X["e20"][i] and X["r14"][i] > 50 and X["m"][i] > X["s"][i]
            t_bear = X["c"][i] < X["e20"][i] and X["r14"][i] < 50 and X["m"][i] < X["s"][i]
            t_bs = X["c"][i] > X["e50"][i] and X["e20"][i] > X["e50"][i] and X["r14"][i] > 50 and X["m"][i] > X["s"][i]
            t_rs = X["c"][i] < X["e50"][i] and X["e20"][i] < X["e50"][i] and X["r14"][i] < 50 and X["m"][i] < X["s"][i]
            xh1 = X["hist"][i - 1] if i else np.nan
            t_br = X["hist"][i] > xh1 and X["r14"][i] > 45 and X["c"][i] > X["e20"][i]
            t_rr = X["hist"][i] < xh1 and X["r14"][i] < 55 and X["c"][i] < X["e20"][i]
            ch_bull = c[i] > e20[i] and e20[i] >= e50[i]
            ch_bear = c[i] < e20[i] and e20[i] <= e50[i]
            mbr = (not np.isnan(bsu[i])) and bsu[i] <= p["mw"]
            mrr = (not np.isnan(bsd[i])) and bsd[i] <= p["mw"]
            mbm = ml[i] > sl_[i] and hist[i] > hist1[i]
            mrm = ml[i] < sl_[i] and hist[i] < hist1[i]
            adx_ok = K["adx"][i] >= 16.0
            bs = sum(int(bool(x)) for x in (rsi[i] > 50, rsif[i] > rsi[i], K["w1"][i] > K["w2"][i], K["cci"][i] > 0, adx_ok and K["pdi"][i] > K["mdi"][i], mbm, c[i] > e20[i] and c[i] > e50[i]))
            rs = sum(int(bool(x)) for x in (rsi[i] < 50, rsif[i] < rsi[i], K["w1"][i] < K["w2"][i], K["cci"][i] < 0, adx_ok and K["mdi"][i] > K["pdi"][i], mrm, c[i] < e20[i] and c[i] < e50[i]))
            bok, rok = bs >= thr, rs >= thr
            pbc = (not np.isnan(bsc[i])) and bsc[i] <= p["pw"]
            pbp = (not np.isnan(bsp[i])) and bsp[i] <= p["pw"]
            prc = c[i] > e20[i] and c[i] > c1[i] and c[i] > o[i]
            prp = c[i] < e20[i] and c[i] < c1[i] and c[i] < o[i]
            nec = c[i] <= e20[i] + atr[i] * 2.3
            nep = c[i] >= e20[i] - atr[i] * 2.3
            comp = abs(e20[i] - e50[i]) < atr[i] * 0.35
            weak = K["adx"][i] < 15.0
            tight = (rhi[i] - rlo[i]) < atr[i] * 1.6
            ins = c[i] < rhi[i] and c[i] > rlo[i]
            chop = p["chop"] and weak and comp and tight and ins
            bbc = c[i] > rhi1[i] and mbm and rsi[i] > 50
            brc = c[i] < rlo1[i] and mrm and rsi[i] < 50
            tac = (not chop) or bbc or brc
            if p["mode"] == "Safe":
                cb, pb = d_bull and (t_bull or t_br), d_bear and (t_bear or t_rr)
            else:
                cb, pb = d_bull or t_bull or t_br, d_bear or t_bear or t_rr
            call_setup = cb and pbc and mbr and mbm and bok and prc and ch_bull and nec and tac
            put_setup = pb and pbp and mrr and mrm and rok and prp and ch_bear and nep and tac
            call_cont = d_sb and t_bs and ch_bull and mbr and bok and c[i] > e20[i] and nec and tac
            put_cont = d_sr and t_rs and ch_bear and mrr and rok and c[i] < e20[i] and nep and tac
        fcs, fps = call_setup or call_cont, put_setup or put_cont
        can = (S["le"] is None or i - S["le"] > p["ce"]) and (S["lx"] is None or i - S["lx"] > p["cx"])
        ce = bool(pos <= 0 and fcs and can) and not t_rs
        pe = bool(pos >= 0 and fps and can) and not t_bs
        if ce:
            if pos < 0:
                out.append(("close", "PUT"))
            out.append(("entry", "CALL", 1, None, None))
            S["le"], S["eb"], S["ea"], S["hse"], S["lse"], S["stop"] = i, i, atr[i], h[i], l[i], c[i] - atr[i] * 2.2
        if pe:
            if pos > 0:
                out.append(("close", "CALL"))
            out.append(("entry", "PUT", -1, None, None))
            S["le"], S["eb"], S["ea"], S["hse"], S["lse"], S["stop"] = i, i, atr[i], h[i], l[i], c[i] + atr[i] * 2.2
        if pos != 0:
            S["hse"] = h[i] if np.isnan(S["hse"]) else max(S["hse"], h[i])
            S["lse"] = l[i] if np.isnan(S["lse"]) else min(S["lse"], l[i])
        bit = i - S["eb"] if (pos != 0 and S["eb"] is not None) else 0
        aa = atr[i] if np.isnan(S["ea"]) else S["ea"]
        avg = info["ep"] if pos != 0 else np.nan
        with np.errstate(invalid="ignore"):
            if pos > 0:
                lpm = S["hse"] >= avg + aa * p["ts"]
                S["stop"] = max(avg + aa * 0.10, S["hse"] - aa * p["tr"]) if lpm else avg - aa * 2.2
            if pos < 0:
                spm = S["lse"] <= avg - aa * p["ts"]
                S["stop"] = min(avg - aa * 0.10, S["lse"] + aa * p["tr"]) if spm else avg + aa * 2.2
            cme = pos > 0 and bit >= 8 and xd[i] and rsi[i] < rma_[i] and c[i] < e20[i] and rs >= 4
            pme = pos < 0 and bit >= 8 and xu[i] and rsi[i] > rma_[i] and c[i] > e20[i] and bs >= 4
            chf = pos > 0 and bit >= 8 and t_rs
            phf = pos < 0 and bit >= 8 and t_bs
            cdf = pos > 0 and bit >= 8 and c[i] < e50[i] and ml[i] < sl_[i] and rsi[i] < 45
            pdf = pos < 0 and bit >= 8 and c[i] > e50[i] and ml[i] > sl_[i] and rsi[i] > 55
            lnp = p["theta"] and pos > 0 and bit >= 18 and S["hse"] < avg + aa * 0.60 and not t_bs
            snp = p["theta"] and pos < 0 and bit >= 18 and S["lse"] > avg - aa * 0.60 and not t_rs
            tex = pos != 0 and bit >= 78
        if pos > 0:
            out.append(("exit", "CALL Exit", "CALL", S["stop"], None))
        if pos < 0:
            out.append(("exit", "PUT Exit", "PUT", S["stop"], None))
        if cme or chf or cdf or lnp or tex:
            out.append(("close", "CALL"))
        if pme or phf or pdf or snp or tex:
            out.append(("close", "PUT"))
        if (S["prev"] > 0 or S["prev"] < 0) and pos == 0:
            S["lx"] = i
        if pos == 0:
            S["eb"], S["ea"], S["hse"], S["lse"], S["stop"] = None, np.nan, np.nan, np.nan, np.nan
        S["prev"] = pos
        return out

    ref = simulate_ord(o, h, l, c, orders, on_close=True)
    ok, d = compare(run_conversion(TV_ID, df, symbol=sym, tf="30", params=params, strategy_overrides={"commission_value": 0, "slippage": 0, "margin_long": 0, "margin_short": 0}), ref)
    return ok and len(ref) > 8, f"{d} (got {len(ref)})"


BASE = dict(mode="Balanced", mw=5, pw=12, chop=True, cl=24, ce=10, cx=4, theta=False, ts=2.0, tr=3.2)


def check():
    df = bars(30000, seed=33, freq="30min")
    for k in ("open", "high", "low", "close"):
        df[k] = 100 * (df[k] / 100) ** 0.3
    msgs, allok = [], True
    cases = (({}, {}),
             ({"Signal Mode": "Aggressive", "30M MACD Cross Active Bars": 3, "Pullback Active Bars": 20, "Use Chop Filter": False}, dict(mode="Aggressive", mw=3, pw=20, chop=False)),
             ({"Signal Mode": "Safe", "Cooldown After Entry Bars": 2, "Cooldown After Exit Bars": 1, "Use Theta No-Progress Exit": True, "Start Trailing After ATR Profit": 1.0, "Trailing Stop ATR": 2.0},
              dict(mode="Safe", ce=2, cx=1, theta=True, ts=1.0, tr=2.0)))
    for params, ov in cases:
        ok, m = one(df, params, {**BASE, **ov})
        allok &= ok
        msgs.append(m)
    return allok, " | ".join(msgs)
