"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : Zero Line Momentum Strategy: Precision Trend Following
Author       : MyStrategyHub
Source URL   : https://www.tradingview.com/script/k13xEYxZ-zero-line-momentum-strategy-precision-trend-following
Pine version : v5
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-09 by Claude (pine-to-python skill)

Deviations from the original: none.
Not carried over: none.
────────────────────────────────────────────────────────────────────────
"""

from pinelib import Script, div, ta


class ZeroLineMomentum(Script):
    TITLE = "Zero Line Momentum Strategy"
    PINE_VERSION = 5
    OVERLAY = True
    STRATEGY = dict()
    SOURCE = {"id": "k13xEYxZ", "author": "MyStrategyHub", "licence": "not stated",
              "url": "https://www.tradingview.com/script/k13xEYxZ-zero-line-momentum-strategy-precision-trend-following"}

    def init(self):
        self.length = 9
        self.avg = 12

    def on_bar(self):
        ema200 = ta.ema(self.close, 200)
        self.plot(ema200)
        esa = ta.ema(self.close, self.length)
        d = ta.ema(abs(self.close - esa), self.length)
        ci = div(self.close - esa, 0.015 * d)
        wt1 = ta.ema(ci, self.avg)
        # Pine v5 evaluates both operands of `and`: the crosses are computed first (LESSONS P4)
        x_up = ta.crossover(wt1, 0)
        x_dn = ta.crossunder(wt1, 0)
        long_condition = self.close > ema200 and x_up
        short_condition = self.close < ema200 and x_dn
        st = self.strategy
        if long_condition:
            st.entry("Long", st.long)
        if short_condition:
            st.entry("Short", st.short)
