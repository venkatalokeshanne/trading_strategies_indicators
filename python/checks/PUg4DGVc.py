"""Independent check — EMA Stack Strategy, DCA or Single Entry (PUg4DGVc): 15-minute bars (24 h synthetic, price ~100) of a stock-style symbol (New York time), market orders at the next open, the script's own quantities (the dollar inputs are passed as quantities), pyramiding 50, commission / slippage / margin off.
The MA stack (EMA 10 / 25 / 50 / 100 or the variant's types), its hold counter, the optional higher-timeframe MAs and ATR (lookahead off, counter advancing on the first chart bar of each period), the block windows (New York clock), the DCA grid (units / percent / ATR distance, geometric step scale, first / average anchor, auto or manual sizes, cash cap), the average-price take profit or last-DCA level, the manually tracked trailing stop, the MA kill switch and every single-entry exit (MA cross, time stop, ATR / R:R / percent bracket, break-even, trailing) are restated bar by bar.
Uses the quantity-aware bracket reference (indep.simulate_brackets) comparing quantities. Variants: DCA defaults; DCA with percent distances, step scale 1, average anchor, trailing and a block window; DCA last-DCA exit with ATR distances and manual sizes; Single ATR bracket with break-even and trailing on 60-minute MAs; Single R:R swing bracket; Single MA-cross exit with SMA / WMA / VWMA / RMA types; Single time stop and percent bracket."""
import numpy as np
import pandas as pd

from indep import bars, compare_q, np_atr, np_ema, np_periods, np_rma, np_security_lookahead_off, np_sma, np_wma, run_conversion, simulate_brackets
from pinelib import SymbolInfo

TV_ID = "PUg4DGVc"
HOLD_BASE = dict(mode="DCA / Grid", unit=0.01, htf=None, types=("EMA", "EMA", "EMA", "EMA"), hold=0, max_entries=15, base=1000.0, cap=15000.0,
                 dca_mode="Units", d_units=25.0, d_pct=0.25, d_atr=1.0, step=1.12, vol=1.4, anchor="First Entry", adds=True, manual=None,
                 tp_mode="Units", tp_units=100.0, tp_pct=0.10, tp_atr=1.0, trail=False, ta_mode="Units", ta_u=100.0, ta_pct=0.10, ta_atr=1.0,
                 td_mode="Units", td_u=50.0, td_pct=0.05, td_atr=0.5, exit_type="BE TP (Current)", no_kill=False, last_mode="Units", last_u=100.0, last_pct=0.10,
                 single="ATR Bracket", atr_stop=1.5, atr_tp=3.0, rr_method="ATR", rr_atr=1.5, swing=20, buf=0.0, rr=2.0, stop_pct=1.0, tp_pct_s=2.0, tstop=50,
                 be=False, be_mode="ATR", be_u=50.0, be_pct=0.5, be_atr=1.0, be_off=0.0, se_trail=False, sa_mode="ATR", sa_u=50.0, sa_pct=0.5, sa_atr=1.0,
                 sd_mode="ATR", sd_u=25.0, sd_pct=0.25, sd_atr=0.5, win=None, block_dca=False, atr_len=14)


def ma(x, v, n, typ):
    if typ == "SMA":
        return np_sma(x, n)
    if typ == "EMA":
        return np_ema(x, n)
    if typ == "SMMA (RMA)":
        return np_rma(x, n)
    if typ == "WMA":
        return np_wma(x, n)
    pv = np_sma(x * v, n)
    vs = np_sma(v, n)
    with np.errstate(divide="ignore", invalid="ignore"):
        return pv / vs


def dist(mode, anchor, unit, units, pct, atr, m):
    return units * unit if mode == "Units" else anchor * (pct / 100.0) if mode == "Percent" else atr * m if mode == "ATR" else np.nan


def rolling(x, n, fn):
    out = np.full(len(x), np.nan)
    for i in range(n - 1, len(x)):
        out[i] = fn(x[i - n + 1:i + 1])
    return out


