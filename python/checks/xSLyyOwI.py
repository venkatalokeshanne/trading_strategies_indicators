"""Independent check — Sector Rotation Momentum (xSLyyOwI): 5-min bars plus a second synthetic series standing in for the sector ETF (served through the
data provider and aligned by bar time). Relative strength = close / ETF close with its EMA20; EMA 20/50 trend and relative strength above/below its
EMA enter (reversing). Both exits unconditional: ATR*1.5 stop / 3 ATR target around the position's average price as of the previous close (na while
flat; OLD average on a reversal's first bar). Margin off on the pinelib side."""
import numpy as np

from indep import bars, compare, np_atr, np_ema, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "xSLyyOwI"


def check():
    df = bars(20000, seed=138, freq="5min")
    etf = bars(20000, seed=139, freq="5min")
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    rs = c / etf["close"].to_numpy()
    rma = np_ema(rs, 20)
    f, s, atr = np_ema(c, 20), np_ema(c, 50), np_atr(h, l, c, 14)
    with np.errstate(invalid="ignore"):
        lg, sg = (f > s) & (rs > rma), (f < s) & (rs < rma)
    ep_now, avg_close = {}, np.full(n, np.nan)

    def orders(i, pos):
        avg_close[i] = ep_now.get(i, np.nan) if pos != 0 else np.nan
        return ([("entry", 1)] if lg[i] and pos <= 0 else []) + ([("entry", -1)] if sg[i] and pos >= 0 else [])

    def level(k):
        def fn(i, pos, ep, eb):
            ep_now[i] = ep
            if i == 0 or np.isnan(avg_close[i - 1]) or np.isnan(atr[i - 1]):
                return None
            a, r = avg_close[i - 1], atr[i - 1] * 1.5
            return (a - r if pos > 0 else a + r) if k == 0 else (a + 2 * r if pos > 0 else a - 2 * r)
        return fn

    ref = simulate(o, h, l, c, orders, stop=level(0), target=level(1))
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="5", data_provider=lambda s, tf: etf,
                                        strategy_overrides={"margin_long": 0, "margin_short": 0}), ref)
    return ok and len(ref) > 10, f"{detail} (need >10 trades, got {len(ref)})"
