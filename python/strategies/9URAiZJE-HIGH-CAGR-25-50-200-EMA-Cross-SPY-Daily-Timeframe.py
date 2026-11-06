"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : 50 / 200 EMA Cross — Filtered Long Only (Working)
Author       : finnick1111
Source URL   : https://www.tradingview.com/script/9URAiZJE-HIGH-CAGR-25-50-200-EMA-Cross-SPY-Daily-Timeframe
Pine version : v5
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. Enter within 70 bars of a bullish cross while the EMAs are separated by more
than 0.35 % and the slow EMA is not falling; exit on a bearish cross. The hard stop is re-issued every
bar from the average price (na while flat), so it first works on the bar after the fill.

Deviations from the original: none.
Not carried over: none.
────────────────────────────────────────────────────────────────────────
"""

from pinelib import Script, color, div, pmath, S, ta


class Ema50200FilteredLongOnly(Script):
    TITLE = "50 / 200 EMA Cross — Filtered Long Only (Working)"
    PINE_VERSION = 5
    OVERLAY = True
    STRATEGY = dict(initial_capital=10000, pyramiding=0)
    SOURCE = {"id": "9URAiZJE", "author": "finnick1111", "licence": "not stated",
              "url": "https://www.tradingview.com/script/9URAiZJE-HIGH-CAGR-25-50-200-EMA-Cross-SPY-Daily-Timeframe"}

    def init(self):
        self.start_year = self.input.int(1900, "Start Year")
        self.fast_len = self.input.int(50, "Fast EMA")
        self.slow_len = self.input.int(200, "Slow EMA")
        self.smooth_len = self.input.int(1, "Extra Smoothing")
        self.confirm_bars = self.input.int(70, "Bars Allowed After Cross")
        self.min_sep_perc = self.input.float(0.35, "Min Separation %")
        self.min_slope_perc = self.input.float(0.0, "Min Slow Slope %")
        self.leverage = self.input.float(5, "Leverage", step=0.1)
        self.stop_perc = self.input.float(10.0, "Hard Stop %")

    def on_bar(self):
        start_time = self.timestamp(self.start_year, 1, 1, 0, 0)
        allow_trade = self.time >= start_time
        fast = ta.ema(ta.ema(self.close, self.fast_len), self.smooth_len)
        slow = S(ta.ema(ta.ema(self.close, self.slow_len), self.smooth_len))
        bull_cross = ta.crossover(fast, slow.cur)
        bear_cross = ta.crossunder(fast, slow.cur)
        bars_since_cross = ta.barssince(bull_cross)
        sep_perc = div(pmath.abs(fast - slow.cur), slow.cur) * 100
        sep_ok = sep_perc > self.min_sep_perc
        slope_perc = div(slow.cur - slow[5], slow.cur) * 100
        slope_ok = slope_perc >= self.min_slope_perc
        enter_long = (allow_trade and bars_since_cross >= 0 and bars_since_cross <= self.confirm_bars
                      and fast > slow.cur and sep_ok and slope_ok)
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
        self.plot(fast, color=color.green, linewidth=2)
        self.plot(slow.cur, color=color.red, linewidth=2)
