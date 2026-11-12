"""Independent check — ORB A+ Confluence Strategy (EuXivz7T): 5-minute bars (24 h synthetic, price scaled to ~20000 so that money limits bite) on a US stock chart (trading day from 09:30 New York), 1 contract per trade, market orders at the signal close (process_orders_on_close), margin / commission off. Opening range = high / low of the 09:30-10:00 New York session on Monday-Friday, ready after it ends and cleared by the next trading day; an 8-point confluence score (VWAP / EMA20 / EMA slope side, strong / extreme volume, strong candle, retest or rejection pattern, location) must reach the A level with a location test, trend filters, a confirmation candle and the maximum-extension test; the stop (ATR x multiple) and target (R:R) are measured from the fill price and issued while the trade is open; the stop moves to the entry after the break-even trigger (high / low reached); a trend failure closes. Prop guardrails: simulated equity = account size + equity change; daily loss (reset each trading day), trailing drawdown and evaluation target flags (the last two permanent) lock out new trades and close open ones; entries per day limit. Equity at the bar close = realised P&L + open P&L (1 contract). Uses the pending-order reference broker (simulate_ord, on_close).
Variants: defaults (prop rules on, large account); small account so the daily loss / drawdown / target locks fire, 2 entries per day; prop rules off with loose filters (score 4, no confirmation candle, no EMA slope, inside-range trades off); other volume / ATR settings with break-even and trend exit off."""
import numpy as np
import pandas as pd

from indep import bars, compare, np_atr, np_ema, np_sma, run_conversion, simulate_ord
from pinelib import SymbolInfo

TV_ID = "EuXivz7T"


