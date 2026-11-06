"""Independent check — TrenchWrld BB + RSI (1s588fgS): hourly bars, one position. While flat at a script run: long when (Reclaim) the previous close was below the previous lower band, the close is back above the
lower band and RSI(14) > 30 (Touch: close <= lower band and RSI <= 30), and close > EMA200 (trend filter); short mirrored (upper band, RSI < 70 / >= 70, close < EMA200). Bands = SMA20 +/- 2 population stdev.
Once a position was open at a script run the bracket stop = avg * (1 -/+ 1.5 %), limit = avg * (1 +/- 3 %) works from the next bar. Variants: default, Touch Band, and no trend filter / long only."""
import numpy as np
import pandas as pd

from indep import bars, compare, np_ema, np_rsi, np_sma, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "1s588fgS"


def one(df, params, touch, use_tf, mode):
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    basis = np_sma(c, 20)
    dev = 2.0 * pd.Series(c).rolling(20, min_periods=20).std(ddof=0).to_numpy()
    up, lo = basis + dev, basis - dev
    rsi, ema = np_rsi(c, 14), np_ema(c, 200)
    sh = lambda x: np.r_[np.nan, x[:-1]]
    with np.errstate(invalid="ignore"):
        if touch:
            ls, ss = (c <= lo) & (rsi <= 30), (c >= up) & (rsi >= 70)
        else:
            ls = (sh(c) < sh(lo)) & (c > lo) & (rsi > 30)
            ss = (sh(c) > sh(up)) & (c < up) & (rsi < 70)
        lt = (c > ema) if use_tf else np.ones(n, bool)
        stt = (c < ema) if use_tf else np.ones(n, bool)

    def orders(i, pos):
        out = []
        if pos == 0:
            if mode in ("Long Only", "Both") and ls[i] and lt[i]:
                out.append(("entry", 1))
            if mode in ("Short Only", "Both") and ss[i] and stt[i]:
                out.append(("entry", -1))
        return out

    stop = lambda i, pos, ep, eb: None if eb >= i else ep * (1 - 0.015 * pos)
    tgt = lambda i, pos, ep, eb: None if eb >= i else ep * (1 + 0.03 * pos)
    with np.errstate(invalid="ignore"):
        ref = simulate(o, h, l, c, orders, stop=stop, target=tgt)
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, d = compare(run_conversion(TV_ID, df, symbol=sym, tf="60", params=params, strategy_overrides={"margin_long": 0, "margin_short": 0}), ref)
    return ok and len(ref) > 10, f"{d} (got {len(ref)})"


def check():
    df = bars(30000, seed=531, freq="1h")
    msgs, allok = [], True
    for params, touch, tf, mode in (({}, False, True, "Both"), ({"Entry Style": "Touch Band"}, True, True, "Both"),
                                    ({"Use 200 EMA Trend Filter": False, "Trade Mode": "Long Only"}, False, False, "Long Only")):
        ok, m = one(df, params, touch, tf, mode)
        allok &= ok
        msgs.append(m)
    return allok, " | ".join(msgs)
