"""
Each pinelib.ta function against an INDEPENDENT pandas/numpy implementation of Pine's
documented formula, written separately here (LESSONS L10: never validate code against
itself). Synthetic bars include a flat run (ties, zero ranges).
"""

from __future__ import annotations

import math

import numpy as np
import pandas as pd
import pytest

from pinelib import Script, run, ta
from pinelib.symbols import SymbolInfo

TOL = 1e-9


def _run_series(bars, fn):
    """Run fn(script) every bar; return the list of values it produced."""
    out = []

    class T(Script):
        def on_bar(self):
            out.append(fn(self))

    run(T, bars, symbol=SymbolInfo.make("TEST:X", "crypto"), timeframe="D")
    return out


def _cmp(ours, ref, start=0, tol=TOL):
    a = np.asarray([np.nan if x is None else float(x) for x in ours], dtype=float)
    b = np.asarray(ref, dtype=float)
    assert len(a) == len(b)
    a, b = a[start:], b[start:]
    both_nan = np.isnan(a) & np.isnan(b)
    assert np.array_equal(np.isnan(a), np.isnan(b)), \
        f"na mismatch at {np.flatnonzero(np.isnan(a) != np.isnan(b))[:5] + start}"
    d = np.abs(a - b)[~both_nan]
    scale = np.maximum(1.0, np.abs(b[~both_nan]))
    worst = float(np.max(d / scale)) if len(d) else 0.0
    assert worst <= tol, f"max rel diff {worst}"


# ── independent references ──────────────────────────────────────────────────
def ref_sma(x, n): return x.rolling(n).mean()


def ref_ema_sma_seed(x, n):
    a = 2 / (n + 1)
    out = np.full(len(x), np.nan)
    v = x.to_numpy()
    prev = np.nan
    for i in range(len(v)):
        if np.isnan(prev):
            if i >= n - 1 and not np.isnan(v[i - n + 1:i + 1]).any():
                prev = v[i - n + 1:i + 1].mean()
                out[i] = prev
        else:
            prev = a * v[i] + (1 - a) * prev
            out[i] = prev
    return out


def ref_rma(x, n):
    out = np.full(len(x), np.nan)
    v = x.to_numpy()
    prev = np.nan
    for i in range(len(v)):
        if np.isnan(prev):
            if i >= n - 1 and not np.isnan(v[i - n + 1:i + 1]).any():
                prev = v[i - n + 1:i + 1].mean()
                out[i] = prev
        else:
            prev = (v[i] + (n - 1) * prev) / n
            out[i] = prev
    return out


def ref_wma(x, n):
    w = np.arange(1, n + 1)
    return x.rolling(n).apply(lambda a: (a * w).sum() / w.sum(), raw=True)


def ref_tr(df, handle_na):
    pc = df.close.shift(1)
    tr = pd.concat([df.high - df.low, (df.high - pc).abs(), (df.low - pc).abs()], axis=1).max(axis=1, skipna=False)
    tr.iloc[0] = df.high.iloc[0] - df.low.iloc[0] if handle_na else np.nan
    return tr


# ── tests ───────────────────────────────────────────────────────────────────
@pytest.mark.parametrize("n", [1, 2, 14, 50])
def test_sma(bars, n):
    _cmp(_run_series(bars, lambda s: ta.sma(s.close, n)), ref_sma(bars.close, n))


@pytest.mark.parametrize("n", [1, 9, 21, 200])
def test_ema_sma_seeded(bars, n):
    _cmp(_run_series(bars, lambda s: ta.ema(s.close, n)), ref_ema_sma_seed(bars.close, n))


@pytest.mark.parametrize("n", [2, 14, 30])
def test_rma(bars, n):
    _cmp(_run_series(bars, lambda s: ta.rma(s.close, n)), ref_rma(bars.close, n))


@pytest.mark.parametrize("n", [1, 5, 20])
def test_wma(bars, n):
    _cmp(_run_series(bars, lambda s: ta.wma(s.close, n)), ref_wma(bars.close, n))


def test_hma(bars):
    n = 16
    ref = ref_wma(2 * ref_wma(bars.close, 8) - ref_wma(bars.close, 16), 4)
    _cmp(_run_series(bars, lambda s: ta.hma(s.close, n)), ref)


def test_vwma(bars):
    ref = (bars.close * bars.volume).rolling(20).mean() / bars.volume.rolling(20).mean()
    _cmp(_run_series(bars, lambda s: ta.vwma(s.close, 20)), ref)


def test_alma(bars):
    n, off, sig = 9, 0.85, 6
    m = off * (n - 1)
    sd = n / sig
    w = np.exp(-((np.arange(n) - m) ** 2) / (2 * sd * sd))
    ref = bars.close.rolling(n).apply(lambda a: (a * w).sum() / w.sum(), raw=True)
    _cmp(_run_series(bars, lambda s: ta.alma(s.close, n, off, sig)), ref)


