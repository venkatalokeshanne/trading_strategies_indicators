"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : Slope & MA Cross + Acc + Range Filter
Author       : hkbayram
Source URL   : https://www.tradingview.com/script/MqmIh0D9
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-29 by Claude (pine-to-python skill)

Line-for-line translation (market orders at the next open). A moving average (Hull 100 by default; ALMA / EMA / VWMA selectable) gives a slope (change over the lookback) and an acceleration (change of the slope). The slope angle (percentage slope times a sensitivity, arctangent in degrees) must reach the minimum for a trend (range filter).
Entry modes: slope zero-cross, price / MA cross, and (default) acceleration zero-cross, plus a re-entry on a close crossing the previous bar's extreme inside a valid trend; exits on slope / price crosses or the reverse acceleration cross. While in a position one exit order per side is re-issued each bar: a percentage stop that can be tightened by a "shrinking" stop (once the bar's profit passes a minimum, while the slope decelerates),
an optional target and a trailing stop (activation price at the start profit, offset = distance in ticks).
Deviations from the original: none.
Not carried over: the dashboard table (display only).
────────────────────────────────────────────────────────────────────────
"""

import math

from pinelib import NA, Script, div, na, pmath, ta


class SlopeMaCross(Script):
    TITLE = "Slope & MA Cross + Acc + Range Filter"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(margin_long=100, margin_short=100)
    SOURCE = {"id": "MqmIh0D9", "author": "hkbayram", "licence": "not stated", "url": "https://www.tradingview.com/script/MqmIh0D9"}

    def init(self):
        i = self.input
        g = "Moving Average Settings"
        self.ma_type = i.string("Hull MA", "MA Type", options=["ALMA", "EMA", "VWMA", "Hull MA"], group=g)
        self.ma_len = i.int(100, "MA Period", minval=1, group=g)
        self.slope_len = i.int(1, "Slope Lookback", minval=1, group=g)
        self.alma_offset = i.float(0.85, "ALMA Offset", minval=0.0, maxval=1.0, step=0.05, group=g)
        self.alma_sigma = i.float(6.0, "ALMA Sigma", group=g)
        g = "Ranging Market Filter (Slope Angle)"
        self.use_range_filter = i.bool(True, "Enable Range Filter", group=g)
        self.min_angle = i.float(35.0, "Minimum Trend Angle (°)", minval=0.1, maxval=89.0, step=0.5, group=g)
        self.angle_mult = i.float(10.0, "Angle Sensitivity Multiplier", minval=1.0, maxval=500.0, step=1.0, group=g)
        g = "Entry and Exit Modes"
        self.use_slope_entry = i.bool(False, "Enter on Slope 0 Cross", group=g)
        self.use_price_entry = i.bool(False, "Enter on Price / MA Cross", group=g)
        self.use_acc_entry = i.bool(True, "Enter on Slope Acceleration 0 Cross", group=g)
        self.use_acc_exit = i.bool(True, "Exit on Reverse Acceleration Cross", group=g)
        self.allow_reentry = i.bool(True, "Allow Re-Entry During Trend", group=g)
        g = "Fixed Stop Loss & Take Profit"
        self.use_sl = i.bool(True, "Enable Fixed / Dynamic SL", group=g)
        self.sl_perc = i.float(1.0, "Entry-Based SL (%)", minval=0.05, step=0.05, group=g) / 100
        self.use_tp = i.bool(False, "Enable Take Profit (TP)", group=g)
        self.tp_perc = i.float(2.0, "Take Profit (%)", minval=0.1, step=0.1, group=g) / 100
        g = "Trailing Stop Settings"
        self.use_trail = i.bool(True, "Enable Trailing Stop", group=g)
        self.trail_start = i.float(1.5, "Trailing Activation Profit (%)", minval=0.1, step=0.05, group=g) / 100
        self.trail_dist = i.float(1.0, "Trailing Distance (%)", minval=0.1, step=0.05, group=g) / 100
        g = "Shrinking Stop Loss"
        self.use_shrinking_sl = i.bool(True, "Enable Shrinking SL", group=g)
        self.shrink_min_profit = i.float(1.5, "Min Profit for Tightening (%)", minval=0.1, step=0.1, group=g) / 100
        self.shrink_mult = i.float(0.5, "Tightening Multiplier", minval=0.1, maxval=1.0, step=0.05, group=g)
        self.use_momentum_trigger = i.bool(True, "Tighten Only When Slope Decelerates", group=g)
        self.shrinking_sl_long = NA
        self.shrinking_sl_short = NA
        self.last_entry_bar = -1

    def get_ma(self):
        close = self.close
        t = self.ma_type
        if t == "ALMA":
            return ta.alma(close, self.ma_len, self.alma_offset, self.alma_sigma)
        if t == "EMA":
            return ta.ema(close, self.ma_len)
        if t == "VWMA":
            return ta.vwma(close, self.ma_len)
        if t == "Hull MA":
            return ta.hma(close, self.ma_len)
        return ta.alma(close, self.ma_len, self.alma_offset, self.alma_sigma)

    def on_bar(self):
        st = self.strategy
        close, high, low = self.close, self.high, self.low
        main_ma = self.get_ma()
        mh = self.H("ma")
        ma_back = mh[self.slope_len]
        mh.set(main_ma)
        ma_slope = main_ma - ma_back
        sh = self.H("slope")
        slope_1 = sh[1]
        sh.set(ma_slope)
        ma_accel = ma_slope - slope_1
        slope_change_perc = div(main_ma - ma_back, ma_back) * 100
        slope_angle = math.degrees(math.atan(slope_change_perc * self.angle_mult))
        is_trending_long = (slope_angle >= self.min_angle) if self.use_range_filter else True
        is_trending_short = (slope_angle <= -self.min_angle) if self.use_range_filter else True
        slope_fading_long = ma_slope < slope_1 and ma_slope > 0
        slope_fading_short = ma_slope > slope_1 and ma_slope < 0
        slope_crossed_up = ta.crossover(ma_slope, 0.0)
        slope_crossed_down = ta.crossunder(ma_slope, 0.0)
        price_crossed_up = ta.crossover(close, main_ma)
        price_crossed_down = ta.crossunder(close, main_ma)
        acc_crossed_up = ta.crossover(ma_accel, 0.0)
        acc_crossed_down = ta.crossunder(ma_accel, 0.0)
        reentry_up = ta.crossover(close, self.high[1])
        reentry_down = ta.crossunder(close, self.low[1])
        in_long_trend = ma_slope > 0 and close > main_ma
        in_short_trend = ma_slope < 0 and close < main_ma
        long_cross_signal = (self.use_slope_entry and slope_crossed_up) or (self.use_price_entry and price_crossed_up) or (self.use_acc_entry and acc_crossed_up)
        short_cross_signal = (self.use_slope_entry and slope_crossed_down) or (self.use_price_entry and price_crossed_down) or (self.use_acc_entry and acc_crossed_down)
        long_reentry_signal = self.allow_reentry and in_long_trend and reentry_up
        short_reentry_signal = self.allow_reentry and in_short_trend and reentry_down
        long_final_entry = (long_cross_signal or long_reentry_signal) and is_trending_long
        short_final_entry = (short_cross_signal or short_reentry_signal) and is_trending_short
        exit_long_condition = slope_crossed_down or price_crossed_down or (self.use_acc_exit and acc_crossed_down)
        exit_short_condition = slope_crossed_up or price_crossed_up or (self.use_acc_exit and acc_crossed_up)
        typical_price = (high + low + close) / 3
        avg = st.position_avg_price
        if st.position_size > 0:
            current_profit_ratio = div(high - avg, avg)
            profit_ok = current_profit_ratio >= self.shrink_min_profit
            momentum_ok = slope_fading_long if self.use_momentum_trigger else True
            if profit_ok and momentum_ok:
                base_stop = typical_price * (1 - self.sl_perc * self.shrink_mult)
                min_allowed_stop = avg * (1 - self.sl_perc)
                calculated_sl = pmath.max(base_stop, min_allowed_stop)
                self.shrinking_sl_long = calculated_sl if na(self.shrinking_sl_long) else pmath.max(self.shrinking_sl_long, calculated_sl)
        else:
            self.shrinking_sl_long = NA
        if st.position_size < 0:
            current_profit_ratio = div(avg - low, avg)
            profit_ok = current_profit_ratio >= self.shrink_min_profit
            momentum_ok = slope_fading_short if self.use_momentum_trigger else True
            if profit_ok and momentum_ok:
                base_stop = typical_price * (1 + self.sl_perc * self.shrink_mult)
                max_allowed_stop = avg * (1 + self.sl_perc)
                calculated_sl = pmath.min(base_stop, max_allowed_stop)
                self.shrinking_sl_short = calculated_sl if na(self.shrinking_sl_short) else pmath.min(self.shrinking_sl_short, calculated_sl)
        else:
            self.shrinking_sl_short = NA
        entry_sl_long = avg * (1 - self.sl_perc)
        entry_sl_short = avg * (1 + self.sl_perc)
        if st.position_size > 0:
            final_long_stop = pmath.max(entry_sl_long, self.shrinking_sl_long) if (self.use_shrinking_sl and not na(self.shrinking_sl_long)) else entry_sl_long
        else:
            final_long_stop = NA
        if st.position_size < 0:
            final_short_stop = pmath.min(entry_sl_short, self.shrinking_sl_short) if (self.use_shrinking_sl and not na(self.shrinking_sl_short)) else entry_sl_short
        else:
            final_short_stop = NA
        if st.position_size > 0 and exit_long_condition:
            st.close("Base MA Long", comment="Close: Long Signal")
        if st.position_size < 0 and exit_short_condition:
            st.close("Base MA Short", comment="Close: Short Signal")
        can_enter_this_bar = self.last_entry_bar != self.bar_index
        if can_enter_this_bar and st.position_size == 0:
            if long_final_entry:
                st.entry("Base MA Long", st.long, comment="Long Cross" if long_cross_signal else "Long Re-Entry")
                self.last_entry_bar = self.bar_index
            elif short_final_entry:
                st.entry("Base MA Short", st.short, comment="Short Cross" if short_cross_signal else "Short Re-Entry")
                self.last_entry_bar = self.bar_index
        long_tp_price = avg * (1 + self.tp_perc) if self.use_tp else NA
        short_tp_price = avg * (1 - self.tp_perc) if self.use_tp else NA
        mintick = self.syminfo.mintick
        long_t_trigger = avg * (1 + self.trail_start) if self.use_trail else NA
        long_t_offset = pmath.max(1, pmath.round(div(avg * self.trail_dist, mintick))) if self.use_trail else NA
        short_t_trigger = avg * (1 - self.trail_start) if self.use_trail else NA
        short_t_offset = pmath.max(1, pmath.round(div(avg * self.trail_dist, mintick))) if self.use_trail else NA
        st.exit("Exit_L", from_entry="Base MA Long", stop=final_long_stop if self.use_sl else NA, limit=long_tp_price,
                trail_price=long_t_trigger if self.use_trail else NA, trail_offset=long_t_offset if self.use_trail else NA,
                comment_loss="SL/Shrink", comment_trailing="Trailing Active")
        st.exit("Exit_S", from_entry="Base MA Short", stop=final_short_stop if self.use_sl else NA, limit=short_tp_price,
                trail_price=short_t_trigger if self.use_trail else NA, trail_offset=short_t_offset if self.use_trail else NA,
                comment_loss="SL/Shrink", comment_trailing="Trailing Active")
