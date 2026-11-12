"""Independent check — Market Open Break 2.0 (7lMAaqyL): 5-minute bars (24 h synthetic, volatility compressed), market orders at the next open, one position. The 09:30 New York bar's high / low is the anchor (counters reset on it; the previous day's realised P&L, summed with each trade's contracts, decides the consecutive-losing-day counter: at 2 the day is skipped and the counter reset). 09:31-11:30: while flat, under 3 trades and 2 losses today, a close crossing the anchor high (low) from inside, not the same direction as the previous entry that day, with stop distance <= Max SL % of the close, enters with contracts = max(1, floor(350 / (distance x 2))); target = close x (1 +/- 0.1 %), stop = the opposite anchor side, both from the fill bar. After 11:30 any open position is closed at the next open. Commission and slippage off on the pinelib side. Variants: default; looser Max SL / TP, 1 trade a day-loss limit."""
import numpy as np
import pandas as pd

from indep import bars, compare, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "7lMAaqyL"


def one(df, params, tp_pct, max_sl, max_tr, max_loss, max_cd):
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    ny = pd.to_datetime(df["time"], unit="ms", utc=True).dt.tz_convert("America/New_York")
    m = (ny.dt.hour * 60 + ny.dt.minute).to_numpy()
    S = dict(ah=np.nan, al=np.nan, aset=False, nt=0, nl=0, skip=False, last=0, cl=0, dse=0.0, pc=0)
    lev = {}
    log = []

    def pnl(t):
        return t[0] * (t[4] - t[2]) * lev[t[1] - 1][2]

    def orders(i, pos):
        out = []
        if m[i] == 570:
            if S["aset"]:
                net = sum(pnl(t) for t in log)
                S["cl"] = S["cl"] + 1 if net - S["dse"] < 0 else 0
            S["skip"] = S["cl"] >= max_cd
            if S["skip"]:
                S["cl"] = 0
            S.update(ah=h[i], al=l[i], aset=True, nt=0, nl=0, last=0, dse=sum(pnl(t) for t in log), pc=len(log))
        if len(log) > S["pc"]:
            S["nl"] += sum(1 for t in log[S["pc"]:] if pnl(t) < 0)
            S["pc"] = len(log)
        inw = 571 <= m[i] <= 690
        can = S["aset"] and not S["skip"] and S["nt"] < max_tr and S["nl"] < max_loss and pos == 0 and inw
        if i == 0:
            return out
        ba = can and c[i] > S["ah"] and c[i - 1] <= S["ah"]
        bb = can and c[i] < S["al"] and c[i - 1] >= S["al"]
        if ba and S["last"] != 1 and (c[i] - S["al"]) / c[i] * 100 <= max_sl:
            q = max(1, np.floor(350.0 / ((c[i] - S["al"]) * 2.0)))
            lev[i] = (S["al"], c[i] * (1 + tp_pct / 100), q)
            S["nt"] += 1
            S["last"] = 1
            out.append(("entry", 1))
        if bb and S["last"] != -1 and (S["ah"] - c[i]) / c[i] * 100 <= max_sl:
            q = max(1, np.floor(350.0 / ((S["ah"] - c[i]) * 2.0)))
            lev[i] = (S["ah"], c[i] * (1 - tp_pct / 100), q)
            S["nt"] += 1
            S["last"] = -1
            out.append(("entry", -1))
        if m[i] > 690 and pos != 0:
            out.append(("close", pos))
        return out

    stop = lambda i, pos, ep, eb: lev[eb - 1][0] if eb - 1 in lev else None
    tgt = lambda i, pos, ep, eb: lev[eb - 1][1] if eb - 1 in lev else None
    ref = simulate(o, h, l, c, orders, stop=stop, target=tgt, log=log)
    sym = SymbolInfo.make("CME_MINI:MNQ1!", "futures", mintick=0.25, qty_step=1e-9)
    ok, d = compare(run_conversion(TV_ID, df, symbol=sym, tf="5", params=params, strategy_overrides={"slippage": 0, "commission_value": 0}), ref)
    return ok and len(ref) > 10, f"{d} (got {len(ref)})"


def check():
    df = bars(12000, seed=515, freq="5min")
    for k in ("open", "high", "low", "close"):
        df[k] = 100 * (df[k] / 100) ** 0.12
    msgs, allok = [], True
    for params, args in (({}, (0.10, 0.30, 3, 2, 2)),
                         ({"TP %": 0.2, "Max SL %": 0.6, "Max Trades/Day": 5, "Max Losses/Day (CB)": 1, "Max Consec Loss Days (CB)": 1}, (0.2, 0.6, 5, 1, 1))):
        ok, msg = one(df, params, *args)
        allok &= ok
        msgs.append(msg)
    return allok, " | ".join(msgs)
