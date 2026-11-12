"""Independent check — MNQ 15m NY Open ORB (0h0KTxCq): 15-minute bars (24h synthetic), process_orders_on_close, one position. Opening range = high / low of the 09:30 bar (09:30-09:45 New York), reset at the first bar of each New
York day, locked on the first bar after it. 09:45-16:00: a close above the range high (below the low) while flat, once per day, enters at the close; exits fixed at entry: profit 2000 ticks, loss 2000 ticks of 0.01 (200 points / 10),
trailing activation 150 ticks, offset 100 ticks (all relative to the entry price, working from the next bar). The first bar after 16:00 closes any position at its close. Margin, slippage, commission off on the pinelib side."""
import numpy as np
import pandas as pd

from indep import bars, compare, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "0h0KTxCq"


def check():
    df = bars(9000, seed=924, freq="15min")
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    ny = pd.to_datetime(df["time"], unit="ms", utc=True).dt.tz_convert("America/New_York")
    m = (ny.dt.hour * 60 + ny.dt.minute).to_numpy()
    day = ny.dt.date.to_numpy()
    in_orb = (m >= 570) & (m < 585)
    in_tr = (m >= 585) & (m < 960)
    S = dict(H=np.nan, L=np.nan, lock=False, traded=False)

    def orders(i, pos):
        out = []
        if i > 0 and day[i] != day[i - 1]:
            S.update(H=np.nan, L=np.nan, lock=False, traded=False)
        if in_orb[i]:
            S["H"] = h[i] if np.isnan(S["H"]) else max(S["H"], h[i])
            S["L"] = l[i] if np.isnan(S["L"]) else min(S["L"], l[i])
        if i > 0 and not in_orb[i] and in_orb[i - 1] and not np.isnan(S["H"]):
            S["lock"] = True
        can = S["lock"] and in_tr[i] and pos == 0 and not S["traded"]
        if can and c[i] > S["H"]:
            out.append(("entry", 1))
            S["traded"] = True
        elif can and c[i] < S["L"]:
            out.append(("entry", -1))
            S["traded"] = True
        if i > 0 and not in_tr[i] and in_tr[i - 1] and pos != 0:
            out.append(("close", pos))
        return out

    def stop(i, pos, ep, eb):
        return ep - pos * 20.0

    def target(i, pos, ep, eb):
        return ep + pos * 20.0

    def trail(i, pos, ep, eb):
        return (150.0, 100.0)

    ref = simulate(o, h, l, c, orders, stop=stop, target=target, trail=trail, tick=0.01, on_close=True)
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="15", strategy_overrides={"margin_long": 0, "margin_short": 0, "slippage": 0, "commission_value": 0}), ref)
    return ok and len(ref) > 10, f"{detail} (need >10 trades, got {len(ref)})"
