"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : Gecko ORB Small Range Breakout Strategy v1.4
Author       : danielbutcher72
Source URL   : https://www.tradingview.com/script/BPqrxgtc-Gecko-ORB-Small-Range-Breakout-Strategy-v1-4
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-29 by Claude (pine-to-python skill)

Line-for-line translation (market orders at the next open). The opening range (default 08:00 - 08:25 exchange time) is measured from its first bar; when it ends its size as a percentage of the first bar's open classifies it (a range at or above the large threshold is not tradeable). In the entry window (08:25 - 11:00), once per day,
a close above the range high (below the range low) enters long (short) with the stop at the opposite range edge and a take-profit at an R multiple or an ORB projection (or none). An open position is closed from the exit time on (once per day).
Deviations from the original: none.
Not carried over: the range box, lines and classification label (display only).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, div, na, pmath


class GeckoOrb(Script):
    TITLE = "ORB Small Range Breakout Strategy v1.4"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(pyramiding=0)
    SOURCE = {"id": "BPqrxgtc", "author": "danielbutcher72", "licence": "not stated",
              "url": "https://www.tradingview.com/script/BPqrxgtc-Gecko-ORB-Small-Range-Breakout-Strategy-v1-4"}

    def init(self):
        i = self.input
        self.small_threshold = i.float(0.50, "Small ORB threshold %")
        self.large_threshold = i.float(1.00, "Large ORB threshold %")
        g = "Opening Range"
        self.orb_start_hour = i.int(8, "Opening Range Start Hour", minval=0, maxval=23, group=g)
        self.orb_start_minute = i.int(0, "Opening Range Start Minute", minval=0, maxval=59, group=g)
        self.orb_end_hour = i.int(8, "Opening Range End Hour", minval=0, maxval=23, group=g)
        self.orb_end_minute = i.int(25, "Opening Range End Minute", minval=0, maxval=59, group=g)
        g = "Entry Window"
        self.cutoff_hour = i.int(11, "Entry Cutoff Hour", minval=0, maxval=23, group=g)
        self.cutoff_minute = i.int(0, "Entry Cutoff Minute", minval=0, maxval=59, group=g)
        self.tp_mode = i.string("R Multiple", "Take Profit Mode", options=["R Multiple", "ORB Projection", "No TP"])
        self.r_multiple = i.float(2.0, "R Multiple TP", step=0.25)
        self.orb_projection_mult = i.float(2.0, "ORB Projection Multiplier", step=0.25)
        self.use_session_exit = i.bool(True, "Close open trade at session time?")
        self.exit_hour = i.int(16, "Exit Hour (exchange local time)", minval=0, maxval=23)
        self.exit_minute = i.int(0, "Exit Minute", minval=0, maxval=59)
        self.orb_high = NA
        self.orb_low = NA
        self.opening_price = NA
        self.drawn = False
        self.breakout_done = False
        self.orb_is_small = False
        self.orb_is_tradeable = False
        self.orb_percent = NA
        self.exited_today = False
        self.prev_is_orb = False

    @staticmethod
    def pad2(n):
        return "0" + str(n) if n < 10 else str(n)

    def on_bar(self):
        st = self.strategy
        close, high, low = self.close, self.high, self.low
        tz = self.syminfo.timezone
        h = self.hour(self.time, tz)
        m = self.minute(self.time, tz)
        orb_session = self.pad2(self.orb_start_hour) + self.pad2(self.orb_start_minute) + "-" + self.pad2(self.orb_end_hour) + self.pad2(self.orb_end_minute)
        entry_session = self.pad2(self.orb_end_hour) + self.pad2(self.orb_end_minute) + "-" + self.pad2(self.cutoff_hour) + self.pad2(self.cutoff_minute)
        is_orb_bar = self.time_in_session(orb_session, tz)
        is_entry_bar = self.time_in_session(entry_session, tz)
        is_first_orb_bar = is_orb_bar and not self.prev_is_orb
        is_draw_bar = self.prev_is_orb and not is_orb_bar
        self.prev_is_orb = bool(is_orb_bar)
        if is_first_orb_bar:
            self.orb_high = float(high)
            self.orb_low = float(low)
            self.opening_price = float(self.open)
            self.drawn = False
            self.breakout_done = False
            self.orb_is_small = False
            self.orb_is_tradeable = False
            self.orb_percent = NA
            self.exited_today = False
        if is_orb_bar:
            self.orb_high = pmath.max(self.orb_high, high)
            self.orb_low = pmath.min(self.orb_low, low)
        if is_draw_bar and (not na(self.orb_high)) and (not na(self.orb_low)):
            range_size = self.orb_high - self.orb_low
            self.orb_percent = div(range_size, self.opening_price) * 100
            self.orb_is_small = self.orb_percent < self.small_threshold
            is_large = self.orb_percent >= self.large_threshold
            self.orb_is_tradeable = not is_large
            self.drawn = True
        long_breakout = self.drawn and self.orb_is_tradeable and (not self.breakout_done) and is_entry_bar and close > self.orb_high
        short_breakout = self.drawn and self.orb_is_tradeable and (not self.breakout_done) and is_entry_bar and close < self.orb_low
        orb_range = self.orb_high - self.orb_low
        if long_breakout:
            long_entry = close
            long_stop = self.orb_low
            long_risk = long_entry - long_stop
            if self.tp_mode == "R Multiple":
                long_tp = long_entry + long_risk * self.r_multiple
            elif self.tp_mode == "ORB Projection":
                long_tp = self.orb_high + orb_range * self.orb_projection_mult
            else:
                long_tp = NA
            st.entry("Long", st.long)
            if self.tp_mode == "No TP":
                st.exit("Long Exit", "Long", stop=long_stop)
            else:
                st.exit("Long Exit", "Long", stop=long_stop, limit=long_tp)
            self.breakout_done = True
        if short_breakout:
            short_entry = close
            short_stop = self.orb_high
            short_risk = short_stop - short_entry
            if self.tp_mode == "R Multiple":
                short_tp = short_entry - short_risk * self.r_multiple
            elif self.tp_mode == "ORB Projection":
                short_tp = self.orb_low - orb_range * self.orb_projection_mult
            else:
                short_tp = NA
            st.entry("Short", st.short)
            if self.tp_mode == "No TP":
                st.exit("Short Exit", "Short", stop=short_stop)
            else:
                st.exit("Short Exit", "Short", stop=short_stop, limit=short_tp)
            self.breakout_done = True
        session_exit = self.use_session_exit and (not self.exited_today) and (h > self.exit_hour or (h == self.exit_hour and m >= self.exit_minute))
        if session_exit:
            st.close_all(comment="Session Exit")
            self.exited_today = True
