"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : TQQQ AG v16 — Vol Overlay
Author       : not stated
Source URL   : https://www.tradingview.com/script/xyMwt4PE
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-30 by Claude (pine-to-python skill)

Line-for-line translation (daily TQQQ chart, orders at the bar's close: process_orders_on_close). A QQQ regime (close vs its 200 SMA with a bull / bear buffer, a 50 SMA fast bear / fast bull trigger, QQQ and TQQQ RSI) drives a five-state machine: 1 bull long, 2 overbought short (fixed and trailing stop), 3 bear-bounce long, 5 bear short (trailing stop, cooldown), 0 cash. The wanted side is entered with a leveraged equity-based quantity (reversing through strategy.entry), flat means close_all, an equity kill-switch halts trading until a bear-to-bull re-arm, and the volatility overlay scales the leverage by target / realised volatility (instant cuts, slow restores, rising-vol penalty, optional graded de-levering). While the side is unchanged the position is rescaled with strategy.order when the target quantity differs by more than the dead-band.
Deviations from the original: none. The regime symbol is requested through the data provider (QQQ daily bars aligned to the chart); the weekly QQQ MACD is requested with timeframe W.
Not carried over: labels, the yearly results table (display only).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, div, na, nz, pmath, ta


class TqqqVolOverlay(Script):
    TITLE = "TQQQ AG v16 — Vol Overlay"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(default_qty_type="percent_of_equity", default_qty_value=100, initial_capital=10000, commission_type="percent", commission_value=0.0,
                    process_orders_on_close=True, margin_long=20, margin_short=8)
    SOURCE = {"id": "xyMwt4PE", "author": "not stated", "licence": "not stated", "url": "https://www.tradingview.com/script/xyMwt4PE"}

    def init(self):
        i = self.input
        g = "v15 Signals"
        self.regime_sym = i.string("QQQ", "Regime Symbol", group=g)
        self.sma_len = i.int(200, "Regime SMA Length", group=g)
        self.sma_bull_buf = i.float(0.35, "Bull Buffer %", group=g)
        self.sma_bear_buf = i.float(0.75, "Bear Buffer %", group=g)
        self.rsi_len = i.int(10, "RSI Length", group=g)
        self.ob_thresh = i.int(81, "OB Short Threshold (QQQ RSI)", group=g)
        self.bull_reentry = i.int(71, "Bull Re-entry RSI (TQQQ RSI)", group=g)
        self.ob_rearm = i.int(78, "OB Re-arm (QQQ RSI)", group=g)
        self.ob_retrig = i.int(73, "OB Re-trigger", group=g)
        self.rs_tqqq_filter = i.int(69, "Bull Reshort Max TQQQ RSI", group=g)
        self.bear_os = i.int(31, "Bear OS Long Threshold (TQQQ RSI)", group=g)
        self.bear_exit_rs = i.int(55, "Bear Bounce Exit RSI", group=g)
        self.max_bounce = i.int(4, "Max Bear Bounce Bars", group=g)
        self.ob_stop_pct = i.float(7.0, "OB Short Fixed Stop %", group=g)
        self.ob_trail_pct = i.float(1.5, "OB Short Trailing Stop %", group=g)
        self.reshort_arm = i.int(53, "Re-short Arm RSI (QQQ RSI)", group=g)
        self.reshort_trig = i.int(55, "Re-short Trigger RSI (QQQ RSI)", group=g)
        self.use_macd = i.bool(False, "Use Weekly MACD Gate", group=g)
        self.use_fast_bear = i.bool(True, "Use Fast Bear (50 SMA)", group=g)
        self.sma50_buf = i.float(1.0, "50 SMA Buffer %", group=g)
        self.use_fast_bull = i.bool(True, "Use Fast Bull (50 SMA)", group=g)
        self.enable_long = i.bool(True, "Enable Longs", group=g)
        self.enable_short = i.bool(True, "Enable Shorts", group=g)
        self.gate_a_len = i.int(18, "Gate A: close > EMA(N)", group=g)
        self.gate_b_fast = i.int(3, "Gate B: EMA fast", group=g)
        self.gate_b_slow = i.int(22, "Gate B: EMA slow", group=g)
        g = "v15 Leverage & Armor"
        self.bull_lev = i.float(1.25, "Bull-Long Leverage (state 1)", group=g)
        self.bounce_lev = i.float(1.5, "Bear-Bounce Leverage (state 3)", group=g)
        self.bear_short_lev = i.float(1.5, "Bear-Short Leverage (state 5)", group=g)
        self.ob_short_lev = i.float(3.0, "OB-Short Leverage (state 2)", group=g)
        self.bs_trail_pct = i.float(15.0, "Bear-Short Trailing Stop % (0=off)", group=g)
        self.bs_cd_bars = i.int(5, "Reshort Cooldown Bars after trail stop", group=g)
        self.kill_dd = i.float(65.0, "Equity Kill-Switch DD % (0=off)", group=g)
        g = "★ v16 Volatility Overlay"
        self.ovl_on = i.bool(True, "Enable Volatility Overlay", group=g)
        self.ovl_target = i.float(0.55, "Target Volatility  (0.55 / 0.75 / 0.90)", step=0.05, minval=0.20, maxval=2.0, group=g)
        self.ovl_fast = i.int(10, "Fast Vol Window (bars)", minval=2, group=g)
        self.ovl_slow = i.int(60, "Slow Vol Window (bars)", minval=5, group=g)
        self.ovl_floor = i.float(0.30, "Multiplier Floor", step=0.05, minval=0.05, maxval=1.0, group=g)
        self.ovl_gamma = i.float(0.60, "Rising-Vol Penalty", step=0.05, minval=0.0, maxval=2.0, group=g)
        self.ovl_restore = i.float(0.02, "Max Restore per Bar (cut is instant)", step=0.01, minval=0.005, maxval=1.0, group=g)
        self.ovl_band = i.float(0.03, "Rebalance Deadband", step=0.01, minval=0.0, maxval=0.50, group=g)
        g = "★ v16 Graded De-lever (optional, set Kill-Switch=0)"
        self.grd_on = i.bool(False, "Enable Graded De-levering", group=g)
        self.grd_x = i.float(40.0, "Full size until own drawdown %", group=g)
        self.grd_y = i.float(75.0, "Floor reached at own drawdown %", group=g)
        self.grd_fl = i.float(0.25, "Graded floor multiplier", step=0.05, group=g)
        self.in_bull = False
        self.state = 0
        self.bounce_bars = 0
        self.bear_short_bars = 0
        self.reshort_primed = False
        self.ob_reshort_primed = False
        self.ob_trail_low = NA
        self.bs_low = NA
        self.bs_cd = 0
        self.halted = False
        self.halt_seen_bear = False
        self.risk_peak = NA
        self.m_prev = 1.0
        self.eq_peak = NA

    def on_bar(self):
        st = self.strategy
        close = self.close
        h_below, h_above = self.H("below50"), self.H("above50")
        below_1, above_1 = h_below[1], h_above[1]
        in_bull_prev = self.in_bull
        h_close = self.H("close")
        close_1 = h_close[1]
        tqqq_rsi = ta.rsi(close, self.rsi_len)
        w_macd, w_sig, _ = self.security(self.regime_sym, "W", lambda v: ta.macd(v.close, 12, 26, 9))
        macd_bear = w_macd < w_sig
        gate_a = close > ta.ema(close, self.gate_a_len)
        gate_b = ta.ema(close, self.gate_b_fast) > ta.ema(close, self.gate_b_slow)
        tqqq_gate = gate_a and gate_b
        regime_close = self.security(self.regime_sym, "D", lambda v: float(v.close))
        qqq_rsi = ta.rsi(regime_close, self.rsi_len)
        regime_sma = ta.sma(regime_close, self.sma_len)
        bull_threshold = regime_sma * (1 + self.sma_bull_buf / 100)
        bear_threshold = regime_sma * (1 - self.sma_bear_buf / 100)
        self.in_bull = True if regime_close > bull_threshold else False if regime_close < bear_threshold else self.in_bull
        in_bull = self.in_bull
        trend_up = in_bull
        bear_just_started = (not in_bull) and in_bull_prev
        regime_sma50 = ta.sma(regime_close, 50)
        below_sma50 = regime_close < regime_sma50 * (1 - self.sma50_buf / 100)
        above_sma50 = regime_close > regime_sma50
        fast_bear_trig = self.use_fast_bear and (not in_bull) and below_sma50 and not (below_1 == 1) and qqq_rsi < 45
        fast_bull_cross = self.use_fast_bull and (not in_bull) and above_sma50 and not (above_1 == 1) and tqqq_rsi > 50

        pos = st.position_size
        if self.state == 2:
            self.ob_trail_low = float(close) if na(self.ob_trail_low) else pmath.min(self.ob_trail_low, close)
        else:
            self.ob_trail_low = NA
        short_entry_price = st.position_avg_price if pos < 0 else NA
        hit_ob_stop = (not na(short_entry_price)) and self.state == 2 and close >= short_entry_price * (1 + self.ob_stop_pct / 100)
        hit_ob_trail = (not na(self.ob_trail_low)) and self.state == 2 and close >= self.ob_trail_low * (1 + self.ob_trail_pct / 100)
        ob_exit = hit_ob_stop or hit_ob_trail
        if self.state == 5:
            self.bs_low = float(close) if na(self.bs_low) else pmath.min(self.bs_low, close)
        else:
            self.bs_low = NA
        bs_exit = self.bs_trail_pct > 0 and (not na(self.bs_low)) and self.state == 5 and close >= self.bs_low * (1 + self.bs_trail_pct / 100)

        if trend_up:
            self.bear_short_bars = 0
            self.reshort_primed = False
            if qqq_rsi >= self.ob_thresh:
                self.state = 2
                self.ob_reshort_primed = False
            elif self.state == 2 and (tqqq_rsi < self.bull_reentry or ob_exit):
                self.state = 1 if tqqq_gate else 0
            elif self.ob_reshort_primed and qqq_rsi <= self.ob_retrig and tqqq_rsi < self.rs_tqqq_filter:
                self.state = 2
                self.ob_reshort_primed = False
            elif self.state != 1 and self.state != 2:
                self.state = 1 if tqqq_gate else 0
            if self.state == 1 and qqq_rsi >= self.ob_rearm:
                self.ob_reshort_primed = True
            if self.state != 1:
                self.ob_reshort_primed = False
        else:
            self.ob_reshort_primed = False
            if bear_just_started or fast_bear_trig:
                self.state = 5
                self.bear_short_bars = 0
                self.reshort_primed = False
            elif fast_bull_cross:
                self.state = 1
                self.bear_short_bars = 0
            elif self.state == 1:
                self.bear_short_bars = 0
            elif self.state == 5:
                self.bear_short_bars += 1
                if tqqq_rsi <= self.bear_os:
                    self.state = 3
                    self.bounce_bars = 0
                    self.bear_short_bars = 0
                elif bs_exit:
                    self.state = 0
                    self.bear_short_bars = 0
                    self.bs_cd = self.bs_cd_bars
            elif tqqq_rsi <= self.bear_os:
                if self.state != 3:
                    self.state = 3
                    self.bounce_bars = 0
            elif self.state == 3:
                self.bounce_bars += 1
                if tqqq_rsi >= self.bear_exit_rs or self.bounce_bars >= self.max_bounce:
                    self.state = 0
                    self.bounce_bars = 0
            else:
                self.state = 0
                self.bounce_bars = 0
            if self.state == 0:
                if self.bs_cd > 0:
                    self.bs_cd -= 1
                if qqq_rsi >= self.reshort_arm:
                    self.reshort_primed = True
                if self.reshort_primed and qqq_rsi <= self.reshort_trig and ((not self.use_macd) or macd_bear) and self.bs_cd == 0:
                    self.state = 5
                    self.reshort_primed = False
                    self.bear_short_bars = 0

        eq_now = st.equity
        self.risk_peak = float(eq_now) if na(self.risk_peak) else self.risk_peak
        if self.kill_dd > 0:
            if (not self.halted) and eq_now <= self.risk_peak * (1 - self.kill_dd / 100.0):
                self.halted = True
                self.halt_seen_bear = not trend_up
            elif self.halted:
                if not trend_up:
                    self.halt_seen_bear = True
                if self.halt_seen_bear and trend_up:
                    self.halted = False
                    self.risk_peak = float(eq_now)
        if not self.halted:
            self.risk_peak = pmath.max(self.risk_peak, eq_now)

        ret1 = nz(div(close, close_1) - 1.0)
        v_fast = ta.stdev(ret1, self.ovl_fast) * pmath.sqrt(252)
        v_slow = ta.stdev(ret1, self.ovl_slow) * pmath.sqrt(252)
        v_est = pmath.max(v_fast, v_slow)
        ovl_pen = pmath.min(0.60, pmath.max(0.0, self.ovl_gamma * (div(v_fast, pmath.max(v_slow, 0.000001)) - 1.0)))
        if na(v_slow) or v_slow <= 0:
            m_raw = 1.0
        else:
            m_raw = pmath.max(self.ovl_floor * 0.5, pmath.min(1.0, pmath.max(self.ovl_floor, div(self.ovl_target, pmath.max(v_est, 0.000001))) * (1.0 - ovl_pen)))
        m_now = m_raw if m_raw < self.m_prev else pmath.min(m_raw, self.m_prev + self.ovl_restore)
        self.m_prev = m_now

        self.eq_peak = float(st.equity) if na(self.eq_peak) else pmath.max(self.eq_peak, st.equity)
        own_dd = (1.0 - div(st.equity, self.eq_peak)) * 100.0 if self.eq_peak > 0 else 0.0
        if not self.grd_on:
            grd_m = 1.0
        elif own_dd <= self.grd_x:
            grd_m = 1.0
        elif own_dd >= self.grd_y:
            grd_m = self.grd_fl
        else:
            grd_m = 1.0 - (1.0 - self.grd_fl) * div(own_dd - self.grd_x, pmath.max(self.grd_y - self.grd_x, 0.000001))
        ovl_m = (m_now if self.ovl_on else 1.0) * grd_m

        want_long = (self.state == 1 or self.state == 3) and self.enable_long and not self.halted
        want_short = (self.state == 2 or self.state == 5) and self.enable_short and not self.halted
        want_flat = (not want_long) and (not want_short)
        lev_l = self.bounce_lev if self.state == 3 else self.bull_lev
        lev_s = self.ob_short_lev if self.state == 2 else self.bear_short_lev
        qty_long = pmath.max(1, pmath.floor(div(st.equity * lev_l * ovl_m, close)))
        qty_short = pmath.max(1, pmath.floor(div(st.equity * lev_s * ovl_m, close)))
        if want_long and pos <= 0:
            st.entry("Long", st.long, qty=qty_long)
        if want_short and pos >= 0:
            st.entry("Short", st.short, qty=qty_short)
        if want_flat and pos != 0:
            st.close_all(comment="Cash")

        pos_dir = 1 if pos > 0 else -1 if pos < 0 else 0
        want_dir = 1 if want_long else -1 if want_short else 0
        if self.ovl_on and pos_dir != 0 and pos_dir == want_dir:
            lev_now = lev_l if pos_dir > 0 else lev_s
            tgt_qty = pmath.max(1, pmath.floor(div(st.equity * lev_now * ovl_m, close))) * pos_dir
            dev = div(abs(tgt_qty - pos), pmath.max(abs(pos), 1))
            if dev > self.ovl_band:
                dq = tgt_qty - pos
                if dq > 0:
                    st.order("RescaleUp", st.long, qty=dq)
                elif dq < 0:
                    st.order("RescaleDn", st.short, qty=-dq)

        h_below.set(1 if below_sma50 else 0)
        h_above.set(1 if above_sma50 else 0)
        h_close.set(close)
