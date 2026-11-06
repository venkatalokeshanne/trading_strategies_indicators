"""Independent check — Up/Dn Volume Sentiment (6GReiiLS): daily bars. Up/down-volume SMA(50) ratio normalised over 756 bars (na-skipping highest/lowest, na where SMA(down)=0); <=10 long, >=90 short (reversing).
Unconditional exits use position_avg_price (na while flat at the previous close), so the 5 % stop / 10 % target first work on the bar after the fill."""
import numpy as np
import pandas as pd

from indep import bars, compare, np_sma, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "6GReiiLS"
SP, RT = 0.05, 2.0


def check():
    df = bars(5000, seed=202)
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    v = df["volume"].to_numpy()
    n = len(c)
    c1 = np.r_[np.nan, c[:-1]]
    with np.errstate(invalid="ignore"):
        up = np.where(c > c1, v, 0.0)
        dn = np.where(c < c1, v, 0.0)
    su, sd = np_sma(up, 50), np_sma(dn, 50)
    with np.errstate(invalid="ignore", divide="ignore"):
        ratio = np.where(sd == 0, np.nan, su / sd)
    lo = pd.Series(ratio).rolling(756, min_periods=1).min().to_numpy()
    hi = pd.Series(ratio).rolling(756, min_periods=1).max().to_numpy()
    cnt = pd.Series(~np.isnan(ratio)).astype(int).rolling(756, min_periods=1).sum().to_numpy()
    warm = np.arange(n) + 1 >= 756                      # ta.lowest/highest are na until a full window of BARS exists
    with np.errstate(invalid="ignore", divide="ignore"):
        osc = (ratio - lo) / (hi - lo) * 100
    osc[~warm] = np.nan
    with np.errstate(invalid="ignore"):
        lg, sh = osc <= 10, osc >= 90

    def stop(i, pos, ep, eb):
        return None if eb >= i else ep * (1 - SP) if pos > 0 else ep * (1 + SP)

    def target(i, pos, ep, eb):
        return None if eb >= i else ep * (1 + SP * RT) if pos > 0 else ep * (1 - SP * RT)

    ref = simulate(o, h, l, c, lambda i, pos: ([("entry", 1)] if lg[i] else []) + ([("entry", -1)] if sh[i] else []), stop=stop, target=target)
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="D"), ref)
    return ok and len(ref) > 10, f"{detail} (need >10 trades, got {len(ref)})"
