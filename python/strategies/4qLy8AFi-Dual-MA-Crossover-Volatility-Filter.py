"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : Dual MA Crossover + Volatility Filter
Author       : Danish7421
Source URL   : https://www.tradingview.com/script/4qLy8AFi-Dual-MA-Crossover-Volatility-Filter
Pine version : v5
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-29 by Claude (pine-to-python skill)

Line-for-line translation. A fast / slow MA cross (EMA / SMA / WMA / HMA) opens a trade while flat when the ATR is expanding (14 over 20), the RSI sits on the right side of its threshold and at least
`Bars to Skip after Open` bars of the trading day have passed. The entry carries an ATR initial stop; once the run reaches `Breakeven Trigger` R the stop moves to the entry price and then trails the best price by an ATR
multiple; a time exit closes the trade after `Time Stop` bars without a new extreme. The stop order is (re-)issued at every script run that sees a position.

Deviations from the original: none.
Not carried over: the MA / stop line plots, the volatility background and alerts (display only).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, color, div, na, pmath, ta


class DualMaCrossoverVolatility(Script):
    TITLE = "Dual MA Crossover + Volatility Filter"
    PINE_VERSION = 5
    OVERLAY = True
    STRATEGY = dict(initial_capital=100000, default_qty_type="cash", commission_type="cash_per_contract", commission_value=2.50, slippage=1)
    SOURCE = {"id": "4qLy8AFi", "author": "Danish7421", "licence": "not stated",
              "url": "https://www.tradingview.com/script/4qLy8AFi-Dual-MA-Crossover-Volatility-Filter"}

    def init(self):
        g = "Moving Averages"
        self.fast_length = self.input.int(20, "Fast MA Length", minval=5, maxval=100, group=g)
        self.slow_length = self.input.int(50, "Slow MA Length", minval=20, maxval=200, group=g)
        self.ma_type = self.input.string("EMA", "MA Type", options=["EMA", "SMA", "WMA", "HMA"], group=g)
        g = "Volatility Filter"
        self.enable_vol_filter = self.input.bool(True, "Enable Volatility Filter", group=g)
        self.atr_filter_length = self.input.int(14, "ATR Filter Period", minval=5, group=g)
        self.atr_compare_length = self.input.int(20, "ATR Comparison Period", minval=10, group=g)
        g = "RSI Filter"
        self.enable_rsi_filter = self.input.bool(True, "Enable RSI Filter", group=g)
        self.rsi_length = self.input.int(14, "RSI Length", minval=5, group=g)
        self.rsi_long_threshold = self.input.int(50, "RSI Long Threshold", minval=30, maxval=70, group=g)
        self.rsi_short_threshold = self.input.int(50, "RSI Short Threshold", minval=30, maxval=70, group=g)
        g = "Time Filter"
        self.enable_time_filter = self.input.bool(True, "Enable Session Filter", group=g)
        self.bars_to_skip = self.input.int(6, "Bars to Skip after Open", minval=0, group=g)
        g = "Risk & Exit Management"
        self.enable_longs = self.input.bool(True, "Enable Longs", group=g)
        self.enable_shorts = self.input.bool(True, "Enable Shorts", group=g)
        self.risk_percent = self.input.float(1.0, "Risk % Per Trade", minval=0.1, maxval=5.0, step=0.1, group=g)
        self.atr_stop_mult = self.input.float(2.0, "Initial Stop ATR Mult", minval=0.5, step=0.1, group=g)
        self.atr_trail_mult = self.input.float(3.0, "Trail ATR Mult", minval=0.5, step=0.1, group=g)
        self.breakeven_trigger = self.input.float(1.0, "Breakeven Trigger (R)", minval=0.5, step=0.1, group=g)
        self.time_stop_bars = self.input.int(10, "Time Stop (Bars)", minval=5, group=g)
        self.bars_since_open = 0
        self.entry_price = NA
        self.current_stop = NA
        self.breakeven_active = False
        self.entry_bar_index = NA
        self.max_price_reached = NA
        self.min_price_reached = NA

    def point_value(self):
        s = self.syminfo.tickerid
        for key, v in (("ES1!", 50.0), ("NQ1!", 20.0), ("YM1!", 5.0), ("RTY1!", 50.0), ("CL1!", 1000.0), ("GC1!", 100.0), ("SI1!", 5000.0)):
            if key in s:
                return v
        return self.syminfo.pointvalue

    def get_ma(self, length):
        if self.ma_type == "SMA":
            return ta.sma(self.close, length)
        if self.ma_type == "WMA":
            return ta.wma(self.close, length)
        if self.ma_type == "HMA":
            return ta.hma(self.close, length)
        return ta.ema(self.close, length)

    def on_bar(self):
        st = self.strategy
        close, high, low = self.close, self.high, self.low
        fast_ma = self.get_ma(self.fast_length)
        slow_ma = self.get_ma(self.slow_length)
        atr_val = ta.atr(self.atr_filter_length)
        atr_comp = ta.atr(self.atr_compare_length)
        rsi_val = ta.rsi(close, self.rsi_length)
        volatility_expanding = (not self.enable_vol_filter) or (atr_val > atr_comp)
        rsi_long_ok = (not self.enable_rsi_filter) or (rsi_val > self.rsi_long_threshold)
        rsi_short_ok = (not self.enable_rsi_filter) or (rsi_val < self.rsi_short_threshold)
        day_change = ta.change(self.time_fn("D"))
        is_new_day = (not na(day_change)) and day_change != 0
        if is_new_day:
            self.bars_since_open = 0
        else:
            self.bars_since_open += 1
        time_filter_passed = (not self.enable_time_filter) or (self.bars_since_open >= self.bars_to_skip)
        long_cross = ta.crossover(fast_ma, slow_ma)
        short_cross = ta.crossunder(fast_ma, slow_ma)
        risk_amount = st.equity * (self.risk_percent / 100)
        stop_dist = atr_val * self.atr_stop_mult
        point_val = self.point_value()
        pos_size = pmath.floor(div(risk_amount, stop_dist * point_val))
        final_qty = pmath.max(1, pos_size)
        can_enter_long = self.enable_longs and long_cross and volatility_expanding and rsi_long_ok and time_filter_passed and st.position_size == 0
        can_enter_short = self.enable_shorts and short_cross and volatility_expanding and rsi_short_ok and time_filter_passed and st.position_size == 0
        if can_enter_long:
            st.entry("Long", st.long, qty=final_qty, comment="MA Cross Up")
            self.entry_price = float(close)
            self.current_stop = close - stop_dist
            self.breakeven_active = False
            self.entry_bar_index = self.bar_index
            self.max_price_reached = float(close)
        if can_enter_short:
            st.entry("Short", st.short, qty=final_qty, comment="MA Cross Down")
            self.entry_price = float(close)
            self.current_stop = close + stop_dist
            self.breakeven_active = False
            self.entry_bar_index = self.bar_index
            self.min_price_reached = float(close)
        if st.position_size > 0:
            self.max_price_reached = pmath.max(self.max_price_reached, high)
            run_in_r = div(self.max_price_reached - self.entry_price, stop_dist)
            if (not self.breakeven_active) and run_in_r >= self.breakeven_trigger:
                self.current_stop = self.entry_price
                self.breakeven_active = True
            if self.breakeven_active:
                trail_level = self.max_price_reached - (atr_val * self.atr_trail_mult)
                self.current_stop = pmath.max(self.current_stop, trail_level)
            hh = ta.highest(high, self.time_stop_bars)
            hh_h = self.H("hh")
            hh_1 = hh_h[1]
            hh_h.set(ta.highest(high, self.time_stop_bars))
            no_new_high = hh <= hh_1
            if (self.bar_index - self.entry_bar_index >= self.time_stop_bars) and no_new_high:
                st.close("Long", comment="Time Exit")
        if st.position_size < 0:
            self.min_price_reached = pmath.min(self.min_price_reached, low)
            run_in_r = div(self.entry_price - self.min_price_reached, stop_dist)
            if (not self.breakeven_active) and run_in_r >= self.breakeven_trigger:
                self.current_stop = self.entry_price
                self.breakeven_active = True
            if self.breakeven_active:
                trail_level = self.min_price_reached + (atr_val * self.atr_trail_mult)
                self.current_stop = pmath.min(self.current_stop, trail_level)
            ll = ta.lowest(low, self.time_stop_bars)
            ll_h = self.H("ll")
            ll_1 = ll_h[1]
            ll_h.set(ta.lowest(low, self.time_stop_bars))
            no_new_low = ll >= ll_1
            if (self.bar_index - self.entry_bar_index >= self.time_stop_bars) and no_new_low:
                st.close("Short", comment="Time Exit")
        if st.position_size != 0:
            st.exit("Exit", "Long", stop=self.current_stop, comment_loss="Stop", comment_profit="Trail/BE")
            st.exit("Exit", "Short", stop=self.current_stop, comment_loss="Stop", comment_profit="Trail/BE")
