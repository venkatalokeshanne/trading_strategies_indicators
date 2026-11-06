"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : Simplified 30m Event Strategy - Reverse
Author       : mbdalq
Source URL   : https://www.tradingview.com/script/kAYwdfND
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-29 by Claude (pine-to-python skill)

Line-for-line translation (market orders at the next open). The 30-minute high / low (request.security, lookahead off) are scanned for pivots with 2 bars on the left and 3 on the right ON THE CHART BARS (the higher-timeframe value is a staircase on a lower-timeframe chart); the latest pivot high and pivot low are remembered (valuewhen),
and once they are at least the minimum range apart a long is taken when the close is above the last pivot low on a bar with negative volume delta (volume signed by the candle colour), a short when the close is below the last pivot high on a bar with positive delta. A position is closed after the given number of bars.
Deviations from the original: none.
Not carried over: nothing (no display code in the source).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import Script, na, ta


class SimplifiedEventReverse(Script):
    TITLE = "Simplified 30m Event Strategy - Reverse"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(initial_capital=10000, default_qty_type="percent_of_equity", default_qty_value=10, pyramiding=1)
    SOURCE = {"id": "kAYwdfND", "author": "mbdalq", "licence": "not stated", "url": "https://www.tradingview.com/script/kAYwdfND"}

    def init(self):
        i = self.input
        self.left = i.int(2, "Pivot Left")
        self.right = i.int(3, "Pivot Right")
        self.exit_bars = i.int(6, "Exit after X bars (5min)")
        self.min_range = i.float(5, "Min Pivot Range")
        self.long_bar_count = 0
        self.short_bar_count = 0

    def on_bar(self):
        st = self.strategy
        close, open_, volume = self.close, self.open, self.volume
        high30 = self.security(None, "30", lambda v: v.high, lookahead=False)
        low30 = self.security(None, "30", lambda v: v.low, lookahead=False)
        ph30 = ta.pivothigh(high30, self.left, self.right)
        pl30 = ta.pivotlow(low30, self.left, self.right)
        last_ph = ta.valuewhen(not na(ph30), ph30, 0)
        last_pl = ta.valuewhen(not na(pl30), pl30, 0)
        valid = (not na(last_ph)) and (not na(last_pl)) and (last_ph - last_pl) >= self.min_range
        delta = volume if close > open_ else (-volume if close < open_ else 0)
        long_signal = valid and close > last_pl and delta < 0
        short_signal = valid and close < last_ph and delta > 0
        if st.position_size > 0:
            self.long_bar_count += 1
        else:
            self.long_bar_count = 0
        if st.position_size < 0:
            self.short_bar_count += 1
        else:
            self.short_bar_count = 0
        if self.long_bar_count >= self.exit_bars:
            st.close("Long")
        if self.short_bar_count >= self.exit_bars:
            st.close("Short")
        if long_signal:
            st.entry("Long", st.long)
        if short_signal:
            st.entry("Short", st.short)
