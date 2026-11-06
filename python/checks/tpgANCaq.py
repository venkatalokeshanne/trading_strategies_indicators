"""Independent check — Delta Imbalance Strategy (tpgANCaq): 5-min bars, pyramiding 2 (indep.simulate_pyr). delta = (close-open)*volume; var bull/bear imbalances updated in the script's order
(else-branch adds -delta to the bear side), floored at 0 and decayed by 0.95; strength = imbalance / SMA50(|delta|); a bull peak (> 1.5) with a down bar goes short, a bear peak with an up
bar goes long; a second same-direction signal stacks. Exits unconditional: bar i works with bar i-1's close -/+ 2 ATR stop and +/- 3 ATR target for whichever direction is open (also on a fill bar)."""
import numpy as np

from indep import bars, compare, np_atr, np_sma, run_conversion, simulate_pyr
from pinelib import SymbolInfo

TV_ID = "tpgANCaq"


def check():
    df = bars(20000, seed=187, freq="5min")
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    v = df["volume"].to_numpy()
    n = len(c)
    delta = (c - o) * v
    bull = bear = 0.0
    bs, es = np.zeros(n), np.zeros(n)
    avg = np_sma(np.abs(delta), 50)
    for i in range(n):
        d = delta[i]
        if d > 0:
            bull += d
        else:
            bear += -d
        if d < 0:
            bull -= abs(d)
        if d > 0:
            bear -= abs(d)
        bull, bear = max(bull, 0.0), max(bear, 0.0)
        bull *= 0.95
        bear *= 0.95
        with np.errstate(invalid="ignore", divide="ignore"):
            bs[i], es[i] = bull / avg[i] if avg[i] else np.nan, bear / avg[i] if avg[i] else np.nan
    with np.errstate(invalid="ignore"):
        rs = (bs > 1.5) & (delta < 0)
        rl = (es > 1.5) & (delta > 0)
    atr = np_atr(h, l, c, 14)

    def orders(i, pos):
        return ([("entry", -1)] if rs[i] else []) + ([("entry", 1)] if rl[i] else [])

    def stop(i, d, tr):
        return None if i == 0 else (c[i - 1] - 2 * atr[i - 1] if d > 0 else c[i - 1] + 2 * atr[i - 1])

    def target(i, d, tr):
        return None if i == 0 else (c[i - 1] + 3 * atr[i - 1] if d > 0 else c[i - 1] - 3 * atr[i - 1])

    with np.errstate(invalid="ignore"):
        ref = simulate_pyr(o, h, l, c, orders, pyramiding=2, stop=stop, target=target)
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="5", strategy_overrides={"margin_long": 0, "margin_short": 0}), ref)
    return ok and len(ref) > 10, f"{detail} (need >10 trades, got {len(ref)})"
