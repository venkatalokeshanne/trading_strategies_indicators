"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : EMA + Ichimoku Base Strategy with RSI Zones
Author       : sandeepchiru199
Source URL   : https://www.tradingview.com/script/4W6ifipi-EMA-Ichimoku-Base-Strategy-with-RSI-Zones
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. A close crossing up (down) through EMA4 opens a long (short) trade (up to 10 stack, an opposite signal reverses). Both exit orders run on every
bar with the Ichimoku base line (10-bar high-low midpoint) as the stop and a percentage of position_avg_price as the target; the long also closes when the close crosses back down
through the EMA (short: up).

Deviations from the original: none.
Not carried over: RSI-zone signal level (only plotted), shapes, hlines (cosmetic).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, color, ta


class EmaIchimokuBase(Script):
    TITLE = "EMA + Ichimoku Base Strategy with RSI Zones"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(pyramiding=10)
    SOURCE = {"id": "4W6ifipi", "author": "sandeepchiru199", "licence": "not stated",
              "url": "https://www.tradingview.com/script/4W6ifipi-EMA-Ichimoku-Base-Strategy-with-RSI-Zones"}

    def init(self):
        self.rsi_len = self.input.int(7, "RSI Length")
        self.rsi_wma_len = self.input.int(5, "RSI WMA Length")
        self.ema_len = self.input.int(4, "EMA Length")
        self.sma_len = self.input.int(6, "SMA Length")
        self.kijun_len = self.input.int(10, "Ichimoku Base Line Length")
        self.upper_band = self.input.float(60.0, "RSI Upper Band")
        self.middle_band = self.input.float(40.0, "RSI Middle Band")
        self.lower_band = self.input.float(32.0, "RSI Lower Band")
        self.tp_percent = self.input.float(30.0, "Take Profit %") / 100.0
        self.signal_level = NA

    def on_bar(self):
        rsi_value = ta.rsi(self.close, self.rsi_len)
        rsi_wma = ta.wma(rsi_value, self.rsi_wma_len)
        ema_val = ta.ema(self.close, self.ema_len)
        sma_val = ta.sma(self.close, self.sma_len)
        highest_high = ta.highest(self.high, self.kijun_len)
        lowest_low = ta.lowest(self.low, self.kijun_len)
        kijun = (highest_high + lowest_low) / 2
        oversold_cross = ta.crossover(sma_val, rsi_value) and rsi_value <= self.lower_band
        overbought_cross = ta.crossunder(sma_val, rsi_value) and rsi_value >= self.upper_band
        if oversold_cross or overbought_cross:
            self.signal_level = float(self.close)
        long_entry = ta.crossover(self.close, ema_val)
        short_entry = ta.crossunder(self.close, ema_val)
        st = self.strategy
        if long_entry:
            st.entry("Long", st.long)
        if short_entry:
            st.entry("Short", st.short)
        long_stop = kijun
        short_stop = kijun
        long_tp = st.position_avg_price * (1 + self.tp_percent)
        short_tp = st.position_avg_price * (1 - self.tp_percent)
        ema_cross_down = ta.crossunder(self.close, ema_val)
        ema_cross_up = ta.crossover(self.close, ema_val)
        st.exit("Long Exit", from_entry="Long", stop=long_stop, limit=long_tp)
        st.exit("Short Exit", from_entry="Short", stop=short_stop, limit=short_tp)
        if st.position_size > 0 and ema_cross_down:
            st.close("Long")
        if st.position_size < 0 and ema_cross_up:
            st.close("Short")
        self.plot(ema_val, "EMA", color=color.orange)
        self.plot(sma_val, "SMA", color=color.blue)
        self.plot(kijun, "Ichimoku Base Line (KS)", color=color.purple)
        self.plot(rsi_value, "RSI", color=color.green)
        self.plot(rsi_wma, "RSI WMA", color=color.red)
