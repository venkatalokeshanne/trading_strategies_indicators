"""Independent check — SMC Fractal Strategy v3 (97G0VL40): 15-minute bars (24h synthetic) on a stock chart (New York clock, 240-minute higher-timeframe blocks from 09:30), one position, market entries at the next open, bracket placed with the entry (works from the fill bar).
Swing high / low = latest confirmed pivot (10 bars each side, strict). A bar that trades below the swing low and closes above it (above the swing high and closes below, for the bear side) records the sweep bar; a close through the opposite swing with the previous close on the other side within 20 bars of the sweep is the break of structure, which sets
trend = +1 / -1, clears that sweep, and (bull) stores the most recent bearish candle among the previous 30 bars as the order block (bear: bullish candle); an order block is dropped when a close goes beyond its far side. Breaker: three prior bearish (bullish) candles and then a close above (below) the highest (lowest) open of those three, while the trend agrees -> zone = their high / low range,
dropped when a close goes beyond it. FVG (trend agrees): high[2] < low with a gap >= 0.0001 -> zone (high[2], low) (bear mirrored). Entry: in the 07:00-15:00 NY session, trend and the 4h bias (4h close vs 4h EMA20, lookahead off) agree, a close inside any zone and flat. Stop = lower edge of the first of (OB, FVG, breaker) tapped - 0.0001 (upper edge + 0.0001 for shorts),
target = 2R; the upper edges of all three bull (bear) zones are cleared on entry. Slippage / margin off on the pinelib side."""
import numpy as np
import pandas as pd

from indep import bars, compare, np_ema, np_periods, np_security_lookahead_off, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "97G0VL40"
K = 10


