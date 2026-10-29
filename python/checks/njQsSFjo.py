"""Independent check — Clean Trend System, HTF Bias Filtered (njQsSFjo): 15-minute bars (24 h synthetic) of a crypto-style symbol (UTC days, 4-hour periods from 00:00), market orders at the next open, default quantity 1, commission / slippage / margin off.
Higher timeframe (15 -> 240): EMA50 / EMA9 / EMA21 and the close of the 4-hour periods, mapped with lookahead ON (every chart bar of a period sees the period's finished values). Bullish stack: close > EMA50, EMA9 > EMA21 > EMA50 on the chart; trigger = (low reaching EMA21 or the session VWAP with a close back above it AND a candle closing up above the previous high) OR a close crossing over the previous bar's 20-bar highest high,
with RSI(5) between 45 and 75 and rising; one entry per trend (state re-armed when the close crosses the 50 EMA the other way); blocked against the higher-timeframe stack; entries reverse. Uses the quantity-aware bracket reference (indep.simulate_brackets), comparing quantities too.
Variants: defaults; EMAs 5 / 13 / 30 with breakout 10; EMAs 12 / 26 / 80, RSI length 9."""
import numpy as np

from indep import bars, compare_q, np_cross_over, np_cross_under, np_ema, np_periods, np_rsi, np_vwap, run_conversion, simulate_brackets
from pinelib import SymbolInfo

TV_ID = "njQsSFjo"


def one(df, params, p):
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    pid, last_of = np_periods(df, 240, start_minutes=0, tz="UTC")
    pc = c[last_of]                                    # one close per period, in period order
    hc = pc[pid]                                       # lookahead on: the period's finished value on every chart bar
    ht, hf, hs = (np_ema(pc, p[k])[pid] for k in ("t", "f", "s"))
    with np.errstate(invalid="ignore"):
        hbull = (hc > ht) & (hf > hs) & (hs > ht)
        hbear = (hc < ht) & (hf < hs) & (hs < ht)
    ef, es, et = np_ema(c, p["f"]), np_ema(c, p["s"]), np_ema(c, p["t"])
    vw = np_vwap(df, (h + l + c) / 3, start_minutes=0, tz="UTC")
    rsi = np_rsi(c, p["rl"])
    rsi1 = np.r_[np.nan, rsi[:-1]]
    B = p["bo"]
    hh = np.array([h[i - B + 1:i + 1].max() if i >= B - 1 else np.nan for i in range(n)])
    ll = np.array([l[i - B + 1:i + 1].min() if i >= B - 1 else np.nan for i in range(n)])
    hh1, ll1 = np.r_[np.nan, hh[:-1]], np.r_[np.nan, ll[:-1]]
    bl, bs = np_cross_over(c, hh1), np_cross_under(c, ll1)
    S = dict(state="NONE")

    def orders(i, info):
        out = []
        pos = info["pos"]
        with np.errstate(invalid="ignore"):
            bt = c[i] > et[i] and ef[i] > es[i] and es[i] > et[i]
            st_ = c[i] < et[i] and ef[i] < es[i] and es[i] < et[i]
            pbl = (l[i] <= es[i] and c[i] > es[i]) or (l[i] <= vw[i] and c[i] > vw[i])
            pbs = (h[i] >= es[i] and c[i] < es[i]) or (h[i] >= vw[i] and c[i] < vw[i])
            bc = c[i] > o[i] and i > 0 and c[i] > h[i - 1]
            sc = c[i] < o[i] and i > 0 and c[i] < l[i - 1]
            rl = rsi[i] > 45 and rsi[i] > rsi1[i] and rsi[i] < 75
            rs = rsi[i] < 55 and rsi[i] < rsi1[i] and rsi[i] > 25
            lt = bt and ((pbl and bc) or bool(bl[i])) and rl
            stg = st_ and ((pbs and sc) or bool(bs[i])) and rs
            if S["state"] == "LONG_FIRED" and c[i] < et[i]:
                S["state"] = "NONE"
            if S["state"] == "SHORT_FIRED" and c[i] > et[i]:
                S["state"] = "NONE"
            lsig = lt and S["state"] != "LONG_FIRED" and pos <= 0 and not hbear[i]
            ssig = stg and S["state"] != "SHORT_FIRED" and pos >= 0 and not hbull[i]
        if lsig:
            out.append(("entry", "Long", 1, 1.0))
            S["state"] = "LONG_FIRED"
        if ssig:
            out.append(("entry", "Short", -1, 1.0))
            S["state"] = "SHORT_FIRED"
        return out

    ref = simulate_brackets(o, h, l, c, orders)
    sym = SymbolInfo.make("BINANCE:XYZUSDT", "crypto", qty_step=1e-9)
    ok, d = compare_q(run_conversion(TV_ID, df, symbol=sym, tf="15", params=params,
                                     strategy_overrides={"margin_long": 0, "margin_short": 0, "commission_value": 0, "slippage": 0}), ref)
    return ok and len(ref) > 12, f"{d} (got {len(ref)})"


BASE = dict(f=9, s=21, t=50, rl=5, bo=20)


def check():
    df = bars(30000, seed=341, freq="15min")
    for k in ("open", "high", "low", "close"):
        df[k] = 100 * (df[k] / 100) ** 0.5
    msgs, allok = [], True
    cases = (({}, {}),
             ({"Fast EMA": 5, "Slow EMA": 13, "Trend EMA": 30, "Breakout Lookback Period": 10}, dict(f=5, s=13, t=30, bo=10)),
             ({"Fast EMA": 12, "Slow EMA": 26, "Trend EMA": 80, "RSI Length": 9}, dict(f=12, s=26, t=80, rl=9)))
    for params, ov in cases:
        ok, m = one(df, params, {**BASE, **ov})
        allok &= ok
        msgs.append(m)
    return allok, " | ".join(msgs)
