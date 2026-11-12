"""Independent check — NYSE Open VWAP Reclaim + Pullback Hold (v5lj2Zyc and its three identical copies Nxo4ELTq, WhqvxciX, v5lj2Zyc): 1-minute bars (24 h synthetic) on a US stock chart, stop entries / protective stop + target, margin / commission / slippage off, one unit.
The strategy only acts on the trading day of the LAST bar and the previous one (days start at 18:00 New York: showThisOrPrevSession is built from last_bar_time), so each case is a short history (a few days) and the total trade count over all cases is what is required (> 8).
09:30-16:00 NY session VWAP (hlc3 x volume cumulated from the session's first bar, kept after the session), EMA 5/8/13 curl, reclaim ("1-close+hold" / "2-closes"), accept counters, hold candle that touches the VWAP (+ buffer) inside 09:45-11:00 with optional rising volume, VWAP-cross counter (limit) -> a pending long / short; entry stop one tick beyond the hold candle, protective stop beyond the other extreme (max ticks), target ticks;
entries re-issued each bar while allowed, pending orders stay in the book when the setup is cancelled; stop / target re-issued each bar while open. Uses the pending-order reference broker (simulate_ord).
Variants: defaults on three seeds (few trades); relaxed filters (no volume confirmation, 15-tick touch buffer, 400-tick stops, 8 crosses) on four seeds; wick cross detection, 2-closes, volume confirmation on, 2 crosses with 60-tick target and 5-tick stop buffer."""
import numpy as np
import pandas as pd

from indep import bars, compare, np_ema, run_conversion, simulate_ord
from pinelib import SymbolInfo

TV_ID = "v5lj2Zyc"
TICK = 0.01
DAY = 24 * 60 * 60 * 1000


