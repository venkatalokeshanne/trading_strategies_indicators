"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : Volatility Reversion Scalper
Author       : sebpageau
Source URL   : https://www.tradingview.com/script/IMKs0OPw
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation, including the original's argument order: the script calls
ta.percentile_linear_interpolation(wvf, int(ph * 100), lb), i.e. length = 99 (101 for the low) and
percentage = 25, which is the reverse of the intended reading but is what Pine executes. The
date inputs default to timestamp("2020-01-01 00:00") and timestamp("2025-01-01 00:00"), given
as UTC epoch milliseconds. Pyramiding is 0 (default), so the 10 %-drawdown add-on never fires
while a long is open.

Deviations from the original: none.
Not carried over: none.
────────────────────────────────────────────────────────────────────────
"""

from pinelib import Script, color, div, ta

START_2020 = 1577836800000     # timestamp("2020-01-01 00:00") UTC
END_2025 = 1735689600000       # timestamp("2025-01-01 00:00") UTC


class VolatilityReversionScalper(Script):
    TITLE = "Volatility Reversion Scalper"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict()
    SOURCE = {"id": "IMKs0OPw", "author": "sebpageau", "licence": "not stated",
              "url": "https://www.tradingview.com/script/IMKs0OPw"}

    def init(self):
        self.pd = self.input.int(11, "LookBack Period Standard Deviation High")
        self.bbl = self.input.int(10, "Bolinger Band Length")
        self.mult = self.input.float(5.0, "Bollinger Band Standard Deviation Up", minval=1, maxval=5)
        self.lb = self.input.int(25, "Look Back Period Percentile High")
        self.ph = self.input.float(.99, "Highest Percentile")
        self.pl = self.input.float(1.01, "Lowest Percentile")
        self.length = self.input.int(10, "Length")
        self.src = self.input.source(self.close, "Source")
        self.mult_fib = self.input.float(0.618, "Multiplier")
        self.start_date = self.input.time(START_2020, "Start Date")
        self.end_date = self.input.time(END_2025, "End Date")

    def on_bar(self):
        hi_close = ta.highest(self.close, self.pd)
        wvf = div(hi_close - self.low, hi_close) * 100
        s_dev = self.mult * ta.stdev(wvf, self.bbl)
        mid_line = ta.sma(wvf, self.bbl)
        lower_band = mid_line - s_dev
        upper_band = mid_line + s_dev
        range_high = ta.percentile_linear_interpolation(wvf, int(self.ph * 100), self.lb)
        range_low = ta.percentile_linear_interpolation(wvf, int(self.pl * 100), self.lb)
        vix_fix = 1 if wvf >= range_high else (-1 if wvf <= range_low else 0)
        basis = ta.sma(self.src, self.length)
        dev = self.mult_fib * ta.stdev(self.src, self.length)
        upper = basis + dev
        lower = basis - dev
        condition1 = self.close <= lower or self.open <= lower
        condition2 = vix_fix == 1
        condition3 = self.close > self.open and self.close[1] < self.open[1]
        in_date_range = (self.time >= self.start_date) and (self.time <= self.end_date)
        buy_condition = condition1 and condition2 and condition3 and self.barstate.isconfirmed and in_date_range
        st = self.strategy
        pyramid_condition = st.position_size > 0 and div(st.position_avg_price - self.close, st.position_avg_price) >= 0.10
        if buy_condition and (st.position_size == 0 or pyramid_condition):
            st.entry("Long", st.long)
        min_take_profit = st.position_avg_price * 1.05
        if st.position_size > 0:
            st.exit("Take Profit", "Long", limit=min_take_profit)
        self.plot(basis, color=color.blue, title="Basis")
        self.plot(upper, color=color.red, title="Upper")
        self.plot(lower, color=color.green, title="Lower")
        self.plotshape(vix_fix == 1, title="VIX Fix Signal")
