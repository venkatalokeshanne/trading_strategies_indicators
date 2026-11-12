"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : MNQ Midpoint Retest (7x2R + 3xRunner 4R/BE) FINAL
Author       : DDBrosio
Source URL   : https://www.tradingview.com/script/iZ9pJtfN-BROSIO-TRADES-8-00-15-Min-Break-and-Retest
Pine version : v5
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-29 by Claude (pine-to-python skill)

Line-for-line translation (market orders at the next open). The 08:00 - 08:15 (New York) range is built on each trading day and locked once it ends (midpoint = average of its high and low). A close beyond the range sets the breakout state (above = 1, below = -1, never cleared); in the 09:45 - 11:00 trade window, with the range locked, a bar that retests the midpoint
(low at or below it after an upside break; high at or above it after a downside break) while no trade is open enters 10 units. Every bar two exit orders per side are re-issued: 70 % with a 2R target and the range edge as stop, and the remaining 30 % with a 4R target and a stop that moves to the entry price once the bar's extreme reached 2R. A position is closed at the end of the trade window.
Quirk kept: the range, lock and trackers are cleared at the daily-period change; the daily period of this chart follows the symbol's session (futures: from 17:00 Chicago).
Deviations from the original: none.
Not carried over: the range plots (display only).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, na, pmath, ta


class BrosioMidpointRetest(Script):
    TITLE = "MNQ Midpoint Retest (7x2R + 3xRunner 4R/BE) FINAL"
    PINE_VERSION = 5
    OVERLAY = True
    STRATEGY = dict(default_qty_type="fixed", default_qty_value=10, pyramiding=10)
    SOURCE = {"id": "iZ9pJtfN", "author": "DDBrosio", "licence": "not stated",
              "url": "https://www.tradingview.com/script/iZ9pJtfN-BROSIO-TRADES-8-00-15-Min-Break-and-Retest"}

    def init(self):
        self.r_high = NA
        self.r_low = NA
        self.mid = NA
        self.range_locked = False
        self.entry = NA
        self.locked_for_day = False
        self.long_tp1_hit = False
        self.short_tp1_hit = False
        self.breakout_state = 0
        self.prev_trade_session = False
        self.prev_pos = 0.0

    def on_bar(self):
        st = self.strategy
        close, high, low = self.close, self.high, self.low
        tz = "America/New_York"
        range_session = self.time_in_session("0800-0815", tz)
        trade_session = self.time_in_session("0945-1100", tz)
        end_session = (not trade_session) and self.prev_trade_session
        self.prev_trade_session = bool(trade_session)
        day_change = ta.change(self.time_fn("D"))
        new_day = (not na(day_change)) and day_change != 0
        if new_day:
            self.r_high = NA
            self.r_low = NA
            self.mid = NA
            self.range_locked = False
            self.entry = NA
            self.locked_for_day = False
            self.long_tp1_hit = False
            self.short_tp1_hit = False
        if range_session and not self.range_locked:
            self.r_high = float(high) if na(self.r_high) else pmath.max(self.r_high, high)
            self.r_low = float(low) if na(self.r_low) else pmath.min(self.r_low, low)
        if (not range_session) and (not self.range_locked) and (not na(self.r_high)) and (not na(self.r_low)):
            self.mid = (self.r_high + self.r_low) / 2
            self.range_locked = True
        if end_session and st.position_size != 0:
            st.close_all(comment="Session End")
        above_range = self.range_locked and close > self.r_high
        below_range = self.range_locked and close < self.r_low
        if above_range:
            self.breakout_state = 1
        if below_range:
            self.breakout_state = -1
        one_trade_only = st.opentrades == 0
        can_trade = self.range_locked and (not self.locked_for_day) and trade_session
        touch_long = can_trade and self.breakout_state == 1 and low <= self.mid
        touch_short = can_trade and self.breakout_state == -1 and high >= self.mid
        if touch_long and one_trade_only:
            st.entry("LONG", st.long)
        if touch_short and one_trade_only:
            st.entry("SHORT", st.short)
        if st.position_size != 0 and self.prev_pos == 0:
            self.entry = st.position_avg_price
            self.long_tp1_hit = False
            self.short_tp1_hit = False
        long_stop = self.r_low
        short_stop = self.r_high
        long_risk = NA if na(self.entry) else self.entry - long_stop
        short_risk = NA if na(self.entry) else short_stop - self.entry
        long_tp1 = NA if na(self.entry) else self.entry + (2 * long_risk)
        long_tp2 = NA if na(self.entry) else self.entry + (4 * long_risk)
        short_tp1 = NA if na(self.entry) else self.entry - (2 * short_risk)
        short_tp2 = NA if na(self.entry) else self.entry - (4 * short_risk)
        if st.position_size > 0 and (not self.long_tp1_hit) and high >= long_tp1:
            self.long_tp1_hit = True
        if st.position_size < 0 and (not self.short_tp1_hit) and low <= short_tp1:
            self.short_tp1_hit = True
        be_stop_long = self.entry if self.long_tp1_hit else long_stop
        be_stop_short = self.entry if self.short_tp1_hit else short_stop
        st.exit("L_TP1", "LONG", qty_percent=70, limit=long_tp1, stop=long_stop)
        st.exit("S_TP1", "SHORT", qty_percent=70, limit=short_tp1, stop=short_stop)
        st.exit("L_RUN", "LONG", qty_percent=30, limit=long_tp2, stop=be_stop_long)
        st.exit("S_RUN", "SHORT", qty_percent=30, limit=short_tp2, stop=be_stop_short)
        self.prev_pos = st.position_size
