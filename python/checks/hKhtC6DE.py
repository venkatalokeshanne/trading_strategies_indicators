"""Independent check — Rabiah6X UT Bot scalper (hKhtC6DE): 15-minute bars (the 60-minute HTF input needs a lower chart timeframe), one position (entries reverse), trade list only. UT Bot: nLoss = 2 x ATR10; stop recursion from prev = nz(stop[1], 0): both closes above prev -> max(prev, close - nLoss), both below -> min(prev,
close + nLoss), else close - nLoss if close > prev else close + nLoss. Buy = close crosses over the stop, sell = crosses under. Entry at the next open; while in a position at a script run an exit order is issued with the LIVE stop and the target fixed at the signal
(close +/- (close - stop) x 1), so bar i works with bar i-1's stop and the latest target, only if a same-side position existed at bar i-1's script run. Early exits (close at the next open): DEMA21 (2 EMA21 - EMA21(EMA21)) crossed the wrong way, or RSI14 crossing back under 70
(long) / over 30 (short); these four cross tests are evaluated only while the matching side is open, so each keeps the previous arguments of its LAST EVALUATED bar. Margin and slippage off, 5% size on the pinelib side."""
import numpy as np

from indep import bars, compare, np_atr, np_ema, np_rsi, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "hKhtC6DE"


class Lazy:
    """a cross-over / cross-under test whose previous arguments are those of its last evaluated call."""

    def __init__(self, over):
        self.over, self.prev = over, None

    def __call__(self, a, b):
        res = False
        if self.prev is not None:
            pa, pb = self.prev
            res = (a > b and pa <= pb) if self.over else (a < b and pa >= pb)
        self.prev = (a, b)
        return bool(res)


def check():
    df = bars(12000, seed=402, freq="15min")
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    atr = np_atr(h, l, c, 10)
    e1 = np_ema(c, 21)
    dema = 2 * e1 - np_ema(e1, 21)
    rsi = np_rsi(c, 14)
    xs = np.full(n, np.nan)
    for i in range(n):
        prev = 0.0 if (i == 0 or np.isnan(xs[i - 1])) else xs[i - 1]
        nl = 2.0 * atr[i]
        s, s1 = c[i], (c[i - 1] if i else np.nan)
        with np.errstate(invalid="ignore"):
            if s > prev and s1 > prev:
                xs[i] = max(prev, s - nl)
            elif s < prev and s1 < prev:
                xs[i] = min(prev, s + nl)
            elif s > prev:
                xs[i] = s - nl
            else:
                xs[i] = s + nl
    xs1 = np.r_[np.nan, xs[:-1]]
    c1 = np.r_[np.nan, c[:-1]]
    with np.errstate(invalid="ignore"):
        bb = (c > xs) & (c1 <= xs1)
        bs = (c < xs) & (c1 >= xs1)
    dl, ds = Lazy(False), Lazy(True)
    rl, rs = Lazy(False), Lazy(True)
    S = dict(tl=np.nan, ts=np.nan)
    poscl = np.zeros(n)
    stop_arr = np.full(n, np.nan)
    tgt_arr = np.full(n, np.nan)

    def orders(i, pos):
        poscl[i] = pos
        out = []
        with np.errstate(invalid="ignore"):
            de_l = pos > 0 and dl(c[i], dema[i])
            de_s = pos < 0 and ds(c[i], dema[i])
            re_l = pos > 0 and rl(rsi[i], 70.0)
            re_s = pos < 0 and rs(rsi[i], 30.0)
        if bb[i]:
            S["tl"] = c[i] + (c[i] - xs[i]) * 1.0
            out.append(("entry", 1))
        if bs[i]:
            S["ts"] = c[i] - (xs[i] - c[i]) * 1.0
            out.append(("entry", -1))
        if pos > 0:
            stop_arr[i], tgt_arr[i] = xs[i], S["tl"]
        if pos < 0:
            stop_arr[i], tgt_arr[i] = xs[i], S["ts"]
        if de_l or re_l:
            out.append(("close", 1))
        if de_s or re_s:
            out.append(("close", -1))
        return out

    def stop(i, pos, ep, eb):
        if i == 0 or poscl[i - 1] * pos <= 0 or np.isnan(stop_arr[i - 1]):
            return None
        return stop_arr[i - 1]

    def target(i, pos, ep, eb):
        if i == 0 or poscl[i - 1] * pos <= 0 or np.isnan(tgt_arr[i - 1]):
            return None
        return tgt_arr[i - 1]

    with np.errstate(invalid="ignore"):
        ref = simulate(o, h, l, c, orders, stop=stop, target=target)
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="15", strategy_overrides={"margin_long": 0, "margin_short": 0, "slippage": 0, "default_qty_value": 5}), ref)
    return ok and len(ref) > 10, f"{detail} (need >10 trades, got {len(ref)})"
