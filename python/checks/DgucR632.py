"""Independent check — Nifty Institutional Trend Rider (DgucR632): 5-min New York bars. Close beyond session VWAP and EMA20 with RSI(14) beyond 60/40 enters
(reversing). The stop is a ratchet recomputed each bar while in the position: long = max(close*(1-0.5 %), previous value), short = min(close*(1+0.5 %),
previous value); 0 / 999999 when flat. The exit is only issued while a position exists, so bar i works with bar i-1's stop and only if a position
existed at bar i-1's close."""
import numpy as np

from indep import bars, compare, np_ema, np_rsi, np_vwap, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "DgucR632"


def check():
    df = bars(20000, seed=140, freq="5min")
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    vw, e20, rsi = np_vwap(df, c), np_ema(c, 20), np_rsi(c, 14)
    with np.errstate(invalid="ignore"):
        lg = (c > vw) & (c > e20) & (rsi > 60)
        sg = (c < vw) & (c < e20) & (rsi < 40)
    lsp, ssp = np.zeros(n), np.full(n, 999999.0)
    poscl = np.zeros(n)

    def orders(i, pos):
        poscl[i] = pos
        pl = lsp[i - 1] if i else 0.0
        ps = ssp[i - 1] if i else 999999.0
        lsp[i] = max(c[i] * (1 - 0.005), pl) if pos > 0 else 0.0
        ssp[i] = min(c[i] * (1 + 0.005), 999999.0 if ps == 0 else ps) if pos < 0 else 999999.0
        return ([("entry", 1)] if lg[i] else []) + ([("entry", -1)] if sg[i] else [])

    def stop(i, pos, ep, eb):
        if i == 0 or poscl[i - 1] == 0:
            return None
        return lsp[i - 1] if pos > 0 else ssp[i - 1]

    ref = simulate(o, h, l, c, orders, stop=stop)
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="5", strategy_overrides={"margin_long": 0, "margin_short": 0}), ref)
    return ok and len(ref) > 10, f"{detail} (need >10 trades, got {len(ref)})"
