"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : 09:29 NY Limit Reversal
Author       : t0907weiiii
Source URL   : https://www.tradingview.com/script/VAmqWscY
Pine version : v5
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-29 by Claude (pine-to-python skill)

Line-for-line translation (market orders at the next open; the entries are pending LIMIT orders). On each new New York day the state is reset and every pending order cancelled. The 09:29 New York bar's close becomes the reference: a buy limit below it and a sell limit above it (offset points) are placed together with their
exit orders (stop and limit in points from the limit price); the pair stays until a fill, until the position is non-zero (the script then cancels the other entry) or from 09:35 on, when everything pending is cancelled while flat.
Deviations from the original: none.
Not carried over: the reference-line drawing (display only).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, na, ta


class NyLimitReversal(Script):
    TITLE = "09:29 NY Limit Reversal"
    PINE_VERSION = 5
    OVERLAY = True
    STRATEGY = dict(initial_capital=10000)
    SOURCE = {"id": "VAmqWscY", "author": "t0907weiiii", "licence": "not stated", "url": "https://www.tradingview.com/script/VAmqWscY"}

    def init(self):
        i = self.input
        self.offset = i.float(20.0, "掛單距離 (Offset)", step=1.0)
        self.sl_points = i.float(10.0, "止損點數 (SL)", step=1.0)
        self.rr_ratio = i.float(2.0, "盈虧比 (RR)", step=0.1)
        self.ref_close = NA
        self.buy_limit = NA
        self.sell_limit = NA
        self.has_ordered_today = False

    def on_bar(self):
        st = self.strategy
        close = self.close
        day_change = ta.change(self.time_fn("D", None, "America/New_York"))
        if (not na(day_change)) and day_change != 0:
            self.ref_close = NA
            self.buy_limit = NA
            self.sell_limit = NA
            self.has_ordered_today = False
            st.cancel_all()
        ny_time = self.hour(self.time, "America/New_York") * 100 + self.minute(self.time, "America/New_York")
        is_0929 = ny_time == 929
        is_0935_up = ny_time >= 935
        if is_0929:
            self.ref_close = float(close)
            self.buy_limit = self.ref_close - self.offset
            self.sell_limit = self.ref_close + self.offset
        if is_0935_up and st.position_size == 0 and self.has_ordered_today:
            st.cancel_all()
            self.has_ordered_today = True
        can_execute = (not na(self.ref_close)) and (not self.has_ordered_today) and ny_time < 935 and st.position_size == 0
        if can_execute:
            self.has_ordered_today = True
            buy_tp = self.buy_limit + (self.sl_points * self.rr_ratio)
            buy_sl = self.buy_limit - self.sl_points
            sell_tp = self.sell_limit - (self.sl_points * self.rr_ratio)
            sell_sl = self.sell_limit + self.sl_points
            st.entry("Long", st.long, limit=self.buy_limit, comment="L-Limit")
            st.exit("ExL", from_entry="Long", stop=buy_sl, limit=buy_tp, comment="L-Out")
            st.entry("Short", st.short, limit=self.sell_limit, comment="S-Limit")
            st.exit("ExS", from_entry="Short", stop=sell_sl, limit=sell_tp, comment="S-Out")
        if st.position_size != 0:
            st.cancel("Long")
            st.cancel("Short")
