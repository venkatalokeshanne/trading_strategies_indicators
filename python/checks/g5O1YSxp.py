"""Independent check — RSI Exact Divergence Strategy (g5O1YSxp): hourly bars of a crypto-style symbol (daily periods from 00:00 UTC), market orders at the next open, fixed quantity 10 on the pinelib side (the original sizes 100 % of equity), commission / slippage / margin off.
RSI(14) pivots (left = right = L bars) paired with the price extreme and RSI value at the pivot bar (L bars back); higher price high + lower RSI high with an overbought level reached by either RSI high = bearish divergence; lower low + higher RSI low with oversold = bullish; the earlier pivot may be at most 'max lookback' bars old.
Daily filter: previous day's close vs previous day's EMA(200) of daily closes (expression offset by one daily bar, lookahead off: the value of period p shows on its last chart bar, the previous period's before that). A bullish divergence with trend up buys, a bearish one with trend down sells (entries reverse); an opposite divergence closes an open position.
Uses the quantity-aware bracket reference (indep.simulate_brackets), comparing quantities too. Variants: HTF filter off; pivot 3 with max lookback 40 and levels 60 / 40."""
import numpy as np

from indep import bars, compare_q, np_ema, np_periods, np_rsi, np_security_lookahead_off, run_conversion, simulate_brackets
from pinelib import SymbolInfo

TV_ID = "g5O1YSxp"
QTY = 10.0


def pivots(x, k, high):
    n = len(x)
    out = np.full(n, np.nan)
    for i in range(2 * k, n):
        m = i - k
        c = x[m]
        if np.isnan(c):
            continue
        lw, rw = x[m - k:m], x[m + 1:i + 1]
        ok = (np.all(c > lw) and np.all(c >= rw)) if high else (np.all(c < lw) and np.all(c <= rw))
        if ok:
            out[i] = c
    return out


def one(df, params, p):
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    k = p["lb"]
    rsi = np_rsi(c, 14)
    pid, last_of = np_periods(df, 1440, start_minutes=0, tz="UTC")
    pc = c[last_of]
    pe = np_ema(pc, 200)
    pe_prev = np.r_[np.nan, pe[:-1]]
    pc_prev = np.r_[np.nan, pc[:-1]]
    hema = np_security_lookahead_off(pe_prev, pid, last_of)
    hclose = np_security_lookahead_off(pc_prev, pid, last_of)
    with np.errstate(invalid="ignore"):
        up = (not p["htf"]) or (hclose > hema)
        dn = (not p["htf"]) or (hclose < hema)
    pvh, pvl = pivots(rsi, k, True), pivots(rsi, k, False)
    S = dict(t=(np.nan,) * 3, tb=np.nan, pt=(np.nan,) * 3, ptb=np.nan, b=(np.nan,) * 3, bb=np.nan, pb=(np.nan,) * 3, pbb=np.nan)

    def orders(i, info):
        out = []
        pos = info["pos"]
        rl = rsi[i - k] if i >= k else np.nan
        hl_, ll_ = (h[i - k], l[i - k]) if i >= k else (np.nan, np.nan)
        if not np.isnan(pvh[i]):
            S["pt"], S["ptb"] = S["t"], S["tb"]
            S["t"], S["tb"] = (rl, hl_), i - k
        if not np.isnan(pvl[i]):
            S["pb"], S["pbb"] = S["b"], S["bb"]
            S["b"], S["bb"] = (rl, ll_), i - k
        bear = bull = False
        with np.errstate(invalid="ignore"):
            if not np.isnan(pvh[i]) and not np.isnan(S["ptb"]) and (i - S["ptb"]) <= p["ml"]:
                prsi, ppx = S["pt"]
                if hl_ > ppx and rl < prsi and (prsi >= p["ob"] or rl >= p["ob"]):
                    bear = True
            if not np.isnan(pvl[i]) and not np.isnan(S["pbb"]) and (i - S["pbb"]) <= p["ml"]:
                prsi, ppx = S["pb"]
                if ll_ < ppx and rl > prsi and (prsi <= p["os"] or rl <= p["os"]):
                    bull = True
        bs = bull and bool(up[i] if hasattr(up, "__len__") else up)
        ss = bear and bool(dn[i] if hasattr(dn, "__len__") else dn)
        if bs:
            out.append(("entry", "Long", 1, QTY))
        if ss:
            out.append(("entry", "Short", -1, QTY))
        if bear and pos > 0:
            out.append(("close", "Long"))
        if bull and pos < 0:
            out.append(("close", "Short"))
        return out

    ref = simulate_brackets(o, h, l, c, orders)
    sym = SymbolInfo.make("BINANCE:XYZUSDT", "crypto", qty_step=1e-9)
    ok, d = compare_q(run_conversion(TV_ID, df, symbol=sym, tf="60", params=params,
                                     strategy_overrides={"margin_long": 0, "margin_short": 0, "commission_value": 0, "slippage": 0, "default_qty_type": "fixed", "default_qty_value": QTY}), ref)
    return ok and len(ref) > 12, f"{d} (got {len(ref)})"


BASE = dict(lb=5, ml=60, ob=70, os=30, htf=True)


def check():
    df = bars(40000, seed=431, freq="1h")
    for kk in ("open", "high", "low", "close"):
        df[kk] = 100 * (df[kk] / 100) ** 0.5
    msgs, allok = [], True
    cases = (({"Overbought Level Threshold": 60, "Oversold Level Threshold": 40}, dict(ob=60, os=40)),
             ({"Enable Higher Time Frame Filter": False, "Overbought Level Threshold": 60, "Oversold Level Threshold": 40}, dict(htf=False, ob=60, os=40)),
             ({"Pivot Lookback Period (Left/Right Bars)": 3, "Max Lookback for Divergence": 40, "Overbought Level Threshold": 60, "Oversold Level Threshold": 40, "Enable Higher Time Frame Filter": False},
              dict(lb=3, ml=40, ob=60, os=40, htf=False)))
    for params, ov in cases:
        ok, m = one(df, params, {**BASE, **ov})
        allok &= ok
        msgs.append(m)
    return allok, " | ".join(msgs)
