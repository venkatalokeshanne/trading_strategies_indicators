"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : How To Set Backtest Time Ranges
Author       : LucF
Source URL   : https://www.tradingview.com/script/xAEG4ZJG-How-To-Set-Backtest-Time-Ranges
Pine version : v5
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. An SMA(14) / SMA(28) crossover enters long and the opposite cross closes it, each only inside
a date window and an entry / exit session (the default 0000-0000 means any time). Cash sizing of 100000 per trade,
percent commission, no pyramiding.

Deviations from the original: none.
Not carried over: the three background-colour highlights (cosmetic).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import Script, color, na, ta


class TimedBacktest(Script):
    TITLE = "How To Set Time Ranges"
    PINE_VERSION = 5
    OVERLAY = True
    STRATEGY = dict(pyramiding=0, initial_capital=100000, default_qty_type="cash", default_qty_value=100000,
                    commission_type="percent", commission_value=0.27)
    SOURCE = {"id": "xAEG4ZJG", "author": "LucF", "licence": "not stated",
              "url": "https://www.tradingview.com/script/xAEG4ZJG-How-To-Set-Backtest-Time-Ranges"}

    def init(self):
        self.fast_ma = self.input.int(14, "FastMA Length", minval=1, step=1)
        self.slow_ma = self.input.int(28, "SlowMA Length", minval=1, step=1)
        self.from_month = self.input.int(1, "From Month", minval=1, maxval=12)
        self.from_day = self.input.int(1, "From Day", minval=1, maxval=31)
        self.from_year = self.input.int(2021, "From Year", minval=1970)
        self.thru_month = self.input.int(1, "Thru Month", minval=1, maxval=12)
        self.thru_day = self.input.int(1, "Thru Day", minval=1, maxval=31)
        self.thru_year = self.input.int(2112, "Thru Year", minval=1970)
        self.entry_time = self.input.session("0000-0000", "Entry Time")
        self.exit_time = self.input.session("0000-0000", "Exit Time")
        self.show_date = self.input.bool(True, "Show Date Range")
        self.show_time_e = self.input.bool(True, "Show Time Entry")
        self.show_time_x = self.input.bool(True, "Show Time Exit")

    def is_date(self):
        start = self.timestamp(self.from_year, self.from_month, self.from_day, 0, 0)
        finish = self.timestamp(self.thru_year, self.thru_month, self.thru_day, 23, 59)
        return self.time >= start and self.time <= finish

    def is_time(self, position):
        return self.time_fn(None, position + ":1234567")

    def on_bar(self):
        enter_long = ta.crossover(ta.sma(self.close, self.fast_ma), ta.sma(self.close, self.slow_ma))
        exit_long = ta.crossunder(ta.sma(self.close, self.fast_ma), ta.sma(self.close, self.slow_ma))
        st = self.strategy
        d = self.is_date()
        if d and not na(self.is_time(self.entry_time)) and enter_long:
            st.entry("L", st.long)
        if d and not na(self.is_time(self.exit_time)) and exit_long:
            st.close("L")
        self.plot(ta.sma(self.close, self.fast_ma), "FastMA", color=color.yellow, linewidth=2)
        self.plot(ta.sma(self.close, self.slow_ma), "SlowMA", color=color.aqua, linewidth=2)
