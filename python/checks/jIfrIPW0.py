"""Independent check — Institutional OB (jIfrIPW0): daily bars, orders at the signal close (process_orders_on_close). BOS: close above the highest high (below the lowest low) of the previous 20 bars. The block is the high / low of the last bearish (bullish) candle at the time of the break (latest including the break bar itself); the latest bull and bear BOS decide which side is "active"
(strictly more recent). Entry signal: active side, the bar overlaps the block, close beyond the block midpoint, EMA50 > EMA200 with close > EMA50 (mirror), RSI14 vs 50, Stoch K (SMA3 of the raw 14-bar stoch of the close) vs D (SMA3 of K, prefix-sum SMAs so exact ties match) with K < 80 (> 20); only the first bar of a run of signals fires.
Stop = block low - 0.25 ATR14 (short: block high + 0.25 ATR14), target 2R, fixed at the signal bar; opposite side closed first."""
import numpy as np
import pandas as pd

from indep import bars, compare, np_atr, np_ema, np_rsi, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "jIfrIPW0"


def psma(x, n):
    x = np.asarray(x, float)
    nanc = np.r_[0, np.cumsum(np.isnan(x))]
    P = np.r_[0.0, np.cumsum(np.where(np.isnan(x), 0.0, x))]
    out = np.full(len(x), np.nan)
    for i in range(n - 1, len(x)):
        if nanc[i + 1] - nanc[i - n + 1] == 0:
            out[i] = (P[i] - P[i - (n - 1)] + x[i]) / n
    return out


def check():
    df = bars(9000, seed=222)
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    ef, es, rsi, atr = np_ema(c, 50), np_ema(c, 200), np_rsi(c, 14), np_atr(h, l, c, 14)
    hh = pd.Series(h).rolling(14).max().to_numpy()
    ll = pd.Series(l).rolling(14).min().to_numpy()
    with np.errstate(invalid="ignore", divide="ignore"):
        raw = 100 * (c - ll) / (hh - ll)
    raw[~np.isfinite(raw)] = np.nan
    K = psma(raw, 3)
    D = psma(K, 3)
    ph = np.r_[np.nan, pd.Series(h).rolling(20).max().to_numpy()[:-1]]
    pl = np.r_[np.nan, pd.Series(l).rolling(20).min().to_numpy()[:-1]]
    with np.errstate(invalid="ignore"):
        bb, sb = c > ph, c < pl
    # valuewhen(cond, src, 0): src's value on the latest bar where cond held (including the current bar)
    def vw(cond, src):
        out = np.full(len(src), np.nan)
        cur = np.nan
        for i in range(len(src)):
            if cond[i]:
                cur = src[i]
            out[i] = cur
        return out
    bear_c, bull_c = c < o, c > o
    lbh, lbl = vw(bear_c, h), vw(bear_c, l)
    lah, lal = vw(bull_c, h), vw(bull_c, l)
    boh, bol = vw(bb, lbh), vw(bb, lbl)
    seh, sel = vw(sb, lah), vw(sb, lal)
    def since(cond):
        out = np.full(n, np.nan)
        last = None
        for i in range(n):
            if cond[i]:
                last = i
            out[i] = np.nan if last is None else i - last
        return out
    sbu, sbe = since(bb), since(sb)
    with np.errstate(invalid="ignore"):
        bact = ~np.isnan(sbu) & (np.isnan(sbe) | (sbu < sbe))
        sact = ~np.isnan(sbe) & (np.isnan(sbu) | (sbe < sbu))
        inb = bact & ~np.isnan(boh) & (l <= boh) & (h >= bol)
        ins = sact & ~np.isnan(seh) & (h >= sel) & (l <= seh)
        bm, sm = (boh + bol) / 2, (seh + sel) / 2
        eb = (ef > es) & (c > ef)
        ebr = (ef < es) & (c < ef)
        bsg = inb & (c > bm) & eb & (rsi > 50) & (K > D) & (K < 80)
        ssg = ins & (c < sm) & ebr & (rsi < 50) & (K < D) & (K > 20)
    bsg1, ssg1 = np.r_[False, bsg[:-1]], np.r_[False, ssg[:-1]]
    bstop = bol - atr * 0.25
    brisk = c - bstop
    sstop = seh + atr * 0.25
    srisk = sstop - c
    with np.errstate(invalid="ignore"):
        vb = bsg & ~bsg1 & (brisk > 0.01)
        vs = ssg & ~ssg1 & (srisk > 0.01)
    lvl = {}

    def orders(i, pos):
        out = []
        if vb[i]:
            out += [("close", -1), ("entry", 1)]
            lvl[1] = (bstop[i], c[i] + brisk[i] * 2.0)
        if vs[i]:
            out += [("close", 1), ("entry", -1)]
            lvl[-1] = (sstop[i], c[i] - srisk[i] * 2.0)
        return out

    def stop(i, pos, ep, eb_):
        return lvl[1 if pos > 0 else -1][0]

    def target(i, pos, ep, eb_):
        return lvl[1 if pos > 0 else -1][1]

    with np.errstate(invalid="ignore"):
        ref = simulate(o, h, l, c, orders, stop=stop, target=target, on_close=True)
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="D", strategy_overrides={"margin_long": 0, "margin_short": 0}), ref)
    return ok and len(ref) > 10, f"{detail} (need >10 trades, got {len(ref)})"
