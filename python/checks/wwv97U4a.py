"""Independent check — 10-Factor Super Indicator Strategy (wwv97U4a): hourly bars of a stock-style symbol (VWAP restarting at 09:30 New York), market orders at the next open, default quantity 1, pyramiding 0, commission / slippage / margin off.
Ten factors (EMA20/50 trend, Supertrend direction, MACD line/signal/histogram, RSI 55/45, ADX with DI, close vs session VWAP, Bollinger position, stochastic RSI [highest/lowest of the RSI over the window, K = SMA3, D = SMA3] between 20 and 80, OBV vs its EMA21, ATR % regime) add their weight with the sign of the side; the raw sum / total weight x 100 is the score.
Entry: score beyond the threshold with EMA, Supertrend, ADX and the ATR regime agreeing, flat or opposite; every bar re-issues one ATR stop / target exit order per side from the average entry price; a score under (over) the exit threshold closes the position. Uses the quantity-aware bracket reference (indep.simulate_brackets), comparing quantities too.
Variants: thresholds 25 / -25; 15 / -15 with exit 0 and tighter ATR brackets (1.2 / 2)."""
import numpy as np

from indep import bars, compare_q, np_atr, np_dmi, np_ema, np_rsi, np_sma, np_supertrend, np_vwap, run_conversion, simulate_brackets
from pinelib import SymbolInfo

TV_ID = "wwv97U4a"


def nan_window(x, n, fn):
    out = np.full(len(x), np.nan)
    for i in range(n - 1, len(x)):
        w = x[i - n + 1:i + 1]
        w = w[~np.isnan(w)]
        if len(w) and not np.isnan(x[i]):
            out[i] = fn(w)
    return out


def sma_prefix(x, n):
    out = np.full(len(x), np.nan)
    psum, pnan = [0.0], [0]
    for i, v in enumerate(x):
        if i + 1 >= n and not np.isnan(v) and pnan[i] - pnan[i - (n - 1)] == 0:
            out[i] = (psum[i] - psum[i - (n - 1)] + v) / n
        psum.append(psum[-1] + (0.0 if np.isnan(v) else v))
        pnan.append(pnan[-1] + (1 if np.isnan(v) else 0))
    return out


def one(df, params, p):
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    v = df["volume"].to_numpy()
    n = len(c)
    ef, es = np_ema(c, 20), np_ema(c, 50)
    macd = np_ema(c, 12) - np_ema(c, 26)
    sig = np_ema(macd, 9)
    hist = macd - sig
    rsi = np_rsi(c, 14)
    pdi, mdi, adx = np_dmi(h, l, c, 14)
    vw = np_vwap(df, (h + l + c) / 3)
    bb = np_sma(c, 20)
    dev = np.array([np.std(c[i - 19:i + 1]) if i >= 19 else np.nan for i in range(n)]) * 2.0
    bu, bl = bb + dev, bb - dev
    lo, hi = nan_window(rsi, 14, np.min), nan_window(rsi, 14, np.max)
    with np.errstate(invalid="ignore", divide="ignore"):
        raw = np.where(hi != lo, 100 * (rsi - lo) / (hi - lo), 0.0)
    raw = np.where(np.isnan(hi) | np.isnan(lo) | np.isnan(rsi), np.nan, raw)
    sk = sma_prefix(raw, 3)
    sd = sma_prefix(sk, 3)
    _, sdir = np_supertrend(h, l, c, 3.0, 10)
    obv = np.cumsum(np.r_[0.0, np.sign(np.diff(c)) * v[1:]])
    oe = np_ema(obv, 21)
    atr = np_atr(h, l, c, 14)
    W = (15, 15, 12, 8, 10, 10, 8, 8, 7, 7)
    tw = sum(W)

    def f(b, r, w):
        return w if b else (-w if r else 0)

    def orders(i, info):
        out = []
        pos, avg = info["pos"], info["avg"]
        with np.errstate(invalid="ignore"):
            atrp = atr[i] / c[i] * 100.0
            act = atrp > 0.4
            eb, ebr = ef[i] > es[i] and c[i] > ef[i], ef[i] < es[i] and c[i] < ef[i]
            sb, sbr = sdir[i] < 0, sdir[i] > 0
            mb, mbr = macd[i] > sig[i] and hist[i] > 0, macd[i] < sig[i] and hist[i] < 0
            rb, rbr = rsi[i] > 55, rsi[i] < 45
            ab, abr = adx[i] > 20 and pdi[i] > mdi[i], adx[i] > 20 and mdi[i] > pdi[i]
            vb, vbr = c[i] > vw[i], c[i] < vw[i]
            bbb, bbr = c[i] > bb[i] and c[i] < bu[i], c[i] < bb[i] and c[i] > bl[i]
            stb = sk[i] > sd[i] and 20 < sk[i] < 80
            stbr = sk[i] < sd[i] and 20 < sk[i] < 80
            ob, obr = obv[i] > oe[i], obv[i] < oe[i]
            raws = (f(eb, ebr, W[0]) + f(sb, sbr, W[1]) + f(mb, mbr, W[2]) + f(rb, rbr, W[3]) + f(ab, abr, W[4]) + f(vb, vbr, W[5])
                    + f(bbb, bbr, W[6]) + f(stb, stbr, W[7]) + f(ob, obr, W[8]) + (W[9] if act else 0))
            score = raws / tw * 100.0
            ls = score >= p["lt"] and eb and sb and adx[i] > 20 and act
            ss = score <= -p["lt"] and ebr and sbr and adx[i] > 20 and act
        if ls and pos <= 0:
            out.append(("entry", "Long", 1, 1.0))
        if ss and pos >= 0:
            out.append(("entry", "Short", -1, 1.0))
        a = atr[i]
        out += [("exit", "Long Exit", "Long", None, None if np.isnan(avg) else avg - a * p["sl"], None if np.isnan(avg) else avg + a * p["tp"]),
                ("exit", "Short Exit", "Short", None, None if np.isnan(avg) else avg + a * p["sl"], None if np.isnan(avg) else avg - a * p["tp"])]
        if pos > 0 and score < p["ex"]:
            out.append(("close", "Long"))
        if pos < 0 and score > -p["ex"]:
            out.append(("close", "Short"))
        return out

    ref = simulate_brackets(o, h, l, c, orders)
    sym = SymbolInfo.make("NASDAQ:XYZ", "stock", qty_step=1e-9)
    ok, d = compare_q(run_conversion(TV_ID, df, symbol=sym, tf="60", params=params,
                                     strategy_overrides={"margin_long": 0, "margin_short": 0, "commission_value": 0, "slippage": 0}), ref)
    return ok and len(ref) > 12, f"{d} (got {len(ref)})"


BASE = dict(lt=45.0, ex=10.0, sl=2.0, tp=3.5)


def check():
    df = bars(30000, seed=571, freq="1h")
    for k in ("open", "high", "low", "close"):
        df[k] = 100 * (df[k] / 100) ** 0.5
    msgs, allok = [], True
    cases = (({"Long Score Threshold": 25.0, "Short Score Threshold": -25.0}, dict(lt=25.0)),
             ({"Long Score Threshold": 15.0, "Short Score Threshold": -15.0, "Exit Score Threshold": 0.0, "Stop ATR Mult": 1.2, "Take Profit ATR Mult": 2.0}, dict(lt=15.0, ex=0.0, sl=1.2, tp=2.0)))
    for params, ov in cases:
        ok, m = one(df, params, {**BASE, **ov})
        allok &= ok
        msgs.append(m)
    return allok, " | ".join(msgs)
