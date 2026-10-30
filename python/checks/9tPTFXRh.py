"""Independent check — All-Day Futures Trend Pullback (9tPTFXRh): daily bars, stop / target 300 / 600 ticks of 0.01 (3 / 6 price units) here (passed to both sides), no trailing, orders at the signal close (process_orders_on_close). Long: close > EMA100 and RSI14 <= 45 and not long;
short: close < EMA100 and RSI14 >= 55 and not short (reversing). While a position exists (as of a bar's close) its own-direction stop / target around the position average price are issued and work from the next bar."""
import numpy as np

from indep import bars, compare, np_ema, np_rsi, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "9tPTFXRh"
SLT, TPT = 300, 600


def check():
    df = bars(9000, seed=7)
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    ema, rsi = np_ema(c, 100), np_rsi(c, 14)
    with np.errstate(invalid="ignore"):
        lg = (c > ema) & (rsi <= 45)
        sh = (c < ema) & (rsi >= 55)
    poscl = np.zeros(n)

    def orders(i, pos):
        poscl[i] = pos
        out = []
        if lg[i] and pos <= 0:
            out.append(("entry", 1))
        if sh[i] and pos >= 0:
            out.append(("entry", -1))
        return out

    def stop(i, pos, ep, eb):
        if i == 0 or poscl[i - 1] * pos <= 0:
            return None
        return ep - SLT * 0.01 if pos > 0 else ep + SLT * 0.01

    def target(i, pos, ep, eb):
        if i == 0 or poscl[i - 1] * pos <= 0:
            return None
        return ep + TPT * 0.01 if pos > 0 else ep - TPT * 0.01

    with np.errstate(invalid="ignore"):
        ref = simulate(o, h, l, c, orders, stop=stop, target=target, on_close=True)
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="D", params={"Stop Loss (ticks)": SLT, "Take Profit (ticks)": TPT},
                                        strategy_overrides={"margin_long": 0, "margin_short": 0}), ref)
    return ok and len(ref) > 10, f"{detail} (need >10 trades, got {len(ref)})"
