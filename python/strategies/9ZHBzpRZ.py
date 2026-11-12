"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : SERHAN1-WMA + RSI + Trailing Scalp (Date Filter)
Author       : boztilkiserhan
Source URL   : https://www.tradingview.com/script/9ZHBzpRZ
Pine version : v5
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. The date inputs default to timestamp("2020-01-01 00:00") and
timestamp("2030-12-31 23:59"), given here as UTC epoch milliseconds. The trailing exit is
re-issued on every bar in a position with trail_points = close * pct / mintick (ticks) and
trail_offset = 0, as in the original; pinelib keeps the trailing extreme between re-issues.

Deviations from the original: none.
Not carried over: none.
────────────────────────────────────────────────────────────────────────
"""

from pinelib import Script, color, div, ta

START_2020 = 1577836800000     # timestamp("2020-01-01 00:00") UTC
END_2030 = 1924991940000       # timestamp("2030-12-31 23:59") UTC


class SerhanWmaRsiTrailing(Script):
    TITLE = "SERHAN1-WMA + RSI + Trailing Scalp (Date Filter)"
    PINE_VERSION = 5
    OVERLAY = True
    STRATEGY = dict(initial_capital=10000, default_qty_type="percent_of_equity", default_qty_value=100)
    SOURCE = {"id": "9ZHBzpRZ", "author": "boztilkiserhan", "licence": "not stated",
              "url": "https://www.tradingview.com/script/9ZHBzpRZ"}

    def init(self):
        self.start_date = self.input.time(START_2020, "Başlangıç Tarihi")
        self.end_date = self.input.time(END_2030, "Bitiş Tarihi")
        self.fast_len = self.input.int(9, "Hızlı WMA", minval=1)
        self.slow_len = self.input.int(21, "Yavaş WMA", minval=1)
        self.rsi_len = self.input.int(14, "RSI Periyodu", minval=1)
        self.trail_perc = self.input.float(1.5, "İz Süren Stop %", minval=0, step=0.1) / 100

    def on_bar(self):
        in_date_range = self.time >= self.start_date and self.time <= self.end_date
        fast_wma = ta.wma(self.close, self.fast_len)
        slow_wma = ta.wma(self.close, self.slow_len)
        rsi_val = ta.rsi(self.close, self.rsi_len)
        cross_up = ta.crossover(fast_wma, slow_wma)
        cross_dn = ta.crossunder(fast_wma, slow_wma)
        long_condition = cross_up and self.close > fast_wma and self.close > slow_wma and rsi_val > 50
        short_condition = cross_dn and self.close < fast_wma and self.close < slow_wma and rsi_val < 50
        st = self.strategy
        if in_date_range and long_condition:
            st.entry("Long", st.long, comment="L")
        if in_date_range and short_condition:
            st.entry("Short", st.short, comment="S")
        if st.position_size > 0 and self.trail_perc > 0:
            st.exit("Exit Long", "Long", trail_points=div(self.close * self.trail_perc, self.syminfo.mintick),
                    trail_offset=0)
        if st.position_size < 0 and self.trail_perc > 0:
            st.exit("Exit Short", "Short", trail_points=div(self.close * self.trail_perc, self.syminfo.mintick),
                    trail_offset=0)
        self.plot(fast_wma, color=color.blue, title="Hızlı WMA")
        self.plot(slow_wma, color=color.orange, title="Yavaş WMA")
