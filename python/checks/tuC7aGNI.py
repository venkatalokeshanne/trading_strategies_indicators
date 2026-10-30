"""Independent check — Strategy 432 BTC Donchian Breakout Continuation (tuC7aGNI): hourly bars of a crypto-style symbol, process_orders_on_close (orders fill at the signal close), fixed quantity 10 on the pinelib side (the original sizes 95 % of equity), commission / slippage / margin off.
Donchian high / low = highest high / lowest low of the previous L bars; entry while flat: close beyond the channel by at least min-ATR, ADX >= minimum, close on the right side of the EMA(200) (shorts optional). Exit: the close back through the opposite channel edge, or the number of bars since the signal bar (set when the entry is called) reaching the maximum.
Uses the quantity-aware bracket reference (indep.simulate_brackets, on_close), comparing quantities too. Variants: defaults with ADX min 10 and break 0.1; shorts on, length 15, hold 10."""
import numpy as np

from indep import bars, compare_q, np_atr, np_dmi, np_ema, run_conversion, simulate_brackets
from pinelib import SymbolInfo

TV_ID = "tuC7aGNI"
QTY = 10.0


def one(df, params, p):
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    L = p["len"]
    hs, ls = np.r_[np.nan, h[:-1]], np.r_[np.nan, l[:-1]]
    dh = np.array([hs[i - L + 1:i + 1].max() if i >= L and not np.isnan(hs[i - L + 1:i + 1]).any() else np.nan for i in range(n)])
    dl = np.array([ls[i - L + 1:i + 1].min() if i >= L and not np.isnan(ls[i - L + 1:i + 1]).any() else np.nan for i in range(n)])
    atr, ema = np_atr(h, l, c, 14), np_ema(c, 200)
    _, _, adx = np_dmi(h, l, c, 14)
    S = dict(eb=None)

    def orders(i, info):
        out = []
        pos = info["pos"]
        with np.errstate(invalid="ignore", divide="ignore"):
            lm = (c[i] - dh[i]) / atr[i] if (c[i] > dh[i] and atr[i] > 0) else 0.0
            sm = (dl[i] - c[i]) / atr[i] if (c[i] < dl[i] and atr[i] > 0) else 0.0
            ready = not (np.isnan(dh[i]) or np.isnan(dl[i]) or np.isnan(atr[i]) or np.isnan(adx[i]) or np.isnan(ema[i]))
            held = None if S["eb"] is None else i - S["eb"]
            le = ready and pos == 0 and c[i] > dh[i] and adx[i] >= p["adx"] and c[i] > ema[i] and lm >= p["mb"]
            se = ready and p["sh"] and pos == 0 and c[i] < dl[i] and adx[i] >= p["adx"] and c[i] < ema[i] and sm >= p["mb"]
            lx = pos > 0 and (c[i] < dl[i] or (held is not None and held >= p["hold"]))
            sx = pos < 0 and (c[i] > dh[i] or (held is not None and held >= p["hold"]))
        if le:
            out.append(("entry", "Long", 1, QTY))
            S["eb"] = i
        if se:
            out.append(("entry", "Short", -1, QTY))
            S["eb"] = i
        if lx:
            out.append(("close", "Long"))
            S["eb"] = None
        if sx:
            out.append(("close", "Short"))
            S["eb"] = None
        return out

    ref = simulate_brackets(o, h, l, c, orders, on_close=True)
    sym = SymbolInfo.make("BINANCE:BTCUSDT", "crypto", qty_step=1e-9)
    ok, d = compare_q(run_conversion(TV_ID, df, symbol=sym, tf="60", params=params,
                                     strategy_overrides={"margin_long": 0, "margin_short": 0, "commission_value": 0, "slippage": 0, "default_qty_type": "fixed", "default_qty_value": QTY}), ref)
    return ok and len(ref) > 12, f"{d} (got {len(ref)})"


BASE = dict(len=30, adx=22.0, mb=0.5, hold=20, sh=False)


def check():
    df = bars(30000, seed=441, freq="1h")
    for k in ("open", "high", "low", "close"):
        df[k] = 100 * (df[k] / 100) ** 0.5
    msgs, allok = [], True
    cases = (({"ADX mínimo": 10.0, "Min Breakout ATR": 0.1}, dict(adx=10.0, mb=0.1)),
             ({"ADX mínimo": 10.0, "Min Breakout ATR": 0.1, "Permitir shorts": True, "Donchian Length": 15, "Máximo de barras en posición": 10}, dict(adx=10.0, mb=0.1, sh=True, len=15, hold=10)))
    for params, ov in cases:
        ok, m = one(df, params, {**BASE, **ov})
        allok &= ok
        msgs.append(m)
    return allok, " | ".join(msgs)
