"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : Wed to Thu 9:20 Nifty Strategy
Author       : mandeepdera42
Source URL   : https://www.tradingview.com/script/wCWq6dje-Wed-to-Thu-9-20-Nifty-Strategy
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation, all times in Asia/Kolkata. The close of the 09:15 bar is stored on each Tuesday and Wednesday
and carried to the next week (ta.change(time("W")) rolls current -> previous). On Wednesday 09:15 the reference is last
week's Wednesday price (or last Tuesday's if that is missing); a close above it buys, below it sells short (the order fills at
the next open), and the Wednesday price is stored. While a position is open at the close a 100-point stop around the average
price is issued (works from the next bar); on any non-Wednesday bar from 15:15 on, an open position is closed at the next
open.

Known caveat: the "week" of time("W") follows pinelib's session-aligned weekly key for the symbol's exchange zone, not
India's own trading week; on the synthetic 24/7 series used for checking the boundary falls between the stored Tuesday
and Wednesday prices of the same week, so the logic is unaffected.

Deviations from the original: none.
Not carried over: the reference-price and stop-level plots (cosmetic).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, color, na, ta

TZ = "Asia/Kolkata"
TUESDAY, WEDNESDAY = 3, 4          # Pine: Sunday = 1


class WedToThu(Script):
    TITLE = "Wed to Thu 9:20 Nifty Strategy"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(margin_long=100, margin_short=100)
    SOURCE = {"id": "wCWq6dje", "author": "mandeepdera42", "licence": "not stated",
              "url": "https://www.tradingview.com/script/wCWq6dje-Wed-to-Thu-9-20-Nifty-Strategy"}

    def init(self):
        self.prev_tue_price = NA
        self.prev_wed_price = NA
        self.curr_tue_price = NA
        self.curr_wed_price = NA
        self.active_ref_price = NA

    def on_bar(self):
        ist_hour = self.hour(self.time, TZ)
        ist_minute = self.minute(self.time, TZ)
        ist_day = self.dayofweek(self.time, TZ)
        chg = ta.change(self.time_fn("W"))
        is_new_week = (not na(chg)) and chg != 0
        if is_new_week:
            self.prev_tue_price = self.curr_tue_price
            self.prev_wed_price = self.curr_wed_price
            self.curr_tue_price = NA
            self.curr_wed_price = NA
            self.active_ref_price = NA
        is_920_time = ist_hour == 9 and ist_minute == 15
        st = self.strategy
        if ist_day == TUESDAY and is_920_time:
            self.curr_tue_price = float(self.close)
        if ist_day == WEDNESDAY and is_920_time:
            self.active_ref_price = self.prev_tue_price if na(self.prev_wed_price) else self.prev_wed_price
            if not na(self.active_ref_price):
                if self.close > self.active_ref_price:
                    st.entry("Long", st.long)
                if self.close < self.active_ref_price:
                    st.entry("Short", st.short)
            self.curr_wed_price = float(self.close)
        if st.position_size > 0:
            st.exit("SL Long", "Long", stop=st.position_avg_price - 100)
        if st.position_size < 0:
            st.exit("SL Short", "Short", stop=st.position_avg_price + 100)
        is_time_exit = st.position_size != 0 and ist_day != WEDNESDAY and ist_hour == 15 and ist_minute >= 15
        if is_time_exit:
            st.close("Long", comment="Next Day 3:20 Exit")
            st.close("Short", comment="Next Day 3:20 Exit")
        self.plot(self.active_ref_price, title="Reference Price (Wed/Tue)", color=color.blue, linewidth=2)
