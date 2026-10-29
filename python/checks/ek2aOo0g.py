"""Independent check — Optimized Keltner Channels (ek2aOo0g): 30-minute bars on a US stock chart, pending stop entries. Bands: moving average (EMA or SMA, 20) +/- 2 x (ATR(10) | the true range of the bar | RMA of the range). A close crossing above the upper band (when the optional EMA200 side / Monday-Friday 09:30-14:45 filters allow) leaves a buy-stop at that bar's high + 1 tick (cross below the lower band: sell-stop at low - 1 tick); a "crossed" flag is set then and the pending order of that side is cancelled (flag cleared) at every bar whose close is back under the average (over for shorts) or whose high reaches the stop price (low for shorts), before a new entry of that bar is issued. Optional wide ATR stop (entry price - 3 x ATR10, set at the first script run in the trade and kept, issued every bar) and mid-band exit (close crossing back through the average closes at the next open). Uses the pending-order reference broker (simulate_ord). Margin off on the pinelib side.
Variants: defaults; EMA200 filter + session filter + ATR stop 2.5 + mid-band exit; True-Range bands with SMA."""
import numpy as np
import pandas as pd

from indep import bars, compare, np_atr, np_ema, np_rma, np_sma, np_tr, run_conversion, simulate_ord
from pinelib import SymbolInfo

TV_ID = "ek2aOo0g"


def one(df, params, style, use_exp, trend, tfilt, atr_stop, asm, mid):
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    ma = np_ema(c, 20) if use_exp else np_sma(c, 20)
    rg = {"atr": np_atr(h, l, c, 10), "tr": np_tr(h, l, c, handle_na=True), "rng": np_rma(h - l, 20)}[style]
    up, lo = ma + rg * 2.0, ma - rg * 2.0
    e200 = np_ema(c, 200)
    atr10 = np_atr(h, l, c, 10)
    ny = pd.to_datetime(df["time"], unit="ms", utc=True).dt.tz_convert("America/New_York")
    m = (ny.dt.hour * 60 + ny.dt.minute).to_numpy()
    wd = ny.dt.dayofweek.to_numpy()
    tallowed = ((m >= 570) & (m < 885) & (wd < 5)) if tfilt else np.ones(n, bool)
    pc, pu, pl, pm = np.r_[np.nan, c[:-1]], np.r_[np.nan, up[:-1]], np.r_[np.nan, lo[:-1]], np.r_[np.nan, ma[:-1]]
    with np.errstate(invalid="ignore"):
        cu = (c > up) & (pc <= pu)
        cl = (c < lo) & (pc >= pl)
        mdn = (c < ma) & (pc >= pm)
        mup = (c > ma) & (pc <= pm)
        la = (((c > e200) if trend else np.ones(n, bool))) & tallowed
        sa = (((c < e200) if trend else np.ones(n, bool))) & tallowed
    S = dict(bp=0.0, sp=0.0, cb=False, cs=False, lsp=np.nan, ssp=np.nan, pp=0)

    def orders(i, pos, info):
        out = []
        pp = S["pp"]
        S["pp"] = pos
        if cu[i] and la[i]:
            S["bp"] = h[i] + 0.01
            S["cb"] = True
        if cl[i] and sa[i]:
            S["sp"] = l[i] - 0.01
            S["cs"] = True
        cancel_b = S["cb"] and (c[i] < ma[i] or h[i] >= S["bp"])
        cancel_s = S["cs"] and (c[i] > ma[i] or l[i] <= S["sp"])
        if cancel_b:
            out.append(("cancel", "KltChLE"))
            S["cb"] = False
        if cu[i] and la[i]:
            out.append(("entry", "KltChLE", 1, S["bp"], None))
        if cancel_s:
            out.append(("cancel", "KltChSE"))
            S["cs"] = False
        if cl[i] and sa[i]:
            out.append(("entry", "KltChSE", -1, S["sp"], None))
        if pos > 0:
            if (pp <= 0 or np.isnan(S["lsp"])):
                ep = info["ep"] if info["ep"] > 0 else c[i]
                S["lsp"] = ep - atr10[i] * asm
        else:
            S["lsp"] = np.nan
        if pos < 0:
            if (pp >= 0 or np.isnan(S["ssp"])):
                ep = info["ep"] if info["ep"] > 0 else c[i]
                S["ssp"] = ep + atr10[i] * asm
        else:
            S["ssp"] = np.nan
        if atr_stop:
            if pos > 0:
                out.append(("exit", "SL Long", "KltChLE", None if np.isnan(S["lsp"]) else S["lsp"], None))
            if pos < 0:
                out.append(("exit", "SL Short", "KltChSE", None if np.isnan(S["ssp"]) else S["ssp"], None))
        if mid:
            if pos > 0 and mdn[i]:
                out.append(("close", "KltChLE"))
            if pos < 0 and mup[i]:
                out.append(("close", "KltChSE"))
        return out

    with np.errstate(invalid="ignore"):
        ref = simulate_ord(o, h, l, c, orders)
    sym = SymbolInfo.make("NASDAQ:XYZ", "stock", qty_step=1e-9)
    ok, d = compare(run_conversion(TV_ID, df, symbol=sym, tf="30", params=params, strategy_overrides={"commission_value": 0, "margin_long": 0, "margin_short": 0}), ref)
    return ok and len(ref) > 5, f"{d} (got {len(ref)})"


def check():
    df = bars(12000, seed=444, freq="30min")
    for k in ("open", "high", "low", "close"):
        df[k] = 100 * (df[k] / 100) ** 0.4
    msgs, allok = [], True
    cases = (({}, ("atr", True, False, False, False, 3.0, False)),
             ({"Use 200 EMA Trend Filter": True, "Use Time Session Filter": True, "Use Wide ATR Stop Loss": True, "ATR Stop Multiplier": 2.5, "Exit on Mid-Band Close": True},
              ("atr", True, True, True, True, 2.5, True)),
             ({"Bands Style": "True Range", "Use Exponential MA": False}, ("tr", False, False, False, False, 3.0, False)))
    for params, args in cases:
        ok, m = one(df, params, *args)
        allok &= ok
        msgs.append(m)
    return allok, " | ".join(msgs)
