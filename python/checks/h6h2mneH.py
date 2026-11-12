"""Independent check — NQ Scalping (h6h2mneH): 15-min bars, Pullback Band 1.0% here (passed to both sides), orders at the signal close (process_orders_on_close). Session 09:30-16:00 New York. Long: close > EMA100, |close - EMA100| <= band, RSI14 >= 55 and not already long;
short mirrors (RSI <= 45), reversing an open opposite trade. Both exits are rebuilt every bar from the position average price at that bar's script time (ATR14 x 1.0 stop, x 1.2 target; na while flat), apply from the next bar to the trade of their own
direction even right after a reversal; after 20 bars in the market (counted on script-time bars with a position) the trade closes at the bar close."""
import numpy as np
import pandas as pd

from indep import bars, compare, np_atr, np_ema, np_rsi, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "h6h2mneH"
PB = 1.0


def check():
    df = bars(14000, seed=66, freq="15min")
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    ny = pd.to_datetime(df["time"], unit="ms", utc=True).dt.tz_convert("America/New_York")
    mins = (ny.dt.hour * 60 + ny.dt.minute).to_numpy()
    sess = (mins >= 570) & (mins < 960)
    ema, rsi, atr = np_ema(c, 100), np_rsi(c, 14), np_atr(h, l, c, 14)
    with np.errstate(invalid="ignore"):
        near = np.abs(c - ema) <= ema * (PB / 100)
        lg = sess & (c > ema) & near & (rsi >= 55)
        sh = sess & (c < ema) & near & (rsi <= 45)
    tmp, lv = {}, {}
    bit = [0]

    def orders(i, pos):
        out = []
        if lg[i] and pos <= 0:
            out.append(("entry", 1))
        if sh[i] and pos >= 0:
            out.append(("entry", -1))
        ep = tmp.get(i) if pos != 0 else None
        lv[i] = None if ep is None else ((ep - atr[i], ep + atr[i] * 1.2), (ep + atr[i], ep - atr[i] * 1.2))
        if pos != 0:
            bit[0] += 1
        else:
            bit[0] = 0
        if pos != 0 and bit[0] >= 20:
            out.append(("close", 1 if pos > 0 else -1))
        return out

    def stop(i, pos, ep, eb):
        tmp[i] = ep
        p = lv.get(i - 1) if i > 0 else None
        lev = None if p is None else p[0] if pos > 0 else p[1]
        return None if lev is None or np.isnan(lev[0]) else lev[0]

    def target(i, pos, ep, eb):
        p = lv.get(i - 1) if i > 0 else None
        lev = None if p is None else p[0] if pos > 0 else p[1]
        return None if lev is None or np.isnan(lev[1]) else lev[1]

    with np.errstate(invalid="ignore"):
        ref = simulate(o, h, l, c, orders, stop=stop, target=target, on_close=True)
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="15", params={"Pullback Band (%) around EMA": PB},
                                        strategy_overrides={"margin_long": 0, "margin_short": 0}), ref)
    return ok and len(ref) > 10, f"{detail} (need >10 trades, got {len(ref)})"
