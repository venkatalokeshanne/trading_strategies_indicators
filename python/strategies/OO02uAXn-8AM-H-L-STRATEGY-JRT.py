"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : Custom Hour High & Low + Sweep Strategy (8AM H/L STRATEGY JRT)
Author       : rukabjustin
Source URL   : https://www.tradingview.com/script/OO02uAXn-8AM-H-L-STRATEGY-JRT
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-29 by Claude (pine-to-python skill)

Line-for-line translation (process_orders_on_close). The high and low of a configurable New York time window (08:00-09:00) become the day's range. Inside the signal window (09:30-11:00) a sweep (wick beyond the level closing back inside) or a tap (within a tick tolerance) of the range low (high) arms a bullish (bearish) setup; after the confirmation bars a bullish (bearish) displacement candle — close beyond the previous bar's high (low) — produces the signal, subject to a maximum count per day and an optional range-percentage filter. The trade is entered at the close with the opposite range extreme as the target and a stop at target distance / R:R, and after the price covers a trigger percentage of the way to the target the stop is cut to a remaining percentage of its original distance.
Deviations from the original: none.
Not carried over: the range lines, signal labels, trade boxes and alerts (display only).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, div, na, pmath

TZ = "America/New_York"


class HourHighLowSweep(Script):
    TITLE = "Custom Hour High & Low + Sweep Strategy"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(pyramiding=0, process_orders_on_close=True)
    SOURCE = {"id": "OO02uAXn", "author": "rukabjustin", "licence": "not stated",
              "url": "https://www.tradingview.com/script/OO02uAXn-8AM-H-L-STRATEGY-JRT"}

    def init(self):
        i = self.input
        g = "Range Settings"
        self.start_h = i.int(8, "Start Hour", minval=0, maxval=23, group=g)
        self.start_m = i.int(0, "Start Minute", minval=0, maxval=59, group=g)
        self.end_h = i.int(9, "End Hour", minval=0, maxval=23, group=g)
        self.end_m = i.int(0, "End Minute", minval=0, maxval=59, group=g)
        g = "Line Extension"
        i.int(12, "Extend Until Hour", minval=0, maxval=23, group=g)
        i.int(0, "Extend Until Minute", minval=0, maxval=59, group=g)
        g = "Line Settings"
        i.int(1, "Line Thickness", minval=1, maxval=5, group=g)
        i.string("Solid", "Line Style", options=["Solid", "Dashed", "Dotted"], group=g)
        g = "Signal Settings"
        self.show_signals = i.bool(True, "Show Buy/Sell Signals", group=g)
        self.sig_start_h = i.int(9, "Signal Start Hour", minval=0, maxval=23, group=g)
        self.sig_start_m = i.int(30, "Signal Start Minute", minval=0, maxval=59, group=g)
        self.sig_end_h = i.int(11, "Signal End Hour", minval=0, maxval=23, group=g)
        self.sig_end_m = i.int(0, "Signal End Minute", minval=0, maxval=59, group=g)
        self.confirm_bars = i.int(1, "Bar Confirmation", minval=1, maxval=20, group=g)
        self.tol_ticks = i.int(0, "Tap Tolerance (Ticks)", minval=0, maxval=100, group=g)
        self.max_buys = i.int(2, "Max Buy Signals", minval=0, maxval=20, group=g)
        self.max_sells = i.int(2, "Max Sell Signals", minval=0, maxval=20, group=g)
        g = "Signal Filters"
        self.use_range_filter = i.bool(False, "Use Range Percentage Filter", group=g)
        self.range_filter_pct = i.float(50.0, "Range Filter %", minval=0.0, maxval=100.0, step=1.0, group=g)
        g = "Signal Appearance"
        i.string("Small", "Signal Size", options=["Tiny", "Small", "Normal", "Large", "Huge"], group=g)
        g = "Trade Management"
        self.risk_reward = i.float(0.75, "Risk : Reward", minval=0.1, step=0.05, group=g)
        self.adjust_sl = i.bool(True, "Adjust SL After TP Progress", group=g)
        self.sl_trigger_pct = i.float(80.0, "SL Adjustment Trigger %", minval=1.0, maxval=100.0, step=1.0, group=g)
        self.sl_remaining_pct = i.float(25.0, "SL Remaining %", minval=0.0, maxval=100.0, step=1.0, group=g)
        g = "TP / SL Boxes"
        i.bool(True, "Show TP / SL Boxes", group=g)
        self.range_high = NA
        self.range_low = NA
        self.buy_count = 0
        self.sell_count = 0
        self.bull_setup = False
        self.bear_setup = False
        self.bull_setup_bar = NA
        self.bear_setup_bar = NA
        self.last_day = NA
        self.in_range_prev = False
        self.active_entry = NA
        self.active_tp = NA
        self.active_sl = NA
        self.orig_sl_dist = NA
        self.trade_dir = 0
        self.sl_adjusted = False

    def on_bar(self):
        st = self.strategy
        close, open_, high, low = self.close, self.open, self.high, self.low
        mintick = self.syminfo.mintick
        cur_min = self.hour(self.time, TZ) * 60 + self.minute(self.time, TZ)
        start_min = self.start_h * 60 + self.start_m
        end_min = self.end_h * 60 + self.end_m
        sig_start = self.sig_start_h * 60 + self.sig_start_m
        sig_end = self.sig_end_h * 60 + self.sig_end_m
        cur_day = self.year(self.time, TZ) * 10000 + self.month(self.time, TZ) * 100 + self.dayofmonth(self.time, TZ)
        new_day = (not na(self.last_day)) and cur_day != self.last_day
        self.last_day = cur_day
        h_h, l_h = self.H("high"), self.H("low")
        high_1 = h_h[1]
        low_1 = l_h[1]
        h_h.set(high)
        l_h.set(low)
        if new_day:
            self.range_high = NA
            self.range_low = NA
            self.buy_count = 0
            self.sell_count = 0
            self.bull_setup = False
            self.bear_setup = False
            self.bull_setup_bar = NA
            self.bear_setup_bar = NA
        in_range = (cur_min >= start_min and cur_min < end_min) if start_min < end_min else (cur_min >= start_min or cur_min < end_min)
        if in_range:
            if na(self.range_high):
                self.range_high = float(high)
                self.range_low = float(low)
            else:
                self.range_high = float(pmath.max(self.range_high, high))
                self.range_low = float(pmath.min(self.range_low, low))
        signal_window = cur_min >= sig_start and cur_min < sig_end
        levels_ready = (not na(self.range_high)) and (not na(self.range_low))
        range_size = self.range_high - self.range_low if levels_ready else NA
        buy_filter = self.range_low + range_size * (self.range_filter_pct / 100.0) if levels_ready else NA
        sell_filter = self.range_high - range_size * (self.range_filter_pct / 100.0) if levels_ready else NA
        buy_range_ok = (not self.use_range_filter) or (levels_ready and close <= buy_filter)
        sell_range_ok = (not self.use_range_filter) or (levels_ready and close >= sell_filter)
        tol = self.tol_ticks * mintick
        rl, rh = self.range_low, self.range_high
        low_sweep = levels_ready and signal_window and low < rl and close > rl
        low_tap = levels_ready and signal_window and low <= rl + tol and low >= rl - tol
        high_sweep = levels_ready and signal_window and high > rh and close < rh
        high_tap = levels_ready and signal_window and high >= rh - tol and high <= rh + tol
        bar = self.bar_index
        if self.buy_count < self.max_buys and (low_sweep or low_tap):
            self.bull_setup = True
            self.bull_setup_bar = bar
        if self.sell_count < self.max_sells and (high_sweep or high_tap):
            self.bear_setup = True
            self.bear_setup_bar = bar
        if self.bull_setup and not na(self.bull_setup_bar):
            if bar - self.bull_setup_bar > self.confirm_bars:
                self.bull_setup = False
                self.bull_setup_bar = NA
        if self.bear_setup and not na(self.bear_setup_bar):
            if bar - self.bear_setup_bar > self.confirm_bars:
                self.bear_setup = False
                self.bear_setup_bar = NA
        bull_disp = close > open_ and close > high_1
        bear_disp = close < open_ and close < low_1
        bull_conf = self.bull_setup and not na(self.bull_setup_bar) and bar - self.bull_setup_bar >= self.confirm_bars
        bear_conf = self.bear_setup and not na(self.bear_setup_bar) and bar - self.bear_setup_bar >= self.confirm_bars
        final_buy = bool(self.show_signals and signal_window and bull_conf and bull_disp and buy_range_ok and self.buy_count < self.max_buys)
        final_sell = bool(self.show_signals and signal_window and bear_conf and bear_disp and sell_range_ok and self.sell_count < self.max_sells)
        if final_buy:
            self.buy_count += 1
            self.bull_setup = False
            self.bull_setup_bar = NA
        if final_sell:
            self.sell_count += 1
            self.bear_setup = False
            self.bear_setup_bar = NA
        if final_buy and st.position_size == 0 and not na(self.range_high):
            self.active_entry = float(close)
            self.active_tp = float(self.range_high)
            tp_dist = self.active_tp - self.active_entry
            self.active_sl = float(self.active_entry - div(tp_dist, self.risk_reward))
            self.orig_sl_dist = abs(self.active_entry - self.active_sl)
            self.trade_dir = 1
            self.sl_adjusted = False
            if self.active_tp > self.active_entry and self.active_sl < self.active_entry:
                st.entry("BUY", st.long)
                st.exit("BUY EXIT", "BUY", limit=self.active_tp, stop=self.active_sl)
        if final_sell and st.position_size == 0 and not na(self.range_low):
            self.active_entry = float(close)
            self.active_tp = float(self.range_low)
            tp_dist = self.active_entry - self.active_tp
            self.active_sl = float(self.active_entry + div(tp_dist, self.risk_reward))
            self.orig_sl_dist = abs(self.active_entry - self.active_sl)
            self.trade_dir = -1
            self.sl_adjusted = False
            if self.active_tp < self.active_entry and self.active_sl > self.active_entry:
                st.entry("SELL", st.short)
                st.exit("SELL EXIT", "SELL", limit=self.active_tp, stop=self.active_sl)
        in_long = st.position_size > 0 and self.trade_dir == 1
        in_short = st.position_size < 0 and self.trade_dir == -1
        if self.adjust_sl and in_long and not self.sl_adjusted and not na(self.active_entry) and not na(self.active_tp) and not na(self.orig_sl_dist):
            trigger = self.active_entry + (self.active_tp - self.active_entry) * (self.sl_trigger_pct / 100.0)
            if high >= trigger:
                self.active_sl = float(self.active_entry - self.orig_sl_dist * (self.sl_remaining_pct / 100.0))
                self.sl_adjusted = True
        if self.adjust_sl and in_short and not self.sl_adjusted and not na(self.active_entry) and not na(self.active_tp) and not na(self.orig_sl_dist):
            trigger = self.active_entry - (self.active_entry - self.active_tp) * (self.sl_trigger_pct / 100.0)
            if low <= trigger:
                self.active_sl = float(self.active_entry + self.orig_sl_dist * (self.sl_remaining_pct / 100.0))
                self.sl_adjusted = True
        if in_long and not na(self.active_tp) and not na(self.active_sl):
            st.exit("BUY EXIT", "BUY", limit=self.active_tp, stop=self.active_sl)
        if in_short and not na(self.active_tp) and not na(self.active_sl):
            st.exit("SELL EXIT", "SELL", limit=self.active_tp, stop=self.active_sl)
        pos_h = self.H("pos")
        pos_1 = pos_h[1]
        pos_h.set(st.position_size)
        if st.position_size == 0 and (not na(pos_1)) and pos_1 != 0:
            self.active_entry = NA
            self.active_tp = NA
            self.active_sl = NA
            self.orig_sl_dist = NA
            self.trade_dir = 0
            self.sl_adjusted = False
