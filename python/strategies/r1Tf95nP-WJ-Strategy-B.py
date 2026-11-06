"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : WJ BUY Strategy (WJ Strategy B)
Author       : YUNUYUN
Source URL   : https://www.tradingview.com/script/r1Tf95nP-WJ-Strategy-B
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation (process_orders_on_close, pyramiding 50). A score of three components (Bollinger lower-band break, close below the SMA120 / 240 / 400, RSI
levels) arms a monitor (mode 1 on crossing up through 2.0, mode 2 at 3.0 or more). When the score falls back below its level and has not risen for the confirm number
of days, with the close back above the short MA (two bars in a row when below the last buy), the "A" entry (once the last B buy is older than two weeks and the close is above
it) or the "B" entry is made at the close. Everything open is closed on the last bar of the data.

Deviations from the original: none.
Not carried over: alerts, labels and alert conditions (cosmetic).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, na, ta


class WJStrategyB(Script):
    TITLE = "WJ BUY Strategy"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(initial_capital=5000000, default_qty_type="cash", default_qty_value=100000, pyramiding=50, process_orders_on_close=True)
    SOURCE = {"id": "r1Tf95nP", "author": "YUNUYUN", "licence": "not stated",
              "url": "https://www.tradingview.com/script/r1Tf95nP-WJ-Strategy-B"}

    def init(self):
        self.entry_amount = self.input.float(100000, "entry_amount")
        self.bb_len = self.input.int(40, "BB 길이")
        self.bb_mult = self.input.float(2.0, "BB 표준편차")
        self.ma_len1 = self.input.int(120, "MA 1 (0.5점)")
        self.ma_len2 = self.input.int(240, "MA 2 (1.0점)")
        self.ma_len3 = self.input.int(400, "MA 3 (1.5점)")
        self.rsi_len = self.input.int(14, "RSI 길이")
        self.confirm_days = self.input.int(2, "점수 하강 유지 기간(일)", minval=1)
        self.entry_ma_len = self.input.int(10, "진입 기준 이평선(일)", minval=1)
        self.start_year = self.input.int(2021, "시작 연도")
        self.start_month = self.input.int(1, "시작 월")
        self.start_day = self.input.int(1, "시작 일")
        self.monitor_mode = 0
        self.days_maintained = 0
        self.last_buy_b_price = NA
        self.last_buy_b_time = NA
        self.last_buy_price = NA

    def on_bar(self):
        start_time = self.timestamp(self.syminfo.timezone, self.start_year, self.start_month, self.start_day, 0, 0)
        in_date_range = self.time >= start_time
        _, bb_upper, bb_lower = ta.bb(self.close, self.bb_len, self.bb_mult)
        ma1 = ta.sma(self.close, self.ma_len1)
        ma2 = ta.sma(self.close, self.ma_len2)
        ma3 = ta.sma(self.close, self.ma_len3)
        rsi_val = ta.rsi(self.close, self.rsi_len)
        score_bb = 0.0
        if self.close < bb_lower:
            score_bb = 1.0
        score_ma = 0.0
        if self.close < ma3:
            score_ma = 1.5
        elif self.close < ma2:
            score_ma = 1.0
        elif self.close < ma1:
            score_ma = 0.5
        score_rsi = 0.0
        if rsi_val <= 25:
            score_rsi = 2.0
        elif rsi_val <= 30:
            score_rsi = 1.5
        elif rsi_val <= 35:
            score_rsi = 1.0
        elif rsi_val <= 40:
            score_rsi = 0.5
        final_score = score_bb + score_ma + score_rsi
        fs_prev = self.H("fs")[1]
        self.H("fs").set(final_score)
        entry_ma = ta.sma(self.close, self.entry_ma_len)
        ema_prev = self.H("entry_ma")[1]
        self.H("entry_ma").set(entry_ma)
        st = self.strategy
        if st.position_size == 0:
            self.last_buy_b_price = NA
            self.last_buy_b_time = NA
            self.last_buy_price = NA
        if in_date_range:
            if final_score >= 3.0:
                self.monitor_mode = 2
                self.days_maintained = 0
            elif fs_prev < 2.0 and final_score >= 2.0 and self.monitor_mode != 2:
                self.monitor_mode = 1
                self.days_maintained = 0
            is_a_active = self.monitor_mode == 1 and final_score < 2.0
            is_b_active = self.monitor_mode == 2 and final_score < 3.0
            if is_a_active or is_b_active:
                if final_score > fs_prev:
                    self.days_maintained = 0
                else:
                    self.days_maintained += 1
                cond_days = self.days_maintained >= self.confirm_days
                is_lower_price = (not na(self.last_buy_price)) and self.close < self.last_buy_price
                if is_lower_price:
                    cond_ma = self.close >= entry_ma and self.close[1] >= ema_prev
                else:
                    cond_ma = self.close >= entry_ma
                if cond_days and cond_ma:
                    if self.monitor_mode == 1:
                        two_weeks = na(self.last_buy_b_time) or (self.time - self.last_buy_b_time >= 14 * 86400000)
                        if (na(self.last_buy_b_price) or self.close > self.last_buy_b_price) and two_weeks:
                            st.entry("A", st.long)
                            self.last_buy_price = float(self.close)
                            self.monitor_mode = 0
                        else:
                            self.monitor_mode = 0
                    elif self.monitor_mode == 2:
                        st.entry("B", st.long)
                        self.last_buy_b_price = float(self.close)
                        self.last_buy_b_time = float(self.time)
                        self.last_buy_price = float(self.close)
                        self.monitor_mode = 0
        if self.barstate.islast:
            st.close_all(comment=" ")
