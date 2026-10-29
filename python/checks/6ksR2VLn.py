"""Independent check — ST Fast/Slow + SMA DCA Basket (6ksR2VLn): 15-minute bars (24 h synthetic, price ~100) of a stock-style symbol, process_orders_on_close (orders fill at the signal close), the strategy's lot size of 5, pyramiding 6, commission / slippage / margin off.
Trend up = fast Supertrend line above the slow line and close above the SMA (down mirrored). While a trend holds, fewer open lots than the maximum and the delay (seconds, bar open times) passed, an order is entered (ids carry a running counter; the pyramiding limit rejects extras but the counter and the delay clock advance).
Basket exits from the open profit at the signal close: take-profit, a trailing exit (peak tracked once the profit reaches the trailing start, exit when it falls back by the distance), and the equity stop (negative level); each closes everything. Uses the quantity-aware bracket reference (indep.simulate_brackets, on_close; info["lots"] for the open profit), comparing quantities too.
Variants: defaults scaled to the price (target 40, stop -40, trailing 20 / 10); max orders 3 with a 1-hour delay; fast multiplier 2 / slow 4."""
import numpy as np

from indep import bars, compare_q, np_sma, np_supertrend, run_conversion, simulate_brackets
from pinelib import SymbolInfo

TV_ID = "6ksR2VLn"


def one(df, params, p):
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    t = df["time"].to_numpy()
    sf, _ = np_supertrend(h, l, c, p["fm"], 10)
    ss, _ = np_supertrend(h, l, c, p["sm"], 10)
    ma = np_sma(c, 10)
    S = dict(peak=np.nan, cnt=0, last=None)

    def orders(i, info):
        out = []
        n_open = info["n"]
        tp_ = sum((c[i] - x["ep"]) * x["q"] * x["d"] for x in info["lots"])
        with np.errstate(invalid="ignore"):
            up = sf[i] > ss[i] and c[i] > ma[i]
            dn = sf[i] < ss[i] and c[i] < ma[i]
        ok_delay = S["last"] is None or (t[i] - S["last"] >= p["delay"] * 1000)
        if up or dn:
            if n_open < p["maxo"] and ok_delay:
                S["cnt"] += 1
                out.append(("entry", ("BUY_%d" if up else "SELL_%d") % S["cnt"], 1 if up else -1, 5.0))
                S["last"] = t[i]
        if n_open > 0 and tp_ >= p["tp"]:
            out.append(("close_all",))
        if n_open > 0:
            if tp_ >= p["ts"]:
                S["peak"] = tp_ if np.isnan(S["peak"]) else max(S["peak"], tp_)
                if tp_ <= S["peak"] - p["td"]:
                    out.append(("close_all",))
            else:
                S["peak"] = np.nan
        if n_open > 0 and tp_ <= p["sl"]:
            out.append(("close_all",))
        if n_open == 0:
            S["peak"] = np.nan
        return out

    ref = simulate_brackets(o, h, l, c, orders, pyramiding=6, on_close=True)
    sym = SymbolInfo.make("NASDAQ:XYZ", "stock", qty_step=1e-9)
    ok, d = compare_q(run_conversion(TV_ID, df, symbol=sym, tf="15", params=params,
                                     strategy_overrides={"margin_long": 0, "margin_short": 0, "commission_value": 0, "slippage": 0}), ref)
    return ok and len(ref) > 12, f"{d} (got {len(ref)})"


BASE = dict(fm=3.0, sm=6.0, maxo=6, delay=60, tp=800.0, sl=-1000.0, ts=400.0, td=300.0)


def check():
    df = bars(30000, seed=361, freq="15min")
    for k in ("open", "high", "low", "close"):
        df[k] = 100 * (df[k] / 100) ** 0.3
    small = {"Basket TP": 40.0, "Equity SL": -40.0, "Trailing Start": 20.0, "Trailing Distance": 10.0}
    sm = dict(tp=40.0, sl=-40.0, ts=20.0, td=10.0)
    msgs, allok = [], True
    cases = ((dict(small), sm),
             ({**small, "Max Orders": 3, "DCA Delay (seconds)": 3600}, dict(sm, maxo=3, delay=3600)),
             ({**small, "ST Fast Mult": 2.0, "ST Slow Mult": 4.0}, dict(sm, fm=2.0, sm=4.0)))
    for params, ov in cases:
        ok, m = one(df, params, {**BASE, **ov})
        allok &= ok
        msgs.append(m)
    return allok, " | ".join(msgs)
