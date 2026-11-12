"""Independent check — All-Day Futures Scalper (PVXJsjmB): 5-minute bars (24 h synthetic, price ~100), process_orders_on_close (orders fill at the signal close), default quantity 1, commission / slippage / margin off.
Signal: EMA fast crossing the slow EMA in the direction of the 200 EMA trend, outside the cooldown (bars since the last bar that went flat <= N blocks) and with ATR/close x 100 >= the minimum; entry while flat. Every bar re-issues the brackets from the average entry price (stop avg -/+ ATR x mult, limit avg +/- ATR x mult; with the break-even trigger met by the bar's extreme the stop is at least/at most the entry);
while flat the average price is na so the brackets carry no levels. Uses the quantity-aware bracket reference (indep.simulate_brackets, on_close), comparing quantities too.
Variants: defaults; no break-even, cooldown 0, chop filter off; wider stops (2 ATR) with a 3 ATR target."""
import numpy as np

from indep import bars, compare_q, np_atr, np_cross_over, np_cross_under, np_ema, run_conversion, simulate_brackets
from pinelib import SymbolInfo

TV_ID = "PVXJsjmB"


def one(df, params, p):
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    ef, es, et = np_ema(c, 9), np_ema(c, 21), np_ema(c, 200)
    atr = np_atr(h, l, c, 14)
    up, dn = np_cross_over(ef, es), np_cross_under(ef, es)
    S = dict(prev=0.0, flat=None)

    def orders(i, info):
        out = []
        pos, avg = info["pos"], info["avg"]
        if pos == 0 and S["prev"] != 0:
            S["flat"] = i
        S["prev"] = pos
        cool = p["cd"] > 0 and S["flat"] is not None and (i - S["flat"]) <= p["cd"]
        with np.errstate(invalid="ignore"):
            chop = (not p["chop"]) or (atr[i] / c[i] * 100.0 >= 0.05)
            can = (not cool) and chop
            lc = can and c[i] > et[i] and bool(up[i])
            sc = can and c[i] < et[i] and bool(dn[i])
        if lc and pos == 0:
            out.append(("entry", "L", 1, 1.0))
        if sc and pos == 0:
            out.append(("entry", "S", -1, 1.0))
        if pos != 0 and not np.isnan(avg):
            ls, lt = avg - p["sl"] * atr[i], avg + p["tp"] * atr[i]
            ss, st_ = avg + p["sl"] * atr[i], avg - p["tp"] * atr[i]
            if p["be"] and pos > 0 and (h[i] - avg) >= 1.0 * atr[i]:
                ls = max(ls, avg)
            if p["be"] and pos < 0 and (avg - l[i]) >= 1.0 * atr[i]:
                ss = min(ss, avg)
            out += [("exit", "L-Exit", "L", None, ls, lt), ("exit", "S-Exit", "S", None, ss, st_)]
        return out

    ref = simulate_brackets(o, h, l, c, orders, on_close=True)
    sym = SymbolInfo.make("CME_MINI:ES1!", "futures", qty_step=1e-9)
    ok, d = compare_q(run_conversion(TV_ID, df, symbol=sym, tf="5", params=params,
                                     strategy_overrides={"margin_long": 0, "margin_short": 0, "commission_value": 0, "slippage": 0}), ref)
    return ok and len(ref) > 12, f"{d} (got {len(ref)})"


BASE = dict(cd=3, chop=True, be=True, sl=1.0, tp=1.5)


def check():
    df = bars(40000, seed=311, freq="5min")
    for k in ("open", "high", "low", "close"):
        df[k] = 100 * (df[k] / 100) ** 0.1
    msgs, allok = [], True
    cases = (({}, {}),
             ({"Move Stop to Breakeven": False, "Cooldown Bars After Exit": 0, "Chop Filter: Require ATR% of Price": False}, dict(be=False, cd=0, chop=False)),
             ({"Stop (ATR Mult)": 2.0, "Take Profit (ATR Mult)": 3.0}, dict(sl=2.0, tp=3.0)))
    for params, ov in cases:
        ok, m = one(df, params, {**BASE, **ov})
        allok &= ok
        msgs.append(m)
    return allok, " | ".join(msgs)
