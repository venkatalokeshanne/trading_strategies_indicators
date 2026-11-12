"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : DNSE VN301!, BB-SMA Trend Following
Author       : (not shown)
Source URL   : https://www.tradingview.com/script/gqnCcy2v
Pine version : v5
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-29 by Claude (pine-to-python skill)

Line-for-line translation. The close crossing over the upper (under the lower) Bollinger band opens a long (short) when the SMA200 slopes the same way; a flip of that slope closes a position against it. Entries are market orders (reversing), inside the time-of-day window (exchange time, bar start);
leaving the window closes any position. Once a position exists, a stop / take-profit bracket around the average price is (re-)issued at each bar close and works from the next bar.

Deviations from the original: none.
Not carried over: the line plots, signal shapes and the out-of-session background (cosmetic).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, color, na, ta


class Cnps4BbSma(Script):
    TITLE = "DNSE VN301!, BB-SMA Trend Following"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(initial_capital=100000000, default_qty_type="fixed", default_qty_value=3, margin_long=0, margin_short=0, slippage=3, commission_type="cash_per_contract", commission_value=10000)
    SOURCE = {"id": "gqnCcy2v", "author": "", "licence": "not stated",
              "url": "https://www.tradingview.com/script/gqnCcy2v"}

    def init(self):
        g = "Bollinger Bands"
        self.bb_len = self.input.int(20, "BB Length", minval=1, group=g)
        self.bb_mult = self.input.float(2.0, "BB Multiplier", minval=0.1, step=0.1, group=g)
        self.sma_len = self.input.int(200, "SMA Length", minval=1, group="Bộ lọc xu hướng")
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
        bb_basis = ta.sma(self.close, self.bb_len)
        bb_dev = self.bb_mult * ta.stdev(self.close, self.bb_len)
        bb_upper = bb_basis + bb_dev
        bb_lower = bb_basis - bb_dev
        raw_long = ta.crossover(self.close, bb_upper)
        raw_short = ta.crossunder(self.close, bb_lower)
        long_signal = raw_long and (is_bull)
        short_signal = raw_short and (is_bear)
        can_long_dir = self.trade_dir == "Long" or self.trade_dir == "Both"
        can_short_dir = self.trade_dir == "Short" or self.trade_dir == "Both"
        session_start = self.start_hour * 60 + self.start_minute
        session_end = self.end_hour * 60 + self.end_minute
        current_minutes = self.hour() * 60 + self.minute()
        in_session = (current_minutes >= session_start and current_minutes < session_end) if self.use_time_filter else True
        ins = self.H("ins")
        session_just_ended = self.use_time_filter and not in_session and prev(ins)
        ins.set(in_session)
        flip_bear = is_bear and bull_1
        flip_bull = is_bull and bear_1
        if flip_bear and st.position_size > 0:
            st.close("Long", comment="SMA đảo chiều")
        if flip_bull and st.position_size < 0:
            st.close("Short", comment="SMA đảo chiều")
        if session_just_ended and st.position_size != 0:
            st.close_all(comment="Hết phiên")

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
