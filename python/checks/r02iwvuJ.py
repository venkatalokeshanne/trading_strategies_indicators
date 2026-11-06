"""Independent check — BB Strategy + SL + Loss Control (r02iwvuJ): 5-min bars. Close crossing back over the lower Bollinger band (20, 2) = long, crossing
under the upper = short (reversing). After two losing trades of a side that side is blocked until the other side wins (the script reads only the latest
closed trade, using `lastDirection` as left by the previous bar). Stop = entryPrice -/+ 8 where entryPrice is the close of the LAST signal bar (even if its
entry was ignored), issued each bar while a position exists. Closed-trade profit = direction * (exit - entry) for 1 contract."""
import numpy as np

from indep import bars, compare, np_cross_over, np_cross_under, np_sma, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "r02iwvuJ"


def one(seed):
    df = bars(20000, seed=seed, freq="5min")
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    basis = np_sma(c, 20)
    sd = np.full(n, np.nan)
    for i in range(19, n):
        sd[i] = np.std(c[i - 19:i + 1])
    up, lo = basis + 2.0 * sd, basis - 2.0 * sd
    lsig, ssig = np_cross_over(c, lo), np_cross_under(c, up)
    log = []
    st = dict(llc=0, slc=0, lb=False, sb=False, ep=np.nan, ld=0, prev_closed=0)
    poscl = np.zeros(n)
    entry_at = np.full(n, np.nan)

    def orders(i, pos):
        poscl[i] = pos
        closed = len(log)
        if closed > 0 and closed != st["prev_closed"]:
            d, eb, ep_, xb, xp = log[-1]
            profit = d * (xp - ep_)
            if st["ld"] == 1:
                if profit < 0:
                    st["llc"] += 1
                else:
                    st["llc"] = 0; st["sb"] = False
                if st["llc"] >= 2:
                    st["lb"] = True
            if st["ld"] == -1:
                if profit < 0:
                    st["slc"] += 1
                else:
                    st["slc"] = 0; st["lb"] = False
                if st["slc"] >= 2:
                    st["sb"] = True
        st["prev_closed"] = closed
        out = []
        if lsig[i] and not st["lb"]:
            out.append(("entry", 1)); st["ep"] = c[i]; st["ld"] = 1
        if ssig[i] and not st["sb"]:
            out.append(("entry", -1)); st["ep"] = c[i]; st["ld"] = -1
        entry_at[i] = st["ep"]
        return out

    def stop(i, pos, ep, eb):
        if i == 0 or poscl[i - 1] != pos or np.isnan(entry_at[i - 1]):
            return None
        return entry_at[i - 1] - 8.0 if pos > 0 else entry_at[i - 1] + 8.0

    with np.errstate(invalid="ignore"):
        ref = simulate(o, h, l, c, orders, stop=stop, log=log)
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="5", strategy_overrides={"margin_long": 0, "margin_short": 0}), ref)
    return ok, detail, len(ref)


def check():
    """The loss control blocks a side after two losses, so a single data set trades little: run several and require > 10 trades in total."""
    res = [one(sd) for sd in (144, 145, 146, 147, 148, 149)]
    total = sum(r[2] for r in res)
    bad = [r[1] for r in res if not r[0]]
    return (not bad) and total > 10, (bad[0] if bad else f"{total} trades identical over {len(res)} data sets") + f" (need >10 trades, got {total})"
