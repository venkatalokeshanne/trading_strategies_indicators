"""Independent check — QQE Channel Strategy (c7V3XVUC): hourly bars of a crypto-style symbol, market orders at the next open, lot size 1, commission / slippage / margin off.
Channel = EMA(high), EMA(low) of length L; direction +1 above the upper edge, -1 below the lower edge, else unchanged; exit line = lower edge when direction >= 0 else upper edge. QQE: RSI(14), smoothed by EMA(5); delta-ATR = EMA(|change|, 27) smoothed again with EMA(27) times the factor; bands ratchet against recursion nz(prev)=0; QQE direction flips when the smoothed RSI crosses over the previous
upper band (comparing with the band two bars back for the previous bar) or under the previous lower band. Entry: channel flip to bull with QQE bull, or a QQE flip to bull inside a bull channel (shorts mirrored); SL = swing low / high over N bars, TP = RR x risk, optional; exit signal = previous bar bull channel and close crossing under the exit line, or QQE bearish while long (mirrored).
Uses the quantity-aware bracket reference (indep.simulate_brackets), comparing quantities too. Variants: defaults with channel 30; no fixed SL/TP, channel 20, factor 3; swing 5, RR 2."""
import numpy as np

from indep import bars, compare_q, np_cross_over, np_cross_under, np_ema, np_rsi, run_conversion, simulate_brackets
from pinelib import SymbolInfo

TV_ID = "c7V3XVUC"


def one(df, params, p):
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    chh, chl = np_ema(h, p["ch"]), np_ema(l, p["ch"])
    chd = np.zeros(n)
    d = 0
    for i in range(n):
        if c[i] > chh[i]:
            d = 1
        elif c[i] < chl[i]:
            d = -1
        chd[i] = d
    chx = np.where(chd >= 0, chl, chh)
    chb, chs = chd == 1, chd == -1
    chg = np.r_[False, chd[1:] != chd[:-1]]
    xu, xo = np_cross_under(c, chx), np_cross_over(c, chx)
    exl = np.r_[False, chb[:-1]] & xu
    exs = np.r_[False, chs[:-1]] & xo
    rsi = np_rsi(c, 14)
    rsm = np_ema(rsi, 5)
    delta = np.abs(rsm - np.r_[0.0, np.nan_to_num(rsm[:-1])])
    a1 = np_ema(delta, 27)
    dar = np_ema(a1, 27) * p["qf"]
    qd = np.zeros(n)
    lb = np.full(n, np.nan)
    sb = np.full(n, np.nan)
    q = 0
    nz = lambda x: 0.0 if np.isnan(x) else x
    for i in range(n):
        lv = rsm[i] - dar[i]
        sv = rsm[i] + dar[i]
        lp, sp = nz(lb[i - 1]) if i else 0.0, nz(sb[i - 1]) if i else 0.0
        with np.errstate(invalid="ignore"):
            lv = max(lv, lp) if rsm[i] > lp else lv
            sv = min(sv, sp) if rsm[i] < sp else sv
        lb[i], sb[i] = lv, sv
        if i >= 2:
            with np.errstate(invalid="ignore"):
                if rsm[i] > sb[i - 1] and rsm[i - 1] <= sb[i - 2]:
                    q = 1
                elif rsm[i] < lb[i - 1] and rsm[i - 1] >= lb[i - 2]:
                    q = -1
        qd[i] = q
    qb, qs = qd == 1, qd == -1
    qg = np.r_[False, qd[1:] != qd[:-1]]
    el = (chg & chb & qb) | (qg & qb & chb)
    es = (chg & chs & qs) | (qg & qs & chs)
    sw = p["sw"]
    slo = np.array([l[i - sw + 1:i + 1].min() if i >= sw - 1 else np.nan for i in range(n)])
    shi = np.array([h[i - sw + 1:i + 1].max() if i >= sw - 1 else np.nan for i in range(n)])
    tick = 0.01

    def orders(i, info):
        out = []
        pos = info["pos"]
        xl = exl[i] or (qs[i] and pos > 0)
        xs = exs[i] or (qb[i] and pos < 0)
        if el[i]:
            risk = max(c[i] - slo[i], tick)
            out.append(("entry", "Long", 1, 1.0))
            if p["fx"] and not np.isnan(slo[i]):
                out.append(("exit", "Long SLTP", "Long", None, slo[i], c[i] + risk * p["rr"]))
        if xl:
            out.append(("close", "Long"))
        if es[i]:
            risk = max(shi[i] - c[i], tick)
            out.append(("entry", "Short", -1, 1.0))
            if p["fx"] and not np.isnan(shi[i]):
                out.append(("exit", "Short SLTP", "Short", None, shi[i], c[i] - risk * p["rr"]))
        if xs:
            out.append(("close", "Short"))
        return out

    ref = simulate_brackets(o, h, l, c, orders)
    sym = SymbolInfo.make("BINANCE:XYZUSDT", "crypto", qty_step=1e-9)
    ok, dd = compare_q(run_conversion(TV_ID, df, symbol=sym, tf="60", params=params,
                                      strategy_overrides={"margin_long": 0, "margin_short": 0, "commission_value": 0, "slippage": 0}), ref)
    return ok and len(ref) > 12, f"{dd} (got {len(ref)})"


BASE = dict(ch=60, qf=4.238, fx=True, sw=10, rr=1.0)


def check():
    df = bars(30000, seed=671, freq="1h")
    for k in ("open", "high", "low", "close"):
        df[k] = 100 * (df[k] / 100) ** 0.5
    msgs, allok = [], True
    cases = (({"Channel EMA Length": 30}, dict(ch=30)),
             ({"Use Fixed SL / TP": False, "Channel EMA Length": 20, "QQ Factor": 3.0}, dict(fx=False, ch=20, qf=3.0)),
             ({"SL Swing Length (bars)": 5, "Risk / Reward Ratio": 2.0, "Channel EMA Length": 30}, dict(sw=5, rr=2.0, ch=30)))
    for params, ov in cases:
        ok, m = one(df, params, {**BASE, **ov})
        allok &= ok
        msgs.append(m)
    return allok, " | ".join(msgs)
