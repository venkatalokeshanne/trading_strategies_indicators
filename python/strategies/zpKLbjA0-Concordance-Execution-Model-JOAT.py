"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : Concordance Execution Model [JOAT]
Author       : officialjackofalltrades
Source URL   : https://www.tradingview.com/script/zpKLbjA0-Concordance-Execution-Model-JOAT
Pine version : v6
Licence      : Mozilla Public License 2.0
Type         : strategy
Status       : FULL
Converted    : 2026-10-29 by Claude (pine-to-python skill)

Line-for-line translation (market orders at the next open). A long / short score (0-100) adds structure break, higher-timeframe EMA bias, a vote of four ALMA-band trend states (15m / 60m / 240m / D, each on the previous bar's close, request.security lookahead off),
an alpha-beta-gamma kinetic filter, regression confidence (R-squared of the 80-bar linreg) with slope, delta pressure and an EMA stack; an entry needs the score >= 72, delta beyond its gate, relative volume and a cooldown (entries reverse).
Exits: a stop (ATR, ratcheted by an ATR trail) and an ATR target re-issued every bar, a time stop, and a close when the structure or the opposing score invalidates the trade.
Deviations from the original: the ALMA-band function and the previous-EMA request keep their per-bar state in plain Python objects inside the request.security call (pinelib runs the expression on its own bars; script-level histories belong to the chart).
Not carried over: plots, the regime fill, bar colours, signal shapes, the panel and the alert conditions (display only).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, div, na, nz, pmath, ta


def clamp(x, lo, hi):
    return pmath.max(lo, pmath.min(hi, x))


def safe_div(n, d):
    return 0.0 if d == 0.0 else div(n, d)


def make_alma_band(o):
    """f_alma_sig for one request.security call: the function's upper / lower / dir and src history live in this closure."""
    state = dict(upper=NA, lower=NA, src1=NA, dir=0)

    def band(v):
        src = float(v.close[1])
        alma = ta.alma(src, o.alma_len, 0.85, 4.0)
        dev = ta.stdev(src, o.sd_len)
        upper = alma + o.alma_factor * dev
        lower = alma - o.alma_factor * dev
        prev_upper = nz(state["upper"], upper)
        prev_lower = nz(state["lower"], lower)
        upper = upper if (upper < prev_upper or state["src1"] > prev_upper) else prev_upper
        lower = lower if (lower > prev_lower or state["src1"] < prev_lower) else prev_lower
        if src > upper:
            state["dir"] = 1
        elif src < lower:
            state["dir"] = -1
        state["upper"], state["lower"], state["src1"] = upper, lower, src
        return state["dir"], alma
    return band


def make_prev_ema():
    """ta.ema(close, 50)[1] on the requested bars."""
    state = dict(prev=NA)

    def prev_ema(v):
        e = ta.ema(v.close, 50)
        out = state["prev"]
        state["prev"] = e
        return out
    return prev_ema


class ConcordanceExecutionModel(Script):
    TITLE = "Concordance Execution Model [JOAT]"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(pyramiding=0, initial_capital=100000, commission_type="percent", commission_value=0.02, slippage=2,
                    default_qty_type="percent_of_equity", default_qty_value=10)
    SOURCE = {"id": "zpKLbjA0", "author": "officialjackofalltrades", "licence": "Mozilla Public License 2.0",
              "url": "https://www.tradingview.com/script/zpKLbjA0-Concordance-Execution-Model-JOAT"}

    def init(self):
        i = self.input
        g = "Regime"
        self.swing_len = i.int(5, "Structure pivot length", minval=2, maxval=25, group=g)
        self.htf = i.timeframe("240", "Bias HTF", group=g)
        self.alma_len = i.int(6, "ALMA length", minval=2, maxval=50, group=g)
        self.sd_len = i.int(4, "Deviation length", minval=2, maxval=50, group=g)
        self.alma_factor = i.float(1.0, "ALMA deviation factor", minval=0.1, maxval=5, step=0.05, group=g)
        self.reg_len = i.int(80, "Regression confidence window", minval=25, maxval=200, group=g)
        self.min_r2 = i.float(0.45, "Minimum confidence", minval=0.10, maxval=0.95, step=0.05, group=g)
        g = "Entry"
        self.delta_gate = i.float(0.03, "Delta pressure gate", minval=0.0, step=0.01, group=g)
        self.rvol_gate = i.float(1.05, "Relative volume gate", minval=0.1, step=0.05, group=g)
        self.cooldown_bars = i.int(8, "Entry cooldown", minval=0, maxval=100, group=g)
        g = "Risk"
        self.atr_len = i.int(14, "ATR length", minval=5, maxval=100, group=g)
        self.stop_atr = i.float(1.6, "Stop ATR", minval=0.5, maxval=8, step=0.1, group=g)
        self.target_atr = i.float(2.8, "Target ATR", minval=0.5, maxval=12, step=0.1, group=g)
        self.use_trail = i.bool(True, "Use trailing stop", group=g)
        self.trail_atr = i.float(1.8, "Trail ATR", minval=0.5, maxval=8, step=0.1, group=g)
        self.time_stop = i.int(80, "Time stop bars", minval=5, maxval=500, group=g)
        self.band15 = make_alma_band(self)
        self.band60 = make_alma_band(self)
        self.band240 = make_alma_band(self)
        self.band_d = make_alma_band(self)
        self.prev_ema = make_prev_ema()
        self.last_ph = NA
        self.last_pl = NA
        self.structure = 0
        self.x_est = NA
        self.v_est = 0.0
        self.a_est = 0.0
        self.last_entry_bar = NA
        self.long_trail = NA
        self.short_trail = NA
        self.entry_bar = NA
        self.prev_pos = 0.0

    def on_bar(self):
        st = self.strategy
        close, high, low, volume = self.close, self.high, self.low, self.volume
        mintick = self.syminfo.mintick
        atr = ta.atr(self.atr_len)
        ema50 = ta.ema(close, 50)
        ema200 = ta.ema(close, 200)
        htf_close = self.security(None, self.htf, lambda v: v.close[1], lookahead=False)
        htf_ema = self.security(None, self.htf, self.prev_ema, lookahead=False)
        htf_bull = htf_close > htf_ema
        htf_bear = htf_close < htf_ema
        alma_sig15, _ = self.security(None, "15", self.band15, lookahead=False)
        alma_sig60, _ = self.security(None, "60", self.band60, lookahead=False)
        alma_sig240, _ = self.security(None, "240", self.band240, lookahead=False)
        alma_sig_d, _ = self.security(None, "D", self.band_d, lookahead=False)
        alma_vote = alma_sig15 + alma_sig60 + alma_sig240 + alma_sig_d
        alma_bull = alma_vote >= 2
        alma_bear = alma_vote <= -2
        ph = ta.pivothigh(high, self.swing_len, self.swing_len)
        pl = ta.pivotlow(low, self.swing_len, self.swing_len)
        if not na(ph):
            self.last_ph = float(ph)
        if not na(pl):
            self.last_pl = float(pl)
        bull_break = (not na(self.last_ph)) and close > self.last_ph + atr * 0.05
        bear_break = (not na(self.last_pl)) and close < self.last_pl - atr * 0.05
        if bull_break:
            self.structure = 1
            self.last_ph = NA
        if bear_break:
            self.structure = -1
            self.last_pl = NA
        rng = pmath.max(high - low, mintick)
        vol0 = nz(volume, 0)
        delta = div(ta.ema((div(close - low, rng) - div(high - close, rng)) * vol0, 7), pmath.max(ta.ema(vol0, 7), 1))
        rvol = div(vol0, pmath.max(ta.sma(vol0, 20), 1))
        c_h = self.H("close")
        close_1 = c_h[1]
        c_h.set(close)
        obv = ta.cum(volume if close > close_1 else (-volume if close < close_1 else 0))
        obv_ma = ta.sma(obv, 20)
        delta_score = 50 + (12 if delta > 0 else -12) + (8 if obv > obv_ma else -8) + (8 if close > ta.vwap(self.hlc3) else -8) + (6 if rvol > self.rvol_gate else -3)
        delta_score = clamp(delta_score, 0, 100)
        lam = 0.85
        alpha = 1.0 - lam ** 3
        beta = 1.5 * (1.0 - lam) ** 2 * (1.0 + lam)
        gamma_gain = 0.5 * (1.0 - lam) ** 3
        if na(self.x_est):
            self.x_est = float(close)
        x_pred = self.x_est + self.v_est + 0.5 * self.a_est
        v_pred = self.v_est + self.a_est
        residual = close - x_pred
        boost = 1.8 if div(abs(residual), pmath.max(atr, mintick)) > 3 else 1.0
        self.x_est = x_pred + alpha * boost * residual
        self.v_est = v_pred + beta * boost * residual
        self.a_est = self.a_est + gamma_gain * boost * residual
        kin_trend = safe_div(self.v_est, pmath.max(atr, mintick))
        kinetic_bull = kin_trend > 0.10 and self.a_est >= 0
        kinetic_bear = kin_trend < -0.10 and self.a_est <= 0
        lr = ta.linreg(close, self.reg_len, 0)
        err = close - lr
        var_price = ta.variance(close, self.reg_len)
        var_err = ta.variance(err, self.reg_len)
        r2 = clamp(1.0 - safe_div(var_err, var_price), 0, 1) if var_price > 0 else 0
        lr_h = self.H("lr")
        lr_5 = lr_h[5]
        lr_h.set(lr)
        lr_slope = lr - lr_5
        reg_bull = r2 >= self.min_r2 and lr_slope > 0
        reg_bear = r2 >= self.min_r2 and lr_slope < 0
        volatility_ok = div(atr, close) > 0.001
        stack_bull = close > ema50 and ema50 > ema200
        stack_bear = close < ema50 and ema50 < ema200
        long_score = clamp((18 if self.structure == 1 else 0) + (12 if htf_bull else 0) + (18 if alma_bull else 0) + (16 if kinetic_bull else 0)
                           + (16 if reg_bull else 0) + (12 if delta_score > 55 else 0) + (8 if stack_bull else 0), 0, 100)
        short_score = clamp((18 if self.structure == -1 else 0) + (12 if htf_bear else 0) + (18 if alma_bear else 0) + (16 if kinetic_bear else 0)
                            + (16 if reg_bear else 0) + (12 if delta_score < 45 else 0) + (8 if stack_bear else 0), 0, 100)
        cooled = na(self.last_entry_bar) or self.bar_index - self.last_entry_bar >= self.cooldown_bars
        long_entry = bool(cooled and volatility_ok and long_score >= 72 and delta > self.delta_gate and rvol >= self.rvol_gate)
        short_entry = bool(cooled and volatility_ok and short_score >= 72 and delta < -self.delta_gate and rvol >= self.rvol_gate)
        pos = st.position_size
        if long_entry and pos <= 0:
            st.entry("CEM Long", st.long)
            self.last_entry_bar = self.bar_index
        if short_entry and pos >= 0:
            st.entry("CEM Short", st.short)
            self.last_entry_bar = self.bar_index
        if pos > 0:
            cand_long = close - atr * self.trail_atr
            self.long_trail = cand_long if self.prev_pos <= 0 else pmath.max(nz(self.long_trail, cand_long), cand_long)
        else:
            self.long_trail = NA
        if pos < 0:
            cand_short = close + atr * self.trail_atr
            self.short_trail = cand_short if self.prev_pos >= 0 else pmath.min(nz(self.short_trail, cand_short), cand_short)
        else:
            self.short_trail = NA
        avg = st.position_avg_price
        long_stop = pmath.max(avg - atr * self.stop_atr, self.long_trail) if (self.use_trail and not na(self.long_trail)) else avg - atr * self.stop_atr
        long_target = avg + atr * self.target_atr
        short_stop = pmath.min(avg + atr * self.stop_atr, self.short_trail) if (self.use_trail and not na(self.short_trail)) else avg + atr * self.stop_atr
        short_target = avg - atr * self.target_atr
        if pos > 0:
            st.exit("CEM Long Exit", "CEM Long", stop=long_stop, limit=long_target)
        if pos < 0:
            st.exit("CEM Short Exit", "CEM Short", stop=short_stop, limit=short_target)
        if pos != 0 and self.prev_pos == 0:
            self.entry_bar = self.bar_index
        if pos == 0:
            self.entry_bar = NA
        time_exit = (not na(self.entry_bar)) and self.bar_index - self.entry_bar >= self.time_stop
        invalidate_long = pos > 0 and (self.structure == -1 or short_score > long_score + 12)
        invalidate_short = pos < 0 and (self.structure == 1 or long_score > short_score + 12)
        if pos > 0 and time_exit:
            st.close("CEM Long", comment="Time stop")
        if pos > 0 and invalidate_long:
            st.close("CEM Long", comment="Structure invalidation")
        if pos < 0 and time_exit:
            st.close("CEM Short", comment="Time stop")
        if pos < 0 and invalidate_short:
            st.close("CEM Short", comment="Structure invalidation")
        self.prev_pos = pos
