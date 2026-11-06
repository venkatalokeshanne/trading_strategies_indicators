"""Independent check — GOLD AI Strategy v2.0 (5YqXo32H): 15-minute bars (24 h synthetic, price ~100, tick 0.01) of a stock-style symbol (New York sessions), market orders at the next open, fixed quantity (the percent-of-equity sizing is replaced), commission / slippage / margin off.
Six-point long / short scores (EMA200, EMA21 vs 55, RSI band, MACD vs signal, close vs Bollinger basis, stochastic K vs D with K = SMA3 of the 14-bar stochastic summed like the engine's rolling sum), triggers (EMA cross, MACD cross, RSI bounce, stochastic cross), London 07:00 - 16:00 / New York 13:00 - 21:00 sessions, volume spike filter, at most max-trades open lots.
Every entry carries one exit order: ATR stop, ATR target and a trailing stop (activation = offset = ATR x trail % x 10 ticks). Uses the quantity-aware bracket reference (indep.simulate_brackets), which also compares the closed quantities.
Variants: defaults; score 3 with the volume filter and sessions off; no trailing, 2 concurrent trades."""
import numpy as np
import pandas as pd

from indep import bars, compare_q, np_atr, np_cross_over, np_cross_under, np_ema, np_rsi, np_sma, run_conversion, simulate_brackets
from pinelib import SymbolInfo

TV_ID = "5YqXo32H"
QTY = 10.0


def sma_prefix(x, n):
    out = np.full(len(x), np.nan)
    psum = [0.0]
    pnan = [0]
    for i, v in enumerate(x):
        m = i
        if m + 1 >= n and not np.isnan(v) and pnan[m] - pnan[m - (n - 1)] == 0:
            out[i] = (psum[m] - psum[m - (n - 1)] + v) / n
        psum.append(psum[-1] + (0.0 if np.isnan(v) else v))
        pnan.append(pnan[-1] + (1 if np.isnan(v) else 0))
    return out


def stoch(c, h, l, n):
    out = np.full(len(c), np.nan)
    for i in range(n - 1, len(c)):
        hi, lo = h[i - n + 1:i + 1].max(), l[i - n + 1:i + 1].min()
        if hi != lo:
            out[i] = 100 * (c[i] - lo) / (hi - lo)
    return out


def one(df, params, p):
    o, h, l, c, v = (df[k].to_numpy() for k in ("open", "high", "low", "close", "volume"))
    n = len(c)
    loc = pd.to_datetime(df["time"], unit="ms", utc=True).dt.tz_convert("America/New_York")
    mins = (loc.dt.hour * 60 + loc.dt.minute).to_numpy()
    in_l = (mins >= 420) & (mins < 960)
    in_n = (mins >= 780) & (mins < 1260)
    ema_f, ema_s, ema_t = np_ema(c, 21), np_ema(c, 55), np_ema(c, 200)
    rsi = np_rsi(c, 14)
    macd = np_ema(c, 12) - np_ema(c, 26)
    sig = np_ema(macd, 9)
    basis = np_sma(c, 20)
    K = sma_prefix(stoch(c, h, l, 14), 3)
    D = sma_prefix(K, 3)
    atr = np_atr(h, l, c, 14)
    vma = np_sma(v, 20)
    xu_e, xd_e = np_cross_over(ema_f, ema_s), np_cross_under(ema_f, ema_s)
    xu_m, xd_m = np_cross_over(macd, sig), np_cross_under(macd, sig)
    xu_r, xd_r = np_cross_over(rsi, 35), np_cross_under(rsi, 65)
    xu_s, xd_s = np_cross_over(K, D), np_cross_under(K, D)

    def orders(i, info):
        with np.errstate(invalid="ignore"):
            sl = int(c[i] > ema_t[i]) + int(ema_f[i] > ema_s[i]) + int(50 < rsi[i] < 70) + int(macd[i] > sig[i]) + int(c[i] > basis[i]) + int(K[i] > D[i] and K[i] < 80)
            ss = int(c[i] < ema_t[i]) + int(ema_f[i] < ema_s[i]) + int(30 < rsi[i] < 50) + int(macd[i] < sig[i]) + int(c[i] < basis[i]) + int(K[i] < D[i] and K[i] > 20)
            sess = (in_l[i] or in_n[i]) if p["sess"] else True
            vol = (v[i] > vma[i] * 1.2) if p["vol"] else True
            tl = bool(xu_e[i] or xu_m[i] or xu_r[i] or (xu_s[i] and K[i] < 40))
            ts = bool(xd_e[i] or xd_m[i] or xd_r[i] or (xd_s[i] and K[i] > 60))
            lsig = sess and vol and sl >= p["score"] and tl and c[i] > ema_t[i]
            ssig = sess and vol and ss >= p["score"] and ts and c[i] < ema_t[i]
        out = []
        if np.isnan(atr[i]):
            return out
        tr = atr[i] * 0.8 * 10
        if lsig and info["n"] < p["max"]:
            out.append(("entry", "LONG", 1, QTY))
            out.append(("exit", "EXIT_L", "LONG", None, c[i] - atr[i] * 1.8, c[i] + atr[i] * 3.0) + ((tr, None, tr) if p["trail"] else ()))
        if ssig and info["n"] < p["max"]:
            out.append(("entry", "SHORT", -1, QTY))
            out.append(("exit", "EXIT_S", "SHORT", None, c[i] + atr[i] * 1.8, c[i] - atr[i] * 3.0) + ((tr, None, tr) if p["trail"] else ()))
        return out

    ref = simulate_brackets(o, h, l, c, orders, pyramiding=1, tick=0.01, qty_step=1e-9)
    sym = SymbolInfo.make("NASDAQ:XYZ", "stock", qty_step=1e-9)
    ok, d = compare_q(run_conversion(TV_ID, df, symbol=sym, tf="15", params=params,
                                     strategy_overrides={"margin_long": 0, "margin_short": 0, "commission_value": 0, "slippage": 0, "default_qty_type": "fixed", "default_qty_value": QTY}), ref)
    return ok and len(ref) > 12, f"{d} (got {len(ref)})"


BASE = dict(score=4, vol=True, sess=True, trail=True, max=1)


def check():
    df = bars(30000, seed=517, freq="15min")
    for k in ("open", "high", "low", "close"):
        df[k] = 100 * (df[k] / 100) ** 0.1
    msgs, allok = [], True
    cases = (({}, {}),
             ({"Min Signal Score (1-6)": 3, "Volume Filter": False, "Enable Session Filter": False}, dict(score=3, vol=False, sess=False)),
             ({"Use Trailing Stop": False, "Max Concurrent Trades": 2}, dict(trail=False, max=2)))
    for params, ov in cases:
        ok, m = one(df, params, {**BASE, **ov})
        allok &= ok
        msgs.append(m)
    return allok, " | ".join(msgs)
