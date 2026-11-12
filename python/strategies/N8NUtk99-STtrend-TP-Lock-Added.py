"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : STtrend - TP Lock Added
Author       : apkw82
Source URL   : https://www.tradingview.com/script/N8NUtk99-STtrend-TP-Lock-Added
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-29 by Claude (pine-to-python skill)

Line-for-line translation (market orders at the next open). A Supertrend flip to up (down) closes the short (long) and enters one unit in the new direction. While in a position, a stop and an optional hard take-profit (both given in dollars, converted to points by the point value) are re-issued every bar from the average entry price: the stop starts at the initial dollar risk and is raised
(lowered for shorts) to lock profit once the open profit passes the lock triggers; the tracked stop only ever tightens, and it is not cleared by a direct reversal (only when flat). A Supertrend flip against the position also closes it.
Deviations from the original: none.
Not carried over: the lock / take-profit / trade labels and flags used only for them (display only).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, div, na, pmath, ta


class StTrendTpLock(Script):
    TITLE = "STtrend - TP Lock Added"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(pyramiding=0, initial_capital=500000, default_qty_type="fixed", default_qty_value=1, margin_long=5, margin_short=5)
    SOURCE = {"id": "N8NUtk99", "author": "apkw82", "licence": "not stated", "url": "https://www.tradingview.com/script/N8NUtk99-STtrend-TP-Lock-Added"}

    def init(self):
        i = self.input
        self.atr_period = i.int(10, "ATR Period", minval=1)
        self.factor = i.float(3.0, "SuperTrend Factor", minval=0.1, step=0.1)
        self.initial_risk = i.float(2000, "Initial Stop Loss ($)", minval=1)
        self.use_profit_locks = i.bool(True, "Enable Profit Locks")
        self.lock1_trigger = i.float(1500, "Lock 1 Trigger ($)", minval=1)
        self.lock1_amount = i.float(500, "Lock 1 Locked Profit ($)", minval=0)
        self.lock2_trigger = i.float(2500, "Lock 2 Trigger ($)", minval=1)
        self.lock2_amount = i.float(1500, "Lock 2 Locked Profit ($)", minval=0)
        self.lock3_trigger = i.float(4000, "Lock 3 Trigger ($)", minval=1)
        self.lock3_amount = i.float(3000, "Lock 3 Locked Profit ($)", minval=0)
        self.use_take_profit = i.bool(True, "Enable Hard Take Profit")
        self.take_profit_dollars = i.float(3000, "Take Profit ($)", minval=1)
        self.active_stop = NA
        self.prev_dir = NA

    def dollars_to_points(self, dollars):
        return div(dollars, self.syminfo.pointvalue)

    def on_bar(self):
        st = self.strategy
        close = self.close
        st_value, st_dir = ta.supertrend(self.factor, self.atr_period)
        dir_1 = self.prev_dir
        self.prev_dir = st_dir
        bull_flip = st_dir < 0 and dir_1 > 0
        bear_flip = st_dir > 0 and dir_1 < 0
        point_value = self.syminfo.pointvalue
        avg_entry = st.position_avg_price
        if st.position_size > 0:
            open_profit = (close - avg_entry) * point_value
        elif st.position_size < 0:
            open_profit = (avg_entry - close) * point_value
        else:
            open_profit = 0.0
        if bull_flip:
            st.close("Short", comment="Opposite Flip")
            st.entry("Long", st.long, qty=1, comment="Long Flip")
        if bear_flip:
            st.close("Long", comment="Opposite Flip")
            st.entry("Short", st.short, qty=1, comment="Short Flip")
        if st.position_size != 0:
            initial_stop_points = self.dollars_to_points(self.initial_risk)
            long_initial_stop = avg_entry - initial_stop_points
            short_initial_stop = avg_entry + initial_stop_points
            locked_profit = 0.0
            if self.use_profit_locks:
                if open_profit >= self.lock3_trigger:
                    locked_profit = self.lock3_amount
                elif open_profit >= self.lock2_trigger:
                    locked_profit = self.lock2_amount
                elif open_profit >= self.lock1_trigger:
                    locked_profit = self.lock1_amount
                else:
                    locked_profit = 0.0
            locked_points = self.dollars_to_points(locked_profit)
            long_lock_stop = NA
            short_lock_stop = NA
            if locked_profit > 0:
                long_lock_stop = avg_entry + locked_points
                short_lock_stop = avg_entry - locked_points
            long_take_profit = NA
            short_take_profit = NA
            if self.use_take_profit:
                tp_points = self.dollars_to_points(self.take_profit_dollars)
                long_take_profit = avg_entry + tp_points
                short_take_profit = avg_entry - tp_points
            if st.position_size > 0:
                candidate = long_initial_stop
                if not na(long_lock_stop):
                    candidate = pmath.max(candidate, long_lock_stop)
                self.active_stop = candidate if na(self.active_stop) else pmath.max(self.active_stop, candidate)
                st.exit("Long Exit", from_entry="Long", stop=self.active_stop, limit=long_take_profit, comment="Long TP/SL")
            if st.position_size < 0:
                candidate = short_initial_stop
                if not na(short_lock_stop):
                    candidate = pmath.min(candidate, short_lock_stop)
                self.active_stop = candidate if na(self.active_stop) else pmath.min(self.active_stop, candidate)
                st.exit("Short Exit", from_entry="Short", stop=self.active_stop, limit=short_take_profit, comment="Short TP/SL")
        else:
            self.active_stop = NA
        if st.position_size > 0 and bear_flip:
            st.close("Long", comment="SuperTrend Flip Exit")
        if st.position_size < 0 and bull_flip:
            st.close("Short", comment="SuperTrend Flip Exit")
