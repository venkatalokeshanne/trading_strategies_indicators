"""Independent check — Range Trading SOL/USD (BjLwxoH4): hourly bars of a crypto-style symbol, market orders at the next open, default quantity 1, pyramiding 3, commission / slippage / margin off.
Range high / low = highest high / lowest low over the L bars that end 12 bars back. A close crossing under the range high enters short, over the range low enters long (up to 3 entries per side; an opposite entry reverses); a high above the range high closes the longs, a low below the range low closes the shorts,
a high above range high + offset closes the shorts, a low below range low - offset closes the longs (closes of an id that is not open at script time are ignored); a position whose loss per unit against the average entry exceeds the maximum is closed in full.
Uses the quantity-aware bracket reference (indep.simulate_brackets), comparing quantities too. Variants: defaults with a small lookback / loss limit; asymmetric offsets and a larger lookback."""
import numpy as np

from indep import bars, compare_q, np_cross_over, np_cross_under, run_conversion, simulate_brackets
from pinelib import SymbolInfo

TV_ID = "BjLwxoH4"


def one(df, params, p):
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    L = p["len"]
    hs = np.r_[np.full(12, np.nan), h[:-12]]
    ls_ = np.r_[np.full(12, np.nan), l[:-12]]
    # ta.highest / lowest need L bars of history but then ignore the na values that high[12] has at the start
    hi = np.array([np.nanmax(hs[i - L + 1:i + 1]) if i >= L - 1 and not np.all(np.isnan(hs[i - L + 1:i + 1])) else np.nan for i in range(n)])
    lo = np.array([np.nanmin(ls_[i - L + 1:i + 1]) if i >= L - 1 and not np.all(np.isnan(ls_[i - L + 1:i + 1])) else np.nan for i in range(n)])
    sc, lc = np_cross_under(c, hi), np_cross_over(c, lo)

    def orders(i, info):
        out = []
        if sc[i]:
            out.append(("entry", "Short", -1, 1.0))
        if lc[i]:
            out.append(("entry", "Long", 1, 1.0))
        with np.errstate(invalid="ignore"):
            if h[i] > hi[i]:
                out.append(("close", "Long"))
            if l[i] < lo[i]:
                out.append(("close", "Short"))
            if h[i] > hi[i] + p["ol"]:
                out.append(("close", "Short"))
            if l[i] < lo[i] - p["os"]:
                out.append(("close", "Long"))
            pos, avg = info["pos"], info["avg"]
            loss = avg - c[i] if pos > 0 else c[i] - avg
            if loss > p["ml"]:
                out.append(("close_all",))
        return out

    ref = simulate_brackets(o, h, l, c, orders, pyramiding=3)
    sym = SymbolInfo.make("BINANCE:SOLUSDT", "crypto", qty_step=1e-9)
    ok, d = compare_q(run_conversion(TV_ID, df, symbol=sym, tf="60", params=params,
                                     strategy_overrides={"margin_long": 0, "margin_short": 0, "commission_value": 0, "slippage": 0}), ref)
    return ok and len(ref) > 12, f"{d} (got {len(ref)})"


BASE = dict(len=72, ol=9.0, os=12.0, ml=7.0)


def check():
    df = bars(20000, seed=221, freq="1h")
    for k in ("open", "high", "low", "close"):
        df[k] = 100 * (df[k] / 100) ** 0.5
    msgs, allok = [], True
    cases = (({}, {}),
             ({"Lookback": 30, "Max Verlust pro Trade": 3.0}, dict(len=30, ml=3.0)),
             ({"Lookback": 120, "offsetlong": 3.0, "offsetshort": 5.0}, dict(len=120, ol=3.0, os=5.0)))
    for params, ov in cases:
        ok, m = one(df, params, {**BASE, **ov})
        allok &= ok
        msgs.append(m)
    return allok, " | ".join(msgs)
