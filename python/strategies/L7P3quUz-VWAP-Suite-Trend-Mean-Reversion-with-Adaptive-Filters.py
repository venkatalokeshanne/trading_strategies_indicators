"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : VWAP Strategy (Trend + Mean Reversion)
Author       : blitz_locked
Source URL   : https://www.tradingview.com/script/L7P3quUz-VWAP-Suite-Trend-Mean-Reversion-with-Adaptive-Filters
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-29 by Claude (pine-to-python skill)

Line-for-line translation (market orders at the next open). A volume-weighted VWAP with standard-deviation bands that restarts every session / week / month. Trend mode enters on a VWAP / band cross with slope, volume, ATR, band-width and optional RSI / EMA-regime filters; mean-reversion mode enters on an outside / cross / reclaim of a chosen band with an ADX ceiling, a maximum deviation from the VWAP and the same filters. Stop = ATR multiple (or band distance); the target is the opposite band or the VWAP. The exit is re-issued each bar while a position is open (the target is live unless it is locked at entry); an optional break-even moves the stop up once the profit reaches an ATR multiple. Position size is risk-based and capped by a maximum percentage of equity.

Deviations from the original: none. Note the original resets all stored stop levels on the first bar that sees the position flat, which also wipes the levels just set by a same-bar re-entry; that is kept (the exit then has only its limit).
Not carried over: the VWAP / band plots and fills (display only).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, div, na, pmath, ta


