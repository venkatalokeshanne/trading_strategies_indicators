"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : NAS100 / SP500 - Turtle Soup NY V4 FIXED
Author       : pacorodriguez_ber
Source URL   : https://www.tradingview.com/script/qfqRq8DM
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-29 by Claude (pine-to-python skill)

Line-for-line translation. The 06:00-08:59 New York range's high / low are tracked each day and are usable once it ends. Between 09:30 and 12:00 a sweep of the low (high) arms a long (short) setup; the next bullish (bearish)
rejection candle (closing beyond the bar's midpoint) with reward / risk of at least `RR mínimo` enters at the next open with the stop beyond the sweep extreme +/- buffer and the target at the opposite range side, both placed with the entry.
One trade per day. The setups are not reset at the day change and the entry itself is not time-gated, as in the original.

Deviations from the original: none.
Not carried over: the range box, range lines, trade lines, labels and alerts (display only).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, div, na, pmath

NY = "America/New_York"


class TurtleSoupNy(Script):
    TITLE = "NAS100 / SP500 - Turtle Soup NY V4 FIXED"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(pyramiding=0, initial_capital=10000)
    SOURCE = {"id": "qfqRq8DM", "author": "pacorodriguez_ber", "licence": "not stated",
              "url": "https://www.tradingview.com/script/qfqRq8DM"}

    def init(self):
        g = "Horario"
        self.range_session = self.input.session("0600-0859", "Rango NY", group=g)
        self.start_hour = self.input.int(9, "Hora inicio", minval=0, maxval=23, group=g)
        self.start_minute = self.input.int(30, "Minuto inicio", minval=0, maxval=59, group=g)
        self.end_hour = self.input.int(12, "Hora fin", minval=0, maxval=23, group=g)
        self.end_minute = self.input.int(0, "Minuto fin", minval=0, maxval=59, group=g)
        g = "Gestión"
        self.sl_buffer = self.input.float(2.0, "SL Buffer", step=0.25, group=g)
        self.minimum_rr = self.input.float(1.0, "RR mínimo", step=0.1, group=g)
        self.trade_taken = False
        self.range_high = NA
        self.range_low = NA
        self.range_ready = False
        self.long_setup = False
        self.short_setup = False
        self.long_manipulation_low = NA
        self.short_manipulation_high = NA

    def on_bar(self):
        st = self.strategy
        close, open_, high, low = self.close, self.open, self.high, self.low
        ny_hour = self.hour(self.time, NY)
        ny_minute = self.minute(self.time, NY)
        after_start = ny_hour > self.start_hour or (ny_hour == self.start_hour and ny_minute >= self.start_minute)
        before_end = ny_hour < self.end_hour or (ny_hour == self.end_hour and ny_minute <= self.end_minute)
        allowed_trading = after_start and before_end
        time_1 = self.time[1]
        new_day = (not na(time_1)) and self.dayofmonth(self.time, NY) != self.dayofmonth(time_1, NY)
        if new_day:
            self.trade_taken = False
        in_range = not na(self.time_fn(None, self.range_session, NY))
        ir_h = self.H("inr")
        in_range_1 = ir_h[1]
        ir_h.set(in_range)
        prev_in = (not na(in_range_1)) and bool(in_range_1)
        new_range = in_range and not prev_in
        end_range = (not in_range) and prev_in
        if new_day:
            self.range_high = NA
            self.range_low = NA
            self.range_ready = False
        if new_range:
            self.range_high = float(high)
            self.range_low = float(low)
        if in_range:
            self.range_high = pmath.max(self.range_high, high)
            self.range_low = pmath.min(self.range_low, low)
        if end_range:
            self.range_ready = True
        sweep_low = low < self.range_low
        sweep_high = high > self.range_high
        bullish_rejection = close > open_ and close > ((high + low) / 2)
        bearish_rejection = close < open_ and close < ((high + low) / 2)
        if self.range_ready and allowed_trading and not self.trade_taken:
            if sweep_low:
                self.long_setup = True
                self.short_setup = False
                self.long_manipulation_low = float(low)
        if self.range_ready and allowed_trading and not self.trade_taken:
            if sweep_high:
                self.short_setup = True
                self.long_setup = False
                self.short_manipulation_high = float(high)
        long_signal = False
        long_sl = NA
        long_tp = NA
        if self.long_setup and bullish_rejection:
            temp_sl = self.long_manipulation_low - self.sl_buffer
            temp_entry = float(close)
            temp_tp = self.range_high
            risk = temp_entry - temp_sl
            reward = temp_tp - temp_entry
            rr = div(reward, risk)
            if rr >= self.minimum_rr:
                long_signal = True
                long_sl = temp_sl
                long_tp = temp_tp
        short_signal = False
        short_sl = NA
        short_tp = NA
        if self.short_setup and bearish_rejection:
            temp_sl = self.short_manipulation_high + self.sl_buffer
            temp_entry = float(close)
            temp_tp = self.range_low
            risk = temp_sl - temp_entry
            reward = temp_entry - temp_tp
            rr = div(reward, risk)
            if rr >= self.minimum_rr:
                short_signal = True
                short_sl = temp_sl
                short_tp = temp_tp
        if long_signal and st.position_size == 0 and not self.trade_taken:
            st.entry("LONG", st.long)
            st.exit("LONG EXIT", from_entry="LONG", stop=long_sl, limit=long_tp)
            self.trade_taken = True
            self.long_setup = False
        if short_signal and st.position_size == 0 and not self.trade_taken:
            st.entry("SHORT", st.short)
            st.exit("SHORT EXIT", from_entry="SHORT", stop=short_sl, limit=short_tp)
            self.trade_taken = True
            self.short_setup = False
