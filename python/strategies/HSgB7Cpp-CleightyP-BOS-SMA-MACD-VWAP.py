"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : Bos/CHOCH by shujat
Author       : CleightyP
Source URL   : https://www.tradingview.com/script/HSgB7Cpp-CleightyP-BOS-SMA-MACD-VWAP
Pine version : v5
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-29 by Claude (pine-to-python skill)

Line-for-line translation. Break-of-structure / change-of-character trading on the last pivot high / low (the pivot lookback scales up on higher time frames): with "Enter On Tick" a buy-stop at the last pivot high (sell-stop at the pivot low) is renewed or cancelled every bar while the SMA-slope / stacking / divergence and VWAP filters pass and the pivot has not been used; otherwise the entry is a market order after a confirmed close beyond the pivot with an optional strong-candle test. The stop (previous swing, entry candle or percent) and the R:R target are measured from the pivot / close and issued while the trade is open. A new day can close the position, cancel pending orders and clear the structure.
Deviations from the original: none. [VERIFY] `strategy.cancel("Long")` runs every bar after a new-day `strategy.close("Long")`; pinelib treats the close as a separate order (TradingView lists it as "Close entry(ies) order Long"), so it is not cancelled.
Not carried over: the structure lines and labels, the SMA / VWAP plots and the P&L boxes (display only); the three colour inputs.
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, na, nz, pmath, ta

TZ_OPTIONS = ["America/New_York", "America/Chicago", "America/Denver", "America/Los_Angeles", "UTC", "Europe/London", "Asia/Tokyo", "Australia/Sydney"]


