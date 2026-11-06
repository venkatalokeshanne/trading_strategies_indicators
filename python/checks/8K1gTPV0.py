"""Independent check — [3Commas] GOOGLUSDT Long DCA, RSI Exit (8K1gTPV0): 15-minute bars with the RSI timeframe equal to the chart, market base order at the next open, safety orders as pending LIMIT entries, commission / slippage / margin off, date window widened to the whole sample.
Lot-based multi-order reference (indep.simulate_lots; one unit per fill, the deal bookkeeping is written separately from the strategy): with no deal open the base order is bought (the bar close becomes the base price, the totals start at the base order);
each bar, while fewer than N safety orders were placed, a low at or below base * (1 - cumulative deviation) places a pending LIMIT buy "SOn" at that price (sizes: first size times the volume coefficient^(n-1); several on one bar) and books it into the totals at once;
the take-profit level uses the totals from the START of the bar; the RSI value is the PREVIOUS bar's RSI (request.security with lookahead on and [1]) and its cross above the threshold is the sell signal; every lot is closed at the next open when the close is at least avg * (1 + min profit) and (if enabled) the signal fired.
Pending limits stay alive after the close and the pyramiding limit of 9 consumes any fill beyond it.
Variants: defaults; RSI gate off with a wider ladder; RSI 7 / threshold 60, 10 safety orders (one beyond the pyramiding limit), small step."""
import numpy as np

from indep import bars, compare, np_cross_over, np_rsi, run_conversion, simulate_lots
from pinelib import SymbolInfo

TV_ID = "8K1gTPV0"


def one(df, params, p):
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    with np.errstate(invalid="ignore"):
        rsi_prev = np.concatenate([[np.nan], np_rsi(c, p["rl"])[:-1]])
        sig = np_cross_over(rsi_prev, p["thr"])
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
        if S["deal"] and tp is not None and ((not p["gate"]) or bool(sig[i])) and c[i] >= tp:
            out.append(("close_all",))
            S.update(deal=False, base=None, vol=0.0, qty=0.0, cnt=0)
        return out

    ref = simulate_lots(o, h, l, c, orders, pyramiding=9)
    sym = SymbolInfo.make("BITGET:GOOGLUSDT", "crypto", qty_step=1e-9)
    ok, d = compare(run_conversion(TV_ID, df, symbol=sym, tf="15", params={**params, "Limit by Date Range": False},
                                   strategy_overrides={"margin_long": 0, "margin_short": 0, "slippage": 0, "commission_value": 0}), ref)
    return ok and len(ref) > 8, f"{d} (need >8 lots, got {len(ref)})"


BASE = dict(bo=13.5, so=9.0, maxso=8, step=0.5, coef=1.22, vcoef=1.0, tp=0.6, rl=14, thr=70.0, gate=True)


def check():
    df = bars(30000, seed=33, freq="15min")
    for k in ("open", "high", "low", "close"):
        df[k] = 100 * (df[k] / 100) ** 0.6
    msgs, allok = [], True
    cases = (({}, {}),
             ({"Require RSI cross-above for close": False, "Price Step % (1st SO from base)": 1.0, "Martingale Step Coefficient": 1.1, "Martingale Volume Coefficient": 1.3, "Max Safety Orders": 6},
              dict(gate=False, step=1.0, coef=1.1, vcoef=1.3, maxso=6)),
             ({"RSI Length": 7, "RSI Threshold": 60.0, "Max Safety Orders": 10, "Price Step % (1st SO from base)": 0.3, "Min Profit % (from avg entry)": 0.3},
              dict(rl=7, thr=60.0, maxso=10, step=0.3, tp=0.3)))
    for params, ov in cases:
        ok, m = one(df, params, {**BASE, **ov})
        allok &= ok
        msgs.append(m)
    return allok, " | ".join(msgs)
