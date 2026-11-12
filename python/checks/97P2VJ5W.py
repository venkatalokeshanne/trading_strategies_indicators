"""Independent check — EMA 9/21 GoldenX Pro-TSL (97P2VJ5W): daily bars, both directions. EMA9 crossing EMA21 with (volume > SMA5 volume or close > SMA5 close [short: < ]) and (ADX14 > 20 or |+DI - -DI| > 10) goes long (short): when the opposite side is open it closes it and enters
(reversal at the next open), when flat it enters, otherwise nothing. While a position exists (as of a bar's close) a stop = min(close - 2 ATR, entry*(1-1%)) (short: max(close + 2 ATR, entry*(1+1%))) is issued for the same-direction trade from the next bar."""
import numpy as np

from indep import bars, compare, np_atr, np_cross_over, np_cross_under, np_dmi, np_ema, np_sma, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "97P2VJ5W"


def check():
    df = bars(9000, seed=38)
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    v = df["volume"].to_numpy()
    n = len(c)
    f, s = np_ema(c, 9), np_ema(c, 21)
    dp, dm, adx = np_dmi(h, l, c, 14)
    atr = np_atr(h, l, c, 14)
    with np.errstate(invalid="ignore"):
        trend = (adx > 20) | (np.abs(dp - dm) > 10)
        vr = v > np_sma(v, 5)
        sm5 = np_sma(c, 5)
        ls = np_cross_over(f, s) & (vr | (c > sm5)) & trend
        ss = np_cross_under(f, s) & (vr | (c < sm5)) & trend
    tmp, lv = {}, {}

    def orders(i, pos):
        out = []
        if ls[i]:
            if pos < 0:
                out += [("close", -1), ("entry", 1)]
            elif pos == 0:
                out.append(("entry", 1))
        if ss[i]:
            if pos > 0:
                out += [("close", 1), ("entry", -1)]
            elif pos == 0:
                out.append(("entry", -1))
        ep = tmp.get(i) if pos != 0 else None
        if ep is None:
            lv[i] = None
        elif pos > 0:
            lv[i] = (1, min(c[i] - atr[i] * 2.0, ep * (1 - 0.01)))
        else:
            lv[i] = (-1, max(c[i] + atr[i] * 2.0, ep * (1 + 0.01)))
        return out

    def stop(i, pos, ep, eb):
        tmp[i] = ep
        p = lv.get(i - 1) if i > 0 else None
        if p is None or p[0] * pos <= 0 or np.isnan(p[1]):
            return None
        return p[1]

    with np.errstate(invalid="ignore"):
        ref = simulate(o, h, l, c, orders, stop=stop)
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="D", strategy_overrides={"margin_long": 0, "margin_short": 0}), ref)
    return ok and len(ref) > 10, f"{detail} (need >10 trades, got {len(ref)})"
