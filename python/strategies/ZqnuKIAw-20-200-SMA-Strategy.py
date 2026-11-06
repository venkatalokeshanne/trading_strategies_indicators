"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : 20 / 200 SMA Strategy
Author       : gpmpastorsc
Source URL   : https://www.tradingview.com/script/ZqnuKIAw-20-200-SMA-Strategy
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-29 by Claude (pine-to-python skill)

Line-for-line translation (process_orders_on_close). A 20 / 200 SMA cross arms a side; the entry is the original armed-cross entry, a pullback of the close through the 20 SMA in the trend direction, or a relaxed close-vs-20 SMA entry, with optional slope / candle colour / distance filters, while flat. The stop is the last opposing candle beyond the 200 SMA, a fixed distance or the recent swing; the target is a fixed number of points; both are placed with the entry.

Deviations from the original: none.
Not carried over: SMA plots, debug markers and the stop / target lines (display only).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, na, pmath, ta


class SMA20200Bot(Script):
    TITLE = "20 / 200 SMA Bot Strategy - Clean Usable Version"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(pyramiding=0, initial_capital=50000, default_qty_type="fixed", default_qty_value=1, process_orders_on_close=True)
    SOURCE = {"id": "ZqnuKIAw", "author": "gpmpastorsc", "licence": "not stated",
              "url": "https://www.tradingview.com/script/ZqnuKIAw-20-200-SMA-Strategy"}

    def init(self):
        i = self.input
        g = "Main Settings"
        self.trade_direction = i.string("Both", "Trade Direction", options=["Both", "Buy Only", "Sell Only"], group=g)
        self.fast_length = i.int(20, "Fast SMA Length", minval=1, group=g)
        self.slow_length = i.int(200, "Slow SMA Length", minval=1, group=g)
        self.entry_strictness = i.string("Trend Pullback Entry", "Entry Strictness", options=["Original Cross Entry", "Trend Pullback Entry", "Relaxed Testing Entry"], group=g)
        self.entry_window_bars = i.int(100, "Bars Allowed After SMA Cross", minval=1, maxval=1000, group=g)
        g = "Risk Settings"
        self.take_profit_points = i.float(100.0, "Take Profit Points", minval=0.25, step=0.25, group=g)
        self.stop_loss_mode = i.string("Last Opposing Candle Beyond 200 SMA", "Stop Loss Method", options=["Last Opposing Candle Beyond 200 SMA", "Fixed Points", "Recent Swing"], group=g)
        self.fixed_stop_points = i.float(30.0, "Fixed / Fallback Stop Points", minval=0.25, step=0.25, group=g)
        self.stop_buffer_points = i.float(1.0, "Stop Buffer Points", minval=0.0, step=0.25, group=g)
        self.opposing_lookback = i.int(300, "Opposing Candle Lookback", minval=1, maxval=2000, group=g)
        self.swing_lookback = i.int(10, "Recent Swing Lookback", minval=1, maxval=500, group=g)
        self.use_opposing_wick = i.bool(True, "Opposing Candle Stop Uses Wick", group=g)
        g = "Optional Filters"
        self.use_slope_filter = i.bool(False, "Use 200 SMA Slope Filter", group=g)
        self.slope_lookback = i.int(5, "200 SMA Slope Lookback", minval=1, maxval=100, group=g)
        self.use_candle_color_filter = i.bool(False, "Use Candle Color Filter", group=g)
        self.use_distance_filter = i.bool(False, "Avoid Entries Too Far From 20 SMA", group=g)
        self.max_distance_from_20 = i.float(50.0, "Max Distance From 20 SMA", minval=0.25, step=0.25, group=g)
        self.long_armed = False
        self.short_armed = False
        self.long_cross_bar = NA
        self.short_cross_bar = NA

    def on_bar(self):
        st = self.strategy
        close, open_, high, low = self.close, self.open, self.high, self.low
        allow_long = self.trade_direction == "Both" or self.trade_direction == "Buy Only"
        allow_short = self.trade_direction == "Both" or self.trade_direction == "Sell Only"
        fast_sma = ta.sma(close, self.fast_length)
        slow_sma = ta.sma(close, self.slow_length)
        bull_cross = ta.crossover(fast_sma, slow_sma)
        bear_cross = ta.crossunder(fast_sma, slow_sma)
        fast_above_slow = fast_sma > slow_sma
        fast_below_slow = fast_sma < slow_sma
        close_above_fast = close > fast_sma
        close_below_fast = close < fast_sma
        bull_candle = close > open_
        bear_candle = close < open_
        slow_h = self.H("slow_sma")
        slow_back = slow_h[self.slope_lookback]
        slow_h.set(slow_sma)
        slow_sma_rising = slow_sma > slow_back
        slow_sma_falling = slow_sma < slow_back
        distance_from_20 = abs(close - fast_sma)
        if bull_cross:
            self.long_armed = True
            self.short_armed = False
            self.long_cross_bar = self.bar_index
        if bear_cross:
            self.short_armed = True
            self.long_armed = False
            self.short_cross_bar = self.bar_index
        long_window_valid = self.long_armed and (not na(self.long_cross_bar)) and self.bar_index - self.long_cross_bar <= self.entry_window_bars
        short_window_valid = self.short_armed and (not na(self.short_cross_bar)) and self.bar_index - self.short_cross_bar <= self.entry_window_bars
        original_long = long_window_valid and close_above_fast
        original_short = short_window_valid and close_below_fast
        pullback_up = ta.crossover(close, fast_sma)
        pullback_dn = ta.crossunder(close, fast_sma)
        trend_pullback_long = fast_above_slow and pullback_up
        trend_pullback_short = fast_below_slow and pullback_dn
        relaxed_long = fast_above_slow and close_above_fast
        relaxed_short = fast_below_slow and close_below_fast
        if self.entry_strictness == "Original Cross Entry":
            base_long, base_short = original_long, original_short
        elif self.entry_strictness == "Trend Pullback Entry":
            base_long, base_short = trend_pullback_long, trend_pullback_short
        else:
            base_long, base_short = relaxed_long, relaxed_short
        long_slope_ok = slow_sma_rising if self.use_slope_filter else True
        short_slope_ok = slow_sma_falling if self.use_slope_filter else True
        long_candle_ok = bull_candle if self.use_candle_color_filter else True
        short_candle_ok = bear_candle if self.use_candle_color_filter else True
        distance_ok = (distance_from_20 <= self.max_distance_from_20) if self.use_distance_filter else True
        long_signal = allow_long and base_long and long_slope_ok and long_candle_ok and distance_ok and st.position_size == 0
        short_signal = allow_short and base_short and short_slope_ok and short_candle_ok and distance_ok and st.position_size == 0
        buy_opposing = close < open_ and close < slow_sma
        sell_opposing = close > open_ and close > slow_sma
        buy_opp_bars_ago = ta.barssince(buy_opposing)
        sell_opp_bars_ago = ta.barssince(sell_opposing)
        buy_val = ta.valuewhen(buy_opposing, low if self.use_opposing_wick else pmath.min(open_, close), 0)
        sell_val = ta.valuewhen(sell_opposing, high if self.use_opposing_wick else pmath.max(open_, close), 0)
        buy_opp_stop = buy_val if buy_opp_bars_ago <= self.opposing_lookback else NA
        sell_opp_stop = sell_val if sell_opp_bars_ago <= self.opposing_lookback else NA
        long_stop_by_opposing = buy_opp_stop - self.stop_buffer_points
        short_stop_by_opposing = sell_opp_stop + self.stop_buffer_points
        long_stop_by_fixed = close - self.fixed_stop_points
        short_stop_by_fixed = close + self.fixed_stop_points
        long_stop_by_swing = ta.lowest(low, self.swing_lookback) - self.stop_buffer_points
        short_stop_by_swing = ta.highest(high, self.swing_lookback) + self.stop_buffer_points
        if self.stop_loss_mode == "Last Opposing Candle Beyond 200 SMA":
            sel_long, sel_short = long_stop_by_opposing, short_stop_by_opposing
        elif self.stop_loss_mode == "Fixed Points":
            sel_long, sel_short = long_stop_by_fixed, short_stop_by_fixed
        else:
            sel_long, sel_short = long_stop_by_swing, short_stop_by_swing
        final_long_stop = sel_long if (not na(sel_long)) and sel_long < close else long_stop_by_fixed
        final_short_stop = sel_short if (not na(sel_short)) and sel_short > close else short_stop_by_fixed
        long_target = close + self.take_profit_points
        short_target = close - self.take_profit_points
        if long_signal:
            st.entry("BUY", st.long)
            st.exit("BUY TP/SL", from_entry="BUY", stop=final_long_stop, limit=long_target)
            self.long_armed = False
        if short_signal:
            st.entry("SELL", st.short)
            st.exit("SELL TP/SL", from_entry="SELL", stop=final_short_stop, limit=short_target)
            self.short_armed = False
