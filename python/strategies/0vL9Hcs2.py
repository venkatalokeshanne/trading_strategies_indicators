"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : Strategy_470 - NY Open 3H Sweep Continuation
Author       : Fran_Pineda
Source URL   : https://www.tradingview.com/script/0vL9Hcs2
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-29 by Claude (pine-to-python skill)

Line-for-line translation (process_orders_on_close). Inside the New York window (09:00-10:30) a bar that trades below the previous 3-hour bar's low (above its high) arms a long (short) setup; the entry level is the latest confirmed swing high (low), the stop the extreme of the sweep bars +/- a tick buffer and the
target the other side of the previous 3-hour range. The bar whose high (low) reaches the entry level enters at its close (once per day). Once in the trade the stop moves to the entry price after a +1R move, and the stop / target are re-issued at every bar of the position.

Deviations from the original: none.
Not carried over: the previous-range lines, signal markers and the debug table (display only).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, div, na, pmath, ta


class NyOpen3hSweep(Script):
    TITLE = "Strategy_470 - NY Open 3H Sweep Continuation"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(initial_capital=10000, pyramiding=0, commission_type="percent", commission_value=0.0, process_orders_on_close=True)
    SOURCE = {"id": "0vL9Hcs2", "author": "Fran_Pineda", "licence": "not stated",
              "url": "https://www.tradingview.com/script/0vL9Hcs2"}

    def init(self):
        i = self.input
        self.ny_session = i.session("0900-1030", "NY Trading Window")
        self.ny_timezone = i.string("America/New_York", "Timezone")
        self.use_longs = i.bool(True, "Enable Longs")
        self.use_shorts = i.bool(True, "Enable Shorts")
        self.swing_len = i.int(2, "Swing Length", minval=1, maxval=10)
        self.buffer_ticks = i.int(2, "SL Buffer Ticks", minval=0, maxval=100)
        self.use_break_even = i.bool(True, "Move SL to BE at +1R")
        self.one_trade_day = i.bool(True, "Max 1 Trade Per Day")
        self.position_pct = i.float(95.0, "Position Size % of Equity", minval=1, maxval=100, step=1)
        self.traded_today = False
        self.last_swing_high = NA
        self.last_swing_low = NA
        self.long_sweep_detected = False
        self.short_sweep_detected = False
        self.long_sweep_low = NA
        self.short_sweep_high = NA
        self.long_entry_level = NA
        self.short_entry_level = NA
        self.long_sl = NA
        self.long_tp = NA
        self.short_sl = NA
        self.short_tp = NA
        self.active_long_sl = NA
        self.active_long_tp = NA
        self.active_short_sl = NA
        self.active_short_tp = NA
        self.long_be_activated = False
        self.short_be_activated = False

    def on_bar(self):
        st = self.strategy
        close, high, low = self.close, self.high, self.low
        pos_h = self.H("pos")
        pos_1 = pos_h[1]
        pos_h.set(st.position_size)
        in_session = not na(self.time_fn(None, self.ny_session, self.ny_timezone))
        day_change = ta.change(self.time_fn("D", "0000-2359", self.ny_timezone))
        new_day = (not na(day_change)) and day_change != 0
        if new_day:
            self.traded_today = False
        can_trade_today = (not self.traded_today) if self.one_trade_day else True
        h3_high_prev = self.security(None, "180", lambda v: v.high[1], lookahead=False)
        h3_low_prev = self.security(None, "180", lambda v: v.low[1], lookahead=False)
        pivot_high = ta.pivothigh(high, self.swing_len, self.swing_len)
        pivot_low = ta.pivotlow(low, self.swing_len, self.swing_len)
        if not na(pivot_high):
            self.last_swing_high = pivot_high
        if not na(pivot_low):
            self.last_swing_low = pivot_low
        if new_day:
            self.long_sweep_detected = False
            self.short_sweep_detected = False
            self.long_sweep_low = NA
            self.short_sweep_high = NA
            self.long_entry_level = NA
            self.short_entry_level = NA
            self.long_sl = NA
            self.long_tp = NA
            self.short_sl = NA
            self.short_tp = NA
        sl_buffer = self.buffer_ticks * self.syminfo.mintick
        if in_session and can_trade_today and st.position_size == 0:
            if self.use_longs and low < h3_low_prev:
                self.long_sweep_detected = True
                self.long_sweep_low = float(low) if na(self.long_sweep_low) else pmath.min(self.long_sweep_low, low)
            if self.use_shorts and high > h3_high_prev:
                self.short_sweep_detected = True
                self.short_sweep_high = float(high) if na(self.short_sweep_high) else pmath.max(self.short_sweep_high, high)
        if in_session and can_trade_today and st.position_size == 0:
            if self.long_sweep_detected and not na(self.last_swing_high):
                self.long_entry_level = self.last_swing_high
                self.long_sl = self.long_sweep_low - sl_buffer
                self.long_tp = h3_high_prev
            if self.short_sweep_detected and not na(self.last_swing_low):
                self.short_entry_level = self.last_swing_low
                self.short_sl = self.short_sweep_high + sl_buffer
                self.short_tp = h3_low_prev
        qty = div(st.equity * self.position_pct / 100.0, close)
        long_ready = (in_session and can_trade_today and self.use_longs and st.position_size == 0 and self.long_sweep_detected and (not na(self.long_entry_level))
                      and (not na(self.long_sl)) and (not na(self.long_tp)) and self.long_entry_level > self.long_sl and self.long_tp > self.long_entry_level)
        short_ready = (in_session and can_trade_today and self.use_shorts and st.position_size == 0 and self.short_sweep_detected and (not na(self.short_entry_level))
                       and (not na(self.short_sl)) and (not na(self.short_tp)) and self.short_entry_level < self.short_sl and self.short_tp < self.short_entry_level)
        long_trigger = long_ready and high >= self.long_entry_level
        short_trigger = short_ready and low <= self.short_entry_level
        if long_trigger:
            st.entry("Long", st.long, qty=qty)
            self.traded_today = True
        if short_trigger:
            st.entry("Short", st.short, qty=qty)
            self.traded_today = True
        new_long_position = st.position_size > 0 and (not na(pos_1)) and pos_1 <= 0
        new_short_position = st.position_size < 0 and (not na(pos_1)) and pos_1 >= 0
        if new_long_position:
            self.active_long_sl = self.long_sl
            self.active_long_tp = self.long_tp
            self.long_be_activated = False
        if new_short_position:
            self.active_short_sl = self.short_sl
            self.active_short_tp = self.short_tp
            self.short_be_activated = False
        if st.position_size == 0:
            self.active_long_sl = NA
            self.active_long_tp = NA
            self.active_short_sl = NA
            self.active_short_tp = NA
            self.long_be_activated = False
            self.short_be_activated = False
        if st.position_size > 0 and self.use_break_even and (not self.long_be_activated) and not na(self.active_long_sl):
            entry_price = st.position_avg_price
            risk_long = entry_price - self.active_long_sl
            be_trigger_long = entry_price + risk_long
            if risk_long > 0 and high >= be_trigger_long:
                self.active_long_sl = entry_price
                self.long_be_activated = True
        if st.position_size < 0 and self.use_break_even and (not self.short_be_activated) and not na(self.active_short_sl):
            entry_price = st.position_avg_price
            risk_short = self.active_short_sl - entry_price
            be_trigger_short = entry_price - risk_short
            if risk_short > 0 and low <= be_trigger_short:
                self.active_short_sl = entry_price
                self.short_be_activated = True
        if st.position_size > 0:
            st.exit("Long Exit", from_entry="Long", stop=self.active_long_sl, limit=self.active_long_tp)
        if st.position_size < 0:
            st.exit("Short Exit", from_entry="Short", stop=self.active_short_sl, limit=self.active_short_tp)
