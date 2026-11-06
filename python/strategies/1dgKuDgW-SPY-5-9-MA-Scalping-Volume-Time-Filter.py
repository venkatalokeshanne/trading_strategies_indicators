"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : SPY 5/9 MA Scalping + Volume + Time Filter
Author       : MaGiCapital
Source URL   : https://www.tradingview.com/script/1dgKuDgW-SPY-5-9-MA-Scalping-Volume-Time-Filter
Pine version : v5
Licence      : Mozilla Public License 2.0
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. The time window (09:32-11:12 New York) is built with
timestamp("America/New_York", year, month, dayofmonth, ...) exactly as in the original, so
year/month/dayofmonth come from the exchange timezone of the symbol. The bracket
(strategy.exit with limit and stop from position_avg_price) is placed on every bar while in
a position, so it first works on the bar AFTER the fill bar, as in Pine.

Deviations from the original: none.
Not carried over: plot() of the two MAs is kept; nothing dropped.
────────────────────────────────────────────────────────────────────────
"""

from pinelib import Script, color, ta


class Spy59MaScalping(Script):
    TITLE = "SPY 5/9 MA Scalping + Volume + Time Filter"
    PINE_VERSION = 5
    OVERLAY = True
    STRATEGY = dict(default_qty_type="percent_of_equity", default_qty_value=100)
    SOURCE = {"id": "1dgKuDgW", "author": "MaGiCapital", "licence": "Mozilla Public License 2.0",
              "url": "https://www.tradingview.com/script/1dgKuDgW-SPY-5-9-MA-Scalping-Volume-Time-Filter"}

    def init(self):
        self.fast_len = self.input.int(5, "Fast MA (5)")
        self.slow_len = self.input.int(9, "Slow MA (9)")
        self.tp_dollars = self.input.float(0.40, "Take Profit ($ move)")
        self.sl_dollars = self.input.float(0.50, "Stop Loss ($ move)")

    def on_bar(self):
        fast_ma = ta.sma(self.close, self.fast_len)
        slow_ma = ta.sma(self.close, self.slow_len)
        vol_condition = self.volume > self.volume[1]
        start_time = self.timestamp("America/New_York", self.year(), self.month(), self.dayofmonth(), 9, 32)
        end_time = self.timestamp("America/New_York", self.year(), self.month(), self.dayofmonth(), 11, 12)
        time_condition = self.time >= start_time and self.time <= end_time
        # v5: both operands of `and` are evaluated, so the ta.* calls come first
        cross_up = ta.crossover(fast_ma, slow_ma)
        cross_dn = ta.crossunder(fast_ma, slow_ma)
        long_condition = cross_up and vol_condition and time_condition
        short_condition = cross_dn and vol_condition and time_condition
        st = self.strategy
        if long_condition:
            st.entry("Long", st.long)
        if short_condition:
            st.entry("Short", st.short)
        if st.position_size > 0:
            entry_price = st.position_avg_price
            st.exit("Exit Long", from_entry="Long", limit=entry_price + self.tp_dollars,
                    stop=entry_price - self.sl_dollars)
        if st.position_size < 0:
            entry_price = st.position_avg_price
            st.exit("Exit Short", from_entry="Short", limit=entry_price - self.tp_dollars,
                    stop=entry_price + self.sl_dollars)
        self.plot(fast_ma, color=color.green, title="5 MA")
        self.plot(slow_ma, color=color.red, title="9 MA")
