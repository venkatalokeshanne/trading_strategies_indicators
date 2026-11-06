"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : WJ Strategy B
Author       : YUNUYUN
Source URL   : https://www.tradingview.com/script/aw6frVKI-WJ-Strategy-B
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. A score (BB lower break 1, MA120/240/400 0.5/1/1.5, RSI <=40/35/30/25 0.5/1/1.5/2) arms a
monitor when it reaches 3.0; once it falls back below, `confirm_days` non-rising days plus close >= SMA10 trigger a
100000-cash entry (pyramiding 20, filled at the bar close). Everything is closed on the last bar.

Deviations from the original: none.
Not carried over: alert(), unused label/price arrays.
────────────────────────────────────────────────────────────────────────
"""

from pinelib import S, Script, color, ta


class WjStrategyB(Script):
    TITLE = "WJ Strategy B"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(initial_capital=2000000, default_qty_type="cash", default_qty_value=100000, pyramiding=20,
                    process_orders_on_close=True)
    SOURCE = {"id": "aw6frVKI", "author": "YUNUYUN", "licence": "not stated",
              "url": "https://www.tradingview.com/script/aw6frVKI-WJ-Strategy-B"}

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
        self.start_year = self.input.int(2024, "시작 연도")
        self.start_month = self.input.int(1, "시작 월")
        self.start_day = self.input.int(1, "시작 일")
        self.monitoring = False
        self.days_maintained = 0

    def on_bar(self):
        start_time = self.timestamp(self.start_year, self.start_month, self.start_day, 0, 0)
        in_date_range = self.time >= start_time
        _, _, bb_lower = ta.bb(self.close, self.bb_len, self.bb_mult)
        ma1 = ta.sma(self.close, self.ma_len1)
        ma2 = ta.sma(self.close, self.ma_len2)
        ma3 = ta.sma(self.close, self.ma_len3)
        rsi_val = ta.rsi(self.close, self.rsi_len)
        score_bb = 1.0 if self.close < bb_lower else 0.0
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
        final_score = S(score_bb + score_ma + score_rsi)
        entry_ma = ta.sma(self.close, self.entry_ma_len)
        st = self.strategy
        if in_date_range:
            if final_score[0] >= 3.0:
                self.monitoring = True
                self.days_maintained = 0
            if self.monitoring and final_score[0] < 3.0:
                if final_score[0] > final_score[1]:
                    self.days_maintained = 0
                else:
                    self.days_maintained += 1
                    cond_days = self.days_maintained >= self.confirm_days
                    cond_ma = self.close >= entry_ma
                    if cond_days and cond_ma:
                        st.entry("WJ Buy", st.long)
                        self.monitoring = False
        if self.barstate.islast:
            st.close_all(comment=" ")
