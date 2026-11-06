"""Independent check — Mpatel RSI 2-Entry (5LYHXbqi): daily bars (returns compressed 3x), pyramiding 2 (indep.simulate_pyr), 1 unit per lot, long only, market orders at the next open. Buy1: RSI14 crosses under 30, close <= the limit price (set to the median close) and flat. Once Buy1 is open (script-time lot count 1 after 0), dca2 = its fill price x 0.98; Buy2: RSI crosses under 30 again, close <= dca2, Buy1 open, Buy2 not yet.
At every script run with lots open the take-profit avg x 1.03 (and, in the stop variant, stop avg x 0.92) are issued for both entry ids and work from the next bar on all lots (a lot filled at that next open is covered too). A RSI cross over 70 closes everything at the next open. The tracking flags reset whenever the script runs flat. Variants: TP 3 %; TP 1 % with stop 2 %. Margin / slippage off on the pinelib side."""
import numpy as np

from indep import bars, compare, np_cross_over, np_cross_under, np_rsi, run_conversion, simulate_pyr
from pinelib import SymbolInfo

TV_ID = "5LYHXbqi"


def one(df, params, limit, tp, sl):
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    rsi = np_rsi(c, 14)
    os_, ob = np_cross_under(rsi, 30.0), np_cross_over(rsi, 70.0)
    S = dict(fill=np.nan, dca=np.nan, e1=False, e2=False, prev=0, avg=np.nan, avg_i=-1)
    tp_arr, sl_arr = np.full(n, np.nan), np.full(n, np.nan)

    def stop(i, d, trades):
        S["avg"], S["avg_i"] = float(np.mean([t[2] for t in trades])), i
        S["first"] = trades[0][2]
        if i == 0 or sl is None or np.isnan(sl_arr[i - 1]):
            return None
        return sl_arr[i - 1]

    def target(i, d, trades):
        return None if (i == 0 or np.isnan(tp_arr[i - 1])) else tp_arr[i - 1]

    def orders(i, pos):
        out = []
        k = abs(pos)
        flat = k == 0
        if flat:
            S.update(fill=np.nan, dca=np.nan, e1=False, e2=False)
        if k == 1 and S["prev"] == 0 and not S["e1"]:
            S["fill"] = S["first"] if S["avg_i"] == i else np.nan
            S["dca"] = S["fill"] * 0.98
            S["e1"] = True
        if k == 2 and S["prev"] == 1 and not S["e2"]:
            S["e2"] = True
        S["prev"] = k
        with np.errstate(invalid="ignore"):
            b1 = os_[i] and c[i] <= limit and flat
            b2 = os_[i] and not np.isnan(S["dca"]) and c[i] <= S["dca"] and S["e1"] and not S["e2"]
        if b1:
            out.append(("entry", 1))
        if b2:
            out.append(("entry", 1))
        if pos > 0 and S["avg_i"] == i:
            tp_arr[i] = S["avg"] * (1 + tp / 100)
            if sl is not None:
                sl_arr[i] = S["avg"] * (1 - sl / 100)
        if pos > 0 and ob[i]:
            out.append(("close", 1))
        return out

    with np.errstate(invalid="ignore"):
        ref = simulate_pyr(o, h, l, c, orders, pyramiding=2, stop=stop, target=target)
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, d = compare(run_conversion(TV_ID, df, symbol=sym, tf="D", params={**params, "Limit Buy Price": limit},
                                   strategy_overrides={"margin_long": 0, "margin_short": 0, "slippage": 0}), ref)
    return ok and len(ref) > 10, f"{d} (got {len(ref)})"


def check():
    df = bars(14000, seed=861)
    for k in ("open", "high", "low", "close"):
        df[k] = 100.0 * (df[k] / 100.0) ** (1 / 3)
    limit = float(np.median(df["close"]))
    msgs, allok = [], True
    for params, tp, sl in (({}, 3.0, None), ({"Take Profit (%)": 1.0, "Enable Stop Loss": True, "Stop Loss (%)": 2.0}, 1.0, 2.0)):
        ok, m = one(df, params, limit, tp, sl)
        allok &= ok
        msgs.append(m)
    return allok, " | ".join(msgs)
