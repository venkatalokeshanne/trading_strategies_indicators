"""Independent check — [3Commas] Gold DCA Long (j36wYVnI): 15-minute bars, market base order at the next open, safety orders as pending LIMIT entries, commission / slippage / margin off, date window widened to the whole sample (passed to both sides).
Lot-based multi-order reference (indep.simulate_lots; one unit per fill, the deal bookkeeping is written separately from the strategy): with no deal open the base order is bought (the bar close becomes the base price, the volume / quantity totals start at the base order);
each bar, while fewer than N safety orders were placed, a low at or below base * (1 - cumulative deviation) places a pending LIMIT buy "SOn" at that price (sizes: first size times the size multiplier^(n-1); several on one bar) and books it into the totals at once;
the average price / take-profit level use the totals from the START of the bar; a high at or above avg * (1 + TP%) closes every lot at the next open (pending limits stay alive and the pyramiding limit of 4 consumes any fill beyond it).
Variants: defaults; 3 safety orders with a wide ladder and multipliers; 4 safety orders (one beyond the pyramiding limit), small step, TP 0.8%."""
import numpy as np

from indep import bars, compare, run_conversion, simulate_lots
from pinelib import SymbolInfo

TV_ID = "j36wYVnI"


def one(df, params, p):
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    S = dict(deal=False, base=None, vol=0.0, qty=0.0, cnt=0)

    def trig(k):
        dev, st = 0.0, p["step"]
        for _ in range(k):
            dev += st
            st *= p["coef"]
        return S["base"] * (1.0 - dev / 100.0)

    def orders(i, nlots):
        out = []
        tp = S["vol"] / S["qty"] * (1.0 + p["tp"] / 100.0) if S["qty"] > 0 else None
        if not S["deal"]:
            q = p["bo"] / c[i]
            S.update(deal=True, base=c[i], vol=p["bo"], qty=q, cnt=0)
            out.append(("buy",))
        if S["deal"]:
            while S["cnt"] < p["maxso"]:
                k = S["cnt"] + 1
                t = trig(k)
                if l[i] <= t:
                    v = p["so"] * p["vcoef"] ** (k - 1)
                    out.append(("buy_limit", "SO%d" % k, t))
                    S["vol"] += v
                    S["qty"] += v / t
                    S["cnt"] = k
                else:
                    break
        if S["deal"] and tp is not None and h[i] >= tp:
            out.append(("close_all",))
            S.update(deal=False, base=None, vol=0.0, qty=0.0, cnt=0)
        return out

    ref = simulate_lots(o, h, l, c, orders, pyramiding=4)
    sym = SymbolInfo.make("BYBIT:XAUTUSDT", "crypto", qty_step=1e-9)
    ok, d = compare(run_conversion(TV_ID, df, symbol=sym, tf="15", params={**params, "Limit by Date Range": False},
                                   strategy_overrides={"margin_long": 0, "margin_short": 0, "slippage": 0, "commission_value": 0}), ref)
    return ok and len(ref) > 8, f"{d} (need >8 lots, got {len(ref)})"


BASE = dict(bo=12.0, so=9.0, maxso=4, step=2.0, coef=1.0, vcoef=1.05, tp=1.5)


def check():
    df = bars(30000, seed=31, freq="15min")
    for k in ("open", "high", "low", "close"):
        df[k] = 100 * (df[k] / 100) ** 0.6
    msgs, allok = [], True
    cases = (({}, {}),
             ({"Max Safety Orders": 3, "Price Step % (1st SO from base)": 3.0, "Deviation Step Multiplier": 1.3, "Order Size Multiplier": 1.5},
              dict(maxso=3, step=3.0, coef=1.3, vcoef=1.5)),
             ({"Price Step % (1st SO from base)": 0.8, "Take Profit % (from avg entry)": 0.8, "Safety Order Volume (USDT)": 20.0},
              dict(step=0.8, tp=0.8, so=20.0)))
    for params, ov in cases:
        ok, m = one(df, params, {**BASE, **ov})
        allok &= ok
        msgs.append(m)
    return allok, " | ".join(msgs)
