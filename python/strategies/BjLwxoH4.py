"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : Range Trading SOL/USD
Author       : haugeneder
Source URL   : https://www.tradingview.com/script/BjLwxoH4
Pine version : v5
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-29 by Claude (pine-to-python skill)

Line-for-line translation (market orders at the next open). The range is the highest high / lowest low of the bars 12 to 83 bars back. A close crossing under the range high opens a short, a close crossing over the range low opens a long (up to 3 entries per side); a high above the range high closes the longs, a low below the range low closes the shorts,
and an extension of the range by the short / long offset closes the opposite side (shorts above high + offset, longs below low - offset). Any position whose open loss per unit (against the average entry price) exceeds the maximum is closed.
Deviations from the original: none.
Not carried over: nothing (no display code in the source).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import Script, ta


class RangeTradingSol(Script):
    TITLE = "Range Trading SOL/USD"
    PINE_VERSION = 5
    OVERLAY = True
    STRATEGY = dict(pyramiding=3)
    SOURCE = {"id": "BjLwxoH4", "author": "haugeneder", "licence": "not stated", "url": "https://www.tradingview.com/script/BjLwxoH4"}

    def init(self):
        i = self.input
        self.length = i.int(72, "Lookback")
        self.offsetlong = i.float(9, "offsetlong")
        self.offsetshort = i.float(12, "offsetshort")
        self.max_loss = i.float(7, "Max Verlust pro Trade")

    def on_bar(self):
        st = self.strategy
        close = self.close
        high12 = self.high[12]
        low12 = self.low[12]
        high1 = ta.highest(high12, self.length)
        low1 = ta.lowest(low12, self.length)
        abs_high = high1 + self.offsetlong
        abs_low = low1 - self.offsetshort
        short_condition = ta.crossunder(close, high1)
        long_condition = ta.crossover(close, low1)
        if short_condition:
            st.entry("Short", st.short)
        if long_condition:
            st.entry("Long", st.long)
        if self.high > high1:
            st.close("Long")
        if self.low < low1:
            st.close("Short")
        if self.high > abs_high:
            st.close("Short")
        if self.low < abs_low:
            st.close("Long")
        avg = st.position_avg_price
        current_loss = avg - close if st.position_size > 0 else close - avg
        if current_loss > self.max_loss:
            st.close_all()
