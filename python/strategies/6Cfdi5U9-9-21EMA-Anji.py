"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : 9/21 EMA | EOD Exit 3:15 IST (9/21EMA_Anji)
Author       : Anji_GA
Source URL   : https://www.tradingview.com/script/6Cfdi5U9-9-21EMA-Anji
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. A 9 EMA crossing over (under) the 21 EMA on a green (red) candle between 09:30 and 15:00 exchange time, inside the backtest range, enters long (short), reversing an opposite
position. The first bar at or after 15:15 closes any open position (end-of-day exit).

Deviations from the original: none.
Not carried over: the EMA band fill, signal shapes, backgrounds and the info table (cosmetic).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import Script, color, ta

START_DATE = 1767205800000     # timestamp('2026-01-01 00:00 +0530')
END_DATE = 1798741740000       # timestamp('2026-12-31 23:59 +0530')


class Ema921Anji(Script):
    TITLE = "9/21 EMA | EOD Exit 3:15 IST"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(initial_capital=100000, default_qty_type="percent_of_equity", default_qty_value=100, commission_type="percent", commission_value=0.03)
    SOURCE = {"id": "6Cfdi5U9", "author": "Anji_GA", "licence": "not stated",
              "url": "https://www.tradingview.com/script/6Cfdi5U9-9-21EMA-Anji"}

    def init(self):
        self.fast_len = self.input.int(9, "Fast EMA length", minval=1)
        self.slow_len = self.input.int(21, "Slow EMA length", minval=1)
        self.start_date = self.input.time(START_DATE, "Backtest start")
        self.end_date = self.input.time(END_DATE, "Backtest end")

    def on_bar(self):
        in_range = self.time >= self.start_date and self.time <= self.end_date
        hour, minute = self.hour(), self.minute()
        is_signal_window = (hour > 9 or (hour == 9 and minute >= 30)) and hour < 15
        is_eod_bar = (hour == 15 and minute >= 15) or hour > 15
        eod_prev = self.H("eod")[1]
        self.H("eod").set(is_eod_bar)
        st = self.strategy
        eod_exit = is_eod_bar and not eod_prev and st.position_size != 0 and in_range
        ema9 = ta.ema(self.close, self.fast_len)
        ema21 = ta.ema(self.close, self.slow_len)
        bull_cross = ta.crossover(ema9, ema21)
        bear_cross = ta.crossunder(ema9, ema21)
        is_green = self.close > self.open
        is_red = self.close < self.open
        cross_bull_signal = bull_cross and is_green and is_signal_window and in_range
        cross_bear_signal = bear_cross and is_red and is_signal_window and in_range
        bull_entry = cross_bull_signal and st.position_size <= 0
        bear_entry = cross_bear_signal and st.position_size >= 0
        if bull_entry and not is_eod_bar:
            st.entry("Long", st.long, comment="BUY")
        if bear_entry and not is_eod_bar:
            st.entry("Short", st.short, comment="SHORT")
        if eod_exit:
            st.close_all(comment="EOD EXIT 3:15")
        self.plot(ema9, "9 EMA", color=color.blue, linewidth=2)
        self.plot(ema21, "21 EMA", color=color.orange, linewidth=2)
