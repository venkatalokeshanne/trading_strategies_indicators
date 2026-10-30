"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : DNSE VN301!, SMA 34/89 Dual Slope Strategy
Author       : (not shown)
Source URL   : https://www.tradingview.com/script/VFP7QkqV
Pine version : v5
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-29 by Claude (pine-to-python skill)

Line-for-line translation. Both SMAs (fast / slow) rising opens a long (both falling a short), optionally only when the SMA filter slopes the same way, inside the
time-of-day window (exchange time, bar start); leaving the window closes any position, and a flip of the SMA slope closes a position taken against it. Once a position exists, a stop / take-profit bracket around the average
price is (re-)issued at each bar close and works from the next bar.

Deviations from the original: none.
Not carried over: the SMA / stop / target line plots, signal shapes and the out-of-session background (cosmetic).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, color, na, ta


class Cnps03SmaDualSlope(Script):
    TITLE = "DNSE VN301!, SMA 34/89 Dual Slope Strategy"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(initial_capital=100000000, default_qty_type="fixed", default_qty_value=3, margin_long=0, margin_short=0, slippage=3, commission_type="cash_per_contract", commission_value=10000)
    SOURCE = {"id": "VFP7QkqV", "author": "", "licence": "not stated",
              "url": "https://www.tradingview.com/script/VFP7QkqV"}

    def init(self):
        g = "Cài đặt chỉ báo"
        self.sma_fast_len = self.input.int(34, "Fast SMA Length", minval=1, group=g)
        self.sma_slow_len = self.input.int(89, "Slow SMA Length", minval=1, group=g)
        g = "Bộ lọc xu hướng"
        self.use_trend_filter = self.input.bool(False, "Use SMA Trend Filter?", group=g)
        self.sma_len = self.input.int(200, "SMA Length", minval=1, group=g)
        self.trade_dir = self.input.string("Both", "Trade Direction", options=["Long", "Short", "Both"], group="Trade Direction")
        g = "Cắt lỗ / Chốt lời"
        self.sl_points = self.input.float(10.0, "Stop Loss Points", minval=0.1, step=0.5, group=g)
        self.use_tp = self.input.bool(True, "Use Take Profit?", group=g)
        self.tp_points = self.input.float(20.0, "Take Profit Points", minval=0.1, step=0.5, group=g)
        g = "Bộ lọc giờ"
        self.use_time_filter = self.input.bool(True, "Use Time Filter?", group=g)
        self.start_hour = self.input.int(9, "Start Hour", minval=0, maxval=23, group=g)
        self.start_minute = self.input.int(0, "Start Minute", minval=0, maxval=59, group=g)
        self.end_hour = self.input.int(14, "End Hour", minval=0, maxval=23, group=g)
        self.end_minute = self.input.int(30, "End Minute", minval=0, maxval=59, group=g)

    def on_bar(self):
        st = self.strategy
        sma_trend = ta.sma(self.close, self.sma_len)
        sma_prev = self.H("sma")
        prev = sma_prev[1]
        sma_prev.set(sma_trend)
        is_bull = sma_trend >= prev
        is_bear = sma_trend < prev
        sma_fast = ta.sma(self.close, self.sma_fast_len)
        sma_slow = ta.sma(self.close, self.sma_slow_len)
        fh, sh = self.H("fast"), self.H("slow")
        fast_rising = sma_fast >= fh[1]
        fast_falling = sma_fast < fh[1]
        slow_rising = sma_slow >= sh[1]
        slow_falling = sma_slow < sh[1]
        fh.set(sma_fast)
        sh.set(sma_slow)
        raw_long = fast_rising and slow_rising
        raw_short = fast_falling and slow_falling
        long_signal = raw_long and (is_bull if self.use_trend_filter else True)
        short_signal = raw_short and (is_bear if self.use_trend_filter else True)
        can_long_dir = self.trade_dir == "Long" or self.trade_dir == "Both"
        can_short_dir = self.trade_dir == "Short" or self.trade_dir == "Both"
        session_start = self.start_hour * 60 + self.start_minute
        session_end = self.end_hour * 60 + self.end_minute
        current_minutes = self.hour() * 60 + self.minute()
        in_session = (current_minutes >= session_start and current_minutes < session_end) if self.use_time_filter else True
        ins = self.H("ins")
        was_in = ins[1]
        session_just_ended = self.use_time_filter and not in_session and not na(was_in) and bool(was_in)
        ins.set(in_session)
        bull_prev, bear_prev = self.H("bu"), self.H("be")
        sma_flip_bear = self.use_trend_filter and is_bear and bool(bull_prev[1]) if not na(bull_prev[1]) else False
        sma_flip_bull = self.use_trend_filter and is_bull and bool(bear_prev[1]) if not na(bear_prev[1]) else False
        bull_prev.set(is_bull)
        bear_prev.set(is_bear)
        if session_just_ended and st.position_size != 0:
            st.close_all(comment="Hết phiên")
        if sma_flip_bear and st.position_size > 0:
            st.close("Long", comment="SMA đảo chiều")
        if sma_flip_bull and st.position_size < 0:
            st.close("Short", comment="SMA đảo chiều")
        can_long = long_signal and in_session and can_long_dir
        can_short = short_signal and in_session and can_short_dir
        long_sl = st.position_avg_price - self.sl_points
        long_tp = st.position_avg_price + self.tp_points
        short_sl = st.position_avg_price + self.sl_points
        short_tp = st.position_avg_price - self.tp_points
        if can_long:
            st.entry("Long", st.long)
        if can_short:
            st.entry("Short", st.short)
        if st.position_size > 0:
            st.exit("Thoát Mua", "Long", stop=long_sl, limit=long_tp if self.use_tp else NA)
        if st.position_size < 0:
            st.exit("Thoát Bán", "Short", stop=short_sl, limit=short_tp if self.use_tp else NA)
        self.plot(sma_fast, "SMA nhanh", color=color.blue if fast_rising else color.orange, linewidth=2)
        self.plot(sma_slow, "SMA chậm", color=color.teal if slow_rising else color.maroon, linewidth=2)
        self.plot(sma_trend if self.use_trend_filter else NA, "Bộ lọc xu hướng SMA", color=color.green if is_bull else color.red, linewidth=1)