def test_linreg(bars):
    n = 20
    t = np.arange(n)

    def f(a):
        sl, ic = np.polyfit(t, a, 1)
        return ic + sl * (n - 1)
    _cmp(_run_series(bars, lambda s: ta.linreg(s.close, n, 0)), bars.close.rolling(n).apply(f, raw=True), tol=1e-8)


def test_highest_lowest_and_bars(bars):
    _cmp(_run_series(bars, lambda s: ta.highest(s.high, 10)), bars.high.rolling(10).max())
    _cmp(_run_series(bars, lambda s: ta.lowest(s.low, 10)), bars.low.rolling(10).min())
    _cmp(_run_series(bars, lambda s: ta.highest(10)), bars.high.rolling(10).max())
    # offset to the highest bar (most recent wins ties): -(n-1-argmax_last)
    ref = bars.high.rolling(10).apply(lambda a: -(len(a) - 1 - (len(a) - 1 - np.argmax(a[::-1]))), raw=True)
    _cmp(_run_series(bars, lambda s: ta.highestbars(s.high, 10)), ref)


def test_change_mom_roc(bars):
    _cmp(_run_series(bars, lambda s: ta.change(s.close)), bars.close.diff())
    _cmp(_run_series(bars, lambda s: ta.mom(s.close, 10)), bars.close - bars.close.shift(10))
    _cmp(_run_series(bars, lambda s: ta.roc(s.close, 10)), 100 * (bars.close - bars.close.shift(10)) / bars.close.shift(10))


def test_rsi(bars):
    ch = bars.close.diff()
    u = ch.clip(lower=0)
    d = (-ch).clip(lower=0)
    ru, rd = ref_rma(u, 14), ref_rma(d, 14)
    ref = 100 - 100 / (1 + ru / rd)
    _cmp(_run_series(bars, lambda s: ta.rsi(s.close, 14)), ref, tol=1e-8)


def test_stoch_cci_wpr(bars):
    hh, ll = bars.high.rolling(14).max(), bars.low.rolling(14).min()
    _cmp(_run_series(bars, lambda s: ta.stoch(s.close, s.high, s.low, 14)),
         (100 * (bars.close - ll) / (hh - ll)).replace([np.inf, -np.inf], np.nan))
    _cmp(_run_series(bars, lambda s: ta.wpr(14)), (100 * (bars.close - hh) / (hh - ll)).replace([np.inf, -np.inf], np.nan))
    md = bars.close.rolling(20).apply(lambda a: np.mean(np.abs(a - a.mean())), raw=True)
    _cmp(_run_series(bars, lambda s: ta.cci(s.close, 20)),
         ((bars.close - bars.close.rolling(20).mean()) / (0.015 * md)).replace([np.inf, -np.inf], np.nan))


def test_cmo_tsi(bars):
    m = bars.close.diff()
    s1 = m.clip(lower=0).rolling(9).sum()
    s2 = (-m).clip(lower=0).rolling(9).sum()
    _cmp(_run_series(bars, lambda s: ta.cmo(s.close, 9)), 100 * (s1 - s2) / (s1 + s2))
    pc = bars.close.diff()
    e1 = pd.Series(ref_ema_sma_seed(pd.Series(ref_ema_sma_seed(pc, 25)), 13))
    e2 = pd.Series(ref_ema_sma_seed(pd.Series(ref_ema_sma_seed(pc.abs(), 25)), 13))
    _cmp(_run_series(bars, lambda s: ta.tsi(s.close, 13, 25)), e1 / e2, tol=1e-8)


def test_mfi(bars):
    x = (bars.high + bars.low + bars.close) / 3
    ch = x.diff()
    up = bars.volume * np.where(ch.isna() | (ch > 0), x, 0.0)      # na change → condition false → x
    dn = bars.volume * np.where(ch.isna() | (ch < 0), x, 0.0)
    upper, lower = pd.Series(up).rolling(14).sum(), pd.Series(dn).rolling(14).sum()
    _cmp(_run_series(bars, lambda s: ta.mfi(s.hlc3, 14)), 100 - 100 / (1 + upper / lower))


def test_macd_bb(bars):
    vals = _run_series(bars, lambda s: ta.macd(s.close, 12, 26, 9))
    m = pd.Series(ref_ema_sma_seed(bars.close, 12)) - pd.Series(ref_ema_sma_seed(bars.close, 26))
    sig = ref_ema_sma_seed(m, 9)
    _cmp([v[0] for v in vals], m)
    _cmp([v[1] for v in vals], sig, tol=1e-8)
    bbv = _run_series(bars, lambda s: ta.bb(s.close, 20, 2))
    basis = bars.close.rolling(20).mean()
    sd = bars.close.rolling(20).std(ddof=0)
    _cmp([v[1] for v in bbv], basis + 2 * sd, tol=1e-8)


