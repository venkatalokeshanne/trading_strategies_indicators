"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : Trend + RSI Strategy (Enhanced)
Author       : glencole_aitd
Source URL   : https://www.tradingview.com/script/wigMmPHd-Trend-RSI-Strategy-Refined
Pine version : v5
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. process_orders_on_close=true: entries fill at the signal bar's close. The
two strategy.exit calls are unconditional with levels from the current close and ATR, so bar i works
with bar i-1's levels, from the bar after the fill. `qty=riskPerTrade` is read as 1.0 contract, as in the
original (the input is a percentage label but is passed as a quantity).

Deviations from the original: none.
Not carried over: none.
────────────────────────────────────────────────────────────────────────
"""

from pinelib import Script, color, ta


class TrendRsiEnhanced(Script):
    TITLE = "Trend + RSI Strategy (Enhanced)"
    PINE_VERSION = 5
    OVERLAY = True
    STRATEGY = dict(initial_capital=10000, commission_type="percent", commission_value=0.10, slippage=2,
                    pyramiding=0, process_orders_on_close=True)
    SOURCE = {"id": "wigMmPHd", "author": "glencole_aitd", "licence": "not stated",
              "url": "https://www.tradingview.com/script/wigMmPHd-Trend-RSI-Strategy-Refined"}

    def init(self):
        self.fast_length = self.input.int(9, "Fast EMA")
        self.slow_length = self.input.int(21, "Slow EMA")
        self.rsi_length = self.input.int(14, "RSI Length")
        self.rsi_threshold = self.input.int(50, "RSI Threshold")
        self.atr_length = self.input.int(14, "ATR Length")
        self.atr_multiplier = self.input.float(1.5, "ATR Stop Multiplier")
        self.risk_per_trade = self.input.float(1.0, "Risk Per Trade (%)", minval=0.1, maxval=5.0)

    def on_bar(self):
        fast_ema = ta.ema(self.close, self.fast_length)
        slow_ema = ta.ema(self.close, self.slow_length)
        rsi = ta.rsi(self.close, self.rsi_length)
        atr = ta.atr(self.atr_length)
        trend_up = fast_ema > slow_ema
        trend_down = fast_ema < slow_ema
        long_condition = trend_up and rsi > self.rsi_threshold
        short_condition = trend_down and rsi < self.rsi_threshold
        st = self.strategy
        if long_condition and st.position_size == 0:
            st.entry("Long", st.long, qty=self.risk_per_trade)
        if short_condition and st.position_size == 0:
            st.entry("Short", st.short, qty=self.risk_per_trade)
        long_stop = self.close - (atr * self.atr_multiplier)
        short_stop = self.close + (atr * self.atr_multiplier)
        long_target = self.close + (atr * self.atr_multiplier * 2)
        short_target = self.close - (atr * self.atr_multiplier * 2)
        st.exit("Exit Long", from_entry="Long", stop=long_stop, limit=long_target)
        st.exit("Exit Short", from_entry="Short", stop=short_stop, limit=short_target)
        self.plot(fast_ema, color=color.blue, title="Fast EMA")
        self.plot(slow_ema, color=color.red, title="Slow EMA")
