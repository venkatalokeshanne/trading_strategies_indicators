"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : Pro SMA Trend Strategy
Author       : imthetradingdoge
Source URL   : https://www.tradingview.com/script/oF6FmwfR-Pro-SMA-Trend-Strategy
Pine version : v5
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. The close crossing over / under SMA(44) goes long / short (reversing) with a quantity of
equity x leverage / close; in "Long Only" the cross under only closes the long, in "Short Only" the cross over only
closes the short.

Deviations from the original: none.
Not carried over: the SMA colouring, signal shapes and background (cosmetic).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import Script, color, div, ta


class ProSmaTrend(Script):
    TITLE = "Pro SMA Trend Strategy"
    PINE_VERSION = 5
    OVERLAY = True
    STRATEGY = dict(initial_capital=10000)
    SOURCE = {"id": "oF6FmwfR", "author": "imthetradingdoge", "licence": "not stated",
              "url": "https://www.tradingview.com/script/oF6FmwfR-Pro-SMA-Trend-Strategy"}

    def init(self):
        g = "Strategy & Leverage Settings"
        self.trade_direction = self.input.string("Both", title="Trade Direction", options=["Both", "Long Only", "Short Only"], group=g)
        self.long_leverage = self.input.float(2.0, title="Long Leverage (e.g., 2.0 = 2x)", step=0.1, minval=0.1, group=g)
        self.short_leverage = self.input.float(1.0, title="Short Leverage (e.g., 1.0 = 1x)", step=0.1, minval=0.1, group=g)
        self.sma_length = self.input.int(44, title="SMA Length (Custom - Try 11, 37, 44, 58, 125)", minval=1, group="Indicator Settings")

    def on_bar(self):
        sma_value = ta.sma(self.close, self.sma_length)
        long_condition = ta.crossover(self.close, sma_value)
        short_condition = ta.crossunder(self.close, sma_value)
        st = self.strategy
        long_qty = div(st.equity * self.long_leverage, self.close)
        short_qty = div(st.equity * self.short_leverage, self.close)
        if long_condition:
            if self.trade_direction == "Both" or self.trade_direction == "Long Only":
                st.entry("Long", st.long, qty=long_qty)
            if self.trade_direction == "Short Only":
                st.close("Short")
        if short_condition:
            if self.trade_direction == "Both" or self.trade_direction == "Short Only":
                st.entry("Short", st.short, qty=short_qty)
            if self.trade_direction == "Long Only":
                st.close("Long")
        self.plot(sma_value, color=color.green if self.close > sma_value else color.red, linewidth=3, title="Trend SMA")
