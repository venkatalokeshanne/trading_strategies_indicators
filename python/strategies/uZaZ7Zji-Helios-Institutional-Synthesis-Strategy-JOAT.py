"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : Helios Institutional Synthesis Strategy [JOAT]
Author       : officialjackofalltrades
Source URL   : https://www.tradingview.com/script/uZaZ7Zji-Helios-Institutional-Synthesis-Strategy-JOAT
Pine version : v6
Licence      : Mozilla Public License 2.0
Type         : strategy
Status       : FULL
Converted    : 2026-10-29 by Claude (pine-to-python skill)

Line-for-line translation (orders processed at the bar close, process_orders_on_close). An adaptive baseline (EMA blended with a KAMA by the efficiency ratio, smoothed) defines the regime together with ADX and an ATR-based volatility score; an 8-point confluence score
(regime, VWAP side, premium / discount of the 120-bar range, momentum + volume pressure, volatility gate, liquidity sweeps incl. the previous day's high / low (request.security, lookahead off), VWAP / channel / squeeze triggers, 60-minute EMA bias)
plus a trigger (baseline / VWAP cross, sweep, bounce) opens a long / short (reversing) when the cooldown, the daily equity guard and the minimum planned R multiple allow it; the position is sized from the stop distance (risk %), has an ATR stop that trails, an ATR target,
a regime-flip close, a time guard and a daily-guard close.
Deviations from the original: none.
Not carried over: plots, fills, trade boxes, risk rails, the dashboard and data-window exports (display only).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, div, na, nz, pmath, ta


def make_prev_ema(length):
    """ta.ema(close, length)[1] on the requested bars."""
    state = dict(prev=NA)

    def prev_ema(v):
        e = ta.ema(v.close, length)
        out = state["prev"]
        state["prev"] = e
        return out
    return prev_ema


def f_clamp(x, lo, hi):
    return pmath.max(lo, pmath.min(hi, x))


def f_div(num, den):
    return div(num, den) if den != 0.0 else 0.0


def f_tanh(x):
    ex = pmath.exp(2.0 * x)
    return f_div(ex - 1.0, ex + 1.0)


class HeliosInstitutionalSynthesis(Script):
    TITLE = "Helios Institutional Synthesis Strategy [JOAT]"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(pyramiding=0, initial_capital=100000, commission_type="percent", commission_value=0.01, slippage=1, process_orders_on_close=True)
    SOURCE = {"id": "uZaZ7Zji", "author": "officialjackofalltrades", "licence": "Mozilla Public License 2.0",
              "url": "https://www.tradingview.com/script/uZaZ7Zji-Helios-Institutional-Synthesis-Strategy-JOAT"}

    def init(self):
        i = self.input
        g = "Core Engine"
        self.baseline_len = i.int(34, "Adaptive Baseline Length", minval=5, maxval=300, group=g)
        self.kama_len = i.int(14, "Efficiency Lookback", minval=2, maxval=100, group=g)
        self.fast_len = i.int(2, "Fast Period", minval=2, maxval=20, group=g)
        self.slow_len = i.int(30, "Slow Period", minval=3, maxval=100, group=g)
        self.baseline_smo = i.int(5, "Baseline Smoothing", minval=1, maxval=50, group=g)
        self.atr_len = i.int(14, "ATR Length", minval=2, maxval=100, group=g)
        self.adx_len = i.int(14, "ADX / DMI Length", minval=2, maxval=100, group=g)
        self.vol_len = i.int(50, "Volatility Window", minval=10, maxval=300, group=g)
        self.anchor_len = i.int(120, "Institutional Anchor Length", minval=20, maxval=500, group=g)
        self.channel_len = i.int(80, "Channel Memory", minval=20, maxval=400, group=g)
        self.squeeze_len = i.int(20, "Squeeze Length", minval=5, maxval=100, group=g)
        self.htf_tf = i.timeframe("60", "Confirmation Timeframe", group=g)
        g = "Filters"
        self.use_longs = i.bool(True, "Enable Longs", group=g)
        self.use_shorts = i.bool(True, "Enable Shorts", group=g)
        self.trade_session = i.session("0930-1600", "Trade Session", group=g)
        self.use_session = i.bool(False, "Restrict to Session", group=g)
        self.min_score = i.int(4, "Min Confluence Score", minval=2, maxval=8, group=g)
        self.cooldown_bars = i.int(4, "Cooldown Bars", minval=0, maxval=100, group=g)
        self.avoid_compression = i.bool(False, "Avoid Fresh Compression", group=g)
        self.min_vol_score = i.float(15.0, "Minimum Volatility Score", minval=0.0, maxval=100.0, step=1.0, group=g)
        self.max_vol_score = i.float(95.0, "Maximum Volatility Score", minval=1.0, maxval=100.0, step=1.0, group=g)
        g = "Risk Controls"
        self.risk_pct = i.float(1.0, "Risk % per Trade", minval=0.1, maxval=10.0, step=0.1, group=g)
        self.stop_atr_mult = i.float(1.8, "ATR Stop Multiple", minval=0.5, maxval=10.0, step=0.1, group=g)
        self.tp_atr_mult = i.float(2.8, "ATR Target Multiple", minval=0.5, maxval=15.0, step=0.1, group=g)
        self.trail_atr_mult = i.float(1.35, "ATR Trail Multiple", minval=0.25, maxval=8.0, step=0.05, group=g)
        self.min_rr = i.float(1.00, "Minimum Planned R Multiple", minval=0.5, maxval=6.0, step=0.05, group=g)
        self.max_atr_percent = i.float(4.5, "Max ATR % of Price", minval=0.1, maxval=25.0, step=0.1, group=g)
        self.max_day_loss_pct = i.float(3.0, "Daily Equity Guard %", minval=0.0, maxval=20.0, step=0.1, group=g)
        self.max_hold_bars = i.int(120, "Max Hold Bars", minval=1, maxval=2000, group=g)
        self.max_qty = i.float(100000.0, "Max Position Qty", minval=0.0, group=g)
        self.min_qty = i.float(0.0, "Min Position Qty", minval=0.0, group=g)
        self.close_on_flip = i.bool(True, "Close On Regime Flip", group=g)
        self.htf_fast_prev = make_prev_ema(21)
        self.htf_slow_prev = make_prev_ema(55)
        self.kama_line = NA
        self.last_entry_bar = NA
        self.day_start_equity = NA
        self.active_entry = NA
        self.active_stop = NA
        self.active_target = NA
        self.active_entry_bar = NA
        self.prev_pos = NA

    def f_qty(self, entry_price, stop_price, equity, risk_percent, cap_qty, floor_qty):
        stop_dist = abs(entry_price - stop_price)
        risk_cash = equity * risk_percent * 0.01
        unit_risk = pmath.max(stop_dist * self.syminfo.pointvalue, self.syminfo.mintick)
        raw_qty = div(risk_cash, unit_risk) if stop_dist > self.syminfo.mintick else 0.0
        return pmath.max(floor_qty, pmath.min(raw_qty, cap_qty))

    def on_bar(self):
        st = self.strategy
        close, open_, high, low, volume = self.close, self.open, self.high, self.low, self.volume
        mintick = self.syminfo.mintick
        atr_val = ta.atr(self.atr_len)
        _, _, adx_val = ta.dmi(self.adx_len, self.adx_len)
        atr_base = ta.sma(atr_val, self.vol_len)
        atr_dev = ta.stdev(atr_val, self.vol_len)
        vol_z = f_div(atr_val - atr_base, atr_dev)
        vol_score = f_clamp(50.0 + 50.0 * f_tanh(vol_z / 2.0), 0.0, 100.0)
        atr_pct = f_div(atr_val, close) * 100.0
        c_h = self.H("close")
        close_1, close_er = c_h[1], c_h[self.kama_len]
        c_h.set(close)
        ema_line = ta.ema(close, self.baseline_len)
        change = abs(close - close_er)
        vol_sum = ta.msum(abs(close - close_1), self.kama_len)
        er = f_div(change, vol_sum)
        fast_sc = div(2.0, self.fast_len + 1.0)
        slow_sc = div(2.0, self.slow_len + 1.0)
        sc = pmath.pow(er * (fast_sc - slow_sc) + slow_sc, 2.0)
        self.kama_line = float(close) if na(self.kama_line) else self.kama_line + sc * (close - self.kama_line)
        blended = ema_line + (self.kama_line - ema_line) * f_clamp(er, 0.0, 1.0)
        baseline = ta.ema(blended, self.baseline_smo) if self.baseline_smo > 1 else blended
        b_h = self.H("baseline")
        baseline_1 = b_h[1]
        b_h.set(baseline)
        baseline_slope = baseline - baseline_1
        baseline_up = baseline_slope > 0
        baseline_down = baseline_slope < 0
        ema_fast = ta.ema(close, 9)
        ema_slow = ta.ema(close, 21)
        rsi_val = ta.rsi(close, 14)
        trend_up = bool(close > baseline and baseline_up and ema_fast > ema_slow)
        trend_down = bool(close < baseline and baseline_down and ema_fast < ema_slow)
        vwap_raw = ta.vwap(self.hlc3)
        session_vwap = ta.ema(self.hlc3, 34) if na(vwap_raw) else vwap_raw
        vwap_sigma = pmath.max(ta.stdev(self.hlc3 - session_vwap, self.channel_len), mintick)
        vwap_lower1 = session_vwap - vwap_sigma
        vwap_upper1 = session_vwap + vwap_sigma
        range_high = ta.highest(high, self.anchor_len)
        range_low = ta.lowest(low, self.anchor_len)
        range_span = pmath.max(range_high - range_low, mintick)
        equilibrium = range_low + range_span * 0.5
        discount25 = range_low + range_span * 0.25
        premium75 = range_low + range_span * 0.75
        pdh = self.security(None, "D", lambda v: v.high[1], lookahead=False)
        pdl = self.security(None, "D", lambda v: v.low[1], lookahead=False)
        htf_close = self.security(None, self.htf_tf, lambda v: v.close[1], lookahead=False)
        htf_fast = self.security(None, self.htf_tf, self.htf_fast_prev, lookahead=False)
        htf_slow = self.security(None, self.htf_tf, self.htf_slow_prev, lookahead=False)
        htf_bull = bool(htf_close > htf_fast and htf_fast > htf_slow)
        htf_bear = bool(htf_close < htf_fast and htf_fast < htf_slow)
        channel_mean = ta.ema((baseline + session_vwap) * 0.5, pmath.max(5, int(self.channel_len / 4)))
        channel_mult = 1.55 * (0.75 + f_clamp(vol_score / 100.0, 0.0, 1.0))
        channel_upper = channel_mean + atr_val * channel_mult
        channel_lower = channel_mean - atr_val * channel_mult
        bb_basis = ta.sma(close, self.squeeze_len)
        bb_dev = ta.stdev(close, self.squeeze_len) * 2.0
        bb_upper = bb_basis + bb_dev
        bb_lower = bb_basis - bb_dev
        kc_basis = ta.ema(close, self.squeeze_len)
        kc_range = ta.ema(ta.tr(True), self.squeeze_len) * 1.5
        kc_upper = kc_basis + kc_range
        kc_lower = kc_basis - kc_range
        squeeze_on = bool(bb_upper < kc_upper and bb_lower > kc_lower)
        sq_h = self.H("squeeze_on")
        squeeze_on_1 = sq_h[1] == 1.0
        sq_h.set(1.0 if squeeze_on else 0.0)
        squeeze_release = (not squeeze_on) and squeeze_on_1
        range_regime = bool(adx_val < 18 and vol_score < 70)
        bull_regime = trend_up and not range_regime
        bear_regime = trend_down and not range_regime
        session_ok = (not self.use_session) or self.time_in_session(self.trade_session)
        above_vwap = close > session_vwap
        below_vwap = close < session_vwap
        prem_discount_long = bool(close < equilibrium or close < discount25)
        prem_discount_short = bool(close > equilibrium or close > premium75)
        volume_base = ta.sma(volume, 30)
        volume_spike = volume > volume_base * 1.35
        spread = pmath.max(high - low, mintick)
        delta = volume * f_div(close - open_, spread)
        pressure = ta.ema(f_div(delta, pmath.max(volume, 1.0)) * 100.0, 8)
        hi_h, lo_h = self.H("high"), self.H("low")
        high_1, low_1 = hi_h[1], lo_h[1]
        hi_h.set(high)
        lo_h.set(low)
        recent_swing_high = ta.highest(high_1, 12)
        recent_swing_low = ta.lowest(low_1, 12)
        bull_sweep_reclaim = bool((not na(recent_swing_low)) and low < recent_swing_low and close > recent_swing_low and close > open_ and volume_spike)
        bear_sweep_reclaim = bool((not na(recent_swing_high)) and high > recent_swing_high and close < recent_swing_high and close < open_ and volume_spike)
        daily_bull_sweep = bool((not na(pdl)) and low < pdl and close > pdl)
        daily_bear_sweep = bool((not na(pdh)) and high > pdh and close < pdh)
        mom_long = bool(rsi_val > 52 and ema_fast > ema_slow and pressure > -10)
        mom_short = bool(rsi_val < 48 and ema_fast < ema_slow and pressure < 10)
        vwap_bounce_long = bool(low <= vwap_lower1 and close > vwap_lower1 and close > open_)
        vwap_bounce_short = bool(high >= vwap_upper1 and close < vwap_upper1 and close < open_)
        channel_reclaim_long = bool(low < channel_lower and close > channel_lower and close > open_)
        channel_reject_short = bool(high > channel_upper and close < channel_upper and close < open_)
        vol_gate = bool(vol_score >= self.min_vol_score and vol_score <= self.max_vol_score and atr_pct <= self.max_atr_percent)
        squeeze_gate = (not self.avoid_compression) or (not squeeze_on)
        dom = self.dayofmonth()
        dom_h = self.H("dom")
        day_changed = dom != dom_h[1]
        dom_h.set(dom)
        equity = st.equity
        self.day_start_equity = float(equity) if (na(self.day_start_equity) or day_changed) else self.day_start_equity
        day_drawdown_pct = f_div(self.day_start_equity - equity, self.day_start_equity) * 100.0 if self.day_start_equity > 0 else 0.0
        daily_guard_ok = self.max_day_loss_pct <= 0 or day_drawdown_pct < self.max_day_loss_pct
        baseline_cross_up = ta.crossover(close, baseline)
        baseline_cross_down = ta.crossunder(close, baseline)
        vwap_cross_up = ta.crossover(close, session_vwap)
        vwap_cross_down = ta.crossunder(close, session_vwap)
        score_long = ((1 if bull_regime else 0) + (1 if above_vwap else 0) + (1 if prem_discount_long else 0) + (1 if mom_long else 0) + (1 if vol_gate else 0)
                      + (1 if (bull_sweep_reclaim or daily_bull_sweep) else 0) + (1 if (vwap_bounce_long or channel_reclaim_long or squeeze_release) else 0)
                      + (1 if htf_bull else 0))
        score_short = ((1 if bear_regime else 0) + (1 if below_vwap else 0) + (1 if prem_discount_short else 0) + (1 if mom_short else 0) + (1 if vol_gate else 0)
                       + (1 if (bear_sweep_reclaim or daily_bear_sweep) else 0) + (1 if (vwap_bounce_short or channel_reject_short or squeeze_release) else 0)
                       + (1 if htf_bear else 0))
        raw_long_trigger = bool(score_long >= self.min_score and (baseline_cross_up or vwap_cross_up or bull_sweep_reclaim or daily_bull_sweep or vwap_bounce_long or channel_reclaim_long))
        raw_short_trigger = bool(score_short >= self.min_score and (baseline_cross_down or vwap_cross_down or bear_sweep_reclaim or daily_bear_sweep or vwap_bounce_short or channel_reject_short))
        can_trade = na(self.last_entry_bar) or self.bar_index - self.last_entry_bar > self.cooldown_bars
        long_stop_base = pmath.min(close - atr_val * self.stop_atr_mult, nz(pdl, close - atr_val * self.stop_atr_mult))
        short_stop_base = pmath.max(close + atr_val * self.stop_atr_mult, nz(pdh, close + atr_val * self.stop_atr_mult))
        long_target_base = close + atr_val * self.tp_atr_mult
        short_target_base = close - atr_val * self.tp_atr_mult
        long_rr = f_div(long_target_base - close, close - long_stop_base)
        short_rr = f_div(close - short_target_base, short_stop_base - close)
        risk_long_ok = bool(long_rr >= self.min_rr and close > long_stop_base and daily_guard_ok)
        risk_short_ok = bool(short_rr >= self.min_rr and close < short_stop_base and daily_guard_ok)
        pos = st.position_size
        long_trigger = bool(session_ok and self.use_longs and can_trade and vol_gate and squeeze_gate and risk_long_ok and raw_long_trigger and pos <= 0)
        short_trigger = bool(session_ok and self.use_shorts and can_trade and vol_gate and squeeze_gate and risk_short_ok and raw_short_trigger and pos >= 0)
        long_qty = self.f_qty(close, long_stop_base, equity, self.risk_pct, self.max_qty, self.min_qty)
        short_qty = self.f_qty(close, short_stop_base, equity, self.risk_pct, self.max_qty, self.min_qty)
        if long_trigger:
            st.entry("Long", st.long, qty=long_qty, comment="JOAT Long")
            self.last_entry_bar = self.bar_index
            self.active_entry = float(close)
            self.active_stop = long_stop_base
            self.active_target = long_target_base
            self.active_entry_bar = self.bar_index
        if short_trigger:
            st.entry("Short", st.short, qty=short_qty, comment="JOAT Short")
            self.last_entry_bar = self.bar_index
            self.active_entry = float(close)
            self.active_stop = short_stop_base
            self.active_target = short_target_base
            self.active_entry_bar = self.bar_index
        if pos == 0 and not na(self.prev_pos) and self.prev_pos != 0:
            self.active_entry = NA
            self.active_stop = NA
            self.active_target = NA
            self.active_entry_bar = NA
        avg = st.position_avg_price
        if pos > 0:
            trail_stop = close - atr_val * self.trail_atr_mult
            self.active_stop = pmath.max(nz(self.active_stop, avg - atr_val * self.stop_atr_mult), trail_stop)
            self.active_stop = pmath.min(self.active_stop, avg - mintick)
            self.active_target = nz(self.active_target, avg + atr_val * self.tp_atr_mult)
            st.exit("Long Exit", from_entry="Long", stop=self.active_stop, limit=self.active_target, comment="Structured Exit")
            if self.close_on_flip and bear_regime and close < baseline:
                st.close("Long", comment="Regime Flip")
        if pos < 0:
            trail_stop = close + atr_val * self.trail_atr_mult
            self.active_stop = pmath.min(nz(self.active_stop, avg + atr_val * self.stop_atr_mult), trail_stop)
            self.active_stop = pmath.max(self.active_stop, avg + mintick)
            self.active_target = nz(self.active_target, avg - atr_val * self.tp_atr_mult)
            st.exit("Short Exit", from_entry="Short", stop=self.active_stop, limit=self.active_target, comment="Structured Exit")
            if self.close_on_flip and bull_regime and close > baseline:
                st.close("Short", comment="Regime Flip")
        bars_in_trade = self.bar_index - self.active_entry_bar if not na(self.active_entry_bar) else 0
        if pos > 0 and bars_in_trade >= self.max_hold_bars:
            st.close("Long", comment="Time Guard")
        if pos < 0 and bars_in_trade >= self.max_hold_bars:
            st.close("Short", comment="Time Guard")
        if (not daily_guard_ok) and pos > 0:
            st.close("Long", comment="Daily Guard")
        if (not daily_guard_ok) and pos < 0:
            st.close("Short", comment="Daily Guard")
        self.prev_pos = pos
