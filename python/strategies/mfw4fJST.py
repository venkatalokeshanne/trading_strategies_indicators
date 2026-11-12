"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : VIX MACD Long
Author       : ryoma3119
Source URL   : https://www.tradingview.com/script/mfw4fJST
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : PARTIAL
Converted    : 2026-10-09 by Claude (pine-to-python skill)

Long the chart symbol when VIX's MACD crosses DOWN through its signal; close when it
crosses back up.

Deviations from the original:
  - CBOE:VIX comes from Yahoo (^VIX, regular session only) aligned to the chart's bars;
    TradingView's CBOE feed has its own bar times — bars near session edges can differ.
Not carried over: none.
────────────────────────────────────────────────────────────────────────
"""

from pinelib import Script, ta


class VixMacdLong(Script):
    TITLE = "VIX MACD Long"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict()
    SOURCE = {"id": "mfw4fJST", "author": "ryoma3119", "licence": "not stated",
              "url": "https://www.tradingview.com/script/mfw4fJST"}

    def init(self):
        self.fast_length = self.input.int(12, "MACD Fast")
        self.slow_length = self.input.int(26, "MACD Slow")
        self.signal_length = self.input.int(9, "MACD Signal")

    def on_bar(self):
        vix = self.security("CBOE:VIX", self.timeframe.period, lambda v: v.close.cur)
        macd_line = ta.ema(vix, self.fast_length) - ta.ema(vix, self.slow_length)
        signal_line = ta.ema(macd_line, self.signal_length)
        long_condition = ta.crossunder(macd_line, signal_line)
        exit_condition = ta.crossover(macd_line, signal_line)
        st = self.strategy
        if long_condition:
            st.entry("Long", st.long)
        if exit_condition:
            st.close("Long")
