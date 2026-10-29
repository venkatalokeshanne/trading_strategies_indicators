"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : Scalping London New York Strategy
Author       : MasayanFX
Source URL   : https://www.tradingview.com/script/yK5180DE
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. The previous bar's candle colour and fast/slow SMA order (SMA periods divided by 5 on a 5-minute chart) give a long or
short signal inside the hour filter. A signal while flat opens a lot; a signal against the open side closes it; while in a position a lot is added
("nanpin") each time the close moves one step against the last entry, up to Max Positions. A stop and limit around the average price are issued each
bar while a position exists.

Deviations from the original: none.
Not carried over: background colour and signal shapes (cosmetic).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, color, na, pmath, ta


class ScalpingLondonNewYork(Script):
    TITLE = "Scalping London New York Strategy"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(pyramiding=10, initial_capital=10000)
    SOURCE = {"id": "yK5180DE", "author": "MasayanFX", "licence": "not stated",
              "url": "https://www.tradingview.com/script/yK5180DE"}

    def init(self):
        self.fast_in = self.input.int(60, "Fast SMA Period", minval=1)
        self.slow_in = self.input.int(280, "Slow SMA Period", minval=1)
        self.max_positions = self.input.int(10, "Max Positions", minval=1, maxval=10)
        self.sl_req = self.input.float(4.0, "Stop Loss Request", minval=0.1)
        self.tp_req = self.input.float(5.0, "Take Profit Request", minval=0.1)
        self.step_req = self.input.float(0.2, "Nanpin Step Request", minval=0.01)
        self.only_long = self.input.bool(False, "Only Long")
        self.short_nanpin = self.input.bool(True, "Short Nanpin")
        self.use_time_filter = self.input.bool(True, "Use Time Filter")
        self.start_hour = self.input.int(7, "Start Hour", minval=0, maxval=23)
        self.end_hour = self.input.int(17, "End Hour", minval=0, maxval=23)
        self.last_long_entry = NA
        self.last_short_entry = NA
        self.long_count = 0
        self.short_count = 0

    def on_bar(self):
        tf = self.timeframe
        is_m5 = tf.isminutes and tf.multiplier == 5
        fast_period = pmath.max(1, int(self.fast_in / 5)) if is_m5 else self.fast_in
        slow_period = pmath.max(1, int(self.slow_in / 5)) if is_m5 else self.slow_in
        fast_ma = ta.sma(self.close, fast_period)
        slow_ma = ta.sma(self.close, slow_period)
        fast_prev = self.H("fast")[1]
        slow_prev = self.H("slow")[1]
        self.H("fast").set(fast_ma)
        self.H("slow").set(slow_ma)
        h = self.hour(self.time)
        if not self.use_time_filter:
            time_allowed = True
        elif self.start_hour <= self.end_hour:
            time_allowed = h >= self.start_hour and h <= self.end_hour
        else:
            time_allowed = h >= self.start_hour or h <= self.end_hour
        is_jpy = "JPY" in str(self.syminfo.ticker)
        pips = 1.0 if is_jpy else 0.01
        long_signal = self.barstate.isconfirmed and time_allowed and self.open[1] < self.close[1] and fast_prev > slow_prev
        short_signal = self.barstate.isconfirmed and time_allowed and self.open[1] > self.close[1] and fast_prev < slow_prev and not self.only_long
        st = self.strategy
        flat = st.position_size == 0
        in_long = st.position_size > 0
        in_short = st.position_size < 0
        if flat:
            self.long_count = 0
            self.short_count = 0
            self.last_long_entry = NA
            self.last_short_entry = NA
        if long_signal and in_short:
            st.close("Short")
            self.short_count = 0
            self.last_short_entry = NA
        if short_signal and in_long:
            st.close("Long")
            self.long_count = 0
            self.last_long_entry = NA
        if long_signal and flat:
            st.entry("Long", st.long)
            self.last_long_entry = float(self.close)
            self.long_count = 1
        if short_signal and flat:
            st.entry("Short", st.short)
            self.last_short_entry = float(self.close)
            self.short_count = 1
        long_nanpin = in_long and self.long_count < self.max_positions and not na(self.last_long_entry) and self.close <= self.last_long_entry - pips * self.step_req
        short_nanpin = (in_short and self.short_count < self.max_positions and self.short_nanpin and not self.only_long and not na(self.last_short_entry)
                        and self.close >= self.last_short_entry + pips * self.step_req)
        if long_nanpin:
            st.entry("Long", st.long)
            self.last_long_entry = float(self.close)
            self.long_count += 1
        if short_nanpin:
            st.entry("Short", st.short)
            self.last_short_entry = float(self.close)
            self.short_count += 1
        avg = st.position_avg_price
        if in_long:
            st.exit("Long Exit", from_entry="Long", stop=avg - pips * self.sl_req, limit=avg + pips * self.tp_req)
        if in_short:
            st.exit("Short Exit", from_entry="Short", stop=avg + pips * self.sl_req, limit=avg - pips * self.tp_req)
        self.plot(fast_ma, "Fast SMA", color=color.aqua, linewidth=2)
        self.plot(slow_ma, "Slow SMA", color=color.orange, linewidth=2)
