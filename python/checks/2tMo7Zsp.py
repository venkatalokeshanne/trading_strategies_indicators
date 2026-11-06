"""Independent check — Top & Bottom Hunter Pro (2tMo7Zsp): 5-min bars (24h synthetic), unlimited pyramiding (indep.simulate_pyr, 1 unit per lot). Fib levels from the last two bars' high / low (0.382 / 0.618 retracement
down from the 2-bar high). Inside 10:00-11:30 or 13:30-15:10 New York bar time, RSI14 crossing over 30 with close above the 0.618 level buys one lot (every signal stacks, same id); RSI crossing under 70 with close below
the 0.382 level issues close_all, ignored when nothing is open at that bar's close. Margin off on the pinelib side."""
import numpy as np
import pandas as pd

from indep import bars, compare, np_cross_over, np_cross_under, np_rsi, run_conversion, simulate_pyr
from pinelib import SymbolInfo

TV_ID = "2tMo7Zsp"


def check():
    df = bars(20000, seed=971, freq="5min")
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    ny = pd.to_datetime(df["time"], unit="ms", utc=True).dt.tz_convert("America/New_York")
    m = (ny.dt.hour * 60 + ny.dt.minute).to_numpy()
    ses = ((m >= 600) & (m < 690)) | ((m >= 810) & (m < 910))
    hh = pd.Series(h).rolling(2).max().to_numpy()
    ll = pd.Series(l).rolling(2).min().to_numpy()
    f0, f1 = hh - (hh - ll) * 0.382, hh - (hh - ll) * 0.618
    rsi = np_rsi(c, 14)
    with np.errstate(invalid="ignore"):
        buy = np_cross_over(rsi, 30.0) & (c > f1) & ses
        sell = np_cross_under(rsi, 70.0) & (c < f0) & ses

    def orders(i, pos):
        out = []
        if buy[i]:
            out.append(("entry", 1))
        if sell[i] and pos != 0:
            out.append(("close_all",))
        return out

    with np.errstate(invalid="ignore"):
        ref = simulate_pyr(o, h, l, c, orders, pyramiding=999)
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="5", strategy_overrides={"margin_long": 0, "margin_short": 0, "slippage": 0}), ref)
    return ok and len(ref) > 10, f"{detail} (need >10 trades, got {len(ref)})"
