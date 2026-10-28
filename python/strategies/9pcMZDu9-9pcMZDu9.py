"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : Serhan3 - WMA + ADX + Trailing + Date Filter
Author       : boztilkiserhan
Source URL   : https://www.tradingview.com/script/9pcMZDu9
Pine version : v5
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. WMA(11) crossing WMA(28) with the close beyond both, ADX(18) above 24 and the bar inside the
date window (exchange time zone) enters long (cross under: short), reversing. While a position is open at the close,
an exit with trail_points = 0.8 % of the close (in ticks, no rounding) and trail_offset = 0 is re-issued each bar, so it
first works on the bar after the fill and always uses the previous close.

Deviations from the original: none.
Not carried over: the WMA plots (cosmetic).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import Script, color, div, ta


class SerhanWmaAdx(Script):
    TITLE = "Serhan3 - WMA + ADX + Trailing + Date Filter"
    PINE_VERSION = 5
    OVERLAY = True
    STRATEGY = dict(initial_capital=10000, default_qty_type="percent_of_equity", default_qty_value=100)
    SOURCE = {"id": "9pcMZDu9", "author": "boztilkiserhan", "licence": "not stated",
              "url": "https://www.tradingview.com/script/9pcMZDu9"}

    def init(self):
        self.fast_len = self.input.int(11, "Hızlı WMA", minval=1)
        self.slow_len = self.input.int(28, "Yavaş WMA", minval=1)
        self.adx_len = self.input.int(18, "ADX Periyodu", minval=1)
        self.adx_threshold = self.input.float(24.0, "ADX Eşik", step=0.1)
        self.trail_perc = self.input.float(0.8, "Trailing Stop %", step=0.1) / 100
        self.from_month = self.input.int(1, "From Month", minval=1, maxval=12)
        self.from_day = self.input.int(1, "From Day", minval=1, maxval=31)
        self.from_year = self.input.int(2025, "From Year", minval=2000)
        self.to_month = self.input.int(12, "To Month", minval=1, maxval=12)
        self.to_day = self.input.int(31, "To Day", minval=1, maxval=31)
        self.to_year = self.input.int(2099, "To Year", minval=2000)

    def on_bar(self):
        start_time = self.timestamp(self.from_year, self.from_month, self.from_day, 0, 0)
        end_time = self.timestamp(self.to_year, self.to_month, self.to_day, 23, 59)
        in_date_range = self.time >= start_time and self.time <= end_time
        fast_wma = ta.wma(self.close, self.fast_len)
        slow_wma = ta.wma(self.close, self.slow_len)
        plus_di, minus_di, adx_val = ta.dmi(self.adx_len, self.adx_len)
        trend_filter = adx_val > self.adx_threshold
        cross_up = ta.crossover(fast_wma, slow_wma)
        cross_dn = ta.crossunder(fast_wma, slow_wma)
        long_condition = cross_up and self.close > fast_wma and self.close > slow_wma and trend_filter and in_date_range
        short_condition = cross_dn and self.close < fast_wma and self.close < slow_wma and trend_filter and in_date_range
        st = self.strategy
        if long_condition:
            st.entry("Long", st.long)
        if short_condition:
            st.entry("Short", st.short)
        if st.position_size > 0:
            st.exit("Exit Long", "Long", trail_points=div(self.close * self.trail_perc, self.syminfo.mintick), trail_offset=0)
        if st.position_size < 0:
            st.exit("Exit Short", "Short", trail_points=div(self.close * self.trail_perc, self.syminfo.mintick), trail_offset=0)
        self.plot(fast_wma, color=color.blue, linewidth=2, title="Fast WMA")
        self.plot(slow_wma, color=color.orange, linewidth=2, title="Slow WMA")
