"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : Market Breadth Trend Strategy
Author       : PinegenAI
Source URL   : https://www.tradingview.com/script/JBDWeA0T-Market-Breadth-Trend-Strategy
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. The "breadth line" is an SMA(20) of 100/0 flags for close > slow EMA. Both
strategy.exit calls are unconditional and use the current position's average price (na while flat) for
both directions, as written, so after a reversal the first bar still works with the old average.

Deviations from the original: none.
Not carried over: none.
────────────────────────────────────────────────────────────────────────
"""

from pinelib import Script, color, ta


class MarketBreadthTrend(Script):
    TITLE = "Market Breadth Trend Strategy"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(initial_capital=100000)
    SOURCE = {"id": "JBDWeA0T", "author": "PinegenAI", "licence": "not stated",
              "url": "https://www.tradingview.com/script/JBDWeA0T-Market-Breadth-Trend-Strategy"}

    def init(self):
        self.ema_fast_len = self.input.int(50, "Fast EMA")
        self.ema_slow_len = self.input.int(200, "Slow EMA")
        self.atr_len = self.input.int(14, "ATR Length")
        self.atr_mult = self.input.float(1.5, "ATR Stop Multiplier")
        self.rr = self.input.float(2.0, "Risk Reward")

    def on_bar(self):
        ema_fast = ta.ema(self.close, self.ema_fast_len)
        ema_slow = ta.ema(self.close, self.ema_slow_len)
        trend_bull = ema_fast > ema_slow
        trend_bear = ema_fast < ema_slow
        breadth_line = ta.sma(100 if self.close > ema_slow else 0, 20)
        strong_breadth = breadth_line > 60
        weak_breadth = breadth_line < 40
        long_condition = trend_bull and strong_breadth
        short_condition = trend_bear and weak_breadth
        st = self.strategy
        if long_condition and st.position_size <= 0:
            st.entry("Long", st.long)
        if short_condition and st.position_size >= 0:
            st.entry("Short", st.short)
        atr_value = ta.atr(self.atr_len)
        long_stop = st.position_avg_price - atr_value * self.atr_mult
        long_target = st.position_avg_price + atr_value * self.atr_mult * self.rr
        short_stop = st.position_avg_price + atr_value * self.atr_mult
        short_target = st.position_avg_price - atr_value * self.atr_mult * self.rr
        st.exit("Exit Long", from_entry="Long", stop=long_stop, limit=long_target)
        st.exit("Exit Short", from_entry="Short", stop=short_stop, limit=short_target)
        self.plot(ema_fast, color=color.orange, title="Fast EMA")
        self.plot(ema_slow, color=color.blue, title="Slow EMA")
