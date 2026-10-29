"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : Swordsmith Bulletproof Version 2
Author       : not stated
Source URL   : https://www.tradingview.com/script/5giSaENe-Swordsmith-Bulletproof-Version-2
Pine version : v5
Licence      : Mozilla Public License 2.0
Type         : strategy
Status       : FULL
Converted    : 2026-10-29 by Claude (pine-to-python skill)

Line-for-line translation (market orders at the next open; 5-minute chart). The 09:30-09:45 New York opening range is locked after the window; a breakout (or retest) beyond it, inside the NY session on an allowed weekday before the cutoff, with a confluence score of at least N
(higher-timeframe EMA trend (request.security, lookahead off), BOS / CHoCH structure, liquidity sweep, order block, FVG, volume flow, ATR smart trail, RSI, session) and no prop-firm lockout (daily / weekly loss, trades per day, consecutive losses, profit targets) opens a position at the next open.
Stop (ATR / ORB mid / opposite ORB / fixed) and R-multiple targets are measured from the signal close and re-issued each bar; after TP1 is touched the stop moves to break-even (or the smart trail); everything is closed at the cutoff.
Deviations from the original: none for a one-contract position; the repeated input titles "Enable" are padded with spaces to stay unique. (Two-contract partial exits are translated as written; the zero-quantity second target when one contract is traded is passed as the original does.)
Not carried over: ORB / trail / HTF plots, signal and BOS markers, order-block / FVG boxes and the dashboard (display only).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, div, na, nz, pmath, ta


