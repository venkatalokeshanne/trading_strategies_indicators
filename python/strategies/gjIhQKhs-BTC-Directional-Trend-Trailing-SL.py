"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : BTC Directional Trend + Trailing SL
Author       : saranglimbole180
Source URL   : https://www.tradingview.com/script/gjIhQKhs-BTC-Directional-Trend-Trailing-SL
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. The two strategy.exit calls are unconditional, re-issued every bar with
trail_points = ATR * mult and trail_offset = ATR (read by Pine as TICKS, as written in the original).

Pine v6 short-circuits `uptrend and ta.crossover(...)`: the cross is only evaluated on bars where the trend
filter is true, so its "previous bar" is the last bar it ran on (pinelib models this, LESSONS P4/P5). If
TradingView treats ta.crossover as stateless history, entries right after a filter flip could differ.

Deviations from the original: none.
Not carried over: the unused longStop / shortStop variables are kept; nothing dropped.
────────────────────────────────────────────────────────────────────────
"""

from pinelib import Script, color, ta


class BtcDirectionalTrendTrailing(Script):
    TITLE = "BTC Directional Trend + Trailing SL"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(initial_capital=5000, default_qty_type="percent_of_equity", default_qty_value=100)
    SOURCE = {"id": "gjIhQKhs", "author": "saranglimbole180", "licence": "not stated",
              "url": "https://www.tradingview.com/script/gjIhQKhs-BTC-Directional-Trend-Trailing-SL"}

    def init(self):
        self.ema_trend_len = self.input.int(200, "Trend EMA")
        self.ema_entry_len = self.input.int(20, "Entry EMA")
        self.atr_len = self.input.int(14, "ATR Length")
        self.atr_multiplier = self.input.float(2.0, "ATR Trailing Multiplier")

    def on_bar(self):
        ema_trend = ta.ema(self.close, self.ema_trend_len)
        ema_entry = ta.ema(self.close, self.ema_entry_len)
        atr = ta.atr(self.atr_len)
        uptrend = self.close > ema_trend
        downtrend = self.close < ema_trend
        long_condition = uptrend and ta.crossover(self.close, ema_entry)
        short_condition = downtrend and ta.crossunder(self.close, ema_entry)
        st = self.strategy
        if long_condition:
            st.entry("Long", st.long)
        if short_condition:
            st.entry("Short", st.short)
        long_stop = self.close - (atr * self.atr_multiplier)
        short_stop = self.close + (atr * self.atr_multiplier)
        st.exit("Long Exit", from_entry="Long", trail_points=atr * self.atr_multiplier, trail_offset=atr)
        st.exit("Short Exit", from_entry="Short", trail_points=atr * self.atr_multiplier, trail_offset=atr)
        self.plot(ema_trend, color=color.blue, title="EMA 200")
        self.plot(ema_entry, color=color.orange, title="EMA 20")
