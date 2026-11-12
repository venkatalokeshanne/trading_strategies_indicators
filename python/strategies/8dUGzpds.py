"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : DNSE VN301!, Keltner Break Out Strategy
Author       : (not shown)
Source URL   : https://www.tradingview.com/script/8dUGzpds
Pine version : v5
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. A close above the upper (below the lower) Keltner band, with the SMA200 slope as trend filter and inside the time window, enters; a stop and optional take-profit in points
around the average price are issued while in a position; the position is closed on the first bar after the session window ends.

Deviations from the original: none.
Not carried over: indicator and band plots, stop / target plots, signal shapes and the out-of-session background (cosmetic).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, color, ta


class Psol02Keltner(Script):
    TITLE = "DNSE VN301!, Keltner Break Out Strategy"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(initial_capital=100000000, default_qty_type="fixed", default_qty_value=3, margin_long=0, margin_short=0, slippage=3, commission_type="cash_per_contract", commission_value=10000)
    SOURCE = {"id": "8dUGzpds", "author": "", "licence": "not stated",
              "url": "https://www.tradingview.com/script/8dUGzpds"}

    def init(self):
        g = "Keltner Channel"
        self.kc_len = self.input.int(20, "EMA Length", minval=1, group=g)
        self.atr_len = self.input.int(10, "ATR Length", minval=1, group=g)
        self.mult = self.input.float(2.0, "Multiplier", minval=0.1, step=0.1, group=g)
        g = "Bộ lọc xu hướng"
        self.use_trend_filter = self.input.bool(True, "Use SMA Trend Filter?", group=g)
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
        sma_trend = ta.sma(self.close, self.sma_len)
        sma_prev = self.H("sma")[1]
        self.H("sma").set(sma_trend)
        is_bull = sma_trend >= sma_prev
        is_bear = sma_trend < sma_prev
        kc_middle = ta.ema(self.close, self.kc_len)
        kc_upper = kc_middle + self.mult * ta.atr(self.atr_len)
        kc_lower = kc_middle - self.mult * ta.atr(self.atr_len)
        raw_long = self.close > kc_upper
        raw_short = self.close < kc_lower
        long_signal = raw_long and (is_bull if self.use_trend_filter else True)
        short_signal = raw_short and (is_bear if self.use_trend_filter else True)
        can_long_dir = self.trade_dir == "Long" or self.trade_dir == "Both"
        can_short_dir = self.trade_dir == "Short" or self.trade_dir == "Both"
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
            st.entry("Long", st.long)
        if can_short:
            st.entry("Short", st.short)
        if st.position_size > 0:
            st.exit("Thoát Mua", "Long", stop=long_sl, limit=long_tp if self.use_tp else NA)
        if st.position_size < 0:
            st.exit("Thoát Bán", "Short", stop=short_sl, limit=short_tp if self.use_tp else NA)
        self.plot(kc_middle, "Keltner Giữa", color=color.orange)
        self.plot(kc_upper, "Keltner Trên", color=color.blue)
        self.plot(kc_lower, "Keltner Dưới", color=color.blue)
