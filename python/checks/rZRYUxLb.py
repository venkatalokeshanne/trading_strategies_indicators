"""Independent check — BTC Smart Pullback Liquidity + Adaptive RSI (rZRYUxLb): hourly bars of a crypto-style symbol (daily periods from 00:00 UTC), market orders at the next open, fixed quantity 10 on the pinelib side (the original sizes 2 % of equity), commission / slippage / margin off.
Daily trend: daily close > daily EMA200, EMA50 > EMA200, daily RSI14 > 45 (period values, lookahead off). Sweep = low under the lowest low of the previous L bars with the close back over it; barssince(sweep) in [0, reclaim bars] and the close over the previous-low level; RSI z-score = (RSI - SMA50)/stdev50 (population, 0 when the deviation is 0); capitulation on the previous bar (z < -1) and z crossing over -0.35; higher close; close under EMA50 + 1.5 ATR; ADX and volume filters.
Entry long while flat (pyramiding 0); two 50 % exits (TP1 / TP2 ATR multiples, common stop) re-issued every bar from the average entry price (none while flat); a close under the 200 EMA closes the position. Uses the quantity-aware bracket reference (indep.simulate_brackets), comparing quantities too.
Variants: filters off (daily trend, ADX, volume) with a 3-bar reclaim; same with TP 1.5 / 3 and stop 1.2."""
import numpy as np

from indep import bars, compare_q, np_atr, np_cross_over, np_dmi, np_ema, np_periods, np_rsi, np_security_lookahead_off, np_sma, run_conversion, simulate_brackets
from pinelib import SymbolInfo

TV_ID = "rZRYUxLb"
QTY = 10.0


def one(df, params, p):
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    v = df["volume"].to_numpy()
    n = len(c)
    rsi = np_rsi(c, 14)
    e50, e200 = np_ema(c, 50), np_ema(c, 200)
    atr = np_atr(h, l, c, 14)
    vs = np_sma(v, 50)
    _, _, adx = np_dmi(h, l, c, 14)
    pid, last_of = np_periods(df, 1440, start_minutes=0, tz="UTC")
    pc = c[last_of]
    mp = lambda x: np_security_lookahead_off(x, pid, last_of)
    dc, d50, d200, drsi = mp(pc), mp(np_ema(pc, 50)), mp(np_ema(pc, 200)), mp(np_rsi(pc, 14))
    with np.errstate(invalid="ignore", divide="ignore"):
        dt = (dc > d200) & (d50 > d200) & (drsi > 45)
        trend = (c > e200) & (e50 > e200) & ((not p["dt"]) | dt)
        mean = np_sma(rsi, 50)
        dev = np.array([np.std(rsi[i - 49:i + 1]) if i >= 49 and not np.isnan(rsi[i - 49:i + 1]).any() else np.nan for i in range(n)])
        z = np.where(dev != 0, (rsi - mean) / dev, 0.0)
        z = np.where(np.isnan(dev), np.nan, z)
    cap = np.r_[False, (z[:-1] < -1.0)]
    reb = np_cross_over(z, np.full(n, -0.35))
    L = 20
    ls_ = np.r_[np.nan, l[:-1]]
    pl = np.array([np.nanmin(ls_[i - L + 1:i + 1]) if i >= L - 1 and not np.all(np.isnan(ls_[i - L + 1:i + 1])) else np.nan for i in range(n)])
    with np.errstate(invalid="ignore"):
        sweep = (l < pl) & (c > pl)
    bs = np.full(n, np.nan)
    last = None
    for i in range(n):
        if sweep[i]:
            last = i
        bs[i] = np.nan if last is None else i - last
    with np.errstate(invalid="ignore"):
        recl = (bs >= 0) & (bs <= p["rb"]) & (c > pl)
        hc = c > np.r_[np.nan, c[:-1]]
        ne = c < e50 + atr * 1.5
        voln = (not p["vol"]) | (v > vs * 1.05)
        adxn = (not p["adx"]) | (adx > 17)
        buy = trend & adxn & voln & recl & cap & reb & hc & ne

    def orders(i, info):
        out = []
        pos, avg = info["pos"], info["avg"]
        if buy[i]:
            out.append(("entry", "Long", 1, QTY))
        if pos > 0 and not np.isnan(avg):
            stop = avg - atr[i] * p["sl"]
            out += [("exit", "TP1", "Long", 50, stop, avg + atr[i] * p["t1"]), ("exit", "TP2", "Long", 50, stop, avg + atr[i] * p["t2"])]
        if pos > 0 and c[i] < e200[i]:
            out.append(("close", "Long"))
        return out

    ref = simulate_brackets(o, h, l, c, orders)
    sym = SymbolInfo.make("BINANCE:BTCUSDT", "crypto", qty_step=1e-9)
    ok, d = compare_q(run_conversion(TV_ID, df, symbol=sym, tf="60", params=params,
                                     strategy_overrides={"margin_long": 0, "margin_short": 0, "commission_value": 0, "slippage": 0, "default_qty_type": "fixed", "default_qty_value": QTY}), ref)
    return ok and len(ref) > 12, f"{d} (got {len(ref)})"


BASE = dict(dt=True, adx=True, vol=True, rb=5, sl=1.8, t1=2.2, t2=4.5)


def check():
    df = bars(40000, seed=421, freq="1h")
    for k in ("open", "high", "low", "close"):
        df[k] = 100 * (df[k] / 100) ** 0.5
    off = {"Filtre tendance Daily": False, "Filtre ADX": False, "Filtre volume": False}
    ov0 = dict(dt=False, adx=False, vol=False)
    msgs, allok = [], True
    cases = (({"Filtre ADX": False, "Filtre volume": False, "Réintégration max après sweep": 8}, dict(dt=True, adx=False, vol=False, rb=8)),
             ({**off, "Réintégration max après sweep": 3}, dict(ov0, rb=3)),
             ({**off, "Réintégration max après sweep": 3, "TP1 ATR": 1.5, "TP2 ATR": 3.0, "Stop ATR": 1.2}, dict(ov0, rb=3, t1=1.5, t2=3.0, sl=1.2)))
    for params, ov in cases:
        ok, m = one(df, params, {**BASE, **ov})
        allok &= ok
        msgs.append(m)
    return allok, " | ".join(msgs)
