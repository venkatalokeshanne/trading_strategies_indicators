"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : Trend Pullback EMA50 EMA200
Author       : MyStrategyHub
Source URL   : https://www.tradingview.com/script/GJgM8vsH-trend-pullback-ema-combo-algorithmic-trend-following
Pine version : v5
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-09 by Claude (pine-to-python skill)

Deviations from the original: none.
Not carried over: none.
────────────────────────────────────────────────────────────────────────
"""

from pinelib import Script, color, div, ta


class TrendPullbackEma(Script):
    TITLE = "Trend Pullback EMA50 EMA200"
    PINE_VERSION = 5
    OVERLAY = True
    STRATEGY = dict(initial_capital=100000, currency="USD", default_qty_type="percent_of_equity",
                    default_qty_value=10, pyramiding=1, commission_type="percent",
                    commission_value=0.05, slippage=1, process_orders_on_close=True)
    SOURCE = {"id": "GJgM8vsH", "author": "MyStrategyHub", "licence": "not stated",
              "url": "https://www.tradingview.com/script/GJgM8vsH-trend-pullback-ema-combo-algorithmic-trend-following"}

    def init(self):
        self.length = 9
        self.avg = 12

    def on_bar(self):
        ema50 = ta.ema(self.close, 50)
        ema200 = ta.ema(self.close, 200)
        self.plot(ema50, "EMA 50", color=color.blue)
        self.plot(ema200, "EMA 200", color=color.red)
        esa = ta.ema(self.close, self.length)
        d = ta.ema(abs(self.close - esa), self.length)
        ci = div(self.close - esa, 0.015 * d)
        wt1 = ta.ema(ci, self.avg)
        wt2 = ta.sma(wt1, 3)
        x_up = ta.crossover(wt1, wt2)          # v5 evaluates both sides of `and` (LESSONS P4)
        x_dn = ta.crossunder(wt1, wt2)
        long_condition = self.close > ema200 and self.close < ema50 and x_up
        short_condition = self.close < ema200 and self.close > ema50 and x_dn
        st = self.strategy
        if long_condition:
            st.entry("Long", st.long)
        if short_condition:
            st.entry("Short", st.short)
