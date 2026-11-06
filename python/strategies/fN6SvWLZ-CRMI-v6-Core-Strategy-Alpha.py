"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : CRMI v6 Core Strategy Alpha
Author       : iamthatboyjb
Source URL   : https://www.tradingview.com/script/fN6SvWLZ-CRMI-v6-Core-Strategy-Alpha
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-29 by Claude (pine-to-python skill)

Line-for-line translation (process_orders_on_close). Major / minor pivot structure (higher highs and lows), a three-EMA trend state (-3..3), a value state from the retracement of the last impulse or the EMA(34) ± ATR band, a regime state from trend efficiency and ATR %, reaction / trigger candle counts and a 0-100 score. In FAST / LONG / HYBRID mode a long (short) needs context, reaction, trigger, score, risk:reward, cool-down and per-cycle limits while flat; the entry stop and target come from the last minor swing and ATR and are issued while the trade is open. A thesis failure (close beyond the equilibrium EMA plus a minor structure shift) closes the trade.

Deviations from the original: none.
Not carried over: trend / value-band plots, entry markers and the debug table (display only).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, div, na, pmath, ta


def score(cond, pts):
    return pts if cond else 0


class CrmiCoreAlpha(Script):
    TITLE = "CRMI v6 Core Strategy Alpha"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(initial_capital=10000, default_qty_type="percent_of_equity", default_qty_value=10, pyramiding=0, process_orders_on_close=True)
    SOURCE = {"id": "fN6SvWLZ", "author": "iamthatboyjb", "licence": "not stated",
              "url": "https://www.tradingview.com/script/fN6SvWLZ-CRMI-v6-Core-Strategy-Alpha"}

    def init(self):
        i = self.input
        g = "Structure"
        self.major_len = i.int(10, "Major Pivot Length", minval=2, group=g)
        self.minor_len = i.int(4, "Minor Pivot Length", minval=2, group=g)
        g = "Trend"
        self.tl_fast = i.int(20, "Trend Base Fast", minval=2, group=g)
        self.tl_mid = i.int(50, "Trend Base Mid", minval=2, group=g)
        self.tl_slow = i.int(200, "Trend Base Slow", minval=2, group=g)
        self.slope_lb = i.int(10, "Trend Slope Lookback", minval=1, group=g)
        self.use_trend = i.bool(True, "Use Trend Confirmation", group=g)
        g = "Value Engine"
        self.eq_len = i.int(34, "Equilibrium Length", minval=2, group=g)
        self.eq_mult = i.float(1.0, "Equilibrium ATR Band", minval=0.1, step=0.1, group=g)
        self.bal_thr = i.float(0.50, "Balanced Pullback Threshold", minval=0.1, maxval=0.95, step=0.05, group=g)
        self.deep_thr = i.float(0.70, "Deep Pullback Threshold", minval=0.1, maxval=0.95, step=0.05, group=g)
        g = "Regime"
        self.atr_len = i.int(14, "ATR Length", minval=1, group=g)
        self.eff_lb = i.int(20, "Trend Efficiency Lookback", minval=5, group=g)
        self.disorder_thr = i.float(2.2, "Volatility Disorder Threshold", minval=0.5, step=0.1, group=g)
        g = "Execution Mode"
        self.mode = i.string("HYBRID", "Execution Mode", options=["FAST", "LONG", "HYBRID"], group=g)
        self.fast_min = i.int(65, "Fast Min Score", minval=0, maxval=100, group=g)
        self.long_min = i.int(80, "Long Min Score", minval=0, maxval=100, group=g)
        self.hybrid_min = i.int(72, "Hybrid Min Score", minval=0, maxval=100, group=g)
        g = "Risk"
        self.stop_fast = i.float(0.8, "ATR Stop Mult Fast", minval=0.1, step=0.1, group=g)
        self.stop_long = i.float(1.5, "ATR Stop Mult Long", minval=0.1, step=0.1, group=g)
        self.take_rr = i.float(1.5, "Target RR", minval=0.5, step=0.1, group=g)
        i.float(1.0, "Break-even Trigger RR", minval=0.2, step=0.1, group=g)
        self.min_rr = i.float(1.2, "Minimum RR Filter", minval=0.5, step=0.1, group=g)
        g = "Trade Control"
        self.cooldown = i.int(8, "Cooldown Bars After Exit", minval=0, group=g)
        self.allow_reentry = i.bool(True, "Allow Re-entry", group=g)
        self.one_per_dir = i.bool(True, "One Trade Per Direction Until Reset", group=g)
        self.max_cycle = i.int(2, "Max Trades Per Direction Cycle", minval=1, group=g)
        g = "Display"
        i.bool(True, "Show Trend Baselines", group=g)
        i.bool(True, "Show Value Bands", group=g)
        i.bool(True, "Show Entry Signals", group=g)
        i.bool(True, "Show Debug Table", group=g)
        self.major_high1 = self.major_high2 = self.major_low1 = self.major_low2 = NA
        self.minor_high1 = self.minor_high2 = self.minor_low1 = self.minor_low2 = NA
        self.last_exit_bar = NA
        self.long_cycle = 0
        self.short_cycle = 0
        self.last_dir = 0
        self.active_long_stop = NA
        self.active_long_target = NA
        self.active_short_stop = NA
        self.active_short_target = NA

    def on_bar(self):
        st = self.strategy
        close, open_, high, low = self.close, self.open, self.high, self.low
        mintick = self.syminfo.mintick
        atr = ta.atr(self.atr_len)
        eq = ta.ema(close, self.eq_len)
        upper_band = eq + atr * self.eq_mult
        lower_band = eq - atr * self.eq_mult
        t_fast = ta.ema(close, self.tl_fast)
        t_mid = ta.ema(close, self.tl_mid)
        t_slow = ta.ema(close, self.tl_slow)
        hf, hm, hs = self.H("t_fast"), self.H("t_mid"), self.H("t_slow")
        slope_fast = t_fast - hf[self.slope_lb]
        slope_mid = t_mid - hm[self.slope_lb]
        slope_slow = t_slow - hs[self.slope_lb]
        hf.set(t_fast)
        hm.set(t_mid)
        hs.set(t_slow)
        above_stack = close > t_fast and close > t_mid and close > t_slow
        below_stack = close < t_fast and close < t_mid and close < t_slow
        ph_major = ta.pivothigh(high, self.major_len, self.major_len)
        pl_major = ta.pivotlow(low, self.major_len, self.major_len)
        ph_minor = ta.pivothigh(high, self.minor_len, self.minor_len)
        pl_minor = ta.pivotlow(low, self.minor_len, self.minor_len)
        if not na(ph_major):
            self.major_high2 = self.major_high1
            self.major_high1 = float(ph_major)
        if not na(pl_major):
            self.major_low2 = self.major_low1
            self.major_low1 = float(pl_major)
        if not na(ph_minor):
            self.minor_high2 = self.minor_high1
            self.minor_high1 = float(ph_minor)
        if not na(pl_minor):
            self.minor_low2 = self.minor_low1
            self.minor_low1 = float(pl_minor)
        mh1, mh2, ml1, ml2 = self.major_high1, self.major_high2, self.major_low1, self.major_low2
        nh1, nh2, nl1, nl2 = self.minor_high1, self.minor_high2, self.minor_low1, self.minor_low2
        major_bull = not na(mh1) and not na(mh2) and not na(ml1) and not na(ml2) and mh1 > mh2 and ml1 > ml2
        major_bear = not na(mh1) and not na(mh2) and not na(ml1) and not na(ml2) and mh1 < mh2 and ml1 < ml2
        minor_bull = not na(nh1) and not na(nh2) and not na(nl1) and not na(nl2) and nh1 > nh2 and nl1 > nl2
        minor_bear = not na(nh1) and not na(nh2) and not na(nl1) and not na(nl2) and nh1 < nh2 and nl1 < nl2
        major_bias = 1 if (major_bull and not major_bear) else (-1 if (major_bear and not major_bull) else 0)
        minor_bias = 1 if (minor_bull and not minor_bear) else (-1 if (minor_bear and not minor_bull) else 0)
        minor_bull_shift = not na(nh1) and close > nh1
        minor_bear_shift = not na(nl1) and close < nl1
        bull_aligned = t_fast > t_mid and t_mid > t_slow and slope_fast > 0 and slope_mid > 0
        bear_aligned = t_fast < t_mid and t_mid < t_slow and slope_fast < 0 and slope_mid < 0
        if above_stack and bull_aligned and slope_slow > 0:
            trend_state = 3
        elif close > t_mid and slope_mid > 0:
            trend_state = 2
        elif close > t_slow:
            trend_state = 1
        elif below_stack and bear_aligned and slope_slow < 0:
            trend_state = -3
        elif close < t_mid and slope_mid < 0:
            trend_state = -2
        elif close < t_slow:
            trend_state = -1
        else:
            trend_state = 0
        if major_bias == 1 or major_bias == -1:
            impulse_low, impulse_high = ml1, mh1
        else:
            impulse_low, impulse_high = nl1, nh1
        impulse_range = abs(impulse_high - impulse_low) if (not na(impulse_high) and not na(impulse_low)) else NA
        ret_bull = div(impulse_high - close, impulse_range) if (not na(impulse_range) and impulse_range > 0) else NA
        ret_bear = div(close - impulse_low, impulse_range) if (not na(impulse_range) and impulse_range > 0) else NA
        in_deep_disc = (major_bias == 1 and not na(ret_bull) and ret_bull >= self.deep_thr) or close < lower_band
        in_disc = (major_bias == 1 and not na(ret_bull) and ret_bull >= self.bal_thr) or close < eq
        in_deep_prem = (major_bias == -1 and not na(ret_bear) and ret_bear >= self.deep_thr) or close > upper_band
        in_prem = (major_bias == -1 and not na(ret_bear) and ret_bear >= self.bal_thr) or close > eq
        value_state = 2 if in_deep_disc else (1 if in_disc else (-2 if in_deep_prem else (-1 if in_prem else 0)))
        c_h = self.H("close")
        net_move = abs(close - c_h[self.eff_lb])
        close_1 = c_h[1]
        c_h.set(close)
        bar_travel = abs(close - close_1)
        travel = ta.msum(bar_travel, self.eff_lb)
        efficiency = 0.0 if travel == 0.0 else div(net_move, travel)
        atr_pct = (0.0 if close == 0.0 else div(atr, close)) * 100.0
        disorder = atr_pct > self.disorder_thr
        trend_expansion = efficiency > 0.45 and abs(trend_state) >= 2
        pullback_cont = abs(trend_state) >= 2 and value_state != 0
        range_rotation = efficiency < 0.25 and abs(trend_state) <= 1
        transition = efficiency >= 0.25 and efficiency <= 0.45 and abs(trend_state) <= 2
        if disorder:
            regime = -2
        elif trend_expansion:
            regime = 2
        elif pullback_cont:
            regime = 1
        elif range_rotation:
            regime = 0
        elif transition:
            regime = -1
        else:
            regime = 0
        is_fast = self.mode == "FAST"
        is_long = self.mode == "LONG"
        min_score = self.fast_min if is_fast else (self.long_min if is_long else self.hybrid_min)
        mgmt_mult = self.stop_long if is_long else (self.stop_fast if is_fast else (self.stop_fast + self.stop_long) / 2.0)
        body = abs(close - open_)
        bd_h = self.H("body")
        body_1 = bd_h[1]
        bd_h.set(body)
        upper_wick = high - pmath.max(open_, close)
        lower_wick = pmath.min(open_, close) - low
        bull_candle = close > open_
        bear_candle = close < open_
        bear_shrink = body < body_1 and bear_candle
        bull_shrink = body < body_1 and bull_candle
        h_h, l_h = self.H("high"), self.H("low")
        high_1, low_1 = h_h[1], l_h[1]
        h_h.set(high)
        l_h.set(low)
        buy_react = 0
        buy_react += score(bear_shrink, 1)
        buy_react += score(lower_wick > body, 1)
        buy_react += score(low <= lower_band or close < eq, 1)
        buy_react += score(close > low + (high - low) * 0.55, 1)
        buy_react += score(close > close_1, 1)
        sell_react = 0
        sell_react += score(bull_shrink, 1)
        sell_react += score(upper_wick > body, 1)
        sell_react += score(high >= upper_band or close > eq, 1)
        sell_react += score(close < low + (high - low) * 0.45, 1)
        sell_react += score(close < close_1, 1)
        buy_react_ok = buy_react >= 2
        sell_react_ok = sell_react >= 2
        bull_restart = close > high_1 and close > eq
        bear_restart = close < low_1 and close < eq
        ema8 = ta.ema(close, 8)
        bull_minor_cnt = score(bull_candle, 1) + score(close > ema8, 1) + score(not na(nl1) and close > nl1, 1)
        bear_minor_cnt = score(bear_candle, 1) + score(close < ema8, 1) + score(not na(nh1) and close < nh1, 1)
        buy_trigger = minor_bull_shift or bull_restart or bull_minor_cnt >= 2
        sell_trigger = minor_bear_shift or bear_restart or bear_minor_cnt >= 2
        s_long = score(major_bias == 1, 10) + score(minor_bias >= 0, 5) + score(minor_bull_shift, 5) + score(not major_bear, 5)
        s_long = int(pmath.max(0, pmath.min(s_long, 25)))
        v_long = score(in_disc, 10) + score(in_deep_disc, 10) + score(close <= lower_band, 5)
        v_long = int(pmath.max(0, pmath.min(v_long, 25)))
        t_long = 15 if trend_state == 3 else (10 if trend_state == 2 else (5 if trend_state == 1 else 0))
        t_long += score(bull_aligned, 5)
        t_long = int(pmath.max(0, pmath.min(t_long, 20)))
        r_long = score(buy_react_ok, 5) + score(lower_wick > body, 5) + score(buy_trigger, 5)
        r_long = int(pmath.max(0, pmath.min(r_long, 15)))
        s_short = score(major_bias == -1, 10) + score(minor_bias <= 0, 5) + score(minor_bear_shift, 5) + score(not major_bull, 5)
        s_short = int(pmath.max(0, pmath.min(s_short, 25)))
        v_short = score(in_prem, 10) + score(in_deep_prem, 10) + score(close >= upper_band, 5)
        v_short = int(pmath.max(0, pmath.min(v_short, 25)))
        t_short = 15 if trend_state == -3 else (10 if trend_state == -2 else (5 if trend_state == -1 else 0))
        t_short += score(bear_aligned, 5)
        t_short = int(pmath.max(0, pmath.min(t_short, 20)))
        r_short = score(sell_react_ok, 5) + score(upper_wick > body, 5) + score(sell_trigger, 5)
        r_short = int(pmath.max(0, pmath.min(r_short, 15)))
        long_ref = nl1 if not na(nl1) else low
        short_ref = nh1 if not na(nh1) else high
        long_stop_c = long_ref - atr * mgmt_mult
        short_stop_c = short_ref + atr * mgmt_mult
        long_risk = close - long_stop_c
        short_risk = short_stop_c - close
        long_target_c = close + long_risk * self.take_rr
        short_target_c = close - short_risk * self.take_rr
        long_rr = 0.0 if long_risk == 0.0 else div(long_target_c - close, long_risk)
        short_rr = 0.0 if short_risk == 0.0 else div(close - short_target_c, short_risk)
        k_long = score(long_risk > mintick * 10, 5) + score(long_rr >= self.min_rr, 5)
        k_long += score((long_target_c <= mh1 * 1.03) if not na(mh1) else True, 5)
        k_long = int(pmath.max(0, pmath.min(k_long, 15)))
        k_short = score(short_risk > mintick * 10, 5) + score(short_rr >= self.min_rr, 5)
        k_short += score((short_target_c >= ml1 * 0.97) if not na(ml1) else True, 5)
        k_short = int(pmath.max(0, pmath.min(k_short, 15)))
        buy_score = s_long + v_long + t_long + r_long + k_long
        sell_score = s_short + v_short + t_short + r_short + k_short
        pos_h, mb_h = self.H("pos"), self.H("major_bias")
        pos_1, major_bias_1 = pos_h[1], mb_h[1]
        pos_h.set(st.position_size)
        mb_h.set(major_bias)
        just_closed = st.position_size == 0 and (not na(pos_1)) and pos_1 != 0
        if just_closed:
            self.last_exit_bar = self.bar_index
        cooldown_active = (not na(self.last_exit_bar)) and (self.bar_index - self.last_exit_bar) < self.cooldown
        if major_bias == 1 and major_bias_1 != 1:
            self.long_cycle = 0
        if major_bias == -1 and major_bias_1 != -1:
            self.short_cycle = 0
        long_cycle_blocked = self.long_cycle >= self.max_cycle
        short_cycle_blocked = self.short_cycle >= self.max_cycle
        same_dir_block_long = self.one_per_dir and self.last_dir == 1 and not self.allow_reentry
        same_dir_block_short = self.one_per_dir and self.last_dir == -1 and not self.allow_reentry
        near_obstacle_long = not na(mh1) and (mh1 - close) < atr * 0.8
        near_obstacle_short = not na(ml1) and (close - ml1) < atr * 0.8
        mid_range = value_state == 0
        structure_conflict = major_bias == 0 and minor_bias == 0
        trend_long_ok = (not self.use_trend) or trend_state >= 2
        trend_short_ok = (not self.use_trend) or trend_state <= -2
        fast_long_ok = (not self.use_trend) or trend_state >= -1
        fast_short_ok = (not self.use_trend) or trend_state <= 1
        hyb_long_ok = (not self.use_trend) or trend_state >= 1
        hyb_short_ok = (not self.use_trend) or trend_state <= -1
        mode_long_trend = trend_long_ok if is_long else (fast_long_ok if is_fast else hyb_long_ok)
        mode_short_trend = trend_short_ok if is_long else (fast_short_ok if is_fast else hyb_short_ok)
        if is_long:
            mode_regime_long = regime == 2 or regime == 1
        elif is_fast:
            mode_regime_long = regime != -2
        else:
            mode_regime_long = regime == 2 or regime == 1 or regime == -1
        mode_regime_short = mode_regime_long
        buy_ctx = ((major_bias == 1 or (is_fast and major_bias == 0)) and value_state >= 1 and mode_regime_long and mode_long_trend
                   and not near_obstacle_long and not disorder and not structure_conflict)
        sell_ctx = ((major_bias == -1 or (is_fast and major_bias == 0)) and value_state <= -1 and mode_regime_short and mode_short_trend
                    and not near_obstacle_short and not disorder and not structure_conflict)
        risk_ok_long = long_rr >= self.min_rr and long_risk > mintick * 10
        risk_ok_short = short_rr >= self.min_rr and short_risk > mintick * 10
        long_allowed = (buy_ctx and buy_react_ok and buy_trigger and buy_score >= min_score and risk_ok_long and not cooldown_active
                        and not long_cycle_blocked and not same_dir_block_long and not mid_range and st.position_size == 0)
        short_allowed = (sell_ctx and sell_react_ok and sell_trigger and sell_score >= min_score and risk_ok_short and not cooldown_active
                         and not short_cycle_blocked and not same_dir_block_short and not mid_range and st.position_size == 0)
        if long_allowed:
            self.active_long_stop = float(long_stop_c)
            self.active_long_target = float(long_target_c)
            st.entry("CRMI Long", st.long)
            self.long_cycle += 1
            self.last_dir = 1
        if short_allowed:
            self.active_short_stop = float(short_stop_c)
            self.active_short_target = float(short_target_c)
            st.entry("CRMI Short", st.short)
            self.short_cycle += 1
            self.last_dir = -1
        if st.position_size > 0:
            st.exit("CRMI Long Exit", "CRMI Long", stop=self.active_long_stop, limit=self.active_long_target)
        if st.position_size < 0:
            st.exit("CRMI Short Exit", "CRMI Short", stop=self.active_short_stop, limit=self.active_short_target)
        long_fail = st.position_size > 0 and (close < eq and minor_bear_shift)
        short_fail = st.position_size < 0 and (close > eq and minor_bull_shift)
        if long_fail:
            st.close("CRMI Long", comment="Thesis Failure")
        if short_fail:
            st.close("CRMI Short", comment="Thesis Failure")
