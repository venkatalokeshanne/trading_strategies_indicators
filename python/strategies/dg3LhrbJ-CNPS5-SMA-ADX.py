"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : CNPS5 - SMA / ADX
Author       : Khanhtq26
Source URL   : https://www.tradingview.com/script/dg3LhrbJ-CNPS5-SMA-ADX
Pine version : v5
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-29 by Claude (pine-to-python skill)

Line-for-line translation. A rising (falling) SMA20 while the ADX is above its threshold opens a long (short), optionally only when the SMA200 slope agrees; a flip of the SMA20 slope closes a position against it. Entries are market orders (reversing), inside the time-of-day window (exchange time, bar start);
leaving the window closes any position. Once a position exists, a stop / take-profit bracket around the average price is (re-)issued at each bar close and works from the next bar.

Deviations from the original: none.
Not carried over: the line plots, signal shapes and the out-of-session background (cosmetic).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, color, na, ta


class Cnps5SmaAdx(Script):
    TITLE = "CNPS5 - SMA / ADX"
    PINE_VERSION = 5
    OVERLAY = True
    STRATEGY = dict(initial_capital=100000000, default_qty_type="fixed", default_qty_value=1)
    SOURCE = {"id": "dg3LhrbJ", "author": "Khanhtq26", "licence": "not stated",
              "url": "https://www.tradingview.com/script/dg3LhrbJ-CNPS5-SMA-ADX"}

    def init(self):
        g = "Cài đặt chỉ báo"
        self.sma_signal_len = self.input.int(20, "Chu kỳ SMA tín hiệu", minval=1, group=g)
        self.adx_len = self.input.int(14, "Chu kỳ ADX", minval=1, group=g)
        self.adx_threshold = self.input.float(25, "Ngưỡng ADX", minval=1, group=g)
        g = "Bộ lọc xu hướng"
        self.use_trend_filter = self.input.bool(True, "Dùng bộ lọc xu hướng SMA?", group=g)
        self.sma_len = self.input.int(200, "Chu kỳ SMA", minval=1, group=g)
        self.trade_dir = self.input.string("Cả hai", "Chiều giao dịch", options=["Mua", "Bán", "Cả hai"], group="Chiều giao dịch")
        g = "Cắt lỗ / Chốt lời"
        self.sl_points = self.input.float(10.0, "Cắt lỗ (điểm)", minval=0.1, step=0.5, group=g)
        self.use_tp = self.input.bool(True, "Dùng chốt lời?", group=g)
        self.tp_points = self.input.float(20.0, "Chốt lời (điểm)", minval=0.1, step=0.5, group=g)
        g = "Bộ lọc giờ"
        self.use_time_filter = self.input.bool(True, "Dùng bộ lọc giờ?", group=g)
        self.start_hour = self.input.int(9, "Giờ bắt đầu", minval=0, maxval=23, group=g)
        self.start_minute = self.input.int(0, "Phút bắt đầu", minval=0, maxval=59, group=g)
        self.end_hour = self.input.int(14, "Giờ kết thúc", minval=0, maxval=23, group=g)
        self.end_minute = self.input.int(30, "Phút kết thúc", minval=0, maxval=59, group=g)

    def on_bar(self):
        st = self.strategy

        def prev(h):
            v = h[1]
            return (not na(v)) and bool(v)

        sma_trend = ta.sma(self.close, self.sma_len)
        sh = self.H("smat")
        prev_sma = sh[1]
        sh.set(sma_trend)
        is_bull = sma_trend >= prev_sma
        is_bear = sma_trend < prev_sma
        bull_h, bear_h = self.H("bull"), self.H("bear")
        bull_1, bear_1 = prev(bull_h), prev(bear_h)
        bull_h.set(is_bull)
        bear_h.set(is_bear)
        sma_signal = ta.sma(self.close, self.sma_signal_len)
        sg = self.H("sg")
        prev_sg = sg[1]
        sg.set(sma_signal)
        sma_slope = sma_signal >= prev_sg
        sma_slope_dn = sma_signal < prev_sg
        slope_h, slope_dn_h = self.H("slope"), self.H("slopedn")
        slope_1, slope_dn_1 = prev(slope_h), prev(slope_dn_h)
        slope_h.set(sma_slope)
        slope_dn_h.set(sma_slope_dn)
        _di_plus, _di_minus, adx_val = ta.dmi(self.adx_len, self.adx_len)
        adx_strong = adx_val > self.adx_threshold
        raw_long = sma_slope and adx_strong
        raw_short = sma_slope_dn and adx_strong
        long_signal = raw_long and (is_bull if self.use_trend_filter else True)
        short_signal = raw_short and (is_bear if self.use_trend_filter else True)
        can_long_dir = self.trade_dir == "Mua" or self.trade_dir == "Cả hai"
        can_short_dir = self.trade_dir == "Bán" or self.trade_dir == "Cả hai"
        session_start = self.start_hour * 60 + self.start_minute
        session_end = self.end_hour * 60 + self.end_minute
        current_minutes = self.hour() * 60 + self.minute()
        in_session = (current_minutes >= session_start and current_minutes < session_end) if self.use_time_filter else True
        ins = self.H("ins")
        session_just_ended = self.use_time_filter and not in_session and prev(ins)
        ins.set(in_session)
        sma_flip_dn = sma_slope_dn and slope_1
        sma_flip_up = sma_slope and slope_dn_1
        if sma_flip_dn and st.position_size > 0:
            st.close("Mua", comment="SMA đảo chiều")
        if sma_flip_up and st.position_size < 0:
            st.close("Bán", comment="SMA đảo chiều")
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
