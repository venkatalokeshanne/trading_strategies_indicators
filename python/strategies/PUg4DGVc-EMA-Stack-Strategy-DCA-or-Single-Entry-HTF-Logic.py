"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : EMA Stack Strategy (DCA or Single Entry, HTF Logic, Non Repainting)
Author       : cryptosquanch
Source URL   : https://www.tradingview.com/script/PUg4DGVc
Pine version : v6
Licence      : Mozilla Public License 2.0
Type         : strategy
Status       : FULL
Converted    : 2026-10-30 by Claude (pine-to-python skill)

Line-for-line translation (market orders at the next open). Four moving averages (SMA / EMA / RMA / WMA / VWMA, optionally from a higher timeframe) form a "stack"; when the fast-over-slow order has held for the chosen number of closes and no block window is active, a flat strategy opens a base position with the base quantity (the Pine passes the dollar input as the order quantity, so it is a quantity here too).
DCA / Grid mode adds entries when price reaches the next grid level (distance in units / percent / ATR, geometrically widened by the step scale, anchored at the first or the average entry) with sizes growing by the volume scale, up to the maximum entries and cash cap; the exit order is a limit at the average price plus the take-profit offset (or the last-DCA level plus an offset), optionally with a trailing stop, and the MA kill switch closes the position when the fast MA crosses the slow one against it.
Single Entry mode exits with an MA cross, a time stop, or an ATR / risk-reward / percent bracket with optional break-even and trailing stop.
Deviations from the original: none for the default settings. A higher-timeframe MA reads its price source by name from the chart's source input.
Not carried over: plots, labels, callouts, tables, help panel and every display-only input.
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, div, na, pmath, ta


def _clamp(x, lo, hi):
    return pmath.max(lo, pmath.min(hi, x))


