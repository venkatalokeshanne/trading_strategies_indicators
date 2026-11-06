"""Independent check — Tetrad Elektro Community v1.0 (YgYQ9MG2): daily-style synthetic bars (hourly spacing so the time stop spans days), market orders at the next open, one position. Long: close <= lower Bollinger band (SMA, 3.3 x population stdev), RSI(14) <= 23 and RSI(7) <= 85. Short: close >= upper band with RSI(14) >= 77 and RSI(7) >= 23, or a bearish divergence (close above the highest of the previous 20 closes while RSI(14) or the MACD line (12, 26) is under its own previous-20 high). Long exit: the upper-band condition; short exit: close <= lower band or (RSI(14) <= 23 and RSI(7) <= 23). Optional stop = average price x factor (0.85 / 1.09), issued once in the position so it works from the bar after the fill; optional time stop closes after N days since the fill bar's open time. With "flat first" off a new opposite entry reverses. Commission / slippage / margin off on the pinelib side.
Variants: looser bands (SMA 100, 2 sd, RSI 30 / 70); the same with stops (0.97 / 1.03), a 2-day time stop and reversal allowed; long only with the divergence short disabled."""
import numpy as np
import pandas as pd

from indep import bars, compare, np_ema, np_rsi, np_sma, run_conversion, simulate

TV_ID = "YgYQ9MG2"


def one(df, params, bbn, bbm, lm, xm, flat_first, use_stop, lsf, ssf, tdays, mode, bdiv):
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    t = df["time"].to_numpy()
    n = len(c)
    s = pd.Series(c)
    basis = np_sma(c, bbn)
    dev = bbm * s.rolling(bbn).std(ddof=0).to_numpy()
    up, lo = basis + dev, basis - dev
    rm, rf = np_rsi(c, 14), np_rsi(c, 7)
    macd = np_ema(c, 12) - np_ema(c, 26)
    pr = lambda x: np.r_[np.nan, x[:-1]]
    hc = pd.Series(pr(c)).rolling(20).max().to_numpy()
    hr = pd.Series(pr(rm)).rolling(20).max().to_numpy()
    hm = pd.Series(pr(macd)).rolling(20).max().to_numpy()
    with np.errstate(invalid="ignore"):
        div = bdiv & (c > hc) & ((rm < hr) | (macd < hm))
        buy = (c <= lo) & (rm <= lm) & (rf <= 85.0)
        sell = (c >= up) & (rm >= xm) & (rf >= 23.0)
        shortc = sell | div
        shortx = (c <= lo) | ((rm <= lm) & (rf <= 23.0))
    S = dict(et=np.nan, pp=0)
    allow_long = mode in ("both", "long")
    allow_short = mode in ("both", "short")

    def orders(i, pos):
        out = []
        if pos != 0 and S["pp"] == 0:
            S["et"] = t[i]
        if pos == 0 and S["pp"] != 0:
            S["et"] = np.nan
        S["pp"] = pos
        col = allow_long and buy[i] and (pos == 0 if flat_first else pos <= 0)
        cos = allow_short and shortc[i] and (pos == 0 if flat_first else pos >= 0)
        if col:
            out.append(("entry", 1))
        if cos:
            out.append(("entry", -1))
        if pos > 0 and sell[i]:
            out.append(("close", 1))
        if pos < 0 and shortx[i]:
            out.append(("close", -1))
        if tdays and pos != 0 and not np.isnan(S["et"]) and (t[i] - S["et"]) / 86400000.0 >= tdays:
            out += [("close", 1), ("close", -1)]       # close_all: whatever is open when the order fills
        return out

    def stop(i, pos, ep, eb):
        if not use_stop or i <= eb:
            return None
        return ep * (lsf if pos > 0 else ssf)

    with np.errstate(invalid="ignore"):
        ref = simulate(o, h, l, c, orders, stop=stop)
    ok, d = compare(run_conversion(TV_ID, df, tf="60", params=params, strategy_overrides={"slippage": 0, "commission_value": 0, "margin_long": 0, "margin_short": 0}), ref)
    return ok and len(ref) > 5, f"{d} (got {len(ref)})"


def check():
    df = bars(30000, seed=321, freq="60min")
    for k in ("open", "high", "low", "close"):
        df[k] = 100 * (df[k] / 100) ** 0.4
    msgs, allok = [], True
    base = {"Bollinger Length": 100, "Bollinger Multiplier": 2.0, "Long Entry Main RSI ≤": 30.0, "Long Exit / Short Setup Main RSI ≥": 70.0}
    cases = ((base, (100, 2.0, 30.0, 70.0, True, False, 0.85, 1.09, 0, "both", True)),
             (dict(base, **{"Use Stop Loss?": True, "Long Stop Factor": 0.97, "Short Stop Factor": 1.03, "Use Time-Based Stop?": True,
                            "Require Flat Before New Opposite Entry?": False}), (100, 2.0, 30.0, 70.0, False, True, 0.97, 1.03, 2, "both", True)),
             (dict(base, **{"Trade Mode": "Long Only", "Enable Bearish Divergence Short Setup?": False}), (100, 2.0, 30.0, 70.0, True, False, 0.85, 1.09, 0, "long", False)))
    for params, args in cases:
        ok, m = one(df, params, *args)
        allok &= ok
        msgs.append(m)
    return allok, " | ".join(msgs)
