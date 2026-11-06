"""Independent check — Shihan's Pure PA + Vol + POC V18.2 (RIv7js9Y): daily bars, one position (reversals), trade list only. From the PREVIOUS candle: body, upper wick (high - max(o, c)), lower wick (min(o, c) - low);
hammer = lower >= 2 x body and upper <= 1.2 x body; star = upper >= 2 x body and lower <= 1.2 x body; micro POC = both wicks >= 1.5 x body and min/max(wicks, 0.0001) >= 0.6; all with body > 0. The previous volume must exceed 1.1 x the
SMA50 of volume taken one bar earlier. Buy: hammer and close > previous close, or POC and close > previous high; sell mirrored. On every signal bar the stop (previous low -/+ 5 ticks of 0.01) and the 1.5R target are
(re)issued - also when the side is already open - and work from the next bar. Mode variants: dual (default) and PA only. Size 5% on the pinelib side; margin and slippage off."""
import numpy as np

from indep import bars, compare, np_sma, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "RIv7js9Y"


def one(df, mode):
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    v = df["volume"].to_numpy()
    n = len(c)
    po, pc, ph, pl, pv = (np.r_[np.nan, x[:-1]] for x in (o, c, h, l, v))
    body = np.abs(pc - po)
    up = ph - np.maximum(po, pc)
    lo = np.where(pl < np.minimum(po, pc), np.minimum(po, pc) - pl, 0.0)
    vb = np.r_[np.nan, np_sma(v, 50)[:-1]]
    with np.errstate(invalid="ignore", divide="ignore"):
        ham = (lo >= body * 2.0) & (up <= body * 1.2) & (body > 0)
        star = (up >= body * 2.0) & (lo <= body * 1.2) & (body > 0)
        sym = np.minimum(up, lo) / np.maximum(np.maximum(up, lo), 0.0001)
        poc = (up >= body * 1.5) & (lo >= body * 1.5) & (sym >= 0.6) & (body > 0)
        vok = pv > vb * 1.1
        pa = mode != "2. POC Mode (Doji Balance)"
        pocm = mode != "1. PA Mode (Hammer/Star)"
        vb_ = (pa & ham & (c > pc) & vok) | (pocm & poc & vok & (c > ph))
        vs_ = (pa & star & (c < pc) & vok) | (pocm & poc & vok & (c < pl))
    lv = {1: None, -1: None}

    def orders(i, pos):
        out = []
        if vb_[i]:
            sl = pl[i] - 0.05
            tp = c[i] + (c[i] - sl) * 1.5
            if (tp - c[i]) / (c[i] - sl) >= 1.2:
                lv[1] = (sl, tp)
                out.append(("entry", 1))
        if vs_[i]:
            sl = ph[i] + 0.05
            tp = c[i] - (sl - c[i]) * 1.5
            if (c[i] - tp) / (sl - c[i]) >= 1.2:
                lv[-1] = (sl, tp)
                out.append(("entry", -1))
        return out

    def stop(i, pos, ep, eb):
        return lv[pos][0] if lv[pos] else None

    def target(i, pos, ep, eb):
        return lv[pos][1] if lv[pos] else None

    with np.errstate(invalid="ignore", divide="ignore"):
        ref = simulate(o, h, l, c, orders, stop=stop, target=target)
    sym_ = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, d = compare(run_conversion(TV_ID, df, symbol=sym_, tf="D", params={"Select Mode": mode},
                                   strategy_overrides={"margin_long": 0, "margin_short": 0, "slippage": 0, "default_qty_value": 5}), ref)
    return ok and len(ref) > 5, f"{mode}: {d} (got {len(ref)})"


def check():
    df = bars(8000, seed=630)
    msgs, allok = [], True
    for mode in ("3. PA + POC (Dual Mode)", "1. PA Mode (Hammer/Star)"):
        ok, m = one(df, mode)
        allok &= ok
        msgs.append(m)
    return allok, " | ".join(msgs)