class EmaStackStrategy(Script):
    TITLE = "EMA Stack Strategy (DCA or Single Entry, HTF Logic, Non Repainting)"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(pyramiding=50, initial_capital=100000, default_qty_type="cash", default_qty_value=1000, commission_type="percent", commission_value=0, slippage=0)
    SOURCE = {"id": "PUg4DGVc", "author": "cryptosquanch", "licence": "Mozilla Public License 2.0", "url": "https://www.tradingview.com/script/PUg4DGVc"}

    def init(self):
        i = self.input
        ma_types = ["SMA", "EMA", "SMMA (RMA)", "WMA", "VWMA"]
        g = "🧭 MODE"
        self.trade_mode = i.string("DCA / Grid", "Trading mode", options=["DCA / Grid", "Single Entry"], group=g)
        g = "📐 UNITS"
        self.unit_mode = i.string("Pips (FX)", "Unit mode", options=["Ticks", "Points", "Pips (FX)"], group=g)
        self.point_size = i.float(0.01, "Point size (if Points)", step=0.0001, group=g)
        self.pip_size_fx = i.float(0.01, "Pip size (if Pips FX)", step=0.0001, group=g)
        g = "📈 MA SETTINGS"
        self.ma_tf_mode = i.string("Current Chart", "MA logic timeframe", options=["Current Chart", "Higher TF"], group=g)
        self.ma_tf = i.timeframe("D", "Higher TF", group=g)
        self.ma1_type = i.string("EMA", "MA #1 Type", options=ma_types, group=g, inline="m1")
        self.ma1_source = i.source(self.close, "", group=g, inline="m1")
        self.ma1_length = i.int(10, "", minval=1, group=g, inline="m1")
        self.ma2_type = i.string("EMA", "MA #2 Type", options=ma_types, group=g, inline="m2")
        self.ma2_source = i.source(self.close, "", group=g, inline="m2")
        self.ma2_length = i.int(25, "", minval=1, group=g, inline="m2")
        self.use_ma3 = i.bool(True, "Use MA #3 filter", group=g, inline="m3")
        self.ma3_type = i.string("EMA", "", options=ma_types, group=g, inline="m3")
        self.ma3_source = i.source(self.close, "", group=g, inline="m3")
        self.ma3_length = i.int(50, "", minval=1, group=g, inline="m3")
        self.use_ma4 = i.bool(True, "Use MA #4 filter", group=g, inline="m4")
        self.ma4_type = i.string("EMA", "", options=ma_types, group=g, inline="m4")
        self.ma4_source = i.source(self.close, "", group=g, inline="m4")
        self.ma4_length = i.int(100, "", minval=1, group=g, inline="m4")
        self.atr_len = i.int(14, "ATR length", minval=1, group="📉 ATR SETTINGS")
        self.stack_hold_closes = i.int(0, "Enter after stack holds X confirmed closes", minval=0, group="✅ ENTRY RULES")
        g = "🧱 DCA / GRID SETTINGS — used only if DCA mode"
        self.dca_sizing_mode = i.string("Auto Grid", "DCA sizing mode", options=["Auto Grid", "Manual Ladder"], group=g)
        self.max_entries = i.int(15, "Max total entries (1..25)", minval=1, maxval=25, group=g)
        self.base_cash = i.float(1000, "Base order size ($)", step=50, minval=0, group=g)
        self.max_total_cash = i.float(15000, "Max total position cash ($ cap)", step=100, minval=0, group=g)
        self.dca_mode = i.string("Units", "DCA distance mode", options=["Units", "Percent", "ATR"], group=g)
        self.base_dca_units = i.float(25.0, "Base interval (Units)", step=0.1, group=g)
        self.base_dca_pct = i.float(0.25, "Base interval (%)", step=0.01, group=g)
        self.base_dca_atr_m = i.float(1.0, "Base interval (ATR mult)", step=0.1, group=g)
        self.step_scale = i.float(1.12, "Step scale (spacing growth)", step=0.01, minval=0.1, group=g)
        self.volume_scale = i.float(1.40, "Volume scale (size growth)", step=0.01, minval=0.1, group=g)
        self.anchor_mode = i.string("First Entry", "DCA anchor mode", options=["First Entry", "Average Entry"], group=g)
        self.allow_dca_adds = i.bool(True, "Enable DCA adds", group=g)
        g = "🧰 MANUAL LADDER SIZES ($) — used only if Manual Ladder"
        self.manual = [i.float(1000, "Entry #%d ($)" % (k + 1), step=50, group=g) for k in range(25)]
        g = "🏁 EXITS (DCA TP/TRAIL + SINGLE EXIT MODES)"
        self.tp_mode = i.string("Units", "DCA take profit mode (Avg BE ± offset)", options=["Units", "Percent", "ATR"], group=g)
        self.tp_units = i.float(100.0, "TP after breakeven (Units)", step=0.1, group=g)
        self.tp_pct = i.float(0.10, "TP after breakeven (%)", step=0.01, group=g)
        self.tp_atr_m = i.float(1.0, "TP after breakeven (ATR mult)", step=0.1, group=g)
        self.trail_enable = i.bool(False, "Enable DCA trailing stop (default OFF)", group=g)
        self.trail_act_mode = i.string("Units", "DCA trail activation mode", options=["Units", "Percent", "ATR"], group=g)
        self.trail_act_u = i.float(100.0, "Activate after profit (Units)", step=0.1, group=g)
        self.trail_act_pct = i.float(0.10, "Activate after profit (%)", step=0.01, group=g)
        self.trail_act_atr_m = i.float(1.0, "Activate after profit (ATR mult)", step=0.1, group=g)
        self.trail_mode = i.string("Units", "DCA trail distance mode", options=["Units", "Percent", "ATR"], group=g)
        self.trail_units = i.float(50.0, "Trail distance (Units)", step=0.1, group=g)
        self.trail_pct = i.float(0.05, "Trail distance (%)", step=0.01, group=g)
        self.trail_atr_m = i.float(0.5, "Trail distance (ATR mult)", step=0.1, group=g)
        self.dca_exit_type = i.string("BE TP (Current)", "DCA exit type", options=["BE TP (Current)", "After Last DCA (Offset)"], group=g)
        self.dca_disable_ma_kill = i.bool(False, "Disable MA kill switch (DCA mode)", group=g)
        self.dca_last_exit_mode = i.string("Units", "Last DCA exit offset mode", options=["Units", "Percent"], group=g)
        self.dca_last_exit_units = i.float(100.0, "Exit offset after last DCA (Units)", step=0.1, group=g)
        self.dca_last_exit_pct = i.float(0.10, "Exit offset after last DCA (%)", step=0.01, group=g)
        self.single_exit_type = i.string("ATR Bracket", "Single entry exit type (Single mode only)", options=["MA Cross", "ATR Bracket", "R:R Bracket", "Percent Bracket", "Time Stop"], group=g)
        self.atr_stop_m = i.float(1.5, "ATR Stop Mult", step=0.1, group=g)
        self.atr_tp_m = i.float(3.0, "ATR TP Mult", step=0.1, group=g)
        self.rr_stop_method = i.string("ATR", "R:R Stop Method", options=["ATR", "Swing"], group=g)
        self.rr_atr_stop_m = i.float(1.5, "R:R ATR Stop Mult (if ATR)", step=0.1, group=g)
        self.swing_lb = i.int(20, "Swing Lookback (if Swing)", minval=1, group=g)
        self.swing_buf_u = i.float(0.0, "Swing Buffer (Units)", step=0.1, group=g)
        self.rr_ratio = i.float(2.0, "Risk:Reward (e.g., 2.0)", step=0.1, minval=0.1, group=g)
        self.stop_pct_single = i.float(1.0, "Stop (%)", step=0.1, minval=0.01, group=g)
        self.tp_pct_single = i.float(2.0, "Take Profit (%)", step=0.1, minval=0.01, group=g)
        self.time_stop_bars = i.int(50, "Time Stop (bars)", minval=1, group=g)
        self.be_enable = i.bool(False, "Enable Break-even move (Single mode)", group=g)
        self.be_trig_mode = i.string("ATR", "BE Trigger Mode", options=["Units", "Percent", "ATR"], group=g)
        self.be_trig_u = i.float(50.0, "BE Trigger (Units)", step=0.1, group=g)
        self.be_trig_pct = i.float(0.5, "BE Trigger (%)", step=0.1, group=g)
        self.be_trig_atr_m = i.float(1.0, "BE Trigger (ATR mult)", step=0.1, group=g)
        self.be_offset_u = i.float(0.0, "BE Stop Offset (Units)", step=0.1, group=g)
        self.se_trail_enable = i.bool(False, "Enable Single Entry Trailing Stop", group=g)
        self.se_trail_act_mode = i.string("ATR", "SE trail activation mode", options=["Units", "Percent", "ATR"], group=g)
        self.se_trail_act_u = i.float(50.0, "SE trail activate after profit (Units)", step=0.1, group=g)
        self.se_trail_act_pct = i.float(0.5, "SE trail activate after profit (%)", step=0.1, group=g)
        self.se_trail_act_atr_m = i.float(1.0, "SE trail activate after profit (ATR mult)", step=0.1, group=g)
        self.se_trail_dist_mode = i.string("ATR", "SE trail distance mode", options=["Units", "Percent", "ATR"], group=g)
        self.se_trail_dist_u = i.float(25.0, "SE trail distance (Units)", step=0.1, group=g)
        self.se_trail_dist_pct = i.float(0.25, "SE trail distance (%)", step=0.01, group=g)
        self.se_trail_dist_atr_m = i.float(0.5, "SE trail distance (ATR mult)", step=0.1, group=g)
        g = "⏰ NO-NEW-TRADE WINDOWS"
        self.tz_opt = i.string("America/New_York", "Time zone", options=["America/New_York", "America/Chicago", "America/Denver", "America/Los_Angeles", "UTC", "Etc/UTC", "Europe/London", "Europe/Paris", "Asia/Tokyo", "Asia/Hong_Kong", "Asia/Singapore", "Australia/Sydney"], group=g)
        self.w1_en = i.bool(False, "Block window #1", group=g, inline="w1")
        self.w1_st = i.string("16:45", "Start", group=g, inline="w1")
        self.w1_en_t = i.string("18:15", "End", group=g, inline="w1")
        self.w2_en = i.bool(False, "Block window #2", group=g, inline="w2")
        self.w2_st = i.string("00:00", "Start", group=g, inline="w2")
        self.w2_en_t = i.string("00:00", "End", group=g, inline="w2")
        self.w3_en = i.bool(False, "Block window #3", group=g, inline="w3")
        self.w3_st = i.string("00:00", "Start", group=g, inline="w3")
        self.w3_en_t = i.string("00:00", "End", group=g, inline="w3")
        self.block_dca_during_windows = i.bool(False, "Also block DCA adds during windows", group=g)
        self.stack_count_long = 0
        self.stack_count_short = 0
        self.first_entry_price = NA
        self.last_dca_price = NA
        self.entries_so_far = 0
        self.planned_cash_used = 0.0
        self.trail_extreme = NA
        self.trail_active = False
        self.bars_in_trade = 0
        self.be_armed = False
        self.se_trail_extreme = NA
        self.se_trail_active = False

    # ── helpers (Pine user functions)
    @staticmethod
    def _hhmm(s):
        parts = s.split(":")
        return (int(parts[0]) if len(parts) > 0 else 0) * 60 + (int(parts[1]) if len(parts) > 1 else 0)

    def _in_window(self, enabled, start, end):
        if not enabled:
            return False
        now = self.hour(tz=self.tz_opt) * 60 + self.minute(tz=self.tz_opt)
        st, en = self._hhmm(start), self._hhmm(end)
        return (now >= st and now <= en) if st <= en else (now >= st or now <= en)

    @staticmethod
    def _dist(mode, anchor, unit, units, pct, atr, atr_m):
        if mode == "Units":
            return units * unit
        if mode == "Percent":
            return anchor * (pct / 100.0)
        if mode == "ATR":
            return atr * atr_m
        return NA

    @staticmethod
    def _ma(src, length, typ):
        if typ == "SMA":
            return ta.sma(src, length)
        if typ == "EMA":
            return ta.ema(src, length)
        if typ == "SMMA (RMA)":
            return ta.rma(src, length)
        if typ == "WMA":
            return ta.wma(src, length)
        if typ == "VWMA":
            return ta.vwma(src, length)
        return NA

    def _view_src(self, v, src):
        return getattr(v, src.name)

    def on_bar(self):
        st = self.strategy
        high, low, close = self.high, self.low, self.close
        h_pos = self.H("pos")
        pos_prev = h_pos[1]
        tick = self.syminfo.mintick
        unit_size = tick if self.unit_mode == "Ticks" else self.point_size if self.unit_mode == "Points" else self.pip_size_fx if self.unit_mode == "Pips (FX)" else tick
        chart = self.ma_tf_mode == "Current Chart"
        if chart:
            logic_update = True
            ma1 = self._ma(self.ma1_source, self.ma1_length, self.ma1_type)
            ma2 = self._ma(self.ma2_source, self.ma2_length, self.ma2_type)
            ma3 = self._ma(self.ma3_source, self.ma3_length, self.ma3_type)
            ma4 = self._ma(self.ma4_source, self.ma4_length, self.ma4_type)
            atr = ta.atr(self.atr_len)
        else:
            logic_update = ta.change(self.time_fn(self.ma_tf)) != 0
            ma1 = self.security(None, self.ma_tf, lambda v: self._ma(self._view_src(v, self.ma1_source), self.ma1_length, self.ma1_type))
            ma2 = self.security(None, self.ma_tf, lambda v: self._ma(self._view_src(v, self.ma2_source), self.ma2_length, self.ma2_type))
            ma3 = self.security(None, self.ma_tf, lambda v: self._ma(self._view_src(v, self.ma3_source), self.ma3_length, self.ma3_type))
            ma4 = self.security(None, self.ma_tf, lambda v: self._ma(self._view_src(v, self.ma4_source), self.ma4_length, self.ma4_type))
            atr = self.security(None, self.ma_tf, lambda v: ta.atr(self.atr_len))
        use_ma4_eff = self.use_ma4 and self.use_ma3
        block_new = self._in_window(self.w1_en, self.w1_st, self.w1_en_t) or self._in_window(self.w2_en, self.w2_st, self.w2_en_t) or self._in_window(self.w3_en, self.w3_st, self.w3_en_t)

        stack_long = (ma1 > ma2) and ((not self.use_ma3) or (ma2 > ma3)) and ((not use_ma4_eff) or (ma3 > ma4))
        stack_short = (ma1 < ma2) and ((not self.use_ma3) or (ma2 < ma3)) and ((not use_ma4_eff) or (ma3 < ma4))
        if logic_update:
            self.stack_count_long = self.stack_count_long + 1 if stack_long else 0
            self.stack_count_short = self.stack_count_short + 1 if stack_short else 0
        ready_long = self.stack_count_long >= (self.stack_hold_closes + 1)
        ready_short = self.stack_count_short >= (self.stack_hold_closes + 1)

        pos = st.position_size
        in_long, in_short, flat = pos > 0, pos < 0, pos == 0
        new_open = (pos != 0 and pos_prev == 0)
        position_closed = (pos == 0 and pos_prev != 0)
        base_cash_eff = self.manual[0] if self.dca_sizing_mode == "Manual Ladder" else self.base_cash
        if new_open:
            self.first_entry_price = float(st.position_avg_price)
            self.last_dca_price = float(st.position_avg_price)
            self.entries_so_far = 1
            self.planned_cash_used = base_cash_eff
        if flat:
            self.first_entry_price = NA
            self.last_dca_price = NA
            self.entries_so_far = 0
            self.planned_cash_used = 0.0

        cross_dn = ta.crossunder(ma1, ma2)
        cross_up = ta.crossover(ma1, ma2)
        kill_long = in_long and (ma1 < ma2)
        kill_short = in_short and (ma1 > ma2)
        can_enter = not block_new
        base_long = logic_update and flat and ready_long and can_enter
        base_short = logic_update and flat and ready_short and can_enter
        if base_long and base_cash_eff > 0:
            st.entry("Long", st.long, qty=base_cash_eff)
        if base_short and base_cash_eff > 0:
            st.entry("Short", st.short, qty=base_cash_eff)

        can_use_dca = self.trade_mode == "DCA / Grid"
        anchor = self.first_entry_price if self.anchor_mode == "First Entry" else st.position_avg_price if self.anchor_mode == "Average Entry" else NA
        can_dca_now = (not block_new) if self.block_dca_during_windows else True
        can_add = can_use_dca and self.allow_dca_adds and can_dca_now and pos != 0 and self.entries_so_far >= 1 and self.entries_so_far < self.max_entries and not na(anchor)
        next_level = NA
        if can_add:
            base = self._dist(self.dca_mode, anchor, unit_size, self.base_dca_units, self.base_dca_pct, atr, self.base_dca_atr_m)
            k = self.entries_so_far
            if k <= 0:
                next_dist = 0.0
            else:
                next_dist = base * k if self.step_scale == 1.0 else div(base * (pmath.pow(self.step_scale, k) - 1.0), self.step_scale - 1.0)
            next_level = (anchor - next_dist) if in_long else (anchor + next_dist)
        touch_next = can_add and not na(next_level) and ((in_long and low <= next_level) or (in_short and high >= next_level))
        auto_next = self.base_cash * pmath.pow(self.volume_scale, self.entries_so_far)
        manual_next = self.manual[self.entries_so_far] if 0 <= self.entries_so_far < 25 else 0.0
        next_raw = manual_next if self.dca_sizing_mode == "Manual Ladder" else auto_next
        room_cash = self.max_total_cash - self.planned_cash_used
        next_cash = _clamp(next_raw, 0.0, room_cash)
        if touch_next and next_cash > 0:
            self.last_dca_price = float(next_level)
            if in_long:
                st.entry("Long", st.long, qty=next_cash)
            if in_short:
                st.entry("Short", st.short, qty=next_cash)
            self.entries_so_far += 1
            self.planned_cash_used += next_cash

        avg = st.position_avg_price
        tp_offset = self._dist(self.tp_mode, avg, unit_size, self.tp_units, self.tp_pct, atr, self.tp_atr_m)
        tp_dca = (avg + tp_offset) if in_long else (avg - tp_offset) if in_short else NA
        reached_last = can_use_dca and pos != 0 and self.entries_so_far >= self.max_entries and not na(self.last_dca_price)
        last_off = self.dca_last_exit_units * unit_size if self.dca_last_exit_mode == "Units" else self.last_dca_price * (self.dca_last_exit_pct / 100.0) if self.dca_last_exit_mode == "Percent" else NA
        tp_after_last = ((self.last_dca_price + last_off) if in_long else (self.last_dca_price - last_off)) if reached_last else NA

        if new_open or pos == 0:
            self.trail_extreme = NA
            self.trail_active = False
        act_off = self._dist(self.trail_act_mode, avg, unit_size, self.trail_act_u, self.trail_act_pct, atr, self.trail_act_atr_m)
        trail_dist = self._dist(self.trail_mode, avg, unit_size, self.trail_units, self.trail_pct, atr, self.trail_atr_m)
        if self.trail_enable and pos != 0 and can_use_dca:
            if in_long:
                self.trail_extreme = float(high) if na(self.trail_extreme) else pmath.max(self.trail_extreme, high)
                if not self.trail_active and (self.trail_extreme - avg) >= act_off:
                    self.trail_active = True
            if in_short:
                self.trail_extreme = float(low) if na(self.trail_extreme) else pmath.min(self.trail_extreme, low)
                if not self.trail_active and (avg - self.trail_extreme) >= act_off:
                    self.trail_active = True
        trail_stop = ((self.trail_extreme - trail_dist) if in_long else (self.trail_extreme + trail_dist)) if (self.trail_enable and self.trail_active and pos != 0 and can_use_dca) else NA

        if new_open:
            self.bars_in_trade = 0
        if pos != 0:
            self.bars_in_trade += 1
        if pos == 0:
            self.bars_in_trade = 0

        swing_low = ta.lowest(low, self.swing_lb)
        swing_high = ta.highest(high, self.swing_lb)
        if self.rr_stop_method == "ATR":
            rr_stop = (avg - atr * self.rr_atr_stop_m) if in_long else (avg + atr * self.rr_atr_stop_m)
        else:
            rr_stop = (swing_low - self.swing_buf_u * unit_size) if in_long else (swing_high + self.swing_buf_u * unit_size)
        rr_risk = (avg - rr_stop) if in_long else (rr_stop - avg) if in_short else NA
        rr_tp = (avg + rr_risk * self.rr_ratio) if in_long else (avg - rr_risk * self.rr_ratio) if in_short else NA
        atr_stop = (avg - atr * self.atr_stop_m) if in_long else (avg + atr * self.atr_stop_m) if in_short else NA
        atr_tp = (avg + atr * self.atr_tp_m) if in_long else (avg - atr * self.atr_tp_m) if in_short else NA
        pct_stop = (avg * (1.0 - self.stop_pct_single / 100.0)) if in_long else (avg * (1.0 + self.stop_pct_single / 100.0)) if in_short else NA
        pct_tp = (avg * (1.0 + self.tp_pct_single / 100.0)) if in_long else (avg * (1.0 - self.tp_pct_single / 100.0)) if in_short else NA

        be_trig = self._dist(self.be_trig_mode, avg, unit_size, self.be_trig_u, self.be_trig_pct, atr, self.be_trig_atr_m)
        if new_open or pos == 0:
            self.be_armed = False
        if self.trade_mode == "Single Entry" and self.be_enable and pos != 0:
            if in_long and not self.be_armed and (high - avg) >= be_trig:
                self.be_armed = True
            if in_short and not self.be_armed and (avg - low) >= be_trig:
                self.be_armed = True
        be_stop = ((avg + self.be_offset_u * unit_size) if in_long else (avg - self.be_offset_u * unit_size)) if (self.be_armed and pos != 0) else NA

        if new_open or pos == 0:
            self.se_trail_extreme = NA
            self.se_trail_active = False
        se_act = self._dist(self.se_trail_act_mode, avg, unit_size, self.se_trail_act_u, self.se_trail_act_pct, atr, self.se_trail_act_atr_m)
        se_dist = self._dist(self.se_trail_dist_mode, avg, unit_size, self.se_trail_dist_u, self.se_trail_dist_pct, atr, self.se_trail_dist_atr_m)
        if self.trade_mode == "Single Entry" and self.se_trail_enable and pos != 0:
            if in_long:
                self.se_trail_extreme = float(high) if na(self.se_trail_extreme) else pmath.max(self.se_trail_extreme, high)
                if not self.se_trail_active and (self.se_trail_extreme - avg) >= se_act:
                    self.se_trail_active = True
            if in_short:
                self.se_trail_extreme = float(low) if na(self.se_trail_extreme) else pmath.min(self.se_trail_extreme, low)
                if not self.se_trail_active and (avg - self.se_trail_extreme) >= se_act:
                    self.se_trail_active = True
        se_trail_stop = ((self.se_trail_extreme - se_dist) if in_long else (self.se_trail_extreme + se_dist)) if (self.trade_mode == "Single Entry" and self.se_trail_enable and self.se_trail_active and pos != 0) else NA

        if self.trade_mode == "DCA / Grid":
            dca_limit = tp_after_last if self.dca_exit_type == "After Last DCA (Offset)" else tp_dca
            stop = trail_stop if (self.trail_enable and self.trail_active) else NA
            if in_long:
                st.exit("X", from_entry="Long", limit=dca_limit, stop=stop)
            if in_short:
                st.exit("X", from_entry="Short", limit=dca_limit, stop=stop)
            use_kill = (not self.dca_disable_ma_kill) and (self.dca_exit_type != "After Last DCA (Offset)")
            if use_kill:
                if kill_long:
                    st.close("Long")
                if kill_short:
                    st.close("Short")

        if self.trade_mode == "Single Entry" and pos != 0:
            if self.se_trail_enable and self.se_trail_active and not na(se_trail_stop):
                st.exit("SE-T", from_entry="Long" if in_long else "Short", stop=se_trail_stop)
            if self.single_exit_type == "MA Cross":
                if in_long and cross_dn:
                    st.close("Long")
                if in_short and cross_up:
                    st.close("Short")
            if self.single_exit_type == "Time Stop":
                if self.bars_in_trade >= self.time_stop_bars:
                    st.close("Long" if in_long else "Short")
            bracket = None
            if self.single_exit_type == "ATR Bracket":
                bracket = (atr_stop, atr_tp)
            if self.single_exit_type == "R:R Bracket":
                bracket = (rr_stop, rr_tp)
            if self.single_exit_type == "Percent Bracket":
                bracket = (pct_stop, pct_tp)
            if bracket is not None:
                stop_p, lim_p = bracket
                if self.be_enable and self.be_armed and not na(be_stop):
                    stop_p = pmath.max(stop_p, be_stop) if in_long else pmath.min(stop_p, be_stop)
                st.exit("SE-B", from_entry="Long" if in_long else "Short", stop=stop_p, limit=lim_p)

        h_pos.set(pos)
