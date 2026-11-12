"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : Hybrid 3-Strategy Smart System v6.1
Author       : not stated
Source URL   : https://www.tradingview.com/script/ZfP0LbHE-Hybrid-3-Strategy-Smart-System-v6-1
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-29 by Claude (pine-to-python skill)

Line-for-line translation (orders processed at the bar close, process_orders_on_close). Three setups share one pending-signal window: an FVG pullback (a fair-value gap in an EMA / ADX / higher-timeframe trend, entered when price retests the gap and the candle confirms),
a volume-exhaustion reversal (extreme-volume, extreme-RSI wick bar followed by a close beyond its extreme within 4 bars) and a swing-break retest; each has a 0-100 score against the mode threshold ("Balanced" / "High Quality" parameter sets).
A signal that is still valid (not expired, within an ATR distance of the signal price, close not too far on the wrong side of the EMA) while flat opens the trade, sized by risk percent of equity over the stop distance, with a stop and an R:R target issued with the entry.
Deviations from the original: none. (The higher-timeframe values are plain request.security, lookahead off.)
Not carried over: the last-executed-trade cache, labels, order boxes, the status panel and the alerts (display only).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, div, na, pmath, ta


class HybridSmartSystem(Script):
    TITLE = "Hybrid 3-Strategy Smart System v6.1"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(initial_capital=2000, pyramiding=0, calc_on_every_tick=True, process_orders_on_close=True, commission_type="percent", commission_value=0.04)
    SOURCE = {"id": "ZfP0LbHE", "author": "not stated", "licence": "not stated",
              "url": "https://www.tradingview.com/script/ZfP0LbHE-Hybrid-3-Strategy-Smart-System-v6-1"}

    def init(self):
        i = self.input
        self.mode = i.string("Balanced", "Mode", options=["Balanced", "High Quality"])
        self.enable_fvg = i.bool(True, "Enable FVG Pullback")
        self.enable_vol = i.bool(True, "Enable Volume Exhaustion")
        self.enable_tl = i.bool(True, "Enable Trendline Break Retest")
        self.risk_percent = i.float(1.0, "Risk % Per Trade", step=0.1, minval=0.1)
        self.ema_len = i.int(50, "EMA Length", minval=20)
        self.atr_len = i.int(14, "ATR Length", minval=5)
        self.adx_len = i.int(14, "ADX Length", minval=5)
        self.rsi_len = i.int(14, "RSI Length", minval=5)
        self.pivot_len = i.int(4, "Pivot Length", minval=2)
        self.vol_len = i.int(20, "Volume MA Length", minval=5)
        self.use_htf_filter = i.bool(True, "Use Higher Timeframe Filter")
        self.htf_tf = i.timeframe("60", "Higher Timeframe")
        self.use_session_filter = i.bool(False, "Use Session Filter")
        self.session_input = i.session("0800-1700", "Trading Session")
        self.last_trade_bar = NA
        self.last_swing_high = NA
        self.last_swing_low = NA
        self.bull_fvg_top = NA
        self.bull_fvg_bot = NA
        self.bull_fvg_bar = NA
        self.bull_fvg_armed = False
        self.bear_fvg_top = NA
        self.bear_fvg_bot = NA
        self.bear_fvg_bar = NA
        self.bear_fvg_armed = False
        self.vol_long_armed = False
        self.vol_short_armed = False
        self.vol_long_trigger = NA
        self.vol_short_trigger = NA
        self.vol_long_bar = NA
        self.vol_short_bar = NA
        self.tl_long_armed = False
        self.tl_short_armed = False
        self.tl_long_level = NA
        self.tl_short_level = NA
        self.tl_long_bar = NA
        self.tl_short_bar = NA
        self.pending_long = False
        self.pending_short = False
        self.pending_entry = NA
        self.pending_sl = NA
        self.pending_tp = NA
        self.pending_expire_bar = NA

    def on_bar(self):
        st = self.strategy
        close, open_, high, low, volume = self.close, self.open, self.high, self.low, self.volume
        bal = self.mode == "Balanced"
        adx_min = 18.0 if bal else 24.0
        vol_mult = 1.4 if bal else 1.8
        fvg_min_atr = 0.20 if bal else 0.40
        fvg_max_age = 20 if bal else 14
        cooldown_bars = 5 if bal else 8
        max_entry_dist_atr = 1.00 if bal else 0.60
        validity_bars = 4 if bal else 3
        max_ema_distance_atr = 2.5 if bal else 1.6
        score_threshold = 55 if bal else 70
        ema_slope_bars = 3 if bal else 5
        ema_slope_atr_min = 0.10 if bal else 0.18
        rr_fvg = 2.0 if bal else 2.2
        rr_vol = 2.2 if bal else 2.5
        rr_tl = 1.8 if bal else 2.0
        ema50 = ta.ema(close, self.ema_len)
        atr = ta.atr(self.atr_len)
        rsi = ta.rsi(close, self.rsi_len)
        vol_ma = ta.sma(volume, self.vol_len)
        _, _, adx = ta.dmi(self.adx_len, self.adx_len)
        htf_close = self.security(None, self.htf_tf, lambda v: v.close)
        htf_ema = self.security(None, self.htf_tf, lambda v: ta.ema(v.close, self.ema_len))
        e_h, c_h, hi_h, lo_h = self.H("ema50"), self.H("close"), self.H("high"), self.H("low")
        ema_back = e_h[ema_slope_bars]
        close_1 = c_h[1]
        high_2, low_2 = hi_h[2], lo_h[2]
        e_h.set(ema50)
        c_h.set(close)
        hi_h.set(high)
        lo_h.set(low)
        in_session = (not self.use_session_filter) or self.time_in_session(self.session_input)
        htf_bull = (not self.use_htf_filter) or (htf_close > htf_ema)
        htf_bear = (not self.use_htf_filter) or (htf_close < htf_ema)
        ema_distance_ok = abs(close - ema50) <= atr * max_ema_distance_atr
        ema_slope_value = abs(ema50 - ema_back)
        trend_strength_ok = ema_slope_value >= atr * ema_slope_atr_min
        market_trending = bool(adx > adx_min and trend_strength_ok)
        body_size = abs(close - open_)
        upper_wick = high - pmath.max(open_, close)
        lower_wick = pmath.min(open_, close) - low
        bull_confirm = close > open_
        bear_confirm = close < open_
        bull_trend = bool(close > ema50 and ema50 > ema_back and htf_bull and in_session and ema_distance_ok)
        bear_trend = bool(close < ema50 and ema50 < ema_back and htf_bear and in_session and ema_distance_ok)
        high_vol = volume > vol_ma * vol_mult
        vol_ratio = div(volume, vol_ma) if vol_ma > 0 else 0.0
        cooldown_ok = na(self.last_trade_bar) or (self.bar_index - self.last_trade_bar > cooldown_bars)
        pivot_high = ta.pivothigh(high, self.pivot_len, self.pivot_len)
        pivot_low = ta.pivotlow(low, self.pivot_len, self.pivot_len)
        if not na(pivot_high):
            self.last_swing_high = float(pivot_high)
        if not na(pivot_low):
            self.last_swing_low = float(pivot_low)
        new_bull_fvg = bool(low > high_2)
        new_bear_fvg = bool(high < low_2)
        bull_fvg_size = (low - high_2) if new_bull_fvg else 0.0
        bear_fvg_size = (low_2 - high) if new_bear_fvg else 0.0
        valid_new_bull_fvg = bool(self.enable_fvg and new_bull_fvg and bull_fvg_size >= atr * fvg_min_atr and bull_trend and market_trending)
        valid_new_bear_fvg = bool(self.enable_fvg and new_bear_fvg and bear_fvg_size >= atr * fvg_min_atr and bear_trend and market_trending)
        if valid_new_bull_fvg:
            self.bull_fvg_top = float(low)
            self.bull_fvg_bot = float(high_2)
            self.bull_fvg_bar = self.bar_index
            self.bull_fvg_armed = True
        if valid_new_bear_fvg:
            self.bear_fvg_top = float(low_2)
            self.bear_fvg_bot = float(high)
            self.bear_fvg_bar = self.bar_index
            self.bear_fvg_armed = True
        if self.bull_fvg_armed and self.bar_index - self.bull_fvg_bar > fvg_max_age:
            self.bull_fvg_armed = False
            self.bull_fvg_top = NA
            self.bull_fvg_bot = NA
            self.bull_fvg_bar = NA
        if self.bear_fvg_armed and self.bar_index - self.bear_fvg_bar > fvg_max_age:
            self.bear_fvg_armed = False
            self.bear_fvg_top = NA
            self.bear_fvg_bot = NA
            self.bear_fvg_bar = NA
        bull_fvg_touch = bool(self.bull_fvg_armed and self.bar_index > self.bull_fvg_bar and low <= self.bull_fvg_top and high >= self.bull_fvg_bot)
        bear_fvg_touch = bool(self.bear_fvg_armed and self.bar_index > self.bear_fvg_bar and high >= self.bear_fvg_bot and low <= self.bear_fvg_top)
        fvg_long_base = bool(self.enable_fvg and bull_trend and cooldown_ok and bull_fvg_touch and bull_confirm and close > self.bull_fvg_bot)
        fvg_short_base = bool(self.enable_fvg and bear_trend and cooldown_ok and bear_fvg_touch and bear_confirm and close < self.bear_fvg_top)
        bull_fvg_score = pmath.min(div(bull_fvg_size, atr), 2.0) * 15.0
        bear_fvg_score = pmath.min(div(bear_fvg_size, atr), 2.0) * 15.0
        fvg_long_score = ((20 if bull_trend else 0) + (15 if htf_bull else 0) + (15 if market_trending else 0) + (15 if bull_fvg_touch else 0)
                          + (10 if bull_confirm else 0) + (10 if high_vol else 0) + bull_fvg_score)
        fvg_short_score = ((20 if bear_trend else 0) + (15 if htf_bear else 0) + (15 if market_trending else 0) + (15 if bear_fvg_touch else 0)
                           + (10 if bear_confirm else 0) + (10 if high_vol else 0) + bear_fvg_score)
        fvg_long_setup = bool(fvg_long_base and fvg_long_score >= score_threshold)
        fvg_short_setup = bool(fvg_short_base and fvg_short_score >= score_threshold)
        if fvg_long_setup:
            self.bull_fvg_armed = False
        if fvg_short_setup:
            self.bear_fvg_armed = False
        bull_exhaust_bar = bool(self.enable_vol and close < ema50 and high_vol and rsi < 38 and close > open_ and lower_wick > body_size * 0.6)
        bear_exhaust_bar = bool(self.enable_vol and close > ema50 and high_vol and rsi > 62 and close < open_ and upper_wick > body_size * 0.6)
        if bull_exhaust_bar:
            self.vol_long_armed = True
            self.vol_long_trigger = float(high)
            self.vol_long_bar = self.bar_index
        if bear_exhaust_bar:
            self.vol_short_armed = True
            self.vol_short_trigger = float(low)
            self.vol_short_bar = self.bar_index
        if self.vol_long_armed and self.bar_index - self.vol_long_bar > 4:
            self.vol_long_armed = False
            self.vol_long_trigger = NA
            self.vol_long_bar = NA
        if self.vol_short_armed and self.bar_index - self.vol_short_bar > 4:
            self.vol_short_armed = False
            self.vol_short_trigger = NA
            self.vol_short_bar = NA
        vol_long_base = bool(self.enable_vol and cooldown_ok and self.vol_long_armed and self.bar_index > self.vol_long_bar and close > self.vol_long_trigger and bull_confirm)
        vol_short_base = bool(self.enable_vol and cooldown_ok and self.vol_short_armed and self.bar_index > self.vol_short_bar and close < self.vol_short_trigger and bear_confirm)
        vol_long_score = ((15 if close > ema50 else 0) + (20 if rsi < 35 else 10) + (20 if high_vol else 0) + (15 if lower_wick > body_size else 8)
                          + (15 if close > self.vol_long_trigger else 0) + (10 if bull_confirm else 0) + pmath.min(vol_ratio, 2.0) * 5.0)
        vol_short_score = ((15 if close < ema50 else 0) + (20 if rsi > 65 else 10) + (20 if high_vol else 0) + (15 if upper_wick > body_size else 8)
                           + (15 if close < self.vol_short_trigger else 0) + (10 if bear_confirm else 0) + pmath.min(vol_ratio, 2.0) * 5.0)
        vol_long_setup = bool(vol_long_base and vol_long_score >= score_threshold)
        vol_short_setup = bool(vol_short_base and vol_short_score >= score_threshold)
        if vol_long_setup:
            self.vol_long_armed = False
        if vol_short_setup:
            self.vol_short_armed = False
        new_break_long = bool(self.enable_tl and (not na(self.last_swing_high)) and close > self.last_swing_high and close_1 <= self.last_swing_high and bull_trend and market_trending)
        new_break_short = bool(self.enable_tl and (not na(self.last_swing_low)) and close < self.last_swing_low and close_1 >= self.last_swing_low and bear_trend and market_trending)
        if new_break_long:
            self.tl_long_armed = True
            self.tl_long_level = self.last_swing_high
            self.tl_long_bar = self.bar_index
        if new_break_short:
            self.tl_short_armed = True
            self.tl_short_level = self.last_swing_low
            self.tl_short_bar = self.bar_index
        if self.tl_long_armed and self.bar_index - self.tl_long_bar > 10:
            self.tl_long_armed = False
            self.tl_long_level = NA
            self.tl_long_bar = NA
        if self.tl_short_armed and self.bar_index - self.tl_short_bar > 10:
            self.tl_short_armed = False
            self.tl_short_level = NA
            self.tl_short_bar = NA
        trend_long_base = bool(self.enable_tl and self.tl_long_armed and cooldown_ok and self.bar_index > self.tl_long_bar and low <= self.tl_long_level
                               and close > self.tl_long_level and bull_confirm)
        trend_short_base = bool(self.enable_tl and self.tl_short_armed and cooldown_ok and self.bar_index > self.tl_short_bar and high >= self.tl_short_level
                                and close < self.tl_short_level and bear_confirm)
        trend_long_score = ((20 if bull_trend else 0) + (20 if market_trending else 0) + (15 if htf_bull else 0) + (15 if low <= self.tl_long_level else 0)
                            + (15 if close > self.tl_long_level else 0) + (10 if bull_confirm else 0) + (5 if high_vol else 0))
        trend_short_score = ((20 if bear_trend else 0) + (20 if market_trending else 0) + (15 if htf_bear else 0) + (15 if high >= self.tl_short_level else 0)
                             + (15 if close < self.tl_short_level else 0) + (10 if bear_confirm else 0) + (5 if high_vol else 0))
        trend_long_setup = bool(trend_long_base and trend_long_score >= score_threshold)
        trend_short_setup = bool(trend_short_base and trend_short_score >= score_threshold)
        if trend_long_setup:
            self.tl_long_armed = False
        if trend_short_setup:
            self.tl_short_armed = False
        if st.position_size == 0 and not self.pending_long and not self.pending_short:
            if fvg_long_setup:
                self.pending_long, self.pending_short = True, False
                self.pending_entry = float(close)
                self.pending_sl = pmath.min(low, self.bull_fvg_bot) - atr * 0.7
                self.pending_tp = self.pending_entry + (self.pending_entry - self.pending_sl) * rr_fvg
                self.pending_expire_bar = self.bar_index + validity_bars
            elif vol_long_setup:
                self.pending_long, self.pending_short = True, False
                self.pending_entry = float(close)
                self.pending_sl = low - atr * 0.9
                self.pending_tp = self.pending_entry + (self.pending_entry - self.pending_sl) * rr_vol
                self.pending_expire_bar = self.bar_index + validity_bars
            elif trend_long_setup:
                self.pending_long, self.pending_short = True, False
                self.pending_entry = float(close)
                self.pending_sl = pmath.min(low, self.tl_long_level) - atr * 0.7
                self.pending_tp = self.pending_entry + (self.pending_entry - self.pending_sl) * rr_tl
                self.pending_expire_bar = self.bar_index + validity_bars
            elif fvg_short_setup:
                self.pending_long, self.pending_short = False, True
                self.pending_entry = float(close)
                self.pending_sl = pmath.max(high, self.bear_fvg_top) + atr * 0.7
                self.pending_tp = self.pending_entry - (self.pending_sl - self.pending_entry) * rr_fvg
                self.pending_expire_bar = self.bar_index + validity_bars
            elif vol_short_setup:
                self.pending_long, self.pending_short = False, True
                self.pending_entry = float(close)
                self.pending_sl = high + atr * 0.9
                self.pending_tp = self.pending_entry - (self.pending_sl - self.pending_entry) * rr_vol
                self.pending_expire_bar = self.bar_index + validity_bars
            elif trend_short_setup:
                self.pending_long, self.pending_short = False, True
                self.pending_entry = float(close)
                self.pending_sl = pmath.max(high, self.tl_short_level) + atr * 0.7
                self.pending_tp = self.pending_entry - (self.pending_sl - self.pending_entry) * rr_tl
                self.pending_expire_bar = self.bar_index + validity_bars
        signal_expired = bool((self.pending_long or self.pending_short) and not na(self.pending_expire_bar) and self.bar_index > self.pending_expire_bar)
        long_still_valid = bool(self.pending_long and not signal_expired and abs(close - self.pending_entry) <= atr * max_entry_dist_atr and close >= ema50 * 0.994)
        short_still_valid = bool(self.pending_short and not signal_expired and abs(close - self.pending_entry) <= atr * max_entry_dist_atr and close <= ema50 * 1.006)
        signal_still_valid = long_still_valid or short_still_valid
        if signal_expired:
            self.pending_long = False
            self.pending_short = False
            self.pending_entry = NA
            self.pending_sl = NA
            self.pending_tp = NA
            self.pending_expire_bar = NA
        risk_amount = st.equity * (self.risk_percent / 100.0)
        long_risk = (self.pending_entry - self.pending_sl) if self.pending_long else NA
        short_risk = (self.pending_sl - self.pending_entry) if self.pending_short else NA
        long_qty = div(risk_amount, long_risk) if (self.pending_long and not na(long_risk) and long_risk > self.syminfo.mintick) else NA
        short_qty = div(risk_amount, short_risk) if (self.pending_short and not na(short_risk) and short_risk > self.syminfo.mintick) else NA
        enter_long = bool(st.position_size == 0 and self.pending_long and signal_still_valid)
        enter_short = bool(st.position_size == 0 and self.pending_short and signal_still_valid)
        if enter_long and not na(long_qty):
            st.entry("LONG", st.long, qty=long_qty, comment="entry")
            st.exit("LONG EXIT", "LONG", stop=self.pending_sl, limit=self.pending_tp)
            self.last_trade_bar = self.bar_index
            self.pending_long = False
            self.pending_short = False
            self.pending_entry = NA
            self.pending_sl = NA
            self.pending_tp = NA
            self.pending_expire_bar = NA
        if enter_short and not na(short_qty):
            st.entry("SHORT", st.short, qty=short_qty, comment="entry")
            st.exit("SHORT EXIT", "SHORT", stop=self.pending_sl, limit=self.pending_tp)
            self.last_trade_bar = self.bar_index
            self.pending_long = False
            self.pending_short = False
            self.pending_entry = NA
            self.pending_sl = NA
            self.pending_tp = NA
            self.pending_expire_bar = NA
