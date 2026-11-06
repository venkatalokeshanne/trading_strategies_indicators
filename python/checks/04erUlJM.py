"""Independent check — LINK breakout (04erUlJM): hourly bars, process_orders_on_close, long only. While flat: close > SMA200, 50 <= RSI14 <= 70, MACD line above its signal with a positive histogram, close above the breakout level (set to 95 on the pinelib side, or the hard-coded 12.00 with the confirmation off, i.e. always true at these prices). Entry at the close;
stop -1.5 % / target +3 % of the entry price, placed with the entry (work from the next bar). Variants: level 95 with confirmation; confirmation off with wider RSI band. Margin off on the pinelib side."""
import numpy as np

from indep import bars, compare, np_ema, np_rsi, np_sma, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "04erUlJM"


def one(df, params, level, rmin, rmax):
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    sma = np_sma(c, 200)
    rsi = np_rsi(c, 14)
    macd = np_ema(c, 12) - np_ema(c, 26)
    sig = np_ema(macd, 9)
    with np.errstate(invalid="ignore"):
        cond = (c > sma) & (rsi >= rmin) & (rsi <= rmax) & (macd > sig) & ((macd - sig) > 0) & (c > level)
    lev = {}

    def orders(i, pos):
        if pos == 0 and cond[i]:
            lev[i] = (c[i] * 0.985, c[i] * 1.03)
            return [("entry", 1)]
        return []

    stop = lambda i, pos, ep, eb: lev[eb][0] if (eb in lev and eb < i) else None
    tgt = lambda i, pos, ep, eb: lev[eb][1] if (eb in lev and eb < i) else None
    with np.errstate(invalid="ignore"):
        ref = simulate(o, h, l, c, orders, stop=stop, target=tgt, on_close=True)
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, d = compare(run_conversion(TV_ID, df, symbol=sym, tf="60", params=params, strategy_overrides={"margin_long": 0, "margin_short": 0}), ref)
    return ok and len(ref) > 10, f"{d} (got {len(ref)})"


def check():
    df = bars(40000, seed=781, freq="1h")
    msgs, allok = [], True
    for params, lv, a, b in (({"Breakout Level": 95.0}, 95.0, 50.0, 70.0), ({"Require Breakout Confirmation": False, "Minimum RSI for Long": 40.0, "Maximum RSI for Long": 80.0}, 12.0, 40.0, 80.0)):
        ok, m = one(df, params, lv, a, b)
        allok &= ok
        msgs.append(m)
    return allok, " | ".join(msgs)
