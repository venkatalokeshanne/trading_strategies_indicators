"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : CNPS 09 EMA Cross (CNPS 9 - SMA7/50 Cross)
Author       : Khanhtq26
Source URL   : https://www.tradingview.com/script/fp0zbifH-CNPS-9-SMA7-50-Cross
Pine version : v5
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. The fast EMA crossing the slow EMA, with the SMA200 slope as the trend filter (up for longs, down for shorts) and inside the time window, enters; a stop and an optional
take-profit in points around the average price are issued while in a position; the position is closed on the first bar after the session window ends.

Deviations from the original: none.
Not carried over: indicator plots, stop / target plots, signal shapes and the out-of-session background (cosmetic).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, color, ta


class Cnps09(Script):
    TITLE = "CNPS 09 EMA Cross"
    PINE_VERSION = 5
    OVERLAY = True
    STRATEGY = dict(initial_capital=100000000, default_qty_type="fixed", default_qty_value=1)
    SOURCE = {"id": "fp0zbifH", "author": "Khanhtq26", "licence": "not stated",
              "url": "https://www.tradingview.com/script/fp0zbifH-CNPS-9-SMA7-50-Cross"}

    def init(self):
        g = "Cài đặt chỉ báo"
        self.fast_len = self.input.int(7, "Chu kỳ EMA nhanh", minval=1, group=g)
        self.slow_len = self.input.int(50, "Chu kỳ EMA chậm", minval=1, group=g)
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
        sma_trend = ta.sma(self.close, self.sma_len)
        sma_prev = self.H("sma")[1]
        self.H("sma").set(sma_trend)
        is_bull = sma_trend >= sma_prev
        is_bear = sma_trend < sma_prev
        ema_fast = ta.ema(self.close, self.fast_len)
        ema_slow = ta.ema(self.close, self.slow_len)
        raw_long = ta.crossover(ema_fast, ema_slow)
        raw_short = ta.crossunder(ema_fast, ema_slow)
        long_signal = raw_long and (is_bull if self.use_trend_filter else True)
        short_signal = raw_short and (is_bear if self.use_trend_filter else True)
        can_long_dir = self.trade_dir == "Mua" or self.trade_dir == "Cả hai"
        can_short_dir = self.trade_dir == "Bán" or self.trade_dir == "Cả hai"
        session_start = self.start_hour * 60 + self.start_minute
        session_end = self.end_hour * 60 + self.end_minute
        current_minutes = self.hour() * 60 + self.minute()
        in_session = (current_minutes >= session_start and current_minutes < session_end) if self.use_time_filter else True
        in_prev = self.H("in_session")[1]
        self.H("in_session").set(in_session)
        session_just_ended = self.use_time_filter and (not in_session) and in_prev
        st = self.strategy
        if session_just_ended and st.position_size != 0:
            st.close_all(comment="Hết phiên")
        can_long = long_signal and in_session and can_long_dir
        can_short = short_signal and in_session and can_short_dir
        avg = st.position_avg_price
        long_sl, long_tp = avg - self.sl_points, avg + self.tp_points
        short_sl, short_tp = avg + self.sl_points, avg - self.tp_points
        if can_long:
            st.entry("Mua", st.long)
        if can_short:
            st.entry("Bán", st.short)
        if st.position_size > 0:
            st.exit("Thoát Mua", "Mua", stop=long_sl, limit=long_tp if self.use_tp else NA)
        if st.position_size < 0:
            st.exit("Thoát Bán", "Bán", stop=short_sl, limit=short_tp if self.use_tp else NA)
        self.plot(ema_fast, "EMA nhanh", color=color.blue, linewidth=2)
        self.plot(ema_slow, "EMA chậm", color=color.orange, linewidth=2)
