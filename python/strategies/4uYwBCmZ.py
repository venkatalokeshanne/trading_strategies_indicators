"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : Fair Value Gap Continuation Framework
Author       : PinegenAI
Source URL   : https://www.tradingview.com/script/4uYwBCmZ
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. The FVG zone variables are var floats updated when a gap forms. Both
strategy.exit calls are unconditional and use the current position's average price (na while flat) for
both directions, so after a reversal the first bar still works with the old average.

Deviations from the original: none.
Not carried over: none.
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, color, na, ta


class FvgContinuation(Script):
    TITLE = "Fair Value Gap Continuation Framework"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(initial_capital=100000)
    SOURCE = {"id": "4uYwBCmZ", "author": "PinegenAI", "licence": "not stated",
              "url": "https://www.tradingview.com/script/4uYwBCmZ"}

    def init(self):
        self.atr_len = self.input.int(14, "ATR Length")
        self.atr_mult = self.input.float(1.5, "Stop ATR Multiplier")
        self.rr = self.input.float(2.0, "Risk Reward")
        self.trend_len = self.input.int(50, "Trend EMA Length")
        self.bull_top = NA
        self.bull_bottom = NA
        self.bear_top = NA
        self.bear_bottom = NA

    def on_bar(self):
        ema_trend = ta.ema(self.close, self.trend_len)
        atr_value = ta.atr(self.atr_len)
        bull_fvg = self.low > self.high[2]
        bear_fvg = self.high < self.low[2]
        if bull_fvg:
            self.bull_top = float(self.low)
            self.bull_bottom = self.high[2]
        if bear_fvg:
            self.bear_top = self.low[2]
            self.bear_bottom = float(self.high)
        bull_retest = not na(self.bull_top) and self.low <= self.bull_top and self.close > self.bull_top
        bear_retest = not na(self.bear_bottom) and self.high >= self.bear_bottom and self.close < self.bear_bottom
        long_condition = bull_retest and self.close > ema_trend
        short_condition = bear_retest and self.close < ema_trend
        st = self.strategy
        if long_condition and st.position_size <= 0:
            st.entry("Long", st.long)
        if short_condition and st.position_size >= 0:
            st.entry("Short", st.short)
        long_stop = st.position_avg_price - atr_value * self.atr_mult
        long_target = st.position_avg_price + atr_value * self.atr_mult * self.rr
        short_stop = st.position_avg_price + atr_value * self.atr_mult
        short_target = st.position_avg_price - atr_value * self.atr_mult * self.rr
        st.exit("Exit Long", from_entry="Long", stop=long_stop, limit=long_target)
        st.exit("Exit Short", from_entry="Short", stop=short_stop, limit=short_target)
        self.plot(ema_trend, title="Trend EMA", color=color.orange)
        self.plot(self.bull_top, title="Bullish FVG", color=color.green, linewidth=2)
        self.plot(self.bear_bottom, title="Bearish FVG", color=color.red, linewidth=2)