def one(df, params, p):
    o, h, l, c, v = (df[k].to_numpy() for k in ("open", "high", "low", "close", "volume"))
    n = len(c)
    sym = SymbolInfo.make("NASDAQ:XYZ", "stock", qty_step=1e-9)
    ny = pd.to_datetime(df["time"], unit="ms", utc=True).dt.tz_convert("America/New_York")
    m = (ny.dt.hour * 60 + ny.dt.minute).to_numpy()
    in_rth = (m >= 570) & (m < 960)
    in_tr = (m >= 585) & (m < 660)

    def tds(ts):
        t = pd.Timestamp(ts, unit="ms", tz="UTC").tz_convert("America/New_York")
        t18 = pd.Timestamp(year=t.year, month=t.month, day=t.day, hour=18, tz="America/New_York")
        ms = int(round(t18.timestamp() * 1000))
        return ms if t.hour >= 18 else ms - DAY

    times = df["time"].to_numpy()
    latest = tds(int(times[-1]))
    shw = np.array([tds(int(t)) in (latest, latest - DAY) for t in times])
    e5, e8, e13 = np_ema(c, 5), np_ema(c, 8), np_ema(c, 13)
    tp = (h + l + c) / 3.0
    S = dict(pv=np.nan, vv=np.nan, cnt=0, bc=0, ac=0, rl=False, rs=False, pl=False, sh_=np.nan, sl_=np.nan, ps=False, sh2=np.nan, sl2=np.nan)
    vw = np.full(n, np.nan)
    cab = np.zeros(n, bool)
    cbl = np.zeros(n, bool)

    def orders(i, pos, info):
        out = []
        newr = bool(in_rth[i]) and not (i > 0 and in_rth[i - 1])
        if newr:
            S["pv"], S["vv"] = tp[i] * v[i], v[i]
        elif in_rth[i]:
            S["pv"] += tp[i] * v[i]
            S["vv"] += v[i]
        vw[i] = S["pv"] / S["vv"] if S["vv"] > 0 else np.nan
        with np.errstate(invalid="ignore"):
            cab[i] = bool(in_rth[i] and not np.isnan(vw[i]) and c[i] > vw[i])
            cbl[i] = bool(in_rth[i] and not np.isnan(vw[i]) and c[i] < vw[i])
            smr = bool(in_rth[i] and shw[i])
            vwp = vw[i - 1] if i else np.nan
            cp = c[i - 1] if i else np.nan
            xu = i > 0 and c[i] > vw[i] and cp <= vwp
            xd = i > 0 and c[i] < vw[i] and cp >= vwp
            cuc = bool(smr and not np.isnan(vw[i]) and not newr and xu)
            cdc = bool(smr and not np.isnan(vw[i]) and not newr and xd)
            span = l[i] <= vw[i] and h[i] >= vw[i]
            pab, pbl = cp > vwp, cp < vwp
            cuw = bool(smr and not np.isnan(vw[i]) and not newr and span and pbl and c[i] > vw[i])
            cdw = bool(smr and not np.isnan(vw[i]) and not newr and span and pab and c[i] < vw[i])
            cu, cd = (cuc, cdc) if p["cb"] == "Close" else (cuw, cdw)
            if newr:
                S["cnt"] = 0
            elif cu or cd:
                S["cnt"] += 1
            allow = S["cnt"] < p["mx"]
            chop = not allow
            p5, p8, p13 = (e5[i - 1], e8[i - 1], e13[i - 1]) if i else (np.nan,) * 3
            elo = bool((e5[i] > e8[i] and e8[i] > e13[i]) and (e5[i] > p5 and e8[i] > p8 and e13[i] > p13))
            eso = bool((e5[i] < e8[i] and e8[i] < e13[i]) and (e5[i] < p5 and e8[i] < p8 and e13[i] < p13))
            S["bc"] = S["bc"] + 1 if cbl[i] else 0
            S["ac"] = S["ac"] + 1 if cab[i] else 0
            accb, acca = S["bc"] >= 2, S["ac"] >= 2
            cab1 = cab[i - 1] if i else False
            cbl1 = cbl[i - 1] if i else False
            rl2, rs2 = cab[i] and cab1, cbl[i] and cbl1
            rlc = cab[i] and (cp <= vwp)
            rsc = cbl[i] and (cp >= vwp)
            rl = rl2 if p["rm"] == "2-closes" else (cab[i] and (cab1 or rlc))
            rs = rs2 if p["rm"] == "2-closes" else (cbl[i] and (cbl1 or rsc))
            vok = (not p["vc"]) or (v[i] > (v[i - 1] if i else np.nan))
            if newr:
                S["rl"] = S["rs"] = False
            else:
                if accb:
                    S["rl"] = False
                elif rl:
                    S["rl"] = True
                if acca:
                    S["rs"] = False
                elif rs:
                    S["rs"] = True
            buf = p["tb"] * TICK
            tl = bool(in_rth[i] and not np.isnan(vw[i]) and l[i] <= vw[i] + buf)
            ts = bool(in_rth[i] and not np.isnan(vw[i]) and h[i] >= vw[i] - buf)
            hl = bool(shw[i] and allow and in_tr[i] and S["rl"] and elo and tl and c[i] > vw[i] and vok)
            hs = bool(shw[i] and allow and in_tr[i] and S["rs"] and eso and ts and c[i] < vw[i] and vok)
        if newr:
            S.update(pl=False, ps=False, sh_=np.nan, sl_=np.nan, sh2=np.nan, sl2=np.nan)
        if hl:
            S.update(pl=True, sh_=h[i], sl_=l[i])
        if hs:
            S.update(ps=True, sh2=h[i], sl2=l[i])
        if S["pl"] and (accb or not elo or not S["rl"] or not in_tr[i] or chop or not shw[i]):
            S.update(pl=False, sh_=np.nan, sl_=np.nan)
        if S["ps"] and (acca or not eso or not S["rs"] or not in_tr[i] or chop or not shw[i]):
            S.update(ps=False, sh2=np.nan, sl2=np.nan)
        sb = p["sb"] * TICK
        les, lsp = S["sh_"] + TICK, S["sl_"] - sb
        lrt = round((les - lsp) / TICK) if (S["pl"] and not np.isnan(lsp)) else np.nan
        lok = bool(S["pl"] and lrt <= p["ms"] and les > lsp)
        ses, ssp = S["sl2"] - TICK, S["sh2"] + sb
        srt = round((ssp - ses) / TICK) if (S["ps"] and not np.isnan(ssp)) else np.nan
        sok = bool(S["ps"] and srt <= p["ms"] and ssp > ses)
        nn = lambda x: None if np.isnan(x) else x
        if pos == 0 and shw[i] and allow and in_tr[i]:
            if S["pl"] and lok:
                out.append(("entry", "L", 1, les, None))
            if S["ps"] and sok:
                out.append(("entry", "S", -1, ses, None))
        if pos > 0:
            out.append(("exit", "L-exit", "L", nn(lsp), info["ep"] + p["tpt"] * TICK))
        if pos < 0:
            out.append(("exit", "S-exit", "S", nn(ssp), info["ep"] - p["tpt"] * TICK))
        return out

    ref = simulate_ord(o, h, l, c, orders)
    ok, d = compare(run_conversion(TV_ID, df, symbol=sym, tf="1", params=params, strategy_overrides={"commission_value": 0, "slippage": 0, "margin_long": 0, "margin_short": 0}), ref)
    return ok, d, len(ref)


BASE = dict(cb="Close", rm="1-close+hold", vc=True, tb=2, sb=2, ms=40, tpt=40, mx=4)


def check():
    msgs, allok, total = [], True, 0
    relax = {"Require Rising Volume on Hold Candle": False, "VWAP Touch Buffer (ticks)": 15, "Max Stop (ticks) — cancel if larger": 400, "Max NYSE Open VWAP Crosses (no new trades after)": 8}
    rov = dict(vc=False, tb=15, ms=400, mx=8)
    cases = [(101, {}, {}), (102, {}, {}), (103, {}, {}),
             (302, relax, rov), (304, relax, rov), (305, relax, rov), (308, relax, rov),
             (305, {**relax, "Cross Detection": "Wick"}, {**rov, "cb": "Wick"}),
             (308, {**relax, "Reclaim Definition": "2-closes"}, {**rov, "rm": "2-closes"}),
             (304, {**relax, "Require Rising Volume on Hold Candle": True}, {**rov, "vc": True}),
             (305, {**relax, "Max NYSE Open VWAP Crosses (no new trades after)": 2, "Take Profit (ticks)": 60, "Stop Buffer Beyond Setup Extreme (ticks)": 5},
              {**rov, "mx": 2, "tpt": 60, "sb": 5})]
    for seed, params, ov in cases:
        df = bars(7000, seed=seed, freq="1min")
        for k in ("open", "high", "low", "close"):
            df[k] = 100 * (df[k] / 100) ** 0.1
        ok, d, nt = one(df, params, {**BASE, **ov})
        allok &= ok
        total += nt
        msgs.append(d)
    return allok and total > 8, f"{' | '.join(msgs)} (total {total} trades)"
