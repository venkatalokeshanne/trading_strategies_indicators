"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : Strategy_501 de FranPineda
Author       : Fran_Pineda
Source URL   : https://www.tradingview.com/script/V9WyS98w
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-29 by Claude (pine-to-python skill)

Line-for-line translation (process_orders_on_close, which has no effect here: every order is a stop entry). The 06:00-08:59 New York range is the day's range; inside the entry window a sweep of the range low (high) arms a LONG (SHORT) setup: a buy-stop at the post-range high (sell-stop at the post-range low) with a stop beyond the other post-range extreme and a 1R target, renewed on every bar; after the "move to BE" time the stop of the open position is set to its entry price. Unfilled orders are cancelled when the entry window ends.

Deviations from the original: none.
Not carried over: range box, level lines, labels and alert conditions (display only).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, na, pmath


class Strategy501(Script):
    TITLE = "Strategy_501 de FranPineda"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(pyramiding=0, initial_capital=10000, process_orders_on_close=True)
    SOURCE = {"id": "V9WyS98w", "author": "Fran_Pineda", "licence": "not stated",
              "url": "https://www.tradingview.com/script/V9WyS98w"}

    def init(self):
        i = self.input
        g = "Horario"
        self.range_session = i.session("0600-0859", "Rango H3 NY", group=g)
        self.start_hour = i.int(9, "Hora inicio entradas", minval=0, maxval=23, group=g)
        self.start_minute = i.int(0, "Minuto inicio entradas", minval=0, maxval=59, group=g)
        self.end_hour = i.int(12, "Hora fin entradas", minval=0, maxval=23, group=g)
        self.end_minute = i.int(30, "Minuto fin entradas", minval=0, maxval=59, group=g)
        g = "Gestión"
        self.be_hour = i.int(16, "Hora mover a BE", minval=0, maxval=23, group=g)
        self.be_minute = i.int(0, "Minuto mover a BE", minval=0, maxval=59, group=g)
        self.sl_buffer = i.float(2.0, "SL Buffer", step=0.25, group=g)
        self.trade_taken = False
        self.pending_order_placed = False
        self.be_moved = False
        self.range_high = NA
        self.range_low = NA
        self.range_ready = False
        self.post_range_high = NA
        self.post_range_low = NA
        self.long_setup = False
        self.short_setup = False
        self.long_entry_price = NA
        self.long_sl = NA
        self.long_tp = NA
        self.short_entry_price = NA
        self.short_sl = NA
        self.short_tp = NA
        self.prev_dom = NA

    def on_bar(self):
        st = self.strategy
        high, low = self.high, self.low
        tz = "America/New_York"
        ny_hour = self.hour(self.time, tz)
        ny_minute = self.minute(self.time, tz)
        after_start = ny_hour > self.start_hour or (ny_hour == self.start_hour and ny_minute >= self.start_minute)
        before_end = ny_hour < self.end_hour or (ny_hour == self.end_hour and ny_minute <= self.end_minute)
        allowed_trading = after_start and before_end
        after_entry_window = ny_hour > self.end_hour or (ny_hour == self.end_hour and ny_minute > self.end_minute)
        be_time_reached = ny_hour > self.be_hour or (ny_hour == self.be_hour and ny_minute >= self.be_minute)
        dom = self.dayofmonth(self.time, tz)
        new_day = na(self.prev_dom) or dom != self.prev_dom
        self.prev_dom = dom
        if new_day:
            self.trade_taken = False
            self.pending_order_placed = False
            self.be_moved = False
        in_range = not na(self.time_fn(None, self.range_session, tz))
        in_range_h = self.H("in_range")
        in_range_1 = in_range_h[1]
        in_range_h.set(in_range)
        new_range = in_range and not ((not na(in_range_1)) and bool(in_range_1))
        end_range = (not in_range) and ((not na(in_range_1)) and bool(in_range_1))
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
        if new_day:
            self.post_range_high = NA
            self.post_range_low = NA
        if end_range:
            self.post_range_high = float(high)
            self.post_range_low = float(low)
        if self.range_ready and (not in_range) and (not self.trade_taken) and st.position_size == 0:
            self.post_range_high = float(high) if na(self.post_range_high) else pmath.max(self.post_range_high, high)
            self.post_range_low = float(low) if na(self.post_range_low) else pmath.min(self.post_range_low, low)
        if new_day:
            self.long_setup = False
            self.short_setup = False
            self.long_entry_price = NA
            self.long_sl = NA
            self.long_tp = NA
            self.short_entry_price = NA
            self.short_sl = NA
            self.short_tp = NA
        if self.range_ready and allowed_trading and (not self.trade_taken) and st.position_size == 0 and low < self.range_low:
            self.long_setup = True
            self.short_setup = False
            self.short_entry_price = NA
            self.short_sl = NA
            self.short_tp = NA
            st.cancel("SHORT")
        if self.range_ready and allowed_trading and (not self.trade_taken) and st.position_size == 0 and high > self.range_high:
            self.short_setup = True
            self.long_setup = False
            self.long_entry_price = NA
            self.long_sl = NA
            self.long_tp = NA
            st.cancel("LONG")
        if self.long_setup and allowed_trading and (not self.trade_taken) and st.position_size == 0 and (not na(self.post_range_high)) and not na(self.post_range_low):
            temp_entry = self.post_range_high
            temp_sl = self.post_range_low - self.sl_buffer
            temp_risk = temp_entry - temp_sl
            temp_tp = temp_entry + temp_risk
            if temp_risk > 0:
                self.long_entry_price = temp_entry
                self.long_sl = temp_sl
                self.long_tp = temp_tp
        if self.short_setup and allowed_trading and (not self.trade_taken) and st.position_size == 0 and (not na(self.post_range_high)) and not na(self.post_range_low):
            temp_entry = self.post_range_low
            temp_sl = self.post_range_high + self.sl_buffer
            temp_risk = temp_sl - temp_entry
            temp_tp = temp_entry - temp_risk
            if temp_risk > 0:
                self.short_entry_price = temp_entry
                self.short_sl = temp_sl
                self.short_tp = temp_tp
        if self.long_setup and allowed_trading and (not self.trade_taken) and st.position_size == 0 and (not na(self.long_entry_price)) \
                and (not na(self.long_sl)) and not na(self.long_tp):
            st.entry("LONG", st.long, stop=self.long_entry_price)
            st.exit("LONG EXIT", from_entry="LONG", stop=self.long_sl, limit=self.long_tp)
            self.pending_order_placed = True
        if self.short_setup and allowed_trading and (not self.trade_taken) and st.position_size == 0 and (not na(self.short_entry_price)) \
                and (not na(self.short_sl)) and not na(self.short_tp):
            st.entry("SHORT", st.short, stop=self.short_entry_price)
            st.exit("SHORT EXIT", from_entry="SHORT", stop=self.short_sl, limit=self.short_tp)
            self.pending_order_placed = True
        if after_entry_window and st.position_size == 0 and not self.trade_taken:
            st.cancel("LONG")
            st.cancel("SHORT")
            self.long_setup = False
            self.short_setup = False
            self.pending_order_placed = False
        if st.position_size != 0 and not self.trade_taken:
            self.trade_taken = True
        if be_time_reached and st.position_size > 0 and not self.be_moved:
            st.exit("LONG EXIT", from_entry="LONG", stop=st.position_avg_price, limit=self.long_tp)
            self.be_moved = True
        if be_time_reached and st.position_size < 0 and not self.be_moved:
            st.exit("SHORT EXIT", from_entry="SHORT", stop=st.position_avg_price, limit=self.short_tp)
            self.be_moved = True
