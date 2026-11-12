"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : Multi-Timeframe Trend Alignment Framework
Author       : PinegenAI
Source URL   : https://www.tradingview.com/script/NEtMdbmJ-Multi-Timeframe-Trend-Alignment-Framework
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. The higher-timeframe EMA200 (default 240 minutes) comes from request.security
with lookahead off: a 4-hour block's value shows on the last chart bar of that block. Both strategy.exit
calls are unconditional with the current position's average price (na while flat) for both directions, so
after a reversal the first bar still works with the old average.

Deviations from the original: none.
Not carried over: none.
────────────────────────────────────────────────────────────────────────
"""

from pinelib import Script, color, ta


class MtfTrendAlignment(Script):
    TITLE = "Multi-Timeframe Trend Alignment Framework"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(initial_capital=100000, default_qty_type="percent_of_equity", default_qty_value=5)
    SOURCE = {"id": "NEtMdbmJ", "author": "PinegenAI", "licence": "not stated",
              "url": "https://www.tradingview.com/script/NEtMdbmJ-Multi-Timeframe-Trend-Alignment-Framework"}

    def init(self):
        self.higher_tf = self.input.timeframe("240", "Higher Timeframe")
        self.fast_len = self.input.int(20, "Fast EMA")
        self.slow_len = self.input.int(50, "Slow EMA")
        self.htf_len = self.input.int(200, "Higher TF EMA")
        self.atr_len = self.input.int(14, "ATR Length")
        self.atr_mult = self.input.float(1.5, "Stop ATR Multiplier")
        self.rr = self.input.float(2.0, "Risk Reward")

    def on_bar(self):
        fast_ema = ta.ema(self.close, self.fast_len)
        slow_ema = ta.ema(self.close, self.slow_len)
        htf_ema = self.security(None, self.higher_tf, lambda v: ta.ema(v.close, self.htf_len), lookahead=False)
        bull_trend = self.close > htf_ema
        bear_trend = self.close < htf_ema
        bull_cross = ta.crossover(fast_ema, slow_ema)
        bear_cross = ta.crossunder(fast_ema, slow_ema)
        long_condition = bull_trend and bull_cross
        short_condition = bear_trend and bear_cross
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
        self.plot(htf_ema, color=color.green, title="Higher Timeframe EMA", linewidth=2)
