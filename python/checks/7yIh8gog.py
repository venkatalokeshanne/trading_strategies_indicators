"""Independent check — GLD linear threshold (7yIh8gog): hourly bars. A fixed linear score of five standardised features; long while score >=
threshold, otherwise close. The threshold is set to the score's median (passed to both sides) because the default 0.379 sits far below the
score on these synthetic bars and would never exit."""
import numpy as np

from indep import bars, compare, np_sma, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "7yIh8gog"


def check():
    df = bars(12000, seed=118, freq="1h")
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    v = df["volume"].to_numpy()
    f0 = np_sma(v, 2)
    f1 = o - c
    f2 = (h - c) * (l - c)
    f3 = np_sma(o - c, 2) * np_sma(v, 2)
    f4 = (l - c) * np_sma(v, 2)
    score = (0.5223463687150838
             + 0.0012444888950145 * ((f0 - 6735594.9841713225468993) / 3241843.4822131437249482)
             + 0.0029769186339496 * ((f1 - -0.0910537243947856) / 1.4953030683416331)
             + 0.0061458206471210 * ((f2 - -0.9481280302141537) / 1.4894312820065110)
             + 0.0113005100794886 * ((f3 - -603183.3954082156997174) / 9833879.5778208561241627)
             + 0.0065075254154198 * ((f4 - -8826653.8223241623491049) / 11670853.5754192266613245))
    thr = float(np.nanmedian(score))
    with np.errstate(invalid="ignore"):
        go = score >= thr
    ref = simulate(o, h, l, c, lambda i, pos: [("entry", 1)] if go[i] else ([("close", 1)] if pos > 0 else []))
    sym = SymbolInfo.make("AMEX:GLD", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="60", params={"Threshold": thr}), ref)
    return ok and len(ref) > 10, f"{detail} (need >10 trades, got {len(ref)})"
