"""Independent check — SPY 5/9 MA Scalping (1dgKuDgW): 5-min bars, New York clock; entries only
09:32-11:12 on an SMA 5/9 cross with rising volume; bracket +0.40 / -0.50 around the average
price, placed at the close of each bar in a position, so it first works on the bar after the fill."""
import numpy as np
import pandas as pd

from indep import bars, compare, np_cross_over, np_cross_under, np_sma, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "1dgKuDgW"


def check():
    df = bars(8000, seed=71, freq="5min")
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    v = df["volume"].to_numpy()
    ny = pd.to_datetime(df["time"], unit="ms", utc=True).dt.tz_convert("America/New_York")
    m = (ny.dt.hour * 60 + ny.dt.minute).to_numpy()
    in_window = (m >= 9 * 60 + 32) & (m <= 11 * 60 + 12)
    f, s = np_sma(c, 5), np_sma(c, 9)
    vol_up = np.r_[False, v[1:] > v[:-1]]
    lc = np_cross_over(f, s) & vol_up & in_window
    sc = np_cross_under(f, s) & vol_up & in_window
    ref = simulate(o, h, l, c, lambda i, pos: ([("entry", 1)] if lc[i] else []) + ([("entry", -1)] if sc[i] else []),
                   stop=lambda i, pos, ep, eb: (ep - 0.50 if pos > 0 else ep + 0.50) if i > eb else None,
                   target=lambda i, pos, ep, eb: (ep + 0.40 if pos > 0 else ep - 0.40) if i > eb else None)
    sym = SymbolInfo.make("NASDAQ:SPY", "stock")
    assert sym.timezone == "America/New_York", sym.timezone
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="5"), ref)
    return ok and len(ref) > 20, f"{detail} (need >20 trades, got {len(ref)})"
