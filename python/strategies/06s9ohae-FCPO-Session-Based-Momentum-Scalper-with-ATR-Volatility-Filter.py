"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : FCPO Session-Based Momentum Scalper with ATR Volatility Filter
Author       : nusser85
Source URL   : https://www.tradingview.com/script/06s9ohae-FCPO-Session-Based-Momentum-Scalper-with-ATR-Volatility-Filter
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-29 by Claude (pine-to-python skill)

Line-for-line translation (process_orders_on_close: market orders fill at the signal close). A momentum scalper: inside the morning / noon sessions of the chosen time zone on an allowed weekday, outside the excluded danger zones, a bar whose range ATR (SMA of the true range) lies between the floor and the limit and whose body passes the minimum ticks and body-to-range ratio opens a position in its own direction. The fixed tick take-profit / stop-loss come from the preset (or the manual inputs) and are issued while the trade is open; a trade is closed after the time-exit bar count and at the session end handling chosen. A daily trade limit, a monthly profit lock (and optional loss limit), per-weekday switches, an optional automatic pivot-trendline breakout filter and a one-day pause after two consecutive losing trades gate new entries.

Deviations from the original: none. The "last closed trade" tick result uses the trade's entry / exit price with the direction recorded when the position was last opened from flat (as in the source).
Not carried over: the vertical session lines, backgrounds, circuit-breaker labels, ATR envelope, 200 SMA line, the drawn trendlines, the early-momentum flags and the dashboard (display only).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, div, na, pmath, ta

MONDAY, TUESDAY, WEDNESDAY, THURSDAY, FRIDAY = 2, 3, 4, 5, 6

PRESETS = {
    "Setup A (SL 35) - M15 Baseline": (12, 35, 12, 0.75),
    "Setup B (SL 30) - M15 Baseline": (12, 30, 12, 0.75),
    "Setup C (Max Profit) - M5 Optimized": (22, 60, 11, 0.75),
    "Setup D (Peak Efficiency) - M5 Optimized": (19, 44, 11, 0.75),
}


