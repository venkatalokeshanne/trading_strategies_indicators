"""Independent check — LinReg Scale-In (dpkq3n4O): hourly bars. Pearson correlation of close with the bar number over 20 bars
(computed with numpy corrcoef); crossing up 0.25/0.50/0.75 opens a long each (pyramiding 3, fixed size), crossing down 0.25
closes everything. All fills at the next open. The reference trades are built by hand (indep.simulate has no pyramiding)."""
import numpy as np

from indep import bars, compare, run_conversion
from pinelib import SymbolInfo

TV_ID = "dpkq3n4O"


def check():
    df = bars(6000, seed=89, freq="1h")
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    idx = np.arange(n, dtype=float)
    r = np.full(n, np.nan)
    for i in range(19, n):
        r[i] = np.corrcoef(c[i - 19:i + 1], idx[i - 19:i + 1])[0, 1]
    pr = np.r_[np.nan, r[:-1]]

    def up(level):
        with np.errstate(invalid="ignore"):
            return (r > level) & (pr <= level)

    u25, u50, u75 = up(0.25), up(0.50), up(0.75)
    with np.errstate(invalid="ignore"):
        d25 = (r < 0.25) & (pr >= 0.25)
    open_, trades = [], []                                # open_: [(entry_bar, entry_price)]
    for i in range(n - 1):                                # orders from bar i fill at bar i+1's open
        for sig in (u25[i], u50[i], u75[i]):
            if sig and len(open_) < 3:
                open_.append((i + 1, o[i + 1]))
        if d25[i]:
            trades += [(1, eb, ep, i + 1, o[i + 1]) for eb, ep in open_]
            open_ = []
    ours_sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    res = run_conversion(TV_ID, df, symbol=ours_sym, tf="60")
    ok, detail = compare(res, trades)
    return ok and len(trades) > 10, f"{detail} (need >10 trades, got {len(trades)})"
