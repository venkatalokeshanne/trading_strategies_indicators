"""Independent check — NovaTrade IRB v2.0.0 (emAsZ8tc), hourly bars priced like EURUSD (mintick 0.00001, pip 0.0001).
Indicators (EMA 10/20/40/50, ATR, ADX, the 4-hour EMA20 with lookahead off on UTC 4-hour blocks) are rebuilt in numpy; the state
machine (pending buy/sell stop for up to 20 bars, replacement on a new setup, cancel, fill, trailing EMA stop that never loosens,
time stop after 40 bars) is replayed against the quantity-aware reference broker, with the 1 %-of-equity lot sizing computed from
a mirror equity (initial capital + closed P&L from the reference log + open P&L at the close)."""
import numpy as np

from indep import (bars, compare_q, np_atr, np_dmi, np_ema, np_periods, np_security_lookahead_off, run_conversion,
                   simulate_brackets)
from pinelib import SymbolInfo

TV_ID = "emAsZ8tc"
PIP, BUF = 0.0001, 0.0001
FLAT, PLONG, PSHORT, LONG, SHORT = 0, 1, 2, 3, 4


def reference(df, confirm=3, trail_n=40):
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    e10, e20, e50, et = np_ema(c, 10), np_ema(c, 20), np_ema(c, 50), np_ema(c, trail_n)
    atr = np_atr(h, l, c, 14)
    adx = np_dmi(h, l, c, 14)[2]
    pid, last_of = np_periods(df, 240, start_minutes=0, tz="UTC")
    h4 = np_security_lookahead_off(np_ema(c[last_of], 20), pid, last_of)
    log = []
    S = dict(state=FLAT, hi=np.nan, lo=np.nan, pend=0, posb=0, stop=np.nan, prev=None)

    def nz(x, y=0.0):
        return y if np.isnan(x) else x

    def lots(i, ep, sp, info):
        closed = sum((1 if d == 1 else -1) * (xp - epr) * q for d, _, epr, _, xp, q in log)
        openp = sum(x["d"] * x["q"] * (c[i] - x["ep"]) for x in info["lots"])
        eq = 100000.0 + closed + openp
        sd = abs(ep - sp) / PIP
        raw = eq * 0.01 / (sd * 10.0) if sd > 0 else 0.01
        cl = max(0.01, min(1.0, raw))
        return np.floor(cl * 100.0 + 0.5) / 100.0 * 100000

    def orders(i, info):
        out = []
        pos = info["pos"]
        was_flat = S["prev"] is not None and S["prev"] == 0
        S["prev"] = pos
        warm = i >= max(50, max(confirm, trail_n))
        rng = h[i] - l[i]
        up_irb = rng > 0 and o[i] <= h[i] - 0.45 * rng and c[i] <= h[i] - 0.45 * rng
        dn_irb = rng > 0 and o[i] >= l[i] + 0.45 * rng and c[i] >= l[i] + 0.45 * rng
        slope = (e20[i] - nz(e20[i - 20] if i >= 20 else np.nan)) / atr[i] if nz(atr[i]) > 0 else 0.0
        t_up, t_dn = slope >= 0.4, slope <= -0.4
        hb = h4[i - 20] if i >= 20 else np.nan
        h4_up = not np.isnan(h4[i]) and not np.isnan(hb) and h4[i] > hb
        h4_dn = not np.isnan(h4[i]) and not np.isnan(hb) and h4[i] < hb
        sw = adx[i] >= 20
        oe = (rng / atr[i] if nz(atr[i]) > 0 else 0.0) <= 2.0
        bull = e10[i] > e20[i] > e50[i]
        bear = e10[i] < e20[i] < e50[i]

        def conf(sign):
            for k in range(confirm):
                j = i - k
                if j < 0 or np.isnan(e10[j]) or not (sign * (c[j] - e10[j]) > 0):
                    return False
            return True

        sig_l = warm and up_irb and t_up and h4_up and sw and oe and bull and conf(1)
        sig_s = warm and dn_irb and t_dn and h4_dn and sw and oe and bear and conf(-1)
        now_l, now_s, now_f = pos > 0, pos < 0, pos == 0
        fill_l, fill_s, closed = now_l and was_flat, now_s and was_flat, now_f and not was_flat
        if closed:
            S.update(state=FLAT, hi=np.nan, lo=np.nan, pend=0, posb=0, stop=np.nan)
        if fill_l and S["state"] == PLONG:
            S.update(state=LONG, posb=0, stop=S["lo"] - BUF)
        if fill_s and S["state"] == PSHORT:
            S.update(state=SHORT, posb=0, stop=S["hi"] + BUF)
        if S["state"] in (PLONG, PSHORT):
            S["pend"] += 1
        if S["state"] in (LONG, SHORT):
            S["posb"] += 1
        if S["state"] == PLONG and S["pend"] >= 20:
            out.append(("cancel", "Long"))
            S.update(state=FLAT, hi=np.nan, lo=np.nan, pend=0)
        if S["state"] == PSHORT and S["pend"] >= 20:
            out.append(("cancel", "Short"))
            S.update(state=FLAT, hi=np.nan, lo=np.nan, pend=0)
        st = S["state"]
        if st == FLAT and sig_l or st == PLONG and sig_l:
            ep, sp = h[i] + BUF, l[i] - BUF
            out.append(("entry", "Long", 1, lots(i, ep, sp, info), ep, None))
            S.update(hi=h[i], lo=l[i], pend=0)
            if st == FLAT:
                S["state"] = PLONG
        elif st == FLAT and sig_s or st == PSHORT and sig_s:
            ep, sp = l[i] - BUF, h[i] + BUF
            out.append(("entry", "Short", -1, lots(i, ep, sp, info), ep, None))
            S.update(hi=h[i], lo=l[i], pend=0)
            if st == FLAT:
                S["state"] = PSHORT
        if S["state"] == LONG:
            S["stop"] = max(nz(S["stop"], et[i]), et[i])
            out.append(("exit", "Long Exit", "Long", None, S["stop"], None))
            if S["posb"] >= 40:
                out.append(("close", "Long"))
        if S["state"] == SHORT:
            S["stop"] = min(nz(S["stop"], et[i]), et[i])
            out.append(("exit", "Short Exit", "Short", None, S["stop"], None))
            if S["posb"] >= 40:
                out.append(("close", "Short"))
        return out

    return simulate_brackets(o, h, l, c, orders, pyramiding=1, tick=0.00001, log=log)


def check():
    df = bars(30000, seed=8, freq="h")
    lc = np.log(df["close"].to_numpy() / 100)
    det = lc - np.polyval(np.polyfit(np.arange(len(lc)), lc, 1), np.arange(len(lc)))
    rel = {k: df[k].to_numpy() / df["close"].to_numpy() for k in ("open", "high", "low", "close")}
    for k in rel:
        df[k] = 1.1 * np.exp(0.3 * det) * rel[k] ** 0.3
    sym = SymbolInfo.make("OANDA:EURUSD", "crypto", mintick=0.00001, qty_step=1e-9)
    msgs, ok_all = [], True
    for params, kw in (({}, {}), ({"Bars Closing Above/Below EMA 10": 2, "Trailing Stop EMA Period": 20}, dict(confirm=2, trail_n=20))):
        ref = reference(df, **kw)
        res = run_conversion(TV_ID, df, symbol=sym, tf="60", params=params,
                             strategy_overrides={"margin_long": 0, "margin_short": 0, "commission_value": 0, "slippage": 0})
        ok, d = compare_q(res, ref)
        ok_all = ok_all and ok and len(ref) > 12
        msgs.append(f"{d} (got {len(ref)})")
    return ok_all, " | ".join(msgs)
