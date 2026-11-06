"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : 21 / 75 EMA Cross — Filtered Long Only
Author       : finnick1111
Source URL   : https://www.tradingview.com/script/QfY9ozPr-SPY-Daily-Timeframe-20-CAGR-High-Risk-High-Reward
Pine version : v5
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. Entry size is computed from the current equity (4x leverage) and passed
as an explicit quantity. The hard stop is re-issued every bar from the average price (na while
flat), so it first works on the bar after the fill.

Deviations from the original: none.
Not carried over: none.
────────────────────────────────────────────────────────────────────────
"""

from pinelib import Script, color, div, pmath, ta


class Ema2175FilteredLongOnly(Script):
    TITLE = "21 / 75 EMA Cross — Filtered Long Only"
    PINE_VERSION = 5
    OVERLAY = True
    STRATEGY = dict(initial_capital=10000, pyramiding=0)
    SOURCE = {"id": "QfY9ozPr", "author": "finnick1111", "licence": "not stated",
              "url": "https://www.tradingview.com/script/QfY9ozPr-SPY-Daily-Timeframe-20-CAGR-High-Risk-High-Reward"}

    def init(self):
        self.start_year = self.input.int(1940, "Start Year")
        self.fast_len = self.input.int(20, "Fast EMA")
        self.slow_len = self.input.int(70, "Slow EMA")
        self.smooth_len = self.input.int(100, "Extra Smoothing")
        self.leverage = self.input.float(4.0, "Leverage", step=0.1)
        self.stop_perc = self.input.float(10.0, "Hard Stop %")

    def on_bar(self):
        start_time = self.timestamp(self.start_year, 1, 1, 0, 0)
        allow_trade = self.time >= start_time
        fast = ta.ema(ta.ema(self.close, self.fast_len), self.smooth_len)
        slow = ta.ema(ta.ema(self.close, self.slow_len), self.smooth_len)
        bull_cross = ta.crossover(fast, slow)
        bear_cross = ta.crossunder(fast, slow)
        enter_long = allow_trade and bull_cross
        exit_long = allow_trade and bear_cross
        st = self.strategy
        equity = pmath.max(st.equity, 0)
        qty = div(equity * self.leverage, self.close) if equity > 0 else 0
        if enter_long and st.position_size == 0 and qty > 0:
            st.entry("Long", st.long, qty=qty)
        stop_price = st.position_avg_price * (1 - self.stop_perc / 100)
        st.exit("Stop", from_entry="Long", stop=stop_price)
        if exit_long:
            st.close("Long")
        self.plot(fast, color=color.green, linewidth=2, title="21 EMA")
        self.plot(slow, color=color.red, linewidth=2, title="75 EMA")
