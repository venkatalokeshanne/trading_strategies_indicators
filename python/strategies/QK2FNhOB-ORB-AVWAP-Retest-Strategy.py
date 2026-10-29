"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : ORB AVWAP Retest Strategy
Author       : LukeBorgerding
Source URL   : https://www.tradingview.com/script/QK2FNhOB-ORB-AVWAP-Retest-Strategy
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-29 by Claude (pine-to-python skill)

Line-for-line translation (process_orders_on_close). The 09:30-09:45 opening range of each trading day is stored; a later close beyond it marks a breakout, and the first bar after that which tests the volume-weighted average price anchored at the open and rejects it
(closes back on the breakout side, in the candle's direction, without losing the opposite range side) enters at the close with the stop at the other side of the range (or an ATR multiple) and the target at `Target R` times the risk, sized by dollar risk. One trade per trading day.
The trading day follows the pinelib convention (it starts at 09:30 New York for a stock chart), so the retest window also runs through the hours after midnight until 09:30, exactly as `rangeReady` persists in the original.

Deviations from the original: none.
Not carried over: the range, anchored VWAP and stop / target line drawings and the timeframe-mismatch label (display only).
────────────────────────────────────────────────────────────────────────
"""

import math

from pinelib import NA, Script, div, na, pmath, ta


class OrbAvwapRetest(Script):
    TITLE = "ORB AVWAP Retest Strategy"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(pyramiding=0, process_orders_on_close=True)
    SOURCE = {"id": "QK2FNhOB", "author": "LukeBorgerding", "licence": "not stated",
              "url": "https://www.tradingview.com/script/QK2FNhOB-ORB-AVWAP-Retest-Strategy"}

    def init(self):
        g = "1. Session"
        self.clock_timezone = self.input.string("America/New_York", "Clock Timezone", group=g)
        self.breakout_tf = self.input.timeframe("5", "Breakout Timeframe", group=g)
        self.or_start_hour = self.input.int(9, "Range Start Hour", minval=0, maxval=23, group=g)
        self.or_start_minute = self.input.int(30, "Range Start Minute", minval=0, maxval=59, group=g)
        self.or_end_hour = self.input.int(9, "Range End Hour", minval=0, maxval=23, group=g)
        self.or_end_minute = self.input.int(45, "Range End Minute", minval=0, maxval=59, group=g)
        self.trade_end_hour = self.input.int(16, "Last Entry Hour", minval=0, maxval=23, group=g)
        self.trade_end_minute = self.input.int(0, "Last Entry Minute", minval=0, maxval=59, group=g)
        self.one_trade_per_session = self.input.bool(True, "One Trade Per Session", group=g)
        g = "2. Direction"
        self.allow_longs = self.input.bool(True, "Allow Longs", group=g)
        self.allow_shorts = self.input.bool(True, "Allow Shorts", group=g)
        g = "3. Risk"
        self.stop_mode = self.input.string("Range Other Side", "Stop Mode", options=["Range Other Side", "ATR"], group=g)
        self.atr_len = self.input.int(14, "ATR Length", minval=1, group=g)
        self.atr_mult = self.input.float(1.0, "ATR Multiplier", minval=0.1, step=0.1, group=g)
        self.target_r = self.input.float(1.0, "Target R", minval=0.1, step=0.1, group=g)
        g = "4. Sizing"
        self.sizing_mode = self.input.string("Dollar Risk", "Sizing Mode", options=["Fixed Contracts", "Dollar Risk"], group=g)
        self.fixed_qty = self.input.float(1, "Fixed Contracts", minval=0.001, step=1, group=g)
        self.risk_dollars = self.input.float(800, "Dollar Risk", minval=1, step=50, group=g)
        self.max_contracts = self.input.float(50, "Max Contracts", minval=1, step=1, group=g)
        self.range_high = NA
        self.range_low = NA
        self.range_ready = False
        self.breakout_dir = 0
        self.breakout_bar = NA
        self.traded_this_session = False
        self.cum_pv = 0.0
        self.cum_vol = 0.0

    def calc_qty(self, entry_price, stop_price):
        risk_per_contract = abs(entry_price - stop_price) * self.syminfo.pointvalue
        if self.sizing_mode == "Fixed Contracts":
            raw_qty = self.fixed_qty
        else:
            raw_qty = math.floor(div(self.risk_dollars, risk_per_contract)) if risk_per_contract > 0 else 0
        return pmath.min(self.max_contracts, raw_qty)

    def on_bar(self):
        st = self.strategy
        close, open_, high, low = self.close, self.open, self.high, self.low
        tz = self.clock_timezone
        or_start = self.or_start_hour * 10000 + self.or_start_minute * 100
        or_end = self.or_end_hour * 10000 + self.or_end_minute * 100
        trade_end = self.trade_end_hour * 10000 + self.trade_end_minute * 100
        now_time = self.hour(self.time, tz) * 10000 + self.minute(self.time, tz) * 100 + self.second(self.time, tz)
        day_change = ta.change(self.time_fn("D", "0000-2359", tz))
        new_session = (not na(day_change)) and day_change != 0
        in_opening_range = now_time >= or_start and now_time < or_end
        after_opening_range = now_time >= or_end
        before_trade_end = now_time <= trade_end
        if new_session:
            self.range_high = NA
            self.range_low = NA
            self.range_ready = False
            self.breakout_dir = 0
            self.breakout_bar = NA
            self.traded_this_session = False
            self.cum_pv = 0.0
            self.cum_vol = 0.0
        if now_time >= or_start:
            self.cum_pv += self.hlc3 * self.volume
            self.cum_vol += self.volume
        avwap = div(self.cum_pv, self.cum_vol) if self.cum_vol > 0 else NA
        if in_opening_range:
            self.range_high = float(high) if na(self.range_high) else pmath.max(self.range_high, high)
            self.range_low = float(low) if na(self.range_low) else pmath.min(self.range_low, low)
        if after_opening_range and (not self.range_ready) and (not na(self.range_high)) and (not na(self.range_low)) and self.range_high > self.range_low:
            self.range_ready = True
        can_look_for_breakout = self.range_ready and before_trade_end and ((not self.one_trade_per_session) or (not self.traded_this_session)) and st.position_size == 0
        if can_look_for_breakout and self.breakout_dir == 0:
            if self.allow_longs and close > self.range_high:
                self.breakout_dir = 1
                self.breakout_bar = self.bar_index
            elif self.allow_shorts and close < self.range_low:
                self.breakout_dir = -1
                self.breakout_bar = self.bar_index
        long_retest_reject = (self.breakout_dir == 1 and self.bar_index > self.breakout_bar and low <= avwap and close > avwap and close > open_ and low > self.range_low)
        short_retest_reject = (self.breakout_dir == -1 and self.bar_index > self.breakout_bar and high >= avwap and close < avwap and close < open_ and high < self.range_high)
        atr = ta.atr(self.atr_len)
        if can_look_for_breakout and long_retest_reject:
            entry_price = float(close)
            stop_price = entry_price - atr * self.atr_mult if self.stop_mode == "ATR" else self.range_low
            risk_points = entry_price - stop_price
            qty = self.calc_qty(entry_price, stop_price)
            if risk_points > 0 and qty > 0:
                target_price = entry_price + risk_points * self.target_r
                st.entry("Long", st.long, qty=qty)
                st.exit("Long Exit", "Long", stop=stop_price, limit=target_price)
                self.traded_this_session = True
                self.breakout_dir = 0
        if can_look_for_breakout and short_retest_reject:
            entry_price = float(close)
            stop_price = entry_price + atr * self.atr_mult if self.stop_mode == "ATR" else self.range_high
            risk_points = stop_price - entry_price
            qty = self.calc_qty(entry_price, stop_price)
            if risk_points > 0 and qty > 0:
                target_price = entry_price - risk_points * self.target_r
                st.entry("Short", st.short, qty=qty)
                st.exit("Short Exit", "Short", stop=stop_price, limit=target_price)
                self.traded_this_session = True
                self.breakout_dir = 0
