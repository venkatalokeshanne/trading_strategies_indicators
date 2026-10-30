"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : Trend Efficiency Framework
Author       : PinegenAI
Source URL   : https://www.tradingview.com/script/oTVSg42n-Trend-Efficiency-Framework
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. Efficiency = net move over the lookback / sum of the absolute bar-to-bar moves
(`for i = 0 to lookback - 1` is inclusive, so range(0, lookback)). Both strategy.exit calls are
unconditional and use the current position's average price (na while flat) for both directions, so after a
reversal the first bar still works with the old average.

Deviations from the original: none.
Not carried over: none.
────────────────────────────────────────────────────────────────────────
"""

from pinelib import Script, color, div, pmath, ta


class TrendEfficiencyFramework(Script):
    TITLE = "Trend Efficiency Framework"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(initial_capital=100000, default_qty_type="percent_of_equity", default_qty_value=5)
    SOURCE = {"id": "oTVSg42n", "author": "PinegenAI", "licence": "not stated",
              "url": "https://www.tradingview.com/script/oTVSg42n-Trend-Efficiency-Framework"}

    def init(self):
        self.fast_len = self.input.int(20, "Fast EMA")
        self.slow_len = self.input.int(50, "Slow EMA")
        self.lookback = self.input.int(20, "Efficiency Lookback")
        self.eff_threshold = self.input.float(0.55, "Efficiency Threshold", step=0.05)
        self.atr_len = self.input.int(14, "ATR Length")
        self.atr_mult = self.input.float(1.5, "ATR Stop Multiplier")
        self.rr = self.input.float(2.0, "Risk Reward")

    def on_bar(self):
        fast_ema = ta.ema(self.close, self.fast_len)
        slow_ema = ta.ema(self.close, self.slow_len)
        bull_trend = fast_ema > slow_ema
        bear_trend = fast_ema < slow_ema
        net_move = pmath.abs(self.close - self.close[self.lookback])
        total_move = 0.0
        for i in range(0, self.lookback):
            total_move += pmath.abs(self.close[i] - self.close[i + 1])
        efficiency = div(net_move, total_move) if total_move != 0 else 0.0
        long_condition = bull_trend and efficiency > self.eff_threshold
        short_condition = bear_trend and efficiency > self.eff_threshold
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
        self.plot(fast_ema, color=color.orange, title="Fast EMA")
        self.plot(slow_ema, color=color.blue, title="Slow EMA")
        self.plot(efficiency, title="Trend Efficiency", color=color.green)
