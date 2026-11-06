"""Independent check — BABEL AUTO TRADER V1 (jhBo6ToF): hourly bars of a stock-style symbol, process_orders_on_close (entries fill at the signal close), default quantity 1, commission / slippage / margin off.
Ten-point score per side (close vs EMA200, EMA21 vs EMA55, EMA55 vs EMA200, momentum = RSI / DI / ADX, volume >= average x mult, candle colour, close beyond the last 3/3 pivot extreme [left strictly, right not], sweep of the other extreme, RSI beyond 55 / 45, ADX >= min); entry while flat when the stacked-EMA trend holds and the score reaches the minimum.
The script has no exits, so after the first signal the position stays open for the rest of the run and nothing else can fire: the check compares the single entry (bar, price, quantity) through the open-trade comparison of indep.simulate_brackets(open_log=...).
Variants: minimum score 6 / 5 / 4 give different first signals and, with longs or shorts disabled, different sides."""
import numpy as np

from indep import bars, compare_open, np_atr, np_dmi, np_ema, np_rsi, np_sma, run_conversion, simulate_brackets
from pinelib import SymbolInfo

TV_ID = "jhBo6ToF"


def pivots(x, k, high):
    n = len(x)
    out = np.full(n, np.nan)
    for i in range(2 * k, n):
        m = i - k
        c = x[m]
        lw, rw = x[m - k:m], x[m + 1:i + 1]
        ok = (np.all(c > lw) and np.all(c >= rw)) if high else (np.all(c < lw) and np.all(c <= rw))
        if ok:
            out[i] = c
    return out


def one(df, params, p):
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    v = df["volume"].to_numpy()
    n = len(c)
    e200, e21, e55 = np_ema(c, 200), np_ema(c, 21), np_ema(c, 55)
    rsi = np_rsi(c, 14)
    pdi, mdi, adx = np_dmi(h, l, c, 14)
    av = np_sma(v, 20)
    ph, pl = pivots(h, 3, True), pivots(l, 3, False)
    S = dict(lh=np.nan, ll=np.nan)

    def orders(i, info):
        if not np.isnan(ph[i]):
            S["lh"] = ph[i]
        if not np.isnan(pl[i]):
            S["ll"] = pl[i]
        with np.errstate(invalid="ignore"):
            bb = (not np.isnan(S["lh"])) and c[i] > S["lh"]
            sb = (not np.isnan(S["ll"])) and c[i] < S["ll"]
            bsw = (not np.isnan(S["ll"])) and l[i] < S["ll"] and c[i] > S["ll"]
            ssw = (not np.isnan(S["lh"])) and h[i] > S["lh"] and c[i] < S["lh"]
            bt = c[i] > e200[i] and e21[i] > e55[i] and e55[i] > e200[i]
            st_ = c[i] < e200[i] and e21[i] < e55[i] and e55[i] < e200[i]
            bm = rsi[i] > 50 and pdi[i] > mdi[i] and adx[i] >= 20.0
            sm = rsi[i] < 50 and mdi[i] > pdi[i] and adx[i] >= 20.0
            vc = v[i] >= av[i] * 1.0
            ls = sum([c[i] > e200[i], e21[i] > e55[i], e55[i] > e200[i], bm, vc, c[i] > o[i], bb, bsw, rsi[i] > 55, adx[i] >= 20.0])
            ss = sum([c[i] < e200[i], e21[i] < e55[i], e55[i] < e200[i], sm, vc, c[i] < o[i], sb, ssw, rsi[i] < 45, adx[i] >= 20.0])
            lsig = p["ul"] and bt and ls >= p["score"] and info["pos"] == 0
            ssig = p["us"] and st_ and ss >= p["score"] and info["pos"] == 0
        out = []
        if lsig:
            out.append(("entry", "BABEL LONG", 1, 1.0))
        if ssig:
            out.append(("entry", "BABEL SHORT", -1, 1.0))
        return out

    open_ref = []
    simulate_brackets(o, h, l, c, orders, on_close=True, open_log=open_ref)
    sym = SymbolInfo.make("NASDAQ:XYZ", "stock", qty_step=1e-9)
    ok, d = compare_open(run_conversion(TV_ID, df, symbol=sym, tf="60", params=params,
                                        strategy_overrides={"margin_long": 0, "margin_short": 0, "commission_value": 0, "slippage": 0}), open_ref)
    return ok and len(open_ref) == 1, f"{d} ({open_ref})"


BASE = dict(score=8, ul=True, us=True)


def check():
    df = bars(20000, seed=471, freq="1h")
    for k in ("open", "high", "low", "close"):
        df[k] = 100 * (df[k] / 100) ** 0.5
    msgs, allok = [], True
    cases = (({"Minimum BABEL Score": 6}, dict(score=6)),
             ({"Minimum BABEL Score": 5, "Enable Longs": False}, dict(score=5, ul=False)),
             ({"Minimum BABEL Score": 5, "Enable Shorts": False}, dict(score=5, us=False)))
    for params, ov in cases:
        ok, m = one(df, params, {**BASE, **ov})
        allok &= ok
        msgs.append(m)
    return allok, " | ".join(msgs)
