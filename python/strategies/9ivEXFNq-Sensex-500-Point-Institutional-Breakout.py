"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : Sensex 9:45 3-Trade Limit Breakout
Author       : money-alchemist
Source URL   : https://www.tradingview.com/script/9ivEXFNq-Sensex-500-Point-Institutional-Breakout
Pine version : v5
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. At the 09:45 bar the grid lines either side of the open (floor / ceil to `increment`) are
stored with targets one increment beyond and the daily trade counter is reset. Between 09:45 and 15:15 (bar start), when
flat and with fewer than `max_trades` trades, a close at or above the upper line goes long and at or below the lower line
short. The initial stop is 100 points away and moves to break-even once the favourable extreme is 200 points from the
average price (at that bar's close). While a position is open at the close one exit (limit = target of its side, stop =
the stop var) is issued, so it first works on the bar after the fill. The 15:25 bar closes everything. `time(...)` used
as a condition is true when it is not na.

Deviations from the original: none.
Not carried over: the trade labels and level plots (cosmetic).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, color, div, na, pmath


class SensexThreeTrade(Script):
    TITLE = "Sensex 9:45 3-Trade Limit Breakout"
    PINE_VERSION = 5
    OVERLAY = True
    STRATEGY = dict(initial_capital=100000)
    SOURCE = {"id": "9ivEXFNq", "author": "money-alchemist", "licence": "not stated",
              "url": "https://www.tradingview.com/script/9ivEXFNq-Sensex-500-Point-Institutional-Breakout"}

    def init(self):
        self.increment = self.input.int(500, "Round Number Increment")
        self.sl_points = self.input.int(100, "Initial SL")
        self.be_trigger = self.input.int(200, "Move to BE Trigger")
        self.max_trades = self.input.int(3, "Max Trades Per Day")
        self.session_start_hour = self.input.int(9, "Start Hour")
        self.session_start_min = self.input.int(45, "Start Minute")
        self.upper_level = NA
        self.lower_level = NA
        self.tp_upper = NA
        self.tp_lower = NA
        self.active_sl = NA
        self.trail_activated = False
        self.trade_count = 0

    def on_bar(self):
        is_start_time = self.hour() == self.session_start_hour and self.minute() == self.session_start_min
        can_trade = not na(self.time_fn(None, "0945-1515"))
        if is_start_time:
            current_price = float(self.open)
            self.lower_level = pmath.floor(div(current_price, self.increment)) * self.increment
            self.upper_level = pmath.ceil(div(current_price, self.increment)) * self.increment
            self.tp_upper = self.upper_level + self.increment
            self.tp_lower = self.lower_level - self.increment
            self.trail_activated = False
            self.trade_count = 0
        st = self.strategy
        long_condition = ((not is_start_time) and self.close >= self.upper_level and can_trade
                          and st.position_size == 0 and self.trade_count < self.max_trades)
        short_condition = ((not is_start_time) and self.close <= self.lower_level and can_trade
                           and st.position_size == 0 and self.trade_count < self.max_trades)
        if long_condition:
            st.entry("Long", st.long)
            self.active_sl = self.close - self.sl_points
            self.trail_activated = False
            self.trade_count += 1
        if short_condition:
            st.entry("Short", st.short)
            self.active_sl = self.close + self.sl_points
            self.trail_activated = False
            self.trade_count += 1
        if st.position_size > 0:
            if (not self.trail_activated) and self.high >= st.position_avg_price + self.be_trigger:
                self.active_sl = st.position_avg_price
                self.trail_activated = True
        if st.position_size < 0:
            if (not self.trail_activated) and self.low <= st.position_avg_price - self.be_trigger:
                self.active_sl = st.position_avg_price
                self.trail_activated = True
        if st.position_size != 0:
            st.exit("Exit", limit=(self.tp_upper if st.position_size > 0 else self.tp_lower), stop=self.active_sl)
        if not na(self.time_fn(None, "1525-1530")):
            st.close_all("EOD")
        self.plot(self.upper_level, "Entry High", color=color.green, linewidth=2)
        self.plot(self.lower_level, "Entry Low", color=color.red, linewidth=2)
