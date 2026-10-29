"""Independent check — EURUSD $300 Sniper v8.7 (sbopOeJ5): 15-minute bars (24 h synthetic, price ~100, pip = 10 ticks = 0.1) of a stock-style symbol (daily periods from 09:30 New York), process_orders_on_close (orders fill at the signal close), fixed quantity 100 on the pinelib side (the original sizes 5000 cash), commission / slippage / margin off.
Only bars within the last N days before the final bar are traded. Window = bar open 11:30 - 22:00 Asia/Kolkata, one entry per daily period (counter reset at the period change). Long: low <= lower Bollinger(20, 2), close > EMA200, RSI < 45 (short mirrored with RSI > 55); while flat. Each bar of a position one exit order from the entry price: limit +/- TP pips, stop SL pips away or at the entry once the bar's favourable extreme reached the BE distance.
Positions are closed from 21:45 Kolkata. Uses the quantity-aware bracket reference (indep.simulate_brackets, on_close), comparing quantities too. Variants: lookback 200 days; lookback 400 with TP 20 / SL 10 / BE 6 pips."""
import numpy as np
import pandas as pd

from indep import bars, compare_q, np_ema, np_periods, np_rsi, np_sma, run_conversion, simulate_brackets
from pinelib import SymbolInfo

TV_ID = "sbopOeJ5"
QTY = 100.0


def one(df, params, p):
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    t = df["time"].to_numpy()
    ist = pd.to_datetime(df["time"], unit="ms", utc=True).dt.tz_convert("Asia/Kolkata")
    mins = (ist.dt.hour * 60 + ist.dt.minute).to_numpy()
    sess = (mins >= 690) & (mins < 1320)
    eod = (mins >= 21 * 60 + 45) & (mins < 22 * 60)
    pid, _ = np_periods(df, 1440)
    basis = np_sma(c, 20)
    dev = 2.0 * np.array([np.std(c[i - 19:i + 1]) if i >= 19 else np.nan for i in range(n)])
    up, lo = basis + dev, basis - dev
    ema, rsi = np_ema(c, 200), np_rsi(c, 14)
    pip = 0.1
    start = t[-1] - p["days"] * 24 * 3600 * 1000
    S = dict(td=0)

    def orders(i, info):
        out = []
        pos, avg = info["pos"], info["avg"]
        if i > 0 and pid[i] != pid[i - 1]:
            S["td"] = 0
        with np.errstate(invalid="ignore"):
            lc = t[i] >= start and sess[i] and S["td"] < 1 and l[i] <= lo[i] and c[i] > ema[i] and rsi[i] < 45
            sc = t[i] >= start and sess[i] and S["td"] < 1 and h[i] >= up[i] and c[i] < ema[i] and rsi[i] > 55
        if lc and pos == 0:
            out.append(("entry", "Long", 1, QTY))
            S["td"] = 1
        if sc and pos == 0:
            out.append(("entry", "Short", -1, QTY))
            S["td"] = 1
        tp, sl, be = p["tp"] * pip, p["sl"] * pip, p["be"] * pip
        if pos > 0:
            stop = avg if (h[i] - avg) >= be else avg - sl
            out.append(("exit", "ExL", "Long", None, stop, avg + tp))
        if pos < 0:
            stop = avg if (avg - l[i]) >= be else avg + sl
            out.append(("exit", "ExS", "Short", None, stop, avg - tp))
        if eod[i] and pos != 0:
            out.append(("close_all",))
        return out

    ref = simulate_brackets(o, h, l, c, orders, on_close=True)
    sym = SymbolInfo.make("NASDAQ:XYZ", "stock", qty_step=1e-9)
    ok, d = compare_q(run_conversion(TV_ID, df, symbol=sym, tf="15", params=params,
                                     strategy_overrides={"margin_long": 0, "margin_short": 0, "commission_value": 0, "slippage": 0, "default_qty_type": "fixed", "default_qty_value": QTY}), ref)
    return ok and len(ref) > 12, f"{d} (got {len(ref)})"


BASE = dict(days=90, tp=35, sl=18, be=12)


def check():
    df = bars(60000, seed=631, freq="15min")
    for k in ("open", "high", "low", "close"):
        df[k] = 100 * (df[k] / 100) ** 0.1
    msgs, allok = [], True
    cases = (({"Backtest Lookback (Days)": 200}, dict(days=200)),
             ({"Backtest Lookback (Days)": 400, "Take Profit (Pips)": 20, "Stop Loss (Pips)": 10, "Breakeven Trigger (Pips)": 6}, dict(days=400, tp=20, sl=10, be=6)))
    for params, ov in cases:
        ok, m = one(df, params, {**BASE, **ov})
        allok &= ok
        msgs.append(m)
    return allok, " | ".join(msgs)
