"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : Europon Reversal FX Rush Ver2 Strategy
Author       : MasayanFX
Source URL   : https://www.tradingview.com/script/8LSSyeLc
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-29 by Claude (pine-to-python skill)

Line-for-line translation (market orders at the next open; only on the 1-hour chart). The RSI of two bars ago (period 3) below the low level during the server-time trade hours buys, above the high level sells (a signal against an open position closes it first and reverses). While long (short) with fewer than the maximum positions, a "nanpin" averaging
entry is added when the previous bar was bullish (bearish) and the shifted RSI is below 3/4 of the low level for the second position (1/2 for the third) - mirrored above the high level for shorts. Every bar re-issues one exit order for the position: stop and take-profit a fixed distance (price unit x request) from the average entry price.
Deviations from the original: none.
Not carried over: the signal background shading and additional-signal markers (display only).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import Script, ta


class EuroponReversalFxRush(Script):
    TITLE = "Europon Reversal FX Rush Ver2 Strategy"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(fill_orders_on_standard_ohlc=True, pyramiding=3)
    SOURCE = {"id": "8LSSyeLc", "author": "MasayanFX", "licence": "not stated", "url": "https://www.tradingview.com/script/8LSSyeLc"}

    def init(self):
        i = self.input
        self.rsi_period = i.int(3, "RSI Period", minval=1)
        self.rsi_shift = i.int(2, "RSI Signal Shift", minval=0)
        self.rsi_high = i.float(60.0, "RSI High Level", minval=50.0, maxval=100.0)
        self.rsi_low = i.float(40.0, "RSI Low Level", minval=0.0, maxval=50.0)
        self.nanpin = i.bool(True, "Enable Nanpin")
        self.short_nanpin = i.bool(True, "Enable Short Nanpin")
        self.max_positions = i.int(3, "Max Positions", minval=1, maxval=3)
        self.use_trade_hour_filter = i.bool(True, "Use Trade Hour Filter")
        self.server_tz = i.string("Europe/Nicosia", "MT4/MT5 Server Time Zone", options=["Europe/Nicosia", "Etc/GMT-2", "Etc/GMT-3", "Asia/Tokyo", "UTC"])
        self.start_hour = i.int(1, "Start Hour", minval=0, maxval=23)
        self.end_hour = i.int(9, "End Hour", minval=0, maxval=23)
        self.price_unit = i.float(0.01, "Price Unit", minval=0.00001, step=0.001)
        self.stop_loss_request = i.float(4.0, "Stop Loss Request", minval=0.1)
        self.take_profit_request = i.float(4.0, "Take Profit Request", minval=0.1)

    def on_bar(self):
        st = self.strategy
        rsi_raw = ta.rsi(self.close, self.rsi_period)
        rh = self.H("rsi")
        rsi_value = rh[self.rsi_shift] if self.rsi_shift > 0 else rsi_raw
        rh.set(rsi_raw)
        server_hour = self.hour(self.time, self.server_tz)
        if self.start_hour <= self.end_hour:
            in_hours = server_hour >= self.start_hour and server_hour <= self.end_hour
        else:
            in_hours = server_hour >= self.start_hour or server_hour <= self.end_hour
        is_trade_hour = (not self.use_trade_hour_filter) or in_hours
        is_h1 = self.timeframe.isminutes and self.timeframe.multiplier == 60
        trade_allowed = is_h1 and is_trade_hour
        long_nanpin_level2 = self.rsi_low - self.rsi_low / 4.0
        long_nanpin_level3 = self.rsi_low - self.rsi_low / 2.0
        short_nanpin_level2 = self.rsi_high + (100.0 - self.rsi_high) / 4.0
        short_nanpin_level3 = self.rsi_high + (100.0 - self.rsi_high) / 2.0
        previous_bull = self.open[1] < self.close[1]
        previous_bear = self.open[1] > self.close[1]
        buy_signal = trade_allowed and rsi_value < self.rsi_low
        sell_signal = trade_allowed and rsi_value > self.rsi_high
        long_nanpin2 = trade_allowed and self.nanpin and previous_bull and rsi_value < long_nanpin_level2
        long_nanpin3 = trade_allowed and self.nanpin and previous_bull and rsi_value < long_nanpin_level3
        short_nanpin2 = trade_allowed and self.nanpin and self.short_nanpin and previous_bear and rsi_value > short_nanpin_level2
        short_nanpin3 = trade_allowed and self.nanpin and self.short_nanpin and previous_bear and rsi_value > short_nanpin_level3
        flat = st.position_size == 0
        in_long = st.position_size > 0
        in_short = st.position_size < 0
        position_count = st.opentrades
        if buy_signal and in_short:
            st.close("Short")
            st.entry("Long", st.long)
        elif buy_signal and flat:
            st.entry("Long", st.long)
        if sell_signal and in_long:
            st.close("Long")
            st.entry("Short", st.short)
        elif sell_signal and flat:
            st.entry("Short", st.short)
        if in_long and position_count < self.max_positions:
            if position_count == 1 and long_nanpin2:
                st.entry("Long", st.long)
            elif position_count == 2 and long_nanpin3:
                st.entry("Long", st.long)
        if in_short and self.short_nanpin and position_count < self.max_positions:
            if position_count == 1 and short_nanpin2:
                st.entry("Short", st.short)
            elif position_count == 2 and short_nanpin3:
                st.entry("Short", st.short)
        stop_distance = self.price_unit * self.stop_loss_request
        take_distance = self.price_unit * self.take_profit_request
        if in_long:
            st.exit("Long Exit", from_entry="Long", stop=st.position_avg_price - stop_distance, limit=st.position_avg_price + take_distance)
        if in_short:
            st.exit("Short Exit", from_entry="Short", stop=st.position_avg_price + stop_distance, limit=st.position_avg_price - take_distance)