class FcpoSessionScalper(Script):
    TITLE = "FCPO God Mode v5 🛡️ (ATR Volatility Floor & Friday PM Shield)"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(initial_capital=12000, default_qty_type="fixed", default_qty_value=1, commission_type="percent", commission_value=0.0, process_orders_on_close=True)
    SOURCE = {"id": "06s9ohae", "author": "nusser85", "licence": "not stated",
              "url": "https://www.tradingview.com/script/06s9ohae-FCPO-Session-Based-Momentum-Scalper-with-ATR-Volatility-Filter"}

    def init(self):
        i = self.input
        g = "══════ Momentum Scalper Settings ══════"
        self.setup_mode = i.string("Setup C (Max Profit) - M5 Optimized", "God Mode Preset", group=g,
                                   options=["Custom (Use Manual Inputs)", "Setup A (SL 35) - M15 Baseline", "Setup B (SL 30) - M15 Baseline",
                                            "Setup C (Max Profit) - M5 Optimized", "Setup D (Peak Efficiency) - M5 Optimized"])
        self.tp_input = i.int(12, "Manual Take Profit (Ticks)", group=g)
        self.sl_input = i.int(30, "Manual Stop Loss (Ticks)", group=g)
        self.atr_len = i.int(14, "ATR Period", group=g)
        self.atr_limit = i.float(12.0, "ATR Limit (Ticks)", group=g)
        self.atr_floor = i.float(5.0, "ATR Floor (Ticks)", group=g)
        self.body_ticks_in = i.int(12, "Minimum Body Size (Ticks)", group=g)
        self.body_ratio_in = i.float(0.75, "Min Body-to-Range Ratio", group=g)
        self.en_time_exit = i.bool(True, "Enable Time Exit Limit", group=g)
        self.time_exit_bars = i.int(15, "Time Exit Bars", group=g)
        self.en_daily = i.bool(True, "Enable Daily Trade Limit", group=g)
        self.max_per_day = i.int(1, "Max Trades Per Day", group=g)
        self.session_exit = i.string("Carry Through Lunch", "Session Exit Handling", group=g,
                                     options=["TradingView Buggy Baseline", "Exit at 12:30 Sharp", "Carry Through Lunch"])
        g = "══════ Session & Timing Settings ══════"
        self.tz = i.string("Asia/Kuala_Lumpur", "Timezone", group=g)
        self.sess_morning = i.session("1030-1230", "Morning Session", group=g)
        self.sess_noon = i.session("1430-1800", "Noon Session", group=g)
        self.sess_night = i.session("2100-2330", "Night Session (Visual Only)", group=g)
        self.en_eod_exit = i.bool(True, "Enable Force EOD Exit (17:55)", group=g)
        g = "══════ Day Filter Settings ══════"
        self.trade_mon = i.bool(True, "✅ Trade on Monday   (RM +10,300 | WR 64.6%)", group=g)
        self.trade_tue = i.bool(False, "⚠️ Trade on Tuesday  (Not tested alone)", group=g)
        self.trade_wed = i.bool(True, "🏆 Trade on Wednesday (RM +16,200 | WR 67.9%)", group=g)
        self.trade_thu = i.bool(False, "❌ Trade on Thursday (Weak — Disyorkan: OFF)", group=g)
        self.trade_fri = i.bool(False, "⚠️ Trade on Friday   (Volatile — optional)", group=g)
        g = "══════ Direction Filter Settings ══════"
        self.direction = i.string("Both", "Allow Trade Direction", group=g, options=["Both", "Short Only", "Long Only"])
        g = "══════ Auto Trendline Breakout Filter ══════"
        self.en_trendline = i.bool(False, "Enable Auto Trendline Filter", group=g)
        self.pivot_len = i.int(5, "Pivot Lookback Length", group=g, minval=2)
        g = "══════ Precision Time Exclusions ══════"
        self.excl_whipsaw = i.bool(True, "Exclude Whipsaw Zone (15:30-16:00)", group=g)
        self.excl_eod = i.bool(True, "Exclude EOD Danger Zone (17:30-18:00)", group=g)
        self.excl_fri_pm = i.bool(True, "Exclude Friday PM Whipsaw (17:00-18:00)", group=g)
        g = "══════ Monthly Profit Lock Settings ══════"
        self.en_monthly = i.bool(True, "Enable Monthly Profit Limit", group=g)
        self.monthly_max = i.int(100, "Monthly Profit Target (Ticks)", group=g)
        self.en_monthly_loss = i.bool(False, "Enable Monthly Loss Limit", group=g)
        self.monthly_min = i.int(-120, "Monthly Loss Limit (Ticks)", group=g)
        self.monthly_ticks = 0.0
        self.current_month = NA
        self.consec_losses = 0
        self.paused_until = 0
        self.trades_today = 0
        self.last_trade_count = 0
        self.my_entry_price = NA
        self.my_dir = 0
        self.entry_tp = NA
        self.entry_sl = NA
        self.entry_bar = NA
        self.ph1_val = self.ph2_val = self.pl1_val = self.pl2_val = NA
        self.ph1_time = self.ph2_time = self.pl1_time = self.pl2_time = NA

    def on_bar(self):
        st = self.strategy
        close, open_, high, low = self.close, self.open, self.high, self.low
        mintick = self.syminfo.mintick
        tfp = self.timeframe.period
        t_h = self.H("time")
        time_back = t_h[self.pivot_len]
        t_h.set(self.time)
        ph = ta.pivothigh(high, self.pivot_len, self.pivot_len)
        pl = ta.pivotlow(low, self.pivot_len, self.pivot_len)
        if not na(ph):
            self.ph2_val, self.ph2_time = self.ph1_val, self.ph1_time
            self.ph1_val, self.ph1_time = float(ph), time_back
        if not na(pl):
            self.pl2_val, self.pl2_time = self.pl1_val, self.pl1_time
            self.pl1_val, self.pl1_time = float(pl), time_back

        def line_val(t1, p1, t2, p2, t):
            if na(t1) or na(t2) or t1 == t2:
                return NA
            return p1 + div(p2 - p1, t2 - t1) * (t - t1)

        valid_upper = not na(self.ph1_time) and not na(self.ph2_time) and self.ph1_time != self.ph2_time
        valid_lower = not na(self.pl1_time) and not na(self.pl2_time) and self.pl1_time != self.pl2_time
        upper_val = line_val(self.ph2_time, self.ph2_val, self.ph1_time, self.ph1_val, self.time)
        lower_val = line_val(self.pl2_time, self.pl2_val, self.pl1_time, self.pl1_val, self.time)
        tl_long_ok = (not self.en_trendline) or (not valid_upper) or (not na(upper_val) and close > upper_val)
        tl_short_ok = (not self.en_trendline) or (not valid_lower) or (not na(lower_val) and close < lower_val)
        dow = self.dayofweek()
        is_active_day = ((dow == MONDAY and self.trade_mon) or (dow == TUESDAY and self.trade_tue) or (dow == WEDNESDAY and self.trade_wed)
                         or (dow == THURSDAY and self.trade_thu) or (dow == FRIDAY and self.trade_fri))
        in_morning = not na(self.time_fn(tfp, self.sess_morning, self.tz))
        in_noon = not na(self.time_fn(tfp, self.sess_noon, self.tz))
        mh, nh = self.H("in_morning"), self.H("in_noon")
        in_morning_1 = (not na(mh[1])) and bool(mh[1])
        in_noon_1 = (not na(nh[1])) and bool(nh[1])
        mh.set(in_morning)
        nh.set(in_noon)
        in_session = in_morning or in_noon
        is_whipsaw = not na(self.time_fn(tfp, "1530-1600", self.tz))
        is_eod = not na(self.time_fn(tfp, "1730-1800", self.tz))
        is_fri_pm = dow == FRIDAY and not na(self.time_fn(tfp, "1700-1800", self.tz))
        in_excluded = (self.excl_whipsaw and is_whipsaw) or (self.excl_eod and is_eod) or (self.excl_fri_pm and is_fri_pm)
        body = abs(close - open_)
        rng = high - low
        c_h = self.H("close")
        close_1 = c_h[1]
        c_h.set(close)
        tr_val = pmath.max(high - low, pmath.max(abs(high - close_1), abs(low - close_1)))
        atr_val = ta.sma(tr_val, self.atr_len)
        body_ticks = div(body, mintick)
        atr_ticks = div(atr_val, mintick)
        body_ratio = div(body, rng) if rng > 0 else 0
        if self.setup_mode in PRESETS:
            tp_ticks, sl_ticks, cur_body_ticks, cur_body_ratio = PRESETS[self.setup_mode]
        else:
            tp_ticks, sl_ticks, cur_body_ticks, cur_body_ratio = self.tp_input, self.sl_input, self.body_ticks_in, self.body_ratio_in
        pos_h = self.H("pos")
        pos_1 = pos_h[1]
        pos_h.set(st.position_size)
        pos_prev0 = (not na(pos_1)) and pos_1 == 0
        pos_prev_nz = (not na(pos_1)) and pos_1 != 0
        if self.barstate.isfirst:
            self.last_trade_count = st.closedtrades + st.opentrades
        if ta.change(self.time_fn("D")) != 0:
            self.trades_today = 0
        count = st.closedtrades + st.opentrades
        if count > self.last_trade_count:
            self.trades_today = self.trades_today + 1
            self.last_trade_count = count
        if pos_prev0 and st.position_size != 0:
            self.my_entry_price = float(st.position_avg_price)
            self.my_dir = 1 if st.position_size > 0 else -1
        mo_h = self.H("month")
        month_1 = mo_h[1]
        month = self.month()
        mo_h.set(month)
        is_new_month = month != month_1 or na(self.current_month)
        if is_new_month:
            self.monthly_ticks = 0.0
            self.current_month = month
        trade_closed = pos_prev_nz and st.position_size == 0
        last_ticks = 0.0
        if trade_closed:
            last_idx = st.closedtrades - 1
            if last_idx >= 0:
                entry_p = st.closedtrades_entry_price(last_idx)
                exit_p = st.closedtrades_exit_price(last_idx)
                if self.my_dir == 1:
                    last_ticks = div(exit_p - entry_p, mintick)
                else:
                    last_ticks = div(entry_p - exit_p, mintick)
            else:
                if self.my_dir == 1:
                    last_ticks = div(close - self.my_entry_price, mintick)
                else:
                    last_ticks = div(self.my_entry_price - close, mintick)
            self.monthly_ticks = self.monthly_ticks + last_ticks
            if last_ticks < 0:
                self.consec_losses = self.consec_losses + 1
            else:
                self.consec_losses = 0
            if self.consec_losses >= 2:
                self.paused_until = self.time + 24 * 60 * 60 * 1000
                self.consec_losses = 0
        monthly_cap = self.en_monthly and self.monthly_ticks >= self.monthly_max
        monthly_loss_hit = self.en_monthly_loss and self.monthly_ticks <= self.monthly_min
        is_paused = self.time < self.paused_until
        dir_long_ok = self.direction == "Both" or self.direction == "Long Only"
        dir_short_ok = self.direction == "Both" or self.direction == "Short Only"
        daily_ok = (not self.en_daily) or self.trades_today < self.max_per_day
        setup_ok = in_session and is_active_day and not is_paused and not in_excluded and not monthly_cap and not monthly_loss_hit and daily_ok
        vol_ok = atr_ticks <= self.atr_limit and atr_ticks >= self.atr_floor
        mom_ok = body_ratio >= cur_body_ratio and body_ticks >= cur_body_ticks
        long_signal = setup_ok and vol_ok and mom_ok and close > open_ and dir_long_ok and tl_long_ok
        short_signal = setup_ok and vol_ok and mom_ok and close < open_ and dir_short_ok and tl_short_ok
        if long_signal:
            st.entry("Long", st.long)
        if short_signal:
            st.entry("Short", st.short)
        if st.position_size == 0:
            self.entry_tp = NA
            self.entry_sl = NA
            self.entry_bar = NA
        if pos_prev0 and st.position_size != 0:
            self.entry_bar = self.bar_index
            if st.position_size > 0:
                self.entry_tp = float(st.position_avg_price + tp_ticks * mintick)
                self.entry_sl = float(st.position_avg_price - sl_ticks * mintick)
            else:
                self.entry_tp = float(st.position_avg_price - tp_ticks * mintick)
                self.entry_sl = float(st.position_avg_price + sl_ticks * mintick)
        if st.position_size > 0:
            st.exit("Exit Long", "Long", limit=self.entry_tp, stop=self.entry_sl)
        if st.position_size < 0:
            st.exit("Exit Short", "Short", limit=self.entry_tp, stop=self.entry_sl)
        is_time_exit = self.en_time_exit and st.position_size != 0 and not na(self.entry_bar) and self.bar_index - self.entry_bar >= self.time_exit_bars
        if is_time_exit:
            st.close_all(comment="Time Exit Stop")
        hour, minute = self.hour(), self.minute()
        is_session_end = False
        if self.session_exit == "TradingView Buggy Baseline":
            is_session_end = (in_morning_1 and not in_morning) or (in_noon_1 and not in_noon)
        elif self.session_exit == "Exit at 12:30 Sharp":
            is_session_end = (hour == 12 and minute == 25) or (hour == 17 and minute == 55)
        elif self.session_exit == "Carry Through Lunch":
            is_session_end = hour == 17 and minute == 55
        if self.en_eod_exit and is_session_end and st.position_size != 0:
            st.close_all(comment="Session End EOD")
