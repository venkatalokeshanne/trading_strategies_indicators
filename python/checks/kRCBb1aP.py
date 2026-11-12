"""Independent check — Ellis US30 Combo (kRCBb1aP): 15-minute bars (24h synthetic), process_orders_on_close, one position (opposite signals reverse), qty 1. stockBuy: SMA21 > SMA50, stochastic-RSI %K crosses over %D with min(K, D) <= 25 (K = SMA3 of the 12-bar stochastic of RSI14, 50 when flat); stockSell mirrored (>= 75). macdBuy: SMA21 > SMA50 > SMA200,
MACD crosses over its signal below zero, RSI14 > 50 and a bullish divergence: the latest pivot-low pair where price and RSI(14) both form a pivot low (5 bars each side) on the same bar, price lower and RSI higher than the previous such pair, no older than 50 bars (mirrored for sells). All cross tests are evaluated every bar (Pine v5).
Entry only inside 09:30-16:00 NY and while the closed P&L since the day's first bar (09:30 NY trading-day convention) is within +/- the daily limits; stop 3.0 / target 6.0 (300 / 600 ticks of 0.01) around the signal close, placed with the entry (work from the next bar); a signal that is both a buy and a sell does nothing. Variants: default; tight daily limits ($10 / $8). Commission / slippage / margin off on the pinelib side."""
import numpy as np
import pandas as pd

from indep import bars, compare, np_cross_over, np_cross_under, np_ema, np_rsi, np_sma, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "kRCBb1aP"
K = 5


def psma(x, n):
    """SMA from a running prefix sum, the way Pine's ta.sma accumulates (matters when %K and %D tie)."""
    x = np.asarray(x, float)
    nanc = np.r_[0, np.cumsum(np.isnan(x))]
    P = np.r_[0.0, np.cumsum(np.where(np.isnan(x), 0.0, x))]
    out = np.full(len(x), np.nan)
    for i in range(n - 1, len(x)):
        if nanc[i + 1] - nanc[i - n + 1] == 0:
            out[i] = (P[i] - P[i - (n - 1)] + x[i]) / n
    return out


def piv(x, lo):
    n = len(x)
    out = np.full(n, np.nan)
    for i in range(2 * K, n):
        j = i - K
        w = np.r_[x[j - K:j], x[j + 1:i + 1]]
        if np.isnan(x[j]) or np.isnan(w).any():
            continue
        if (x[j] < w.min()) if lo else (x[j] > w.max()):
            out[i] = x[j]
    return out