def one(df, params, p):
    p = {**HOLD_BASE, **p}
    o, h, l, c, v = (df[k].to_numpy() for k in ("open", "high", "low", "close", "volume"))
    n = len(c)
    loc = pd.to_datetime(df["time"], unit="ms", utc=True).dt.tz_convert("America/New_York")
    mins = (loc.dt.hour * 60 + loc.dt.minute).to_numpy()
    if p["htf"] is None:
        mas = [ma(c, v, ln, t) for ln, t in zip((10, 25, 50, 100), p["types"])]
        atr = np_atr(h, l, c, p["atr_len"])
        upd = np.full(n, True)
    else:
        pid, last_of = np_periods(df, p["htf"])
        g = pd.DataFrame({"pid": pid, "h": h, "l": l, "c": c, "v": v}).groupby("pid")
        hc, hh, hl, hv = g["c"].last().to_numpy(), g["h"].max().to_numpy(), g["l"].min().to_numpy(), g["v"].sum().to_numpy()
        mas = [np_security_lookahead_off(ma(hc, hv, ln, t), pid, last_of) for ln, t in zip((10, 25, 50, 100), p["types"])]
        atr = np_security_lookahead_off(np_atr(hh, hl, hc, p["atr_len"]), pid, last_of)
        upd = np.r_[False, pid[1:] != pid[:-1]]
    m1, m2, m3, m4 = mas
    sw_low, sw_high = rolling(l, p["swing"], np.min), rolling(h, p["swing"], np.max)
    dca = p["mode"] == "DCA / Grid"
    unit = p["unit"]

    def in_win(i):
        if not p["win"]:
            return False
        for st, en in p["win"]:
            now = int(mins[i])
            if (st <= now <= en) if st <= en else (now >= st or now <= en):
                return True
        return False

    S = dict(cl=0, cs=0, fe=np.nan, ld=np.nan, es=0, pc=0.0, te=np.nan, ta=False, bt=0, ba=False, se=np.nan, sa=False, prev=None)

    def orders(i, info):
        pos = info["pos"]
        avg = info["avg"]
        pp = S["prev"]
        S["prev"] = pos
        a = atr[i]
        out = []
        with np.errstate(invalid="ignore"):
            sl_ = bool(m1[i] > m2[i] and m2[i] > m3[i] and m3[i] > m4[i])
            ss_ = bool(m1[i] < m2[i] and m2[i] < m3[i] and m3[i] < m4[i])
        if upd[i]:
            S["cl"] = S["cl"] + 1 if sl_ else 0
            S["cs"] = S["cs"] + 1 if ss_ else 0
        rl, rs = S["cl"] >= p["hold"] + 1, S["cs"] >= p["hold"] + 1
        in_l, in_s, flat = pos > 0, pos < 0, pos == 0
        new_open = pos != 0 and pp is not None and pp == 0
        base_eff = p["manual"][0] if p["manual"] else p["base"]
        if new_open:
            S["fe"], S["ld"], S["es"], S["pc"] = avg, avg, 1, base_eff
        if flat:
            S["fe"] = S["ld"] = np.nan
            S["es"], S["pc"] = 0, 0.0
        block = in_win(i)
        with np.errstate(invalid="ignore"):
            cu = bool(i > 0 and m1[i] > m2[i] and m1[i - 1] <= m2[i - 1])
            cd = bool(i > 0 and m1[i] < m2[i] and m1[i - 1] >= m2[i - 1])
            kill_l = bool(in_l and m1[i] < m2[i])
            kill_s = bool(in_s and m1[i] > m2[i])
        if upd[i] and flat and rl and not block and base_eff > 0:
            out.append(("entry", "Long", 1, base_eff))
        if upd[i] and flat and rs and not block and base_eff > 0:
            out.append(("entry", "Short", -1, base_eff))
        nxt = np.nan
        if dca:
            anchor = S["fe"] if p["anchor"] == "First Entry" else avg
            dca_now = (not block) if p["block_dca"] else True
            can_add = p["adds"] and dca_now and pos != 0 and S["es"] >= 1 and S["es"] < p["max_entries"] and not np.isnan(anchor)
            if can_add:
                base = dist(p["dca_mode"], anchor, unit, p["d_units"], p["d_pct"], a, p["d_atr"])
                k = S["es"]
                d = base * k if p["step"] == 1.0 else base * (p["step"] ** k - 1.0) / (p["step"] - 1.0)
                nxt = anchor - d if in_l else anchor + d
            touch = can_add and not np.isnan(nxt) and ((in_l and l[i] <= nxt) or (in_s and h[i] >= nxt))
            raw = (p["manual"][S["es"]] if S["es"] < 25 else 0.0) if p["manual"] else p["base"] * p["vol"] ** S["es"]
            cash = max(0.0, min(p["cap"] - S["pc"], raw))
            if touch and cash > 0:
                S["ld"] = nxt
                out.append(("entry", "Long" if in_l else "Short", 1 if in_l else -1, cash))
                S["es"] += 1
                S["pc"] += cash
        tpo = dist(p["tp_mode"], avg, unit, p["tp_units"], p["tp_pct"], a, p["tp_atr"])
        tp_dca = avg + tpo if in_l else avg - tpo if in_s else np.nan
        reached = dca and pos != 0 and S["es"] >= p["max_entries"] and not np.isnan(S["ld"])
        lo = p["last_u"] * unit if p["last_mode"] == "Units" else S["ld"] * (p["last_pct"] / 100.0)
        tp_last = (S["ld"] + lo if in_l else S["ld"] - lo) if reached else np.nan
        if new_open or pos == 0:
            S["te"], S["ta"] = np.nan, False
        act = dist(p["ta_mode"], avg, unit, p["ta_u"], p["ta_pct"], a, p["ta_atr"])
        tdist = dist(p["td_mode"], avg, unit, p["td_u"], p["td_pct"], a, p["td_atr"])
        if p["trail"] and pos != 0 and dca:
            if in_l:
                S["te"] = h[i] if np.isnan(S["te"]) else max(S["te"], h[i])
                if not S["ta"] and (S["te"] - avg) >= act:
                    S["ta"] = True
            if in_s:
                S["te"] = l[i] if np.isnan(S["te"]) else min(S["te"], l[i])
                if not S["ta"] and (avg - S["te"]) >= act:
                    S["ta"] = True
        tstop = (S["te"] - tdist if in_l else S["te"] + tdist) if (p["trail"] and S["ta"] and pos != 0 and dca) else np.nan
        if new_open:
            S["bt"] = 0
        if pos != 0:
            S["bt"] += 1
        if pos == 0:
            S["bt"] = 0
        if p["rr_method"] == "ATR":
            rr_stop = avg - a * p["rr_atr"] if in_l else avg + a * p["rr_atr"]
        else:
            rr_stop = sw_low[i] - p["buf"] * unit if in_l else sw_high[i] + p["buf"] * unit
        risk = avg - rr_stop if in_l else rr_stop - avg if in_s else np.nan
        rr_tp = avg + risk * p["rr"] if in_l else avg - risk * p["rr"] if in_s else np.nan
        a_stop = avg - a * p["atr_stop"] if in_l else avg + a * p["atr_stop"] if in_s else np.nan
        a_tp = avg + a * p["atr_tp"] if in_l else avg - a * p["atr_tp"] if in_s else np.nan
        p_stop = avg * (1 - p["stop_pct"] / 100) if in_l else avg * (1 + p["stop_pct"] / 100) if in_s else np.nan
        p_tp = avg * (1 + p["tp_pct_s"] / 100) if in_l else avg * (1 - p["tp_pct_s"] / 100) if in_s else np.nan
        bet = dist(p["be_mode"], avg, unit, p["be_u"], p["be_pct"], a, p["be_atr"])
        if new_open or pos == 0:
            S["ba"] = False
        if not dca and p["be"] and pos != 0:
            if in_l and not S["ba"] and (h[i] - avg) >= bet:
                S["ba"] = True
            if in_s and not S["ba"] and (avg - l[i]) >= bet:
                S["ba"] = True
        be_stop = (avg + p["be_off"] * unit if in_l else avg - p["be_off"] * unit) if (S["ba"] and pos != 0) else np.nan
        if new_open or pos == 0:
            S["se"], S["sa"] = np.nan, False
        sact = dist(p["sa_mode"], avg, unit, p["sa_u"], p["sa_pct"], a, p["sa_atr"])
        sdist = dist(p["sd_mode"], avg, unit, p["sd_u"], p["sd_pct"], a, p["sd_atr"])
        if not dca and p["se_trail"] and pos != 0:
            if in_l:
                S["se"] = h[i] if np.isnan(S["se"]) else max(S["se"], h[i])
                if not S["sa"] and (S["se"] - avg) >= sact:
                    S["sa"] = True
            if in_s:
                S["se"] = l[i] if np.isnan(S["se"]) else min(S["se"], l[i])
                if not S["sa"] and (avg - S["se"]) >= sact:
                    S["sa"] = True
        se_stop = (S["se"] - sdist if in_l else S["se"] + sdist) if (not dca and p["se_trail"] and S["sa"] and pos != 0) else np.nan
        nz = lambda x: None if x is None or np.isnan(x) else float(x)
        if dca:
            lim = tp_last if p["exit_type"] == "After Last DCA (Offset)" else tp_dca
            stop = tstop if (p["trail"] and S["ta"]) else np.nan
            if in_l:
                out.append(("exit", "X", "Long", None, nz(stop), nz(lim)))
            if in_s:
                out.append(("exit", "X", "Short", None, nz(stop), nz(lim)))
            if (not p["no_kill"]) and p["exit_type"] != "After Last DCA (Offset)":
                if kill_l:
                    out.append(("close", "Long"))
                if kill_s:
                    out.append(("close", "Short"))
        elif pos != 0:
            fid = "Long" if in_l else "Short"
            if p["se_trail"] and S["sa"] and not np.isnan(se_stop):
                out.append(("exit", "SE-T", fid, None, float(se_stop), None))
            if p["single"] == "MA Cross":
                if in_l and cd:
                    out.append(("close", "Long"))
                if in_s and cu:
                    out.append(("close", "Short"))
            if p["single"] == "Time Stop" and S["bt"] >= p["tstop"]:
                out.append(("close", fid))
            br = {"ATR Bracket": (a_stop, a_tp), "R:R Bracket": (rr_stop, rr_tp), "Percent Bracket": (p_stop, p_tp)}.get(p["single"])
            if br:
                sp, lp = br
                if p["be"] and S["ba"] and not np.isnan(be_stop):
                    sp = max(sp, be_stop) if in_l else min(sp, be_stop)
                out.append(("exit", "SE-B", fid, None, nz(sp), nz(lp)))
        return out

    ref = simulate_brackets(o, h, l, c, orders, pyramiding=50, tick=0.01, qty_step=1e-9)
    sym = SymbolInfo.make("NASDAQ:XYZ", "stock", qty_step=1e-9)
    ov = {"margin_long": 0, "margin_short": 0, "commission_value": 0, "slippage": 0}
    ok, d = compare_q(run_conversion(TV_ID, df, symbol=sym, tf="15", params=params, strategy_overrides=ov), ref)
    return ok and len(ref) > 12, f"{d} (got {len(ref)})"


