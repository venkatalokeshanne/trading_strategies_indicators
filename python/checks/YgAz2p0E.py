"""Independent check — tradingview BOT GOAT (YgAz2p0E): 30-minute bars (24 h synthetic, 7 days a week, so the weekday filter matters) on a crypto-style symbol (UTC calendar, mintick 0.01), market orders at the next open, fixed quantity 10 on the pinelib side (the original sizes 100 % of equity), margin / commission / slippage off.
Signal: EMA fast crossing over / under EMA slow on a weekday flips the position (close the other side, enter). Exit orders, issued on every bar for both sides: TP1 for 50 % of the entry quantity at +TP1 ticks; the other order for the rest with +TP2 ticks, -SL ticks and a trailing stop (activation after lag ticks of profit, follow distance in ticks);
they wait for their entry and are dropped when it is gone. Uses the quantity-aware bracket reference (indep.simulate_brackets: tick-form exits and the trailing leg), which also compares the closed quantities.
Variants: defaults; EMAs 8 / 21 with wider dollars; TP1 30 %, larger stop and tighter trailing, weekday filter off."""
import numpy as np
import pandas as pd

from indep import bars, compare_q, np_cross_over, np_cross_under, np_ema, run_conversion, simulate_brackets
from pinelib import SymbolInfo

TV_ID = "YgAz2p0E"
QTY = 10.0


def one(df, params, p):
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    sym = SymbolInfo.make("BINANCE:XYZUSDT", "crypto", qty_step=1e-9)
    tick = sym.mintick
    ef, es = np_ema(c, p["f"]), np_ema(c, p["s"])
    up, dn = np_cross_over(ef, es), np_cross_under(ef, es)
    dow = pd.to_datetime(df["time"], unit="ms", utc=True).dt.dayofweek.to_numpy()          # Monday = 0
    wk = (dow < 5) if p["wk"] else np.ones(len(c), bool)
    T = lambda dollars: max(1, int(np.floor(dollars / tick + 0.5)))

    def orders(i, info):
        out = []
        if up[i] and wk[i]:
            out += [("close", "Short"), ("entry", "Long", 1, QTY)]
        if dn[i] and wk[i]:
            out += [("close", "Long"), ("entry", "Short", -1, QTY)]
        for side, sid in (("Long", "Long"), ("Short", "Short")):
            out.append(("exit", "TP1 " + side, sid, p["tp1pct"], None, None, None, None, None, T(p["tp1"]), None))
            out.append(("exit", "Exit " + side, sid, None, None, None, T(p["lag"]), None, T(p["follow"]), T(p["tp2"]), T(p["sl"])))
        return out

    ref = simulate_brackets(o, h, l, c, orders, tick=tick)
    ok, d = compare_q(run_conversion(TV_ID, df, symbol=sym, tf="30", params=params,
                                     strategy_overrides={"margin_long": 0, "margin_short": 0, "default_qty_type": "fixed", "default_qty_value": QTY}), ref)
    return ok and len(ref) > 12, f"{d} (got {len(ref)})"


BASE = dict(f=21, s=55, wk=True, sl=1.0, tp1=1.0, tp2=3.0, tp1pct=50.0, lag=1.0, follow=0.5)


def check():
    df = bars(30000, seed=92, freq="30min")
    for k in ("open", "high", "low", "close"):
        df[k] = 100 * (df[k] / 100) ** 0.3
    msgs, allok = [], True
    cases = (({}, {}),
             ({"Fast EMA": 8, "Slow EMA": 21, "Take Profit 1 - half ($)": 0.6, "Take Profit 2 - full ($)": 4.0, "Stop Loss ($)": 1.5},
              dict(f=8, s=21, tp1=0.6, tp2=4.0, sl=1.5)),
             ({"TP1 size (% of position)": 30.0, "Stop Loss ($)": 2.0, "Trailing follow distance ($)": 0.3, "Trade weekdays only (Mon-Fri)": False},
              dict(tp1pct=30.0, sl=2.0, follow=0.3, wk=False)))
    for params, ov in cases:
        ok, m = one(df, params, {**BASE, **ov})
        allok &= ok
        msgs.append(m)
    return allok, " | ".join(msgs)
