"""Independent check — EQL/EQH Reversal (qUoorUCD; YhkzTWJE is the same script): 15-min continuous bars, Longs Only OFF (both sides), tolerance 1.0, entry-within 1.0, stop 2.0 points (passed to both sides). isEQL = at least 3 of the previous 30 bars have a low within the tolerance of the current low (EQH with highs). The anchor is the bar's own low/high, replaced when it is more than 2x
tolerance from the old anchor (which re-arms the done flag). A signal needs the 09:45-14:00 New York session, anchor distance <= entry-within, RSI14 <= 40 (>= 60 for shorts), a rejection candle (close above / below the candle mid) and 3 bars since the last same-side signal; it enters at the next open with stop = anchor -/+ 2 and target = anchor +/- 3 ATR14, fixed on the signal bar.
The first bar outside the session closes any open position."""
import numpy as np
import pandas as pd

from indep import bars, compare, np_atr, np_rsi, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "qUoorUCD"
TOL, DIST, STOP = 1.0, 1.0, 2.0


def check():
    df = bars(24000, seed=480, freq="15min")
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    ny = pd.to_datetime(df["time"], unit="ms", utc=True).dt.tz_convert("America/New_York")
    mins = (ny.dt.hour * 60 + ny.dt.minute).to_numpy()
    sess = (mins >= 585) & (mins < 840)
    atr, rsi = np_atr(h, l, c, 14), np_rsi(c, 14)
    S = dict(ah=np.nan, al=np.nan, dh=False, dl=False, bs=999, bl=999)
    lvl = {}

    def orders(i, pos):
        out = []
        ch = cl = 0
        for k in range(1, 31):
            if i - k >= 0:
                ch += abs(h[i - k] - h[i]) <= TOL
                cl += abs(l[i - k] - l[i]) <= TOL
        eqh, eql = ch >= 3, cl >= 3
        mid = (h[i] + l[i]) / 2
        S["bs"] += 1
        S["bl"] += 1
        if eqh and (np.isnan(S["ah"]) or abs(h[i] - S["ah"]) > TOL * 2):
            S["ah"], S["dh"] = h[i], False
        if eql and (np.isnan(S["al"]) or abs(l[i] - S["al"]) > TOL * 2):
            S["al"], S["dl"] = l[i], False
        dh = abs(h[i] - S["ah"]) if eqh else 9999.0
        dl = abs(l[i] - S["al"]) if eql else 9999.0
        with np.errstate(invalid="ignore"):
            ss = eqh and sess[i] and not S["dh"] and dh <= DIST and rsi[i] >= 60 and c[i] < mid and S["bs"] >= 3
            ls = eql and sess[i] and not S["dl"] and dl <= DIST and rsi[i] <= 40 and c[i] > mid and S["bl"] >= 3
        if ss:
            S["dh"], S["bs"] = True, 0
            out.append(("entry", -1))
            lvl[-1] = (S["ah"] + STOP, S["ah"] - atr[i] * 3)
        if ls:
            S["dl"], S["bl"] = True, 0
            out.append(("entry", 1))
            lvl[1] = (S["al"] - STOP, S["al"] + atr[i] * 3)
        if (not sess[i]) and pos != 0:
            out.append(("close", 1 if pos > 0 else -1))
        return out

    def stop(i, pos, ep, eb):
        return lvl[1 if pos > 0 else -1][0]

    def target(i, pos, ep, eb):
        return lvl[1 if pos > 0 else -1][1]

    with np.errstate(invalid="ignore"):
        ref = simulate(o, h, l, c, orders, stop=stop, target=target)
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="15", params={"Longs Only": False, "Tolerance (pts)": TOL, "Entry Within (pts)": DIST, "Stop Loss (pts)": STOP},
                                        strategy_overrides={"margin_long": 0, "margin_short": 0}), ref)
    return ok and len(ref) > 5, f"{detail} (need >5 trades, got {len(ref)})"
