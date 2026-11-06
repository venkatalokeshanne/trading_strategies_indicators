"""Independent check — BTC Future 4H (C9c7lz9r): 4-hour bars, market orders at the next open, fixed quantity 10 on the pinelib side (the original sizes 10 % of equity), commission / slippage / margin off.
Entry while flat: EMA fast > mid > slow (mirror for shorts), RSI inside its band (45-75 long, 25-55 short), a Supertrend flip into the trend direction (direction -1 = up-trend) and volume above its 20-bar SMA. Stop = the wider of close -/+ ATR x multiple and the swing low / high over the lookback pushed out by the wick buffer %;
two exit orders (50 % each) target the 1st and 2nd risk multiple from the signal close, both with that stop. Uses the quantity-aware bracket reference (indep.simulate_brackets), which also compares the closed quantities.
Variants: loose RSI-independent settings (shorter EMAs 8/13/21, volume filter off); stricter ATR stop and nearer targets."""
import numpy as np

from indep import bars, compare_q, np_atr, np_ema, np_rsi, np_sma, np_supertrend, run_conversion, simulate_brackets
from pinelib import SymbolInfo

TV_ID = "C9c7lz9r"
QTY = 10.0


def one(df, params, p):
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    v = df["volume"].to_numpy()
    n = len(c)
    e1, e2, e3 = np_ema(c, p["e1"]), np_ema(c, p["e2"]), np_ema(c, p["e3"])
    rsi, atr = np_rsi(c, 14), np_atr(h, l, c, 14)
    _, sd = np_supertrend(h, l, c, 3.0, 10)
    vma = np_sma(v, 20)
    sw = p["sw"]
    slow = np.array([l[i - sw + 1:i + 1].min() if i >= sw - 1 else np.nan for i in range(n)])
    shigh = np.array([h[i - sw + 1:i + 1].max() if i >= sw - 1 else np.nan for i in range(n)])
    bull = sd < 0
    flip_up = bull & ~np.r_[False, bull[:-1]]
    flip_dn = ~bull & np.r_[False, bull[:-1]]
    with np.errstate(invalid="ignore"):
        volok = (~np.bool_(p["vol"])) | (v > vma)
        ls = (e1 > e2) & (e2 > e3) & (rsi >= 45) & (rsi <= 75) & flip_up & volok
        ss = (e1 < e2) & (e2 < e3) & (rsi >= 25) & (rsi <= 55) & flip_dn & volok

    def orders(i, info):
        out = []
        if info["pos"] != 0:
            return out
        with np.errstate(invalid="ignore"):
            if ls[i]:
                sl = min(c[i] - atr[i] * p["am"], slow[i] * (1 - 0.3 / 100))
                r = c[i] - sl
                out += [("entry", "Long", 1, QTY), ("exit", "Long TP1", "Long", 50, sl, c[i] + r * p["r1"]), ("exit", "Long TP2", "Long", 50, sl, c[i] + r * p["r2"])]
            if ss[i]:
                sl = max(c[i] + atr[i] * p["am"], shigh[i] * (1 + 0.3 / 100))
                r = sl - c[i]
                out += [("entry", "Short", -1, QTY), ("exit", "Short TP1", "Short", 50, sl, c[i] - r * p["r1"]), ("exit", "Short TP2", "Short", 50, sl, c[i] - r * p["r2"])]
        return out

    ref = simulate_brackets(o, h, l, c, orders)
    sym = SymbolInfo.make("BINANCE:BTCUSDT", "crypto", qty_step=1e-9)
    ok, d = compare_q(run_conversion(TV_ID, df, symbol=sym, tf="240", params=params,
                                     strategy_overrides={"margin_long": 0, "margin_short": 0, "commission_value": 0, "slippage": 0, "default_qty_type": "fixed", "default_qty_value": QTY}), ref)
    return ok and len(ref) > 12, f"{d} (got {len(ref)})"


BASE = dict(e1=21, e2=55, e3=200, sw=5, vol=True, am=2.0, r1=1.5, r2=2.5)


def check():
    df = bars(30000, seed=151, freq="4h")
    for k in ("open", "high", "low", "close"):
        df[k] = 100 * (df[k] / 100) ** 0.5
    msgs, allok = [], True
    cases = (({"EMA Fast": 8, "EMA Mid": 13, "EMA Slow": 21, "Volume Filter": False}, dict(e1=8, e2=13, e3=21, vol=False)),
             ({"EMA Fast": 8, "EMA Mid": 13, "EMA Slow": 21, "ATR SL Multiplier": 1.5, "TP1 RR": 1.0, "TP2 RR": 1.8, "Swing Lookback (bars)": 8},
              dict(e1=8, e2=13, e3=21, am=1.5, r1=1.0, r2=1.8, sw=8)))
    for params, ov in cases:
        ok, m = one(df, params, {**BASE, **ov})
        allok &= ok
        msgs.append(m)
    return allok, " | ".join(msgs)
