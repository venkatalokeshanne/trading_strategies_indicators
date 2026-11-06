"""Independent check — EXPMA三线回踩 (uMHceUfi): daily bars of a stock-style symbol, market orders at the next open, fixed quantity 100 on the pinelib side (the original sizes 100000 cash), commission / slippage / margin off.
The three pull-back signals (EMA10 > EMA20, up day, bias / upper-shadow / volume bands) of the PREVIOUS bar open a long while the script's position-type tracker is 0 (recording the signal bar's open as the entry price). The tracker, hold days, fixed stops, +5 % / +10 % stop raises, two take-profit stages (absolute-quantity partial close, then a full close - a later close order of the same bar replaces
an earlier one), the 20-EMA exit and the 3-day time exit are restated statement by statement, including the final reset of the tracker whenever the position is flat at script time (which clears it on the signal bar itself, before the entry has filled).
Uses the quantity-aware bracket reference (indep.simulate_brackets with absolute-quantity closes), comparing quantities too. Variants: defaults with loosened volume / shadow limits; tighter stops and nearer targets."""
import numpy as np

from indep import bars, compare_q, np_ema, np_sma, run_conversion, simulate_brackets
from pinelib import SymbolInfo

TV_ID = "uMHceUfi"
QTY = 100.0


def one(df, params, p):
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    v = df["volume"].to_numpy()
    n = len(c)
    e10, e20, vma = np_ema(c, 10), np_ema(c, 20), np_sma(v, 20)
    with np.errstate(invalid="ignore", divide="ignore"):
        bias = (e10 - e20) / e20 * 100
        shadow = (h - c) / c * 100
        gain = np.r_[np.nan, np.diff(c)] / np.r_[np.nan, c[:-1]] * 100
        cv = (v >= vma * p["vmin"]) & (v <= vma * 3.5)
        cb = (bias >= 0.0) & (bias <= 2.5)
        cs = shadow < p["shadow"]
        cu = gain > 0
        ct = e10 > e20
        com = cu & cb & cs & cv
        s1 = ct & (o > e10) & (l <= e20) & (c > e10) & com
        s2 = ct & (o > e20) & (o < e10) & (l <= e20) & (c > e10) & com
        s3 = ct & (o > e10) & (l <= e10) & (c > e10) & com
    hh3 = np.array([h[i - 2:i + 1].max() if i >= 2 else np.nan for i in range(n)])
    S = dict(ep=np.nan, pt=0, hd=0)

    def orders(i, info):
        out = []
        pos = info["pos"]
        for k, sg in enumerate((s1, s2, s3)):
            if i > 0 and sg[i - 1] and S["pt"] == 0:
                out.append(("entry", "Long", 1, QTY))
                S.update(ep=o[i], pt=k + 1, hd=0)
        if pos > 0:
            S["hd"] += 1
        with np.errstate(invalid="ignore", divide="ignore"):
            stop = p["sl"][S["pt"] - 1] / 100 if S["pt"] in (1, 2, 3) else None
            sp = S["ep"] * (1 - stop) if stop is not None else np.nan
            if pos > 0 and c[i] / S["ep"] >= 1.05:
                sp = max(sp, S["ep"]) if not np.isnan(sp) else np.nan
            if pos > 0 and c[i] / S["ep"] >= 1.10:
                sp = max(sp, S["ep"] + (c[i] - S["ep"]) / 2) if not np.isnan(sp) else np.nan
            exit_stop = c[i] <= sp or c[i] <= e20[i]
            time_exit = S["hd"] >= 3 and hh3[i] / S["ep"] < 1.05
            if S["pt"] in (1, 2, 3) and pos > 0:
                t = S["pt"] - 1
                if c[i] / S["ep"] >= 1 + p["tp1"][t] / 100:
                    out.append(("close_qty", "Long", pos * (0.4 if S["pt"] == 1 else 0.5)))
                if c[i] / S["ep"] >= 1 + p["tp2"][t] / 100:
                    out.append(("close", "Long"))
            if pos > 0 and (exit_stop or time_exit):
                out.append(("close", "Long"))
        if pos == 0:
            S.update(ep=np.nan, pt=0, hd=0)
        return out

    ref = simulate_brackets(o, h, l, c, orders, qty_step=1e-9)
    sym = SymbolInfo.make("NASDAQ:XYZ", "stock", qty_step=1e-9)
    ok, d = compare_q(run_conversion(TV_ID, df, symbol=sym, tf="D", params=params,
                                     strategy_overrides={"margin_long": 0, "margin_short": 0, "commission_value": 0, "slippage": 0, "default_qty_type": "fixed", "default_qty_value": QTY}), ref)
    return ok and len(ref) > 6, f"{d} (got {len(ref)})"


BASE = dict(vmin=1.0, shadow=0.8, sl=(3.5, 3.0, 2.2), tp1=(7.0, 6.0, 5.0), tp2=(13.0, 11.0, 9.0))


def check():
    df = bars(8000, seed=331, freq="D")
    msgs, allok = [], True
    cases = (({"成交量下限倍数(改1.0更容易出信号)": 0.0, "上影/收盘价上限%": 5.0}, dict(vmin=0.0, shadow=5.0)),
             ({"成交量下限倍数(改1.0更容易出信号)": 0.0, "上影/收盘价上限%": 5.0, "多1固定止损%": 1.5, "多2固定止损%": 1.5, "多3固定止损%": 1.5, "多1一档止盈%": 2.0, "多1二档止盈%": 4.0, "多2一档止盈%": 2.0, "多2二档止盈%": 4.0, "多3一档止盈%": 2.0, "多3二档止盈%": 4.0},
              dict(vmin=0.0, shadow=5.0, sl=(1.5,) * 3, tp1=(2.0,) * 3, tp2=(4.0,) * 3)))
    for params, ov in cases:
        ok, m = one(df, params, {**BASE, **ov})
        allok &= ok
        msgs.append(m)
    return allok, " | ".join(msgs)
