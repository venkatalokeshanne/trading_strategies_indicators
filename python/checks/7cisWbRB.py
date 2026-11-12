"""Independent check — DRO Momentum Surge (7cisWbRB): hourly bars of a stock-style symbol, market orders at the next open, fixed quantity 10 on the pinelib side (the original sizes 5 % of equity), commission / slippage / margin off.
Entry while flat: volume >= multiple x its SMA, an up bar closing in the top part of its range, RSI < max, close over the trend EMA, no blow-off bar (volume ratio >= blow-off multiple with an upper wick share >= the wick ratio). The tracker (entry price, hard stop = close - ATR x mult, highest close since entry, trailing activation at the minimum gain %, stop = trailing level once active) is restated in order;
one stop order at max(hard stop, trail stop) is re-issued every bar of a position; a blow-off bar while long closes at the next open and clears the tracker. Uses the quantity-aware bracket reference (indep.simulate_brackets), comparing quantities too. Variants: surge 1.5 with a small gain threshold (5 %) and trail 2; surge 1.3, RSI max 90, blow-off 2.5."""
import numpy as np

from indep import bars, compare_q, np_atr, np_ema, np_rsi, np_sma, run_conversion, simulate_brackets
from pinelib import SymbolInfo

TV_ID = "7cisWbRB"
QTY = 10.0


def one(df, params, p):
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    v = df["volume"].to_numpy()
    vm, ema, rsi, atr = np_sma(v, 10), np_ema(c, 20), np_rsi(c, 14), np_atr(h, l, c, 10)
    S = dict(ep=np.nan, hs=np.nan, th=np.nan, ts=np.nan, ta=False)

    def orders(i, info):
        out = []
        pos = info["pos"]
        with np.errstate(invalid="ignore", divide="ignore"):
            vr = v[i] / vm[i]
            rng = h[i] - l[i]
            cp = (c[i] - l[i]) / rng if rng > 0 else 0.5
            bull = c[i] > o[i] and cp >= 0.6
            uw = h[i] - max(o[i], c[i])
            blow = vr >= p["blow"] and rng > 0 and (uw / rng) >= 0.35
            sig = vr >= p["surge"] and bull and rsi[i] < p["rsi"] and c[i] > ema[i] and not blow and pos == 0
            if sig:
                S.update(ep=c[i], hs=c[i] - 2.5 * atr[i], th=c[i], ta=False)
                S["ts"] = S["hs"]
                out.append(("entry", "Long", 1, QTY))
            if pos > 0:
                S["th"] = max(S["th"], c[i]) if not np.isnan(S["th"]) else np.nan
                gain = (S["th"] - S["ep"]) / S["ep"] * 100
                if gain >= p["gain"]:
                    S["ta"] = True
                S["ts"] = S["th"] - p["tr"] * atr[i] if S["ta"] else S["hs"]
                lv = np.nan if (np.isnan(S["hs"]) or np.isnan(S["ts"])) else max(S["hs"], S["ts"])
                out.append(("exit", "Exit", "Long", None, None if np.isnan(lv) else lv, None))
            if pos > 0 and blow:
                out.append(("close", "Long"))
                S.update(ep=np.nan, hs=np.nan, th=np.nan, ts=np.nan, ta=False)
        return out

    ref = simulate_brackets(o, h, l, c, orders)
    sym = SymbolInfo.make("NASDAQ:XYZ", "stock", qty_step=1e-9)
    ok, d = compare_q(run_conversion(TV_ID, df, symbol=sym, tf="60", params=params,
                                     strategy_overrides={"margin_long": 0, "margin_short": 0, "commission_value": 0, "slippage": 0, "default_qty_type": "fixed", "default_qty_value": QTY}), ref)
    return ok and len(ref) > 12, f"{d} (got {len(ref)})"


BASE = dict(surge=2.0, blow=3.5, rsi=80, gain=15.0, tr=3.0)


def check():
    df = bars(30000, seed=541, freq="1h")
    for k in ("open", "high", "low", "close"):
        df[k] = 100 * (df[k] / 100) ** 0.5
    msgs, allok = [], True
    cases = (({"Volume Surge Multiplier": 1.5, "Min Gain % for Trail": 5.0, "ATR Trail Stop Mult": 2.0}, dict(surge=1.5, gain=5.0, tr=2.0)),
             ({"Volume Surge Multiplier": 1.3, "Max RSI at Entry": 90, "Blow-off Vol Multiplier": 2.5}, dict(surge=1.3, rsi=90, blow=2.5)))
    for params, ov in cases:
        ok, m = one(df, params, {**BASE, **ov})
        allok &= ok
        msgs.append(m)
    return allok, " | ".join(msgs)
