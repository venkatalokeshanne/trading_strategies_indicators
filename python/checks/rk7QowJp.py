"""Independent check — Scalping Strategy Improved v2 (rk7QowJp): 5-min bars. EMA50>EMA200 trend, RSI(3) crossing
back over 20 / under 80, ADX(5)>20 (own Wilder DMI below, from the textbook formulas), strong body candle;
bracket 1.2 ATR stop / 2R target from the signal close, working from the fill bar (trail_points alone never trails)."""
import numpy as np

from indep import bars, compare, np_atr, np_cross_over, np_cross_under, np_ema, np_rma, np_rsi, np_tr, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "rk7QowJp"


def np_adx(h, l, c, n):
    up = np.r_[np.nan, np.diff(h)]
    down = -np.r_[np.nan, np.diff(l)]
    pdm = np.where(np.isnan(up), np.nan, np.where((up > down) & (up > 0), up, 0.0))
    mdm = np.where(np.isnan(down), np.nan, np.where((down > up) & (down > 0), down, 0.0))
    trur = np_rma(np_tr(h, l, c, False), n)

    def ffill(x):                                              # fixnan
        out = x.copy()
        for i in range(1, len(out)):
            if np.isnan(out[i]):
                out[i] = out[i - 1]
        return out

    with np.errstate(divide="ignore", invalid="ignore"):
        plus = ffill(100 * np_rma(pdm, n) / trur)
        minus = ffill(100 * np_rma(mdm, n) / trur)
        tot = plus + minus
        return np_rma(np.abs(plus - minus) / np.where(tot == 0, 1.0, tot), n) * 100


def check():
    df = bars(30000, seed=79, freq="5min")
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    e50, e200, rsi, atr = np_ema(c, 50), np_ema(c, 200), np_rsi(c, 3), np_atr(h, l, c, 14)
    adx = np_adx(h, l, c, 5)
    body, rng = np.abs(c - o), h - l
    with np.errstate(invalid="ignore"):
        lgo = (c > e50) & (e50 > e200) & np_cross_over(rsi, 20) & (adx > 20) & (c > o) & (body > rng * 0.5)
        sgo = (c < e50) & (e50 < e200) & np_cross_under(rsi, 80) & (adx > 20) & (c < o) & (body > rng * 0.5)
    n = len(c)
    levels = {1: [], -1: []}
    cur = {1: (np.nan, np.nan), -1: (np.nan, np.nan)}
    for j in range(n):
        if lgo[j]:
            s = c[j] - atr[j] * 1.2
            cur[1] = (s, c[j] + (c[j] - s) * 2)
        if sgo[j]:
            s = c[j] + atr[j] * 1.2
            cur[-1] = (s, c[j] - (s - c[j]) * 2)
        levels[1].append(cur[1]); levels[-1].append(cur[-1])

    def level(k):
        return lambda i, pos, ep, eb: levels[pos][i - 1][k] if i > 0 else None

    ref = simulate(o, h, l, c, lambda i, pos: ([("entry", 1)] if lgo[i] else []) + ([("entry", -1)] if sgo[i] else []),
                   stop=level(0), target=level(1))
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="5"), ref)
    return ok and len(ref) > 10, f"{detail} (need >10 trades, got {len(ref)})"
