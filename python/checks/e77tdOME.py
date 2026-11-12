"""Independent check — Reversal & COG (e77tdOME): daily bars. State A (kept between bars): +1 when close[2] < close[1] < close with SMA20(stoch4) below its SMA4 signal and above 4; -1 mirrored. State B: +1 when the
close is above the linear-regression value (length 5, offset 14, np.polyfit extrapolated to x = L-1-offset) + 1 % of close, -1 below it - 1 %. Both +1 -> long, both -1 -> short (entries repeat harmlessly), anything else closes
everything when a position exists. Second run with the % stop on: unconditional exits at the position's average price as of the previous close -/+ 1.5 % (OLD average on a reversal's first bar). Margin off on the
pinelib side."""
import numpy as np

from indep import bars, compare, np_sma, np_stoch, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "e77tdOME"


def linreg_at(c, L, off):
    n = len(c)
    out = np.full(n, np.nan)
    x = np.arange(L)
    for i in range(L - 1, n):
        slope, icpt = np.polyfit(x, c[i - L + 1:i + 1], 1)
        out[i] = icpt + slope * (L - 1 - off)
    return out


def check():
    df = bars(5000, seed=236)
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    vf = np_sma(np_stoch(c, h, l, 4), 20)
    vs = np_sma(vf, 4)
    c1, c2 = np.r_[np.nan, c[:-1]], np.r_[np.nan, np.nan, c[:-2]]
    lg = linreg_at(c, 5, 14)
    with np.errstate(invalid="ignore"):
        up = (c2 < c1) & (c > c1) & (vf < vs) & (vf > 4)
        dn = (c2 > c1) & (c < c1) & (vf > vs) & (vf < 4)
        cu, cd = c > lg + c * 1.0 / 100, c < lg - c * 1.0 / 100
    pa = pb = 0.0
    sig = np.zeros(n, int)
    for i in range(n):
        pa = 1.0 if up[i] else (-1.0 if dn[i] else pa)
        pb = 1.0 if cu[i] else (-1.0 if cd[i] else pb)
        sig[i] = 1 if (pa == 1 and pb == 1) else (-1 if (pa == -1 and pb == -1) else 0)
    msgs, ok_all = [], True
    for sl_on in (False, True):
        ep_now, avg_close = {}, np.full(n, np.nan)

        def orders(i, pos):
            avg_close[i] = ep_now.get(i, np.nan) if pos != 0 else np.nan
            out = []
            if sig[i] == 1:
                out.append(("entry", 1))
            if sig[i] == -1:
                out.append(("entry", -1))
            if sig[i] == 0 and pos != 0:
                out += [("close", 1), ("close", -1)]
            return out

        def stop(i, pos, ep, eb):
            ep_now[i] = ep
            if not sl_on or i == 0 or np.isnan(avg_close[i - 1]):
                return None
            return avg_close[i - 1] * (1 - 1.5 / 100) if pos > 0 else avg_close[i - 1] * (1 + 1.5 / 100)

        with np.errstate(invalid="ignore"):
            ref = simulate(o, h, l, c, orders, stop=stop)
        sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
        ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="D", params={"Use Stop Loss (%)": True} if sl_on else None,
                                            strategy_overrides={"margin_long": 0, "margin_short": 0}), ref)
        ok_all = ok_all and ok and len(ref) > 10
        msgs.append(f"SL {'on' if sl_on else 'off'}: {detail} ({len(ref)})")
    return ok_all, "; ".join(msgs)
