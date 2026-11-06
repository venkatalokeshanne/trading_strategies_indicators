"""Independent check — LUBE (i9tJOtjl): hourly bars, lookbacks shrunk through the inputs (friction window 40, extreme window 60; passed to both sides) for speed.
friction(i) = sum over k = 1..40 of (41 / (k + 40)) for each earlier bar whose high-low range contains the current close; lowf/highf = min/max of friction over 60 bars;
midf = 0.5*lowf + 0.5*highf, lowf2 = 1.1*lowf - 0.1*highf (tlevel -10 -> tl = -0.1), both read 5 bars back. A 4-3-2-1 weighted FIR of the source decides the
trend; long/short when friction < lowf2[5] with the trend, "end" when friction > midf[5]. Orders in source order: entry Long, close Long, entry Short, close Short
(close(id) acts only on an open trade; barcount > 20). Written with plain numpy loops."""
import numpy as np

from indep import bars, compare, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "i9tJOtjl"
B, RNG = 40, 60


def nz(x):
    return 0.0 if np.isnan(x) else x


def one(seed):
    df = bars(5000, seed=seed, freq="1h")
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    fr = np.zeros(n)
    for i in range(n):
        for k in range(1, B + 1):
            if i - k >= 0 and h[i - k] >= c[i] and l[i - k] <= c[i]:
                fr[i] += (1 + B) / (k + B)
    lowf, highf = np.full(n, np.nan), np.full(n, np.nan)
    for i in range(RNG - 1, n):
        lowf[i], highf[i] = fr[i - RNG + 1:i + 1].min(), fr[i - RNG + 1:i + 1].max()
    midf = lowf * (1 - 0.5) + highf * 0.5
    lowf2 = lowf * (1 + 0.1) + highf * (-0.1)
    sh5 = lambda x: np.r_[[np.nan] * 5, x[:-5]]
    mid5, low2_5 = sh5(midf), sh5(lowf2)
    fir = np.array([(4 * c[i] + 3 * nz(c[i - 1] if i >= 1 else np.nan) + 2 * nz(c[i - 2] if i >= 2 else np.nan) + nz(c[i - 3] if i >= 3 else np.nan)) / 10 for i in range(n)])
    pf = np.r_[np.nan, fir[:-1]]
    with np.errstate(invalid="ignore"):
        trend = np.where(fir > pf, 1, -1)
        lg = (fr < low2_5) & (trend == 1)
        sg = (fr < low2_5) & (trend == -1)
        en = fr > mid5

    def orders(i, pos):
        out = []
        bc = i + 1
        if lg[i] and bc > 20:
            out.append(("entry", 1))
        if (sg[i] or en[i]) and pos > 0:
            out.append(("close", 1))
        if sg[i] and bc > 20:
            out.append(("entry", -1))
        if (lg[i] or en[i]) and pos < 0:
            out.append(("close", -1))
        return out

    ref = simulate(o, h, l, c, orders)
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    params = {"bars back to measure friction": B, "bars back to measure lowest friction": RNG}
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="60", params=params, strategy_overrides={"margin_long": 0, "margin_short": 0}), ref)
    return ok, detail, len(ref)


def check():
    """Few signals per data set (friction must fall under a 5-bar-old floor): run several and require > 10 trades in total."""
    res = [one(sd) for sd in (175, 178, 179, 180, 181, 182)]
    total = sum(r[2] for r in res)
    bad = [r[1] for r in res if not r[0]]
    return (not bad) and total > 10, (bad[0] if bad else f"{total} trades identical over {len(res)} data sets") + f" (need >10 trades, got {total})"
