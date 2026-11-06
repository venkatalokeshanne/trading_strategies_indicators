"""Independent check — ETH Long | MVRV Setup (gSXg6CU1): 4-hour bars of a synthetic price compressed into the 1700-3200 range, process_orders_on_close (the entry fills at the signal close), fixed quantity 10 on the pinelib side (the original sizes 10 % of equity), commission / slippage / margin off.
Entry while flat: close inside the zone [low, high] and above 1800, EMA21 > EMA55, 45 < RSI14 < 70, volume above its 20-bar SMA. Exit orders issued with the entry: 40 % at TP1, 35 % at TP2, 25 % at TP3 of the entry quantity, all with the same stop level; each order closes its share at its limit, or the stop level (gap fills at the open).
Uses the quantity-aware bracket reference (indep.simulate_brackets), which also compares the closed quantities.
Variants: defaults; wider zone with closer targets and a tighter stop; zone 1750-2100, targets 2000 / 2300 / 2700, stop 1900 (the stop sits inside the zone, so gaps through it matter)."""
import numpy as np

from indep import bars, compare_q, np_ema, np_rsi, np_sma, run_conversion, simulate_brackets
from pinelib import SymbolInfo

TV_ID = "gSXg6CU1"
QTY = 10.0


def one(df, params, p):
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    v = df["volume"].to_numpy()
    e21, e55, rsi, vma = np_ema(c, 21), np_ema(c, 55), np_rsi(c, 14), np_sma(v, 20)

    def orders(i, info):
        with np.errstate(invalid="ignore"):
            ok = (c[i] >= p["lo"] and c[i] <= p["hi"] and e21[i] > e55[i] and c[i] > 1800.0 and rsi[i] > 45 and rsi[i] < 70 and v[i] > vma[i] and info["pos"] == 0)
        if not ok:
            return []
        return [("entry", "ETH Long", 1, QTY), ("exit", "TP1", "ETH Long", 40, p["sl"], p["t1"]), ("exit", "TP2", "ETH Long", 35, p["sl"], p["t2"]), ("exit", "TP3", "ETH Long", 25, p["sl"], p["t3"])]

    ref = simulate_brackets(o, h, l, c, orders, on_close=True)
    sym = SymbolInfo.make("BINANCE:ETHUSDT", "crypto", qty_step=1e-9)
    ok, d = compare_q(run_conversion(TV_ID, df, symbol=sym, tf="240", params=params,
                                     strategy_overrides={"margin_long": 0, "margin_short": 0, "default_qty_type": "fixed", "default_qty_value": QTY}), ref)
    return ok and len(ref) >= 12, f"{d} (got {len(ref)})"


BASE = dict(lo=1800.0, hi=1950.0, sl=1680.0, t1=2245.0, t2=2650.0, t3=3000.0)


def check():
    df = bars(30000, seed=61, freq="4h")
    base = df["close"].iloc[0]
    for k in ("open", "high", "low", "close"):
        df[k] = 1700 * (df[k] / base) ** 0.35
    msgs, allok = [], True
    cases = (({}, {}),
             ({"Entry Zone - Upper Bound": 2100.0, "TP1 — Realized Price": 2000.0, "TP2 — Intermediate Target": 2200.0, "TP3 — Final Target": 2400.0, "Stop Loss": 1750.0},
              dict(hi=2100.0, t1=2000.0, t2=2200.0, t3=2400.0, sl=1750.0)),
             ({"Entry Zone - Lower Bound": 1750.0, "Entry Zone - Upper Bound": 2100.0, "TP1 — Realized Price": 2000.0, "TP2 — Intermediate Target": 2300.0, "TP3 — Final Target": 2700.0, "Stop Loss": 1900.0},
              dict(lo=1750.0, hi=2100.0, t1=2000.0, t2=2300.0, t3=2700.0, sl=1900.0)))
    for params, ov in cases:
        ok, m = one(df, params, {**BASE, **ov})
        allok &= ok
        msgs.append(m)
    return allok, " | ".join(msgs)
