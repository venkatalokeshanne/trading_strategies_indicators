"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : CNPS 01 MACD
Author       : Khanhtq26
Source URL   : https://www.tradingview.com/script/nk1xM7QA-CNPS01-MACD
Pine version : v5
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-29 by Claude (pine-to-python skill)

Line-for-line translation. MACD line crossing its signal opens a long (short on the cross down), optionally only when the SMA filter slopes the same way, inside the
time-of-day window (exchange time, bar start); leaving the window closes any position. Once a position exists, a stop / take-profit bracket around the average
price is (re-)issued at each bar close and works from the next bar.

Deviations from the original: none.
Not carried over: the SMA / stop / target line plots, signal shapes and the out-of-session background (cosmetic).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, color, na, ta


class Cnps01Macd(Script):
    TITLE = "CNPS 01 MACD"
    PINE_VERSION = 5
    OVERLAY = True
    STRATEGY = dict(initial_capital=100000000, default_qty_type="fixed", default_qty_value=1)
    SOURCE = {"id": "nk1xM7QA", "author": "Khanhtq26", "licence": "not stated",
              "url": "https://www.tradingview.com/script/nk1xM7QA-CNPS01-MACD"}

    def init(self):
        g = "Cài đặt MACD"
        self.macd_fast = self.input.int(12, "Chu kỳ nhanh", minval=1, group=g)
        self.macd_slow = self.input.int(26, "Chu kỳ chậm", minval=1, group=g)
        self.macd_signal = self.input.int(9, "Chu kỳ tín hiệu", minval=1, group=g)
        g = "Bộ lọc xu hướng"
        self.use_trend_filter = self.input.bool(True, "Dùng bộ lọc xu hướng SMA?", group=g)
        self.sma_len = self.input.int(200, "Chu kỳ SMA", minval=1, group=g)
        self.trade_dir = self.input.string("Cả hai", "Chiều giao dịch", options=["Mua", "Bán", "Cả hai"], group="Chiều giao dịch")
        g = "Cắt lỗ / Chốt lời"
        self.sl_points = self.input.float(10.0, "Cắt lỗ (điểm)", minval=0.1, step=0.5, group=g)
        self.use_tp = self.input.bool(True, "Dùng chốt lời?", group=g)
        self.tp_points = self.input.float(30.0, "Chốt lời (điểm)", minval=0.1, step=0.5, group=g)
        g = "Bộ lọc giờ"
        self.use_time_filter = self.input.bool(True, "Dùng bộ lọc giờ?", group=g)
        self.start_hour = self.input.int(9, "Giờ bắt đầu", minval=0, maxval=23, group=g)
        self.start_minute = self.input.int(0, "Phút bắt đầu", minval=0, maxval=59, group=g)
        self.end_hour = self.input.int(14, "Giờ kết thúc", minval=0, maxval=23, group=g)
        self.end_minute = self.input.int(30, "Phút kết thúc", minval=0, maxval=59, group=g)

    def on_bar(self):
        st = self.strategy
        sma_trend = ta.sma(self.close, self.sma_len)
        sma_prev = self.H("sma")
        prev = sma_prev[1]
        sma_prev.set(sma_trend)
        is_bull = sma_trend >= prev
        is_bear = sma_trend < prev
        macd_line, signal_line, _ = ta.macd(self.close, self.macd_fast, self.macd_slow, self.macd_signal)
        raw_long = ta.crossover(macd_line, signal_line)
        raw_short = ta.crossunder(macd_line, signal_line)
        long_signal = raw_long and (is_bull if self.use_trend_filter else True)
        short_signal = raw_short and (is_bear if self.use_trend_filter else True)
        can_long_dir = self.trade_dir == "Mua" or self.trade_dir == "Cả hai"
        can_short_dir = self.trade_dir == "Bán" or self.trade_dir == "Cả hai"
        session_start = self.start_hour * 60 + self.start_minute
        session_end = self.end_hour * 60 + self.end_minute
        current_minutes = self.hour() * 60 + self.minute()
        in_session = (current_minutes >= session_start and current_minutes < session_end) if self.use_time_filter else True
        ins = self.H("ins")
        was_in = ins[1]
        session_just_ended = self.use_time_filter and not in_session and not na(was_in) and bool(was_in)
        ins.set(in_session)
        if session_just_ended and st.position_size != 0:
            st.close_all(comment="Hết phiên")
        can_long = long_signal and in_session and can_long_dir
        can_short = short_signal and in_session and can_short_dir
        long_sl = st.position_avg_price - self.sl_points
        long_tp = st.position_avg_price + self.tp_points
        short_sl = st.position_avg_price + self.sl_points
        short_tp = st.position_avg_price - self.tp_points
        if can_long:
            st.entry("Mua", st.long)
        if can_short:
            st.entry("Bán", st.short)
        if st.position_size > 0:
            st.exit("Thoát Mua", "Mua", stop=long_sl, limit=long_tp if self.use_tp else NA)
        if st.position_size < 0:
            st.exit("Thoát Bán", "Bán", stop=short_sl, limit=short_tp if self.use_tp else NA)
        self.plot(sma_trend if self.use_trend_filter else NA, "Bộ lọc xu hướng SMA", color=color.green if is_bull else color.red, linewidth=1)
