"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : Initial Balance Breakout (IBB)
Author       : Bnf6082
Source URL   : https://www.tradingview.com/script/MyjxUMGt-Initial-Balance-Breakout-Strategy
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-29 by Claude (pine-to-python skill)

Line-for-line translation (process_orders_on_close, which only acts on the time-stop market close). The high / low of the first hour (ET) is the initial balance; if its size is within the percentage limits and the price breaks out of only one side during the entry window, a resting limit entry is placed at a retracement of the range back toward the breakout side, with a stop at a fraction of the range and a target a multiple of the range beyond the breakout level. The pending order is cancelled when the window ends or the other side breaks; any position is closed at the time stop.

Deviations from the original: none.
Not carried over: IB lines, box, label, signal shapes and the performance table (display only).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, div, na, pmath


class InitialBalanceBreakout(Script):
    TITLE = "Initial Balance Breakout (IBB)"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(default_qty_type="fixed", default_qty_value=1, commission_type="cash_per_contract", commission_value=2.50, slippage=1,
                    pyramiding=0, process_orders_on_close=True)
    SOURCE = {"id": "MyjxUMGt", "author": "Bnf6082", "licence": "not stated",
              "url": "https://www.tradingview.com/script/MyjxUMGt-Initial-Balance-Breakout-Strategy"}

    def init(self):
        i = self.input
        g = "Initial Balance Window"
        self.ib_start_hour = i.int(9, "IB Start Hour", group=g, minval=0, maxval=23)
        self.ib_start_minute = i.int(30, "IB Start Minute", group=g, minval=0, maxval=59)
        self.ib_end_hour = i.int(10, "IB End Hour", group=g, minval=0, maxval=23)
        self.ib_end_minute = i.int(30, "IB End Minute", group=g, minval=0, maxval=59)
        g = "Entry Rules"
        self.entry_window_end_hour = i.int(13, "Entry Window End Hour", group=g, minval=0, maxval=23)
        self.entry_window_end_minute = i.int(0, "Entry Window End Minute", group=g, minval=0, maxval=59)
        self.retracement_pct = i.float(25.0, "Retracement % for Entry", group=g, minval=1, maxval=99, step=1)
        self.min_ib_size_pct = i.float(0.3, "Min IB Size %", group=g, minval=0.05, step=0.05)
        self.max_ib_size_pct = i.float(1.5, "Max IB Size %", group=g, minval=0.1, step=0.1)
        g = "Exit Rules"
        self.close_hour = i.int(15, "Time Stop Hour", group=g, minval=0, maxval=23)
        self.close_minute = i.int(30, "Time Stop Minute", group=g, minval=0, maxval=59)
        self.stop_pct_of_ib = i.float(60.0, "Stop Loss % of IB Range", group=g, minval=1, maxval=99, step=1)
        self.tp1_multiplier = i.float(0.50, "TP Multiplier (× IB)", group=g, minval=0.1, step=0.05)
        self.ib_high = NA
        self.ib_low = NA
        self.ib_range = NA
        self.ib_valid = False
        self.ib_locked = False
        self.traded_today = False
        self.broke_high = False
        self.broke_low = False
        self.order_placed_today = False
        self.entry_price = NA
        self.stop_price = NA
        self.tp1_price = NA
        self.trade_direction = 0

    def on_bar(self):
        st = self.strategy
        high, low, close = self.high, self.low, self.close
        ny_time = self.hour(self.time, "America/New_York") * 60 + self.minute(self.time, "America/New_York")
        ib_start_mins = self.ib_start_hour * 60 + self.ib_start_minute
        ib_end_mins = self.ib_end_hour * 60 + self.ib_end_minute
        entry_window_end_mins = self.entry_window_end_hour * 60 + self.entry_window_end_minute
        close_mins = self.close_hour * 60 + self.close_minute
        at_ib_start = ny_time == ib_start_mins
        in_ib_window = ny_time >= ib_start_mins and ny_time < ib_end_mins
        ib_just_closed = ny_time == ib_end_mins
        in_entry_window = ny_time >= ib_end_mins and ny_time < entry_window_end_mins
        at_close_time = ny_time >= close_mins
        if at_ib_start:
            self.ib_high = float(high)
            self.ib_low = float(low)
            self.ib_locked = False
            self.ib_valid = False
            self.traded_today = False
            self.broke_high = False
            self.broke_low = False
            self.order_placed_today = False
        if in_ib_window and not self.ib_locked:
            self.ib_high = pmath.max(self.ib_high, high)
            self.ib_low = pmath.min(self.ib_low, low)
        if ib_just_closed and (not self.ib_locked) and not na(self.ib_high):
            self.ib_locked = True
            self.ib_range = self.ib_high - self.ib_low
            ib_pct = div(self.ib_range, self.ib_high) * 100 if self.ib_high > 0 else 0.0
            self.ib_valid = ib_pct >= self.min_ib_size_pct and ib_pct <= self.max_ib_size_pct
        if self.ib_locked and self.ib_valid and in_entry_window and not self.traded_today:
            if high > self.ib_high:
                self.broke_high = True
            if low < self.ib_low:
                self.broke_low = True
        retrace_long_zone = self.ib_high - self.ib_range * (self.retracement_pct / 100) if (not na(self.ib_high)) and not na(self.ib_range) else NA
        retrace_short_zone = self.ib_low + self.ib_range * (self.retracement_pct / 100) if (not na(self.ib_low)) and not na(self.ib_range) else NA
        if st.position_size != 0 and not self.traded_today:
            self.traded_today = True
        long_order = self.ib_locked and self.ib_valid and in_entry_window and (not self.traded_today) and (not self.order_placed_today) and self.broke_high and not self.broke_low
        short_order = self.ib_locked and self.ib_valid and in_entry_window and (not self.traded_today) and (not self.order_placed_today) and self.broke_low and not self.broke_high
        if long_order and st.position_size == 0:
            self.entry_price = retrace_long_zone
            self.stop_price = self.ib_high - self.ib_range * (self.stop_pct_of_ib / 100)
            self.tp1_price = self.ib_high + self.ib_range * self.tp1_multiplier
            self.trade_direction = 1
            self.order_placed_today = True
            st.entry("Long", st.long, limit=self.entry_price)
            st.exit("Long TP", from_entry="Long", limit=self.tp1_price, stop=self.stop_price, comment="TP")
        elif short_order and st.position_size == 0:
            self.entry_price = retrace_short_zone
            self.stop_price = self.ib_low + self.ib_range * (self.stop_pct_of_ib / 100)
            self.tp1_price = self.ib_low - self.ib_range * self.tp1_multiplier
            self.trade_direction = -1
            self.order_placed_today = True
            st.entry("Short", st.short, limit=self.entry_price)
            st.exit("Short TP", from_entry="Short", limit=self.tp1_price, stop=self.stop_price, comment="TP")
        if self.order_placed_today and (not self.traded_today) and st.position_size == 0:
            if (not in_entry_window) or (self.trade_direction == 1 and self.broke_low) or (self.trade_direction == -1 and self.broke_high):
                st.cancel_all()
                self.order_placed_today = False
        if at_close_time and st.position_size != 0:
            st.close_all(comment="Time Stop")
