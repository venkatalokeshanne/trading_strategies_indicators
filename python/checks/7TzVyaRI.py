"""Independent check — Fibonacci Concept Execution Engine (7TzVyaRI): 15-minute bars (24 h synthetic, price ~100, tick 0.01) of a stock-style symbol, market orders at the next open, default quantity 1, commission / slippage / margin off.
Fibonacci levels from the highest high / lowest low of the lookback; the script's in-trade flag gates new signals (it is maintained from the bar's high / low versus the stored stop / target - the touch is evaluated on the signal bar itself, using the CURRENT bar, and a break-even touch moves the stop to the entry and re-issues the exit order). Long: close over SMA290 and EMA200 and a close crossing UNDER the retracement
from the high; short: below both and crossing OVER the retracement from the low. Entry and exit order issued together. Uses the quantity-aware bracket reference (indep.simulate_brackets), comparing quantities too. Variants: SMA 50 / EMA 30 with RR 1.5 and a 50-tick stop; MA filter off with BE at 0.5 R; fib 0.5, lookback 10."""
import numpy as np

from indep import bars, compare_q, np_cross_over, np_cross_under, np_ema, np_sma, run_conversion, simulate_brackets
from pinelib import SymbolInfo

TV_ID = "7TzVyaRI"


def one(df, params, p):
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    sym = SymbolInfo.make("NASDAQ:XYZ", "stock", qty_step=1e-9)
    tick = sym.mintick
    sm, em = np_sma(c, p["sma"]), np_ema(c, p["ema"])
    L = p["lb"]
    hh = np.array([h[i - L + 1:i + 1].max() if i >= L - 1 else np.nan for i in range(n)])
    ll = np.array([l[i - L + 1:i + 1].min() if i >= L - 1 else np.nan for i in range(n)])
    rg = hh - ll
    lf, sf = hh - rg * p["fib"], ll + rg * p["fib"]
    cd, cu = np_cross_under(c, lf), np_cross_over(c, sf)
    S = dict(it=False, d=0, ep=np.nan, sl=np.nan, tp=np.nan, be=np.nan, ba=False)

    def orders(i, info):
        out = []
        with np.errstate(invalid="ignore"):
            lok = (not p["ma"]) or (c[i] > sm[i] and c[i] > em[i])
            sok = (not p["ma"]) or (c[i] < sm[i] and c[i] < em[i])
            if not S["it"]:
                lc, sc = lok and bool(cd[i]), sok and bool(cu[i])
                if lc or sc:
                    risk = p["ticks"] * tick
                    S.update(it=True, d=1 if lc else -1, ep=c[i], ba=False)
                    if lc:
                        S.update(sl=c[i] - risk, tp=c[i] + risk * p["rr"], be=c[i] + risk * p["be"])
                        out += [("entry", "Long", 1, 1.0), ("exit", "Exit", "Long", None, S["sl"], S["tp"])]
                    else:
                        S.update(sl=c[i] + risk, tp=c[i] - risk * p["rr"], be=c[i] - risk * p["be"])
                        out += [("entry", "Short", -1, 1.0), ("exit", "Exit", "Short", None, S["sl"], S["tp"])]
            if S["it"]:
                d = S["d"]
                hsl = (d == 1 and l[i] <= S["sl"]) or (d == -1 and h[i] >= S["sl"])
                htp = (d == 1 and h[i] >= S["tp"]) or (d == -1 and l[i] <= S["tp"])
                hbe = (not S["ba"]) and p["ube"] and ((d == 1 and h[i] >= S["be"]) or (d == -1 and l[i] <= S["be"]))
                if hbe:
                    S["ba"] = True
                    S["sl"] = S["ep"]
                    out.append(("exit", "Exit", "Long" if d == 1 else "Short", None, S["sl"], S["tp"]))
                if hsl or htp:
                    S["it"] = False
        return out

    ref = simulate_brackets(o, h, l, c, orders)
    ok, d = compare_q(run_conversion(TV_ID, df, symbol=sym, tf="15", params=params,
                                     strategy_overrides={"margin_long": 0, "margin_short": 0, "commission_value": 0, "slippage": 0}), ref)
    return ok and len(ref) > 12, f"{d} (got {len(ref)})"


BASE = dict(sma=290, ema=200, lb=20, fib=0.618, ticks=100, rr=2.0, be=1.0, ube=True, ma=True)


def check():
    df = bars(40000, seed=551, freq="15min")
    for k in ("open", "high", "low", "close"):
        df[k] = 100 * (df[k] / 100) ** 0.3
    msgs, allok = [], True
    cases = (({"SMA Length": 50, "EMA Length": 30, "Risk:Reward Ratio": 1.5, "Fixed SL (Ticks)": 50}, dict(sma=50, ema=30, rr=1.5, ticks=50)),
             ({"Use MA Filter (Above=Buy, Below=Sell)": False, "Trigger BE at RR (e.g., 1.0 = 1:1)": 0.5, "Fixed SL (Ticks)": 50}, dict(ma=False, be=0.5, ticks=50)),
             ({"Use MA Filter (Above=Buy, Below=Sell)": False, "Fibonacci Entry Level": 0.5, "Swing Lookback (Bars)": 10, "Enable Break Even (BE)": False, "Fixed SL (Ticks)": 70}, dict(ma=False, fib=0.5, lb=10, ube=False, ticks=70)))
    for params, ov in cases:
        ok, m = one(df, params, {**BASE, **ov})
        allok &= ok
        msgs.append(m)
    return allok, " | ".join(msgs)