class VwapTrendMeanReversion(Script):
    TITLE = "VWAP Strategy (Trend + Mean Reversion)"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(initial_capital=100000, default_qty_type="fixed", default_qty_value=1, commission_type="percent", commission_value=0.05, pyramiding=0)
    SOURCE = {"id": "L7P3quUz", "author": "blitz_locked", "licence": "not stated",
              "url": "https://www.tradingview.com/script/L7P3quUz-VWAP-Suite-Trend-Mean-Reversion-with-Adaptive-Filters"}

    def init(self):
        i = self.input
        self.anchor = i.string("Session", "VWAP Anchor Period", options=["Session", "Week", "Month"])
        self.mode = i.string("Trend Following", "Strategy Mode", options=["Trend Following", "Mean Reversion"])
        self.b1 = i.float(1.0, "Band 1 (St Dev Mult)", step=0.1)
        self.b2 = i.float(2.0, "Band 2 (St Dev Mult)", step=0.1)
        self.b3 = i.float(3.0, "Band 3 (St Dev Mult)", step=0.1)
        self.use_vol = i.bool(True, "Use Volume Filter")
        self.vol_thresh = i.float(1.2, "Volume Threshold", step=0.1)
        self.vol_len = i.int(20, "Volume Average Length", minval=1)
        self.use_slope = i.bool(True, "Use VWAP Slope Filter")
        self.slope_lb = i.int(5, "Slope Lookback (bars)", minval=1)
        self.min_slope = i.float(0.05, "Minimum VWAP Slope (%)", step=0.01)
        self.use_atr_f = i.bool(True, "Use Volatility (ATR) Filter")
        self.atr_len = i.int(14, "ATR Length", minval=1)
        self.atr_thresh = i.float(0.2, "Minimum ATR (% of Price)", step=0.05)
        self.use_bw = i.bool(True, "Use Band Width Filter")
        self.min_bw = i.float(0.2, "Minimum Bandwidth (% Price)", step=0.05)
        self.second = i.string("None", "Secondary Indicator", options=["None", "RSI", "EMA Regime"])
        self.rsi_len = i.int(14, "RSI Length", minval=1)
        self.rsi_tl = i.int(50, "Trend RSI Minimum for Longs", minval=0, maxval=100)
        self.rsi_ts = i.int(50, "Trend RSI Maximum for Shorts", minval=0, maxval=100)
        self.rsi_os = i.int(30, "Mean Reversion RSI Oversold", minval=1, maxval=50)
        self.rsi_ob = i.int(70, "Mean Reversion RSI Overbought", minval=50, maxval=99)
        self.ema_len = i.int(200, "EMA Regime Length", minval=1)
        self.use_adx = i.bool(True, "Use ADX Filter")
        self.adx_len = i.int(14, "ADX Length", minval=1)
        self.max_adx = i.float(25.0, "Maximum ADX", step=1.0)
        self.trend_entry = i.string("VWAP Cross", "Trend Entry Trigger", options=["VWAP Cross", "Band 1 Break", "Band 2 Break"])
        self.mr_entry = i.string("Band Reclaim", "Mean Reversion Entry Trigger", options=["Outside Band", "Band Cross", "Band Reclaim"])
        self.mr_band = i.string("Band 2", "Mean Reversion Entry Band", options=["Band 1", "Band 2", "Band 3"])
        self.max_dev = i.float(3.0, "Maximum VWAP Deviation (ATR)", step=0.1)
        self.risk_pct = i.float(1.0, "Risk per Trade (%)", step=0.1, minval=0.1)
        self.max_pos_pct = i.float(20.0, "Maximum Position Size (% Equity)", step=5.0, minval=1.0)
        self.sl_method = i.string("ATR", "Stop Loss Method", options=["Band Based", "ATR"])
        self.stop_atr = i.float(1.5, "Stop ATR Multiple", step=0.1)
        self.tp_method = i.string("Opposite Band", "Take Profit Method", options=["Opposite Band", "VWAP Target"])
        self.fixed_tp = i.bool(False, "Lock Take Profit at Entry")
        self.use_be = i.bool(False, "Use Break-Even Stop")
        self.be_atr = i.float(1.0, "Profit Required Before Break-Even (ATR)", step=0.1)
        self.cum_pv = 0.0
        self.cum_vol = 0.0
        self.cum_pv2 = 0.0
        self.long_stop = NA
        self.short_stop = NA
        self.long_tp = NA
        self.short_tp = NA
        self.entry_atr = NA

    def on_bar(self):
        st = self.strategy
        close, high, low = self.close, self.high, self.low
        tp_ = (high + low + close) / 3
        tf = {"Session": "D", "Week": "W", "Month": "M"}[self.anchor]
        if ta.change(self.time_fn(tf)) != 0:
            self.cum_pv = 0.0
            self.cum_vol = 0.0
            self.cum_pv2 = 0.0
        self.cum_pv += tp_ * self.volume
        self.cum_vol += self.volume
        self.cum_pv2 += self.volume * pmath.pow(tp_, 2)
        vwap = self.cum_pv / self.cum_vol if self.cum_vol != 0 else tp_
        variance = (self.cum_pv2 / self.cum_vol) - pmath.pow(vwap, 2) if self.cum_vol != 0 else 0.0
        sd = pmath.sqrt(pmath.max(variance, 0.0))
        up1, lo1 = vwap + sd * self.b1, vwap - sd * self.b1
        up2, lo2 = vwap + sd * self.b2, vwap - sd * self.b2
        up3, lo3 = vwap + sd * self.b3, vwap - sd * self.b3
        atr = ta.atr(self.atr_len)
        rsi = ta.rsi(close, self.rsi_len)
        reg_ema = ta.ema(close, self.ema_len)
        avg_vol = ta.sma(self.volume, self.vol_len)
        _, _, adx = ta.dmi(self.adx_len, self.adx_len)
        vw_h = self.H("vwap")
        vwap_back = vw_h[self.slope_lb]
        vw_h.set(vwap)
        vol_ok = (not self.use_vol) or self.volume > avg_vol * self.vol_thresh
        atr_pct = div(atr, close) * 100
        volat_ok = (not self.use_atr_f) or atr_pct > self.atr_thresh
        bw_pct = div(up1 - lo1, close) * 100
        bw_ok = (not self.use_bw) or bw_pct > self.min_bw
        slope = div(vwap - vwap_back, vwap_back) * 100 if not na(vwap_back) else 0.0
        slope_long = (not self.use_slope) or slope > self.min_slope
        slope_short = (not self.use_slope) or slope < -self.min_slope
        base_ok = vol_ok and volat_ok and bw_ok
        adx_ok = (not self.use_adx) or adx < self.max_adx
        dist_atr = div(close - vwap, atr) if atr > 0 else 0.0
        dev_ok = abs(dist_atr) <= self.max_dev
        trend_rsi_l = rsi > self.rsi_tl
        trend_rsi_s = rsi < self.rsi_ts
        mr_rsi_l = ta.crossover(rsi, self.rsi_os)
        mr_rsi_s = ta.crossunder(rsi, self.rsi_ob)
        ema_l = close > reg_ema
        ema_s = close < reg_ema
        if self.second == "RSI":
            tc_l, tc_s, mc_l, mc_s = trend_rsi_l, trend_rsi_s, mr_rsi_l, mr_rsi_s
        elif self.second == "EMA Regime":
            tc_l, tc_s, mc_l, mc_s = ema_l, ema_s, ema_l, ema_s
        else:
            tc_l = tc_s = mc_l = mc_s = True
        mr_up = {"Band 1": up1, "Band 2": up2, "Band 3": up3}[self.mr_band]
        mr_lo = {"Band 1": lo1, "Band 2": lo2, "Band 3": lo3}[self.mr_band]
        if self.trend_entry == "VWAP Cross":
            t_long, t_short = ta.crossover(close, vwap), ta.crossunder(close, vwap)
        elif self.trend_entry == "Band 1 Break":
            t_long, t_short = ta.crossover(close, up1), ta.crossunder(close, lo1)
        else:
            t_long, t_short = ta.crossover(close, up2), ta.crossunder(close, lo2)
        if self.mr_entry == "Outside Band":
            m_long, m_short = close < mr_lo, close > mr_up
        elif self.mr_entry == "Band Cross":
            m_long, m_short = ta.crossunder(close, mr_lo), ta.crossover(close, mr_up)
        else:
            m_long = low < mr_lo and close > mr_lo
            m_short = high > mr_up and close < mr_up
        if self.mode == "Trend Following":
            long_cond = t_long and base_ok and slope_long and tc_l
            short_cond = t_short and base_ok and slope_short and tc_s
        else:
            long_cond = m_long and base_ok and adx_ok and dev_ok and mc_l
            short_cond = m_short and base_ok and adx_ok and dev_ok and mc_s
        trend = self.mode == "Trend Following"
        atr_stop = self.sl_method == "ATR"
        if trend:
            long_dist = atr * self.stop_atr if atr_stop else abs(close - lo1)
            short_dist = atr * self.stop_atr if atr_stop else abs(up1 - close)
        else:
            long_dist = atr * self.stop_atr if atr_stop else abs(close - lo3)
            short_dist = atr * self.stop_atr if atr_stop else abs(up3 - close)
        risk_amt = st.equity * (self.risk_pct / 100)
        max_val = st.equity * (self.max_pos_pct / 100)
        raw_l = risk_amt / long_dist if long_dist > 0 else 0
        raw_s = risk_amt / short_dist if short_dist > 0 else 0
        max_qty = max_val / close if close > 0 else 0
        qty_l = pmath.min(raw_l, max_qty)
        qty_s = pmath.min(raw_s, max_qty)
        if self.tp_method == "VWAP Target":
            long_target = short_target = vwap
        elif trend:
            long_target, short_target = up2, lo2
        else:
            long_target = short_target = vwap
        pos_h = self.H("pos")
        pos_prev = pos_h[1]
        pos_h.set(st.position_size)
        if long_cond and st.position_size == 0:
            self.long_stop = float(close - long_dist)
            self.long_tp = float(long_target)
            self.entry_atr = float(atr)
            st.entry("Long", st.long, qty=qty_l)
        if short_cond and st.position_size == 0:
            self.short_stop = float(close + short_dist)
            self.short_tp = float(short_target)
            self.entry_atr = float(atr)
            st.entry("Short", st.short, qty=qty_s)
        if st.position_size > 0 and self.use_be:
            be_trigger = st.position_avg_price + self.entry_atr * self.be_atr
            if high >= be_trigger:
                self.long_stop = float(pmath.max(self.long_stop, st.position_avg_price))
        if st.position_size < 0 and self.use_be:
            be_trigger = st.position_avg_price - self.entry_atr * self.be_atr
            if low <= be_trigger:
                self.short_stop = float(pmath.min(self.short_stop, st.position_avg_price))
        if st.position_size > 0:
            st.exit("Long Exit", "Long", stop=self.long_stop, limit=self.long_tp if self.fixed_tp else long_target)
        if st.position_size < 0:
            st.exit("Short Exit", "Short", stop=self.short_stop, limit=self.short_tp if self.fixed_tp else short_target)
        if st.position_size == 0 and not na(pos_prev) and pos_prev != 0:
            self.long_stop = NA
            self.short_stop = NA
            self.long_tp = NA
            self.short_tp = NA
            self.entry_atr = NA
