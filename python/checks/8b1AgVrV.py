"""Independent check — Gold Swing (8b1AgVrV): 15-min bars, SL / TP 5 / 10 pips of 0.1 = 0.5 / 1.0 price units here (SL 5 / TP 10 pips passed to both sides), orders at the signal close (process_orders_on_close), pyramiding 0. Mon-Fri 06:00-20:00 New York.
Bull: close > VWAP(hlc3, 09:30-NY reset) and EMA20 > EMA50 and EMA20 > EMA20[2], low <= EMA20 < close and close > open, RSI14 >= 54, 2-bar cooldown from the last signal; short mirrors with RSI <= 46. A signal while the opposite trade is open reverses it.
The bracket levels (close -/+ SL, close +/- TP) are fixed on the signal bar, per direction."""
import numpy as np
import pandas as pd

from indep import bars, compare, np_ema, np_rsi, np_vwap, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "8b1AgVrV"
SL, TP = 5, 10


def check():
    df = bars(12000, seed=63, freq="15min")
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    ny = pd.to_datetime(df["time"], unit="ms", utc=True).dt.tz_convert("America/New_York")
    mins = (ny.dt.hour * 60 + ny.dt.minute).to_numpy()
    ok_sess = (mins >= 360) & (mins < 1200) & (ny.dt.dayofweek.to_numpy() < 5)
    ef, es, rsi = np_ema(c, 20), np_ema(c, 50), np_rsi(c, 14)
    vw = np_vwap(df, (h + l + c) / 3)
    ef2 = np.r_[[np.nan] * 2, ef[:-2]]
    with np.errstate(invalid="ignore"):
        bt = (c > vw) & (ef > es) & (ef > ef2)
        st_ = (c < vw) & (ef < es) & (ef < ef2)
        br = (l <= ef) & (c > ef) & (c > o)
        sr = (h >= ef) & (c < ef) & (c < o)
    last = [None]
    lvl = {}

    def orders(i, pos):
        out = []
        cd = last[0] is None or i - last[0] > 2   # one cooldown test per bar, before either side updates it
        with np.errstate(invalid="ignore"):
            if ok_sess[i] and cd and bt[i] and br[i] and rsi[i] >= 54 and pos <= 0:
                out.append(("entry", 1))
                lvl[1] = (c[i] - SL * 0.1, c[i] + TP * 0.1)
                last[0] = i
            if ok_sess[i] and cd and st_[i] and sr[i] and rsi[i] <= 46 and pos >= 0:
                out.append(("entry", -1))
                lvl[-1] = (c[i] + SL * 0.1, c[i] - TP * 0.1)
                last[0] = i
        return out

    def stop(i, pos, ep, eb):
        return lvl.get(1 if pos > 0 else -1, (None, None))[0]

    def target(i, pos, ep, eb):
        return lvl.get(1 if pos > 0 else -1, (None, None))[1]

    ref = simulate(o, h, l, c, orders, stop=stop, target=target, on_close=True)
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="15", params={"SL Pips": SL, "TP Pips": TP}, strategy_overrides={"margin_long": 0, "margin_short": 0}), ref)
    return ok and len(ref) > 10, f"{detail} (need >10 trades, got {len(ref)})"