def one(df, params, p):
    o, h, l, c, v = (df[k].to_numpy() for k in ("open", "high", "low", "close", "volume"))
    n = len(c)
    sym = SymbolInfo.make("NASDAQ:XYZ", "stock", qty_step=1e-9)
    ny = pd.to_datetime(df["time"], unit="ms", utc=True).dt.tz_convert("America/New_York")
    m = (ny.dt.hour * 60 + ny.dt.minute).to_numpy()
    dow = ((ny.dt.dayofweek + 1) % 7 + 1).to_numpy()
    day = (ny.dt.tz_localize(None) - pd.Timedelta(minutes=570)).dt.date.to_numpy()
    inr = (m >= 570) & (m < 600) & np.isin(dow, [2, 3, 4, 5, 6])
    hl3 = (h + l + c) / 3
    vw = np.zeros(n)
    pv = vv = 0.0
    for i in range(n):
        if i == 0 or day[i] != day[i - 1]:
            pv = vv = 0.0
        pv += hl3[i] * v[i]
        vv += v[i]
        vw[i] = pv / vv if vv else np.nan
    ema = np_ema(c, p["emal"])
    atr = np_atr(h, l, c, 14)
    vavg = np_sma(v, 20)
    S = dict(rh=np.nan, rl=np.nan, rdy=False, base=None, ds=np.nan, pk=np.nan, td=0, db=False, ddb=False, tr=False, lr=np.nan, sr=np.nan, lbe=False, sbe=False, pp=None)
    trades: list = []
    nn = lambda x: None if np.isnan(x) else x

    def orders(i, pos, info):
        out = []
        pp, S["pp"] = S["pp"], pos
        nd = i == 0 or day[i] != day[i - 1]
        was = i > 0 and inr[i - 1]
        rs, re = inr[i] and not was, (not inr[i]) and was
        if nd:
            S.update(rh=np.nan, rl=np.nan, rdy=False)
        if rs:
            S.update(rh=h[i], rl=l[i], rdy=False)
        elif inr[i]:
            S["rh"], S["rl"] = max(S["rh"], h[i]), min(S["rl"], l[i])
        if re:
            S["rdy"] = True
        rh, rl = S["rh"], S["rl"]
        mid = (rh + rl) / 2.0 if not (np.isnan(rh) or np.isnan(rl)) else np.nan
        with np.errstate(invalid="ignore"):
            e, vwp, a = ema[i], vw[i], atr[i]
            sv = (not np.isnan(vavg[i])) and v[i] >= vavg[i] * p["vm"]
            xv = (not np.isnan(vavg[i])) and v[i] >= vavg[i] * p["xvm"]
            eb = ema[i - p["sl"]] if i >= p["sl"] else np.nan
            rise, fall = e > eb, e < eb
            ab, be_ = c[i] > e, c[i] < e
            av, bv = c[i] > vwp, c[i] < vwp
            rng = h[i] - l[i]
            body = abs(c[i] - o[i])
            bp = body / rng if rng > 0 else 0.0
            bull, bear = c[i] > o[i], c[i] < o[i]
            sbu = bull and bp >= 0.55 and c[i] >= h[i] - rng * 0.25
            sbe = bear and bp >= 0.55 and c[i] <= l[i] + rng * 0.25
            rdy = S["rdy"]
            ol = rdy and c[i] > rh
            os_ = rdy and c[i] < rl
            ins = rdy and c[i] <= rh and c[i] >= rl
            uh = ins and c[i] > mid
            lh = ins and c[i] < mid
            tol = a * p["tol"]
            lor = rdy and l[i] <= rh + tol and l[i] >= rh - tol and c[i] > rh
            sor = rdy and h[i] >= rl - tol and h[i] <= rl + tol and c[i] < rl
            ler = l[i] <= e + tol and c[i] > e and bull
            ser = h[i] >= e - tol and c[i] < e and bear
            lvr = l[i] <= vwp + tol and c[i] > vwp and bull
            svr = h[i] >= vwp - tol and c[i] < vwp and bear
            llr = ins and l[i] <= rl + tol and c[i] > rl + tol and bull
            shr = ins and h[i] >= rh - tol and c[i] < rh - tol and bear
            c1 = c[i - 1] if i else np.nan
            lmc = ins and c[i] > mid and c1 <= mid and ab and av and sbu
            smc = ins and c[i] < mid and c1 >= mid and be_ and bv and sbe
            noe = abs(c[i] - e) <= a * p["maxext"]
            ls = int(av) + int(ab) + int(rise) + int(sv) + int(sbu) + int(bool(lor or ler or lvr or llr or lmc)) + int(bool(ol or uh or llr)) + int(xv)
            ss = int(bv) + int(be_) + int(fall) + int(sv) + int(sbe) + int(bool(sor or ser or svr or shr or smc)) + int(bool(os_ or lh or shr)) + int(xv)
            lconf = (not p["rconf"]) or sbu
            sconf = (not p["rconf"]) or sbe
            vll = ol or (p["inside"] and ins and (uh or llr or lmc))
            vsl = os_ or (p["inside"] and ins and (lh or shr or smc))
        # simulated equity at this bar's close: realised + open (1 contract)
        realised = sum((t[0]) * (t[4] - t[2]) for t in trades)
        openp = (c[i] - info["ep"]) * pos if pos != 0 else 0.0
        eq = realised + openp
        if S["base"] is None:
            S["base"] = eq
        sim = p["acct"] + eq - S["base"]
        if np.isnan(S["ds"]) or nd:
            S["ds"], S["td"], S["db"] = sim, 0, False
        S["pk"] = sim if np.isnan(S["pk"]) else max(S["pk"], sim)
        if p["prop"]:
            if sim <= S["ds"] - p["acct"] * p["dl"] / 100.0:
                S["db"] = True
            if sim <= S["pk"] - p["acct"] * p["dd"] / 100.0:
                S["ddb"] = True
            if sim >= p["acct"] + p["acct"] * p["tg"] / 100.0:
                S["tr"] = True
        lock = p["prop"] and (S["db"] or S["ddb"] or S["tr"])
        allowed = (not p["prop"]) or ((not lock) and S["td"] < p["maxt"])
        perm = rdy and (not inr[i]) and pos == 0 and allowed and noe
        ltr = ((not p["uv"]) or av) and ((not p["ue"]) or ab) and ((not p["us"]) or rise)
        str_ = ((not p["uv"]) or bv) and ((not p["ue"]) or be_) and ((not p["us"]) or fall)
        lsg = bool(perm and vll and ltr and lconf and ls >= p["mina"])
        ssg = bool(perm and vsl and str_ and sconf and ss >= p["mina"])
        fl, fs = lsg and not ssg, ssg and not lsg
        if fl:
            S["td"] += 1
            out.append(("entry", "Long", 1, None, None))
        if fs:
            S["td"] += 1
            out.append(("entry", "Short", -1, None, None))
        newl = pos > 0 and pp is not None and pp <= 0
        news = pos < 0 and pp is not None and pp >= 0
        if newl:
            S["lr"] = a * p["sm"]
        if news:
            S["sr"] = a * p["sm"]
        if pos == 0:
            S["lr"] = S["sr"] = np.nan
        if pos != 0:
            ep = info["ep"]
        with np.errstate(invalid="ignore"):
            if newl:
                S["lbe"] = False
            if news:
                S["sbe"] = False
            if pos > 0 and p["be"] and not np.isnan(S["lr"]) and h[i] >= ep + S["lr"] * p["bet"]:
                S["lbe"] = True
            if pos < 0 and p["be"] and not np.isnan(S["sr"]) and l[i] <= ep - S["sr"] * p["bet"]:
                S["sbe"] = True
            if pos == 0:
                S["lbe"] = S["sbe"] = False
            if pos > 0 and not np.isnan(S["lr"]):
                base = ep - S["lr"]
                stop = max(base, ep) if S["lbe"] else base
                out.append(("exit", "Long Target/Stop", "Long", nn(stop), nn(ep + S["lr"] * p["rr"])))
            if pos < 0 and not np.isnan(S["sr"]):
                base = ep + S["sr"]
                stop = min(base, ep) if S["sbe"] else base
                out.append(("exit", "Short Target/Stop", "Short", nn(stop), nn(ep - S["sr"] * p["rr"])))
            if p["tx"] and pos > 0 and c[i] < e and c[i] < vwp and bear:
                out.append(("close", "Long"))
            if p["tx"] and pos < 0 and c[i] > e and c[i] > vwp and bull:
                out.append(("close", "Short"))
        if lock and pos != 0:
            out.append(("close_all",))
        return out

    ref = simulate_ord(o, h, l, c, orders, log=trades, on_close=True)
    ok, d = compare(run_conversion(TV_ID, df, symbol=sym, tf="5", params=params, strategy_overrides={"commission_value": 0, "margin_long": 0, "margin_short": 0}), ref)
    return ok and len(ref) > 8, f"{d} (got {len(ref)})"