def check():
    df = bars(24000, seed=941, freq="15min")
    for k in ("open", "high", "low", "close"):
        df[k] = 100 * (df[k] / 100) ** 0.1
    msgs, allok = [], True
    single = {"Trading mode": "Single Entry"}
    cases = (
        ({}, {}),
        ({"DCA distance mode": "Percent", "Step scale (spacing growth)": 1.0, "DCA anchor mode": "Average Entry", "Enable DCA trailing stop (default OFF)": True, "DCA trail activation mode": "Percent", "DCA trail distance mode": "Percent",
          "Block window #1": True, "Start": "16:45", "End": "18:15", "Also block DCA adds during windows": True, "DCA take profit mode (Avg BE ± offset)": "Percent", "Enter after stack holds X confirmed closes": 2},
         dict(dca_mode="Percent", step=1.0, anchor="Average Entry", trail=True, ta_mode="Percent", td_mode="Percent", win=[(16 * 60 + 45, 18 * 60 + 15)], block_dca=True, tp_mode="Percent", hold=2)),
        ({"DCA exit type": "After Last DCA (Offset)", "Max total entries (1..25)": 4, "DCA distance mode": "ATR", "DCA sizing mode": "Manual Ladder", "Entry #1 ($)": 700, "Entry #2 ($)": 900, "Entry #3 ($)": 1300, "Entry #4 ($)": 400,
          "Last DCA exit offset mode": "Percent", "Base interval (ATR mult)": 0.8, "Max total position cash ($ cap)": 3000},
         dict(exit_type="After Last DCA (Offset)", max_entries=4, dca_mode="ATR", manual=[700.0, 900.0, 1300.0, 400.0] + [1000.0] * 21, last_mode="Percent", d_atr=0.8, cap=3000.0)),
        ({**single, "MA logic timeframe": "Higher TF", "Higher TF": "60", "Enable Break-even move (Single mode)": True, "Enable Single Entry Trailing Stop": True},
         dict(mode="Single Entry", htf=60, be=True, se_trail=True)),
        ({**single, "Single entry exit type (Single mode only)": "R:R Bracket", "R:R Stop Method": "Swing", "Swing Buffer (Units)": 5.0},
         dict(mode="Single Entry", single="R:R Bracket", rr_method="Swing", buf=5.0)),
        ({**single, "Single entry exit type (Single mode only)": "MA Cross", "MA #1 Type": "SMA", "MA #2 Type": "WMA", "": "VWMA"},
         dict(mode="Single Entry", single="MA Cross", types=("SMA", "WMA", "EMA", "EMA"))),
        ({**single, "Single entry exit type (Single mode only)": "Percent Bracket", "Stop (%)": 0.4, "Take Profit (%)": 0.9, "Enable Break-even move (Single mode)": True, "BE Trigger Mode": "Percent", "BE Trigger (%)": 0.3, "BE Stop Offset (Units)": 3.0},
         dict(mode="Single Entry", single="Percent Bracket", stop_pct=0.4, tp_pct_s=0.9, be=True, be_mode="Percent", be_pct=0.3, be_off=3.0)),
        ({**single, "Single entry exit type (Single mode only)": "Time Stop", "Time Stop (bars)": 12}, dict(mode="Single Entry", single="Time Stop", tstop=12)),
    )
    for params, ov in cases:
        ok, m = one(df, params, ov)
        allok &= ok
        msgs.append(m)
    return allok, " | ".join(msgs)
