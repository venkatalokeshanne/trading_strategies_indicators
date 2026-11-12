"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : Sensex 9:45 Break-Even @ 200pts
Author       : money-alchemist
Source URL   : https://www.tradingview.com/script/EERPSUNJ-Sensex-Institutional-Level-Breakout-500-Point-Grids
Pine version : v5
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. At the 09:45 bar the round-number grid lines either side of the open are stored (floor /
ceil to `increment`) with targets one increment beyond. Between 09:45 and 15:15 (bar start), when flat, a close crossing under
the upper line goes LONG and a close crossing under the lower line goes SHORT (as written). The initial stop is 100 points
away; once the favourable extreme has moved 200 points from the average price the stop moves to break-even. While a
position is open at the close a single exit (limit at the target of its side, stop at the stop var) is issued, so it first
works on the bar after the fill. The 15:25 bar closes everything. `time(...)` used as a condition is true when it is not na.

Deviations from the original: none.
Not carried over: the level plots and the stop cross markers (cosmetic).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, color, div, na, pmath, ta


class SensexBreakEven(Script):
    TITLE = "Sensex 9:45 Break-Even @ 200pts"
    PINE_VERSION = 5
    OVERLAY = True
    STRATEGY = dict(initial_capital=100000)
    SOURCE = {"id": "EERPSUNJ", "author": "money-alchemist", "licence": "not stated",
              "url": "https://www.tradingview.com/script/EERPSUNJ-Sensex-Institutional-Level-Breakout-500-Point-Grids"}

    def init(self):
        self.increment = self.input.int(500, "Round Number Increment", minval=100)
        self.sl_points = self.input.int(100, "Initial Stop Loss Points")
        self.be_trigger = self.input.int(200, "Move to BE Trigger Points")
        self.session_start_hour = self.input.int(9, "Start Hour")
        self.session_start_min = self.input.int(45, "Start Minute")
        self.upper_level = NA
        self.lower_level = NA
        self.tp_upper = NA
        self.tp_lower = NA
        self.active_sl = NA
        self.trail_activated = False

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
        st = self.strategy
        cross_up_level = ta.crossunder(self.close, self.upper_level)
        cross_lo_level = ta.crossunder(self.close, self.lower_level)
        long_condition = cross_up_level and can_trade and st.position_size == 0
        short_condition = cross_lo_level and can_trade and st.position_size == 0
        if long_condition:
            st.entry("Long", st.long)
            self.active_sl = self.close - self.sl_points
            self.trail_activated = False
        if short_condition:
            st.entry("Short", st.short)
            self.active_sl = self.close + self.sl_points
            self.trail_activated = False
        if st.position_size > 0:
            if (not self.trail_activated) and self.high >= st.position_avg_price + self.be_trigger:
                self.active_sl = st.position_avg_price
                self.trail_activated = True
        if st.position_size < 0:
            if (not self.trail_activated) and self.low <= st.position_avg_price - self.be_trigger:
                self.active_sl = st.position_avg_price
                self.trail_activated = True
        if st.position_size != 0:
            st.exit("Exit", qty_percent=100, limit=(self.tp_upper if st.position_size > 0 else self.tp_lower), stop=self.active_sl)
        if not na(self.time_fn(None, "1525-1530")):
            st.close_all("EOD Square-off")
        self.plot(self.upper_level, "Entry High", color=color.green, linewidth=2)
        self.plot(self.lower_level, "Entry Low", color=color.red, linewidth=2)
