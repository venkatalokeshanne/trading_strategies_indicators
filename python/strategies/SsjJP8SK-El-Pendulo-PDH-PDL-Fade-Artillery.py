"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : El Pendulo PDH PDL Fade [Artillery]
Author       : ArtilleryTrades
Source URL   : https://www.tradingview.com/script/SsjJP8SK-El-Pendulo-PDH-PDL-Fade-Artillery
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-29 by Claude (pine-to-python skill)

Line-for-line translation (process_orders_on_close). The regular-session high / low / midpoint of the previous day are tracked; in the evening trade window a touch of the previous-day high (low), followed by a bearish (bullish) reversal candle that closes back near the level, arms a fade within a few grace bars if the VWAP side agrees; the entry is at the close with a stop beyond the tested extreme and a target at the midpoint or a risk:reward multiple. A time stop, the window end and midnight close the trade.

Deviations from the original: none.
Not carried over: PDH / PDL / midpoint lines and labels, markers and the dashboard (display only).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, na, nz, pmath, ta


class ElPendulo(Script):
    TITLE = "El Pendulo PDH PDL Fade [Artillery]"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(initial_capital=50000, default_qty_type="fixed", default_qty_value=1, commission_type="cash_per_contract", commission_value=0.62,
                    slippage=1, pyramiding=0, process_orders_on_close=True, margin_long=5, margin_short=5)
    SOURCE = {"id": "SsjJP8SK", "author": "ArtilleryTrades", "licence": "not stated",
              "url": "https://www.tradingview.com/script/SsjJP8SK-El-Pendulo-PDH-PDL-Fade-Artillery"}

    def init(self):
        i = self.input
        g = "RTH Session"
        self.rth_start_h = i.int(9, "RTH Start Hour (ET)", minval=0, maxval=23, group=g)
        self.rth_start_m = i.int(30, "RTH Start Minute", minval=0, maxval=59, group=g)
        self.rth_end_h = i.int(16, "RTH End Hour (ET)", minval=0, maxval=23, group=g)
        self.rth_end_m = i.int(0, "RTH End Minute", minval=0, maxval=59, group=g)
        g = "Trade Window"
        self.tw_start_h = i.int(21, "Trade Start Hour (ET)", minval=0, maxval=23, group=g)
        self.tw_start_m = i.int(0, "Trade Start Minute", minval=0, maxval=59, group=g)
        self.tw_end_h = i.int(23, "Trade End Hour (ET)", minval=0, maxval=23, group=g)
        self.tw_end_m = i.int(55, "Trade End Minute", minval=0, maxval=59, group=g)
        self.no_entry_h = i.int(23, "No Entry After Hour", minval=0, maxval=23, group=g)
        self.no_entry_m = i.int(0, "No Entry After Minute", minval=0, maxval=59, group=g)
        g = "Detection"
        self.touch_zone = i.float(5.0, "Touch Zone (pts from PDH/PDL)", minval=1, step=1, group=g)
        self.min_body = i.float(2.0, "Min Reversal Body (pts)", minval=0.5, step=0.5, group=g)
        self.close_tol = i.float(2.0, "Close Tolerance Past Level (pts)", minval=0, step=0.5, group=g)
        self.entry_grace = i.int(3, "Entry Grace Bars After Signal", minval=0, maxval=6, group=g)
        self.use_vwap = i.bool(True, "Use VWAP Directional Filter", group="VWAP")
        g = "Risk"
        self.sl_buffer = i.float(4.0, "SL Beyond Extreme (pts)", minval=1, step=1, group=g)
        self.max_sl_dist = i.float(25.0, "Max SL Distance (pts)", minval=10, step=5, group=g)
        self.rr_target = i.float(1.0, "R:R Target", minval=0.25, maxval=3.0, step=0.25, group=g)
        self.use_mid_tp = i.bool(True, "Use PDH/PDL Midpoint as TP", group=g)
        self.max_trades = i.int(2, "Max Trades/Session", minval=1, maxval=5, group=g)
        self.time_stop_bars = i.int(24, "Time Stop (bars)", minval=6, maxval=60, group=g)
        self.rth_high = NA
        self.rth_low = NA
        self.rth_high_pd = NA
        self.rth_low_pd = NA
        self.rth_mid_pd = NA
        self.rth_building = False
        self.test_dir = 0
        self.test_extreme = NA
        self.test_start_bar = NA
        self.signal_ready = False
        self.signal_bar = NA
        self.session_n = 0
        self.entry_bar = NA

    @staticmethod
    def in_window(n_m, s_h, s_m, e_h, e_m):
        s = s_h * 60 + s_m
        e = e_h * 60 + e_m
        return (n_m >= s and n_m < e) if s <= e else (n_m >= s or n_m < e)

    def reset_test(self):
        self.test_dir = 0
        self.test_extreme = NA
        self.test_start_bar = NA

    def reset_signal(self):
        self.signal_ready = False
        self.signal_bar = NA

    def on_bar(self):
        st = self.strategy
        close, open_, high, low = self.close, self.open, self.high, self.low
        tz = "America/New_York"
        et_h = self.hour(self.time, tz)
        et_m = self.minute(self.time, tz)
        et_time = et_h * 60 + et_m
        eh_h, em_h = self.H("et_h"), self.H("et_m")
        et_h_1, et_m_1 = eh_h[1], em_h[1]
        eh_h.set(et_h)
        em_h.set(et_m)
        n_m = et_h * 60 + et_m
        in_rth = self.in_window(n_m, self.rth_start_h, self.rth_start_m, self.rth_end_h, self.rth_end_m)
        in_trade = self.in_window(n_m, self.tw_start_h, self.tw_start_m, self.tw_end_h, self.tw_end_m)
        in_rth_h = self.H("in_rth")
        in_rth_1 = in_rth_h[1]
        in_rth_1 = (not na(in_rth_1)) and bool(in_rth_1)
        in_rth_h.set(in_rth)
        no_entry = et_time >= self.no_entry_h * 60 + self.no_entry_m
        new_evening = et_h == 20 and et_m == 0 and not (et_h_1 == 20 and et_m_1 == 0)
        rth_start = in_rth and not in_rth_1
        if rth_start:
            if (not na(self.rth_high)) and not na(self.rth_low):
                self.rth_high_pd = self.rth_high
                self.rth_low_pd = self.rth_low
                self.rth_mid_pd = (self.rth_high + self.rth_low) / 2.0
            self.rth_high = float(high)
            self.rth_low = float(low)
            self.rth_building = True
        if in_rth and self.rth_building:
            self.rth_high = pmath.max(nz(self.rth_high, high), high)
            self.rth_low = pmath.min(nz(self.rth_low, low), low)
        rth_end = (not in_rth) and in_rth_1 and self.rth_building
        if rth_end:
            self.rth_high_pd = self.rth_high
            self.rth_low_pd = self.rth_low
            self.rth_mid_pd = (self.rth_high + self.rth_low) / 2.0
            self.rth_building = False
        vwap_val = ta.vwap()
        levels_ready = (not na(self.rth_high_pd)) and (not na(self.rth_low_pd)) and self.rth_high_pd > self.rth_low_pd
        pdh_test = levels_ready and in_trade and high >= self.rth_high_pd - self.touch_zone
        pdl_test = levels_ready and in_trade and low <= self.rth_low_pd + self.touch_zone
        body_size = abs(close - open_)
        bull_body = close > open_ and body_size >= self.min_body
        bear_body = close < open_ and body_size >= self.min_body
        if new_evening:
            self.reset_test()
            self.reset_signal()
        if pdh_test and self.test_dir != 1 and not self.signal_ready:
            self.test_dir = 1
            self.test_extreme = float(high)
            self.test_start_bar = self.bar_index
        if pdl_test and self.test_dir != -1 and not self.signal_ready:
            self.test_dir = -1
            self.test_extreme = float(low)
            self.test_start_bar = self.bar_index
        if self.test_dir == 1:
            self.test_extreme = pmath.max(nz(self.test_extreme, high), high)
        if self.test_dir == -1:
            self.test_extreme = pmath.min(nz(self.test_extreme, low), low)
        if self.test_dir == 1 and not self.signal_ready:
            if bear_body and close <= self.rth_high_pd + self.close_tol:
                self.signal_ready = True
                self.signal_bar = self.bar_index
        if self.test_dir == -1 and not self.signal_ready:
            if bull_body and close >= self.rth_low_pd - self.close_tol:
                self.signal_ready = True
                self.signal_bar = self.bar_index
        if self.test_dir != 0 and (not self.signal_ready) and not na(self.test_start_bar):
            if self.bar_index - self.test_start_bar > 10:
                self.reset_test()
        if new_evening:
            self.session_n = 0
        flat = st.position_size == 0
        can_go = flat and levels_ready and in_trade and (not no_entry) and self.session_n < self.max_trades and self.signal_ready
        in_grace = (not na(self.signal_bar)) and self.bar_index >= self.signal_bar and self.bar_index <= self.signal_bar + self.entry_grace
        vwap_long_ok = (not self.use_vwap) or ((not na(vwap_val)) and close < vwap_val)
        vwap_short_ok = (not self.use_vwap) or ((not na(vwap_val)) and close > vwap_val)
        go_long = can_go and self.test_dir == -1 and in_grace and vwap_long_ok
        go_short = can_go and self.test_dir == 1 and in_grace and vwap_short_ok
        if go_long and not na(self.test_extreme):
            sl = self.test_extreme - self.sl_buffer
            sl_dist = close - sl
            if sl_dist > 0 and sl_dist <= self.max_sl_dist:
                rr_tp = close + sl_dist * self.rr_target
                mid_tp = self.rth_mid_pd if (self.use_mid_tp and not na(self.rth_mid_pd)) else rr_tp
                tp = pmath.min(mid_tp, rr_tp) if (self.use_mid_tp and mid_tp > close) else rr_tp
                if tp <= close:
                    tp = rr_tp
                st.entry("Long", st.long)
                st.exit("LX", "Long", limit=tp, stop=sl)
                self.session_n += 1
                self.entry_bar = self.bar_index
                self.reset_test()
                self.reset_signal()
        if go_short and not na(self.test_extreme):
            sl = self.test_extreme + self.sl_buffer
            sl_dist = sl - close
            if sl_dist > 0 and sl_dist <= self.max_sl_dist:
                rr_tp = close - sl_dist * self.rr_target
                mid_tp = self.rth_mid_pd if (self.use_mid_tp and not na(self.rth_mid_pd)) else rr_tp
                tp = pmath.max(mid_tp, rr_tp) if (self.use_mid_tp and mid_tp < close) else rr_tp
                if tp >= close:
                    tp = rr_tp
                st.entry("Short", st.short)
                st.exit("SX", "Short", limit=tp, stop=sl)
                self.session_n += 1
                self.entry_bar = self.bar_index
                self.reset_test()
                self.reset_signal()
        if st.position_size != 0 and not na(self.entry_bar):
            if self.bar_index - self.entry_bar >= self.time_stop_bars:
                st.close_all(comment="Time Stop")
        if st.position_size != 0 and not in_trade:
            st.close_all(comment="Session Close")
        if st.position_size != 0 and et_h == 0 and et_m == 0:
            st.close_all(comment="Midnight Close")
        if self.signal_ready and (not na(self.signal_bar)) and self.bar_index > self.signal_bar + self.entry_grace and flat:
            self.reset_test()
            self.reset_signal()
