"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : Auto-Logger MTF + Calendar Backtest
Author       : Mukhlisilahi
Source URL   : https://www.tradingview.com/script/OtFXuPmK
Pine version : v5
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. Inside the configured calendar window, an EMA9 / EMA21 cross-up above EMA200 goes long and a cross-down below it goes short (each reversing at the next open).
The monthly / multi-timeframe result tables of the source are display only.

Deviations from the original: none.
Not carried over: the two statistics tables and the per-month bookkeeping that only feeds them.
────────────────────────────────────────────────────────────────────────
"""

from pinelib import Script, color, ta


class AutoLoggerMtf(Script):
    TITLE = "Auto-Logger MTF + Calendar Backtest"
    PINE_VERSION = 5
    OVERLAY = True
    STRATEGY = dict(initial_capital=10000, default_qty_type="percent_of_equity", default_qty_value=10)
    SOURCE = {"id": "OtFXuPmK", "author": "Mukhlisilahi", "licence": "not stated",
              "url": "https://www.tradingview.com/script/OtFXuPmK"}

    def init(self):
        g = "Backtest Period"
        self.start_year = self.input.int(2020, "Start Year", group=g)
        self.start_month = self.input.int(1, "Start Month", minval=1, maxval=12, group=g)
        self.start_day = self.input.int(1, "Start Day", minval=1, maxval=31, group=g)
        self.end_year = self.input.int(2030, "End Year", group=g)
        self.end_month = self.input.int(12, "End Month", minval=1, maxval=12, group=g)
        self.end_day = self.input.int(31, "End Day", minval=1, maxval=31, group=g)
        g = "Strategy Parameters"
        self.fast_len = self.input.int(9, "Fast EMA", group=g)
        self.slow_len = self.input.int(21, "Slow EMA", group=g)
        self.regime_len = self.input.int(200, "Regime EMA", group=g)

    def on_bar(self):
        in_date_range = (self.time >= self.timestamp(self.start_year, self.start_month, self.start_day, 0, 0)
                         and self.time <= self.timestamp(self.end_year, self.end_month, self.end_day, 23, 59))
        fast_ema = ta.ema(self.close, self.fast_len)
        slow_ema = ta.ema(self.close, self.slow_len)
        regime_ema = ta.ema(self.close, self.regime_len)
        long_cond = ta.crossover(fast_ema, slow_ema) and self.close > regime_ema
        short_cond = ta.crossunder(fast_ema, slow_ema) and self.close < regime_ema
        st = self.strategy
        if in_date_range:
            if long_cond:
                st.entry("Long", st.long)
            if short_cond:
                st.entry("Short", st.short)
        self.plot(fast_ema, "Fast EMA", color=color.blue)
        self.plot(slow_ema, "Slow EMA", color=color.orange)
        self.plot(regime_ema, "Regime EMA", color=color.white, linewidth=2)