def check():
    df = bars(40000, seed=741, freq="15min")
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    pid, last_of = np_periods(df, 240)
    npd = pid[-1] + 1
    pc = np.array([c[(pid == p) & last_of][0] for p in range(npd)])
    pe = np_ema(pc, 20)
    htf_e = np_security_lookahead_off(pe, pid, last_of)
    htf_c = np_security_lookahead_off(pc, pid, last_of)
    with np.errstate(invalid="ignore"):
        htf_tr = np.where(htf_c > htf_e, 1, np.where(htf_c < htf_e, -1, 0))
    ny = pd.to_datetime(df["time"], unit="ms", utc=True).dt.tz_convert("America/New_York")
    m = (ny.dt.hour * 60 + ny.dt.minute).to_numpy()
    ses = (m >= 420) & (m < 900)
    ph, pl = np.full(n, np.nan), np.full(n, np.nan)
    for i in range(2 * K, n):
        j = i - K
        if h[j] > h[j - K:j].max() and h[j] > h[j + 1:i + 1].max():
            ph[i] = h[j]
        if l[j] < l[j - K:j].min() and l[j] < l[j + 1:i + 1].min():
            pl[i] = l[j]
    S = dict(hi=np.nan, lo=np.nan, sb=-999, sr=-999, tr=0)
    Z = {k: np.nan for k in ("boh", "bol", "seh", "sel", "bbh", "bbl", "sbh", "sbl", "bfh", "bfl", "sfh", "sfl")}
    lev = {}
    B = 0.0001

    def orders(i, pos):
        out = []
        if not np.isnan(ph[i]):
            S["hi"] = ph[i]
        if not np.isnan(pl[i]):
            S["lo"] = pl[i]
        if not np.isnan(S["lo"]) and l[i] < S["lo"] and c[i] > S["lo"]:
            S["sb"] = i
        if not np.isnan(S["hi"]) and h[i] > S["hi"] and c[i] < S["hi"]:
            S["sr"] = i
        pcl = c[i - 1] if i else np.nan
        bbos = (i - S["sb"]) <= 20 and not np.isnan(S["hi"]) and c[i] > S["hi"] and pcl <= S["hi"]
        sbos = (i - S["sr"]) <= 20 and not np.isnan(S["lo"]) and c[i] < S["lo"] and pcl >= S["lo"]
        if bbos:
            S["tr"], S["sb"] = 1, -999
        if sbos:
            S["tr"], S["sr"] = -1, -999
        if bbos:
            for k in range(1, 31):
                if i - k >= 0 and c[i - k] < o[i - k]:
                    Z["boh"], Z["bol"] = h[i - k], l[i - k]
                    break
        if sbos:
            for k in range(1, 31):
                if i - k >= 0 and c[i - k] > o[i - k]:
                    Z["seh"], Z["sel"] = h[i - k], l[i - k]
                    break
        if not np.isnan(Z["bol"]) and c[i] < Z["bol"]:
            Z["boh"] = Z["bol"] = np.nan
        if not np.isnan(Z["seh"]) and c[i] > Z["seh"]:
            Z["seh"] = Z["sel"] = np.nan
        if i >= 3:
            pb3 = c[i - 1] < o[i - 1] and c[i - 2] < o[i - 2] and c[i - 3] < o[i - 3]
            pu3 = c[i - 1] > o[i - 1] and c[i - 2] > o[i - 2] and c[i - 3] > o[i - 3]
            if S["tr"] == 1 and pb3 and c[i] > max(o[i - 1], o[i - 2], o[i - 3]):
                Z["bbh"], Z["bbl"] = max(h[i - 1], h[i - 2], h[i - 3]), min(l[i - 1], l[i - 2], l[i - 3])
            if S["tr"] == -1 and pu3 and c[i] < min(o[i - 1], o[i - 2], o[i - 3]):
                Z["sbh"], Z["sbl"] = max(h[i - 1], h[i - 2], h[i - 3]), min(l[i - 1], l[i - 2], l[i - 3])
        if not np.isnan(Z["bbl"]) and c[i] < Z["bbl"]:
            Z["bbh"] = Z["bbl"] = np.nan
        if not np.isnan(Z["sbh"]) and c[i] > Z["sbh"]:
            Z["sbh"] = Z["sbl"] = np.nan
        if i >= 2:
            if S["tr"] == 1 and h[i - 2] < l[i] and (l[i] - h[i - 2]) >= B:
                Z["bfh"], Z["bfl"] = l[i], h[i - 2]
            if S["tr"] == -1 and l[i - 2] > h[i] and (l[i - 2] - h[i]) >= B:
                Z["sfh"], Z["sfl"] = l[i - 2], h[i]
        isn = np.isnan
        bo = (not isn(Z["boh"])) and c[i] <= Z["boh"] and c[i] >= Z["bol"]
        bf = (not isn(Z["bfh"])) and c[i] <= Z["bfh"] and c[i] >= Z["bfl"]
        bb = (not isn(Z["bbh"])) and c[i] <= Z["bbh"] and c[i] >= Z["bbl"]
        so = (not isn(Z["seh"])) and c[i] >= Z["sel"] and c[i] <= Z["seh"]
        sf = (not isn(Z["sfh"])) and c[i] >= Z["sfl"] and c[i] <= Z["sfh"]
        sb_ = (not isn(Z["sbh"])) and c[i] >= Z["sbl"] and c[i] <= Z["sbh"]
        if ses[i] and S["tr"] == 1 and htf_tr[i] == 1 and (bo or bf or bb) and pos == 0:
            ref = Z["bol"] if bo else (Z["bfl"] if bf else Z["bbl"])
            sl = ref - B
            out.append(("entry", 1))
            lev[i] = (sl, c[i] + (c[i] - sl) * 2.0)
            Z["boh"] = Z["bfh"] = Z["bbh"] = np.nan
        if ses[i] and S["tr"] == -1 and htf_tr[i] == -1 and (so or sf or sb_) and pos == 0:
            ref = Z["seh"] if so else (Z["sfh"] if sf else Z["sbh"])
            sl = ref + B
            out.append(("entry", -1))
            lev[i] = (sl, c[i] - (sl - c[i]) * 2.0)
            Z["seh"] = Z["sfh"] = Z["sbh"] = np.nan
        return out

    stop = lambda i, pos, ep, eb: lev[eb - 1][0] if eb - 1 in lev else None
    tgt = lambda i, pos, ep, eb: lev[eb - 1][1] if eb - 1 in lev else None
    with np.errstate(invalid="ignore"):
        ref_ = simulate(o, h, l, c, orders, stop=stop, target=tgt)
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, d = compare(run_conversion(TV_ID, df, symbol=sym, tf="15", strategy_overrides={"margin_long": 0, "margin_short": 0, "slippage": 0}), ref_)
    return ok and len(ref_) > 10, f"{d} (got {len(ref_)})"
