"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : Traffic Light Strategy -Power of stocks
Author       : The_Stock_Yogi
Source URL   : https://www.tradingview.com/script/CzrYjKOp-Traffic-Light-Strategy-Power-of-stocks
Pine version : v5
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. `ta.change(time("D")) != 0` is na on the first bar, and Pine treats
an na condition as false (Python would treat nan != 0 as True), so it is guarded explicitly.
`isRed[1]`/`isGreen[1]` are written as the previous bar's close/open comparison, which is what
they evaluate to. strategy.exit is re-issued on every bar in a position with the stored
stop/target, so it first works on the bar after the fill bar, as in Pine. The 9:15 rule only
matters on a 1-minute chart (it is the Indian open); on US 1-minute bars it never triggers.

Deviations from the original: none.
Not carried over: alert_message texts; bgcolor highlight and plot styles (cosmetic).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, color, na, pmath, ta


class TrafficLightStrategy(Script):
    TITLE = "Traffic Light Strategy -Power of stocks"
    PINE_VERSION = 5
    OVERLAY = True
    STRATEGY = dict(initial_capital=100000, default_qty_type="cash", default_qty_value=100000)
    SOURCE = {"id": "CzrYjKOp", "author": "The_Stock_Yogi", "licence": "not stated",
              "url": "https://www.tradingview.com/script/CzrYjKOp-Traffic-Light-Strategy-Power-of-stocks"}

    def init(self):
        self.rr_ratio = self.input.float(2.0, "Risk to Reward Ratio", minval=0.1)
        self.use_max_sl_filter = self.input.bool(False, "Enable Max SL Point Filter?")
        self.max_sl_points = self.input.float(100.0, "Max SL Filter (Index Points)")
        self.exit_hour = self.input.int(15, "Exit Hour (24hr)", minval=0, maxval=23)
        self.exit_min = self.input.int(20, "Exit Minute", minval=0, maxval=59)
        self.hi = NA
        self.lo = NA
        self.pair_found = False
        self.trade_count = 0
        self.current_stop = NA
        self.current_target = NA

    def on_bar(self):
        is_1_minute = self.timeframe.isintraday and self.timeframe.multiplier == 1
        chg = ta.change(self.time_fn("D"))
        is_new_day = (not na(chg)) and chg != 0
        if is_new_day:
            self.pair_found = False
            self.hi = NA
            self.lo = NA
            self.trade_count = 0
        is_green = self.close > self.open
        is_red = self.close < self.open
        is_first_candle = self.hour() == 9 and self.minute() == 15
        can_search = not (is_1_minute and is_first_candle)
        if not self.pair_found and not is_new_day and can_search:
            # hour[1]/minute[1] are na on the first bar
            prev_hour = self.hour(self.time[1]) if self.bar_index > 0 else NA
            prev_minute = self.minute(self.time[1]) if self.bar_index > 0 else NA
            prev_can_search = not (is_1_minute and prev_hour == 9 and prev_minute == 15)
            prev_red = self.close[1] < self.open[1]
            prev_green = self.close[1] > self.open[1]
            if prev_can_search and ((is_green and prev_red) or (is_red and prev_green)):
                temp_hi = pmath.max(self.high, self.high[1])
                temp_lo = pmath.min(self.low, self.low[1])
                range_size = temp_hi - temp_lo
                is_range_valid = (not self.use_max_sl_filter) or (range_size <= self.max_sl_points)
                if is_range_valid:
                    self.hi = temp_hi
                    self.lo = temp_lo
                    self.pair_found = True
        st = self.strategy
        cross_up = ta.crossover(self.close, self.hi)         # v5 evaluates every operand
        cross_dn = ta.crossunder(self.close, self.lo)
        long_condition = self.pair_found and cross_up and st.position_size == 0 and self.trade_count < 3
        short_condition = self.pair_found and cross_dn and st.position_size == 0 and self.trade_count < 3
        if long_condition:
            self.current_stop = self.lo
            self.current_target = self.hi + ((self.hi - self.lo) * self.rr_ratio)
            self.trade_count += 1
            st.entry("Long", st.long, comment="entry")
        if short_condition:
            self.current_stop = self.hi
            self.current_target = self.lo - ((self.hi - self.lo) * self.rr_ratio)
            self.trade_count += 1
            st.entry("Short", st.short, comment="entry")
        if st.position_size > 0:
            st.exit("Exit Long", "Long", stop=self.current_stop, limit=self.current_target, comment="exit")
        if st.position_size < 0:
            st.exit("Exit Short", "Short", stop=self.current_stop, limit=self.current_target, comment="exit")
        time_exit = self.hour() == self.exit_hour and self.minute() >= self.exit_min
        if time_exit and st.position_size != 0:
            st.close_all(comment="Time Exit")
        self.plot(self.hi if self.pair_found else NA, color=color.new(color.green, 20), linewidth=2, title="Pair High")
        self.plot(self.lo if self.pair_found else NA, color=color.new(color.red, 20), linewidth=2, title="Pair Low")
        self.plot(self.current_target if st.position_size != 0 else NA, color=color.lime, title="Active Target")
        self.plot(self.current_stop if st.position_size != 0 else NA, color=color.red, title="Active Stop")
