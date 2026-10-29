"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : Daybreak Strategy
Author       : achirameegasthanne
Source URL   : https://www.tradingview.com/script/MtKHXU6w-Daybreak-Strategy-Achira-Meegasthanne
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-29 by Claude (pine-to-python skill)

Line-for-line translation (1-hour chart only). The high / low of the first bar whose exchange hour is 9 is the opening range (cleared at each daily-period change). Once per cleared day both a buy-stop above the range high plus ATR x sensitivity and a sell-stop below the range low minus ATR x sensitivity are placed (1 unit each), each with an exit order
(take-profit and stop-loss in ticks from the fill). Both pending orders stay until they fill; in the 21:30 - 22:00 Monday-Friday window they are cancelled.
Deviations from the original: none.
Not carried over: the colours and the dashboard / statistics tables (display only).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, na, ta


class DaybreakStrategy(Script):
    TITLE = "Daybreak Strategy"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = {}
    SOURCE = {"id": "MtKHXU6w", "author": "achirameegasthanne", "licence": "not stated", "url": "https://www.tradingview.com/script/MtKHXU6w-Daybreak-Strategy-Achira-Meegasthanne"}

    def init(self):
        i = self.input
        self.sensitivity = i.float(0.5, "Sensitivity")
        self.profit = i.int(40, "Take Profit (in ticks)")
        self.loss = i.int(25, "Stop Loss (in ticks)")
        self.open_range_high = NA
        self.open_range_low = NA
        self.orders_placed = False

    def on_bar(self):
        st = self.strategy
        high, low = self.high, self.low
        atr = ta.atr(14)
        is_1h = self.timeframe.period == "60"
        day_change = ta.change(self.time_fn("D"))
        new_day = (day_change == day_change) and day_change != 0
        is_open_bar = self.hour(self.time) == 9
        if new_day:
            self.open_range_high = NA
            self.open_range_low = NA
            self.orders_placed = False
        if is_open_bar and na(self.open_range_high):
            self.open_range_high = float(high)
            self.open_range_low = float(low)
        if (not self.orders_placed) and (not na(self.open_range_high)) and is_1h:
            st.entry("Long", st.long, stop=self.open_range_high + atr * self.sensitivity, qty=1)
            st.exit("Exit Long", from_entry="Long", profit=self.profit, loss=self.loss)
            st.entry("Short", st.short, stop=self.open_range_low - atr * self.sensitivity, qty=1)
            st.exit("Exit Short", from_entry="Short", profit=self.profit, loss=self.loss)
            self.orders_placed = True
        in_end_session = self.time_in_session("2130-2200:23456") and is_1h
        if in_end_session:
            st.cancel("Long")
            st.cancel("Short")
