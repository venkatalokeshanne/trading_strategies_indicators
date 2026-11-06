"""Independent check — Phase Oscillator Momentum (bwmZOabG): 5-minute bars on a stock chart (New York clock), one position, market orders at the next open. rawOsc = (close - EMA21) / (3 ATR14) x 100 (0 while the ATR is na, na while only the EMA is na), po = EMA3(rawOsc) (first value once three valid inputs exist).
Entries (inside the entry window = bar start 09:30-11:00, or 09:30-16:00; unless holding overnight the bar must close before 16:00) when po crosses up through +U (long) / down through -U (short), U = 100 / 61.8 / 0. Exit rules: the opposite -U / +U cross, the zero cross, or the cross back out of the zone;
the exit signal does not apply on a bar with the opposite entry. At the first bar whose close reaches 16:00 (and whenever a position sits outside regular hours) positions are flattened at the next open unless holding overnight. A hard stop (percent of the entry price; issued with the entry and re-issued while open)
works from the fill bar. Slippage / margin / commission off on the pinelib side."""
import numpy as np
import pandas as pd

from indep import bars, compare, np_atr, np_cross_over, np_cross_under, np_ema, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "bwmZOabG"


def one(df, params, level, full, hold, exit_mode, hard):
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    atr, pivot = np_atr(h, l, c, 14), np_ema(c, 21)
    with np.errstate(invalid="ignore", divide="ignore"):
        raw = np.where(atr > 0, (c - pivot) / (3.0 * atr) * 100.0, 0.0)
    po = np_ema(raw, 3)
    up, lo = level, -level
    cu, cd = np_cross_over(po, up), np_cross_under(po, lo)
    zu, zd = np_cross_over(po, 0.0), np_cross_under(po, 0.0)
    xul, xdu = np_cross_over(po, lo), np_cross_under(po, up)
    ny = pd.to_datetime(df["time"], unit="ms", utc=True).dt.tz_convert("America/New_York")
    m = (ny.dt.hour * 60 + ny.dt.minute).to_numpy()
    win = (m >= 570) & (m < 660)
    rth = (m >= 570) & (m < 960)
    bcm = m + 5
    flat_now = (bcm >= 960) & np.r_[True, bcm[:-1] < 960]
    entry_time = (rth if full else win) & (hold | (bcm < 960))
    lx = zd if exit_mode == "zero" else (xdu if exit_mode == "zone" else cd)
    sx = zu if exit_mode == "zero" else (xul if exit_mode == "zone" else cu)
    S = dict(ep=np.nan)
    sl_long, sl_short = np.full(n, np.nan), np.full(n, np.nan)

    def orders(i, pos):
        out = []
        el = bool(entry_time[i] and cu[i])
        es = bool(entry_time[i] and cd[i])
        if el:
            out.append(("entry", 1))
        if es:
            out.append(("entry", -1))
        if pos > 0 and lx[i] and not es:
            out.append(("close", 1))
        if pos < 0 and sx[i] and not el:
            out.append(("close", -1))
        if hard:
            if el or pos > 0:
                sl_long[i] = (S["ep"] if pos > 0 else c[i]) * (1 - hard / 100)
            if es or pos < 0:
                sl_short[i] = (S["ep"] if pos < 0 else c[i]) * (1 + hard / 100)
        if (not hold) and pos != 0 and (flat_now[i] or (not rth[i] and not win[i])):
            out.append(("close", pos))
        return out

    def stop(i, pos, ep, eb):
        S["ep"] = ep
        if not hard or i == 0:
            return None
        v = sl_long[i - 1] if pos > 0 else sl_short[i - 1]
        return None if np.isnan(v) else v

    with np.errstate(invalid="ignore"):
        ref = simulate(o, h, l, c, orders, stop=stop)
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, d = compare(run_conversion(TV_ID, df, symbol=sym, tf="5", params=params,
                                   strategy_overrides={"margin_long": 0, "margin_short": 0, "slippage": 0, "commission_value": 0}), ref)
    return ok, d, len(ref)


def check():
    df = bars(60000, seed=651, freq="5min")
    msgs, allok, tot = [], True, 0
    for params, level, full, hold, em, hard in (
            ({}, 100.0, False, False, "opp", 0),
            ({"Signal level": "Extended (+/-61.8)", "Allow entries 09:30-16:00 instead": True}, 61.8, True, False, "opp", 0),
            ({"Signal level": "Zero line (0)", "Hard stop": True, "%": 0.5}, 0.0, False, False, "opp", 0.5),
            ({"Signal level": "Zero line (0)", "Hold overnight (skip the flat)": True, "Exit rule": "Return to zero"}, 0.0, False, True, "zero", 0),
            ({"Signal level": "Extended (+/-61.8)", "Exit rule": "Leave the entry zone"}, 61.8, False, False, "zone", 0)):
        ok, d, k = one(df, params, level, full, hold, em, hard)
        allok &= ok
        tot += k
        msgs.append(f"{d} (got {k})")
    return allok and tot > 30, " | ".join(msgs)
