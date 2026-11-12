"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : EMA 5/13 Strategy
Author       : dianargenti
Source URL   : https://www.tradingview.com/script/N18VdyZl-EMA-5-13-Strategy
Pine version : v5
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-09 by Claude (pine-to-python skill)

Deviations from the original: none.
Not carried over: none.
────────────────────────────────────────────────────────────────────────
"""

from pinelib import Script, ta


class Ema513(Script):
    TITLE = "EMA 5/13 Crossover (Long & Short, No Plots)"
    PINE_VERSION = 5
    OVERLAY = True
    STRATEGY = dict(default_qty_type="percent_of_equity", default_qty_value=100)
    SOURCE = {"id": "N18VdyZl", "author": "dianargenti", "licence": "not stated",
              "url": "https://www.tradingview.com/script/N18VdyZl-EMA-5-13-Strategy"}

    def init(self):
        self.fast_length = self.input.int(5, title="Fast EMA Length")
        self.slow_length = self.input.int(13, title="Slow EMA Length")

    def on_bar(self):
        ema_fast = ta.ema(self.close, self.fast_length)
        ema_slow = ta.ema(self.close, self.slow_length)
        long_condition = ta.crossover(ema_fast, ema_slow)
        short_condition = ta.crossunder(ema_fast, ema_slow)
        st = self.strategy
        if long_condition:
            st.close("Short")
            st.entry("Long", st.long)
        if short_condition:
            st.close("Long")
            st.entry("Short", st.short)
