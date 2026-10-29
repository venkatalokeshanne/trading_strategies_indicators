"""Independent check — Nifty Futures ORB Smart Trail (CDhXq8DM): 5-minute bars (24h synthetic) on an Asia/Kolkata chart whose trading day starts at 09:15, one position, trade list only. Opening range = high / low of the 09:15-09:30 IST bars of the
day (reset at the first bar of each trading day), locked on the first bar after it, valid when (high - low) / close x 100 <= width (input loosened to 50 on both sides). Before 14:30 IST a close above the range high (below the low) enters once per side per day while
flat; stop distance = max(distance to the other side of the range, 1.5 ATR14). No exit order exists on the entry (fill) bar; from the first script run with the position the stop ratchets: long stop = max(old, max(high - ATR14 x m, lowest low of 5 bars)) with m = 3 / 2 / 1 for
profit (high - entry close) / initial distance < 1 / < 2 / >= 2 (short mirrored), re-issued every bar, so bar i works with bar i-1's stop if a same-side position existed at bar i-1's script run. A candle against the position larger than 1 ATR closes it (next open); the
15:15-15:30 window closes any position. Margin and slippage off on the pinelib side."""
import numpy as np
import pandas as pd

from indep import bars, compare, np_atr, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "CDhXq8DM"


def check():
    df = bars(25000, seed=921, freq="5min")
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    ist = pd.to_datetime(df["time"], unit="ms", utc=True).dt.tz_convert("Asia/Kolkata")
    m = (ist.dt.hour * 60 + ist.dt.minute).to_numpy()
    tday = (ist.dt.tz_localize(None) - pd.Timedelta(minutes=9 * 60 + 15)).dt.date.to_numpy()
    in_or = (m >= 555) & (m < 570)
    in_sq = (m >= 915) & (m < 930)
    in_ne = (m >= 870) & (m < 930)
    atr = np_atr(h, l, c, 14)
    sw_hi = pd.Series(h).rolling(5, min_periods=5).max().to_numpy()
    sw_lo = pd.Series(l).rolling(5, min_periods=5).min().to_numpy()
    S = dict(H=np.nan, L=np.nan, lock=False, tl=False, ts=False, ep=np.nan, ir=np.nan, sp=np.nan)
    poscl = np.zeros(n)
    sp_arr = np.full(n, np.nan)

    def orders(i, pos):
        poscl[i] = pos
        out = []
        nd = i > 0 and tday[i] != tday[i - 1]
        if nd:
            S.update(H=np.nan, L=np.nan, lock=False, tl=False, ts=False)
        if in_or[i]:
            S["H"] = h[i] if np.isnan(S["H"]) else max(S["H"], h[i])
            S["L"] = l[i] if np.isnan(S["L"]) else min(S["L"], l[i])
        if (not in_or[i]) and (not S["lock"]) and not np.isnan(S["H"]):
            S["lock"] = True
        with np.errstate(invalid="ignore"):
            wid = (S["H"] - S["L"]) / c[i] * 100 if not (np.isnan(S["H"]) or np.isnan(S["L"])) else np.nan
            valid = S["lock"] and not np.isnan(wid) and wid <= 50.0
            can = valid and (not in_ne[i]) and pos == 0
            if can and (not S["tl"]) and c[i] > S["H"]:
                d = max(c[i] - S["L"], atr[i] * 1.5)
                out.append(("entry", 1))
                S.update(ep=c[i], ir=d, sp=c[i] - d, tl=True)
            if can and (not S["ts"]) and c[i] < S["L"]:
                d = max(S["H"] - c[i], atr[i] * 1.5)
                out.append(("entry", -1))
                S.update(ep=c[i], ir=d, sp=c[i] + d, ts=True)
        if pos > 0:
            pr = (h[i] - S["ep"]) / S["ir"]
            mult = 1.0 if pr >= 2 else (2.0 if pr >= 1 else 3.0)
            S["sp"] = max(S["sp"], max(h[i] - atr[i] * mult, sw_lo[i]))
            sp_arr[i] = S["sp"]
        if pos < 0:
            pr = (S["ep"] - l[i]) / S["ir"]
            mult = 1.0 if pr >= 2 else (2.0 if pr >= 1 else 3.0)
            S["sp"] = min(S["sp"], min(l[i] + atr[i] * mult, sw_hi[i]))
            sp_arr[i] = S["sp"]
        if pos > 0 and (c[i] - o[i]) < 0 and (o[i] - c[i]) > atr[i] * 1.0:
            out.append(("close", 1))
        if pos < 0 and (c[i] - o[i]) > 0 and (c[i] - o[i]) > atr[i] * 1.0:
            out.append(("close", -1))
        if in_sq[i] and pos != 0:
            out += [("close", 1), ("close", -1)]
        return out

    def stop(i, pos, ep, eb):
        if i == 0 or poscl[i - 1] * pos <= 0 or np.isnan(sp_arr[i - 1]):
            return None
        return sp_arr[i - 1]

    with np.errstate(invalid="ignore"):
        ref = simulate(o, h, l, c, orders, stop=stop)
    sym = SymbolInfo.make("NSE:NIFTY", "stock", qty_step=1e-9, timezone="Asia/Kolkata", session="0915-1530")
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="5", params={"Max OR Width (% of price) — skip wider days": 50.0},
                                        strategy_overrides={"margin_long": 0, "margin_short": 0, "slippage": 0}), ref)
    return ok and len(ref) > 10, f"{detail} (need >10 trades, got {len(ref)})"