def test_stdev_variance_dev_correlation_median(bars):
    _cmp(_run_series(bars, lambda s: ta.stdev(s.close, 20)), bars.close.rolling(20).std(ddof=0), tol=1e-8)
    _cmp(_run_series(bars, lambda s: ta.stdev(s.close, 20, False)), bars.close.rolling(20).std(ddof=1), tol=1e-8)
    _cmp(_run_series(bars, lambda s: ta.variance(s.close, 20)), bars.close.rolling(20).var(ddof=0), tol=1e-8)
    _cmp(_run_series(bars, lambda s: ta.correlation(s.close, s.open, 20)), bars.close.rolling(20).corr(bars.open), tol=1e-8)
    _cmp(_run_series(bars, lambda s: ta.median(s.close, 11)), bars.close.rolling(11).median())


def test_atr_tr(bars):
    _cmp(_run_series(bars, lambda s: ta.tr()), ref_tr(bars, False))
    _cmp(_run_series(bars, lambda s: ta.tr(True)), ref_tr(bars, True))
    _cmp(_run_series(bars, lambda s: ta.atr(14)), ref_rma(ref_tr(bars, True), 14))


def test_crossover_barssince_valuewhen(bars):
    f, s = pd.Series(ref_ema_sma_seed(bars.close, 5)), pd.Series(ref_ema_sma_seed(bars.close, 20))
    ref_x = ((f > s) & (f.shift(1) <= s.shift(1))).astype(float)
    ours = _run_series(bars, lambda sc: ta.crossover(ta.ema(sc.close, 5), ta.ema(sc.close, 20)))
    _cmp([float(v) for v in ours], ref_x)
    cond = bars.close > bars.open
    since, last, ref_bs, ref_vw = np.nan, np.nan, [], []
    for i, c in enumerate(cond):
        since = 0 if c else (since + 1 if since == since else np.nan)
        if c:
            last = bars.close.iloc[i]
        ref_bs.append(since)
        ref_vw.append(last)
    _cmp(_run_series(bars, lambda sc: ta.barssince(sc.close > sc.open)), ref_bs)
    _cmp(_run_series(bars, lambda sc: ta.valuewhen(sc.close > sc.open, sc.close, 0)), ref_vw)


def test_pivots(bars):
    l, r = 3, 2
    h = bars.high.to_numpy()
    ref = np.full(len(h), np.nan)
    for i in range(l + r, len(h)):
        p = i - r
        if all(h[p] > h[k] for k in range(p - l, p)) and all(h[p] >= h[k] for k in range(p + 1, i + 1)):
            ref[i] = h[p]
    _cmp(_run_series(bars, lambda s: ta.pivothigh(s.high, l, r)), ref)
    _cmp(_run_series(bars, lambda s: ta.pivothigh(l, r)), ref)


def test_supertrend_matches_reference_loop(bars):
    """Independent re-statement of Pine's documented pine_supertrend."""
    tr = ref_tr(bars, True)
    atr = ref_rma(tr, 10)
    hl2 = ((bars.high + bars.low) / 2).to_numpy()
    c = bars.close.to_numpy()
    L = U = ST = np.nan
    prev_atr = np.nan
    ref_st, ref_dir = [], []
    for i in range(len(c)):
        up, lo = hl2[i] + 3 * atr[i], hl2[i] - 3 * atr[i]
        pl, pu = (0 if np.isnan(L) else L), (0 if np.isnan(U) else U)
        pcl = c[i - 1] if i else np.nan
        lo = lo if (lo > pl or pcl < pl) else pl
        up = up if (up < pu or pcl > pu) else pu
        if np.isnan(prev_atr):
            d = 1
        elif ST == pu:
            d = -1 if c[i] > up else 1
        else:
            d = 1 if c[i] < lo else -1
        st = lo if d == -1 else up
        ref_st.append(st)
        ref_dir.append(d)
        L, U, ST, prev_atr = lo, up, st, atr[i]
    vals = _run_series(bars, lambda s: ta.supertrend(3, 10))
    _cmp([v[0] for v in vals], ref_st)
    _cmp([v[1] for v in vals], ref_dir)


def test_vwap_resets_each_day():
    from conftest import make_bars
    b = make_bars(n=600, freq="1h")
    hlc3 = (b.high + b.low + b.close) / 3
    day = pd.to_datetime(b.time, unit="ms", utc=True).dt.date
    ref = (hlc3 * b.volume).groupby(day).cumsum() / b.volume.groupby(day).cumsum()
    out = []

    class T(Script):
        def on_bar(self):
            out.append(ta.vwap())

    run(T, b, symbol=SymbolInfo.make("TEST:X", "crypto"), timeframe="60")
    _cmp(out, ref)
