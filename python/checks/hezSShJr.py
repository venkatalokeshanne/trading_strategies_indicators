"""Independent check — Hybrid Breakout (hezSShJr): daily bars, process_orders_on_close, fixed quantity 100 on the pinelib side (the original sizes 100 % of equity), commission / slippage / margin off, date range left at its defaults.
Trend: close over SMA50 over SMA150 over SMA200, SMA200 above its previous value and above its value N bars back, SMA50 not below its previous value. Squeeze: percent rank (share of the previous L values that are <= the current one) of the 3-bar high-low range % is within the maximum, or the 3-bar close range % is small. Volume above its SMA x multiple.
On a signal while flat a buy-stop at the previous bar's 3-bar highest high is placed (replaced on every new signal bar, kept until filled; it fills at the stop price, or at the open if the bar gaps above it). While long, every bar re-issues three exit orders from the average entry price: 25 % at +TP1, 50 % at +TP2, the rest at +TP3, all with the -SL % stop.
Uses the quantity-aware bracket reference (indep.simulate_brackets), comparing quantities too. Variants: loosened trend and squeeze (short MAs 10 / 20 / 40), tighter targets; volume filter off with a wider squeeze."""
import numpy as np

from indep import bars, compare_q, np_sma, run_conversion, simulate_brackets
from pinelib import SymbolInfo

TV_ID = "hezSShJr"
QTY = 100.0


def rolling(x, n, fn):
    return np.array([fn(x[i - n + 1:i + 1]) if i >= n - 1 else np.nan for i in range(len(x))])


def one(df, params, p):
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    v = df["volume"].to_numpy()
    n = len(c)
    m1, m2, m3 = np_sma(c, p["a"]), np_sma(c, p["b"]), np_sma(c, p["d"])
    hr, lr = rolling(h, 3, np.max), rolling(l, 3, np.min)
    rp = (hr - lr) / hr * 100
    hc, lc = rolling(c, 3, np.max), rolling(c, 3, np.min)
    cp = (hc - lc) / hc * 100
    L = p["lb"]
    rank = np.full(n, np.nan)
    for i in range(L, n):
        if not np.isnan(rp[i]):
            prev = rp[i - L:i]
            rank[i] = 100.0 * np.sum(prev <= rp[i]) / L
    vma = np_sma(v, 20)
    rh = rolling(h, 3, np.max)
    S = dict(prev_rh=np.nan)
    q = p["q"]

    def orders(i, info):
        out = []
        sh = S["prev_rh"]
        S["prev_rh"] = rh[i]
        pos, avg = info["pos"], info["avg"]
        with np.errstate(invalid="ignore"):
            r200 = m3[i - 1] if i >= 1 else np.nan
            r200n = m3[i - q] if i >= q else np.nan
            r50 = m1[i - 1] if i >= 1 else np.nan
            bull = c[i] > m1[i] and m1[i] > m2[i] and m2[i] > m3[i] and m3[i] > r200 and m3[i] > r200n and m1[i] >= r50
            pivot = rank[i] <= p["pmax"] or cp[i] <= 4.0
            vol = (not p["vf"]) or v[i] > vma[i] * 1.2
            sig = bool(bull and pivot and vol)
        if sig and pos == 0 and not np.isnan(sh):
            out.append(("entry", "Long", 1, QTY, sh, None))
        if pos > 0:
            sl = avg * (1 - 0.08)
            out += [("exit", "TP1", "Long", 25, sl, avg * (1 + p["t1"])), ("exit", "TP2", "Long", 50, sl, avg * (1 + p["t2"])), ("exit", "TP3", "Long", 100, sl, avg * (1 + p["t3"]))]
        return out

    ref = simulate_brackets(o, h, l, c, orders, on_close=True)
    sym = SymbolInfo.make("NASDAQ:XYZ", "stock", qty_step=1e-9)
    ok, d = compare_q(run_conversion(TV_ID, df, symbol=sym, tf="D", params=params,
                                     strategy_overrides={"margin_long": 0, "margin_short": 0, "commission_value": 0, "slippage": 0, "default_qty_type": "fixed", "default_qty_value": QTY}), ref)
    return ok and len(ref) > 12, f"{d} (got {len(ref)})"


BASE = dict(a=50, b=150, d=200, lb=150, q=20, pmax=40, vf=True, t1=0.10, t2=0.20, t3=0.30)


def check():
    df = bars(5000, seed=201, freq="D")
    msgs, allok = [], True
    cases = (({"Max Range Percentile (Squeeze)": 70}, dict(pmax=70)),
             ({"Fast MA Length": 10, "Mid MA Length": 20, "Slow MA Length": 40, "Bars Slow MA Must Be Rising Over": 5, "Percentile Lookback": 50, "Take Profit 1 %": 3.0, "Take Profit 2 %": 6.0, "Take Profit 3 %": 9.0},
              dict(a=10, b=20, d=40, q=5, lb=50, t1=0.03, t2=0.06, t3=0.09)),
             ({"Fast MA Length": 10, "Mid MA Length": 20, "Slow MA Length": 40, "Bars Slow MA Must Be Rising Over": 5, "Percentile Lookback": 50, "Require Volume Expansion on Breakout": False, "Max Range Percentile (Squeeze)": 60},
              dict(a=10, b=20, d=40, q=5, lb=50, vf=False, pmax=60)))
    for params, ov in cases:
        ok, m = one(df, params, {**BASE, **ov})
        allok &= ok
        msgs.append(m)
    return allok, " | ".join(msgs)
