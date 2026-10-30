"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : DNSE VN301!, SMA ADX/DI Trend Following Strategy
Author       : (not shown)
Source URL   : https://www.tradingview.com/script/ToaH6cKJ
Pine version : v5
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-29 by Claude (pine-to-python skill)

Line-for-line translation. A rising (falling) SMA89 over its value N bars ago with the ADX above its threshold and +DI over -DI (-DI over +DI) opens a long (short) on the first bar of the state, optionally only when the SMA200 slope agrees; a flip of the SMA89 slope closes a position against it. Entries are market orders (reversing), inside the time-of-day window (exchange time, bar start);
leaving the window closes any position. Once a position exists, a stop / take-profit bracket around the average price is (re-)issued at each bar close and works from the next bar.

Deviations from the original: none.
Not carried over: the line plots, signal shapes and the out-of-session background (cosmetic).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, color, na, ta


class DnseSmaAdxDi(Script):
    TITLE = "DNSE VN301!, SMA ADX/DI Trend Following Strategy"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(initial_capital=100000000, default_qty_type="fixed", default_qty_value=3, margin_long=0, margin_short=0, slippage=3, commission_type="cash_per_contract", commission_value=10000)
    SOURCE = {"id": "ToaH6cKJ", "author": "", "licence": "not stated",
              "url": "https://www.tradingview.com/script/ToaH6cKJ"}

    def init(self):
        g = "Indicator Settings"
        self.sma_signal_len = self.input.int(89, "Signal SMA Length", minval=1, group=g)
        self.sma_slope_lookback = self.input.int(5, "SMA Slope Lookback", minval=1, group=g)
        self.adx_len = self.input.int(14, "ADX Length", minval=1, group=g)
        self.adx_threshold = self.input.float(20.0, "ADX Threshold", minval=1, step=0.5, group=g)
        self.use_di_filter = self.input.bool(True, "Use DI Filter?", group=g)
        self.use_new_signal_only = self.input.bool(True, "Enter Only On New Signal?", group=g)
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
        sig_n = sg[self.sma_slope_lookback]
        sg.set(sma_signal)
        sma_slope = (not na(sig_n)) and sma_signal > sig_n
        sma_slope_dn = (not na(sig_n)) and sma_signal < sig_n
        slope_h, slope_dn_h = self.H("slope"), self.H("slopedn")
        slope_1, slope_dn_1 = prev(slope_h), prev(slope_dn_h)
        slope_h.set(sma_slope)
        slope_dn_h.set(sma_slope_dn)
        di_plus, di_minus, adx_val = ta.dmi(self.adx_len, self.adx_len)
        adx_strong = adx_val > self.adx_threshold
        di_bull = di_plus > di_minus
        di_bear = di_minus > di_plus
        long_state = sma_slope and adx_strong and (di_bull if self.use_di_filter else True)
        short_state = sma_slope_dn and adx_strong and (di_bear if self.use_di_filter else True)
        ls_h, ss_h = self.H("ls"), self.H("ss")
        ls_1, ss_1 = prev(ls_h), prev(ss_h)
        ls_h.set(long_state)
        ss_h.set(short_state)
        raw_long = (long_state and not ls_1) if self.use_new_signal_only else long_state
        raw_short = (short_state and not ss_1) if self.use_new_signal_only else short_state
        long_signal = raw_long and (is_bull if self.use_trend_filter else True)
        short_signal = raw_short and (is_bear if self.use_trend_filter else True)
        can_long_dir = self.trade_dir == "Long" or self.trade_dir == "Both"
        can_short_dir = self.trade_dir == "Short" or self.trade_dir == "Both"
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
            st.close("Long", comment="SMA Slope Reversal")
        if sma_flip_up and st.position_size < 0:
            st.close("Short", comment="SMA Slope Reversal")
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
