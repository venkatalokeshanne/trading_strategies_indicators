"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : Xiznit Scalper
Author       : not stated
Source URL   : https://www.tradingview.com/script/oPZA3pgr-Xiznit-Scalper
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-29 by Claude (pine-to-python skill)

Line-for-line translation (market orders at the next open). One of four entry signals (EMA cross, session-VWAP deviation, Heikin Ashi + RSI, price structure) is taken inside the Asia / London / New York sessions (Chicago time, per-session trade caps and a global cooldown)
when the Efficiency-Ratio regime allows it (trending for EMA / HA, trending or mildly ranging for VWAP / structure) and the optional filters (volume surge, ADX, higher-timeframe EMA (request.security, lookahead off), VWAP bias, ROC) pass; an ATR stop and an R:R target are issued with the entry.
Deviations from the original: the duplicate input titles (Start / End Hour, Max Trades, Length) are prefixed with their session / filter name.
Not carried over: the trade-grade labels, the regime background, the EMA / VWAP plots and the webhook alert messages (display only).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, div, na, ta


class XiznitScalper(Script):
    TITLE = "Xiznit Scalper"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(margin_long=100, margin_short=100, default_qty_type="fixed", default_qty_value=1)
    SOURCE = {"id": "oPZA3pgr", "author": "not stated", "licence": "not stated", "url": "https://www.tradingview.com/script/oPZA3pgr-Xiznit-Scalper"}

    def init(self):
        i = self.input
        g = "Signal Mode"
        self.signal_mode = i.string("EMA Cross", "Entry Signal Mode", options=["EMA Cross", "VWAP Deviation", "Heikin Ashi + RSI", "Price Structure"], group=g)
        self.ema_fast_len = i.int(9, "EMA Fast Length", group=g)
        self.ema_slow_len = i.int(21, "EMA Slow Length", group=g)
        self.vwap_dev = i.float(0.0015, "VWAP Deviation Threshold (%/100)", group=g, step=0.0001)
        self.rsi_len = i.int(14, "RSI Length", group=g)
        self.rsi_ob = i.int(55, "RSI Bull Threshold (Long > X)", group=g)
        self.rsi_os = i.int(45, "RSI Bear Threshold (Short < X)", group=g)
        self.struct_bars = i.int(2, "Structure Lookback Candles (2–3)", group=g, minval=2, maxval=3)
        g = "ER Regime Filter"
        self.er_len = i.int(10, "ER Length", group=g)
        self.er_trend_min = i.float(0.6, "Trending Threshold ≥", group=g, step=0.05)
        self.er_range_min = i.float(0.3, "Mild Ranging Threshold ≥", group=g, step=0.05)
        g = "ATR Stop / Target"
        self.atr_len = i.int(14, "ATR Length", group=g)
        self.atr_sl = i.float(1.2, "SL Multiplier", group=g, step=0.1)
        self.atr_rr = i.float(1.5, "R:R Ratio (TP)", group=g, step=0.1)
        g = "Session Settings"
        self.asia_on = i.bool(True, "Asia Session", group=g)
        self.asia_start = i.int(19, "Asia Start Hour (CT)", group=g)
        self.asia_end = i.int(24, "Asia End Hour (CT)", group=g)
        self.asia_max = i.int(5, "Asia Max Trades", group=g)
        self.lon_on = i.bool(True, "London Session", group=g)
        self.lon_start = i.int(2, "London Start Hour (CT)", group=g)
        self.lon_end = i.int(8, "London End Hour (CT)", group=g)
        self.lon_max = i.int(5, "London Max Trades", group=g)
        self.ny_on = i.bool(True, "New York Session", group=g)
        self.ny_start = i.int(8, "NY Start Hour (CT)", group=g)
        self.ny_end = i.int(15, "NY End Hour (CT)", group=g)
        self.ny_max = i.int(5, "NY Max Trades", group=g)
        self.cooldown = i.int(3, "Cooldown Bars Between Entries", group=g, minval=1)
        g = "Entry Filters"
        self.vol_on = i.bool(False, "Volume Surge", group=g)
        self.vol_mult = i.float(1.5, "× Avg", group=g, step=0.1)
        self.vol_len = i.int(20, "over N bars", group=g, minval=1)
        self.adx_on = i.bool(False, "ADX Strength", group=g)
        self.adx_len = i.int(14, "ADX Length", group=g, minval=1)
        self.adx_min = i.int(20, "Min ADX", group=g, minval=1)
        self.htf_on = i.bool(False, "HTF Trend Align", group=g)
        self.htf_tf = i.timeframe("15", "Timeframe", group=g)
        self.htf_ema_len = i.int(50, "EMA Length", group=g, minval=1)
        self.vwap_bias_on = i.bool(False, "VWAP Bias", group=g)
        self.roc_on = i.bool(False, "ROC Momentum", group=g)
        self.roc_len = i.int(9, "ROC Length", group=g, minval=1)
        self.prev_asia = False
        self.prev_london = False
        self.prev_ny = False
        self.asia_trades = 0
        self.london_trades = 0
        self.ny_trades = 0
        self.bars_since_entry = 9999
        self.vwap_num = 0.0
        self.vwap_den = 0.0
        self.ha_open_val = 0.0

    def on_bar(self):
        st = self.strategy
        close, open_, high, low, volume = self.close, self.open, self.high, self.low, self.volume
        ct_hour = self.hour(self.time, "America/Chicago")
        in_asia = bool(self.asia_on and (ct_hour >= self.asia_start or ct_hour < (0 if self.asia_end == 24 else self.asia_end)))
        in_london = bool(self.lon_on and (ct_hour >= self.lon_start and ct_hour < self.lon_end))
        in_ny = bool(self.ny_on and (ct_hour >= self.ny_start and ct_hour < self.ny_end))
        in_any_session = in_asia or in_london or in_ny
        asia_open_bar = in_asia and not self.prev_asia
        london_open_bar = in_london and not self.prev_london
        ny_open_bar = in_ny and not self.prev_ny
        if asia_open_bar:
            self.asia_trades = 0
        if london_open_bar:
            self.london_trades = 0
        if ny_open_bar:
            self.ny_trades = 0
        sess_count = self.asia_trades if in_asia else (self.london_trades if in_london else (self.ny_trades if in_ny else 999))
        sess_max = self.asia_max if in_asia else (self.lon_max if in_london else (self.ny_max if in_ny else 0))
        trades_ok = in_any_session and sess_count < sess_max
        self.bars_since_entry = self.bars_since_entry + 1
        cooldown_ok = self.bars_since_entry >= self.cooldown
        c_h, h_h, l_h = self.H("close"), self.H("high"), self.H("low")
        close_1, close_er, close_roc = c_h[1], c_h[self.er_len], c_h[self.roc_len]
        high_1, high_2, low_1, low_2 = h_h[1], h_h[2], l_h[1], l_h[2]
        c_h.set(close)
        h_h.set(high)
        l_h.set(low)
        er_direction = abs(close - close_er)
        er_path = ta.msum(abs(close - close_1), self.er_len)
        er_val = div(er_direction, er_path) if er_path > 0 else 0.0
        er_regime = 2 if er_val >= self.er_trend_min else (1 if er_val >= self.er_range_min else 0)
        atr_val = ta.atr(self.atr_len)
        if asia_open_bar or london_open_bar or ny_open_bar:
            self.vwap_num = 0.0
            self.vwap_den = 0.0
        self.vwap_num += self.hlc3 * volume
        self.vwap_den += volume
        sess_vwap = div(self.vwap_num, self.vwap_den) if self.vwap_den > 0 else self.hlc3
        vol_avg = ta.sma(volume, self.vol_len)
        filter_vol = (not self.vol_on) or (volume > vol_avg * self.vol_mult)
        up_move = high - high_1
        down_move = low_1 - low
        dm_plus = up_move if (up_move > down_move and up_move > 0) else 0.0
        dm_minus = down_move if (down_move > up_move and down_move > 0) else 0.0
        atr_adx = ta.rma(ta.tr(True), self.adx_len)
        di_plus = 100 * div(ta.rma(dm_plus, self.adx_len), atr_adx)
        di_minus = 100 * div(ta.rma(dm_minus, self.adx_len), atr_adx)
        dx = div(abs(di_plus - di_minus), di_plus + di_minus) * 100
        adx_val = ta.rma(dx, self.adx_len)
        filter_adx = (not self.adx_on) or (adx_val >= self.adx_min)
        htf_ema_raw = self.security(None, self.htf_tf, lambda v: ta.ema(v.close, self.htf_ema_len), lookahead=False)
        filter_htf_long = (not self.htf_on) or (close > htf_ema_raw)
        filter_htf_short = (not self.htf_on) or (close < htf_ema_raw)
        vwap_bias_active = self.vwap_bias_on and self.signal_mode != "VWAP Deviation"
        filter_vbias_long = (not vwap_bias_active) or (close > sess_vwap)
        filter_vbias_short = (not vwap_bias_active) or (close < sess_vwap)
        roc_val = div(close - close_roc, close_roc) * 100
        filter_roc_long = (not self.roc_on) or (roc_val > 0)
        filter_roc_short = (not self.roc_on) or (roc_val < 0)
        filters_long = bool(filter_vol and filter_adx and filter_htf_long and filter_vbias_long and filter_roc_long)
        filters_short = bool(filter_vol and filter_adx and filter_htf_short and filter_vbias_short and filter_roc_short)
        ema_fast = ta.ema(close, self.ema_fast_len)
        ema_slow = ta.ema(close, self.ema_slow_len)
        ema_long = ta.crossover(ema_fast, ema_slow)
        ema_short = ta.crossunder(ema_fast, ema_slow)
        vwap_dev_pct = div(close - sess_vwap, sess_vwap)
        vwap_long = vwap_dev_pct < -self.vwap_dev
        vwap_short = vwap_dev_pct > self.vwap_dev
        ha_close = (open_ + high + low + close) / 4
        hc_h, ho_h = self.H("ha_close"), self.H("ha_open")
        ha_close_1, ha_open_1 = hc_h[1], ho_h[1]
        self.ha_open_val = (open_ + close) / 2 if na(ha_open_1) else (ha_open_1 + ha_close_1) / 2
        hc_h.set(ha_close)
        ho_h.set(self.ha_open_val)
        ha_bull = ha_close > self.ha_open_val and ha_close_1 > ha_open_1
        ha_bear = ha_close < self.ha_open_val and ha_close_1 < ha_open_1
        rsi_val = ta.rsi(close, self.rsi_len)
        ha_long = ha_bull and rsi_val > self.rsi_ob
        ha_short = ha_bear and rsi_val < self.rsi_os
        if self.struct_bars == 2:
            struct_long = high > high_1 and low > low_1
            struct_short = high < high_1 and low < low_1
        else:
            struct_long = high > high_1 and high_1 > high_2 and low > low_1 and low_1 > low_2
            struct_short = high < high_1 and high_1 < high_2 and low < low_1 and low_1 < low_2
        mode_ema = self.signal_mode == "EMA Cross" and er_regime == 2
        mode_vwap = self.signal_mode == "VWAP Deviation" and er_regime >= 1
        mode_ha = self.signal_mode == "Heikin Ashi + RSI" and er_regime == 2
        mode_str = self.signal_mode == "Price Structure" and er_regime >= 1
        sig_long = (mode_ema and ema_long) or (mode_vwap and vwap_long) or (mode_ha and ha_long) or (mode_str and struct_long)
        sig_short = (mode_ema and ema_short) or (mode_vwap and vwap_short) or (mode_ha and ha_short) or (mode_str and struct_short)
        is_flat = st.position_size == 0
        can_enter_long = bool(sig_long and is_flat and trades_ok and cooldown_ok and in_any_session and filters_long)
        can_enter_short = bool(sig_short and is_flat and trades_ok and cooldown_ok and in_any_session and filters_short)
        if can_enter_long:
            sl_price = close - atr_val * self.atr_sl
            tp_price = close + atr_val * self.atr_sl * self.atr_rr
            st.entry("Long", st.long)
            st.exit("Long Exit", from_entry="Long", stop=sl_price, limit=tp_price)
            self.bars_since_entry = 0
            if in_asia:
                self.asia_trades += 1
            elif in_london:
                self.london_trades += 1
            elif in_ny:
                self.ny_trades += 1
        if can_enter_short:
            sl_price = close + atr_val * self.atr_sl
            tp_price = close - atr_val * self.atr_sl * self.atr_rr
            st.entry("Short", st.short)
            st.exit("Short Exit", from_entry="Short", stop=sl_price, limit=tp_price)
            self.bars_since_entry = 0
            if in_asia:
                self.asia_trades += 1
            elif in_london:
                self.london_trades += 1
            elif in_ny:
                self.ny_trades += 1
        self.prev_asia = in_asia
        self.prev_london = in_london
        self.prev_ny = in_ny
