"""Independent check — Monthly Returns / pivot reversal (kzp8e4X3): daily bars, 25 % equity, pending stop entries. pivothigh(2, 1) / pivotlow(2, 1): a bar whose high (low) is above (below) the two bars before and the bar after, known one bar later. The last pivot high (low) price is remembered; the long flag turns on at a pivot high and off once a bar's high exceeds that price (short flag: pivot low / low below it). While a flag is on a buy-stop at pivot high + 1 tick (sell-stop at pivot low - 1 tick) is re-placed at every bar close; stops fill at their level (at the open when gapped) and reverse the opposite position. Uses the pending-order reference broker (simulate_ord). Commission and margin off on the pinelib side."""
import numpy as np

from indep import bars, compare, run_conversion, simulate_ord

TV_ID = "kzp8e4X3"


def check():
    df = bars(5000, seed=26)
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    S = dict(hp=0.0, lp=0.0, le=False, se=False)

    def orders(i, pos):
        swh = swl = np.nan
        if i >= 3:
            j = i - 1
            if h[j] > h[j - 2:j].max() and h[j] > h[i]:
                swh = h[j]
            if l[j] < l[j - 2:j].min() and l[j] < l[i]:
                swl = l[j]
        S["hp"] = swh if not np.isnan(swh) else S["hp"]
        S["lp"] = swl if not np.isnan(swl) else S["lp"]
        S["le"] = True if not np.isnan(swh) else (False if (S["le"] and h[i] > S["hp"]) else S["le"])
        S["se"] = True if not np.isnan(swl) else (False if (S["se"] and l[i] < S["lp"]) else S["se"])
        out = []
        if S["le"]:
            out.append(("entry", "PivRevLE", 1, S["hp"] + 0.01, None))
        if S["se"]:
            out.append(("entry", "PivRevSE", -1, S["lp"] - 0.01, None))
        return out

    ref = simulate_ord(o, h, l, c, orders)
    ok, d = compare(run_conversion(TV_ID, df, strategy_overrides={"commission_value": 0, "margin_long": 0, "margin_short": 0}), ref)
    return ok and len(ref) > 10, f"{d} (got {len(ref)})"
