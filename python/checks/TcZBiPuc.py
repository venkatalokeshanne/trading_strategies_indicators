"""Independent check — CNPS MACD (TcZBiPuc): daily bars. MACD(12,26,9) line crossing over / under its signal reverses long / short (1 contract). While a position exists at a bar's close, a stop at entry -/+ SL points
and a target at entry +/- TP points (scaled to the price level, passed to both sides) work from the NEXT bar. The close of the old side queued behind the reversing entry is a no-op."""
from indep import bars, compare, np_cross_over, np_cross_under, np_ema, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "TcZBiPuc"


def check():
    df = bars(5000, seed=203)
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    sl_p, tp_p = float(c.mean()) * 0.02, float(c.mean()) * 0.06
    m = np_ema(c, 12) - np_ema(c, 26)
    sig = np_ema(m, 9)
    up, dn = np_cross_over(m, sig), np_cross_under(m, sig)

    def orders(i, pos):
        out = ([("entry", 1)] if up[i] else []) + ([("entry", -1)] if dn[i] else [])
        if dn[i] and pos > 0:
            out.append(("close", 1))
        if up[i] and pos < 0:
            out.append(("close", -1))
        return out

    ref = simulate(o, h, l, c, orders,
                   stop=lambda i, pos, ep, eb: None if eb >= i else ep - pos * sl_p,
                   target=lambda i, pos, ep, eb: None if eb >= i else ep + pos * tp_p)
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, detail = compare(run_conversion(TV_ID, df, symbol=sym, tf="D", params={"Dừng lỗ (points)": sl_p, "Chốt lời (points)": tp_p}), ref)
    return ok and len(ref) > 10, f"{detail} (need >10 trades, got {len(ref)})"
