"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : 30M Options Swing Edge - Lorentzian Style Trend Pullback
Author       : not stated
Source URL   : https://www.tradingview.com/script/vAVhJe1C-SVT-30M-Options-Swing-Indicator
Pine version : v5
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-29 by Claude (pine-to-python skill)

Line-for-line translation (orders processed at the bar close, process_orders_on_close; made for a 30-minute chart). Daily and 2-hour bias come from request.security (lookahead off) suites of EMA / RSI / MACD / DMI / CCI / WaveTrend values; the 30-minute chart adds a MACD cross window, a seven-feature
"Lorentzian-style" score, a pullback window, a chop filter and cooldowns. CALL = long, PUT = short (a signal against an open position first closes it). The stop is an ATR emergency stop that turns into a break-even / trailing stop once the profit threshold is reached, plus MACD / 2H / deep-failure exits.
Deviations from the original: none. (As written in the original, the trade-tracking variables are cleared at the end of the entry bar's script run because the position is still flat then, so a new trade from flat has no entry bar: the hold-bar / time / theta exits never trigger for it and the ATR is the current one. This is reproduced.)
Not carried over: EMA / stop plots, signal shapes, the chop background, the status table and the alert conditions (display only).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, div, na, pmath, ta


class OptionsSwingEdge(Script):
    TITLE = "30M Options Swing Edge - Lorentzian Style Trend Pullback"
    PINE_VERSION = 5
    OVERLAY = True
    STRATEGY = dict(pyramiding=0, process_orders_on_close=True, initial_capital=100000)
    SOURCE = {"id": "vAVhJe1C", "author": "not stated", "licence": "not stated",
              "url": "https://www.tradingview.com/script/vAVhJe1C-SVT-30M-Options-Swing-Indicator"}

    def init(self):
        i = self.input
        self.daily_tf = i.timeframe("D", "Daily Bias Timeframe")
        self.confirm_tf = i.timeframe("120", "2H Confirmation Timeframe")
        self.mode = i.string("Balanced", "Signal Mode", options=["Aggressive", "Balanced", "Safe"])
        self.rsi_len = i.int(14, "RSI 14 Length", minval=1)
        self.rsi_fast_len = i.int(9, "RSI 9 Length", minval=1)
        self.rsi_ma_len = i.int(14, "RSI MA Length", minval=1)
        self.macd_fast = i.int(12, "MACD Fast Length", minval=1)
        self.macd_slow = i.int(26, "MACD Slow Length", minval=1)
        self.macd_signal_len = i.int(9, "MACD Signal Length", minval=1)
        self.macd_cross_active_bars = i.int(5, "30M MACD Cross Active Bars", minval=1)
        self.ema_fast_len = i.int(20, "EMA 20 Length", minval=1)
        self.ema_mid_len = i.int(50, "EMA 50 Length", minval=1)
        self.ema_slow_len = i.int(200, "EMA 200 Length", minval=1)
        self.wt_channel_len = i.int(10, "WaveTrend Channel Length", minval=1)
        self.wt_average_len = i.int(11, "WaveTrend Average Length", minval=1)
        self.cci_len = i.int(20, "CCI Length", minval=1)
        self.adx_len = i.int(20, "ADX Length", minval=1)
        self.adx_smooth = i.int(14, "ADX Smoothing", minval=1)
        self.adx_min = i.float(16.0, "Minimum ADX", step=0.5)
        self.atr_len = i.int(14, "ATR Length", minval=1)
        self.emergency_stop_atr = i.float(2.2, "Emergency Stop ATR", step=0.1)
        self.trail_start_atr = i.float(2.0, "Start Trailing After ATR Profit", step=0.1)
        self.trail_atr = i.float(3.2, "Trailing Stop ATR", step=0.1)
        self.pullback_bars = i.int(12, "Pullback Active Bars", minval=1)
        self.cooldown_after_entry = i.int(10, "Cooldown After Entry Bars", minval=0)
        self.cooldown_after_exit = i.int(4, "Cooldown After Exit Bars", minval=0)
        self.min_hold_bars = i.int(8, "Minimum Hold Bars", minval=1)
        self.max_hold_bars = i.int(78, "Maximum Hold Bars", minval=1)
        self.use_chop_filter = i.bool(True, "Use Chop Filter")
        self.chop_lookback = i.int(24, "Chop Lookback", minval=5)
        self.chop_adx = i.float(15.0, "Chop ADX Threshold", step=0.5)
        self.ema_compression_atr = i.float(0.35, "EMA Compression ATR", step=0.05)
        self.use_theta_protection = i.bool(False, "Use Theta No-Progress Exit")
        self.theta_check_bars = i.int(18, "Theta Check Bars", minval=1)
        self.min_move_atr_to_hold = i.float(0.60, "Minimum ATR Move To Hold", step=0.05)
        self.last_entry_bar = NA
        self.last_exit_bar = NA
        self.entry_bar = NA
        self.entry_atr = NA
        self.high_since_entry = NA
        self.low_since_entry = NA
        self.active_stop = NA
        self.prev_pos = 0.0

    def wavetrend(self, src, n1, n2):
        esa = ta.ema(src, n1)
        dev = ta.ema(abs(src - esa), n1)
        ci = div(src - esa, 0.015 * dev) if dev != 0 else 0.0
        wt1 = ta.ema(ci, n2)
        wt2 = ta.sma(wt1, 4)
        return wt1, wt2

    def htf_data(self, close, hlc3):
        e20 = ta.ema(close, self.ema_fast_len)
        e50 = ta.ema(close, self.ema_mid_len)
        e200 = ta.ema(close, self.ema_slow_len)
        rsi14 = ta.rsi(close, self.rsi_len)
        rsi9 = ta.rsi(close, self.rsi_fast_len)
        m, s, h = ta.macd(close, self.macd_fast, self.macd_slow, self.macd_signal_len)
        pdi_val, mdi_val, ax = ta.dmi(self.adx_len, self.adx_smooth)
        cci_val = ta.cci(hlc3, self.cci_len)
        wt_a, wt_b = self.wavetrend(hlc3, self.wt_channel_len, self.wt_average_len)
        return close, e20, e50, e200, rsi14, rsi9, m, s, h, pdi_val, mdi_val, ax, cci_val, wt_a, wt_b

    def on_bar(self):
        st = self.strategy
        close, open_, high, low = self.close, self.open, self.high, self.low
        lorentz_threshold = 4 if self.mode == "Aggressive" else (5 if self.mode == "Balanced" else 6)
        (d_close, d_ema20, d_ema50, d_ema200, d_rsi, d_rsi_fast, d_macd, d_signal, d_hist, d_pdi, d_mdi, d_adx, d_cci, d_wt1, d_wt2) = \
            self.security(None, self.daily_tf, lambda v: self.htf_data(v.close, v.hlc3), lookahead=False)
        (c_close, c_ema20, c_ema50, c_ema200, c_rsi, c_rsi_fast, c_macd, c_signal, c_hist, c_pdi, c_mdi, c_adx, c_cci, c_wt1, c_wt2) = \
            self.security(None, self.confirm_tf, lambda v: self.htf_data(v.close, v.hlc3), lookahead=False)
        ema20 = ta.ema(close, self.ema_fast_len)
        ema50 = ta.ema(close, self.ema_mid_len)
        ema200 = ta.ema(close, self.ema_slow_len)
        rsi = ta.rsi(close, self.rsi_len)
        rsi_fast = ta.rsi(close, self.rsi_fast_len)
        rsi_ma = ta.sma(rsi, self.rsi_ma_len)
        macd_line, signal_line, hist = ta.macd(close, self.macd_fast, self.macd_slow, self.macd_signal_len)
        pdi, mdi, adx = ta.dmi(self.adx_len, self.adx_smooth)
        cci = ta.cci(self.hlc3, self.cci_len)
        wt1, wt2 = self.wavetrend(self.hlc3, self.wt_channel_len, self.wt_average_len)
        atr = ta.atr(self.atr_len)
        daily_bull = bool(d_close > d_ema50 and d_rsi > 50)
        daily_bear = bool(d_close < d_ema50 and d_rsi < 50)
        daily_strong_bull = bool(d_close > d_ema50 and d_ema50 > d_ema200 and d_rsi > 52)
        daily_strong_bear = bool(d_close < d_ema50 and d_ema50 < d_ema200 and d_rsi < 48)
        ch_h = self.H("c_hist")
        c_hist_1 = ch_h[1]
        ch_h.set(c_hist)
        two_hour_bull = bool(c_close > c_ema20 and c_rsi > 50 and c_macd > c_signal)
        two_hour_bear = bool(c_close < c_ema20 and c_rsi < 50 and c_macd < c_signal)
        two_hour_bull_strong = bool(c_close > c_ema50 and c_ema20 > c_ema50 and c_rsi > 50 and c_macd > c_signal)
        two_hour_bear_strong = bool(c_close < c_ema50 and c_ema20 < c_ema50 and c_rsi < 50 and c_macd < c_signal)
        two_hour_bull_recovery = bool(c_hist > c_hist_1 and c_rsi > 45 and c_close > c_ema20)
        two_hour_bear_recovery = bool(c_hist < c_hist_1 and c_rsi < 55 and c_close < c_ema20)
        chart_bull = bool(close > ema20 and ema20 >= ema50)
        chart_bear = bool(close < ema20 and ema20 <= ema50)
        macd_cross_up = ta.crossover(macd_line, signal_line)
        macd_cross_down = ta.crossunder(macd_line, signal_line)
        macd_bull_bars = ta.barssince(macd_cross_up)
        macd_bear_bars = ta.barssince(macd_cross_down)
        macd_bull_recent = (not na(macd_bull_bars)) and macd_bull_bars <= self.macd_cross_active_bars
        macd_bear_recent = (not na(macd_bear_bars)) and macd_bear_bars <= self.macd_cross_active_bars
        hist_h = self.H("hist")
        hist_1 = hist_h[1]
        hist_h.set(hist)
        macd_bull_momentum = bool(macd_line > signal_line and hist > hist_1)
        macd_bear_momentum = bool(macd_line < signal_line and hist < hist_1)
        bull_score = 0
        bull_score += 1 if rsi > 50 else 0
        bull_score += 1 if rsi_fast > rsi else 0
        bull_score += 1 if wt1 > wt2 else 0
        bull_score += 1 if cci > 0 else 0
        bull_score += 1 if (adx >= self.adx_min and pdi > mdi) else 0
        bull_score += 1 if macd_bull_momentum else 0
        bull_score += 1 if (close > ema20 and close > ema50) else 0
        bear_score = 0
        bear_score += 1 if rsi < 50 else 0
        bear_score += 1 if rsi_fast < rsi else 0
        bear_score += 1 if wt1 < wt2 else 0
        bear_score += 1 if cci < 0 else 0
        bear_score += 1 if (adx >= self.adx_min and mdi > pdi) else 0
        bear_score += 1 if macd_bear_momentum else 0
        bear_score += 1 if (close < ema20 and close < ema50) else 0
        bull_lorentz_ok = bull_score >= lorentz_threshold
        bear_lorentz_ok = bear_score >= lorentz_threshold
        pullback_call_now = bool(low <= ema20 or low <= ema50 or rsi < 45)
        pullback_put_now = bool(high >= ema20 or high >= ema50 or rsi > 55)
        bars_since_call_pullback = ta.barssince(pullback_call_now)
        bars_since_put_pullback = ta.barssince(pullback_put_now)
        pullback_call = (not na(bars_since_call_pullback)) and bars_since_call_pullback <= self.pullback_bars
        pullback_put = (not na(bars_since_put_pullback)) and bars_since_put_pullback <= self.pullback_bars
        c_h = self.H("close")
        close_1 = c_h[1]
        c_h.set(close)
        price_reclaim_call = bool(close > ema20 and close > close_1 and close > open_)
        price_reject_put = bool(close < ema20 and close < close_1 and close < open_)
        not_extended_call = bool(close <= ema20 + atr * 2.3)
        not_extended_put = bool(close >= ema20 - atr * 2.3)
        range_high = ta.highest(high, self.chop_lookback)
        range_low = ta.lowest(low, self.chop_lookback)
        rh_h, rl_h = self.H("range_high"), self.H("range_low")
        range_high_1, range_low_1 = rh_h[1], rl_h[1]
        rh_h.set(range_high)
        rl_h.set(range_low)
        range_size = range_high - range_low
        ema_compressed = abs(ema20 - ema50) < atr * self.ema_compression_atr
        weak_adx = adx < self.chop_adx
        tight_range = range_size < atr * 1.6
        inside_range = close < range_high and close > range_low
        chop_zone = bool(self.use_chop_filter and weak_adx and ema_compressed and tight_range and inside_range)
        bull_break_from_chop = bool(close > range_high_1 and macd_bull_momentum and rsi > 50)
        bear_break_from_chop = bool(close < range_low_1 and macd_bear_momentum and rsi < 50)
        trade_allowed_by_chop = (not chop_zone) or bull_break_from_chop or bear_break_from_chop
        if self.mode == "Safe":
            call_bias = daily_bull and (two_hour_bull or two_hour_bull_recovery)
            put_bias = daily_bear and (two_hour_bear or two_hour_bear_recovery)
        else:
            call_bias = daily_bull or two_hour_bull or two_hour_bull_recovery
            put_bias = daily_bear or two_hour_bear or two_hour_bear_recovery
        call_setup = bool(call_bias and pullback_call and macd_bull_recent and macd_bull_momentum and bull_lorentz_ok and price_reclaim_call
                          and chart_bull and not_extended_call and trade_allowed_by_chop)
        put_setup = bool(put_bias and pullback_put and macd_bear_recent and macd_bear_momentum and bear_lorentz_ok and price_reject_put
                         and chart_bear and not_extended_put and trade_allowed_by_chop)
        call_continuation = bool(daily_strong_bull and two_hour_bull_strong and chart_bull and macd_bull_recent and bull_lorentz_ok and close > ema20
                                 and not_extended_call and trade_allowed_by_chop)
        put_continuation = bool(daily_strong_bear and two_hour_bear_strong and chart_bear and macd_bear_recent and bear_lorentz_ok and close < ema20
                                and not_extended_put and trade_allowed_by_chop)
        final_call_setup = call_setup or call_continuation
        final_put_setup = put_setup or put_continuation
        entry_cooldown_ok = na(self.last_entry_bar) or self.bar_index - self.last_entry_bar > self.cooldown_after_entry
        exit_cooldown_ok = na(self.last_exit_bar) or self.bar_index - self.last_exit_bar > self.cooldown_after_exit
        can_enter = entry_cooldown_ok and exit_cooldown_ok
        pos = st.position_size
        call_entry = bool(pos <= 0 and final_call_setup and can_enter)
        put_entry = bool(pos >= 0 and final_put_setup and can_enter)
        call_entry = call_entry and not two_hour_bear_strong
        put_entry = put_entry and not two_hour_bull_strong
        if call_entry:
            if pos < 0:
                st.close("PUT")
            st.entry("CALL", st.long)
            self.last_entry_bar = self.bar_index
            self.entry_bar = self.bar_index
            self.entry_atr = float(atr)
            self.high_since_entry = float(high)
            self.low_since_entry = float(low)
            self.active_stop = close - atr * self.emergency_stop_atr
        if put_entry:
            if pos > 0:
                st.close("CALL")
            st.entry("PUT", st.short)
            self.last_entry_bar = self.bar_index
            self.entry_bar = self.bar_index
            self.entry_atr = float(atr)
            self.high_since_entry = float(high)
            self.low_since_entry = float(low)
            self.active_stop = close + atr * self.emergency_stop_atr
        if pos > 0:
            self.high_since_entry = float(high) if na(self.high_since_entry) else pmath.max(self.high_since_entry, high)
            self.low_since_entry = float(low) if na(self.low_since_entry) else pmath.min(self.low_since_entry, low)
        if pos < 0:
            self.high_since_entry = float(high) if na(self.high_since_entry) else pmath.max(self.high_since_entry, high)
            self.low_since_entry = float(low) if na(self.low_since_entry) else pmath.min(self.low_since_entry, low)
        bars_in_trade = self.bar_index - self.entry_bar if (pos != 0 and not na(self.entry_bar)) else 0
        active_atr = atr if na(self.entry_atr) else self.entry_atr
        avg = st.position_avg_price
        long_emergency_stop = avg - active_atr * self.emergency_stop_atr
        short_emergency_stop = avg + active_atr * self.emergency_stop_atr
        long_profit_move = bool(pos > 0 and self.high_since_entry >= avg + active_atr * self.trail_start_atr)
        short_profit_move = bool(pos < 0 and self.low_since_entry <= avg - active_atr * self.trail_start_atr)
        long_trail_stop = self.high_since_entry - active_atr * self.trail_atr
        short_trail_stop = self.low_since_entry + active_atr * self.trail_atr
        long_break_even_stop = avg + active_atr * 0.10
        short_break_even_stop = avg - active_atr * 0.10
        if pos > 0:
            self.active_stop = pmath.max(long_break_even_stop, long_trail_stop) if long_profit_move else long_emergency_stop
        if pos < 0:
            self.active_stop = pmath.min(short_break_even_stop, short_trail_stop) if short_profit_move else short_emergency_stop
        call_macd_exit = bool(pos > 0 and bars_in_trade >= self.min_hold_bars and macd_cross_down and rsi < rsi_ma and close < ema20 and bear_score >= 4)
        put_macd_exit = bool(pos < 0 and bars_in_trade >= self.min_hold_bars and macd_cross_up and rsi > rsi_ma and close > ema20 and bull_score >= 4)
        call_htf_fail = bool(pos > 0 and bars_in_trade >= self.min_hold_bars and two_hour_bear_strong)
        put_htf_fail = bool(pos < 0 and bars_in_trade >= self.min_hold_bars and two_hour_bull_strong)
        call_deep_fail = bool(pos > 0 and bars_in_trade >= self.min_hold_bars and close < ema50 and macd_line < signal_line and rsi < 45)
        put_deep_fail = bool(pos < 0 and bars_in_trade >= self.min_hold_bars and close > ema50 and macd_line > signal_line and rsi > 55)
        long_no_progress = bool(self.use_theta_protection and pos > 0 and bars_in_trade >= self.theta_check_bars
                                and self.high_since_entry < avg + active_atr * self.min_move_atr_to_hold and not two_hour_bull_strong)
        short_no_progress = bool(self.use_theta_protection and pos < 0 and bars_in_trade >= self.theta_check_bars
                                 and self.low_since_entry > avg - active_atr * self.min_move_atr_to_hold and not two_hour_bear_strong)
        time_exit = bool(pos != 0 and bars_in_trade >= self.max_hold_bars)
        if pos > 0:
            st.exit("CALL Exit", from_entry="CALL", stop=self.active_stop)
        if pos < 0:
            st.exit("PUT Exit", from_entry="PUT", stop=self.active_stop)
        if call_macd_exit or call_htf_fail or call_deep_fail or long_no_progress or time_exit:
            st.close("CALL")
        if put_macd_exit or put_htf_fail or put_deep_fail or short_no_progress or time_exit:
            st.close("PUT")
        call_closed = self.prev_pos > 0 and pos == 0
        put_closed = self.prev_pos < 0 and pos == 0
        if call_closed or put_closed:
            self.last_exit_bar = self.bar_index
        if pos == 0:
            self.entry_bar = NA
            self.entry_atr = NA
            self.high_since_entry = NA
            self.low_since_entry = NA
            self.active_stop = NA
        self.prev_pos = pos
