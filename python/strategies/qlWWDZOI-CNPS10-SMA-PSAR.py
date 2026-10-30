"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : CNPS10 - SMA/PSAR
Author       : Khanhtq26
Source URL   : https://www.tradingview.com/script/qlWWDZOI-CNPS10-SMA-PSAR
Pine version : v5
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-29 by Claude (pine-to-python skill)

Line-for-line translation. A rising SMA with the close above the parabolic SAR opens a long (falling SMA and close below, a short); the position is closed when the SMA turns against it or the close crosses the SAR. Entries are market orders (reversing), inside the time-of-day window (exchange time, bar start);
leaving the window closes any position. Once a position exists, a stop / take-profit bracket around the average price is (re-)issued at each bar close and works from the next bar.

Deviations from the original: none.
Not carried over: the line plots, signal shapes and the out-of-session background (cosmetic).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, color, na, ta


class Cnps10SmaPsar(Script):
    TITLE = "CNPS10 - SMA/PSAR"
    PINE_VERSION = 5
    OVERLAY = True
    STRATEGY = dict(initial_capital=100000000, default_qty_type="fixed", default_qty_value=1)
    SOURCE = {"id": "qlWWDZOI", "author": "Khanhtq26", "licence": "not stated",
              "url": "https://www.tradingview.com/script/qlWWDZOI-CNPS10-SMA-PSAR"}

    def init(self):
        g = "Cài đặt chỉ báo"
        self.sma_len = self.input.int(14, "Chu kỳ SMA tín hiệu", minval=1, group=g)
        self.psar_step = self.input.float(0.02, "PSAR Bước (Step)", minval=0.001, step=0.001, group=g)
        self.psar_max = self.input.float(0.2, "PSAR Tối đa (Max)", minval=0.01, step=0.01, group=g)

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

        def prev(h):
            v = h[1]
            return (not na(v)) and bool(v)

        sma_val = ta.sma(self.close, self.sma_len)
        sv = self.H("sv")
        prev_v = sv[1]
        sv.set(sma_val)
        sma_up = sma_val > prev_v
        sma_down = sma_val < prev_v
        psar_val = ta.sar(self.psar_step, self.psar_step, self.psar_max)
        price_above_psar = self.close > psar_val
        price_below_psar = self.close < psar_val
        raw_long = sma_up and price_above_psar
        raw_short = sma_down and price_below_psar
        exit_long = sma_down or not price_above_psar
        exit_short = sma_up or not price_below_psar
        long_signal = raw_long and (True)
        short_signal = raw_short and (True)
        can_long_dir = self.trade_dir == "Mua" or self.trade_dir == "Cả hai"
        can_short_dir = self.trade_dir == "Bán" or self.trade_dir == "Cả hai"
        session_start = self.start_hour * 60 + self.start_minute
        session_end = self.end_hour * 60 + self.end_minute
        current_minutes = self.hour() * 60 + self.minute()
        in_session = (current_minutes >= session_start and current_minutes < session_end) if self.use_time_filter else True
        ins = self.H("ins")
        session_just_ended = self.use_time_filter and not in_session and prev(ins)
        ins.set(in_session)
        if st.position_size > 0 and exit_long:
            st.close("Mua", comment="Thoát tín hiệu")
        if st.position_size < 0 and exit_short:
            st.close("Bán", comment="Thoát tín hiệu")
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
