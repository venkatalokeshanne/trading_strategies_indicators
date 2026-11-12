"""Independent check — System 2 Structure Continuation (TlwmnFdI): daily bars. A candle with body > 1.5 ATR14 arms that side (and disarms the other) and records its low (bull) / high (bear). Within 10 bars after it (not on it), a bar that
stays above the recorded low (below the high) and closes in the displacement direction, while flat and past the 10-bar cooldown, enters when the risk distance exceeds one tick (0.01); stop = recorded extreme, target = 2R from the close,
both fixed on the signal bar. The setup is disarmed after a trade. Quantity (2% equity risk) never changes prices."""
import numpy as np

from indep import bars, compare, np_atr, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "TlwmnFdI"


def check():
    df = bars(8000, seed=15)
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    atr = np_atr(h, l, c, 14)
    s = dict(db=None, lo=np.nan, hi=np.nan, bu=False, be=False, lt=None)
    lvl = {}

    def orders(i, pos):
        out = []
        with np.errstate(invalid="ignore"):
            if c[i] - o[i] > atr[i] * 1.5:
                s.update(db=i, lo=l[i], bu=True, be=False)
            if o[i] - c[i] > atr[i] * 1.5:
                s.update(db=i, hi=h[i], be=True, bu=False)
            vp = s["db"] is not None and 0 < i - s["db"] <= 10
            bull = s["bu"] and vp and l[i] > s["lo"] and c[i] > o[i]
            bear = s["be"] and vp and h[i] < s["hi"] and c[i] < o[i]
        cd = s["lt"] is None or i - s["lt"] > 10
        if bull and cd and pos == 0:
            rd = c[i] - s["lo"]
            if rd > 0.01:
                out.append(("entry", 1))
                lvl[1] = (s["lo"], c[i] + rd * 2)
                s["lt"], s["bu"] = i, False
        if bear and cd and pos == 0:
            rd = s["hi"] - c[i]
            if rd > 0.01:
                out.append(("entry", -1))
                lvl[-1] = (s["hi"], c[i] - rd * 2)
                s["lt"], s["be"] = i, False
        return out

    def stop(i, pos, ep, eb):
        return lvl[1 if pos > 0 else -1][0]

    def target(i, pos, ep, eb):
        return lvl[1 if pos > 0 else -1][1]

    with np.errstate(invalid="ignore"):
        ref = simulate(o, h, l, c, orders, stop=stop, target=target)
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="D", strategy_overrides={"margin_long": 0, "margin_short": 0}), ref)
    return ok and len(ref) > 10, f"{detail} (need >10 trades, got {len(ref)})"