def one(df, params, target, loss):
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    s21, s50, s200 = np_sma(c, 21), np_sma(c, 50), np_sma(c, 200)
    r14 = np_rsi(c, 14)
    lo12 = pd.Series(r14).rolling(12, min_periods=12).min().to_numpy()
    hi12 = pd.Series(r14).rolling(12, min_periods=12).max().to_numpy()
    with np.errstate(invalid="ignore", divide="ignore"):
        raw = np.where(hi12 - lo12 == 0, 50.0, (r14 - lo12) / (hi12 - lo12) * 100.0)
    raw = np.where(np.isnan(hi12) | np.isnan(r14), np.nan, raw)
    kk = psma(raw, 3)
    dd = psma(kk, 3)
    macd = np_ema(c, 12) - np_ema(c, 26)
    sig = np_ema(macd, 9)
    pl_p, ph_p, pl_r, ph_r = piv(l, True), piv(h, False), piv(r14, True), piv(r14, False)
    ny = pd.to_datetime(df["time"], unit="ms", utc=True).dt.tz_convert("America/New_York")
    m = (ny.dt.hour * 60 + ny.dt.minute).to_numpy()
    day = (ny.dt.tz_localize(None) - pd.Timedelta(minutes=9 * 60 + 30)).dt.date.to_numpy()
    sess = (m >= 570) & (m < 960)
    with np.errstate(invalid="ignore"):
        kd_up, kd_dn = np_cross_over(kk, dd), np_cross_under(kk, dd)
        mu, md = np_cross_over(macd, sig), np_cross_under(macd, sig)
        sbuy = (s21 > s50) & kd_up & (np.fmin(kk, dd) <= 25.0)
        ssell = (s21 < s50) & kd_dn & (np.fmax(kk, dd) >= 75.0)
    Sd = dict(pb=np.nan, lb=np.nan, prb=np.nan, lrb=np.nan, lbb=None, pbe=np.nan, lbe=np.nan, prbe=np.nan, lrbe=np.nan, lbeb=None, start=0.0)
    log: list = []
    lev = {}

    def orders(i, pos):
        out = []
        if not np.isnan(pl_p[i]) and not np.isnan(pl_r[i]):
            Sd.update(pb=Sd["lb"], prb=Sd["lrb"], lb=pl_p[i], lrb=pl_r[i], lbb=i - K)
        if not np.isnan(ph_p[i]) and not np.isnan(ph_r[i]):
            Sd.update(pbe=Sd["lbe"], prbe=Sd["lrbe"], lbe=ph_p[i], lrbe=ph_r[i], lbeb=i - K)
        isn = np.isnan
        bull_div = (not isn(Sd["pb"])) and (not isn(Sd["lb"])) and (not isn(Sd["prb"])) and (not isn(Sd["lrb"])) and Sd["lb"] < Sd["pb"] and Sd["lrb"] > Sd["prb"] and Sd["lbb"] is not None and i - Sd["lbb"] <= 50
        bear_div = (not isn(Sd["pbe"])) and (not isn(Sd["lbe"])) and (not isn(Sd["prbe"])) and (not isn(Sd["lrbe"])) and Sd["lbe"] > Sd["pbe"] and Sd["lrbe"] < Sd["prbe"] and Sd["lbeb"] is not None and i - Sd["lbeb"] <= 50
        mbuy = (s21[i] > s50[i] and s21[i] > s200[i] and s50[i] > s200[i] and mu[i] and macd[i] < 0 and sig[i] < 0 and r14[i] > 50.0 and bull_div)
        msell = (s21[i] < s50[i] and s21[i] < s200[i] and s50[i] < s200[i] and md[i] and macd[i] > 0 and sig[i] > 0 and r14[i] < 50.0 and bear_div)
        buy, sell = bool(sbuy[i] or mbuy), bool(ssell[i] or msell)
        net = sum((t[4] - t[2]) * t[0] for t in log)
        if i > 0 and day[i] != day[i - 1]:
            Sd["start"] = net
        pnl = net - Sd["start"]
        blocked = (pnl >= target) or (pnl <= -loss)
        allow = sess[i] and not blocked
        if allow and buy and pos <= 0 and not sell:
            out.append(("entry", 1))
            lev[i] = (c[i] - 3.0, c[i] + 6.0)
        if allow and sell and pos >= 0 and not buy:
            out.append(("entry", -1))
            lev[i] = (c[i] + 3.0, c[i] - 6.0)
        return out

    stop = lambda i, pos, ep, eb: lev[eb][0] if (eb in lev and eb < i) else None
    tgt = lambda i, pos, ep, eb: lev[eb][1] if (eb in lev and eb < i) else None
    with np.errstate(invalid="ignore"):
        ref = simulate(o, h, l, c, orders, stop=stop, target=tgt, on_close=True, log=log)
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, d = compare(run_conversion(TV_ID, df, symbol=sym, tf="15", params=params, strategy_overrides={"margin_long": 0, "margin_short": 0, "slippage": 0, "commission_value": 0}), ref)
    return ok and len(ref) > 10, f"{d} (got {len(ref)})"


def check():
    df = bars(40000, seed=761, freq="15min")
    msgs, allok = [], True
    for params, tg, ls in (({}, 100.0, 100.0), ({"Daily Profit Target ($)": 10.0, "Daily Loss Limit ($)": 8.0}, 10.0, 8.0)):
        ok, m = one(df, params, tg, ls)
        allok &= ok
        msgs.append(m)
    return allok, " | ".join(msgs)
