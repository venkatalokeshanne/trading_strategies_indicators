"""Independent check — Qing EMA + MACD + Squeeze (PxAUrVvp): 15-minute bars (24 h synthetic, price ~100) of a stock-style symbol, market orders at the next open, the script's own risk-based quantities (equity mirrored from the closed trades + open P&L), commission / slippage off.
MACD(6, 14, 8) cross-over with the 5-bar cooldown after a trade closes enters long with a quantity risking 1 % of equity over 1.2 ATR(10) (min 1); the 10/50 SMA cross-under closes it (default) or an ATR stop / 2.5 ATR target is attached. Shorts (6/12 EMA cross-under, MACD cross-under, price over the 50 and 200 EMA, RSI under 45 and the optional daily SMA bias) are enabled in the variants.
Uses the quantity-aware bracket reference (indep.simulate_brackets). Variants: defaults; stop / target exits; shorts enabled with the daily bias."""
import numpy as np

from indep import bars, compare_q, np_atr, np_cross_over, np_cross_under, np_ema, np_periods, np_rsi, np_security_lookahead_off, np_sma, run_conversion, simulate_brackets
from pinelib import SymbolInfo

TV_ID = "PxAUrVvp"


def one(df, params, p):
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    ev, es, el, eg = np_ema(c, 6), np_ema(c, 12), np_ema(c, 50), np_ema(c, 200)
    macd = np_ema(c, 6) - np_ema(c, 14)
    sig = np_ema(macd, 8)
    mu, md = np_cross_over(macd, sig), np_cross_under(macd, sig)
    s10, s50 = np_sma(c, 10), np_sma(c, 50)
    ex_l, ex_s = np_cross_under(s10, s50), np_cross_over(s10, s50)
    cvs = np_cross_under(ev, es)
    rsi = np_rsi(c, 14)
    atr = np_atr(h, l, c, 10)
    pid, last_of = np_periods(df, 1440)
    dc = np.array([c[pid == k][-1] for k in range(pid.max() + 1)])
    ds, dl = np_sma(dc, 10), np_sma(dc, 50)
    hs, hl = np_security_lookahead_off(ds, pid, last_of), np_security_lookahead_off(dl, pid, last_of)
    log: list = []
    S = dict(prev_n=None, last_close=None)

    def orders(i, info):
        out = []
        n_open = info["n"]
        pn = S["prev_n"]
        S["prev_n"] = n_open
        if n_open == 0 and pn is not None and pn != 0:
            S["last_close"] = i
        can = S["last_close"] is None or i - S["last_close"] >= 5
        eq = 10000.0 + sum(d * (xp - ep) * q for d, _, ep, _, xp, q in log) + sum(x["d"] * x["q"] * (c[i] - x["ep"]) for x in info["lots"])
        with np.errstate(invalid="ignore"):
            el_ = bool(mu[i] and can and n_open == 0)
            bias = (hs[i] < hl[i]) if p["htf"] else True
            es_ = bool(p["shorts"] and c[i] > el[i] and c[i] > eg[i] and cvs[i] and md[i] and can and n_open == 0 and bias and rsi[i] < p["rsi_bear"])
            dist = atr[i] * 1.2
            qty = max(1.0, eq * 0.01 / dist) if dist > 0 else 1.0
        if el_:
            out.append(("entry", "Long", 1, float(qty)))
            if not p["sig_exit"]:
                out.append(("exit", "Long Exit TP/SL", "Long", None, c[i] - dist, c[i] + dist * 2.5))
        if p["sig_exit"] and ex_l[i] and info["pos"] > 0:
            out.append(("close", "Long"))
        if es_:
            out.append(("entry", "Short", -1, float(qty)))
            if not p["sig_exit"]:
                out.append(("exit", "Short Exit TP/SL", "Short", None, c[i] + dist, c[i] - dist * 2.5))
        if p["sig_exit"] and ex_s[i] and info["pos"] < 0:
            out.append(("close", "Short"))
        return out

    ref = simulate_brackets(o, h, l, c, orders, pyramiding=1, tick=0.01, qty_step=1e-9, log=log)
    sym = SymbolInfo.make("NASDAQ:XYZ", "stock", qty_step=1e-9)
    ok, d = compare_q(run_conversion(TV_ID, df, symbol=sym, tf="15", params=params,
                                     strategy_overrides={"margin_long": 0, "margin_short": 0, "commission_value": 0, "slippage": 0}), ref)
    return ok and len(ref) > 12, f"{d} (got {len(ref)})"


def check():
    df = bars(40000, seed=141, freq="15min")
    for k in ("open", "high", "low", "close"):
        df[k] = 100 * (df[k] / 100) ** 0.3
    msgs, allok = [], True
    cases = (({}, dict(sig_exit=True, shorts=False, htf=False, rsi_bear=45)),
             ({"Use Signal Crossover for Exit?": False}, dict(sig_exit=False, shorts=False, htf=False, rsi_bear=45)),
             ({"Allow Short Trades?": True, "Use Higher Timeframe Filter?": True, "RSI Bearish Filter (e.g., <45)": 50}, dict(sig_exit=True, shorts=True, htf=True, rsi_bear=50)))
    alt = bars(40000, seed=142, freq="15min")                  # a choppier series in which the short setup fires
    for k in ("open", "high", "low", "close"):
        alt[k] = 100 * (alt[k] / 100) ** 0.9
    for params, ov in cases:
        ok, m = one(alt if ov["shorts"] else df, params, ov)
        allok &= ok
        msgs.append(m)
    return allok, " | ".join(msgs)
