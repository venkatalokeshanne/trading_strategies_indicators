"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : MNQ StochRSI Long & Short Strategy
Author       : kalagoralarka
Source URL   : https://www.tradingview.com/script/9u8pzF0I-2hr-MNQ-OPTIMIZED
Pine version : v5
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-29 by Claude (pine-to-python skill)

Line-for-line translation (market orders at the next open). K = SMA(stochastic of the RSI). A short is armed when K reaches the arm level while flat (disarmed at the short-exit level), becomes ready once the high has touched the 20 EMA after arming, and enters when K falls to the entry level; the long side mirrors it
(armed at the low level, ready on a low touching the EMA, entry when K rises to its entry level). No entries between 16:58 and 18:00 New York time. At the 16:58 bar an open position is saved (direction) and closed; the bar at 18:00 re-opens the saved direction.
Every bar both sides re-issue an exit order with a hard stop (dollar stop / dollars per point, from the position's average price) and a trailing stop whose activation and offset are the trail inputs (in TICKS, as strategy.exit defines them); K reaching the exit level closes the position at the next open.
Deviations from the original: none.
Not carried over: the entry / exit markers and the hard-stop plot lines (display only).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import Script, div, ta


class MnqStochRsi(Script):
    TITLE = "MNQ StochRSI Long & Short Strategy"
    PINE_VERSION = 5
    OVERLAY = True
    STRATEGY = dict(default_qty_type="fixed", default_qty_value=8, initial_capital=4500, commission_type="cash_per_contract", commission_value=0.62)
    SOURCE = {"id": "9u8pzF0I", "author": "kalagoralarka", "licence": "not stated", "url": "https://www.tradingview.com/script/9u8pzF0I-2hr-MNQ-OPTIMIZED"}

    def init(self):
        i = self.input
        self.rsi_len = i.int(14, "RSI Length", minval=1)
        self.stoch_len = i.int(14, "Stoch Length", minval=1)
        self.smooth_k = i.int(3, "K Smoothing", minval=1)
        self.ema_len = i.int(20, "EMA Length", minval=1)
        self.short_arm = i.float(95.0, "Short Trigger 1 (Arm)", minval=50, maxval=100)
        self.short_entry = i.float(75.0, "Short Trigger 2 (Entry)", minval=50, maxval=100)
        self.short_exit = i.float(5.0, "Short Exit (StochRSI)", minval=0, maxval=50)
        self.short_trail = i.float(30.0, "Short Trailing Stop (points)")
        self.long_arm = i.float(5.0, "Long Trigger 1 (Arm)", minval=0, maxval=50)
        self.long_entry = i.float(20.0, "Long Trigger 2 (Entry)", minval=0, maxval=50)
        self.long_exit = i.float(95.0, "Long Exit (StochRSI)", minval=50, maxval=100)
        self.long_trail = i.float(35.0, "Long Trailing Stop (points)")
        self.dollar_stop = i.float(3000.0, "Hard Stop Loss ($)", minval=1)
        self.point_value = i.float(16.0, "$ Per Point (contracts × $2)", minval=1)
        self.short_ema_hit = False
        self.long_ema_hit = False
        self.saved_direction = 0
        self.short_armed = False
        self.long_armed = False

    def on_bar(self):
        st = self.strategy
        close = self.close
        hard_stop_pts = div(self.dollar_stop, self.point_value)
        close_hour, close_minute, open_hour, open_minute = 16, 58, 18, 0
        bar_hour = self.hour(self.time, "America/New_York")
        bar_minute = self.minute(self.time, "America/New_York")
        bar_time_min = bar_hour * 60 + bar_minute
        close_time_min = close_hour * 60 + close_minute
        open_time_min = open_hour * 60 + open_minute
        in_dead_zone = bar_time_min >= close_time_min and bar_time_min < open_time_min
        is_close_bar = bar_hour == close_hour and bar_minute == close_minute
        rsi_val = ta.rsi(close, self.rsi_len)
        k_raw = ta.stoch(rsi_val, rsi_val, rsi_val, self.stoch_len)
        k = ta.sma(k_raw, self.smooth_k)
        ema20 = ta.ema(close, self.ema_len)
        if is_close_bar and st.position_size != 0:
            self.saved_direction = 1 if st.position_size > 0 else -1
            st.close_all(comment="Market Close 4:58 PM")
        if bar_hour == open_hour and bar_minute == open_minute:
            if self.saved_direction == 1:
                st.entry("Long", st.long, qty=8, comment="Reopen Long 6 PM")
            elif self.saved_direction == -1:
                st.entry("Short", st.short, qty=8, comment="Reopen Short 6 PM")
            self.saved_direction = 0
        if st.position_size == 0 and not in_dead_zone:
            if k >= self.short_arm:
                self.short_armed = True
                self.short_ema_hit = False
            if k <= self.short_exit:
                self.short_armed = False
                self.short_ema_hit = False
        if self.short_armed and st.position_size == 0 and not in_dead_zone:
            if self.high >= ema20:
                self.short_ema_hit = True
        short_condition = self.short_armed and self.short_ema_hit and st.position_size == 0 and k <= self.short_entry and not in_dead_zone
        if short_condition:
            st.entry("Short", st.short, qty=8)
            self.short_armed = False
            self.short_ema_hit = False
        if st.position_size == 0 and not in_dead_zone:
            if k <= self.long_arm:
                self.long_armed = True
                self.long_ema_hit = False
            if k >= self.long_exit:
                self.long_armed = False
                self.long_ema_hit = False
        if self.long_armed and st.position_size == 0 and not in_dead_zone:
            if self.low <= ema20:
                self.long_ema_hit = True
        long_condition = self.long_armed and self.long_ema_hit and st.position_size == 0 and k >= self.long_entry and not in_dead_zone
        if long_condition:
            st.entry("Long", st.long, qty=8)
            self.long_armed = False
            self.long_ema_hit = False
        avg = st.position_avg_price
        st.exit("Short Trail Stop", from_entry="Short", stop=avg + hard_stop_pts, trail_points=self.short_trail, trail_offset=self.short_trail)
        st.exit("Long Trail Stop", from_entry="Long", stop=avg - hard_stop_pts, trail_points=self.long_trail, trail_offset=self.long_trail)
        if st.position_size < 0 and k <= self.short_exit:
            st.close("Short", comment="StochRSI Exit")
        if st.position_size > 0 and k >= self.long_exit:
            st.close("Long", comment="StochRSI Exit")
