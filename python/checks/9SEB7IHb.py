"""Independent check — VWAP Mean Reversion v6 (9SEB7IHb): daily bars, RSI bounds 35 / 55 and volume multiplier 1.5 here (passed to both sides). basis = volume-weighted mean of close over 60 bars, dev = volume-weighted mean absolute deviation about it,
bands basis +/- 2 dev (na for the first 59 bars). Long when close crosses under the lower band with RSI14 < oversold and not (volume > 1.5 x SMA20 volume); short mirrors. While a position exists (as of a bar's close) the stop (close -/+ 0.5%) and
target (basis) of that bar apply to the same-direction trade on the next bar."""
import numpy as np

from indep import bars, compare, np_cross_over, np_cross_under, np_rsi, np_sma, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "9SEB7IHb"
OB, OS, VM = 55, 35, 1.5


def check():
    df = bars(8000, seed=14)
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    v = df["volume"].to_numpy()
    n = len(c)
    basis = np.full(n, np.nan)
    dev = np.full(n, np.nan)
    for i in range(59, n):
        w, vw = c[i - 59:i + 1], v[i - 59:i + 1]
        basis[i] = (w * vw).sum() / vw.sum()
        dev[i] = (vw * np.abs(w - basis[i])).sum() / vw.sum()
    up, lo = basis + 2 * dev, basis - 2 * dev
    rsi = np_rsi(c, 14)
    ext = v > np_sma(v, 20) * VM
    with np.errstate(invalid="ignore"):
        lg = np_cross_under(c, lo) & (rsi < OS) & ~ext
        sh = np_cross_over(c, up) & (rsi > OB) & ~ext
    poscl = np.zeros(n)

    def orders(i, pos):
        poscl[i] = pos
        out = []
        if lg[i]:
            out.append(("entry", 1))
        if sh[i]:
            out.append(("entry", -1))
        return out

    def stop(i, pos, ep, eb):
        if i == 0 or poscl[i - 1] * pos <= 0:
            return None
        return c[i - 1] * (1 - 0.005) if pos > 0 else c[i - 1] * (1 + 0.005)

    def target(i, pos, ep, eb):
        if i == 0 or poscl[i - 1] * pos <= 0 or np.isnan(basis[i - 1]):
            return None
        return basis[i - 1]

    with np.errstate(invalid="ignore"):
        ref = simulate(o, h, l, c, orders, stop=stop, target=target)
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="D",
                                        params={"RSI Overbought": OB, "RSI Oversold": OS, "Volume Multiplier": VM},
                                        strategy_overrides={"margin_long": 0, "margin_short": 0}), ref)
    return ok and len(ref) > 10, f"{detail} (need >10 trades, got {len(ref)})"
