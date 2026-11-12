"""Independent check — NTR NASDAQ M1 Trend Runner (O4PX6w2i): 1-minute bars (24 h synthetic, price ~100, pip = 10 ticks) of a stock-style symbol, 10 shares per entry (the 100 %-of-equity sizing replaced), market orders at the next open, commission / slippage off.
MACD(12, 26, 9) cross-over with both lines under 10, the close within the pip distance of the 200 SMA, the 50 SMA slope filter (sma50[10] reference), the 07:30-15:00 Mexico City session, the one-bar re-entry lock, the daily trade / win limits (reset when the day-of-month of the D period changes, not across na session-less bars), the 30-bar technical low (previous bar's) minus 2 pips as the initial stop (20-pip fallback) and the +100 pips trailing stop 100 pips under the close that only moves up are restated bar by bar.
Uses the quantity-aware bracket reference (indep.simulate_brackets). Variants: defaults with a looser distance (400 pips) and slope; 25-pip trailing and activation, 1 win per day."""
import numpy as np
import pandas as pd

from indep import bars, compare_q, np_ema, np_sma, np_cross_over, run_conversion, simulate_brackets
from pinelib import SymbolInfo

TV_ID = "O4PX6w2i"
QTY = 10.0
PIP = 0.1


def one(df, params, p):
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    ny = pd.to_datetime(df["time"], unit="ms", utc=True).dt.tz_convert("America/New_York")
    mx = pd.to_datetime(df["time"], unit="ms", utc=True).dt.tz_convert("America/Mexico_City")
    mxm = (mx.dt.hour * 60 + mx.dt.minute).to_numpy()
    sess = (mxm >= 7 * 60 + 30) & (mxm < 15 * 60)
    period_day = (ny.dt.tz_localize(None) - pd.Timedelta(minutes=570)).dt.day.to_numpy().astype(float)
    dom = np.where(mxm == 1439, np.nan, period_day)               # time("D", "0000-2359", MX) is na on the one excluded minute
    macd = np_ema(c, 12) - np_ema(c, 26)
    sig = np_ema(macd, 9)
    hist_unused = macd - sig
    cu = np_cross_over(macd, sig)
    sma200, sma50 = np_sma(c, 200), np_sma(c, 50)
    low30 = np.full(n, np.nan)
    for i in range(29, n):
        low30[i] = l[i - 29:i + 1].min()
    log: list = []
    S = dict(prev=None, closed_prev=0, last_exit=0, ops=0, wins=0, sl=np.nan, trail=np.nan, stop=np.nan, trail_prev=np.nan)

    def orders(i, info):
        out = []
        pos, avg = info["pos"], info["avg"]
        pp = S["prev"]
        S["prev"] = pos
        if pp is not None and pos != pp and pos == 0:
            S["last_exit"] = i
        lock = i > S["last_exit"]
        if i > 0 and not np.isnan(dom[i]) and not np.isnan(dom[i - 1]) and dom[i] != dom[i - 1]:
            S["ops"] = S["wins"] = 0
        closed = len(log)
        if closed > S["closed_prev"]:
            S["ops"] += 1
            # one closed-trade row per exit piece here (1 lot): the last row is the trade just closed
            if log[-1][0] * (log[-1][4] - log[-1][2]) * log[-1][5] > 0:
                S["wins"] += 1
        S["closed_prev"] = closed
        with np.errstate(invalid="ignore"):
            slope = (sma50[i] - (sma50[i - p["sl_n"]] if i >= p["sl_n"] else np.nan)) / p["sl_n"]
            near = abs(c[i] - sma200[i]) / PIP <= p["dist"]
            sig_ok = bool(cu[i] and macd[i] < 10 and sig[i] < 10 and near and lock and sess[i] and slope >= p["slope"])
        buy = sig_ok and S["ops"] < 3 and S["wins"] < p["wins"] and pos == 0
        if buy:
            tmin = low30[i - 1] if i > 0 else np.nan
            S["sl"] = tmin - 2.0 * PIP
            risk = c[i] - S["sl"]
            if risk <= 0:
                risk = 20 * PIP
                S["sl"] = c[i] - risk
            out.append(("entry", "Compra", 1, QTY))
            S["stop"] = S["sl"]
        if pos > 0:
            if c[i] - avg >= p["act"] * PIP:
                new = c[i] - p["trail"] * PIP
                prev = 0.0 if np.isnan(S["trail_prev"]) else S["trail_prev"]
                S["trail"] = max(new, prev)
                S["stop"] = S["trail"]
            out.append(("exit", "Salida", "Compra", None, None if np.isnan(S["stop"]) else float(S["stop"]), None))
        if pos == 0:
            S["sl"] = S["trail"] = np.nan
        S["trail_prev"] = S["trail"]
        return out

    ref = simulate_brackets(o, h, l, c, orders, pyramiding=10, tick=0.01, qty_step=1e-9, log=log)
    sym = SymbolInfo.make("NASDAQ:XYZ", "stock", qty_step=1e-9)
    ok, d = compare_q(run_conversion(TV_ID, df, symbol=sym, tf="1", params=params,
                                     strategy_overrides={"margin_long": 0, "margin_short": 0, "commission_value": 0, "slippage": 0, "default_qty_type": "fixed", "default_qty_value": QTY}), ref)
    return ok and len(ref) > 12, f"{d} (got {len(ref)})"


BASE = dict(dist=75.0, slope=-2.5, sl_n=10, wins=2, act=100.0, trail=100.0)


def check():
    df = bars(120000, seed=121, freq="1min")
    for k in ("open", "high", "low", "close"):
        df[k] = 100 * (df[k] / 100) ** 0.06
    msgs, allok = [], True
    cases = (({"Distancia Máxima Pips": 400.0, "Pendiente mínima SMA50": -50.0}, dict(dist=400.0, slope=-50.0)),
             ({"Distancia Máxima Pips": 400.0, "Pendiente mínima SMA50": -50.0, "Distancia Trailing Stop": 25.0, "Activar Trailing después de profit": 25.0}, dict(dist=400.0, slope=-50.0, trail=25.0, act=25.0)))
    for params, ov in cases:
        ok, m = one(df, params, {**BASE, **ov})
        allok &= ok
        msgs.append(m)
    return allok, " | ".join(msgs)
