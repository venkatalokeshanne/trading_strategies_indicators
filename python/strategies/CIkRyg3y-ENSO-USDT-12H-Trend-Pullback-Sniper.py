"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : ENSO/USDT 15m Trend Pullback Sniper
Author       : Rr0nchee
Source URL   : https://www.tradingview.com/script/CIkRyg3y-ENSO-USDT-12H-Trend-Pullback-Sniper
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-29 by Claude (pine-to-python skill)

Line-for-line translation (market orders at the next open). In an EMA uptrend (9 over 21 and the close over the 50) with the close over the VWAP, within one ATR (times the zone input) of the 21 EMA and the stochastic-RSI %K crossing up through %D from below the oversold level,
a long is opened while flat (mirror for shorts at the overbought level). The entry issues two exit orders from it: half the quantity at TP1 (ATR multiple) and the rest at TP2, both with the stop at ATR x multiple from the signal close; a close beyond the 50 EMA against the position closes it at the next open.
Deviations from the original: none.
Not carried over: the trend background and the entry triangles (display only).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import Script, ta


class EnsoPullbackSniper(Script):
    TITLE = "ENSO/USDT 15m Trend Pullback Sniper"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(default_qty_type="percent_of_equity", default_qty_value=100, initial_capital=10000, commission_type="percent", commission_value=0.075)
    SOURCE = {"id": "CIkRyg3y", "author": "Rr0nchee", "licence": "not stated",
              "url": "https://www.tradingview.com/script/CIkRyg3y-ENSO-USDT-12H-Trend-Pullback-Sniper"}

    def init(self):
        i = self.input
        self.ema_fast_len = i.int(9, "EMA Fast Length", minval=1)
        self.ema_mid_len = i.int(21, "EMA Mid Length", minval=1)
        self.ema_slow_len = i.int(50, "EMA Slow Length", minval=1)
        self.stoch_rsi_len = i.int(14, "Stoch RSI Length", minval=1)
        self.stoch_k = i.int(3, "Stoch K Smoothing", minval=1)
        self.stoch_d = i.int(3, "Stoch D Smoothing", minval=1)
        self.stoch_ob = i.int(80, "Stoch Overbought", minval=50, maxval=100)
        self.stoch_os = i.int(20, "Stoch Oversold", minval=0, maxval=50)
        self.atr_len = i.int(14, "ATR Length", minval=1)
        self.sl_multi = i.float(1.5, "Stop Loss ATR Multiplier", step=0.1)
        self.tp1_multi = i.float(2.0, "Take Profit 1 ATR Multiplier", step=0.1)
        self.tp2_multi = i.float(3.0, "Take Profit 2 ATR Multiplier", step=0.1)
        self.pullback_atr = i.float(1.0, "Pullback Zone (ATR from EMA21)", step=0.1)

    def on_bar(self):
        st = self.strategy
        close = self.close
        ema_fast = ta.ema(close, self.ema_fast_len)
        ema_mid = ta.ema(close, self.ema_mid_len)
        ema_slow = ta.ema(close, self.ema_slow_len)
        vwap_val = ta.vwap(self.hlc3)
        atr_val = ta.atr(self.atr_len)
        rsi_val = ta.rsi(close, self.stoch_rsi_len)
        stoch_k_val = ta.sma(ta.stoch(rsi_val, rsi_val, rsi_val, self.stoch_rsi_len), self.stoch_k)
        stoch_d_val = ta.sma(stoch_k_val, self.stoch_d)
        stoch_cross_up = ta.crossover(stoch_k_val, stoch_d_val)
        stoch_cross_down = ta.crossunder(stoch_k_val, stoch_d_val)
        uptrend_ema = ema_fast > ema_mid and close > ema_slow
        downtrend_ema = ema_fast < ema_mid and close < ema_slow
        bullish_vwap = close > vwap_val
        bearish_vwap = close < vwap_val
        near_ema21 = abs(close - ema_mid) <= (atr_val * self.pullback_atr)
        k_hist = self.H("stoch_k")
        stoch_k_1 = k_hist[1]
        k_hist.set(stoch_k_val)
        stoch_os_cross = stoch_cross_up and stoch_k_1 < self.stoch_os
        stoch_ob_cross = stoch_cross_down and stoch_k_1 > self.stoch_ob
        long_condition = uptrend_ema and bullish_vwap and near_ema21 and stoch_os_cross
        short_condition = downtrend_ema and bearish_vwap and near_ema21 and stoch_ob_cross
        if long_condition and st.position_size == 0:
            sl_price = close - (atr_val * self.sl_multi)
            tp1_price = close + (atr_val * self.tp1_multi)
            tp2_price = close + (atr_val * self.tp2_multi)
            st.entry("Long", st.long)
            st.exit("Long TP1", "Long", qty_percent=50, limit=tp1_price, stop=sl_price)
            st.exit("Long TP2", "Long", qty_percent=100, limit=tp2_price, stop=sl_price)
        if short_condition and st.position_size == 0:
            sl_price = close + (atr_val * self.sl_multi)
            tp1_price = close - (atr_val * self.tp1_multi)
            tp2_price = close - (atr_val * self.tp2_multi)
            st.entry("Short", st.short)
            st.exit("Short TP1", "Short", qty_percent=50, limit=tp1_price, stop=sl_price)
            st.exit("Short TP2", "Short", qty_percent=100, limit=tp2_price, stop=sl_price)
        if st.position_size > 0 and close < ema_slow:
            st.close("Long", comment="EMA50 Invalidation")
        if st.position_size < 0 and close > ema_slow:
            st.close("Short", comment="EMA50 Invalidation")
