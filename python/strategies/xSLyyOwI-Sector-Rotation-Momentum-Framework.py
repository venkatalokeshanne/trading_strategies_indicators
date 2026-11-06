"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : Sector Rotation Momentum Framework
Author       : PinegenAI
Source URL   : https://www.tradingview.com/script/xSLyyOwI-Sector-Rotation-Momentum-Framework
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. The sector ETF (default AMEX:XLK) is read with request.security at the chart
timeframe, which needs the pipeline's data provider for that symbol. Both strategy.exit calls are
unconditional with the current position's average price (na while flat) for both directions, so after a
reversal the first bar still works with the old average.

Deviations from the original: none.
Not carried over: none.
────────────────────────────────────────────────────────────────────────
"""

from pinelib import Script, color, div, ta


class SectorRotationMomentum(Script):
    TITLE = "Sector Rotation Momentum Framework"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(initial_capital=100000, default_qty_type="percent_of_equity", default_qty_value=5)
    SOURCE = {"id": "xSLyyOwI", "author": "PinegenAI", "licence": "not stated",
              "url": "https://www.tradingview.com/script/xSLyyOwI-Sector-Rotation-Momentum-Framework"}

    def init(self):
        self.benchmark = self.input.symbol("AMEX:XLK", "Sector ETF")
        self.fast_len = self.input.int(20, "Fast EMA")
        self.slow_len = self.input.int(50, "Slow EMA")
        self.rs_len = self.input.int(20, "Relative Strength EMA")
        self.atr_len = self.input.int(14, "ATR Length")
        self.atr_mult = self.input.float(1.5, "ATR Stop Multiplier")
        self.rr = self.input.float(2.0, "Risk Reward")

    def on_bar(self):
        benchmark_close = self.security(self.benchmark, self.timeframe.period, lambda v: v.close, lookahead=False)
        relative_strength = div(self.close, benchmark_close)
        relative_ma = ta.ema(relative_strength, self.rs_len)
        fast_ema = ta.ema(self.close, self.fast_len)
        slow_ema = ta.ema(self.close, self.slow_len)
        bull_trend = fast_ema > slow_ema
        bear_trend = fast_ema < slow_ema
        long_condition = bull_trend and relative_strength > relative_ma
        short_condition = bear_trend and relative_strength < relative_ma
        st = self.strategy
        if long_condition and st.position_size <= 0:
            st.entry("Long", st.long)
        if short_condition and st.position_size >= 0:
            st.entry("Short", st.short)
        atr = ta.atr(self.atr_len)
        long_stop = st.position_avg_price - atr * self.atr_mult
        long_target = st.position_avg_price + atr * self.atr_mult * self.rr
        short_stop = st.position_avg_price + atr * self.atr_mult
        short_target = st.position_avg_price - atr * self.atr_mult * self.rr
        st.exit("Exit Long", "Long", stop=long_stop, limit=long_target)
        st.exit("Exit Short", "Short", stop=short_stop, limit=short_target)
        self.plot(fast_ema, color=color.orange, title="Fast EMA")
        self.plot(slow_ema, color=color.blue, title="Slow EMA")
        self.plot(relative_ma * benchmark_close, color=color.green, title="Relative Strength Trend")