BASE = dict(emal=20, sl=3, vm=1.25, xvm=1.6, mina=5, tol=0.25, maxext=1.25, rconf=True, inside=True, uv=True, ue=True, us=True, sm=1.25, rr=2.0, be=True, bet=1.0, tx=True,
            prop=True, acct=50000.0, dl=3.0, dd=6.0, tg=6.0, maxt=3)


def check():
    df = bars(30000, seed=777, freq="5min")
    for k in ("open", "high", "low", "close"):
        df[k] = 20000 * (df[k] / 100) ** 0.12
    msgs, allok = [], True
    cases = (({}, {}),
             ({"Prop account size": 8000.0, "Maximum entries per day": 2}, dict(acct=8000.0, maxt=2)),
             ({"Enable prop guardrails": False, "Minimum score for A setup": 4, "Require confirmation candle": False, "Use EMA slope confirmation": False, "Allow A/A+ setups inside ORB": False},
              dict(prop=False, mina=4, rconf=False, us=False, inside=False)),
             ({"Strong volume multiplier": 0.9, "Stop ATR multiplier": 2.0, "Risk-to-reward": 1.5, "Move stop to break-even": False, "Enable trend failure exit": False, "Prop account size": 30000.0,
               "Retest tolerance (ATR)": 0.5},
              dict(vm=0.9, sm=2.0, rr=1.5, be=False, tx=False, acct=30000.0, tol=0.5)))
    for params, ov in cases:
        ok, mm = one(df, params, {**BASE, **ov})
        allok &= ok
        msgs.append(mm)
    return allok, " | ".join(msgs)
