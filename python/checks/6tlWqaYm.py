"""Independent check — river 10 min (6tlWqaYm): daily bars, process_orders_on_close, one position (reversals). SuperTrend(3, 10) flips enter (down->up = long); a second SuperTrend(1.5, 7) flip against the position closes it at
the close (before the entry orders of the same bar, in source order). While in a position at a script run: stop = entry price -/+ 2 x ATR14 re-issued each bar (so bar i works with bar i-1's ATR, only if a position existed at bar i-1's
script) and, once the close is >= 1.5% in profit, an additional stop at the entry price that stays for the rest of the trade; the effective stop is the tighter of the two. Margin and slippage off, size 5% on the pinelib side."""
import numpy as np

from indep import bars, compare, np_atr, np_supertrend, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "6tlWqaYm"


def check():
    df = bars(6000, seed=858)
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    _, d1 = np_supertrend(h, l, c, 3.0, 10)
    _, d2 = np_supertrend(h, l, c, 1.5, 7)
    ch1 = d1 - np.r_[np.nan, d1[:-1]]
    ch2 = d2 - np.r_[np.nan, d2[:-1]]
    atr = np_atr(h, l, c, 14)
    S = dict(be=False)
    poscl = np.zeros(n)
    be_at = np.zeros(n, bool)
    ep_now = {"i": -1, "ep": np.nan}

    def orders(i, pos):
        poscl[i] = pos
        out = []
        if pos != 0 and ep_now["i"] == i:
            ep = ep_now["ep"]
            if not S["be"]:
                prof = (c[i] - ep) / ep * 100 if pos > 0 else (ep - c[i]) / ep * 100
                if prof >= 1.5:
                    S["be"] = True
        if pos == 0:
            S["be"] = False
        be_at[i] = S["be"]
        with np.errstate(invalid="ignore"):
            if pos > 0 and ch2[i] > 0:
                out.append(("close", 1))
            if pos < 0 and ch2[i] < 0:
                out.append(("close", -1))
            if ch1[i] < 0:
                out.append(("entry", 1))
            if ch1[i] > 0:
                out.append(("entry", -1))
        return out

    def stop(i, pos, ep, eb):
        ep_now["i"], ep_now["ep"] = i, ep
        if i == 0 or poscl[i - 1] * pos <= 0 or np.isnan(atr[i - 1]):
            return None
        sl = ep - 2.0 * atr[i - 1] if pos > 0 else ep + 2.0 * atr[i - 1]
        if be_at[i - 1]:
            return max(sl, ep) if pos > 0 else min(sl, ep)
        return sl

    with np.errstate(invalid="ignore"):
        ref = simulate(o, h, l, c, orders, stop=stop, on_close=True)
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="D", strategy_overrides={"margin_long": 0, "margin_short": 0, "slippage": 0, "default_qty_value": 5}), ref)
    return ok and len(ref) > 10, f"{detail} (need >10 trades, got {len(ref)})"
