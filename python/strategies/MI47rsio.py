"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : Trend Persistence Analysis Framework
Author       : PinegenAI
Source URL   : https://www.tradingview.com/script/MI47rsio
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. bullBars/bearBars count consecutive bars of each EMA trend (var ints). Both
strategy.exit calls are unconditional and use the current position's average price (na while flat) for
both directions, so after a reversal the first bar still works with the old average.

Deviations from the original: none.
Not carried over: none.
────────────────────────────────────────────────────────────────────────
"""

from pinelib import Script, color, ta


class TrendPersistenceFramework(Script):
    TITLE = "Trend Persistence Analysis Framework"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(initial_capital=100000, default_qty_type="percent_of_equity", default_qty_value=5)
    SOURCE = {"id": "MI47rsio", "author": "PinegenAI", "licence": "not stated",
              "url": "https://www.tradingview.com/script/MI47rsio"}

    def init(self):
        self.fast_len = self.input.int(20, "Fast EMA")
        self.slow_len = self.input.int(50, "Slow EMA")
        self.min_trend_bars = self.input.int(10, "Minimum Trend Duration")
        self.atr_len = self.input.int(14, "ATR Length")
        self.atr_mult = self.input.float(1.5, "Stop ATR Multiplier")
        self.rr = self.input.float(2.0, "Risk Reward")
        self.bull_bars = 0
        self.bear_bars = 0

    def on_bar(self):
        fast_ema = ta.ema(self.close, self.fast_len)
        slow_ema = ta.ema(self.close, self.slow_len)
        bull_trend = fast_ema > slow_ema
        bear_trend = fast_ema < slow_ema
        self.bull_bars = self.bull_bars + 1 if bull_trend else 0
        self.bear_bars = self.bear_bars + 1 if bear_trend else 0
        long_condition = bull_trend and self.bull_bars >= self.min_trend_bars
        short_condition = bear_trend and self.bear_bars >= self.min_trend_bars
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
        self.plot(fast_ema, title="Fast EMA", color=color.orange)
        self.plot(slow_ema, title="Slow EMA", color=color.blue)
