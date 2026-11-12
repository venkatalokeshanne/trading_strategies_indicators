"""Independent check — Nasdaq Silver Bullet (gRKaz4L6): 30-min continuous bars (so the 10:00-11:00 New York window holds two bars), SL / TP 0.3% / 0.6%. up_count / dn_count = consecutive bullish / bearish candles; in the window with count >= 2 and close beyond EMA200 -> entry when flat at the next open.
While a position exists (as of a bar's close) the percentage stop / target around the entry are issued for the same direction from the next bar; the first bar after the window ends closes any position."""
import numpy as np
import pandas as pd

from indep import bars, compare, np_ema, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "gRKaz4L6"


def check():
    df = bars(14000, seed=300, freq="30min")
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    ny = pd.to_datetime(df["time"], unit="ms", utc=True).dt.tz_convert("America/New_York")
    mins = (ny.dt.hour * 60 + ny.dt.minute).to_numpy()
    win = (mins >= 600) & (mins < 660)
    ema = np_ema(c, 200)
    up = np.zeros(n, int)
    dn = np.zeros(n, int)
    for i in range(n):
        pu, pd_ = (up[i - 1], dn[i - 1]) if i else (0, 0)
        if c[i] > o[i]:
            up[i], dn[i] = pu + 1, 0
        elif c[i] < o[i]:
            up[i], dn[i] = 0, pd_ + 1
    with np.errstate(invalid="ignore"):
        lg = win & (up >= 2) & (c > ema)
        sh = win & (dn >= 2) & (c < ema)
    poscl = np.zeros(n)

    def orders(i, pos):
        poscl[i] = pos
        out = []
        if lg[i] and pos == 0:
            out.append(("entry", 1))
        if sh[i] and pos == 0:
            out.append(("entry", -1))
        if (not win[i]) and pos != 0:
            out.append(("close", 1 if pos > 0 else -1))
        return out

    def stop(i, pos, ep, eb):
        if i == 0 or poscl[i - 1] * pos <= 0:
            return None
        return ep * (1 - 0.003) if pos > 0 else ep * (1 + 0.003)

    def target(i, pos, ep, eb):
        if i == 0 or poscl[i - 1] * pos <= 0:
            return None
        return ep * (1 + 0.006) if pos > 0 else ep * (1 - 0.006)

    with np.errstate(invalid="ignore"):
        ref = simulate(o, h, l, c, orders, stop=stop, target=target)
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="30", strategy_overrides={"margin_long": 0, "margin_short": 0}), ref)
    return ok and len(ref) > 10, f"{detail} (need >10 trades, got {len(ref)})"
