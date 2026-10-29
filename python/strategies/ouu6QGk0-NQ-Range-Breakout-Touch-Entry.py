"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : NQ 區間突破 (觸價即進場版)
Author       : baddasss
Source URL   : https://www.tradingview.com/script/ouu6QGk0
Pine version : v5
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-29 by Claude (pine-to-python skill)

Line-for-line translation. The high / low of a morning time window becomes the day's range; once the window has ended and the range is neither too small nor too large, a buy-stop above and a sell-stop below the range (a fraction of its size away) are placed together with their stop-loss / take-profit exits. The first fill ends the day's trading: the other side is cancelled.

Deviations from the original: none.
Not carried over: the webhook alert messages (text only).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, div, na, pmath


class NqRangeBreakout(Script):
    TITLE = "NQ 區間突破 (觸價即進場版)"
    PINE_VERSION = 5
    OVERLAY = True
    STRATEGY = dict(initial_capital=10000, pyramiding=1)
    SOURCE = {"id": "ouu6QGk0", "author": "baddasss", "licence": "not stated",
              "url": "https://www.tradingview.com/script/ouu6QGk0"}

    def init(self):
        i = self.input
        self.user_timezone = i.string("Asia/Taipei", "圖表顯示時區", options=["Asia/Taipei", "America/New_York", "UTC"])
        self.start_h = i.int(11, "區間開始 (小時)", minval=0, maxval=23)
        self.start_m = i.int(43, "區間開始 (分鐘)", minval=0, maxval=59)
        self.end_h = i.int(13, "區進結束 (小時)", minval=0, maxval=23)
        self.end_m = i.int(33, "區間結束 (分鐘)", minval=0, maxval=59)
        self.buffer_input = i.float(38.2, "進場緩衝比例 (%)", minval=0.0, step=0.5)
        self.tp_ratio = i.float(0.618, "止盈倍數", step=0.01)
        self.sl_at_level = i.float(0.1, "止損位於區間水平", step=0.01)
        self.max_range_pct = i.float(1.0, "最大區間比例 (%)", minval=0.1, step=0.1) / 100
        self.min_range_pct = i.float(0.1, "最小區間比例 (%)", minval=0.0, step=0.05) / 100
        self.r_h = NA
        self.r_l = NA
        self.already_traded_today = False
        self.prev_day = NA

    def on_bar(self):
        st = self.strategy
        tz = self.user_timezone
        curr_time_total = self.hour(self.time, tz) * 60 + self.minute(self.time, tz)
        start_time_total = self.start_h * 60 + self.start_m
        end_time_total = self.end_h * 60 + self.end_m
        day = self.dayofmonth(self.time, tz)
        day_change = day - self.prev_day if not na(self.prev_day) else NA
        self.prev_day = day
        closed_h = self.H("closedtrades")
        closed_prev = closed_h[1]
        closed_h.set(st.closedtrades)
        if (not na(day_change)) and day_change != 0:
            self.r_h = NA
            self.r_l = NA
            self.already_traded_today = False
        in_range = curr_time_total >= start_time_total and curr_time_total < end_time_total
        in_trade_window = curr_time_total >= end_time_total
        if in_range:
            self.r_h = float(self.high) if na(self.r_h) else pmath.max(self.r_h, self.high)
            self.r_l = float(self.low) if na(self.r_l) else pmath.min(self.r_l, self.low)
        range_percent = div(self.r_h - self.r_l, self.r_h)
        is_oversize = range_percent > self.max_range_pct
        is_undersize = range_percent < self.min_range_pct
        if st.position_size != 0 or st.closedtrades > closed_prev:
            self.already_traded_today = True
        can_trade = in_trade_window and (not na(self.r_h)) and (not self.already_traded_today) and (not is_oversize) and not is_undersize
        if can_trade:
            range_sz = self.r_h - self.r_l
            long_trg = self.r_h + (range_sz * (self.buffer_input / 100))
            short_trg = self.r_l - (range_sz * (self.buffer_input / 100))
            long_sl = self.r_l + (range_sz * self.sl_at_level)
            short_sl = self.r_h - (range_sz * self.sl_at_level)
            long_tp = self.r_h + (range_sz * self.tp_ratio)
            short_tp = self.r_l - (range_sz * self.tp_ratio)
            st.entry("Long", st.long, stop=long_trg, comment="觸價多")
            st.entry("Short", st.short, stop=short_trg, comment="觸價空")
            st.exit("ExL", "Long", limit=long_tp, stop=long_sl, comment_loss="多損", comment_profit="多利")
            st.exit("ExS", "Short", limit=short_tp, stop=short_sl, comment_loss="空損", comment_profit="空利")
        if self.already_traded_today:
            st.cancel("Long")
            st.cancel("Short")