class SwordsmithBulletproofV2(Script):
    TITLE = "Swordsmith Bulletproof Version 2"
    PINE_VERSION = 5
    OVERLAY = True
    STRATEGY = dict(pyramiding=0, default_qty_type="fixed", default_qty_value=1, initial_capital=50000, commission_type="cash_per_contract",
                    commission_value=0.5, slippage=1)
    SOURCE = {"id": "5giSaENe", "author": "not stated", "licence": "Mozilla Public License 2.0",
              "url": "https://www.tradingview.com/script/5giSaENe-Swordsmith-Bulletproof-Version-2"}

    def init(self):
        i = self.input
        g = "Instrument Settings"
        self.point_value = i.float(2.0, "Point Value Override", group=g)
        self.qty = i.int(1, "Contracts", minval=1, maxval=2, group=g)
        self.trade_dir = i.string("Both", "Trade Direction", options=["Long Only", "Short Only", "Both"], group=g)
        g = "Opening Range"
        self.orb_start = i.session("0930-0945", "ORB Window (NY)", group=g)
        self.orb_end = i.int(9, "ORB End Hour (NY 24h)", group=g)
        self.orb_end_min = i.int(30, "ORB End Minute", group=g)
        self.cutoff_hour = i.int(15, "Trade Cutoff Hour (NY)", group=g)
        self.cutoff_min = i.int(0, "Trade Cutoff Min", group=g)
        self.retest_mode = i.bool(False, "Require ORB Retest", group=g)
        self.retest_tol_in = i.float(0.25, "Retest Tolerance (% of ORB range)", group=g)
        g = "C1: HTF Trend (15m)"
        self.c1_en = i.bool(True, "Enable", group=g)
        self.htf_tf = i.timeframe("15", "HTF Timeframe", group=g)
        self.htf_fast_len = i.int(9, "Fast EMA Length", group=g)
        self.htf_slow_len = i.int(21, "Slow EMA Length", group=g)
        g = "C2: BOS / CHoCH"
        self.c2_en = i.bool(True, "Enable ", group=g)
        self.piv_len = i.int(5, "Pivot Length", group=g)
        self.c2_score = i.int(2, "Score Weight", minval=1, maxval=3, group=g)
        g = "C3: Liquidity Sweep"
        self.c3_en = i.bool(True, "Enable  ", group=g)
        self.liq_len = i.int(10, "Swing Lookback", group=g)
        g = "C4: Order Block"
        self.c4_en = i.bool(True, "Enable   ", group=g)
        self.ob_mit_pct = i.float(50.0, "Mitigation % (0=touch, 100=full close thru)", group=g)
        g = "C5: Fair Value Gap"
        self.c5_en = i.bool(True, "Enable    ", group=g)
        self.fvg_max_bars = i.int(50, "FVG Max Age (bars)", group=g)
        g = "C6: Volume Flow"
        self.c6_en = i.bool(True, "Enable     ", group=g)
        self.vol_ma_len = i.int(20, "Volume MA Length", group=g)
        self.use_obv = i.bool(False, "Use OBV Confirmation", group=g)
        g = "C7: Smart Trail"
        self.c7_en = i.bool(True, "Enable      ", group=g)
        self.atr_len = i.int(14, "ATR Length", group=g)
        self.atr_mult = i.float(2.0, "ATR Multiplier", group=g)
        g = "C8: Momentum"
        self.c8_en = i.bool(True, "Enable       ", group=g)
        self.rsi_len = i.int(14, "RSI Length", group=g)
        self.rsi_bull_thr = i.int(50, "RSI Bull Threshold", group=g)
        self.rsi_bear_thr = i.int(50, "RSI Bear Threshold", group=g)
        self.use_div = i.bool(False, "Use Divergence Filter", group=g)
        g = "C9: Session Filter"
        self.c9_en = i.bool(True, "Enable        ", group=g)
        self.ny_en = i.bool(True, "NY Session", group=g)
        self.ldn_en = i.bool(False, "London Session", group=g)
        self.ny_start = i.int(9, "NY Start Hour", group=g)
        self.ny_end = i.int(16, "NY End Hour", group=g)
        self.ldn_start = i.int(3, "London Start Hour", group=g)
        self.ldn_end = i.int(8, "London End Hour", group=g)
        self.mon_en = i.bool(True, "Monday", group=g)
        self.tue_en = i.bool(True, "Tuesday", group=g)
        self.wed_en = i.bool(True, "Wednesday", group=g)
        self.thu_en = i.bool(True, "Thursday", group=g)
        self.fri_en = i.bool(True, "Friday", group=g)
        self.min_score = i.int(6, "Min Score Required", minval=1, maxval=14, group="Confluence")
        g = "Exit Settings"
        self.stop_type = i.string("ATR", "Stop Type", options=["ATR", "ORB Mid", "Opposite ORB", "Fixed Points"], group=g)
        self.fixed_stop = i.float(20.0, "Fixed Stop (points)", group=g)
        self.atr_stop_mult = i.float(1.5, "ATR Stop Multiplier", group=g)
        self.tp1_r = i.float(1.0, "TP1 R Multiple", group=g)
        self.tp2_r = i.float(2.0, "TP2 R Multiple", group=g)
        self.tp1_pct = i.float(50.0, "TP1 Exit %", group=g)
        self.be_pct = i.float(0.0, "Breakeven Offset (ticks)", group=g)
        self.trail_after_tp1 = i.bool(True, "Smart Trail after TP1", group=g)
        g = "Prop Firm Risk Controls"
        self.daily_max_loss = i.float(500.0, "Daily Max Loss ($)", group=g)
        self.weekly_max_loss = i.float(1000.0, "Weekly Max Loss ($)", group=g)
        self.max_trades_day = i.int(5, "Max Trades/Day", group=g)
        self.max_consec_loss = i.int(3, "Max Consecutive Losses", group=g)
        self.daily_pt = i.float(0.0, "Daily Profit Target (0=off)", group=g)
        self.weekly_pt = i.float(0.0, "Weekly Profit Target (0=off)", group=g)
        self.orb_high = NA
        self.orb_low = NA
        self.orb_set = False
        self.retest_long_ready = False
        self.retest_short_ready = False
        self.retest_long_fired = False
        self.retest_short_fired = False
        self.last_swing_high = NA
        self.last_swing_low = NA
        self.in_bear_trend = False
        self.in_bull_trend = False
        self.bull_ob_high = NA
        self.bull_ob_low = NA
        self.bear_ob_high = NA
        self.bear_ob_low = NA
        self.bull_ob_active = False
        self.bear_ob_active = False
        self.bull_fvg_top = NA
        self.bull_fvg_bot = NA
        self.bull_fvg_bar = NA
        self.bear_fvg_top = NA
        self.bear_fvg_bot = NA
        self.bear_fvg_bar = NA
        self.trail = NA
        self.trail_dir = 0
        self.last_rsi_h = NA
        self.last_prc_h = NA
        self.last_rsi_l = NA
        self.last_prc_l = NA
        self.prev_rsi_h = NA
        self.prev_prc_h = NA
        self.prev_rsi_l = NA
        self.prev_prc_l = NA
        self.last_day = NA
        self.last_week = NA
        self.day_start_pnl = 0.0
        self.week_start_pnl = 0.0
        self.daily_trades = 0
        self.consec_loss = 0
        self.last_closed_trades = 0
        self.entry_price = NA
        self.stop_dst = NA
        self.tp1_price = NA
        self.tp2_price = NA
        self.stop_price = NA
        self.tp1_hit = False

    def stop_dist(self, is_long, atr, close):
        if self.stop_type == "ATR":
            sd = atr * self.atr_stop_mult
        elif self.stop_type == "ORB Mid":
            orb_mid = self.orb_mid
            sd = (close - orb_mid) if is_long else (orb_mid - close)
        elif self.stop_type == "Opposite ORB":
            sd = (close - self.orb_low) if is_long else (self.orb_high - close)
        else:
            sd = self.fixed_stop
        return pmath.max(nz(sd, atr * self.atr_stop_mult), self.syminfo.mintick)

    def on_bar(self):
        st = self.strategy
        close, open_, high, low, volume = self.close, self.open, self.high, self.low, self.volume
        tz = "America/New_York"
        ny_hour = self.hour(self.time, tz)
        ny_minute = self.minute(self.time, tz)
        dow = self.dayofweek(self.time, tz)
        in_ny = ny_hour >= self.ny_start and ny_hour < self.ny_end
        in_ldn = ny_hour >= self.ldn_start and ny_hour < self.ldn_end
        in_session = bool((self.ny_en and in_ny) or (self.ldn_en and in_ldn))
        day_ok = bool((dow == 2 and self.mon_en) or (dow == 3 and self.tue_en) or (dow == 4 and self.wed_en) or (dow == 5 and self.thu_en) or (dow == 6 and self.fri_en))
        past_cutoff = bool((ny_hour > self.cutoff_hour) or (ny_hour == self.cutoff_hour and ny_minute >= self.cutoff_min))
        in_orb_window = self.time_in_session(self.orb_start, tz)
        new_day = ta.change(self.time_fn("D")) != 0
        if new_day:
            self.orb_high = NA
            self.orb_low = NA
            self.orb_set = False
        if in_orb_window:
            self.orb_high = float(high) if na(self.orb_high) else pmath.max(self.orb_high, high)
            self.orb_low = float(low) if na(self.orb_low) else pmath.min(self.orb_low, low)
        orb_window_closed = (not in_orb_window) and (not na(self.orb_high))
        if orb_window_closed and not self.orb_set:
            self.orb_set = True
        self.orb_mid = (self.orb_high + self.orb_low) / 2 if (not na(self.orb_high) and not na(self.orb_low)) else NA
        orb_mid = self.orb_mid
        long_breakout = bool(self.orb_set and close > self.orb_high)
        short_breakout = bool(self.orb_set and close < self.orb_low)
        orb_range = (self.orb_high - self.orb_low) if (not na(self.orb_high) and not na(self.orb_low)) else 0.0
        retest_tol = orb_range * (self.retest_tol_in / 100.0)
        if new_day:
            self.retest_long_ready = False
            self.retest_short_ready = False
            self.retest_long_fired = False
            self.retest_short_fired = False
        if long_breakout and not self.retest_long_fired:
            self.retest_long_ready = True
        if short_breakout and not self.retest_short_fired:
            self.retest_short_ready = True
        retest_long = bool(self.retest_long_ready and low <= self.orb_high + retest_tol and close > self.orb_high)
        retest_short = bool(self.retest_short_ready and high >= self.orb_low - retest_tol and close < self.orb_low)
        long_signal_raw = bool(self.orb_set and (retest_long if self.retest_mode else long_breakout) and not past_cutoff)
        short_signal_raw = bool(self.orb_set and (retest_short if self.retest_mode else short_breakout) and not past_cutoff)
        htf_fast = self.security(None, self.htf_tf, lambda v: ta.ema(v.close, self.htf_fast_len), lookahead=False)
        htf_slow = self.security(None, self.htf_tf, lambda v: ta.ema(v.close, self.htf_slow_len), lookahead=False)
        htf_bull = bool(htf_fast > htf_slow and close > htf_fast)
        htf_bear = bool(htf_fast < htf_slow and close < htf_fast)
        c1_long = (not self.c1_en) or htf_bull
        c1_short = (not self.c1_en) or htf_bear
        c1_score_long = (1 if htf_bull else 0) if self.c1_en else 0
        c1_score_short = (1 if htf_bear else 0) if self.c1_en else 0
        c_h, o_h, h_h, l_h = self.H("close"), self.H("open"), self.H("high"), self.H("low")
        close_1 = c_h[1]
        closes_b = [c_h[k] for k in range(1, 6)]
        opens_b = [o_h[k] for k in range(1, 6)]
        highs_b = [h_h[k] for k in range(1, 6)]
        lows_b = [l_h[k] for k in range(1, 6)]
        high_2, low_2 = highs_b[1], lows_b[1]
        c_h.set(close)
        o_h.set(open_)
        h_h.set(high)
        l_h.set(low)
        swing_high = ta.pivothigh(high, self.piv_len, self.piv_len)
        swing_low = ta.pivotlow(low, self.piv_len, self.piv_len)
        if not na(swing_high):
            self.last_swing_high = float(swing_high)
        if not na(swing_low):
            self.last_swing_low = float(swing_low)
        bull_bos = bool((not na(self.last_swing_high)) and close > self.last_swing_high and close_1 <= self.last_swing_high)
        bear_bos = bool((not na(self.last_swing_low)) and close < self.last_swing_low and close_1 >= self.last_swing_low)
        bull_choch = self.in_bear_trend and bull_bos
        bear_choch = self.in_bull_trend and bear_bos
        if bull_bos:
            self.in_bull_trend = True
            self.in_bear_trend = False
        if bear_bos:
            self.in_bear_trend = True
            self.in_bull_trend = False
        c2_long = (bull_bos or bull_choch) if self.c2_en else False
        c2_short = (bear_bos or bear_choch) if self.c2_en else False
        c2_score_long = (self.c2_score if c2_long else 0) if self.c2_en else 0
        c2_score_short = (self.c2_score if c2_short else 0) if self.c2_en else 0
        hh_h, ll_h = self.H("liq_high"), self.H("liq_low")
        recent_high, recent_low = hh_h[1], ll_h[1]
        hh_h.set(ta.highest(high, self.liq_len))
        ll_h.set(ta.lowest(low, self.liq_len))
        bull_sweep = bool(low < recent_low and close > recent_low)
        bear_sweep = bool(high > recent_high and close < recent_high)
        c3_score_long = (1 if bull_sweep else 0) if self.c3_en else 0
        c3_score_short = (1 if bear_sweep else 0) if self.c3_en else 0
        if bull_bos:
            for k in range(5):
                if closes_b[k] < opens_b[k]:
                    self.bull_ob_high = float(highs_b[k])
                    self.bull_ob_low = float(lows_b[k])
                    self.bull_ob_active = True
                    break
        if bear_bos:
            for k in range(5):
                if closes_b[k] > opens_b[k]:
                    self.bear_ob_high = float(highs_b[k])
                    self.bear_ob_low = float(lows_b[k])
                    self.bear_ob_active = True
                    break
        mit_pct = self.ob_mit_pct / 100.0
        if self.bull_ob_active and not na(self.bull_ob_high):
            mit_level = self.bull_ob_low + (self.bull_ob_high - self.bull_ob_low) * mit_pct
            if close < mit_level:
                self.bull_ob_active = False
        if self.bear_ob_active and not na(self.bear_ob_high):
            mit_level = self.bear_ob_high - (self.bear_ob_high - self.bear_ob_low) * mit_pct
            if close > mit_level:
                self.bear_ob_active = False
        in_bull_ob = bool(self.bull_ob_active and not na(self.bull_ob_high) and low <= self.bull_ob_high and close >= self.bull_ob_low)
        in_bear_ob = bool(self.bear_ob_active and not na(self.bear_ob_high) and high >= self.bear_ob_low and close <= self.bear_ob_high)
        c4_score_long = (1 if in_bull_ob else 0) if self.c4_en else 0
        c4_score_short = (1 if in_bear_ob else 0) if self.c4_en else 0
        bull_fvg = bool(low > high_2)
        bear_fvg = bool(high < low_2)
        if bull_fvg:
            self.bull_fvg_top = float(low)
            self.bull_fvg_bot = float(high_2)
            self.bull_fvg_bar = self.bar_index
        if bear_fvg:
            self.bear_fvg_top = float(low_2)
            self.bear_fvg_bot = float(high)
            self.bear_fvg_bar = self.bar_index
        bull_fvg_age = (self.bar_index - self.bull_fvg_bar) if not na(self.bull_fvg_bar) else 999
        bear_fvg_age = (self.bar_index - self.bear_fvg_bar) if not na(self.bear_fvg_bar) else 999
        in_bull_fvg = bool((not na(self.bull_fvg_top)) and bull_fvg_age <= self.fvg_max_bars and close >= self.bull_fvg_bot and close <= self.bull_fvg_top)
        in_bear_fvg = bool((not na(self.bear_fvg_top)) and bear_fvg_age <= self.fvg_max_bars and close >= self.bear_fvg_bot and close <= self.bear_fvg_top)
        c5_score_long = (1 if in_bull_fvg else 0) if self.c5_en else 0
        c5_score_short = (1 if in_bear_fvg else 0) if self.c5_en else 0
        vol_ma = ta.sma(volume, self.vol_ma_len)
        vol_above = volume > vol_ma
        bull_candle = close > open_
        bear_candle = close < open_
        obv = ta.cum(pmath.sign(close - close_1) * volume)
        obv_h = self.H("obv")
        obv_3 = obv_h[3]
        obv_h.set(obv)
        obv_slope = obv - obv_3
        c6_long = (bool(vol_above and bull_candle and ((not self.use_obv) or obv_slope > 0))) if self.c6_en else False
        c6_short = (bool(vol_above and bear_candle and ((not self.use_obv) or obv_slope < 0))) if self.c6_en else False
        c6_score_long = (1 if c6_long else 0) if self.c6_en else 0
        c6_score_short = (1 if c6_short else 0) if self.c6_en else 0
        atr = ta.atr(self.atr_len)
        trail_step = atr * self.atr_mult
        if na(self.trail):
            self.trail = float(close)
        trail_up = close - trail_step
        trail_down = close + trail_step
        if close > self.trail:
            self.trail = pmath.max(self.trail, trail_up)
            self.trail_dir = 1
        elif close < self.trail:
            self.trail = pmath.min(self.trail, trail_down)
            self.trail_dir = -1
        trail_bull = self.trail_dir == 1
        trail_bear = self.trail_dir == -1
        c7_score_long = (1 if trail_bull else 0) if self.c7_en else 0
        c7_score_short = (1 if trail_bear else 0) if self.c7_en else 0
        rsi = ta.rsi(close, self.rsi_len)
        rsi_bull = rsi >= self.rsi_bull_thr
        rsi_bear = rsi <= self.rsi_bear_thr
        rsi_piv_high = ta.pivothigh(rsi, self.piv_len, self.piv_len)
        rsi_piv_low = ta.pivotlow(rsi, self.piv_len, self.piv_len)
        price_piv_h = ta.pivothigh(high, self.piv_len, self.piv_len)
        price_piv_l = ta.pivotlow(low, self.piv_len, self.piv_len)
        if not na(rsi_piv_high):
            self.prev_rsi_h = self.last_rsi_h
            self.prev_prc_h = self.last_prc_h
            self.last_rsi_h = float(rsi_piv_high)
            self.last_prc_h = float(price_piv_h)
        if not na(rsi_piv_low):
            self.prev_rsi_l = self.last_rsi_l
            self.prev_prc_l = self.last_prc_l
            self.last_rsi_l = float(rsi_piv_low)
            self.last_prc_l = float(price_piv_l)
        bear_div = bool(self.use_div and (not na(self.prev_prc_h)) and (not na(self.last_prc_h)) and self.last_prc_h > self.prev_prc_h and self.last_rsi_h < self.prev_rsi_h)
        bull_div = bool(self.use_div and (not na(self.prev_prc_l)) and (not na(self.last_prc_l)) and self.last_prc_l < self.prev_prc_l and self.last_rsi_l > self.prev_rsi_l)
        c8_long = bool(rsi_bull and not bear_div) if self.c8_en else False
        c8_short = bool(rsi_bear and not bull_div) if self.c8_en else False
        c8_score_long = (1 if c8_long else 0) if self.c8_en else 0
        c8_score_short = (1 if c8_short else 0) if self.c8_en else 0
        c9_long = (in_session and day_ok) if self.c9_en else False
        c9_score_long = (1 if c9_long else 0) if self.c9_en else 0
        c9_score_short = c9_score_long
        score_long = (c1_score_long + c2_score_long + c3_score_long + c4_score_long + c5_score_long + c6_score_long + c7_score_long + c8_score_long + c9_score_long)
        score_short = (c1_score_short + c2_score_short + c3_score_short + c4_score_short + c5_score_short + c6_score_short + c7_score_short + c8_score_short + c9_score_short)
        dom = self.dayofmonth()
        woy = self.weekofyear()
        is_new_day = na(self.last_day) or dom != self.last_day
        is_new_week = na(self.last_week) or woy != self.last_week
        if is_new_day:
            self.last_day = dom
        if is_new_week:
            self.last_week = woy
        if is_new_day:
            self.day_start_pnl = st.netprofit
            self.daily_trades = 0
        if is_new_week:
            self.week_start_pnl = st.netprofit
        daily_pnl = st.netprofit - self.day_start_pnl
        weekly_pnl = st.netprofit - self.week_start_pnl
        open_pnl = st.openprofit
        eff_daily = daily_pnl + open_pnl
        eff_weekly = weekly_pnl + open_pnl
        daily_loss = eff_daily <= -abs(self.daily_max_loss)
        weekly_loss = eff_weekly <= -abs(self.weekly_max_loss)
        max_trades = self.daily_trades >= self.max_trades_day
        max_consec = self.consec_loss >= self.max_consec_loss
        daily_pt_hit = self.daily_pt > 0 and eff_daily >= self.daily_pt
        weekly_pt_hit = self.weekly_pt > 0 and eff_weekly >= self.weekly_pt
        risk_lockout = bool(daily_loss or weekly_loss or max_trades or max_consec or daily_pt_hit or weekly_pt_hit)
        num_closed = st.closedtrades
        if num_closed > self.last_closed_trades:
            self.daily_trades += 1
            last_trade_profit = st.closedtrades_profit(num_closed - 1)
            if last_trade_profit < 0:
                self.consec_loss += 1
            else:
                self.consec_loss = 0
            self.last_closed_trades = num_closed
        pos = st.position_size
        can_long = bool((self.trade_dir == "Long Only" or self.trade_dir == "Both") and score_long >= self.min_score and long_signal_raw and day_ok and in_session
                        and c1_long and not risk_lockout and pos == 0)
        can_short = bool((self.trade_dir == "Short Only" or self.trade_dir == "Both") and score_short >= self.min_score and short_signal_raw and day_ok and in_session
                         and c1_short and not risk_lockout and pos == 0)
        if can_long:
            self.entry_price = float(close)
            self.stop_dst = self.stop_dist(True, atr, close)
            self.stop_price = self.entry_price - self.stop_dst
            self.tp1_price = self.entry_price + self.stop_dst * self.tp1_r
            self.tp2_price = self.entry_price + self.stop_dst * self.tp2_r
            self.tp1_hit = False
            st.entry("Long", st.long, qty=self.qty)
        if can_short:
            self.entry_price = float(close)
            self.stop_dst = self.stop_dist(False, atr, close)
            self.stop_price = self.entry_price + self.stop_dst
            self.tp1_price = self.entry_price - self.stop_dst * self.tp1_r
            self.tp2_price = self.entry_price - self.stop_dst * self.tp2_r
            self.tp1_hit = False
            st.entry("Short", st.short, qty=self.qty)
        tp1_qty = int(pmath.round(self.qty * (self.tp1_pct / 100.0)))
        tp2_qty = pmath.max(self.qty - tp1_qty, 0)
        is_long = pos > 0
        is_short = pos < 0
        if is_long and high >= self.tp1_price and not self.tp1_hit:
            self.tp1_hit = True
        if is_short and low <= self.tp1_price and not self.tp1_hit:
            self.tp1_hit = True
        if pos == 0:
            self.tp1_hit = False
        be_offset = self.be_pct * self.syminfo.mintick
        be_stop_long = nz(self.entry_price, close) + be_offset
        be_stop_short = nz(self.entry_price, close) - be_offset
        if self.tp1_hit:
            active_stop_long = pmath.max(be_stop_long, nz(self.trail, be_stop_long)) if self.trail_after_tp1 else be_stop_long
            active_stop_short = pmath.min(be_stop_short, nz(self.trail, be_stop_short)) if self.trail_after_tp1 else be_stop_short
        else:
            active_stop_long = nz(self.stop_price, close - atr)
            active_stop_short = nz(self.stop_price, close + atr)
        if is_long:
            st.exit("L-TP1", "Long", qty=tp1_qty, limit=self.tp1_price, stop=active_stop_long, comment="TP1")
            st.exit("L-TP2", "Long", qty=tp2_qty, limit=self.tp2_price, stop=active_stop_long, comment="TP2")
        if is_short:
            st.exit("S-TP1", "Short", qty=tp1_qty, limit=self.tp1_price, stop=active_stop_short, comment="TP1")
            st.exit("S-TP2", "Short", qty=tp2_qty, limit=self.tp2_price, stop=active_stop_short, comment="TP2")
        if past_cutoff and pos != 0:
            st.close_all(comment="EOD")
