"""Independent check — ORB + Fib Breakout (KX7AgFeB): 5-minute bars (prices x20), Chicago clock, process_orders_on_close, one position. Opening range = bars starting 08:30-08:44 of each day (reset at the first range bar), ready from the first bar after it; signals only inside 08:30-15:00. A close (or wick) crossing over the range high / under the range low
is evaluated only on bars where the session is on and the range is ready (Pine v6 lazy `and`: the cross's previous arguments are those of its last evaluated call). One signal per direction per day (the fired flags reset with the range, and are set even if the entry is refused). Entry at the close: stop = close - 1.5 ATR - 2 ticks (or the opposite range side), at least 1 tick away, target =
entry + 2R (or the 1.272 extension), qty 1; the daily guard (closed P&L since the session start + open P&L at the close) blocks new trades and flattens at its limit; max entries per day; session end flattens at the close of the first bar after the session. A high reaching entry + 1R (low for shorts) moves the stop to entry +/- 2 ticks; the bracket is issued from the first script run that sees the position (works from the next bar).
Variants: default; wick trigger + opposite-side stop + 1.272 target + tighter guards. Margin / slippage / commission off on the pinelib side."""
import numpy as np
import pandas as pd

from indep import bars, compare, np_atr, run_conversion, simulate
from pinelib import SymbolInfo

TV_ID = "KX7AgFeB"


class Lazy:
    def __init__(self, over):
        self.over, self.prev = over, None

    def __call__(self, a, b):
        res = False
        if self.prev is not None:
            pa, pb = self.prev
            res = (a > b and pa <= pb) if self.over else (a < b and pa >= pb)
        self.prev = (a, b)
        return bool(res)


def one(df, params, wick, mode, ext, max_tr, loss):
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    n = len(c)
    atr = np_atr(h, l, c, 14)
    ch = pd.to_datetime(df["time"], unit="ms", utc=True).dt.tz_convert("America/Chicago")
    m = (ch.dt.hour * 60 + ch.dt.minute).to_numpy()
    in_orb = (m >= 510) & (m < 525)
    in_sess = (m >= 510) & (m < 900)
    S = dict(oh=np.nan, ol=np.nan, ready=False, bf=False, sf=False, tt=0, anchor=0.0, blocked=False, ep=np.nan, ent=np.nan, stop=np.nan, tgt=np.nan, risk=np.nan)
    lz_b, lz_s = Lazy(True), Lazy(False)
    log: list = []
    poscl = np.zeros(n)
    stop_arr, tgt_arr = np.full(n, np.nan), np.full(n, np.nan)
    mt = 0.01

    def orders(i, pos):
        poscl[i] = pos
        out = []
        pin = in_orb[i - 1] if i else False
        psess = in_sess[i - 1] if i else False
        new_orb = in_orb[i] and not pin
        ended = (not in_orb[i]) and pin
        new_sess = in_sess[i] and not psess
        sess_ended = (not in_sess[i]) and psess
        if new_orb:
            S.update(oh=h[i], ol=l[i], ready=False, bf=False, sf=False)
        elif in_orb[i]:
            S["oh"] = max(h[i] if np.isnan(S["oh"]) else S["oh"], h[i])
            S["ol"] = min(l[i] if np.isnan(S["ol"]) else S["ol"], l[i])
        if ended:
            S["ready"] = True
        rng = S["oh"] - S["ol"]
        disp = in_sess[i] and S["ready"]
        rb = rs = False
        if disp:
            rb = lz_b(h[i] if wick else c[i], S["oh"])
            rs = lz_s(l[i] if wick else c[i], S["ol"])
        bs = rb and not S["bf"]
        ss = rs and not S["sf"]
        if bs:
            S["bf"] = True
        if ss:
            S["sf"] = True
        net = sum((t[4] - t[2]) * t[0] for t in log)
        if new_sess:
            S.update(tt=0, anchor=net, blocked=False)
        openp = pos * (c[i] - S["ep"]) if pos != 0 else 0.0
        pnl = net - S["anchor"] + openp
        if pnl <= -loss:
            S["blocked"] = True
        can = (not S["blocked"]) and S["tt"] < max_tr
        if bs and can:
            px = c[i]
            raw = (S["ol"] if mode == "opp" else px - atr[i] * 1.5)
            st_ = min(raw - 2 * mt, px - mt)
            rk = px - st_
            S.update(ent=px, stop=st_, risk=rk, tgt=(S["oh"] + rng * 0.272) if ext else px + 2.0 * rk)
            out.append(("entry", 1))
            S["tt"] += 1
        if ss and can:
            px = c[i]
            raw = (S["oh"] if mode == "opp" else px + atr[i] * 1.5)
            st_ = max(raw + 2 * mt, px + mt)
            rk = st_ - px
            S.update(ent=px, stop=st_, risk=rk, tgt=(S["ol"] - rng * 0.272) if ext else px - 2.0 * rk)
            out.append(("entry", -1))
            S["tt"] += 1
        if pos > 0:
            if h[i] >= S["ent"] + S["risk"]:
                S["stop"] = max(S["stop"], S["ent"] + 2 * mt)
            stop_arr[i], tgt_arr[i] = S["stop"], S["tgt"]
        if pos < 0:
            if l[i] <= S["ent"] - S["risk"]:
                S["stop"] = min(S["stop"], S["ent"] - 2 * mt)
            stop_arr[i], tgt_arr[i] = S["stop"], S["tgt"]
        if S["blocked"] and pos != 0:
            out.append(("close", pos))
        if sess_ended and pos != 0:
            out.append(("close", pos))
        return out

    def lvl(arr):
        def f(i, pos, ep, eb):
            S["ep"] = ep
            if i == 0 or eb >= i or poscl[i - 1] * pos <= 0 or np.isnan(arr[i - 1]):
                return None
            return arr[i - 1]
        return f

    sf, tf = lvl(stop_arr), lvl(tgt_arr)

    def stop(i, pos, ep, eb):
        S["ep"] = ep
        return sf(i, pos, ep, eb)

    with np.errstate(invalid="ignore"):
        ref = simulate(o, h, l, c, orders, stop=stop, target=tf, on_close=True, log=log)
    sym = SymbolInfo.make("NASDAQ:SPY", "stock", qty_step=1e-9)
    ok, d = compare(run_conversion(TV_ID, df, symbol=sym, tf="5", params=params,
                                   strategy_overrides={"margin_long": 0, "margin_short": 0, "slippage": 0, "commission_value": 0}), ref)
    return ok and len(ref) > 10, f"{d} (got {len(ref)})"


def check():
    df = bars(50000, seed=731, freq="5min")
    for k in ("open", "high", "low", "close"):
        df[k] = df[k] * 20.0
    msgs, allok = [], True
    for params, wick, mode, ext, mt_, loss in (
            ({}, False, "atr", False, 4, 500.0),
            ({"Breakout Trigger": "Wick (High/Low)", "Stop placement": "ORB opposite", "Target": "Ext 1.272", "Max entries per day": 2, "Daily loss limit ($)": 150.0}, True, "opp", True, 2, 150.0)):
        ok, m = one(df, params, wick, mode, ext, mt_, loss)
        allok &= ok
        msgs.append(m)
    return allok, " | ".join(msgs)