class BosChochShujat(Script):
    TITLE = "Bos/CHOCH by shujat"
    PINE_VERSION = 5
    OVERLAY = True
    STRATEGY = dict(pyramiding=0)
    SOURCE = {"id": "HSgB7Cpp", "author": "CleightyP", "licence": "not stated",
              "url": "https://www.tradingview.com/script/HSgB7Cpp-CleightyP-BOS-SMA-MACD-VWAP"}

    def init(self):
        i = self.input
        g = "Structure Detection"
        self.swing_size = i.int(1, "Pivot Lookback", minval=1, maxval=50, group=g)
        self.auto_swing = i.bool(True, "Auto-adjust Pivot Lookback for TF", group=g)
        g = "Stop Loss"
        self.sl_type = i.string("Previous Swing", "Stop Loss Type", options=["Previous Swing", "Entry Candle", "Percent"], group=g)
        self.sl_percent = i.float(0.5, "Stop Loss %", minval=0.1, step=0.1, group=g)
        self.sl_buf_pts = i.float(0.0, "SL Buffer (points)", minval=0.0, step=0.1, group=g)
        self.sl_buf_pct = i.float(0.0, "SL Buffer %", minval=0.0, step=0.1, group=g)
        g = "Take Profit"
        self.sep_rr = i.bool(False, "Separate Long/Short R:R", group=g)
        self.rr_long = i.float(1.5, "Long R:R Multiplier", minval=0.1, step=0.1, group=g)
        self.rr_short = i.float(1.5, "Short R:R Multiplier", minval=0.1, step=0.1, group=g)
        self.rr_target = i.float(0.7, "R:R Multiplier (both)", minval=0.1, step=0.1, group=g)
        g = "Entry Timing"
        self.enter_on_tick = i.bool(True, "Enter On Tick (BOS candle)", group=g)
        g = "Strategy"
        self.bos_only = i.bool(True, "Enter On BOS Only", group=g)
        self.choch_only = i.bool(False, "Enter On CHoCH Only", group=g)
        self.use_strong = i.bool(True, "Use Strong Candle Filter", group=g)
        self.body_over_wick = i.float(100.0, "Body > Wick By (%)", minval=0.0, step=5.0, group=g)
        g = "SMA Trend Filter"
        self.use_sma = i.bool(True, "Use SMA Slope Filter", group=g)
        self.sma_mode = i.string("2 of 3 SMAs", "SMA Filter Mode", options=["All 3 SMAs", "2 of 3 SMAs", "SMA 21+84 Only", "SMA 21 Only", "Price vs SMA"], group=g)
        self.sma21_len = i.int(21, "SMA 21 Length", minval=1, group=g)
        self.sma84_len = i.int(84, "SMA 84 Length", minval=1, group=g)
        self.sma252_len = i.int(252, "SMA 252 Length", minval=1, group=g)
        self.use_stack = i.bool(False, "Use SMA Stacking Filter", group=g)
        self.use_diverge = i.bool(False, "Use SMA Slope Divergence Filter", group=g)
        g = "Daily Settings"
        self.close_eod = i.bool(False, "Close Positions at End of Day", group=g)
        self.max_per_day = i.int(0, "Max Trades Per Day (0=unlimited)", minval=0, maxval=20, group=g)
        self.reset_daily = i.bool(False, "Reset Structure on New Day", group=g)
        g = "P&L Display"
        i.bool(True, "Show P&L Boxes", group=g)
        g = "NY VWAP Filter"
        self.ny_tz = i.string("America/New_York", "NY VWAP Timezone", options=TZ_OPTIONS, group=g)
        self.ny_hour = i.int(9, "NY VWAP Anchor Hour", minval=0, maxval=23, inline="nyanchor", group=g)
        self.ny_min = i.int(30, ":", minval=0, maxval=59, inline="nyanchor", group=g)
        i.bool(True, "Show NY VWAP", group=g)
        self.filter_ny = i.bool(False, "Filter by NY VWAP", group=g)
        g = "Daily VWAP Filter"
        self.d_tz = i.string("America/New_York", "Daily VWAP Timezone", options=TZ_OPTIONS, group=g)
        self.d_hour = i.int(0, "Daily VWAP Anchor Hour", minval=0, maxval=23, inline="dailyanchor", group=g)
        self.d_min = i.int(0, ":", minval=0, maxval=59, inline="dailyanchor", group=g)
        i.bool(True, "Show Daily VWAP", group=g)
        self.filter_daily = i.bool(False, "Filter by Daily VWAP", group=g)
        self.prev_high = NA
        self.prev_low = NA
        self.high_active = False
        self.low_active = False
        self.prev_break_dir = 0
        self.long_sl = self.long_tp = self.short_sl = self.short_tp = NA
        self.trades_today = 0
        self.last_long_pivot = NA
        self.last_short_pivot = NA
        self.last_pos_size = 0.0

    def _entry_type_ok(self, is_bos):
        use_bos = self.bos_only and not self.choch_only
        use_choch = self.choch_only and not self.bos_only
        if use_bos:
            return is_bos
        if use_choch:
            return not is_bos
        return True

    def on_bar(self):
        st = self.strategy
        close, open_, high, low = self.close, self.open, self.high, self.low
        mintick = self.syminfo.mintick
        tf_minutes = self.timeframe.in_seconds() / 60
        swing = self.swing_size
        if self.auto_swing:
            if tf_minutes >= 1440:
                swing = pmath.max(self.swing_size, 3)
            elif tf_minutes >= 240:
                swing = pmath.max(self.swing_size, 2)
            elif tf_minutes >= 60:
                swing = pmath.max(self.swing_size, 2)
        sma21 = ta.sma(close, self.sma21_len)
        sma84 = ta.sma(close, self.sma84_len)
        sma252 = ta.sma(close, self.sma252_len)
        h21, h84, h252 = self.H("sma21"), self.H("sma84"), self.H("sma252")
        s21, s84, s252 = sma21 - h21[1], sma84 - h84[1], sma252 - h252[1]
        h21.set(sma21)
        h84.set(sma84)
        h252.set(sma252)
        up21, up84, up252 = s21 > 0, s84 > 0, s252 > 0
        dn21, dn84, dn252 = s21 < 0, s84 < 0, s252 < 0
        above_all = close > sma21 and close > sma84 and close > sma252
        below_all = close < sma21 and close < sma84 and close < sma252
        stack_bull = sma21 > sma84 and sma84 > sma252
        stack_bear = sma21 < sma84 and sma84 < sma252
        stack_long_ok = True if not self.use_stack else stack_bull
        stack_short_ok = True if not self.use_stack else stack_bear
        div_bull = s21 > s84 and s84 > s252
        div_bear = s21 < s84 and s84 < s252
        div_long_ok = True if not self.use_diverge else div_bull
        div_short_ok = True if not self.use_diverge else div_bear
        mode = self.sma_mode
        if not self.use_sma:
            long_slope_ok = short_slope_ok = True
        elif mode == "All 3 SMAs":
            long_slope_ok, short_slope_ok = (up21 and up84 and up252), (dn21 and dn84 and dn252)
        elif mode == "2 of 3 SMAs":
            long_slope_ok = (int(up21) + int(up84) + int(up252)) >= 2
            short_slope_ok = (int(dn21) + int(dn84) + int(dn252)) >= 2
        elif mode == "SMA 21+84 Only":
            long_slope_ok, short_slope_ok = (up21 and up84), (dn21 and dn84)
        elif mode == "SMA 21 Only":
            long_slope_ok, short_slope_ok = up21, dn21
        elif mode == "Price vs SMA":
            long_slope_ok, short_slope_ok = above_all, below_all
        else:
            long_slope_ok = short_slope_ok = True
        long_trend_ok = long_slope_ok and stack_long_ok and div_long_ok
        short_trend_ok = short_slope_ok and stack_short_ok and div_short_ok
        is_new_day = ta.change(self.time_fn("D")) != 0
        if is_new_day:
            self.trades_today = 0
            if self.close_eod:
                if st.position_size > 0:
                    st.close("Long", comment="EOD Close")
                if st.position_size < 0:
                    st.close("Short", comment="EOD Close")
            if st.position_size == 0:
                st.cancel_all()
            if st.position_size == 0:
                self.long_sl = self.long_tp = self.short_sl = self.short_tp = NA
            self.last_long_pivot = NA
            self.last_short_pivot = NA
            if self.reset_daily:
                self.prev_high = NA
                self.prev_low = NA
                self.high_active = False
                self.low_active = False
                self.prev_break_dir = 0
        vwap_src = (open_ + high + low + close) / 4
        ny_anchor = self.timestamp(self.ny_tz, self.year(), self.month(), self.dayofmonth(), self.ny_hour, self.ny_min)
        t_h = self.H("time")
        time_1 = t_h[1]
        t_h.set(self.time)
        is_new_ny = self.time >= ny_anchor and (na(time_1) or time_1 < ny_anchor)
        ny_vwap, _, _ = ta.vwap(vwap_src, is_new_ny, 1)
        d_anchor = self.timestamp(self.d_tz, self.year(), self.month(), self.dayofmonth(), self.d_hour, self.d_min)
        is_new_d = self.time >= d_anchor and (na(time_1) or time_1 < d_anchor)
        d_vwap, _, _ = ta.vwap(vwap_src, is_new_d, 1)
        ny_long_ok = (not na(ny_vwap) and close > ny_vwap) if self.filter_ny else True
        ny_short_ok = (not na(ny_vwap) and close < ny_vwap) if self.filter_ny else True
        d_long_ok = (not na(d_vwap) and close > d_vwap) if self.filter_daily else True
        d_short_ok = (not na(d_vwap) and close < d_vwap) if self.filter_daily else True
        vwap_long_ok = ny_long_ok and d_long_ok
        vwap_short_ok = ny_short_ok and d_short_ok
        piv_hi = ta.pivothigh(high, swing, swing)
        piv_lo = ta.pivotlow(low, swing, swing)
        if not na(piv_hi):
            self.prev_high = float(piv_hi)
            self.high_active = True
        if not na(piv_lo):
            self.prev_low = float(piv_lo)
            self.low_active = True
        body = abs(close - open_)
        wick = pmath.max((high - low) - body, 0.0)
        strong_bull = close > open_ and body >= wick * (1 + self.body_over_wick / 100)
        strong_bear = close < open_ and body >= wick * (1 + self.body_over_wick / 100)
        can_trade_today = self.max_per_day == 0 or self.trades_today < self.max_per_day
        prev_high, prev_low = self.prev_high, self.prev_low
        if self.enter_on_tick:
            is_bull_bos = self.prev_break_dir != -1
            pivot_ok_l = na(self.last_long_pivot) or na(prev_high) or abs(prev_high - self.last_long_pivot) > mintick
            long_ok = (self.high_active and not na(prev_high) and long_trend_ok and self._entry_type_ok(is_bull_bos) and vwap_long_ok
                       and st.position_size <= 0 and can_trade_today and pivot_ok_l)
            if long_ok:
                if self.sl_type == "Previous Swing":
                    sl_base = prev_low
                elif self.sl_type == "Entry Candle":
                    sl_base = low
                else:
                    sl_base = prev_high * (1 - (self.sl_percent / 100))
                sl_calc = sl_base - self.sl_buf_pts - (prev_high * self.sl_buf_pct / 100)
                risk = prev_high - sl_calc
                if risk > 0:
                    self.long_sl = float(sl_calc)
                    rr = self.rr_long if self.sep_rr else self.rr_target
                    self.long_tp = float(prev_high + (risk * rr))
                    self.last_long_pivot = prev_high
                    st.entry("Long", st.long, stop=prev_high)
                else:
                    st.cancel("Long")
            else:
                st.cancel("Long")
            is_bear_bos = self.prev_break_dir != 1
            pivot_ok_s = na(self.last_short_pivot) or na(prev_low) or abs(prev_low - self.last_short_pivot) > mintick
            short_ok = (self.low_active and not na(prev_low) and short_trend_ok and self._entry_type_ok(is_bear_bos) and vwap_short_ok
                        and st.position_size >= 0 and can_trade_today and pivot_ok_s)
            if short_ok:
                if self.sl_type == "Previous Swing":
                    sl_base = prev_high
                elif self.sl_type == "Entry Candle":
                    sl_base = high
                else:
                    sl_base = prev_low * (1 + (self.sl_percent / 100))
                sl_calc = sl_base + self.sl_buf_pts + (prev_low * self.sl_buf_pct / 100)
                risk = sl_calc - prev_low
                if risk > 0:
                    self.short_sl = float(sl_calc)
                    rr = self.rr_short if self.sep_rr else self.rr_target
                    self.short_tp = float(prev_low - (risk * rr))
                    self.last_short_pivot = prev_low
                    st.entry("Short", st.short, stop=prev_low)
                else:
                    st.cancel("Short")
            else:
                st.cancel("Short")
            if self.high_active and not na(prev_high) and high >= prev_high:
                self.high_active = False
                self.prev_break_dir = 1
            if self.low_active and not na(prev_low) and low <= prev_low:
                self.low_active = False
                self.prev_break_dir = -1
        else:
            if self.high_active and not na(prev_high) and close > prev_high:
                self.high_active = False
                is_bos = self.prev_break_dir != -1
                if self.sl_type == "Previous Swing":
                    sl_base = prev_low
                elif self.sl_type == "Entry Candle":
                    sl_base = low
                else:
                    sl_base = close * (1 - (self.sl_percent / 100))
                sl_long = sl_base - self.sl_buf_pts - (close * self.sl_buf_pct / 100)
                candle_ok = (not self.use_strong) or strong_bull
                pivot_ok_l = na(self.last_long_pivot) or abs(prev_high - self.last_long_pivot) > mintick
                if self._entry_type_ok(is_bos) and candle_ok and not na(sl_long) and long_trend_ok and vwap_long_ok and can_trade_today and pivot_ok_l:
                    risk = close - sl_long
                    if risk > 0 and st.position_size <= 0:
                        self.long_sl = float(sl_long)
                        rr = self.rr_long if self.sep_rr else self.rr_target
                        self.long_tp = float(close + (risk * rr))
                        self.last_long_pivot = prev_high
                        st.entry("Long", st.long)
                self.prev_break_dir = 1
            if self.low_active and not na(prev_low) and close < prev_low:
                self.low_active = False
                is_bos = self.prev_break_dir != 1
                if self.sl_type == "Previous Swing":
                    sl_base = prev_high
                elif self.sl_type == "Entry Candle":
                    sl_base = high
                else:
                    sl_base = close * (1 + (self.sl_percent / 100))
                sl_short = sl_base + self.sl_buf_pts + (close * self.sl_buf_pct / 100)
                candle_ok = (not self.use_strong) or strong_bear
                pivot_ok_s = na(self.last_short_pivot) or abs(prev_low - self.last_short_pivot) > mintick
                if self._entry_type_ok(is_bos) and candle_ok and not na(sl_short) and short_trend_ok and vwap_short_ok and can_trade_today and pivot_ok_s:
                    risk = sl_short - close
                    if risk > 0 and st.position_size >= 0:
                        self.short_sl = float(sl_short)
                        rr = self.rr_short if self.sep_rr else self.rr_target
                        self.short_tp = float(close - (risk * rr))
                        self.last_short_pivot = prev_low
                        st.entry("Short", st.short)
                self.prev_break_dir = -1
        if st.position_size > 0 and not na(self.long_sl) and not na(self.long_tp):
            st.exit("Long Exit", "Long", stop=self.long_sl, limit=self.long_tp, comment_loss="SL", comment_profit="TP")
        if st.position_size < 0 and not na(self.short_sl) and not na(self.short_tp):
            st.exit("Short Exit", "Short", stop=self.short_sl, limit=self.short_tp, comment_loss="SL", comment_profit="TP")
        pos_just_opened = st.position_size != 0 and self.last_pos_size == 0
        if pos_just_opened:
            self.trades_today = self.trades_today + 1
        self.last_pos_size = float(st.position_size)
