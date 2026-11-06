"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : ORB A+ Confluence Strategy
Author       : mthibs21
Source URL   : https://www.tradingview.com/script/i10lTr3L
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-29 by Claude (pine-to-python skill)

Line-for-line translation (process_orders_on_close); the session moving average is selectable (EMA, SMA, WMA or RMA). The high / low of an opening-range session (09:30-10:00, Monday-Friday in the chosen zone) becomes the day's range once the session has ended. After it, an eight-point confluence score (VWAP, session moving-average and slope side, strong / extreme volume, a strong candle, a retest or rejection pattern, a location inside / outside the range) must reach the A threshold while a trend filter, a location test, a confirmation candle and a maximum-extension test pass; the entry is at the close. The ATR stop and R:R target are measured from the fill price, the stop moves to the entry once the break-even trigger is reached, and a trend failure (close below the session moving average and the VWAP with a bearish candle) exits. Optional prop-style guardrails (daily loss, trailing drawdown, evaluation target, entries per day) lock out new trades and flatten.
Deviations from the original: none.
Not carried over: the range / EMA / VWAP plots, the opening-range fill, the A / A+ labels and alerts (display only).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, div, na, pmath, ta


class OrbAPlusConfluenceMA(Script):
    TITLE = "ORB A+ Confluence Strategy"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(initial_capital=1000000, default_qty_type="fixed", default_qty_value=1, pyramiding=0, commission_type="percent", commission_value=0,
                    process_orders_on_close=True)
    SOURCE = {"id": "i10lTr3L", "author": "mthibs21", "licence": "not stated",
              "url": "https://www.tradingview.com/script/i10lTr3L"}

    def init(self):
        i = self.input
        g = "Opening Range"
        self.range_session = i.session("0930-1000:23456", "Opening Range Session", group=g)
        self.tz = i.string("America/New_York", "Session Timezone", options=["America/New_York", "Etc/UTC", "Europe/London", "Asia/Tokyo"], group=g)
        i.bool(True, "Show OR Midpoint", group=g)
        self.allow_inside = i.bool(True, "Allow A/A+ Setups Inside OR", group=g)
        g = "Session Moving Average"
        i.bool(True, "Show Session Moving Average", group=g)
        self.ma_len = i.int(20, "Length", minval=1, group=g)
        self.ma_type = i.string("EMA", "Type", options=["EMA", "SMA", "WMA", "RMA"], group=g)
        g = "A+ Trend Filters"
        self.slope_lb = i.int(3, "MA Slope Lookback", minval=1, group=g)
        self.use_vwap = i.bool(True, "Use VWAP Confirmation", group=g)
        self.use_ema = i.bool(True, "Use Session MA Confirmation", group=g)
        self.use_slope = i.bool(True, "Use MA Slope Confirmation", group=g)
        i.bool(True, "Show VWAP", group=g)
        g = "Volume Confirmation"
        self.vol_len = i.int(20, "Volume Average Length", minval=1, group=g)
        self.vol_mult = i.float(1.25, "Strong Volume Multiplier", minval=0.1, step=0.05, group=g)
        self.xvol_mult = i.float(1.60, "A+ Volume Multiplier", minval=0.1, step=0.05, group=g)
        g = "A+ Setup Scoring"
        self.min_a = i.int(5, "Minimum Score for A", minval=1, maxval=8, group=g)
        self.min_aplus = i.int(7, "Minimum Score for A+", minval=1, maxval=8, group=g)
        self.retest_tol = i.float(0.25, "Retest Tolerance (ATR)", minval=0.05, step=0.05, group=g)
        self.max_ext = i.float(1.25, "Maximum MA Extension (ATR)", minval=0.25, step=0.05, group=g)
        self.req_confirm = i.bool(True, "Require Confirmation Candle", group=g)
        g = "Trade Targets"
        self.atr_len = i.int(14, "ATR Length", minval=1, group=g)
        self.stop_mult = i.float(1.25, "Stop ATR Multiplier", minval=0.1, step=0.05, group=g)
        self.rr = i.float(2.0, "Risk / Reward", minval=0.5, step=0.25, group=g)
        self.use_be = i.bool(True, "Move Stop to Break-Even", group=g)
        self.be_trigger = i.float(1.0, "Break-Even Trigger (R)", minval=0.25, step=0.25, group=g)
        self.use_trend_exit = i.bool(True, "Enable Trend Failure Exit", group=g)
        g = "Prop-Style Risk Rules"
        self.prop_on = i.bool(True, "Enable Prop Guardrails", group=g)
        self.prop_size = i.float(50000, "Prop Account Size", minval=1, step=1000, group=g)
        self.daily_loss_pct = i.float(3.0, "Daily Loss Limit (%)", minval=0.1, step=0.1, group=g)
        self.max_dd_pct = i.float(6.0, "Trailing Max Drawdown (%)", minval=0.1, step=0.1, group=g)
        self.max_trades = i.int(3, "Maximum Entries Per Day", minval=1, group=g)
        self.target_pct = i.float(6.0, "Evaluation Target (%)", minval=0.1, step=0.1, group=g)
        g = "Style"
        i.bool(True, "Show A/A+ Signals", group=g)
        i.bool(True, "Show Active Targets", group=g)
        self.range_high = NA
        self.range_low = NA
        self.range_ready = False
        self.base_equity = NA
        self.day_start_equity = NA
        self.peak_equity = NA
        self.trades_today = 0
        self.daily_breached = False
        self.dd_breached = False
        self.target_reached = False
        self.long_risk = NA
        self.short_risk = NA
        self.long_be = False
        self.short_be = False

    def on_bar(self):
        st = self.strategy
        close, open_, high, low, volume = self.close, self.open, self.high, self.low, self.volume
        tfp = self.timeframe.period
        day_stamp = self.time_fn("D", "0000-2359", self.tz)
        ds_h = self.H("day_stamp")
        ds_1 = ds_h[1]
        ds_h.set(day_stamp)
        new_day = (not na(day_stamp)) and (na(ds_1) or day_stamp != ds_1)
        in_range = not na(self.time_fn(tfp, self.range_session, self.tz))
        ir_h = self.H("in_range")
        ir_1 = ir_h[1]
        ir_h.set(in_range)
        was_in_range = self.bar_index > 0 and (not na(ir_1)) and bool(ir_1)
        range_start = in_range and not was_in_range
        range_end = (not in_range) and was_in_range
        if new_day:
            self.range_high = NA
            self.range_low = NA
            self.range_ready = False
        if range_start:
            self.range_high = float(high)
            self.range_low = float(low)
            self.range_ready = False
        elif in_range:
            self.range_high = float(pmath.max(self.range_high, high))
            self.range_low = float(pmath.min(self.range_low, low))
        if range_end:
            self.range_ready = True
        rh, rl = self.range_high, self.range_low
        range_mid = (rh + rl) / 2.0 if (not na(rh) and not na(rl)) else NA
        if self.ma_type == "SMA":
            ema20 = ta.sma(close, self.ma_len)
        elif self.ma_type == "WMA":
            ema20 = ta.wma(close, self.ma_len)
        elif self.ma_type == "RMA":
            ema20 = ta.rma(close, self.ma_len)
        else:
            ema20 = ta.ema(close, self.ma_len)
        vwap = ta.vwap(self.hlc3)
        atr = ta.atr(self.atr_len)
        vol_avg = ta.sma(volume, self.vol_len)
        strong_vol = (not na(vol_avg)) and volume >= vol_avg * self.vol_mult
        extreme_vol = (not na(vol_avg)) and volume >= vol_avg * self.xvol_mult
        e_h = self.H("ema20")
        ema_back = e_h[self.slope_lb]
        e_h.set(ema20)
        ema_rising = ema20 > ema_back
        ema_falling = ema20 < ema_back
        above_ema, below_ema = close > ema20, close < ema20
        above_vwap, below_vwap = close > vwap, close < vwap
        c_h = self.H("close")
        close_1 = c_h[1]
        c_h.set(close)
        candle_range = high - low
        body = abs(close - open_)
        body_pct = div(body, candle_range) if candle_range > 0 else 0.0
        bull_candle, bear_candle = close > open_, close < open_
        strong_bull = bull_candle and body_pct >= 0.55 and close >= high - candle_range * 0.25
        strong_bear = bear_candle and body_pct >= 0.55 and close <= low + candle_range * 0.25
        ready = self.range_ready
        outside_long = ready and close > rh
        outside_short = ready and close < rl
        inside_orb = ready and close <= rh and close >= rl
        upper_half = inside_orb and close > range_mid
        lower_half = inside_orb and close < range_mid
        tol = atr * self.retest_tol
        long_orb_retest = ready and low <= rh + tol and low >= rh - tol and close > rh
        short_orb_retest = ready and high >= rl - tol and high <= rl + tol and close < rl
        long_ema_retest = low <= ema20 + tol and close > ema20 and bull_candle
        short_ema_retest = high >= ema20 - tol and close < ema20 and bear_candle
        long_vwap_retest = low <= vwap + tol and close > vwap and bull_candle
        short_vwap_retest = high >= vwap - tol and close < vwap and bear_candle
        long_low_rej = inside_orb and low <= rl + tol and close > rl + tol and bull_candle
        short_high_rej = inside_orb and high >= rh - tol and close < rh - tol and bear_candle
        long_mid_cont = inside_orb and close > range_mid and close_1 <= range_mid and above_ema and above_vwap and strong_bull
        short_mid_cont = inside_orb and close < range_mid and close_1 >= range_mid and below_ema and below_vwap and strong_bear
        not_overext = abs(close - ema20) <= atr * self.max_ext
        long_score = (int(above_vwap) + int(above_ema) + int(ema_rising) + int(strong_vol) + int(strong_bull)
                      + int(bool(long_orb_retest or long_ema_retest or long_vwap_retest or long_low_rej or long_mid_cont))
                      + int(bool(outside_long or upper_half or long_low_rej)) + int(extreme_vol))
        short_score = (int(below_vwap) + int(below_ema) + int(ema_falling) + int(strong_vol) + int(strong_bear)
                       + int(bool(short_orb_retest or short_ema_retest or short_vwap_retest or short_high_rej or short_mid_cont))
                       + int(bool(outside_short or lower_half or short_high_rej)) + int(extreme_vol))
        long_confirm = (not self.req_confirm) or strong_bull
        short_confirm = (not self.req_confirm) or strong_bear
        valid_long_loc = outside_long or (self.allow_inside and inside_orb and (upper_half or long_low_rej or long_mid_cont))
        valid_short_loc = outside_short or (self.allow_inside and inside_orb and (lower_half or short_high_rej or short_mid_cont))
        if na(self.base_equity):
            self.base_equity = float(st.equity)
        sim_equity = self.prop_size + st.equity - self.base_equity
        if na(self.day_start_equity) or new_day:
            self.day_start_equity = float(sim_equity)
            self.trades_today = 0
            self.daily_breached = False
        self.peak_equity = float(sim_equity) if na(self.peak_equity) else float(pmath.max(self.peak_equity, sim_equity))
        daily_loss_amt = self.prop_size * self.daily_loss_pct / 100.0
        max_dd_amt = self.prop_size * self.max_dd_pct / 100.0
        target_amt = self.prop_size * self.target_pct / 100.0
        if self.prop_on:
            if sim_equity <= self.day_start_equity - daily_loss_amt:
                self.daily_breached = True
            if sim_equity <= self.peak_equity - max_dd_amt:
                self.dd_breached = True
            if sim_equity >= self.prop_size + target_amt:
                self.target_reached = True
        prop_lockout = self.prop_on and (self.daily_breached or self.dd_breached or self.target_reached)
        prop_allowed = (not self.prop_on) or ((not prop_lockout) and self.trades_today < self.max_trades)
        base_permission = ready and (not in_range) and st.position_size == 0 and prop_allowed and not_overext
        long_trend_ok = ((not self.use_vwap) or above_vwap) and ((not self.use_ema) or above_ema) and ((not self.use_slope) or ema_rising)
        short_trend_ok = ((not self.use_vwap) or below_vwap) and ((not self.use_ema) or below_ema) and ((not self.use_slope) or ema_falling)
        long_signal = bool(base_permission and valid_long_loc and long_trend_ok and long_confirm and long_score >= self.min_a)
        short_signal = bool(base_permission and valid_short_loc and short_trend_ok and short_confirm and short_score >= self.min_a)
        final_long = long_signal and not short_signal
        final_short = short_signal and not long_signal
        long_grade = "A+" if long_score >= self.min_aplus else "A"
        short_grade = "A+" if short_score >= self.min_aplus else "A"
        if final_long:
            self.trades_today += 1
            st.entry("Long", st.long, comment=long_grade + " LONG")
        if final_short:
            self.trades_today += 1
            st.entry("Short", st.short, comment=short_grade + " SHORT")
        pos_h = self.H("pos")
        pos_1 = pos_h[1]
        pos_h.set(st.position_size)
        new_long = st.position_size > 0 and ((not na(pos_1)) and pos_1 <= 0)
        new_short = st.position_size < 0 and ((not na(pos_1)) and pos_1 >= 0)
        if new_long:
            self.long_risk = float(atr * self.stop_mult)
        if new_short:
            self.short_risk = float(atr * self.stop_mult)
        if st.position_size == 0:
            self.long_risk = NA
            self.short_risk = NA
        avg = st.position_avg_price
        long_base_stop = avg - self.long_risk if (st.position_size > 0 and not na(self.long_risk)) else NA
        long_target = avg + self.long_risk * self.rr if (st.position_size > 0 and not na(self.long_risk)) else NA
        short_base_stop = avg + self.short_risk if (st.position_size < 0 and not na(self.short_risk)) else NA
        short_target = avg - self.short_risk * self.rr if (st.position_size < 0 and not na(self.short_risk)) else NA
        long_be_reached = st.position_size > 0 and self.use_be and not na(self.long_risk) and high >= avg + self.long_risk * self.be_trigger
        short_be_reached = st.position_size < 0 and self.use_be and not na(self.short_risk) and low <= avg - self.short_risk * self.be_trigger
        if new_long:
            self.long_be = False
        if new_short:
            self.short_be = False
        if long_be_reached:
            self.long_be = True
        if short_be_reached:
            self.short_be = True
        if st.position_size == 0:
            self.long_be = False
            self.short_be = False
        active_long_stop = pmath.max(long_base_stop, avg) if self.long_be else long_base_stop
        active_short_stop = pmath.min(short_base_stop, avg) if self.short_be else short_base_stop
        st.exit("Long Target/Stop", "Long", stop=active_long_stop, limit=long_target)
        st.exit("Short Target/Stop", "Short", stop=active_short_stop, limit=short_target)
        long_fail = self.use_trend_exit and st.position_size > 0 and close < ema20 and close < vwap and bear_candle
        short_fail = self.use_trend_exit and st.position_size < 0 and close > ema20 and close > vwap and bull_candle
        if long_fail:
            st.close("Long", comment="Trend Exit")
        if short_fail:
            st.close("Short", comment="Trend Exit")
        if prop_lockout and st.position_size != 0:
            st.close_all(comment="Prop Lockout")
