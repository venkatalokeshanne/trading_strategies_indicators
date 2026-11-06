"""Independent check — [3Commas] Aggressive RSI HYPE/USDT Long (XbtQXDMb): 15-minute bars, market base order at the next open, safety orders as pending LIMIT entries, commission / slippage / margin off, date window off (the default).
Lot-based multi-order reference (indep.simulate_lots; one unit per fill, the deal bookkeeping is written separately from the strategy): with no deal open an RSI cross below the buy level buys the base order (the bar close becomes the base price, the totals start at the base order);
each bar, while fewer than N safety orders were placed, a low at or below base * (1 - cumulative deviation) places a pending LIMIT buy "SOn" at that price (sizes: first size times the volume coefficient^(n-1); several on one bar) and books it into the totals at once;
the take-profit level uses the totals from the START of the bar; every lot is closed at the next open when the close is at least avg * (1 + min profit %) and (if enabled) the RSI crossed above the sell level on that bar.
Pending limits stay alive after the close and the pyramiding limit of 10 consumes any fill beyond it.
Variants: defaults; signal gate off, 3 safety orders with a wide ladder; buy level 40 / sell level 60, 12 safety orders (beyond the pyramiding limit), small steps."""
import numpy as np

from indep import bars, compare, np_cross_over, np_cross_under, np_rsi, run_conversion, simulate_lots
from pinelib import SymbolInfo

TV_ID = "XbtQXDMb"


def one(df, params, p):
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    with np.errstate(invalid="ignore"):
        rsi = np_rsi(c, 14)
        buy = np_cross_under(rsi, p["buy"])
        sell = np_cross_over(rsi, p["sell"])
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
        if not S["deal"] and bool(buy[i]):
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
        if S["deal"] and tp is not None and ((not p["gate"]) or bool(sell[i])) and c[i] >= tp:
            out.append(("close_all",))
            S.update(deal=False, base=None, vol=0.0, qty=0.0, cnt=0)
        return out

    ref = simulate_lots(o, h, l, c, orders, pyramiding=10)
    sym = SymbolInfo.make("BINANCE:HYPEUSDT", "crypto", qty_step=1e-9)
    ok, d = compare(run_conversion(TV_ID, df, symbol=sym, tf="15", params=params,
                                   strategy_overrides={"margin_long": 0, "margin_short": 0, "slippage": 0, "commission_value": 0}), ref)
    return ok and len(ref) > 8, f"{d} (need >8 lots, got {len(ref)})"


BASE = dict(buy=31.0, sell=69.0, bo=45.0, so=55.0, maxso=5, step=1.3, vcoef=1.25, coef=1.30, tp=2.4, gate=True)


def check():
    df = bars(30000, seed=35, freq="15min")
    for k in ("open", "high", "low", "close"):
        df[k] = 100 * (df[k] / 100) ** 0.6
    msgs, allok = [], True
    cases = (({}, {}),
             ({"Require RSI Sell Signal to Close (deal_close_type=strategy)": False, "Max Safety Orders": 3, "Price Deviation % (SO step from base)": 2.5, "Min Profit % (from avg entry)": 1.5},
              dict(gate=False, maxso=3, step=2.5, tp=1.5)),
             ({"RSI Buy Trigger (cross below)": 40.0, "RSI Sell Trigger (cross above)": 60.0, "Max Safety Orders": 12, "Price Deviation % (SO step from base)": 0.4, "Min Profit % (from avg entry)": 0.8},
              dict(buy=40.0, sell=60.0, maxso=12, step=0.4, tp=0.8)))
    for params, ov in cases:
        ok, m = one(df, params, {**BASE, **ov})
        allok &= ok
        msgs.append(m)
    return allok, " | ".join(msgs)
